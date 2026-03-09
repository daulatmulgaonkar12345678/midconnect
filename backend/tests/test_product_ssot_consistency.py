"""
Product Identity & SSOT (Single Source of Truth) Consistency Tests
===================================================================

Tests the fix for the P0 bug where /api/products returned 0 products
while other endpoints correctly found listings.

The root cause was 'aggregation-layer identity mismatch' where different
endpoints used inconsistent query logic (productId vs product_name).

Features tested:
1. GET /api/products - Should return products with active seller listings
2. GET /api/categories/public - Should return categories with active seller listings
3. GET /api/products/detail/{productId} - Should return product details with sellers
4. GET /api/products?category_id={id} - Should filter products by category
5. SSOT Consistency - All endpoints return same category_id for same product
"""

import pytest
import requests
import os

# Get BASE_URL from environment (frontend env for public testing)
BASE_URL = "https://auth-overhaul-33.preview.emergentagent.com"

# Expected test data (from seed data)
EXPECTED_PRODUCT_ID = "6981a9a74108b0cbd93aa631"
EXPECTED_PRODUCT_NAME = "Three Phase AC Motor"
EXPECTED_CATEGORY_ID = "6981a9a74108b0cbd93aa630"
EXPECTED_CATEGORY_NAME = "Electrical Equipment"


class TestProductsEndpoint:
    """Tests for GET /api/products endpoint"""
    
    def test_products_returns_list(self):
        """GET /api/products should return a list"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ /api/products returns list with {len(data)} products")
    
    def test_products_returns_at_least_one(self):
        """GET /api/products should return at least 1 product (P0 BUG FIX)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, f"P0 BUG: /api/products returned {len(data)} products, expected >= 1"
        print(f"✓ P0 Bug Fix Verified: /api/products returns {len(data)} product(s)")
    
    def test_products_has_seller_count(self):
        """Products should have seller_count > 0 for active listings"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 product to test"
        
        product = data[0]
        assert "seller_count" in product, "Product missing seller_count field"
        assert product["seller_count"] > 0, f"seller_count should be > 0, got {product['seller_count']}"
        print(f"✓ Product has seller_count: {product['seller_count']}")
    
    def test_products_has_min_price(self):
        """Products should have min_price from pricing tiers"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 product to test"
        
        product = data[0]
        assert "min_price" in product, "Product missing min_price field"
        assert product["min_price"] is not None, "min_price should not be None"
        assert product["min_price"] > 0, f"min_price should be > 0, got {product['min_price']}"
        print(f"✓ Product has min_price: {product['min_price']}")
    
    def test_products_has_category_id(self):
        """Products should have category_id from products collection (SSOT)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 product to test"
        
        product = data[0]
        assert "category_id" in product, "Product missing category_id field"
        assert product["category_id"] == EXPECTED_CATEGORY_ID, \
            f"Expected category_id '{EXPECTED_CATEGORY_ID}', got '{product.get('category_id')}'"
        print(f"✓ Product has correct category_id: {product['category_id']}")
    
    def test_products_has_category_name(self):
        """Products should have category_name from categories collection"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 product to test"
        
        product = data[0]
        assert "category_name" in product, "Product missing category_name field"
        assert product["category_name"] == EXPECTED_CATEGORY_NAME, \
            f"Expected category_name '{EXPECTED_CATEGORY_NAME}', got '{product.get('category_name')}'"
        print(f"✓ Product has correct category_name: {product['category_name']}")


class TestCategoriesPublicEndpoint:
    """Tests for GET /api/categories/public endpoint"""
    
    def test_categories_public_returns_list(self):
        """GET /api/categories/public should return a list"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ /api/categories/public returns list with {len(data)} categories")
    
    def test_categories_public_returns_at_least_one(self):
        """GET /api/categories/public should return at least 1 category"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, f"Expected >= 1 categories, got {len(data)}"
        print(f"✓ /api/categories/public returns {len(data)} category(ies)")
    
    def test_categories_public_has_correct_category(self):
        """Should return 'Electrical Equipment' category"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 category to test"
        
        category = data[0]
        assert category["_id"] == EXPECTED_CATEGORY_ID, \
            f"Expected category _id '{EXPECTED_CATEGORY_ID}', got '{category.get('_id')}'"
        assert category["name"] == EXPECTED_CATEGORY_NAME, \
            f"Expected category name '{EXPECTED_CATEGORY_NAME}', got '{category.get('name')}'"
        print(f"✓ Found correct category: {category['name']} (ID: {category['_id']})")
    
    def test_categories_public_has_product_count(self):
        """Categories should have product_count > 0"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Need at least 1 category to test"
        
        category = data[0]
        assert "product_count" in category, "Category missing product_count field"
        assert category["product_count"] > 0, f"product_count should be > 0, got {category['product_count']}"
        print(f"✓ Category has product_count: {category['product_count']}")


class TestProductDetailEndpoint:
    """Tests for GET /api/products/detail/{productId} endpoint"""
    
    def test_product_detail_returns_200(self):
        """GET /api/products/detail/{id} should return 200 for valid product"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ /api/products/detail/{EXPECTED_PRODUCT_ID[:8]}... returns 200")
    
    def test_product_detail_returns_correct_product(self):
        """Should return correct product data"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("product_id") == EXPECTED_PRODUCT_ID, \
            f"Expected product_id '{EXPECTED_PRODUCT_ID}', got '{data.get('product_id')}'"
        assert data.get("product_name") == EXPECTED_PRODUCT_NAME, \
            f"Expected product_name '{EXPECTED_PRODUCT_NAME}', got '{data.get('product_name')}'"
        print(f"✓ Product detail correct: {data['product_name']}")
    
    def test_product_detail_has_sellers(self):
        """Product detail should include sellers list"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "sellers" in data, "Response missing sellers field"
        assert "seller_count" in data, "Response missing seller_count field"
        assert len(data["sellers"]) > 0, "Should have at least 1 seller"
        assert data["seller_count"] == len(data["sellers"]), \
            f"seller_count ({data['seller_count']}) should match sellers array length ({len(data['sellers'])})"
        print(f"✓ Product has {data['seller_count']} seller(s)")
    
    def test_product_detail_has_category_id(self):
        """Product detail should have category_id from products collection (SSOT)"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "category_id" in data, "Response missing category_id field"
        assert data["category_id"] == EXPECTED_CATEGORY_ID, \
            f"Expected category_id '{EXPECTED_CATEGORY_ID}', got '{data.get('category_id')}'"
        print(f"✓ Product detail has correct category_id: {data['category_id']}")
    
    def test_product_detail_has_category_name(self):
        """Product detail should have category_name from categories collection"""
        response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "category_name" in data, "Response missing category_name field"
        assert data["category_name"] == EXPECTED_CATEGORY_NAME, \
            f"Expected category_name '{EXPECTED_CATEGORY_NAME}', got '{data.get('category_name')}'"
        print(f"✓ Product detail has correct category_name: {data['category_name']}")
    
    def test_product_detail_not_found(self):
        """Should return 404 for non-existent product"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/products/detail/{fake_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent product returns 404")


class TestProductsCategoryFilter:
    """Tests for GET /api/products?category_id={id} filter"""
    
    def test_products_filter_by_valid_category(self):
        """Should filter products by category_id"""
        response = requests.get(f"{BASE_URL}/api/products?category_id={EXPECTED_CATEGORY_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 1, f"Expected >= 1 products in category, got {len(data)}"
        
        # All returned products should have the requested category_id
        for product in data:
            assert product.get("category_id") == EXPECTED_CATEGORY_ID, \
                f"Product {product.get('_id')} has wrong category_id: {product.get('category_id')}"
        
        print(f"✓ Filter by category_id returns {len(data)} product(s)")
    
    def test_products_filter_by_invalid_category(self):
        """Should return empty list for non-existent category"""
        fake_category_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/products?category_id={fake_category_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 0, f"Expected 0 products for non-existent category, got {len(data)}"
        print(f"✓ Filter by non-existent category returns empty list")


class TestSSOTConsistency:
    """
    CRITICAL: Tests that all three endpoints return SAME category_id
    This is the core of the SSOT (Single Source of Truth) policy fix.
    """
    
    def test_category_id_consistency_across_endpoints(self):
        """
        All three endpoints should return the SAME category_id for the SAME product.
        This was the root cause of the P0 bug - inconsistent identity resolution.
        """
        # Get category_id from /api/products
        products_response = requests.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products_data = products_response.json()
        assert len(products_data) > 0, "Need products to test"
        products_category_id = products_data[0].get("category_id")
        
        # Get category_id from /api/categories/public
        categories_response = requests.get(f"{BASE_URL}/api/categories/public")
        assert categories_response.status_code == 200
        categories_data = categories_response.json()
        assert len(categories_data) > 0, "Need categories to test"
        categories_category_id = categories_data[0].get("_id")
        
        # Get category_id from /api/products/detail/{id}
        detail_response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        detail_category_id = detail_data.get("category_id")
        
        # CRITICAL ASSERTION: All three should be identical
        assert products_category_id == categories_category_id == detail_category_id, \
            f"SSOT VIOLATION: category_id inconsistency!\n" \
            f"  /api/products: {products_category_id}\n" \
            f"  /api/categories/public: {categories_category_id}\n" \
            f"  /api/products/detail: {detail_category_id}"
        
        print(f"✓ SSOT VERIFIED: All endpoints return same category_id: {products_category_id}")
    
    def test_category_name_consistency_across_endpoints(self):
        """Category name should be consistent across endpoints"""
        # Get category_name from /api/products
        products_response = requests.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products_data = products_response.json()
        assert len(products_data) > 0
        products_category_name = products_data[0].get("category_name")
        
        # Get category_name from /api/categories/public
        categories_response = requests.get(f"{BASE_URL}/api/categories/public")
        assert categories_response.status_code == 200
        categories_data = categories_response.json()
        assert len(categories_data) > 0
        categories_category_name = categories_data[0].get("name")
        
        # Get category_name from /api/products/detail/{id}
        detail_response = requests.get(f"{BASE_URL}/api/products/detail/{EXPECTED_PRODUCT_ID}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        detail_category_name = detail_data.get("category_name")
        
        # All should be the same
        assert products_category_name == categories_category_name == detail_category_name, \
            f"Category name inconsistency!\n" \
            f"  /api/products: {products_category_name}\n" \
            f"  /api/categories/public: {categories_category_name}\n" \
            f"  /api/products/detail: {detail_category_name}"
        
        print(f"✓ Category name consistent across endpoints: {products_category_name}")
    
    def test_product_id_consistency(self):
        """Product ID should be consistent between /api/products and /api/products/detail"""
        products_response = requests.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products_data = products_response.json()
        assert len(products_data) > 0
        products_product_id = products_data[0].get("_id")
        
        detail_response = requests.get(f"{BASE_URL}/api/products/detail/{products_product_id}")
        assert detail_response.status_code == 200, \
            f"Product ID from /api/products should be valid in /api/products/detail"
        detail_data = detail_response.json()
        detail_product_id = detail_data.get("product_id")
        
        assert products_product_id == detail_product_id, \
            f"Product ID mismatch: /api/products {products_product_id} != /api/products/detail {detail_product_id}"
        
        print(f"✓ Product ID consistent: {products_product_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
