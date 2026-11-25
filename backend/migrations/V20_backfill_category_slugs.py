"""
Migration V20: Backfill Category Slugs (Batch 6, 2026-11-20)

PURPOSE:
- Backfill unique slugs for all categories (production categories currently
  have slug: null, which breaks canonical category URLs).
- Deterministic slug generation: slugify(name), collision -> "-2", "-3", ...
  appended in stable document order (sorted by _id), so the same input data
  always produces the same slugs.
- Guard: a generated slug is rejected if it is ObjectId-like (24 hex chars),
  so /categories/{slug} can never be ambiguous with /categories/{ObjectId}
  (owner revision 6).
- Verifies idx_categories_slug_unique is exactly (slug asc, unique, sparse)
  with NO semantic extra option: partialFilterExpression, collation,
  TTL/expireAfterSeconds, hidden, wildcardProjection, text/geo extras or any
  unrecognized option fails closed BEFORE any write, naming the exact
  incompatible option detected (final review finding 3); the index is never
  dropped or replaced automatically; a missing index is created only in
  apply mode.
- Even an EMPTY migration plan (every category already has a slug) still
  verifies and reconciles the index (final review finding 2): dry-run
  reports and writes nothing; apply mode creates a missing index only after
  the index preconditions are validated (compatible-or-missing index, no
  duplicate slugs, no null/empty slugs) and a provenance backup is written
  first — index validation is never silently skipped.
- Processes the COMPLETE categories collection — no document cap
  (correction 8).

SAFETY (Batch 6 blockers 1-4 + final-review corrections 2-4 & 6):
- DEFAULT MODE IS DRY-RUN: prints a full report, writes NOTHING.
- Writes only with --apply, and ONLY AFTER the JSON backup of every category
  it will touch is written to migrations/backups/V20_categories_<ts>.json AND
  validated by reading it back. Index verification before that point is
  strictly read-only; the index itself is created LAST, after slugs are
  backfilled (blocker 1: no database mutation of any kind precedes a
  validated backup).
- Documents whose slug is null, "" or missing are backfilled BEFORE the
  unique sparse index is created, and index creation is skipped (reported as
  DEFERRED) if any conflicting document still holds a null/empty slug —
  a sparse index still indexes explicit nulls, so creating it over duplicate
  nulls would fail with E11000 (blocker 2).
- Every apply write is CONDITIONAL: it matches only documents whose slug is
  still missing/null/"" (the state the plan was generated from). If a slug
  was populated after plan generation, the write matches nothing, the
  concurrent value wins, and the conflict is reported (blocker 3).
- ROLLBACK IS CONFLICT-GUARDED (blocker 4 / final-review correction 2): the
  backup records the slug V20 assigned (assigned_slug); rollback restores
  the pre-migration state ONLY when the current slug still equals that
  assigned value AT THE MOMENT OF THE WRITE — the restore update itself is
  conditional on slug == assigned_slug, and its matched/modified results
  are checked. A slug changed after V20 — even between the verification
  read and the rollback write — is reported as a conflict and is NEVER
  overwritten.
- ROLLBACK PREFLIGHTS BEFORE ANY MUTATION (final review finding 1, HIGH):
  the COMPLETE rollback plan — backup structure, index provenance, every
  backed-up document's current state and rollback conflicts, and index
  constraints against the ENTIRE planned restored state (null/empty restores
  AND duplicate restored slugs) — is validated while strictly read-only.
  Any blocking conflict aborts BEFORE the index is dropped and before ANY
  document is modified. Race guards remain active during the writes
  themselves (conditional on assigned_slug at write time); concurrent
  changes are never overwritten.
- ROLLBACK HANDLES THE V20 INDEX (final-review correction 3): the backup
  records whether idx_categories_slug_unique existed before V20 or was
  created by it. If V20 created the index, rollback drops it FIRST, before
  restoring original null/missing slugs (a unique sparse index still
  indexes explicit nulls, so several slug=null restores would otherwise
  fail mid-rollback with E11000) and never recreates it. An index that
  existed BEFORE V20 is never dropped; unrelated indexes are untouched;
  a rollback that would place multiple explicit null slugs under a
  pre-existing unique index fails closed BEFORE touching any document.
- BACKUP FILES ARE EXCLUSIVE (final-review correction 4): backup files are
  created with O_CREAT|O_EXCL; on a name collision (second-resolution
  timestamp, concurrent run) a unique random suffix is appended instead of
  truncating. An existing backup is NEVER silently replaced.
- PRE-EXISTING DUPLICATE SLUGS FAIL CLOSED (final-review correction 6):
  before any backfill write, backup or index creation, existing non-empty
  slugs are scanned for duplicates; duplicates are reported and --apply
  refuses to proceed (dry-run reports them and still writes nothing).
- ROLLBACK RESTORES EXACT STATE (owner-approved exact rollback): the backup
  records, per category, the pre-migration `slug` AND `legacySlugs` state,
  including whether each field existed. Rollback restores both exactly:
  an absent field is $unset, a present field is $set to the recorded value
  (null stays null; an array is restored with its order and duplicates).
  The slug V20 assigned is never added to legacySlugs. legacyIds and unrelated
  fields are never written by rollback. Backups in the old V2 format have no
  legacySlugs state and are refused, never guessed. Run:
      python migrations/V20_backfill_category_slugs.py --rollback --backup migrations/backups/V20_categories_<ts>.json

SLUG RULES:
- lowercase, hyphen-separated, derived from category name (same slugify as
  the frontend sitemap fallback, so the 9 already-indexed name-slug URLs
  become canonical with no URL churn)
- unique (append -2, -3, ... on collision)
- immutable after creation (renames go through legacySlugs, see admin routes)

RUN (dry-run first, always):
    python migrations/V20_backfill_category_slugs.py
    python migrations/V20_backfill_category_slugs.py --apply
    python migrations/V20_backfill_category_slugs.py --verify   (read-only post-migration check)
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from urllib.parse import urlparse

# Round 3 (P1): no implicit .env loading. The target must be supplied in the
# process environment explicitly, so a stray .env cannot select a database.

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
INDEX_NAME = "idx_categories_slug_unique"

# Round 3 (P1): operator-approved target policy. Empty by default, so every run
# fails closed until the operator approves an exact (host, port, database) triple.
# Production names are always refused, even if someone adds them to the policy.
APPROVED_TARGETS = frozenset()  # e.g. {("127.0.0.1", 27117, "midconnect_v20_disposable")}
FORBIDDEN_DB_NAMES = frozenset({"b2b_marketplace", "midconnect", "admin", "config", "local"})


# Expected production mapping (name -> slug) from the hosted sitemap at
# baseline 09bc2fc. Used only to annotate the dry-run report; generation
# itself is always derived from the name.
EXPECTED_SLUGS = {
    "cleaning-products",
    "electrical-equipment-supplies",
    "electronics-it-industrial-automation",
    "lights-lighting-accessories",
    "metals-industrial-raw-materials",
    "panel-meters-and-accessories",
    "safety-products",
    "solar-equipment-panels",
    "vfd-plc-hmi-control-equipments",
}


# Backup format V3 (exact rollback): each record also captures the ORIGINAL
# legacySlugs state. V2 backups lack that state and are refused by rollback.
BACKUP_KIND = "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V3"


def original_legacy_slugs_problem(cat):
    """Return None when the document's legacySlugs can be recorded exactly.

    Absent is recorded as absent; an array of strings (possibly empty) is
    recorded verbatim. Anything else (null, a scalar, an array holding
    non-string entries) cannot be restored exactly, so the migration refuses
    to back it up and performs no write (fail closed, nothing guessed).
    """
    if "legacySlugs" not in cat:
        return None
    value = cat["legacySlugs"]
    if not isinstance(value, list):
        return (f"legacySlugs is {type(value).__name__}, not an array; its "
                "original state cannot be recorded exactly (fail-closed)")
    if not all(isinstance(item, str) for item in value):
        return ("legacySlugs holds a non-string entry; its original state "
                "cannot be recorded exactly (fail-closed)")
    return None


def slugify(name: str) -> str:
    """Same rules as V4/its frontend counterpart: lowercase, [a-z0-9-] only."""
    if not name:
        return ""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def is_objectid_like(slug: str) -> bool:
    """Owner revision 6: a 24-hex slug would be ambiguous with ObjectId URLs."""
    return bool(re.fullmatch(r"[0-9a-f]{24}", slug))


SLUG_FORMAT_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def validate_existing_slug(value):
    """F2: classify a category's existing `slug` field value.

    Returns "BACKFILL" for a missing field, null, or empty string (the only
    values V20 may fill). Returns "VALID" for a string that is already in the
    expected slug format (lowercase a-z/0-9 words joined by single hyphens,
    not ObjectId-like). Returns an error message (str) for anything else:
    numbers, booleans, objects, arrays, whitespace-only, uppercase, malformed
    or ObjectId-like strings. Invalid values are never overwritten.
    """
    if value is None or (isinstance(value, str) and value == ""):
        return "BACKFILL"
    if not isinstance(value, str):
        return f"not a string (type {type(value).__name__}, value {value!r})"
    if not SLUG_FORMAT_RE.fullmatch(value):
        return f"malformed slug {value!r} (expected lowercase a-z/0-9 words joined by single hyphens)"
    if is_objectid_like(value):
        return f"ObjectId-like slug {value!r} is ambiguous with /categories/<id>"
    return "VALID"


def generate_unique_slug(base_name: str, taken: set, doc_id: str) -> str:
    """Deterministic: slugify(name), then -2, -3, ... on collision.

    Correction 1: the empty/ObjectId-like fallback is ID-based — derived from
    the document's own id ("category-<last 8 hex>"), never a random UUID. The
    "category-" prefix guarantees the result is never ObjectId-like.
    """
    candidate = slugify(base_name)
    if not candidate or is_objectid_like(candidate):
        candidate = f"category-{str(doc_id)[-8:]}"
    final = candidate
    counter = 2
    while final in taken:
        final = f"{candidate}-{counter}"
        counter += 1
    return final


# Exit codes: 0 = complete (or dry-run report), 2 = blocked/fail-closed,
# 3 = INCOMPLETE: the run stopped short of a complete migration (deferred
# index, skipped conflicts, partial state). Incomplete runs never report
# success to the operator or to CI.
EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_INCOMPLETE = 3


class MigrationBlocked(RuntimeError):
    """Fail-closed precondition failure (correction 9): the migration refuses
    to touch data when the environment is not exactly as expected."""


# Round 3 (P4): set immediately before the first database write of a run, so
# the exception classifier can tell a pre-write block (exit 2) from a failure
# after writes may have happened (exit 3).
_MUTATION = {"started": False}


def _mark_mutation_started():
    _MUTATION["started"] = True


class TargetRefused(MigrationBlocked):
    """Round 3 (P1): raised before any MongoDB client is created when the
    target database is not explicitly approved, or the confirmation does not
    name the exact target. Maps to exit 2 (no database touched)."""


class InvalidExistingSlugs(MigrationBlocked):
    """F2: one or more categories hold an existing slug value that is not a
    valid slug. Raised before any backup or write."""


# Finding 3: options reported by index_information() that do NOT change what
# the index covers or does (server bookkeeping); everything else must be
# explicitly understood or the verification fails closed.
# 'name' is the index's own label. The live server did not report it in the
# probe, but some drivers/servers may; it changes neither coverage nor behaviour.
_BENIGN_INDEX_OPTIONS = frozenset({"key", "v", "background", "ns", "name"})
# Finding 3: options that WOULD change the index's semantics. The V20
# contract is an unconditional unique sparse single-key index — none of
# these may be present on idx_categories_slug_unique.
_SEMANTIC_INDEX_OPTIONS = (
    "partialFilterExpression",   # changes WHICH documents are indexed
    "collation",                 # changes HOW strings compare (uniqueness scope)
    "expireAfterSeconds",        # TTL: the index itself would DELETE documents
    "wildcardProjection",        # changes WHICH fields are indexed
    "hidden",                    # planner-visibility changes index semantics
    "clustered",                 # changes document storage itself
    "bucketSize",
    "weights",
    "default_language",
    "language_override",
    "textIndexVersion",
    "2dsphereIndexVersion",
    "bits",
    "max",
    "min",
)
# Boolean flags where an explicit False is semantically identical to absent.
_SEMANTIC_FLAG_OPTIONS = frozenset({"hidden", "clustered"})


def describe_index_incompatibilities(info: dict) -> list:
    """Finding 3: list EVERY way an existing idx_categories_slug_unique
    differs from the V20 contract: key=[('slug', 1)], unique=True, sparse=True
    and no semantic extra option. Returns one message per incompatibility,
    each naming the exact option detected; an empty list means compatible."""
    problems = []
    key = [tuple(kv) for kv in (info.get("key") or [])]
    if key != [("slug", 1)]:
        problems.append(f"key={key} (expected [('slug', 1)])")
    if not info.get("unique"):
        problems.append("unique is not True (duplicate slugs would be permitted)")
    if not info.get("sparse"):
        problems.append(
            "sparse is not True (documents with a missing slug would be "
            "indexed, breaking the null-backfill contract)"
        )
    for opt in _SEMANTIC_INDEX_OPTIONS:
        present = (
            opt in info if opt not in _SEMANTIC_FLAG_OPTIONS else bool(info.get(opt))
        )
        if present:
            problems.append(
                f"option {opt!r} = {info.get(opt)!r} changes index semantics "
                "(what the index covers or does); the V20 contract allows none"
            )
    known = (_BENIGN_INDEX_OPTIONS | frozenset(_SEMANTIC_INDEX_OPTIONS)
             | {"key", "unique", "sparse"})
    for opt in sorted(set(info) - known):
        problems.append(
            f"unrecognized option {opt!r} = {info.get(opt)!r} cannot be proven "
            "harmless — failing closed (finding 3)"
        )
    return problems


def find_slug_index(index_info: dict):
    """Find exactly one slug-related index, independent of its name."""
    candidates = []
    for name, info in (index_info or {}).items():
        key = [tuple(kv) for kv in (info.get("key") or [])]
        if name == INDEX_NAME or any(field == "slug" for field, _ in key):
            candidates.append((name, info))

    if not candidates:
        return None, None, []

    if len(candidates) > 1:
        names = sorted(name for name, _ in candidates)
        return None, None, [
            f"multiple slug-related indexes found: {names!r}; "
            "cannot safely choose one"
        ]

    name, info = candidates[0]
    return name, info, describe_index_incompatibilities(info)


async def verify_slug_index(db, create: bool) -> dict:
    """Verify idx_categories_slug_unique is EXACTLY: key=[('slug', 1)],
    unique=True, sparse=True — with NO extra option that changes index
    semantics (partialFilterExpression, collation, TTL expireAfterSeconds,
    hidden, wildcardProjection, text/geo extras, or anything unrecognized).

    Finding 3: EVERY observed option is validated against the contract; an
    existing index that is malformed or carries ANY incompatible option
    raises MigrationBlocked naming exactly which option was detected, BEFORE
    any data write. The index is never dropped or replaced automatically.
    A missing index is created only in apply mode; in dry-run mode its
    absence is reported without writes. Finding 2: this verification ALWAYS
    runs — even when the migration plan is empty.
    """
    indexes = await db.categories.index_information()
    actual_name, info, problems = find_slug_index(indexes)

    if actual_name is not None:
        if problems:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 3): existing slug index {actual_name!r} "
                "is incompatible with the V20 contract (expected exactly "
                "key=[('slug', 1)], unique=True, sparse=True, no semantic "
                "extras). Detected: " + "; ".join(problems) + ". No data was "
                "written; the index was NOT dropped or replaced automatically."
            )
        key = [tuple(kv) for kv in (info.get("key") or [])]
        return {
            "exists": True,
            "key": key,
            "unique": bool(info.get("unique")),
            "sparse": bool(info.get("sparse")),
            "actual_name": actual_name,
            "action": "verified",
        }

    if problems:
        raise MigrationBlocked(
            "FAIL-CLOSED: " + "; ".join(problems)
            + ". No data was written."
        )

    if create:
        await db.categories.create_index(
            [("slug", 1)], unique=True, sparse=True, name=INDEX_NAME
        )
        return {
            "exists": False,
            "actual_name": INDEX_NAME,
            "action": "created (apply mode)",
        }

    return {
        "exists": False,
        "actual_name": None,
        "action": "missing (dry-run: --apply would create it)",
    }


async def build_slug_plan(db):
    """Scan the COMPLETE categories collection; return (plan, backup_records).

    Correction 8: no document cap — every category is considered in stable
    _id order, so the plan is deterministic regardless of collection size.
    Correction 10: each backup record captures the EXACT pre-migration slug
    field state: the value (str or None) AND whether the field existed at all
    (slug_field_present), so rollback can restore field-absent documents to
    field-absent instead of injecting a null.
    """
    total = await db.categories.count_documents({})
    print(f"\nFound {total} categories (complete collection, sorted by _id for determinism)")

    taken = {s for s in await db.categories.distinct("slug") if isinstance(s, str) and s}
    plan = []
    backup_records = []
    invalid = []
    async for cat in db.categories.find({}, {"_id": 1, "name": 1, "slug": 1, "legacySlugs": 1}).sort("_id", 1):
        name = cat.get("name", "")
        existing = cat.get("slug")
        # F2: every existing value is validated, not just truthy ones. Invalid
        # values are collected and reported; the migration then fails closed.
        state = validate_existing_slug(existing) if "slug" in cat else "BACKFILL"
        if state == "BACKFILL":
            legacy_problem = original_legacy_slugs_problem(cat)
            if legacy_problem:
                invalid.append({"_id": str(cat["_id"]), "name": name,
                                "slug": existing, "reason": legacy_problem})
                continue
        elif state == "VALID":
            print(f"  [SKIP] {name!r} - already has valid slug: {existing}")
            continue
        else:
            invalid.append({"_id": str(cat["_id"]), "name": name, "slug": existing, "reason": state})
            continue
        new_slug = generate_unique_slug(name, taken, str(cat["_id"]))
        taken.add(new_slug)
        matches_expected = new_slug in EXPECTED_SLUGS
        note = "" if matches_expected else "  (NOTE: differs from hosted-sitemap slug)"
        print(f"  [PLAN] {name!r} -> {new_slug}{note}")
        plan.append({"_id": str(cat["_id"]), "name": name, "slug": new_slug})
        record = {
            "_id": str(cat["_id"]),
            "name": name,
            "slug": existing,
            "slug_field_present": "slug" in cat,
            # Blocker 4: rollback proves the current slug is still the one V20
            # assigned before it restores anything.
            "assigned_slug": new_slug,
            # V3 (exact rollback): the ORIGINAL legacySlugs state. V20 never
            # writes legacySlugs, so this is also the state rollback restores.
            "legacySlugs_field_present": "legacySlugs" in cat,
        }
        if "legacySlugs" in cat:
            record["legacySlugs"] = list(cat["legacySlugs"])
        backup_records.append(record)
    if invalid:
        raise InvalidExistingSlugs(report_invalid_slugs(invalid))
    return plan, backup_records


def report_invalid_slugs(invalid) -> str:
    """F2: print and return a clear report of every invalid existing slug."""
    lines = [f"FAIL-CLOSED (F2): {len(invalid)} category document(s) hold an "
             "invalid existing slug. No backup, backfill or index write was "
             "made. Invalid values are never overwritten; correct them "
             "manually and re-run V20:"]
    for row in invalid:
        lines.append(f"  _id={row['_id']} name={row['name']!r}: {row['reason']}")
    message = "\n".join(lines)
    print("\n" + message)
    return message


def _open_backup_file_exclusively():
    """Correction 4: create the backup file EXCLUSIVELY (O_CREAT | O_EXCL).

    An existing backup file — including one being written by a concurrent
    run within the same second — is never silently replaced: on a name
    collision a unique random suffix is appended and creation is retried
    until an unused name is claimed. Returns (path, fd)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = os.path.join(BACKUP_DIR, f"V20_categories_{ts}")
    last_error = None
    for attempt in range(8):
        candidate = base if attempt == 0 else f"{base}_{uuid4().hex[:8]}"
        path = f"{candidate}.json"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            return path, fd
        except FileExistsError as exc:
            # The exact name is taken (an earlier backup or a concurrent
            # run): NEVER truncate it — retry under a fresh unique name.
            last_error = exc
    raise MigrationBlocked(
        f"Backup collision (correction 4): could not claim an unused backup "
        f"file under {BACKUP_DIR!r} (last conflict on {base}.json: "
        f"{last_error}). No database write was made; existing backups are "
        "never replaced."
    )


def write_and_validate_backup(backup_records, index_status) -> str:
    """Blocker 1 + corrections 3 & 4: write the JSON backup EXCLUSIVELY, then
    read it back and compare, so a validated backup exists on disk before ANY
    database write may happen. The backup leads with a _meta record capturing
    the index provenance (existed before V20 vs created by V20) so rollback
    can treat the unique index safely (correction 3)."""
    meta = {
        "_meta": {
            "kind": BACKUP_KIND,
            "index_name": INDEX_NAME,
            "index_actual_name": (
                index_status.get("actual_name")
                or (INDEX_NAME if index_status.get("exists") else None)
            ),
            "index_existed_before_v20": bool(index_status.get("exists")),
            "index_created_by_v20": not bool(index_status.get("exists")),
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        }
    }
    payload = [meta] + list(backup_records)
    # Exit-code contract: a backup that cannot be created or read back is a
    # precondition failure BEFORE any database write (exit 2). I/O and JSON
    # errors are therefore converted to MigrationBlocked, never a traceback.
    try:
        backup_path, fd = _open_backup_file_exclusively()
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            # Round 3 (P6): the backup must be durable on disk before it is
            # considered validated and before any database write may follow.
            os.fsync(f.fileno())
        with open(backup_path, encoding="utf-8") as f:
            validated = json.load(f)
    except (OSError, ValueError) as exc:
        raise MigrationBlocked(
            f"Backup creation/validation failed ({exc}). No database write was "
            "made; any partially written backup file is kept, never deleted."
        )
    if validated != payload:
        raise MigrationBlocked(
            "Backup validation failed: the written backup does not read back "
            "identically. Refusing to touch the database (no writes made)."
        )
    return backup_path


async def apply_slug_writes(db, plan) -> dict:
    """Blocker 3: apply every planned slug CONDITIONALLY.

    The filter matches only the pre-migration state of a planned document
    (slug missing, null, or empty string). If the slug was populated after
    the plan was generated, the filter matches nothing, the concurrent value
    wins, and the document is reported as a conflict — never overwritten.
    """
    updated = 0
    conflicts = []
    for item in plan:
        guard = {"_id": ObjectId(item["_id"]), "slug": {"$in": [None, ""]}}
        res = await db.categories.update_one(guard, {"$set": {"slug": item["slug"]}})
        if res.modified_count == 1:
            updated += 1
            continue
        current = await db.categories.find_one(
            {"_id": ObjectId(item["_id"])}, {"slug": 1, "name": 1}
        )
        current_slug = (current or {}).get("slug")
        if not current:
            reason = "document deleted after the plan was generated"
        elif current_slug:
            reason = "slug populated after the plan was generated"
        else:
            # Still null/empty although the guarded write did not apply (a
            # tight write race): retry once, then report instead of forcing.
            res2 = await db.categories.update_one(
                guard, {"$set": {"slug": item["slug"]}}
            )
            if res2.modified_count == 1:
                updated += 1
                continue
            reason = "slug still empty after one retry (write raced)"
        conflicts.append({
            "_id": item["_id"],
            "name": (current or {}).get("name", item.get("name")),
            "current_slug": current_slug,
            "planned_slug": item["slug"],
            "reason": reason,
        })
    return {"updated": updated, "conflicts": conflicts}


async def find_preexisting_slug_duplicates(db) -> list:
    """Correction 6: scan for duplicate NON-EMPTY slugs already present.

    Null/empty/missing slugs are the legitimate backfill targets; only real
    string slugs can violate the intended unique-slug integrity. Returns one
    row per duplicated slug ({slug, count, ids, names}), sorted by slug for a
    deterministic report."""
    pipeline = [
        {"$match": {"slug": {"$type": "string", "$gt": ""}}},
        {"$group": {"_id": "$slug", "ids": {"$addToSet": "$_id"},
                    "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"_id": 1}},
    ]
    dupes = []
    async for row in db.categories.aggregate(pipeline):
        names = []
        for doc_id in row["ids"]:
            doc = await db.categories.find_one({"_id": doc_id}, {"name": 1})
            names.append((doc or {}).get("name", str(doc_id)))
        dupes.append({
            "slug": row["_id"],
            "count": row["count"],
            "ids": [str(i) for i in row["ids"]],
            "names": names,
        })
    return dupes


def report_slug_duplicates(dupes) -> None:
    print("\nFAIL-CLOSED (correction 6): duplicate pre-existing slugs detected "
          f"({len(dupes)} slug(s)):")
    for d in dupes:
        listing = ", ".join(
            f"{name!r}({_id})" for name, _id in zip(d["names"], d["ids"])
        )
        print(f"  slug={d['slug']!r} x{d['count']}: {listing}")
    print("A unique slug index cannot be established over duplicate values. "
          "Resolve the duplicates manually, then re-run V20.")


async def create_slug_index_guarded(db, backup_path: str, backfilled: int, conflicts: int = 0) -> dict:
    """F1: the ONLY place the unique slug index is created.

    Immediately before create_index, re-validates the index preconditions from
    the live collection (not from plan time): (a) no duplicate non-empty slugs,
    (b) no remaining null/empty slugs (an explicit null would collide under a
    unique sparse index). If either fails, or create_index itself fails
    (e.g. a concurrent insert raced past the checks, surfacing as
    DuplicateKeyError), nothing is claimed: a MigrationBlocked is raised whose
    message states the partial state (backup path, slugs backfilled, index
    NOT created) so the operator knows exactly what changed. Existing indexes
    are never dropped or modified here; an existing compatible index is left
    as-is by verify_slug_index.
    """
    partial = (f"PARTIAL STATE: backup written at {backup_path!r}; {backfilled} "
               f"category slug(s) backfilled; {conflicts} conflict(s) skipped; "
               f"index {INDEX_NAME!r} NOT created. Resolve the issue and re-run V20 "
               "(reruns are idempotent: existing valid slugs are skipped).")
    dupes = await find_preexisting_slug_duplicates(db)
    if dupes:
        report_slug_duplicates(dupes)
        raise MigrationBlocked(
            f"FAIL-CLOSED (F1): {len(dupes)} duplicate slug(s) present immediately "
            "before unique-index creation; the index was NOT created and "
            "success is NOT claimed. " + partial
        )
    remaining = await db.categories.count_documents({"slug": {"$exists": True, "$in": [None, ""]}})
    if remaining:
        raise MigrationBlocked(
            f"DEFERRED (F1): {remaining} category document(s) hold a null/empty "
            "slug immediately before index creation; the index was NOT created "
            "and success is NOT claimed. " + partial
        )
    try:
        return await verify_slug_index(db, create=True)
    except DuplicateKeyError as exc:
        raise MigrationBlocked(
            f"FAIL-CLOSED (F1): create_index({INDEX_NAME!r}) raced a concurrent "
            f"write and hit a duplicate key ({exc}). The index was NOT created "
            "and success is NOT claimed. " + partial
        )
    except Exception as exc:
        raise MigrationBlocked(
            f"FAIL-CLOSED (F1): create_index({INDEX_NAME!r}) failed ({exc}). "
            "The index was NOT created and success is NOT claimed. " + partial
        )


def resolve_target(env=None) -> tuple:
    """Round 3 (P1): fail-closed target resolution. Returns (host, port, db_name).

    Pure: reads only the given environment mapping, never prints the URL and
    never creates a client. Refuses (TargetRefused) when MONGO_URL or DB_NAME
    is missing or empty, when DB_NAME is a production name, or when the exact
    (host, port, db_name) triple is not in APPROVED_TARGETS.
    """
    env = os.environ if env is None else env
    mongo_url = (env.get("MONGO_URL") or "").strip()
    if not mongo_url:
        raise TargetRefused("MONGO_URL is not set; no database target was resolved.")
    raw_db = env.get("DB_NAME")
    if raw_db is None or not raw_db.strip():
        raise TargetRefused(
            "DB_NAME must be set explicitly and non-empty (no implicit default)."
        )
    db_name = raw_db.strip()
    if db_name in FORBIDDEN_DB_NAMES:
        raise TargetRefused(f"database name {db_name!r} is a protected name and is refused.")
    try:
        parsed = urlparse(mongo_url)
        host = parsed.hostname
        port = parsed.port or 27017
    except ValueError:
        raise TargetRefused("MONGO_URL could not be parsed; no connection attempted.")
    if not host:
        raise TargetRefused("MONGO_URL has no host; no connection attempted.")
    if (host, port, db_name) not in APPROVED_TARGETS:
        raise TargetRefused(
            f"target host/port/database ({host}:{port}/{db_name}) is not in the "
            "operator-approved APPROVED_TARGETS policy; refusing before connecting."
        )
    return host, port, db_name


def require_confirmation(mode: str, db_name: str, confirm) -> None:
    """Round 3 (P1): --apply and --rollback each require their own explicit
    confirmation that names the exact target database, e.g.
    `--confirm-apply <db_name>` or `--confirm-rollback <db_name>`."""
    if mode not in ("apply", "rollback"):
        raise TargetRefused(f"unknown mode {mode!r}")
    if confirm != db_name:
        raise TargetRefused(
            f"{mode} requires --confirm-{mode} with the exact target database name "
            f"({db_name!r}); the confirmation is missing or does not match. Nothing was touched."
        )


def evaluate_expected_public_slugs(rows, final_slugs) -> list:
    """Round 3 (P2): pure check that every required public slug is reachable.

    rows: iterable of {"_id", "name"}; final_slugs: {str(_id): slug} as it
    WILL be after the planned writes. For each of the nine EXPECTED_SLUGS
    returns a failure string unless exactly one category's name slugifies to
    it AND exactly one category holds it, and that holder is that same
    category. An earlier _id or a duplicate name would otherwise take the
    public URL and push the intended category to a -N suffix.
    """
    rows = [dict(r) for r in rows]
    failures = []
    for expected in sorted(EXPECTED_SLUGS):
        same_name = [r for r in rows if slugify(r.get("name") or "") == expected]
        holders = sorted(cid for cid, s in final_slugs.items() if s == expected)
        if len(same_name) != 1:
            names = [f"{r.get('name')!r}({r.get('_id')})" for r in same_name] or ["none"]
            failures.append(
                f"public slug {expected!r}: {len(same_name)} categories have a name "
                f"that slugifies to it ({', '.join(names)}); exactly one is required"
            )
            continue
        owner = str(same_name[0]["_id"])
        if not holders:
            failures.append(f"public slug {expected!r} would be held by no category")
        elif holders != [owner]:
            failures.append(
                f"public slug {expected!r} would be held by {', '.join(holders)} "
                f"instead of {owner} (earlier _id or duplicate name takes the URL)"
            )
    return failures


async def check_expected_public_slugs(db, plan) -> list:
    """Round 3 (P2): read-only. Builds the post-plan slug map from the live
    collection and returns evaluate_expected_public_slugs() failures."""
    rows = await db.categories.find({}, {"_id": 1, "name": 1, "slug": 1}).to_list(None)
    planned = {item["_id"]: item["slug"] for item in plan}
    final = {}
    for row in rows:
        cid = str(row["_id"])
        if cid in planned:
            final[cid] = planned[cid]
        elif isinstance(row.get("slug"), str) and validate_existing_slug(row["slug"]) == "VALID":
            final[cid] = row["slug"]
    return evaluate_expected_public_slugs(rows, final)


async def run_migration(apply: bool, rollback_path: str = None, confirm_db: str = None) -> int:
    try:
        host, port, db_name = resolve_target()
        if apply:
            require_confirmation("apply", db_name, confirm_db)
        if rollback_path:
            require_confirmation("rollback", db_name, confirm_db)
    except TargetRefused as exc:
        print(f"TARGET REFUSED (exit 2): {exc}")
        return EXIT_BLOCKED
    mongo_url = os.environ["MONGO_URL"].strip()
    client = AsyncIOMotorClient(mongo_url)
    _MUTATION["started"] = False
    try:
        return await _run_migration_with_client(client, db_name, apply, rollback_path, host, port)
    except (MigrationBlocked, PyMongoError, Exception) as exc:
        # Round 3 (P4): classify, never escape as exit 1. Before the first
        # database write this is a block (2); after a write may have happened
        # it is an incomplete run (3).
        label = type(exc).__name__
        if _MUTATION["started"]:
            print(f"\nINCOMPLETE (exit 3): {label} after database writes may have "
                  f"started: {exc}. Inspect the backup and re-run or roll back.")
            return EXIT_INCOMPLETE
        print(f"\nBLOCKED (exit 2): {label} before any database mutation: {exc}")
        return EXIT_BLOCKED
    finally:
        client.close()


async def _run_migration_with_client(client, db_name, apply, rollback_path, host, port) -> int:
    db = client[db_name]
    print(f"TARGET: {host}:{port}/{db_name} (approved)")

    print("=" * 60)
    print("MIGRATION V20: Backfill Category Slugs")
    print(f"MODE: {'APPLY' if apply else 'DRY-RUN (no writes)'}")
    print("=" * 60)

    # ---- Rollback path ----
    if rollback_path:
        return await do_rollback(db, rollback_path)

    # SAFETY ORDER (blockers 1-4): index verification here is strictly
    # READ-ONLY (a malformed existing index still fails closed); the backup,
    # validation, conditional slug writes, and only then index creation, in
    # that order. No database mutation precedes a validated backup.
    index_status = await verify_slug_index(db, create=False)
    print(f"\nIndex check ({INDEX_NAME}): {index_status}")

    plan, backup_records = await build_slug_plan(db)

    # ---- Correction 6: pre-existing duplicate slugs fail closed BEFORE any
    # mutation (backfill writes, backup, index creation). Read-only scan.
    dupes = await find_preexisting_slug_duplicates(db)
    if dupes:
        report_slug_duplicates(dupes)
        if apply:
            raise MigrationBlocked(
                f"FAIL-CLOSED (correction 6): {len(dupes)} duplicate pre-existing "
                "slug(s) detected. No backfill write was made, no backup was "
                "written, and no index was created; the migration refuses to "
                "proceed because the intended unique-slug integrity cannot be "
                "established."
            )
        # Exit-code contract: a duplicate pre-existing slug is exit 2 in every
        # mode. Dry-run still writes nothing, but reports the failure honestly
        # rather than returning success for a migration --apply would refuse.
        print("DRY-RUN BLOCKED (exit 2): --apply would fail closed on these "
              "duplicates (correction 6); nothing was written.")
        return 2

    # ---- Round 3 (P2): the nine mandatory public slugs must be reachable
    # after the plan. Read-only; in dry-run it reports and exits 2, in apply it
    # refuses before any backup or write.
    slug_failures = await check_expected_public_slugs(db, plan)
    if slug_failures:
        print("EXPECTED PUBLIC SLUG MISMATCH (P2): the planned mapping would not "
              "satisfy the required public URLs:")
        for failure in slug_failures:
            print(f"  [FAIL] {failure}")
        if apply:
            raise MigrationBlocked(
                f"{len(slug_failures)} expected public slug(s) not satisfied. "
                "No backup, backfill or index write was made."
            )
        print("DRY-RUN BLOCKED (exit 2): the plan does not satisfy the expected "
              "public slugs; nothing was written.")
        return EXIT_BLOCKED

    if not plan:
        # Finding 2: an EMPTY migration plan does NOT skip index validation.
        # The read-only index verification above already ran (and failed
        # closed on any incompatible index), and the duplicate-slug
        # precondition above already failed closed in apply mode. Dry-run
        # stays strictly read-only; apply mode reconciles (creates) a missing
        # index — still backup-first (blocker 1: even an index-only run
        # records its provenance backup before the mutation).
        print("\nNothing to backfill: all categories already have slugs.")
        if not apply:
            if index_status.get("exists") is False:
                print("Index note: idx_categories_slug_unique is missing; "
                      "--apply still reconciles it after re-validating the "
                      "index preconditions (finding 2) — but dry-run writes "
                      "nothing.")
            print("DRY-RUN ONLY — no writes performed. Re-run with --apply to execute.")
            return 0
        if index_status.get("exists"):
            print(f"Index check ({INDEX_NAME}): already exists and is verified "
                  "compatible — nothing to reconcile.")
            return 0
        # Apply-mode index preconditions are re-validated NOW (not trusted
        # from plan time): a concurrent insert could have added a null/empty
        # slug since the plan was generated, and creating a unique sparse
        # index over duplicate nulls would fail with E11000.
        remaining = await db.categories.count_documents(
            {"slug": {"$exists": True, "$in": [None, ""]}}
        )
        if remaining:
            print(f"DEFERRED: {remaining} category document(s) hold a "
                  "null/empty slug (concurrent writes since the plan was "
                  f"generated); creating the unique index {INDEX_NAME} over "
                  "duplicate nulls would fail with E11000. Re-run V20 once "
                  "the writes settle; the index is created on a clean pass.")
            print("INCOMPLETE: index not created; exit 3 (success NOT claimed).")
            return EXIT_INCOMPLETE
        backup_path = write_and_validate_backup([], index_status)
        _mark_mutation_started()
        print(f"Backup written and validated: {backup_path} "
              "(0 document records; index provenance recorded)")
        created = await create_slug_index_guarded(db, backup_path, backfilled=0)
        print(f"Index check ({INDEX_NAME}): {created}")
        print(f"Rollback with: python migrations/{os.path.basename(__file__)} --rollback --backup {backup_path}")
        return 0

    print(f"\nPlan: {len(plan)} categories would receive slugs.")

    if not apply:
        if index_status.get("exists") is False:
            print("Index note: idx_categories_slug_unique is missing; --apply "
                  "creates it AFTER slugs are backfilled and validated — never "
                  "before the backup — so documents still holding null/empty "
                  "slugs cannot break index creation with duplicate nulls.")
        print("DRY-RUN ONLY — no writes performed. Re-run with --apply to execute.")
        return 0

    # ---- 1. Backup written AND validated before ANY write (blocker 1) ----
    # Correction 3: the backup also records the index provenance (pre-existing
    # vs created by V20) so the rollback can treat the unique index safely.
    backup_path = write_and_validate_backup(backup_records, index_status)
    print(f"Backup written and validated: {backup_path} "
          f"({len(backup_records)} exact slug states)")

    # ---- 2. Conditional writes with conflict detection (blocker 3) ----
    try:
        _mark_mutation_started()
        stats = await apply_slug_writes(db, plan)
    except Exception as exc:
        # The backup exists, so the state is partial, not blocked: exit 3.
        print(f"\nINCOMPLETE (exit 3): backfill write failed part-way ({exc}). "
              f"Backup {backup_path!r} holds the exact pre-V20 state. Rerun V20 "
              "(idempotent) or roll back with --rollback.")
        return EXIT_INCOMPLETE
    print(f"\nApplied: {stats['updated']} categories updated.")
    for conflict in stats["conflicts"]:
        print(f"  [CONFLICT] _id={conflict['_id']} name={conflict.get('name')!r}: "
              f"{conflict['reason']}; current slug is "
              f"{conflict['current_slug']!r}, planned slug "
              f"{conflict['planned_slug']!r} was NOT applied (concurrent value "
              "preserved)")
    if stats["conflicts"]:
        print(f"{len(stats['conflicts'])} conflict(s) skipped safely; "
              "re-run V20 once the concurrent writes settle.")

    # ---- 3. Index creation LAST (blockers 1 & 2, F1) ----
    if index_status.get("exists") is False:
        remaining = await db.categories.count_documents(
            {"slug": {"$exists": True, "$in": [None, ""]}}
        )
        if remaining:
            print(f"DEFERRED: {remaining} category document(s) still hold a "
                  "null/empty slug (concurrent conflicts); creating the unique "
                  f"index {INDEX_NAME} over duplicate nulls would fail with "
                  "E11000. Resolve the conflicts and re-run V20; the index is "
                  "created on a clean pass.")
            print(f"PARTIAL STATE: backup {backup_path!r}; {stats['updated']} "
                  f"slug(s) backfilled; {len(stats['conflicts'])} conflict(s); "
                  f"index {INDEX_NAME!r} NOT created; success NOT claimed.")
            return EXIT_INCOMPLETE
        # Exit-code contract: slugs were already written by this point, so an
        # index failure is an INCOMPLETE migration (exit 3), not a block.
        try:
            created = await create_slug_index_guarded(
                db, backup_path, backfilled=stats["updated"],
                conflicts=len(stats["conflicts"]),
            )
        except MigrationBlocked as exc:
            print(f"\nINCOMPLETE (exit 3): index creation failed after backfill: {exc}")
            return EXIT_INCOMPLETE
        print(f"Index check ({INDEX_NAME}): {created}")

    print(f"Rollback with: python migrations/{os.path.basename(__file__)} --rollback --backup {backup_path}")
    if stats["conflicts"]:
        # Skipped conflicts mean planned categories did not receive their slug:
        # the migration is incomplete even though the index may now exist.
        print(f"INCOMPLETE: {len(stats['conflicts'])} planned slug(s) not applied; exit 3.")
        return EXIT_INCOMPLETE
    return EXIT_OK


def _load_and_validate_rollback_backup(backup_path: str):
    """Finding 1: parse and STRUCTURALLY validate the rollback backup BEFORE
    any database access. Returns (meta, docs). Raises MigrationBlocked — with
    ZERO mutations — when the file is not a well-formed V20 backup."""
    try:
        with open(backup_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as exc:
        raise MigrationBlocked(
            f"FAIL-CLOSED (finding 1): rollback backup {backup_path!r} cannot "
            f"be read or parsed as JSON ({exc}). No database access was made."
        )
    if not isinstance(raw, list):
        raise MigrationBlocked(
            f"FAIL-CLOSED (finding 1): rollback backup {backup_path!r} must "
            "be a JSON array of records. No database access was made."
        )
    meta = None
    docs = []
    seen_ids = set()
    for rec in raw:
        if not isinstance(rec, dict):
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup record is not an object: "
                f"{rec!r}. Nothing was mutated."
            )
        if isinstance(rec.get("_meta"), dict):
            if meta is not None:
                raise MigrationBlocked(
                    "FAIL-CLOSED (finding 1): backup contains more than one "
                    "_meta record. Nothing was mutated."
                )
            if "_id" in rec:
                raise MigrationBlocked(
                    "FAIL-CLOSED (finding 1): ambiguous backup record carries "
                    f"both _meta and _id: {rec!r}. Nothing was mutated."
                )
            meta = rec["_meta"]
            continue
        _id = rec.get("_id")
        if _id is None:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): backup record without _id: "
                f"{rec!r}. Nothing was mutated."
            )
        try:
            ObjectId(_id)
        except Exception as exc:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): backup record _id {_id!r} is not a "
                f"valid ObjectId ({exc}). Nothing was mutated."
            )
        assigned = rec.get("assigned_slug")
        if not isinstance(assigned, str) or not assigned:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): backup record {_id} has no usable "
                "assigned_slug — rollback cannot prove the current slug was "
                "set by V20. Nothing was mutated."
            )
        if not isinstance(rec.get("slug_field_present"), bool):
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): backup record {_id} is missing the "
                "boolean slug_field_present. Nothing was mutated."
            )
        rec_slug = rec.get("slug")
        if rec_slug is not None and not isinstance(rec_slug, str):
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): backup record {_id} has a "
                f"non-string, non-null slug {rec_slug!r}. Nothing was mutated."
            )
        if rec.get("slug_field_present") is False and rec_slug is not None:
            raise MigrationBlocked(
                f"FAIL-CLOSED (rollback review): backup record {_id} says the "
                f"slug field was absent but records slug {rec_slug!r}; the "
                "record is internally inconsistent. Nothing was mutated."
            )
        if _id in seen_ids:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): duplicate backup record for _id "
                f"{_id}. Nothing was mutated."
            )
        # V3 (exact rollback): the original legacySlugs state must be recorded.
        # A V2 record (or any record lacking it) cannot be restored exactly, so
        # it is refused before any database access. Nothing is guessed.
        legacy_present = rec.get("legacySlugs_field_present")
        if not isinstance(legacy_present, bool):
            raise MigrationBlocked(
                f"FAIL-CLOSED (exact rollback): backup record {_id} has no "
                "legacySlugs_field_present flag (V2 backups cannot be restored "
                "exactly). Nothing was mutated."
            )
        if legacy_present:
            original_legacy = rec.get("legacySlugs")
            if not isinstance(original_legacy, list) or not all(
                isinstance(item, str) for item in original_legacy
            ):
                raise MigrationBlocked(
                    f"FAIL-CLOSED (exact rollback): backup record {_id} has a "
                    "legacySlugs value that is not an array of strings. Nothing "
                    "was mutated."
                )
        elif "legacySlugs" in rec:
            raise MigrationBlocked(
                f"FAIL-CLOSED (exact rollback): backup record {_id} records "
                "legacySlugs although it was absent before V20. Nothing was "
                "mutated."
            )
        seen_ids.add(_id)
        docs.append(rec)
    if meta is not None:
        if meta.get("kind") != BACKUP_KIND:
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta.kind "
                f"{meta.get('kind')!r} is not this migration's exact-rollback "
                f"backup format ({BACKUP_KIND!r}). Nothing was mutated."
            )
        if meta.get("index_name") != INDEX_NAME:
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta.index_name "
                f"{meta.get('index_name')!r} does not belong to "
                f"{INDEX_NAME!r}. Nothing was mutated."
            )
        actual_name = meta.get("index_actual_name")
        if actual_name is not None and (
            not isinstance(actual_name, str) or not actual_name.strip()
        ):
            raise MigrationBlocked(
                "FAIL-CLOSED: backup _meta.index_actual_name must be a "
                "non-empty string or null. Nothing was mutated."
            )
        created = meta.get("index_created_by_v20")
        existed = meta.get("index_existed_before_v20")
        if not isinstance(created, bool) or not isinstance(existed, bool):
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta index provenance flags "
                "must both be booleans. Nothing was mutated."
            )
        if created == existed:
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta must claim exactly "
                "one of index_created_by_v20 and index_existed_before_v20. "
                "Nothing was mutated."
            )
        if created and actual_name not in (None, INDEX_NAME):
            raise MigrationBlocked(
                "FAIL-CLOSED: a V20-created index must use the reserved "
                f"name {INDEX_NAME!r}, not {actual_name!r}. Nothing was mutated."
            )
    return meta, docs


_ABSENT = object()


def _legacy_matches_v20_state(doc, current_legacy) -> bool:
    """True when legacySlugs is still the exact state V20 left behind, i.e.
    the state the backup recorded. Any later change is a conflict."""
    if doc.get("legacySlugs_field_present"):
        return isinstance(current_legacy, list) and current_legacy == doc.get("legacySlugs")
    return current_legacy is _ABSENT


def _already_restored(doc, current) -> bool:
    """Rollback rerun safety: True when the live document is already in its
    exact pre-V20 state (so a previous rollback run restored it). Such a
    document is a no-op, not a conflict."""
    slug_ok = (
        ("slug" in current and current["slug"] == doc.get("slug"))
        if doc.get("slug_field_present") else ("slug" not in current)
    )
    legacy_current = current.get("legacySlugs", _ABSENT)
    if doc.get("legacySlugs_field_present"):
        legacy_ok = isinstance(legacy_current, list) and legacy_current == doc.get("legacySlugs")
    else:
        legacy_ok = legacy_current is _ABSENT
    return slug_ok and legacy_ok


async def do_rollback(db, backup_path: str) -> int:
    """Conflict-guarded, exact-state rollback (blocker 4 + corrections 2-3 +
    final review findings 1-3).

    FINDING 1 (HIGH): the COMPLETE rollback plan is built and validated in a
    strictly READ-ONLY preflight BEFORE any mutation, in this order:
    1. the backup file is parsed and STRUCTURALLY validated (record shapes,
       ObjectId _ids, assigned_slug/slug_field_present/slug types, exactly
       one _meta with self-consistent provenance) before ANY database access;
    2. every backed-up document's current state and rollback conflict is
       validated — a slug changed after V20 is a BLOCKING conflict;
    3. the index plan is decided from the recorded provenance: an index V20
       created is dropped only if it still matches the exact definition V20
       creates (finding 3, reused); a pre-existing index is NEVER dropped;
    4. index constraints are validated against the ENTIRE planned restored
       state: null/empty restores AND duplicate restored slugs (within the
       plan and against documents outside the backup).
    If ANY blocking conflict exists, the rollback aborts BEFORE the index is
    dropped and before ANY document is modified. Only after preflight
    succeeds does execution begin; race guards stay active during the writes
    themselves, and concurrent changes are never overwritten.
    For every restorable category:
    - field was present  -> $set the exact pre-migration value (even null);
      field was ABSENT -> $unset the field (restore true absence).
    Correction 2: the restoration write itself is CONDITIONAL on the slug
    still being the one V20 assigned at the moment of the update — a change
    that lands between the preflight read and the rollback write makes the
    filter match nothing; the concurrent value is never overwritten and the
    conflict is reported from the matched/modified results.
    Correction 3: an index V20 created is dropped BEFORE any restore
    (restoring several explicit null slugs under the unique sparse index
    would fail mid-rollback with E11000); an index that existed before V20 is
    never dropped, and unrelated indexes are preserved.
    EXACT ROLLBACK (owner-approved): the rollback restores the EXACT
    pre-migration state of BOTH slug and legacySlugs. slug: field absent ->
    $unset; present (including null/"") -> $set to the recorded value.
    legacySlugs: absent before V20 -> $unset; present -> $set to the recorded
    array, preserving content and order. The slug V20 assigned is never added
    to legacySlugs (V20 does not write legacySlugs, so nothing it assigned
    must be removed from there). legacyIds and unrelated fields are never
    written by rollback.
    INDEX-DROP WINDOW (round 3 reassessment): the index V20 created is dropped
    only after the preflight passes and before restore writes; a drop failure
    aborts with exit 2 and no document mutated; concurrent writes are still
    guarded by the conditional filter on the assigned slug.
    """
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path} — aborting.")
        return 2
    # Finding 1: the backup is parsed and STRUCTURALLY validated before ANY
    # database access; a malformed backup aborts with zero mutations.
    meta, docs = _load_and_validate_rollback_backup(backup_path)
    if meta is None:
        print("  [WARN] backup has no _meta record: index provenance UNKNOWN — "
              f"an existing {INDEX_NAME} is treated as pre-existing and is "
              "NEVER dropped (finding 1)")
    v20_created = bool(meta and meta.get("index_created_by_v20"))
    print(f"Rolling back {len(docs)} categories from {backup_path}")

    # ============ PREFLIGHT (finding 1) — strictly READ-ONLY ============
    # The COMPLETE rollback plan is built and validated before ANY mutation:
    # (1) every backed-up document's current state and rollback conflict,
    # (2) the index plan from the recorded provenance, (3) index constraints
    # against the ENTIRE planned restored state. Any blocking conflict aborts
    # here: the index is NOT dropped and NO document is modified.
    planned = []           # (doc, cat_id, action); action: RESTORE | MISSING
    preflight_conflicts = []
    for doc in docs:
        cat_id = ObjectId(doc["_id"])
        current = await db.categories.find_one({"_id": cat_id}, {"slug": 1, "legacySlugs": 1})
        if not current:
            planned.append((doc, cat_id, "MISSING"))
            continue
        assigned_slug = doc["assigned_slug"]
        current_slug = current.get("slug")
        current_legacy = current.get("legacySlugs", _ABSENT)
        if current_slug == assigned_slug and _legacy_matches_v20_state(doc, current_legacy):
            planned.append((doc, cat_id, "RESTORE"))
            continue
        if _already_restored(doc, current):
            planned.append((doc, cat_id, "ALREADY"))
            continue
        preflight_conflicts.append((doc, current_slug))
    if preflight_conflicts:
        for doc, current_slug in preflight_conflicts:
            print(f"  [CONFLICT] {doc.get('name')!r} ({doc['_id']}): current slug "
                  f"{current_slug!r} != slug assigned by V20 "
                  f"{doc['assigned_slug']!r} — changed after V20")
        print(f"  FAIL-CLOSED (finding 1): {len(preflight_conflicts)} document "
              "rollback conflict(s) detected in preflight. Aborting BEFORE any "
              "mutation: the index was NOT dropped and NO document was "
              "modified — not even the documents that were still restorable. "
              "Slugs changed after V20 are never overwritten; resolve them "
              "manually if this rollback must proceed.")
        return 2

    # ---- Index plan from the recorded provenance (read-only) ----
    index_info = await db.categories.index_information()
    # V2 backups created before index_actual_name existed fall back to the
    # historical INDEX_NAME. New backups preserve the exact MongoDB name.
    actual_index_name = (
        (meta.get("index_actual_name") if meta else None) or INDEX_NAME
    )
    index_exists = actual_index_name in index_info
    plan_drop_index = False

    if meta and meta.get("index_existed_before_v20") and not index_exists:
        print(
            f"  FAIL-CLOSED: pre-existing index {actual_index_name!r} "
            "recorded in the backup is missing. Refusing to restore documents "
            "without its original unique-index protection; nothing was modified."
        )
        return 2

    if index_exists and v20_created:
        # Finding 3 (reused): drop the index only if it still matches EXACTLY
        # the definition V20 creates — a differently-shaped index under the
        # V20 name is not V20's index and is never dropped automatically.
        problems = describe_index_incompatibilities(
            index_info.get(actual_index_name) or {}
        )
        if problems:
            print(f"  FAIL-CLOSED (finding 1): the index {INDEX_NAME} is "
                  "recorded as created by V20 but no longer matches the "
                  f"definition V20 creates ({'; '.join(problems)}). Refusing "
                  "to drop a foreign index; NO document was modified. "
                  "Inspect and resolve the index manually.")
            return 2
        plan_drop_index = True
    elif index_exists:
        # Pre-existing (or provenance unknown): NEVER drop it. Instead prove
        # the ENTIRE planned restored state cannot violate it, before touching
        # anything (finding 1) — null/empty restores AND duplicate restored
        # slugs, within the plan and against documents outside the backup.
        planned_ids = [ObjectId(d["_id"]) for (d, _cid, _act) in planned]
        null_restores = [
            d for (d, _cid, action) in planned
            if action == "RESTORE"
            and d.get("slug_field_present") and not (d.get("slug") or "")
        ]
        # Documents already in their pre-V20 state that hold an explicit
        # null/empty slug also occupy the unique sparse index.
        already_empty = sum(
            1 for (d, _cid, action) in planned
            if action == "ALREADY"
            and d.get("slug_field_present") and not (d.get("slug") or "")
        )
        other_empty = await db.categories.count_documents(
            {"slug": {"$exists": True, "$in": [None, ""]}, "_id": {"$nin": planned_ids}}
        )
        if len(null_restores) + already_empty + other_empty > 1:
            print(
                f"  FAIL-CLOSED: {INDEX_NAME} existed before V20 and is NOT "
                f"dropped, but this rollback would restore {len(null_restores)} "
                f"explicit null/empty slug(s) while {other_empty} other "
                "document(s) still hold a null/empty slug — a unique sparse "
                "index indexes explicit nulls, so restoring under it would "
                "fail mid-rollback with E11000. Nothing was modified; resolve "
                "the empty slugs manually (or remove the index) and re-run."
            )
            return 2
        restored_values = {}
        for (d, _cid, action) in planned:
            if (action in ("RESTORE", "ALREADY") and d.get("slug_field_present")
                    and isinstance(d.get("slug"), str) and d["slug"]):
                restored_values.setdefault(d["slug"], []).append(str(d["_id"]))
        dupe_problems = []
        for value, owners in sorted(restored_values.items()):
            if len(owners) > 1:
                dupe_problems.append(
                    f"{value!r} would be restored onto {len(owners)} backed-up "
                    f"documents ({', '.join(owners)})"
                )
            else:
                others = await db.categories.count_documents(
                    {"slug": value, "_id": {"$nin": planned_ids}}
                )
                if others:
                    dupe_problems.append(
                        f"{value!r} is already held by {others} document(s) "
                        "outside this backup"
                    )
        if dupe_problems:
            print(f"  FAIL-CLOSED (finding 1): {INDEX_NAME} existed before V20 "
                  "and the planned restored state would violate its unique "
                  "slug constraint: " + "; ".join(dupe_problems) + ". Nothing "
                  "was modified; resolve the conflicting slugs manually and "
                  "re-run.")
            return 2
        print(f"  [INDEX] {INDEX_NAME} existed before V20 — preserved untouched; "
              "the ENTIRE planned restored state was validated against it in "
              "preflight (finding 1)")

    # ============ EXECUTE (mutations begin ONLY here) ============
    _mark_mutation_started()
    if plan_drop_index:
        # V20 created this index; the true pre-V20 state had none. Drop it
        # BEFORE restoring original null/missing slugs — a unique sparse
        # index indexes explicit nulls, so several slug=null restores would
        # otherwise fail mid-rollback with E11000. Rollback never recreates
        # it (pre-V20 there was none). This drop happens only AFTER the
        # preflight above validated every document state and conflict
        # (finding 1: no mutation precedes a validated plan).
        try:
            await db.categories.drop_index(actual_index_name)
        except Exception as exc:
            print(f"  FAIL-CLOSED: the index {INDEX_NAME} was created by V20 but "
                  f"could not be dropped ({exc}). No document was modified; "
                  "drop it manually and re-run the rollback.")
            return 2
        print(f"  [INDEX] dropped {actual_index_name} (created by V20; the pre-V20 "
              "state had no index)")

    restored = 0
    already = 0
    conflicts = 0
    for doc, cat_id, action in planned:
        if action == "MISSING":
            # A deleted category cannot be restored: it is NOT restored, so the
            # rollback is reported as incomplete (never claimed as full).
            print(f"  [MISS] {doc['_id']} not found — NOT restored (deleted "
                  "after V20; never resurrected)")
            conflicts += 1
            continue
        if action == "ALREADY":
            # Rerun safety: a previous rollback run already restored this
            # document; nothing is written.
            already += 1
            print(f"  [ALREADY] {doc.get('name')!r} already in its pre-V20 state — no write")
            continue
        assigned_slug = doc["assigned_slug"]
        had_field = bool(doc.get("slug_field_present"))
        prev_slug = doc.get("slug") if had_field else None
        if had_field:
            # Exact original state: field present with its original value
            # (which may legitimately be null).
            update = {"$set": {"slug": prev_slug}}
            label = f"slug -> {prev_slug!r} (field kept)"
        else:
            # Exact original state: the slug field did not exist.
            update = {"$unset": {"slug": ""}}
            label = "slug -> <field removed>"
        if doc.get("legacySlugs_field_present"):
            # Exact original state: restore the recorded array verbatim.
            update.setdefault("$set", {})["legacySlugs"] = list(doc.get("legacySlugs") or [])
        else:
            # Exact original state: the legacySlugs field did not exist.
            update.setdefault("$unset", {})["legacySlugs"] = ""
        # Correction 2: conditional AT THE MOMENT OF THE WRITE — the filter
        # matches only while the slug is still the one V20 assigned AND
        # legacySlugs is still the state V20 left (the recorded state, or
        # absent). A change landing after the preflight matches nothing
        # (matched_count == 0): the concurrent value is never overwritten.
        if doc.get("legacySlugs_field_present"):
            legacy_filter = {"legacySlugs": doc.get("legacySlugs")}
        else:
            legacy_filter = {"legacySlugs": {"$exists": False}}
        try:
            res = await db.categories.update_one(
                {"_id": cat_id, "slug": assigned_slug, **legacy_filter}, update
            )
        except DuplicateKeyError:
            print(f"  [CONFLICT] {doc.get('name')!r} ({doc['_id']}): restore "
                  "would violate the unique slug index (another document "
                  "already holds the original slug) — skipped untouched")
            conflicts += 1
            continue
        except PyMongoError as exc:
            # Partial-rollback reporting: a failed write leaves this document
            # unrestored (never overwritten) and the run reports exit 3.
            print(f"  [CONFLICT] {doc.get('name')!r} ({doc['_id']}): restore write "
                  f"failed ({exc}) — not restored, nothing overwritten")
            conflicts += 1
            continue
        if res.matched_count != 1:
            current_again = await db.categories.find_one(
                {"_id": cat_id}, {"slug": 1}
            )
            print(f"  [CONFLICT] {doc.get('name')!r} ({doc['_id']}): slug changed "
                  f"to {(current_again or {}).get('slug')!r} between verification "
                  "and the rollback write — nothing overwritten (correction 2)")
            conflicts += 1
            continue
        restored += 1
        if res.modified_count != 1:
            print(f"  [NOTE] {doc.get('name')!r}: already in the exact pre-V20 "
                  "state (no-op write)")
        print(f"  [RESTORED] {doc.get('name')!r} {label}")
    print(f"Rollback pass: {restored} restored, {already} already in pre-V20 "
          f"state, {conflicts} not restored (conflict or deleted); "
          "legacySlugs/legacyIds preserved.")
    if conflicts:
        print(f"INCOMPLETE: {conflicts} document(s) NOT restored; exit 3. "
              "Rerunning rollback with the same backup is safe: restored "
              "documents are skipped.")
        return EXIT_INCOMPLETE
    return EXIT_OK


# The collection is verified in full: its size is NOT compared against a fixed
# number. The nine EXPECTED_SLUGS are mandatory public slugs; any other category
# is accepted when its slug is valid and unique.


def evaluate_post_migration(rows, index_info) -> dict:
    """Post-migration verification logic. Pure: no database access.

    rows: category documents with _id, name and the stored slug field
    (None when missing). index_info: index_information() of the categories
    collection, or None. Every check is evaluated and reported; data problems
    are returned as failures, never raised. report['passed'] is True only when
    every check holds.
    """
    failures = []
    mapping = []
    rows = list(rows)
    slug_owners = {}
    invalid_count = 0
    for row in rows:
        cid = str(row.get("_id"))
        name = row.get("name")
        slug = row.get("slug")
        mapping.append({"_id": cid, "name": name, "slug": slug})
        if not isinstance(slug, str) or slug.strip() == "":
            invalid_count += 1
            failures.append(f"{cid} ({name!r}): slug missing, null or blank ({slug!r})")
            continue
        if not SLUG_FORMAT_RE.fullmatch(slug) or is_objectid_like(slug):
            invalid_count += 1
            failures.append(
                f"{cid} ({name!r}): slug {slug!r} is not a valid URL slug "
                "(lowercase a-z/0-9 words joined by single hyphens, not ObjectId-like)"
            )
            continue
        slug_owners.setdefault(slug, []).append(cid)
    duplicate_slugs = []
    for slug, owners in sorted(slug_owners.items()):
        if len(owners) > 1:
            duplicate_slugs.append(slug)
            failures.append(f"slug {slug!r} is not unique (held by {', '.join(owners)})")
    found = set(slug_owners)
    expected_found = sorted(EXPECTED_SLUGS & found)
    expected_missing = sorted(EXPECTED_SLUGS - found)
    # Additional valid unique slugs are accepted; they are reported, not failed.
    unexpected = sorted(found - EXPECTED_SLUGS)
    for slug in expected_missing:
        failures.append(f"required public category slug {slug!r} is not held by any category")
    valid_count = len(rows) - invalid_count
    actual_name, actual_info, index_problems = find_slug_index(index_info)
    if actual_name is None and not index_problems:
        failures.append(
            f"unique sparse slug index is missing (expected {INDEX_NAME!r} "
            "or another index on the slug key)"
        )
        index_status = "missing"
    elif index_problems:
        for problem in index_problems:
            failures.append(f"slug index: {problem}")
        index_status = "incompatible"
    else:
        index_status = "compatible"
    return {
        "passed": not failures,
        "failures": failures,
        "count": len(rows),
        "valid_count": valid_count,
        "unique_count": len(found),
        "duplicate_count": len(duplicate_slugs),
        "invalid_count": invalid_count,
        "mapping": mapping,
        "expected_found": expected_found,
        "expected_missing": expected_missing,
        "unexpected": unexpected,
        "index_status": index_status,
    }


async def verify_post_migration(db) -> dict:
    """Read-only: load every category and the index definition, then evaluate."""
    rows = [
        doc async for doc in
        db.categories.find({}, {"_id": 1, "name": 1, "slug": 1}).sort("_id", 1)
    ]
    index_info = await db.categories.index_information()
    return evaluate_post_migration(rows, index_info)


def report_post_migration(report) -> None:
    print("\nPOST-MIGRATION VERIFICATION (read-only, no writes)")
    print(f"  total categories checked: {report['count']}")
    print(f"  categories with valid slugs: {report['valid_count']}")
    print(f"  unique slug count: {report['unique_count']}")
    print(f"  required public slugs found: "
          f"{len(report['expected_found'])}/{len(EXPECTED_SLUGS)}")
    print(f"  additional valid category slugs: {len(report['unexpected'])}")
    print(f"  duplicate slug count: {report['duplicate_count']}")
    print(f"  missing or invalid slug count: {report['invalid_count']}")
    print(f"  unique sparse index {INDEX_NAME!r}: {report['index_status']}")
    print("  slug mapping report:")
    for item in sorted(report["mapping"], key=lambda m: str(m["name"])):
        print(f"    {item['name']!r} -> {item['slug']!r}  (_id={item['_id']})")
    for failure in report["failures"]:
        print(f"  [FAIL] {failure}")
    print("RESULT: PASS" if report["passed"] else "RESULT: FAIL")


async def run_verify() -> int:
    try:
        host, port, db_name = resolve_target()
    except TargetRefused as exc:
        print(f"TARGET REFUSED (exit 2): {exc}")
        return EXIT_BLOCKED
    client = AsyncIOMotorClient(os.environ["MONGO_URL"].strip())
    try:
        report = await verify_post_migration(client[db_name])
    finally:
        client.close()
    report_post_migration(report)
    return EXIT_OK if report["passed"] else EXIT_BLOCKED


def _parse_args(argv):
    """Round 3 (P1): strict CLI parsing. Returns (mode, rollback_path, confirm)
    or raises TargetRefused on any conflicting or unknown argument.
    mode is one of: dry-run, apply, rollback, verify."""
    known = {"--apply", "--verify", "--rollback", "--backup", "--confirm-apply", "--confirm-rollback"}
    i = 1
    flags = set()
    values = {}
    while i < len(argv):
        tok = argv[i]
        if tok not in known:
            raise TargetRefused(f"unknown argument {tok!r}")
        if tok in ("--backup", "--confirm-apply", "--confirm-rollback"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                raise TargetRefused(f"{tok} requires a value")
            if tok in values:
                raise TargetRefused(f"{tok} given more than once")
            values[tok] = argv[i + 1]
            i += 2
            continue
        if tok in flags:
            raise TargetRefused(f"{tok} given more than once")
        flags.add(tok)
        i += 1
    apply = "--apply" in flags
    verify = "--verify" in flags
    rollback = "--rollback" in flags
    if apply and rollback:
        raise TargetRefused("--apply and --rollback cannot be combined")
    if verify and (apply or rollback):
        raise TargetRefused("--verify is read-only and cannot be combined with --apply or --rollback")
    if rollback and "--backup" not in values:
        raise TargetRefused("--rollback requires --backup <path>")
    if "--backup" in values and not rollback:
        raise TargetRefused("--backup is only valid with --rollback")
    if "--confirm-apply" in values and not apply:
        raise TargetRefused("--confirm-apply is only valid with --apply")
    if "--confirm-rollback" in values and not rollback:
        raise TargetRefused("--confirm-rollback is only valid with --rollback")
    if apply and "--confirm-apply" not in values:
        raise TargetRefused("--apply requires --confirm-apply <exact DB_NAME>")
    if rollback and "--confirm-rollback" not in values:
        raise TargetRefused("--rollback requires --confirm-rollback <exact DB_NAME>")
    if verify:
        return "verify", None, None
    if rollback:
        return "rollback", values["--backup"], values["--confirm-rollback"]
    if apply:
        return "apply", None, values["--confirm-apply"]
    return "dry-run", None, None


def main():
    try:
        mode, rollback_path, confirm = _parse_args(sys.argv)
    except TargetRefused as exc:
        print(f"ARGUMENTS REFUSED (exit 2): {exc}")
        return EXIT_BLOCKED
    if mode == "verify":
        try:
            return asyncio.run(run_verify())
        except MigrationBlocked as exc:
            print(f"\nMIGRATION V20 VERIFY BLOCKED (exit 2): {exc}")
            return EXIT_BLOCKED
        except Exception as exc:
            print(f"\nMIGRATION V20 VERIFY INCOMPLETE (exit 3): {type(exc).__name__}: {exc}")
            return EXIT_INCOMPLETE
    try:
        return asyncio.run(run_migration(
            apply=(mode == "apply"), rollback_path=rollback_path, confirm_db=confirm))
    except MigrationBlocked as exc:
        # F1/F2: fail-closed. The report above (or in the message) states what
        # was and was not changed; success is never claimed.
        print(f"\nMIGRATION V20 BLOCKED (exit 2): {exc}")
        return EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
