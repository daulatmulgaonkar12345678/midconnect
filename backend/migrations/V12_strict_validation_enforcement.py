"""
V12 Strict Validation Enforcement Migration
============================================
Upgrades all MongoDB validators from moderate/warn to strict/error.

This is PRODUCTION-GRADE validation:
- validationLevel: "strict" - All inserts AND updates must pass validation
- validationAction: "error" - Reject invalid documents (don't just warn)

IMPORTANT: Run this ONLY after confirming all existing data passes validation.
Run V11 first to ensure data is clean.

Collections Updated:
- categories
- category_requests  
- inquiries
- inquiry_reports
- product_requests
- products
- seller_listings
- spec_templates
- subscription_changes
- subscriptions
- users
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
import json

# Import schemas from V11
from V11_final_schema_enforcement import SCHEMAS

async def validate_existing_data(db, collection_name: str, schema: dict) -> dict:
    """
    Validate all existing documents against the schema.
    Returns validation report.
    """
    report = {
        "collection": collection_name,
        "total_docs": 0,
        "valid_docs": 0,
        "invalid_docs": 0,
        "issues": []
    }
    
    try:
        # Count documents
        report["total_docs"] = await db[collection_name].count_documents({})
        
        if report["total_docs"] == 0:
            report["valid_docs"] = 0
            return report
        
        # Get required fields from schema
        json_schema = schema.get("$jsonSchema", {})
        required_fields = json_schema.get("required", [])
        properties = json_schema.get("properties", {})
        
        # Check each document
        async for doc in db[collection_name].find():
            is_valid = True
            doc_issues = []
            
            # Check required fields
            for field in required_fields:
                if field not in doc or doc[field] is None:
                    is_valid = False
                    doc_issues.append(f"Missing required field: {field}")
            
            # Check for snake_case fields that shouldn't exist
            snake_case_fields = [k for k in doc.keys() if '_' in k and k != '_id']
            if snake_case_fields:
                # Only flag if camelCase equivalent exists in schema
                for sc_field in snake_case_fields:
                    # Convert snake_case to camelCase
                    parts = sc_field.split('_')
                    camel_case = parts[0] + ''.join(p.capitalize() for p in parts[1:])
                    if camel_case in properties:
                        doc_issues.append(f"Legacy snake_case field found: {sc_field}")
            
            if is_valid and not doc_issues:
                report["valid_docs"] += 1
            else:
                report["invalid_docs"] += 1
                if len(report["issues"]) < 5:  # Limit to 5 example issues
                    report["issues"].append({
                        "doc_id": str(doc["_id"]),
                        "problems": doc_issues[:3]  # Limit problems per doc
                    })
        
        return report
        
    except Exception as e:
        report["error"] = str(e)
        return report


async def run_migration(dry_run: bool = True):
    """
    Upgrade validators to strict/error mode.
    
    Args:
        dry_run: If True, only validate data without applying strict mode.
                 If False, apply strict validation.
    """
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL not set")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client.b2b_marketplace
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "validation_reports": {},
        "upgrades_applied": {},
        "errors": []
    }
    
    print("=" * 70)
    print(f"V12 STRICT VALIDATION ENFORCEMENT {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print("=" * 70)
    
    # Step 1: Validate all existing data
    print("\n📊 STEP 1: Validating existing data against schemas...")
    all_valid = True
    
    for coll_name, schema in SCHEMAS.items():
        validation_report = await validate_existing_data(db, coll_name, schema)
        report["validation_reports"][coll_name] = validation_report
        
        total = validation_report["total_docs"]
        valid = validation_report["valid_docs"]
        invalid = validation_report["invalid_docs"]
        
        if invalid > 0:
            all_valid = False
            print(f"  ⚠️  {coll_name}: {valid}/{total} valid ({invalid} invalid)")
            for issue in validation_report.get("issues", [])[:2]:
                print(f"      Example: {issue['doc_id']} - {issue['problems'][:2]}")
        else:
            print(f"  ✅ {coll_name}: {valid}/{total} documents valid")
    
    # Step 2: Apply strict validation (only if not dry run and all valid)
    if dry_run:
        print("\n🔍 DRY RUN COMPLETE - No changes applied")
        print("   Run with dry_run=False to apply strict validation")
    else:
        if not all_valid:
            print("\n⛔ CANNOT APPLY STRICT VALIDATION - Invalid documents found")
            print("   Fix data issues first, then retry")
            report["errors"].append("Invalid documents found - strict validation not applied")
        else:
            print("\n🔒 STEP 2: Applying STRICT validation...")
            for coll_name, schema in SCHEMAS.items():
                try:
                    await db.command("collMod", coll_name,
                        validator=schema,
                        validationLevel="strict",
                        validationAction="error"
                    )
                    print(f"  ✅ {coll_name}: STRICT validation applied")
                    report["upgrades_applied"][coll_name] = "strict/error"
                except Exception as e:
                    print(f"  ❌ {coll_name}: {str(e)[:60]}")
                    report["upgrades_applied"][coll_name] = f"error: {str(e)}"
                    report["errors"].append({
                        "collection": coll_name,
                        "error": str(e)
                    })
    
    # Save report
    report_path = f"/app/backend/migrations/V12_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n" + "=" * 70)
    print(f"{'DRY RUN' if dry_run else 'MIGRATION'} COMPLETE")
    print(f"Report saved: {report_path}")
    print("=" * 70)
    
    return len(report["errors"]) == 0


async def rollback_to_moderate():
    """
    Emergency rollback: Change validators back to moderate/warn.
    Use this if strict validation causes issues in production.
    """
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL not set")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client.b2b_marketplace
    
    print("🔄 ROLLBACK: Reverting to moderate/warn validation...")
    
    for coll_name, schema in SCHEMAS.items():
        try:
            await db.command("collMod", coll_name,
                validator=schema,
                validationLevel="moderate",
                validationAction="warn"
            )
            print(f"  ✅ {coll_name}: Reverted to moderate/warn")
        except Exception as e:
            print(f"  ❌ {coll_name}: {str(e)[:60]}")
    
    print("✅ Rollback complete")
    return True


if __name__ == "__main__":
    import sys
    
    # Default to dry run for safety
    dry_run = True
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--apply":
            dry_run = False
        elif sys.argv[1] == "--rollback":
            asyncio.run(rollback_to_moderate())
            sys.exit(0)
    
    success = asyncio.run(run_migration(dry_run=dry_run))
    sys.exit(0 if success else 1)
