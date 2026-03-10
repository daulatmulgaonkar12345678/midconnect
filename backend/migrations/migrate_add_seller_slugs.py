"""
Migration Script: Add sellerSlug to ALL Existing Sellers
=========================================================

Run this script on your production database after deploying 
the new code to add sellerSlug to all existing sellers.

This will make all seller names clickable across the platform.

Usage:
    MONGO_URL="your_production_mongo_url" python3 migrate_add_seller_slugs.py
"""

import asyncio
import re
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "midconnect")

if not MONGO_URL:
    print("ERROR: MONGO_URL environment variable is required")
    print("Usage: MONGO_URL='mongodb://...' python3 migrate_add_seller_slugs.py")
    exit(1)


def generate_seller_slug(business_name: str) -> str:
    """
    Generate SEO-friendly seller slug from business name.
    
    Examples:
    - "C N B LEATHER WORKS" -> "c-n-b-leather-works"
    - "ECO SHINE INDUSTRIES" -> "eco-shine-industries"
    - "Sharma & Sons Trading Co." -> "sharma-sons-trading-co"
    """
    if not business_name:
        return ""
    
    # Convert to lowercase
    slug = business_name.lower().strip()
    
    # Remove special characters except spaces and hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    
    # Replace multiple spaces/hyphens with single hyphen
    slug = re.sub(r'[\s-]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit to 90 characters (don't cut mid-word)
    if len(slug) > 90:
        slug = slug[:90].rsplit('-', 1)[0]
    
    return slug


async def migrate_sellers():
    """Add sellerSlug to all sellers without one."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 60)
    print("SELLER SLUG MIGRATION")
    print("=" * 60)
    
    # Find all sellers in users collection
    sellers = await db.users.find({
        "roles": "seller"
    }).to_list(10000)
    
    print(f"\nFound {len(sellers)} sellers in users collection")
    
    # Get all existing slugs to ensure uniqueness
    existing_slugs = set()
    for s in sellers:
        if s.get("sellerSlug"):
            existing_slugs.add(s["sellerSlug"])
    
    print(f"Existing slugs: {len(existing_slugs)}")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for seller in sellers:
        seller_id = seller["_id"]
        
        # Get business name from profile
        profile = seller.get("profile") or {}
        business_name = profile.get("businessName") or seller.get("businessName") or ""
        
        # Check if already has slug
        if seller.get("sellerSlug"):
            print(f"  [SKIP] {business_name or 'Unknown'} - already has slug: {seller['sellerSlug']}")
            skipped_count += 1
            continue
        
        if not business_name:
            print(f"  [SKIP] Seller {seller_id} - no business name")
            skipped_count += 1
            continue
        
        # Generate slug
        base_slug = generate_seller_slug(business_name)
        
        if not base_slug:
            print(f"  [ERROR] Could not generate slug for: {business_name}")
            error_count += 1
            continue
        
        # Ensure uniqueness
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(slug)
        
        # Get platform registration year from createdAt
        created_at = seller.get("createdAt")
        platform_year = None
        if created_at and hasattr(created_at, 'year'):
            platform_year = created_at.year
        
        # Update seller
        update_fields = {"sellerSlug": slug}
        if platform_year:
            update_fields["platformRegistrationYear"] = platform_year
        
        await db.users.update_one(
            {"_id": seller_id},
            {"$set": update_fields}
        )
        
        print(f"  [OK] {business_name} -> {slug}")
        updated_count += 1
    
    # Also check sellers collection (legacy)
    print(f"\nChecking legacy sellers collection...")
    legacy_sellers = await db.sellers.find({}).to_list(10000)
    
    for seller in legacy_sellers:
        if seller.get("sellerSlug"):
            continue
        
        business_name = seller.get("businessName") or ""
        if not business_name:
            continue
        
        base_slug = generate_seller_slug(business_name)
        if not base_slug:
            continue
        
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(slug)
        
        await db.sellers.update_one(
            {"_id": seller["_id"]},
            {"$set": {"sellerSlug": slug}}
        )
        
        print(f"  [LEGACY] {business_name} -> {slug}")
        updated_count += 1
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors:  {error_count}")
    print("=" * 60)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate_sellers())
