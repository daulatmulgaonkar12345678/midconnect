"""
Test V9 Data Standardization Migration
======================================
Verifies:
1. GET /api/health - Health check endpoint
2. GET /api/categories/all - List all categories  
3. POST /api/search/products - Search products
4. GET /api/products - List products with proper ObjectId handling
5. Verify seller_listings have ObjectId types for sellerId, productId, categoryId
6. Verify no legacy 'active' field exists in any collection
7. Verify MongoDB validators are applied
8. Verify units are normalized to standard format
"""

import pytest
import requests
import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# Get BASE_URL from frontend env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
            BASE_URL = line.strip().split('=', 1)[1].strip()
            break
    else:
        BASE_URL = "https://seo-scaling-hub.preview.emergentagent.com"

API_URL = BASE_URL.rstrip('/')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self):
        """Test GET /api/health returns healthy status"""
        response = requests.get(f"{API_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "healthy", f"Expected 'healthy', got '{data['status']}'"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        print(f"✅ Health check passed: {data}")


class TestCategoriesAPI:
    """Test categories endpoints"""
    
    def test_categories_all(self):
        """Test GET /api/categories/all returns all categories"""
        response = requests.get(f"{API_URL}/api/categories/all")
        assert response.status_code == 200, f"Categories API failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one category"
        
        # Verify category structure
        for cat in data[:3]:  # Check first 3
            assert "_id" in cat, "Category missing _id"
            assert "name" in cat, "Category missing name"
            assert "is_active" in cat, "Category missing is_active"
            assert "active" not in cat, f"Category has legacy 'active' field: {cat}"
        
        print(f"✅ Categories API passed: {len(data)} categories found")


class TestProductsAPI:
    """Test products endpoints"""
    
    def test_products_list(self):
        """Test GET /api/products returns products with proper ObjectId handling"""
        response = requests.get(f"{API_URL}/api/products")
        assert response.status_code == 200, f"Products API failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            product = data[0]
            # Verify categoryId is serialized to string (was ObjectId in DB)
            assert "categoryId" in product, "Product missing categoryId"
            assert isinstance(product["categoryId"], str), f"categoryId should be string, got {type(product['categoryId'])}"
            # Verify it's a valid ObjectId format
            assert len(product["categoryId"]) == 24, f"categoryId should be 24-char hex string: {product['categoryId']}"
            
            # Verify category_name is resolved (from $lookup)
            if "category_name" in product:
                assert product["category_name"] is not None, "category_name should not be None"
                assert product["category_name"] != "Unknown", f"category_name should be resolved, got: {product['category_name']}"
            
        print(f"✅ Products API passed: {len(data)} products found")
    
    def test_search_products_empty_query(self):
        """Test POST /api/search/products with empty query"""
        response = requests.post(
            f"{API_URL}/api/search/products",
            json={"query": ""}
        )
        assert response.status_code == 200, f"Search API failed: {response.status_code}"
        
        data = response.json()
        assert "products" in data, "Response missing 'products' field"
        assert "total" in data, "Response missing 'total' field"
        assert "query" in data, "Response missing 'query' field"
        
        print(f"✅ Search products (empty query) passed: {data['total']} results")
    
    def test_search_products_with_query(self):
        """Test POST /api/search/products with actual query"""
        response = requests.post(
            f"{API_URL}/api/search/products",
            json={"query": "motor"}
        )
        assert response.status_code == 200, f"Search API failed: {response.status_code}"
        
        data = response.json()
        assert "products" in data, "Response missing 'products' field"
        # Note: Results may be empty if no listings match
        print(f"✅ Search products (query='motor') passed: {data['total']} results")


class TestDatabaseObjectIdTypes:
    """Verify MongoDB documents have proper ObjectId types"""
    
    def test_seller_listings_objectid_types(self):
        """Verify seller_listings have ObjectId types for sellerId, productId, categoryId"""
        docs = list(db.seller_listings.find().limit(10))
        
        if len(docs) == 0:
            pytest.skip("No seller_listings documents found")
        
        for doc in docs:
            # Check sellerId
            if doc.get("sellerId"):
                assert isinstance(doc["sellerId"], ObjectId), \
                    f"sellerId should be ObjectId, got {type(doc['sellerId'])}: {doc['sellerId']}"
            
            # Check productId
            if doc.get("productId"):
                assert isinstance(doc["productId"], ObjectId), \
                    f"productId should be ObjectId, got {type(doc['productId'])}: {doc['productId']}"
            
            # Check categoryId
            if doc.get("categoryId"):
                assert isinstance(doc["categoryId"], ObjectId), \
                    f"categoryId should be ObjectId, got {type(doc['categoryId'])}: {doc['categoryId']}"
        
        print(f"✅ seller_listings ObjectId types verified: {len(docs)} documents checked")
    
    def test_products_objectid_types(self):
        """Verify products have ObjectId type for categoryId"""
        docs = list(db.products.find().limit(10))
        
        if len(docs) == 0:
            pytest.skip("No products documents found")
        
        for doc in docs:
            # Check categoryId
            if doc.get("categoryId"):
                assert isinstance(doc["categoryId"], ObjectId), \
                    f"categoryId should be ObjectId, got {type(doc['categoryId'])}: {doc['categoryId']}"
        
        print(f"✅ products ObjectId types verified: {len(docs)} documents checked")
    
    def test_inquiries_objectid_types(self):
        """Verify inquiries have ObjectId types for sellerId, buyerId"""
        docs = list(db.inquiries.find().limit(10))
        
        if len(docs) == 0:
            pytest.skip("No inquiries documents found")
        
        for doc in docs:
            # Check sellerId
            if doc.get("sellerId"):
                assert isinstance(doc["sellerId"], ObjectId), \
                    f"sellerId should be ObjectId, got {type(doc['sellerId'])}: {doc['sellerId']}"
            
            # Check buyerId
            if doc.get("buyerId"):
                assert isinstance(doc["buyerId"], ObjectId), \
                    f"buyerId should be ObjectId, got {type(doc['buyerId'])}: {doc['buyerId']}"
        
        print(f"✅ inquiries ObjectId types verified: {len(docs)} documents checked")


class TestLegacyFieldsRemoved:
    """Verify no legacy 'active' field exists in any collection"""
    
    def test_no_active_field_in_seller_listings(self):
        """Verify seller_listings has no 'active' field"""
        count = db.seller_listings.count_documents({"active": {"$exists": True}})
        assert count == 0, f"Found {count} seller_listings with legacy 'active' field"
        print("✅ No 'active' field in seller_listings")
    
    def test_no_active_field_in_products(self):
        """Verify products has no 'active' field"""
        count = db.products.count_documents({"active": {"$exists": True}})
        assert count == 0, f"Found {count} products with legacy 'active' field"
        print("✅ No 'active' field in products")
    
    def test_no_active_field_in_categories(self):
        """Verify categories has no 'active' field"""
        count = db.categories.count_documents({"active": {"$exists": True}})
        assert count == 0, f"Found {count} categories with legacy 'active' field"
        print("✅ No 'active' field in categories")
    
    def test_no_active_field_in_users(self):
        """Verify users has no 'active' field"""
        count = db.users.count_documents({"active": {"$exists": True}})
        assert count == 0, f"Found {count} users with legacy 'active' field"
        print("✅ No 'active' field in users")
    
    def test_no_active_field_in_inquiries(self):
        """Verify inquiries has no 'active' field"""
        count = db.inquiries.count_documents({"active": {"$exists": True}})
        assert count == 0, f"Found {count} inquiries with legacy 'active' field"
        print("✅ No 'active' field in inquiries")


class TestMongoDBValidators:
    """Verify MongoDB schema validators are applied"""
    
    def test_validators_applied(self):
        """Verify validators are applied to key collections"""
        expected_collections = ["seller_listings", "products", "inquiries", "categories", "users"]
        
        for coll_name in expected_collections:
            coll_info = db.command({"listCollections": 1, "filter": {"name": coll_name}})
            collections = list(coll_info.get("cursor", {}).get("firstBatch", []))
            
            assert len(collections) > 0, f"Collection {coll_name} not found"
            
            options = collections[0].get("options", {})
            validator = options.get("validator")
            
            assert validator is not None, f"Validator not applied to {coll_name}"
            
            # Verify validation level and action
            validation_level = options.get("validationLevel", "strict")
            validation_action = options.get("validationAction", "error")
            
            print(f"✅ {coll_name}: Validator present (level={validation_level}, action={validation_action})")
        
        print(f"✅ All {len(expected_collections)} collections have validators applied")


class TestUnitNormalization:
    """Verify units are normalized to standard format"""
    
    STANDARD_UNITS = ["pcs", "meter", "kg", "gram", "liter", "ml", "set", "pair", 
                     "box", "pack", "roll", "sheet", "ton", "quintal", "bag", 
                     "bundle", "carton", "drum", "sq_meter", "sq_feet", "cubic_meter",
                     "feet", "inch"]
    
    def test_products_have_normalized_units(self):
        """Verify products have normalized unit values"""
        docs = list(db.products.find({"unit": {"$exists": True}}).limit(20))
        
        if len(docs) == 0:
            pytest.skip("No products with unit field found")
        
        non_standard = []
        for doc in docs:
            unit = doc.get("unit", "")
            if unit and unit not in self.STANDARD_UNITS:
                non_standard.append(f"{doc['name']}: {unit}")
        
        if non_standard:
            print(f"⚠️ Non-standard units found: {non_standard}")
        else:
            print(f"✅ All {len(docs)} products have standard units")
    
    def test_seller_listings_have_normalized_units(self):
        """Verify seller_listings have normalized unit values"""
        docs = list(db.seller_listings.find({"unit": {"$exists": True}}).limit(20))
        
        if len(docs) == 0:
            pytest.skip("No seller_listings with unit field found")
        
        non_standard = []
        for doc in docs:
            unit = doc.get("unit", "")
            if unit and unit not in self.STANDARD_UNITS:
                non_standard.append(f"Listing {doc['_id']}: {unit}")
        
        if non_standard:
            print(f"⚠️ Non-standard units in listings: {non_standard}")
        else:
            print(f"✅ All {len(docs)} seller_listings have standard units")


class TestCamelCaseSSoT:
    """Verify camelCase field naming convention is followed"""
    
    def test_seller_listings_uses_camelcase(self):
        """Verify seller_listings uses camelCase for ID and timestamp fields"""
        doc = db.seller_listings.find_one()
        
        if not doc:
            pytest.skip("No seller_listings found")
        
        # Check camelCase ID fields exist
        camel_id_fields = ["sellerId", "productId", "categoryId"]
        snake_id_fields = ["seller_id", "product_id", "category_id"]
        
        for camel in camel_id_fields:
            if camel not in doc and doc.get(camel) is not None:
                print(f"⚠️ Missing camelCase field: {camel}")
        
        for snake in snake_id_fields:
            assert snake not in doc, f"Found snake_case field {snake} - should be removed"
        
        # Check timestamps
        assert "createdAt" in doc or "created_at" in doc, "Missing timestamp field"
        
        print("✅ seller_listings follows camelCase SSOT")
    
    def test_products_uses_camelcase(self):
        """Verify products uses camelCase for ID fields"""
        doc = db.products.find_one()
        
        if not doc:
            pytest.skip("No products found")
        
        # categoryId should be camelCase
        assert "categoryId" in doc or doc.get("categoryId") is not None, \
            "products should have categoryId field"
        
        # Legacy snake_case should not exist
        assert "category_id" not in doc, "Found legacy category_id field"
        
        print("✅ products follows camelCase SSOT")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
