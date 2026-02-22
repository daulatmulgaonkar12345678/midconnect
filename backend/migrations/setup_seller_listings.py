"""
Migration Script: Setup seller_listings indexes and seed data

This script:
1. Creates the unique compound index on (productId, sellerId)
2. Creates query optimization indexes
3. Optionally seeds sample data for testing

Usage:
    python -m migrations.setup_seller_listings

"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "midconnect").strip()


async def setup_indexes(db):
    """Create required indexes for seller_listings collection"""
    logger.info("Creating indexes for seller_listings collection...")
    
    # 1. Unique compound index (CRITICAL for data integrity)
    try:
        await db.seller_listings.create_index(
            [("productId", 1), ("sellerId", 1)],
            unique=True,
            name="unique_product_seller",
            background=True
        )
        logger.info("  [OK] Created unique compound index (productId, sellerId)")
    except Exception as e:
        if "already exists" in str(e):
            logger.info("  [SKIP] Unique compound index already exists")
        else:
            logger.error(f"  [ERROR] {e}")
    
    # 2. Query optimization indexes
    simple_indexes = [
        [("productId", 1)],
        [("sellerId", 1)],
        [("status", 1)],
        [("status", 1), ("productId", 1)],
        [("createdAt", -1)],
    ]
    
    for idx in simple_indexes:
        try:
            await db.seller_listings.create_index(idx, background=True)
            logger.info(f"  [OK] Created index {idx}")
        except Exception as e:
            if "already exists" in str(e):
                logger.info(f"  [SKIP] Index {idx} already exists")
            else:
                logger.error(f"  [ERROR] Creating index {idx}: {e}")
    
    logger.info("Index setup complete!")


async def seed_sample_data(db, force=False):
    """Seed sample seller_listings for testing"""
    
    # Check if data already exists
    count = await db.seller_listings.count_documents({})
    if count > 0 and not force:
        logger.info(f"  [SKIP] {count} listings already exist. Use force=True to add more.")
        return
    
    logger.info("Seeding sample seller_listings...")
    
    # Get some existing products and sellers
    products = await db.products.find({"status": "active"}).limit(5).to_list(length=5)
    sellers = await db.users.find({"is_seller": True}).limit(3).to_list(length=3)
    
    if not products:
        logger.warning("  [WARN] No products found. Skipping seed.")
        return
    
    if not sellers:
        logger.warning("  [WARN] No sellers found. Skipping seed.")
        return
    
    now = datetime.now(timezone.utc)
    sample_listings = []
    
    for i, product in enumerate(products):
        for j, seller in enumerate(sellers):
            # Create pricing tiers
            base_price = 100 + (i * 50) + (j * 10)
            pricing_tiers = [
                {"minQty": 1, "maxQty": 99, "pricePerUnit": base_price},
                {"minQty": 100, "maxQty": 499, "pricePerUnit": base_price * 0.9},
                {"minQty": 500, "maxQty": None, "pricePerUnit": base_price * 0.8},
            ]
            
            listing = {
                "productId": product["_id"],
                "sellerId": seller["_id"],
                "status": "active" if (i + j) % 3 != 0 else "inactive",
                "stock": 100 + (i * 50) - (j * 20),
                "leadTime": 7 + i,
                "currency": "INR",
                "pricingTiers": pricing_tiers,
                "createdAt": now,
                "updatedAt": now
            }
            sample_listings.append(listing)
    
    try:
        # Use ordered=False to continue on duplicate key errors
        result = await db.seller_listings.insert_many(sample_listings, ordered=False)
        logger.info(f"  [OK] Inserted {len(result.inserted_ids)} sample listings")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            logger.info("  [INFO] Some listings already existed (duplicate key)")
        else:
            logger.error(f"  [ERROR] {e}")


async def migrate_existing_seller_listings(db):
    """
    Migrate existing seller_listings to the new schema format.
    
    Old format had different field names:
    - product_id -> productId
    - seller_id -> sellerId
    - pricing_slabs -> pricingTiers
    """
    logger.info("Checking for legacy seller_listings format...")
    
    # Count documents with old field names
    old_format_count = await db.seller_listings.count_documents({
        "$or": [
            {"product_id": {"$exists": True}},
            {"seller_id": {"$exists": True}},
            {"pricing_slabs": {"$exists": True}}
        ]
    })
    
    if old_format_count == 0:
        logger.info("  [SKIP] No legacy format documents found")
        return
    
    logger.info(f"  Found {old_format_count} documents with legacy format. Migrating...")
    
    # Update field names
    updates = []
    
    # Rename product_id to productId
    result = await db.seller_listings.update_many(
        {"product_id": {"$exists": True}},
        {"$rename": {"product_id": "productId"}}
    )
    if result.modified_count > 0:
        logger.info(f"  [OK] Renamed product_id -> productId ({result.modified_count} docs)")
    
    # Rename seller_id to sellerId
    result = await db.seller_listings.update_many(
        {"seller_id": {"$exists": True}},
        {"$rename": {"seller_id": "sellerId"}}
    )
    if result.modified_count > 0:
        logger.info(f"  [OK] Renamed seller_id -> sellerId ({result.modified_count} docs)")
    
    # Convert pricing_slabs to pricingTiers (requires aggregation)
    cursor = db.seller_listings.find({"pricing_slabs": {"$exists": True}})
    async for doc in cursor:
        old_slabs = doc.get("pricing_slabs", [])
        new_tiers = []
        for slab in old_slabs:
            new_tiers.append({
                "minQty": slab.get("min_quantity", 1),
                "maxQty": slab.get("max_quantity"),
                "pricePerUnit": slab.get("price_per_unit", 0)
            })
        
        await db.seller_listings.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {"pricingTiers": new_tiers},
                "$unset": {"pricing_slabs": ""}
            }
        )
    
    logger.info("  Migration complete!")


async def main():
    if not MONGO_URL:
        logger.error("MONGO_URL not configured!")
        return
    
    logger.info(f"Connecting to database: {DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Step 1: Setup indexes
        await setup_indexes(db)
        
        # Step 2: Migrate existing data if needed
        await migrate_existing_seller_listings(db)
        
        # Step 3: Seed sample data (optional)
        # await seed_sample_data(db, force=False)
        
        logger.info("\n=== Migration Complete ===")
        
        # Show stats
        listing_count = await db.seller_listings.count_documents({})
        active_count = await db.seller_listings.count_documents({"status": "active"})
        logger.info(f"Total listings: {listing_count}")
        logger.info(f"Active listings: {active_count}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
