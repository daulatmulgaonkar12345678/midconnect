"""
SEO Phase 2 Enhancement Tests for UdyogConnect B2B marketplace.
Tests the backend SEO endpoints and frontend SSR JSON-LD injection.

Coverage:
- GET /api/products/{slug}/seo — title, description, content, JSON-LD schemas
- GET /api/products/{slug}/city/{city} — city-scoped SEO + JSON-LD
- GET /api/products/{slug}/city/{invalid} — 404 handling
- Bulk update script (--dry-run, --force, SEO_VERSION check)
- Frontend SSR: /products/{slug} and /products/{slug}/in/{city} HTML JSON-LD injection
- No duplicate JSON-LD on city pages
"""
import os
import re
import json
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
PRODUCT_SLUG = "ss304-round-bar-steel-raw-materials-supplier-india"
FALLBACK_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"
CITY = "mumbai"
INVALID_CITY = "nowhereville123xyz"


# ---------- Backend API Tests ----------
class TestProductSeoEndpoint:
    """GET /api/products/{slug}/seo validations for Phase 2"""

    @pytest.fixture(scope="class")
    def seo_payload(self):
        for slug in (PRODUCT_SLUG, FALLBACK_SLUG):
            r = requests.get(f"{BASE_URL}/api/products/{slug}/seo", timeout=30)
            if r.status_code == 200:
                return slug, r.json()
        pytest.skip("No test product found for SEO endpoint")

    def test_status_and_structure(self, seo_payload):
        _, data = seo_payload
        assert "seoTitle" in data and "seoDescription" in data and "seoContent" in data
        assert "jsonLd" in data, "jsonLd must be present (Phase 2)"
        assert "breadcrumbJsonLd" in data, "breadcrumbJsonLd must be present (Phase 2)"
        assert "faqJsonLd" in data, "faqJsonLd must be present (Phase 2)"

    def test_title_length(self, seo_payload):
        _, data = seo_payload
        tlen = len(data["seoTitle"])
        assert 30 <= tlen <= 65, f"seoTitle length {tlen} not in 30-65"

    def test_description_length(self, seo_payload):
        _, data = seo_payload
        dlen = len(data["seoDescription"])
        assert 120 <= dlen <= 160, f"seoDescription length {dlen} not in 120-160"

    def test_content_words_and_sections(self, seo_payload):
        _, data = seo_payload
        content = data["seoContent"]
        wc = len(content.split())
        assert wc >= 400, f"seoContent has only {wc} words (<400)"
        low = content.lower()
        assert "frequently asked" in low, "missing 'frequently asked' section"
        assert "market insights" in low, "missing 'market insights' section"

    def test_product_jsonld(self, seo_payload):
        _, data = seo_payload
        j = data["jsonLd"]
        assert j.get("@context") == "https://schema.org" or j.get("@context") == "schema.org"
        assert j.get("@type") == "Product"
        assert "offers" in j, "Product JSON-LD must include offers"
        offers = j["offers"]
        # AggregateOffer preferred
        if isinstance(offers, dict):
            assert offers.get("@type") in ("AggregateOffer", "Offer")

    def test_breadcrumb_jsonld(self, seo_payload):
        _, data = seo_payload
        b = data["breadcrumbJsonLd"]
        assert b.get("@type") == "BreadcrumbList"
        items = b.get("itemListElement", [])
        assert 3 <= len(items) <= 4, f"breadcrumb items {len(items)} not in 3-4"

    def test_faq_jsonld(self, seo_payload):
        _, data = seo_payload
        f = data["faqJsonLd"]
        assert f.get("@type") == "FAQPage"
        me = f.get("mainEntity", [])
        assert len(me) >= 3, f"FAQ has only {len(me)} questions (<3)"

    def test_regression_fields_still_present(self, seo_payload):
        _, data = seo_payload
        for key in ("sellerCount", "minPrice", "maxPrice", "canonicalUrl", "internalLinks", "sellersByCity"):
            assert key in data, f"Missing regression field: {key}"


# ---------- City Page Tests ----------
class TestCityPageEndpoint:
    """GET /api/products/{slug}/city/{city}"""

    @pytest.fixture(scope="class")
    def city_payload(self):
        for slug in (PRODUCT_SLUG, FALLBACK_SLUG):
            r = requests.get(f"{BASE_URL}/api/products/{slug}/city/{CITY}", timeout=30)
            if r.status_code == 200:
                return slug, r.json()
        pytest.skip("No test product with city data")

    def test_city_seo_structure(self, city_payload):
        _, data = city_payload
        seo = data.get("seo") or data
        assert "title" in seo or "seoTitle" in seo
        assert "description" in seo or "seoDescription" in seo

    def test_city_content_length(self, city_payload):
        _, data = city_payload
        seo = data.get("seo") or data
        content = seo.get("seoContent") or seo.get("content") or ""
        wc = len(content.split())
        assert wc >= 400, f"city seoContent has only {wc} words (<400)"

    def test_city_product_jsonld_area_served(self, city_payload):
        _, data = city_payload
        seo = data.get("seo") or data
        j = seo.get("jsonLd")
        assert j, "city seo must include jsonLd"
        assert j.get("@type") == "Product"
        area = j.get("areaServed")
        # areaServed can be dict or list of dicts
        if isinstance(area, list):
            names = [a.get("name", "").lower() for a in area if isinstance(a, dict)]
            assert any(CITY in n for n in names), f"areaServed.name missing city. Got: {names}"
        elif isinstance(area, dict):
            assert CITY in area.get("name", "").lower(), f"areaServed.name={area.get('name')}"
        else:
            pytest.fail(f"areaServed missing or wrong type: {area}")

    def test_city_breadcrumb_jsonld(self, city_payload):
        _, data = city_payload
        seo = data.get("seo") or data
        b = seo.get("breadcrumbJsonLd")
        assert b, "city breadcrumbJsonLd missing"
        items = b.get("itemListElement", [])
        assert len(items) == 4, f"city breadcrumb should have 4 items (Home/Products/Product/City), got {len(items)}"

    def test_city_faq_jsonld(self, city_payload):
        _, data = city_payload
        seo = data.get("seo") or data
        f = seo.get("faqJsonLd")
        assert f, "city faqJsonLd missing"
        me = f.get("mainEntity", [])
        assert len(me) >= 3, f"city FAQ has only {len(me)} questions (<3)"

    def test_invalid_city_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/products/{PRODUCT_SLUG}/city/{INVALID_CITY}", timeout=30)
        assert r.status_code == 404, f"expected 404 for invalid city, got {r.status_code}"


# ---------- Bulk Update Script ----------
class TestBulkUpdateScript:
    SCRIPT = "/app/backend/scripts/update_seo_for_all_products.py"

    def test_script_exists(self):
        assert os.path.exists(self.SCRIPT), f"Bulk script missing: {self.SCRIPT}"

    def test_dry_run(self):
        r = subprocess.run(
            ["python3", self.SCRIPT, "--dry-run"],
            capture_output=True, text=True, timeout=120, cwd="/app/backend"
        )
        assert r.returncode == 0, f"dry-run failed: stderr={r.stderr[:500]}"
        combined = (r.stdout + r.stderr).lower()
        assert "dry" in combined or "would update" in combined or "skipping" in combined or "no products" in combined, \
            f"dry-run output unexpected: {r.stdout[:500]}"

    def test_seo_version_check_in_code(self):
        with open(self.SCRIPT) as f:
            src = f.read()
        assert "SEO_VERSION" in src, "Script must reference SEO_VERSION"
        assert "seoVersion" in src, "Script must read/write seoVersion field"
        # Should have a comparison
        assert ("<" in src and "SEO_VERSION" in src), "Script should compare seoVersion<SEO_VERSION"

    def test_seo_version_constant(self):
        with open("/app/backend/services/seo_service.py") as f:
            src = f.read()
        m = re.search(r"SEO_VERSION\s*=\s*(\d+)", src)
        assert m, "SEO_VERSION constant missing in seo_service.py"
        assert int(m.group(1)) >= 3, f"SEO_VERSION must be >=3, got {m.group(1)}"


# ---------- Frontend SSR JSON-LD ----------
def _extract_jsonld_scripts(html):
    """Extract all <script type='application/ld+json'> blocks and their data-testid."""
    # Match script tags with application/ld+json (allow attributes in any order)
    pattern = re.compile(
        r'<script\b([^>]*type=["\']application/ld\+json["\'][^>]*)>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    results = []
    for m in pattern.finditer(html):
        attrs = m.group(1)
        body = m.group(2).strip()
        tid = re.search(r'data-testid=["\']([^"\']+)["\']', attrs)
        results.append({
            "testid": tid.group(1) if tid else None,
            "body": body,
        })
    return results


class TestFrontendMainProductSSR:
    """GET /products/{slug} — must include 4 JSON-LD blocks with data-testid"""

    @pytest.fixture(scope="class")
    def html(self):
        url = f"{BASE_URL}/products/{PRODUCT_SLUG}"
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 seo-test"})
        if r.status_code != 200:
            # try fallback slug
            url = f"{BASE_URL}/products/{FALLBACK_SLUG}"
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 seo-test"})
        assert r.status_code == 200, f"product page returned {r.status_code}"
        return r.text

    def test_has_4_jsonld_blocks(self, html):
        scripts = _extract_jsonld_scripts(html)
        testids = [s["testid"] for s in scripts if s["testid"]]
        expected = {"product-jsonld", "breadcrumb-jsonld", "faq-jsonld", "org-jsonld"}
        missing = expected - set(testids)
        assert not missing, f"Missing JSON-LD blocks: {missing}. Found: {testids}"

    def test_each_jsonld_is_valid_json_and_schema_org(self, html):
        scripts = _extract_jsonld_scripts(html)
        target_ids = {"product-jsonld", "breadcrumb-jsonld", "faq-jsonld", "org-jsonld"}
        for s in scripts:
            if s["testid"] in target_ids:
                try:
                    obj = json.loads(s["body"])
                except json.JSONDecodeError as e:
                    pytest.fail(f"JSON-LD {s['testid']} invalid JSON: {e}. Body snippet: {s['body'][:200]}")
                ctx = obj.get("@context", "") if isinstance(obj, dict) else ""
                assert "schema.org" in str(ctx), f"{s['testid']} @context missing schema.org: {ctx}"


class TestFrontendCityPageSSR:
    """GET /products/{slug}/in/{city} — must include city-scoped JSON-LD, no duplicates."""

    @pytest.fixture(scope="class")
    def html(self):
        url = f"{BASE_URL}/products/{PRODUCT_SLUG}/in/{CITY}"
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 seo-test"})
        if r.status_code != 200:
            url = f"{BASE_URL}/products/{FALLBACK_SLUG}/in/{CITY}"
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 seo-test"})
        assert r.status_code == 200, f"city page returned {r.status_code}"
        return r.text

    def test_city_has_4_jsonld_blocks(self, html):
        scripts = _extract_jsonld_scripts(html)
        testids = [s["testid"] for s in scripts if s["testid"]]
        expected = {"city-product-jsonld", "city-breadcrumb-jsonld", "city-faq-jsonld", "city-org-jsonld"}
        missing = expected - set(testids)
        assert not missing, f"Missing city JSON-LD blocks: {missing}. Found: {testids}"

    def test_city_no_duplicate_main_jsonld(self, html):
        """Main product-jsonld/breadcrumb-jsonld/faq-jsonld should NOT appear on city pages."""
        scripts = _extract_jsonld_scripts(html)
        testids = [s["testid"] for s in scripts if s["testid"]]
        forbidden = {"product-jsonld", "breadcrumb-jsonld", "faq-jsonld"}
        leaked = forbidden & set(testids)
        assert not leaked, f"Main-product JSON-LD leaked onto city page: {leaked}. All: {testids}"

    def test_city_jsonld_valid_json(self, html):
        scripts = _extract_jsonld_scripts(html)
        target_ids = {"city-product-jsonld", "city-breadcrumb-jsonld", "city-faq-jsonld", "city-org-jsonld"}
        for s in scripts:
            if s["testid"] in target_ids:
                try:
                    obj = json.loads(s["body"])
                except json.JSONDecodeError as e:
                    pytest.fail(f"City JSON-LD {s['testid']} invalid JSON: {e}")
                ctx = obj.get("@context", "") if isinstance(obj, dict) else ""
                assert "schema.org" in str(ctx)
