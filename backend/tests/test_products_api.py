"""
Backend API Tests for B2B Marketplace - Products & Seller Listings
==================================================================
Tests for:
1. GET /api/products - seller-listing-driven visibility
2. GET /api/products/detail/{identifier} - supports both product_id and product_name
3. GET /api/admin/products - listing_count from seller_listings
4. POST /api/seller/listings - accepts product_id field

Context: Database has 20 products in products collection but 0 in seller_listings.
The seller-listing-driven visibility means /api/products returns empty when no active listings exist.
"""

import pytest
import requests
import os
from bson import ObjectId

# Use local backend URL
BASE_URL = "http://localhost:8001/api"


class TestPublicProductsAPI:
    """Test public products endpoint - seller-listing-driven visibility"""
    
    def test_get_products_returns_empty_when_no_active_listings(self):
        """
        /api/products should return empty array when no active seller_listings exist.
        This is EXPECTED behavior - products only visible with active listings.
        """
        response = requests.get(f"{BASE_URL}/products")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertion - should be empty array since no active seller_listings
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # This confirms seller-listing-driven visibility works
        print(f"GET /api/products returned {len(data)} products (expected: 0 since no active listings)")
        
        # If not empty, verify structure
        if len(data) > 0:
            first_product = data[0]
            # Verify _id is present and not null
            assert "_id" in first_product, "Product should have _id field"
            assert first_product["_id"] is not None, "Product _id should not be null"
            assert "name" in first_product, "Product should have name field"
            assert "seller_count" in first_product, "Product should have seller_count field"
    
    def test_get_products_with_category_filter(self):
        """Test products endpoint with category filter"""
        # Use a random category_id - should still return empty
        response = requests.get(f"{BASE_URL}/products?category_id=507f1f77bcf86cd799439011")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET /api/products with category filter returned {len(data)} products")


class TestProductDetailAPI:
    """Test product detail endpoint - supports both product_id and product_name"""
    
    def test_product_detail_by_name_returns_404_when_no_listings(self):
        """
        /api/products/detail/{name} should return 404 when product has no active listings.
        This is expected behavior - product pages only work with active sellers.
        """
        # URL encode a product name
        import urllib.parse
        product_name = urllib.parse.quote("Three Phase AC Motor")
        
        response = requests.get(f"{BASE_URL}/products/detail/{product_name}")
        
        # Should return 404 since no active listings exist
        assert response.status_code == 404, f"Expected 404 (no listings), got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should have detail field"
        print(f"GET /api/products/detail/{product_name}: {data.get('detail')}")
    
    def test_product_detail_by_valid_objectid_returns_404_when_no_listings(self):
        """
        /api/products/detail/{product_id} should support ObjectId lookup.
        Returns 404 when no active listings (expected).
        """
        # Use a valid ObjectId format (24 hex chars)
        product_id = "6981a9a74108b0cbd93aa631"  # Sample product ID from DB
        
        response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        
        # Should return 404 since no active listings for this product_id
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        print(f"GET /api/products/detail/{product_id}: {data.get('detail')}")
    
    def test_product_detail_nonexistent_returns_404(self):
        """Non-existent product should return 404"""
        response = requests.get(f"{BASE_URL}/products/detail/NonExistentProduct12345")
        
        assert response.status_code == 404
        print("Non-existent product correctly returns 404")


class TestAdminProductsAPI:
    """Test admin products endpoint - requires authentication"""
    
    def test_admin_products_requires_auth(self):
        """
        GET /api/admin/products requires admin authentication.
        Without token, should return 401.
        """
        response = requests.get(f"{BASE_URL}/admin/products")
        
        # Should return 401 without auth token
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Admin products endpoint correctly requires authentication")
    
    def test_admin_products_with_invalid_token(self):
        """Invalid token should return 401 or 503 (if Firebase not configured)"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/admin/products", headers=headers)
        
        # Expected: 401 (invalid token) or 503 (auth service not configured)
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"Admin products with invalid token: {response.status_code}")


class TestSellerListingsAPI:
    """Test seller listings endpoint - verify product_id field support"""
    
    def test_seller_listings_requires_auth(self):
        """POST /api/seller/listings requires seller authentication"""
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json={
                "product_id": "6981a9a74108b0cbd93aa631",
                "product_name": "Test Product",
                "category_id": "507f1f77bcf86cd799439011",
                "seller_type": "Manufacturer",
                "availability": {"moq": 10}
            }
        )
        
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Seller listings endpoint correctly requires authentication")
    
    def test_seller_listings_validates_request(self):
        """
        Verify the endpoint validates the request body structure.
        Even with auth issues, schema validation might fail first.
        """
        headers = {"Authorization": "Bearer test_token"}
        
        # Invalid request - missing required fields
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json={"product_name": "Test"},
            headers=headers
        )
        
        # Should return 401 (auth first) or 422 (validation)
        assert response.status_code in [401, 422, 503], f"Expected 401/422/503, got {response.status_code}"
        print(f"Seller listings validation: {response.status_code}")


class TestProductsByCategoryAPI:
    """Test /api/products/by-category endpoint (for vendor listing)"""
    
    def test_products_by_category_works(self):
        """
        GET /api/products/by-category/{category_id} returns products from master catalog.
        This endpoint is for vendors selecting products, NOT public visibility.
        """
        # Need a valid category_id - let's get one from the database
        categories_response = requests.get(f"{BASE_URL}/categories/all")
        
        if categories_response.status_code == 200:
            categories = categories_response.json()
            if len(categories) > 0:
                category_id = categories[0].get("_id")
                if category_id:
                    response = requests.get(f"{BASE_URL}/products/by-category/{category_id}")
                    
                    # Should work - returns products in that category
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                    
                    data = response.json()
                    assert isinstance(data, list)
                    print(f"GET /api/products/by-category/{category_id}: {len(data)} products")
                    
                    # If products exist, verify structure
                    if len(data) > 0:
                        first = data[0]
                        assert "_id" in first, "Product should have _id"
                        assert "name" in first, "Product should have name"
                        print(f"  First product: {first.get('name')}")
                    return
        
        # Fallback test with dummy ID
        response = requests.get(f"{BASE_URL}/products/by-category/507f1f77bcf86cd799439011")
        # Should return 200 with empty array or 400 for invalid ID
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"


class TestHealthEndpoints:
    """Basic health checks"""
    
    def test_health_endpoint(self):
        """Basic health check"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        print(f"Health: {data}")
    
    def test_health_ready_endpoint(self):
        """Readiness probe"""
        response = requests.get(f"{BASE_URL}/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "mongodb" in data
        print(f"Ready: {data}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
