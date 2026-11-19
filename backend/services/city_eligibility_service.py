"""
PHASE 1 CITY ELIGIBILITY AGGREGATION
====================================
Grouped product-city eligibility for the sitemap (`mode=all`).

Approved rules:
- Seller excluded when users.accountStatus == "deleted", users.isActive == false,
  or users.sellerStatus in {"suspended", "banned"}.
  A missing sellerStatus is NOT an exclusion. canLogin is not an exclusion.
- Product must be active (isActive != false) with a non-empty slug.
- City: a listing matches a city if any of city / sellerCity / seller.profile.city
  (trimmed, lowercased) equals it.
- city intent:      >= 1 eligible listing in the city.
- price intent:     >= 1 eligible listing with a pricingTiers[].pricePerUnit that is
                    numeric (double/int/long/decimal) and > 0. No top-level or
                    legacy `price` fallback.
- suppliers intent: >= 2 distinct eligible sellers in the city.

Counting happens inside MongoDB ($group). The city filter runs inside the
pipeline, before the limit, so the limit cannot silently drop allowed pairs.
If more than `max_pairs` groups exist, PairOverflowError is raised.
"""

from typing import Any, Dict, List

NUMERIC_TYPES = ["double", "int", "long", "decimal"]


class PairOverflowError(RuntimeError):
    """Raised when eligible product-city groups exceed the configured maximum."""

    def __init__(self, count_seen: int, max_pairs: int):
        super().__init__(
            f"eligible product-city pairs exceed max_pairs={max_pairs} "
            f"(saw at least {count_seen}); refusing to return partial data"
        )
        self.count_seen = count_seen
        self.max_pairs = max_pairs


def _norm_city(path: str) -> Dict[str, Any]:
    """Lowercased, trimmed value of `path`, or [] when empty (so it drops out of the set)."""
    value = {"$trim": {"input": {"$toLower": {"$ifNull": [path, ""]}}}}
    return {"$cond": [{"$eq": [value, ""]}, [], [value]]}


def _city_values_expr() -> Dict[str, Any]:
    """Set of distinct, non-empty normalised city strings a listing matches on."""
    return {
        "$setUnion": [
            _norm_city("$city"),
            _norm_city("$sellerCity"),
            _norm_city("$seller.profile.city"),
        ]
    }


def build_eligibility_pipeline(allowed_cities: List[str], max_pairs: int) -> List[Dict[str, Any]]:
    """Pipeline returning one document per eligible (productSlug, city) group."""
    return [
        {"$match": {"status": "active"}},
        {"$lookup": {"from": "users", "localField": "sellerId", "foreignField": "_id", "as": "seller"}},
        {"$unwind": "$seller"},  # inner join: listings with no seller document are dropped
        {"$match": {
            "seller.accountStatus": {"$ne": "deleted"},
            "seller.isActive": {"$ne": False},
            "seller.sellerStatus": {"$nin": ["suspended", "banned"]},
        }},
        {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "product"}},
        {"$unwind": "$product"},
        {"$match": {
            "product.isActive": {"$ne": False},
            "product.slug": {"$nin": [None, ""]},
        }},
        {"$addFields": {"cityValues": _city_values_expr()}},
        {"$unwind": "$cityValues"},
        {"$match": {"cityValues": {"$in": allowed_cities}}},
        {"$addFields": {
            "hasValidPrice": {"$anyElementTrue": [{
                "$map": {
                    "input": {"$ifNull": ["$pricingTiers", []]},
                    "as": "t",
                    "in": {"$and": [
                        {"$in": [{"$type": "$$t.pricePerUnit"}, NUMERIC_TYPES]},
                        {"$gt": ["$$t.pricePerUnit", 0]},
                    ]},
                }
            }]},
        }},
        {"$group": {
            "_id": {"productSlug": "$product.slug", "city": "$cityValues"},
            "listings": {"$sum": 1},
            "pricedListings": {"$sum": {"$cond": ["$hasValidPrice", 1, 0]}},
            "sellerIds": {"$addToSet": "$sellerId"},
            "lastModified": {"$max": "$updatedAt"},
        }},
        {"$project": {
            "_id": 0,
            "productSlug": "$_id.productSlug",
            "city": "$_id.city",
            "listings": 1,
            "pricedListings": 1,
            "supplierCount": {"$size": "$sellerIds"},
            "lastModified": 1,
        }},
        {"$sort": {"productSlug": 1, "city": 1}},
        {"$limit": max_pairs + 1},  # one extra row detects overflow; never silent truncation
    ]


async def fetch_eligible_pairs(db, allowed_cities: List[str], max_pairs: int) -> List[Dict[str, Any]]:
    """Run the grouped pipeline and return per-pair intent flags.

    Raises PairOverflowError when more than `max_pairs` eligible groups exist.
    """
    pipeline = build_eligibility_pipeline(allowed_cities, max_pairs)
    rows = await db.sellerListings.aggregate(pipeline, allowDiskUse=True).to_list(None)
    if len(rows) > max_pairs:
        raise PairOverflowError(len(rows), max_pairs)

    out = []
    for r in rows:
        out.append({
            "productSlug": r["productSlug"],
            "citySlug": r["city"],
            "lastModified": r["lastModified"].isoformat() if r.get("lastModified") else None,
            "listings": r["listings"],
            "cityEligible": r["listings"] >= 1,
            "priceEligible": r["pricedListings"] >= 1,
            "suppliersEligible": r["supplierCount"] >= 2,
        })
    return out
