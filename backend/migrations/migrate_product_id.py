#!/usr/bin/env python3
"""
Migration Script: Add product_id to seller_listings
====================================================
This script performs a CONTROLLED migration to link seller_listings 
to the products collection via product_id.

Migration Strategy:
1. EXACT name match only (case-sensitive)
2. Log all unmatched listings for manual review
3. NO fuzzy matching - prevents false associations
4. Generates detailed report

Run with: python migrations/migrate_product_id.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "midconnect").strip()


async def run_migration():
    """Main migration function"""
    if not MONGO_URL:
        print("ERROR: MONGO_URL not set")
        return
    
    print("=" * 60)
    print("SELLER_LISTINGS PRODUCT_ID MIGRATION")
    print("=" * 60)
    print(f"Database: {DB_NAME}")
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get all seller_listings without product_id
    listings_without_pid = await db.seller_listings.find({
        "$or": [
            {"product_id": {"$exists": False}},
            {"product_id": None}
        ]
    }).to_list(None)
    
    total_listings = len(listings_without_pid)
    print(f"Found {total_listings} listings without product_id")
    print("-" * 60)
    
    if total_listings == 0:
        print("No migration needed - all listings have product_id")
        return
    
    # Build product name -> product_id lookup (exact match only)
    products = await db.products.find({"is_active": {"$ne": False}}).to_list(None)
    product_lookup = {}
    for prod in products:
        name = prod.get("name", "").strip()
        if name:
            # Use exact name as key
            if name not in product_lookup:
                product_lookup[name] = str(prod["_id"])
            else:
                print(f"  WARNING: Duplicate product name '{name}' - using first occurrence")
    
    print(f"Loaded {len(product_lookup)} unique products from catalog")
    print()
    
    # Process listings
    matched = []
    unmatched = []
    
    for listing in listings_without_pid:
        listing_id = str(listing["_id"])
        listing_name = listing.get("product_name", "").strip()
        seller_id = listing.get("seller_id", "unknown")
        
        if listing_name in product_lookup:
            matched.append({
                "listing_id": listing_id,
                "product_name": listing_name,
                "product_id": product_lookup[listing_name],
                "seller_id": seller_id
            })
        else:
            unmatched.append({
                "listing_id": listing_id,
                "product_name": listing_name,
                "seller_id": seller_id,
                "reason": "No exact product name match in catalog"
            })
    
    print(f"MATCH RESULTS:")
    print(f"  - Matched: {len(matched)}")
    print(f"  - Unmatched: {len(unmatched)}")
    print()
    
    # Apply updates for matched listings
    if matched:
        print("APPLYING UPDATES...")
        update_count = 0
        for item in matched:
            result = await db.seller_listings.update_one(
                {"_id": ObjectId(item["listing_id"])},
                {"$set": {
                    "product_id": item["product_id"],
                    "migration_date": datetime.now(timezone.utc),
                    "migration_note": "Backfilled from exact product_name match"
                }}
            )
            if result.modified_count > 0:
                update_count += 1
                print(f"  ✓ {item['product_name'][:40]:<40} -> {item['product_id']}")
        
        print(f"\nUpdated {update_count} listings")
    
    # Log unmatched listings
    if unmatched:
        print()
        print("=" * 60)
        print("UNMATCHED LISTINGS (require manual review)")
        print("=" * 60)
        for item in unmatched:
            print(f"  ✗ Listing: {item['listing_id']}")
            print(f"    Name: {item['product_name']}")
            print(f"    Seller: {item['seller_id']}")
            print(f"    Reason: {item['reason']}")
            print()
        
        # Save unmatched report to database for admin review
        report = {
            "type": "product_id_migration",
            "created_at": datetime.now(timezone.utc),
            "total_processed": total_listings,
            "matched_count": len(matched),
            "unmatched_count": len(unmatched),
            "unmatched_listings": unmatched
        }
        await db.migration_reports.insert_one(report)
        print(f"Migration report saved to 'migration_reports' collection")
    
    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print(f"Finished: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
