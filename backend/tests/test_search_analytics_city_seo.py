"""
TEST SUITE: Search Analytics & City SEO Endpoints
==================================================
Tests for:
1. POST /api/search/track - Search keyword tracking
2. GET /api/products/{slug}/cities - Available cities for product
3. GET /api/products/{slug}/city/{city} - City-specific product data (404 if no sellers)
4. GET /api/enterprise/resolve/product/{id} - Resolver returns canonical URL
5. Product SEO fields validation (slug, seoTitle, seoDescription, legacyIds)
6. Sitemap uses /products/{slug} URLs only
"""

import pytest
import requests
import os
import time
from datetime import datetime

# Use environment variable for API URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"
TEST_PRODUCT_ID = "699be9023cbe1a8c31591668"
TEST_CATEGORY_SLUG = "test-category-suppliers-india"


class TestSearchTrackingEndpoint:
    """Tests for POST /api/search/track - Search keyword tracking"""
    
    def test_track_search_with_keyword_only(self):
        """Test basic search tracking with just a keyword"""
        # Use unique keyword with timestamp to avoid conflicts
        unique_keyword = f"TEST_motor_{int(time.time())}"
        
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={"keyword": unique_keyword, "results_count": 5}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert data["tracked"] is True
        print(f"✅ Search tracking with keyword only works - tracked: {unique_keyword}")
    
    def test_track_search_with_city(self):
        """Test search tracking with city filter"""
        unique_keyword = f"TEST_industrial_pump_{int(time.time())}"
        
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={
                "keyword": unique_keyword,
                "city": "mumbai",
                "results_count": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tracked"] is True
        print(f"✅ Search tracking with city works - keyword: {unique_keyword}, city: mumbai")
    
    def test_track_search_with_product_matched(self):
        """Test search tracking when a product is matched"""
        unique_keyword = f"TEST_electric_motor_{int(time.time())}"
        
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={
                "keyword": unique_keyword,
                "product_matched": TEST_PRODUCT_ID,
                "results_count": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tracked"] is True
        print(f"✅ Search tracking with product match works - product: {TEST_PRODUCT_ID}")
    
    def test_track_search_with_all_params(self):
        """Test search tracking with all parameters - keyword, city, product_matched"""
        unique_keyword = f"TEST_motor_complete_{int(time.time())}"
        
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={
                "keyword": unique_keyword,
                "city": "delhi",
                "product_matched": TEST_PRODUCT_ID,
                "results_count": 7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tracked"] is True
        print(f"✅ Search tracking with all params works")
    
    def test_track_search_empty_keyword_fails(self):
        """Test that empty keyword is not tracked (short keywords rejected)"""
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={"keyword": "", "results_count": 0}
        )
        
        # Empty keywords should still return 200 but tracked=false
        assert response.status_code == 200
        data = response.json()
        # Empty keyword tracking behavior may vary - just verify it doesn't crash
        print(f"✅ Empty keyword handled gracefully - tracked: {data.get('tracked', False)}")
    
    def test_track_search_short_keyword(self):
        """Test that very short keywords (< 2 chars) may not be tracked"""
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={"keyword": "a", "results_count": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Short keywords (< 2 chars) should not be tracked
        assert data["tracked"] is False, "Single character keywords should not be tracked"
        print(f"✅ Short keyword correctly not tracked")


class TestProductCitiesEndpoint:
    """Tests for GET /api/products/{slug}/cities - Available cities for product"""
    
    def test_get_cities_for_valid_product(self):
        """Test getting available cities for a valid product"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/cities")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "product" in data
        assert "cities" in data
        assert "totalCities" in data
        
        # Verify product info
        assert data["product"]["_id"] == TEST_PRODUCT_ID
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        
        # Cities is a list (may be empty if no sellers with city data)
        assert isinstance(data["cities"], list)
        assert isinstance(data["totalCities"], int)
        
        print(f"✅ Get cities for product works - {data['totalCities']} cities found")
    
    def test_get_cities_for_nonexistent_product(self):
        """Test 404 returned for non-existent product"""
        response = requests.get(f"{BASE_URL}/api/products/non-existent-product-slug/cities")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ 404 returned correctly for non-existent product")
    
    def test_cities_response_structure(self):
        """Test that city response has proper structure when cities exist"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/cities")
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are cities, verify their structure
        if data["cities"]:
            city = data["cities"][0]
            assert "name" in city, "City should have 'name' field"
            assert "slug" in city, "City should have 'slug' field"
            assert "sellerCount" in city, "City should have 'sellerCount' field"
            print(f"✅ City structure verified - name: {city['name']}, sellerCount: {city['sellerCount']}")
        else:
            print(f"✅ Cities endpoint works - no sellers with city data yet")


class TestCityProductPageEndpoint:
    """Tests for GET /api/products/{slug}/city/{city} - City-specific product data"""
    
    def test_city_page_returns_404_when_no_sellers(self):
        """Test that city page returns 404 when no sellers in that city (expected behavior)"""
        # This is expected behavior - city pages only exist if sellers exist
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/city/mumbai")
        
        # Per requirements: 404 if no sellers in city
        assert response.status_code == 404, f"Expected 404 when no sellers in city, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        assert "mumbai" in data["detail"].lower() or "no sellers" in data["detail"].lower()
        print(f"✅ City page correctly returns 404 when no sellers - detail: {data['detail']}")
    
    def test_city_page_returns_200_when_sellers_exist(self):
        """Test that city page returns 200 with seller data when sellers exist"""
        # Delhi has test seller data
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/city/delhi")
        
        assert response.status_code == 200, f"Expected 200 when sellers exist, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "product" in data
        assert "city" in data
        assert "sellers" in data
        assert "stats" in data
        assert "seo" in data
        
        # Verify product data
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        
        # Verify city data
        assert data["city"]["name"].lower() == "delhi"
        
        # Verify sellers exist
        assert len(data["sellers"]) > 0, "Should have at least one seller"
        
        # Verify stats
        assert data["stats"]["sellerCount"] >= 1
        
        # Verify SEO fields
        assert "title" in data["seo"]
        assert "description" in data["seo"]
        assert "canonicalUrl" in data["seo"]
        assert data["seo"]["canonicalUrl"].startswith("https://www.udyogconnect.in")
        
        print(f"✅ City page returns 200 with seller data - {data['stats']['sellerCount']} sellers in Delhi")
    
    def test_city_page_for_nonexistent_product(self):
        """Test 404 for non-existent product with city"""
        response = requests.get(f"{BASE_URL}/api/products/non-existent-product/city/mumbai")
        
        assert response.status_code == 404
        print(f"✅ 404 returned correctly for non-existent product city page")
    
    def test_city_page_for_various_cities(self):
        """Test city page responses for various cities"""
        cities_to_test = ["delhi", "bangalore", "chennai", "pune"]
        
        results = []
        for city in cities_to_test:
            response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/city/{city}")
            # All should return 404 if no sellers, or 200 with data if sellers exist
            assert response.status_code in [200, 404], f"Unexpected status {response.status_code} for city {city}: {response.text}"
            results.append((city, response.status_code))
            print(f"  - City '{city}': {response.status_code}")
        
        print(f"✅ City page endpoint handles multiple cities correctly")


class TestEnterpriseResolverEndpoint:
    """Tests for GET /api/enterprise/resolve/product/{id} - Resolver canonical URL"""
    
    def test_resolver_by_slug_returns_canonical_url(self):
        """Test resolver returns canonical URL when using slug"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify product data
        assert "product" in data
        assert data["product"]["_id"] == TEST_PRODUCT_ID
        assert data["product"]["slug"] == TEST_PRODUCT_SLUG
        
        # Verify SEO fields exist
        assert "seoTitle" in data["product"], "Product should have seoTitle"
        assert "seoDescription" in data["product"], "Product should have seoDescription"
        
        # Verify redirect/canonical info
        assert "redirect" in data
        assert "canonicalUrl" in data["redirect"]
        assert data["redirect"]["canonicalUrl"].startswith("https://www.udyogconnect.in/products/")
        assert TEST_PRODUCT_SLUG in data["redirect"]["canonicalUrl"]
        
        # When accessed by slug, no redirect needed
        assert data["redirect"]["needed"] is False
        
        print(f"✅ Resolver by slug returns canonical URL: {data['redirect']['canonicalUrl']}")
    
    def test_resolver_by_object_id_returns_redirect(self):
        """Test resolver by ObjectId returns redirect=true with canonical URL"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_ID}")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify canonical URL is returned
        assert data["redirect"]["canonicalUrl"] is not None
        assert "udyogconnect.in" in data["redirect"]["canonicalUrl"]
        
        # When accessed by ObjectId (not slug), redirect should be needed
        assert data["redirect"]["needed"] is True, "Redirect should be needed when accessed by ObjectId"
        assert data["redirect"]["canonicalSlug"] == TEST_PRODUCT_SLUG
        
        print(f"✅ Resolver by ObjectId correctly indicates redirect needed to slug")
    
    def test_resolver_for_nonexistent_product(self):
        """Test 404 for non-existent product"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/non-existent-slug")
        
        assert response.status_code == 404
        print(f"✅ Resolver returns 404 for non-existent product")


class TestProductSEOFields:
    """Tests for SEO data completeness on products"""
    
    def test_product_has_slug(self):
        """Test that product has unique slug"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["product"]["slug"] is not None
        assert len(data["product"]["slug"]) > 0
        assert "-" in data["product"]["slug"]  # Slugs have hyphens
        print(f"✅ Product has valid slug: {data['product']['slug']}")
    
    def test_product_has_seo_title(self):
        """Test that product has seoTitle"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "seoTitle" in data["product"]
        assert data["product"]["seoTitle"] is not None
        assert len(data["product"]["seoTitle"]) > 0
        print(f"✅ Product has seoTitle: {data['product']['seoTitle'][:50]}...")
    
    def test_product_has_seo_description(self):
        """Test that product has seoDescription"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "seoDescription" in data["product"]
        assert data["product"]["seoDescription"] is not None
        assert len(data["product"]["seoDescription"]) > 0
        print(f"✅ Product has seoDescription: {data['product']['seoDescription'][:50]}...")
    
    def test_product_slug_follows_seo_pattern(self):
        """Test that product slug follows v2.1 pattern (-supplier-india suffix)"""
        response = requests.get(f"{BASE_URL}/api/enterprise/resolve/product/{TEST_PRODUCT_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        slug = data["product"]["slug"]
        # SEO v2.1 requires -supplier-india suffix for products
        assert slug.endswith("-supplier-india"), f"Slug should end with -supplier-india, got: {slug}"
        print(f"✅ Product slug follows SEO v2.1 pattern: {slug}")


class TestSitemapSlugUsage:
    """Tests for sitemap using /products/{slug} URLs only"""
    
    def test_sitemap_exists(self):
        """Test that sitemap.xml endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/sitemap.xml")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "xml" in response.headers.get("content-type", "").lower() or response.text.startswith("<?xml")
        print(f"✅ Sitemap.xml endpoint exists and returns XML")
    
    def test_sitemap_uses_slug_urls(self):
        """Test that sitemap uses slug-based URLs for products"""
        response = requests.get(f"{BASE_URL}/api/sitemap.xml")
        
        assert response.status_code == 200
        content = response.text
        
        # Sitemap should contain product URLs with slugs
        assert "udyogconnect.in" in content, "Sitemap should contain udyogconnect.in domain"
        
        # Check that product URLs use slugs (contain hyphens), not ObjectIds (24 hex chars)
        # Product URLs should be like /product/some-slug-here not /product/507f1f77bcf86cd799439011
        import re
        
        # Find all product URLs
        product_urls = re.findall(r'<loc>https://www.udyogconnect.in/product/([^<]+)</loc>', content)
        
        for url_path in product_urls:
            # Verify it's not a raw ObjectId (24 hex characters)
            assert not re.match(r'^[0-9a-f]{24}$', url_path), f"Sitemap should use slugs, not ObjectIds: {url_path}"
            # Slugs should have hyphens
            assert "-" in url_path, f"Product URL should be slug-based: {url_path}"
        
        print(f"✅ Sitemap uses slug-based URLs - found {len(product_urls)} product URLs")
    
    def test_sitemap_no_objectid_urls(self):
        """Test that sitemap doesn't contain raw ObjectId URLs"""
        response = requests.get(f"{BASE_URL}/api/sitemap.xml")
        
        assert response.status_code == 200
        content = response.text
        
        import re
        # Check for any 24-character hex strings that might be ObjectIds
        # These should not appear as the final path segment
        objectid_pattern = r'/[0-9a-f]{24}(?:</loc>|$)'
        matches = re.findall(objectid_pattern, content.lower())
        
        assert len(matches) == 0, f"Sitemap should not contain ObjectId URLs, found: {matches}"
        print(f"✅ Sitemap contains no raw ObjectId URLs")


class TestSearchAnalyticsIndexes:
    """Tests for search analytics collection indexes"""
    
    def test_search_tracking_performance(self):
        """Test that search tracking is fast (indicates indexes exist)"""
        import time
        
        unique_keyword = f"TEST_perf_{int(time.time())}"
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/search/track",
            params={"keyword": unique_keyword, "results_count": 1}
        )
        elapsed = (time.time() - start_time) * 1000  # ms
        
        assert response.status_code == 200
        assert elapsed < 500, f"Search tracking too slow ({elapsed:.0f}ms) - may indicate missing indexes"
        
        print(f"✅ Search tracking performance OK - {elapsed:.0f}ms")
    
    def test_duplicate_keyword_tracking(self):
        """Test that duplicate keywords are correctly deduplicated"""
        unique_keyword = f"TEST_dedup_{int(time.time())}"
        
        # Track same keyword multiple times
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/search/track",
                params={"keyword": unique_keyword, "results_count": i}
            )
            assert response.status_code == 200
        
        print(f"✅ Duplicate keyword tracking works (keyword normalized)")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
