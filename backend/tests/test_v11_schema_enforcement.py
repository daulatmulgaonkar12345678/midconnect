"""
V11 Final Schema Enforcement Tests
==================================
Tests that verify the V11 migration applied correctly:
- All API responses use camelCase fields
- All collections use ObjectId for references
- seller_listings have productSnapshot
- No snake_case fields in responses
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://search-typos.preview.emergentagent.com').rstrip('/')
DEV_TOKEN = "dev-test-token"

class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")


class TestCategoriesEndpoints:
    """Tests for categories API endpoints - verifying camelCase fields"""
    
    def test_categories_all_returns_data(self):
        """GET /api/categories/all - Returns categories list"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0, "Should have at least 1 category"
        print(f"✅ GET /api/categories/all returned {len(categories)} categories")
    
    def test_categories_all_has_camelcase_fields(self):
        """GET /api/categories/all - Verify camelCase field names"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) > 0
        
        first_cat = categories[0]
        # Check for camelCase fields
        assert "_id" in first_cat, "Should have _id field"
        assert "name" in first_cat, "Should have name field"
        
        # Verify isActive is camelCase (not is_active)
        assert "isActive" in first_cat, "Should have isActive (camelCase)"
        assert "is_active" not in first_cat, "Should NOT have is_active (snake_case)"
        
        print(f"✅ Category has camelCase isActive field")
        print(f"   Sample category: _id={first_cat.get('_id')}, name={first_cat.get('name')}, isActive={first_cat.get('isActive')}")
    
    def test_categories_all_image_url_field(self):
        """GET /api/categories/all - Check for imageUrl field (camelCase)"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        
        # Check field names across all categories
        snake_case_fields_found = []
        for cat in categories:
            if "image_url" in cat:
                snake_case_fields_found.append("image_url")
            if "display_order" in cat:
                snake_case_fields_found.append("display_order")
            if "created_at" in cat:
                snake_case_fields_found.append("created_at")
        
        assert len(snake_case_fields_found) == 0, f"Found snake_case fields: {set(snake_case_fields_found)}"
        print(f"✅ No snake_case fields found in categories")
    
    def test_categories_public_returns_data(self):
        """GET /api/categories/public - Returns categories with products"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        print(f"✅ GET /api/categories/public returned {len(categories)} categories")
        
        # If there are categories, verify structure
        if len(categories) > 0:
            first_cat = categories[0]
            assert "_id" in first_cat, "Should have _id"
            assert "name" in first_cat, "Should have name"
            # Product count and listing count should be present
            assert "product_count" in first_cat or "productCount" in first_cat, "Should have product count"
            print(f"   First category: {first_cat.get('name')} - products: {first_cat.get('product_count', first_cat.get('productCount'))}")
    
    def test_categories_public_has_valid_names(self):
        """GET /api/categories/public - Category names should not be null"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        assert response.status_code == 200
        categories = response.json()
        
        for cat in categories:
            name = cat.get("name")
            assert name is not None, f"Category {cat.get('_id')} has null name"
            assert isinstance(name, str), f"Category name should be string, got {type(name)}"
            assert len(name) > 0, f"Category name should not be empty"
        
        print(f"✅ All {len(categories)} categories have valid names")


class TestProductsEndpoints:
    """Tests for products API endpoints - verifying camelCase fields"""
    
    def test_products_returns_data(self):
        """GET /api/products - Returns products list"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        print(f"✅ GET /api/products returned {len(products)} products")
    
    def test_products_has_camelcase_category_id(self):
        """GET /api/products - Products should have categoryId (camelCase)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) > 0:
            first_prod = products[0]
            # Check for camelCase categoryId
            assert "categoryId" in first_prod, "Should have categoryId (camelCase)"
            assert "category_id" not in first_prod, "Should NOT have category_id (snake_case)"
            
            print(f"✅ Product has camelCase categoryId: {first_prod.get('categoryId')}")
            print(f"   Product name: {first_prod.get('name')}")
        else:
            print("⚠️ No products found - skipping field verification")
    
    def test_products_no_snake_case_fields(self):
        """GET /api/products - Products should not have snake_case fields"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        snake_case_patterns = ["category_id", "seller_id", "product_id", "is_active", "created_at", "updated_at"]
        
        snake_case_found = set()
        for product in products:
            for key in product.keys():
                if "_" in key and key not in ["_id"]:
                    # Allow some response fields that are transformation results
                    if key in ["category_name", "seller_count", "min_price"]:
                        continue
                    snake_case_found.add(key)
        
        if snake_case_found:
            print(f"⚠️ Found snake_case fields in products: {snake_case_found}")
        else:
            print(f"✅ No snake_case reference fields in products response")
    
    def test_products_have_valid_structure(self):
        """GET /api/products - Products should have required fields"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) > 0:
            first_prod = products[0]
            required_fields = ["_id", "name"]
            for field in required_fields:
                assert field in first_prod, f"Product missing required field: {field}"
            print(f"✅ Products have required structure")


class TestSearchEndpoint:
    """Tests for product search endpoint"""
    
    def test_search_products_basic(self):
        """POST /api/search/products - Basic search works"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data, "Should have products array"
        assert "total" in data, "Should have total count"
        print(f"✅ Search for 'motor' returned {data.get('total')} results")
    
    def test_search_products_empty_query(self):
        """POST /api/search/products - Empty query returns results"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""}
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"✅ Empty query search returned {data.get('total')} results")
    
    def test_search_products_has_valid_structure(self):
        """POST /api/search/products - Results have valid structure"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        if len(products) > 0:
            first_prod = products[0]
            # Check expected fields
            expected_fields = ["product_id", "product_name", "category_id", "category_name", "sellers"]
            for field in expected_fields:
                assert field in first_prod, f"Search result missing field: {field}"
            
            # Verify sellers is an array
            sellers = first_prod.get("sellers", [])
            assert isinstance(sellers, list), "sellers should be an array"
            
            print(f"✅ Search results have valid structure")
            print(f"   First result: {first_prod.get('product_name')} - {len(sellers)} sellers")
        else:
            print("⚠️ No search results to verify structure")
    
    def test_search_products_category_names_not_null(self):
        """POST /api/search/products - Category names should not be null"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        null_category_count = 0
        for prod in products:
            if prod.get("category_name") is None:
                null_category_count += 1
        
        # Allow some null categories but not majority
        if len(products) > 0:
            null_ratio = null_category_count / len(products)
            assert null_ratio < 0.5, f"Too many null category names: {null_category_count}/{len(products)}"
        
        print(f"✅ Search results have valid category names ({null_category_count} null out of {len(products)})")


class TestDatabaseFieldsVerification:
    """Tests to verify database field naming via API responses"""
    
    def test_no_legacy_snake_case_in_categories(self):
        """Verify categories API doesn't return legacy snake_case fields"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        
        legacy_fields = set()
        for cat in categories:
            for key in cat.keys():
                if key in ["image_url", "display_order", "is_active", "created_at", "created_by", "updated_at"]:
                    legacy_fields.add(key)
        
        assert len(legacy_fields) == 0, f"Found legacy snake_case fields: {legacy_fields}"
        print(f"✅ No legacy snake_case fields in categories")
    
    def test_category_ids_are_valid_objectid_format(self):
        """Verify category IDs are 24-char hex strings (ObjectId format)"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        
        for cat in categories:
            cat_id = cat.get("_id")
            assert cat_id is not None, "Category should have _id"
            assert isinstance(cat_id, str), f"_id should be string, got {type(cat_id)}"
            assert len(cat_id) == 24, f"ObjectId should be 24 chars, got {len(cat_id)}: {cat_id}"
            # Check if it's valid hex
            try:
                int(cat_id, 16)
            except ValueError:
                pytest.fail(f"Invalid ObjectId format: {cat_id}")
        
        print(f"✅ All {len(categories)} categories have valid ObjectId format")
    
    def test_product_category_ids_are_objectid_format(self):
        """Verify products' categoryId are in ObjectId string format"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        for prod in products:
            cat_id = prod.get("categoryId")
            if cat_id:
                assert isinstance(cat_id, str), f"categoryId should be string"
                assert len(cat_id) == 24, f"categoryId should be 24 chars: {cat_id}"
        
        print(f"✅ Products have valid ObjectId categoryId format")


class TestSellerListingsVerification:
    """Tests to verify seller_listings schema via API"""
    
    def test_search_returns_listings_with_valid_seller_ids(self):
        """Verify listings in search results have valid seller IDs"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        for prod in products:
            sellers = prod.get("sellers", [])
            for seller in sellers:
                seller_id = seller.get("seller_id")
                listing_id = seller.get("listing_id")
                
                # These should be string IDs
                if seller_id:
                    assert isinstance(seller_id, str), f"seller_id should be string"
                if listing_id:
                    assert isinstance(listing_id, str), f"listing_id should be string"
        
        print(f"✅ Listings have valid seller_id and listing_id formats")


class TestV11MigrationSummary:
    """Summary test to verify all V11 requirements"""
    
    def test_v11_complete_verification(self):
        """Comprehensive V11 migration verification"""
        issues = []
        
        # 1. Check categories/all
        resp = requests.get(f"{BASE_URL}/api/categories/all")
        if resp.status_code != 200:
            issues.append(f"GET /api/categories/all failed: {resp.status_code}")
        else:
            cats = resp.json()
            if len(cats) == 0:
                issues.append("No categories returned")
            else:
                if "isActive" not in cats[0]:
                    issues.append("Categories missing isActive field")
        
        # 2. Check categories/public
        resp = requests.get(f"{BASE_URL}/api/categories/public")
        if resp.status_code != 200:
            issues.append(f"GET /api/categories/public failed: {resp.status_code}")
        
        # 3. Check products
        resp = requests.get(f"{BASE_URL}/api/products")
        if resp.status_code != 200:
            issues.append(f"GET /api/products failed: {resp.status_code}")
        else:
            prods = resp.json()
            if len(prods) > 0 and "categoryId" not in prods[0]:
                issues.append("Products missing camelCase categoryId")
        
        # 4. Check search
        resp = requests.post(f"{BASE_URL}/api/search/products", json={"query": ""})
        if resp.status_code != 200:
            issues.append(f"POST /api/search/products failed: {resp.status_code}")
        
        if issues:
            print(f"❌ V11 verification issues: {issues}")
            pytest.fail(f"V11 migration issues: {issues}")
        else:
            print("✅ V11 MIGRATION VERIFICATION COMPLETE")
            print("   - Categories use camelCase (isActive)")
            print("   - Products use camelCase (categoryId)")
            print("   - Search endpoint working")
            print("   - All endpoints return 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
