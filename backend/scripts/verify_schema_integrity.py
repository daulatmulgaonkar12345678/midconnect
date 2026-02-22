"""
Schema Integrity Verification Script

This script performs a comprehensive integrity check on the seller_listings collection
to ensure it meets the canonical SSOT requirements.

Run this after any migration to verify data integrity.

PASS CRITERIA:
1. NO documents have legacy fields (seller_id, product_id, category_id)
2. ALL documents have sellerId, productId, categoryId as ObjectId
3. ALL foreign key references point to existing documents
4. Required indexes exist including unique constraint

Usage:
    python verify_schema_integrity.py
"""

import os
import sys
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()


def verify_schema_integrity():
    """
    Comprehensive schema integrity verification.
    Returns: (passed: bool, report: dict)
    """
    print("=" * 70)
    print("🔍 SCHEMA INTEGRITY VERIFICATION")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": DB_NAME,
        "checks": {},
        "passed": True,
        "critical_failures": []
    }
    
    # ========== CHECK 1: Legacy Field Detection ==========
    print("\n📋 CHECK 1: Legacy Field Detection")
    print("-" * 40)
    
    legacy_fields = ['seller_id', 'product_id', 'category_id', 'product_name', 'category_name']
    legacy_counts = {}
    
    for field in legacy_fields:
        count = db.seller_listings.count_documents({field: {"$exists": True}})
        legacy_counts[field] = count
        if count > 0:
            print(f"  ❌ {field}: {count} documents (SHOULD BE 0)")
            report["passed"] = False
            report["critical_failures"].append(f"Legacy field '{field}' found in {count} documents")
        else:
            print(f"  ✅ {field}: 0 documents")
    
    report["checks"]["legacy_fields"] = {
        "passed": all(c == 0 for c in legacy_counts.values()),
        "counts": legacy_counts
    }
    
    # Hard rule query (must return 0)
    hard_rule_query = {
        "$or": [
            {"seller_id": {"$exists": True}},
            {"product_id": {"$exists": True}},
            {"category_id": {"$exists": True}}
        ]
    }
    hard_rule_count = db.seller_listings.count_documents(hard_rule_query)
    
    print(f"\n  🚨 HARD RULE CHECK: {hard_rule_count} documents with legacy ID fields")
    if hard_rule_count > 0:
        report["passed"] = False
        report["critical_failures"].append(f"HARD RULE FAILED: {hard_rule_count} documents have legacy ID fields")
    
    # ========== CHECK 2: Canonical Field Types ==========
    print("\n📋 CHECK 2: Canonical Field Type Validation")
    print("-" * 40)
    
    canonical_fields = ['sellerId', 'productId', 'categoryId']
    type_errors = []
    
    total_docs = db.seller_listings.count_documents({})
    print(f"  Total documents to check: {total_docs}")
    
    for doc in db.seller_listings.find():
        doc_id = doc['_id']
        for field in canonical_fields:
            value = doc.get(field)
            if value is None:
                type_errors.append({
                    "doc_id": str(doc_id),
                    "field": field,
                    "error": "Field is missing"
                })
            elif not isinstance(value, ObjectId):
                type_errors.append({
                    "doc_id": str(doc_id),
                    "field": field,
                    "error": f"Expected ObjectId, got {type(value).__name__}"
                })
    
    if type_errors:
        print(f"  ❌ {len(type_errors)} type errors found:")
        for err in type_errors[:5]:
            print(f"     - Doc {err['doc_id']}: {err['field']} - {err['error']}")
        if len(type_errors) > 5:
            print(f"     ... and {len(type_errors) - 5} more")
        report["passed"] = False
        report["critical_failures"].append(f"{len(type_errors)} canonical fields are not ObjectId type")
    else:
        print(f"  ✅ All {total_docs} documents have correct ObjectId types")
    
    report["checks"]["field_types"] = {
        "passed": len(type_errors) == 0,
        "total_docs": total_docs,
        "error_count": len(type_errors),
        "sample_errors": type_errors[:10]
    }
    
    # ========== CHECK 3: Referential Integrity ==========
    print("\n📋 CHECK 3: Referential Integrity")
    print("-" * 40)
    
    ref_errors = []
    
    # Check sellerId -> users
    for doc in db.seller_listings.find({"sellerId": {"$exists": True, "$type": "objectId"}}):
        seller = db.users.find_one({"_id": doc["sellerId"]})
        if not seller:
            ref_errors.append({
                "doc_id": str(doc["_id"]),
                "field": "sellerId",
                "value": str(doc["sellerId"]),
                "error": "User not found"
            })
    
    # Check productId -> products
    for doc in db.seller_listings.find({"productId": {"$exists": True, "$type": "objectId"}}):
        product = db.products.find_one({"_id": doc["productId"]})
        if not product:
            ref_errors.append({
                "doc_id": str(doc["_id"]),
                "field": "productId",
                "value": str(doc["productId"]),
                "error": "Product not found"
            })
    
    # Check categoryId -> categories
    for doc in db.seller_listings.find({"categoryId": {"$exists": True, "$type": "objectId"}}):
        category = db.categories.find_one({"_id": doc["categoryId"]})
        if not category:
            ref_errors.append({
                "doc_id": str(doc["_id"]),
                "field": "categoryId",
                "value": str(doc["categoryId"]),
                "error": "Category not found"
            })
    
    if ref_errors:
        print(f"  ⚠️  {len(ref_errors)} referential integrity issues:")
        for err in ref_errors[:5]:
            print(f"     - Doc {err['doc_id']}: {err['field']}={err['value']} - {err['error']}")
    else:
        print(f"  ✅ All foreign key references are valid")
    
    report["checks"]["referential_integrity"] = {
        "passed": len(ref_errors) == 0,
        "error_count": len(ref_errors),
        "sample_errors": ref_errors[:10]
    }
    
    # ========== CHECK 4: Index Verification ==========
    print("\n📋 CHECK 4: Index Verification")
    print("-" * 40)
    
    existing_indexes = {idx['name']: idx for idx in db.seller_listings.list_indexes()}
    
    required_indexes = [
        "sellerId_1",
        "productId_1", 
        "categoryId_1",
        "status_1",
    ]
    
    unique_index_exists = any(
        idx.get('unique', False) and 
        'sellerId' in str(idx.get('key', {})) and 
        'productId' in str(idx.get('key', {}))
        for idx in existing_indexes.values()
    )
    
    missing_indexes = []
    for idx_name in required_indexes:
        if idx_name in existing_indexes:
            print(f"  ✅ Index exists: {idx_name}")
        else:
            print(f"  ❌ Index missing: {idx_name}")
            missing_indexes.append(idx_name)
    
    if unique_index_exists:
        print(f"  ✅ Unique compound index (sellerId, productId) exists")
    else:
        print(f"  ❌ Unique compound index missing!")
        missing_indexes.append("unique_seller_product")
    
    report["checks"]["indexes"] = {
        "passed": len(missing_indexes) == 0,
        "existing": list(existing_indexes.keys()),
        "missing": missing_indexes,
        "unique_index_exists": unique_index_exists
    }
    
    # ========== CHECK 5: Collection Statistics ==========
    print("\n📋 CHECK 5: Collection Statistics")
    print("-" * 40)
    
    active_count = db.seller_listings.count_documents({"status": "active"})
    inactive_count = db.seller_listings.count_documents({"status": "inactive"})
    draft_count = db.seller_listings.count_documents({"status": "draft"})
    
    print(f"  Total listings: {total_docs}")
    print(f"  Active: {active_count}")
    print(f"  Inactive: {inactive_count}")
    print(f"  Draft: {draft_count}")
    
    # Unique sellers and products
    unique_sellers = len(db.seller_listings.distinct("sellerId"))
    unique_products = len(db.seller_listings.distinct("productId"))
    
    print(f"  Unique sellers: {unique_sellers}")
    print(f"  Unique products: {unique_products}")
    
    report["checks"]["statistics"] = {
        "total": total_docs,
        "active": active_count,
        "inactive": inactive_count,
        "draft": draft_count,
        "unique_sellers": unique_sellers,
        "unique_products": unique_products
    }
    
    # ========== FINAL VERDICT ==========
    print("\n" + "=" * 70)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 70)
    
    all_checks_passed = all(
        check.get("passed", True) 
        for check in report["checks"].values()
    )
    
    # Override with hard rule failures
    if hard_rule_count > 0 or len(type_errors) > 0:
        all_checks_passed = False
    
    report["passed"] = all_checks_passed
    
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Schema integrity verified")
    else:
        print("❌ VERIFICATION FAILED")
        print("\nCritical failures:")
        for failure in report["critical_failures"]:
            print(f"  - {failure}")
    
    print("=" * 70)
    
    return all_checks_passed, report


def main():
    passed, report = verify_schema_integrity()
    
    # Save report to file
    report_path = "/app/backend/scripts/schema_integrity_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n📄 Report saved to: {report_path}")
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
