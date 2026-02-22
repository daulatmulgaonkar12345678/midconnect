"""
Migration V6: Enforce Canonical SSOT & ObjectId Identity in seller_listings

This migration:
1. Converts legacy string IDs to ObjectId references
2. Removes denormalized name fields (product_name, category_name)
3. Ensures all foreign keys are ObjectId type
4. Adds required indexes
5. Validates referential integrity

CRITICAL: This is a P0 migration - run with caution on production data.
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

def validate_objectid(value, field_name, doc_id):
    """Validate and convert a value to ObjectId."""
    if value is None:
        return None, f"Field {field_name} is None in document {doc_id}"
    
    if isinstance(value, ObjectId):
        return value, None
    
    if isinstance(value, str):
        try:
            return ObjectId(value), None
        except InvalidId:
            return None, f"Invalid ObjectId string for {field_name}: {value} in document {doc_id}"
    
    return None, f"Unknown type for {field_name}: {type(value).__name__} in document {doc_id}"


def run_migration():
    print("=" * 70)
    print("🚀 MIGRATION V6: Enforce Canonical SSOT & ObjectId Identity")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # ========== PHASE 1: Pre-flight validation ==========
    print("\n" + "=" * 70)
    print("📋 PHASE 1: Pre-flight Validation")
    print("=" * 70)
    
    total_docs = db.seller_listings.count_documents({})
    print(f"Total seller_listings documents: {total_docs}")
    
    if total_docs == 0:
        print("✅ No documents to migrate")
        return True
    
    # Check for valid references
    errors = []
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        
        # Validate sellerId
        seller_id_raw = doc.get('sellerId') or doc.get('seller_id')
        if seller_id_raw:
            seller_oid, err = validate_objectid(seller_id_raw, 'sellerId', doc_id)
            if err:
                errors.append(err)
            elif seller_oid:
                # Check if user exists
                user = db.users.find_one({"_id": seller_oid})
                if not user:
                    errors.append(f"Seller {seller_oid} not found in users collection (doc: {doc_id})")
        else:
            errors.append(f"Missing sellerId in document {doc_id}")
        
        # Validate productId
        product_id_raw = doc.get('productId') or doc.get('product_id')
        if product_id_raw:
            product_oid, err = validate_objectid(product_id_raw, 'productId', doc_id)
            if err:
                errors.append(err)
            elif product_oid:
                # Check if product exists
                product = db.products.find_one({"_id": product_oid})
                if not product:
                    errors.append(f"Product {product_oid} not found in products collection (doc: {doc_id})")
        else:
            errors.append(f"Missing productId in document {doc_id}")
    
    if errors:
        print("\n❌ PRE-FLIGHT VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        print("\n⚠️  Migration aborted. Fix the above issues before retrying.")
        return False
    
    print("✅ Pre-flight validation passed")
    
    # ========== PHASE 2: Data Migration ==========
    print("\n" + "=" * 70)
    print("🔄 PHASE 2: Data Migration")
    print("=" * 70)
    
    migrated_count = 0
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # --- Convert sellerId ---
        seller_id_raw = doc.get('sellerId') or doc.get('seller_id')
        if seller_id_raw:
            seller_oid, _ = validate_objectid(seller_id_raw, 'sellerId', doc_id)
            if seller_oid and not isinstance(doc.get('sellerId'), ObjectId):
                updates["$set"]["sellerId"] = seller_oid
                needs_update = True
        
        # --- Convert productId ---
        product_id_raw = doc.get('productId') or doc.get('product_id')
        if product_id_raw:
            product_oid, _ = validate_objectid(product_id_raw, 'productId', doc_id)
            if product_oid and not isinstance(doc.get('productId'), ObjectId):
                updates["$set"]["productId"] = product_oid
                needs_update = True
        
        # --- Derive and set categoryId from product ---
        if product_oid:
            product = db.products.find_one({"_id": product_oid})
            if product and product.get('category_id'):
                cat_oid, _ = validate_objectid(product['category_id'], 'categoryId', doc_id)
                if cat_oid:
                    updates["$set"]["categoryId"] = cat_oid
                    needs_update = True
        
        # --- Remove legacy fields ---
        legacy_fields_to_remove = [
            'seller_id', 'product_id', 'category_id', 
            'product_name', 'category_name'
        ]
        for field in legacy_fields_to_remove:
            if field in doc:
                updates["$unset"][field] = ""
                needs_update = True
        
        # --- Normalize timestamps ---
        if 'created_at' in doc and 'createdAt' not in doc:
            updates["$set"]["createdAt"] = doc['created_at']
            updates["$unset"]["created_at"] = ""
            needs_update = True
        
        if 'updated_at' in doc and 'updatedAt' not in doc:
            updates["$set"]["updatedAt"] = doc['updated_at']
            updates["$unset"]["updated_at"] = ""
            needs_update = True
        
        if 'published_at' in doc and 'publishedAt' not in doc:
            updates["$set"]["publishedAt"] = doc['published_at']
            updates["$unset"]["published_at"] = ""
            needs_update = True
        
        # --- Ensure is_active is set ---
        if doc.get('is_active') is None:
            updates["$set"]["is_active"] = doc.get('status') == 'active'
            needs_update = True
        
        # --- Apply updates ---
        if needs_update:
            # Clean up empty $set/$unset
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                db.seller_listings.update_one({"_id": doc_id}, updates)
                migrated_count += 1
                print(f"  ✅ Migrated document {doc_id}")
    
    print(f"\n📊 Migrated {migrated_count}/{total_docs} documents")
    
    # ========== PHASE 3: Create Indexes ==========
    print("\n" + "=" * 70)
    print("📇 PHASE 3: Creating Mandatory Indexes")
    print("=" * 70)
    
    indexes_to_create = [
        ("sellerId_1", {"sellerId": 1}),
        ("productId_1", {"productId": 1}),
        ("categoryId_1", {"categoryId": 1}),
        ("status_1", {"status": 1}),
        ("is_active_1", {"is_active": 1}),
        ("sellerId_productId_unique", {"sellerId": 1, "productId": 1}),
    ]
    
    existing_indexes = {idx['name'] for idx in db.seller_listings.list_indexes()}
    
    for idx_name, idx_keys in indexes_to_create:
        if idx_name not in existing_indexes and idx_name != "sellerId_productId_unique":
            db.seller_listings.create_index(list(idx_keys.items()), name=idx_name)
            print(f"  ✅ Created index: {idx_name}")
        elif idx_name == "sellerId_productId_unique":
            # Check if unique index exists with different name
            if "unique_product_seller" not in existing_indexes:
                db.seller_listings.create_index(
                    list(idx_keys.items()), 
                    name=idx_name, 
                    unique=True
                )
                print(f"  ✅ Created unique index: {idx_name}")
            else:
                print(f"  ⏭️  Unique index already exists as: unique_product_seller")
        else:
            print(f"  ⏭️  Index already exists: {idx_name}")
    
    # ========== PHASE 4: Post-migration Verification ==========
    print("\n" + "=" * 70)
    print("🔍 PHASE 4: Post-migration Verification")
    print("=" * 70)
    
    verification_passed = True
    
    # Check all documents have required ObjectId fields
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        
        if not isinstance(doc.get('sellerId'), ObjectId):
            print(f"  ❌ Document {doc_id}: sellerId is not ObjectId")
            verification_passed = False
        
        if not isinstance(doc.get('productId'), ObjectId):
            print(f"  ❌ Document {doc_id}: productId is not ObjectId")
            verification_passed = False
        
        if not isinstance(doc.get('categoryId'), ObjectId):
            print(f"  ❌ Document {doc_id}: categoryId is not ObjectId")
            verification_passed = False
        
        # Check no legacy fields exist
        for field in legacy_fields_to_remove:
            if field in doc:
                print(f"  ❌ Document {doc_id}: Legacy field '{field}' still exists")
                verification_passed = False
    
    if verification_passed:
        print("  ✅ All documents pass verification")
    else:
        print("\n  ⚠️  Some documents failed verification")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("📋 MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  Documents processed: {total_docs}")
    print(f"  Documents migrated: {migrated_count}")
    print(f"  Verification: {'PASSED ✅' if verification_passed else 'FAILED ❌'}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    return verification_passed


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
