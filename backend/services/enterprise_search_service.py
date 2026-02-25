"""
ENTERPRISE SEARCH SERVICE (Phase 3)
====================================

Production-hardened search engine for 100k+ listings on MongoDB M0.

PHASE 3 HARDENING:
1. Minimum query length enforcement (2+ chars)
2. LRU cache for page 1 searches (20 entries, 5 min TTL)
3. Optimized count strategy (no full count on page > 1)
4. Search timeout protection (1.5s max)
5. Rate limiting ready (via slowapi)
6. Result projection (minimal payload)
7. Query normalization upgrade
8. Strict pagination (page ≤ 250)
9. Slow query logging (>700ms flagged)
10. M10 migration flag

ARCHITECTURE:
- Filter FIRST, Score SECOND
- Compound query: must (text) + filter (structured) + should (boost)
- Hard limits: 50 max results, page ≤ 250

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
import asyncio
import os
import time
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from functools import lru_cache
import re

logger = logging.getLogger("enterprise_search")

# ==================== CONFIGURATION ====================

# Search engine mode: "m0" (current) or "m10" (future upgrade)
SEARCH_ENGINE_MODE = os.environ.get("SEARCH_ENGINE_MODE", "m0")

# Hard limits
MAX_RESULTS = 50  # Maximum results per page
MAX_PAGE = 250    # Maximum page number (prevents deep pagination)
MAX_SKIP = MAX_RESULTS * MAX_PAGE  # 12,500

# Query constraints
MIN_QUERY_LENGTH = 2
SEARCH_TIMEOUT_SECONDS = 1.5

# Cache settings
CACHE_MAX_SIZE = 20
CACHE_TTL_SECONDS = 300  # 5 minutes

# Slow query threshold
SLOW_QUERY_THRESHOLD_MS = 700

# Boost weights (non-monetized, but ready)
BOOST_PREMIUM_SELLER = 3
BOOST_HIGH_RATING = 2  # rating >= 4
BOOST_IN_STOCK = 1
BOOST_RECENT = 1  # created within 30 days


# ==================== LRU CACHE ====================

class SearchCache:
    """
    In-memory LRU cache with TTL for page 1 searches.
    Only caches: page=1, sort=relevance
    """
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def _make_key(self, query: str, filters: Dict[str, Any]) -> str:
        """Generate cache key from normalized query + filters."""
        key_parts = [
            query.lower().strip(),
            filters.get("category_id", ""),
            filters.get("manufacturer_id", ""),
            filters.get("city", ""),
            filters.get("state", ""),
        ]
        key_str = "|".join(str(p) for p in key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached result if valid."""
        key = self._make_key(query, filters)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache HIT: {query[:20]}")
                return result
            else:
                # Expired
                del self.cache[key]
        return None
    
    def set(self, query: str, filters: Dict[str, Any], result: Dict[str, Any]):
        """Cache result for page 1 searches only."""
        # Enforce max size (LRU eviction)
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        key = self._make_key(query, filters)
        self.cache[key] = (result, time.time())
        logger.debug(f"Cache SET: {query[:20]}")


# Global cache instance
_search_cache = SearchCache()


# ==================== QUERY NORMALIZATION ====================

class QueryNormalizer:
    """
    Enhanced query normalization for search optimization.
    
    Handles:
    - Lowercase conversion
    - Extra space removal
    - Unit normalization (0.5hp → 0.5 hp)
    - Common abbreviations (ampr → amp)
    - Fraction conversion (half hp → 0.5 hp)
    """
    
    # Common unit patterns
    UNIT_PATTERNS = [
        (r'(\d+(?:\.\d+)?)\s*(hp|kw|amp|volt|v|w|a)', r'\1 \2'),  # 0.5hp → 0.5 hp
        (r'(\d+(?:\.\d+)?)\s*(mm|cm|m|kg|g|l|ml)', r'\1 \2'),      # 10mm → 10 mm
    ]
    
    # Fraction conversions
    FRACTIONS = {
        'half': '0.5',
        'quarter': '0.25',
        'one fourth': '0.25',
        'three fourth': '0.75',
        'one third': '0.33',
        'two third': '0.67',
    }
    
    # Common abbreviation corrections
    ABBREVIATIONS = {
        'ampr': 'amp',
        'amps': 'amp',
        'volts': 'volt',
        'watts': 'watt',
        'kws': 'kw',
        'hps': 'hp',
        'mtr': 'motor',
        'mtrs': 'motors',
        'elec': 'electric',
        'ctrl': 'control',
        'contctr': 'contactor',
    }
    
    @classmethod
    def normalize(cls, query: str) -> str:
        """Normalize query for optimal search."""
        if not query:
            return ""
        
        # Lowercase and strip
        q = query.lower().strip()
        
        # Remove extra spaces
        q = re.sub(r'\s+', ' ', q)
        
        # Convert fractions (half hp → 0.5 hp)
        for fraction, decimal in cls.FRACTIONS.items():
            q = re.sub(rf'\b{fraction}\b', decimal, q)
        
        # Fix abbreviations
        for abbr, full in cls.ABBREVIATIONS.items():
            q = re.sub(rf'\b{abbr}\b', full, q)
        
        # Normalize unit spacing
        for pattern, replacement in cls.UNIT_PATTERNS:
            q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)
        
        return q.strip()
    
    @classmethod
    def is_valid_query(cls, query: str) -> Tuple[bool, str]:
        """
        Validate query meets minimum requirements.
        
        Returns: (is_valid, error_message)
        """
        if not query:
            return False, "Search query is required"
        
        q = query.strip()
        
        # Check minimum length
        if len(q) < MIN_QUERY_LENGTH:
            # Exception: Allow numeric queries like "0.5"
            if not re.match(r'^\d+\.?\d*$', q):
                return False, f"Please enter at least {MIN_QUERY_LENGTH} characters"
        
        return True, ""


# ==================== ENTERPRISE SEARCH SERVICE ====================

class EnterpriseSearchService:
    """
    Production-grade search service optimized for M0.
    
    Phase 3 Features:
    - Query validation & normalization
    - LRU caching (page 1 only)
    - Timeout protection
    - Slow query logging
    - Minimal result projection
    - Strict pagination limits
    """
    
    def __init__(self, db):
        self.db = db
        self.normalizer = QueryNormalizer()
    
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
        Execute enterprise search with Phase 3 hardening.
        
        Returns:
            {
                "listings": [...],
                "total": int (approximate),
                "page": int,
                "hasMore": bool,
                "query": str,
                "filters_applied": {...},
                "search_time_ms": int,
                "cached": bool
            }
        """
        start_time = time.time()
        
        # ============================================================
        # STEP 1: Query Validation (Phase 3)
        # ============================================================
        is_valid, error_msg = self.normalizer.is_valid_query(query)
        if not is_valid and query:  # Allow empty query for browse mode
            return {
                "listings": [],
                "total": 0,
                "page": 1,
                "hasMore": False,
                "query": query,
                "message": error_msg,
                "search_time_ms": 0
            }
        
        # ============================================================
        # STEP 2: Query Normalization (Phase 3)
        # ============================================================
        normalized_query = self.normalizer.normalize(query) if query else ""
        
        # ============================================================
        # STEP 3: Enforce Hard Limits (Phase 3)
        # ============================================================
        limit = min(limit, MAX_RESULTS)
        page = min(page, MAX_PAGE)
        skip = (page - 1) * limit
        
        if page > MAX_PAGE:
            return {
                "error": "pagination_limit_exceeded",
                "message": f"Maximum page is {MAX_PAGE}. Please refine your search filters.",
                "listings": [],
                "total": 0
            }
        
        # ============================================================
        # STEP 4: Check Cache (Page 1, relevance sort only)
        # ============================================================
        filters = {
            "category_id": category_id,
            "manufacturer_id": manufacturer_id,
            "city": city,
            "state": state,
        }
        
        use_cache = page == 1 and sort_by == "relevance"
        
        if use_cache:
            cached_result = _search_cache.get(normalized_query, filters)
            if cached_result:
                cached_result["cached"] = True
                cached_result["search_time_ms"] = int((time.time() - start_time) * 1000)
                return cached_result
        
        # ============================================================
        # STEP 5: Build Filter Stage (FILTER FIRST)
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
        # STEP 6: Build Text Search (SCORE SECOND)
        # ============================================================
        text_search_stage = None
        
        if normalized_query:
            # Build regex pattern for text matching
            search_tokens = normalized_query.split()
            search_pattern = "|".join(re.escape(t) for t in search_tokens)
            
            text_search_stage = {
                "$or": [
                    {"searchableText": {"$regex": search_pattern, "$options": "i"}},
                    {"normalizedSearchTokens": {"$in": [t.lower() for t in search_tokens]}},
                    {"manufacturerName": {"$regex": search_pattern, "$options": "i"}},
                ]
            }
        
        # ============================================================
        # STEP 7: Build Aggregation Pipeline
        # ============================================================
        pipeline = []
        
        # Match stage (FILTER FIRST)
        match_query = {**base_filter}
        if text_search_stage:
            match_query.update(text_search_stage)
        
        pipeline.append({"$match": match_query})
        
        # ============================================================
        # STEP 8: Add Boost Score (Ranking)
        # ============================================================
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        pipeline.append({
            "$addFields": {
                "rankScore": {
                    "$add": [
                        {"$ifNull": ["$boostScore", 0]},
                        {"$cond": [{"$eq": ["$isPremiumSeller", True]}, BOOST_PREMIUM_SELLER, 0]},
                        {"$cond": [{"$gte": [{"$ifNull": ["$sellerRating", 0]}, 4]}, BOOST_HIGH_RATING, 0]},
                        {"$cond": [{"$eq": ["$inStock", True]}, BOOST_IN_STOCK, 0]},
                        {"$cond": [{"$gte": ["$createdAt", thirty_days_ago]}, BOOST_RECENT, 0]},
                    ]
                }
            }
        })
        
        # ============================================================
        # STEP 9: Sorting
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
        # STEP 10: Pagination with hasMore detection
        # ============================================================
        # Fetch limit+1 to detect if more results exist
        pipeline.append({"$skip": skip})
        pipeline.append({"$limit": limit + 1})
        
        # ============================================================
        # STEP 11: Result Projection (Minimal Payload - Phase 3)
        # ============================================================
        pipeline.append({
            "$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "product",
                "pipeline": [{"$project": {"name": 1}}]  # Only fetch name
            }
        })
        pipeline.append({"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}})
        
        # Minimal projection for performance
        pipeline.append({
            "$project": {
                "_id": 1,
                "productId": 1,
                "productName": "$product.name",
                "categoryId": 1,
                "manufacturerId": 1,
                "manufacturerName": 1,
                "description": {"$substrCP": [{"$ifNull": ["$description", ""]}, 0, 150]},  # Truncate
                "images": {"$slice": ["$images", 2]},  # Only first 2 images
                "minPrice": 1,
                "pricingTiers": {"$slice": ["$pricingTiers", 3]},  # Only first 3 tiers
                "moq": 1,
                "stock": 1,
                "inStock": 1,
                "leadTime": 1,
                "currency": 1,
                "city": 1,
                "state": 1,
                "sellerRating": 1,
                "isPremiumSeller": 1,
                "sellerTier": 1,
                "rankScore": 1,
                "sellerId": 1,
                "createdAt": 1,
            }
        })
        
        # ============================================================
        # STEP 12: Execute with Timeout Protection (Phase 3)
        # ============================================================
        try:
            results = await asyncio.wait_for(
                self.db.sellerListings.aggregate(pipeline).to_list(limit + 1),
                timeout=SEARCH_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(f"[SLOW_QUERY] TIMEOUT: query='{normalized_query}', filters={filters_applied}")
            return {
                "error": "search_timeout",
                "message": "Search took too long. Please refine your query or add filters.",
                "listings": [],
                "total": 0,
                "search_time_ms": int(SEARCH_TIMEOUT_SECONDS * 1000)
            }
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            return {
                "error": "search_failed",
                "message": str(e),
                "listings": [],
                "total": 0
            }
        
        # ============================================================
        # STEP 13: Detect hasMore (without full count)
        # ============================================================
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]  # Remove the extra result
        
        # Approximate total (for page 1)
        if page == 1:
            if has_more:
                # We have more, estimate total as at least page * 2
                approx_total = limit * 2
            else:
                approx_total = len(results)
        else:
            # For page > 1, we don't know exact total
            approx_total = skip + len(results) + (1 if has_more else 0)
        
        # ============================================================
        # STEP 14: Format Results
        # ============================================================
        formatted_listings = []
        for listing in results:
            formatted_listings.append(self._format_listing(listing))
        
        # Calculate search time
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # ============================================================
        # STEP 15: Slow Query Logging (Phase 3)
        # ============================================================
        if search_time_ms > SLOW_QUERY_THRESHOLD_MS:
            logger.warning(
                f"[SLOW_QUERY] time={search_time_ms}ms, query='{normalized_query}', "
                f"filters={filters_applied}, results={len(formatted_listings)}"
            )
        
        # ============================================================
        # STEP 16: Log Analytics (Fire and Forget)
        # ============================================================
        try:
            asyncio.create_task(self._log_search_analytics(
                normalized_query, filters_applied, len(formatted_listings), search_time_ms
            ))
        except Exception as e:
            logger.debug(f"Analytics logging failed: {e}")
        
        # Build response
        result = {
            "listings": formatted_listings,
            "total": approx_total,
            "page": page,
            "limit": limit,
            "hasMore": has_more,
            "query": query,
            "normalizedQuery": normalized_query,
            "filters_applied": filters_applied,
            "sort_by": sort_by,
            "search_time_ms": search_time_ms,
            "cached": False,
            "engine_mode": SEARCH_ENGINE_MODE
        }
        
        # ============================================================
        # STEP 17: Cache Result (Page 1 only)
        # ============================================================
        if use_cache and formatted_listings:
            _search_cache.set(normalized_query, filters, result)
        
        return result
    
    def _format_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Format listing for API response (minimal fields)."""
        return {
            "_id": str(listing["_id"]),
            "productId": str(listing.get("productId", "")),
            "productName": listing.get("productName", ""),
            "categoryId": str(listing.get("categoryId", "")) if listing.get("categoryId") else None,
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
            "city": listing.get("city"),
            "state": listing.get("state"),
            "sellerId": str(listing.get("sellerId", "")),
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
        results_count: int,
        search_time_ms: int
    ):
        """
        Log search for analytics (fire and forget).
        """
        if not query:
            return
        
        normalized_query = query.lower().strip()
        
        try:
            await self.db.searchAnalytics.update_one(
                {"query": normalized_query},
                {
                    "$inc": {"count": 1},
                    "$set": {
                        "lastSearchedAt": datetime.now(timezone.utc),
                        "lastResultsCount": results_count,
                        "lastSearchTimeMs": search_time_ms,
                        "lastFilters": filters
                    },
                    "$setOnInsert": {
                        "query": normalized_query,
                        "createdAt": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.debug(f"Analytics update failed: {e}")
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries."""
        try:
            results = await self.db.searchAnalytics.find(
                {"count": {"$gte": 2}}
            ).sort("count", -1).limit(limit).to_list(limit)
            
            return [
                {
                    "query": r["query"],
                    "count": r["count"],
                    "lastSearchedAt": r.get("lastSearchedAt")
                }
                for r in results
            ]
        except Exception:
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics (for monitoring)."""
        return {
            "cache_size": len(_search_cache.cache),
            "max_size": _search_cache.max_size,
            "ttl_seconds": _search_cache.ttl
        }


def create_enterprise_search_service(db):
    """Factory function to create search service."""
    return EnterpriseSearchService(db)
