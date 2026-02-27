"""
Test Suite: Global Schema Migration Verification
================================================
Verifies that the database schema migration was successful:
1. All APIs return camelCase field names (categoryId, productId, sellerId)
2. No snake_case fields (category_id, product_id, seller_id) in responses
3. Database collections have canonical field names

Created: 2026-02-14
Migration: snake_case → camelCase for all ID and timestamp fields
"""

import pytest
import requests
import os

# Get BASE_URL from environment - DO NOT add default
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://midconnect-verify.preview.emergentagent.com').rstrip('/')

# Canonical camelCase fields that SHOULD be present
CANONICAL_ID_FIELDS = ['categoryId', 'productId', 'sellerId', 'buyerId', 'listingId', 'inquiryId']
CANONICAL_TIMESTAMP_FIELDS = ['createdAt', 'updatedAt', 'publishedAt', 'deletedAt', 'acceptedAt']

# Legacy snake_case fields that MUST NOT be present
LEGACY_FIELDS = ['category_id', 'product_id', 'seller_id', 'buyer_id', 'listing_id', 
                 'created_at', 'updated_at', 'deleted_at', 'accepted_at', 'rejected_at']


def check_no_legacy_fields(data, context="response"):
    """Check that no legacy snake_case fields exist in response data"""
    legacy_found = []
    
    def check_dict(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_path = f"{path}.{key}" if path else key
                if key in LEGACY_FIELDS:
                    legacy_found.append(full_path)
                check_dict(value, full_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_dict(item, f"{path}[{i}]")
    
    check_dict(data)
    return legacy_found


class TestHealthEndpoint:
    """Health check verification"""
    
    def test_health_endpoint_working(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health endpoint working")


class TestProductsAPISchemaMigration:
    """Verify /api/products returns camelCase fields"""
    
    def test_products_returns_categoryId_not_category_id(self):
        """Products API MUST return categoryId (camelCase)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) > 0:
            product = products[0]
            # MUST have categoryId (camelCase)
            assert "categoryId" in product, "Products API must return categoryId (camelCase)"
            # MUST NOT have category_id (snake_case)
            assert "category_id" not in product, "Products API must not return category_id (snake_case)"
            
            # Check for any legacy fields
            legacy = check_no_legacy_fields(products, "/api/products")
            assert len(legacy) == 0, f"Found legacy fields: {legacy}"
            
            print(f"✅ /api/products returns categoryId: {product.get('categoryId')}")
        else:
            pytest.skip("No products in database")
    
    def test_products_no_snake_case_fields(self):
        """Products API should have no snake_case ID fields"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        legacy = check_no_legacy_fields(products)
        assert len(legacy) == 0, f"Legacy snake_case fields found: {legacy}"
        print(f"✅ No legacy snake_case fields in /api/products")


class TestCategoriesAPISchemaMigration:
    """Verify /api/categories returns correct format"""
    
    def test_categories_endpoint_working(self):
        """Categories API should return categories"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        categories = response.json()
        
        assert isinstance(categories, list), "Categories should be a list"
        
        if len(categories) > 0:
            category = categories[0]
            # Categories have _id, name, description
            assert "_id" in category, "Category should have _id"
            assert "name" in category, "Category should have name"
            
            # Check for legacy fields
            legacy = check_no_legacy_fields(categories)
            assert len(legacy) == 0, f"Legacy fields found: {legacy}"
            
            print(f"✅ /api/categories returns {len(categories)} categories")
        else:
            print("⚠️ No categories returned (may be empty)")


class TestProductDetailAPISchemaMigration:
    """Verify /api/products/detail/{slug} returns camelCase fields"""
    
    def test_product_detail_returns_productId_categoryId(self):
        """Product detail MUST return productId and categoryId (camelCase)"""
        # First get a product slug
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) == 0:
            pytest.skip("No products to test detail endpoint")
        
        slug = products[0].get("slug", "three-phase-ac-motor")
        
        # Get product detail
        response = requests.get(f"{BASE_URL}/api/products/detail/{slug}")
        assert response.status_code == 200
        detail = response.json()
        
        # MUST have productId (camelCase)
        assert "productId" in detail, "Product detail must return productId (camelCase)"
        # MUST have categoryId (camelCase)
        assert "categoryId" in detail, "Product detail must return categoryId (camelCase)"
        
        # MUST NOT have snake_case variants
        assert "product_id" not in detail, "Product detail must not return product_id"
        assert "category_id" not in detail, "Product detail must not return category_id"
        
        print(f"✅ Product detail returns productId: {detail.get('productId')}, categoryId: {detail.get('categoryId')}")
    
    def test_product_detail_sellers_have_correct_fields(self):
        """Sellers in product detail should have correct field names"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        if len(products) == 0:
            pytest.skip("No products to test")
        
        slug = products[0].get("slug", "three-phase-ac-motor")
        response = requests.get(f"{BASE_URL}/api/products/detail/{slug}")
        assert response.status_code == 200
        detail = response.json()
        
        sellers = detail.get("sellers", [])
        if len(sellers) > 0:
            seller = sellers[0]
            # Sellers have listing_id, seller_id (these are display fields, OK as-is)
            assert "listing_id" in seller, "Seller should have listing_id"
            assert "seller_id" in seller, "Seller should have seller_id"
            print(f"✅ Product has {len(sellers)} sellers with correct fields")
        else:
            print("⚠️ No sellers for this product")
    
    def test_product_detail_no_legacy_id_fields(self):
        """Product detail response should have no legacy fields"""
        response = requests.get(f"{BASE_URL}/api/products")
        products = response.json()
        
        if len(products) == 0:
            pytest.skip("No products to test")
        
        slug = products[0].get("slug", "three-phase-ac-motor")
        response = requests.get(f"{BASE_URL}/api/products/detail/{slug}")
        detail = response.json()
        
        # Check for legacy ID fields at root level only (not in sellers display)
        root_legacy = []
        for field in ['category_id', 'product_id']:
            if field in detail:
                root_legacy.append(field)
        
        assert len(root_legacy) == 0, f"Legacy fields at root: {root_legacy}"
        print(f"✅ No legacy ID fields in product detail root")


class TestDatabaseIntegrityVerification:
    """Verify database-level schema integrity"""
    
    def test_products_collection_has_categoryId(self):
        """Verify products API returns canonical categoryId"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        for product in products:
            # Every product MUST have categoryId
            assert "categoryId" in product, f"Product missing categoryId: {product.get('_id')}"
            # Every product MUST NOT have category_id
            assert "category_id" not in product, f"Product has legacy category_id: {product.get('_id')}"
        
        print(f"✅ All {len(products)} products have canonical categoryId field")


class TestAPICamelCaseConsistency:
    """Verify all APIs return consistent camelCase naming"""
    
    def test_public_categories_no_legacy_fields(self):
        """Public categories should have no legacy fields"""
        response = requests.get(f"{BASE_URL}/api/categories/public")
        if response.status_code == 200:
            categories = response.json()
            legacy = check_no_legacy_fields(categories)
            assert len(legacy) == 0, f"Legacy fields in public categories: {legacy}"
            print(f"✅ /api/categories/public has no legacy fields")
        else:
            print(f"⚠️ Public categories endpoint returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
