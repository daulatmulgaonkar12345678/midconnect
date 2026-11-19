"""
Phase 1 — 20-case eligibility regression matrix (disposable MongoDB only).

Runs against PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME. Skips when unset.
Every test uses unique product/seller ids (prefix P1T-) and deletes only what it inserted.
"""
import asyncio
import os
import uuid

import pytest
from bson import ObjectId

import os as _os
import sys as _sys
_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
_sys.path.insert(0, _BACKEND)
_sys.path.insert(0, _os.path.join(_BACKEND, "tests"))
from phase1_db_guard import validate_test_target, UnsafeTestDatabase
from services.city_eligibility_service import fetch_eligible_pairs, PairOverflowError

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)

CITY = "pune"


def _run(coro):
    return asyncio.run(coro)


class Harness:
    """Creates a fresh Motor client per test run and tracks inserted ids for cleanup."""

    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        validate_test_target(URL, DB_NAME)
        self.client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        self.db = self.client[DB_NAME]
        self.tag = "P1T-" + uuid.uuid4().hex[:8]
        self.users, self.products, self.listings = [], [], []

    def user(self, **fields):
        uid = ObjectId()
        doc = {"_id": uid, "role": "seller", "tag": self.tag, "isActive": True,
               "accountStatus": "active", **fields}
        self.users.append(uid)
        return doc

    async def insert_user(self, **fields):
        doc = self.user(**fields)
        await self.db.users.insert_one(doc)
        return doc["_id"]

    async def product(self, slug=None, **fields):
        pid = ObjectId()
        doc = {"_id": pid, "tag": self.tag, "name": "p", "slug": slug or f"{self.tag}-prod",
               "isActive": True, **fields}
        await self.db.products.insert_one(doc)
        self.products.append(pid)
        return doc

    async def listing(self, seller_id, product_id, city="pune", tiers=None, **fields):
        doc = {"_id": ObjectId(), "tag": self.tag, "status": "active", "sellerId": seller_id,
               "productId": product_id, "city": city, "pricingTiers": tiers or [], **fields}
        await self.db.sellerListings.insert_one(doc)
        self.listings.append(doc["_id"])
        return doc

    async def cleanup(self):
        await self.db.sellerListings.delete_many({"tag": self.tag})
        await self.db.products.delete_many({"tag": self.tag})
        await self.db.users.delete_many({"tag": self.tag})
        self.client.close()


async def _eval(h: Harness, allowed=None, max_pairs=1000):
    rows = await fetch_eligible_pairs(h.db, allowed or [CITY], max_pairs)
    return [r for r in rows if r["productSlug"].startswith(h.tag)]


def _scenario(build):
    """Run an async scenario with a fresh harness, always cleaning up."""
    async def go():
        h = Harness()
        try:
            await build(h)
            return await _eval(h)
        finally:
            await h.cleanup()
    return _run(go())


def _one(rows):
    assert len(rows) == 1, rows
    return rows[0]


GOOD_TIER = [{"pricePerUnit": 12.5}]


def test_01_active_seller_numeric_price_one_seller():
    async def s(h):
        sid = await h.insert_user(sellerStatus="active")
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    r = _one(_scenario(s))
    assert r["cityEligible"] and r["priceEligible"] and not r["suppliersEligible"]


def test_02_deleted_seller_excluded():
    async def s(h):
        sid = await h.insert_user(accountStatus="deleted")
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert _scenario(s) == []


def test_03_inactive_seller_excluded():
    async def s(h):
        sid = await h.insert_user(isActive=False)
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert _scenario(s) == []


@pytest.mark.parametrize("status", ["suspended", "banned"])
def test_04_suspended_or_banned_seller_excluded(status):
    async def s(h):
        sid = await h.insert_user(sellerStatus=status)
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert _scenario(s) == []


def test_05_canlogin_false_alone_not_excluded():
    async def s(h):
        sid = await h.insert_user(canLogin=False)
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert _one(_scenario(s))["cityEligible"]


def test_06_inactive_product_excluded():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product(isActive=False)
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert _scenario(s) == []


def test_07_no_valid_price_city_true_price_false():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=[])
    r = _one(_scenario(s))
    assert r["cityEligible"] and not r["priceEligible"]


def test_08_positive_numeric_price_true():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=[{"pricePerUnit": 12.5}])
    assert _one(_scenario(s))["priceEligible"]


@pytest.mark.parametrize("value", [0, -3, None])
def test_09_10_11_zero_negative_null_price_false(value):
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=[{"pricePerUnit": value}])
    r = _one(_scenario(s))
    assert r["cityEligible"] and not r["priceEligible"]


def test_12_string_price_not_numeric_false():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=[{"pricePerUnit": "12"}])
    assert not _one(_scenario(s))["priceEligible"]


def test_13_zero_tier_with_legacy_price_no_fallback():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=[{"pricePerUnit": 0}], price=5)
    assert not _one(_scenario(s))["priceEligible"]


def test_14_two_listings_one_seller_not_suppliers():
    async def s(h):
        sid = await h.insert_user()
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
        await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    assert not _one(_scenario(s))["suppliersEligible"]


def test_15_two_distinct_sellers_suppliers_true():
    async def s(h):
        a = await h.insert_user()
        b = await h.insert_user()
        p = await h.product()
        await h.listing(a, p["_id"], tiers=GOOD_TIER)
        await h.listing(b, p["_id"], tiers=GOOD_TIER)
    assert _one(_scenario(s))["suppliersEligible"]


def test_16_intents_evaluated_independently():
    async def s(h):
        a = await h.insert_user()
        b = await h.insert_user()
        p = await h.product()
        await h.listing(a, p["_id"], tiers=[])            # city only
        await h.listing(b, p["_id"], tiers=GOOD_TIER)     # price + second seller
    r = _one(_scenario(s))
    assert r["cityEligible"] and r["priceEligible"] and r["suppliersEligible"]

    async def s2(h):
        a = await h.insert_user()
        p = await h.product()
        await h.listing(a, p["_id"], tiers=[])
    r2 = _one(_scenario(s2))
    assert r2["cityEligible"] and not r2["priceEligible"] and not r2["suppliersEligible"]


def test_17_listing_without_seller_document_excluded():
    async def s(h):
        p = await h.product()
        await h.listing(ObjectId(), p["_id"], tiers=GOOD_TIER)  # orphan sellerId
    assert _scenario(s) == []


def test_18_large_city_counted_completely():
    async def s(h):
        p = await h.product()
        for _ in range(60):  # 60 sellers, all in one city: no row cap truncation
            sid = await h.insert_user()
            await h.listing(sid, p["_id"], tiers=GOOD_TIER)
    r = _one(_scenario(s))
    assert r["suppliersEligible"] and r["listings"] == 60


def test_19_group_overflow_fails_loudly():
    async def s(h):
        for i in range(3):
            sid = await h.insert_user()
            p = await h.product(slug=f"{h.tag}-prod-{i}")
            await h.listing(sid, p["_id"], tiers=GOOD_TIER)

    async def go():
        h = Harness()
        try:
            await s(h)
            await fetch_eligible_pairs(h.db, [CITY], max_pairs=1)
        finally:
            await h.cleanup()

    with pytest.raises(PairOverflowError):
        _run(go())


def test_20_listing_level_city_matches_without_seller_profile_city():
    # Documented difference: the eligibility pipeline matches listing-level `city`,
    # while the legacy seller-backed path matches only seller.profile.city.
    async def s(h):
        sid = await h.insert_user()  # seller.profile.city not set
        p = await h.product()
        await h.listing(sid, p["_id"], tiers=GOOD_TIER, city="pune")
    assert _one(_scenario(s))["cityEligible"]
