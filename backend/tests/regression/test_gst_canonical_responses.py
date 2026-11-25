"""
GST canonical verification — response-level regression tests (no database, no network).

Canonical rule: a seller is GST verified only when gst.verified is the literal True.

Covers the corrections:
1. admin user list (admin_list_users) and user detail (admin_get_user_detail) return
   gst.verified from the canonical field only; business.gstVerified cannot override it;
2. admin_get_sellers reads nested gst.verified (never root gstVerified) and projects it;
3. seller catalog API returns an actual boolean for gstVerified.

Importing server.py connects to MongoDB at import time (referral_router seeds plan config
synchronously), so it cannot be imported in a unit test. The three admin handlers are
therefore extracted from the real server.py source by AST and compiled unchanged; their
`db` is an in-memory fake. The seller catalog router has no import-time database use and
is imported directly.
"""
import ast
import asyncio
import math
import os
import sys
import types
import typing

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _BACKEND)
_SERVER_PATH = os.path.join(_BACKEND, "server.py")

_HANDLERS = {"admin_list_users", "admin_get_user_detail", "admin_get_sellers", "calculate_subscription_fields"}


class _Cursor:
    def __init__(self, docs, projection, recorder):
        self._docs = list(docs)
        self._projection = projection
        self._recorder = recorder
        self._skip = 0
        self._limit = None

    def sort(self, *args, **kwargs):
        return self

    def skip(self, n):
        self._skip = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    async def to_list(self, length=None):
        self._recorder.append(self._projection)
        docs = self._docs[self._skip:]
        if self._limit is not None:
            docs = docs[: self._limit]
        return docs

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _Collection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.projections = []

    def find(self, query=None, projection=None):
        self.projections.append(projection)
        return _Cursor(self.docs, projection, self.projections)

    async def find_one(self, query=None, projection=None):
        return self.docs[0] if self.docs else None

    async def count_documents(self, query=None):
        return len(self.docs)


class FakeDb:
    def __init__(self, users=None):
        self.users = _Collection(users)
        self.subscriptions = _Collection([])
        self.sellerListings = _Collection([])


def _load_handlers():
    """Compile the production handlers from server.py with their dependencies stubbed."""
    with open(_SERVER_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    nodes = [
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in _HANDLERS
    ]
    assert {n.name for n in nodes} == _HANDLERS, "expected handler(s) missing from server.py"
    for n in nodes:
        n.decorator_list = []  # route decorators are not needed to call the handler

    valid = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "VALID_BADGE_TYPES" for t in n.targets)
    ]
    module = ast.Module(body=valid + nodes, type_ignores=[])
    ast.fix_missing_locations(module)

    def _noop(*a, **k):
        return None

    class _HTTPException(Exception):
        def __init__(self, status_code=None, detail=None):
            super().__init__(detail)

    ns = {
        "__builtins__": __builtins__,
        "Depends": _noop,
        "Query": lambda default=None, *a, **k: default,
        "HTTPException": _HTTPException,
        "ObjectId": ObjectId,
        "Optional": typing.Optional,
        "math": math,
        "logger": types.SimpleNamespace(info=_noop, warning=_noop, error=_noop, debug=_noop),
        "api_router": types.SimpleNamespace(get=lambda *a, **k: (lambda f: f)),
        "require_admin": None,
        "db": None,
    }
    exec(compile(module, _SERVER_PATH, "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def handlers():
    return _load_handlers()


def _admin():
    return {"id": "admin", "isAdmin": True}


def _run(coro):
    return asyncio.run(coro)


def _user(**extra):
    base = {
        "_id": ObjectId(),
        "email": "seller@example.com",
        "profile": {"businessName": "Seller Co"},
        "roles": ["seller"],
        "accountStatus": "active",
        "isActive": True,
        "canLogin": True,
        "createdAt": None,
        "updatedAt": None,
        "deletedAt": None,
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# 1. Admin user list and detail
# ---------------------------------------------------------------------------
_USER_CASES = [
    (dict(gst={"verified": True, "status": "verified"}), True),
    (dict(gst={"verified": False, "status": "pending"}), False),
    # Legacy business.gstVerified must not override canonical false.
    (dict(gst={"verified": False}, business={"gstVerified": True}), False),
    # Legacy business.gstVerified alone must not establish verification.
    (dict(business={"gstVerified": True}), False),
    # Missing GST object.
    (dict(), False),
    # Missing gst.verified.
    (dict(gst={"status": "verified"}), False),
    # String "true" is not the literal boolean True.
    (dict(gst={"verified": "true"}), False),
]


@pytest.mark.parametrize("extra, expected", _USER_CASES)
def test_admin_user_list_uses_canonical_gst_verified(monkeypatch, handlers, extra, expected):
    db = FakeDb([_user(**extra)])
    monkeypatch.setitem(handlers, "db", db)
    result = _run(handlers["admin_list_users"](admin=_admin()))
    assert result["users"][0]["gst"]["verified"] is expected


@pytest.mark.parametrize("extra, expected", _USER_CASES)
def test_admin_user_detail_uses_canonical_gst_verified(monkeypatch, handlers, extra, expected):
    user = _user(**extra)
    db = FakeDb([user])
    monkeypatch.setitem(handlers, "db", db)
    result = _run(handlers["admin_get_user_detail"](str(user["_id"]), admin=_admin()))
    assert result["gst"]["verified"] is expected


# ---------------------------------------------------------------------------
# 2. Admin sellers endpoint
# ---------------------------------------------------------------------------
def _seller(**extra):
    base = {
        "_id": ObjectId(),
        "businessName": "Seller Co",
        "email": "seller@example.com",
        "createdAt": None,
        "status": "active",
    }
    base.update(extra)
    return base


def test_admin_sellers_projection_requests_nested_gst_verified(monkeypatch, handlers):
    db = FakeDb([_seller(gst={"verified": True})])
    monkeypatch.setitem(handlers, "db", db)
    _run(handlers["admin_get_sellers"](admin=_admin()))
    projection = db.users.projections[-1]
    assert projection.get("gst.verified") == 1
    assert "gstVerified" not in projection


@pytest.mark.parametrize(
    "extra, expected",
    [
        (dict(gst={"verified": True}), True),
        # Root-level legacy field must be ignored.
        (dict(gst={"verified": False}, gstVerified=True), False),
        (dict(gstVerified=True), False),  # root legacy alone
        (dict(), False),  # missing GST object
        (dict(gst={}), False),  # missing gst.verified
        (dict(gst={"verified": "true"}), False),  # string is not True
    ],
)
def test_admin_sellers_response_is_canonical_boolean(monkeypatch, handlers, extra, expected):
    db = FakeDb([_seller(**extra)])
    monkeypatch.setitem(handlers, "db", db)
    result = _run(handlers["admin_get_sellers"](admin=_admin()))
    assert result["sellers"][0]["gstVerified"] is expected


# ---------------------------------------------------------------------------
# 3. Seller catalog API
# ---------------------------------------------------------------------------
_CATALOG_SELLER = {"doc": None}


@pytest.fixture(scope="module")
def catalog_client():
    # init_seller_catalog_routes mutates a module-level router, so register it once per module.
    from routers import seller_catalog_router as scr

    async def fake_by_slug(db, slug):
        return _CATALOG_SELLER["doc"]

    async def fake_rating(db, seller_id):
        return {"averageRating": 0, "totalReviews": 0}

    async def fake_categories(db, seller_id, n):
        return []

    originals = {
        name: getattr(scr, name)
        for name in ("get_seller_by_slug", "calculate_seller_rating", "get_seller_products_by_category")
    }
    scr.get_seller_by_slug = fake_by_slug
    scr.calculate_seller_rating = fake_rating
    scr.get_seller_products_by_category = fake_categories
    try:
        app = FastAPI()
        app.include_router(scr.init_seller_catalog_routes(FakeDb()), prefix="/api")
        yield TestClient(app)
    finally:
        for name, fn in originals.items():
            setattr(scr, name, fn)


@pytest.mark.parametrize(
    "gst_fields, expected",
    [
        ({"gst": {"verified": True}}, True),
        ({"gst": {"verified": False}}, False),
        ({}, False),
        ({"gst": {}}, False),
        ({"gst": {"verified": "true"}}, False),
        ({"gst": {"verified": None}}, False),
    ],
)
def test_seller_catalog_returns_actual_boolean(catalog_client, gst_fields, expected):
    _CATALOG_SELLER["doc"] = {"_id": ObjectId(), "companyName": "A", **gst_fields}
    resp = catalog_client.get("/api/seller-catalog/some-slug")
    assert resp.status_code == 200, resp.text
    value = resp.json()["seller"]["gstVerified"]
    assert value is expected
    assert type(value) is bool
