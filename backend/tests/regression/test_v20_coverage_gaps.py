"""V20 coverage-gap tests (disposable MongoDB only).

Closes four gaps from the 15-scenario coverage report:
  1. rollback restores an ORIGINAL empty-string slug exactly (not null/absent);
  2. an empty-string slug remaining before index creation blocks the unique
     sparse index;
  3. a successful apply leaves existing valid slugs unchanged;
  4. the exact `DRY-RUN BLOCKED` output, with no database writes.

Isolation: every DB-backed test gets its own freshly generated database
(DB_NAME + "_" + uuid4 hex[:8]), validated by validate_test_target before any
connection, and dropped in finally. No test uses the shared PHASE1_TEST_DB_NAME
for data or migration execution, and no test deletes or drops indexes by tag.
MONGO_URL is never read from the environment; the migration is pointed at the
disposable URL and the per-test database via monkeypatch.
"""
import asyncio
import glob
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
from phase1_db_guard import validate_test_target  # noqa: E402

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)

EXACT_DRY_RUN_BLOCKED = (
    "DRY-RUN BLOCKED (exit 2): --apply would fail closed on these duplicates "
    "(correction 6); nothing was written."
)


def _iso_db_name():
    """A unique, per-test disposable database name derived from DB_NAME."""
    return DB_NAME + "_" + uuid.uuid4().hex[:8]


def _run(coro):
    return asyncio.run(coro)


_NINE_PUBLIC = [
    ("cleaning-products", "Cleaning Products"),
    ("electrical-equipment-supplies", "Electrical Equipment & Supplies"),
    ("electronics-it-industrial-automation", "Electronics IT Industrial Automation"),
    ("lights-lighting-accessories", "Lights Lighting Accessories"),
    ("metals-industrial-raw-materials", "Metals Industrial Raw Materials"),
    ("panel-meters-and-accessories", "Panel Meters and Accessories"),
    ("safety-products", "Safety Products"),
    ("solar-equipment-panels", "Solar Equipment Panels"),
    ("vfd-plc-hmi-control-equipments", "VFD PLC HMI Control Equipments"),
]


def _approved(iso_name):
    """Round 3: the (host, port, db) triple of the disposable target, for the gate."""
    from urllib.parse import urlparse
    parsed = urlparse(URL)
    return (parsed.hostname, parsed.port or 27017, iso_name)


def test_rollback_restores_original_empty_string_slug(tmp_path):
    """An original slug of "" (field present) must be restored to exactly "",
    not to null and not removed. The V20-assigned slug is kept in legacySlugs."""
    tag = "v20gap-rbempty-" + uuid.uuid4().hex[:8]
    doc_id = ObjectId()
    iso_name = _iso_db_name()
    validate_test_target(URL, iso_name)

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_one(
                {"_id": doc_id, "tag": tag, "name": f"Rb Empty {tag}", "slug": ""}
            )
            # What V20 apply did to this document: backfilled "" -> assigned slug.
            await db.categories.update_one(
                {"_id": doc_id}, {"$set": {"slug": f"rb-empty-{tag}"}}
            )
            backup = [{
                "_id": str(doc_id),
                "name": f"Rb Empty {tag}",
                "slug": "",
                "slug_field_present": True, "legacySlugs_field_present": False,
                "assigned_slug": f"rb-empty-{tag}",
            }]
            backup_path = tmp_path / "v20_rb_empty.json"
            backup_path.write_text(json.dumps(backup), encoding="utf-8")
            rc = await v20.do_rollback(db, str(backup_path))
            doc = await db.categories.find_one({"_id": doc_id})
            return rc, doc
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc, doc = _run(go())
    assert rc == 0
    assert "slug" in doc, "field present originally must stay present"
    assert type(doc["slug"]) is str and doc["slug"] == "", (
        f"original empty string must be restored exactly, got {doc['slug']!r}"
    )
    assert f"rb-empty-{tag}" not in (doc.get("legacySlugs") or []), "exact rollback never adds the V20-assigned slug to legacySlugs"
    assert "legacySlugs" not in doc, "legacySlugs absent before V20 stays absent"


def test_empty_string_slug_after_apply_blocks_unique_sparse_index(tmp_path):
    """If an empty-string slug remains when index creation is attempted, the
    guard refuses (DEFERRED) and no unique sparse index is created."""
    tag = "v20gap-emptyblk-" + uuid.uuid4().hex[:8]
    backup_path = str(tmp_path / "unused_backup.json")
    iso_name = _iso_db_name()
    validate_test_target(URL, iso_name)

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_one(
                {"_id": ObjectId(), "tag": tag, "name": f"Empty Blocker {tag}", "slug": ""}
            )
            error = None
            try:
                await v20.create_slug_index_guarded(db, backup_path, backfilled=0)
            except v20.MigrationBlocked as exc:
                error = str(exc)
            indexes = await db.categories.index_information()
            return error, indexes
        finally:
            await client.drop_database(iso_name)
            client.close()

    error, indexes = _run(go())
    assert error is not None, "an empty-string slug must block index creation"
    assert "DEFERRED (F1)" in error and "null/empty" in error
    assert v20.INDEX_NAME not in indexes, "no unique sparse index may be created"


def test_successful_apply_preserves_existing_valid_slugs(tmp_path, monkeypatch):
    """A passing apply backfills only the missing slug. A pre-existing valid
    slug is byte-for-byte unchanged and is not written to the backup."""
    tag = "v20gap-keep-" + uuid.uuid4().hex[:8]
    valid_id, missing_id = ObjectId(), ObjectId()
    valid_slug = f"keep-valid-{uuid.uuid4().hex[:10]}"
    iso_name = _iso_db_name()
    validate_test_target(URL, iso_name)

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            # Round 3 (P2): the nine mandatory public categories already hold
            # their public slugs, so the public-slug check passes; only the
            # two fixture categories below are under test.
            public = [{"_id": ObjectId(), "tag": tag, "name": n, "slug": s}
                      for s, n in _NINE_PUBLIC]
            await db.categories.insert_many(public + [
                {"_id": valid_id, "tag": tag, "name": f"Keep Valid {tag}", "slug": valid_slug},
                {"_id": missing_id, "tag": tag, "name": f"Keep Missing {tag}", "slug": None},
            ])
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", iso_name)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
            # Round 3: approve exactly this generated disposable target and
            # pass the exact apply confirmation for it.
            monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({_approved(iso_name)}))
            rc = await v20.run_migration(apply=True, confirm_db=iso_name)
            valid_doc = await db.categories.find_one({"_id": valid_id})
            missing_doc = await db.categories.find_one({"_id": missing_id})
            backups = glob.glob(str(tmp_path / "*.json"))
            return rc, valid_doc, missing_doc, backups
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc, valid_doc, missing_doc, backups = _run(go())
    assert rc == 0
    assert valid_doc["slug"] == valid_slug, "existing valid slug must be unchanged"
    assert missing_doc["slug"], "missing slug must be backfilled"
    assert missing_doc["slug"] != valid_slug
    assert len(backups) == 1
    with open(backups[0], encoding="utf-8") as fh:
        records = json.load(fh)
    # records[0] is the _meta header written by write_and_validate_backup.
    ids = {r["_id"] for r in records if "_id" in r}
    assert str(valid_id) not in ids, "an already-valid slug must not appear in the backup"
    assert str(missing_id) in ids


def test_dry_run_blocked_prints_exact_message_and_writes_nothing(tmp_path, monkeypatch, capsys):
    """Duplicate pre-existing slugs in dry-run print the exact DRY-RUN BLOCKED
    line, return 2, and leave every document, the index set and the backup
    directory untouched."""
    tag = "v20gap-dryblk-" + uuid.uuid4().hex[:8]
    dup_a, dup_b = ObjectId(), ObjectId()
    dup_slug = f"dry-blk-{tag}"
    iso_name = _iso_db_name()
    validate_test_target(URL, iso_name)

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[iso_name]
        try:
            await db.categories.insert_many([
                {"_id": dup_a, "tag": tag, "name": f"Dry Blk A {tag}", "slug": dup_slug},
                {"_id": dup_b, "tag": tag, "name": f"Dry Blk B {tag}", "slug": dup_slug},
            ])
            before_docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            before_indexes = await db.categories.index_information()
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", iso_name)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
            monkeypatch.setattr(v20, "APPROVED_TARGETS", frozenset({_approved(iso_name)}))
            rc = await v20.run_migration(apply=False)
            after_docs = await db.categories.find({}).sort("_id", 1).to_list(None)
            after_indexes = await db.categories.index_information()
            return rc, before_docs, after_docs, before_indexes, after_indexes
        finally:
            await client.drop_database(iso_name)
            client.close()

    rc, before_docs, after_docs, before_idx, after_idx = _run(go())
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.startswith("DRY-RUN BLOCKED")]
    assert lines == [EXACT_DRY_RUN_BLOCKED], f"exact DRY-RUN BLOCKED line expected, got {lines!r}"
    assert rc == 2
    assert after_docs == before_docs, "dry-run must not write any document"
    assert after_idx == before_idx, "dry-run must not create or drop any index"
    assert glob.glob(str(tmp_path / "*")) == [], "dry-run must not write a backup"
