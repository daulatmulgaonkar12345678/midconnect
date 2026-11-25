"""V20 exact rollback — pure validation tests (NO database).

Drives the REAL backup format and rollback validator in
migrations.V20_backfill_category_slugs. Nothing here connects to MongoDB.
"""
import json
import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)

import migrations.V20_backfill_category_slugs as v20  # noqa: E402
from bson import ObjectId  # noqa: E402

OID = str(ObjectId())


def _meta(**over):
    meta = {
        "kind": v20.BACKUP_KIND,
        "index_name": v20.INDEX_NAME,
        "index_actual_name": None,
        "index_existed_before_v20": True,
        "index_created_by_v20": False,
        "created_at_utc": "20260101T000000Z",
    }
    meta.update(over)
    return {"_meta": meta}


def _rec(**over):
    rec = {
        "_id": OID,
        "name": "X",
        "slug": None,
        "slug_field_present": False,
        "assigned_slug": "x-assigned",
        "legacySlugs_field_present": False,
    }
    rec.update(over)
    return rec


def _write(tmp_path, payload):
    path = tmp_path / "backup.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


# ---------------- backup format: original legacySlugs state is recorded ----------------

def test_backup_kind_is_v3_exact_rollback_format():
    assert v20.BACKUP_KIND == "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V3"


@pytest.mark.parametrize("cat, problem", [
    ({"legacySlugs": None}, "not an array"),
    ({"legacySlugs": "single"}, "not an array"),
    ({"legacySlugs": {"a": 1}}, "not an array"),
    ({"legacySlugs": ["ok", 7]}, "non-string entry"),
])
def test_malformed_legacy_slugs_cannot_be_recorded_exactly(cat, problem):
    message = v20.original_legacy_slugs_problem(cat)
    assert message is not None and problem in message


@pytest.mark.parametrize("cat", [
    {},                                   # absent
    {"legacySlugs": []},                  # empty
    {"legacySlugs": ["a", "b", "a"]},     # populated, duplicate kept
])
def test_recordable_legacy_slugs_states_are_accepted(cat):
    assert v20.original_legacy_slugs_problem(cat) is None


# ---------------- rollback validator: fail closed before any database access ----------------

def test_v2_backup_is_refused_as_not_exactly_restorable(tmp_path):
    v2 = _meta()
    v2["_meta"]["kind"] = "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2"
    with pytest.raises(v20.MigrationBlocked) as info:
        v20._load_and_validate_rollback_backup(_write(tmp_path, [v2, _rec()]))
    assert "FAIL-CLOSED" in str(info.value)


def test_record_without_legacy_flag_is_refused(tmp_path):
    rec = _rec()
    del rec["legacySlugs_field_present"]
    with pytest.raises(v20.MigrationBlocked, match="legacySlugs_field_present"):
        v20._load_and_validate_rollback_backup(_write(tmp_path, [_meta(), rec]))


def test_absent_legacy_state_with_recorded_array_is_refused(tmp_path):
    rec = _rec(legacySlugs_field_present=False, legacySlugs=["should-not-be-here"])
    with pytest.raises(v20.MigrationBlocked, match="absent before V20"):
        v20._load_and_validate_rollback_backup(_write(tmp_path, [_meta(), rec]))


@pytest.mark.parametrize("value", ["not-an-array", None, ["ok", 3]])
def test_present_legacy_state_must_be_array_of_strings(tmp_path, value):
    rec = _rec(legacySlugs_field_present=True, legacySlugs=value)
    with pytest.raises(v20.MigrationBlocked, match="not an array of strings"):
        v20._load_and_validate_rollback_backup(_write(tmp_path, [_meta(), rec]))


def test_exact_v3_record_is_accepted_and_order_is_preserved(tmp_path):
    order = ["zeta", "alpha", "zeta"]
    rec = _rec(legacySlugs_field_present=True, legacySlugs=order)
    meta, docs = v20._load_and_validate_rollback_backup(_write(tmp_path, [_meta(), rec]))
    assert docs[0]["legacySlugs"] == order
    assert docs[0]["legacySlugs_field_present"] is True


# ---------------- exact-state matchers used by the conditional rollback ----------------

def test_legacy_match_absent_requires_absent():
    doc = {"legacySlugs_field_present": False}
    assert v20._legacy_matches_v20_state(doc, v20._ABSENT)
    assert not v20._legacy_matches_v20_state(doc, [])


def test_legacy_match_present_requires_exact_array_and_order():
    doc = {"legacySlugs_field_present": True, "legacySlugs": ["a", "b"]}
    assert v20._legacy_matches_v20_state(doc, ["a", "b"])
    assert not v20._legacy_matches_v20_state(doc, ["b", "a"])      # order matters
    assert not v20._legacy_matches_v20_state(doc, ["a", "b", "c"])  # concurrent change
    assert not v20._legacy_matches_v20_state(doc, v20._ABSENT)


def test_already_restored_requires_both_fields_exact():
    doc = {"slug_field_present": True, "slug": None,
           "legacySlugs_field_present": False}
    assert v20._already_restored(doc, {"slug": None})
    assert not v20._already_restored(doc, {"slug": None, "legacySlugs": []})


# ---------------- helper: a MigrationBlocked-or-dict guard for pytest.raises ----------------


# ---------------- DB-backed: conditional-write conflicts on legacySlugs (disposable DB) ----------------

import uuid  # noqa: E402

from migrations.V20_backfill_category_slugs import INDEX_NAME  # noqa: E402

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

_DB_REQUIRED = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)


def _db_run(coro):
    import asyncio
    return asyncio.run(coro)


@_DB_REQUIRED
def test_legacy_slugs_changed_after_v20_is_a_conflict_and_never_overwritten(tmp_path):
    """A legacySlugs array changed AFTER V20 is a rollback conflict: the
    concurrent value is preserved, nothing is restored over it, and the run is
    incomplete (never reported as a clean rollback)."""
    from motor.motor_asyncio import AsyncIOMotorClient

    tag = "exactrb-" + uuid.uuid4().hex[:8]
    doc_id = ObjectId()
    assigned = f"exact-{tag}"
    v20_legacy = ["before-v20"]
    concurrent = ["before-v20", "added-after-v20"]

    async def go():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            await db.categories.insert_one({
                "_id": doc_id, "tag": tag, "name": f"Exact {tag}",
                "slug": assigned, "legacySlugs": concurrent,
            })
            import json as _json
            meta = {"_meta": {"kind": v20.BACKUP_KIND, "index_name": INDEX_NAME,
                              "index_actual_name": None,
                              "index_existed_before_v20": True,
                              "index_created_by_v20": False,
                              "created_at_utc": "20260101T000000Z"}}
            rec = {"_id": str(doc_id), "name": f"Exact {tag}", "slug": None,
                   "slug_field_present": True, "assigned_slug": assigned,
                   "legacySlugs_field_present": True, "legacySlugs": v20_legacy}
            path = tmp_path / "exact_conflict.json"
            path.write_text(_json.dumps([meta, rec]), encoding="utf-8")
            # The index must exist to match the recorded provenance.
            try:
                await db.categories.create_index([("slug", 1)], unique=True, sparse=True,
                                                 name=INDEX_NAME)
            except Exception:
                pass
            rc = await v20.do_rollback(db, str(path))
            doc = await db.categories.find_one({"_id": doc_id})
            return rc, doc
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            client.close()

    rc, doc = _db_run(go())
    assert rc == 2, "a legacySlugs change after V20 is a preflight conflict (exit 2)"
    assert doc["legacySlugs"] == concurrent, "the concurrent legacySlugs must be preserved"
    assert doc["slug"] == assigned, "the slug must not be overwritten"
