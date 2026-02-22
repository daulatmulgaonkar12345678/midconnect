"""
V2_global_objectid_migration.py
================================
Global Identity & SSOT Policy Enforcement Migration

This migration converts all string-based foreign keys to ObjectId across:
- inquiries: buyer_id, seller_id, listing_id, product_id
- subscriptions: user_id
- subscription_history: user_id, admin_id

IMPORTANT: Run this migration only once. It is idempotent but will log warnings
for documents that are already migrated.

Author: E1 Agent
Date: 2025-01-12
"""

import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

# Configuration
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "b2b_marketplace"


def is_valid_objectid_string(value):
    """Check if a value is a valid 24-char hex string that can become an ObjectId."""
    if not isinstance(value, str):
        return False
    if len(value) != 24:
        return False
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


def safe_to_objectid(value, field_name, doc_id):
    """
    Safely convert a value to ObjectId.
    Returns (ObjectId, True) on success, (original_value, False) on failure.
    """
    if isinstance(value, ObjectId):
        return value, False  # Already ObjectId, no change needed
    
    if value is None:
        return None, False  # None stays None
    
    if is_valid_objectid_string(value):
        return ObjectId(value), True  # Successfully converted
    
    print(f"  ⚠️  Cannot convert {field_name}='{value}' in doc {doc_id} (not a valid ObjectId string)")
    return value, False  # Return unchanged


def migrate_collection(db, collection_name, fields_to_convert):
    """
    Migrate a collection by converting specified fields from string to ObjectId.
    
    Args:
        db: MongoDB database instance
        collection_name: Name of the collection
        fields_to_convert: List of field names to convert
    
    Returns:
        dict with migration stats
    """
    collection = db[collection_name]
    total_docs = collection.count_documents({})
    
    print(f"\n{'='*60}")
    print(f"Migrating collection: {collection_name}")
    print(f"Total documents: {total_docs}")
    print(f"Fields to convert: {fields_to_convert}")
    print(f"{'='*60}")
    
    stats = {
        "total": total_docs,
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "fields_converted": {}
    }
    
    for field in fields_to_convert:
        stats["fields_converted"][field] = 0
    
    cursor = collection.find({})
    
    for doc in cursor:
        doc_id = doc["_id"]
        stats["processed"] += 1
        
        update_fields = {}
        changes_made = False
        
        for field in fields_to_convert:
            if field in doc:
                original_value = doc[field]
                converted_value, was_converted = safe_to_objectid(original_value, field, doc_id)
                
                if was_converted:
                    update_fields[field] = converted_value
                    changes_made = True
                    stats["fields_converted"][field] += 1
        
        if changes_made:
            # Add migration metadata
            update_fields["_migrated_at"] = datetime.now(timezone.utc)
            update_fields["_migration_version"] = "V2_global_objectid"
            
            try:
                result = collection.update_one(
                    {"_id": doc_id},
                    {"$set": update_fields}
                )
                if result.modified_count > 0:
                    stats["updated"] += 1
                    print(f"  ✅ Migrated doc {doc_id}: {list(update_fields.keys())}")
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ Error updating doc {doc_id}: {e}")
        else:
            stats["skipped"] += 1
    
    return stats


def verify_migration(db, collection_name, fields):
    """Verify that all documents have ObjectId types for specified fields."""
    collection = db[collection_name]
    
    print(f"\n--- Verification: {collection_name} ---")
    
    issues = []
    for field in fields:
        # Find documents where the field is a string (not ObjectId)
        string_type_query = {field: {"$type": "string"}}
        count = collection.count_documents(string_type_query)
        
        if count > 0:
            issues.append(f"  ❌ {field}: {count} documents still have string type")
        else:
            # Count documents with ObjectId type
            oid_count = collection.count_documents({field: {"$type": "objectId"}})
            null_count = collection.count_documents({field: None})
            print(f"  ✅ {field}: {oid_count} ObjectId, {null_count} null, 0 string")
    
    for issue in issues:
        print(issue)
    
    return len(issues) == 0


def main():
    """Run the global ObjectId migration."""
    print("\n" + "="*70)
    print("  GLOBAL IDENTITY & SSOT POLICY - ObjectId Migration V2")
    print("="*70)
    print(f"\nStarted at: {datetime.now(timezone.utc).isoformat()}")
    print(f"Database: {DB_NAME}")
    
    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Verify connection
    try:
        db.command('ping')
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Migration Plan (following user's prescribed order)
    migration_plan = [
        # Phase 2: Relational/Transactional Collections
        # Note: Phase 1 collections (users, products, categories, spec_templates) 
        # already have correct ObjectId types based on our audit
        
        ("inquiries", ["buyer_id", "seller_id", "listing_id", "product_id"]),
        ("subscriptions", ["user_id"]),
        ("subscription_history", ["user_id", "admin_id"]),
    ]
    
    all_stats = {}
    
    # Execute migrations
    for collection_name, fields in migration_plan:
        if collection_name in db.list_collection_names():
            stats = migrate_collection(db, collection_name, fields)
            all_stats[collection_name] = stats
        else:
            print(f"\n⚠️  Collection '{collection_name}' does not exist, skipping...")
    
    # Verification
    print("\n" + "="*70)
    print("  VERIFICATION")
    print("="*70)
    
    all_verified = True
    for collection_name, fields in migration_plan:
        if collection_name in db.list_collection_names():
            verified = verify_migration(db, collection_name, fields)
            if not verified:
                all_verified = False
    
    # Summary
    print("\n" + "="*70)
    print("  MIGRATION SUMMARY")
    print("="*70)
    
    for collection_name, stats in all_stats.items():
        print(f"\n{collection_name}:")
        print(f"  Total: {stats['total']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")
        for field, count in stats['fields_converted'].items():
            if count > 0:
                print(f"    - {field}: {count} converted")
    
    print(f"\n{'='*70}")
    if all_verified:
        print("✅ MIGRATION COMPLETE - All documents verified")
    else:
        print("⚠️  MIGRATION COMPLETE - Some verification issues found")
    print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*70}\n")
    
    client.close()


if __name__ == "__main__":
    main()
