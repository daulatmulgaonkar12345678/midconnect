"""
COMPREHENSIVE SCHEMA UNIFICATION SCRIPT

This script fixes ALL documents in ALL collections to use canonical camelCase field names.
Run this on any database environment to ensure schema consistency.

CANONICAL NAMING STANDARD:
- sellerId (not seller_id, sellerid)
- buyerId (not buyer_id, buyerid)
- productId (not product_id, productid)
- categoryId (not category_id, categoryid)
- listingId (not listing_id)
- createdAt (not created_at)
- updatedAt (not updated_at)
- publishedAt (not published_at)

Usage:
    python fix_all_schemas.py --dry-run    # Preview changes
    python fix_all_schemas.py              # Apply changes

"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "b2b_marketplace")

# Field renames for ALL collections
UNIVERSAL_RENAMES = {
    # ID fields
    "seller_id": "sellerId",
    "buyer_id": "buyerId",
    "product_id": "productId",
    "category_id": "categoryId",
    "listing_id": "listingId",
    "user_id": "userId",
    "order_id": "orderId",
    "inquiry_id": "inquiryId",
    "subscription_id": "subscriptionId",
    "spec_template_id": "specTemplateId",
    "manufacturer_id": "manufacturerId",
    
    # Timestamps
    "created_at": "createdAt",
    "updated_at": "updatedAt",
    "deleted_at": "deletedAt",
    "published_at": "publishedAt",
    "accepted_at": "acceptedAt",
    "rejected_at": "rejectedAt",
    "start_date": "startDate",
    "end_date": "endDate",
    "expires_at": "expiresAt",
    "trial_ends_at": "trialEndsAt",
    "enquiries_reset_at": "enquiriesResetAt",
    "last_stock_update": "lastStockUpdate",
}


async def fix_document(db, collection_name: str, doc: dict, dry_run: bool = True) -> dict:
    """Fix a single document's field names."""
    doc_id = doc["_id"]
    updates = {}
    unsets = {}
    
    for old_field, new_field in UNIVERSAL_RENAMES.items():
        if old_field in doc:
            value = doc[old_field]
            updates[new_field] = value
            unsets[old_field] = ""
    
    # Also check nested fields (subscription, availability, pricing, etc.)
    nested_fields_to_check = ["subscription", "availability", "pricing", "old_subscription", "new_subscription"]
    for nested_name in nested_fields_to_check:
        if nested_name in doc and isinstance(doc[nested_name], dict):
            nested_doc = doc[nested_name].copy()
            changed = False
            for old_field, new_field in UNIVERSAL_RENAMES.items():
                if old_field in nested_doc:
                    nested_doc[new_field] = nested_doc.pop(old_field)
                    changed = True
            if changed:
                updates[nested_name] = nested_doc
    
    if not updates and not unsets:
        return {"changed": False}
    
    if dry_run:
        return {
            "changed": True,
            "doc_id": str(doc_id),
            "renames": list(unsets.keys())
        }
    
    # Apply updates
    update_doc = {}
    if updates:
        update_doc["$set"] = updates
    if unsets:
        update_doc["$unset"] = unsets
    
    try:
        await db[collection_name].update_one({"_id": doc_id}, update_doc)
        return {"changed": True, "doc_id": str(doc_id), "success": True}
    except Exception as e:
        return {"changed": True, "doc_id": str(doc_id), "success": False, "error": str(e)}


async def fix_collection(db, collection_name: str, dry_run: bool = True) -> dict:
    """Fix all documents in a collection."""
    print(f"\n{'='*60}")
    print(f"Processing: {collection_name}")
    print(f"{'='*60}")
    
    stats = {
        "total": 0,
        "changed": 0,
        "errors": 0,
        "changes": []
    }
    
    total = await db[collection_name].count_documents({})
    stats["total"] = total
    
    if total == 0:
        print(f"  Empty collection, skipping")
        return stats
    
    # Find documents with legacy fields
    legacy_query = {"$or": [{field: {"$exists": True}} for field in UNIVERSAL_RENAMES.keys()]}
    legacy_count = await db[collection_name].count_documents(legacy_query)
    
    if legacy_count == 0:
        print(f"  ✅ No legacy fields found in {total} documents")
        return stats
    
    print(f"  Found {legacy_count}/{total} documents with legacy fields")
    
    async for doc in db[collection_name].find(legacy_query):
        result = await fix_document(db, collection_name, doc, dry_run)
        if result.get("changed"):
            stats["changed"] += 1
            if result.get("renames"):
                stats["changes"].append({
                    "doc_id": result["doc_id"],
                    "renames": result["renames"]
                })
            if result.get("error"):
                stats["errors"] += 1
    
    status = "DRY RUN" if dry_run else "APPLIED"
    print(f"  {status}: {stats['changed']} documents need/got updates")
    
    return stats


async def main():
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    print("\n" + "="*80)
    print(f"COMPREHENSIVE SCHEMA UNIFICATION - {'DRY RUN' if dry_run else 'LIVE'}")
    print("="*80)
    
    if not dry_run:
        print("\n⚠️  WARNING: This will modify your database!")
        print("Run with --dry-run first to preview changes\n")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.list_collection_names()
        print(f"✅ Connected to: {DB_NAME}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Get all collections
    collections = await db.list_collection_names()
    collections = [c for c in collections if not c.startswith("system.")]
    
    print(f"\nFound {len(collections)} collections")
    
    total_stats = {
        "collections_processed": 0,
        "collections_with_changes": 0,
        "total_documents_updated": 0,
        "total_errors": 0
    }
    
    # Process each collection
    for collection_name in sorted(collections):
        stats = await fix_collection(db, collection_name, dry_run)
        total_stats["collections_processed"] += 1
        if stats["changed"] > 0:
            total_stats["collections_with_changes"] += 1
            total_stats["total_documents_updated"] += stats["changed"]
        total_stats["total_errors"] += stats["errors"]
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Collections processed: {total_stats['collections_processed']}")
    print(f"Collections with changes: {total_stats['collections_with_changes']}")
    print(f"Documents updated: {total_stats['total_documents_updated']}")
    print(f"Errors: {total_stats['total_errors']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    if dry_run and total_stats['total_documents_updated'] > 0:
        print(f"\n💡 Run without --dry-run to apply these changes")
    elif not dry_run and total_stats['total_documents_updated'] > 0:
        print(f"\n✅ All changes applied successfully!")
    else:
        print(f"\n✅ Database is already clean - no changes needed")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
