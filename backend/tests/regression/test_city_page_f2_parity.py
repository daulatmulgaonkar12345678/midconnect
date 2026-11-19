"""
F2 city-page eligibility — parity and FAQ-consistency regression (disposable DB).

Runs against PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME. Skips when unset.

Verifies, on seeded data with mixed seller health:

- the city-page eligibility check (city_seo_service) and the sitemap
  eligibility aggregation (city_eligibility_service) agree: a page exists for
  exactly the pairs the sitemap emits (no zero-eligible-supply pages);
- stats.sellerCount is the DISTINCT ELIGIBLE seller count, and the FAQ
  JSON-LD and Product JSON-LD quote exactly that same number;
- a product-city pair whose only supply is ineligible returns no page data
  (the route 404s) and produces no sitemap pair.
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
from phase1_db_guard import validate_test_target
from services.city_eligibility_service import fetch_eligible_pairs
from services.city_seo_service import create_city_seo_service

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)

CITY = "pune"


class Seed:
    """Two products: P has one eligible seller; Q has only banned supply."""

    def __init__(self):
        self.tag = "f2-" + uuid.uuid4().hex[:8]
        self.slug_p = f"{self.tag}-widget"
        self.slug_q = f"{self.tag}-ghost"
        self.product_p = ObjectId()
        self.product_q = ObjectId()
        self.seller_ok = ObjectId()   # eligible, 2 listings, one priced
        self.seller_banned = ObjectId()
        self.seller_deleted = ObjectId()

    def docs(self):
        users = [
            {"_id": self.seller_ok, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "active", "sellerStatus": "approved",
             "profile": {"city": "Pune", "businessName": "Alpha Works"}},
            {"_id": self.seller_banned, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "active", "sellerStatus": "banned",
             "profile": {"city": "Pune", "businessName": "Banned Co"}},
            {"_id": self.seller_deleted, "role": "seller", "tag": self.tag,
             "isActive": True, "accountStatus": "deleted", "sellerStatus": "approved",
             "profile": {"city": "Pune", "businessName": "Deleted Co"}},
        ]
        products = [
            {"_id": self.product_p, "tag": self.tag, "name": "F2 Widget",
             "slug": self.slug_p, "isActive": True},
            {"_id": self.product_q, "tag": self.tag, "name": "F2 Ghost",
             "slug": self.slug_q, "isActive": True},
        ]

        def listing(product_id, seller_id, priced=False):
            tiers = [{"pricePerUnit": 100, "minQty": 1}] if priced else []
            return {"_id": ObjectId(), "tag": self.tag, "productId": product_id,
                    "sellerId": seller_id, "status": "active", "isActive": True,
                    "city": CITY, "pricingTiers": tiers, "moq": 1}

        listings = [
            listing(self.product_p, self.seller_ok),
            listing(self.product_p, self.seller_ok, priced=True),
            listing(self.product_p, self.seller_banned, priced=True),
            listing(self.product_p, self.seller_deleted, priced=True),
            listing(self.product_q, self.seller_banned, priced=True),  # Q: zero eligible supply
        ]
        return users, products, listings


async def _scenario():
    seed = Seed()
    from motor.motor_asyncio import AsyncIOMotorClient
    validate_test_target(URL, DB_NAME)
    client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
    try:
        db = client[DB_NAME]
        users, products, listings = seed.docs()
        await db.users.insert_many(users)
        await db.products.insert_many(products)
        await db.sellerListings.insert_many(listings)

        service = create_city_seo_service(db)
        pairs = await fetch_eligible_pairs(db, [CITY], 1000)
        page_p = await service.get_city_page_data(seed.slug_p, CITY)
        page_q = await service.get_city_page_data(seed.slug_q, CITY)
        elig_p = await service.check_city_page_eligibility(seed.product_p, CITY)
        elig_q = await service.check_city_page_eligibility(seed.product_q, CITY)
        elig_p_upper = await service.check_city_page_eligibility(seed.product_p, "PUNE")
        return seed, pairs, page_p, page_q, elig_p, elig_q, elig_p_upper
    finally:
        for coll in ("users", "products", "sellerListings"):
            await db[coll].delete_many({"tag": seed.tag})
        client.close()


def _pairs_for(pairs, slug):
    return [p for p in pairs if p["productSlug"] == slug]


def test_city_page_and_sitemap_eligibility_agree():
    seed, pairs, page_p, page_q, elig_p, elig_q, elig_p_upper = asyncio.run(_scenario())

    rows_p = _pairs_for(pairs, seed.slug_p)
    assert len(rows_p) == 1, f"expected exactly one sitemap pair for P, got {rows_p}"
    row_p = rows_p[0]
    assert row_p["cityEligible"] is True and elig_p[0] is True
    assert row_p["priceEligible"] is True
    assert row_p["suppliersEligible"] is False  # 1 distinct eligible seller
    # Sitemap counts eligible LISTINGS (2); the page counts DISTINCT sellers
    # (1) — different measures over the same eligible supply, same boolean.
    assert row_p["listings"] == 2
    assert elig_p[1] == 1

    # Q has only banned supply: no sitemap pair AND no page (404 upstream).
    assert _pairs_for(pairs, seed.slug_q) == []
    assert page_q is None
    assert elig_q == (False, 0)

    # Case-insensitive city resolution matches the normalized sitemap city.
    assert elig_p_upper == elig_p


def test_page_counts_and_faq_json_ld_quote_eligible_sellers():
    seed, pairs, page_p, page_q, elig_p, elig_q, elig_p_upper = asyncio.run(_scenario())

    assert page_p is not None
    assert page_p["stats"]["sellerCount"] == 1

    # Visible cards: only the counted eligible seller's listings.
    assert len(page_p["sellers"]) == 2
    assert {s["companyName"] for s in page_p["sellers"]} == {"Alpha Works"}

    # FAQ JSON-LD quotes the same number the page displays.
    faq = page_p["seo"]["faqJsonLd"]["mainEntity"]
    assert "1 verified supplier" in faq[0]["acceptedAnswer"]["text"]
    assert "0 verified" not in faq[0]["acceptedAnswer"]["text"]

    # Product JSON-LD agrees with the page.
    assert "1 verified supplier" in page_p["seo"]["jsonLd"]["description"]
    assert page_p["seo"]["jsonLd"]["offers"]["price"] == 100


def test_two_eligible_sellers_flip_suppliers_intent_and_counts():
    """Second scenario: a second eligible seller satisfies the suppliers intent."""
    seed = Seed()
    # Rebuild the seed with one extra eligible seller sharing product P.
    from motor.motor_asyncio import AsyncIOMotorClient
    validate_test_target(URL, DB_NAME)

    async def scenario():
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        try:
            db = client[DB_NAME]
            seller_two = ObjectId()
            users, products, listings = seed.docs()
            users.append({
                "_id": seller_two, "role": "seller", "tag": seed.tag,
                "isActive": True, "accountStatus": "active", "sellerStatus": "approved",
                "profile": {"city": "Pune", "businessName": "Beta Traders"},
            })
            listings.append({
                "_id": ObjectId(), "tag": seed.tag, "productId": seed.product_p,
                "sellerId": seller_two, "status": "active", "isActive": True,
                "city": CITY, "pricingTiers": [{"pricePerUnit": 150, "minQty": 1}],
                "moq": 1,
            })
            await db.users.insert_many(users)
            await db.products.insert_many(products)
            await db.sellerListings.insert_many(listings)

            service = create_city_seo_service(db)
            pairs = await fetch_eligible_pairs(db, [CITY], 1000)
            row = [p for p in pairs if p["productSlug"] == seed.slug_p][0]
            page = await service.get_city_page_data(seed.slug_p, CITY)
            elig = await service.check_city_page_eligibility(seed.product_p, CITY)
            return row, page, elig
        finally:
            for coll in ("users", "products", "sellerListings"):
                await db[coll].delete_many({"tag": seed.tag})
            client.close()

    row, page, elig = asyncio.run(scenario())
    assert row["suppliersEligible"] is True   # 2 distinct eligible sellers
    assert row["cityEligible"] is True and elig[0] is True
    assert elig[1] == 2 and page["stats"]["sellerCount"] == 2
    faq = page["seo"]["faqJsonLd"]["mainEntity"]
    assert "2 verified suppliers" in faq[0]["acceptedAnswer"]["text"]
    assert "1 verified supplier" not in faq[0]["acceptedAnswer"]["text"]


def test_city_payload_self_urls_use_apex_origin():
    """Batch 2: city payload self URLs always use the approved apex origin.

    Production evidence (2026-11-19): a cached city payload captured before the
    backend apex switch served a stale www canonical/og:url from the frontend
    for up to one revalidation window. Frontend emission now re-anchors every
    payload URL on the apex origin via the frontend site URL helper
    `canonicalSelfUrl`; this test additionally pins the payload source itself:
    canonicalUrl, pageUrl, cityPageUrl and the intent+city link family must be
    apex-anchored and never carry a www host.
    """
    seed, pairs, page_p, page_q, elig_p, elig_q, elig_p_upper = asyncio.run(_scenario())

    assert page_p is not None
    seo = page_p["seo"]
    for key in ("canonicalUrl", "pageUrl", "cityPageUrl"):
        url = seo[key]
        assert url.startswith("https://udyogconnect.in/"), f"seo.{key} not apex: {url}"
        assert "www." not in url, f"seo.{key} carries a www host: {url}"
    assert seo["canonicalUrl"] == f"https://udyogconnect.in/products/{seed.slug_p}"
    assert seo["pageUrl"] == f"https://udyogconnect.in/products/{seed.slug_p}/in/{CITY}"

    # The intent+city URL family is built by the same apex-anchored templates.
    links = page_p["internalLinks"]
    assert links["mainProductPage"] == f"https://udyogconnect.in/products/{seed.slug_p}"
    for link in links["relatedIntents"]:
        assert link["url"].startswith("https://udyogconnect.in/products/"), f"intent link not apex: {link['url']}"
        assert "www." not in link["url"], f"intent link carries a www host: {link['url']}"
