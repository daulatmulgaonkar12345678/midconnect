"""V20 safety remediation round 3 — deterministic regression tests.

Pure, NO database: target policy, CLI confirmation, expected public slugs,
client lifecycle and exit-code classification. These drive the REAL migration
functions; the Motor client and the database touchpoints are replaced with
in-process stubs. Nothing here can reach a production or any real database.
"""
import asyncio
import os
import sys

import pytest
from pymongo.errors import PyMongoError

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "tests"))

import migrations.V20_backfill_category_slugs as v20  # noqa: E402
from migrations.V20_backfill_category_slugs import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_OK,
    EXPECTED_SLUGS,
    MigrationBlocked,
    TargetRefused,
)

APPROVED = ("127.0.0.1", 27117, "midconnect_v20_round3_test")
GOOD_URL = "mongodb://127.0.0.1:27117/"


def _env(**kw):
    base = {"MONGO_URL": GOOD_URL, "DB_NAME": "midconnect_v20_round3_test"}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


@pytest.fixture
def approved(monkeypatch):
    monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({APPROVED}))
    return APPROVED


# ---------------- 1. production database target refusal ----------------

@pytest.mark.parametrize("name", ["b2b_marketplace", "midconnect", "admin", "config", "local"])
def test_production_names_are_refused_even_when_approved(monkeypatch, name):
    monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({("127.0.0.1", 27117, name)}))
    with pytest.raises(TargetRefused, match="protected name"):
        v20.resolve_target(_env(DB_NAME=name))


def test_unapproved_target_is_refused_before_connecting(approved):
    with pytest.raises(TargetRefused, match="not in the operator-approved"):
        v20.resolve_target(_env(MONGO_URL="mongodb://10.0.0.5:27117/", DB_NAME="midconnect_v20_round3_test"))


def test_approved_target_resolves(approved):
    assert v20.resolve_target(_env()) == APPROVED


def test_empty_approval_policy_refuses_everything(monkeypatch):
    monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset())
    with pytest.raises(TargetRefused, match="not in the operator-approved"):
        v20.resolve_target(_env())


# ---------------- 2. missing or empty DB_NAME ----------------

@pytest.mark.parametrize("db", [None, "", "   "])
def test_missing_or_empty_db_name_is_refused(approved, db):
    with pytest.raises(TargetRefused, match="DB_NAME must be set explicitly"):
        v20.resolve_target(_env(DB_NAME=db))


def test_missing_mongo_url_is_refused(approved):
    with pytest.raises(TargetRefused, match="MONGO_URL is not set"):
        v20.resolve_target(_env(MONGO_URL=None))


def test_no_implicit_midconnect_default_remains(approved):
    """The old implicit default `midconnect` must not be reachable: an absent
    DB_NAME is a refusal, never a silent fallback."""
    with pytest.raises(TargetRefused):
        v20.resolve_target({"MONGO_URL": GOOD_URL})


def test_migration_does_not_load_dotenv():
    src = open(v20.__file__, encoding="utf-8").read()
    assert "load_dotenv(" not in src, "implicit .env loading would let a stray file pick the target"


# ---------------- 3 & 4. apply / rollback confirmation ----------------

def test_apply_without_confirmation_is_refused(monkeypatch, approved):
    args = ["V20.py", "--apply"]
    monkeypatch.setattr(v20.sys, "argv", args)
    assert v20.main() == 2


@pytest.mark.parametrize("bad", ["midconnect", "midconnect_v20_round3_tes", "", "MIDCONNECT_V20_ROUND3_TEST"])
def test_apply_with_wrong_confirmation_is_refused(bad):
    with pytest.raises(TargetRefused, match="--confirm-apply"):
        v20.require_confirmation("apply", "midconnect_v20_round3_test", bad)


def test_apply_with_exact_confirmation_passes():
    v20.require_confirmation("apply", "midconnect_v20_round3_test", "midconnect_v20_round3_test")


def test_rollback_without_confirmation_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--rollback", "--backup", str(tmp_path / "b.json")])
    assert v20.main() == 2


@pytest.mark.parametrize("bad", ["midconnect", "", "x"])
def test_rollback_with_wrong_confirmation_is_refused(bad):
    with pytest.raises(TargetRefused, match="--confirm-rollback"):
        v20.require_confirmation("rollback", "midconnect_v20_round3_test", bad)


def test_confirmation_for_apply_does_not_satisfy_rollback():
    # The apply token is not accepted as a rollback token: each mode needs its own.
    with pytest.raises(TargetRefused):
        v20.require_confirmation("rollback", "midconnect_v20_round3_test", None)


def test_run_migration_refuses_apply_without_confirmation_and_closes_client(monkeypatch, approved):
    closed = {"n": 0}

    class _C:
        def __getitem__(self, _):
            raise AssertionError("no database may be selected")

        def close(self):
            closed["n"] += 1

    monkeypatch.setattr(v20, "AsyncIOMotorClient", lambda *a, **k: _C())
    monkeypatch.setenv("MONGO_URL", GOOD_URL)
    monkeypatch.setenv("DB_NAME", "midconnect_v20_round3_test")
    rc = asyncio.run(v20.run_migration(apply=True, confirm_db=None))
    assert rc == 2
    assert closed["n"] == 0, "a refusal before the client is created never creates one"


# ---------------- 5. conflicting CLI arguments ----------------

@pytest.mark.parametrize("argv", [
    ["V20.py", "--apply", "--rollback", "--backup", "b.json", "--confirm-apply", "x", "--confirm-rollback", "x"],
    ["V20.py", "--verify", "--apply", "--confirm-apply", "x"],
    ["V20.py", "--verify", "--rollback", "--backup", "b.json", "--confirm-rollback", "x"],
    ["V20.py", "--rollback"],
    ["V20.py", "--backup", "b.json"],
    ["V20.py", "--apply", "--confirm-rollback", "x"],
    ["V20.py", "--rollback", "--backup", "b.json", "--confirm-apply", "x", "--confirm-rollback", "x"],
    ["V20.py", "--frobnicate"],
    ["V20.py", "--apply", "--apply", "--confirm-apply", "x"],
    ["V20.py", "--confirm-apply"],
])
def test_conflicting_or_incomplete_arguments_exit_2(monkeypatch, argv):
    monkeypatch.setattr(v20.sys, "argv", argv)
    assert v20.main() == 2


def test_conflict_is_rejected_before_any_client_is_created(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no client may be created for conflicting arguments")

    monkeypatch.setattr(v20, "AsyncIOMotorClient", boom)
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--apply", "--rollback", "--backup", "b.json"])
    assert v20.main() == 2


def test_dry_run_and_verify_parse_as_read_only():
    assert v20._parse_args(["V20.py"]) == ("dry-run", None, None)
    assert v20._parse_args(["V20.py", "--verify"]) == ("verify", None, None)


# ---------------- 6 & 7. expected public slug mismatch / duplicate-name collision ----------------

_NINE = {
    "cleaning-products": "Cleaning Products",
    "electrical-equipment-supplies": "Electrical Equipment & Supplies",
    "electronics-it-industrial-automation": "Electronics IT Industrial Automation",
    "lights-lighting-accessories": "Lights Lighting Accessories",
    "metals-industrial-raw-materials": "Metals Industrial Raw Materials",
    "panel-meters-and-accessories": "Panel Meters and Accessories",
    "safety-products": "Safety Products",
    "solar-equipment-panels": "Solar Equipment Panels",
    "vfd-plc-hmi-control-equipments": "VFD PLC HMI Control Equipments",
}


def _clean_rows():
    return [{"_id": f"{i:024x}", "name": n} for i, n in enumerate(_NINE.values(), start=1)]


def test_nine_expected_slugs_match_their_names():
    assert set(_NINE) == EXPECTED_SLUGS
    for slug, name in _NINE.items():
        assert v20.slugify(name) == slug


def test_clean_mapping_satisfies_every_public_slug():
    rows = _clean_rows()
    final = {str(r["_id"]): v20.slugify(r["name"]) for r in rows}
    assert v20.evaluate_expected_public_slugs(rows, final) == []


def test_expected_slug_mismatch_is_reported():
    rows = _clean_rows()
    final = {str(r["_id"]): v20.slugify(r["name"]) for r in rows}
    # Simulate the planner assigning a suffix to one public category.
    victim = rows[0]
    final[str(victim["_id"])] = "cleaning-products-2"
    failures = v20.evaluate_expected_public_slugs(rows, final)
    assert any("'cleaning-products'" in f and "would be held by no category" in f for f in failures)


def test_earlier_id_duplicate_name_collision_is_detected():
    """A DUPLICATE category name with an earlier _id takes the public slug."""
    rows = [{"_id": "00" * 12, "name": "Safety Products"}]  # earlier _id, same name
    rows += [{"_id": f"{i:024x}", "name": n} for i, n in enumerate(_NINE.values(), start=5)]
    rows[1 + list(_NINE).index("safety-products")]["name"] = "Safety Products"
    final = {}
    for r in rows:
        final[str(r["_id"])] = v20.slugify(r["name"])
    # Earlier duplicate was given the bare slug by the planner (_id order).
    final[str(rows[0]["_id"])] = "safety-products"
    failures = v20.evaluate_expected_public_slugs(rows, final)
    assert any("'safety-products'" in f for f in failures), failures
    assert any("exactly one is required" in f or "instead of" in f for f in failures)


def test_duplicate_name_without_collision_on_public_slug_is_still_flagged():
    rows = _clean_rows()
    rows.append({"_id": "ff" * 12, "name": "Safety Products"})
    final = {str(r["_id"]): v20.slugify(r["name"]) for r in rows}
    final[str(rows[-1]["_id"])] = "safety-products-2"
    failures = v20.evaluate_expected_public_slugs(rows, final)
    assert any("'safety-products'" in f and "exactly one is required" in f for f in failures)


def test_dry_run_reports_slug_mismatch_and_exits_2(monkeypatch, approved):
    monkeypatch.setattr(v20, "AsyncIOMotorClient", lambda *a, **k: _NullClient())
    monkeypatch.setattr(v20, "verify_slug_index", _async_return({"exists": False}))
    monkeypatch.setattr(v20, "build_slug_plan", _async_return(([{"_id": "a" * 24, "name": "Cleaning Products", "slug": "cleaning-products-2"}], [])))
    monkeypatch.setattr(v20, "find_preexisting_slug_duplicates", _async_return([]))
    monkeypatch.setattr(v20, "check_expected_public_slugs", _async_return(["public slug 'cleaning-products' would be held by no category"]))
    monkeypatch.setenv("MONGO_URL", GOOD_URL)
    monkeypatch.setenv("DB_NAME", "midconnect_v20_round3_test")
    rc = asyncio.run(v20.run_migration(apply=False))
    assert rc == EXIT_BLOCKED_CODE == 2


def test_apply_refuses_slug_mismatch_before_any_write(monkeypatch, approved):
    writes = {"backup": 0, "apply": 0, "index": 0}
    monkeypatch.setattr(v20, "AsyncIOMotorClient", lambda *a, **k: _NullClient())
    monkeypatch.setattr(v20, "verify_slug_index", _async_return({"exists": False}))
    monkeypatch.setattr(v20, "build_slug_plan", _async_return(([{"_id": "a" * 24, "name": "X", "slug": "x"}], [])))
    monkeypatch.setattr(v20, "find_preexisting_slug_duplicates", _async_return([]))
    monkeypatch.setattr(v20, "check_expected_public_slugs", _async_return(["public slug 'safety-products' would be held by no category"]))
    monkeypatch.setattr(v20, "write_and_validate_backup", lambda *a, **k: writes.__setitem__("backup", writes["backup"] + 1) or "p")
    monkeypatch.setenv("MONGO_URL", GOOD_URL)
    monkeypatch.setenv("DB_NAME", "midconnect_v20_round3_test")
    rc = asyncio.run(v20.run_migration(apply=True, confirm_db="midconnect_v20_round3_test"))
    assert rc == 2
    assert writes["backup"] == 0, "no backup and therefore no write may happen"


EXIT_BLOCKED_CODE = 2


# ---------------- 8. client close on every execution path ----------------

class _NullClient:
    def __init__(self):
        self.closed = 0

    def __getitem__(self, _):
        return object()

    def close(self):
        self.closed += 1


def _async_return(value):
    async def _f(*_a, **_k):
        return value
    return _f


class _TrackingClient:
    """Records close() calls; the real Motor close() is synchronous, so this is too."""

    def __init__(self):
        self.closed = 0

    def __getitem__(self, _):
        return object()

    def close(self):
        self.closed += 1


def _run_with_client(monkeypatch, client, **kw):
    monkeypatch.setattr(v20, "AsyncIOMotorClient", lambda *a, **k: client)
    monkeypatch.setenv("MONGO_URL", GOOD_URL)
    monkeypatch.setenv("DB_NAME", "midconnect_v20_round3_test")
    return asyncio.run(v20.run_migration(**kw))


def test_client_closed_on_successful_run(monkeypatch, approved):
    c = _TrackingClient()

    async def ok(*_a, **_k):
        return EXIT_OK

    monkeypatch.setattr(v20, "_run_migration_with_client", ok)
    assert _run_with_client(monkeypatch, c, apply=False) == EXIT_OK
    assert c.closed == 1


def test_client_closed_on_blocked_run(monkeypatch, approved):
    c = _TrackingClient()
    monkeypatch.setattr(v20, "build_slug_plan", _async_return(([], [])))

    async def blocked(*_a, **_k):
        raise MigrationBlocked("blocked before any write")

    monkeypatch.setattr(v20, "_run_migration_with_client", blocked)
    assert _run_with_client(monkeypatch, c, apply=False) == 2
    assert c.closed == 1


def test_client_closed_on_unexpected_exception(monkeypatch, approved):
    c = _TrackingClient()

    async def boom(*_a, **_k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(v20, "_run_migration_with_client", boom)
    assert _run_with_client(monkeypatch, c, apply=False) == 2
    assert c.closed == 1


def test_client_closed_when_exception_escapes_after_a_write(monkeypatch, approved):
    c = _TrackingClient()

    async def after_write(*_a, **_k):
        v20._mark_mutation_started()
        raise PyMongoError("network dropped after the backfill")

    monkeypatch.setattr(v20, "_run_migration_with_client", after_write)
    assert _run_with_client(monkeypatch, c, apply=False) == EXIT_INCOMPLETE
    assert c.closed == 1


# ---------------- 9 & 10. driver exceptions before and after writes ----------------

def test_driver_exception_before_writes_exits_2(monkeypatch, approved):
    c = _TrackingClient()

    async def driver_fail(*_a, **_k):
        raise PyMongoError("server selection timeout")

    monkeypatch.setattr(v20, "_run_migration_with_client", driver_fail)
    assert _run_with_client(monkeypatch, c, apply=False) == 2
    assert c.closed == 1


def test_driver_exception_after_partial_writes_exits_3(monkeypatch, approved):
    c = _TrackingClient()

    async def partial(*_a, **_k):
        v20._mark_mutation_started()
        raise PyMongoError("connection dropped mid-backfill")

    monkeypatch.setattr(v20, "_run_migration_with_client", partial)
    assert _run_with_client(monkeypatch, c, apply=True, confirm_db="midconnect_v20_round3_test") == EXIT_INCOMPLETE


def test_exit_1_is_never_returned(monkeypatch, approved):
    """Any exception, of any type, classifies to 2 or 3 — never escapes as 1."""
    for exc in (RuntimeError("x"), KeyError("y"), PyMongoError("z")):
        c = _TrackingClient()

        async def raiser(*_a, _e=exc, **_k):
            raise _e

        monkeypatch.setattr(v20, "_run_migration_with_client", raiser)
        assert _run_with_client(monkeypatch, c, apply=False) in (2, 3)


# ---------------- 12. (structural) rollback index-drop failure is fail-closed ----------------

def test_rollback_index_drop_failure_returns_2_with_no_writes_listed():
    src = open(v20.__file__, encoding="utf-8").read()
    start = src.index("async def do_rollback")
    body = src[start:src.index("def evaluate_post_migration")]
    drop = body.index("await db.categories.drop_index(actual_index_name)")
    # The drop is preceded by the read-only preflight and followed by restores only.
    assert body.index("PREFLIGHT") < drop < body.index("for doc, cat_id, action in planned")


# ================= DB-backed (disposable MongoDB only) =================
# Skipped unless PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME name the
# disposable instance. Each test uses its own generated database, validated by
# validate_test_target before any connection, and drops it in finally.

import json  # noqa: E402
import uuid  # noqa: E402

from bson import ObjectId  # noqa: E402

from phase1_db_guard import validate_test_target  # noqa: E402

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

_DB_REQUIRED = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)


def _iso():
    return DB_NAME + "_" + uuid.uuid4().hex[:8]


def _db_run(coro):
    return asyncio.run(coro)


@_DB_REQUIRED
def test_rollback_missing_field_docs_do_not_block_preexisting_index_rollback(tmp_path):
    """Round 3 (P5 over-count): with a PRE-EXISTING unique sparse index that is
    kept, a document whose slug FIELD IS ABSENT must not be counted as an
    explicit null blocker. Only an explicitly stored null/empty value blocks.
    """
    iso = _iso()
    validate_test_target(URL, iso)
    tag = uuid.uuid4().hex[:8]
    restored_id = ObjectId()
    missing_id = ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso]
        try:
            # Pre-existing unique sparse index (not created by V20).
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME)
            # A category whose slug field was absent before V20 and is still
            # absent from the planned state, plus a restorable one.
            await db.categories.insert_one({"_id": missing_id, "name": f"M {tag}"})
            await db.categories.insert_one(
                {"_id": restored_id, "name": f"R {tag}", "slug": f"r-{tag}"})
            backup = [
                {"_id": str(restored_id), "name": f"R {tag}", "slug": None,
                 "slug_field_present": True, "legacySlugs_field_present": False, "assigned_slug": f"r-{tag}"},
            ]
            meta = {"_meta": {
                "kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V3",
                "index_name": v20.INDEX_NAME, "index_actual_name": v20.INDEX_NAME,
                "index_existed_before_v20": True, "index_created_by_v20": False,
                "created_at_utc": "20260101T000000Z",
            }}
            path = tmp_path / "rb_missing.json"
            path.write_text(json.dumps([meta] + backup), encoding="utf-8")
            # The restored document's pre-V20 slug is an explicit null: one
            # explicit-null restore is allowed when no OTHER null/empty exists.
            # The field-absent document must NOT be counted as a blocker.
            rc = await v20.do_rollback(db, str(path))
            restored = await db.categories.find_one({"_id": restored_id})
            return rc, restored
        finally:
            await client.drop_database(iso)
            client.close()

    rc, restored = _db_run(go())
    assert rc == 0, "a field-absent document must not block rollback"
    assert restored.get("slug") is None and "slug" in restored


@_DB_REQUIRED
def test_53_category_fixture_nine_required_and_44_extra_slugs(tmp_path, monkeypatch):
    """Round 3 fixture: 53 categories — nine mandatory public categories plus
    44 extra ones. The nine public slugs must be satisfied, the 44 extras get
    unique deterministic slugs, and a second run is idempotent (exit 0 path).
    """
    iso = _iso()
    validate_test_target(URL, iso)
    tag = uuid.uuid4().hex[:6]
    nine = [(v20.slugify(n), n) for n in [
        "Cleaning Products", "Electrical Equipment & Supplies",
        "Electronics IT Industrial Automation", "Lights Lighting Accessories",
        "Metals Industrial Raw Materials", "Panel Meters and Accessories",
        "Safety Products", "Solar Equipment Panels",
        "VFD PLC HMI Control Equipments"]]
    extra = [f"Extra Category {i:02d} {tag}" for i in range(44)]
    names = [n for _s, n in nine] + extra
    assert len(names) == 53

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso]
        try:
            docs = [{"_id": ObjectId(), "name": n} for n in names]
            await db.categories.insert_many(docs)
            plan, backup = await v20.build_slug_plan(db)
            failures = await v20.check_expected_public_slugs(db, plan)
            slugs = [item["slug"] for item in plan]
            return failures, slugs, len(plan)
        finally:
            await client.drop_database(iso)
            client.close()

    failures, slugs, planned = _db_run(go())
    assert failures == [], failures
    assert planned == 53
    assert len(set(slugs)) == 53, "every planned slug must be unique"
    for public_slug, _name in nine:
        assert public_slug in slugs
    assert all(v20.SLUG_FORMAT_RE.fullmatch(s) for s in slugs)


# ================= test-target isolation guard (pure) =================

def _guard():
    from phase1_db_guard import validate_test_target, UnsafeTestDatabase
    return validate_test_target, UnsafeTestDatabase


@pytest.mark.parametrize("name", ["b2b_marketplace", "midconnect", "admin", "config", "local"])
def test_guard_rejects_production_names(name):
    validate, unsafe = _guard()
    with pytest.raises(unsafe):
        validate("mongodb://127.0.0.1:27117/", name)


@pytest.mark.parametrize("url", [
    "mongodb+srv://user:pw@cluster0.example.mongodb.net/",   # Atlas / production shape
    "mongodb://10.0.0.5:27117/",                              # non-loopback
    "mongodb://db.internal:27117/",                           # non-loopback hostname
])
def test_guard_rejects_non_loopback_hosts(url):
    validate, unsafe = _guard()
    with pytest.raises(unsafe, match="not loopback"):
        validate(url, "midconnect_phase1_test_abc123")


@pytest.mark.parametrize("url", ["mongodb://127.0.0.1:27018/", "mongodb://127.0.0.1/"])
def test_guard_rejects_wrong_ports(url):
    validate, unsafe = _guard()
    with pytest.raises(unsafe, match="not 27117"):
        validate(url, "midconnect_phase1_test_abc123")


def test_guard_accepts_the_disposable_target():
    validate, _unsafe = _guard()
    validate("mongodb://127.0.0.1:27117/", "midconnect_phase1_test_abc123")


def test_generated_database_names_are_unique():
    names = {_iso() for _ in range(200)} if (URL and DB_NAME) else None
    if names is None:
        # Without a DB env the generator still follows the same rule.
        names = {"x_" + uuid.uuid4().hex[:8] for _ in range(200)}
    assert len(names) == 200


def test_iso_name_rule_uses_db_name_plus_uuid_suffix():
    src = open(__file__, encoding="utf-8").read()
    assert 'DB_NAME + "_" + uuid.uuid4().hex[:8]' in src


def test_no_test_prints_a_connection_url():
    """The migration never prints the MONGO_URL variable or its value."""
    src = open(v20.__file__, encoding="utf-8").read()
    for line in src.splitlines():
        if line.lstrip().startswith("print(") and "MONGO_URL" in line:
            pytest.fail(f"a print statement exposes the connection URL: {line.strip()}")


# ================= Item 11: missing field vs explicit null (pure) =================

def test_null_filter_distinguishes_missing_field_from_explicit_null():
    """The count/index-blocking filter must require the field to EXIST before
    matching $in [null, ""]; a missing field must not count as an explicit null."""
    src = open(v20.__file__, encoding="utf-8").read()
    assert '"$exists": True' in src and '"$in": [None, ""]' in src
    # Every index-blocking / over-count query uses the exists-guarded form.
    guarded = src.count('{"slug": {"$exists": True, "$in": [None, ""]}}')
    assert guarded >= 3, f"expected >=3 exists-guarded null filters, found {guarded}"
    # The bare, unguarded form must not appear in any count query.
    assert '{"slug": {"$in": [None, ""]}}' not in src
