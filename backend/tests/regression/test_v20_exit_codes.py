"""V20 migration exit-code contract — deterministic, NO database.

Exit codes: 0 complete, 2 blocked before mutation or verification failure,
3 partial or incomplete migration/rollback. run_migration and main() are
driven with the database touchpoints replaced by in-process stubs, so the
branch taken and the returned code are exercised without MongoDB. The real
backup writer runs in a pytest tmp_path. No test reads a production URL:
the Motor client is replaced before use.
"""
import asyncio
import json
import os
import sys

import pytest
from pymongo.errors import PyMongoError

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)

import migrations.V20_backfill_category_slugs as v20  # noqa: E402
from migrations.V20_backfill_category_slugs import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_OK,
    MigrationBlocked,
)


# Round 3 (P2): one category per mandatory public slug, named so that
# slugify(name) == the slug. Used so the exit-code branches are reached.
_NINE_NAMES = [
    "Cleaning Products",
    "Electrical Equipment & Supplies",
    "Electronics IT Industrial Automation",
    "Lights Lighting Accessories",
    "Metals Industrial Raw Materials",
    "Panel Meters and Accessories",
    "Safety Products",
    "Solar Equipment Panels",
    "VFD PLC HMI Control Equipments",
]


_NINE_SLUGS = [
    "cleaning-products",
    "electrical-equipment-supplies",
    "electronics-it-industrial-automation",
    "lights-lighting-accessories",
    "metals-industrial-raw-materials",
    "panel-meters-and-accessories",
    "safety-products",
    "solar-equipment-panels",
    "vfd-plc-hmi-control-equipments",
]


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, _length):
        return list(self._rows)


class _Categories:
    """Stub collection: only the reads run_migration performs before a write."""

    def __init__(self, state):
        self._state = state

    async def count_documents(self, _query):
        return self._state["remaining_null"]

    def find(self, _query=None, _projection=None):
        # Round 3 (P2): the public-slug check reads every category.
        return _Cursor(list(self._state["public_rows"]))


class _Db:
    def __init__(self, state):
        self.categories = _Categories(state)


class _FakeClient:
    """Stand-in for AsyncIOMotorClient. Never connects anywhere."""

    def __init__(self, state):
        self._db = _Db(state)

    def __getitem__(self, _name):
        return self._db

    def close(self):
        pass


@pytest.fixture
def harness(monkeypatch, tmp_path):
    """Stub the database touchpoints of run_migration; keep the real backup writer."""
    calls = {"writes": 0, "index_created": 0}
    state = {
        "index": {},
        "plan": [{"_id": "a" * 24, "name": "A", "slug": "a"}],
        "backup_records": [{"_id": "a" * 24, "name": "A", "slug": None,
                            "slug_field_present": True, "legacySlugs_field_present": False, "assigned_slug": "a"}],
        # Round 3 (P2): the public-slug check runs before any write. The plan
        # plus the untouched categories must satisfy all nine EXPECTED_SLUGS.
        "public_rows": [{"_id": f"{i:024x}", "name": n, "slug": slug}
                        for i, (n, slug) in enumerate(zip(_NINE_NAMES, _NINE_SLUGS), start=1)],
        "dupes": [],
        "stats": {"updated": 1, "conflicts": []},
        "remaining_null": 0,
        "index_error": None,
    }

    async def fake_verify_slug_index(db, create):
        if state["index"]:
            return {"exists": True, "action": "verified"}
        return {"exists": False, "action": "missing (dry-run: --apply would create it)"}

    async def fake_build_slug_plan(db):
        return list(state["plan"]), list(state["backup_records"])

    async def fake_dupes(db):
        return list(state["dupes"])

    async def fake_apply(db, plan):
        calls["writes"] += 1
        return state["stats"]

    async def fake_guarded(db, backup_path, backfilled, conflicts=0):
        calls["index_created"] += 1
        if state["index_error"]:
            raise MigrationBlocked(state["index_error"])
        state["index"] = {"exists": True}
        return {"exists": False, "action": "created (apply mode)"}

    monkeypatch.setenv("MONGO_URL", "mongodb://127.0.0.1:1/unused-by-stub")
    monkeypatch.setenv("DB_NAME", "midconnect_phase1_test_stub")
    # Round 3: the stub target must be explicitly approved to pass the gate.
    monkeypatch.setattr(v20, "APPROVED_TARGETS",
                        frozenset({("127.0.0.1", 1, "midconnect_phase1_test_stub")}))
    monkeypatch.setattr(v20, "AsyncIOMotorClient", lambda *_a, **_k: _FakeClient(state))
    monkeypatch.setattr(v20, "verify_slug_index", fake_verify_slug_index)
    monkeypatch.setattr(v20, "build_slug_plan", fake_build_slug_plan)
    monkeypatch.setattr(v20, "find_preexisting_slug_duplicates", fake_dupes)
    monkeypatch.setattr(v20, "apply_slug_writes", fake_apply)
    monkeypatch.setattr(v20, "create_slug_index_guarded", fake_guarded)
    monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
    return state, calls


def _run(apply=True):
    return asyncio.run(v20.run_migration(
        apply=apply, confirm_db="midconnect_phase1_test_stub" if apply else None))


# ---------------- exit 0 ----------------

def test_successful_migration_exits_0(harness):
    state, calls = harness
    assert _run(apply=True) == EXIT_OK
    assert calls["writes"] == 1
    assert calls["index_created"] == 1


def test_existing_compatible_index_with_empty_plan_exits_0(harness):
    state, calls = harness
    state["index"] = {"exists": True}
    state["plan"] = []
    state["backup_records"] = []
    assert _run(apply=True) == EXIT_OK
    assert calls["writes"] == 0, "an empty plan performs no slug writes"
    assert calls["index_created"] == 0, "an existing compatible index is not recreated"


# ---------------- exit 2: blocked before mutation ----------------

def test_invalid_existing_slug_exits_2(harness, monkeypatch):
    state, calls = harness

    async def invalid_plan(db):
        raise v20.InvalidExistingSlugs("FAIL-CLOSED (F2): invalid slug")

    monkeypatch.setattr(v20, "build_slug_plan", invalid_plan)
    assert _run(apply=True) == 2
    assert calls["writes"] == 0


def test_duplicate_existing_slug_exits_2(harness):
    state, calls = harness
    state["dupes"] = [{"slug": "dup", "count": 2, "ids": ["x", "y"], "names": ["X", "Y"]}]
    assert _run(apply=True) == 2
    assert calls["writes"] == 0


def test_backup_creation_failure_exits_2(harness, monkeypatch):
    """The REAL writer hits an OSError opening the backup file: exit 2, no writes."""
    state, calls = harness

    def failing_open():
        raise OSError("disk full")

    monkeypatch.setattr(v20, "_open_backup_file_exclusively", failing_open)
    assert _run(apply=True) == 2
    assert calls["writes"] == 0, "no write may happen without a validated backup"


def test_backup_validation_failure_exits_2(harness, monkeypatch):
    """The REAL writer reads back a file that differs from what it wrote:
    the on-disk backup is altered between write and read-back."""
    state, calls = harness
    import io
    real_open = open

    def tamper_on_readback(path, mode="r", *a, **k):
        # Only the validation read-back of the backup file is redirected, to a
        # VALID but different JSON document: only the equality check rejects it.
        if str(path).endswith(".json") and mode == "r":
            return io.StringIO(json.dumps([{"_id": "tampered"}]))
        return real_open(path, mode, *a, **k)

    monkeypatch.setattr(v20, "open", tamper_on_readback, raising=False)
    assert _run(apply=True) == 2
    assert calls["writes"] == 0


def test_main_maps_migration_blocked_to_exit_2(monkeypatch):
    async def fake_run(apply, rollback_path=None, **_kwargs):
        raise MigrationBlocked("blocked before mutation")
    monkeypatch.setattr(v20, "run_migration", fake_run)
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--apply", "--confirm-apply", "midconnect_phase1_test_stub"])
    assert v20.main() == 2


# ---------------- exit 3: partial or incomplete ----------------

def test_partial_backfill_with_conflicts_exits_3(harness):
    state, calls = harness
    state["stats"] = {"updated": 0, "conflicts": [{
        "_id": "a", "name": "A", "current_slug": "x", "planned_slug": "a",
        "reason": "slug populated after the plan was generated"}]}
    assert _run(apply=True) == EXIT_INCOMPLETE


def test_concurrent_unresolved_conflicts_defer_index_exit_3(harness):
    state, calls = harness
    state["stats"] = {"updated": 0, "conflicts": [{
        "_id": "a", "name": "A", "current_slug": "x", "planned_slug": "a",
        "reason": "slug populated after the plan was generated"}]}
    state["remaining_null"] = 1
    assert _run(apply=True) == EXIT_INCOMPLETE
    assert calls["index_created"] == 0, "the index is deferred while nulls remain"


def test_index_creation_failure_after_backfill_exits_3(harness):
    state, calls = harness
    state["index_error"] = "FAIL-CLOSED (F1): duplicate key raced"
    assert _run(apply=True) == EXIT_INCOMPLETE
    assert calls["writes"] == 1, "backfill happened before the index failure"


def test_backfill_write_failure_exits_3(harness, monkeypatch):
    state, calls = harness

    async def failing_apply(db, plan):
        raise PyMongoError("connection dropped mid-backfill")

    monkeypatch.setattr(v20, "apply_slug_writes", failing_apply)
    assert _run(apply=True) == EXIT_INCOMPLETE


# ---------------- main() preserves every code ----------------

@pytest.mark.parametrize("code", [EXIT_OK, 2, EXIT_INCOMPLETE])
def test_main_returns_run_migration_code_unchanged(monkeypatch, code):
    async def fake_run(apply, rollback_path=None, **_kwargs):
        return code
    monkeypatch.setattr(v20, "run_migration", fake_run)
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--apply", "--confirm-apply", "midconnect_phase1_test_stub"])
    assert v20.main() == code


def test_main_rollback_missing_backup_argument_exits_2(monkeypatch):
    monkeypatch.setattr(v20.sys, "argv", ["V20.py", "--rollback"])
    assert v20.main() == 2


def test_duplicate_existing_slug_dry_run_exits_2_without_writes(harness):
    """Exit-code contract applies in dry-run too: duplicates report exit 2,
    and no backup, backfill or index write happens."""
    state, calls = harness
    state["dupes"] = [{"slug": "dup", "count": 2, "ids": ["x", "y"], "names": ["X", "Y"]}]
    assert _run(apply=False) == 2
    assert calls["writes"] == 0
    assert calls["index_created"] == 0
