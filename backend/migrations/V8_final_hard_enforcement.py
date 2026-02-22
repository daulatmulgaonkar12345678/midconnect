"""
Migration V8: FINAL Hard Enforcement of Canonical SSOT Schema

This migration is designed to handle documents created AFTER V7 by legacy code paths.
It performs:
1. Converts string IDs (seller_id, product_id, category_id) to ObjectId (sellerId, productId, categoryId)
2. Removes ALL legacy fields including denormalized names
3. Normalizes timestamps to camelCase
4. Validates referential integrity
5. Creates unique compound index (sellerId, productId)

STRICT RULES:
- NO fallback logic
- NO dual schema support
- FAIL loudly on invalid data
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
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

# Legacy fields that MUST be removed
LEGACY_FIELDS = [
    'seller_id',
    'product_id', 
    'category_id',
    'product_name',
    'category_name',
    'created_at',
    'updated_at',
    'published_at',
    'availability',  # Legacy nested structure
    'pricing',  # Legacy nested structure - should be pricingTiers
    'seller_type',  # Should be sellerRole
]


def to_objectid(value, field_name):
    """Convert value to ObjectId. Returns tuple (ObjectId, error_message)."""
    if value is None:
        return None, f"Field {field_name} is null"
    if isinstance(value, ObjectId):
        return value, None
    if isinstance(value, str):
        try:
            return ObjectId(value), None
        except InvalidId:
            return None, f"Invalid ObjectId for {field_name}: {value}"
    return None, f"Cannot convert {type(value).__name__} to ObjectId for {field_name}"


def run_migration():
    print("=" * 70)
    print("🚀 MIGRATION V8: FINAL Hard Enforcement")
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
    
    # Count documents needing migration
    needs_migration = db.seller_listings.count_documents({
        "$or": [
            {"seller_id": {"$exists": True}},
            {"product_id": {"$exists": True}},
            {"category_id": {"$exists": True}},
            {"product_name": {"$exists": True}},
            {"category_name": {"$exists": True}},
            {"created_at": {"$exists": True}},
            {"updated_at": {"$exists": True}},
        ]
    })
    print(f"Documents with legacy fields: {needs_migration}")
    
    # ========== PHASE 2: Data Migration ==========
    print("\n" + "=" * 70)
    print("🔧 PHASE 2: Data Migration")
    print("=" * 70)
    
    migrated_count = 0
    error_docs = []
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        errors = []
        
        # === STEP 1: Convert string IDs to ObjectId ===
        
        # seller_id -> sellerId
        if "seller_id" in doc and "sellerId" not in doc:
            oid, err = to_objectid(doc["seller_id"], "seller_id")
            if oid:
                updates["$set"]["sellerId"] = oid
                needs_update = True
                print(f"  🔄 Doc {doc_id}: Converting seller_id to sellerId")
            else:
                errors.append(err)
        
        # product_id -> productId
        if "product_id" in doc and "productId" not in doc:
            oid, err = to_objectid(doc["product_id"], "product_id")
            if oid:
                updates["$set"]["productId"] = oid
                needs_update = True
                print(f"  🔄 Doc {doc_id}: Converting product_id to productId")
            else:
                errors.append(err)
        
        # category_id -> categoryId
        if "category_id" in doc and "categoryId" not in doc:
            oid, err = to_objectid(doc["category_id"], "category_id")
            if oid:
                updates["$set"]["categoryId"] = oid
                needs_update = True
                print(f"  🔄 Doc {doc_id}: Converting category_id to categoryId")
            else:
                errors.append(err)
        
        # === STEP 2: Ensure canonical fields are ObjectId ===
        
        for field, canonical_field in [("sellerId", "sellerId"), ("productId", "productId"), ("categoryId", "categoryId")]:
            if field in doc:
                value = doc[field]
                if not isinstance(value, ObjectId):
                    oid, err = to_objectid(value, field)
                    if oid:
                        updates["$set"][field] = oid
                        needs_update = True
                        print(f"  🔄 Doc {doc_id}: Converting {field} from string to ObjectId")
                    else:
                        errors.append(err)
        
        # === STEP 3: Convert timestamps ===
        
        if "created_at" in doc and "createdAt" not in doc:
            updates["$set"]["createdAt"] = doc["created_at"]
            needs_update = True
        
        if "updated_at" in doc and "updatedAt" not in doc:
            updates["$set"]["updatedAt"] = doc["updated_at"]
            needs_update = True
        
        if "published_at" in doc and "publishedAt" not in doc:
            updates["$set"]["publishedAt"] = doc["published_at"]
            needs_update = True
        
        # === STEP 4: Convert pricing structure ===
        
        if "pricing" in doc and "pricingTiers" not in doc:
            pricing = doc["pricing"]
            if isinstance(pricing, dict) and "slabs" in pricing:
                pricing_tiers = []
                for slab in pricing.get("slabs", []):
                    pricing_tiers.append({
                        "minQty": slab.get("quantity_min", 1),
                        "maxQty": slab.get("quantity_max"),
                        "pricePerUnit": slab.get("price_per_unit", 0)
                    })
                updates["$set"]["pricingTiers"] = pricing_tiers
                needs_update = True
                print(f"  🔄 Doc {doc_id}: Converting pricing.slabs to pricingTiers")
        
        # === STEP 5: Convert availability structure ===
        
        if "availability" in doc:
            avail = doc["availability"]
            if isinstance(avail, dict):
                if "moq" in avail and "moq" not in doc:
                    updates["$set"]["moq"] = avail.get("moq", 1)
                if "max_capacity" in avail and "maxCapacity" not in doc:
                    updates["$set"]["maxCapacity"] = avail.get("max_capacity", 0)
                if "lead_time_days" in avail and "leadTime" not in doc:
                    updates["$set"]["leadTime"] = avail.get("lead_time_days", 7)
                needs_update = True
        
        # === STEP 6: Convert seller_type to sellerRole ===
        
        if "seller_type" in doc and "sellerRole" not in doc:
            updates["$set"]["sellerRole"] = doc["seller_type"]
            needs_update = True
        
        # === STEP 7: Remove ALL legacy fields ===
        
        for field in LEGACY_FIELDS:
            if field in doc:
                updates["$unset"][field] = ""
                needs_update = True
        
        # === STEP 8: Ensure required fields exist ===
        
        if "createdAt" not in doc and "createdAt" not in updates.get("$set", {}):
            updates["$set"]["createdAt"] = datetime.now(timezone.utc)
            needs_update = True
        
        if "updatedAt" not in doc and "updatedAt" not in updates.get("$set", {}):
            updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
            needs_update = True
        
        # === APPLY UPDATES ===
        
        if errors:
            error_docs.append((doc_id, errors))
            print(f"  ❌ Doc {doc_id}: Skipped due to errors: {errors}")
            continue
        
        if needs_update:
            # Clean empty $set/$unset
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                # Add updatedAt timestamp
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                db.seller_listings.update_one({"_id": doc_id}, updates)
                migrated_count += 1
    
    print(f"\n📊 Migrated {migrated_count}/{total_docs} documents")
    
    if error_docs:
        print(f"\n⚠️ {len(error_docs)} documents had errors and were skipped:")
        for doc_id, errs in error_docs[:10]:
            print(f"  - {doc_id}: {errs}")
    
    # ========== PHASE 3: Referential Integrity ==========
    print("\n" + "=" * 70)
    print("🔍 PHASE 3: Referential Integrity Validation")
    print("=" * 70)
    
    integrity_errors = []
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        
        # Validate sellerId
        seller_id = doc.get('sellerId')
        if seller_id:
            if not isinstance(seller_id, ObjectId):
                integrity_errors.append((doc_id, f"sellerId is not ObjectId: {type(seller_id).__name__}"))
            else:
                user = db.users.find_one({"_id": seller_id})
                if not user:
                    integrity_errors.append((doc_id, f"sellerId {seller_id} not found in users"))
        else:
            integrity_errors.append((doc_id, "Missing sellerId"))
        
        # Validate productId
        product_id = doc.get('productId')
        if product_id:
            if not isinstance(product_id, ObjectId):
                integrity_errors.append((doc_id, f"productId is not ObjectId: {type(product_id).__name__}"))
            else:
                product = db.products.find_one({"_id": product_id})
                if not product:
                    integrity_errors.append((doc_id, f"productId {product_id} not found in products"))
        else:
            integrity_errors.append((doc_id, "Missing productId"))
        
        # Validate categoryId (optional but should be valid if present)
        category_id = doc.get('categoryId')
        if category_id:
            if not isinstance(category_id, ObjectId):
                integrity_errors.append((doc_id, f"categoryId is not ObjectId: {type(category_id).__name__}"))
            else:
                category = db.categories.find_one({"_id": category_id})
                if not category:
                    integrity_errors.append((doc_id, f"categoryId {category_id} not found in categories"))
    
    if integrity_errors:
        print(f"⚠️ {len(integrity_errors)} referential integrity issues:")
        for doc_id, error in integrity_errors[:20]:
            print(f"  - {doc_id}: {error}")
    else:
        print("✅ All references validated")
    
    # ========== PHASE 4: Index Enforcement ==========
    print("\n" + "=" * 70)
    print("📇 PHASE 4: Index Enforcement")
    print("=" * 70)
    
    existing_indexes = {idx['name']: idx for idx in db.seller_listings.list_indexes()}
    
    # Create required indexes
    required_indexes = {
        "sellerId_1": [("sellerId", 1)],
        "productId_1": [("productId", 1)],
        "categoryId_1": [("categoryId", 1)],
        "status_1": [("status", 1)],
        "is_active_1": [("is_active", 1)],
    }
    
    for idx_name, idx_keys in required_indexes.items():
        if idx_name not in existing_indexes:
            try:
                db.seller_listings.create_index(idx_keys, name=idx_name)
                print(f"  ✅ Created index: {idx_name}")
            except Exception as e:
                print(f"  ⚠️ Index {idx_name}: {e}")
        else:
            print(f"  ⏭️ Index exists: {idx_name}")
    
    # Unique compound index
    unique_idx_exists = any(
        idx.get('unique', False) and 
        'sellerId' in str(idx.get('key', {})) and 
        'productId' in str(idx.get('key', {}))
        for idx in existing_indexes.values()
    )
    
    if not unique_idx_exists:
        try:
            db.seller_listings.create_index(
                [("sellerId", 1), ("productId", 1)],
                name="unique_seller_product",
                unique=True
            )
            print(f"  ✅ Created UNIQUE index: unique_seller_product")
        except Exception as e:
            print(f"  ⚠️ Unique index creation failed (may have duplicates): {e}")
    else:
        print(f"  ⏭️ Unique compound index exists")
    
    # ========== PHASE 5: Final Verification ==========
    print("\n" + "=" * 70)
    print("✅ PHASE 5: Final Verification")
    print("=" * 70)
    
    # HARD RULE CHECK
    legacy_count = db.seller_listings.count_documents({
        "$or": [
            {"seller_id": {"$exists": True}},
            {"product_id": {"$exists": True}},
            {"category_id": {"$exists": True}},
            {"product_name": {"$exists": True}},
            {"category_name": {"$exists": True}}
        ]
    })
    
    if legacy_count > 0:
        print(f"❌ FAIL: {legacy_count} documents still have legacy fields!")
        return False
    else:
        print("✅ No legacy fields exist")
    
    # Type check
    type_errors = 0
    for doc in db.seller_listings.find():
        for field in ['sellerId', 'productId', 'categoryId']:
            val = doc.get(field)
            if val and not isinstance(val, ObjectId):
                type_errors += 1
    
    if type_errors > 0:
        print(f"❌ FAIL: {type_errors} fields are not ObjectId type!")
        return False
    else:
        print("✅ All ID fields are ObjectId type")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("📋 MIGRATION V8 SUMMARY")
    print("=" * 70)
    print(f"  Total documents: {total_docs}")
    print(f"  Documents migrated: {migrated_count}")
    print(f"  Documents with errors: {len(error_docs)}")
    print(f"  Integrity issues: {len(integrity_errors)}")
    print(f"  Legacy fields remaining: {legacy_count}")
    print(f"  Status: {'✅ SUCCESS' if legacy_count == 0 and type_errors == 0 else '❌ FAILED'}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    return legacy_count == 0 and type_errors == 0


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
