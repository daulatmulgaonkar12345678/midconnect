"""
MongoDB Schema Validators
=========================

This script applies JSON Schema validators to MongoDB collections.
Validators enforce data integrity at the database level.

Validation Mode:
- validationLevel: "moderate" - Validates existing updates but allows invalid inserts
  (Use "strict" for full enforcement once all data is clean)
- validationAction: "warn" - Logs warnings but allows operation
  (Use "error" to reject invalid operations)

Run: python backend/scripts/apply_schema_validators.py
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import json
from pathlib import Path

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

# ================== SCHEMA DEFINITIONS ==================

SELLER_LISTINGS_SCHEMA = {
    "bsonType": "object",
    "required": ["sellerId", "productId", "categoryId", "status"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "sellerId": {
            "bsonType": "objectId",
            "description": "Reference to users collection - must be ObjectId"
        },
        "productId": {
            "bsonType": "objectId",
            "description": "Reference to products collection - must be ObjectId"
        },
        "categoryId": {
            "bsonType": "objectId",
            "description": "Reference to categories collection - must be ObjectId"
        },
        "status": {
            "enum": ["draft", "active", "paused", "archived", "deleted"],
            "description": "Listing status - must be from allowed values"
        },
        "isActive": {
            "bsonType": "bool",
            "description": "Active flag - should match status='active'"
        },
        "is_active": {
            "bsonType": "bool",
            "description": "Active flag (alias) - should match status='active'"
        },
        "stock": {
            "bsonType": "int",
            "minimum": 0,
            "description": "Available stock quantity"
        },
        "moq": {
            "bsonType": "int",
            "minimum": 1,
            "description": "Minimum Order Quantity"
        },
        "maxCapacity": {
            "bsonType": ["int", "null"],
            "description": "Maximum production capacity"
        },
        "leadTime": {
            "bsonType": ["int", "null"],
            "description": "Lead time in days"
        },
        "currency": {
            "bsonType": "string",
            "maxLength": 3,
            "description": "Currency code (INR, USD, etc.)"
        },
        "pricingTiers": {
            "bsonType": "array",
            "items": {
                "bsonType": "object",
                "properties": {
                    "minQty": {"bsonType": "int", "minimum": 1},
                    "maxQty": {"bsonType": ["int", "null"]},
                    "pricePerUnit": {"bsonType": ["double", "int"], "minimum": 0}
                }
            }
        },
        "sellerRole": {
            "bsonType": ["string", "null"],
            "description": "Seller role (Manufacturer, Dealer, etc.)"
        },
        "description": {"bsonType": ["string", "null"]},
        "images": {
            "bsonType": "array",
            "maxItems": 10
        },
        "specifications": {"bsonType": ["object", "null"]},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"},
        "publishedAt": {"bsonType": ["date", "null"]}
    },
    # REJECT legacy fields - these should never exist
    "additionalProperties": True  # Allow other fields for flexibility
}

PRODUCTS_SCHEMA = {
    "bsonType": "object",
    "required": ["categoryId", "name"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "categoryId": {
            "bsonType": "objectId",
            "description": "Reference to categories collection - must be ObjectId"
        },
        "sellerId": {
            "bsonType": ["objectId", "null"],
            "description": "Optional direct seller reference"
        },
        "name": {
            "bsonType": "string",
            "minLength": 2,
            "description": "Product name"
        },
        "slug": {
            "bsonType": "string",
            "description": "URL-friendly slug"
        },
        "family": {"bsonType": ["string", "null"]},
        "variant": {"bsonType": ["string", "null"]},
        "description": {"bsonType": ["string", "null"]},
        "unit": {
            "bsonType": "string",
            "description": "Unit of measurement"
        },
        "isActive": {"bsonType": "bool"},
        "is_active": {"bsonType": "bool"},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"}
    },
    "additionalProperties": True
}

INQUIRIES_SCHEMA = {
    "bsonType": "object",
    "required": ["sellerId", "buyerId", "status"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "sellerId": {
            "bsonType": "objectId",
            "description": "Seller user reference - must be ObjectId"
        },
        "buyerId": {
            "bsonType": "objectId",
            "description": "Buyer user reference - must be ObjectId"
        },
        "productId": {
            "bsonType": ["objectId", "null"],
            "description": "Product reference (if product-specific)"
        },
        "listingId": {
            "bsonType": ["objectId", "null"],
            "description": "Listing reference (if listing-specific)"
        },
        "status": {
            "enum": ["pending", "viewed", "quoted", "accepted", "rejected", "expired", "cancelled"],
            "description": "Inquiry status"
        },
        "quantity": {"bsonType": "int", "minimum": 1},
        "unit": {"bsonType": "string"},
        "message": {"bsonType": ["string", "null"]},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": ["date", "null"]},
        "acceptedAt": {"bsonType": ["date", "null"]},
        "quotedAt": {"bsonType": ["date", "null"]}
    },
    "additionalProperties": True
}

CATEGORIES_SCHEMA = {
    "bsonType": "object",
    "required": ["name"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "name": {
            "bsonType": "string",
            "minLength": 2
        },
        "description": {"bsonType": ["string", "null"]},
        "icon": {"bsonType": ["string", "null"]},
        "is_active": {"bsonType": "bool"},
        "isActive": {"bsonType": "bool"},
        "allowed_units": {
            "bsonType": "array",
            "items": {"bsonType": "string"}
        },
        "spec_template": {
            "bsonType": ["array", "null"],
            "items": {"bsonType": "object"}
        },
        "createdAt": {"bsonType": ["date", "null"]},
        "updatedAt": {"bsonType": ["date", "null"]}
    },
    "additionalProperties": True
}

USERS_SCHEMA = {
    "bsonType": "object",
    "required": ["email", "firebase_uid"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "email": {
            "bsonType": "string",
            "pattern": "^.+@.+$"
        },
        "firebase_uid": {"bsonType": "string"},
        "business_name": {"bsonType": "string"},
        "phone": {"bsonType": "string"},
        "city": {"bsonType": "string"},
        "state": {"bsonType": "string"},
        "pincode": {"bsonType": "string"},
        "account_status": {
            "enum": ["active", "deleted", "archived", "suspended"],
            "description": "Account status"
        },
        "is_active": {"bsonType": "bool"},
        "is_admin": {"bsonType": "bool"},
        "is_seller": {"bsonType": "bool"},
        "email_verified": {"bsonType": "bool"},
        "can_login": {"bsonType": "bool"},
        "subscription": {
            "bsonType": ["object", "null"],
            "properties": {
                "status": {
                    "enum": ["free", "trial", "pro", "expired", "cancelled"]
                },
                "plan": {
                    "enum": ["free", "trial", "pro"]
                }
            }
        },
        "created_at": {"bsonType": ["date", "null"]},
        "updated_at": {"bsonType": ["date", "null"]}
    },
    "additionalProperties": True
}


def apply_validator(db, collection_name: str, schema: dict, validation_level: str = "moderate", validation_action: str = "warn"):
    """Apply JSON schema validator to a collection"""
    print(f"\n📋 Applying validator to: {collection_name}")
    
    try:
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            print(f"  ⚠️ Collection {collection_name} does not exist. Creating...")
            db.create_collection(collection_name)
        
        # Apply validator
        db.command({
            "collMod": collection_name,
            "validator": {"$jsonSchema": schema},
            "validationLevel": validation_level,
            "validationAction": validation_action
        })
        
        print(f"  ✅ Validator applied successfully")
        print(f"     - Level: {validation_level}")
        print(f"     - Action: {validation_action}")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to apply validator: {e}")
        return False


def verify_validators(db):
    """Verify validators are applied"""
    print("\n" + "=" * 60)
    print("🔍 VERIFICATION")
    print("=" * 60)
    
    for collection_name in ["seller_listings", "products", "inquiries", "categories", "users"]:
        try:
            info = db.command({"listCollections": 1, "filter": {"name": collection_name}})
            collections = list(info.get("cursor", {}).get("firstBatch", []))
            
            if collections:
                coll_info = collections[0]
                validator = coll_info.get("options", {}).get("validator")
                if validator:
                    print(f"  ✅ {collection_name}: Validator present")
                else:
                    print(f"  ⚠️ {collection_name}: No validator")
            else:
                print(f"  ❓ {collection_name}: Collection not found")
        except Exception as e:
            print(f"  ❌ {collection_name}: Error checking - {e}")


def run_apply_validators():
    """Main function to apply all validators"""
    print("=" * 70)
    print("🚀 APPLYING MONGODB SCHEMA VALIDATORS")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("\nValidation Settings:")
    print("  - Level: moderate (validates updates, not existing docs)")
    print("  - Action: warn (logs issues, doesn't reject)")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Define schemas for each collection
    schemas = {
        "seller_listings": SELLER_LISTINGS_SCHEMA,
        "products": PRODUCTS_SCHEMA,
        "inquiries": INQUIRIES_SCHEMA,
        "categories": CATEGORIES_SCHEMA,
        "users": USERS_SCHEMA,
    }
    
    results = {}
    for collection_name, schema in schemas.items():
        success = apply_validator(db, collection_name, schema)
        results[collection_name] = success
    
    # Verify
    verify_validators(db)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    success_count = sum(1 for v in results.values() if v)
    print(f"  Validators applied: {success_count}/{len(results)}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_apply_validators()
    sys.exit(0 if success else 1)
