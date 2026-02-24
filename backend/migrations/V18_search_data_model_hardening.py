"""
V18 - Search Data Model Hardening
==================================

PHASE 1 of Enterprise Search Architecture

This migration:
1. Updates manufacturers collection with slug field and index
2. Adds search-optimized fields to sellerListings
3. Creates structured indexes for fast filtering
4. Seeds initial manufacturers

Run: python -m migrations.V18_search_data_model_hardening
"""

import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import re
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("V18_migration")

# Initial manufacturer seed data (Industrial/Electrical)
SEED_MANUFACTURERS = [
    {"brandName": "ABB", "country": "Switzerland", "categories": ["electrical", "motors", "switchgear"]},
    {"brandName": "Siemens", "country": "Germany", "categories": ["electrical", "motors", "automation"]},
    {"brandName": "Crompton", "country": "India", "categories": ["motors", "pumps", "fans"]},
    {"brandName": "L&T", "country": "India", "categories": ["electrical", "switchgear", "motors"]},
    {"brandName": "Schneider Electric", "country": "France", "categories": ["electrical", "switchgear", "automation"]},
    {"brandName": "Havells", "country": "India", "categories": ["electrical", "cables", "switches"]},
    {"brandName": "Bharat Bijlee", "country": "India", "categories": ["motors", "transformers"]},
    {"brandName": "Kirloskar", "country": "India", "categories": ["motors", "pumps", "compressors"]},
    {"brandName": "CG Power", "country": "India", "categories": ["motors", "transformers", "switchgear"]},
    {"brandName": "WEG", "country": "Brazil", "categories": ["motors", "drives", "automation"]},
]


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'[\s-]+', '-', slug)  # Replace spaces with hyphens
    slug = slug.strip('-')
    return slug


async def run_migration(dry_run: bool = False):
    """
    Execute Phase 1 Data Model Hardening.
    
    Args:
        dry_run: If True, only log changes without applying them
    """
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'midconnect')]
    
    report = {
        "phase": "V18 - Search Data Model Hardening",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "manufacturers_updated": 0,
        "manufacturers_seeded": 0,
        "listings_updated": 0,
        "indexes_created": [],
        "errors": []
    }
    
    try:
        # ==================== STEP 1: Update Manufacturers Schema ====================
        logger.info("Step 1: Updating manufacturers collection...")
        
        # Add slug to existing manufacturers
        existing_mfrs = await db.manufacturers.find({}).to_list(None)
        for mfr in existing_mfrs:
            if not mfr.get("slug"):
                slug = generate_slug(mfr.get("brandName", ""))
                if not dry_run:
                    await db.manufacturers.update_one(
                        {"_id": mfr["_id"]},
                        {"$set": {"slug": slug, "updatedAt": datetime.now(timezone.utc)}}
                    )
                logger.info(f"  Added slug '{slug}' to manufacturer: {mfr.get('brandName')}")
                report["manufacturers_updated"] += 1
        
        # ==================== STEP 2: Seed Initial Manufacturers ====================
        logger.info("Step 2: Seeding initial manufacturers...")
        
        for mfr_data in SEED_MANUFACTURERS:
            slug = generate_slug(mfr_data["brandName"])
            
            # Check if exists by slug (case-insensitive name or exact slug)
            existing = await db.manufacturers.find_one({
                "$or": [
                    {"slug": slug},
                    {"brandName": {"$regex": f"^{re.escape(mfr_data['brandName'])}$", "$options": "i"}}
                ]
            })
            
            if not existing:
                now = datetime.now(timezone.utc)
                doc = {
                    "_id": ObjectId(),
                    "brandName": mfr_data["brandName"],
                    "slug": slug,
                    "country": mfr_data.get("country"),
                    "categories": mfr_data.get("categories", []),
                    "status": "approved",
                    "isActive": True,
                    "createdAt": now,
                    "updatedAt": now
                }
                if not dry_run:
                    await db.manufacturers.insert_one(doc)
                logger.info(f"  Seeded manufacturer: {mfr_data['brandName']} (slug: {slug})")
                report["manufacturers_seeded"] += 1
            else:
                logger.info(f"  Skipped (exists): {mfr_data['brandName']}")
        
        # ==================== STEP 3: Add Search Fields to sellerListings ====================
        logger.info("Step 3: Adding search-optimized fields to sellerListings...")
        
        # Find listings missing new fields
        listings = await db.sellerListings.find({
            "$or": [
                {"sellerTier": {"$exists": False}},
                {"boostScore": {"$exists": False}},
                {"isPremiumSeller": {"$exists": False}},
                {"inStock": {"$exists": False}},
                {"minPrice": {"$exists": False}}
            ]
        }).to_list(None)
        
        for listing in listings:
            updates = {}
            
            # Add sellerTier (default: free)
            if not listing.get("sellerTier"):
                updates["sellerTier"] = "free"
            
            # Add boostScore (default: 0)
            if listing.get("boostScore") is None:
                updates["boostScore"] = 0
            
            # Add isPremiumSeller (default: false)
            if listing.get("isPremiumSeller") is None:
                updates["isPremiumSeller"] = False
            
            # Add inStock (derived from stock > 0)
            if listing.get("inStock") is None:
                updates["inStock"] = (listing.get("stock", 0) > 0)
            
            # Add minPrice (from first pricing tier)
            if listing.get("minPrice") is None:
                pricing_tiers = listing.get("pricingTiers", [])
                if pricing_tiers:
                    updates["minPrice"] = pricing_tiers[0].get("pricePerUnit", 0)
                else:
                    updates["minPrice"] = 0
            
            if updates:
                updates["updatedAt"] = datetime.now(timezone.utc)
                if not dry_run:
                    await db.sellerListings.update_one(
                        {"_id": listing["_id"]},
                        {"$set": updates}
                    )
                report["listings_updated"] += 1
        
        logger.info(f"  Updated {report['listings_updated']} listings with search fields")
        
        # ==================== STEP 4: Create Structured Indexes ====================
        logger.info("Step 4: Creating structured indexes...")
        
        # Manufacturers indexes
        mfr_indexes = [
            {"keys": [("slug", 1)], "unique": True, "name": "idx_mfr_slug_unique"},
            {"keys": [("brandName", 1)], "name": "idx_mfr_brand_name"},
            {"keys": [("status", 1), ("isActive", 1)], "name": "idx_mfr_status_active"},
        ]
        
        for idx in mfr_indexes:
            try:
                if not dry_run:
                    await db.manufacturers.create_index(
                        idx["keys"],
                        unique=idx.get("unique", False),
                        name=idx["name"],
                        background=True
                    )
                logger.info(f"  Created index: manufacturers.{idx['name']}")
                report["indexes_created"].append(f"manufacturers.{idx['name']}")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"  Index exists: manufacturers.{idx['name']}")
                else:
                    logger.error(f"  Index error: {e}")
                    report["errors"].append(str(e))
        
        # sellerListings structured indexes (for fast filtering)
        listing_indexes = [
            {"keys": [("manufacturerId", 1)], "name": "idx_listing_manufacturer"},
            {"keys": [("categoryId", 1)], "name": "idx_listing_category"},
            {"keys": [("city", 1)], "name": "idx_listing_city"},
            {"keys": [("state", 1)], "name": "idx_listing_state"},
            {"keys": [("minPrice", 1)], "name": "idx_listing_min_price"},
            {"keys": [("sellerRating", -1)], "name": "idx_listing_seller_rating"},
            {"keys": [("createdAt", -1)], "name": "idx_listing_created_at"},
            {"keys": [("isPremiumSeller", 1)], "name": "idx_listing_premium"},
            {"keys": [("inStock", 1)], "name": "idx_listing_in_stock"},
            {"keys": [("sellerTier", 1)], "name": "idx_listing_seller_tier"},
            {"keys": [("boostScore", -1)], "name": "idx_listing_boost_score"},
            # Compound index for common filter combinations
            {"keys": [("isActive", 1), ("status", 1), ("categoryId", 1), ("city", 1)], "name": "idx_listing_compound_search"},
            {"keys": [("isActive", 1), ("status", 1), ("minPrice", 1), ("sellerRating", -1)], "name": "idx_listing_compound_price_rating"},
        ]
        
        for idx in listing_indexes:
            try:
                if not dry_run:
                    await db.sellerListings.create_index(
                        idx["keys"],
                        name=idx["name"],
                        background=True
                    )
                logger.info(f"  Created index: sellerListings.{idx['name']}")
                report["indexes_created"].append(f"sellerListings.{idx['name']}")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"  Index exists: sellerListings.{idx['name']}")
                else:
                    logger.error(f"  Index error: {e}")
                    report["errors"].append(str(e))
        
        # ==================== STEP 5: Create searchAnalytics Collection ====================
        logger.info("Step 5: Setting up searchAnalytics collection...")
        
        # Create index on searchAnalytics
        try:
            if not dry_run:
                await db.searchAnalytics.create_index(
                    [("query", 1)],
                    name="idx_search_query"
                )
                await db.searchAnalytics.create_index(
                    [("count", -1)],
                    name="idx_search_count"
                )
                await db.searchAnalytics.create_index(
                    [("lastSearchedAt", -1)],
                    name="idx_search_last"
                )
            logger.info("  Created searchAnalytics indexes")
            report["indexes_created"].append("searchAnalytics indexes")
        except Exception as e:
            if "already exists" not in str(e):
                report["errors"].append(str(e))
        
        # ==================== SUMMARY ====================
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Manufacturers Updated (slug added): {report['manufacturers_updated']}")
        logger.info(f"Manufacturers Seeded: {report['manufacturers_seeded']}")
        logger.info(f"Listings Updated (search fields): {report['listings_updated']}")
        logger.info(f"Indexes Created: {len(report['indexes_created'])}")
        if report["errors"]:
            logger.warning(f"Errors: {len(report['errors'])}")
            for err in report["errors"]:
                logger.warning(f"  - {err}")
        logger.info("="*60)
        
        return report
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        report["errors"].append(str(e))
        raise
    finally:
        client.close()


async def verify_migration():
    """Verify the migration was successful."""
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'midconnect')]
    
    try:
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION")
        logger.info("="*60)
        
        # Check manufacturers
        mfr_count = await db.manufacturers.count_documents({"status": "approved"})
        mfr_with_slug = await db.manufacturers.count_documents({"slug": {"$exists": True, "$ne": None}})
        logger.info(f"Approved Manufacturers: {mfr_count}")
        logger.info(f"Manufacturers with slug: {mfr_with_slug}")
        
        # List manufacturers
        mfrs = await db.manufacturers.find({"status": "approved"}).to_list(20)
        for m in mfrs:
            logger.info(f"  - {m.get('brandName')} (slug: {m.get('slug')}, country: {m.get('country')})")
        
        # Check listings
        listings_total = await db.sellerListings.count_documents({})
        listings_with_tier = await db.sellerListings.count_documents({"sellerTier": {"$exists": True}})
        listings_with_boost = await db.sellerListings.count_documents({"boostScore": {"$exists": True}})
        logger.info(f"\nTotal Listings: {listings_total}")
        logger.info(f"Listings with sellerTier: {listings_with_tier}")
        logger.info(f"Listings with boostScore: {listings_with_boost}")
        
        # Check indexes
        mfr_indexes = await db.manufacturers.index_information()
        listing_indexes = await db.sellerListings.index_information()
        logger.info(f"\nManufacturer Indexes: {len(mfr_indexes)}")
        logger.info(f"Listing Indexes: {len(listing_indexes)}")
        
        logger.info("="*60)
        
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv
    verify_only = "--verify" in sys.argv
    
    if verify_only:
        asyncio.run(verify_migration())
    else:
        asyncio.run(run_migration(dry_run=dry_run))
        asyncio.run(verify_migration())
