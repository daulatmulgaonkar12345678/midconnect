"""V20 rollback: concurrent legacySlugs change between preflight and write (disposable DB only).

Preflight reads each backed-up category and confirms its legacySlugs still matches
the V20 state. The restore then issues a conditional update_one whose filter pins
both the assigned slug and the recorded legacySlugs. This test injects a concurrent
legacySlugs change immediately before that conditional update_one, via a proxy on
the real disposable database, and asserts rollback does NOT overwrite it.

Guarded by PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME and validate_test_target.
The database name is unique per test and is dropped in finally.
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

CONCURRENT_LEGACY = ["concurrent-change"]


class _RacingCategories:
    """Proxy for db.categories: before the FIRST conditional restore write, a
    concurrent writer changes legacySlugs directly on the real collection."""

    def __init__(self, real, race_id, log):
        self._real = real
        self._race_id = race_id
        self._log = log
        self._fired = False

    def __getattr__(self, name):
        return getattr(self._real, name)

    async def update_one(self, filter_, update, *args, **kwargs):
        if not self._fired and "slug" in filter_ and "legacySlugs" in filter_:
            self._fired = True
            self._log.append("race_injected")
            await self._real.update_one(
                {"_id": self._race_id}, {"$set": {"legacySlugs": CONCURRENT_LEGACY}}
            )
        self._log.append("update_one")
        return await self._real.update_one(filter_, update, *args, **kwargs)


class _DBProxy:
    def __init__(self, real, race_id, log):
        self._real = real
        self.categories = _RacingCategories(real.categories, race_id, log)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _ClientProxy:
    def __init__(self, real, race_id, log):
        self._real = real
        self._race_id = race_id
        self._log = log

    def __getitem__(self, name):
        return _DBProxy(self._real[name], self._race_id, self._log)

    def close(self):
        self._real.close()


def _backup(path, categories):
    meta = {"_meta": {
        "kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V3",
        "index_name": v20.INDEX_NAME,
        "index_actual_name": v20.INDEX_NAME,
        "index_existed_before_v20": True,
        "index_created_by_v20": False,
        "created_at_utc": "20260101T000000Z",
    }}
    path.write_text(json.dumps([meta] + categories), encoding="utf-8")
    return str(path)


def test_concurrent_legacy_change_between_preflight_and_write_is_not_overwritten(
    tmp_path, monkeypatch, capsys
):
    from motor.motor_asyncio import AsyncIOMotorClient
    from phase1_db_guard import validate_test_target

    iso_name = DB_NAME + "_" + uuid.uuid4().hex[:8]
    validate_test_target(URL, iso_name)

    monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({("127.0.0.1", 27117, iso_name)}))
    monkeypatch.setenv("MONGO_URL", URL)
    monkeypatch.setenv("DB_NAME", iso_name)

    a_id = ObjectId()
    backup_path = _backup(tmp_path / "legacy_race.json", [
        # Pre-V20: slug was "legacy-a" and legacySlugs was ["old-a"].
        # V20 assigned "alpha"; post-V20 legacySlugs is still ["old-a"], so preflight passes.
        {"_id": str(a_id), "name": "Alpha", "slug": "legacy-a", "slug_field_present": True,
         "legacySlugs": ["old-a"], "legacySlugs_field_present": True,
         "assigned_slug": "alpha"},
    ])

    real_client_cls = AsyncIOMotorClient
    log = []

    def factory(url, *args, **kwargs):
        return _ClientProxy(real_client_cls(url, *args, **kwargs), a_id, log)

    monkeypatch.setattr(v20, "AsyncIOMotorClient", factory)

    async def seed():
        client = real_client_cls(URL, serverSelectionTimeoutMS=5000)
        try:
            await client[iso_name].categories.insert_many([
                {"_id": a_id, "name": "Alpha", "slug": "alpha", "legacySlugs": ["old-a"]},
            ])
            await client[iso_name].categories.create_index(
                [("slug", 1)], name=v20.INDEX_NAME, unique=True, sparse=True
            )
        finally:
            client.close()

    async def read_doc():
        client = real_client_cls(URL, serverSelectionTimeoutMS=5000)
        try:
            return await client[iso_name].categories.find_one({"_id": a_id})
        finally:
            client.close()

    async def go():
        try:
            await seed()
            rc = await v20.run_migration(apply=False, rollback_path=backup_path, confirm_db=iso_name)
            return rc, await read_doc()
        finally:
            cleanup = real_client_cls(URL, serverSelectionTimeoutMS=5000)
            try:
                await cleanup.drop_database(iso_name)
            finally:
                cleanup.close()

    rc, doc = asyncio.run(go())
    out = capsys.readouterr().out

    # The race was really injected between preflight and the conditional write.
    assert log[:2] == ["race_injected", "update_one"], f"race not injected in order: {log}"
    # The conditional write matched nothing: reported as a conflict, not success.
    assert rc == v20.EXIT_INCOMPLETE
    assert "CONFLICT" in out
    assert "nothing overwritten" in out
    # The concurrent legacySlugs change survives untouched.
    assert doc["legacySlugs"] == CONCURRENT_LEGACY
    # The slug was not restored to the pre-V20 value.
    assert doc["slug"] == "alpha"
