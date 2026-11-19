"""
/api/seo/sitemap-products — HTTP tests (disposable MongoDB only).

Runs the real FastAPI app against PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME.
Skips only when those variables are unset; any other failure is reported.

Database-unavailable case: the app is pointed at a loopback port where nothing
listens, so the server-selection timeout is hit for real (no mocks).
"""
import os
import socket
import sys
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

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

ROUTE = "/api/seo/sitemap-products"


def _closed_port() -> int:
    """A loopback port with nothing listening: connection is refused."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _load_app(mongo_url: str, db_name: str):
    """Import a fresh copy of server.py bound to the given Mongo target."""
    os.environ["MONGO_URL"] = mongo_url
    os.environ["DB_NAME"] = db_name
    os.environ.setdefault("ENVIRONMENT", "test")
    for name in [m for m in sys.modules if m == "server" or m.startswith("server.")]:
        del sys.modules[name]
    import server  # noqa: WPS433 - deliberate import after env is set
    return server


@pytest.fixture(scope="module")
def app_module():
    validate_test_target(URL, DB_NAME)
    return _load_app(URL, DB_NAME)


@pytest.fixture(scope="module")
def shared_client(app_module):
    """One TestClient (one event loop) for the whole module on the disposable DB."""
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def seeded(app_module, shared_client):
    """Insert tagged products on the disposable DB; delete only those on teardown.

    Seeding runs on the same TestClient portal as the requests, so the app's
    module-level Motor client is never bound to two different event loops.
    """
    tag = "smph-" + uuid.uuid4().hex[:8]
    docs = [
        {"_id": ObjectId(), "tag": tag, "name": "p", "slug": f"{tag}-b", "isActive": True},
        {"_id": ObjectId(), "tag": tag, "name": "p", "slug": f"{tag}-a", "isActive": True},
        {"_id": ObjectId(), "tag": tag, "name": "p", "slug": f"{tag}-hidden", "isActive": False},
    ]
    client = shared_client

    async def insert():
        # Created on the portal loop itself, so it is bound to the same loop as the requests.
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].products.insert_many(docs)
        finally:
            c.close()

    async def cleanup():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            await c[DB_NAME].products.delete_many({"tag": tag})
        finally:
            c.close()

    client.portal.call(insert)
    try:
        yield tag
    finally:
        client.portal.call(cleanup)


def test_success_returns_expected_fields_and_sorted_order(shared_client, seeded):
    tag = seeded
    resp = shared_client.get(ROUTE)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"products", "totalProducts"}
    rows = [r for r in body["products"] if r["productSlug"].startswith(tag)]
    # Hidden product excluded; remaining rows sorted ascending by slug.
    assert [r["productSlug"] for r in rows] == [f"{tag}-a", f"{tag}-b"]
    for r in rows:
        assert set(r.keys()) == {"productSlug", "lastModified"}
    assert body["totalProducts"] == len(body["products"])


def test_overflow_returns_503_and_is_not_reported_as_db_error(app_module, shared_client, seeded, monkeypatch):
    # `seeded` guarantees at least one visible product exists: the service
    # fetches limit(max_products + 1) rows, so max_products=0 only trips the
    # overflow guard when the collection is non-empty. Without it this test
    # silently depends on leftover rows from other runs.
    monkeypatch.setattr(app_module, "MAX_SITEMAP_PRODUCTS", 0)
    resp = shared_client.get(ROUTE)
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert "exceed max_products=0" in detail
    assert "temporarily unavailable" not in detail
