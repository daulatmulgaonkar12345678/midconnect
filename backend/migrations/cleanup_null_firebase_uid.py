"""
MongoDB Migration: Clean up null firebaseUid values
====================================================

This script safely removes firebaseUid field from documents where it is null.
This allows the unique partial index to work correctly.

Run: python -m migrations.cleanup_null_firebase_uid
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime, timezone

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "b2b_marketplace")

def run_migration():
    print("=" * 60)
    print("Migration: Clean up null firebaseUid values")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Database: {DB_NAME}")
    print()
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Step 1: Find documents with firebaseUid = null
    print("Step 1: Finding documents with firebaseUid = null...")
    null_docs = list(db.users.find(
        {"firebaseUid": None},
        {"_id": 1, "email": 1, "firebaseUid": 1, "createdAt": 1}
    ))
    
    print(f"Found {len(null_docs)} documents with firebaseUid = null")
    
    if len(null_docs) == 0:
        print("✅ No documents to clean up. Migration complete.")
        return
    
    # Step 2: Log affected documents for audit
    print("\nAffected documents (preview):")
    print("-" * 40)
    for doc in null_docs[:10]:  # Show first 10
        print(f"  _id: {doc['_id']}")
        print(f"  email: {doc.get('email', 'N/A')}")
        print(f"  firebaseUid: {doc.get('firebaseUid')}")
        print(f"  createdAt: {doc.get('createdAt', 'N/A')}")
        print()
    
    if len(null_docs) > 10:
        print(f"  ... and {len(null_docs) - 10} more documents")
    
    # Step 3: Perform the cleanup using $unset
    print("\nStep 2: Removing firebaseUid field from null records...")
    print("Command: db.users.updateMany({ firebaseUid: null }, { $unset: { firebaseUid: '' } })")
    
    result = db.users.update_many(
        {"firebaseUid": None},
        {"$unset": {"firebaseUid": ""}}
    )
    
    print(f"\n✅ Migration complete!")
    print(f"   Matched: {result.matched_count}")
    print(f"   Modified: {result.modified_count}")
    
    # Step 4: Verify cleanup
    print("\nStep 3: Verifying cleanup...")
    remaining = db.users.count_documents({"firebaseUid": None})
    print(f"Documents with firebaseUid = null remaining: {remaining}")
    
    if remaining == 0:
        print("✅ All null firebaseUid values have been cleaned up!")
    else:
        print("⚠️ Some documents still have firebaseUid = null")
    
    # Step 5: Show index status
    print("\nStep 4: Checking indexes on users collection...")
    indexes = list(db.users.list_indexes())
    for idx in indexes:
        if 'firebaseUid' in str(idx.get('key', {})):
            print(f"  Index: {idx['name']}")
            print(f"  Key: {idx['key']}")
            print(f"  Unique: {idx.get('unique', False)}")
            print(f"  Partial: {idx.get('partialFilterExpression', 'None')}")
    
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    run_migration()
