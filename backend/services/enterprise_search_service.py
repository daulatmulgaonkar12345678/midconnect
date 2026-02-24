"""
ENTERPRISE SEARCH SERVICE (Phase 2)
====================================

Optimized search engine for 100k+ listings on MongoDB M0.

ARCHITECTURE:
- Filter FIRST, Score SECOND
- Compound query: must (text) + filter (structured) + should (boost)
- Hard limits: 50 max results, skip ≤ 5000
- Analytics logging (fire and forget)

DESIGN PRINCIPLES:
✅ Always filter first, score second
✅ Always index structured fields
✅ Always normalize before querying
✅ Always limit result set early
❌ Never depend only on text search
❌ Never sort large result sets after aggregation
❌ Never return unbounded results
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import re

logger = logging.getLogger("enterprise_search")

# ==================== CONSTANTS ====================

MAX_RESULTS = 50  # Hard limit
MAX_SKIP = 5000   # Prevent deep pagination
MIN_QUERY_LENGTH = 2

# Boost weights (non-monetized, but ready)
BOOST_PREMIUM_SELLER = 3
BOOST_HIGH_RATING = 2  # rating >= 4
BOOST_IN_STOCK = 1
BOOST_RECENT = 1  # created within 30 days


class EnterpriseSearchService:
    """
    Production-grade search service optimized for M0.
    
    Key Features:
    - Compound filtering (text + structured)
    - Ranking boosts (premium, rating, stock, recency)
    - Strict pagination limits
    - Analytics tracking
    """
    
    def __init__(self, db):
        self.db = db
    
    async def search(
        self,
        query: str,
        # Structured filters
        category_id: Optional[str] = None,
        manufacturer_id: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False,
        # Pagination
        page: int = 1,
        limit: int = 20,
        # Sorting
        sort_by: str = "relevance"  # relevance, price_asc, price_desc, rating, recent
    ) -> Dict[str, Any]:
        """
        Execute enterprise search with compound query.
        
        Returns:
            {
                "listings": [...],
                "total": int,
                "page": int,
                "pages": int,
                "query": str,
                "filters_applied": {...},
                "search_time_ms": int
            }
        """
        import time
        start_time = time.time()
        
        # ============================================================
        # STEP 1: Input Validation & Normalization
        # ============================================================
        query = (query or "").strip()
        
        # Enforce hard limits
        limit = min(limit, MAX_RESULTS)
        skip = (page - 1) * limit
        
        if skip > MAX_SKIP:
            return {
                "error": "pagination_limit_exceeded",
                "message": f"Maximum pagination depth is {MAX_SKIP // limit} pages",
                "listings": [],
                "total": 0
            }
        
        # ============================================================
        # STEP 2: Build Filter Stage (FILTER FIRST)
        # ============================================================
        base_filter = {
            "isActive": True,
            "status": "active"
        }
        
        filters_applied = {}
        
        # Category filter (indexed)
        if category_id:
            try:
                base_filter["categoryId"] = ObjectId(category_id)
                filters_applied["categoryId"] = category_id
            except Exception:
                pass
        
        # Manufacturer filter (indexed)
        if manufacturer_id:
            try:
                base_filter["manufacturerId"] = ObjectId(manufacturer_id)
                filters_applied["manufacturerId"] = manufacturer_id
            except Exception:
                pass
        
        # Location filters (indexed)
        if city:
            base_filter["city"] = {"$regex": f"^{re.escape(city)}$", "$options": "i"}
            filters_applied["city"] = city
        
        if state:
            base_filter["state"] = {"$regex": f"^{re.escape(state)}$", "$options": "i"}
            filters_applied["state"] = state
        
        # Price range filter (indexed)
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
                filters_applied["minPrice"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
                filters_applied["maxPrice"] = max_price
            base_filter["minPrice"] = price_filter
        
        # Stock filter (indexed)
        if in_stock_only:
            base_filter["inStock"] = True
            filters_applied["inStock"] = True
        
        # ============================================================
        # STEP 3: Build Text Search (SCORE SECOND)
        # ============================================================
        text_search_stage = None
        
        if query and len(query) >= MIN_QUERY_LENGTH:
            # Normalize query
            from services.search_normalization_service import search_normalizer
            parsed = search_normalizer.parse_search_query(query)
            
            search_tokens = parsed.search_tokens
            
            if search_tokens:
                # Build regex pattern for text matching
                search_pattern = "|".join(re.escape(t) for t in search_tokens)
                
                text_search_stage = {
                    "$or": [
                        {"searchableText": {"$regex": search_pattern, "$options": "i"}},
                        {"normalizedSearchTokens": {"$in": [t.lower() for t in search_tokens]}},
                        {"manufacturerName": {"$regex": search_pattern, "$options": "i"}},
                    ]
                }
        
        # ============================================================
        # STEP 4: Build Aggregation Pipeline
        # ============================================================
        pipeline = []
        
        # Match stage (FILTER FIRST)
        match_query = {**base_filter}
        if text_search_stage:
            match_query.update(text_search_stage)
        
        pipeline.append({"$match": match_query})
        
        # ============================================================
        # STEP 5: Add Boost Score (Ranking)
        # ============================================================
        # Calculate dynamic score for sorting by relevance
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        pipeline.append({
            "$addFields": {
                "rankScore": {
                    "$add": [
                        # Base boost score from DB
                        {"$ifNull": ["$boostScore", 0]},
                        # Premium seller boost
                        {"$cond": [{"$eq": ["$isPremiumSeller", True]}, BOOST_PREMIUM_SELLER, 0]},
                        # High rating boost
                        {"$cond": [{"$gte": [{"$ifNull": ["$sellerRating", 0]}, 4]}, BOOST_HIGH_RATING, 0]},
                        # In stock boost
                        {"$cond": [{"$eq": ["$inStock", True]}, BOOST_IN_STOCK, 0]},
                        # Recent listing boost
                        {"$cond": [{"$gte": ["$createdAt", thirty_days_ago]}, BOOST_RECENT, 0]},
                    ]
                }
            }
        })
        
        # ============================================================
        # STEP 6: Sorting
        # ============================================================
        sort_options = {
            "relevance": {"rankScore": -1, "createdAt": -1},
            "price_asc": {"minPrice": 1, "rankScore": -1},
            "price_desc": {"minPrice": -1, "rankScore": -1},
            "rating": {"sellerRating": -1, "rankScore": -1},
            "recent": {"createdAt": -1, "rankScore": -1},
        }
        
        sort_spec = sort_options.get(sort_by, sort_options["relevance"])
        pipeline.append({"$sort": sort_spec})
        
        # ============================================================
        # STEP 7: Count total (before pagination)
        # ============================================================
        # Use facet to get both count and paginated results in one query
        pipeline.append({
            "$facet": {
                "metadata": [{"$count": "total"}],
                "listings": [
                    {"$skip": skip},
                    {"$limit": limit},
                    # Lookup product info
                    {"$lookup": {
                        "from": "products",
                        "localField": "productId",
                        "foreignField": "_id",
                        "as": "product"
                    }},
                    {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
                    # Lookup seller info
                    {"$lookup": {
                        "from": "users",
                        "localField": "sellerId",
                        "foreignField": "_id",
                        "as": "seller"
                    }},
                    {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
                    # Project only needed fields
                    {"$project": {
                        "_id": 1,
                        "productId": 1,
                        "productName": "$product.name",
                        "categoryId": 1,
                        "manufacturerId": 1,
                        "manufacturerName": 1,
                        "description": 1,
                        "images": 1,
                        "minPrice": 1,
                        "pricingTiers": 1,
                        "moq": 1,
                        "stock": 1,
                        "inStock": 1,
                        "leadTime": 1,
                        "currency": 1,
                        "searchableAttributes": 1,
                        "attributeLabels": 1,
                        "city": 1,
                        "state": 1,
                        "sellerRating": 1,
                        "isPremiumSeller": 1,
                        "sellerTier": 1,
                        "rankScore": 1,
                        "createdAt": 1,
                        "seller": {
                            "_id": 1,
                            "profile.businessName": 1,
                            "profile.city": 1,
                            "profile.state": 1,
                        }
                    }}
                ]
            }
        })
        
        # ============================================================
        # STEP 8: Execute Query
        # ============================================================
        try:
            results = await self.db.sellerListings.aggregate(pipeline).to_list(1)
            
            if results:
                result = results[0]
                total = result["metadata"][0]["total"] if result["metadata"] else 0
                listings = result["listings"]
            else:
                total = 0
                listings = []
            
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            return {
                "error": "search_failed",
                "message": str(e),
                "listings": [],
                "total": 0
            }
        
        # ============================================================
        # STEP 9: Format Results
        # ============================================================
        formatted_listings = []
        for listing in listings:
            formatted_listings.append(self._format_listing(listing))
        
        # Calculate search time
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # ============================================================
        # STEP 10: Log Analytics (Fire and Forget)
        # ============================================================
        # Don't await - fire and forget to not block response
        try:
            await self._log_search_analytics(query, filters_applied, total)
        except Exception as e:
            logger.warning(f"Analytics logging failed: {e}")
        
        return {
            "listings": formatted_listings,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "limit": limit,
            "query": query,
            "filters_applied": filters_applied,
            "sort_by": sort_by,
            "search_time_ms": search_time_ms
        }
    
    def _format_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Format listing for API response."""
        seller = listing.get("seller", {})
        profile = seller.get("profile", {})
        
        return {
            "_id": str(listing["_id"]),
            "productId": str(listing.get("productId", "")),
            "productName": listing.get("productName", ""),
            "categoryId": str(listing.get("categoryId", "")),
            "manufacturerId": str(listing.get("manufacturerId", "")) if listing.get("manufacturerId") else None,
            "manufacturerName": listing.get("manufacturerName"),
            "description": listing.get("description"),
            "images": listing.get("images", []),
            "price": listing.get("minPrice"),
            "pricingTiers": listing.get("pricingTiers", []),
            "moq": listing.get("moq", 1),
            "stock": listing.get("stock", 0),
            "inStock": listing.get("inStock", False),
            "leadTime": listing.get("leadTime"),
            "currency": listing.get("currency", "INR"),
            "searchableAttributes": listing.get("searchableAttributes", {}),
            "attributeLabels": listing.get("attributeLabels", {}),
            "seller": {
                "_id": str(seller.get("_id", listing.get("sellerId", ""))),
                "businessName": profile.get("businessName", ""),
                "city": listing.get("city") or profile.get("city", ""),
                "state": listing.get("state") or profile.get("state", ""),
            },
            "sellerRating": listing.get("sellerRating", 0),
            "isPremiumSeller": listing.get("isPremiumSeller", False),
            "sellerTier": listing.get("sellerTier", "free"),
            "rankScore": listing.get("rankScore", 0),
            "createdAt": listing.get("createdAt").isoformat() if listing.get("createdAt") else None,
        }
    
    async def _log_search_analytics(
        self, 
        query: str, 
        filters: Dict[str, Any], 
        results_count: int
    ):
        """
        Log search for analytics.
        
        Uses upsert to increment count for existing queries.
        """
        if not query:
            return
        
        normalized_query = query.lower().strip()
        
        await self.db.searchAnalytics.update_one(
            {"query": normalized_query},
            {
                "$inc": {"count": 1},
                "$set": {
                    "lastSearchedAt": datetime.now(timezone.utc),
                    "lastResultsCount": results_count,
                    "lastFilters": filters
                },
                "$setOnInsert": {
                    "query": normalized_query,
                    "createdAt": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries."""
        results = await self.db.searchAnalytics.find(
            {"count": {"$gte": 2}}  # At least searched twice
        ).sort("count", -1).limit(limit).to_list(limit)
        
        return [
            {
                "query": r["query"],
                "count": r["count"],
                "lastSearchedAt": r.get("lastSearchedAt")
            }
            for r in results
        ]


def create_enterprise_search_service(db):
    """Factory function to create search service."""
    return EnterpriseSearchService(db)
