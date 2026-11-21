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


def test_post_verify_fails_on_wrong_category_count():
    rows = _good_rows()[:8]
    report = v20.evaluate_post_migration(rows, {v20.INDEX_NAME: GOOD_INDEX})
    assert report["passed"] is False
    assert "category count is 8" in _failures(report)


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
