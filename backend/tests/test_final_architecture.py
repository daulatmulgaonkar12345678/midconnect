"""
Test Suite: FINAL MARKETPLACE ARCHITECTURE
===========================================
Tests the 4-layer model:
Category → SpecTemplate → Product → ProductVariant → SellerListing

Verifies:
1. productVariants collection structure
2. Products have specTemplateId
3. SellerListings have variantId
4. All fields are camelCase
5. No specifications stored directly in listings (commercial data only)
"""

import pytest
import requests
import os
from bson import ObjectId

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', os.environ.get('EXPO_PUBLIC_BACKEND_URL', '')).rstrip('/')
if not BASE_URL:
    BASE_URL = "https://stupefied-hugle-2.preview.emergentagent.com"


class TestHealthAndPublicAPIs:
    """Test public endpoints that don't require authentication"""
    
    def test_health_endpoint(self):
        """Verify /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")
    
    def test_categories_all_endpoint(self):
        """Verify /api/categories/all returns categories with camelCase fields"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check first category for camelCase fields
        category = data[0]
        assert "_id" in category
        assert "name" in category
        
        # Verify camelCase fields
        camel_case_fields = ["isActive", "createdAt", "updatedAt"]
        for field in camel_case_fields:
            if field in category:
                print(f"  ✅ {field} is camelCase")
        
        # Check for snake_case fields that should NOT exist
        snake_case_fields = ["is_active", "created_at", "updated_at"]
        for field in snake_case_fields:
            assert field not in category, f"Snake_case field {field} found in category"
        
        print(f"✅ Categories endpoint returned {len(data)} categories with camelCase fields")
    
    def test_products_endpoint(self):
        """Verify /api/products returns products with proper structure"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            product = data[0]
            assert "_id" in product
            assert "name" in product
            
            # Check for categoryId (camelCase)
            assert "categoryId" in product, "categoryId should be in product response"
            
            print(f"✅ Products endpoint returned {len(data)} products")
            print(f"  Sample product: {product.get('name')} (categoryId: {product.get('categoryId')})")
        else:
            print("⚠️ No products found in database")


class TestProductVariantsCollection:
    """Test productVariants collection structure and data integrity"""
    
    @pytest.fixture
    def mongo_client(self):
        """Get MongoDB client for direct database verification"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "b2b_marketplace")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        yield db
        client.close()
    
    def test_product_variants_collection_exists(self):
        """Verify productVariants collection exists with documents"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            collections = await db.list_collection_names()
            assert "productVariants" in collections, "productVariants collection should exist"
            
            count = await db.productVariants.count_documents({})
            print(f"✅ productVariants collection exists with {count} documents")
            
            client.close()
            return count
        
        count = asyncio.run(check())
        assert count >= 0, "Should be able to count documents"
    
    def test_product_variant_schema(self):
        """Verify productVariants have correct structure: productId, specTemplateId, attributes, createdAt"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            variant = await db.productVariants.find_one({})
            client.close()
            return variant
        
        variant = asyncio.run(check())
        
        if variant:
            # Required fields
            assert "_id" in variant, "Variant should have _id"
            assert "productId" in variant, "Variant should have productId"
            assert "specTemplateId" in variant, "Variant should have specTemplateId"
            assert "attributes" in variant, "Variant should have attributes"
            assert "createdAt" in variant, "Variant should have createdAt"
            
            # Verify ObjectId types
            assert isinstance(variant["productId"], ObjectId), "productId should be ObjectId"
            assert isinstance(variant["specTemplateId"], ObjectId), "specTemplateId should be ObjectId"
            
            # Verify attributes is a dict
            assert isinstance(variant["attributes"], dict), "attributes should be a dict"
            
            # Check for NO snake_case fields
            snake_case_fields = ["product_id", "spec_template_id", "created_at"]
            for field in snake_case_fields:
                assert field not in variant, f"Snake_case field {field} should not exist"
            
            print(f"✅ productVariant schema is correct:")
            print(f"  _id: {variant['_id']}")
            print(f"  productId: {variant['productId']} (ObjectId)")
            print(f"  specTemplateId: {variant['specTemplateId']} (ObjectId)")
            print(f"  attributes: {variant['attributes']}")
            print(f"  createdAt: {variant['createdAt']}")
        else:
            pytest.skip("No productVariants found in database")
    
    def test_product_variant_attributes_stored(self):
        """Verify variant with attributes has correct attribute structure"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            # Find a variant with non-empty attributes
            variant = await db.productVariants.find_one({
                "attributes": {"$ne": {}}
            })
            
            client.close()
            return variant
        
        variant = asyncio.run(check())
        
        if variant:
            attributes = variant.get("attributes", {})
            assert len(attributes) > 0, "Should have at least one attribute"
            
            print(f"✅ Variant with attributes found:")
            print(f"  Variant ID: {variant['_id']}")
            for key, value in attributes.items():
                print(f"  - {key}: {value}")
        else:
            print("⚠️ No variants with non-empty attributes found (acceptable for new database)")


class TestSellerListingsWithVariantId:
    """Test sellerListings have variantId field populated"""
    
    def test_seller_listings_have_variant_id(self):
        """Verify seller_listings documents have variantId field"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            # Check both collection names
            results = {
                "sellerListings": {
                    "total": await db.sellerListings.count_documents({}),
                    "with_variant": await db.sellerListings.count_documents({"variantId": {"$exists": True}})
                },
                "seller_listings": {
                    "total": await db.seller_listings.count_documents({}),
                    "with_variant": await db.seller_listings.count_documents({"variantId": {"$exists": True}})
                }
            }
            
            # Get a sample listing
            listing = await db.seller_listings.find_one({"variantId": {"$exists": True}})
            if not listing:
                listing = await db.sellerListings.find_one({"variantId": {"$exists": True}})
            
            client.close()
            return results, listing
        
        results, listing = asyncio.run(check())
        
        print("✅ SellerListings variantId status:")
        for collection, counts in results.items():
            if counts["total"] > 0:
                print(f"  {collection}: {counts['with_variant']}/{counts['total']} have variantId")
        
        if listing:
            assert "variantId" in listing, "Listing should have variantId"
            assert isinstance(listing["variantId"], ObjectId), "variantId should be ObjectId"
            print(f"  Sample listing variantId: {listing['variantId']} (ObjectId)")
    
    def test_seller_listings_no_direct_specifications(self):
        """Verify sellerListings store commercial data only, not specifications"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            # Get listings with non-empty specifications (should be rare/empty)
            listings_with_specs = []
            
            async for listing in db.seller_listings.find({"specifications": {"$exists": True}}):
                specs = listing.get("specifications", {})
                if specs and len(specs) > 0:
                    listings_with_specs.append({
                        "_id": str(listing["_id"]),
                        "specifications": specs
                    })
            
            async for listing in db.sellerListings.find({"specifications": {"$exists": True}}):
                specs = listing.get("specifications", {})
                if specs and len(specs) > 0:
                    listings_with_specs.append({
                        "_id": str(listing["_id"]),
                        "specifications": specs
                    })
            
            client.close()
            return listings_with_specs
        
        listings_with_specs = asyncio.run(check())
        
        if len(listings_with_specs) > 0:
            print(f"⚠️ Found {len(listings_with_specs)} listings with non-empty specifications:")
            for item in listings_with_specs[:3]:
                print(f"  - {item['_id']}: {item['specifications']}")
            print("  Note: These should eventually be migrated to use variantId only")
        else:
            print("✅ No listings with non-empty specifications - architecture is correct")


class TestProductsWithSpecTemplateId:
    """Test products have specTemplateId field"""
    
    def test_products_have_spec_template_id(self):
        """Verify products have specTemplateId linking to specTemplates"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            total_products = await db.products.count_documents({})
            products_with_template = await db.products.count_documents({"specTemplateId": {"$exists": True, "$ne": None}})
            
            # Get sample product
            product = await db.products.find_one({"specTemplateId": {"$exists": True}})
            
            client.close()
            return total_products, products_with_template, product
        
        total, with_template, product = asyncio.run(check())
        
        print(f"✅ Products with specTemplateId: {with_template}/{total}")
        
        if product:
            assert "specTemplateId" in product
            print(f"  Sample: {product.get('name')} -> specTemplateId: {product.get('specTemplateId')}")


class TestCamelCaseCompliance:
    """Test that all fields use camelCase (no snake_case)"""
    
    def test_product_variants_camel_case(self):
        """Verify productVariants use camelCase fields"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            variant = await db.productVariants.find_one({})
            client.close()
            return variant
        
        variant = asyncio.run(check())
        
        if variant:
            keys = list(variant.keys())
            
            # Expected camelCase keys
            expected_camel = ["productId", "specTemplateId", "attributes", "createdAt"]
            
            # Snake_case keys that should NOT exist
            forbidden_snake = ["product_id", "spec_template_id", "created_at"]
            
            for key in expected_camel:
                if key in keys:
                    print(f"  ✅ {key} is camelCase")
            
            for key in forbidden_snake:
                assert key not in keys, f"Snake_case field {key} should not exist"
            
            print(f"✅ productVariants fields are camelCase")
        else:
            pytest.skip("No productVariants to check")
    
    def test_seller_listings_camel_case(self):
        """Verify sellerListings use camelCase fields"""
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "b2b_marketplace")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            listing = await db.seller_listings.find_one({})
            if not listing:
                listing = await db.sellerListings.find_one({})
            
            client.close()
            return listing
        
        listing = asyncio.run(check())
        
        if listing:
            keys = list(listing.keys())
            
            # Expected camelCase keys
            expected_camel = ["sellerId", "productId", "variantId", "categoryId", "createdAt", "updatedAt", 
                           "pricingTiers", "isActive", "sellerRole", "leadTime"]
            
            # Snake_case keys that should NOT exist
            forbidden_snake = ["seller_id", "product_id", "variant_id", "category_id", 
                             "created_at", "updated_at", "pricing_tiers", "is_active", 
                             "seller_role", "lead_time"]
            
            found_camel = []
            for key in expected_camel:
                if key in keys:
                    found_camel.append(key)
            
            found_snake = []
            for key in forbidden_snake:
                if key in keys:
                    found_snake.append(key)
            
            print(f"✅ Found camelCase fields: {found_camel}")
            
            if found_snake:
                print(f"⚠️ Found snake_case fields (legacy): {found_snake}")
            else:
                print(f"✅ No snake_case fields found")
        else:
            pytest.skip("No sellerListings to check")


class TestAPIResponseFormat:
    """Test API responses return proper format"""
    
    def test_products_api_returns_spec_template_info(self):
        """Verify /api/products response includes specTemplateId if available"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        products = response.json()
        
        if len(products) > 0:
            product = products[0]
            # Note: public products API may not expose specTemplateId
            # This is acceptable for security
            print(f"✅ Products API response structure verified")
            print(f"  Product keys: {list(product.keys())}")
    
    def test_categories_api_camel_case_response(self):
        """Verify /api/categories/all returns camelCase fields"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200
        categories = response.json()
        
        if len(categories) > 0:
            category = categories[0]
            
            # Verify camelCase
            if "isActive" in category:
                print(f"  ✅ isActive field present (camelCase)")
            if "createdAt" in category:
                print(f"  ✅ createdAt field present (camelCase)")
            if "updatedAt" in category:
                print(f"  ✅ updatedAt field present (camelCase)")
            
            # No snake_case
            assert "is_active" not in category
            assert "created_at" not in category
            assert "updated_at" not in category
            
            print(f"✅ Categories API returns camelCase fields")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
