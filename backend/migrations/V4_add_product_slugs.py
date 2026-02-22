"""
Migration V4: Add Product Slugs

PURPOSE:
- Generate unique slugs for all products
- Create unique index on products.slug
- Slugs are used for SEO-friendly URLs

SLUG RULES:
- lowercase
- hyphen-separated
- derived from product name
- unique (append number if collision)
- immutable after creation

RUN: python migrations/V4_add_product_slugs.py
"""

import asyncio
import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()


def generate_slug(name: str) -> str:
    """
    Generate URL-friendly slug from product name.
    
    Rules:
    - lowercase
    - replace spaces and special chars with hyphens
    - remove consecutive hyphens
    - trim hyphens from start/end
    """
    if not name:
        return ""
    
    # Convert to lowercase
    slug = name.lower()
    
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Trim hyphens from start/end
    slug = slug.strip('-')
    
    return slug


async def run_migration():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL").strip())
    db = client[os.getenv("DB_NAME", "midconnect").strip()]
    
    print("=" * 60)
    print("MIGRATION V4: Add Product Slugs")
    print("=" * 60)
    
    # Step 1: Get all products
    products = await db.products.find({}).to_list(1000)
    print(f"\nFound {len(products)} products to process")
    
    # Step 2: Generate slugs and handle collisions
    slug_counts = {}  # Track slug usage for collision handling
    updates = []
    
    for product in products:
        name = product.get("name", "")
        existing_slug = product.get("slug")
        
        if existing_slug:
            print(f"  [SKIP] {name} - already has slug: {existing_slug}")
            slug_counts[existing_slug] = slug_counts.get(existing_slug, 0) + 1
            continue
        
        base_slug = generate_slug(name)
        
        if not base_slug:
            print(f"  [WARN] {name} - could not generate slug")
            continue
        
        # Handle collision
        final_slug = base_slug
        counter = 1
        while final_slug in slug_counts:
            final_slug = f"{base_slug}-{counter}"
            counter += 1
        
        slug_counts[final_slug] = 1
        updates.append({
            "_id": product["_id"],
            "slug": final_slug
        })
        print(f"  [OK] {name} -> {final_slug}")
    
    # Step 3: Apply updates
    if updates:
        print(f"\nApplying {len(updates)} slug updates...")
        for update in updates:
            await db.products.update_one(
                {"_id": update["_id"]},
                {"$set": {"slug": update["slug"]}}
            )
        print(f"  Updated {len(updates)} products")
    else:
        print("\n  No updates needed - all products have slugs")
    
    # Step 4: Create unique index on slug
    print("\nCreating unique index on products.slug...")
    try:
        await db.products.create_index(
            "slug",
            unique=True,
            sparse=True,  # Allow null for legacy products
            name="unique_product_slug"
        )
        print("  Index created: unique_product_slug")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Index already exists")
        else:
            print(f"  Error creating index: {e}")
    
    # Step 5: Verify
    print("\nVerification:")
    products_with_slug = await db.products.count_documents({"slug": {"$exists": True, "$ne": None}})
    products_without_slug = await db.products.count_documents({"$or": [{"slug": {"$exists": False}}, {"slug": None}]})
    print(f"  Products with slug: {products_with_slug}")
    print(f"  Products without slug: {products_without_slug}")
    
    # Show sample
    print("\nSample products with slugs:")
    samples = await db.products.find({"slug": {"$exists": True}}).limit(5).to_list(5)
    for s in samples:
        print(f"  {s.get('_id')} | {s.get('name')} | slug: {s.get('slug')}")
    
    client.close()
    print("\n" + "=" * 60)
    print("Migration V4 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_migration())
