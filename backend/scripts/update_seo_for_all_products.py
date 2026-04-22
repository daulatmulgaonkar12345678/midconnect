"""
Bulk SEO Update Script (v3)
===========================
Regenerates SEO data for products that have:
- seoVersion < SEO_VERSION (current)
- weak/missing seoTitle, seoDescription, seoContent, slug
- seoContent with < 400 words OR missing FAQ/JSON-LD hints
- --force flag (regenerate everything, even manually edited)

Writes:
- seoTitle, seoDescription, seoContent, slug (if missing/weak)
- seoVersion = SEO_VERSION
- seoGeneratedAt = ISO timestamp

Usage:
    cd /app/backend && python scripts/update_seo_for_all_products.py
    cd /app/backend && python scripts/update_seo_for_all_products.py --dry-run
    cd /app/backend && python scripts/update_seo_for_all_products.py --force
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from motor.motor_asyncio import AsyncIOMotorClient
from services.seo_service import seo_service, SEO_VERSION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("seo_bulk_update")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "midconnect")


def needs_regeneration(product: dict, force: bool) -> tuple[bool, str]:
    """Return (needs_update, reason)."""
    if force:
        return True, "force flag"

    # Respect manual edits
    if product.get("seoManuallyEdited"):
        return False, "manually edited"

    # Version check — primary trigger for bulk upgrades
    current_version = product.get("seoVersion", 0) or 0
    if current_version < SEO_VERSION:
        return True, f"seoVersion {current_version} < {SEO_VERSION}"

    # Weak content checks
    seo_title = product.get("seoTitle") or ""
    seo_desc = product.get("seoDescription") or ""
    seo_content = product.get("seoContent") or ""
    slug = product.get("slug") or ""

    if not seo_title or len(seo_title) < 30:
        return True, "weak title"
    if not seo_desc or len(seo_desc) < 120:
        return True, "weak description"
    if not seo_content:
        return True, "missing content"

    word_count = len(seo_content.split())
    if word_count < 400:
        return True, f"content only {word_count} words"

    # Require FAQ section presence
    if "frequently asked" not in seo_content.lower() and "faq" not in seo_content.lower():
        return True, "missing FAQ"

    if not slug:
        return True, "missing slug"

    return False, "fresh"


async def bulk_update_seo(force: bool = False, dry_run: bool = False):
    """Fetch all products and regenerate weak/missing/out-of-version SEO."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    products = await db.products.find({"isActive": {"$ne": False}}).to_list(length=20000)
    logger.info(f"Found {len(products)} active products. Target SEO_VERSION={SEO_VERSION}")

    # Slugs for uniqueness (we'll pop each product's own slug when regenerating)
    existing_slugs = await db.products.distinct("slug")
    slug_set = set(s for s in existing_slugs if s)

    updated_count = 0
    skipped_count = 0
    reason_counts: dict = {}

    for product in products:
        product_id = product["_id"]
        product_name = product.get("name", "Unknown")

        needs, reason = needs_regeneration(product, force)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if not needs:
            skipped_count += 1
            continue

        # Get category
        category = None
        if product.get("categoryId"):
            try:
                category = await db.categories.find_one({"_id": product["categoryId"]})
            except Exception:
                category = None
        category_name = category.get("name") if category else None

        # Collect seller stats for richer title/desc/content
        seller_stats = await db.sellerListings.aggregate([
            {"$match": {"productId": product_id, "status": "active"}},
            {"$group": {
                "_id": None,
                "sellerCount": {"$sum": 1},
                "minPrice": {"$min": {"$min": "$pricingTiers.pricePerUnit"}},
                "maxPrice": {"$max": {"$max": "$pricingTiers.pricePerUnit"}},
            }}
        ]).to_list(1)

        stats = seller_stats[0] if seller_stats else {}
        seller_count = stats.get("sellerCount", 0) or 0
        min_price = stats.get("minPrice")
        max_price = stats.get("maxPrice")

        # Get available cities from active listings
        cities_agg = await db.sellerListings.aggregate([
            {"$match": {"productId": product_id, "status": "active"}},
            {"$lookup": {
                "from": "users", "localField": "sellerId",
                "foreignField": "_id", "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            {"$group": {"_id": {"$ifNull": ["$seller.profile.city", None]}}},
            {"$match": {"_id": {"$ne": None}}},
            {"$limit": 20}
        ]).to_list(20)
        available_cities = [c["_id"].title() for c in cities_agg if c.get("_id")]

        # Generate SEO
        # Remove this product's own slug from uniqueness set so regeneration doesn't append "-1"
        own_slug = product.get("slug")
        if own_slug and own_slug in slug_set:
            slug_set.discard(own_slug)

        new_slug = seo_service.generate_seo_slug(product_name, category_name, list(slug_set))
        new_title = seo_service.generate_seo_title(
            product_name, category_name, min_price=min_price, seller_count=seller_count
        )
        new_desc = seo_service.generate_seo_description(
            product_name, category_name, seller_count, min_price, max_price
        )
        new_content = seo_service.generate_seo_content(
            product_name, category_name,
            product.get("specifications", {}),
            product.get("description"),
            seller_count, available_cities,
            min_price=min_price, max_price=max_price
        )

        word_count = len(new_content.split())

        if dry_run:
            logger.info(f"[DRY RUN] {product_name} ({reason})")
            logger.info(f"  Slug: {product.get('slug', 'MISSING')} -> {new_slug}")
            logger.info(f"  Title ({len(new_title)}): {new_title}")
            logger.info(f"  Desc ({len(new_desc)}): {new_desc[:80]}...")
            logger.info(f"  Content: {word_count} words")
        else:
            update_data = {
                "seoTitle": new_title,
                "seoDescription": new_desc,
                "seoContent": new_content,
                "seoVersion": SEO_VERSION,
                "seoGeneratedAt": datetime.now(timezone.utc).isoformat(),
            }
            # Only update slug if missing or not in v2.1 format
            if not product.get("slug") or not product["slug"].endswith("-supplier-india"):
                update_data["slug"] = new_slug
                slug_set.add(new_slug)
            else:
                # Re-add own slug back to set so other products don't clash
                slug_set.add(product["slug"])

            await db.products.update_one({"_id": product_id}, {"$set": update_data})
            logger.info(f"Updated: {product_name} ({word_count}w, {reason})")

        updated_count += 1

    logger.info("")
    logger.info("=== Summary ===")
    logger.info(f"Updated: {updated_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Reasons: {reason_counts}")
    client.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("=== DRY RUN MODE (no changes will be made) ===")
    if force:
        logger.info("=== FORCE MODE (all products will be updated) ===")

    asyncio.run(bulk_update_seo(force=force, dry_run=dry_run))
