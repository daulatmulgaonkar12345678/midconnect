"""
Batch 5 — deterministic product slug resolution: HTTP route regression.

Boots the REAL FastAPI app as a uvicorn subprocess against the disposable
MongoDB (PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME; skips when unset) and
exercises the routes over true HTTP.

Why a subprocess and not fastapi.testclient.TestClient: the in-process
TestClient path binds the app's Motor client and Starlette's middleware
task group to different event loops in this environment ("Future attached
to a different loop"), which fails unrelated pre-existing suites too
(test_sitemap_products_http.py). A real server process has exactly one
loop and proves the actual production behavior.

Each test uses a unique tag and deletes only the documents it inserted.
"""
import asyncio
import os
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
    err_path = os.path.join(os.environ.get("TEMP", "."), "midconnect-b5-uvicorn.err.log")
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
    """Two tagged products; the first has one active listing so /products/detail works."""
    tag = "b5sl-" + uuid.uuid4().hex[:8]
    canonical = f"{tag}-industrial-electric-motor-supplier-india"
    notebooks = f"{tag}-notebooks-office-supplies-supplier-india"
    legacy_slug = f"{tag}-motor-old-name-supplier-india"
    legacy_id = str(ObjectId())
    product_oid = ObjectId()

    docs = [
        {
            "_id": product_oid,
            "tag": tag,
            "name": "Industrial Electric Motor 5HP",
            "slug": canonical,
            "isActive": True,
            "legacySlugs": [legacy_slug],
            "legacyIds": [legacy_id],
            "categoryId": None,
        },
        {
            "_id": ObjectId(),
            "tag": tag,
            "name": "Notebooks",
            "slug": notebooks,
            "isActive": True,
        },
    ]
    listing = {
        "tag": tag,
        "productId": product_oid,
        "sellerId": ObjectId(),
        "status": "active",
        "isActive": True,
        "moq": 1,
        "pricingTiers": [{"minQty": 1, "pricePerUnit": 5000}],
    }

    async def seed():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].products.insert_many(docs)
            await c[DB_NAME].sellerListings.insert_one(listing)
        finally:
            c.close()

    async def cleanup():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].products.delete_many({"tag": tag})
            await c[DB_NAME].sellerListings.delete_many({"tag": tag})
        finally:
            c.close()

    _run(seed())
    try:
        yield {
            "tag": tag,
            "canonical": canonical,
            "notebooks": notebooks,
            "legacy_slug": legacy_slug,
            "legacy_id": legacy_id,
        }
    finally:
        _run(cleanup())


def ObjectId():
    from bson import ObjectId
    return ObjectId()


# ----------------------------- valid slugs -----------------------------

def test_canonical_slug_seo_resolves_200_with_payload(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/{seeded['canonical']}/seo", timeout=30)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["productName"] == "Industrial Electric Motor 5HP"
    assert body["slug"] == seeded["canonical"]
    assert body["canonicalUrl"].endswith(f"/products/{seeded['canonical']}")


def test_product_detail_resolves_canonical_slug_200(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/detail/{seeded['canonical']}", timeout=30)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == seeded["canonical"]
    # canonical slug: no redirect needed (endpoint only emits redirect info when needed)
    assert body.get("redirect", {}).get("needed") is not True


def test_case_normalized_slug_resolves_with_canonical_slug(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/{seeded['canonical'].upper()}/seo", timeout=30)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == seeded["canonical"]


def test_legacy_slug_resolves_with_redirect_info(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/detail/{seeded['legacy_slug']}", timeout=30)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == seeded["canonical"]
    assert body.get("redirect", {}).get("needed") is True
    assert body.get("redirect", {}).get("canonicalSlug") == seeded["canonical"]


def test_legacy_id_resolves_with_redirect_info(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/detail/{seeded['legacy_id']}", timeout=30)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == seeded["canonical"]
    assert body.get("redirect", {}).get("needed") is True


# ----------------------------- invalid slugs -----------------------------

def test_garbage_slug_returns_404_with_no_product_payload(base_url, seeded):
    import requests
    resp = requests.get(f"{base_url}/api/products/xyzzy-plugh-zorkmidconnect-42/seo", timeout=30)
    assert resp.status_code == 404
    assert "productName" not in resp.json()


def test_single_common_token_does_not_resolve_a_product(base_url, seeded):
    # "motor" is a token of the seeded product's name/slug but not a slug;
    # pre-Batch-5 this resolved via token matching. Must now 404.
    import requests
    resp = requests.get(f"{base_url}/api/products/motor-supplier-india/seo", timeout=30)
    assert resp.status_code == 404


def test_any_token_fallback_defect_case_returns_404(base_url, seeded):
    # Shares the "notebook" prefix with the seeded Notebooks product; the old
    # ANY-token fallback returned Notebooks with HTTP 200. Must now 404.
    import requests
    resp = requests.get(
        f"{base_url}/api/products/{seeded['tag']}-notebook-xyzzyq/seo", timeout=30
    )
    assert resp.status_code == 404


def test_city_suffixed_slug_returns_404(base_url, seeded):
    import requests
    resp = requests.get(
        f"{base_url}/api/products/{seeded['canonical']}-mumbai/seo", timeout=30
    )
    assert resp.status_code == 404


def test_garbage_slug_on_detail_returns_404(base_url, seeded):
    import requests
    resp = requests.get(
        f"{base_url}/api/products/detail/xyzzy-plugh-zorkmidconnect-42", timeout=30
    )
    assert resp.status_code == 404


# ----------------------------- service level -----------------------------

def test_resolve_slug_service_matches_http_contract(seeded):
    async def resolve_all():
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.slug_resolver_service import create_slug_resolver
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            db = c[DB_NAME]
            resolver = create_slug_resolver(db)
            results = {}
            results["canonical"] = await resolver.resolve_slug(seeded["canonical"])
            results["legacy"] = await resolver.resolve_slug(seeded["legacy_slug"])
            for bad in (
                "motor-supplier-india",
                f"{seeded['tag']}-notebook-xyzzyq",
                f"{seeded['canonical']}-mumbai",
                "xyzzy-plugh-zorkmidconnect-42",
            ):
                results[bad] = await resolver.resolve_slug(bad)
            return results
        finally:
            c.close()

    results = _run(resolve_all())

    product, needs_redirect, canonical, _ = results["canonical"]
    assert product is not None and needs_redirect is False
    assert canonical == seeded["canonical"]

    product2, needs_redirect2, canonical2, _ = results["legacy"]
    assert product2 is not None and needs_redirect2 is True
    assert canonical2 == seeded["canonical"]

    for bad, outcome in results.items():
        if bad in ("canonical", "legacy"):
            continue
        product_bad, _, _, matches = outcome
        assert product_bad is None, f"invalid slug resolved: {bad}"
        assert matches == []
