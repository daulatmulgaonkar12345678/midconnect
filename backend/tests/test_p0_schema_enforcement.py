"""
P0 Production-Grade Architecture Tests - Schema Enforcement

Tests the MongoDB JSON Schema Validator enforcement at the database level:
1. MongoDB schema validator rejects legacy field writes (seller_id instead of sellerId)
2. MongoDB schema validator rejects string IDs (must be ObjectId)
3. MongoDB schema validator accepts valid canonical documents
4. Deployment guard passes all checks
5. Public /api/products returns correct seller_count
6. Public /api/health returns healthy status
7. Schema integrity verification passes

These tests verify the P0 architectural redesign is complete and working.
"""

import pytest
import requests
import os
import subprocess
import json
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment from backend .env file
load_dotenv('/app/backend/.env')

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://product-variants-2.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

# MongoDB connection for direct schema validation tests
MONGO_URL = os.environ.get('MONGO_URL', '').strip().strip('"')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip().strip('"')


class TestPublicAPIs:
    """Test public API endpoints return correct data"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Status not healthy: {data}"
        assert "timestamp" in data, "Timestamp missing from health response"
        print(f"✅ Health check passed: {data}")
    
    def test_products_endpoint_returns_seller_count(self):
        """Test /api/products returns products with correct seller_count"""
        response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert response.status_code == 200, f"Products API failed: {response.text}"
        
        products = response.json()
        assert isinstance(products, list), f"Expected list, got {type(products)}"
        assert len(products) >= 1, "No products returned"
        
        # Verify product structure
        product = products[0]
        assert "_id" in product, "Product missing _id"
        assert "name" in product, "Product missing name"
        assert "seller_count" in product, "Product missing seller_count"
        
        # Verify seller_count is correct (should be 1 based on test data)
        seller_count = product.get("seller_count", 0)
        assert seller_count == 1, f"Expected seller_count=1, got {seller_count}"
        
        print(f"✅ Products API returns correct seller_count: {seller_count}")
        print(f"   Product: {product.get('name')}")


class TestSchemaValidatorEnforcement:
    """Test MongoDB schema validator rejects invalid data"""
    
    @pytest.fixture(scope="class")
    def db(self):
        """Get MongoDB database connection"""
        if not MONGO_URL:
            pytest.skip("MONGO_URL not configured")
        client = MongoClient(MONGO_URL)
        return client[DB_NAME]
    
    def test_validator_rejects_legacy_seller_id_field(self, db):
        """
        Test 1: Schema validator MUST reject documents with legacy 'seller_id' field
        
        The canonical field is 'sellerId' (camelCase) with ObjectId type.
        Any write with 'seller_id' (snake_case) should be rejected.
        """
        test_doc = {
            "seller_id": "invalid_string_id",  # LEGACY field - should be rejected
            "productId": ObjectId(),
            "categoryId": ObjectId(),
            "status": "active",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        with pytest.raises(Exception) as exc_info:
            db.seller_listings.insert_one(test_doc)
        
        # Verify it was rejected due to schema violation
        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "document failed validation" in error_msg or "writeerror" in error_msg, \
            f"Expected schema validation error, got: {exc_info.value}"
        
        print("✅ Schema validator correctly rejected legacy 'seller_id' field")
    
    def test_validator_rejects_string_seller_id(self, db):
        """
        Test 2: Schema validator MUST reject sellerId as string type
        
        The sellerId field must be ObjectId, not string.
        """
        test_doc = {
            "sellerId": "invalid_string_id",  # String instead of ObjectId - should be rejected
            "productId": ObjectId(),
            "categoryId": ObjectId(),
            "status": "active",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        with pytest.raises(Exception) as exc_info:
            db.seller_listings.insert_one(test_doc)
        
        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "document failed validation" in error_msg or "writeerror" in error_msg, \
            f"Expected schema validation error, got: {exc_info.value}"
        
        print("✅ Schema validator correctly rejected string sellerId (must be ObjectId)")
    
    def test_validator_rejects_string_product_id(self, db):
        """
        Test 3: Schema validator MUST reject productId as string type
        """
        test_doc = {
            "sellerId": ObjectId(),
            "productId": "invalid_string_id",  # String instead of ObjectId
            "categoryId": ObjectId(),
            "status": "active",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        with pytest.raises(Exception) as exc_info:
            db.seller_listings.insert_one(test_doc)
        
        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "document failed validation" in error_msg or "writeerror" in error_msg, \
            f"Expected schema validation error, got: {exc_info.value}"
        
        print("✅ Schema validator correctly rejected string productId")
    
    def test_validator_accepts_valid_canonical_document(self, db):
        """
        Test 4: Schema validator MUST accept valid canonical documents
        
        A properly formatted document with:
        - sellerId as ObjectId
        - productId as ObjectId  
        - categoryId as ObjectId
        - All required fields present
        
        Should be accepted.
        """
        test_doc_id = ObjectId()
        test_doc = {
            "_id": test_doc_id,
            "sellerId": ObjectId(),
            "productId": ObjectId(),
            "categoryId": ObjectId(),
            "status": "draft",
            "is_active": False,
            "stock": 100,
            "moq": 10,
            "currency": "INR",
            "pricingTiers": [{"minQty": 1, "maxQty": 100, "pricePerUnit": 500}],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        try:
            result = db.seller_listings.insert_one(test_doc)
            assert result.inserted_id == test_doc_id, "Insert returned wrong ID"
            
            # Clean up
            db.seller_listings.delete_one({"_id": test_doc_id})
            print(f"✅ Schema validator accepted valid canonical document (id={test_doc_id})")
        except Exception as e:
            pytest.fail(f"Valid document was rejected: {e}")


class TestDeploymentGuard:
    """Test deployment guard validation"""
    
    def test_deployment_guard_passes(self):
        """
        Test 5: Deployment guard script passes all checks
        
        The deployment guard validates:
        - No legacy fields exist
        - All ID fields are ObjectId type
        - Schema validator is active
        - Required indexes exist
        """
        result = subprocess.run(
            ["python", "/app/backend/guards/deployment_guard.py"],
            capture_output=True,
            text=True,
            cwd="/app/backend"
        )
        
        # Should exit with code 0 (success)
        assert result.returncode == 0, f"Deployment guard failed:\n{result.stdout}\n{result.stderr}"
        
        # Check for success message in output (may be in stdout or stderr due to logging)
        combined_output = result.stdout + result.stderr
        assert "ALL CRITICAL CHECKS PASSED" in combined_output, \
            f"Deployment guard did not pass all checks:\n{combined_output}"
        
        print("✅ Deployment guard passed all checks")
        print(f"   Output: {combined_output[:500]}")


class TestSchemaIntegrityVerification:
    """Test schema integrity verification script"""
    
    def test_schema_integrity_verification_passes(self):
        """
        Test 6: Schema integrity verification passes all checks
        
        Validates:
        - No legacy fields (seller_id, product_id, category_id)
        - All canonical fields are ObjectId type
        - Referential integrity is maintained
        - Required indexes exist
        """
        result = subprocess.run(
            ["python", "/app/backend/scripts/verify_schema_integrity.py"],
            capture_output=True,
            text=True,
            cwd="/app/backend"
        )
        
        # Should exit with code 0 (success)
        assert result.returncode == 0, f"Schema verification failed:\n{result.stdout}\n{result.stderr}"
        
        # Check for success message
        assert "ALL CHECKS PASSED" in result.stdout, \
            f"Schema verification did not pass:\n{result.stdout}"
        
        print("✅ Schema integrity verification passed")
    
    def test_no_legacy_fields_in_database(self):
        """
        Test 7: Verify no legacy fields exist in seller_listings collection
        """
        if not MONGO_URL:
            pytest.skip("MONGO_URL not configured")
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        legacy_fields = ['seller_id', 'product_id', 'category_id', 'product_name', 'category_name']
        
        for field in legacy_fields:
            count = db.seller_listings.count_documents({field: {"$exists": True}})
            assert count == 0, f"Legacy field '{field}' found in {count} documents!"
        
        print("✅ No legacy fields exist in database")


class TestSchemaValidatorConfiguration:
    """Test MongoDB schema validator is correctly configured"""
    
    def test_validator_is_strict_mode(self):
        """
        Test 8: Verify schema validator is in strict mode
        
        The validator must be configured with:
        - validationLevel: "strict"
        - validationAction: "error"
        """
        if not MONGO_URL:
            pytest.skip("MONGO_URL not configured")
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Get collection info
        coll_info = db.command({"listCollections": 1, "filter": {"name": "seller_listings"}})
        collections = coll_info.get("cursor", {}).get("firstBatch", [])
        
        assert len(collections) > 0, "seller_listings collection not found"
        
        coll = collections[0]
        options = coll.get("options", {})
        validator = options.get("validator")
        level = options.get("validationLevel", "off")
        action = options.get("validationAction", "warn")
        
        assert validator is not None, "Schema validator not configured"
        assert level == "strict", f"Validation level is '{level}', expected 'strict'"
        assert action == "error", f"Validation action is '{action}', expected 'error'"
        
        print(f"✅ Schema validator is configured correctly:")
        print(f"   - validationLevel: {level}")
        print(f"   - validationAction: {action}")
        print(f"   - validator: {bool(validator)}")


class TestDataIntegrity:
    """Test data integrity in the database"""
    
    def test_all_listings_have_objectid_fields(self):
        """
        Test 9: Verify all seller_listings documents have ObjectId types for ID fields
        """
        if not MONGO_URL:
            pytest.skip("MONGO_URL not configured")
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Check all documents
        docs = list(db.seller_listings.find({}))
        assert len(docs) >= 1, "No documents in seller_listings"
        
        for doc in docs:
            doc_id = doc.get("_id")
            
            # Check sellerId
            seller_id = doc.get("sellerId")
            assert seller_id is not None, f"Document {doc_id} missing sellerId"
            assert isinstance(seller_id, ObjectId), \
                f"Document {doc_id}: sellerId is {type(seller_id).__name__}, expected ObjectId"
            
            # Check productId
            product_id = doc.get("productId")
            assert product_id is not None, f"Document {doc_id} missing productId"
            assert isinstance(product_id, ObjectId), \
                f"Document {doc_id}: productId is {type(product_id).__name__}, expected ObjectId"
            
            # Check categoryId
            category_id = doc.get("categoryId")
            assert category_id is not None, f"Document {doc_id} missing categoryId"
            assert isinstance(category_id, ObjectId), \
                f"Document {doc_id}: categoryId is {type(category_id).__name__}, expected ObjectId"
        
        print(f"✅ All {len(docs)} documents have correct ObjectId types")
    
    def test_unique_compound_index_exists(self):
        """
        Test 10: Verify unique compound index (sellerId, productId) exists
        """
        if not MONGO_URL:
            pytest.skip("MONGO_URL not configured")
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        indexes = list(db.seller_listings.list_indexes())
        
        unique_index_exists = any(
            idx.get('unique', False) and
            'sellerId' in str(idx.get('key', {})) and
            'productId' in str(idx.get('key', {}))
            for idx in indexes
        )
        
        assert unique_index_exists, "Missing unique compound index (sellerId, productId)"
        
        print("✅ Unique compound index (sellerId, productId) exists")


# Run tests directly if executed as script
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
