"""
Migration V7: Final Enforcement of Canonical SSOT in seller_listings

This migration performs a final cleanup and strict verification:
1. Removes ANY remaining legacy fields (seller_id, product_id, category_id, product_name, category_name)
2. Validates ALL documents have ObjectId types for sellerId, productId, categoryId
3. Validates referential integrity (all IDs point to existing records)
4. Ensures required indexes exist (including unique constraint)
5. Fixes any string IDs that should be ObjectId

CRITICAL: This is a destructive migration. Backup before running in production.
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'midconnect').strip()

# Legacy fields that MUST NOT exist
LEGACY_FIELDS = [
    'seller_id',
    'product_id', 
    'category_id',
    'product_name',
    'category_name',
    'created_at',  # Should be createdAt
    'updated_at',  # Should be updatedAt
    'published_at',  # Should be publishedAt
]

# Canonical fields that MUST exist and MUST be ObjectId
CANONICAL_OBJECTID_FIELDS = ['sellerId', 'productId', 'categoryId']


def to_objectid(value, field_name):
    """Convert value to ObjectId, return None if impossible."""
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except InvalidId:
            print(f"  ⚠️  Cannot convert {field_name}='{value}' to ObjectId")
            return None
    return None


def run_migration():
    print("=" * 70)
    print("🚀 MIGRATION V7: Final SSOT Enforcement for seller_listings")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # ========== PHASE 1: Pre-migration Analysis ==========
    print("\n" + "=" * 70)
    print("📊 PHASE 1: Pre-migration Analysis")
    print("=" * 70)
    
    total_docs = db.seller_listings.count_documents({})
    print(f"Total seller_listings documents: {total_docs}")
    
    if total_docs == 0:
        print("✅ No documents to process. Migration complete.")
        return True
    
    # Count legacy fields
    for field in LEGACY_FIELDS:
        count = db.seller_listings.count_documents({field: {"$exists": True}})
        if count > 0:
            print(f"  ⚠️  {count} documents have legacy field: {field}")
    
    # ========== PHASE 2: Data Cleanup & Conversion ==========
    print("\n" + "=" * 70)
    print("🔧 PHASE 2: Data Cleanup & Type Enforcement")
    print("=" * 70)
    
    fixed_count = 0
    error_docs = []
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # --- Step 1: Convert/validate canonical ObjectId fields ---
        for field in CANONICAL_OBJECTID_FIELDS:
            current_value = doc.get(field)
            
            if current_value is None:
                # Try legacy field as fallback
                legacy_field = field[0].lower() + field[1:].replace('Id', '_id')  # sellerId -> seller_id
                legacy_value = doc.get(legacy_field)
                if legacy_value:
                    oid = to_objectid(legacy_value, field)
                    if oid:
                        updates["$set"][field] = oid
                        needs_update = True
                        print(f"  🔄 Doc {doc_id}: Set {field} from legacy {legacy_field}")
                else:
                    error_docs.append((doc_id, f"Missing required field: {field}"))
                    continue
            elif not isinstance(current_value, ObjectId):
                # Convert string to ObjectId
                oid = to_objectid(current_value, field)
                if oid:
                    updates["$set"][field] = oid
                    needs_update = True
                    print(f"  🔄 Doc {doc_id}: Converted {field} from string to ObjectId")
                else:
                    error_docs.append((doc_id, f"Invalid {field} value: {current_value}"))
        
        # --- Step 2: Remove ALL legacy fields ---
        for field in LEGACY_FIELDS:
            if field in doc:
                updates["$unset"][field] = ""
                needs_update = True
        
        # --- Step 3: Normalize status and is_active ---
        if doc.get('is_active') is None:
            updates["$set"]["is_active"] = doc.get('status') == 'active'
            needs_update = True
        
        # Convert string booleans to actual booleans
        is_active = doc.get('is_active')
        if isinstance(is_active, str):
            updates["$set"]["is_active"] = is_active.lower() == 'true'
            needs_update = True
        
        # --- Step 4: Apply updates ---
        if needs_update:
            # Clean empty $set/$unset
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                db.seller_listings.update_one({"_id": doc_id}, updates)
                fixed_count += 1
    
    print(f"\n📊 Fixed {fixed_count}/{total_docs} documents")
    
    if error_docs:
        print(f"\n⚠️  {len(error_docs)} documents have errors:")
        for doc_id, error in error_docs[:10]:
            print(f"  - {doc_id}: {error}")
    
    # ========== PHASE 3: Referential Integrity Check ==========
    print("\n" + "=" * 70)
    print("🔍 PHASE 3: Referential Integrity Validation")
    print("=" * 70)
    
    integrity_errors = []
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        
        # Validate sellerId references users collection
        seller_id = doc.get('sellerId')
        if seller_id:
            if not isinstance(seller_id, ObjectId):
                integrity_errors.append((doc_id, f"sellerId is not ObjectId: {type(seller_id).__name__}"))
            else:
                user = db.users.find_one({"_id": seller_id})
                if not user:
                    integrity_errors.append((doc_id, f"sellerId {seller_id} not found in users"))
        
        # Validate productId references products collection
        product_id = doc.get('productId')
        if product_id:
            if not isinstance(product_id, ObjectId):
                integrity_errors.append((doc_id, f"productId is not ObjectId: {type(product_id).__name__}"))
            else:
                product = db.products.find_one({"_id": product_id})
                if not product:
                    integrity_errors.append((doc_id, f"productId {product_id} not found in products"))
        
        # Validate categoryId references categories collection
        category_id = doc.get('categoryId')
        if category_id:
            if not isinstance(category_id, ObjectId):
                integrity_errors.append((doc_id, f"categoryId is not ObjectId: {type(category_id).__name__}"))
            else:
                category = db.categories.find_one({"_id": category_id})
                if not category:
                    integrity_errors.append((doc_id, f"categoryId {category_id} not found in categories"))
    
    if integrity_errors:
        print(f"⚠️  {len(integrity_errors)} referential integrity issues found:")
        for doc_id, error in integrity_errors[:20]:
            print(f"  - {doc_id}: {error}")
    else:
        print("✅ All references validated")
    
    # ========== PHASE 4: Index Enforcement ==========
    print("\n" + "=" * 70)
    print("📇 PHASE 4: Index Enforcement")
    print("=" * 70)
    
    required_indexes = {
        "sellerId_1": [("sellerId", 1)],
        "productId_1": [("productId", 1)],
        "categoryId_1": [("categoryId", 1)],
        "status_1": [("status", 1)],
        "is_active_1": [("is_active", 1)],
    }
    
    existing_indexes = {idx['name']: idx for idx in db.seller_listings.list_indexes()}
    
    for idx_name, idx_keys in required_indexes.items():
        if idx_name not in existing_indexes:
            try:
                db.seller_listings.create_index(idx_keys, name=idx_name)
                print(f"  ✅ Created index: {idx_name}")
            except Exception as e:
                print(f"  ⚠️  Index {idx_name} already exists with different name: {e}")
        else:
            print(f"  ⏭️  Index exists: {idx_name}")
    
    # Unique compound index
    unique_idx_name = "unique_seller_product"
    if unique_idx_name not in existing_indexes and "unique_product_seller" not in existing_indexes:
        try:
            db.seller_listings.create_index(
                [("sellerId", 1), ("productId", 1)],
                name=unique_idx_name,
                unique=True
            )
            print(f"  ✅ Created UNIQUE index: {unique_idx_name}")
        except Exception as e:
            print(f"  ⚠️  Failed to create unique index (possible duplicates): {e}")
    else:
        print(f"  ⏭️  Unique index exists")
    
    # ========== PHASE 5: Final Verification ==========
    print("\n" + "=" * 70)
    print("✅ PHASE 5: Final Verification")
    print("=" * 70)
    
    # Hard rule check: No legacy fields should exist
    legacy_count = db.seller_listings.count_documents({
        "$or": [
            {"seller_id": {"$exists": True}},
            {"product_id": {"$exists": True}},
            {"category_id": {"$exists": True}}
        ]
    })
    
    if legacy_count > 0:
        print(f"❌ FAIL: {legacy_count} documents still have legacy fields!")
        return False
    else:
        print("✅ No legacy fields exist (seller_id, product_id, category_id)")
    
    # Check all required fields are ObjectId
    bad_type_count = 0
    for doc in db.seller_listings.find():
        for field in CANONICAL_OBJECTID_FIELDS:
            val = doc.get(field)
            if val and not isinstance(val, ObjectId):
                bad_type_count += 1
    
    if bad_type_count > 0:
        print(f"❌ FAIL: {bad_type_count} field(s) are not ObjectId type!")
        return False
    else:
        print("✅ All canonical fields (sellerId, productId, categoryId) are ObjectId type")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("📋 MIGRATION V7 SUMMARY")
    print("=" * 70)
    print(f"  Total documents: {total_docs}")
    print(f"  Documents fixed: {fixed_count}")
    print(f"  Integrity errors: {len(integrity_errors)}")
    print(f"  Legacy fields remaining: {legacy_count}")
    print(f"  Status: {'✅ SUCCESS' if legacy_count == 0 and bad_type_count == 0 else '❌ FAILED'}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    return legacy_count == 0 and bad_type_count == 0


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
