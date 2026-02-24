"""
Enterprise DB Consistency Check Script
======================================
Verifies schema consistency across all collections.

Run this script to check for:
- Products missing specTemplateIds
- Products with empty specTemplateIds array
- Listings with empty searchableAttributes
- Listings with empty images
- Orphaned variants

Usage:
    python scripts/check_enterprise_consistency.py
    python scripts/check_enterprise_consistency.py --fix  # Apply fixes
"""

import asyncio
import argparse
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


async def check_products(db, fix: bool = False):
    """Check products for schema consistency."""
    
    print("\n" + "=" * 70)
    print("📦 PRODUCTS CONSISTENCY CHECK")
    print("=" * 70)
    
    issues = []
    
    # 1. Products missing specTemplateIds
    missing_template_ids = await db.products.count_documents({
        "specTemplateIds": {"$exists": False}
    })
    if missing_template_ids > 0:
        issues.append(f"❌ {missing_template_ids} products missing specTemplateIds field")
        if fix:
            # Try to migrate from singular specTemplateId
            async for product in db.products.find({"specTemplateIds": {"$exists": False}}):
                singular_id = product.get("specTemplateId")
                if singular_id:
                    await db.products.update_one(
                        {"_id": product["_id"]},
                        {"$set": {"specTemplateIds": [singular_id]}}
                    )
                    print(f"   ✅ Migrated product {product['_id']} from singular to array")
                else:
                    await db.products.update_one(
                        {"_id": product["_id"]},
                        {"$set": {"specTemplateIds": []}}
                    )
                    print(f"   ⚠️ Set empty specTemplateIds for product {product['_id']}")
    
    # 2. Products with empty specTemplateIds array
    empty_template_ids = await db.products.count_documents({
        "specTemplateIds": {"$size": 0}
    })
    if empty_template_ids > 0:
        issues.append(f"⚠️ {empty_template_ids} products with empty specTemplateIds array")
    
    # 3. Products still using singular specTemplateId
    using_singular = await db.products.count_documents({
        "specTemplateId": {"$exists": True}
    })
    if using_singular > 0:
        issues.append(f"⚠️ {using_singular} products still have legacy specTemplateId field")
        if fix:
            # Remove singular field after migration
            await db.products.update_many(
                {"specTemplateId": {"$exists": True}},
                {"$unset": {"specTemplateId": ""}}
            )
            print(f"   ✅ Removed legacy specTemplateId from {using_singular} products")
    
    # 4. Products missing images array
    missing_images = await db.products.count_documents({
        "images": {"$exists": False}
    })
    if missing_images > 0:
        issues.append(f"⚠️ {missing_images} products missing images array")
        if fix:
            async for product in db.products.find({"images": {"$exists": False}}):
                images = []
                if product.get("coverImageUrl"):
                    images.append(product["coverImageUrl"])
                elif product.get("imageUrl"):
                    images.append(product["imageUrl"])
                await db.products.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"images": images}}
                )
            print(f"   ✅ Set images array for {missing_images} products")
    
    if not issues:
        print("✅ All products have consistent schema")
    else:
        for issue in issues:
            print(f"   {issue}")
    
    return len(issues)


async def check_seller_listings(db, fix: bool = False):
    """Check seller listings for schema consistency."""
    
    print("\n" + "=" * 70)
    print("👤 SELLER LISTINGS CONSISTENCY CHECK")
    print("=" * 70)
    
    issues = []
    
    # 1. Listings missing searchableAttributes
    missing_attrs = await db.sellerListings.count_documents({
        "searchableAttributes": {"$exists": False}
    })
    if missing_attrs > 0:
        issues.append(f"❌ {missing_attrs} listings missing searchableAttributes field")
        if fix:
            # Try to populate from variant
            async for listing in db.sellerListings.find({"searchableAttributes": {"$exists": False}}):
                variant_id = listing.get("variantId")
                if variant_id:
                    variant = await db.productVariants.find_one({"_id": variant_id})
                    if variant and variant.get("attributes"):
                        await db.sellerListings.update_one(
                            {"_id": listing["_id"]},
                            {"$set": {"searchableAttributes": variant["attributes"]}}
                        )
                        print(f"   ✅ Populated searchableAttributes for listing {listing['_id']}")
                        continue
                await db.sellerListings.update_one(
                    {"_id": listing["_id"]},
                    {"$set": {"searchableAttributes": {}}}
                )
                print(f"   ⚠️ Set empty searchableAttributes for listing {listing['_id']}")
    
    # 2. Listings with empty searchableAttributes
    empty_attrs = await db.sellerListings.count_documents({
        "searchableAttributes": {}
    })
    if empty_attrs > 0:
        issues.append(f"⚠️ {empty_attrs} listings with empty searchableAttributes")
    
    # 3. Listings missing images
    missing_images = await db.sellerListings.count_documents({
        "$or": [
            {"images": {"$exists": False}},
            {"images": {"$size": 0}}
        ]
    })
    if missing_images > 0:
        issues.append(f"❌ {missing_images} listings missing/empty images array")
    
    # 4. Active listings with incomplete data
    incomplete_active = await db.sellerListings.count_documents({
        "status": "active",
        "$or": [
            {"searchableAttributes": {}},
            {"images": {"$size": 0}},
            {"pricingTiers": {"$size": 0}}
        ]
    })
    if incomplete_active > 0:
        issues.append(f"🚨 {incomplete_active} ACTIVE listings with incomplete data!")
        if fix:
            # Deactivate incomplete active listings
            result = await db.sellerListings.update_many(
                {
                    "status": "active",
                    "$or": [
                        {"searchableAttributes": {}},
                        {"images": {"$size": 0}},
                        {"pricingTiers": {"$size": 0}}
                    ]
                },
                {"$set": {"status": "draft", "isActive": False}}
            )
            print(f"   ✅ Deactivated {result.modified_count} incomplete listings")
    
    if not issues:
        print("✅ All seller listings have consistent schema")
    else:
        for issue in issues:
            print(f"   {issue}")
    
    return len(issues)


async def check_product_variants(db, fix: bool = False):
    """Check product variants for schema consistency."""
    
    print("\n" + "=" * 70)
    print("🔧 PRODUCT VARIANTS CONSISTENCY CHECK")
    print("=" * 70)
    
    issues = []
    
    # 1. Variants missing attributes
    missing_attrs = await db.productVariants.count_documents({
        "attributes": {"$exists": False}
    })
    if missing_attrs > 0:
        issues.append(f"⚠️ {missing_attrs} variants missing attributes field")
        if fix:
            await db.productVariants.update_many(
                {"attributes": {"$exists": False}},
                {"$set": {"attributes": {}}}
            )
            print(f"   ✅ Set empty attributes for {missing_attrs} variants")
    
    # 2. Variants with empty attributes
    empty_attrs = await db.productVariants.count_documents({
        "attributes": {}
    })
    if empty_attrs > 0:
        issues.append(f"⚠️ {empty_attrs} variants with empty attributes")
    
    # 3. Orphaned variants (no product reference)
    orphaned = 0
    async for variant in db.productVariants.find({}):
        product_id = variant.get("productId")
        if product_id:
            product = await db.products.find_one({"_id": product_id})
            if not product:
                orphaned += 1
                if fix:
                    await db.productVariants.delete_one({"_id": variant["_id"]})
                    print(f"   🗑️ Deleted orphaned variant {variant['_id']}")
    
    if orphaned > 0:
        issues.append(f"🗑️ {orphaned} orphaned variants (no product found)")
    
    if not issues:
        print("✅ All product variants have consistent schema")
    else:
        for issue in issues:
            print(f"   {issue}")
    
    return len(issues)


async def create_indexes(db):
    """Create enterprise indexes."""
    
    print("\n" + "=" * 70)
    print("📊 CREATING ENTERPRISE INDEXES")
    print("=" * 70)
    
    # sellerListings indexes
    await db.sellerListings.create_index([
        ("productId", 1),
        ("variantId", 1),
        ("status", 1)
    ], name="enterprise_product_variant_status")
    print("   ✅ Created sellerListings.enterprise_product_variant_status index")
    
    await db.sellerListings.create_index([
        ("sellerId", 1),
        ("status", 1)
    ], name="enterprise_seller_status")
    print("   ✅ Created sellerListings.enterprise_seller_status index")
    
    # products indexes
    await db.products.create_index([
        ("specTemplateIds", 1)
    ], name="enterprise_spec_template_ids")
    print("   ✅ Created products.enterprise_spec_template_ids index")
    
    print("\n✅ Enterprise indexes created")


async def main():
    parser = argparse.ArgumentParser(description="Check enterprise DB consistency")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--indexes", action="store_true", help="Create indexes only")
    args = parser.parse_args()
    
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    if not mongo_url:
        print("❌ MONGO_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 70)
    print("🏗 ENTERPRISE DB CONSISTENCY CHECK")
    print(f"   Database: {db_name}")
    print(f"   Fix Mode: {args.fix}")
    print("=" * 70)
    
    try:
        if args.indexes:
            await create_indexes(db)
            return
        
        total_issues = 0
        
        total_issues += await check_products(db, fix=args.fix)
        total_issues += await check_seller_listings(db, fix=args.fix)
        total_issues += await check_product_variants(db, fix=args.fix)
        
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        
        if total_issues == 0:
            print("✅ All collections have consistent schema!")
        else:
            print(f"⚠️ Found {total_issues} schema issues")
            if not args.fix:
                print("   Run with --fix to attempt automatic fixes")
        
        # Collection stats
        print("\n📊 COLLECTION COUNTS:")
        products = await db.products.count_documents({})
        variants = await db.productVariants.count_documents({})
        listings = await db.sellerListings.count_documents({})
        templates = await db.specTemplates.count_documents({})
        
        print(f"   Products: {products}")
        print(f"   ProductVariants: {variants}")
        print(f"   SellerListings: {listings}")
        print(f"   SpecTemplates: {templates}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
