"""
Bulk SEO Update Script
======================
Regenerates SEO data (title, description, content, slug) for all products
that have weak or missing SEO fields.

Usage:
    cd /app/backend && python scripts/update_seo_for_all_products.py

Options:
    --force    Regenerate ALL products (even those with good SEO)
    --dry-run  Show what would be updated without making changes
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from motor.motor_asyncio import AsyncIOMotorClient
from services.seo_service import seo_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("seo_bulk_update")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "midconnect")


async def bulk_update_seo(force: bool = False, dry_run: bool = False):
    """Fetch all products and regenerate weak/missing SEO."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    products = await db.products.find({"isActive": {"$ne": False}}).to_list(length=10000)
    logger.info(f"Found {len(products)} active products")
    
    # Get all existing slugs for uniqueness check
    existing_slugs = await db.products.distinct("slug")
    slug_set = set(existing_slugs)
    
    updated_count = 0
    skipped_count = 0
    
    for product in products:
        product_id = product["_id"]
        product_name = product.get("name", "Unknown")
        
        # Check if SEO needs regeneration
        if not force and not seo_service.should_regenerate_seo(product):
            skipped_count += 1
            continue
        
        # Get category name
        category = None
        if product.get("categoryId"):
            category = await db.categories.find_one({"_id": product["categoryId"]})
        category_name = category.get("name") if category else None
        
        # Generate new SEO data
        new_slug = seo_service.generate_seo_slug(product_name, category_name, list(slug_set))
        new_title = seo_service.generate_seo_title(product_name, category_name)
        new_desc = seo_service.generate_seo_description(product_name, category_name, 0)
        new_content = seo_service.generate_seo_content(
            product_name, category_name,
            product.get("specifications", {}),
            product.get("description"),
            0, []
        )
        
        word_count = len(new_content.split())
        
        if dry_run:
            logger.info(f"[DRY RUN] Would update: {product_name}")
            logger.info(f"  Slug: {product.get('slug', 'MISSING')} -> {new_slug}")
            logger.info(f"  Title: {len(new_title)} chars")
            logger.info(f"  Description: {len(new_desc)} chars")
            logger.info(f"  Content: {word_count} words")
        else:
            update_data = {
                "seoTitle": new_title,
                "seoDescription": new_desc,
                "seoContent": new_content,
                "seoGeneratedAt": "bulk_update",
            }
            # Only update slug if missing or weak
            if not product.get("slug") or not product["slug"].endswith("-supplier-india"):
                update_data["slug"] = new_slug
                slug_set.add(new_slug)
            
            await db.products.update_one({"_id": product_id}, {"$set": update_data})
            logger.info(f"Updated: {product_name} ({word_count} words)")
        
        updated_count += 1
    
    logger.info(f"\nDone! Updated: {updated_count}, Skipped: {skipped_count}")
    client.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        logger.info("=== DRY RUN MODE (no changes will be made) ===")
    if force:
        logger.info("=== FORCE MODE (all products will be updated) ===")
    
    asyncio.run(bulk_update_seo(force=force, dry_run=dry_run))
