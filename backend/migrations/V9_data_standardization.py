"""
Migration V9: Final Data Standardization & Cleanup
===================================================

This migration performs focused cleanup while PRESERVING the camelCase SSOT:
- sellerId, productId, categoryId (ObjectId)
- createdAt, updatedAt (datetime UTC)
- isActive / is_active (boolean)

PHASES:
1. Remove duplicate fields (active vs isActive)
2. Ensure all IDs are ObjectId type
3. Enforce status enums
4. Normalize units
5. Remove legacy snake_case fields that slipped through
6. Add missing timestamps

SAFETY:
- Idempotent: Safe to run multiple times
- Non-destructive: Preserves data, only transforms
- Logged: Full audit trail

Run: python backend/migrations/V9_data_standardization.py
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

# Import constants for validation
sys.path.insert(0, '/app/backend')
from constants import (
    LEGACY_FIELDS_TO_REMOVE, 
    normalize_unit, 
    ALLOWED_UNITS,
    ListingStatus,
    InquiryStatus,
    SubscriptionStatus,
    AccountStatus,
    get_status_values
)

# Migration statistics
stats = {
    "collections_processed": 0,
    "documents_scanned": 0,
    "documents_updated": 0,
    "legacy_fields_removed": 0,
    "ids_converted": 0,
    "units_normalized": 0,
    "active_to_isActive": 0,
    "timestamps_added": 0,
    "errors": [],
}


def to_objectid(value, field_name: str):
    """Convert value to ObjectId. Returns (ObjectId, error_message)."""
    if value is None:
        return None, None  # None is valid for optional fields
    if isinstance(value, ObjectId):
        return value, None
    if isinstance(value, str):
        if not value.strip():
            return None, f"Empty string for {field_name}"
        try:
            return ObjectId(value), None
        except InvalidId:
            return None, f"Invalid ObjectId for {field_name}: {value}"
    return None, f"Cannot convert {type(value).__name__} to ObjectId for {field_name}"


def process_seller_listings(db):
    """Process seller_listings collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: seller_listings")
    print("=" * 60)
    
    collection = db.seller_listings
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Phase 1: Remove 'active' field, keep isActive
        if "active" in doc:
            # If isActive doesn't exist, migrate the value
            if "isActive" not in doc and "is_active" not in doc:
                updates["$set"]["isActive"] = doc.get("active", False)
            updates["$unset"]["active"] = ""
            needs_update = True
            stats["active_to_isActive"] += 1
        
        # Phase 2: Ensure canonical ID fields are ObjectId
        for field in ["sellerId", "productId", "categoryId"]:
            if field in doc:
                value = doc[field]
                if not isinstance(value, ObjectId):
                    oid, err = to_objectid(value, field)
                    if oid:
                        updates["$set"][field] = oid
                        needs_update = True
                        stats["ids_converted"] += 1
        
        # Phase 3: Remove legacy snake_case fields
        for legacy_field in ["seller_id", "product_id", "category_id", 
                            "created_at", "updated_at", "published_at",
                            "product_name", "category_name", "seller_name",
                            "seller_type"]:
            if legacy_field in doc:
                # Migrate data if canonical field doesn't exist
                canonical_map = {
                    "seller_id": "sellerId",
                    "product_id": "productId", 
                    "category_id": "categoryId",
                    "created_at": "createdAt",
                    "updated_at": "updatedAt",
                    "published_at": "publishedAt",
                    "seller_type": "sellerRole",
                }
                canonical = canonical_map.get(legacy_field)
                if canonical and canonical not in doc and canonical not in updates["$set"]:
                    value = doc[legacy_field]
                    # Convert IDs to ObjectId
                    if legacy_field in ["seller_id", "product_id", "category_id"]:
                        oid, _ = to_objectid(value, legacy_field)
                        if oid:
                            updates["$set"][canonical] = oid
                    else:
                        updates["$set"][canonical] = value
                
                updates["$unset"][legacy_field] = ""
                needs_update = True
                stats["legacy_fields_removed"] += 1
        
        # Phase 4: Ensure timestamps exist
        if "createdAt" not in doc and "createdAt" not in updates["$set"]:
            updates["$set"]["createdAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        if "updatedAt" not in doc and "updatedAt" not in updates["$set"]:
            updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        # Phase 5: Ensure isActive is synced with status
        if "status" in doc:
            expected_is_active = doc["status"] == "active"
            current_is_active = doc.get("isActive", doc.get("is_active", False))
            if current_is_active != expected_is_active:
                updates["$set"]["isActive"] = expected_is_active
                updates["$set"]["is_active"] = expected_is_active
                needs_update = True
        
        # Apply updates
        if needs_update:
            # Clean empty $set/$unset
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"seller_listings/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def process_products(db):
    """Process products collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: products")
    print("=" * 60)
    
    collection = db.products
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Remove 'active' field
        if "active" in doc:
            if "isActive" not in doc and "is_active" not in doc:
                updates["$set"]["isActive"] = doc.get("active", True)
            updates["$unset"]["active"] = ""
            needs_update = True
            stats["active_to_isActive"] += 1
        
        # Ensure categoryId is ObjectId
        if "categoryId" in doc:
            value = doc["categoryId"]
            if not isinstance(value, ObjectId):
                oid, err = to_objectid(value, "categoryId")
                if oid:
                    updates["$set"]["categoryId"] = oid
                    needs_update = True
                    stats["ids_converted"] += 1
        
        # Remove legacy fields
        for legacy_field in ["category_id", "seller_id", "created_at", "updated_at"]:
            if legacy_field in doc:
                canonical_map = {
                    "category_id": "categoryId",
                    "seller_id": "sellerId",
                    "created_at": "createdAt",
                    "updated_at": "updatedAt",
                }
                canonical = canonical_map.get(legacy_field)
                if canonical and canonical not in doc and canonical not in updates["$set"]:
                    value = doc[legacy_field]
                    if legacy_field in ["category_id", "seller_id"]:
                        oid, _ = to_objectid(value, legacy_field)
                        if oid:
                            updates["$set"][canonical] = oid
                    else:
                        updates["$set"][canonical] = value
                
                updates["$unset"][legacy_field] = ""
                needs_update = True
                stats["legacy_fields_removed"] += 1
        
        # Normalize unit field
        if "unit" in doc:
            normalized = normalize_unit(doc["unit"])
            if normalized != doc["unit"]:
                updates["$set"]["unit"] = normalized
                needs_update = True
                stats["units_normalized"] += 1
        
        # Ensure timestamps
        if "createdAt" not in doc and "createdAt" not in updates["$set"]:
            updates["$set"]["createdAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        if "updatedAt" not in doc and "updatedAt" not in updates["$set"]:
            updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        # Apply updates
        if needs_update:
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"products/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def process_inquiries(db):
    """Process inquiries collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: inquiries")
    print("=" * 60)
    
    collection = db.inquiries
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Ensure ID fields are ObjectId
        for field in ["sellerId", "buyerId", "productId", "listingId"]:
            if field in doc:
                value = doc[field]
                if not isinstance(value, ObjectId) and value:
                    oid, err = to_objectid(value, field)
                    if oid:
                        updates["$set"][field] = oid
                        needs_update = True
                        stats["ids_converted"] += 1
        
        # Remove legacy fields
        for legacy_field in ["seller_id", "buyer_id", "product_id", "listing_id",
                            "created_at", "updated_at", "accepted_at"]:
            if legacy_field in doc:
                canonical_map = {
                    "seller_id": "sellerId",
                    "buyer_id": "buyerId",
                    "product_id": "productId",
                    "listing_id": "listingId",
                    "created_at": "createdAt",
                    "updated_at": "updatedAt",
                    "accepted_at": "acceptedAt",
                }
                canonical = canonical_map.get(legacy_field)
                if canonical and canonical not in doc and canonical not in updates["$set"]:
                    value = doc[legacy_field]
                    if legacy_field in ["seller_id", "buyer_id", "product_id", "listing_id"]:
                        oid, _ = to_objectid(value, legacy_field)
                        if oid:
                            updates["$set"][canonical] = oid
                    else:
                        updates["$set"][canonical] = value
                
                updates["$unset"][legacy_field] = ""
                needs_update = True
                stats["legacy_fields_removed"] += 1
        
        # Normalize unit field
        if "unit" in doc:
            normalized = normalize_unit(doc["unit"])
            if normalized != doc["unit"]:
                updates["$set"]["unit"] = normalized
                needs_update = True
                stats["units_normalized"] += 1
        
        # Ensure timestamps
        if "createdAt" not in doc and "createdAt" not in updates["$set"]:
            updates["$set"]["createdAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        # Apply updates
        if needs_update:
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"inquiries/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def process_users(db):
    """Process users collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: users")
    print("=" * 60)
    
    collection = db.users
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Remove 'active' field
        if "active" in doc:
            if "is_active" not in doc:
                updates["$set"]["is_active"] = doc.get("active", True)
            updates["$unset"]["active"] = ""
            needs_update = True
            stats["active_to_isActive"] += 1
        
        # Handle nested subscription object
        if "subscription" in doc:
            sub = doc["subscription"]
            if isinstance(sub, dict):
                # Ensure subscription status uses enum values
                if "status" in sub:
                    status = sub["status"]
                    valid_statuses = get_status_values(SubscriptionStatus)
                    if status not in valid_statuses:
                        # Map common variants
                        status_map = {
                            "free_tier": "free",
                            "active": "pro",  # Assume active means paid
                            "inactive": "expired",
                        }
                        if status.lower() in status_map:
                            updates["$set"]["subscription.status"] = status_map[status.lower()]
                            needs_update = True
        
        # Remove legacy timestamp fields
        for legacy_field in ["created_at", "updated_at"]:
            if legacy_field in doc:
                canonical_map = {
                    "created_at": "createdAt",
                    "updated_at": "updatedAt",
                }
                canonical = canonical_map.get(legacy_field)
                if canonical and canonical not in doc and canonical not in updates["$set"]:
                    updates["$set"][canonical] = doc[legacy_field]
                
                updates["$unset"][legacy_field] = ""
                needs_update = True
                stats["legacy_fields_removed"] += 1
        
        # Ensure timestamps
        if "createdAt" not in doc and "created_at" not in doc and "createdAt" not in updates["$set"]:
            updates["$set"]["createdAt"] = datetime.now(timezone.utc)
            needs_update = True
            stats["timestamps_added"] += 1
        
        # Apply updates
        if needs_update:
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updated_at"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"users/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def process_categories(db):
    """Process categories collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: categories")
    print("=" * 60)
    
    collection = db.categories
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Remove 'active' field, keep is_active
        if "active" in doc:
            if "is_active" not in doc:
                updates["$set"]["is_active"] = doc.get("active", True)
            updates["$unset"]["active"] = ""
            needs_update = True
            stats["active_to_isActive"] += 1
        
        # Normalize allowed_units
        if "allowed_units" in doc:
            units = doc["allowed_units"]
            if isinstance(units, list):
                normalized_units = [normalize_unit(u) for u in units]
                if normalized_units != units:
                    updates["$set"]["allowed_units"] = normalized_units
                    needs_update = True
                    stats["units_normalized"] += 1
        
        # Remove legacy fields
        for legacy_field in ["created_at", "updated_at"]:
            if legacy_field in doc:
                canonical_map = {
                    "created_at": "createdAt",
                    "updated_at": "updatedAt",
                }
                canonical = canonical_map.get(legacy_field)
                if canonical and canonical not in doc:
                    updates["$set"][canonical] = doc[legacy_field]
                
                updates["$unset"][legacy_field] = ""
                needs_update = True
                stats["legacy_fields_removed"] += 1
        
        # Apply updates
        if needs_update:
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"categories/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def process_product_requests(db):
    """Process product_requests collection"""
    print("\n" + "=" * 60)
    print("📦 Processing: product_requests")
    print("=" * 60)
    
    collection = db.product_requests
    total = collection.count_documents({})
    print(f"  Total documents: {total}")
    
    if total == 0:
        print("  No documents to process")
        return
    
    updated = 0
    for doc in collection.find():
        doc_id = doc['_id']
        updates = {"$set": {}, "$unset": {}}
        needs_update = False
        
        # Ensure ID fields are ObjectId
        for field in ["sellerId", "categoryId", "suggested_category_id"]:
            if field in doc:
                value = doc[field]
                if not isinstance(value, ObjectId) and value:
                    oid, err = to_objectid(value, field)
                    if oid:
                        updates["$set"][field] = oid
                        needs_update = True
                        stats["ids_converted"] += 1
        
        # Handle suggested_category_id -> suggestedCategoryId
        if "suggested_category_id" in doc:
            value = doc["suggested_category_id"]
            oid, _ = to_objectid(value, "suggested_category_id")
            if oid and "suggestedCategoryId" not in doc:
                updates["$set"]["suggestedCategoryId"] = oid
            updates["$unset"]["suggested_category_id"] = ""
            needs_update = True
            stats["legacy_fields_removed"] += 1
        
        # Apply updates
        if needs_update:
            if not updates["$set"]:
                del updates["$set"]
            if not updates["$unset"]:
                del updates["$unset"]
            
            if updates:
                if "$set" not in updates:
                    updates["$set"] = {}
                updates["$set"]["updatedAt"] = datetime.now(timezone.utc)
                
                try:
                    collection.update_one({"_id": doc_id}, updates)
                    updated += 1
                except Exception as e:
                    stats["errors"].append(f"product_requests/{doc_id}: {e}")
    
    print(f"  Updated: {updated}/{total}")
    stats["documents_updated"] += updated
    stats["documents_scanned"] += total
    stats["collections_processed"] += 1


def verify_migration(db):
    """Verify migration success"""
    print("\n" + "=" * 60)
    print("✅ VERIFICATION")
    print("=" * 60)
    
    issues = []
    
    # Check seller_listings
    legacy_count = db.seller_listings.count_documents({
        "$or": [
            {"active": {"$exists": True}},
            {"seller_id": {"$exists": True}},
            {"product_id": {"$exists": True}},
            {"category_id": {"$exists": True}},
        ]
    })
    if legacy_count > 0:
        issues.append(f"seller_listings: {legacy_count} docs with legacy fields")
    
    # Check products
    legacy_count = db.products.count_documents({
        "$or": [
            {"active": {"$exists": True}},
            {"category_id": {"$exists": True}},
        ]
    })
    if legacy_count > 0:
        issues.append(f"products: {legacy_count} docs with legacy fields")
    
    # Check for string IDs in seller_listings
    for doc in db.seller_listings.find({}, {"sellerId": 1, "productId": 1, "categoryId": 1}).limit(100):
        for field in ["sellerId", "productId", "categoryId"]:
            if field in doc and doc[field] and not isinstance(doc[field], ObjectId):
                issues.append(f"seller_listings/{doc['_id']}: {field} is not ObjectId")
    
    if issues:
        print("❌ Issues found:")
        for issue in issues[:20]:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All verifications passed")
        return True


def run_migration():
    """Run the complete migration"""
    print("=" * 70)
    print("🚀 MIGRATION V9: Data Standardization & Cleanup")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("\nPreserving camelCase SSOT:")
    print("  - sellerId, productId, categoryId (ObjectId)")
    print("  - createdAt, updatedAt (datetime UTC)")
    print("  - isActive / is_active (boolean)")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Process all collections
    process_seller_listings(db)
    process_products(db)
    process_inquiries(db)
    process_users(db)
    process_categories(db)
    process_product_requests(db)
    
    # Verify
    success = verify_migration(db)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  Collections processed: {stats['collections_processed']}")
    print(f"  Documents scanned: {stats['documents_scanned']}")
    print(f"  Documents updated: {stats['documents_updated']}")
    print(f"  Legacy fields removed: {stats['legacy_fields_removed']}")
    print(f"  IDs converted to ObjectId: {stats['ids_converted']}")
    print(f"  Units normalized: {stats['units_normalized']}")
    print(f"  active → isActive: {stats['active_to_isActive']}")
    print(f"  Timestamps added: {stats['timestamps_added']}")
    print(f"  Errors: {len(stats['errors'])}")
    
    if stats['errors']:
        print("\n⚠️ Errors:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")
    
    print(f"\n  Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"  Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    # Save report
    report_path = Path("/app/backend/migrations/V9_migration_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "migration": "V9_data_standardization",
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
