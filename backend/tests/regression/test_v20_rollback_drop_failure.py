"""V20 rollback: controlled failure of the index drop (disposable DB only).

Drives the NORMAL rollback entry point (run_migration with rollback_path) against
a disposable database. The Motor client is replaced by a recording proxy whose
db.categories.drop_index() raises a controlled exception. Every other call is
forwarded to the real disposable database.

Guarded by PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME and validate_test_target.
The database name is unique per test and is dropped in finally. No production
URL is read: MONGO_URL is set to the disposable URL only inside the test.
"""
import asyncio
import json
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

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)

WRITE_OPS = {
    "insert_one", "insert_many", "update_one", "update_many", "replace_one",
    "delete_one", "delete_many", "bulk_write", "find_one_and_update",
    "find_one_and_replace", "find_one_and_delete", "create_index",
    "create_indexes", "drop", "drop_indexes",
}
SIMULATED_MESSAGE = "simulated index drop failure (test)"


class SimulatedDropIndexFailure(Exception):
    pass


class _RecordingCategories:
    """Proxy for db.categories: records writes, makes drop_index raise."""

    def __init__(self, real, log):
        self._real = real
        self._log = log

    def __getattr__(self, name):
        attr = getattr(self._real, name)
        if name in WRITE_OPS:
            async def recorded(*args, **kwargs):
                self._log.append(name)
                return await attr(*args, **kwargs)
            return recorded
        return attr

    async def drop_index(self, name):
        self._log.append("drop_index")
        raise SimulatedDropIndexFailure(SIMULATED_MESSAGE)


class _DBProxy:
    def __init__(self, real, log):
        self._real = real
        self._log = log
        self.categories = _RecordingCategories(real.categories, log)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _ClientProxy:
    def __init__(self, real, log):
        self._real = real
        self._log = log

    def __getitem__(self, name):
        return _DBProxy(self._real[name], self._log)

    def close(self):
        self._real.close()


def _backup(path, categories):
    """V20 backup: the index was CREATED by V20, so rollback must drop it."""
    meta = {"_meta": {
        "kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V3",
        "index_name": v20.INDEX_NAME,
        "index_actual_name": v20.INDEX_NAME,
        "index_existed_before_v20": False,
        "index_created_by_v20": True,
        "created_at_utc": "20260101T000000Z",
    }}
    path.write_text(json.dumps([meta] + categories), encoding="utf-8")
    return str(path)


def test_rollback_index_drop_failure_exits_2_and_changes_nothing(tmp_path, monkeypatch, capsys):
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)

    # The normal entry point resolves the target against the approved list.
    monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({("127.0.0.1", 27117, iso_name)}))
    monkeypatch.setenv("MONGO_URL", URL)
    monkeypatch.setenv("DB_NAME", iso_name)

    a_id, b_id, c_id = ObjectId(), ObjectId(), ObjectId()
    backup_path = _backup(tmp_path / "drop_failure.json", [
        # Post-V20 state: slug equals the V20-assigned slug, so preflight has no conflict.
        {"_id": str(a_id), "name": "Alpha", "slug": None, "slug_field_present": False, "legacySlugs_field_present": False,
         "assigned_slug": "alpha"},
        {"_id": str(b_id), "name": "Beta", "slug": "legacy-beta", "slug_field_present": True, "legacySlugs_field_present": False,
         "assigned_slug": "beta"},
    ])
    post_v20_docs = [
        {"_id": a_id, "name": "Alpha", "slug": "alpha"},
        {"_id": b_id, "name": "Beta", "slug": "beta"},
        # Not in the backup: must never be touched by rollback.
        {"_id": c_id, "name": "Gamma", "slug": "gamma"},
    ]

    real_client_cls = AsyncIOMotorClient
    proxies = []
    log = []

    def factory(url, *args, **kwargs):
        proxy = _ClientProxy(real_client_cls(url, *args, **kwargs), log)
        proxies.append(proxy)
        return proxy

    monkeypatch.setattr(v20, "AsyncIOMotorClient", factory)

    async def seed():
        client = real_client_cls(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many(post_v20_docs)
            await db.categories.create_index(
                [("slug", 1)], name=v20.INDEX_NAME, unique=True, sparse=True
            )
            await db.categories.create_index([("name", 1)], name="unrelated_name_idx")
        finally:
            client.close()

    async def snapshot():
        client = real_client_cls(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            idx = await db.categories.index_information()
            return docs, idx
        finally:
            client.close()

    async def go():
        try:
            await seed()
            before_docs, before_idx = await snapshot()
            rc = await v20.run_migration(apply=False, rollback_path=backup_path, confirm_db=iso_name)
            after_docs, after_idx = await snapshot()
            return rc, before_docs, before_idx, after_docs, after_idx
        finally:
            cleanup = real_client_cls(URL, serverSelectionTimeoutMS=5000)
            try:
                await cleanup.drop_database(iso_name)
            finally:
                cleanup.close()

    rc, before_docs, before_idx, after_docs, after_idx = asyncio.run(go())

    out = capsys.readouterr().out

    # Exit code 2: fail-closed, not success and not an unclassified exit 1.
    assert rc == 2
    # The failure is reported clearly and names the index and the cause.
    assert "FAIL-CLOSED" in out
    assert "could not be dropped" in out
    assert SIMULATED_MESSAGE in out
    assert "No document was modified" in out
    # The drop was attempted, and no write operation was issued at all.
    assert len(proxies) == 1
    assert log == ["drop_index"], f"unexpected operations: {log}"
    # No category restore writes: slugs and documents are byte-identical.
    assert before_docs == after_docs
    slugs = {d["name"]: d.get("slug") for d in after_docs}
    assert slugs == {"Alpha": "alpha", "Beta": "beta", "Gamma": "gamma"}
    # The original slug index survives the simulated failure, unchanged.
    assert v20.INDEX_NAME in after_idx
    assert before_idx == after_idx
    # Unrelated index is unchanged.
    assert "unrelated_name_idx" in after_idx
