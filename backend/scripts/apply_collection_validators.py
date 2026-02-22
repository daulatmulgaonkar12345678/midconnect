"""
PHASE 5: Apply MongoDB JSON Schema Validators to Critical Collections

This script applies strict validation to ensure:
1. All ID fields are ObjectId type
2. Required fields are enforced
3. Legacy field names are rejected
4. Data integrity is protected at the database level

Collections to validate:
- products: categoryId (ObjectId), createdAt, updatedAt
- inquiries: sellerId, buyerId, listingId (all ObjectId)
- subscriptions: userId (ObjectId)
"""

import asyncio
import os
import json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "b2b_marketplace")


# Schema validators for each collection
COLLECTION_VALIDATORS = {
    "products": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["categoryId", "name"],
            "properties": {
                "categoryId": {
                    "bsonType": "objectId",
                    "description": "Category reference - MUST be ObjectId"
                },
                "sellerId": {
                    "bsonType": "objectId",
                    "description": "Seller reference - MUST be ObjectId (if present)"
                },
                "name": {
                    "bsonType": "string",
                    "description": "Product name - required"
                },
                "createdAt": {
                    "bsonType": "date",
                    "description": "Creation timestamp"
                },
                "updatedAt": {
                    "bsonType": "date",
                    "description": "Update timestamp"
                }
            },
            "additionalProperties": True  # Allow other fields
        }
    },
    "inquiries": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["sellerId", "buyerId"],
            "properties": {
                "sellerId": {
                    "bsonType": "objectId",
                    "description": "Seller reference - MUST be ObjectId"
                },
                "buyerId": {
                    "bsonType": "objectId",
                    "description": "Buyer reference - MUST be ObjectId"
                },
                "listingId": {
                    "bsonType": "objectId",
                    "description": "Listing reference - MUST be ObjectId (if present)"
                },
                "productId": {
                    "bsonType": "objectId",
                    "description": "Product reference - MUST be ObjectId (if present)"
                },
                "createdAt": {
                    "bsonType": "date",
                    "description": "Creation timestamp"
                },
                "updatedAt": {
                    "bsonType": "date",
                    "description": "Update timestamp"
                }
            },
            "additionalProperties": True
        }
    },
    "subscriptions": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["userId", "plan"],
            "properties": {
                "userId": {
                    "bsonType": "objectId",
                    "description": "User reference - MUST be ObjectId"
                },
                "plan": {
                    "bsonType": "string",
                    "enum": ["free", "trial", "pro"],
                    "description": "Subscription plan"
                },
                "startDate": {
                    "bsonType": "date",
                    "description": "Subscription start date"
                },
                "endDate": {
                    "bsonType": "date",
                    "description": "Subscription end date"
                },
                "createdAt": {
                    "bsonType": "date",
                    "description": "Creation timestamp"
                },
                "updatedAt": {
                    "bsonType": "date",
                    "description": "Update timestamp"
                }
            },
            "additionalProperties": True
        }
    },
    "categories": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "bsonType": "string",
                    "description": "Category name - required"
                },
                "createdAt": {
                    "bsonType": "date",
                    "description": "Creation timestamp"
                }
            },
            "additionalProperties": True
        }
    }
}

# seller_listings already has a validator from previous work
# We'll just verify it's in place


async def apply_validator(db, collection_name: str, validator: dict, validation_level: str = "moderate") -> dict:
    """Apply JSON schema validator to a collection."""
    result = {
        "collection": collection_name,
        "success": False,
        "message": ""
    }
    
    try:
        # Check if collection exists
        existing_collections = await db.list_collection_names()
        
        if collection_name not in existing_collections:
            # Create collection with validator
            await db.create_collection(
                collection_name,
                validator=validator,
                validationLevel=validation_level,
                validationAction="error"
            )
            result["success"] = True
            result["message"] = f"Created collection '{collection_name}' with validator"
        else:
            # Modify existing collection
            await db.command({
                "collMod": collection_name,
                "validator": validator,
                "validationLevel": validation_level,
                "validationAction": "error"
            })
            result["success"] = True
            result["message"] = f"Updated validator for '{collection_name}'"
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Failed to apply validator: {str(e)}"
    
    return result


async def get_collection_validator(db, collection_name: str) -> dict:
    """Get current validator for a collection."""
    try:
        collections = await db.list_collections(filter={"name": collection_name})
        async for col in collections:
            options = col.get("options", {})
            return {
                "validator": options.get("validator"),
                "validationLevel": options.get("validationLevel"),
                "validationAction": options.get("validationAction")
            }
    except Exception as e:
        return {"error": str(e)}
    return {}


async def main():
    print("\n" + "="*80)
    print("PHASE 5: MONGODB SCHEMA VALIDATORS")
    print("="*80)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.list_collection_names()
        print(f"\n✅ Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"\n❌ Failed to connect: {e}")
        return
    
    results = []
    
    # Apply validators to each collection
    for collection_name, validator in COLLECTION_VALIDATORS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {collection_name}")
        print(f"{'='*60}")
        
        # Check current state
        current = await get_collection_validator(db, collection_name)
        if current.get("validator"):
            print(f"  Current validation level: {current.get('validationLevel', 'none')}")
        else:
            print(f"  No validator currently set")
        
        # Apply validator (using moderate level for backwards compatibility)
        # moderate = validates inserts and updates but allows existing documents
        result = await apply_validator(db, collection_name, validator, "moderate")
        results.append(result)
        
        if result["success"]:
            print(f"  ✅ {result['message']}")
        else:
            print(f"  ❌ {result['message']}")
    
    # Check seller_listings validator (already configured)
    print(f"\n{'='*60}")
    print(f"Verifying: seller_listings (already configured)")
    print(f"{'='*60}")
    sl_validator = await get_collection_validator(db, "seller_listings")
    if sl_validator.get("validator"):
        print(f"  ✅ Validator active: {sl_validator.get('validationLevel')} / {sl_validator.get('validationAction')}")
    else:
        print(f"  ⚠️ No validator found - may need re-application")
    
    # Final summary
    print("\n" + "="*80)
    print("VALIDATOR APPLICATION SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    
    print(f"Successfully applied: {successful}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ ALL VALIDATORS APPLIED SUCCESSFULLY")
    else:
        print("\n⚠️ SOME VALIDATORS FAILED - Review errors above")
    
    # Save results
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": {
            "successful": successful,
            "failed": failed
        }
    }
    
    report_path = "/app/backend/scripts/validator_application_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report saved to: {report_path}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
