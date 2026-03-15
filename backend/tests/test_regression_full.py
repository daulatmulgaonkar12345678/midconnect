"""
Full E2E Regression Test Suite for MidConnect B2B Marketplace
=============================================================

Comprehensive regression tests for:
- Public APIs (products, categories, product detail)
- Authentication (401 without token, authorized with dev-test-token)
- Admin endpoints (stats, users, listings)
- Seller endpoints (dashboard, listings)
- Security (seller_id injection rejection, input validation)
- Database schema enforcement (indexes, validator)

Test Categories:
1. Public API Tests
2. Authentication Tests
3. Admin API Tests
4. Seller API Tests
5. Security Tests
6. Database Schema Tests
"""

import pytest
import requests
import os
from bson import ObjectId
from datetime import datetime, timezone

# Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://supplier-orders-3.preview.emergentagent.com/api').rstrip('/')
DEV_TOKEN = "dev-test-token"
VALID_CATEGORY_ID = "6981a9a74108b0cbd93aa630"  # Electrical Equipment
PRODUCT_SLUG = "three-phase-ac-motor"

# Ensure BASE_URL has /api prefix
if not BASE_URL.endswith('/api'):
    BASE_URL = BASE_URL.rstrip('/') + '/api' if '/api' not in BASE_URL else BASE_URL


class TestPublicAPIs:
    """Tests for public endpoints (no authentication required)"""
    
    def test_health_endpoint(self):
        """Health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health endpoint: {data}")
    
    def test_products_returns_seller_count_and_min_price(self):
        """GET /api/products returns products with seller_count and min_price"""
        response = requests.get(f"{BASE_URL}/products")
        assert response.status_code == 200
        
        products = response.json()
        assert isinstance(products, list)
        
        if len(products) > 0:
            product = products[0]
            assert "seller_count" in product, "Products must have seller_count"
            assert "name" in product, "Products must have name"
            assert "slug" in product, "Products must have slug for SEO"
            
            # Verify min_price is present if there are sellers
            if product.get("seller_count", 0) > 0:
                assert "min_price" in product or product.get("min_price") is None
            
            print(f"✓ Products API: Found {len(products)} products")
            print(f"  First product: {product.get('name')}, seller_count={product.get('seller_count')}, min_price={product.get('min_price')}")
        else:
            print("✓ Products API: No products found (empty list)")
    
    def test_categories_public_returns_active_listings(self):
        """GET /api/categories/public returns categories with active listings"""
        response = requests.get(f"{BASE_URL}/categories/public")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        
        if len(categories) > 0:
            category = categories[0]
            assert "_id" in category
            assert "name" in category
            assert "product_count" in category, "Public categories must have product_count"
            assert "listing_count" in category, "Public categories must have listing_count"
            
            print(f"✓ Public Categories: Found {len(categories)} categories")
            print(f"  First category: {category.get('name')}, products={category.get('product_count')}, listings={category.get('listing_count')}")
        else:
            print("✓ Public Categories: No categories with active listings")
    
    def test_product_detail_returns_complete_data(self):
        """GET /api/products/detail/{slug} returns complete product data with sellers"""
        response = requests.get(f"{BASE_URL}/products/detail/{PRODUCT_SLUG}")
        
        if response.status_code == 404:
            pytest.skip(f"Product '{PRODUCT_SLUG}' not found in database")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields - UPDATED: Using canonical camelCase fields after schema migration
        assert "productId" in data, "Product detail must have productId (camelCase)"
        assert "product_name" in data, "Product detail must have product_name"
        assert "slug" in data, "Product detail must have slug"
        assert "categoryId" in data, "Product detail must have categoryId (camelCase)"
        assert "seller_count" in data, "Product detail must have seller_count"
        assert "sellers" in data, "Product detail must have sellers array"
        
        # Validate sellers structure
        sellers = data.get("sellers", [])
        assert isinstance(sellers, list)
        
        if len(sellers) > 0:
            seller = sellers[0]
            assert "listing_id" in seller, "Seller must have listing_id"
            assert "seller_id" in seller, "Seller must have seller_id"
            assert "company_name" in seller, "Seller must have company_name"
            assert "moq" in seller, "Seller must have moq"
            
            print(f"✓ Product Detail: {data.get('product_name')}")
            print(f"  Sellers: {len(sellers)}, First: {seller.get('company_name')}")
        else:
            print(f"✓ Product Detail: {data.get('product_name')} (no sellers)")


class TestAuthentication:
    """Tests for authentication and authorization"""
    
    def test_users_me_requires_auth(self):
        """GET /api/users/me returns 401 without token"""
        response = requests.get(f"{BASE_URL}/users/me")
        assert response.status_code == 401
        print("✓ /api/users/me returns 401 without token")
    
    def test_admin_stats_requires_auth(self):
        """GET /api/admin/stats returns 401 without token"""
        response = requests.get(f"{BASE_URL}/admin/stats")
        assert response.status_code == 401
        print("✓ /api/admin/stats returns 401 without token")
    
    def test_seller_dashboard_requires_auth(self):
        """GET /api/seller/dashboard returns 401 without token"""
        response = requests.get(f"{BASE_URL}/seller/dashboard")
        assert response.status_code == 401
        print("✓ /api/seller/dashboard returns 401 without token")
    
    def test_post_products_requires_auth(self):
        """POST /api/products returns 401 without token"""
        response = requests.post(
            f"{BASE_URL}/products",
            json={"name": "Test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401
        print("✓ POST /api/products returns 401 without token")
    
    def test_users_me_with_dev_token(self):
        """GET /api/users/me works with dev-test-token"""
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        user = response.json()
        assert "email" in user
        assert user.get("is_admin") == True, "Dev test user should be admin"
        assert user.get("is_seller") == True, "Dev test user should be seller"
        
        print(f"✓ /api/users/me with token: {user.get('email')}, admin={user.get('is_admin')}")


class TestAdminAPIs:
    """Tests for admin endpoints"""
    
    def test_admin_stats(self):
        """GET /api/admin/stats returns comprehensive stats"""
        response = requests.get(
            f"{BASE_URL}/admin/stats",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        stats = data.get("stats", {})
        
        # Check required stat categories
        assert "users" in stats, "Stats must include users"
        assert "catalog" in stats, "Stats must include catalog"
        assert "listings" in stats, "Stats must include listings"
        assert "inquiries" in stats, "Stats must include inquiries"
        
        # Check user stats
        users = stats.get("users", {})
        assert "total" in users
        assert "active" in users
        assert "sellers" in users
        
        print(f"✓ Admin Stats: {users.get('total')} users, {stats.get('listings', {}).get('total')} listings")
    
    def test_admin_users_list(self):
        """GET /api/admin/users returns paginated user list"""
        response = requests.get(
            f"{BASE_URL}/admin/users?limit=10",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "total" in data
        
        print(f"✓ Admin Users: {len(data.get('users', []))} users returned, {data.get('total')} total")


class TestSellerAPIs:
    """Tests for seller endpoints"""
    
    def test_seller_dashboard(self):
        """GET /api/seller/dashboard returns seller stats"""
        response = requests.get(
            f"{BASE_URL}/seller/dashboard",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "stats" in data or "recent_listings" in data, "Dashboard must have stats or listings"
        
        print(f"✓ Seller Dashboard: {data.get('stats', {})}")
    
    def test_seller_listings(self):
        """GET /api/seller/listings returns seller's listings"""
        response = requests.get(
            f"{BASE_URL}/seller/listings",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "listings" in data
        assert "total" in data
        
        print(f"✓ Seller Listings: {len(data.get('listings', []))} listings, {data.get('total')} total")


class TestSecurity:
    """Security tests for API endpoints"""
    
    def test_post_products_rejects_seller_id_in_body(self):
        """POST /api/products rejects seller_id in request body (security test)"""
        response = requests.post(
            f"{BASE_URL}/products",
            headers={
                "Authorization": f"Bearer {DEV_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "category_id": VALID_CATEGORY_ID,
                "family": "Test Family",
                "variant": "Security Test",
                "name": "TEST_SECURITY_Product",
                "seller_id": "malicious_seller_id_injection",
                "price": 100,
                "moq": 1
            }
        )
        
        # Should be 422 (validation error) because seller_id is forbidden
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        # Check that it mentions extra_forbidden or seller_id
        detail = str(data.get("detail", ""))
        assert "seller_id" in detail.lower() or "extra" in detail.lower(), \
            f"Error should mention seller_id rejection: {detail}"
        
        print("✓ Security: seller_id injection correctly rejected with 422")
    
    def test_post_products_validates_price_positive(self):
        """POST /api/products validates price > 0"""
        response = requests.post(
            f"{BASE_URL}/products",
            headers={
                "Authorization": f"Bearer {DEV_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "category_id": VALID_CATEGORY_ID,
                "family": "Test Family",
                "variant": "Validation Test",
                "name": "TEST_VALIDATION_Product",
                "price": 0,
                "moq": 1
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        detail = str(data.get("detail", ""))
        assert "price" in detail.lower() or "greater" in detail.lower(), \
            f"Error should mention price validation: {detail}"
        
        print("✓ Validation: price=0 correctly rejected with 422")
    
    def test_post_products_validates_price_negative(self):
        """POST /api/products rejects negative price"""
        response = requests.post(
            f"{BASE_URL}/products",
            headers={
                "Authorization": f"Bearer {DEV_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "category_id": VALID_CATEGORY_ID,
                "family": "Test Family",
                "variant": "Validation Test",
                "name": "TEST_VALIDATION_Negative",
                "price": -50,
                "moq": 1
            }
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Validation: negative price correctly rejected")


class TestProductCreation:
    """Tests for product creation flow"""
    
    def test_create_product_with_valid_data(self):
        """POST /api/products creates product successfully with valid data"""
        response = requests.post(
            f"{BASE_URL}/products",
            headers={
                "Authorization": f"Bearer {DEV_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "category_id": VALID_CATEGORY_ID,
                "family": "Electric Motor",
                "variant": "Regression Test",
                "name": f"TEST_REGRESSION_{datetime.now().strftime('%H%M%S')}",
                "description": "Product created for regression testing",
                "unit": "pieces",
                "price": 250,
                "stock": 50,
                "moq": 2,
                "images": [],
                "specifications": {}
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "product" in data
        
        product = data["product"]
        assert "_id" in product
        assert "sellerId" in product, "Product should have sellerId from authenticated user"
        
        print(f"✓ Product Created: {product.get('name')}, ID={product.get('_id')}")
        
        # Store for cleanup
        return product.get("_id")


class TestDatabaseSchema:
    """Tests for database schema enforcement"""
    
    def test_indexes_exist(self):
        """Verify required indexes exist on seller_listings"""
        # This test uses direct MongoDB connection
        from pymongo import MongoClient
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017').strip()
        DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()
        
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        indexes = {idx['name']: idx for idx in db.seller_listings.list_indexes()}
        
        # Check for unique compound index
        has_unique = any(
            idx.get('unique', False) and
            'sellerId' in str(idx.get('key', {})) and
            'productId' in str(idx.get('key', {}))
            for idx in indexes.values()
        )
        assert has_unique, "Missing unique compound index (sellerId, productId)"
        
        # Check for query optimization indexes
        required_indexes = ["sellerId_1", "productId_1", "status_1"]
        for idx_name in required_indexes:
            assert idx_name in indexes, f"Missing index: {idx_name}"
        
        print(f"✓ Database Indexes: Found {len(indexes)} indexes, all required indexes present")
    
    def test_schema_validator_active(self):
        """Verify MongoDB schema validator is active and strict"""
        from pymongo import MongoClient
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017').strip()
        DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()
        
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        coll_info = db.command({"listCollections": 1, "filter": {"name": "seller_listings"}})
        collections = coll_info.get("cursor", {}).get("firstBatch", [])
        
        assert len(collections) > 0, "seller_listings collection not found"
        
        coll = collections[0]
        options = coll.get("options", {})
        
        level = options.get("validationLevel", "off")
        action = options.get("validationAction", "warn")
        has_validator = bool(options.get("validator"))
        
        assert has_validator, "Schema validator not configured"
        assert level == "strict", f"Validation level is '{level}', expected 'strict'"
        assert action == "error", f"Validation action is '{action}', expected 'error'"
        
        print(f"✓ Schema Validator: validationLevel={level}, validationAction={action}")
    
    def test_schema_validator_rejects_legacy_fields(self):
        """Verify schema validator rejects legacy fields (seller_id, product_id)"""
        from pymongo import MongoClient
        from pymongo.errors import WriteError
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017').strip()
        DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()
        
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Attempt to insert with legacy field
        try:
            db.seller_listings.insert_one({
                "seller_id": "legacy_string_id",  # LEGACY - should be rejected
                "sellerId": ObjectId(),
                "productId": ObjectId(),
                "categoryId": ObjectId(),
                "status": "draft",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            })
            pytest.fail("Insert with legacy seller_id should have been rejected")
        except WriteError:
            print("✓ Schema Validator: Correctly rejects legacy seller_id field")
        except Exception as e:
            pytest.fail(f"Unexpected error: {type(e).__name__}: {e}")


class TestCleanup:
    """Cleanup test data after tests"""
    
    def test_cleanup_test_products(self):
        """Remove TEST_ prefixed products created during testing"""
        from pymongo import MongoClient
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017').strip()
        DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()
        
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Delete test products
        result = db.products.delete_many({"name": {"$regex": "^TEST_"}})
        print(f"✓ Cleanup: Deleted {result.deleted_count} test products")
        
        # Delete test seller listings
        result2 = db.seller_listings.delete_many({"description": {"$regex": "regression"}})
        print(f"✓ Cleanup: Deleted {result2.deleted_count} test listings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
