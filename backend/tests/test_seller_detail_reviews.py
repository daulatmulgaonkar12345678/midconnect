"""
SELLER DETAIL PAGE & REVIEWS API TESTS
========================================
Tests for seller detail page with reviews feature:
- GET /api/reviews/seller-listing/{id}/details - Full seller listing details
- GET /api/reviews/eligible - Check review eligibility
- avgRating and totalReviews in enterprise products API
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://relational-update.preview.emergentagent.com').rstrip('/')

# Test listing ID from context
TEST_LISTING_ID = "699be9023cbe1a8c31591669"
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"


class TestSellerListingDetailsAPI:
    """Tests for /api/reviews/seller-listing/{id}/details endpoint"""
    
    def test_seller_listing_details_returns_200(self):
        """Test that seller listing details endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Seller listing details endpoint returns 200")
    
    def test_seller_listing_details_contains_product(self):
        """Test that response contains product data"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        data = response.json()
        
        assert "product" in data, "Response should contain 'product'"
        assert data["product"] is not None, "Product should not be None"
        assert "_id" in data["product"], "Product should have _id"
        assert "name" in data["product"], "Product should have name"
        print(f"✅ Product data present: {data['product'].get('name')}")
    
    def test_seller_listing_details_contains_seller(self):
        """Test that response contains seller data"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        data = response.json()
        
        assert "seller" in data, "Response should contain 'seller'"
        assert data["seller"] is not None, "Seller should not be None"
        assert "badgeType" in data["seller"], "Seller should have badgeType"
        print(f"✅ Seller data present: {data['seller'].get('businessName')}")
    
    def test_seller_listing_details_contains_listing_info(self):
        """Test that response contains seller listing commercial info"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        data = response.json()
        
        assert "sellerListing" in data, "Response should contain 'sellerListing'"
        listing = data["sellerListing"]
        assert listing is not None, "sellerListing should not be None"
        assert "moq" in listing, "sellerListing should have moq"
        assert "stock" in listing, "sellerListing should have stock"
        assert "pricingTiers" in listing, "sellerListing should have pricingTiers"
        print(f"✅ Seller listing info: MOQ={listing.get('moq')}, Stock={listing.get('stock')}")
    
    def test_seller_listing_details_contains_reviews_array(self):
        """Test that response contains reviews array"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        data = response.json()
        
        assert "reviews" in data, "Response should contain 'reviews'"
        assert isinstance(data["reviews"], list), "Reviews should be a list"
        print(f"✅ Reviews array present with {len(data['reviews'])} reviews")
    
    def test_seller_listing_details_contains_rating_aggregation(self):
        """Test that response contains avgRating and totalReviews"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/{TEST_LISTING_ID}/details")
        data = response.json()
        
        assert "avgRating" in data, "Response should contain 'avgRating'"
        assert "totalReviews" in data, "Response should contain 'totalReviews'"
        assert isinstance(data["avgRating"], (int, float)), "avgRating should be numeric"
        assert isinstance(data["totalReviews"], int), "totalReviews should be integer"
        print(f"✅ Rating aggregation: avgRating={data['avgRating']}, totalReviews={data['totalReviews']}")
    
    def test_seller_listing_details_invalid_id_returns_400_or_404(self):
        """Test that invalid listing ID returns appropriate error"""
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/invalid-id/details")
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"✅ Invalid ID returns {response.status_code}")
    
    def test_seller_listing_details_nonexistent_returns_404(self):
        """Test that non-existent listing ID returns 404"""
        # Valid ObjectId format but doesn't exist
        response = requests.get(f"{BASE_URL}/api/reviews/seller-listing/000000000000000000000000/details")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent listing returns 404")


class TestReviewEligibilityAPI:
    """Tests for /api/reviews/eligible endpoint"""
    
    def test_eligible_without_auth_returns_401_or_403(self):
        """Test that eligibility check without auth returns 401/403"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/eligible",
            params={"sellerListingId": TEST_LISTING_ID}
        )
        # Without auth token, should fail
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print(f"✅ Eligibility without auth returns {response.status_code}")
    
    def test_eligible_without_listing_id_returns_401_or_422(self):
        """Test that eligibility check without listingId returns 401 (auth first) or 422 (missing param)"""
        response = requests.get(f"{BASE_URL}/api/reviews/eligible")
        # Without auth, should return 401 first (auth check happens before param validation)
        # If auth is skipped, would return 422 for missing param
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print(f"✅ Eligibility without listing ID returns {response.status_code}")


class TestEnterpriseProductRatingFields:
    """Tests for avgRating and totalReviews in enterprise products API"""
    
    def test_enterprise_product_sellers_have_rating_fields(self):
        """Test that seller listings in enterprise API have rating fields"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/enterprise")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        sellers = data.get("sellers", [])
        assert len(sellers) > 0, "Should have at least one seller"
        
        seller = sellers[0]
        assert "avgRating" in seller, "Seller should have avgRating field"
        assert "totalReviews" in seller, "Seller should have totalReviews field"
        print(f"✅ Enterprise seller has rating fields: avgRating={seller['avgRating']}, totalReviews={seller['totalReviews']}")
    
    def test_enterprise_product_rating_fields_are_numeric(self):
        """Test that rating fields are properly typed"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/enterprise")
        data = response.json()
        sellers = data.get("sellers", [])
        
        for seller in sellers:
            assert isinstance(seller.get("avgRating"), (int, float)), f"avgRating should be numeric, got {type(seller.get('avgRating'))}"
            assert isinstance(seller.get("totalReviews"), int), f"totalReviews should be int, got {type(seller.get('totalReviews'))}"
        
        print(f"✅ All {len(sellers)} sellers have properly typed rating fields")


class TestSellerListingReviewsAPI:
    """Tests for /api/reviews/listing/{id} endpoint"""
    
    def test_listing_reviews_returns_200(self):
        """Test that listing reviews endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/reviews/listing/{TEST_LISTING_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Listing reviews endpoint returns 200")
    
    def test_listing_reviews_has_required_fields(self):
        """Test that listing reviews response has required structure"""
        response = requests.get(f"{BASE_URL}/api/reviews/listing/{TEST_LISTING_ID}")
        data = response.json()
        
        assert "reviews" in data, "Response should contain 'reviews'"
        assert "avgRating" in data, "Response should contain 'avgRating'"
        assert "totalReviews" in data, "Response should contain 'totalReviews'"
        print(f"✅ Listing reviews has required fields: {len(data['reviews'])} reviews, avg={data['avgRating']}")


class TestProductFilterRatingFields:
    """Tests for avgRating and totalReviews in filter API"""
    
    def test_filter_results_have_rating_fields(self):
        """Test that filter API results include rating fields"""
        response = requests.post(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/filter",
            json={"sortBy": "price", "order": "asc", "page": 1, "limit": 10}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        results = data.get("results", [])
        
        if len(results) > 0:
            result = results[0]
            assert "avgRating" in result, "Result should have avgRating"
            assert "totalReviews" in result, "Result should have totalReviews"
            print(f"✅ Filter results have rating fields: avgRating={result['avgRating']}, totalReviews={result['totalReviews']}")
        else:
            print("⚠️ No results to verify, but endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
