"""
Enterprise Schema Migration Script
===================================
Standardizes data schema for products and sellerListings collections.

Migration Goals:
1. Products: Ensure `images` array exists (migrate from coverImageUrl/imageUrl/image)
2. SellerListings: Ensure `images` array exists, `searchableAttributes` exists

Run this script to migrate existing data:
    python scripts/migrate_enterprise_schema.py

Dry run (preview only):
    python scripts/migrate_enterprise_schema.py --dry-run
"""

import asyncio
import argparse
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


async def migrate_products(db, dry_run=False):
    """
    Migrate products collection to standardized schema.
    
    Ensures every product has an `images` array field.
    Falls back from: coverImageUrl -> imageUrl -> image -> []
    """
    print("\n" + "="*60)
    print("📦 MIGRATING PRODUCTS COLLECTION")
    print("="*60)
    
    # Find products that need migration (no images field OR images is null/empty)
    products_cursor = db.products.find({
        "$or": [
            {"images": {"$exists": False}},
            {"images": None},
            {"images": []},
        ]
    })
    
    migrated_count = 0
    skipped_count = 0
    
    async for product in products_cursor:
        product_id = product["_id"]
        product_name = product.get("name", "Unknown")
        
        # Build images array from available fields
        images = []
        
        # Priority: coverImageUrl -> imageUrl -> image
        if product.get("coverImageUrl"):
            images.append(product["coverImageUrl"])
        elif product.get("imageUrl"):
            images.append(product["imageUrl"])
        elif product.get("image"):
            images.append(product["image"])
        
        # Skip if no images to migrate (will keep empty array)
        if dry_run:
            print(f"  [DRY RUN] Would update product '{product_name}': images={images}")
            migrated_count += 1
            continue
        
        # Update the document
        result = await db.products.update_one(
            {"_id": product_id},
            {
                "$set": {
                    "images": images,
                    "enterpriseMigratedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"  ✅ Migrated product '{product_name}': images={images}")
            migrated_count += 1
        else:
            print(f"  ⏭️ Skipped product '{product_name}' (no changes)")
            skipped_count += 1
    
    print(f"\n📊 Products Migration Summary:")
    print(f"   Migrated: {migrated_count}")
    print(f"   Skipped: {skipped_count}")
    
    return migrated_count


async def migrate_seller_listings(db, dry_run=False):
    """
    Migrate sellerListings collection to standardized schema.
    
    Ensures every listing has:
    - `images` array (migrate from imageUrl/image)
    - `searchableAttributes` object (migrate from technicalSpecs)
    - `attributeLabels` object
    """
    print("\n" + "="*60)
    print("👤 MIGRATING SELLER LISTINGS COLLECTION")
    print("="*60)
    
    # Find listings that need migration
    listings_cursor = db.sellerListings.find({
        "$or": [
            {"images": {"$exists": False}},
            {"images": None},
            {"searchableAttributes": {"$exists": False}},
            {"attributeLabels": {"$exists": False}},
        ]
    })
    
    migrated_count = 0
    skipped_count = 0
    
    async for listing in listings_cursor:
        listing_id = listing["_id"]
        
        update_fields = {}
        
        # Migrate images
        if "images" not in listing or listing.get("images") is None:
            images = []
            if listing.get("imageUrl"):
                if isinstance(listing["imageUrl"], list):
                    images = listing["imageUrl"]
                else:
                    images = [listing["imageUrl"]]
            elif listing.get("image"):
                if isinstance(listing["image"], list):
                    images = listing["image"]
                else:
                    images = [listing["image"]]
            update_fields["images"] = images
        
        # Migrate searchableAttributes from technicalSpecs
        if "searchableAttributes" not in listing:
            if listing.get("technicalSpecs"):
                update_fields["searchableAttributes"] = listing["technicalSpecs"]
            else:
                update_fields["searchableAttributes"] = {}
        
        # Ensure attributeLabels exists
        if "attributeLabels" not in listing:
            update_fields["attributeLabels"] = {}
        
        if not update_fields:
            skipped_count += 1
            continue
        
        if dry_run:
            print(f"  [DRY RUN] Would update listing '{listing_id}': {list(update_fields.keys())}")
            migrated_count += 1
            continue
        
        # Update the document
        update_fields["enterpriseMigratedAt"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.sellerListings.update_one(
            {"_id": listing_id},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            print(f"  ✅ Migrated listing '{listing_id}': {list(update_fields.keys())}")
            migrated_count += 1
        else:
            print(f"  ⏭️ Skipped listing '{listing_id}'")
            skipped_count += 1
    
    print(f"\n📊 SellerListings Migration Summary:")
    print(f"   Migrated: {migrated_count}")
    print(f"   Skipped: {skipped_count}")
    
    return migrated_count


async def verify_schema(db):
    """
    Verify schema after migration.
    """
    print("\n" + "="*60)
    print("🔍 VERIFYING SCHEMA POST-MIGRATION")
    print("="*60)
    
    # Check products
    products_missing_images = await db.products.count_documents({
        "$or": [
            {"images": {"$exists": False}},
            {"images": None}
        ]
    })
    
    # Check seller listings
    listings_missing_images = await db.sellerListings.count_documents({
        "$or": [
            {"images": {"$exists": False}},
            {"images": None}
        ]
    })
    
    listings_missing_attrs = await db.sellerListings.count_documents({
        "searchableAttributes": {"$exists": False}
    })
    
    print(f"\n📊 Verification Results:")
    print(f"   Products missing 'images': {products_missing_images}")
    print(f"   Listings missing 'images': {listings_missing_images}")
    print(f"   Listings missing 'searchableAttributes': {listings_missing_attrs}")
    
    if products_missing_images == 0 and listings_missing_images == 0 and listings_missing_attrs == 0:
        print("\n✅ Schema migration COMPLETE - all documents standardized!")
        return True
    else:
        print("\n⚠️ Some documents still need migration")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Migrate enterprise schema")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()
    
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    if not mongo_url:
        print("❌ MONGO_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("="*60)
    print("🚀 ENTERPRISE SCHEMA MIGRATION")
    print(f"   Database: {db_name}")
    print(f"   Dry Run: {args.dry_run}")
    print("="*60)
    
    try:
        # Run migrations
        await migrate_products(db, dry_run=args.dry_run)
        await migrate_seller_listings(db, dry_run=args.dry_run)
        
        # Verify if not dry run
        if not args.dry_run:
            await verify_schema(db)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
