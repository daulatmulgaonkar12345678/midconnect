"""
Round 1 SEO regression — B2 URL contract + B5 distinct product descriptions.

Pure-function regression suite over backend/services/seo_service.py:
- every Product JSON-LD, BreadcrumbList JSON-LD, internal link and canonical
  URL uses the real plural /products/{slug} and /categories/{slug} frontend
  routes (no singular /product/{slug} anywhere);
- canonical, Product JSON-LD URL and BreadcrumbList item URLs agree for all
  48 audited product slugs;
- per-product meta descriptions are distinct, factual, length-banded, never
  bake in seller numbers, and never publish broken stored values (the
  panel-fan nine-character description regression).

No database required: everything under test is deterministic.
"""
import os as _os
import sys as _sys

_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
_sys.path.insert(0, _BACKEND)
_sys.path.insert(0, _os.path.join(_BACKEND, "tests"))

from services.seo_service import seo_service, SEO_VERSION

SLUGS = sorted(seo_service.PRODUCT_DESCRIPTION_SEEDS)
SITE = seo_service.SITE_URL
PANEL_FAN_SLUG = "panel-fan-panel-meters-and-accessories-supplier-india"


def _product(slug):
    name = slug.replace("-supplier-india", "").replace("-", " ").title()
    return {"_id": "507f1f77bcf86cd799439011", "name": name, "slug": slug}


def _category():
    return {"name": "Panel Meters & Accessories", "slug": "panel-meters-and-accessories"}


# ----------------------------- B2: URL contract -----------------------------

def test_seo_version_is_v8_url_contract_generation():
    assert SEO_VERSION == 8


def test_48_seed_inventory_present_unique_and_factual():
    assert len(SLUGS) == 48
    seeds = [seo_service.PRODUCT_DESCRIPTION_SEEDS[s] for s in SLUGS]
    assert len(set(seeds)) == 48, "every product needs a distinct seed"
    for slug, seed in zip(SLUGS, seeds):
        normalized = " ".join(seed.split())
        assert len(normalized) >= 40, f"seed too short for {slug}"
        # Facts must come from live caller data, never be baked into the seed.
        assert "verified seller" not in normalized.lower(), slug
        assert "listed with" not in normalized.lower(), slug


def test_panel_fan_broken_description_is_replaced():
    seed = seo_service.PRODUCT_DESCRIPTION_SEEDS[PANEL_FAN_SLUG]
    assert seed.strip().lower() != "panel fan"
    assert len(seed.strip()) >= 40


def test_all_48_payload_url_surfaces_use_plural_routes():
    cat = _category()
    for slug in SLUGS:
        product = _product(slug)

        ld = seo_service.generate_json_ld(product, [], cat["name"])
        assert ld["url"] == f"{SITE}/products/{slug}", slug
        assert ld["description"] and len(ld["description"]) >= 40, slug

        bc = seo_service.generate_breadcrumb_json_ld(
            product["name"], slug, cat["name"], cat["slug"]
        )
        assert bc["itemListElement"][-1]["item"] == f"{SITE}/products/{slug}", slug
        for item in bc["itemListElement"]:
            url = item["item"]
            assert (
                url == SITE
                or url.startswith(f"{SITE}/products")
                or url.startswith(f"{SITE}/categories")
            ), slug


def test_canonical_json_ld_and_breadcrumb_agree_representative_product():
    slug = "vfd-vfd-plc-hmi-control-equipments-supplier-india"
    product = _product(slug)
    cat = _category()

    data = seo_service.generate_complete_seo_data(product, cat, sellers=[])
    ld = seo_service.generate_json_ld(product, [], cat["name"])
    bc = seo_service.generate_breadcrumb_json_ld(
        product["name"], slug, cat["name"], cat["slug"]
    )

    assert data["canonicalUrl"] == f"{SITE}/products/{slug}"
    assert data["canonicalUrl"] == ld["url"]
    assert data["canonicalUrl"] == bc["itemListElement"][-1]["item"]
    assert data["seoVersion"] == SEO_VERSION


def test_complete_seo_payload_has_no_singular_route_anywhere():
    for slug in SLUGS:
        data = seo_service.generate_complete_seo_data(_product(slug), _category(), sellers=[])
        blob = str(data)
        # "/product/" is not a substring of "/products/", so this is exact.
        assert "/product/" not in blob, slug
        assert "/category/" not in blob, slug


def test_internal_links_use_real_routes_only():
    links = seo_service.generate_internal_links(
        "id1",
        "VFD",
        "cat1",
        "Control Equipments",
        "control-equipments",
        similar_products=[{"_id": "s1", "name": "PLC", "slug": "plc-x"}],
        available_cities=["Pune", "Mumbai"],
        product_slug="vfd-x",
    )
    urls = [links["category"]["url"]]
    urls += [p["url"] for p in links["similarProducts"]]
    urls += [c["url"] for c in links["cityPages"]]
    urls += [c["url"] for c in links["intentCityPages"]]
    assert urls, "expected at least one generated internal link"
    for url in urls:
        assert "/product/" not in url and "/category/" not in url, url
        assert url.startswith(f"{SITE}/products") or url.startswith(
            f"{SITE}/categories"
        ), url


# ------------------------- B5: distinct descriptions -------------------------

def test_generated_description_uses_seed_and_live_facts():
    d = seo_service.generate_product_description(
        "Panel Fan", PANEL_FAN_SLUG, 4, 120.0, 450.0, "Panel Meters"
    )
    base = seo_service.PRODUCT_DESCRIPTION_SEEDS[PANEL_FAN_SLUG].rstrip(".")
    assert d.startswith(base)
    assert "4 verified sellers" in d
    assert "₹120" in d and "₹450" in d
    assert 40 <= len(d) <= 165


def test_generated_description_single_seller_wording():
    d = seo_service.generate_product_description(
        "Panel Fan", PANEL_FAN_SLUG, 1, None, None, None
    )
    assert "1 verified seller " in d or d.endswith("1 verified seller.")


def test_generated_description_never_exceeds_natural_band():
    slug = "led-panel-lights-lighting-accessories-supplier-india"
    d = seo_service.generate_product_description(
        "LED Panel Lights", slug, 999, 1000.0, 999999.0, "Lighting"
    )
    base = seo_service.PRODUCT_DESCRIPTION_SEEDS[slug].rstrip(".")
    # Optional sentences (facts, CTAs) are dropped before any hard truncation,
    # so the result is the short factual base — never a mid-word ellipsis.
    assert len(d) <= 165
    assert d == base


def test_unmapped_slug_falls_back_to_templated_generator():
    d = seo_service.generate_product_description(
        "Hydraulic Press Machine", None, 0, None, None, None
    )
    assert isinstance(d, str)
    assert len(d) >= 20


def test_broken_or_name_equal_stored_descriptions_are_rejected():
    name = "Panel Fan"
    assert seo_service.usable_stored_description({"description": "Panel fan"}, name) is None
    assert seo_service.usable_stored_description({"description": name}, name) is None
    assert seo_service.usable_stored_description({}, name) is None
    good = "Panel ventilation fans for control panels and enclosures in industrial plants."
    assert seo_service.usable_stored_description({"description": good}, name) == good
    assert seo_service.usable_stored_description({"seoDescription": good}, name) == good


def test_seeded_descriptions_are_distinct_across_category_neighbours():
    out = {
        slug: seo_service.generate_product_description(
            _product(slug)["name"], slug, 0, None, None, "Panel Meters"
        )
        for slug in SLUGS
    }
    assert len(set(out.values())) == 48, "descriptions must be distinct per product"


# ------------- B4: city page supply gate (disposable DB only) -------------

import asyncio
import os
import uuid

import pytest

_DB_REQUIRED = pytest.mark.skipif(
    not (os.getenv("PHASE1_TEST_MONGO_URL") and os.getenv("PHASE1_TEST_DB_NAME")),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)


@_DB_REQUIRED
class TestCityPageSupplyGate:
    """B4: city pages exist only where eligible supply exists; supplier
    counts, FAQ answers and Product JSON-LD all state the same real count.
    Uses the disposable Phase 1 MongoDB (127.0.0.1:27117) only, and deletes
    exactly the documents it inserted (tagged)."""

    def setup_method(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        from phase1_db_guard import validate_test_target

        url = os.getenv("PHASE1_TEST_MONGO_URL")
        db_name = os.getenv("PHASE1_TEST_DB_NAME")
        validate_test_target(url, db_name)
        self.client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.tag = "R1-" + uuid.uuid4().hex[:8]

    def teardown_method(self):
        # Fresh client: the setup client is bound to the per-test event loop
        # that asyncio.run has already closed by teardown time.
        from motor.motor_asyncio import AsyncIOMotorClient

        url = os.getenv("PHASE1_TEST_MONGO_URL")
        db_name = os.getenv("PHASE1_TEST_DB_NAME")
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)

        async def _clean():
            db = client[db_name]
            await db.users.delete_many({"tag": self.tag})
            await db.products.delete_many({"tag": self.tag})
            await db.sellerListings.delete_many({"tag": self.tag})

        asyncio.run(_clean())
        client.close()
        try:
            self.client.close()
        except Exception:
            pass

    async def _seed(self):
        """Pune: 2 eligible sellers (+1 deleted ignored). Nagpur: only a
        suspended and a deactivated seller (no eligible supply). Surat: one
        eligible seller with TWO listings (distinct-seller counting)."""
        from bson import ObjectId

        async def _do():
            sellers = {}
            overrides = {
                "deleted": {"accountStatus": "deleted"},
                "suspended": {"sellerStatus": "suspended"},
                "inactive": {"isActive": False},
            }
            for name in ["active1", "active2", "deleted", "suspended", "inactive"]:
                uid = ObjectId()
                await self.db.users.insert_one({
                    "_id": uid, "role": "seller", "tag": self.tag,
                    "isActive": True, "accountStatus": "active", **overrides.get(name, {}),
                })
                sellers[name] = uid
            pid = ObjectId()
            await self.db.products.insert_one({
                "_id": pid, "tag": self.tag, "name": "Panel Fan",
                "slug": f"{self.tag}-panel-fan", "isActive": True,
            })

            def listing(seller, city, price):
                return {
                    "tag": self.tag, "status": "active", "sellerId": sellers[seller],
                    "productId": pid, "city": city,
                    "pricingTiers": [{"pricePerUnit": price}],
                }

            await self.db.sellerListings.insert_many([
                listing("active1", "Pune", 120.0),
                listing("active2", "Pune", 450.0),
                listing("deleted", "Pune", 1.0),      # must NOT count or display
                listing("suspended", "Nagpur", 5.0),  # must NOT count
                listing("inactive", "Nagpur", 6.0),   # must NOT count
                listing("active1", "Surat", 90.0),
                listing("active1", "Surat", 95.0),    # same seller again: 1 supplier
            ])
            return pid

        await _do()
        return None

    async def _page(self, slug, city):
        from services.city_seo_service import create_city_seo_service

        svc = create_city_seo_service(self.db)
        return await svc.get_city_page_data(slug, city)

    def test_counts_distinct_eligible_sellers_with_real_prices(self):
        async def scenario():
            # Motor binds to the loop of its first operation: seed and query
            # inside ONE asyncio.run so the client never faces a closed loop.
            await self._seed()
            return await self._page(f"{self.tag}-panel-fan", "Pune")

        data = asyncio.run(scenario())
        assert data is not None
        assert data["stats"]["sellerCount"] == 2
        assert data["stats"]["minPrice"] == 120.0
        assert len(data["sellers"]) == 2, "deleted seller must not be displayed"
        desc = data["seo"]["jsonLd"]["description"]
        assert "2 verified suppliers in Pune" in desc
        faq_answer = data["seo"]["faqJsonLd"]["mainEntity"][0]["acceptedAnswer"]["text"]
        assert "2 verified suppliers" in faq_answer

    def test_zero_supply_city_returns_none(self):
        async def scenario():
            await self._seed()
            slug = f"{self.tag}-panel-fan"
            nagpur = await self._page(slug, "Nagpur")
            mumbai = await self._page(slug, "Mumbai")
            return nagpur, mumbai

        nagpur, mumbai = asyncio.run(scenario())
        assert nagpur is None
        assert mumbai is None

    def test_single_supplier_distinct_count_and_singular_wording(self):
        async def scenario():
            await self._seed()
            return await self._page(f"{self.tag}-panel-fan", "Surat")

        data = asyncio.run(scenario())
        assert data is not None
        assert data["stats"]["sellerCount"] == 1, "same seller twice counts once"
        assert data["stats"]["minPrice"] == 90.0
        desc = data["seo"]["jsonLd"]["description"]
        assert "1 verified supplier in Surat" in desc
        assert "1 verified suppliers" not in desc
