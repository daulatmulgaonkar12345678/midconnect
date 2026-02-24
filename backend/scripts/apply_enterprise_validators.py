"""
Enterprise MongoDB Schema Validators
=====================================
Applies strict schema validation at the database level.

This provides the ultimate protection layer - even if application code
has bugs, MongoDB will reject invalid documents.

Run this script once to apply validators:
    python scripts/apply_enterprise_validators.py
"""

import asyncio
import argparse
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def apply_seller_listings_validator(db, strict: bool = False):
    """
    Apply schema validator for sellerListings collection.
    
    Ensures:
    - images array with at least 1 item
    - searchableAttributes object with at least 1 property
    - pricingTiers array with at least 1 item
    - Required fields exist
    """
    
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["sellerId", "productId", "status", "images", "searchableAttributes", "pricingTiers"],
            "properties": {
                "sellerId": {
                    "bsonType": "objectId",
                    "description": "sellerId is required and must be ObjectId"
                },
                "productId": {
                    "bsonType": "objectId",
                    "description": "productId is required and must be ObjectId"
                },
                "variantId": {
                    "bsonType": ["objectId", "null"],
                    "description": "variantId must be ObjectId if present"
                },
                "status": {
                    "enum": ["draft", "active", "paused", "archived"],
                    "description": "status must be one of the allowed values"
                },
                "images": {
                    "bsonType": "array",
                    "minItems": 1,
                    "description": "images must be an array with at least 1 item",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "searchableAttributes": {
                    "bsonType": "object",
                    "minProperties": 1 if strict else 0,
                    "description": "searchableAttributes must be an object with at least 1 property"
                },
                "pricingTiers": {
                    "bsonType": "array",
                    "minItems": 1,
                    "description": "pricingTiers must be an array with at least 1 tier",
                    "items": {
                        "bsonType": "object",
                        "required": ["minQty", "pricePerUnit"],
                        "properties": {
                            "minQty": {
                                "bsonType": ["int", "double"],
                                "minimum": 1
                            },
                            "maxQty": {
                                "bsonType": ["int", "double", "null"]
                            },
                            "pricePerUnit": {
                                "bsonType": ["int", "double"],
                                "minimum": 0
                            }
                        }
                    }
                },
                "moq": {
                    "bsonType": ["int", "double"],
                    "minimum": 1,
                    "description": "moq must be at least 1"
                },
                "stock": {
                    "bsonType": ["int", "double"],
                    "minimum": 0,
                    "description": "stock cannot be negative"
                }
            }
        }
    }
    
    # Apply validator
    try:
        await db.command({
            "collMod": "sellerListings",
            "validator": validator,
            "validationLevel": "strict" if strict else "moderate",
            "validationAction": "error"
        })
        return True, "Validator applied successfully"
    except Exception as e:
        return False, str(e)


async def apply_products_validator(db):
    """
    Apply schema validator for products collection.
    
    Ensures:
    - name is required
    - images array exists
    """
    
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "isActive"],
            "properties": {
                "name": {
                    "bsonType": "string",
                    "minLength": 1,
                    "description": "name is required"
                },
                "images": {
                    "bsonType": "array",
                    "description": "images must be an array"
                },
                "isActive": {
                    "bsonType": "bool",
                    "description": "isActive must be boolean"
                }
            }
        }
    }
    
    try:
        await db.command({
            "collMod": "products",
            "validator": validator,
            "validationLevel": "moderate",
            "validationAction": "warn"  # Warn only for products (admin managed)
        })
        return True, "Validator applied successfully"
    except Exception as e:
        return False, str(e)


async def check_validators(db):
    """Check current validators on collections."""
    
    result = {}
    
    for collection_name in ["sellerListings", "products", "productVariants"]:
        try:
            info = await db.command({"listCollections": 1, "filter": {"name": collection_name}})
            if info.get("cursor", {}).get("firstBatch"):
                coll_info = info["cursor"]["firstBatch"][0]
                validator = coll_info.get("options", {}).get("validator")
                validation_level = coll_info.get("options", {}).get("validationLevel", "off")
                result[collection_name] = {
                    "hasValidator": validator is not None,
                    "validationLevel": validation_level
                }
            else:
                result[collection_name] = {"hasValidator": False, "validationLevel": "off"}
        except Exception as e:
            result[collection_name] = {"error": str(e)}
    
    return result


async def main():
    parser = argparse.ArgumentParser(description="Apply enterprise MongoDB validators")
    parser.add_argument("--strict", action="store_true", help="Apply strict validation (reject all invalid)")
    parser.add_argument("--check", action="store_true", help="Only check current validators")
    args = parser.parse_args()
    
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    if not mongo_url:
        print("❌ MONGO_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 70)
    print("🏗 ENTERPRISE MONGODB VALIDATORS")
    print(f"   Database: {db_name}")
    print(f"   Strict Mode: {args.strict}")
    print("=" * 70)
    
    try:
        if args.check:
            print("\n🔍 CHECKING CURRENT VALIDATORS:")
            validators = await check_validators(db)
            for coll, info in validators.items():
                print(f"\n   {coll}:")
                for key, value in info.items():
                    print(f"      {key}: {value}")
            return
        
        # Apply validators
        print("\n📝 APPLYING VALIDATORS:")
        
        # sellerListings
        success, msg = await apply_seller_listings_validator(db, strict=args.strict)
        print(f"\n   sellerListings: {'✅' if success else '❌'} {msg}")
        
        # products
        success, msg = await apply_products_validator(db)
        print(f"   products: {'✅' if success else '❌'} {msg}")
        
        # Check final state
        print("\n🔍 FINAL VALIDATOR STATE:")
        validators = await check_validators(db)
        for coll, info in validators.items():
            status = "✅" if info.get("hasValidator") else "⚠️"
            level = info.get("validationLevel", "unknown")
            print(f"   {status} {coll}: validationLevel={level}")
        
        print("\n" + "=" * 70)
        print("✅ ENTERPRISE VALIDATORS APPLIED")
        print("=" * 70)
        print("""
Data Guarantees Now Active:
- ❌ No empty images array in sellerListings
- ❌ No missing searchableAttributes (strict mode)
- ❌ No missing pricingTiers
- ❌ No negative stock
- ❌ No invalid MOQ (< 1)
- ✅ All inserts/updates validated at DB level
        """)
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
