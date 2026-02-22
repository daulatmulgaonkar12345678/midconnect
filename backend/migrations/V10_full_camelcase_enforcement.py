"""
Migration V10: FULL CamelCase SSOT Enforcement
==============================================

This migration performs COMPLETE snake_case → camelCase conversion.

FIELD MAPPINGS:
- category_id → categoryId
- seller_id → sellerId  
- buyer_id → buyerId
- product_id → productId
- listing_id → listingId
- is_active → isActive
- created_at → createdAt
- updated_at → updatedAt
- deleted_at → deletedAt
- published_at → publishedAt
- created_by → createdBy
- deleted_by → deletedBy
- spec_template_id → specTemplateId
- spec_template_ids → specTemplateIds
- category_name → categoryName
- product_name → productName
- buyer_type → buyerType
- buyer_info → buyerInfo
- requirement_note → requirementNote

After migration:
- All documents use camelCase
- All snake_case fields removed
- isActive synced with status

Run: python backend/migrations/V10_full_camelcase_enforcement.py
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
import json
from pathlib import Path

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

# Field mapping: snake_case → camelCase
FIELD_MAP = {
    # ID fields
    "category_id": "categoryId",
    "seller_id": "sellerId",
    "buyer_id": "buyerId",
    "product_id": "productId",
    "listing_id": "listingId",
    "spec_template_id": "specTemplateId",
    "spec_template_ids": "specTemplateIds",
    "suggested_category_id": "suggestedCategoryId",
    
    # Boolean fields
    "is_active": "isActive",
    
    # Timestamp fields
    "created_at": "createdAt",
    "updated_at": "updatedAt",
    "deleted_at": "deletedAt",
    "published_at": "publishedAt",
    
    # User reference fields
    "created_by": "createdBy",
    "deleted_by": "deletedBy",
    "reviewed_by": "reviewedBy",
    
    # Name fields
    "category_name": "categoryName",
    "product_name": "productName",
    "seller_name": "sellerName",
    "business_name": "businessName",
    
    # Other fields
    "buyer_type": "buyerType",
    "buyer_info": "buyerInfo",
    "requirement_note": "requirementNote",
    "standard_parameters": "standardParameters",
    "spec_schema": "specSchema",
    "normalized_specs": "normalizedSpecs",
    "normalized_spec_hash": "normalizedSpecHash",
    "gst_status": "gstStatus",
    "seller_status": "sellerStatus",
    "account_status": "accountStatus",
}

# Fields to keep as snake_case (user collection legacy)
USER_LEGACY_KEEP = {
    "firebase_uid",  # Firebase convention
    "email_verified",  # Common convention
    "is_admin",  # Boolean - keep for clarity
    "is_seller",  # Boolean - keep for clarity
    "is_active",  # Will be renamed to isActive
}

# Migration statistics
stats = {
    "collections_processed": 0,
    "documents_scanned": 0,
    "documents_updated": 0,
    "fields_renamed": 0,
    "fields_removed": 0,
    "ids_converted": 0,
    "isActive_synced": 0,
    "errors": [],
}


def to_objectid(value, field_name: str):
    """Convert value to ObjectId if valid."""
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            return ObjectId(value)
        except InvalidId:
            return None  # Invalid, will be removed
    return None


def migrate_document(doc: dict, collection_name: str) -> tuple:
    """Migrate a single document. Returns (updates_dict, needs_update)."""
    updates = {"$set": {}, "$unset": {}}
    needs_update = False
    
    for snake_field, camel_field in FIELD_MAP.items():
        # Skip user legacy fields for users collection
        if collection_name == "users" and snake_field in USER_LEGACY_KEEP:
            continue
            
        if snake_field in doc:
            value = doc[snake_field]
            
            # If camelCase field doesn't exist, migrate the value
            if camel_field not in doc and camel_field not in updates["$set"]:
                # Convert string IDs to ObjectId for ID fields
                if snake_field.endswith("_id") and not snake_field.endswith("_ids"):
                    oid = to_objectid(value, snake_field)
                    if oid:
                        updates["$set"][camel_field] = oid
                        stats["ids_converted"] += 1
                    elif value:  # Non-empty but invalid
                        updates["$set"][camel_field] = value  # Keep as-is
                else:
                    updates["$set"][camel_field] = value
                    
                stats["fields_renamed"] += 1
            
            # Always remove snake_case field
            updates["$unset"][snake_field] = ""
            stats["fields_removed"] += 1
            needs_update = True
    
    # Special handling: sync isActive with status
    status = doc.get("status")
    if status:
        expected_is_active = status == "active"
        current_is_active = doc.get("isActive", doc.get("is_active", None))
        if current_is_active != expected_is_active:
            updates["$set"]["isActive"] = expected_is_active
            stats["isActive_synced"] += 1
            needs_update = True
    
    return updates, needs_update


def process_collection(db, collection_name: str):
    """Process a single collection."""
    print(f"\n{'=' * 60}")
    print(f"📦 Processing: {collection_name}")
    print("=" * 60)
    
    collection = db[collection_name]
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    if total == 0:
        print("  No documents to process")
        stats["collections_processed"] += 1
        return
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates, needs_update = migrate_document(doc, collection_name)
        
        if needs_update:
            # Clean empty $set/$unset
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                # Always update updatedAt
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"{collection_name}/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def verify_migration(db):
    """Verify no snake_case fields remain."""
    print("\n" + "=" * 60)
    print("✅ VERIFICATION")
    print("=" * 60)
    
    issues = []
    
    collections = ['products', 'seller_listings', 'inquiries', 'categories', 'users']
    
    for coll_name in collections:
        coll = db[coll_name]
        
        # Check for remaining snake_case fields
        for snake_field in FIELD_MAP.keys():
            if coll_name == "users" and snake_field in USER_LEGACY_KEEP:
                continue
                
            count = coll.count_documents({snake_field: {"$exists": True}})
            if count > 0:
                issues.append(f"{coll_name}: {count} docs still have '{snake_field}'")
    
    if issues:
        print("❌ Issues found:")
        for issue in issues[:20]:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All snake_case fields removed")
        return True


def run_migration():
    """Run the complete migration."""
    print("=" * 70)
    print("🚀 MIGRATION V10: Full CamelCase SSOT Enforcement")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("\nThis migration will:")
    print("  - Convert ALL snake_case fields to camelCase")
    print("  - Convert string IDs to ObjectId")
    print("  - Sync isActive with status field")
    print("  - Remove duplicate snake_case fields")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Process all collections
    for coll_name in ['products', 'seller_listings', 'inquiries', 'categories', 'users', 'product_requests', 'spec_templates']:
        if coll_name in db.list_collection_names():
            process_collection(db, coll_name)
    
    # Verify
    success = verify_migration(db)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  Collections processed: {stats['collections_processed']}")
    print(f"  Documents scanned: {stats['documents_scanned']}")
    print(f"  Documents updated: {stats['documents_updated']}")
    print(f"  Fields renamed: {stats['fields_renamed']}")
    print(f"  Fields removed: {stats['fields_removed']}")
    print(f"  IDs converted to ObjectId: {stats['ids_converted']}")
    print(f"  isActive synced: {stats['isActive_synced']}")
    print(f"  Errors: {len(stats['errors'])}")
    
    if stats['errors']:
        print("\n⚠️ Errors:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")
    
    print(f"\n  Status: {'✅ SUCCESS' if success else '❌ ISSUES FOUND'}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    # Save report
    report_path = Path("/app/backend/migrations/V10_migration_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "migration": "V10_full_camelcase_enforcement",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": DB_NAME,
            "success": success,
            "stats": stats,
        }, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")
    
    return success


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
