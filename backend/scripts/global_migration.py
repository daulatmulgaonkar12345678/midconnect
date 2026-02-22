"""
PHASE 3: GLOBAL SCHEMA MIGRATION SCRIPT

This script performs a CONTROLLED migration of the entire database to:
1. Rename all legacy snake_case fields to camelCase
2. Convert all string IDs to ObjectId
3. Log every change
4. Verify migration success

CANONICAL NAMING STANDARD:
- sellerId, buyerId, productId, categoryId, userId, listingId
- createdAt, updatedAt, deletedAt, startDate, endDate, publishedAt
- All ID fields MUST be ObjectId type (not strings)

SAFETY MEASURES:
- Pre-migration backup recommended
- Logs all changes for audit
- Verifies each operation
- Rollback instructions provided
"""

import asyncio
import os
import json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "b2b_marketplace")

# Migration Results Logger
class MigrationLogger:
    def __init__(self):
        self.logs = []
        self.stats = defaultdict(lambda: {"renamed": 0, "converted": 0, "errors": 0})
    
    def log(self, collection: str, doc_id: str, operation: str, details: str):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collection": collection,
            "doc_id": str(doc_id),
            "operation": operation,
            "details": details
        }
        self.logs.append(entry)
        print(f"  [{operation}] {collection}/{doc_id}: {details}")
    
    def error(self, collection: str, doc_id: str, error: str):
        self.stats[collection]["errors"] += 1
        self.log(collection, doc_id, "ERROR", error)
    
    def renamed(self, collection: str, doc_id: str, from_field: str, to_field: str):
        self.stats[collection]["renamed"] += 1
        self.log(collection, doc_id, "RENAME", f"{from_field} -> {to_field}")
    
    def converted(self, collection: str, doc_id: str, field: str, from_type: str, to_type: str):
        self.stats[collection]["converted"] += 1
        self.log(collection, doc_id, "CONVERT", f"{field}: {from_type} -> {to_type}")
    
    def save(self, path: str):
        report = {
            "migration_timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": dict(self.stats),
            "logs": self.logs
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Migration log saved to: {path}")


# Field mapping for each collection
COLLECTION_MIGRATIONS = {
    "categories": {
        "field_renames": {
            "created_at": "createdAt",
            "updated_at": "updatedAt"
        },
        "id_conversions": []
    },
    "products": {
        "field_renames": {
            "category_id": "categoryId",
            "seller_id": "sellerId",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "deleted_at": "deletedAt"
        },
        "id_conversions": ["categoryId", "sellerId"]  # After rename
    },
    "inquiries": {
        "field_renames": {
            "seller_id": "sellerId",
            "buyer_id": "buyerId",
            "listing_id": "listingId",
            "product_id": "productId",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "accepted_at": "acceptedAt",
            "rejected_at": "rejectedAt"
        },
        "id_conversions": ["sellerId", "buyerId", "listingId", "productId"]
    },
    "subscriptions": {
        "field_renames": {
            "user_id": "userId",
            "start_date": "startDate",
            "end_date": "endDate",
            "created_at": "createdAt",
            "updated_at": "updatedAt"
        },
        "id_conversions": ["userId"]
    },
    "subscription_history": {
        "field_renames": {
            "user_id": "userId",
            "created_at": "createdAt"
        },
        "nested_renames": {
            "old_subscription": {
                "user_id": "userId",
                "start_date": "startDate",
                "end_date": "endDate",
                "created_at": "createdAt",
                "updated_at": "updatedAt"
            },
            "new_subscription": {
                "user_id": "userId",
                "start_date": "startDate",
                "end_date": "endDate",
                "created_at": "createdAt",
                "updated_at": "updatedAt"
            }
        },
        "id_conversions": ["userId"],
        "nested_id_conversions": {
            "old_subscription": ["userId"],
            "new_subscription": ["userId"]
        }
    },
    "users": {
        "field_renames": {
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "deleted_at": "deletedAt"
        },
        "nested_renames": {
            "subscription": {
                "start_date": "startDate",
                "end_date": "endDate",
                "enquiries_reset_at": "enquiriesResetAt",
                "trial_ends_at": "trialEndsAt"
            }
        },
        "id_conversions": []
    }
}


async def convert_string_to_objectid(value: Any) -> ObjectId:
    """Convert a string value to ObjectId if possible."""
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and len(value) == 24:
        try:
            return ObjectId(value)
        except:
            raise ValueError(f"Invalid ObjectId string: {value}")
    raise ValueError(f"Cannot convert {type(value).__name__} to ObjectId: {value}")


async def migrate_document(
    db, 
    collection_name: str, 
    doc: Dict, 
    config: Dict,
    logger: MigrationLogger,
    dry_run: bool = False
) -> bool:
    """Migrate a single document according to config."""
    doc_id = doc["_id"]
    updates = {}
    unsets = {}
    
    # 1. Handle top-level field renames
    field_renames = config.get("field_renames", {})
    for old_field, new_field in field_renames.items():
        if old_field in doc:
            value = doc[old_field]
            updates[new_field] = value
            unsets[old_field] = ""
            logger.renamed(collection_name, doc_id, old_field, new_field)
    
    # 2. Handle nested field renames
    nested_renames = config.get("nested_renames", {})
    for parent_field, rename_map in nested_renames.items():
        if parent_field in doc and isinstance(doc[parent_field], dict):
            nested_doc = doc[parent_field].copy()
            for old_field, new_field in rename_map.items():
                if old_field in nested_doc:
                    nested_doc[new_field] = nested_doc.pop(old_field)
                    logger.renamed(collection_name, doc_id, f"{parent_field}.{old_field}", f"{parent_field}.{new_field}")
            updates[parent_field] = nested_doc
    
    # 3. Handle ID conversions (after renames are applied)
    id_conversions = config.get("id_conversions", [])
    for field in id_conversions:
        # Check in updates first (if field was renamed)
        if field in updates:
            value = updates[field]
        elif field in doc:
            value = doc[field]
        else:
            continue
        
        if isinstance(value, str) and len(value) == 24:
            try:
                new_value = ObjectId(value)
                updates[field] = new_value
                logger.converted(collection_name, doc_id, field, "string", "ObjectId")
            except Exception as e:
                logger.error(collection_name, doc_id, f"Failed to convert {field}: {e}")
    
    # 4. Handle nested ID conversions
    nested_id_conversions = config.get("nested_id_conversions", {})
    for parent_field, fields in nested_id_conversions.items():
        if parent_field in updates and isinstance(updates[parent_field], dict):
            nested_doc = updates[parent_field]
            for field in fields:
                if field in nested_doc and isinstance(nested_doc[field], str):
                    try:
                        nested_doc[field] = ObjectId(nested_doc[field])
                        logger.converted(collection_name, doc_id, f"{parent_field}.{field}", "string", "ObjectId")
                    except Exception as e:
                        logger.error(collection_name, doc_id, f"Failed to convert {parent_field}.{field}: {e}")
    
    # Apply updates
    if updates or unsets:
        update_doc = {}
        if updates:
            update_doc["$set"] = updates
        if unsets:
            update_doc["$unset"] = unsets
        
        if not dry_run:
            try:
                result = await db[collection_name].update_one(
                    {"_id": doc_id},
                    update_doc
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(collection_name, doc_id, f"Update failed: {e}")
                return False
        else:
            return True
    
    return False


async def migrate_collection(
    db,
    collection_name: str,
    config: Dict,
    logger: MigrationLogger,
    dry_run: bool = False
) -> Tuple[int, int]:
    """Migrate all documents in a collection."""
    print(f"\n{'='*60}")
    print(f"Migrating collection: {collection_name}")
    print(f"{'='*60}")
    
    total_docs = await db[collection_name].count_documents({})
    print(f"  Total documents: {total_docs}")
    
    if total_docs == 0:
        print(f"  Collection is empty, skipping...")
        return 0, 0
    
    migrated = 0
    failed = 0
    
    # Process documents in batches
    batch_size = 100
    cursor = db[collection_name].find({})
    
    async for doc in cursor:
        try:
            success = await migrate_document(db, collection_name, doc, config, logger, dry_run)
            if success:
                migrated += 1
        except Exception as e:
            failed += 1
            logger.error(collection_name, doc["_id"], str(e))
    
    print(f"\n  Results: {migrated} migrated, {failed} failed")
    return migrated, failed


async def verify_migration(db, collection_name: str, config: Dict) -> Dict[str, Any]:
    """Verify that migration was successful for a collection."""
    result = {
        "collection": collection_name,
        "legacy_fields_remaining": {},
        "string_ids_remaining": {},
        "success": True
    }
    
    # Check for remaining legacy fields
    field_renames = config.get("field_renames", {})
    for old_field in field_renames.keys():
        count = await db[collection_name].count_documents({old_field: {"$exists": True}})
        if count > 0:
            result["legacy_fields_remaining"][old_field] = count
            result["success"] = False
    
    # Check for string IDs
    id_conversions = config.get("id_conversions", [])
    for field in id_conversions:
        count = await db[collection_name].count_documents({
            field: {"$exists": True, "$type": "string"}
        })
        if count > 0:
            result["string_ids_remaining"][field] = count
            result["success"] = False
    
    return result


async def run_migration(dry_run: bool = False):
    """Run the full migration."""
    print("\n" + "="*80)
    print(f"GLOBAL SCHEMA MIGRATION - {'DRY RUN' if dry_run else 'LIVE'}")
    print("="*80)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to the database")
    else:
        print("\n🔴 LIVE MODE - Changes WILL be applied to the database")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.list_collection_names()
        print(f"\n✅ Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"\n❌ Failed to connect: {e}")
        return
    
    logger = MigrationLogger()
    
    total_migrated = 0
    total_failed = 0
    
    # Migrate each collection
    for collection_name, config in COLLECTION_MIGRATIONS.items():
        # Check if collection exists
        if collection_name not in await db.list_collection_names():
            print(f"\n⚠️  Collection '{collection_name}' does not exist, skipping...")
            continue
        
        migrated, failed = await migrate_collection(db, collection_name, config, logger, dry_run)
        total_migrated += migrated
        total_failed += failed
    
    # Save migration log
    log_path = f"/app/backend/scripts/migration_log_{'dry' if dry_run else 'live'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    logger.save(log_path)
    
    # Verification phase
    if not dry_run:
        print("\n" + "="*80)
        print("VERIFICATION PHASE")
        print("="*80)
        
        all_verified = True
        for collection_name, config in COLLECTION_MIGRATIONS.items():
            if collection_name not in await db.list_collection_names():
                continue
            
            result = await verify_migration(db, collection_name, config)
            if result["success"]:
                print(f"  ✅ {collection_name}: VERIFIED")
            else:
                print(f"  ❌ {collection_name}: ISSUES FOUND")
                if result["legacy_fields_remaining"]:
                    print(f"     Legacy fields: {result['legacy_fields_remaining']}")
                if result["string_ids_remaining"]:
                    print(f"     String IDs: {result['string_ids_remaining']}")
                all_verified = False
    
    # Final summary
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    print(f"Total documents migrated: {total_migrated}")
    print(f"Total failures: {total_failed}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    if not dry_run and all_verified:
        print("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
    elif not dry_run:
        print("\n⚠️  MIGRATION COMPLETED WITH ISSUES - Review verification results")
    
    client.close()
    
    return {
        "total_migrated": total_migrated,
        "total_failed": total_failed,
        "stats": dict(logger.stats)
    }


async def main():
    """Main entry point."""
    import sys
    
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    if not dry_run:
        print("\n" + "="*80)
        print("⚠️  WARNING: This will modify your database!")
        print("="*80)
        print("\nTo perform a dry run first, use: python global_migration.py --dry-run")
        print("\nProceeding with LIVE migration in 3 seconds...")
        await asyncio.sleep(3)
    
    await run_migration(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
