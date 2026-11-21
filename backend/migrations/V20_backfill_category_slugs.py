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
- ROLLBACK RESTORES EXACT STATE: the backup records, per category, the
  pre-migration `slug` value AND whether the field existed
  (slug_field_present). Rollback $sets the original value back (null stays
  null) or $unsets the field when it was absent — it never injects a null
  where the field did not exist. Rollback NEVER removes pre-existing
  legacySlugs / legacyIds data and never uses a blanket $unset. Run:
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
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

load_dotenv()

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
INDEX_NAME = "idx_categories_slug_unique"

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
    info = indexes.get(INDEX_NAME)
    if info:
        problems = describe_index_incompatibilities(info)
        if problems:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 3): existing index {INDEX_NAME!r} is "
                "incompatible with the V20 contract (expected exactly "
                "key=[('slug', 1)], unique=True, sparse=True, no semantic "
                "extras). Detected: " + "; ".join(problems) + ". No data was "
                "written; the index was NOT dropped or replaced automatically "
                "— inspect and resolve it manually before running V20."
            )
        key = [tuple(kv) for kv in (info.get("key") or [])]
        return {"exists": True, "key": key,
                "unique": bool(info.get("unique")),
                "sparse": bool(info.get("sparse")),
                "action": "verified"}
    if create:
        await db.categories.create_index(
            [("slug", 1)], unique=True, sparse=True, name=INDEX_NAME
        )
        return {"exists": False, "action": "created (apply mode)"}
    return {"exists": False, "action": "missing (dry-run: --apply would create it)"}


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
    async for cat in db.categories.find({}, {"_id": 1, "name": 1, "slug": 1}).sort("_id", 1):
        name = cat.get("name", "")
        existing = cat.get("slug")
        # F2: every existing value is validated, not just truthy ones. Invalid
        # values are collected and reported; the migration then fails closed.
        state = validate_existing_slug(existing) if "slug" in cat else "BACKFILL"
        if state == "BACKFILL":
            pass
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
        backup_records.append({
            "_id": str(cat["_id"]),
            "name": name,
            "slug": existing,
            "slug_field_present": "slug" in cat,
            # Blocker 4: rollback proves the current slug is still the one V20
            # assigned before it restores anything.
            "assigned_slug": new_slug,
        })
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
            "kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
            "index_name": INDEX_NAME,
            "index_existed_before_v20": bool(index_status.get("exists")),
            "index_created_by_v20": not bool(index_status.get("exists")),
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        }
    }
    payload = [meta] + list(backup_records)
    backup_path, fd = _open_backup_file_exclusively()
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(backup_path, encoding="utf-8") as f:
        validated = json.load(f)
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
    remaining = await db.categories.count_documents({"slug": {"$in": [None, ""]}})
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


async def run_migration(apply: bool, rollback_path: str = None) -> int:
    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME", "midconnect").strip()
    if not mongo_url:
        print("MONGO_URL not set — aborting (no DB touched).")
        return 2
    client = AsyncIOMotorClient(mongo_url.strip())
    db = client[db_name]

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
        print("Dry-run note: --apply would fail closed on these duplicates "
              "(correction 6); nothing was written.")

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
            {"slug": {"$in": [None, ""]}}
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
    stats = await apply_slug_writes(db, plan)
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
            {"slug": {"$in": [None, ""]}}
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
        created = await create_slug_index_guarded(
            db, backup_path, backfilled=stats["updated"],
            conflicts=len(stats["conflicts"]),
        )
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
        if _id in seen_ids:
            raise MigrationBlocked(
                f"FAIL-CLOSED (finding 1): duplicate backup record for _id "
                f"{_id}. Nothing was mutated."
            )
        seen_ids.add(_id)
        docs.append(rec)
    if meta is not None:
        if meta.get("kind") != "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2":
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta.kind "
                f"{meta.get('kind')!r} is not this migration's backup format "
                "('V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2'). Nothing was mutated."
            )
        if meta.get("index_name") != INDEX_NAME:
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta.index_name "
                f"{meta.get('index_name')!r} does not belong to "
                f"{INDEX_NAME!r}. Nothing was mutated."
            )
        created = meta.get("index_created_by_v20")
        existed = meta.get("index_existed_before_v20")
        if not isinstance(created, bool) or not isinstance(existed, bool):
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta index provenance flags "
                "must both be booleans. Nothing was mutated."
            )
        if created and existed:
            raise MigrationBlocked(
                "FAIL-CLOSED (finding 1): backup _meta claims the index both "
                "existed before V20 and was created by V20 — inconsistent "
                "provenance. Nothing was mutated."
            )
    return meta, docs


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
    The slug the migration assigned is preserved in legacySlugs (data is
    never destroyed, owner revision 3); pre-existing legacySlugs/legacyIds
    entries are never removed.
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
        current = await db.categories.find_one({"_id": cat_id}, {"slug": 1})
        if not current:
            planned.append((doc, cat_id, "MISSING"))
            continue
        assigned_slug = doc["assigned_slug"]
        current_slug = current.get("slug")
        if current_slug != assigned_slug:
            preflight_conflicts.append((doc, current_slug))
            continue
        planned.append((doc, cat_id, "RESTORE"))
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
    index_exists = INDEX_NAME in index_info
    plan_drop_index = False
    if index_exists and v20_created:
        # Finding 3 (reused): drop the index only if it still matches EXACTLY
        # the definition V20 creates — a differently-shaped index under the
        # V20 name is not V20's index and is never dropped automatically.
        problems = describe_index_incompatibilities(index_info.get(INDEX_NAME) or {})
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
        other_empty = await db.categories.count_documents(
            {"slug": {"$in": [None, ""]}, "_id": {"$nin": planned_ids}}
        )
        if len(null_restores) + other_empty > 1:
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
            if (action == "RESTORE" and d.get("slug_field_present")
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
    if plan_drop_index:
        # V20 created this index; the true pre-V20 state had none. Drop it
        # BEFORE restoring original null/missing slugs — a unique sparse
        # index indexes explicit nulls, so several slug=null restores would
        # otherwise fail mid-rollback with E11000. Rollback never recreates
        # it (pre-V20 there was none). This drop happens only AFTER the
        # preflight above validated every document state and conflict
        # (finding 1: no mutation precedes a validated plan).
        try:
            await db.categories.drop_index(INDEX_NAME)
        except Exception as exc:
            print(f"  FAIL-CLOSED: the index {INDEX_NAME} was created by V20 but "
                  f"could not be dropped ({exc}). No document was modified; "
                  "drop it manually and re-run the rollback.")
            return 2
        print(f"  [INDEX] dropped {INDEX_NAME} (created by V20; the pre-V20 "
              "state had no index)")

    restored = 0
    conflicts = 0
    for doc, cat_id, action in planned:
        if action == "MISSING":
            print(f"  [MISS] {doc['_id']} not found — skipped (a concurrent "
                  "deletion is never resurrected)")
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
        if assigned_slug and assigned_slug != prev_slug:
            # Keep the assigned slug addressable (never destroy data).
            update["$addToSet"] = {"legacySlugs": assigned_slug}
        # Correction 2: conditional AT THE MOMENT OF THE WRITE — the filter
        # only matches the document while its slug is still exactly the one
        # V20 assigned. A slug changed between the read above and this write
        # matches nothing (matched_count == 0): the concurrent value is never
        # overwritten and the conflict is reported.
        try:
            res = await db.categories.update_one(
                {"_id": cat_id, "slug": assigned_slug}, update
            )
        except DuplicateKeyError:
            print(f"  [CONFLICT] {doc.get('name')!r} ({doc['_id']}): restore "
                  "would violate the unique slug index (another document "
                  "already holds the original slug) — skipped untouched")
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
    print(f"Rollback complete: {restored} restored, {conflicts} conflict(s) skipped "
          "safely; legacySlugs/legacyIds preserved.")
    if conflicts:
        print(f"INCOMPLETE: {conflicts} document(s) NOT restored; exit 3.")
        return EXIT_INCOMPLETE
    return EXIT_OK


POST_VERIFY_EXPECTED_COUNT = len(EXPECTED_SLUGS)  # 9 categories expected


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
    if len(rows) != POST_VERIFY_EXPECTED_COUNT:
        failures.append(
            f"category count is {len(rows)}; expected {POST_VERIFY_EXPECTED_COUNT}"
        )
    slug_owners = {}
    for row in rows:
        cid = str(row.get("_id"))
        name = row.get("name")
        slug = row.get("slug")
        mapping.append({"_id": cid, "name": name, "slug": slug})
        if not isinstance(slug, str) or slug.strip() == "":
            failures.append(f"{cid} ({name!r}): slug missing, null or blank ({slug!r})")
            continue
        if not SLUG_FORMAT_RE.fullmatch(slug) or is_objectid_like(slug):
            failures.append(
                f"{cid} ({name!r}): slug {slug!r} is not a valid URL slug "
                "(lowercase a-z/0-9 words joined by single hyphens, not ObjectId-like)"
            )
            continue
        slug_owners.setdefault(slug, []).append(cid)
    for slug, owners in sorted(slug_owners.items()):
        if len(owners) > 1:
            failures.append(f"slug {slug!r} is not unique (held by {', '.join(owners)})")
    found = set(slug_owners)
    expected_found = sorted(EXPECTED_SLUGS & found)
    expected_missing = sorted(EXPECTED_SLUGS - found)
    unexpected = sorted(found - EXPECTED_SLUGS)
    for slug in expected_missing:
        failures.append(f"expected category slug {slug!r} is not held by any category")
    for slug in unexpected:
        failures.append(f"slug {slug!r} is not one of the {POST_VERIFY_EXPECTED_COUNT} expected categories")
    if not index_info or INDEX_NAME not in index_info:
        failures.append(f"unique sparse index {INDEX_NAME!r} is missing")
        index_status = "missing"
    else:
        problems = describe_index_incompatibilities(index_info[INDEX_NAME])
        for problem in problems:
            failures.append(f"index {INDEX_NAME!r}: {problem}")
        index_status = "compatible" if not problems else "incompatible"
    return {
        "passed": not failures,
        "failures": failures,
        "count": len(rows),
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
    print(f"  categories: {report['count']} (expected {POST_VERIFY_EXPECTED_COUNT})")
    print(f"  unique sparse index {INDEX_NAME!r}: {report['index_status']}")
    print(f"  expected categories accounted for: "
          f"{len(report['expected_found'])}/{POST_VERIFY_EXPECTED_COUNT}")
    print("  slug mapping report:")
    for item in sorted(report["mapping"], key=lambda m: str(m["name"])):
        print(f"    {item['name']!r} -> {item['slug']!r}  (_id={item['_id']})")
    for failure in report["failures"]:
        print(f"  [FAIL] {failure}")
    print("RESULT: PASS" if report["passed"] else "RESULT: FAIL")


async def run_verify() -> int:
    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME", "midconnect").strip()
    if not mongo_url:
        print("MONGO_URL not set — aborting (no DB touched).")
        return 2
    client = AsyncIOMotorClient(mongo_url.strip())
    try:
        report = await verify_post_migration(client[db_name])
    finally:
        client.close()
    report_post_migration(report)
    return 0 if report["passed"] else 2


def main():
    apply = "--apply" in sys.argv
    verify = "--verify" in sys.argv
    rollback_path = None
    if "--rollback" in sys.argv:
        idx = sys.argv.index("--backup") if "--backup" in sys.argv else -1
        rollback_path = sys.argv[idx + 1] if idx != -1 and idx + 1 < len(sys.argv) else None
        if not rollback_path:
            print("--rollback requires --backup <path>")
            return 2
    if verify:
        if apply or rollback_path:
            print("--verify is read-only and cannot be combined with --apply or --rollback")
            return 2
        try:
            return asyncio.run(run_verify())
        except MigrationBlocked as exc:
            print(f"\nMIGRATION V20 VERIFY BLOCKED (exit 2): {exc}")
            return 2
    try:
        return asyncio.run(run_migration(apply=apply, rollback_path=rollback_path))
    except MigrationBlocked as exc:
        # F1/F2: fail-closed. The report above (or in the message) states what
        # was and was not changed; success is never claimed.
        print(f"\nMIGRATION V20 BLOCKED (exit 2): {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
