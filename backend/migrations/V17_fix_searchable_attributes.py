"""
V17 Fix searchableAttributes Data Alignment
============================================

This migration fixes the data alignment issue where:
1. sellerListings have empty searchableAttributes {}
2. But the linked productVariants have valid attributes

The fix:
- For each sellerListing with empty searchableAttributes
- Look up the linked variantId in productVariants
- Copy the variant's attributes to sellerListing.searchableAttributes

Also ensures:
- specTemplates.categoryId is stored as ObjectId (not string)
- Products.specTemplateIds reference valid templates
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

load_dotenv()


def to_objectid(value):
    """Safely convert to ObjectId"""
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except InvalidId:
            return None
    return None


async def run_migration():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.environ.get('DB_NAME', 'b2b_marketplace')
    db = client[db_name]
    print(f"Using database: {db_name}")
    
    print("=" * 70)
    print("V17 FIX SEARCHABLE ATTRIBUTES DATA ALIGNMENT")
    print("=" * 70)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    # Track stats
    stats = {
        "listings_checked": 0,
        "listings_fixed": 0,
        "listings_skipped_no_variant": 0,
        "listings_skipped_variant_empty": 0,
        "spec_templates_fixed": 0,
        "products_with_invalid_template": 0,
    }
    
    # =====================================================
    # PHASE 1: Fix sellerListings.searchableAttributes
    # =====================================================
    print("\n--- PHASE 1: Fix sellerListings.searchableAttributes ---")
    
    # Find all listings with empty or missing searchableAttributes
    empty_searchable_query = {
        "$or": [
            {"searchableAttributes": {"$exists": False}},
            {"searchableAttributes": {}},
            {"searchableAttributes": None}
        ]
    }
    
    listings_to_fix = await db.sellerListings.find(empty_searchable_query).to_list(None)
    print(f"Found {len(listings_to_fix)} listings with empty searchableAttributes")
    
    for listing in listings_to_fix:
        stats["listings_checked"] += 1
        listing_id = listing["_id"]
        variant_id = listing.get("variantId")
        
        if not variant_id:
            print(f"  [SKIP] Listing {listing_id}: no variantId")
            stats["listings_skipped_no_variant"] += 1
            continue
        
        # Get the variant
        variant_oid = to_objectid(variant_id)
        if not variant_oid:
            print(f"  [SKIP] Listing {listing_id}: invalid variantId format")
            stats["listings_skipped_no_variant"] += 1
            continue
        
        variant = await db.productVariants.find_one({"_id": variant_oid})
        if not variant:
            print(f"  [SKIP] Listing {listing_id}: variant {variant_oid} not found")
            stats["listings_skipped_no_variant"] += 1
            continue
        
        # Get attributes from variant
        variant_attrs = variant.get("attributes", {})
        if not variant_attrs or len(variant_attrs) == 0:
            print(f"  [SKIP] Listing {listing_id}: variant {variant_oid} has no attributes")
            stats["listings_skipped_variant_empty"] += 1
            continue
        
        # Update the listing with variant attributes
        update_result = await db.sellerListings.update_one(
            {"_id": listing_id},
            {
                "$set": {
                    "searchableAttributes": variant_attrs,
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        if update_result.modified_count > 0:
            print(f"  [FIXED] Listing {listing_id}: copied {len(variant_attrs)} attributes from variant")
            stats["listings_fixed"] += 1
        else:
            print(f"  [WARN] Listing {listing_id}: update returned 0 modified")
    
    # =====================================================
    # PHASE 2: Fix specTemplates.categoryId type
    # =====================================================
    print("\n--- PHASE 2: Fix specTemplates.categoryId type ---")
    
    # Find templates where categoryId is a string instead of ObjectId
    templates = await db.specTemplates.find({}).to_list(None)
    print(f"Checking {len(templates)} spec templates...")
    
    for template in templates:
        template_id = template["_id"]
        category_id = template.get("categoryId")
        
        if category_id is None:
            print(f"  [WARN] Template {template_id}: no categoryId")
            continue
        
        # Check if it's a string that should be ObjectId
        if isinstance(category_id, str):
            category_oid = to_objectid(category_id)
            if category_oid:
                await db.specTemplates.update_one(
                    {"_id": template_id},
                    {"$set": {"categoryId": category_oid}}
                )
                print(f"  [FIXED] Template {template_id}: converted categoryId to ObjectId")
                stats["spec_templates_fixed"] += 1
            else:
                print(f"  [WARN] Template {template_id}: categoryId '{category_id}' is not valid ObjectId")
    
    # =====================================================
    # PHASE 3: Validate products.specTemplateIds references
    # =====================================================
    print("\n--- PHASE 3: Validate products.specTemplateIds references ---")
    
    products = await db.products.find({"specTemplateIds": {"$exists": True, "$ne": []}}).to_list(None)
    print(f"Checking {len(products)} products with specTemplateIds...")
    
    for product in products:
        product_id = product["_id"]
        template_ids = product.get("specTemplateIds", [])
        
        for template_id in template_ids:
            template_oid = to_objectid(template_id)
            if not template_oid:
                print(f"  [WARN] Product {product_id}: invalid template ID format in specTemplateIds")
                stats["products_with_invalid_template"] += 1
                continue
            
            # Check if template exists
            template = await db.specTemplates.find_one({"_id": template_oid})
            if not template:
                print(f"  [WARN] Product {product_id}: references non-existent template {template_oid}")
                stats["products_with_invalid_template"] += 1
    
    # =====================================================
    # PHASE 4: Verify fixes
    # =====================================================
    print("\n--- PHASE 4: Verify fixes ---")
    
    # Count remaining empty searchableAttributes
    remaining_empty = await db.sellerListings.count_documents(empty_searchable_query)
    print(f"Remaining listings with empty searchableAttributes: {remaining_empty}")
    
    # Count listings with valid searchableAttributes
    valid_attrs = await db.sellerListings.count_documents({
        "searchableAttributes": {"$exists": True, "$ne": {}, "$type": "object"}
    })
    print(f"Listings with valid searchableAttributes: {valid_attrs}")
    
    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Listings checked: {stats['listings_checked']}")
    print(f"Listings fixed: {stats['listings_fixed']}")
    print(f"Listings skipped (no variant): {stats['listings_skipped_no_variant']}")
    print(f"Listings skipped (variant empty): {stats['listings_skipped_variant_empty']}")
    print(f"Spec templates fixed (categoryId type): {stats['spec_templates_fixed']}")
    print(f"Products with invalid template refs: {stats['products_with_invalid_template']}")
    print(f"\nCompleted at: {datetime.now(timezone.utc).isoformat()}")
    
    client.close()
    print("\nMigration finished!")
    
    return stats


if __name__ == "__main__":
    asyncio.run(run_migration())
