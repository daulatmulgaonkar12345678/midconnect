"""
F1 seller-count semantics — regression tests (disposable MongoDB only).

Runs against PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME. Skips when unset.

Verifies the three distinct seller-count surfaces after the F1 fix, on one
seeded product with deliberately mixed seller health:

- listingCount        = ALL active listings (6), even ones whose seller is
                        banned / deleted / deactivated or missing entirely;
- sellerCount         = DISTINCT ELIGIBLE sellers (2) under the approved
                        Phase 1 rules — the authoritative supplier count;
- verifiedSellerCount = eligible sellers with users.gst.verified (1).

Checked on: the seller-stats service, /api/products/{slug}/seo,
/api/products/{slug} and /api/products/{id}/enterprise — plus the generated
description/JSON-LD, which must carry the eligible-seller number and never
the listing count.
"""
import asyncio
import os
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
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield client


class Seed:
    """One product, six listings across five sellers of mixed health."""

    def __init__(self):
        self.tag = "f1-" + uuid.uuid4().hex[:8]
        self.slug = f"{self.tag}-widget"
        self.product_id = ObjectId()
        self.seller_ok_verified = ObjectId()   # eligible + gst.verified (2 listings)
        self.seller_ok_plain = ObjectId()      # eligible, not verified (1 listing)
        self.seller_banned = ObjectId()        # excluded by sellerStatus
        self.seller_deleted = ObjectId()       # excluded by accountStatus
        self.seller_inactive = ObjectId()      # excluded by isActive False

    def user_docs(self):
        return [
            {"_id": self.seller_ok_verified, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "active", "sellerStatus": "approved",
             "gst": {"verified": True},
             "profile": {"city": "pune", "businessName": "Alpha Works"}},
            {"_id": self.seller_ok_plain, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "active", "sellerStatus": "approved",
             "gst": {"verified": False},
             "profile": {"city": "delhi", "businessName": "Beta Traders"}},
            {"_id": self.seller_banned, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "active", "sellerStatus": "banned",
             "gst": {"verified": True},
             "profile": {"city": "pune", "businessName": "Banned Co"}},
            {"_id": self.seller_deleted, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "deleted", "sellerStatus": "approved",
             "gst": {"verified": True},
             "profile": {"city": "pune", "businessName": "Deleted Co"}},
            {"_id": self.seller_inactive, "role": "seller", "tag": self.tag,
             "isActive": False, "accountStatus": "active", "sellerStatus": "approved",
             "gst": {"verified": True},
             "profile": {"city": "pune", "businessName": "Inactive Co"}},
        ]

    def product_doc(self):
        return {"_id": self.product_id, "tag": self.tag, "name": "F1 Widget",
                "slug": self.slug, "isActive": True}

    def listing_docs(self):
        def listing(seller_id, listing_is_active=True):
            return {"_id": ObjectId(), "tag": self.tag, "productId": self.product_id,
                    "sellerId": seller_id, "status": "active",
                    "isActive": listing_is_active, "pricingTiers": [], "moq": 1}

        return [
            listing(self.seller_ok_verified),
            listing(self.seller_ok_verified),
            listing(self.seller_ok_plain),
            listing(self.seller_banned),
            listing(self.seller_deleted),
            listing(self.seller_inactive),
            listing(ObjectId()),  # seller document missing entirely
        ]

    @property
    def expected(self):
        # 7 active listings; 2 distinct eligible sellers; 1 of them verified.
        return {"listingCount": 7, "sellerCount": 2, "verifiedSellerCount": 1}


@pytest.fixture
def seeded(app_module, shared_client):
    seed = Seed()
    client = shared_client

    async def insert():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            db = c[DB_NAME]
            await db.users.insert_many(seed.user_docs())
            await db.products.insert_one(seed.product_doc())
            await db.sellerListings.insert_many(seed.listing_docs())
        finally:
            c.close()

    async def cleanup():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            db = c[DB_NAME]
            await db.users.delete_many({"tag": seed.tag})
            await db.products.delete_many({"tag": seed.tag})
            await db.sellerListings.delete_many({"tag": seed.tag})
        finally:
            c.close()

    client.portal.call(insert)
    try:
        yield seed
    finally:
        client.portal.call(cleanup)


def test_service_counts_are_distinct_and_authoritative():
    """The seller-stats service reports all three counts from one aggregation."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from services.seller_stats_service import fetch_product_seller_stats

    validate_test_target(URL, DB_NAME)

    async def scenario():
        seed = Seed()
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            db = client[DB_NAME]
            await db.users.insert_many(seed.user_docs())
            await db.products.insert_one(seed.product_doc())
            await db.sellerListings.insert_many(seed.listing_docs())
            stats = await fetch_product_seller_stats(db, seed.product_id)
            return stats, seed.expected
        finally:
            client.close()

    stats, expected = asyncio.run(scenario())
    assert stats["listingCount"] == expected["listingCount"]
    assert stats["sellerCount"] == expected["sellerCount"]
    assert stats["verifiedSellerCount"] == expected["verifiedSellerCount"]


def test_seo_payload_distinguishes_listings_sellers_verified(shared_client, seeded):
    seed = seeded
    resp = shared_client.get(f"/api/products/{seed.slug}/seo")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["sellerCount"] == seed.expected["sellerCount"]
    assert data["listingCount"] == seed.expected["listingCount"]
    assert data["verifiedSellerCount"] == seed.expected["verifiedSellerCount"]

    # Generated copy carries the ELIGIBLE seller number, never the listing count.
    assert f"{seed.expected['sellerCount']}+ verified sellers" in data["seoDescription"]
    assert f"{seed.expected['listingCount']}+ verified sellers" not in data["seoDescription"]
    assert f"{seed.expected['sellerCount']}+ verified sellers" in data["jsonLd"]["description"]

    # Cards shown are only from counted eligible sellers (2 + 1 listings).
    cards = [s for group in data["sellersByCity"].values() for s in group]
    assert len(cards) == 3
    assert {c["companyName"] for c in cards} == {"Alpha Works", "Beta Traders"}


def test_product_detail_counts_are_eligible_sellers_not_cards(shared_client, seeded):
    seed = seeded
    resp = shared_client.get(f"/api/products/detail/{seed.slug}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["sellerCount"] == seed.expected["sellerCount"]
    assert data["listingCount"] == seed.expected["listingCount"]
    assert data["verifiedSellerCount"] == seed.expected["verifiedSellerCount"]


def test_enterprise_summary_matches_authoritative_counts(shared_client, seeded):
    seed = seeded
    resp = shared_client.get(f"/api/products/{seed.product_id}/enterprise")
    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]

    assert summary["sellerCount"] == seed.expected["sellerCount"]
    assert summary["listingCount"] == seed.expected["listingCount"]
    assert summary["verifiedSellerCount"] == seed.expected["verifiedSellerCount"]
