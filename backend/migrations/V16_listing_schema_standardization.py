"""
V16 Listing Schema Standardization Migration
=============================================

Standardizes all listing fields to snake_case:
- sellerId → seller_id
- productId → product_id
- categoryId → category_id
- sellerRole → seller_role
- maxCapacity → max_capacity
- leadTime → lead_time
- pricingTiers → pricing_tiers
- createdAt → created_at
- updatedAt → updated_at
- publishedAt → published_at
- isActive → is_active

Also migrates the collection name from seller_listings to listings (optional).
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['b2b_marketplace']
    
    print("=" * 60)
    print("V16 LISTING SCHEMA STANDARDIZATION MIGRATION")
    print("=" * 60)
    
    # Get current stats
    total_listings = await db.seller_listings.count_documents({})
    print(f"\nTotal listings in seller_listings: {total_listings}")
    
    # Check for camelCase fields that need to be renamed
    with_sellerId = await db.seller_listings.count_documents({"sellerId": {"$exists": True}})
    with_productId = await db.seller_listings.count_documents({"productId": {"$exists": True}})
    with_categoryId = await db.seller_listings.count_documents({"categoryId": {"$exists": True}})
    with_sellerRole = await db.seller_listings.count_documents({"sellerRole": {"$exists": True}})
    with_maxCapacity = await db.seller_listings.count_documents({"maxCapacity": {"$exists": True}})
    with_leadTime = await db.seller_listings.count_documents({"leadTime": {"$exists": True}})
    with_pricingTiers = await db.seller_listings.count_documents({"pricingTiers": {"$exists": True}})
    with_createdAt = await db.seller_listings.count_documents({"createdAt": {"$exists": True}})
    with_updatedAt = await db.seller_listings.count_documents({"updatedAt": {"$exists": True}})
    with_publishedAt = await db.seller_listings.count_documents({"publishedAt": {"$exists": True}})
    with_isActive = await db.seller_listings.count_documents({"isActive": {"$exists": True}})
    
    print(f"\nDocuments with camelCase fields to rename:")
    print(f"  - sellerId: {with_sellerId}")
    print(f"  - productId: {with_productId}")
    print(f"  - categoryId: {with_categoryId}")
    print(f"  - sellerRole: {with_sellerRole}")
    print(f"  - maxCapacity: {with_maxCapacity}")
    print(f"  - leadTime: {with_leadTime}")
    print(f"  - pricingTiers: {with_pricingTiers}")
    print(f"  - createdAt: {with_createdAt}")
    print(f"  - updatedAt: {with_updatedAt}")
    print(f"  - publishedAt: {with_publishedAt}")
    print(f"  - isActive: {with_isActive}")
    
    # STEP 1: Rename camelCase fields to snake_case
    print("\n--- STEP 1: Rename camelCase fields to snake_case ---")
    
    # Rename sellerId -> seller_id
    if with_sellerId > 0:
        result = await db.seller_listings.update_many(
            {"sellerId": {"$exists": True}},
            {"$rename": {"sellerId": "seller_id"}}
        )
        print(f"  Renamed sellerId -> seller_id: {result.modified_count} docs")
    
    # Rename productId -> product_id
    if with_productId > 0:
        result = await db.seller_listings.update_many(
            {"productId": {"$exists": True}},
            {"$rename": {"productId": "product_id"}}
        )
        print(f"  Renamed productId -> product_id: {result.modified_count} docs")
    
    # Rename categoryId -> category_id
    if with_categoryId > 0:
        result = await db.seller_listings.update_many(
            {"categoryId": {"$exists": True}},
            {"$rename": {"categoryId": "category_id"}}
        )
        print(f"  Renamed categoryId -> category_id: {result.modified_count} docs")
    
    # Rename sellerRole -> seller_role
    if with_sellerRole > 0:
        result = await db.seller_listings.update_many(
            {"sellerRole": {"$exists": True}},
            {"$rename": {"sellerRole": "seller_role"}}
        )
        print(f"  Renamed sellerRole -> seller_role: {result.modified_count} docs")
    
    # Rename maxCapacity -> max_capacity
    if with_maxCapacity > 0:
        result = await db.seller_listings.update_many(
            {"maxCapacity": {"$exists": True}},
            {"$rename": {"maxCapacity": "max_capacity"}}
        )
        print(f"  Renamed maxCapacity -> max_capacity: {result.modified_count} docs")
    
    # Rename leadTime -> lead_time
    if with_leadTime > 0:
        result = await db.seller_listings.update_many(
            {"leadTime": {"$exists": True}},
            {"$rename": {"leadTime": "lead_time"}}
        )
        print(f"  Renamed leadTime -> lead_time: {result.modified_count} docs")
    
    # Rename pricingTiers -> pricing_tiers
    if with_pricingTiers > 0:
        result = await db.seller_listings.update_many(
            {"pricingTiers": {"$exists": True}},
            {"$rename": {"pricingTiers": "pricing_tiers"}}
        )
        print(f"  Renamed pricingTiers -> pricing_tiers: {result.modified_count} docs")
    
    # Rename createdAt -> created_at
    if with_createdAt > 0:
        result = await db.seller_listings.update_many(
            {"createdAt": {"$exists": True}},
            {"$rename": {"createdAt": "created_at"}}
        )
        print(f"  Renamed createdAt -> created_at: {result.modified_count} docs")
    
    # Rename updatedAt -> updated_at
    if with_updatedAt > 0:
        result = await db.seller_listings.update_many(
            {"updatedAt": {"$exists": True}},
            {"$rename": {"updatedAt": "updated_at"}}
        )
        print(f"  Renamed updatedAt -> updated_at: {result.modified_count} docs")
    
    # Rename publishedAt -> published_at
    if with_publishedAt > 0:
        result = await db.seller_listings.update_many(
            {"publishedAt": {"$exists": True}},
            {"$rename": {"publishedAt": "published_at"}}
        )
        print(f"  Renamed publishedAt -> published_at: {result.modified_count} docs")
    
    # Rename isActive -> is_active
    if with_isActive > 0:
        result = await db.seller_listings.update_many(
            {"isActive": {"$exists": True}},
            {"$rename": {"isActive": "is_active"}}
        )
        print(f"  Renamed isActive -> is_active: {result.modified_count} docs")
    
    # STEP 2: Also rename nested pricing tier fields
    print("\n--- STEP 2: Rename nested pricing tier fields ---")
    
    # Update pricing_tiers array elements
    listings = await db.seller_listings.find({
        "pricing_tiers": {"$exists": True}
    }).to_list(None)
    
    updated_pricing = 0
    for listing in listings:
        pricing_tiers = listing.get("pricing_tiers", [])
        updated_tiers = []
        needs_update = False
        
        for tier in pricing_tiers:
            new_tier = {}
            # Check if using camelCase
            if "minQty" in tier:
                new_tier["min_qty"] = tier.get("minQty")
                needs_update = True
            else:
                new_tier["min_qty"] = tier.get("min_qty")
            
            if "maxQty" in tier:
                new_tier["max_qty"] = tier.get("maxQty")
                needs_update = True
            else:
                new_tier["max_qty"] = tier.get("max_qty")
            
            if "pricePerUnit" in tier:
                new_tier["price_per_unit"] = tier.get("pricePerUnit")
                needs_update = True
            else:
                new_tier["price_per_unit"] = tier.get("price_per_unit")
            
            updated_tiers.append(new_tier)
        
        if needs_update:
            await db.seller_listings.update_one(
                {"_id": listing["_id"]},
                {"$set": {"pricing_tiers": updated_tiers}}
            )
            updated_pricing += 1
    
    print(f"  Updated pricing_tiers in {updated_pricing} documents")
    
    # STEP 3: Verify the migration
    print("\n--- STEP 3: Verify migration results ---")
    
    # Check for remaining camelCase fields
    remaining_camel = await db.seller_listings.count_documents({
        "$or": [
            {"sellerId": {"$exists": True}},
            {"productId": {"$exists": True}},
            {"categoryId": {"$exists": True}},
            {"sellerRole": {"$exists": True}},
            {"maxCapacity": {"$exists": True}},
            {"leadTime": {"$exists": True}},
            {"pricingTiers": {"$exists": True}},
            {"createdAt": {"$exists": True}},
            {"updatedAt": {"$exists": True}},
            {"publishedAt": {"$exists": True}},
            {"isActive": {"$exists": True}}
        ]
    })
    
    print(f"\n  Documents still with camelCase fields: {remaining_camel}")
    
    # Check for snake_case fields
    with_snake_case = await db.seller_listings.count_documents({
        "seller_id": {"$exists": True}
    })
    print(f"  Documents with snake_case seller_id: {with_snake_case}")
    
    # Final stats
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    
    final_total = await db.seller_listings.count_documents({})
    print(f"\nTotal listings after migration: {final_total}")
    
    client.close()
    print("\nMigration finished successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
