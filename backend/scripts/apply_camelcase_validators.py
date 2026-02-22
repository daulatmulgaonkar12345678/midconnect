"""
MongoDB Schema Validators - CamelCase SSOT
==========================================

This script applies strict JSON Schema validators aligned with camelCase SSOT.

Field naming:
- ALL fields use camelCase
- ID fields: sellerId, productId, categoryId, etc.
- Timestamps: createdAt, updatedAt
- Booleans: isActive

Run: python backend/scripts/apply_camelcase_validators.py
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import json

load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

# ================== SCHEMA DEFINITIONS (CamelCase SSOT) ==================

PRODUCTS_SCHEMA = {
    "bsonType": "object",
    "required": ["categoryId", "name"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "categoryId": {
            "bsonType": "objectId",
            "description": "Reference to categories collection"
        },
        "sellerId": {
            "bsonType": ["objectId", "null"],
            "description": "Optional direct seller reference"
        },
        "createdBy": {
            "bsonType": ["string", "null"],
            "description": "User who created the product"
        },
        "name": {
            "bsonType": "string",
            "minLength": 2
        },
        "slug": {"bsonType": ["string", "null"]},
        "family": {"bsonType": ["string", "null"]},
        "variant": {"bsonType": ["string", "null"]},
        "description": {"bsonType": ["string", "null"]},
        "unit": {"bsonType": ["string", "null"]},
        "price": {"bsonType": ["double", "int", "null"]},
        "stock": {"bsonType": ["int", "null"]},
        "moq": {"bsonType": ["int", "null"]},
        "images": {"bsonType": ["array", "null"]},
        "specifications": {"bsonType": ["object", "null"]},
        "specTemplateId": {"bsonType": ["string", "null"]},
        "specTemplateIds": {"bsonType": ["array", "null"]},
        "specSchema": {"bsonType": ["array", "null"]},
        "standardParameters": {"bsonType": ["array", "null"]},
        "normalizedSpecHash": {"bsonType": ["string", "null"]},
        "normalizedSpecs": {"bsonType": ["object", "null"]},
        "isActive": {"bsonType": "bool"},
        "status": {"bsonType": ["string", "null"]},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"},
        "deletedAt": {"bsonType": ["date", "null"]},
        "deletedBy": {"bsonType": ["string", "null"]}
    },
    "additionalProperties": True
}

SELLER_LISTINGS_SCHEMA = {
    "bsonType": "object",
    "required": ["sellerId", "productId", "categoryId", "status"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "sellerId": {
            "bsonType": "objectId",
            "description": "Reference to users collection"
        },
        "productId": {
            "bsonType": "objectId",
            "description": "Reference to products collection"
        },
        "categoryId": {
            "bsonType": "objectId",
            "description": "Reference to categories collection"
        },
        "status": {
            "enum": ["draft", "active", "paused", "archived", "deleted"]
        },
        "isActive": {"bsonType": "bool"},
        "stock": {"bsonType": ["int", "null"]},
        "moq": {"bsonType": ["int", "null"]},
        "maxCapacity": {"bsonType": ["int", "null"]},
        "leadTime": {"bsonType": ["int", "null"]},
        "currency": {"bsonType": ["string", "null"]},
        "pricingTiers": {"bsonType": ["array", "null"]},
        "sellerRole": {"bsonType": ["string", "null"]},
        "description": {"bsonType": ["string", "null"]},
        "images": {"bsonType": ["array", "null"]},
        "specifications": {"bsonType": ["object", "null"]},
        "sellerNotes": {"bsonType": ["string", "null"]},
        "packagingSize": {"bsonType": ["string", "null"]},
        "deliveryLocations": {"bsonType": ["array", "null"]},
        "capacityTimeBasis": {"bsonType": ["string", "null"]},
        "lastStockUpdate": {"bsonType": ["date", "null"]},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"},
        "publishedAt": {"bsonType": ["date", "null"]}
    },
    "additionalProperties": True
}

INQUIRIES_SCHEMA = {
    "bsonType": "object",
    "required": ["sellerId", "buyerId", "status"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "sellerId": {"bsonType": "objectId"},
        "buyerId": {"bsonType": "objectId"},
        "productId": {"bsonType": ["objectId", "null"]},
        "listingId": {"bsonType": ["objectId", "null"]},
        "status": {
            "enum": ["pending", "viewed", "quoted", "accepted", "rejected", "expired", "cancelled"]
        },
        "quantity": {"bsonType": ["int", "null"]},
        "unit": {"bsonType": ["string", "null"]},
        "message": {"bsonType": ["string", "null"]},
        "buyerType": {"bsonType": ["string", "null"]},
        "buyerInfo": {"bsonType": ["object", "null"]},
        "requirementNote": {"bsonType": ["string", "null"]},
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
        "name": {"bsonType": "string", "minLength": 2},
        "description": {"bsonType": ["string", "null"]},
        "icon": {"bsonType": ["string", "null"]},
        "image": {"bsonType": ["string", "null"]},
        "isActive": {"bsonType": ["bool", "null"]},
        "displayOrder": {"bsonType": ["int", "null"]},
        "allowedUnits": {"bsonType": ["array", "null"]},
        "specTemplate": {"bsonType": ["array", "null"]},
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
        "email": {"bsonType": "string"},
        "firebase_uid": {"bsonType": "string"},
        "business_name": {"bsonType": ["string", "null"]},
        "phone": {"bsonType": ["string", "null"]},
        "city": {"bsonType": ["string", "null"]},
        "state": {"bsonType": ["string", "null"]},
        "pincode": {"bsonType": ["string", "null"]},
        "account_status": {"bsonType": ["string", "null"]},
        "is_active": {"bsonType": ["bool", "null"]},
        "is_admin": {"bsonType": ["bool", "null"]},
        "is_seller": {"bsonType": ["bool", "null"]},
        "email_verified": {"bsonType": ["bool", "null"]},
        "subscription": {"bsonType": ["object", "null"]},
        "createdAt": {"bsonType": ["date", "null"]},
        "updatedAt": {"bsonType": ["date", "null"]}
    },
    "additionalProperties": True
}


def apply_validator(db, collection_name: str, schema: dict):
    """Apply JSON schema validator to a collection"""
    print(f"\n📋 Applying validator to: {collection_name}")
    
    try:
        if collection_name not in db.list_collection_names():
            print(f"  ⚠️ Collection {collection_name} does not exist. Skipping...")
            return True
        
        db.command({
            "collMod": collection_name,
            "validator": {"$jsonSchema": schema},
            "validationLevel": "moderate",
            "validationAction": "warn"
        })
        
        print(f"  ✅ Validator applied")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def run_apply_validators():
    """Main function"""
    print("=" * 70)
    print("🚀 APPLYING CAMELCASE MONGODB SCHEMA VALIDATORS")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    schemas = {
        "products": PRODUCTS_SCHEMA,
        "seller_listings": SELLER_LISTINGS_SCHEMA,
        "inquiries": INQUIRIES_SCHEMA,
        "categories": CATEGORIES_SCHEMA,
        "users": USERS_SCHEMA,
    }
    
    results = {}
    for collection_name, schema in schemas.items():
        success = apply_validator(db, collection_name, schema)
        results[collection_name] = success
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    success_count = sum(1 for v in results.values() if v)
    print(f"  Validators applied: {success_count}/{len(results)}")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_apply_validators()
    sys.exit(0 if success else 1)
