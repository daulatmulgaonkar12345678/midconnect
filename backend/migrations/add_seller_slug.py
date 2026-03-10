"""
Migration: Add sellerSlug to existing sellers
Run once to populate sellerSlug for all existing sellers
"""
import asyncio
import re
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "midconnect")

def generate_seller_slug(business_name: str) -> str:
    """Generate SEO-friendly seller slug from business name."""
    if not business_name:
        return ""
    slug = business_name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > 90:
        slug = slug[:90].rsplit('-', 1)[0]
    return slug

async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Find all sellers without sellerSlug
    sellers = await db.users.find({
        "roles": "seller",
        "$or": [
            {"sellerSlug": {"$exists": False}},
            {"sellerSlug": None},
            {"sellerSlug": ""}
        ]
    }).to_list(1000)
    
    print(f"Found {len(sellers)} sellers without sellerSlug")
    
    # Get all existing slugs
    existing_slugs = set(await db.users.distinct("sellerSlug"))
    
    updated = 0
    for seller in sellers:
        profile = seller.get("profile") or {}
        business_name = profile.get("businessName") or seller.get("businessName") or ""
        
        if not business_name:
            print(f"  Skipping seller {seller['_id']} - no business name")
            continue
        
        base_slug = generate_seller_slug(business_name)
        
        if not base_slug:
            print(f"  Skipping seller {seller['_id']} - empty slug")
            continue
        
        # Ensure uniqueness
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(slug)
        
        # Also add platformRegistrationYear
        created_at = seller.get("createdAt")
        platform_year = created_at.year if created_at and hasattr(created_at, 'year') else 2026
        
        # Update seller
        await db.users.update_one(
            {"_id": seller["_id"]},
            {"$set": {
                "sellerSlug": slug,
                "platformRegistrationYear": platform_year
            }}
        )
        print(f"  Updated {business_name} -> {slug}")
        updated += 1
    
    print(f"\nMigration complete: {updated} sellers updated")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
