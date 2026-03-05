"""
Migration: Raw Material Calculator System Setup

This migration:
1. Creates the 'materials' collection with pre-populated data
2. Adds 'product_type' field to products (default: 'standard_product')
3. Adds 'category_type' field to categories (default: 'standard')
4. Updates 'sellerListings' schema for rate_per_kg, material_supported
5. Updates 'inquiries' schema for dimension data

Run: python migrations/002_raw_material_calculator.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "b2b_marketplace")


# Pre-populated materials with industrial standard densities
INITIAL_MATERIALS = [
    {"name": "MS Steel", "density": 7850, "description": "Mild Steel / Carbon Steel", "isActive": True},
    {"name": "SS304", "density": 7930, "description": "Stainless Steel 304", "isActive": True},
    {"name": "SS316", "density": 8000, "description": "Stainless Steel 316", "isActive": True},
    {"name": "Aluminum", "density": 2700, "description": "Aluminum Alloy", "isActive": True},
    {"name": "Copper", "density": 8960, "description": "Pure Copper", "isActive": True},
    {"name": "Brass", "density": 8500, "description": "Brass Alloy", "isActive": True},
]


async def run_migration():
    """Run the migration"""
    print("=" * 60)
    print("Raw Material Calculator System Migration")
    print("=" * 60)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # ============================================================
        # 1. CREATE MATERIALS COLLECTION
        # ============================================================
        print("\n[1/5] Setting up materials collection...")
        
        # Check if materials already exist
        existing_count = await db.materials.count_documents({})
        if existing_count > 0:
            print(f"  ⚠️  Materials collection already has {existing_count} documents")
            print("  Skipping initial material creation (already populated)")
        else:
            # Insert initial materials
            now = datetime.now(timezone.utc)
            for material in INITIAL_MATERIALS:
                material["createdAt"] = now
                material["updatedAt"] = now
            
            result = await db.materials.insert_many(INITIAL_MATERIALS)
            print(f"  ✅ Created {len(result.inserted_ids)} materials")
            
            # Create index on name
            await db.materials.create_index("name", unique=True)
            print("  ✅ Created unique index on materials.name")
        
        # ============================================================
        # 2. ADD product_type TO PRODUCTS
        # ============================================================
        print("\n[2/5] Adding product_type field to products...")
        
        # Update products without product_type
        result = await db.products.update_many(
            {"product_type": {"$exists": False}},
            {"$set": {"product_type": "standard_product"}}
        )
        print(f"  ✅ Updated {result.modified_count} products with default product_type='standard_product'")
        
        # Create index on product_type
        await db.products.create_index("product_type")
        print("  ✅ Created index on products.product_type")
        
        # ============================================================
        # 3. ADD category_type TO CATEGORIES
        # ============================================================
        print("\n[3/5] Adding category_type field to categories...")
        
        # Update categories without category_type
        result = await db.categories.update_many(
            {"category_type": {"$exists": False}},
            {"$set": {"category_type": "standard"}}
        )
        print(f"  ✅ Updated {result.modified_count} categories with default category_type='standard'")
        
        # Create index on category_type
        await db.categories.create_index("category_type")
        print("  ✅ Created index on categories.category_type")
        
        # ============================================================
        # 4. UPDATE sellerListings SCHEMA
        # ============================================================
        print("\n[4/5] Preparing sellerListings for raw material support...")
        
        # Note: We don't set defaults for rate_per_kg as it should only be set
        # for raw material listings. Just ensure the field can be queried.
        
        # Create sparse index on rate_per_kg (only index documents that have this field)
        try:
            await db.sellerListings.create_index(
                "rate_per_kg",
                sparse=True,
                name="rate_per_kg_sparse"
            )
            print("  ✅ Created sparse index on sellerListings.rate_per_kg")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ⚠️  Index already exists on sellerListings.rate_per_kg")
            else:
                print(f"  ⚠️  Warning creating index: {e}")
        
        # ============================================================
        # 5. UPDATE INQUIRIES SCHEMA
        # ============================================================
        print("\n[5/5] Preparing inquiries for dimension data...")
        
        # Create index on inquiry_type for filtering
        try:
            await db.inquiries.create_index(
                "inquiry_type",
                sparse=True,
                name="inquiry_type_sparse"
            )
            print("  ✅ Created sparse index on inquiries.inquiry_type")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ⚠️  Index already exists on inquiries.inquiry_type")
            else:
                print(f"  ⚠️  Warning creating index: {e}")
        
        # ============================================================
        # VERIFICATION
        # ============================================================
        print("\n" + "=" * 60)
        print("MIGRATION VERIFICATION")
        print("=" * 60)
        
        # Count materials
        materials_count = await db.materials.count_documents({})
        print(f"\nMaterials: {materials_count}")
        async for mat in db.materials.find({}):
            print(f"  - {mat['name']}: {mat['density']} kg/m³")
        
        # Sample product with product_type
        sample_product = await db.products.find_one({"product_type": {"$exists": True}})
        if sample_product:
            print(f"\nSample product with product_type: {sample_product.get('name', 'N/A')} -> {sample_product.get('product_type')}")
        
        # Sample category with category_type
        sample_category = await db.categories.find_one({"category_type": {"$exists": True}})
        if sample_category:
            print(f"Sample category with category_type: {sample_category.get('name', 'N/A')} -> {sample_category.get('category_type')}")
        
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
