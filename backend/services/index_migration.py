"""
ENTERPRISE INDEX STRATEGY
=========================
Critical indexes for scalability and performance.

Run this migration to ensure all indexes are in place.
Safe to run multiple times (idempotent).
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("index_migration")


async def run_index_migration(db):
    """
    Create all enterprise indexes.
    
    Index Strategy:
    1. Unique indexes on slug fields (SEO)
    2. Compound indexes for common queries
    3. Single field indexes for sorting
    4. Text indexes for search
    
    This is idempotent - safe to run multiple times.
    """
    results = {
        "created": [],
        "existed": [],
        "errors": []
    }
    
    # ==================== PRODUCTS INDEXES ====================
    product_indexes = [
        # SEO slug - unique
        {
            "keys": [("slug", 1)],
            "options": {"unique": True, "sparse": True, "name": "idx_products_slug_unique"}
        },
        # Category lookup - compound
        {
            "keys": [("categoryId", 1), ("isActive", 1)],
            "options": {"name": "idx_products_category_active"}
        },
        # Active products sorted by date
        {
            "keys": [("isActive", 1), ("createdAt", -1)],
            "options": {"name": "idx_products_active_date"}
        },
        # Name text search
        {
            "keys": [("name", "text"), ("description", "text")],
            "options": {"name": "idx_products_text_search", "weights": {"name": 10, "description": 1}}
        },
        # Family/Variant for product identity
        {
            "keys": [("categoryId", 1), ("family", 1), ("variant", 1)],
            "options": {"name": "idx_products_identity"}
        },
        # Legacy IDs for redirects
        {
            "keys": [("legacyIds", 1)],
            "options": {"sparse": True, "name": "idx_products_legacy_ids"}
        },
        # Legacy slugs for redirects
        {
            "keys": [("legacySlugs", 1)],
            "options": {"sparse": True, "name": "idx_products_legacy_slugs"}
        }
    ]
    
    for idx in product_indexes:
        try:
            await db.products.create_index(idx["keys"], **idx["options"])
            results["created"].append(f"products.{idx['options']['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "existing index" in str(e).lower():
                results["existed"].append(f"products.{idx['options']['name']}")
            else:
                results["errors"].append(f"products.{idx['options']['name']}: {e}")
    
    # ==================== CATEGORIES INDEXES ====================
    category_indexes = [
        # SEO slug - unique
        {
            "keys": [("slug", 1)],
            "options": {"unique": True, "sparse": True, "name": "idx_categories_slug_unique"}
        },
        # Active categories
        {
            "keys": [("isActive", 1)],
            "options": {"name": "idx_categories_active"}
        },
        # Legacy IDs for redirects
        {
            "keys": [("legacyIds", 1)],
            "options": {"sparse": True, "name": "idx_categories_legacy_ids"}
        }
    ]
    
    for idx in category_indexes:
        try:
            await db.categories.create_index(idx["keys"], **idx["options"])
            results["created"].append(f"categories.{idx['options']['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "existing index" in str(e).lower():
                results["existed"].append(f"categories.{idx['options']['name']}")
            else:
                results["errors"].append(f"categories.{idx['options']['name']}: {e}")
    
    # ==================== SELLER LISTINGS INDEXES ====================
    listing_indexes = [
        # Product lookup - primary query pattern
        {
            "keys": [("productId", 1), ("status", 1)],
            "options": {"name": "idx_listings_product_status"}
        },
        # Seller lookup
        {
            "keys": [("sellerId", 1), ("status", 1)],
            "options": {"name": "idx_listings_seller_status"}
        },
        # Price sorting (first tier price)
        {
            "keys": [("productId", 1), ("pricingTiers.0.pricePerUnit", 1)],
            "options": {"name": "idx_listings_product_price"}
        },
        # Date sorting
        {
            "keys": [("createdAt", -1)],
            "options": {"name": "idx_listings_created"}
        },
        # Unique constraint: one listing per seller per product
        {
            "keys": [("productId", 1), ("sellerId", 1)],
            "options": {"unique": True, "name": "idx_listings_product_seller_unique"}
        }
    ]
    
    for idx in listing_indexes:
        try:
            await db.sellerListings.create_index(idx["keys"], **idx["options"])
            results["created"].append(f"sellerListings.{idx['options']['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "existing index" in str(e).lower():
                results["existed"].append(f"sellerListings.{idx['options']['name']}")
            else:
                results["errors"].append(f"sellerListings.{idx['options']['name']}: {e}")
    
    # ==================== USERS INDEXES ====================
    user_indexes = [
        # Email lookup (Firebase UID alternative)
        {
            "keys": [("email", 1)],
            "options": {"unique": True, "sparse": True, "name": "idx_users_email_unique"}
        },
        # Firebase UID
        {
            "keys": [("firebaseUid", 1)],
            "options": {"unique": True, "sparse": True, "name": "idx_users_firebase_unique"}
        },
        # Role lookup
        {
            "keys": [("role", 1)],
            "options": {"name": "idx_users_role"}
        },
        # Seller by city for location search
        {
            "keys": [("role", 1), ("profile.city", 1)],
            "options": {"name": "idx_users_seller_city"}
        }
    ]
    
    for idx in user_indexes:
        try:
            await db.users.create_index(idx["keys"], **idx["options"])
            results["created"].append(f"users.{idx['options']['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "existing index" in str(e).lower():
                results["existed"].append(f"users.{idx['options']['name']}")
            else:
                results["errors"].append(f"users.{idx['options']['name']}: {e}")
    
    # ==================== QUOTES/INQUIRIES INDEXES ====================
    quote_indexes = [
        # Buyer lookup
        {
            "keys": [("buyerId", 1), ("createdAt", -1)],
            "options": {"name": "idx_quotes_buyer_date"}
        },
        # Seller lookup
        {
            "keys": [("sellerId", 1), ("createdAt", -1)],
            "options": {"name": "idx_quotes_seller_date"}
        },
        # Product lookup
        {
            "keys": [("productId", 1)],
            "options": {"name": "idx_quotes_product"}
        },
        # Status filtering
        {
            "keys": [("status", 1), ("createdAt", -1)],
            "options": {"name": "idx_quotes_status_date"}
        }
    ]
    
    for idx in quote_indexes:
        try:
            await db.quotes.create_index(idx["keys"], **idx["options"])
            results["created"].append(f"quotes.{idx['options']['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "existing index" in str(e).lower():
                results["existed"].append(f"quotes.{idx['options']['name']}")
            else:
                results["errors"].append(f"quotes.{idx['options']['name']}: {e}")
    
    return results


async def get_index_stats(db):
    """Get index statistics for all collections."""
    stats = {}
    
    collections = ["products", "categories", "sellerListings", "users", "quotes"]
    
    for coll_name in collections:
        try:
            coll = db[coll_name]
            indexes = await coll.index_information()
            stats[coll_name] = {
                "indexCount": len(indexes),
                "indexes": list(indexes.keys())
            }
        except Exception as e:
            stats[coll_name] = {"error": str(e)}
    
    return stats
