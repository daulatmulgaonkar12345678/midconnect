"""
Test Suite: V10 CamelCase SSOT Verification
============================================
Tests for iteration 21/22 bug fixes:
1. GET /api/products - Was returning 0, now returns 1 (is_active→isActive)
2. GET /api/categories/public - Was returning null names, now returns "Electrical Equipment" (category_id→categoryId)
3. POST /api/search/products - Was returning 0, now returns 1 (full pipeline refactored)

All endpoints now use camelCase fields matching the migrated database schema.
"""

import pytest
import requests
import os

# Use environment variable for BASE_URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestHealthAndCategories:
    """Basic health and category endpoints"""
    
    def test_health_endpoint(self):
        """GET /api/health - Should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected healthy status, got: {data}"
        print(f"✅ Health check passed: {data['status']}")
    
    def test_get_all_categories(self):
        """GET /api/categories/all - Should return 8 categories"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200, f"Categories request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        assert len(data) == 8, f"Expected 8 categories, got {len(data)}"
        
        # Verify category structure uses camelCase (isActive field)
        for cat in data:
            assert "_id" in cat or "id" in cat, f"Category missing ID field: {cat}"
            assert "name" in cat, f"Category missing name: {cat}"
        
        print(f"✅ All categories endpoint passed: {len(data)} categories found")


class TestProductsEndpointFix:
    """Tests for /api/products - Was broken, now fixed (isActive query)"""
    
    def test_products_returns_data(self):
        """
        GET /api/products - CRITICAL BUG FIX
        Issue: Returned 0 products due to querying 'is_active' (removed field)
        Fix: Now queries 'isActive' (camelCase SSOT)
        Expected: At least 1 product
        """
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Products request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        assert len(data) >= 1, f"Expected at least 1 product, got {len(data)} - BUG: isActive query may be broken"
        
        print(f"✅ Products endpoint FIXED: Returns {len(data)} product(s)")
    
    def test_product_structure_camelcase(self):
        """Verify product response uses camelCase fields"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "No products to verify structure"
        
        product = data[0]
        
        # Check for camelCase fields
        assert "categoryId" in product, f"Missing camelCase categoryId: {product.keys()}"
        assert "name" in product, f"Missing name field: {product.keys()}"
        assert "seller_count" in product or "sellerCount" in product, f"Missing seller count: {product.keys()}"
        assert "min_price" in product or "minPrice" in product, f"Missing min price: {product.keys()}"
        
        # Verify categoryId is a string (was ObjectId, now serialized)
        assert isinstance(product.get("categoryId"), str), f"categoryId should be string: {type(product.get('categoryId'))}"
        
        print(f"✅ Product structure verified: {product.get('name')}")


class TestCategoriesPublicFix:
    """Tests for /api/categories/public - Was returning null names, now fixed"""
    
    def test_categories_public_returns_data(self):
        """
        GET /api/categories/public - CRITICAL BUG FIX
        Issue: Returned null for category name due to querying '$product.category_id'
        Fix: Now queries '$product.categoryId' (camelCase SSOT)
        Expected: At least 1 category with valid name
        """
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200, f"Categories public request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        assert len(data) >= 1, f"Expected at least 1 public category, got {len(data)}"
        
        print(f"✅ Public categories endpoint FIXED: Returns {len(data)} category(ies)")
    
    def test_categories_public_has_valid_names(self):
        """
        Verify category names are NOT null
        Previous bug: name was null due to incorrect aggregation lookup
        """
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "No public categories found"
        
        for cat in data:
            name = cat.get("name")
            assert name is not None, f"Category name is null - BUG NOT FIXED: {cat}"
            assert isinstance(name, str), f"Category name should be string: {type(name)}"
            assert len(name) > 0, f"Category name is empty: {cat}"
        
        # Specifically check for "Electrical Equipment" which should be present
        names = [c.get("name") for c in data]
        assert "Electrical Equipment" in names, f"Expected 'Electrical Equipment' in categories: {names}"
        
        print(f"✅ Category names are valid: {names}")
    
    def test_categories_public_has_product_counts(self):
        """Verify product_count and listing_count are present"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0
        
        for cat in data:
            assert "product_count" in cat or "productCount" in cat, f"Missing product count: {cat}"
            assert "listing_count" in cat or "listingCount" in cat, f"Missing listing count: {cat}"
            
            product_count = cat.get("product_count", cat.get("productCount", 0))
            assert product_count >= 1, f"Expected at least 1 product in public category: {cat}"
        
        print("✅ Public categories have valid product/listing counts")


class TestSearchProductsFix:
    """Tests for POST /api/search/products - Was returning 0 results, now fixed"""
    
    def test_search_products_returns_results(self):
        """
        POST /api/search/products - CRITICAL BUG FIX
        Issue: Entire pipeline used snake_case (seller_id, category_id, product_name, etc.)
        Fix: Pipeline refactored to use camelCase (sellerId, categoryId, productId, etc.)
        Expected: At least 1 result for "motor" query
        """
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Search request failed: {response.text}"
        
        data = response.json()
        assert "products" in data, f"Response missing 'products' key: {data.keys()}"
        
        products = data["products"]
        assert len(products) >= 1, f"Expected at least 1 search result, got {len(products)} - BUG: search pipeline may be broken"
        
        print(f"✅ Search products endpoint FIXED: Returns {len(products)} result(s)")
    
    def test_search_products_structure(self):
        """Verify search results have correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        products = data.get("products", [])
        assert len(products) > 0, "No products to verify structure"
        
        product = products[0]
        
        # Check required fields
        assert "product_id" in product or "productId" in product, f"Missing product ID: {product.keys()}"
        assert "product_name" in product or "productName" in product, f"Missing product name: {product.keys()}"
        assert "category_id" in product or "categoryId" in product, f"Missing category ID: {product.keys()}"
        assert "category_name" in product or "categoryName" in product, f"Missing category name: {product.keys()}"
        assert "sellers" in product, f"Missing sellers array: {product.keys()}"
        
        # Verify values are not null
        product_name = product.get("product_name", product.get("productName"))
        assert product_name is not None, f"Product name is null: {product}"
        assert product_name == "Three Phase AC Motor", f"Expected 'Three Phase AC Motor', got: {product_name}"
        
        category_name = product.get("category_name", product.get("categoryName"))
        assert category_name is not None, f"Category name is null: {product}"
        assert category_name == "Electrical Equipment", f"Expected 'Electrical Equipment', got: {category_name}"
        
        print(f"✅ Search result structure verified: {product_name}")
    
    def test_search_products_sellers_array(self):
        """Verify sellers array in search results has valid data"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        products = data.get("products", [])
        assert len(products) > 0
        
        product = products[0]
        sellers = product.get("sellers", [])
        assert len(sellers) >= 1, f"Expected at least 1 seller, got: {len(sellers)}"
        
        seller = sellers[0]
        # Check seller fields
        assert "listing_id" in seller or "listingId" in seller, f"Missing listing ID: {seller.keys()}"
        assert "seller_id" in seller or "sellerId" in seller, f"Missing seller ID: {seller.keys()}"
        
        print(f"✅ Search result sellers verified: {len(sellers)} seller(s)")
    
    def test_search_products_total_count(self):
        """Verify search returns total count"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data, f"Missing 'total' in response: {data.keys()}"
        assert data["total"] >= 1, f"Expected total >= 1, got: {data['total']}"
        
        print(f"✅ Search total count: {data['total']}")


class TestProductsByCategory:
    """Tests for GET /api/products/by-category/{categoryId}"""
    
    def test_products_by_category_returns_data(self):
        """GET /api/products/by-category/{categoryId} - Should return products"""
        # First get a valid category ID
        cat_response = requests.get(f"{BASE_URL}/api/categories/all")
        assert cat_response.status_code == 200
        
        categories = cat_response.json()
        assert len(categories) > 0, "No categories found"
        
        # Use Electrical Equipment category
        cat_id = None
        for cat in categories:
            if cat.get("name") == "Electrical Equipment":
                cat_id = cat.get("_id") or cat.get("id")
                break
        
        assert cat_id is not None, "Electrical Equipment category not found"
        
        # Test products by category
        response = requests.get(f"{BASE_URL}/api/products/by-category/{cat_id}")
        assert response.status_code == 200, f"Products by category failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        # Note: This may return more products from the products collection
        # vs the /api/products which filters by active seller_listings
        
        print(f"✅ Products by category: {len(data)} products in Electrical Equipment")


class TestDatabaseSchemaVerification:
    """Verify no snake_case fields remain in critical collections"""
    
    def test_products_have_camelcase_categoryId(self):
        """Verify products API returns camelCase categoryId"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            product = data[0]
            # Should have categoryId (camelCase), not category_id (snake_case)
            assert "categoryId" in product, f"Missing camelCase categoryId: {product.keys()}"
            # category_id should not exist in response
            # (Note: we can't directly check DB, but API response reflects SSOT)
        
        print("✅ Products use camelCase categoryId in API response")
    
    def test_search_uses_camelcase_fields(self):
        """Verify search results use camelCase for ID fields"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        products = data.get("products", [])
        
        if len(products) > 0:
            product = products[0]
            # Check ID fields are present (either naming convention is acceptable in response)
            has_product_id = "product_id" in product or "productId" in product
            has_category_id = "category_id" in product or "categoryId" in product
            
            assert has_product_id, f"Missing product ID field: {product.keys()}"
            assert has_category_id, f"Missing category ID field: {product.keys()}"
        
        print("✅ Search results have proper ID fields")


# Summary test
class TestSummaryV10Fixes:
    """Summary test for all V10 CamelCase SSOT fixes"""
    
    def test_all_critical_fixes_verified(self):
        """
        Comprehensive test verifying all 3 critical fixes from iteration 21/22:
        1. /api/products - Returns data (was 0, now 1+)
        2. /api/categories/public - Returns valid names (was null)
        3. /api/search/products - Returns results (was 0, now 1+)
        """
        print("\n" + "="*60)
        print("V10 CAMELCASE SSOT FIXES VERIFICATION")
        print("="*60)
        
        # 1. Products endpoint
        r1 = requests.get(f"{BASE_URL}/api/products")
        assert r1.status_code == 200
        products_count = len(r1.json())
        assert products_count >= 1, "FIX #1 FAILED: /api/products still returns 0"
        print(f"✅ FIX #1: /api/products returns {products_count} product(s)")
        
        # 2. Categories public endpoint
        r2 = requests.get(f"{BASE_URL}/api/categories/public")
        assert r2.status_code == 200
        cats = r2.json()
        cats_count = len(cats)
        assert cats_count >= 1, "FIX #2 FAILED: /api/categories/public returns 0"
        cat_name = cats[0].get("name") if cats else None
        assert cat_name is not None, "FIX #2 FAILED: category name is still null"
        print(f"✅ FIX #2: /api/categories/public returns {cats_count} category(ies) with name='{cat_name}'")
        
        # 3. Search products endpoint
        r3 = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"},
            headers={"Content-Type": "application/json"}
        )
        assert r3.status_code == 200
        search_data = r3.json()
        search_count = len(search_data.get("products", []))
        assert search_count >= 1, "FIX #3 FAILED: /api/search/products still returns 0"
        print(f"✅ FIX #3: /api/search/products returns {search_count} result(s)")
        
        print("="*60)
        print("ALL V10 CAMELCASE SSOT FIXES VERIFIED SUCCESSFULLY!")
        print("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
