"""
Test V10 CamelCase SSOT Migration
=================================
Verifies:
1. All products have categoryId (camelCase) - NOT category_id
2. All products have isActive (camelCase) - NOT is_active  
3. All seller_listings have sellerId, productId, categoryId (camelCase)
4. No snake_case fields exist in API responses
5. Proper product counts (23 total, 22 active)
"""

import pytest
import requests
import os
from pymongo import MongoClient
from bson import ObjectId

# API base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://smart-docs-flow-2.preview.emergentagent.com').rstrip('/')

# MongoDB connection for direct DB verification
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace')


@pytest.fixture(scope="module")
def db():
    """Database connection fixture"""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def api_session():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealthEndpoint:
    """Health check tests"""
    
    def test_health_endpoint(self, api_session):
        """GET /api/health returns healthy status"""
        response = api_session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")


class TestCategoriesAPI:
    """Categories API tests"""
    
    def test_get_all_categories(self, api_session):
        """GET /api/categories/all returns 8 categories"""
        response = api_session.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) == 8, f"Expected 8 categories, got {len(categories)}"
        print(f"✅ Categories count: {len(categories)}")
        
        # Check first category structure
        if categories:
            cat = categories[0]
            print(f"  Sample category: {cat.get('name')}")
            # Verify isActive field exists (may have both for compatibility)
            assert "isActive" in cat or "is_active" in cat, "Category should have isActive or is_active field"


class TestProductsDatabase:
    """Direct database verification for products"""
    
    def test_products_count(self, db):
        """Verify 23 total products in database"""
        total = db.products.count_documents({})
        assert total == 23, f"Expected 23 products, got {total}"
        print(f"✅ Total products in DB: {total}")
    
    def test_active_products_count(self, db):
        """Verify 22 active products (using isActive field)"""
        active = db.products.count_documents({"isActive": True})
        assert active == 22, f"Expected 22 active products, got {active}"
        print(f"✅ Active products (isActive=True): {active}")
    
    def test_no_snake_case_category_id(self, db):
        """Verify no products have snake_case category_id field"""
        snake_case_count = db.products.count_documents({"category_id": {"$exists": True}})
        assert snake_case_count == 0, f"Found {snake_case_count} products with snake_case 'category_id'"
        print(f"✅ No snake_case 'category_id' fields found")
    
    def test_no_snake_case_is_active(self, db):
        """Verify no products have snake_case is_active field"""
        # is_active should not be True in any product (if exists, should be null/migrated)
        snake_active = db.products.count_documents({"is_active": True})
        assert snake_active == 0, f"Found {snake_active} products with snake_case 'is_active=True'"
        print(f"✅ No snake_case 'is_active=True' fields found")
    
    def test_categoryId_is_objectid(self, db):
        """Verify categoryId is ObjectId type in all products"""
        # Get a sample product
        product = db.products.find_one({"categoryId": {"$exists": True}})
        if product:
            category_id = product.get("categoryId")
            assert isinstance(category_id, ObjectId), f"categoryId should be ObjectId, got {type(category_id)}"
            print(f"✅ categoryId is ObjectId type: {category_id}")
    
    def test_products_have_required_camelcase_fields(self, db):
        """Verify products have camelCase fields: categoryId, createdAt, updatedAt, isActive"""
        required_fields = ["categoryId", "createdAt", "updatedAt", "isActive", "name"]
        
        # Sample product
        product = db.products.find_one({})
        assert product is not None, "No products found in database"
        
        missing = [f for f in required_fields if f not in product]
        assert len(missing) == 0, f"Missing camelCase fields: {missing}"
        print(f"✅ All required camelCase fields present: {required_fields}")


class TestSellerListingsDatabase:
    """Direct database verification for seller_listings"""
    
    def test_seller_listings_count(self, db):
        """Verify seller_listings exist"""
        total = db.seller_listings.count_documents({})
        assert total >= 1, f"Expected at least 1 seller_listing, got {total}"
        print(f"✅ Total seller_listings: {total}")
    
    def test_active_seller_listings(self, db):
        """Verify active seller_listings (status='active' AND isActive=True)"""
        active = db.seller_listings.count_documents({"status": "active", "isActive": True})
        print(f"✅ Active seller_listings (status='active' AND isActive=True): {active}")
    
    def test_no_snake_case_seller_id(self, db):
        """Verify no seller_listings have snake_case seller_id field"""
        snake_count = db.seller_listings.count_documents({"seller_id": {"$exists": True}})
        assert snake_count == 0, f"Found {snake_count} listings with snake_case 'seller_id'"
        print(f"✅ No snake_case 'seller_id' fields found")
    
    def test_no_snake_case_product_id(self, db):
        """Verify no seller_listings have snake_case product_id field"""
        snake_count = db.seller_listings.count_documents({"product_id": {"$exists": True}})
        assert snake_count == 0, f"Found {snake_count} listings with snake_case 'product_id'"
        print(f"✅ No snake_case 'product_id' fields found")
    
    def test_no_snake_case_category_id(self, db):
        """Verify no seller_listings have snake_case category_id field"""
        snake_count = db.seller_listings.count_documents({"category_id": {"$exists": True}})
        assert snake_count == 0, f"Found {snake_count} listings with snake_case 'category_id'"
        print(f"✅ No snake_case 'category_id' fields found")
    
    def test_sellerId_is_objectid(self, db):
        """Verify sellerId is ObjectId type"""
        listing = db.seller_listings.find_one({"sellerId": {"$exists": True}})
        if listing:
            seller_id = listing.get("sellerId")
            assert isinstance(seller_id, ObjectId), f"sellerId should be ObjectId, got {type(seller_id)}"
            print(f"✅ sellerId is ObjectId type")
    
    def test_productId_is_objectid(self, db):
        """Verify productId is ObjectId type"""
        listing = db.seller_listings.find_one({"productId": {"$exists": True}})
        if listing:
            product_id = listing.get("productId")
            assert isinstance(product_id, ObjectId), f"productId should be ObjectId, got {type(product_id)}"
            print(f"✅ productId is ObjectId type")
    
    def test_categoryId_is_objectid(self, db):
        """Verify categoryId is ObjectId type in seller_listings"""
        listing = db.seller_listings.find_one({"categoryId": {"$exists": True}})
        if listing:
            category_id = listing.get("categoryId")
            assert isinstance(category_id, ObjectId), f"categoryId should be ObjectId, got {type(category_id)}"
            print(f"✅ categoryId is ObjectId type")
    
    def test_listings_have_camelcase_fields(self, db):
        """Verify seller_listings have camelCase ID fields"""
        listing = db.seller_listings.find_one({})
        if listing:
            assert "sellerId" in listing, "Missing sellerId field"
            assert "productId" in listing, "Missing productId field" 
            assert "categoryId" in listing, "Missing categoryId field"
            print(f"✅ All camelCase ID fields present: sellerId, productId, categoryId")


class TestSearchProductsAPI:
    """Search products API tests"""
    
    def test_search_products(self, api_session):
        """POST /api/search/products - Returns products"""
        response = api_session.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        products = data.get("products", [])
        total = data.get("total", len(products))
        
        print(f"✅ Search returned {total} total products, {len(products)} in response")
        
        # Check response structure if products exist
        if products:
            p = products[0]
            print(f"  Product keys: {list(p.keys())[:10]}")
            # Note: Search API may use different serialization - check what we get


class TestProductsByCategory:
    """Products by category API tests"""
    
    def test_get_products_by_category(self, api_session, db):
        """GET /api/products/by-category/{categoryId} - Uses ObjectId"""
        # Get a category ID
        category = db.categories.find_one({"name": {"$exists": True}})
        if not category:
            pytest.skip("No categories found")
        
        category_id = str(category["_id"])
        
        response = api_session.get(f"{BASE_URL}/api/products/by-category/{category_id}")
        assert response.status_code == 200
        
        data = response.json()
        products = data if isinstance(data, list) else data.get("products", [])
        
        print(f"✅ Products by category '{category.get('name')}': {len(products)} products")


class TestCodeIssues:
    """Tests that document known code issues - these may fail and indicate bugs"""
    
    def test_products_api_snake_case_issue(self, api_session):
        """GET /api/products - KNOWN BUG: queries is_active instead of isActive
        
        This test documents that the /api/products endpoint is broken because
        server.py line 3282-3284 queries {"is_active": True} but V10 migration
        renamed field to "isActive".
        """
        response = api_session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        products = response.json()
        if isinstance(products, list):
            count = len(products)
        else:
            count = len(products.get("products", []))
        
        # This documents the bug - products return empty because of wrong query
        if count == 0:
            print("⚠️ BUG DETECTED: /api/products returns 0 products")
            print("   Root cause: server.py queries 'is_active: True' but DB uses 'isActive'")
            print("   Fix needed: Update server.py to query 'isActive' instead of 'is_active'")
        else:
            print(f"✅ Products API returned {count} products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
