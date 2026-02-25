"""
V19 - Populate Seller Location on Listings
===========================================

This migration updates all sellerListings to include city/state
from the seller's profile for search and display purposes.

Run: python -m migrations.V19_populate_listing_locations
"""

import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("V19_migration")


async def run_migration(dry_run: bool = False):
    """
    Populate city/state on all sellerListings from seller profiles.
    """
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'midconnect')]
    
    report = {
        "phase": "V19 - Populate Listing Locations",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "listings_updated": 0,
        "listings_skipped": 0,
        "seller_not_found": 0,
        "errors": []
    }
    
    try:
        # Get all listings
        listings = await db.sellerListings.find({}).to_list(None)
        logger.info(f"Found {len(listings)} listings to process")
        
        # Build seller cache
        seller_ids = list(set(str(l.get("sellerId")) for l in listings if l.get("sellerId")))
        logger.info(f"Found {len(seller_ids)} unique sellers")
        
        # Fetch all seller profiles
        seller_profiles = {}
        if seller_ids:
            # Convert string IDs to ObjectIds where valid
            valid_oids = []
            for sid in seller_ids:
                try:
                    valid_oids.append(ObjectId(sid))
                except:
                    pass
            
            sellers = await db.users.find(
                {"_id": {"$in": valid_oids}},
                {"profile": 1}
            ).to_list(None)
            
            for s in sellers:
                profile = s.get("profile", {})
                seller_profiles[str(s["_id"])] = {
                    "city": profile.get("city"),
                    "state": profile.get("state"),
                    "businessName": profile.get("businessName")
                }
        
        logger.info(f"Loaded {len(seller_profiles)} seller profiles")
        
        # Update each listing
        for listing in listings:
            listing_id = listing["_id"]
            seller_id = str(listing.get("sellerId", ""))
            
            seller_info = seller_profiles.get(seller_id)
            
            if not seller_info:
                logger.warning(f"Seller not found for listing {listing_id}")
                report["seller_not_found"] += 1
                continue
            
            # Check if update needed
            current_city = listing.get("city")
            current_state = listing.get("state")
            new_city = seller_info.get("city")
            new_state = seller_info.get("state")
            
            if current_city == new_city and current_state == new_state:
                report["listings_skipped"] += 1
                continue
            
            # Update listing
            updates = {
                "city": new_city,
                "state": new_state,
                "updatedAt": datetime.now(timezone.utc)
            }
            
            if not dry_run:
                await db.sellerListings.update_one(
                    {"_id": listing_id},
                    {"$set": updates}
                )
            
            logger.info(f"Updated listing {listing_id}: city={new_city}, state={new_state}")
            report["listings_updated"] += 1
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Listings Updated: {report['listings_updated']}")
        logger.info(f"Listings Skipped (no change): {report['listings_skipped']}")
        logger.info(f"Seller Not Found: {report['seller_not_found']}")
        logger.info("="*60)
        
        return report
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        report["errors"].append(str(e))
        raise
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_migration(dry_run=dry_run))
