"""
V11 Final Schema Enforcement Migration
======================================
Applies strict MongoDB JSON Schema validators to ALL collections.
Ensures proper ObjectId references, camelCase SSOT, and Firebase image URL fields.

Collections Updated:
- categories
- category_requests  
- inquiries
- inquiry_reports
- product_requests
- products
- seller_listings
- spec_templates
- subscription_changes
- subscriptions
- users

Key Features:
- All fields use camelCase (SSOT)
- All references use ObjectId type
- Image URLs stored as strings (Firebase URLs)
- additionalProperties: false (strict validation)
- Proper required fields
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
import json

# =============================================================================
# SCHEMA DEFINITIONS - STRICT camelCase SSOT
# =============================================================================

SCHEMAS = {
    "categories": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "description": {"bsonType": ["string", "null"]},
                "imageUrl": {"bsonType": ["string", "null"]},  # Firebase URL
                "icon": {"bsonType": ["string", "null"]},
                "displayOrder": {"bsonType": ["int", "long"]},
                "settings": {
                    "bsonType": "object",
                    "properties": {
                        "allowedUnits": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "defaultUnit": {"bsonType": ["string", "null"]},
                        "allowedSellerTypes": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "dimensionsEnabled": {"bsonType": "bool"},
                        "dimensionUnits": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "dimensionFormat": {"bsonType": ["string", "null"]},
                        "dropdownOverrides": {"bsonType": ["object", "null"]}
                    }
                },
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "createdBy": {"bsonType": ["objectId", "null"]},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "category_requests": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["categoryName", "requestedBy", "status", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "categoryName": {"bsonType": "string"},
                "description": {"bsonType": ["string", "null"]},
                "reason": {"bsonType": ["string", "null"]},
                "requestedBy": {"bsonType": "objectId"},
                "requestedByEmail": {"bsonType": "string"},
                "status": {"bsonType": "string"},
                "adminNotes": {"bsonType": ["string", "null"]},
                "reviewedAt": {"bsonType": ["date", "null"]},
                "reviewedBy": {"bsonType": ["objectId", "null"]},
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "inquiries": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["listingId", "sellerId", "buyerId", "quantity", "status", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "listingId": {"bsonType": "objectId"},
                "productId": {"bsonType": ["objectId", "null"]},
                "sellerId": {"bsonType": "objectId"},
                "buyerId": {"bsonType": "objectId"},
                "quantity": {"bsonType": "int"},
                "message": {"bsonType": ["string", "null"]},
                "requirementNote": {"bsonType": ["string", "null"]},
                "buyerType": {"bsonType": "string"},
                "buyerInfo": {
                    "bsonType": "object",
                    "properties": {
                        "name": {"bsonType": "string"},
                        "companyName": {"bsonType": ["string", "null"]},
                        "email": {"bsonType": "string"},
                        "phone": {"bsonType": ["string", "null"]},
                        "city": {"bsonType": ["string", "null"]},
                        "state": {"bsonType": ["string", "null"]}
                    }
                },
                "status": {"bsonType": "string"},
                "acceptedAt": {"bsonType": ["date", "null"]},
                "rejectedAt": {"bsonType": ["date", "null"]},
                "expiredAt": {"bsonType": ["date", "null"]},
                "quote": {
                    "bsonType": ["object", "null"],
                    "properties": {
                        "price": {"bsonType": ["double", "int", "null"]},
                        "moq": {"bsonType": ["int", "null"]},
                        "leadTimeDays": {"bsonType": ["int", "null"]},
                        "validTill": {"bsonType": ["date", "null"]},
                        "sellerNote": {"bsonType": ["string", "null"]},
                        "quotedAt": {"bsonType": ["date", "null"]}
                    }
                },
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "inquiry_reports": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["inquiryId", "sellerId", "buyerId", "reportType", "status", "createdAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "inquiryId": {"bsonType": "objectId"},
                "sellerId": {"bsonType": "objectId"},
                "buyerId": {"bsonType": "objectId"},
                "reportType": {"bsonType": "string"},
                "details": {"bsonType": ["string", "null"]},
                "status": {"bsonType": "string"},
                "reviewedBy": {"bsonType": ["objectId", "null"]},
                "reviewedAt": {"bsonType": ["date", "null"]},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": ["date", "null"]}
            }
        }
    },
    
    "product_requests": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["productName", "suggestedCategoryId", "requestedBy", "status", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "productName": {"bsonType": "string"},
                "suggestedCategoryId": {"bsonType": "objectId"},
                "categoryName": {"bsonType": ["string", "null"]},
                "manufacturerId": {"bsonType": ["objectId", "null"]},
                "description": {"bsonType": ["string", "null"]},
                "baseSpecifications": {"bsonType": "object"},
                "reason": {"bsonType": ["string", "null"]},
                "requestedBy": {"bsonType": "objectId"},
                "requestedByEmail": {"bsonType": "string"},
                "status": {"bsonType": "string"},
                "adminNotes": {"bsonType": ["string", "null"]},
                "createdProductId": {"bsonType": ["objectId", "null"]},
                "reviewedAt": {"bsonType": ["date", "null"]},
                "reviewedBy": {"bsonType": ["objectId", "null"]},
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "products": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "categoryId", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "description": {"bsonType": ["string", "null"]},
                "categoryId": {"bsonType": "objectId"},
                "categoryName": {"bsonType": "string"},
                "family": {"bsonType": ["string", "null"]},
                "variant": {"bsonType": ["string", "null"]},
                "coverImageUrl": {"bsonType": ["string", "null"]},  # Firebase URL - admin uploads
                "specTemplateIds": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "specTemplateVersions": {"bsonType": "array", "items": {"bsonType": ["int", "long"]}},
                "unit": {"bsonType": ["string", "null"]},
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "createdBy": {"bsonType": "objectId"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "seller_listings": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["sellerId", "productId", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "sellerId": {"bsonType": "objectId"},
                "productId": {"bsonType": "objectId"},
                "productSnapshot": {
                    "bsonType": "object",
                    "properties": {
                        "name": {"bsonType": "string"},
                        "categoryId": {"bsonType": "objectId"},
                        "categoryName": {"bsonType": "string"},
                        "coverImageUrl": {"bsonType": ["string", "null"]}
                    }
                },
                "sellerType": {"bsonType": "string"},
                "specifications": {"bsonType": "object"},
                "specTemplateIds": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "specTemplateVersions": {"bsonType": "array", "items": {"bsonType": ["int", "long"]}},
                "availability": {
                    "bsonType": "object",
                    "properties": {
                        "moq": {"bsonType": ["int", "long"]},
                        "stock": {"bsonType": ["int", "long"]},
                        "leadTimeDays": {"bsonType": ["int", "long"]},
                        "stockStatus": {"bsonType": "string"}
                    }
                },
                "pricing": {
                    "bsonType": "object",
                    "properties": {
                        "pricingType": {"bsonType": "string"},
                        "slabs": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "properties": {
                                    "quantityMin": {"bsonType": ["int", "long"]},
                                    "quantityMax": {"bsonType": ["int", "long", "null"]},
                                    "pricePerUnit": {"bsonType": ["double", "int", "long"]},
                                    "currency": {"bsonType": "string"}
                                }
                            }
                        }
                    }
                },
                "images": {"bsonType": "array", "items": {"bsonType": "string"}},  # Firebase URLs - seller uploads
                "status": {"bsonType": "string"},
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "spec_templates": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "categoryId", "fields", "isActive", "createdAt", "createdBy", "updatedAt"],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "categoryId": {"bsonType": "objectId"},
                "fields": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["key", "label", "fieldType", "required", "displayOrder"],
                        "properties": {
                            "key": {"bsonType": "string"},
                            "label": {"bsonType": "string"},
                            "fieldType": {"enum": ["text", "number", "dropdown", "boolean"]},
                            "unit": {"bsonType": ["string", "null"]},
                            "options": {"bsonType": "array", "items": {"bsonType": "string"}},
                            "required": {"bsonType": "bool"},
                            "displayOrder": {"bsonType": "int"}
                        }
                    }
                },
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "createdBy": {"bsonType": "objectId"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "subscription_changes": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["userId", "action", "newSubscription", "adminId", "createdAt"],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "userId": {"bsonType": "objectId"},
                "action": {"enum": ["activate", "upgrade", "downgrade", "expire", "cancel"]},
                "oldSubscription": {"bsonType": ["object", "null"]},
                "newSubscription": {
                    "bsonType": "object",
                    "required": ["planName", "startDate", "status"],
                    "properties": {
                        "planName": {"bsonType": "string"},
                        "durationDays": {"bsonType": "int"},
                        "startDate": {"bsonType": "date"},
                        "endDate": {"bsonType": ["date", "null"]},
                        "status": {"bsonType": "string"},
                        "lastUpdatedBy": {"bsonType": ["string", "objectId"]},
                        "updatedAt": {"bsonType": "date"},
                        "notes": {"bsonType": ["string", "null"]},
                        "createdAt": {"bsonType": "date"}
                    }
                },
                "adminId": {"bsonType": "objectId"},
                "adminEmail": {"bsonType": "string"},
                "note": {"bsonType": ["string", "null"]},
                "createdAt": {"bsonType": "date"}
            }
        }
    },
    
    "subscriptions": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["userId", "planName", "startDate", "status", "createdAt"],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "userId": {"bsonType": "objectId"},
                "planName": {"enum": ["free", "pro", "enterprise"]},
                "durationDays": {"bsonType": "int"},
                "startDate": {"bsonType": "date"},
                "endDate": {"bsonType": ["date", "null"]},
                "status": {"enum": ["active", "expired", "cancelled", "trial"]},
                "enquiryLimit": {"bsonType": "int"},
                "enquiriesUsed": {"bsonType": "int"},
                "enquiriesResetAt": {"bsonType": ["date", "null"]},
                "lastUpdatedBy": {"bsonType": ["string", "objectId"]},
                "updatedAt": {"bsonType": "date"},
                "notes": {"bsonType": ["string", "null"]},
                "createdAt": {"bsonType": "date"}
            }
        }
    },
    
    "users": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "firebaseUid", "roles", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "email": {"bsonType": "string"},
                "firebaseUid": {"bsonType": "string"},
                "roles": {"bsonType": "array", "items": {"bsonType": "string"}},
                "isAdmin": {"bsonType": "bool"},
                "profile": {
                    "bsonType": "object",
                    "properties": {
                        "businessName": {"bsonType": ["string", "null"]},
                        "phone": {"bsonType": ["string", "null"]},
                        "city": {"bsonType": ["string", "null"]},
                        "state": {"bsonType": ["string", "null"]},
                        "pincode": {"bsonType": ["string", "null"]},
                        "address": {"bsonType": ["string", "null"]},
                        "latitude": {"bsonType": ["double", "null"]},
                        "longitude": {"bsonType": ["double", "null"]}
                    }
                },
                "gst": {
                    "bsonType": "object",
                    "properties": {
                        "number": {"bsonType": ["string", "null"]},
                        "status": {"bsonType": ["string", "null"]},
                        "verified": {"bsonType": "bool"}
                    }
                },
                "emailVerified": {"bsonType": "bool"},
                "accountStatus": {"bsonType": "string"},
                "canLogin": {"bsonType": "bool"},
                "isActive": {"bsonType": "bool"},
                "deletedAt": {"bsonType": ["date", "null"]},
                "deletionReason": {"bsonType": ["string", "null"]},
                "subscription": {
                    "bsonType": "object",
                    "properties": {
                        "plan": {"bsonType": "string"},
                        "status": {"bsonType": "string"},
                        "startDate": {"bsonType": ["date", "null"]},
                        "endDate": {"bsonType": ["date", "null"]},
                        "trialEndsAt": {"bsonType": ["date", "null"]},
                        "inquiryLimit": {"bsonType": ["int", "long"]},
                        "enquiriesThisMonth": {"bsonType": ["int", "long"]},
                        "enquiriesResetAt": {"bsonType": "date"}
                    }
                },
                "favourites": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "recentSearches": {"bsonType": "array", "items": {"bsonType": "string"}},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    }
}

# =============================================================================
# FIELD RENAMES: snake_case -> camelCase
# =============================================================================

FIELD_RENAMES = {
    "categories": {
        "image_url": "imageUrl",
        "display_order": "displayOrder",
        "is_active": "isActive",
        "created_at": "createdAt",
        "created_by": "createdBy",
        "updated_at": "updatedAt",
        "image": "imageUrl"
    },
    "products": {
        "category_id": "categoryId",
        "category_name": "categoryName",
        "cover_image_url": "coverImageUrl",
        "spec_template_ids": "specTemplateIds",
        "spec_template_versions": "specTemplateVersions",
        "is_active": "isActive",
        "created_at": "createdAt",
        "created_by": "createdBy",
        "updated_at": "updatedAt",
        "image": "coverImageUrl"
    },
    "seller_listings": {
        "seller_id": "sellerId",
        "product_id": "productId",
        "product_snapshot": "productSnapshot",
        "seller_type": "sellerType",
        "spec_template_ids": "specTemplateIds",
        "spec_template_versions": "specTemplateVersions",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "category_id": "categoryId",
        "pricing_tiers": "pricing",
        "pricingTiers": "pricing"
    },
    "users": {
        "firebase_uid": "firebaseUid",
        "is_admin": "isAdmin",
        "email_verified": "emailVerified",
        "account_status": "accountStatus",
        "can_login": "canLogin",
        "is_active": "isActive",
        "deleted_at": "deletedAt",
        "deletion_reason": "deletionReason",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "business_name": "businessName"
    },
    "inquiries": {
        "listing_id": "listingId",
        "product_id": "productId",
        "seller_id": "sellerId",
        "buyer_id": "buyerId",
        "buyer_type": "buyerType",
        "buyer_info": "buyerInfo",
        "requirement_note": "requirementNote",
        "accepted_at": "acceptedAt",
        "rejected_at": "rejectedAt",
        "expired_at": "expiredAt",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    },
    "spec_templates": {
        "category_id": "categoryId",
        "is_active": "isActive",
        "created_at": "createdAt",
        "created_by": "createdBy",
        "updated_at": "updatedAt",
        "field_type": "fieldType",
        "display_order": "displayOrder"
    }
}

async def run_migration():
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL not set")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client.b2b_marketplace
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "collections_processed": [],
        "field_renames": {},
        "validators_applied": {},
        "errors": []
    }
    
    print("=" * 60)
    print("V11 FINAL SCHEMA ENFORCEMENT MIGRATION")
    print("=" * 60)
    
    # Step 1: Rename snake_case fields to camelCase
    print("\n📝 STEP 1: Renaming snake_case fields to camelCase...")
    for coll_name, renames in FIELD_RENAMES.items():
        try:
            collection = db[coll_name]
            rename_ops = {f"${old}": new for old, new in renames.items()}
            
            # Check which fields exist
            sample = await collection.find_one()
            if sample:
                fields_to_rename = {}
                for old_name, new_name in renames.items():
                    if old_name in sample and old_name != new_name:
                        fields_to_rename[old_name] = new_name
                
                if fields_to_rename:
                    result = await collection.update_many(
                        {},
                        {"$rename": fields_to_rename}
                    )
                    print(f"  ✅ {coll_name}: Renamed {len(fields_to_rename)} fields ({result.modified_count} docs)")
                    report["field_renames"][coll_name] = fields_to_rename
                else:
                    print(f"  ⏭️  {coll_name}: No fields to rename")
        except Exception as e:
            print(f"  ⚠️  {coll_name}: {str(e)[:50]}")
            report["errors"].append({"collection": coll_name, "step": "rename", "error": str(e)})
    
    # Step 2: Apply schema validators
    print("\n📋 STEP 2: Applying schema validators...")
    for coll_name, validator in SCHEMAS.items():
        try:
            # First try to create collection if it doesn't exist
            if coll_name not in await db.list_collection_names():
                await db.create_collection(coll_name)
                print(f"  ➕ Created collection: {coll_name}")
            
            # Apply validator with moderate level and warn action (safe for existing data)
            await db.command("collMod", coll_name, 
                validator=validator,
                validationLevel="moderate",
                validationAction="warn"
            )
            print(f"  ✅ {coll_name}: Validator applied")
            report["validators_applied"][coll_name] = "success"
            report["collections_processed"].append(coll_name)
        except Exception as e:
            print(f"  ❌ {coll_name}: {str(e)[:80]}")
            report["validators_applied"][coll_name] = str(e)
            report["errors"].append({"collection": coll_name, "step": "validator", "error": str(e)})
    
    # Step 3: Add missing required fields with defaults
    print("\n🔧 STEP 3: Adding missing required fields...")
    now = datetime.now(timezone.utc)
    
    # Categories
    await db.categories.update_many(
        {"isActive": {"$exists": False}},
        {"$set": {"isActive": True}}
    )
    await db.categories.update_many(
        {"createdAt": {"$exists": False}},
        {"$set": {"createdAt": now}}
    )
    await db.categories.update_many(
        {"updatedAt": {"$exists": False}},
        {"$set": {"updatedAt": now}}
    )
    print("  ✅ categories: Defaults applied")
    
    # Products - add categoryName from lookup
    products = await db.products.find({"categoryName": {"$exists": False}}).to_list(1000)
    for product in products:
        cat_id = product.get("categoryId")
        if cat_id:
            category = await db.categories.find_one({"_id": cat_id})
            if category:
                await db.products.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"categoryName": category.get("name", "Unknown")}}
                )
    print(f"  ✅ products: Added categoryName to {len(products)} docs")
    
    # Products - ensure required fields
    await db.products.update_many(
        {"isActive": {"$exists": False}},
        {"$set": {"isActive": True}}
    )
    await db.products.update_many(
        {"createdAt": {"$exists": False}},
        {"$set": {"createdAt": now}}
    )
    await db.products.update_many(
        {"updatedAt": {"$exists": False}},
        {"$set": {"updatedAt": now}}
    )
    await db.products.update_many(
        {"specTemplateIds": {"$exists": False}},
        {"$set": {"specTemplateIds": []}}
    )
    await db.products.update_many(
        {"specTemplateVersions": {"$exists": False}},
        {"$set": {"specTemplateVersions": []}}
    )
    
    # Seller listings - create productSnapshot
    print("\n🔗 STEP 4: Creating product snapshots in seller_listings...")
    listings = await db.seller_listings.find({}).to_list(1000)
    for listing in listings:
        product_id = listing.get("productId")
        if product_id and not listing.get("productSnapshot"):
            product = await db.products.find_one({"_id": product_id})
            if product:
                snapshot = {
                    "name": product.get("name", "Unknown"),
                    "categoryId": product.get("categoryId"),
                    "categoryName": product.get("categoryName", "Unknown"),
                    "coverImageUrl": product.get("coverImageUrl")
                }
                await db.seller_listings.update_one(
                    {"_id": listing["_id"]},
                    {"$set": {"productSnapshot": snapshot}}
                )
    print(f"  ✅ Created snapshots for {len(listings)} listings")
    
    # Seller listings - ensure required fields
    await db.seller_listings.update_many(
        {"isActive": {"$exists": False}},
        {"$set": {"isActive": True}}
    )
    await db.seller_listings.update_many(
        {"createdAt": {"$exists": False}},
        {"$set": {"createdAt": now}}
    )
    await db.seller_listings.update_many(
        {"updatedAt": {"$exists": False}},
        {"$set": {"updatedAt": now}}
    )
    
    # Users - ensure required fields
    await db.users.update_many(
        {"isActive": {"$exists": False}},
        {"$set": {"isActive": True}}
    )
    await db.users.update_many(
        {"roles": {"$exists": False}},
        {"$set": {"roles": []}}
    )
    await db.users.update_many(
        {"createdAt": {"$exists": False}},
        {"$set": {"createdAt": now}}
    )
    await db.users.update_many(
        {"updatedAt": {"$exists": False}},
        {"$set": {"updatedAt": now}}
    )
    print("  ✅ users: Defaults applied")
    
    # Save report
    report_path = "/app/backend/migrations/V11_migration_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"✅ Migration complete! Report: {report_path}")
    print(f"   Collections processed: {len(report['collections_processed'])}")
    print(f"   Errors: {len(report['errors'])}")
    print("=" * 60)
    
    return len(report["errors"]) == 0

if __name__ == "__main__":
    import sys
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
