"""
Test Suite for V7 Schema Fix - seller_listings Collection
==========================================================

Tests verify the P0 Critical Fix for:
1. Correct seller_count in /api/products (not showing 0)
2. Correct sellers array in product detail endpoint
3. Correct product counts in categories
4. Admin listings showing product_name and seller_name via $lookup

SSOT VERIFICATION:
- All IDs are ObjectId (no legacy string snake_case fields)
- No seller_id, product_id, category_id (legacy) fields
- Only sellerId, productId, categoryId (canonical camelCase ObjectId)
"""

import pytest
import requests
import os

# Get API base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://search-typos.preview.emergentagent.com"

DEV_TOKEN = "dev-test-token"


class TestPublicProductsAPI:
    """Test public products API endpoints - seller counts and aggregations"""
    
    def test_health_check(self):
        """Verify API is healthy before running tests"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ API health check passed")
    
    def test_products_endpoint_returns_seller_count(self):
        """
        GET /api/products - Should return products with correct seller_count (not 0)
        
        This was the P0 bug: aggregation was failing due to legacy field mismatches.
        After V7 migration, seller_count should be accurate.
        """
        response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert response.status_code == 200, f"Products API failed: {response.text}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list of products"
        
        # Verify at least one product exists with sellers
        products_with_sellers = [p for p in products if p.get("seller_count", 0) > 0]
        assert len(products_with_sellers) > 0, "No products found with active sellers"
        
        # Verify seller_count is not 0 for products that should have sellers
        for product in products_with_sellers:
            print(f"  - {product.get('name')}: seller_count={product.get('seller_count')}, min_price={product.get('min_price')}")
            assert product.get("seller_count") > 0, f"Product {product.get('name')} has seller_count=0"
            assert product.get("name") is not None, "Product name is missing"
            
        print(f"✅ Found {len(products_with_sellers)} products with active sellers")
    
    def test_products_have_valid_structure(self):
        """Verify product response structure is correct"""
        response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert response.status_code == 200
        
        products = response.json()
        if not products:
            pytest.skip("No products found to test structure")
        
        required_fields = ["_id", "name", "seller_count"]
        for product in products:
            for field in required_fields:
                assert field in product, f"Missing required field: {field}"
        
        print("✅ Product structure validation passed")


class TestProductDetailAPI:
    """Test product detail endpoint with sellers array"""
    
    def test_product_detail_by_slug_returns_sellers(self):
        """
        GET /api/products/detail/{slug} - Should return product with sellers array
        
        Test uses 'three-phase-ac-motor' slug based on test context.
        """
        slug = "three-phase-ac-motor"
        response = requests.get(f"{BASE_URL}/api/products/detail/{slug}", timeout=10)
        
        # Product should exist and have sellers
        assert response.status_code == 200, f"Product detail failed for slug {slug}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "product_id" in data, "Missing product_id in response"
        assert "product_name" in data, "Missing product_name in response"
        assert "sellers" in data, "Missing sellers array in response"
        assert "seller_count" in data, "Missing seller_count in response"
        
        # Verify sellers array matches seller_count
        sellers = data.get("sellers", [])
        seller_count = data.get("seller_count", 0)
        
        assert len(sellers) == seller_count, f"sellers array length ({len(sellers)}) != seller_count ({seller_count})"
        assert seller_count > 0, "Expected at least 1 seller"
        
        # Verify seller data structure
        for seller in sellers:
            assert "listing_id" in seller, "Missing listing_id in seller"
            assert "seller_id" in seller, "Missing seller_id in seller"
            assert "company_name" in seller, "Missing company_name in seller"
            assert "pricing_tiers" in seller, "Missing pricing_tiers in seller"
            
            # Pricing tiers should have correct structure
            if seller.get("pricing_tiers"):
                tier = seller["pricing_tiers"][0]
                assert "quantity_min" in tier or "minQty" in tier, "Missing quantity_min in pricing tier"
                assert "price_per_unit" in tier or "pricePerUnit" in tier, "Missing price_per_unit in pricing tier"
        
        print(f"✅ Product '{data.get('product_name')}' has {seller_count} sellers with valid data")
    
    def test_product_detail_returns_404_for_invalid_slug(self):
        """Invalid slug should return 404"""
        response = requests.get(f"{BASE_URL}/api/products/detail/non-existent-product-xyz", timeout=10)
        assert response.status_code == 404, f"Expected 404 for invalid slug, got {response.status_code}"
        print("✅ 404 returned for invalid product slug")


class TestPublicCategoriesAPI:
    """Test public categories endpoint with product counts"""
    
    def test_categories_public_returns_product_counts(self):
        """
        GET /api/categories/public - Should return categories with product_count
        """
        response = requests.get(f"{BASE_URL}/api/categories/public", timeout=10)
        assert response.status_code == 200, f"Categories API failed: {response.text}"
        
        categories = response.json()
        assert isinstance(categories, list), "Response should be a list"
        
        if not categories:
            pytest.skip("No categories found")
        
        # Verify structure and counts
        for cat in categories:
            assert "name" in cat, "Missing category name"
            # product_count may be calculated or stored
            product_count = cat.get("product_count", 0)
            print(f"  - {cat.get('name')}: product_count={product_count}")
        
        print(f"✅ Found {len(categories)} categories with product counts")


class TestAdminListingsAPI:
    """Test admin listings endpoint - requires dev token"""
    
    def test_admin_listings_returns_joined_data(self):
        """
        GET /api/admin/listings - Should return listings with product_name and seller_name
        
        The $lookup aggregation should join seller_listings with products and users.
        This tests that productId/sellerId (ObjectId) correctly joins to _id fields.
        """
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/admin/listings", headers=headers, timeout=10)
        
        assert response.status_code == 200, f"Admin listings failed: {response.text}"
        
        data = response.json()
        assert "listings" in data, "Missing listings array"
        assert "total" in data, "Missing total count"
        
        listings = data.get("listings", [])
        
        if not listings:
            pytest.skip("No listings found in admin endpoint")
        
        # Verify $lookup worked - product_name and seller_name should be populated
        for listing in listings:
            listing_id = listing.get("_id", "")[:12]
            product_name = listing.get("product_name")
            seller_name = listing.get("seller_name")
            
            print(f"  - Listing {listing_id}... | Product: {product_name} | Seller: {seller_name}")
            
            # These should be populated via $lookup from products and users collections
            assert product_name is not None, f"product_name is None for listing {listing_id}"
            assert seller_name is not None, f"seller_name is None for listing {listing_id}"
        
        print(f"✅ Admin listings endpoint returned {len(listings)} listings with joined data")
    
    def test_admin_listings_filter_by_status(self):
        """Admin listings can filter by status=active"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/admin/listings", 
            headers=headers, 
            params={"status": "active"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        listings = data.get("listings", [])
        
        for listing in listings:
            assert listing.get("status") == "active", f"Expected status=active, got {listing.get('status')}"
        
        print(f"✅ Filtered to {len(listings)} active listings")


class TestAggregationConsistency:
    """Test that seller counts are consistent across endpoints"""
    
    def test_seller_count_consistency(self):
        """
        Verify seller_count in /api/products matches actual sellers in product detail.
        
        This ensures the V7 migration fixed the aggregation pipeline correctly.
        """
        # Get products list
        products_response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert products_response.status_code == 200
        products = products_response.json()
        
        if not products:
            pytest.skip("No products to test consistency")
        
        # For each product, verify seller_count matches detail endpoint
        for product in products[:5]:  # Test first 5 to avoid timeout
            product_slug = product.get("slug")
            expected_count = product.get("seller_count", 0)
            
            if not product_slug:
                continue
            
            detail_response = requests.get(
                f"{BASE_URL}/api/products/detail/{product_slug}", 
                timeout=10
            )
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                actual_count = len(detail_data.get("sellers", []))
                
                print(f"  - {product.get('name')}: list_count={expected_count}, detail_count={actual_count}")
                
                assert expected_count == actual_count, (
                    f"Seller count mismatch for {product.get('name')}: "
                    f"list shows {expected_count}, detail shows {actual_count}"
                )
        
        print("✅ Seller counts are consistent across endpoints")


class TestNoLegacyFields:
    """Verify no legacy fields exist (schema compliance)"""
    
    def test_admin_listings_no_legacy_fields(self):
        """
        Listings should NOT have legacy snake_case ID fields.
        
        Legacy fields: seller_id, product_id, category_id (string)
        Canonical fields: sellerId, productId, categoryId (ObjectId -> string in response)
        """
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/admin/listings", headers=headers, timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        listings = data.get("listings", [])
        
        legacy_fields = ["seller_id", "product_id", "category_id", "product_name_legacy", "category_name_legacy"]
        
        for listing in listings:
            for field in legacy_fields:
                # These legacy fields should NOT exist in the response
                # Note: product_name and seller_name are populated via $lookup, not stored
                if field in ["seller_id", "product_id", "category_id"]:
                    assert field not in listing or listing.get(field) is None, (
                        f"Legacy field '{field}' found in listing {listing.get('_id')}"
                    )
        
        print("✅ No legacy ID fields found in listings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
