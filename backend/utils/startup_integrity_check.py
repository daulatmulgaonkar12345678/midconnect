"""
Enterprise Data Integrity Startup Check
========================================
Runs on server startup to detect schema drift.

Checks for:
- Products with empty specTemplateIds
- Templates with string categoryId
- Listings with empty searchableAttributes
- Active listings with missing images

Enterprise systems self-audit.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("enterprise_audit")


async def run_startup_integrity_check(db: AsyncIOMotorDatabase) -> dict:
    """
    Run data integrity checks on startup.
    
    Returns dict with check results.
    """
    logger.info("🔍 Running enterprise data integrity check...")
    
    results = {
        "passed": True,
        "checks": [],
        "warnings": [],
        "errors": []
    }
    
    # Check 1: Products with empty specTemplateIds
    empty_templates = await db.products.count_documents({
        "$or": [
            {"specTemplateIds": {"$exists": False}},
            {"specTemplateIds": {"$size": 0}}
        ],
        "isActive": True
    })
    if empty_templates > 0:
        results["warnings"].append(f"{empty_templates} active products have empty specTemplateIds")
    results["checks"].append(f"Products with empty specTemplateIds: {empty_templates}")
    
    # Check 2: Templates with string categoryId
    string_category = await db.specTemplates.count_documents({
        "categoryId": {"$type": "string"}
    })
    if string_category > 0:
        results["errors"].append(f"{string_category} specTemplates have STRING categoryId (must be ObjectId)")
        results["passed"] = False
    results["checks"].append(f"Templates with string categoryId: {string_category}")
    
    # Check 3: Active listings with empty searchableAttributes
    empty_attrs = await db.sellerListings.count_documents({
        "status": "active",
        "$or": [
            {"searchableAttributes": {}},
            {"searchableAttributes": {"$exists": False}}
        ]
    })
    if empty_attrs > 0:
        results["errors"].append(f"{empty_attrs} ACTIVE listings have empty searchableAttributes")
        results["passed"] = False
    results["checks"].append(f"Active listings with empty searchableAttributes: {empty_attrs}")
    
    # Check 4: Active listings with empty images
    empty_images = await db.sellerListings.count_documents({
        "status": "active",
        "$or": [
            {"images": {"$size": 0}},
            {"images": {"$exists": False}}
        ]
    })
    if empty_images > 0:
        results["errors"].append(f"{empty_images} ACTIVE listings have empty images")
        results["passed"] = False
    results["checks"].append(f"Active listings with empty images: {empty_images}")
    
    # Check 5: Variants with empty attributes
    empty_variant_attrs = await db.productVariants.count_documents({
        "attributes": {}
    })
    if empty_variant_attrs > 0:
        results["warnings"].append(f"{empty_variant_attrs} variants have empty attributes")
    results["checks"].append(f"Variants with empty attributes: {empty_variant_attrs}")
    
    # Log results
    if results["passed"]:
        logger.info("✅ Enterprise data integrity check PASSED")
        for check in results["checks"]:
            logger.info(f"   {check}")
    else:
        logger.error("❌ Enterprise data integrity check FAILED")
        for error in results["errors"]:
            logger.error(f"   ❌ {error}")
        for warning in results["warnings"]:
            logger.warning(f"   ⚠️ {warning}")
    
    if results["warnings"]:
        for warning in results["warnings"]:
            logger.warning(f"   ⚠️ {warning}")
    
    return results
