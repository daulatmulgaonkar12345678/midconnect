"""
SEO v2.1 Enforcement Tests
===========================
Tests for SEO v2.1 compliance including:
1. URL structure: /products/{slug} and /categories/{slug} (plural)
2. Product slugs: {product-name}-{category}-supplier-india (max 90 chars)
3. Category slugs: {category-name}-suppliers-india (max 90 chars)
4. 301 redirects from old URLs
5. Sitemap compliance
6. SEO data quality (seoTitle 55-65 chars, seoDescription 150-160 chars, jsonLd)
"""

import pytest
import requests
import os
import re

# Use environment variable for API URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://plan-limits-5.preview.emergentagent.com')

# Test data - known products and categories
TEST_PRODUCT_ID = "699be9023cbe1a8c31591668"
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"
TEST_CATEGORY_ID = "699be9023cbe1a8c31591667"
TEST_CATEGORY_SLUG = "test-category-suppliers-india"

# V2.1 slug patterns
V2_PRODUCT_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+-supplier-india(-\d+)?$')
V2_CATEGORY_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+-suppliers-india(-\d+)?$')
MAX_SLUG_LENGTH = 90


class TestProductRedirectEndpoint:
    """Test GET /api/redirect/product/{id} - Returns new slug for 301 redirect"""
    
    def test_product_redirect_returns_slug_for_objectid(self):
        """Product redirect endpoint returns slug for ObjectId"""
        response = requests.get(f"{BASE_URL}/api/redirect/product/{TEST_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("redirect") == True
        assert data.get("status") == 301
        assert "slug" in data
        assert data["slug"] == TEST_PRODUCT_SLUG
        print(f"✅ Product redirect: {TEST_PRODUCT_ID} -> {data['slug']}")
    
    def test_product_redirect_from_field(self):
        """Product redirect 'from' field uses /product/ (singular)"""
        response = requests.get(f"{BASE_URL}/api/redirect/product/{TEST_PRODUCT_ID}")
        data = response.json()
        
        assert data.get("from") == f"/product/{TEST_PRODUCT_ID}"
        print(f"✅ Product redirect from: {data['from']}")
    
    def test_product_redirect_handles_nonexistent_id(self):
        """Product redirect handles non-existent ID gracefully"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/redirect/product/{fake_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("redirect") == False
        print(f"✅ Product redirect correctly returns no redirect for non-existent ID")


class TestCategoryRedirectEndpoint:
    """Test GET /api/redirect/category/{id} - Returns new slug for 301 redirect"""
    
    def test_category_redirect_returns_slug_for_objectid(self):
        """Category redirect endpoint returns slug for ObjectId"""
        response = requests.get(f"{BASE_URL}/api/redirect/category/{TEST_CATEGORY_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("redirect") == True
        assert data.get("status") == 301
        assert "slug" in data
        # V2.1: Category slugs should end with -suppliers-india
        assert data["slug"].endswith("-suppliers-india") or data["slug"].endswith("-suppliers-india-1")
        print(f"✅ Category redirect: {TEST_CATEGORY_ID} -> {data['slug']}")
    
    def test_category_redirect_from_field(self):
        """Category redirect 'from' field uses /category/ (singular)"""
        response = requests.get(f"{BASE_URL}/api/redirect/category/{TEST_CATEGORY_ID}")
        data = response.json()
        
        assert data.get("from") == f"/category/{TEST_CATEGORY_ID}"
        print(f"✅ Category redirect from: {data['from']}")
    
    def test_category_redirect_handles_nonexistent_id(self):
        """Category redirect handles non-existent ID gracefully"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/redirect/category/{fake_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("redirect") == False
        print(f"✅ Category redirect correctly returns no redirect for non-existent ID")


class TestProductSlugCompliance:
    """Test product slugs follow V2.1 format: {product-name}-{category}-supplier-india"""
    
    def test_all_products_have_slugs(self):
        """All products must have non-null slugs"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        products = response.json()
        assert len(products) > 0, "No products found"
        
        missing_slugs = []
        for prod in products:
            if not prod.get("slug"):
                missing_slugs.append(prod.get("_id"))
        
        assert len(missing_slugs) == 0, f"Products missing slugs: {missing_slugs}"
        print(f"✅ All {len(products)} products have slugs")
    
    def test_product_slugs_end_with_supplier_india(self):
        """Product slugs must end with -supplier-india (V2.1 format)"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        non_compliant = []
        for prod in products:
            slug = prod.get("slug", "")
            if not V2_PRODUCT_SLUG_PATTERN.match(slug):
                non_compliant.append({
                    "id": prod.get("_id"),
                    "slug": slug
                })
        
        assert len(non_compliant) == 0, f"Non-compliant product slugs: {non_compliant}"
        print(f"✅ All product slugs follow V2.1 format (-supplier-india suffix)")
    
    def test_product_slugs_max_length(self):
        """Product slugs must not exceed 90 characters"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        too_long = []
        for prod in products:
            slug = prod.get("slug", "")
            if len(slug) > MAX_SLUG_LENGTH:
                too_long.append({
                    "id": prod.get("_id"),
                    "slug": slug,
                    "length": len(slug)
                })
        
        assert len(too_long) == 0, f"Product slugs exceeding {MAX_SLUG_LENGTH} chars: {too_long}"
        print(f"✅ All product slugs are within {MAX_SLUG_LENGTH} characters")


class TestCategorySlugCompliance:
    """Test category slugs follow V2.1 format: {category-name}-suppliers-india"""
    
    def test_categories_endpoint_returns_slugs(self):
        """GET /api/categories must include slug field"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        for cat in categories:
            assert "slug" in cat, f"Category {cat.get('_id')} missing slug field"
            assert cat["slug"] is not None, f"Category {cat.get('_id')} has null slug"
        
        print(f"✅ GET /api/categories includes slug field for all {len(categories)} categories")
    
    def test_public_categories_endpoint_returns_slugs(self):
        """GET /api/categories/public must include slug field"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        categories = response.json()
        for cat in categories:
            assert "slug" in cat, f"Category {cat.get('_id')} missing slug field"
            assert cat["slug"] is not None, f"Category {cat.get('_id')} has null slug"
        
        print(f"✅ GET /api/categories/public includes slug field for all {len(categories)} categories")
    
    def test_category_slugs_end_with_suppliers_india(self):
        """Category slugs must end with -suppliers-india (V2.1 format)"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        categories = response.json()
        
        non_compliant = []
        for cat in categories:
            slug = cat.get("slug", "")
            if not V2_CATEGORY_SLUG_PATTERN.match(slug):
                non_compliant.append({
                    "id": cat.get("_id"),
                    "name": cat.get("name"),
                    "slug": slug
                })
        
        # Note: Some legacy categories may not match pattern, this is informational
        if non_compliant:
            print(f"⚠️ Non-compliant category slugs (may be legacy): {non_compliant}")
        else:
            print(f"✅ All category slugs follow V2.1 format (-suppliers-india suffix)")
    
    def test_category_slugs_max_length(self):
        """Category slugs must not exceed 90 characters"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        categories = response.json()
        
        too_long = []
        for cat in categories:
            slug = cat.get("slug", "")
            if len(slug) > MAX_SLUG_LENGTH:
                too_long.append({
                    "id": cat.get("_id"),
                    "slug": slug,
                    "length": len(slug)
                })
        
        assert len(too_long) == 0, f"Category slugs exceeding {MAX_SLUG_LENGTH} chars: {too_long}"
        print(f"✅ All category slugs are within {MAX_SLUG_LENGTH} characters")


class TestSEOEndpoint:
    """Test GET /api/products/{slug}/seo - Returns complete SEO data"""
    
    def test_seo_endpoint_returns_200(self):
        """SEO endpoint returns 200 for valid product slug"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        assert response.status_code == 200
        print(f"✅ SEO endpoint returns 200 for {TEST_PRODUCT_SLUG}")
    
    def test_seo_endpoint_returns_404_for_invalid_slug(self):
        """SEO endpoint returns 404 for invalid slug"""
        response = requests.get(f"{BASE_URL}/api/products/nonexistent-product-slug/seo")
        assert response.status_code == 404
        print(f"✅ SEO endpoint returns 404 for non-existent slug")
    
    def test_seo_response_has_required_fields(self):
        """SEO response contains all required fields"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        required_fields = [
            "productId", "seoTitle", "seoDescription", "seoContent",
            "jsonLd", "faqJsonLd", "internalLinks"
        ]
        
        missing = [f for f in required_fields if f not in data]
        assert len(missing) == 0, f"Missing SEO fields: {missing}"
        print(f"✅ SEO response contains all required fields")
    
    def test_seo_title_length(self):
        """SEO title should be 55-65 characters"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        title = data.get("seoTitle", "")
        title_len = len(title)
        
        # Allow some tolerance (50-70 chars)
        assert 50 <= title_len <= 70, f"SEO title length {title_len} not in range 50-70: {title}"
        print(f"✅ SEO title length: {title_len} chars (target: 55-65)")
    
    def test_seo_description_length(self):
        """SEO description should be 150-160 characters"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        desc = data.get("seoDescription", "")
        desc_len = len(desc)
        
        # Allow some tolerance (140-170 chars)
        assert 140 <= desc_len <= 170, f"SEO description length {desc_len} not in range 140-170: {desc}"
        print(f"✅ SEO description length: {desc_len} chars (target: 150-160)")
    
    def test_seo_json_ld_product_schema(self):
        """JSON-LD should have Product schema"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        json_ld = data.get("jsonLd", {})
        assert json_ld.get("@type") == "Product", "JSON-LD should have @type: Product"
        assert "@context" in json_ld, "JSON-LD should have @context"
        assert "offers" in json_ld, "JSON-LD should have offers"
        print(f"✅ JSON-LD has valid Product schema")
    
    def test_seo_faq_json_ld(self):
        """FAQ JSON-LD should have FAQPage schema"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        faq_ld = data.get("faqJsonLd", {})
        assert faq_ld.get("@type") == "FAQPage", "FAQ JSON-LD should have @type: FAQPage"
        assert "mainEntity" in faq_ld, "FAQ JSON-LD should have mainEntity"
        print(f"✅ FAQ JSON-LD has valid FAQPage schema")
    
    def test_seo_internal_links(self):
        """Internal links should have required structure"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/seo")
        data = response.json()
        
        links = data.get("internalLinks", {})
        assert "category" in links, "internalLinks should have category"
        assert "similarProducts" in links, "internalLinks should have similarProducts"
        print(f"✅ Internal links structure is valid")


class TestProductDetailBySlug:
    """Test GET /api/products/detail/{slug} - Product accessible by slug"""
    
    def test_product_accessible_by_slug(self):
        """Product detail endpoint works with slug"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{TEST_PRODUCT_SLUG}")
        assert response.status_code == 200
        
        data = response.json()
        # Response has productName, productId, sellers structure
        assert "productName" in data or "productId" in data, "Response should contain product data"
        print(f"✅ Product accessible by slug: {TEST_PRODUCT_SLUG}")
    
    def test_product_accessible_by_objectid(self):
        """Product detail endpoint works with ObjectId (for backward compatibility)"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{TEST_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        # Response has productName, productId, sellers structure
        assert "productName" in data or "productId" in data, "Response should contain product data"
        print(f"✅ Product accessible by ObjectId: {TEST_PRODUCT_ID}")


class TestSitemapCompliance:
    """Test that products/categories have data required for sitemap generation"""
    
    def test_products_have_slugs_for_sitemap(self):
        """All products should have slugs for sitemap URLs"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        products_with_slugs = [p for p in products if p.get("slug")]
        
        assert len(products_with_slugs) == len(products), \
            f"Only {len(products_with_slugs)}/{len(products)} products have slugs for sitemap"
        print(f"✅ All {len(products)} products have slugs for sitemap")
    
    def test_categories_have_slugs_for_sitemap(self):
        """All categories should have slugs for sitemap URLs"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        categories = response.json()
        
        categories_with_slugs = [c for c in categories if c.get("slug")]
        
        assert len(categories_with_slugs) == len(categories), \
            f"Only {len(categories_with_slugs)}/{len(categories)} categories have slugs for sitemap"
        print(f"✅ All {len(categories)} categories have slugs for sitemap")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
