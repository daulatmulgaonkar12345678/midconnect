"""
SITEMAP PRODUCT SOURCE (independent of seller listings)
=======================================================
Product URLs in the sitemap must not depend on active seller listings.
This service reads the `products` collection directly and applies the
existing product visibility rules:

- isActive != false (an explicit false hides the product)
- deletedAt is null or absent, and isDeleted is not true
- slug is a non-empty string (the canonical slug; legacy aliases are never emitted)

`/api/products` is intentionally NOT changed: it is listing-driven and has
other consumers.
"""

from typing import Any, Dict, List

CANONICAL_SLUG_REGEX = r"^[a-z0-9]+(-[a-z0-9]+)*$"

VISIBLE_PRODUCT_FILTER: Dict[str, Any] = {
    "isActive": {"$ne": False},
    "$or": [
        {"deletedAt": None},
        {"deletedAt": {"$exists": False}},
    ],
    "isDeleted": {"$ne": True},
    # Canonical slug form: lowercase letters/digits, single hyphens between parts.
    "slug": {"$type": "string", "$regex": CANONICAL_SLUG_REGEX},
}


class SitemapProductOverflowError(RuntimeError):
    """Raised when more visible products exist than the configured maximum."""

    def __init__(self, max_products: int):
        super().__init__(
            f"visible products exceed max_products={max_products}; refusing to return partial data"
        )
        self.max_products = max_products


async def fetch_sitemap_products(db, max_products: int) -> List[Dict[str, Any]]:
    """Return {productSlug, lastModified} for every visible product, sorted by slug.

    Raises SitemapProductOverflowError rather than silently truncating.
    """
    cursor = db.products.find(
        VISIBLE_PRODUCT_FILTER,
        {"_id": 0, "slug": 1, "updatedAt": 1},
    ).sort("slug", 1).limit(max_products + 1)
    docs = await cursor.to_list(None)
    if len(docs) > max_products:
        raise SitemapProductOverflowError(max_products)
    return [
        {
            "productSlug": d["slug"],
            "lastModified": d["updatedAt"].isoformat() if d.get("updatedAt") and hasattr(d["updatedAt"], "isoformat") else None,
        }
        for d in docs
    ]
