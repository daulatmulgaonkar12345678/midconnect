"""
Batch 6 — deterministic category slug resolution regression.

Covers the Batch 6 category URL integrity changes at baseline 09bc2fc+:

1. resolve_category_slug is deterministic (exact slug, case-normalized slug,
   ObjectId, explicit legacySlugs/legacyIds) — the legacy ANY-token regex
   matching over slug/name is gone, so arbitrary invalid slugs return None
   (and the enterprise endpoint answers 404 instead of an unrelated category).
2. The enterprise resolve endpoint never advertises a redirect to a null
   target: an ObjectId of a category whose slug is still null returns
   redirect.needed = false (previously {"needed": true, "canonicalSlug": null}).
3. The V20 migration helpers: deterministic slugify, collision suffixing,
   ObjectId-like slug guard (owner revision 6), dry-run default.
4. Admin rename preserves the previous slug in legacySlugs and moves the
   canonical slug to the new name-derived slug (owner revision 4) — the
   server-side rename block is pinned structurally because require_admin
   cannot be exercised without admin credentials.

Boots the REAL FastAPI app as a uvicorn subprocess against the disposable
MongoDB (PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME; skips when unset) —
same harness rationale as test_slug_resolver_deterministic.py.

Each test uses a unique tag and deletes only the documents it inserted.
"""
import asyncio
import os
import re
import socket
import subprocess
import sys
import time
import uuid

import pytest
from bson import ObjectId

import os as _os
import sys as _sys

_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
_sys.path.insert(0, _BACKEND)
_sys.path.insert(0, _os.path.join(_BACKEND, "tests"))
from phase1_db_guard import validate_test_target

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def base_url():
    """Boot server.py as a uvicorn subprocess on the disposable DB."""
    validate_test_target(URL, DB_NAME)
    port = _free_port()
    env = dict(os.environ)
    env["MONGO_URL"] = URL
    env["DB_NAME"] = DB_NAME
    env["ENVIRONMENT"] = "test"
    err_path = os.path.join(os.environ.get("TEMP", "."), "midconnect-b6-uvicorn.err.log")
    with open(err_path, "w", encoding="utf-8") as err_file:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=_BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=err_file,
        )
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 45
        last_error = None
        try:
            import requests
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"uvicorn exited early with code {proc.returncode}; "
                        f"see {err_path}"
                    )
                try:
                    r = requests.get(f"{base}/api/health", timeout=2)
                    if r.status_code == 200:
                        last_error = None
                        break
                except requests.RequestException as exc:
                    last_error = exc
                time.sleep(0.5)
            if last_error is not None:
                raise RuntimeError(
                    f"uvicorn did not become healthy within 45s: {last_error}; "
                    f"see {err_path}"
                )
            yield base
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def seeded(base_url):
    """One category with a slug, one without (slug=None, like production today)."""
    tag = "b6cat-" + uuid.uuid4().hex[:8]
    slug = f"{tag}-safety-products"
    legacy_slug = f"{tag}-safety-gear-old"
    legacy_id = str(ObjectId())
    oid_null = ObjectId()

    docs = [
        {
            "_id": ObjectId(),
            "tag": tag,
            "name": f"Safety Products {tag}",
            "slug": slug,
            "isActive": True,
            "legacySlugs": [legacy_slug],
            "legacyIds": [legacy_id],
        },
        {
            "_id": oid_null,
            "tag": tag,
            "name": f"Cleaning products {tag}",
            "slug": None,
            "isActive": True,
        },
    ]

    async def seed():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].categories.insert_many(docs)
        finally:
            c.close()

    async def cleanup():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].categories.delete_many({"tag": tag})
        finally:
            c.close()

    _run(seed())
    try:
        yield {
            "tag": tag,
            "slug": slug,
            "legacy_slug": legacy_slug,
            "legacy_id": legacy_id,
            "null_oid": str(oid_null),
            "null_name": f"Cleaning products {tag}",
        }
    finally:
        _run(cleanup())


# ------------------- service level: deterministic resolver -------------------

def test_category_exact_slug_no_redirect(seeded):
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            return await resolver.resolve_category_slug(seeded["slug"])
        finally:
            c.close()

    category, needs_redirect, canonical = _run(go())
    assert category is not None
    assert needs_redirect is False
    assert canonical == seeded["slug"]


def test_category_case_normalized_slug_redirects(seeded):
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            return await resolver.resolve_category_slug(seeded["slug"].upper())
        finally:
            c.close()

    category, needs_redirect, canonical = _run(go())
    assert category is not None
    assert needs_redirect is True
    assert canonical == seeded["slug"]


def test_category_objectid_redirects_to_slug(seeded):
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            doc = await c[DB_NAME].categories.find_one({"slug": seeded["slug"]}, {"_id": 1})
            return await resolver.resolve_category_slug(str(doc["_id"]))
        finally:
            c.close()

    category, needs_redirect, canonical = _run(go())
    assert category is not None
    assert needs_redirect is True
    assert canonical == seeded["slug"]


def test_category_objectid_with_null_slug_has_no_redirect_target(seeded):
    """ObjectId resolves the category but slug is null: needs_redirect stays
    True with a None target at resolver level; the ENDPOINT must suppress it."""
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            return await resolver.resolve_category_slug(seeded["null_oid"])
        finally:
            c.close()

    category, needs_redirect, canonical = _run(go())
    assert category is not None
    assert canonical is None


def test_category_legacy_slug_and_id_redirect(seeded):
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            by_slug = await resolver.resolve_category_slug(seeded["legacy_slug"])
            by_id = await resolver.resolve_category_slug(seeded["legacy_id"])
            return by_slug, by_id
        finally:
            c.close()

    (c_slug, r_slug, t_slug), (c_id, r_id, t_id) = _run(go())
    assert c_slug is not None and r_slug is True and t_slug == seeded["slug"]
    assert c_id is not None and r_id is True and t_id == seeded["slug"]


def test_category_invalid_tokeny_slugs_resolve_to_none(seeded):
    """Batch 6 core assertion: no ANY-token fallback. Tokens from one category
    must never surface the other category (the exact defect reported in
    production: arbitrary slugs rendered unrelated category content)."""
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            results = {}
            for bad in (
                "safety",                       # token of the slug category
                "cleaning-products",            # token of the null-slug category
                f"{seeded['tag']}-safety",      # partial slug
                "xyzzy-plugh-zorkmidconnect-42",
            ):
                results[bad] = await resolver.resolve_category_slug(bad)
            return results
        finally:
            c.close()

    results = _run(go())
    for bad, (category, _, _) in results.items():
        assert category is None, f"invalid category slug resolved: {bad}"


# ------------------- HTTP level: enterprise resolve endpoint -------------------

def test_resolve_endpoint_contract(base_url, seeded):
    import requests
    base = base_url

    # Canonical slug: 200, redirect not needed.
    r = requests.get(f"{base}/api/enterprise/resolve/category/{seeded['slug']}", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"]["slug"] == seeded["slug"]
    assert body["redirect"]["needed"] is False
    assert body["redirect"]["canonicalUrl"].endswith(f"/categories/{seeded['slug']}")

    # ObjectId of a slug-bearing category: redirect needed with a concrete slug.
    r2 = requests.get(f"{base}/api/enterprise/resolve/category/{seeded['legacy_id']}", timeout=30)
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert b2["redirect"]["needed"] is True
    assert b2["redirect"]["canonicalSlug"] == seeded["slug"]

    # ObjectId of a NULL-slug category: resolved, but redirect must NOT be
    # advertised with a null target (Batch 6 bug fix, revision 3 safety).
    r3 = requests.get(f"{base}/api/enterprise/resolve/category/{seeded['null_oid']}", timeout=30)
    assert r3.status_code == 200, r3.text
    b3 = r3.json()
    assert b3["category"]["_id"] == seeded["null_oid"]
    assert b3["category"]["name"] == seeded["null_name"]
    assert b3["redirect"]["needed"] is False, b3["redirect"]
    assert b3["redirect"]["canonicalSlug"] is None
    assert b3["redirect"]["canonicalUrl"] is None

    # Invalid slug: deterministic 404 (previously an unrelated category).
    r4 = requests.get(f"{base}/api/enterprise/resolve/category/xyzzy-plugh-zorkmidconnect-42", timeout=30)
    assert r4.status_code == 404


# ------------------- V20 migration helpers (no DB writes) -------------------

def test_v20_slugify_matches_hosted_sitemap_slugs():
    from migrations.V20_backfill_category_slugs import slugify
    expected = {
        "Cleaning products": "cleaning-products",
        "Electrical Equipment & Supplies": "electrical-equipment-supplies",
        "Electronics, IT & Industrial Automation": "electronics-it-industrial-automation",
        "Lights & Lighting Accessories": "lights-lighting-accessories",
        "Metals & Industrial Raw Materials": "metals-industrial-raw-materials",
        "Panel Meters And Accessories": "panel-meters-and-accessories",
        "Safety Products": "safety-products",
        "Solar Equipment & Panels": "solar-equipment-panels",
        "VFD, PLC, HMI & Control Equipments": "vfd-plc-hmi-control-equipments",
    }
    for name, slug in expected.items():
        assert slugify(name) == slug, f"{name!r} -> {slugify(name)} (want {slug})"


def test_v20_objectid_like_slug_guard():
    from migrations.V20_backfill_category_slugs import is_objectid_like, generate_unique_slug
    assert is_objectid_like("6a44b3e38b430643bfad186e")
    assert not is_objectid_like("cleaning-products")
    # A 24-hex-looking name never yields an ObjectId-like slug (revision 6).
    taken = set()
    slug = generate_unique_slug("6a44b3e38b430643bfad186e", taken, "0123456789abcdef01234567")
    assert not is_objectid_like(slug)


def test_v20_collision_suffix_is_deterministic():
    from migrations.V20_backfill_category_slugs import generate_unique_slug
    # Caller contract (mirrors run_migration): each assigned slug is added to
    # `taken` before the next category is processed.
    taken = set()
    first = generate_unique_slug("Safety Products", taken, "aa")
    taken.add(first)
    second = generate_unique_slug("Safety Products", taken, "bb")
    taken.add(second)
    third = generate_unique_slug("Safety Products", taken, "cc")
    assert first == "safety-products"
    assert second == "safety-products-2"
    assert third == "safety-products-3"
    # Same inputs, same outputs (determinism across runs).
    again = []
    t2 = set()
    for doc_id in ("aa", "bb", "cc"):
        slug = generate_unique_slug("Safety Products", t2, doc_id)
        t2.add(slug)
        again.append(slug)
    assert again == [first, second, third]


def test_v20_defaults_to_dry_run(monkeypatch, tmp_path):
    """Revision 2: without --apply, main() must not write."""
    import migrations.V20_backfill_category_slugs as v20

    applied = {"value": None}

    async def fake_run(apply, rollback_path=None):
        applied["value"] = apply
        return 0

    monkeypatch.setattr(v20, "run_migration", fake_run)
    monkeypatch.setattr(v20.sys, "argv", ["V20_backfill_category_slugs.py"])
    v20.main()
    assert applied["value"] is False

    monkeypatch.setattr(v20.sys, "argv", ["V20_backfill_category_slugs.py", "--apply"])
    v20.main()
    assert applied["value"] is True


# ------------------- admin rename: legacySlugs preservation -------------------

def test_admin_rename_preserves_old_slug_as_legacy_mapping():
    """Owner revision 4. The admin PATCH handler requires admin credentials and
    cannot be exercised over HTTP here; the rename block is pinned
    structurally instead (same convention as page/layout pins in the
    frontend seo harness)."""
    import re
    src = open(os.path.join(_BACKEND, "server.py"), encoding="utf-8").read()

    # Rename only fires when the name actually changes.
    m = re.search(
        r'if updates\.name is not None and updates\.name != existing\.get\("name"\):',
        src,
    )
    assert m, "admin PATCH rename must compare against the existing name"

    # The old canonical slug is preserved (never destroyed) ...
    assert re.search(
        r'rename_update\["\$addToSet"\] = \{"legacySlugs": renamed_from_slug\}',
        src,
    ), "rename must add the old slug to legacySlugs, composed into the atomic update"

    # ... and the canonical slug moves to the new name-derived slug (with the
    # collision probe excluding the renamed category itself — correction 2).
    assert re.search(
        r'renamed_from_slug = existing\.get\("slug"\)',
        src,
    ), "rename must track the previous canonical slug"
    assert re.search(
        r'new_slug = await _generate_unique_category_slug\(\s*'
        r'updates\.name, ObjectId\(category_id\), exclude_id=ObjectId\(category_id\)\s*\)',
        src,
    ), "rename must re-derive the canonical slug excluding the renamed category"
    assert 'renamed_from_slug = None  # Batch 6: set when a rename moves the canonical slug' in src

    # Batch 6 final review (correction 5): the canonical slug change and the
    # legacy mapping are ONE atomic MongoDB update — $set and $addToSet are
    # composed into a single update document carried by exactly one
    # update_one call, so no partial rename state (new slug without its
    # legacy mapping, or the reverse) can ever be observed.
    patch_start = src.index("async def admin_update_category")
    patch_block = src[patch_start:src.index("# ============== SECURE IMAGE UPLOAD ENDPOINTS", patch_start)]
    assert re.search(
        r'rename_update\["\$addToSet"\] = \{"legacySlugs": renamed_from_slug\}',
        patch_block,
    ), "the legacy mapping must be composed into the same update document as $set"
    assert re.search(
        r'await db\.categories\.update_one\(\{"_id": ObjectId\(category_id\)\}, rename_update\)',
        patch_block,
    ), "one atomic update_one must carry the whole rename"
    assert patch_block.count("db.categories.update_one") == 1, (
        "a separate legacySlugs update may not remain (correction 5: atomic rename)"
    )


def test_admin_create_assigns_slug():
    import re
    src = open(os.path.join(_BACKEND, "server.py"), encoding="utf-8").read()
    # Category creation assigns a slug at insert time (no more slug=null rows).
    create_block = src[src.index('async def admin_create_category'):]
    create_block = create_block[:create_block.index('async def admin_update_category')]
    assert '"slug": assigned_slug' in create_block
    assert re.search(
        r'_generate_unique_category_slug\(category\.name, category_oid\)',
        create_block,
    ), "create must derive the slug with the document's own ObjectId in hand"
    assert '"_id": category_oid' in create_block


# ------------------- Batch 6 final remediation: corrections 1-3 (server.py) -------------------

def test_server_slug_fallback_is_deterministic_id_based_not_uuid():
    """Correction 1: the empty/ObjectId-like slug fallback derives from the
    category's own ObjectId, never from a random UUID."""
    src = open(os.path.join(_BACKEND, "server.py"), encoding="utf-8").read()
    fn_start = src.index("async def _generate_unique_category_slug(")
    fn_src = src[fn_start:src.index("@api_router.post", fn_start)]
    assert "uuid.uuid4" not in fn_src, "category slug fallback must not use a random UUID"
    assert 'f"category-{str(doc_id)[-8:]}"' in fn_src
    assert "doc_id: ObjectId" in fn_src


def test_server_rename_collision_check_excludes_the_renamed_category():
    """Correction 2: the uniqueness probe supports excluding a document, and
    the rename path excludes the category currently being renamed."""
    src = open(os.path.join(_BACKEND, "server.py"), encoding="utf-8").read()
    assert 'collision_query["_id"] = {"$ne": exclude_id}' in src
    assert re.search(
        r'new_slug = await _generate_unique_category_slug\(\s*'
        r'updates\.name, ObjectId\(category_id\), exclude_id=ObjectId\(category_id\)\s*\)',
        src,
    )


def test_server_handles_unique_index_collisions_on_create_and_rename():
    """Correction 3: a DuplicateKeyError from the unique slug index is
    answered with a deterministic retry (create) or HTTP 409
    (create/rename) — never an unhandled 500."""
    src = open(os.path.join(_BACKEND, "server.py"), encoding="utf-8").read()
    assert "from pymongo.errors import DuplicateKeyError" in src
    create_block = src[src.index("async def admin_create_category"):]
    create_block = create_block[:create_block.index("async def admin_update_category")]
    assert "except DuplicateKeyError:" in create_block, "create must survive a unique-index race"
    patch_start = src.index("async def admin_update_category")
    patch_block = src[patch_start:src.index("# ============== SECURE IMAGE UPLOAD ENDPOINTS", patch_start)]
    assert "except DuplicateKeyError:" in patch_block, "rename must answer a unique-index race with 409"
    assert 'status_code=409, detail="Category slug conflict; please retry"' in src


# ------------------- resolver identifier normalization (correction 6) -------------------

def test_category_identifier_is_trimmed_and_case_normalized(seeded):
    """Correction 6: surrounding whitespace is stripped and noncanonical
    casing resolves to the canonical slug with needs_redirect=True."""
    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            resolver = create_slug_resolver(c[DB_NAME])
            return await resolver.resolve_category_slug(f"  {seeded['slug'].upper()}  ")
        finally:
            c.close()

    category, needs_redirect, canonical = _run(go())
    assert category is not None
    assert needs_redirect is True
    assert canonical == seeded["slug"]


# ------------------- V20: corrections 8, 9, 10 (real disposable DB) -------------------


def test_v20_build_slug_plan_processes_full_collection_without_cap():
    """Correction 8: 1010 newly inserted uncapped categories are ALL planned
    (the old implementation stopped at 1000 documents), in stable _id order."""
    from migrations.V20_backfill_category_slugs import build_slug_plan
    tag = "b6v20cap-" + uuid.uuid4().hex[:8]

    async def go():
        # One event loop per test: client is created and closed inside the
        # same asyncio.run (motor must not cross loops on Windows).
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            pre = await db.categories.count_documents({"slug": None})
            docs = [
                {"_id": ObjectId(), "tag": tag, "name": f"Cap Batch {i:04d}", "isActive": True}
                for i in range(1010)
            ]
            await db.categories.insert_many(docs)
            plan, backup_records = await build_slug_plan(db)
            return pre, plan, backup_records, {str(d["_id"]) for d in docs}
        finally:
            await db.categories.delete_many({"tag": tag})
            client.close()

    pre, plan, backup_records, tagged_ids = _run(go())

    assert len(plan) >= 1010
    assert len(plan) == pre + 1010, "every uncapped category must be planned"
    assert tagged_ids <= {p["_id"] for p in plan}
    assert plan == sorted(plan, key=lambda p: p["_id"]), "plan must follow stable _id order"
    tagged_records = [r for r in backup_records if r["_id"] in tagged_ids]
    assert len(tagged_records) == 1010
    assert all(r["slug_field_present"] is False and r["slug"] is None for r in tagged_records)


def test_v20_verify_slug_index_fails_closed_on_malformed_index():
    """Correction 9: an existing index under the V20 name with the wrong
    definition aborts BEFORE any data write."""
    from migrations.V20_backfill_category_slugs import INDEX_NAME, MigrationBlocked, verify_slug_index

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        raised = None
        try:
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            # Wrong key AND non-sparse: incompatible with the V20 index contract.
            await db.categories.create_index([("name", 1)], name=INDEX_NAME)
            try:
                await verify_slug_index(db, create=True)
            except MigrationBlocked as exc:
                raised = exc
            return raised
        finally:
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            client.close()

    raised = _run(go())
    assert raised is not None, "a malformed index must raise MigrationBlocked"
    assert "FAIL-CLOSED" in str(raised)


def test_v20_rollback_restores_exact_slug_field_state(tmp_path):
    """Correction 10: field-absent docs are restored to field-ABSENT ($unset,
    not an injected null); slug=null docs are restored to null; the assigned
    slugs survive in legacySlugs; pre-existing legacy data is untouched."""
    import json as _json
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20rb-" + uuid.uuid4().hex[:8]
    absent_id, null_id = ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            # Order-independence: this rollback targets a collection WITHOUT
            # the unique index (correction 3 covers index-aware rollbacks);
            # drop any index another test may have left behind.
            from migrations.V20_backfill_category_slugs import INDEX_NAME as _IDX
            try:
                await db.categories.drop_index(_IDX)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": absent_id, "tag": tag, "name": "Rollback Absent", "isActive": True,
                 "legacySlugs": ["pre-existing-legacy"]},
                {"_id": null_id, "tag": tag, "name": "Rollback Null", "slug": None,
                 "isActive": True},
            ])
            # Simulate exactly what the migration applied ($set slug only).
            await db.categories.update_one({"_id": absent_id}, {"$set": {"slug": "rollback-absent"}})
            await db.categories.update_one({"_id": null_id}, {"$set": {"slug": "rollback-null"}})
            backup = [
                {"_id": str(absent_id), "name": "Rollback Absent", "slug": None,
                 "slug_field_present": False, "assigned_slug": "rollback-absent"},
                {"_id": str(null_id), "name": "Rollback Null", "slug": None,
                 "slug_field_present": True, "assigned_slug": "rollback-null"},
            ]
            backup_path = tmp_path / "v20_rollback_test.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            absent = await db.categories.find_one({"_id": absent_id})
            nulled = await db.categories.find_one({"_id": null_id})
            return rc, absent, nulled
        finally:
            await db.categories.delete_many({"tag": tag})
            client.close()

    rc, absent, nulled = _run(go())
    assert rc == 0
    assert "slug" not in absent, "field-absent category must be restored to field-ABSENT"
    assert nulled["slug"] is None, "slug=null category must be restored to null"
    assert "rollback-absent" in absent.get("legacySlugs", [])
    assert "pre-existing-legacy" in absent.get("legacySlugs", [])
    assert "rollback-null" in nulled.get("legacySlugs", [])


# ------------------- V20 safety blockers 1-4 (Batch 6, 2026-11-20) -------------------


def test_v20_apply_backup_writes_then_index_creation(tmp_path, monkeypatch):
    """Blockers 1 & 2: the backup is written and validated BEFORE any database
    mutation, and the unique sparse index is created LAST.

    Two documents hold slug=null. A unique sparse index still INDEXES explicit
    nulls, so if V20 created the index before backfilling (or before the
    backup), create_index would fail with E11000 and the run would crash
    before producing slugs. A successful run with an existing index, a valid
    backup containing the exact pre-migration states, and all slugs assigned
    proves the order: backup -> writes -> index.
    """
    import glob as _glob
    import migrations.V20_backfill_category_slugs as v20
    tag = "b6v20order-" + uuid.uuid4().hex[:8]
    ids = [ObjectId() for _ in range(3)]

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": ids[0], "tag": tag, "name": f"Order Alpha {tag}", "slug": None},
                {"_id": ids[1], "tag": tag, "name": f"Order Beta {tag}", "slug": None},
                {"_id": ids[2], "tag": tag, "name": f"Order Gamma {tag}"},  # field absent
            ])
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", DB_NAME)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
            rc = await v20.run_migration(apply=True)
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            backup_files = _glob.glob(str(tmp_path / "*.json"))
            return rc, indexes, docs, backup_files
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    rc, indexes, docs, backup_files = _run(go())

    assert rc == 0
    assert v20.INDEX_NAME in indexes, "index must exist after a clean apply run"
    assert indexes[v20.INDEX_NAME].get("unique") and indexes[v20.INDEX_NAME].get("sparse")
    assert len(backup_files) == 1, "exactly one validated backup must be written"
    import json as _json
    backup = _json.loads(open(backup_files[0], encoding="utf-8").read())
    # Final-review correction 3: the backup leads with a _meta record holding
    # the index provenance — V20 created this index (it was missing before).
    assert backup[0]["_meta"]["index_name"] == v20.INDEX_NAME
    assert backup[0]["_meta"]["index_created_by_v20"] is True
    assert backup[0]["_meta"]["index_existed_before_v20"] is False
    tagged = [r for r in backup if isinstance(r, dict) and r.get("_id") in {str(i) for i in ids}]
    assert len(tagged) == 3
    for rec in tagged:
        assert rec["assigned_slug"], "backup must record the slug V20 assigned"
        assert rec["slug"] is None  # pre-migration state
    slugs = sorted(d["slug"] for d in docs)
    assert len(set(slugs)) == 3, "all planned documents got distinct slugs"
    assert None not in slugs and "" not in slugs


def test_v20_apply_conflicts_reported_and_index_deferred(tmp_path, monkeypatch):
    """Blocker 3 (run level): a concurrent slug population after plan
    generation is reported as a conflict, the concurrent value wins, and the
    unique index is DEFERRED (not created over remaining nulls)."""
    import migrations.V20_backfill_category_slugs as v20
    tag = "b6v20conf-" + uuid.uuid4().hex[:8]
    doc_id = ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_one(
                {"_id": doc_id, "tag": tag, "name": f"Conflict Cat {tag}", "slug": None}
            )
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", DB_NAME)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))

            async def conflicting_writes(_db, _plan):
                # Simulate: every guarded write was lost to a concurrent write
                # that populated the slug after the plan was generated.
                return {"updated": 0, "conflicts": [{
                    "_id": str(doc_id), "name": f"Conflict Cat {tag}",
                    "current_slug": "concurrent-slug",
                    "planned_slug": "conflict-cat-planned",
                    "reason": "slug populated after the plan was generated",
                }]}

            monkeypatch.setattr(v20, "apply_slug_writes", conflicting_writes)
            rc = await v20.run_migration(apply=True)
            indexes = await db.categories.index_information()
            doc = await db.categories.find_one({"_id": doc_id})
            return rc, indexes, doc
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    rc, indexes, doc = _run(go())
    assert rc == 3, "skipped conflicts + deferred index are INCOMPLETE (exit 3), not success"
    assert doc["slug"] is None, "conflicting document must be left untouched by this run"
    assert v20.INDEX_NAME not in indexes, (
        "index creation must be DEFERRED while documents still hold null slugs"
    )


def test_v20_conditional_write_never_overwrites_concurrent_slug():
    """Blocker 3 (helper level): apply_slug_writes matches only documents whose
    slug is still missing/null/empty; a slug populated after plan generation
    is reported as a conflict and never overwritten."""
    from migrations.V20_backfill_category_slugs import apply_slug_writes
    tag = "b6v20cond-" + uuid.uuid4().hex[:8]
    concurrent_id, absent_id = ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            await db.categories.insert_many([
                {"_id": concurrent_id, "tag": tag, "name": "Concurrent Doc", "slug": None},
                {"_id": absent_id, "tag": tag, "name": "Absent Doc"},  # field missing
            ])
            # Concurrent write AFTER the plan was generated:
            await db.categories.update_one(
                {"_id": concurrent_id}, {"$set": {"slug": f"{tag}-concurrent"}}
            )
            plan = [
                {"_id": str(concurrent_id), "name": "Concurrent Doc",
                 "slug": f"{tag}-planned-wrong"},
                {"_id": str(absent_id), "name": "Absent Doc", "slug": f"{tag}-absent"},
            ]
            stats = await apply_slug_writes(db, plan)
            concurrent = await db.categories.find_one({"_id": concurrent_id})
            absent = await db.categories.find_one({"_id": absent_id})
            return stats, concurrent, absent
        finally:
            await db.categories.delete_many({"tag": tag})
            client.close()

    stats, concurrent, absent = _run(go())
    assert stats["updated"] == 1
    assert len(stats["conflicts"]) == 1
    conflict = stats["conflicts"][0]
    assert conflict["_id"] == str(concurrent_id)
    assert conflict["current_slug"] == f"{tag}-concurrent"
    assert conflict["planned_slug"] == f"{tag}-planned-wrong"
    assert concurrent["slug"] == f"{tag}-concurrent", (
        "the concurrent slug must win; the planned slug must never overwrite it"
    )
    assert absent["slug"] == f"{tag}-absent", "still-null/missing docs are planned"


def test_v20_rollback_skips_slug_changed_after_v20(tmp_path):
    """Blocker 4 + finding 1 (HIGH): a slug changed after V20 is a BLOCKING
    rollback conflict. The preflight detects it BEFORE any mutation and aborts
    the WHOLE rollback: the changed slug is never overwritten, the
    still-matching sibling document is NOT restored either, and no
    legacySlugs is polluted."""
    import json as _json
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20rbconf-" + uuid.uuid4().hex[:8]
    conflict_id, ok_id = ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            # This scenario restores TWO null slugs, which is only legal
            # without the unique sparse index (correction 3 fail-closed path
            # covers the index-present case); drop any index another test
            # may have left behind.
            from migrations.V20_backfill_category_slugs import INDEX_NAME as _IDX2
            try:
                await db.categories.drop_index(_IDX2)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": conflict_id, "tag": tag, "name": "Rollback Conflict",
                 "slug": None, "isActive": True},
                {"_id": ok_id, "tag": tag, "name": "Rollback Untouched", "slug": None,
                 "isActive": True},
            ])
            # Simulate what V20 applied: slug = assigned slug.
            await db.categories.update_one(
                {"_id": conflict_id}, {"$set": {"slug": "v20-assigned"}}
            )
            await db.categories.update_one(
                {"_id": ok_id}, {"$set": {"slug": "v20-assigned-ok"}}
            )
            # AFTER V20: an operator renames the conflicting category.
            await db.categories.update_one(
                {"_id": conflict_id}, {"$set": {"slug": "changed-after-v20"}}
            )
            backup = [
                {"_id": str(conflict_id), "name": "Rollback Conflict", "slug": None,
                 "slug_field_present": True, "assigned_slug": "v20-assigned"},
                {"_id": str(ok_id), "name": "Rollback Untouched", "slug": None,
                 "slug_field_present": True, "assigned_slug": "v20-assigned-ok"},
            ]
            backup_path = tmp_path / "v20_rollback_conflict.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            conflict = await db.categories.find_one({"_id": conflict_id})
            ok = await db.categories.find_one({"_id": ok_id})
            return rc, conflict, ok
        finally:
            await db.categories.delete_many({"tag": tag})
            client.close()

    rc, conflict, ok = _run(go())
    assert rc == 2, "a document rollback conflict must abort the rollback (finding 1)"
    assert conflict["slug"] == "changed-after-v20", (
        "rollback must NOT overwrite a slug changed after V20"
    )
    assert "v20-assigned" not in (conflict.get("legacySlugs") or []), (
        "an aborted rollback must not pollute legacySlugs"
    )
    assert ok["slug"] == "v20-assigned-ok", (
        "finding 1: preflight failure aborts the WHOLE rollback — no document, "
        "not even a still-matching one, is modified"
    )
    assert "v20-assigned-ok" not in (ok.get("legacySlugs") or []), (
        "an aborted rollback must not partially restore any document"
    )


# ------------------- Batch 6 final review corrections 2-4 & 6 (2026-11-20) -------------------


def test_v20_rollback_write_is_conditional_on_assigned_slug_at_write_time(tmp_path):
    """Final-review correction 2: the restoration update is conditional AT THE
    MOMENT OF THE WRITE — its filter matches only slug == assigned_slug. A
    concurrent change landing between the verification read and the rollback
    write makes the filter match nothing: the concurrent value is never
    overwritten, the conflict is reported, legacySlugs is not polluted, and
    unrelated documents in the same backup are still restored."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20toctou-" + uuid.uuid4().hex[:8]
    race_id, ok_id = ObjectId(), ObjectId()
    race_slug = "v20-assigned-race"

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": race_id, "tag": tag, "name": "TOCTOU Race", "slug": None,
                 "isActive": True},
                {"_id": ok_id, "tag": tag, "name": "TOCTOU Untouched", "slug": None,
                 "isActive": True},
            ])
            await db.categories.update_one(
                {"_id": race_id}, {"$set": {"slug": race_slug}}
            )
            await db.categories.update_one(
                {"_id": ok_id}, {"$set": {"slug": "v20-assigned-ok"}}
            )

            class RacingCategories:
                """Proxies the real collection: the moment do_rollback issues
                the guarded restore write for the raced document, a concurrent
                rename lands first — exactly the read/write interleaving the
                correction-2 guard must survive."""

                def __init__(self, real):
                    self._real = real

                def index_information(self, *a, **kw):
                    return self._real.index_information(*a, **kw)

                def find_one(self, *a, **kw):
                    return self._real.find_one(*a, **kw)

                async def update_one(self, filt, upd, *a, **kw):
                    if filt.get("slug") == race_slug and filt.get("_id") == race_id:
                        await self._real.update_one(
                            {"_id": race_id}, {"$set": {"slug": f"{tag}-raced"}}
                        )
                    return await self._real.update_one(filt, upd, *a, **kw)

            class RacingDB:
                def __init__(self, real_db):
                    # Proxy the COLLECTION (not the database): do_rollback only
                    # ever touches db.categories.
                    self.categories = RacingCategories(real_db.categories)

            backup = [
                {"_id": str(race_id), "name": "TOCTOU Race", "slug": None,
                 "slug_field_present": True, "assigned_slug": race_slug},
                {"_id": str(ok_id), "name": "TOCTOU Untouched", "slug": None,
                 "slug_field_present": True, "assigned_slug": "v20-assigned-ok"},
            ]
            backup_path = tmp_path / "v20_toctou.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(RacingDB(db), str(backup_path))
            raced = await db.categories.find_one({"_id": race_id})
            ok = await db.categories.find_one({"_id": ok_id})
            return rc, raced, ok
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    rc, raced, ok = _run(go())
    assert rc == 3, "a skipped conflict makes the rollback INCOMPLETE (exit 3), not success"
    assert raced["slug"] == f"{tag}-raced", (
        "the concurrent write between the read and the rollback write must win"
    )
    assert race_slug not in (raced.get("legacySlugs") or []), (
        "a write-time conflict must not pollute legacySlugs"
    )
    assert ok["slug"] is None, "unraced documents in the same backup still restore"
    assert "v20-assigned-ok" in ok.get("legacySlugs", [])


def test_v20_rollback_guard_and_index_provenance_are_structural():
    """Final-review corrections 2 & 3, structural pins: the restore write
    filters on slug == assigned_slug and reports matched/modified; the index
    decision is made before any document write; a V20-created index is
    dropped first; a pre-existing index is never dropped; the multi-null
    pre-existing-index case fails closed."""
    src = open(os.path.join(
        _BACKEND, "migrations", "V20_backfill_category_slugs.py"
    ), encoding="utf-8").read()
    rollback_src = src[src.index("async def do_rollback"):]
    assert '{"_id": cat_id, "slug": assigned_slug}' in rollback_src, (
        "the restore write must be conditional on the assigned slug at write time"
    )
    assert "res.matched_count" in rollback_src
    assert "res.modified_count" in rollback_src
    assert "from pymongo.errors import DuplicateKeyError" in src
    assert rollback_src.index("index_created_by_v20") < rollback_src.index(
        "for doc in docs"
    ), "index provenance must be decided BEFORE any restore write"
    assert "drop_index(INDEX_NAME)" in rollback_src
    assert "existed before V20" in rollback_src
    assert "FAIL-CLOSED" in rollback_src, (
        "multiple null restores under a pre-existing unique index must fail closed"
    )


def test_v20_rollback_drops_v20_created_index_before_restoring_nulls(tmp_path):
    """Final-review correction 3: the backup records that V20 created the
    index; rollback drops it BEFORE restoring, so several original slug=null
    documents are restored without E11000. Unrelated indexes are preserved
    and the V20 index is not recreated."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20idxdrop-" + uuid.uuid4().hex[:8]
    ids = [ObjectId() for _ in range(3)]
    assigned = [f"idx-drop-{n}-{uuid.uuid4().hex[:6]}" for n in range(3)]
    unrelated = "idx_v20rb_unrelated_" + uuid.uuid4().hex[:6]

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": i, "tag": tag, "name": f"Idx {tag} {n}", "slug": None}
                for n, i in enumerate(ids)
            ])
            for i, s in zip(ids, assigned):
                await db.categories.update_one({"_id": i}, {"$set": {"slug": s}})
            # The index state V20 leaves behind: unique sparse slug index
            # created by V20, plus one unrelated index that must survive.
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME
            )
            await db.categories.create_index([("tag", 1)], name=unrelated)
            backup = [
                {"_meta": {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                           "index_name": v20.INDEX_NAME,
                           "index_existed_before_v20": False,
                           "index_created_by_v20": True}},
            ] + [
                {"_id": str(i), "name": f"Idx {tag} {n}", "slug": None,
                 "slug_field_present": True, "assigned_slug": s}
                for n, (i, s) in enumerate(zip(ids, assigned))
            ]
            backup_path = tmp_path / "v20_idxdrop.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            for name in (v20.INDEX_NAME, unrelated):
                try:
                    await db.categories.drop_index(name)
                except Exception:
                    pass
            client.close()

    rc, indexes, docs = _run(go())
    assert rc == 0
    assert v20.INDEX_NAME not in indexes, (
        "the V20-created index must be dropped by the rollback"
    )
    assert unrelated in indexes, "unrelated indexes must be preserved"
    assert len(docs) == 3
    for d, s in zip(docs, assigned):
        assert d["slug"] is None, (
            "multiple original null slugs must be restored without E11000"
        )
        assert s in d.get("legacySlugs", []), "the assigned slug stays addressable"


def test_v20_rollback_never_drops_preexisting_index_and_fails_closed(tmp_path):
    """Final-review correction 3: an index that existed BEFORE V20 is never
    dropped. A rollback that would restore several explicit null slugs under
    it fails closed BEFORE touching any document: rc 2, slugs unchanged, no
    legacySlugs pollution, and both the V20-named and the unrelated index
    still intact."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20idxkeep-" + uuid.uuid4().hex[:8]
    ids = [ObjectId() for _ in range(3)]
    assigned = [f"idx-keep-{n}-{uuid.uuid4().hex[:6]}" for n in range(3)]
    unrelated = "idx_v20rb_keep_" + uuid.uuid4().hex[:6]

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            await db.categories.insert_many([
                {"_id": i, "tag": tag, "name": f"Keep {tag} {n}", "slug": None}
                for n, i in enumerate(ids)
            ])
            for i, s in zip(ids, assigned):
                await db.categories.update_one({"_id": i}, {"$set": {"slug": s}})
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME
            )
            await db.categories.create_index([("tag", 1)], name=unrelated)
            backup = [
                {"_meta": {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                           "index_name": v20.INDEX_NAME,
                           "index_existed_before_v20": True,
                           "index_created_by_v20": False}},
            ] + [
                {"_id": str(i), "name": f"Keep {tag} {n}", "slug": None,
                 "slug_field_present": True, "assigned_slug": s}
                for n, (i, s) in enumerate(zip(ids, assigned))
            ]
            backup_path = tmp_path / "v20_idxkeep.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            for name in (v20.INDEX_NAME, unrelated):
                try:
                    await db.categories.drop_index(name)
                except Exception:
                    pass
            client.close()

    rc, indexes, docs = _run(go())
    assert rc == 2, "the multi-null rollback under a pre-existing index must fail closed"
    assert v20.INDEX_NAME in indexes, "an index that pre-existed V20 must NOT be dropped"
    assert unrelated in indexes, "unrelated indexes must be preserved"
    for d, s in zip(docs, assigned):
        assert d["slug"] == s, "nothing was modified before the fail-closed abort"
        assert s not in (d.get("legacySlugs") or []), "no partial rollback state"


def test_v20_rollback_preserves_preexisting_index_for_single_null_restore(tmp_path):
    """Final-review correction 3: with a pre-existing unique sparse index, a
    rollback that restores exactly ONE explicit null (and nothing else holds
    a null/empty slug) is safe — it proceeds WITHOUT dropping the index."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20idxone-" + uuid.uuid4().hex[:8]
    doc_id = ObjectId()
    assigned = f"idx-one-{uuid.uuid4().hex[:6]}"

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            await db.categories.insert_one(
                {"_id": doc_id, "tag": tag, "name": f"One {tag}", "slug": None}
            )
            await db.categories.update_one({"_id": doc_id}, {"$set": {"slug": assigned}})
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME
            )
            backup = [
                {"_meta": {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                           "index_name": v20.INDEX_NAME,
                           "index_existed_before_v20": True,
                           "index_created_by_v20": False}},
                {"_id": str(doc_id), "name": f"One {tag}", "slug": None,
                 "slug_field_present": True, "assigned_slug": assigned},
            ]
            backup_path = tmp_path / "v20_idxone.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            indexes = await db.categories.index_information()
            doc = await db.categories.find_one({"_id": doc_id})
            return rc, indexes, doc
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    rc, indexes, doc = _run(go())
    assert rc == 0
    assert v20.INDEX_NAME in indexes, "a pre-existing index must be preserved"
    assert doc["slug"] is None
    assert assigned in doc.get("legacySlugs", [])


def test_v20_backup_file_creation_never_overwrites_existing_backup(tmp_path, monkeypatch):
    """Final-review correction 4: backup files are created EXCLUSIVELY
    (O_CREAT|O_EXCL). When the deterministic second-resolution name is already
    taken — as with a concurrent run — the writer uses a unique suffix instead
    of truncating, and the pre-existing backup's bytes stay untouched."""
    import glob as _glob
    import json as _json
    import re as _re
    from datetime import datetime as _dt, timezone as _tz
    import migrations.V20_backfill_category_slugs as v20

    monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
    real_dt = v20.datetime

    class FixedDatetime(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 11, 20, 12, 0, 0, tzinfo=_tz.utc)

    monkeypatch.setattr(v20, "datetime", FixedDatetime)

    records_a = [{"_id": str(ObjectId()), "name": "Collision A", "slug": None,
                  "slug_field_present": True, "assigned_slug": "collision-a"}]
    first = v20.write_and_validate_backup(records_a, {"exists": False})
    assert first.endswith("V20_categories_20261120T120000Z.json")

    # Second run in the SAME fixed second: the deterministic name now exists.
    records_b = [{"_id": str(ObjectId()), "name": "Collision B", "slug": None,
                  "slug_field_present": False, "assigned_slug": "collision-b"}]
    second = v20.write_and_validate_backup(records_b, {"exists": True})

    assert second != first, "an existing backup must never be replaced"
    assert _re.search(r"V20_categories_20261120T120000Z_[0-9a-f]{8}\.json$", second), (
        "the colliding writer must claim a unique exclusive name"
    )
    first_payload = _json.loads(open(first, encoding="utf-8").read())
    assert first_payload[1]["assigned_slug"] == "collision-a", (
        "the pre-existing backup's bytes are untouched (no silent overwrite)"
    )
    assert first_payload[0]["_meta"]["index_created_by_v20"] is True
    second_payload = _json.loads(open(second, encoding="utf-8").read())
    assert second_payload[1]["assigned_slug"] == "collision-b"
    assert second_payload[0]["_meta"]["index_existed_before_v20"] is True
    assert second_payload[0]["_meta"]["index_created_by_v20"] is False
    assert len(_glob.glob(str(tmp_path / "*.json"))) == 2


def test_v20_fails_closed_on_preexisting_duplicate_slugs(tmp_path, monkeypatch):
    """Final-review correction 6: duplicate non-empty slugs already present in
    the collection are detected BEFORE any mutation; --apply refuses to run
    (fail closed): no backfill write, no backup file, no index creation, and
    existing valid slugs stay untouched."""
    import glob as _glob
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import MigrationBlocked
    tag = "b6v20dup-" + uuid.uuid4().hex[:8]
    dup_a, dup_b, null_id = ObjectId(), ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": dup_a, "tag": tag, "name": f"Dup A {tag}",
                 "slug": f"dup-shared-{tag}"},
                {"_id": dup_b, "tag": tag, "name": f"Dup B {tag}",
                 "slug": f"dup-shared-{tag}"},
                {"_id": null_id, "tag": tag, "name": f"Dup Null {tag}", "slug": None},
            ])
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", DB_NAME)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
            raised = None
            try:
                await v20.run_migration(apply=True)
            except MigrationBlocked as exc:
                raised = exc
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            return raised, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    raised, indexes, docs = _run(go())
    assert raised is not None, "--apply must fail closed on duplicate pre-existing slugs"
    assert "FAIL-CLOSED" in str(raised) and "duplicate" in str(raised).lower()
    assert v20.INDEX_NAME not in indexes, "no index may be created by a failed-closed run"
    assert _glob.glob(str(tmp_path / "*.json")) == [], (
        "no backup may be written by a failed-closed run"
    )
    by_id = {d["_id"]: d for d in docs}
    assert by_id[dup_a]["slug"] == f"dup-shared-{tag}", "existing slugs are never modified"
    assert by_id[dup_b]["slug"] == f"dup-shared-{tag}"
    assert by_id[null_id]["slug"] is None, "no backfill write happened before the abort"


def test_v20_dry_run_reports_duplicates_and_exits_2(tmp_path, monkeypatch):
    """Final-review correction 6: dry-run stays the default — it REPORTS
    pre-existing duplicates (so the operator sees them in the report) and
    still writes nothing, raises nothing, and creates no index."""
    import glob as _glob
    import migrations.V20_backfill_category_slugs as v20
    tag = "b6v20dupdry-" + uuid.uuid4().hex[:8]
    dup_a, dup_b = ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            await db.categories.insert_many([
                {"_id": dup_a, "tag": tag, "name": f"DryDup A {tag}",
                 "slug": f"dry-dup-{tag}"},
                {"_id": dup_b, "tag": tag, "name": f"DryDup B {tag}",
                 "slug": f"dry-dup-{tag}"},
            ])
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", DB_NAME)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))
            rc = await v20.run_migration(apply=False)
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            client.close()

    rc, indexes, docs = _run(go())
    assert rc == 2, "a dry-run that --apply would refuse must report exit 2"
    assert v20.INDEX_NAME not in indexes
    assert _glob.glob(str(tmp_path / "*.json")) == []
    assert all(d["slug"] == f"dry-dup-{tag}" for d in docs)


def test_v20_duplicate_slug_scan_runs_before_backup_and_writes():
    """Final-review correction 6, structural: the duplicate scan runs in
    run_migration BEFORE the backup write, so a fail-closed abort can never
    have written a backup or mutated the database — and the scan matches only
    non-empty string slugs (null/missing are the legitimate backfill targets,
    not collisions)."""
    src = open(os.path.join(
        _BACKEND, "migrations", "V20_backfill_category_slugs.py"
    ), encoding="utf-8").read()
    run_src = src[src.index("async def run_migration"):
                  src.index("async def do_rollback")]
    scan_at = run_src.index("find_preexisting_slug_duplicates(db)")
    backup_at = run_src.index("write_and_validate_backup(")
    assert scan_at < backup_at, "duplicates must fail closed before the backup write"
    fn_src = src[src.index("async def find_preexisting_slug_duplicates"):
                 src.index("async def run_migration")]
    assert '"$type": "string"' in fn_src
    assert '"$gt": ""' in fn_src, "empty strings are backfill targets, not duplicates"


# ------------------- Final review round 2: findings 1-3 (2026-11-20) -------------------


def test_v20_rollback_preflight_failure_leaves_database_untouched(tmp_path):
    """Finding 1 (HIGH): the rollback builds and validates its COMPLETE plan
    BEFORE any mutation. The backup says V20 created the index (the pre-finding-1
    code dropped it FIRST); one backed-up document was changed after V20. The
    preflight conflict aborts the rollback: the V20-named index is NOT dropped,
    NO document is modified, and no legacySlugs is polluted."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20pf-" + uuid.uuid4().hex[:8]
    conflict_id, restorable_id = ObjectId(), ObjectId()
    unrelated = "idx_v20pf_unrelated_" + uuid.uuid4().hex[:6]
    assigned_conflict = f"pf-conflict-assigned-{tag}"
    assigned_restorable = f"pf-restorable-assigned-{tag}"
    original_restorable = f"pf-original-{tag}"

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_many([
                {"_id": conflict_id, "tag": tag, "name": "PF Conflict",
                 "slug": None, "isActive": True},
                {"_id": restorable_id, "tag": tag, "name": "PF Restorable",
                 "slug": None, "isActive": True},
            ])
            # Simulate exactly what V20 applied.
            await db.categories.update_one(
                {"_id": conflict_id}, {"$set": {"slug": assigned_conflict}})
            await db.categories.update_one(
                {"_id": restorable_id}, {"$set": {"slug": assigned_restorable}})
            # AFTER V20: an operator renamed the conflicting category.
            await db.categories.update_one(
                {"_id": conflict_id},
                {"$set": {"slug": f"{tag}-renamed-after-v20"}})
            # Post-V20 index state: the unique sparse index V20 created, plus
            # an unrelated index that must survive regardless.
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME)
            await db.categories.create_index([("tag", 1)], name=unrelated)
            backup = [
                {"_meta": {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                           "index_name": v20.INDEX_NAME,
                           "index_existed_before_v20": False,
                           "index_created_by_v20": True}},
                {"_id": str(conflict_id), "name": "PF Conflict", "slug": None,
                 "slug_field_present": True, "assigned_slug": assigned_conflict},
                {"_id": str(restorable_id), "name": "PF Restorable",
                 "slug": original_restorable, "slug_field_present": True,
                 "assigned_slug": assigned_restorable},
            ]
            backup_path = tmp_path / "v20_preflight_abort.json"
            backup_path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(backup_path))
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            for name in (v20.INDEX_NAME, unrelated):
                try:
                    await db.categories.drop_index(name)
                except Exception:
                    pass
            client.close()

    rc, indexes, docs = _run(go())
    assert rc == 2, "a preflight conflict must abort the rollback (finding 1)"
    assert v20.INDEX_NAME in indexes, (
        "finding 1: the index must NOT be dropped when the preflight fails — "
        "the pre-finding-1 code dropped it before checking document conflicts"
    )
    assert indexes[v20.INDEX_NAME].get("unique") and indexes[v20.INDEX_NAME].get("sparse"), (
        "the surviving index must be byte-identical in semantics (never replaced)"
    )
    assert unrelated in indexes, "unrelated indexes must be preserved"
    by_id = {d["_id"]: d for d in docs}
    assert by_id[conflict_id]["slug"] == f"{tag}-renamed-after-v20", (
        "a slug changed after V20 is never overwritten"
    )
    assert assigned_conflict not in (by_id[conflict_id].get("legacySlugs") or [])
    assert by_id[restorable_id]["slug"] == assigned_restorable, (
        "finding 1: NO document is modified on a failed preflight — not even "
        "the restorable one (no partial rollback)"
    )
    assert assigned_restorable not in (by_id[restorable_id].get("legacySlugs") or []), (
        "an aborted rollback must not leave partial rollback state"
    )


def test_v20_rollback_fails_closed_on_invalid_backup_structure(tmp_path):
    """Finding 1: the backup is STRUCTURALLY validated before any database
    access. Non-object records, records without _id, invalid ObjectIds,
    missing assigned_slug / slug_field_present, duplicate _ids, and _meta
    records that do not belong to this migration all abort with ZERO
    mutations (MigrationBlocked), leaving the collection untouched."""
    import json as _json
    from migrations.V20_backfill_category_slugs import (
        INDEX_NAME, MigrationBlocked, do_rollback)
    tag = "b6v20struct-" + uuid.uuid4().hex[:8]
    doc_id = ObjectId()
    assigned = f"struct-assigned-{tag}"

    valid = {"_id": str(doc_id), "name": "Struct Valid", "slug": None,
             "slug_field_present": True, "assigned_slug": assigned}
    foreign_meta = {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                    "index_name": INDEX_NAME,
                    "index_existed_before_v20": True,
                    "index_created_by_v20": False}
    cases = [
        ("non-object record", [valid, "not-an-object"]),
        ("record without _id", [{"name": "n", "slug": None,
                                 "slug_field_present": True,
                                 "assigned_slug": "x"}]),
        ("invalid ObjectId", [{"_id": "zz-not-hex24", "slug": None,
                               "slug_field_present": True,
                               "assigned_slug": "x"}]),
        ("missing assigned_slug", [{"_id": str(doc_id), "name": "n",
                                    "slug": None, "slug_field_present": True}]),
        ("missing slug_field_present", [{"_id": str(doc_id), "slug": None,
                                         "assigned_slug": assigned}]),
        ("duplicate _id", [valid, dict(valid)]),
        ("foreign _meta kind", [dict(foreign_meta, kind="OTHER_MIGRATION"), valid]),
        ("foreign _meta index_name", [dict(foreign_meta, index_name="other_index"),
                                      valid]),
        ("inconsistent provenance", [dict(foreign_meta, index_created_by_v20=True),
                                     valid]),
    ]

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        results = []
        try:
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            await db.categories.insert_one(
                {"_id": doc_id, "tag": tag, "name": "Struct Doc",
                 "slug": assigned, "isActive": True})
            for idx, (label, payload) in enumerate(cases):
                path = tmp_path / f"v20_struct_{idx}.json"
                path.write_text(_json.dumps(payload), encoding="utf-8")
                raised = None
                try:
                    await do_rollback(db, str(path))
                except MigrationBlocked as exc:
                    raised = exc
                doc = await db.categories.find_one({"_id": doc_id})
                count = await db.categories.count_documents({"tag": tag})
                indexes = await db.categories.index_information()
                results.append((label, raised, doc, count, INDEX_NAME in indexes))
            return results
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            client.close()

    results = _run(go())
    assert len(results) == len(cases)
    for label, raised, doc, count, index_present in results:
        assert raised is not None, f"{label!r} must fail closed with MigrationBlocked"
        assert "FAIL-CLOSED (finding 1)" in str(raised)
        assert count == 1, f"{label!r}: no document may be created/removed"
        assert doc["slug"] == assigned, f"{label!r}: the document must be untouched"
        assert not (doc.get("legacySlugs") or []), (
            f"{label!r}: legacySlugs must not be polluted by an aborted rollback"
        )
        assert index_present is False, f"{label!r}: no index may be dropped"


def test_v20_rollback_fails_closed_when_restored_state_violates_unique_index(tmp_path):
    """Finding 1: the preflight validates index constraints against the ENTIRE
    planned restored state — not just null restores. Two blocking shapes:
    (a) a restored slug is already held by a document OUTSIDE the backup;
    (b) two backed-up documents restore the SAME original slug. Both abort
    before any mutation; the pre-existing index is never dropped."""
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import do_rollback
    tag = "b6v20rstate-" + uuid.uuid4().hex[:8]

    def _meta():
        return {"_meta": {"kind": "V20_BACKFILL_CATEGORY_SLUGS_BACKUP_V2",
                          "index_name": v20.INDEX_NAME,
                          "index_existed_before_v20": True,
                          "index_created_by_v20": False}}

    async def go_outside_holder():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        doc_a, doc_c = ObjectId(), ObjectId()
        try:
            await db.categories.insert_many([
                {"_id": doc_a, "tag": tag, "name": "RS A", "slug": f"{tag}-a"},
                {"_id": doc_c, "tag": tag, "name": "RS C", "slug": f"{tag}-shared"},
            ])
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME)
            backup = [_meta(), {
                "_id": str(doc_a), "name": "RS A", "slug": f"{tag}-shared",
                "slug_field_present": True, "assigned_slug": f"{tag}-a"}]
            path = tmp_path / "v20_rstate_outside.json"
            path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(path))
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    async def go_within_plan():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        doc_a, doc_b = ObjectId(), ObjectId()
        try:
            await db.categories.insert_many([
                {"_id": doc_a, "tag": tag, "name": "RS A2", "slug": f"{tag}-a2"},
                {"_id": doc_b, "tag": tag, "name": "RS B2", "slug": f"{tag}-b2"},
            ])
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=v20.INDEX_NAME)
            backup = [_meta(),
                      {"_id": str(doc_a), "name": "RS A2",
                       "slug": f"{tag}-shared2", "slug_field_present": True,
                       "assigned_slug": f"{tag}-a2"},
                      {"_id": str(doc_b), "name": "RS B2",
                       "slug": f"{tag}-shared2", "slug_field_present": True,
                       "assigned_slug": f"{tag}-b2"}]
            path = tmp_path / "v20_rstate_within.json"
            path.write_text(_json.dumps(backup), encoding="utf-8")
            rc = await do_rollback(db, str(path))
            indexes = await db.categories.index_information()
            docs = await db.categories.find({"tag": tag}).sort("_id", 1).to_list(10)
            return rc, indexes, docs
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    # (a) restored slug collides with a document outside the backup
    rc, indexes, docs = _run(go_outside_holder())
    assert rc == 2, "a restored slug colliding outside the backup must abort"
    assert v20.INDEX_NAME in indexes, "the pre-existing index must be preserved"
    assert {d["slug"] for d in docs} == {f"{tag}-a", f"{tag}-shared"}, (
        "nothing was modified before the fail-closed abort"
    )
    assert all(not (d.get("legacySlugs") or []) for d in docs)

    # (b) two backed-up documents restore the same original slug
    rc, indexes, docs = _run(go_within_plan())
    assert rc == 2, "an in-plan duplicate restored slug must abort"
    assert v20.INDEX_NAME in indexes
    assert {d["slug"] for d in docs} == {f"{tag}-a2", f"{tag}-b2"}
    assert all(not (d.get("legacySlugs") or []) for d in docs)


def test_v20_verify_slug_index_rejects_incompatible_semantic_options():
    """Finding 3: EVERY semantic index option is validated. An existing
    idx_categories_slug_unique carrying collation, expireAfterSeconds (TTL)
    or partialFilterExpression fails closed with the EXACT option named in
    the error, and the index is never dropped or replaced automatically.
    A fully conforming index verifies cleanly."""
    from migrations.V20_backfill_category_slugs import (
        INDEX_NAME, MigrationBlocked, describe_index_incompatibilities,
        verify_slug_index)
    cases = [
        ("collation", dict(collation={"locale": "en", "strength": 2})),
        ("expireAfterSeconds", dict(expireAfterSeconds=100)),
        ("partialFilterExpression", dict(partialFilterExpression={"isActive": True})),
    ]

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        results = []
        try:
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            for opt_name, kwargs in cases:
                await db.categories.create_index(
                    [("slug", 1)], unique=True, name=INDEX_NAME, **kwargs)
                raised = None
                try:
                    await verify_slug_index(db, create=True)
                except MigrationBlocked as exc:
                    raised = exc
                info = await db.categories.index_information()
                still_there = INDEX_NAME in info
                info_def = info.get(INDEX_NAME)
                await db.categories.drop_index(INDEX_NAME)
                results.append((opt_name, raised, still_there, info_def))
            # Positive control: the exact V20 contract verifies cleanly.
            await db.categories.create_index(
                [("slug", 1)], unique=True, sparse=True, name=INDEX_NAME)
            status = await verify_slug_index(db, create=True)
            return results, status
        finally:
            try:
                await db.categories.drop_index(INDEX_NAME)
            except Exception:
                pass
            client.close()

    results, status = _run(go())
    for opt_name, raised, still_there, info_def in results:
        assert raised is not None, f"{opt_name} must fail closed"
        msg = str(raised)
        assert "FAIL-CLOSED (finding 3)" in msg
        assert f"'{opt_name}'" in msg, (
            f"the error must name the exact incompatible option {opt_name!r}; got: {msg}"
        )
        assert still_there, (
            f"{opt_name}: an incompatible index is never dropped automatically"
        )
        assert describe_index_incompatibilities(info_def), (
            f"{opt_name}: the index definition must be untouched (never replaced)"
        )
    assert status["exists"] is True and status["action"] == "verified"


def test_v20_empty_plan_still_reconciles_index(tmp_path, monkeypatch):
    """Finding 2: an empty migration plan (every category already has a slug)
    does NOT skip index validation. Dry-run stays strictly read-only (no
    index, no backup). Apply mode creates the missing index AFTER the
    preconditions are validated (compatible-or-missing index, no duplicate
    slugs, no null/empty slugs) and a provenance backup is written FIRST;
    with the index already present, apply mode reconciles nothing; and
    duplicate pre-existing slugs still fail closed before any index creation
    (no backup, no index)."""
    import glob as _glob
    import json as _json
    import migrations.V20_backfill_category_slugs as v20
    from migrations.V20_backfill_category_slugs import MigrationBlocked
    tag = "b6v20empty-" + uuid.uuid4().hex[:8]
    doc_a, dup_1, dup_2 = ObjectId(), ObjectId(), ObjectId()

    async def go():
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        try:
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            monkeypatch.setenv("MONGO_URL", URL)
            monkeypatch.setenv("DB_NAME", DB_NAME)
            monkeypatch.setattr(v20, "BACKUP_DIR", str(tmp_path))

            # Phase 4 first (no index yet): empty plan + duplicate slugs
            # must still fail closed BEFORE any index creation.
            await db.categories.insert_many([
                {"_id": dup_1, "tag": tag, "name": f"Empty Dup 1 {tag}",
                 "slug": f"{tag}-dup"},
                {"_id": dup_2, "tag": tag, "name": f"Empty Dup 2 {tag}",
                 "slug": f"{tag}-dup"},
            ])
            raised = None
            try:
                await v20.run_migration(apply=True)
            except MigrationBlocked as exc:
                raised = exc
            dup_indexes = await db.categories.index_information()
            dup_backups = _glob.glob(str(tmp_path / "*.json"))
            dup_docs = await db.categories.find({"tag": tag}).to_list(10)
            await db.categories.delete_many({"tag": tag})

            # Phase 1: empty plan, index missing, dry-run — strictly read-only.
            await db.categories.insert_one(
                {"_id": doc_a, "tag": tag, "name": f"Empty A {tag}",
                 "slug": f"{tag}-a"})
            rc1 = await v20.run_migration(apply=False)
            indexes1 = await db.categories.index_information()
            backups1 = _glob.glob(str(tmp_path / "*.json"))

            # Phase 2: empty plan, index missing, apply — reconcile it
            # (backup-first, preconditions validated).
            rc2 = await v20.run_migration(apply=True)
            indexes2 = await db.categories.index_information()
            backups2 = sorted(_glob.glob(str(tmp_path / "*.json")))
            doc_a_after = await db.categories.find_one({"_id": doc_a})

            # Phase 3: empty plan, index already present — nothing to do,
            # no additional backup.
            rc3 = await v20.run_migration(apply=True)
            indexes3 = await db.categories.index_information()
            backups3 = _glob.glob(str(tmp_path / "*.json"))
            return (raised, dup_indexes, dup_backups, dup_docs,
                    rc1, indexes1, backups1,
                    rc2, indexes2, backups2, doc_a_after,
                    rc3, indexes3, backups3)
        finally:
            await db.categories.delete_many({"tag": tag})
            try:
                await db.categories.drop_index(v20.INDEX_NAME)
            except Exception:
                pass
            client.close()

    (raised, dup_indexes, dup_backups, dup_docs,
     rc1, indexes1, backups1,
     rc2, indexes2, backups2, doc_a_after,
     rc3, indexes3, backups3) = _run(go())

    # Phase 4: duplicates fail closed even though nothing needs backfilling.
    assert raised is not None, "duplicates must fail closed on an empty plan"
    assert "FAIL-CLOSED" in str(raised)
    assert v20.INDEX_NAME not in dup_indexes, "no index may be created"
    assert dup_backups == [], "no backup may be written by the failed run"
    assert all(d["slug"] == f"{tag}-dup" for d in dup_docs), "slugs untouched"

    # Phase 1: dry-run writes NOTHING (no index, no backup).
    assert rc1 == 0
    assert v20.INDEX_NAME not in indexes1, "dry-run must not reconcile the index"
    assert backups1 == [], "dry-run must not write a backup"

    # Phase 2: apply reconciles the index, backup-first.
    assert rc2 == 0
    assert v20.INDEX_NAME in indexes2, (
        "finding 2: the empty plan must still reconcile the missing index"
    )
    assert indexes2[v20.INDEX_NAME].get("unique") and indexes2[v20.INDEX_NAME].get("sparse")
    assert len(backups2) == 1, "exactly one provenance backup is written"
    payload = _json.loads(open(backups2[0], encoding="utf-8").read())
    assert len(payload) == 1, "an index-only backup has no document records"
    assert payload[0]["_meta"]["index_name"] == v20.INDEX_NAME
    assert payload[0]["_meta"]["index_created_by_v20"] is True
    assert payload[0]["_meta"]["index_existed_before_v20"] is False
    assert doc_a_after["slug"] == f"{tag}-a", "documents are never modified"

    # Phase 3: compatible index already present — nothing to reconcile.
    assert rc3 == 0
    assert v20.INDEX_NAME in indexes3
    assert len(backups3) == 1, "no additional backup without any mutation"


def test_v20_rollback_preflight_precedes_every_mutation_structurally():
    """Finding 1, structural: in do_rollback the backup validation, the
    READ-ONLY preflight (document conflict scan) and the EXECUTE marker all
    appear before the index drop and the restore write, and the preflight
    conflict abort returns 2 BEFORE the drop can run."""
    src = open(os.path.join(
        _BACKEND, "migrations", "V20_backfill_category_slugs.py"
    ), encoding="utf-8").read()
    rollback_src = src[src.index("async def do_rollback"):]
    loader_at = rollback_src.index("_load_and_validate_rollback_backup(backup_path)")
    preflight_at = rollback_src.index("PREFLIGHT (finding 1)")
    abort_at = rollback_src.index("FAIL-CLOSED (finding 1)")
    execute_at = rollback_src.index("EXECUTE (mutations begin ONLY here)")
    drop_at = rollback_src.index("await db.categories.drop_index(INDEX_NAME)")
    restore_write_at = rollback_src.index('{"_id": cat_id, "slug": assigned_slug}')
    assert loader_at < preflight_at < execute_at < drop_at, (
        "backup validation and the read-only preflight must precede any mutation"
    )
    assert loader_at < abort_at < drop_at, (
        "the preflight conflict abort must return BEFORE the index drop"
    )
    assert drop_at < restore_write_at, (
        "the index drop happens before the restore writes (correction 3), "
        "but only after the whole preflight (finding 1)"
    )
    # The restored-state index validation runs in preflight, read-only.
    assert "planned restored state" in rollback_src
    assert rollback_src.index("other_empty = await db.categories.count_documents") < drop_at
