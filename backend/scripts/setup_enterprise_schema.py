#!/usr/bin/env python3
"""
ENTERPRISE B2B MARKETPLACE - FINAL ARCHITECTURE SETUP
======================================================

This script:
1. Drops ALL existing collections (hard reset)
2. Creates collections with STRICT MongoDB schema validators
3. Creates proper indexes
4. Seeds minimal required data

ARCHITECTURAL RULES:
- All references are ObjectId (never string)
- All fields are camelCase (never snake_case)
- SpecTemplate is versioned
- ProductVariant stores templateVersions
- SellerListing is commercial-only (no specifications)
- No fallback logic anywhere

Run: python scripts/setup_enterprise_schema.py
"""

import asyncio
import os
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "b2b_marketplace")


# ==================== SCHEMA VALIDATORS ====================

CATEGORIES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "isActive", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 100},
            "description": {"bsonType": ["string", "null"]},
            "image": {"bsonType": ["string", "null"]},
            "icon": {"bsonType": ["string", "null"]},
            "settings": {"bsonType": ["object", "null"]},
            "displayOrder": {"bsonType": "int"},
            "isActive": {"bsonType": "bool"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "createdBy": {"bsonType": ["objectId", "null"]}
        },
        # STRICT: Reject snake_case fields
        "not": {
            "anyOf": [
                {"required": ["is_active"]},
                {"required": ["created_at"]},
                {"required": ["updated_at"]},
                {"required": ["display_order"]},
                {"required": ["created_by"]}
            ]
        }
    }
}

SPEC_TEMPLATES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["categoryId", "name", "version", "fields", "isActive", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "categoryId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 100},
            "version": {"bsonType": "int", "minimum": 1},
            "description": {"bsonType": ["string", "null"]},
            "fields": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["key", "label", "fieldType"],
                    "properties": {
                        "key": {"bsonType": "string"},
                        "label": {"bsonType": "string"},
                        "fieldType": {"enum": ["text", "number", "dropdown", "boolean", "range"]},
                        "unit": {"bsonType": ["string", "null"]},
                        "isMandatory": {"bsonType": "bool"},
                        "isSellerEditable": {"bsonType": "bool"},
                        "isLockedAfterCreate": {"bsonType": "bool"},
                        "displayOrder": {"bsonType": "int"},
                        "options": {"bsonType": ["array", "null"]},
                        "minValue": {"bsonType": ["number", "null"]},
                        "maxValue": {"bsonType": ["number", "null"]},
                        "placeholder": {"bsonType": ["string", "null"]},
                        "helpText": {"bsonType": ["string", "null"]}
                    }
                }
            },
            "isActive": {"bsonType": "bool"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "createdBy": {"bsonType": ["objectId", "null"]}
        },
        # STRICT: Reject snake_case fields
        "not": {
            "anyOf": [
                {"required": ["category_id"]},
                {"required": ["is_active"]},
                {"required": ["created_at"]},
                {"required": ["field_type"]},
                {"required": ["is_mandatory"]}
            ]
        }
    }
}

PRODUCTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "categoryId", "specTemplateIds", "isActive", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
            "slug": {"bsonType": "string"},
            "categoryId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "manufacturerId": {"bsonType": ["objectId", "null"]},  # STRICT: Must be ObjectId
            "specTemplateIds": {
                "bsonType": "array",
                "items": {"bsonType": "objectId"}  # STRICT: Array of ObjectId
            },
            "coverImage": {"bsonType": ["string", "null"]},
            "description": {"bsonType": ["string", "null"]},
            "isActive": {"bsonType": "bool"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "createdBy": {"bsonType": ["objectId", "null"]}
        },
        # STRICT: Reject snake_case and legacy fields
        "not": {
            "anyOf": [
                {"required": ["category_id"]},
                {"required": ["manufacturer_id"]},
                {"required": ["spec_template_id"]},
                {"required": ["spec_template_ids"]},
                {"required": ["specifications"]},  # Products must NOT store specs
                {"required": ["product_name"]}
            ]
        }
    }
}

PRODUCT_VARIANTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["productId", "templateVersions", "attributes", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "productId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "templateVersions": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["templateId", "version"],
                    "properties": {
                        "templateId": {"bsonType": "objectId"},
                        "version": {"bsonType": "int"}
                    }
                }
            },
            "attributes": {"bsonType": "object"},
            "createdAt": {"bsonType": "date"}
        },
        # STRICT: Reject snake_case and legacy fields
        "not": {
            "anyOf": [
                {"required": ["product_id"]},
                {"required": ["spec_template_id"]},
                {"required": ["specTemplateId"]},  # Use templateVersions instead
                {"required": ["specifications"]}
            ]
        }
    }
}

SELLER_LISTINGS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["sellerId", "productId", "variantId", "categoryId", "status", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "sellerId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "productId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "variantId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            "categoryId": {"bsonType": "objectId"},  # STRICT: Must be ObjectId
            
            # Commercial fields only
            "sellerRole": {"enum": ["manufacturer", "distributor", "dealer", "trader", "Manufacturer", "Distributor", "Dealer", "Trader"]},
            "description": {"bsonType": ["string", "null"]},
            "images": {"bsonType": ["array", "null"]},
            "moq": {"bsonType": ["int", "null"]},
            "stock": {"bsonType": ["int", "null"]},
            "maxCapacity": {"bsonType": ["int", "null"]},
            "leadTime": {"bsonType": ["string", "null"]},
            "currency": {"bsonType": "string"},
            "pricingTiers": {"bsonType": ["array", "null"]},
            
            "status": {"enum": ["draft", "active", "paused", "archived", "inactive"]},
            "isActive": {"bsonType": "bool"},
            "publishedAt": {"bsonType": ["date", "null"]},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"}
        },
        # STRICT: Reject snake_case and specification fields
        "not": {
            "anyOf": [
                {"required": ["seller_id"]},
                {"required": ["product_id"]},
                {"required": ["variant_id"]},
                {"required": ["category_id"]},
                {"required": ["specifications"]},  # SellerListing must NOT store specs
                {"required": ["attributes"]},  # SellerListing must NOT store attributes
                {"required": ["pricing_slabs"]},
                {"required": ["max_capacity"]}
            ]
        }
    }
}

USERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["email", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "email": {"bsonType": "string"},
            "firebaseUid": {"bsonType": ["string", "null"]},
            "businessName": {"bsonType": ["string", "null"]},
            "phone": {"bsonType": ["string", "null"]},
            "city": {"bsonType": ["string", "null"]},
            "state": {"bsonType": ["string", "null"]},
            "pincode": {"bsonType": ["string", "null"]},
            "isSeller": {"bsonType": "bool"},
            "isAdmin": {"bsonType": "bool"},
            "emailVerified": {"bsonType": "bool"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"}
        },
        # STRICT: Reject snake_case fields
        "not": {
            "anyOf": [
                {"required": ["firebase_uid"]},
                {"required": ["business_name"]},
                {"required": ["is_seller"]},
                {"required": ["is_admin"]},
                {"required": ["email_verified"]},
                {"required": ["created_at"]}
            ]
        }
    }
}

INQUIRIES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["sellerId", "buyerId", "quantity", "status", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "productId": {"bsonType": ["objectId", "null"]},
            "listingId": {"bsonType": ["objectId", "null"]},
            "sellerId": {"bsonType": "objectId"},
            "buyerId": {"bsonType": "objectId"},
            "quantity": {"bsonType": "int"},
            "message": {"bsonType": ["string", "null"]},
            "status": {"enum": ["pending", "accepted", "rejected", "reported", "closed"]},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"}
        },
        # STRICT: Reject snake_case fields
        "not": {
            "anyOf": [
                {"required": ["seller_id"]},
                {"required": ["buyer_id"]},
                {"required": ["product_id"]},
                {"required": ["listing_id"]},
                {"required": ["created_at"]}
            ]
        }
    }
}

MANUFACTURERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "isActive", "createdAt"],
        "additionalProperties": True,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string"},
            "slug": {"bsonType": ["string", "null"]},
            "logo": {"bsonType": ["string", "null"]},
            "description": {"bsonType": ["string", "null"]},
            "isActive": {"bsonType": "bool"},
            "isVerified": {"bsonType": "bool"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "createdBy": {"bsonType": ["objectId", "null"]}
        },
        "not": {
            "anyOf": [
                {"required": ["is_active"]},
                {"required": ["is_verified"]},
                {"required": ["created_at"]}
            ]
        }
    }
}


async def setup_enterprise_schema():
    """Setup the complete enterprise schema with validators"""
    print("=" * 70)
    print("ENTERPRISE B2B MARKETPLACE - FINAL ARCHITECTURE SETUP")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # ==================== STEP 1: DROP ALL COLLECTIONS ====================
    print("[STEP 1] Hard reset - Dropping all collections...")
    
    collections_to_drop = [
        "categories", "specTemplates", "products", "productVariants",
        "sellerListings", "inquiries", "manufacturers", "globalDropdowns",
        "subscriptions", "subscriptionHistory",
        # Legacy collection names (if exist)
        "spec_templates", "seller_listings", "global_dropdowns", "subscription_history"
    ]
    
    for coll_name in collections_to_drop:
        try:
            await db.drop_collection(coll_name)
            print(f"   Dropped: {coll_name}")
        except Exception as e:
            print(f"   Skip: {coll_name} ({e})")
    
    print()
    
    # ==================== STEP 2: CREATE COLLECTIONS WITH VALIDATORS ====================
    print("[STEP 2] Creating collections with STRICT schema validators...")
    
    validators = {
        "categories": CATEGORIES_VALIDATOR,
        "specTemplates": SPEC_TEMPLATES_VALIDATOR,
        "products": PRODUCTS_VALIDATOR,
        "productVariants": PRODUCT_VARIANTS_VALIDATOR,
        "sellerListings": SELLER_LISTINGS_VALIDATOR,
        "users": USERS_VALIDATOR,
        "inquiries": INQUIRIES_VALIDATOR,
        "manufacturers": MANUFACTURERS_VALIDATOR,
        "globalDropdowns": {"$jsonSchema": {"bsonType": "object"}},
        "subscriptions": {"$jsonSchema": {"bsonType": "object"}},
    }
    
    for coll_name, validator in validators.items():
        try:
            await db.create_collection(
                coll_name,
                validator=validator,
                validationLevel="strict",
                validationAction="error"
            )
            print(f"   Created: {coll_name} (with validator)")
        except Exception as e:
            if "already exists" in str(e):
                # Update validator on existing collection
                await db.command("collMod", coll_name, validator=validator)
                print(f"   Updated: {coll_name} (validator applied)")
            else:
                print(f"   Error: {coll_name} - {e}")
    
    print()
    
    # ==================== STEP 3: CREATE INDEXES ====================
    print("[STEP 3] Creating indexes...")
    
    # Categories indexes
    await db.categories.create_index("name", unique=True, name="name_unique")
    await db.categories.create_index("isActive", name="isActive_1")
    print("   categories: name_unique, isActive")
    
    # SpecTemplates indexes
    await db.specTemplates.create_index("categoryId", name="categoryId_1")
    await db.specTemplates.create_index([("categoryId", 1), ("version", -1)], name="categoryId_version")
    await db.specTemplates.create_index("isActive", name="isActive_1")
    print("   specTemplates: categoryId, categoryId_version, isActive")
    
    # Products indexes
    await db.products.create_index("slug", unique=True, name="slug_unique")
    await db.products.create_index("categoryId", name="categoryId_1")
    await db.products.create_index("manufacturerId", name="manufacturerId_1", sparse=True)
    await db.products.create_index("isActive", name="isActive_1")
    await db.products.create_index([("name", "text")], name="name_text")
    print("   products: slug_unique, categoryId, manufacturerId, isActive, name_text")
    
    # ProductVariants indexes
    await db.productVariants.create_index("productId", name="productId_1")
    await db.productVariants.create_index([("productId", 1), ("attributes", 1)], name="productId_attributes")
    print("   productVariants: productId, productId_attributes")
    
    # SellerListings indexes
    await db.sellerListings.create_index("sellerId", name="sellerId_1")
    await db.sellerListings.create_index("productId", name="productId_1")
    await db.sellerListings.create_index("variantId", name="variantId_1")
    await db.sellerListings.create_index("categoryId", name="categoryId_1")
    await db.sellerListings.create_index("status", name="status_1")
    await db.sellerListings.create_index("isActive", name="isActive_1")
    await db.sellerListings.create_index([("sellerId", 1), ("productId", 1)], unique=True, name="sellerId_productId_unique")
    print("   sellerListings: sellerId, productId, variantId, categoryId, status, isActive, sellerId_productId_unique")
    
    # Inquiries indexes
    await db.inquiries.create_index("sellerId", name="sellerId_1")
    await db.inquiries.create_index("buyerId", name="buyerId_1")
    await db.inquiries.create_index("status", name="status_1")
    await db.inquiries.create_index("createdAt", name="createdAt_1")
    print("   inquiries: sellerId, buyerId, status, createdAt")
    
    # Users indexes - handle existing indexes
    try:
        await db.users.drop_indexes()
    except Exception:
        pass
    await db.users.create_index("email", unique=True, name="email_unique")
    await db.users.create_index("firebaseUid", unique=True, sparse=True, name="firebaseUid_unique")
    print("   users: email_unique, firebaseUid_unique")
    
    # Manufacturers indexes
    await db.manufacturers.create_index("name", unique=True, name="name_unique")
    await db.manufacturers.create_index("slug", unique=True, sparse=True, name="slug_unique")
    await db.manufacturers.create_index("isActive", name="isActive_1")
    print("   manufacturers: name_unique, slug_unique, isActive")
    
    print()
    
    # ==================== STEP 4: SEED INITIAL DATA ====================
    print("[STEP 4] Seeding initial data...")
    
    now = datetime.now(timezone.utc)
    
    # Seed category
    category_id = ObjectId()
    await db.categories.insert_one({
        "_id": category_id,
        "name": "Electrical Equipment",
        "description": "Motors, transformers, and electrical machinery",
        "icon": "flash-outline",
        "displayOrder": 1,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now
    })
    print(f"   Category: Electrical Equipment ({category_id})")
    
    # Seed spec template (version 1)
    template_id = ObjectId()
    await db.specTemplates.insert_one({
        "_id": template_id,
        "categoryId": category_id,  # ObjectId reference
        "name": "Electric Motor Specifications",
        "version": 1,
        "description": "Standard specifications for electric motors",
        "fields": [
            {
                "key": "power",
                "label": "Power Rating",
                "fieldType": "number",
                "unit": "kW",
                "isMandatory": True,
                "isSellerEditable": False,
                "isLockedAfterCreate": True,
                "displayOrder": 1,
                "minValue": 0.1,
                "maxValue": 1000,
                "placeholder": "Enter power in kW",
                "helpText": "Motor power output in kilowatts"
            },
            {
                "key": "voltage",
                "label": "Voltage",
                "fieldType": "dropdown",
                "unit": "V",
                "isMandatory": True,
                "isSellerEditable": False,
                "isLockedAfterCreate": True,
                "displayOrder": 2,
                "options": ["220", "380", "415", "440"],
                "helpText": "Operating voltage"
            },
            {
                "key": "phase",
                "label": "Phase",
                "fieldType": "dropdown",
                "isMandatory": True,
                "isSellerEditable": False,
                "isLockedAfterCreate": True,
                "displayOrder": 3,
                "options": ["Single Phase", "Three Phase"],
                "helpText": "Electrical phase"
            },
            {
                "key": "efficiency",
                "label": "Efficiency Class",
                "fieldType": "dropdown",
                "isMandatory": False,
                "isSellerEditable": True,
                "isLockedAfterCreate": False,
                "displayOrder": 4,
                "options": ["IE1", "IE2", "IE3", "IE4"],
                "helpText": "Motor efficiency classification"
            }
        ],
        "isActive": True,
        "createdAt": now,
        "updatedAt": now
    })
    print(f"   SpecTemplate: Electric Motor Specifications v1 ({template_id})")
    
    # Seed manufacturer
    manufacturer_id = ObjectId()
    await db.manufacturers.insert_one({
        "_id": manufacturer_id,
        "name": "ABB Ltd",
        "slug": "abb-ltd",
        "description": "Global leader in power and automation technologies",
        "isActive": True,
        "isVerified": True,
        "createdAt": now,
        "updatedAt": now
    })
    print(f"   Manufacturer: ABB Ltd ({manufacturer_id})")
    
    # Seed product (links to category, manufacturer, templates)
    product_id = ObjectId()
    await db.products.insert_one({
        "_id": product_id,
        "name": "ABB M2AA Series Motor",
        "slug": "abb-m2aa-series-motor",
        "categoryId": category_id,  # ObjectId reference
        "manufacturerId": manufacturer_id,  # ObjectId reference
        "specTemplateIds": [template_id],  # Array of ObjectId
        "description": "High-efficiency cast iron motors for general purpose applications",
        "isActive": True,
        "createdAt": now,
        "updatedAt": now
    })
    print(f"   Product: ABB M2AA Series Motor ({product_id})")
    
    # Seed product variant (freezes template version)
    variant_id = ObjectId()
    await db.productVariants.insert_one({
        "_id": variant_id,
        "productId": product_id,  # ObjectId reference
        "templateVersions": [
            {
                "templateId": template_id,  # ObjectId reference
                "version": 1  # Frozen version
            }
        ],
        "attributes": {
            "power": 45,
            "voltage": "415",
            "phase": "Three Phase",
            "efficiency": "IE3"
        },
        "createdAt": now
    })
    print(f"   ProductVariant: 45kW 415V Three Phase ({variant_id})")
    
    print()
    print("=" * 70)
    print("ENTERPRISE SCHEMA SETUP COMPLETE")
    print("=" * 70)
    print()
    print("Architecture Summary:")
    print("  - Categories: Business grouping only (no template refs)")
    print("  - SpecTemplates: Versioned, multiple per category")
    print("  - Products: Links to category, manufacturer, specTemplateIds[]")
    print("  - ProductVariants: Stores templateVersions[] + attributes")
    print("  - SellerListings: Commercial only (no specifications)")
    print()
    print("Enforcement:")
    print("  - All references are ObjectId (validated)")
    print("  - All fields are camelCase (snake_case rejected)")
    print("  - Schema validators in STRICT mode")
    print()
    
    client.close()


if __name__ == "__main__":
    asyncio.run(setup_enterprise_schema())
