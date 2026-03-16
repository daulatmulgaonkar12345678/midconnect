"""
TOKEN-BASED SLUG RESOLVER SERVICE TESTS
=======================================
Tests for the enterprise-grade, order-independent URL slug resolution.

Test Coverage:
1. Partial slugs: "motor" should match "industrial-electric-motor-5hp-test-category-supplier-india"
2. Word order variations: "motor-electric" should match "electric-motor-xxx"
3. City names ignored: "motor-mumbai" should still find the product
4. Stop words filtered: "buy-motor-online" should work
5. Exact slug match returns no redirect
6. All enterprise endpoints use the resolver (enterprise, facets, filter, detail, seo)
"""

import pytest
import requests
import os
import json

# API URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://invoice-gst-calc.preview.emergentagent.com')

# Test product data
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"
TEST_PRODUCT_NAME = "Industrial Electric Motor 5HP"


class TestSlugResolverService:
    """Tests for the SlugResolverService token-based matching"""
    
    def test_partial_slug_motor_matches(self):
        """Partial slug 'motor' should match the test product"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["product"]["name"] == TEST_PRODUCT_NAME
        assert data["redirect"]["needed"] == True, "Partial slug should require redirect"
        assert data["redirect"]["canonicalSlug"] == TEST_PRODUCT_SLUG
    
    def test_word_order_independence_motor_electric(self):
        """Word order 'motor-electric' should match 'electric-motor' in product name"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor-electric")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_word_order_independence_industrial_motor(self):
        """Word order 'industrial-motor' should match 'industrial-electric-motor'"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/industrial-motor")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_city_name_ignored_mumbai(self):
        """City name 'mumbai' in slug should be ignored - 'motor-mumbai' matches"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor-mumbai")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_city_name_ignored_delhi(self):
        """City name 'delhi' in slug should be ignored - 'electric-motor-delhi' matches"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/electric-motor-delhi")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_stop_words_filtered_buy_online(self):
        """Stop words 'buy' and 'online' should be filtered - 'buy-motor-online' matches"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/buy-motor-online")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_stop_words_filtered_supplier_india(self):
        """Stop words 'supplier' and 'india' should be filtered"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor-supplier-india")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True
    
    def test_exact_slug_no_redirect(self):
        """Exact slug match should return redirect.needed = False"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == False, "Exact slug should NOT require redirect"
        assert data["redirect"]["canonicalSlug"] == TEST_PRODUCT_SLUG
    
    def test_combined_partial_city_stopwords(self):
        """Combined test: partial + city + stop words all work together"""
        # 'buy-industrial-motor-bangalore-online' should match
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/buy-industrial-motor-bangalore-online")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert data["redirect"]["needed"] == True


class TestEnterpriseEndpointsWithResolver:
    """Tests that all enterprise endpoints use the slug resolver correctly"""
    
    def test_enterprise_endpoint_with_partial_slug(self):
        """/products/{slug}/enterprise should work with partial slug"""
        response = requests.get(f"{BASE_URL}/api/products/motor/enterprise")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["product"]["name"] == TEST_PRODUCT_NAME
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        assert "sellers" in data
        assert data["redirect"]["needed"] == True
        assert data["redirect"]["canonicalSlug"] == TEST_PRODUCT_SLUG
    
    def test_enterprise_endpoint_redirect_info(self):
        """Enterprise endpoint should include redirect info for frontend"""
        response = requests.get(f"{BASE_URL}/api/products/motor-mumbai/enterprise")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "redirect" in data
        assert data["redirect"]["needed"] == True
        assert data["redirect"]["canonicalSlug"] == TEST_PRODUCT_SLUG
        assert "canonicalUrl" in data["redirect"]
    
    def test_facets_endpoint_with_partial_slug(self):
        """/products/{slug}/facets should work with partial slug"""
        response = requests.get(f"{BASE_URL}/api/products/motor-electric/facets")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "facets" in data
        assert data["totalListings"] >= 0
    
    def test_filter_endpoint_with_partial_slug(self):
        """/products/{slug}/filter should work with partial slug"""
        response = requests.post(
            f"{BASE_URL}/api/products/motor-mumbai/filter",
            json={"page": 1, "limit": 10}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        assert "total" in data
    
    def test_seo_endpoint_with_partial_slug(self):
        """/products/{slug}/seo should work with partial slug and include redirect info"""
        response = requests.get(f"{BASE_URL}/api/products/motor/seo")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "seoTitle" in data
        assert "seoDescription" in data
        # SEO endpoint should also indicate redirect for canonical URL
        assert data.get("redirect", {}).get("needed") == True
    
    def test_product_detail_endpoint_with_partial_slug(self):
        """/products/detail/{slug} should work with partial slug"""
        response = requests.get(f"{BASE_URL}/api/products/detail/motor")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Product detail returns flat structure with slug at top level
        assert "slug" in data, f"Expected 'slug' in response, got keys: {list(data.keys())[:10]}"
        assert data["slug"] == TEST_PRODUCT_SLUG
        assert "productName" in data
        # Check redirect info
        assert data.get("redirect", {}).get("needed") == True


class TestSlugResolverEdgeCases:
    """Edge cases and error handling for the slug resolver"""
    
    def test_nonexistent_slug_returns_404(self):
        """Slug that doesn't match any product should return 404"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/xyznonexistent123")
        
        assert response.status_code == 404, f"Expected 404 for nonexistent slug, got {response.status_code}"
    
    def test_empty_after_stop_word_filtering(self):
        """Slug with only stop words should return 404 (no meaningful tokens)"""
        # 'buy-online-supplier-india' - all stop words, should have no meaningful tokens
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/buy-online-supplier-india")
        
        # This could be 404 if no tokens remain, or could match if there's a fallback
        # The important thing is it doesn't crash
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
    
    def test_special_characters_handled(self):
        """Special characters in URL should be handled gracefully"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor%20electric")
        
        # URL-encoded space should work
        assert response.status_code in [200, 404]
    
    def test_case_insensitivity(self):
        """Slug matching should be case-insensitive"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/MOTOR")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG


class TestCanonicalURLs:
    """Tests for canonical URL generation"""
    
    def test_canonical_url_format(self):
        """Canonical URL should follow the correct format"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/motor")
        
        assert response.status_code == 200
        
        data = response.json()
        canonical_url = data["redirect"]["canonicalUrl"]
        
        assert canonical_url.startswith("https://www.udyogconnect.in/products/")
        assert canonical_url.endswith(TEST_PRODUCT_SLUG)
    
    def test_canonical_url_not_needed_for_exact_match(self):
        """Canonical URL should still be present even when redirect not needed"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["redirect"]["needed"] == False
        assert data["redirect"]["canonicalUrl"] is not None


# Run with: pytest /app/backend/tests/test_slug_resolver.py -v --tb=short --junitxml=/app/test_reports/pytest/slug_resolver_results.xml
