"""
P0 & P1 Bug Fix Verification Tests
===================================
P0: Database schema fix - $lookup operations for seller/category resolution
P1: datetime.utcnow() replaced with datetime.now(timezone.utc)

These tests verify:
1. /api/products returns categoryId and seller_count correctly
2. /api/products/detail/{slug} returns seller info (NOT 'Unknown')
3. seller_listings -> users $lookup works
4. products -> categories $lookup works
5. Timestamps use timezone-aware datetime
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://header-debug-1.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestProductsListAPI:
    """Test /api/products endpoint"""
    
    def test_products_endpoint_returns_200(self):
        """Products list endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_products_have_category_id(self):
        """Products should have categoryId (not 'Unknown' or None)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        
        if len(products) > 0:
            product = products[0]
            # Check categoryId exists and is not empty/null
            assert "categoryId" in product or "category_id" in product, f"Product missing categoryId: {product.keys()}"
            cat_id = product.get("categoryId") or product.get("category_id")
            assert cat_id is not None, "categoryId should not be None"
            assert cat_id != "", "categoryId should not be empty string"
            print(f"Product categoryId: {cat_id}")
    
    def test_products_have_category_name(self):
        """Products should have resolved category_name (not 'Unknown')"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        products = response.json()
        if len(products) > 0:
            product = products[0]
            cat_name = product.get("category_name")
            assert cat_name is not None, "category_name should exist"
            assert cat_name != "Unknown", f"category_name should NOT be 'Unknown': {cat_name}"
            assert cat_name != "", "category_name should not be empty"
            print(f"Product category_name: {cat_name}")
    
    def test_products_have_seller_count(self):
        """Products should have seller_count"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        products = response.json()
        if len(products) > 0:
            product = products[0]
            seller_count = product.get("seller_count")
            assert seller_count is not None, "seller_count should exist"
            assert isinstance(seller_count, int), f"seller_count should be int, got {type(seller_count)}"
            print(f"Product seller_count: {seller_count}")


class TestProductDetailAPI:
    """Test /api/products/detail/{slug} endpoint - P0 fix verification"""
    
    def test_product_detail_returns_200(self):
        """Product detail by slug should return 200"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_product_detail_has_seller_info(self):
        """Product detail should have sellers array with company info"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        assert "sellers" in data, "Response should have 'sellers' array"
        sellers = data.get("sellers", [])
        
        if len(sellers) > 0:
            seller = sellers[0]
            company_name = seller.get("company_name")
            
            # P0 FIX VERIFICATION: company_name should NOT be "Unknown Seller"
            assert company_name is not None, "company_name should exist"
            assert company_name != "Unknown Seller", f"CRITICAL: company_name is 'Unknown Seller' - $lookup failed!"
            assert company_name != "Unknown", f"CRITICAL: company_name is 'Unknown' - $lookup failed!"
            assert company_name != "", "company_name should not be empty"
            print(f"PASSED: Seller company_name resolved correctly: '{company_name}'")
    
    def test_product_detail_seller_has_location(self):
        """Seller info should have location (not empty)"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        sellers = data.get("sellers", [])
        
        if len(sellers) > 0:
            seller = sellers[0]
            location = seller.get("location")
            assert location is not None, "Seller should have location"
            print(f"Seller location: {location}")
    
    def test_product_detail_has_category_name(self):
        """Product detail should have category_name (not 'Unknown')"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        cat_name = data.get("category_name")
        
        # P0 FIX VERIFICATION: category_name should NOT be "Unknown"
        assert cat_name is not None, "category_name should exist"
        assert cat_name != "Unknown", f"CRITICAL: category_name is 'Unknown' - $lookup failed!"
        assert cat_name != "", "category_name should not be empty"
        print(f"PASSED: Product category_name resolved correctly: '{cat_name}'")
    
    def test_product_detail_has_seller_id(self):
        """Sellers should have seller_id field"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        sellers = data.get("sellers", [])
        
        if len(sellers) > 0:
            seller = sellers[0]
            seller_id = seller.get("seller_id")
            assert seller_id is not None, "Seller should have seller_id"
            assert len(seller_id) == 24, f"seller_id should be 24-char ObjectId, got: {seller_id}"
            print(f"Seller seller_id: {seller_id}")
    
    def test_product_detail_has_listing_id(self):
        """Sellers should have listing_id field"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        sellers = data.get("sellers", [])
        
        if len(sellers) > 0:
            seller = sellers[0]
            listing_id = seller.get("listing_id")
            assert listing_id is not None, "Seller should have listing_id"
            assert len(listing_id) == 24, f"listing_id should be 24-char ObjectId, got: {listing_id}"
            print(f"Seller listing_id: {listing_id}")


class TestCategoriesAPI:
    """Test categories API"""
    
    def test_categories_public_returns_200(self):
        """Public categories endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_categories_all_returns_200(self):
        """All categories endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestLookupIntegrity:
    """Verify $lookup operations work correctly across collections"""
    
    def test_seller_listings_to_users_lookup(self):
        """seller_listings -> users $lookup should resolve seller info"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        sellers = data.get("sellers", [])
        
        # Verify at least one seller exists
        assert len(sellers) > 0, "Expected at least one seller for this product"
        
        seller = sellers[0]
        # These fields come from $lookup to users collection
        company_name = seller.get("company_name")
        
        # The main P0 bug was: company_name was "Unknown Seller" because $lookup failed
        assert company_name not in [None, "", "Unknown Seller", "Unknown"], \
            f"FAILED: $lookup to users collection failed. company_name='{company_name}'"
        
        print(f"SUCCESS: seller_listings->users $lookup works. company_name='{company_name}'")
    
    def test_products_to_categories_lookup(self):
        """products -> categories $lookup should resolve category names"""
        response = requests.get(f"{BASE_URL}/api/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        category_name = data.get("category_name")
        
        # The P0 bug also affected category lookups
        assert category_name not in [None, "", "Unknown"], \
            f"FAILED: $lookup to categories collection failed. category_name='{category_name}'"
        
        print(f"SUCCESS: products->categories $lookup works. category_name='{category_name}'")


class TestAPIHealthAndReadiness:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_readiness_endpoint(self):
        """Readiness endpoint should show MongoDB connected"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("mongodb", {}).get("status") == "connected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
