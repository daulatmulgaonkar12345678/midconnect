"""
Migration Script: FINAL MARKETPLACE ARCHITECTURE
=================================================
Migrates to 4-layer model:
1. specTemplates (keep as SSOT)
2. products (add specTemplateId)
3. productVariants (NEW - create from existing specifications)
4. sellerListings (add variantId, remove specifications)

This migration:
1. Creates productVariants collection with indexes
2. For each existing sellerListing with specifications:
   - Create or reuse productVariant
   - Add variantId to listing
   - Remove specifications from listing
3. Updates sellerListings schema

Idempotent - safe to run multiple times.
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
    print("FINAL MARKETPLACE ARCHITECTURE MIGRATION")
    print("="*60)
    
    # ==================== STEP 1: Create Indexes ====================
    print("\n[STEP 1] Creating indexes...")
    
    # productVariants indexes
    try:
        await db.productVariants.create_index("productId", name="productId_1")
        await db.productVariants.create_index(
            [("productId", 1), ("specTemplateId", 1)],
            name="productId_specTemplateId"
        )
        await db.productVariants.create_index("attributes.power", name="attributes_power", sparse=True)
        await db.productVariants.create_index("attributes.voltage", name="attributes_voltage", sparse=True)
        await db.productVariants.create_index("createdAt", name="createdAt_1")
        print("  ✅ productVariants indexes created")
    except Exception as e:
        print(f"  ⚠️ productVariants index warning: {e}")
    
    # products text index
    try:
        await db.products.create_index(
            [("name", "text")],
            name="name_text"
        )
        print("  ✅ products text index created")
    except Exception as e:
        print(f"  ⚠️ products text index warning: {e}")
    
    # sellerListings indexes
    try:
        await db.sellerListings.create_index("variantId", name="variantId_1")
        await db.sellerListings.create_index("sellerId", name="sellerId_1")
        await db.sellerListings.create_index("status", name="status_1")
        await db.sellerListings.create_index("updatedAt", name="updatedAt_1")
        print("  ✅ sellerListings indexes created")
    except Exception as e:
        print(f"  ⚠️ sellerListings index warning: {e}")
    
    # Also create indexes on legacy collection name
    try:
        await db.seller_listings.create_index("variantId", name="variantId_1")
        print("  ✅ seller_listings (legacy) variantId index created")
    except Exception as e:
        print(f"  ⚠️ seller_listings index warning: {e}")
    
    # ==================== STEP 2: Migrate Existing Listings ====================
    print("\n[STEP 2] Migrating existing listings to use variantId...")
    
    # Try both collection names
    listings = []
    
    # Check new collection name
    new_count = await db.sellerListings.count_documents({})
    if new_count > 0:
        listings.extend(await db.sellerListings.find({}).to_list(length=None))
        print(f"  Found {new_count} listings in sellerListings collection")
    
    # Check legacy collection name
    legacy_count = await db.seller_listings.count_documents({})
    if legacy_count > 0:
        listings.extend(await db.seller_listings.find({}).to_list(length=None))
        print(f"  Found {legacy_count} listings in seller_listings collection")
    
    print(f"  Total listings to process: {len(listings)}")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for listing in listings:
        listing_id = listing["_id"]
        
        # Skip if already has variantId
        if listing.get("variantId"):
            skipped += 1
            continue
        
        # Get product info
        product_id = listing.get("productId")
        if not product_id:
            print(f"  ⚠️ Listing {listing_id} has no productId - skipping")
            errors += 1
            continue
        
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        product = await db.products.find_one({"_id": product_id})
        if not product:
            print(f"  ⚠️ Listing {listing_id} - product not found: {product_id}")
            errors += 1
            continue
        
        # Get spec template ID
        template_id = product.get("specTemplateId")
        if not template_id:
            template_ids = product.get("specTemplateIds", [])
            if template_ids:
                template_id = template_ids[0]
        
        if not template_id:
            # Try to find template by category
            category_id = product.get("categoryId")
            if category_id:
                template = await db.specTemplates.find_one({"categoryId": category_id})
                if not template:
                    template = await db.spec_templates.find_one({
                        "$or": [
                            {"categoryId": str(category_id)},
                            {"category_id": str(category_id)}
                        ]
                    })
                if template:
                    template_id = str(template["_id"])
        
        if not template_id:
            print(f"  ⚠️ Listing {listing_id} - no spec template found")
            errors += 1
            continue
        
        # Get attributes from existing specifications or pricingTiers
        attributes = listing.get("specifications", {})
        
        # If no specifications, create minimal attributes from variant data
        if not attributes:
            # Try to infer from any available data
            attributes = {}
            if listing.get("moq"):
                pass  # moq is commercial, not attribute
        
        # Normalize attributes
        normalized_attrs = {}
        for key in sorted(attributes.keys()):
            value = attributes[key]
            if isinstance(value, str):
                value = value.strip()
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
            normalized_attrs[key] = value
        
        if isinstance(template_id, str):
            template_oid = ObjectId(template_id)
        else:
            template_oid = template_id
        
        # Check for existing variant with same attributes
        existing_variant = await db.productVariants.find_one({
            "productId": product_id,
            "attributes": normalized_attrs
        })
        
        if existing_variant:
            variant_id = existing_variant["_id"]
            print(f"  📦 Reusing variant {variant_id} for listing {listing_id}")
        else:
            # Create new variant
            now = datetime.now(timezone.utc)
            variant_doc = {
                "_id": ObjectId(),
                "productId": product_id,
                "specTemplateId": template_oid,
                "attributes": normalized_attrs,
                "createdAt": now
            }
            await db.productVariants.insert_one(variant_doc)
            variant_id = variant_doc["_id"]
            print(f"  ✨ Created variant {variant_id} for listing {listing_id}")
        
        # Update listing with variantId
        update_ops = {
            "$set": {
                "variantId": variant_id,
                "updatedAt": datetime.now(timezone.utc)
            }
        }
        
        # Optionally remove specifications (keep for backward compat during transition)
        # update_ops["$unset"] = {"specifications": ""}
        
        # Determine which collection has this listing
        if await db.sellerListings.count_documents({"_id": listing_id}) > 0:
            await db.sellerListings.update_one({"_id": listing_id}, update_ops)
        else:
            await db.seller_listings.update_one({"_id": listing_id}, update_ops)
        
        migrated += 1
    
    print(f"\n  Migration Summary:")
    print(f"    Migrated: {migrated}")
    print(f"    Skipped (already had variantId): {skipped}")
    print(f"    Errors: {errors}")
    
    # ==================== STEP 3: Update Products with specTemplateId ====================
    print("\n[STEP 3] Ensuring products have specTemplateId...")
    
    products = await db.products.find({}).to_list(length=None)
    updated_products = 0
    
    for product in products:
        product_id = product["_id"]
        
        # Skip if already has specTemplateId
        if product.get("specTemplateId"):
            continue
        
        # Try to get from specTemplateIds array
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            template_id = template_ids[0]
            await db.products.update_one(
                {"_id": product_id},
                {"$set": {"specTemplateId": template_id}}
            )
            updated_products += 1
            print(f"  ✅ Product {product_id}: set specTemplateId from array")
            continue
        
        # Try to find template by category
        category_id = product.get("categoryId")
        if category_id:
            if isinstance(category_id, str):
                category_id = ObjectId(category_id)
            
            template = await db.specTemplates.find_one({"categoryId": category_id})
            if not template:
                template = await db.spec_templates.find_one({
                    "$or": [
                        {"categoryId": str(category_id)},
                        {"category_id": str(category_id)}
                    ]
                })
            
            if template:
                await db.products.update_one(
                    {"_id": product_id},
                    {"$set": {"specTemplateId": str(template["_id"])}}
                )
                updated_products += 1
                print(f"  ✅ Product {product_id}: found template by category")
    
    print(f"  Updated {updated_products} products with specTemplateId")
    
    # ==================== STEP 4: Verify Migration ====================
    print("\n[STEP 4] Verification...")
    
    # Count productVariants
    variant_count = await db.productVariants.count_documents({})
    print(f"  productVariants: {variant_count} documents")
    
    # Count listings with variantId
    listings_with_variant = await db.sellerListings.count_documents({"variantId": {"$exists": True}})
    listings_with_variant += await db.seller_listings.count_documents({"variantId": {"$exists": True}})
    total_listings = await db.sellerListings.count_documents({})
    total_listings += await db.seller_listings.count_documents({})
    
    print(f"  Listings with variantId: {listings_with_variant}/{total_listings}")
    
    # Count products with specTemplateId
    products_with_template = await db.products.count_documents({"specTemplateId": {"$exists": True}})
    total_products = await db.products.count_documents({})
    print(f"  Products with specTemplateId: {products_with_template}/{total_products}")
    
    # Sample data
    print("\n  Sample productVariant:")
    sample_variant = await db.productVariants.find_one({})
    if sample_variant:
        print(f"    _id: {sample_variant['_id']}")
        print(f"    productId: {sample_variant.get('productId')}")
        print(f"    attributes: {sample_variant.get('attributes')}")
    else:
        print("    No variants found")
    
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    
    client.close()
    return migrated, skipped, errors


if __name__ == "__main__":
    asyncio.run(run_migration())
