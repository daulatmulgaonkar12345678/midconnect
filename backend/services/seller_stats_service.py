"""
F1 — PRODUCT SELLER STATS (single authoritative seller-count aggregation)
=========================================================================

One $facet aggregation per product that computes, from sellerListings:

- listingCount:         total ACTIVE listings for the product (regardless of
                        seller account state or a missing seller document);
- sellerCount:          DISTINCT ELIGIBLE sellers — the authoritative number
                        displayed to buyers as the supplier count;
- verifiedSellerCount:  DISTINCT ELIGIBLE sellers whose users.gst.verified
                        is True.

Eligibility mirrors the approved Phase 1 seller rules (city_eligibility_service):
a seller is eligible only when a live seller document exists and that seller
is not deleted / deactivated / suspended / banned. A missing sellerStatus is
NOT an exclusion.

Counting happens inside MongoDB ($group by sellerId) — no per-seller queries,
no Python-side fan-out, one round-trip per product.
"""

from typing import Any, Dict

from bson import ObjectId


def build_product_seller_stats_pipeline(product_id: ObjectId) -> list:
    """The single authoritative seller-stats aggregation for one product."""
    return [
        {"$match": {"productId": product_id, "status": "active"}},
        # Left join: the listing itself always counts toward listingCount,
        # but only listings with a live seller document can count toward a
        # seller (same exclusion as the city eligibility service's inner
        # join, expressed via the sellerEligible flag).
        {"$lookup": {
            "from": "users",
            "localField": "sellerId",
            "foreignField": "_id",
            "as": "seller",
        }},
        {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {
            "sellerEligible": {"$and": [
                {"$ne": [{"$ifNull": ["$seller", None]}, None]},
                {"$ne": ["$seller.accountStatus", "deleted"]},
                {"$ne": ["$seller.isActive", False]},
                {"$not": {"$in": [
                    {"$ifNull": ["$seller.sellerStatus", None]},
                    ["suspended", "banned"]
                ]}},
            ]},
            "sellerVerified": {"$and": [
                {"$ne": [{"$ifNull": ["$seller", None]}, None]},
                {"$eq": [{"$ifNull": ["$seller.gst.verified", False]}, True]},
            ]},
        }},
        {"$facet": {
            "listingCount": [{"$count": "n"}],
            "sellerCount": [
                {"$match": {"sellerEligible": True}},
                {"$group": {"_id": "$sellerId"}},
                {"$count": "n"},
            ],
            "verifiedSellerCount": [
                {"$match": {"sellerEligible": True, "sellerVerified": True}},
                {"$group": {"_id": "$sellerId"}},
                {"$count": "n"},
            ],
        }},
    ]


def _facet_count(facet: Dict[str, Any], key: str) -> int:
    bucket = facet.get(key)
    if not bucket:
        return 0
    return int(bucket[0].get("n", 0))


async def fetch_product_seller_stats(db, product_id: ObjectId) -> Dict[str, int]:
    """Return {listingCount, sellerCount, verifiedSellerCount} for one product.

    Never fabricates counts: every number comes from the same aggregation.
    Raises pymongo connection errors to the caller (never swallowed here).
    """
    rows = await db.sellerListings.aggregate(
        build_product_seller_stats_pipeline(ObjectId(product_id))
    ).to_list(1)
    facet = rows[0] if rows else {}
    return {
        "listingCount": _facet_count(facet, "listingCount"),
        "sellerCount": _facet_count(facet, "sellerCount"),
        "verifiedSellerCount": _facet_count(facet, "verifiedSellerCount"),
    }
