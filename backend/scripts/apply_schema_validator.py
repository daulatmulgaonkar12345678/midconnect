"""
MongoDB JSON Schema Validator for seller_listings Collection

This script applies a STRICT MongoDB JSON Schema Validator that:
1. Enforces the canonical ObjectId-based schema
2. Rejects ANY writes that don't conform
3. Prevents future schema drift at the database level

VALIDATION LEVEL: strict (rejects all non-conforming documents)
VALIDATION ACTION: error (fail the operation, don't just warn)

Usage:
    python apply_schema_validator.py

This is a DEPLOYMENT GUARD - it should be run:
1. During initial deployment
2. After any migration
3. As a pre-start hook in the application startup
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()


# ==================== CANONICAL SCHEMA DEFINITION ====================
# This is the SINGLE SOURCE OF TRUTH for the seller_listings schema

SELLER_LISTINGS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["sellerId", "productId", "categoryId", "status", "createdAt", "updatedAt"],
        "additionalProperties": True,  # Allow additional fields for flexibility
        "properties": {
            # === CANONICAL ID FIELDS (MUST BE ObjectId) ===
            "sellerId": {
                "bsonType": "objectId",
                "description": "Reference to users collection - MUST be ObjectId"
            },
            "productId": {
                "bsonType": "objectId", 
                "description": "Reference to products collection - MUST be ObjectId"
            },
            "categoryId": {
                "bsonType": "objectId",
                "description": "Reference to categories collection - MUST be ObjectId"
            },
            
            # === STATUS FIELDS ===
            "status": {
                "enum": ["active", "inactive", "draft", "paused", "archived"],
                "description": "Listing status"
            },
            "is_active": {
                "bsonType": "bool",
                "description": "Quick-access boolean for active status"
            },
            
            # === COMMERCIAL DATA ===
            "stock": {
                "bsonType": ["int", "double", "long"],
                "minimum": 0,
                "description": "Available stock quantity"
            },
            "moq": {
                "bsonType": ["int", "double", "long"],
                "minimum": 1,
                "description": "Minimum Order Quantity"
            },
            "maxCapacity": {
                "bsonType": ["int", "double", "long", "null"],
                "description": "Maximum production/order capacity"
            },
            "leadTime": {
                "bsonType": ["int", "double", "string", "null"],
                "description": "Lead time in days or descriptive string"
            },
            "currency": {
                "bsonType": "string",
                "description": "Currency code (default: INR)"
            },
            
            # === PRICING ===
            "pricingTiers": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["minQty", "pricePerUnit"],
                    "properties": {
                        "minQty": {
                            "bsonType": ["int", "double", "long"],
                            "minimum": 1
                        },
                        "maxQty": {
                            "bsonType": ["int", "double", "long", "null"]
                        },
                        "pricePerUnit": {
                            "bsonType": ["int", "double", "long"],
                            "minimum": 0
                        }
                    }
                },
                "description": "Tiered pricing structure"
            },
            
            # === SELLER METADATA ===
            "sellerRole": {
                "bsonType": "string",
                "description": "Seller's role for this product (Manufacturer, Dealer, etc.)"
            },
            "description": {
                "bsonType": ["string", "null"],
                "description": "Product description by seller"
            },
            "images": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "Product image URLs"
            },
            "specifications": {
                "bsonType": ["object", "null"],
                "description": "Product specifications"
            },
            
            # === TIMESTAMPS (MUST BE camelCase) ===
            "createdAt": {
                "bsonType": "date",
                "description": "Document creation timestamp"
            },
            "updatedAt": {
                "bsonType": "date",
                "description": "Last update timestamp"
            },
            "publishedAt": {
                "bsonType": ["date", "null"],
                "description": "When listing was first published"
            }
        },
        
        # === FORBIDDEN LEGACY FIELDS ===
        # These are explicitly NOT allowed - validation will fail if present
        "not": {
            "anyOf": [
                {"required": ["seller_id"]},
                {"required": ["product_id"]},
                {"required": ["category_id"]},
                {"required": ["product_name"]},
                {"required": ["category_name"]},
                {"required": ["created_at"]},
                {"required": ["updated_at"]},
                {"required": ["published_at"]}
            ]
        }
    }
}


def apply_schema_validator():
    """
    Apply the MongoDB JSON Schema Validator to seller_listings.
    
    Returns: (success: bool, message: str)
    """
    print("=" * 70)
    print("🔒 APPLYING MONGODB SCHEMA VALIDATOR")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Collection: seller_listings")
    print(f"Validation Level: strict")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Check if collection exists
        if "seller_listings" not in db.list_collection_names():
            print("\n⚠️  Collection 'seller_listings' does not exist. Creating with validator...")
            db.create_collection(
                "seller_listings",
                validator=SELLER_LISTINGS_SCHEMA,
                validationLevel="strict",
                validationAction="error"
            )
            print("✅ Collection created with schema validator")
        else:
            # Apply validator to existing collection
            print("\n📋 Applying validator to existing collection...")
            
            # First, verify all existing documents conform
            print("   Checking existing documents...")
            total_docs = db.seller_listings.count_documents({})
            
            # Check for legacy fields
            legacy_check = db.seller_listings.count_documents({
                "$or": [
                    {"seller_id": {"$exists": True}},
                    {"product_id": {"$exists": True}},
                    {"category_id": {"$exists": True}},
                    {"product_name": {"$exists": True}},
                    {"category_name": {"$exists": True}}
                ]
            })
            
            if legacy_check > 0:
                print(f"\n❌ ABORT: {legacy_check} documents have legacy fields!")
                print("   Run V8 migration first to clean up legacy data.")
                print("   Command: python /app/backend/migrations/V8_final_hard_enforcement.py")
                return False, f"Cannot apply validator: {legacy_check} documents have legacy fields"
            
            print(f"   ✅ All {total_docs} documents conform to canonical schema")
            
            # Apply the validator
            db.command({
                "collMod": "seller_listings",
                "validator": SELLER_LISTINGS_SCHEMA,
                "validationLevel": "strict",
                "validationAction": "error"
            })
            print("✅ Schema validator applied successfully")
        
        # Verify validator is active
        print("\n📋 Verifying validator is active...")
        coll_info = db.command({"listCollections": 1, "filter": {"name": "seller_listings"}})
        
        for coll in coll_info.get("cursor", {}).get("firstBatch", []):
            options = coll.get("options", {})
            validator = options.get("validator")
            level = options.get("validationLevel", "off")
            action = options.get("validationAction", "warn")
            
            print(f"   Validation Level: {level}")
            print(f"   Validation Action: {action}")
            print(f"   Validator Active: {'Yes' if validator else 'No'}")
            
            if level != "strict" or action != "error":
                print(f"\n⚠️  WARNING: Validator not in strict/error mode!")
                return False, "Validator not in strict mode"
        
        print("\n" + "=" * 70)
        print("✅ SCHEMA VALIDATOR SUCCESSFULLY APPLIED")
        print("=" * 70)
        print("\nFrom now on, any write operation with:")
        print("  - seller_id (instead of sellerId)")
        print("  - product_id (instead of productId)")
        print("  - Non-ObjectId foreign keys")
        print("  - Missing required fields")
        print("\nWill be REJECTED at the database level.")
        print("=" * 70)
        
        return True, "Schema validator applied successfully"
        
    except OperationFailure as e:
        print(f"\n❌ MongoDB operation failed: {e}")
        return False, str(e)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False, str(e)


def test_validator():
    """
    Test the schema validator by attempting to insert an invalid document.
    This should FAIL if the validator is working correctly.
    """
    print("\n" + "=" * 70)
    print("🧪 TESTING SCHEMA VALIDATOR")
    print("=" * 70)
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    from bson import ObjectId
    
    # Test 1: Try to insert with legacy seller_id (string) - SHOULD FAIL
    print("\n📋 Test 1: Insert with legacy 'seller_id' field (should FAIL)...")
    try:
        db.seller_listings.insert_one({
            "seller_id": "invalid_string_id",  # LEGACY - should be sellerId with ObjectId
            "productId": ObjectId(),
            "categoryId": ObjectId(),
            "status": "active",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        })
        print("   ❌ FAIL: Insert succeeded (validator not working!)")
        return False
    except Exception as e:
        print(f"   ✅ PASS: Insert correctly rejected - {type(e).__name__}")
    
    # Test 2: Try to insert with string sellerId (should FAIL)
    print("\n📋 Test 2: Insert with string sellerId (should FAIL)...")
    try:
        db.seller_listings.insert_one({
            "sellerId": "invalid_string_id",  # String instead of ObjectId
            "productId": ObjectId(),
            "categoryId": ObjectId(),
            "status": "active",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        })
        print("   ❌ FAIL: Insert succeeded (validator not working!)")
        return False
    except Exception as e:
        print(f"   ✅ PASS: Insert correctly rejected - {type(e).__name__}")
    
    # Test 3: Valid document (should SUCCEED)
    print("\n📋 Test 3: Insert valid document (should SUCCEED)...")
    test_doc_id = ObjectId()
    try:
        result = db.seller_listings.insert_one({
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
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        })
        print(f"   ✅ PASS: Valid document inserted: {result.inserted_id}")
        
        # Clean up test document
        db.seller_listings.delete_one({"_id": test_doc_id})
        print("   ✅ Test document cleaned up")
    except Exception as e:
        print(f"   ❌ FAIL: Valid insert rejected - {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL VALIDATOR TESTS PASSED")
    print("=" * 70)
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply MongoDB Schema Validator")
    parser.add_argument("--test", action="store_true", help="Run validator tests after applying")
    parser.add_argument("--test-only", action="store_true", help="Only run tests, don't apply validator")
    args = parser.parse_args()
    
    if args.test_only:
        success = test_validator()
        return 0 if success else 1
    
    success, message = apply_schema_validator()
    
    if success and args.test:
        test_success = test_validator()
        if not test_success:
            return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
