"""
Migration V5: Sync Product Slugs and Validate Data Integrity

PURPOSE:
- Add slugs to all products that don't have them
- Ensure is_active field is consistent (default to True if missing)
- Validate all category_id references exist
- Report any data integrity issues

This migration is SAFE to run multiple times (idempotent).

RUN: python migrations/V5_sync_product_slugs.py
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
    db = client[os.getenv("DB_NAME", "b2b_marketplace").strip()]
    
    print("=" * 70)
    print("MIGRATION V5: Sync Product Slugs and Validate Data Integrity")
    print(f"Database: {db.name}")
    print("=" * 70)
    
    # ==================== STEP 1: Load all categories ====================
    print("\n[STEP 1] Loading categories...")
    categories = await db.categories.find({}).to_list(1000)
    category_ids = {str(c["_id"]) for c in categories}
    print(f"  Found {len(categories)} categories:")
    for c in categories:
        print(f"    - {c.get('_id')} | {c.get('name')}")
    
    # ==================== STEP 2: Load all products ====================
    print("\n[STEP 2] Loading products...")
    products = await db.products.find({}).to_list(1000)
    print(f"  Found {len(products)} products")
    
    # ==================== STEP 3: Validate and fix products ====================
    print("\n[STEP 3] Validating and fixing products...")
    
    slug_counts = {}  # Track slug usage for collision handling
    updates = []
    issues = []
    
    # First pass: collect existing slugs
    for product in products:
        existing_slug = product.get("slug")
        if existing_slug:
            slug_counts[existing_slug] = slug_counts.get(existing_slug, 0) + 1
    
    # Second pass: validate and prepare updates
    for product in products:
        product_id = product["_id"]
        name = product.get("name", "")
        existing_slug = product.get("slug")
        is_active = product.get("is_active")
        active = product.get("active")
        category_id = product.get("category_id")
        
        update_fields = {}
        
        # --- Check slug ---
        if not existing_slug:
            base_slug = generate_slug(name)
            if base_slug:
                # Handle collision
                final_slug = base_slug
                counter = 1
                while final_slug in slug_counts:
                    final_slug = f"{base_slug}-{counter}"
                    counter += 1
                slug_counts[final_slug] = 1
                update_fields["slug"] = final_slug
                print(f"  [SLUG] {name} -> {final_slug}")
            else:
                issues.append(f"Product {product_id} has no name, cannot generate slug")
        
        # --- Check is_active ---
        if is_active is None:
            # Default: use 'active' field if exists, else True
            new_is_active = active if active is not None else True
            update_fields["is_active"] = new_is_active
            print(f"  [IS_ACTIVE] {name} -> {new_is_active}")
        
        # --- Validate category_id ---
        if category_id:
            cat_id_str = str(category_id)
            if cat_id_str not in category_ids:
                issues.append(f"Product '{name}' ({product_id}) has invalid category_id: {category_id}")
        else:
            issues.append(f"Product '{name}' ({product_id}) has no category_id")
        
        # Queue update if needed
        if update_fields:
            updates.append({
                "_id": product_id,
                "name": name,
                "updates": update_fields
            })
    
    # ==================== STEP 4: Apply updates ====================
    if updates:
        print(f"\n[STEP 4] Applying {len(updates)} updates...")
        for update in updates:
            await db.products.update_one(
                {"_id": update["_id"]},
                {"$set": update["updates"]}
            )
            print(f"  Updated: {update['name']}")
        print(f"  ✓ Applied {len(updates)} updates")
    else:
        print("\n[STEP 4] No updates needed - all products valid")
    
    # ==================== STEP 5: Create/verify unique index ====================
    print("\n[STEP 5] Ensuring unique index on products.slug...")
    try:
        await db.products.create_index(
            "slug",
            unique=True,
            sparse=True,  # Allow null for products without slug
            name="unique_product_slug"
        )
        print("  ✓ Index created/verified: unique_product_slug")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Index already exists")
        else:
            print(f"  Error creating index: {e}")
    
    # ==================== STEP 6: Report issues ====================
    if issues:
        print(f"\n[ISSUES] Found {len(issues)} data integrity issues:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("\n[ISSUES] No data integrity issues found")
    
    # ==================== STEP 7: Final verification ====================
    print("\n[STEP 7] Final verification...")
    products_with_slug = await db.products.count_documents({"slug": {"$exists": True, "$ne": None, "$ne": ""}})
    products_active = await db.products.count_documents({"is_active": True})
    products_inactive = await db.products.count_documents({"is_active": False})
    
    print(f"  Products with slug: {products_with_slug}")
    print(f"  Products active: {products_active}")
    print(f"  Products inactive: {products_inactive}")
    
    # Show sample products
    print("\n[SAMPLE] First 10 products after migration:")
    sample_products = await db.products.find({}).limit(10).to_list(10)
    for p in sample_products:
        print(f"  {p.get('_id')} | {p.get('name')}")
        print(f"    slug: {p.get('slug', 'MISSING')}")
        print(f"    is_active: {p.get('is_active')}")
        print(f"    category_id: {p.get('category_id')}")
    
    client.close()
    print("\n" + "=" * 70)
    print("Migration V5 complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_migration())
