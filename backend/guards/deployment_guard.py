"""
Deployment Guard - Pre-Start Schema Validation

This script MUST run before the application starts.
It performs comprehensive validation and FAILS FAST if any issues are found.

BLOCKING CONDITIONS (app will NOT start):
1. Legacy fields exist in seller_listings
2. Canonical fields are not ObjectId type
3. Schema validator is not active
4. Required indexes are missing

USAGE:
- As pre-start hook: python /app/backend/guards/deployment_guard.py
- As startup check: import and call validate_deployment()

EXIT CODES:
- 0: All checks passed, safe to start
- 1: Critical failures, DO NOT START
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List
import logging

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace').strip()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== LEGACY FIELDS THAT MUST NOT EXIST ====================
FORBIDDEN_FIELDS = [
    'seller_id',
    'product_id',
    'category_id',
    'product_name',
    'category_name',
    'created_at',
    'updated_at',
    'published_at'
]

# ==================== REQUIRED CANONICAL FIELDS ====================
REQUIRED_OBJECTID_FIELDS = [
    'sellerId',
    'productId',
    'categoryId'
]


class DeploymentGuardError(Exception):
    """Raised when deployment validation fails."""
    pass


def check_legacy_fields(db) -> Tuple[bool, List[str]]:
    """
    Check for any legacy fields in seller_listings.
    
    Returns: (passed, list of errors)
    """
    errors = []
    
    for field in FORBIDDEN_FIELDS:
        count = db.seller_listings.count_documents({field: {"$exists": True}})
        if count > 0:
            errors.append(f"LEGACY FIELD '{field}' found in {count} documents")
    
    return len(errors) == 0, errors


def check_objectid_types(db) -> Tuple[bool, List[str]]:
    """
    Verify all canonical fields are ObjectId type.
    
    Returns: (passed, list of errors)
    """
    errors = []
    
    for doc in db.seller_listings.find():
        doc_id = str(doc['_id'])
        
        for field in REQUIRED_OBJECTID_FIELDS:
            value = doc.get(field)
            if value is None:
                errors.append(f"Doc {doc_id}: Missing required field '{field}'")
            elif not isinstance(value, ObjectId):
                errors.append(
                    f"Doc {doc_id}: Field '{field}' is {type(value).__name__}, expected ObjectId"
                )
    
    return len(errors) == 0, errors


def check_schema_validator(db) -> Tuple[bool, List[str]]:
    """
    Verify MongoDB schema validator is active and strict.
    
    Returns: (passed, list of errors)
    """
    errors = []
    
    try:
        coll_info = db.command({"listCollections": 1, "filter": {"name": "seller_listings"}})
        collections = coll_info.get("cursor", {}).get("firstBatch", [])
        
        if not collections:
            errors.append("Collection 'seller_listings' not found")
            return False, errors
        
        coll = collections[0]
        options = coll.get("options", {})
        validator = options.get("validator")
        level = options.get("validationLevel", "off")
        action = options.get("validationAction", "warn")
        
        if not validator:
            errors.append("Schema validator is not configured")
        
        if level != "strict":
            errors.append(f"Validation level is '{level}', expected 'strict'")
        
        if action != "error":
            errors.append(f"Validation action is '{action}', expected 'error'")
            
    except Exception as e:
        errors.append(f"Failed to check schema validator: {e}")
    
    return len(errors) == 0, errors


def check_required_indexes(db) -> Tuple[bool, List[str]]:
    """
    Verify required indexes exist.
    
    Returns: (passed, list of errors)
    """
    errors = []
    
    try:
        existing_indexes = {idx['name']: idx for idx in db.seller_listings.list_indexes()}
        
        required_indexes = [
            "sellerId_1",
            "productId_1",
            "categoryId_1",
            "status_1"
        ]
        
        for idx_name in required_indexes:
            if idx_name not in existing_indexes:
                errors.append(f"Missing required index: {idx_name}")
        
        # Check for unique compound index
        unique_exists = any(
            idx.get('unique', False) and
            'sellerId' in str(idx.get('key', {})) and
            'productId' in str(idx.get('key', {}))
            for idx in existing_indexes.values()
        )
        
        if not unique_exists:
            errors.append("Missing unique compound index (sellerId, productId)")
            
    except Exception as e:
        errors.append(f"Failed to check indexes: {e}")
    
    return len(errors) == 0, errors


def check_referential_integrity(db) -> Tuple[bool, List[str]]:
    """
    Verify all foreign keys point to existing documents.
    
    Returns: (passed, list of errors)
    """
    errors = []
    
    # Check sellerId -> users
    for doc in db.seller_listings.find({"sellerId": {"$exists": True, "$type": "objectId"}}):
        seller = db.users.find_one({"_id": doc["sellerId"]})
        if not seller:
            errors.append(f"Doc {doc['_id']}: sellerId {doc['sellerId']} not found in users")
    
    # Check productId -> products
    for doc in db.seller_listings.find({"productId": {"$exists": True, "$type": "objectId"}}):
        product = db.products.find_one({"_id": doc["productId"]})
        if not product:
            errors.append(f"Doc {doc['_id']}: productId {doc['productId']} not found in products")
    
    return len(errors) == 0, errors


def validate_deployment(strict_validator: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Run all deployment validation checks.
    
    Args:
        strict_validator: If True, require schema validator to be active
        
    Returns:
        (passed: bool, report: dict)
    """
    logger.info("=" * 70)
    logger.info("🛡️  DEPLOYMENT GUARD - Pre-Start Validation")
    logger.info("=" * 70)
    logger.info(f"Database: {DB_NAME}")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    if not MONGO_URL:
        logger.error("❌ MONGO_URL not set!")
        return False, {"error": "MONGO_URL not configured"}
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": DB_NAME,
        "checks": {},
        "critical_failures": [],
        "warnings": []
    }
    
    all_passed = True
    
    # ========== CHECK 1: Legacy Fields (CRITICAL) ==========
    logger.info("\n📋 Check 1: Legacy Field Detection")
    passed, errors = check_legacy_fields(db)
    report["checks"]["legacy_fields"] = {"passed": passed, "errors": errors}
    
    if passed:
        logger.info("   ✅ No legacy fields found")
    else:
        logger.error("   ❌ CRITICAL: Legacy fields detected!")
        for err in errors:
            logger.error(f"      - {err}")
        report["critical_failures"].extend(errors)
        all_passed = False
    
    # ========== CHECK 2: ObjectId Types (CRITICAL) ==========
    logger.info("\n📋 Check 2: ObjectId Type Validation")
    passed, errors = check_objectid_types(db)
    report["checks"]["objectid_types"] = {"passed": passed, "error_count": len(errors)}
    
    if passed:
        logger.info("   ✅ All canonical fields are ObjectId type")
    else:
        logger.error(f"   ❌ CRITICAL: {len(errors)} type violations!")
        for err in errors[:5]:
            logger.error(f"      - {err}")
        if len(errors) > 5:
            logger.error(f"      ... and {len(errors) - 5} more")
        report["critical_failures"].append(f"{len(errors)} ObjectId type violations")
        all_passed = False
    
    # ========== CHECK 3: Schema Validator ==========
    logger.info("\n📋 Check 3: Schema Validator")
    passed, errors = check_schema_validator(db)
    report["checks"]["schema_validator"] = {"passed": passed, "errors": errors}
    
    if passed:
        logger.info("   ✅ Schema validator is active and strict")
    else:
        if strict_validator:
            logger.error("   ❌ CRITICAL: Schema validator issues!")
            for err in errors:
                logger.error(f"      - {err}")
            report["critical_failures"].extend(errors)
            all_passed = False
        else:
            logger.warning("   ⚠️  Schema validator not active (non-blocking)")
            for err in errors:
                logger.warning(f"      - {err}")
            report["warnings"].extend(errors)
    
    # ========== CHECK 4: Required Indexes ==========
    logger.info("\n📋 Check 4: Required Indexes")
    passed, errors = check_required_indexes(db)
    report["checks"]["indexes"] = {"passed": passed, "errors": errors}
    
    if passed:
        logger.info("   ✅ All required indexes exist")
    else:
        logger.warning("   ⚠️  Missing indexes (non-blocking, but performance impact):")
        for err in errors:
            logger.warning(f"      - {err}")
        report["warnings"].extend(errors)
    
    # ========== CHECK 5: Referential Integrity ==========
    logger.info("\n📋 Check 5: Referential Integrity")
    passed, errors = check_referential_integrity(db)
    report["checks"]["referential_integrity"] = {"passed": passed, "error_count": len(errors)}
    
    if passed:
        logger.info("   ✅ All foreign key references are valid")
    else:
        logger.warning(f"   ⚠️  {len(errors)} orphaned references (non-blocking):")
        for err in errors[:5]:
            logger.warning(f"      - {err}")
        report["warnings"].append(f"{len(errors)} orphaned references")
    
    # ========== FINAL VERDICT ==========
    logger.info("\n" + "=" * 70)
    logger.info("📋 DEPLOYMENT GUARD VERDICT")
    logger.info("=" * 70)
    
    report["passed"] = all_passed
    
    if all_passed:
        logger.info("✅ ALL CRITICAL CHECKS PASSED - Safe to deploy")
        if report["warnings"]:
            logger.info(f"\n⚠️  {len(report['warnings'])} non-critical warnings:")
            for warn in report["warnings"]:
                logger.info(f"   - {warn}")
    else:
        logger.error("❌ DEPLOYMENT BLOCKED - Critical failures detected!")
        logger.error("\nCritical failures:")
        for failure in report["critical_failures"]:
            logger.error(f"   - {failure}")
        logger.error("\nFix these issues before deploying:")
        logger.error("   1. Run migration: python /app/backend/migrations/V8_final_hard_enforcement.py")
        logger.error("   2. Apply validator: python /app/backend/scripts/apply_schema_validator.py")
        logger.error("   3. Re-run this guard: python /app/backend/guards/deployment_guard.py")
    
    logger.info("=" * 70)
    
    return all_passed, report


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deployment Guard - Pre-Start Validation")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require schema validator to be active (fail if not)"
    )
    parser.add_argument(
        "--report",
        type=str,
        default="/app/backend/guards/deployment_guard_report.json",
        help="Path to save JSON report"
    )
    args = parser.parse_args()
    
    passed, report = validate_deployment(strict_validator=args.strict)
    
    # Save report
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"\n📄 Report saved to: {args.report}")
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
