"""V20 post-migration verification tests.

Pure tests (no database) exercise evaluate_post_migration directly. The one
DB-backed test runs only against the disposable PHASE1 test database, guarded
by PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME and validate_test_target. No
test connects to production or the migration's MONGO_URL.
"""
import asyncio
import os
import sys
import uuid

import pytest
from bson import ObjectId

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "tests"))

import migrations.V20_backfill_category_slugs as v20  # noqa: E402

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

GOOD_INDEX = {
    "v": 2,
    "key": [("slug", 1)],
    "name": v20.INDEX_NAME,
    "unique": True,
    "sparse": True,
}


def _good_rows():
    """Nine categories, one per expected slug, all valid and unique."""
    rows = []
    for slug in sorted(v20.EXPECTED_SLUGS):
        rows.append({"_id": ObjectId(), "name": slug.replace("-", " ").title(), "slug": slug})
    return rows


def _failures(report):
    return "\n".join(report["failures"])


# ---------------- pure verification logic ----------------

def test_post_verify_passes_for_complete_valid_mapping():
    report = v20.evaluate_post_migration(_good_rows(), {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is True, _failures(report)
    assert report["count"] == 9
    assert report["index_status"] == "compatible"
    assert sorted(report["expected_found"]) == sorted(v20.EXPECTED_SLUGS)
    assert report["expected_missing"] == []
    assert report["unexpected"] == []
    assert len(report["mapping"]) == 9


@pytest.mark.parametrize("bad_slug", [None, "", "   "])
def test_post_verify_fails_on_missing_null_or_blank_slug(bad_slug):
    rows = _good_rows()
    rows[0]["slug"] = bad_slug
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert "slug missing, null or blank" in _failures(report)


def test_post_verify_fails_on_absent_slug_field():
    rows = _good_rows()
    del rows[0]["slug"]
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False


@pytest.mark.parametrize("bad_slug", ["Has Upper", "under_score", "-leading", "trailing-", "a--b", 42])
def test_post_verify_fails_on_malformed_slug(bad_slug):
    rows = _good_rows()
    rows[0]["slug"] = bad_slug
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    if isinstance(bad_slug, str):
        assert "not a valid URL slug" in _failures(report)
    else:
        assert "slug missing, null or blank" in _failures(report)


def test_post_verify_fails_on_objectid_like_slug():
    rows = _good_rows()
    rows[0]["slug"] = "65a1b2c3d4e5f60718293a4b"
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert "not a valid URL slug" in _failures(report)


def test_post_verify_fails_on_duplicate_slugs():
    rows = _good_rows()
    rows[1]["slug"] = rows[0]["slug"]
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert "is not unique" in _failures(report)


def test_post_verify_fails_when_an_expected_category_is_unaccounted_for():
    rows = _good_rows()
    missing = sorted(v20.EXPECTED_SLUGS)[0]
    rows = [r for r in rows if r["slug"] != missing]
    rows.append({"_id": ObjectId(), "name": "Extra", "slug": "extra-category"})
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert missing in report["expected_missing"]
    assert "extra-category" in report["unexpected"]


def test_post_verify_passes_for_53_categories_with_44_additional_valid_slugs():
    rows = _good_rows()
    for i in range(44):
        rows.append({"_id": ObjectId(), "name": f"Extra {i}", "slug": f"extra-category-{i:02d}"})
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is True, _failures(report)
    assert report["count"] == 53
    assert report["valid_count"] == 53
    assert report["unique_count"] == 53
    assert report["duplicate_count"] == 0
    assert report["invalid_count"] == 0
    assert len(report["expected_found"]) == 9
    assert len(report["unexpected"]) == 44


def test_post_verify_fails_when_eight_categories_leave_a_required_slug_out():
    rows = _good_rows()[:8]
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert "required public category slug" in _failures(report)
    assert len(report["expected_missing"]) == 1


def test_post_verify_fails_when_index_is_missing():
    report = v20.evaluate_post_migration(_good_rows(), {})
    assert report["passed"] is False
    assert report["index_status"] == "missing"
    assert "missing" in _failures(report)


def test_post_verify_fails_when_index_is_not_unique_or_sparse():
    not_unique = dict(GOOD_INDEX, unique=False)
    report = v20.evaluate_post_migration(_good_rows(), {v20.INDEX_NAME: not_unique})
    assert report["passed"] is False
    assert report["index_status"] == "incompatible"
    assert "unique" in _failures(report)

    not_sparse = dict(GOOD_INDEX, sparse=False)
    report = v20.evaluate_post_migration(_good_rows(), {v20.INDEX_NAME: not_sparse})
    assert report["passed"] is False
    assert "sparse" in _failures(report)


def test_post_verify_fails_on_index_with_semantic_extra_option():
    partial = dict(GOOD_INDEX, partialFilterExpression={"slug": {"$type": "string"}})
    report = v20.evaluate_post_migration(_good_rows(), {v20.INDEX_NAME: partial})
    assert report["passed"] is False
    assert "partialFilterExpression" in _failures(report)


def test_post_verify_report_lists_slug_mapping():
    rows = _good_rows()
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    mapped = {m["slug"] for m in report["mapping"]}
    assert mapped == set(v20.EXPECTED_SLUGS)


def test_post_verify_never_raises_on_bad_data():
    rows = [{"_id": ObjectId(), "name": None, "slug": {"nested": True}}]
    report = v20.evaluate_post_migration(rows, None)
    assert report["passed"] is False
    assert report["index_status"] == "missing"


# ---------------- DB-backed read-only verification (disposable DB only) ----------------

@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_post_verify_db_is_read_only_and_reports_real_state():
    """Runs against its OWN freshly created disposable database (a generated
    midconnect_phase1_test_<suffix> name, guarded by validate_test_target).
    Nothing is shared: no index on a shared collection is dropped, no record
    is deleted by tag, and the whole database is dropped in finally. Verify
    must leave the collection and index byte-identical."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many([
                {"_id": ObjectId(), "name": "Verify Probe", "slug": "v20-verify-probe"},
            ])
            await db.categories.create_index(
                [("slug", 1)], name=v20.INDEX_NAME, unique=True, sparse=True
            )
            before_docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            before_idx = await db.categories.index_information()
            report = await v20.verify_post_migration(db)
            after_docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            after_idx = await db.categories.index_information()
            return report, before_docs, after_docs, before_idx, after_idx
        finally:
            await client.drop_database(iso_name)
            client.close()

    report, before_docs, after_docs, before_idx, after_idx = asyncio.run(go())
    # Read-only: documents and index definitions are identical before and after.
    assert before_docs == after_docs
    assert before_idx == after_idx
    assert v20.INDEX_NAME in after_idx, "verify must not drop the index"
    # One category only: the 9-category check must fail and say so.
    assert report["passed"] is False
    assert report["count"] == 1
    assert report["index_status"] == "compatible"


# ---------------- rollback reruns and exit codes (disposable DB only) ----------------

def _rollback_backup(path, docs, index_created=False):
    import json
    meta = {"_meta": {
        "kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
        "index_name": v20.INDEX_NAME,
        "index_existed_before_v20": not index_created,
        "index_created_by_v20": index_created,
        "created_at_utc": "20260101T000000Z",
    }}
    path.write_text(json.dumps([meta] + docs), encoding="utf-8")
    return str(path)


@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_rollback_rerun_is_idempotent_and_exits_zero(tmp_path):
    """A second rollback over the same backup must find every document already
    restored, write nothing, and exit 0 (not conflict on its own slugs)."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)
    a_id, b_id = ObjectId(), ObjectId()
    backup = _rollback_backup(tmp_path / "rerun.json", [
        {"_id": str(a_id), "name": "A", "slug": None, "slug_field_present": False,
         "assigned_slug": "rerun-a"},
        {"_id": str(b_id), "name": "B", "slug": "legacy-b", "slug_field_present": True,
         "assigned_slug": "rerun-b"},
    ])

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many([
                {"_id": a_id, "name": "A", "slug": "rerun-a"},
                {"_id": b_id, "name": "B", "slug": "rerun-b"},
            ])
            rc1 = await v20.do_rollback(db, backup)
            state1 = await db.categories.find({}).sort("_id", 1).to_list(None)
            rc2 = await v20.do_rollback(db, backup)
            state2 = await db.categories.find({}).sort("_id", 1).to_list(None)
            return rc1, rc2, state1, state2
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc1, rc2, state1, state2 = asyncio.run(go())
    assert rc1 == v20.EXIT_OK
    assert rc2 == v20.EXIT_OK, "rerun after a complete rollback must not conflict"
    assert state1 == state2, "rerun must not write"
    assert "slug" not in state1[0], "absent field restored as absent"
    assert state1[1]["slug"] == "legacy-b"


@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_rollback_with_deleted_category_is_incomplete_exit_3(tmp_path):
    """A backed-up category deleted after V20 cannot be restored: the rollback
    must NOT claim full success (exit 3), and the remaining documents are
    still restored."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)
    kept_id, gone_id = ObjectId(), ObjectId()
    backup = _rollback_backup(tmp_path / "deleted.json", [
        {"_id": str(kept_id), "name": "Kept", "slug": None, "slug_field_present": True,
         "assigned_slug": "del-kept"},
        {"_id": str(gone_id), "name": "Gone", "slug": None, "slug_field_present": True,
         "assigned_slug": "del-gone"},
    ])

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_one({"_id": kept_id, "name": "Kept", "slug": "del-kept"})
            rc = await v20.do_rollback(db, backup)
            kept = await db.categories.find_one({"_id": kept_id})
            return rc, kept
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc, kept = asyncio.run(go())
    assert rc == v20.EXIT_INCOMPLETE, "a deleted backed-up category is NOT a full rollback"
    assert kept["slug"] is None, "the surviving document is still restored"


def test_backup_rejects_absent_field_with_non_null_slug(tmp_path):
    """Pure: an inconsistent record is rejected before any database access."""
    backup = _rollback_backup(tmp_path / "bad.json", [
        {"_id": str(ObjectId()), "name": "X", "slug": "stale", "slug_field_present": False,
         "assigned_slug": "x-slug"},
    ])
    with pytest.raises(v20.MigrationBlocked):
        v20._load_and_validate_rollback_backup(backup)


def test_main_preserves_exit_code_from_rollback(monkeypatch, tmp_path):
    """Deterministic: main() returns the exit code of run_migration unchanged."""
    async def fake_run(apply, rollback_path=None):
        return v20.EXIT_INCOMPLETE
    monkeypatch.setattr(v20, "run_migration", fake_run)
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--rollback", "--backup", str(tmp_path / "b.json")])
    assert v20.main() == 3


# ---------------- 53-category fixture on a generated disposable DB ----------------

@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_fixture_53_categories_passes_real_verification_on_disposable_db():
    """Real MongoDB: 9 required public slugs plus 44 extra valid unique slugs.
    verify_post_migration must pass and report 53/53. The generated database
    is validated and dropped in finally."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)

    rows = _good_rows()
    for i in range(44):
        rows.append({"_id": ObjectId(), "name": f"Extra {i}",
                     "slug": f"fixture-extra-{i:02d}"})

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many(rows)
            await db.categories.create_index(
                [("slug", 1)], name=v20.INDEX_NAME, unique=True, sparse=True)
            return await v20.verify_post_migration(db)
        finally:
            await client.drop_database(iso_name)
            client.close()

    report = asyncio.run(go())
    assert report["passed"] is True, _failures(report)
    assert report["count"] == 53
    assert report["valid_count"] == 53
    assert report["unique_count"] == 53
    assert len(report["expected_found"]) == 9
    assert len(report["unexpected"]) == 44


# ---------------- pre-existing index: missing-field documents are not nulls ----------------

@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_rollback_missing_field_docs_do_not_count_as_nulls_under_preexisting_index(tmp_path):
    """Two restored-to-absent documents (field removed) plus one explicit-null
    restore under a PRE-EXISTING index: documents whose field is absent never
    occupy the sparse index, so the rollback must succeed (exit 0), not fail
    closed on a false null count."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)
    absent_a, absent_b, null_c = ObjectId(), ObjectId(), ObjectId()
    records = [
        {"_id": str(absent_a), "name": "AbsA", "slug": None, "slug_field_present": False,
         "assigned_slug": "abs-a"},
        {"_id": str(absent_b), "name": "AbsB", "slug": None, "slug_field_present": False,
         "assigned_slug": "abs-b"},
        {"_id": str(null_c), "name": "NullC", "slug": None, "slug_field_present": True,
         "assigned_slug": "null-c"},
    ]
    # Index existed before V20 (not created by V20): provenance keeps it.
    backup = _rollback_backup(tmp_path / "absent.json", records, index_created=False)

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many([
                {"_id": absent_a, "name": "AbsA", "slug": "abs-a"},
                {"_id": absent_b, "name": "AbsB", "slug": "abs-b"},
                {"_id": null_c, "name": "NullC", "slug": "null-c"},
            ])
            # Pre-existing index: NOT created by V20, so provenance says keep it.
            await db.categories.create_index(
                [("slug", 1)], name=v20.INDEX_NAME, unique=True, sparse=True)
            rc = await v20.do_rollback(db, backup)
            docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            index_present = v20.INDEX_NAME in await db.categories.index_information()
            return rc, docs, index_present
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc, docs, index_present = asyncio.run(go())
    assert rc == v20.EXIT_OK, "missing-field documents must not trip the null guard"
    by_name = {d["name"]: d for d in docs}
    assert "slug" not in by_name["AbsA"] and "slug" not in by_name["AbsB"]
    assert by_name["NullC"]["slug"] is None
    assert index_present, "a pre-existing index is never dropped"


# ---------------- partial rollback: a mid-rollback write error is exit 3 ----------------

@pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)
def test_rollback_write_error_mid_run_is_incomplete_and_rerun_recovers(tmp_path, monkeypatch):
    """A database error on one restore write must not claim success: that
    document is reported as not restored (exit 3), the rest are still restored,
    and a rerun with the same backup restores the failed document (exit 0)."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import PyMongoError
    from phase1_db_guard import validate_test_target
    from motor.motor_asyncio import AsyncIOMotorCollection

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)
    first, failing = ObjectId(), ObjectId()
    backup = _rollback_backup(tmp_path / "partial.json", [
        {"_id": str(first), "name": "First", "slug": "orig-first", "slug_field_present": True,
         "assigned_slug": "pw-first"},
        {"_id": str(failing), "name": "Failing", "slug": "orig-failing", "slug_field_present": True,
         "assigned_slug": "pw-failing"},
    ])
    real_update = AsyncIOMotorCollection.update_one
    fail_once = {"armed": True}

    async def flaky_update(self, flt, update, *a, **k):
        if fail_once["armed"] and flt.get("_id") == failing:
            fail_once["armed"] = False
            raise PyMongoError("simulated transient write failure")
        return await real_update(self, flt, update, *a, **k)

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many([
                {"_id": first, "name": "First", "slug": "pw-first"},
                {"_id": failing, "name": "Failing", "slug": "pw-failing"},
            ])
            monkeypatch.setattr(AsyncIOMotorCollection, "update_one", flaky_update)
            rc1 = await v20.do_rollback(db, backup)
            state1 = {d["name"]: d for d in await db.categories.find({}).to_list(None)}
            monkeypatch.setattr(AsyncIOMotorCollection, "update_one", real_update)
            rc2 = await v20.do_rollback(db, backup)
            state2 = {d["name"]: d for d in await db.categories.find({}).to_list(None)}
            return rc1, state1, rc2, state2
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc1, state1, rc2, state2 = asyncio.run(go())
    assert rc1 == v20.EXIT_INCOMPLETE, "a failed restore write is NOT a full rollback"
    assert state1["First"]["slug"] == "orig-first", "the other document is restored"
    assert state1["Failing"]["slug"] == "pw-failing", "the failed document is never overwritten"
    assert rc2 == v20.EXIT_OK, "a rerun with the same backup completes the rollback"
    assert state2["Failing"]["slug"] == "orig-failing"
