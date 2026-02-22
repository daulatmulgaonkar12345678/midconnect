"""
Migration Script: SSOT V8 - Pricing and Availability Flattening
================================================================
Migrates seller_listings from:
- pricing.slabs -> pricingTiers (root level)
- availability object -> flat fields (moq, stock, maxCapacity, leadTime)

This is a one-time migration to align existing data with SSOT V8 schema.
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

async def run_migration():
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "b2b_marketplace")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"Connected to MongoDB: {db_name}")
    print("="*60)
    
    # Get all seller_listings
    listings = await db.seller_listings.find({}).to_list(length=None)
    print(f"Found {len(listings)} seller listings to process")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for listing in listings:
        listing_id = listing["_id"]
        update_ops = {}
        unset_ops = {}
        needs_update = False
        
        # 1. Migrate pricing.slabs -> pricingTiers
        if "pricing" in listing and listing["pricing"]:
            old_pricing = listing.get("pricing", {})
            old_slabs = old_pricing.get("slabs", [])
            
            # Check if pricingTiers doesn't exist or is empty
            existing_tiers = listing.get("pricingTiers", [])
            if not existing_tiers and old_slabs:
                new_tiers = []
                for slab in old_slabs:
                    new_tiers.append({
                        "minQty": slab.get("quantity_min", slab.get("minQty", 1)),
                        "maxQty": slab.get("quantity_max", slab.get("maxQty")),
                        "pricePerUnit": slab.get("price_per_unit", slab.get("pricePerUnit", 0))
                    })
                update_ops["pricingTiers"] = new_tiers
                needs_update = True
                print(f"  [MIGRATE] {listing_id}: pricing.slabs -> pricingTiers ({len(new_tiers)} tiers)")
            
            # Mark pricing for removal
            unset_ops["pricing"] = ""
        
        # 2. Migrate availability object -> flat fields
        if "availability" in listing and listing["availability"]:
            avail = listing.get("availability", {})
            
            # Only migrate if flat fields are missing or zero
            if not listing.get("moq") and avail.get("moq"):
                update_ops["moq"] = avail.get("moq")
                needs_update = True
                print(f"  [MIGRATE] {listing_id}: availability.moq -> moq")
            
            if not listing.get("stock") and avail.get("stock"):
                update_ops["stock"] = avail.get("stock")
                needs_update = True
            
            if not listing.get("maxCapacity"):
                max_cap = avail.get("max_capacity") or avail.get("maxCapacity")
                if max_cap:
                    update_ops["maxCapacity"] = max_cap
                    needs_update = True
                    print(f"  [MIGRATE] {listing_id}: availability.max_capacity -> maxCapacity")
            
            if not listing.get("leadTime"):
                lead_time = avail.get("lead_time_days") or avail.get("leadTime")
                if lead_time:
                    update_ops["leadTime"] = lead_time
                    needs_update = True
                    print(f"  [MIGRATE] {listing_id}: availability.lead_time_days -> leadTime")
            
            # Mark availability for removal
            unset_ops["availability"] = ""
        
        # 3. Rename any remaining snake_case fields
        snake_case_fields = {
            "seller_id": "sellerId",
            "product_id": "productId", 
            "category_id": "categoryId",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "published_at": "publishedAt",
            "spec_template_id": "specTemplateId",
            "spec_template_version": "specTemplateVersion",
            "datasheet_url": "datasheetUrl",
            "price_history": "priceHistory",
            "price_audit_log": "priceAuditLog",
            "is_active": "isActive",
        }
        
        for old_key, new_key in snake_case_fields.items():
            if old_key in listing and new_key not in listing:
                update_ops[new_key] = listing[old_key]
                unset_ops[old_key] = ""
                needs_update = True
                print(f"  [RENAME] {listing_id}: {old_key} -> {new_key}")
        
        # Apply updates
        if needs_update:
            try:
                mongo_update = {}
                if update_ops:
                    mongo_update["$set"] = update_ops
                    mongo_update["$set"]["updatedAt"] = datetime.now(timezone.utc)
                if unset_ops:
                    mongo_update["$unset"] = unset_ops
                
                await db.seller_listings.update_one(
                    {"_id": listing_id},
                    mongo_update
                )
                migrated_count += 1
            except Exception as e:
                print(f"  [ERROR] {listing_id}: {e}")
                error_count += 1
        else:
            skipped_count += 1
    
    print("="*60)
    print(f"Migration Complete!")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped (already compliant): {skipped_count}")
    print(f"  Errors: {error_count}")
    
    # Verify migration
    print("\n" + "="*60)
    print("Verification Sample:")
    sample = await db.seller_listings.find_one({})
    if sample:
        print(f"  Keys in first document: {list(sample.keys())}")
        print(f"  Has pricingTiers: {'pricingTiers' in sample}")
        print(f"  Has OLD pricing: {'pricing' in sample}")
        print(f"  Has OLD availability: {'availability' in sample}")
        print(f"  Has flat moq: {'moq' in sample}")
        print(f"  Has flat leadTime: {'leadTime' in sample}")
    
    client.close()
    return migrated_count, skipped_count, error_count


if __name__ == "__main__":
    asyncio.run(run_migration())
