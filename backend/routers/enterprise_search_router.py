"""
ENTERPRISE SEARCH ROUTER
========================

Intelligent search system with:
- Unit normalization (1/2hp = 0.5hp = half hp)
- Synonym expansion (ampere = amp = amps)
- Fuzzy matching
- Geo-radius filtering
- Intelligent fallback
- Related suggestions
- STRUCTURED location autocomplete (seller-validated cities only)
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
import re
import logging

from services.search_normalization_service import search_normalizer, ParsedQuery
from services.pincode_geocode_service import geocode_service, GeoLocation
from services.seller_location_service import create_seller_location_service

logger = logging.getLogger(__name__)


# ==================== REQUEST/RESPONSE MODELS ====================

class LocationFilter(BaseModel):
    """Structured location filter from frontend"""
    areaType: str  # 'city', 'state', 'pincode', 'radius', 'pan_india'
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    coordinates: Optional[List[float]] = None  # [lng, lat]
    radiusKm: Optional[int] = None


class SearchRequest(BaseModel):
    """Structured search request"""
    query: str
    location: Optional[LocationFilter] = None
    category: Optional[str] = None
    minPrice: Optional[float] = None
    maxPrice: Optional[float] = None
    voltage: Optional[float] = None
    powerHp: Optional[float] = None
    phase: Optional[str] = None
    page: int = 1
    limit: int = 20
    sortBy: str = "relevance"


def create_enterprise_search_router(db, require_auth=None):
    """
    Factory function to create enterprise search router.
    """
    router = APIRouter(prefix="/search", tags=["Enterprise Search"])
    
    # Initialize seller location service
    location_service = create_seller_location_service(db)
    
    # ==================== LOCATION AUTOCOMPLETE ====================
    
    @router.get("/locations/active")
    async def get_active_seller_cities(
        limit: int = Query(20, ge=1, le=50)
    ):
        """
        Get all cities with active sellers (no query required).
        
        Used by the location dropdown to show options immediately.
        """
        try:
            cities = await location_service.get_cities_with_sellers(limit)
            return {
                "cities": [
                    {
                        "label": f"{c.get('city')}, {c.get('state')}",
                        "type": "city",
                        "city": c.get("city"),
                        "state": c.get("state"),
                        "sellerCount": c.get("sellerCount", 0)
                    }
                    for c in cities
                ]
            }
        except Exception as e:
            logger.error(f"Get active cities error: {e}")
            return {"cities": []}
    
    @router.get("/locations")
    async def location_autocomplete(
        q: str = Query(..., min_length=1, description="Location query (city, state, or pincode)"),
        limit: int = Query(10, ge=1, le=20)
    ):
        """
        Location autocomplete for search.
        
        ONLY returns cities where sellers are onboarded.
        
        Example:
            GET /api/search/locations?q=pu
            
        Returns:
            [
                {"label": "Pune, Maharashtra", "type": "city", "sellerCount": 42},
                {"label": "Punjab", "type": "state"},
                {"label": "Puri, Odisha", "type": "city", "sellerCount": 5}
            ]
        """
        try:
            suggestions = await location_service.get_location_suggestions(q, limit)
            
            return {
                "query": q,
                "suggestions": [
                    {
                        "label": s.label,
                        "type": s.type,
                        "city": s.city,
                        "state": s.state,
                        "pincode": s.pincode,
                        "coordinates": s.coordinates,
                        "sellerCount": s.seller_count
                    }
                    for s in suggestions
                ]
            }
        except Exception as e:
            logger.error(f"Location autocomplete error: {e}")
            return {"query": q, "suggestions": []}
    
    @router.get("/locations/check")
    async def check_location_availability(
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        pincode: Optional[str] = Query(None)
    ):
        """
        Check if sellers exist in a location.
        
        If no sellers, returns nearby alternatives.
        
        Example:
            GET /api/search/locations/check?city=Nashik
            
        Returns:
            {
                "hasSellers": false,
                "message": "No sellers onboarded yet in Nashik",
                "nearbyAlternatives": [
                    {"label": "Pune, Maharashtra (85 km away)", "sellerCount": 42},
                    {"label": "Mumbai, Maharashtra (165 km away)", "sellerCount": 78}
                ]
            }
        """
        try:
            result = await location_service.check_sellers_in_location(
                city=city, state=state, pincode=pincode
            )
            return result
        except Exception as e:
            logger.error(f"Location check error: {e}")
            return {"hasSellers": False, "error": str(e)}
    
    @router.post("/locations/rebuild")
    async def rebuild_active_seller_cities():
        """
        Admin endpoint to rebuild activeSellerCities collection.
        Call this if data gets out of sync.
        """
        try:
            count = await location_service.rebuild_active_seller_cities()
            return {"success": True, "citiesWithSellers": count}
        except Exception as e:
            logger.error(f"Rebuild error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== SEARCH ENDPOINT ====================
    
    @router.get("")
    async def enterprise_search(
        q: str = Query("", description="Search query"),
        category: Optional[str] = Query(None, description="Category ID filter"),
        manufacturer: Optional[str] = Query(None, description="Manufacturer ID filter"),
        # Location filters
        city: Optional[str] = Query(None, description="Filter by city"),
        state: Optional[str] = Query(None, description="Filter by state"),
        # Price filters
        min_price: Optional[float] = Query(None, alias="minPrice"),
        max_price: Optional[float] = Query(None, alias="maxPrice"),
        # Stock filter
        in_stock: Optional[bool] = Query(None, alias="inStock", description="Only show in-stock items"),
        # Pagination & sorting
        page: int = Query(1, ge=1, le=250),  # HARD LIMIT: max page 250
        limit: int = Query(20, ge=1, le=50),  # HARD LIMIT: 50 max per page
        sort_by: str = Query("relevance", alias="sortBy", description="relevance, price_asc, price_desc, rating, recent"),
    ):
        """
        Enterprise-grade search with typo tolerance and compound filtering.
        
        SMART SEARCH FEATURES:
        - Typo tolerance (moter → motor)
        - Phonetic matching (motar → motor)
        - "Did you mean?" suggestions
        - Auto-correction for common typos
        
        PRODUCTION HARDENING:
        - Minimum query length: 2 characters
        - Maximum page: 250
        - Maximum per page: 50
        - Search timeout: 1.5s
        - LRU cache for page 1
        - Slow query logging (>700ms)
        """
        from services.enterprise_search_service import create_enterprise_search_service
        from services.smart_search_service import create_smart_search_service
        
        search_service = create_enterprise_search_service(db)
        smart_search = create_smart_search_service(db)
        
        # Get spelling suggestion first
        did_you_mean = None
        corrected_query = None
        
        if q and len(q) >= 2:
            try:
                spelling = await smart_search.get_spelling_suggestion(q)
                if spelling:
                    did_you_mean = spelling.get("corrected")
                    corrected_query = did_you_mean
            except Exception as e:
                logger.warning(f"Spelling suggestion error: {e}")
        
        # Perform search with original query
        results = await search_service.search(
            query=q,
            category_id=category,
            manufacturer_id=manufacturer,
            city=city,
            state=state,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock or False,
            page=page,
            limit=limit,
            sort_by=sort_by
        )
        
        # If no results and we have a spelling correction, try with corrected query
        if results.get("total", 0) == 0 and corrected_query and corrected_query.lower() != q.lower():
            corrected_results = await search_service.search(
                query=corrected_query,
                category_id=category,
                manufacturer_id=manufacturer,
                city=city,
                state=state,
                min_price=min_price,
                max_price=max_price,
                in_stock_only=in_stock or False,
                page=page,
                limit=limit,
                sort_by=sort_by
            )
            
            # If corrected query found results, use those
            if corrected_results.get("total", 0) > 0:
                corrected_results["originalQuery"] = q
                corrected_results["correctedQuery"] = corrected_query
                corrected_results["didYouMean"] = corrected_query
                corrected_results["autoCorreected"] = True
                return corrected_results
        
        # Add "Did you mean?" suggestion to response
        if did_you_mean and did_you_mean.lower() != q.lower():
            results["didYouMean"] = did_you_mean
        
        return results
    
    # ==================== GEO SEARCH WITH FALLBACK ====================
    
    @router.get("/geo")
    async def geo_search(
        q: str = Query("", description="Search query"),
        # Geo parameters
        lat: Optional[float] = Query(None, description="User latitude"),
        lng: Optional[float] = Query(None, description="User longitude"),
        radius_km: int = Query(50, ge=1, le=500, alias="radiusKm", description="Search radius in km"),
        city: Optional[str] = Query(None, description="City filter"),
        state: Optional[str] = Query(None, description="State filter"),
        # Other filters
        category: Optional[str] = Query(None, description="Category ID"),
        min_price: Optional[float] = Query(None, alias="minPrice"),
        max_price: Optional[float] = Query(None, alias="maxPrice"),
        in_stock: Optional[bool] = Query(None, alias="inStock"),
        # Pagination
        limit: int = Query(20, ge=1, le=50),
        skip: int = Query(0, ge=0, le=5000),
    ):
        """
        Geo-enabled search with intelligent fallback strategy.
        
        FALLBACK ORDER:
        1. City exact match → 
        2. Radius search (if coords provided) →
        3. State → 
        4. Pan India
        
        RETURNS:
        - `fallbackUsed`: "radius" | "state" | "pan_india" | null
        - `message`: User-friendly fallback message
        - `searchedLocation`: Original search parameters
        
        USAGE:
        - /search/geo?city=Pune&state=Maharashtra → City fallback
        - /search/geo?lat=18.52&lng=73.85&radiusKm=50 → Radius search
        - /search/geo?q=motor&city=Amritsar → Text + location search
        """
        from services.enterprise_search_service import create_enterprise_search_service
        
        search_service = create_enterprise_search_service(db)
        
        results = await search_service.geo_search(
            query=q,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            city=city,
            state=state,
            category_id=category,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock or False,
            limit=limit,
            skip=skip,
        )
        
        return results
    
    @router.get("/stats")
    async def search_stats():
        """
        Get search service statistics (cache, performance).
        For monitoring purposes.
        """
        from services.enterprise_search_service import create_enterprise_search_service
        
        search_service = create_enterprise_search_service(db)
        cache_stats = search_service.get_cache_stats()
        
        # Get popular searches
        popular = await search_service.get_popular_searches(limit=5)
        
        return {
            "cache": cache_stats,
            "popularSearches": popular,
            "config": {
                "maxResults": 50,
                "maxPage": 250,
                "searchTimeoutSec": 1.5,
                "slowQueryThresholdMs": 700
            }
        }
    
    @router.get("/autocomplete")
    async def search_autocomplete(
        q: str = Query(..., min_length=2, description="Partial search query"),
        limit: int = Query(10, ge=1, le=20)
    ):
        """
        Smart autocomplete suggestions with typo tolerance.
        
        Features:
        - Direct product/category matches
        - Fuzzy matching for typos (moter → motor)
        - Phonetic matching (India-friendly)
        - "Did you mean?" suggestions
        - Popular searches ranking
        """
        try:
            from services.smart_search_service import create_smart_search_service
            
            smart_search = create_smart_search_service(db)
            suggestions = []
            did_you_mean = None
            corrected_query = None
            
            # Normalize the query for better matching
            parsed = search_normalizer.parse_search_query(q)
            
            # Get spelling suggestion
            spelling = await smart_search.get_spelling_suggestion(q)
            if spelling:
                did_you_mean = spelling.get("corrected")
                corrected_query = did_you_mean
            
            # Use corrected query for matching
            search_q = corrected_query or q
            
            # 1. Product name matches (direct + fuzzy)
            product_regex = {"$regex": search_q, "$options": "i"}
            products = await db.products.find(
                {"name": product_regex, "isActive": True},
                {"name": 1, "categoryName": 1}
            ).limit(5).to_list(5)
            
            for p in products:
                suggestions.append({
                    "type": "product",
                    "text": p.get("name"),
                    "category": p.get("categoryName"),
                    "icon": "package"
                })
            
            # 2. If not enough direct matches, try fuzzy
            if len(suggestions) < 3:
                fuzzy_result = await smart_search.get_smart_autocomplete(q, limit=5)
                for s in fuzzy_result.get("suggestions", []):
                    if s.get("text") not in [x.get("text") for x in suggestions]:
                        suggestions.append({
                            "type": "product",
                            "text": s.get("text"),
                            "matchType": s.get("matchType", "fuzzy"),
                            "icon": "package"
                        })
            
            # 3. Category matches
            categories = await db.categories.find(
                {"name": product_regex, "is_active": True},
                {"name": 1}
            ).limit(3).to_list(3)
            
            for c in categories:
                suggestions.append({
                    "type": "category",
                    "text": c.get("name"),
                    "icon": "folder"
                })
            
            # 4. Popular searches (from analytics)
            popular = await db.searchAnalytics.aggregate([
                {"$match": {"query": {"$regex": f"^{search_q}", "$options": "i"}}},
                {"$group": {"_id": "$query", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 3}
            ]).to_list(3)
            
            for p in popular:
                if p["_id"] not in [s["text"] for s in suggestions]:
                    suggestions.append({
                        "type": "popular",
                        "text": p["_id"],
                        "count": p["count"],
                        "icon": "trending"
                    })
            
            # 5. Attribute-based suggestions
            if parsed.extracted_attributes:
                attr_suggestions = generate_attribute_suggestions(parsed)
                suggestions.extend(attr_suggestions[:3])
            
            return {
                "query": q,
                "correctedQuery": corrected_query,
                "didYouMean": did_you_mean if did_you_mean and did_you_mean.lower() != q.lower() else None,
                "suggestions": suggestions[:limit]
            }
            
        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
            return {"query": q, "suggestions": []}
    
    @router.get("/spelling")
    async def check_spelling(
        q: str = Query(..., min_length=2, description="Query to check")
    ):
        """
        Check spelling and get suggestions.
        
        Returns:
        - corrected: Corrected query (if different)
        - corrections: List of individual word corrections
        - type: "typo", "phonetic", or "fuzzy"
        - confidence: 0.0-1.0
        
        Examples:
        - moter → motor (typo)
        - motar → motor (phonetic)
        - elctric → electric (fuzzy)
        """
        try:
            from services.smart_search_service import create_smart_search_service
            
            smart_search = create_smart_search_service(db)
            result = await smart_search.get_spelling_suggestion(q)
            
            if result:
                return {
                    "query": q,
                    "corrected": result.get("corrected"),
                    "didYouMean": result.get("corrected"),
                    "corrections": result.get("corrections", []),
                    "type": result.get("type"),
                    "confidence": result.get("confidence")
                }
            else:
                return {
                    "query": q,
                    "corrected": None,
                    "didYouMean": None,
                    "message": "No spelling corrections needed"
                }
                
        except Exception as e:
            logger.error(f"Spelling check error: {e}")
            return {"query": q, "error": str(e)}
    
    @router.get("/related")
    async def get_related_searches(
        q: str = Query(..., description="Current search query"),
        limit: int = Query(5, ge=1, le=10)
    ):
        """
        Get related search suggestions.
        """
        try:
            related = []
            parsed = search_normalizer.parse_search_query(q)
            
            # 1. Add attribute variations
            if parsed.extracted_attributes.get('power_hp'):
                hp = parsed.extracted_attributes['power_hp']
                related.extend([
                    f"{hp} hp single phase motor",
                    f"{hp} hp three phase motor",
                    f"{hp * 2} hp motor",  # Double power
                ])
            
            if parsed.category_hint:
                category = parsed.category_hint
                related.extend([
                    f"{category} price",
                    f"best {category}",
                    f"{category} near me",
                ])
            
            # 2. Get from search analytics
            analytics_related = await db.searchAnalytics.aggregate([
                {"$match": {
                    "query": {"$regex": parsed.search_tokens[0] if parsed.search_tokens else q, "$options": "i"},
                    "resultsCount": {"$gt": 0}
                }},
                {"$group": {"_id": "$query", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]).to_list(5)
            
            for r in analytics_related:
                if r["_id"].lower() != q.lower():
                    related.append(r["_id"])
            
            # Remove duplicates and limit
            seen = set()
            unique_related = []
            for r in related:
                r_lower = r.lower()
                if r_lower not in seen and r_lower != q.lower():
                    seen.add(r_lower)
                    unique_related.append(r)
            
            return {
                "query": q,
                "related": unique_related[:limit]
            }
            
        except Exception as e:
            logger.error(f"Related searches error: {e}")
            return {"query": q, "related": []}
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def execute_search_with_fallback(
        db,
        parsed: ParsedQuery,
        category_filter: Optional[str],
        pincode: Optional[str],
        radius_km: Optional[int],
        city: Optional[str],
        state: Optional[str],
        location_type: Optional[str],
        min_price: Optional[float],
        max_price: Optional[float],
        voltage: Optional[float],
        power_hp: Optional[float],
        phase: Optional[str],
        page: int,
        limit: int,
        sort_by: str
    ) -> Dict[str, Any]:
        """
        Execute search with intelligent fallback.
        
        Fallback levels:
        1. Exact match with all filters
        2. Remove attribute filters
        3. Text-only search
        4. Category search
        5. Trending products
        """
        
        # Get user location for geo search
        user_location = None
        if pincode or city:
            user_location = geocode_service.get_coordinates(pincode=pincode, city=city, state=state)
        
        # Build base query
        base_query = {"isActive": True, "status": "active"}
        
        # Category filter
        if category_filter:
            try:
                base_query["categoryId"] = ObjectId(category_filter)
            except Exception:
                pass
        elif parsed.category_hint:
            # Try to find category by name
            cat = await db.categories.find_one({
                "name": {"$regex": parsed.category_hint, "$options": "i"},
                "is_active": True
            })
            if cat:
                base_query["categoryId"] = cat["_id"]
        
        # Location filter
        if location_type == "city" and city:
            base_query["sellerCity"] = {"$regex": city, "$options": "i"}
        elif location_type == "state" and state:
            base_query["sellerState"] = {"$regex": state, "$options": "i"}
        # Note: For radius search, we'll filter after fetching if no geo index
        
        # Price filter
        if min_price is not None or max_price is not None:
            base_query["pricingTiers.0.pricePerUnit"] = {}
            if min_price is not None:
                base_query["pricingTiers.0.pricePerUnit"]["$gte"] = min_price
            if max_price is not None:
                base_query["pricingTiers.0.pricePerUnit"]["$lte"] = max_price
        
        # === LEVEL 1: Full search with all filters ===
        search_tokens = parsed.search_tokens + list(parsed.extracted_attributes.keys())
        
        if search_tokens:
            # Build text search pattern
            search_pattern = "|".join(re.escape(t) for t in search_tokens)
            text_query = {
                "$or": [
                    {"searchableText": {"$regex": search_pattern, "$options": "i"}},
                    {"normalizedSearchTokens": {"$in": [t.lower() for t in search_tokens]}},
                    {"productName": {"$regex": search_pattern, "$options": "i"}},
                ]
            }
            
            # Attribute filters
            attr_filters = []
            if voltage or parsed.extracted_attributes.get('voltage'):
                v = voltage or parsed.extracted_attributes.get('voltage')
                attr_filters.append({
                    "$or": [
                        {"searchableAttributes.voltage": v},
                        {"searchableAttributes.voltage": {"$gte": v - 10, "$lte": v + 10}}  # ±10V tolerance
                    ]
                })
            
            if power_hp or parsed.extracted_attributes.get('power_hp'):
                hp = power_hp or parsed.extracted_attributes.get('power_hp')
                attr_filters.append({
                    "$or": [
                        {"searchableAttributes.power": hp},
                        {"searchableAttributes.power_hp": hp},
                        {"searchableAttributes.power": {"$gte": hp * 0.9, "$lte": hp * 1.1}}  # ±10% tolerance
                    ]
                })
            
            if phase or parsed.extracted_attributes.get('phase'):
                p = phase or parsed.extracted_attributes.get('phase')
                attr_filters.append({
                    "searchableAttributes.phase": {"$regex": p, "$options": "i"}
                })
            
            # Combine queries
            full_query = {**base_query, **text_query}
            if attr_filters:
                full_query["$and"] = attr_filters
            
            results = await execute_query(db, full_query, page, limit, sort_by, user_location)
            
            if results["total"] > 0:
                results["searchLevel"] = 1
                results["searchType"] = "exact_match"
                return results
        
        # === LEVEL 2: Remove attribute filters ===
        if search_tokens:
            text_only_query = {**base_query, **text_query}
            results = await execute_query(db, text_only_query, page, limit, sort_by, user_location)
            
            if results["total"] > 0:
                results["searchLevel"] = 2
                results["searchType"] = "text_match"
                results["suggestion"] = f"Showing results for '{parsed.normalized_text}' without attribute filters"
                return results
        
        # === LEVEL 3: Category only ===
        if "categoryId" in base_query:
            cat_only_query = {"isActive": True, "status": "active", "categoryId": base_query["categoryId"]}
            results = await execute_query(db, cat_only_query, page, limit, sort_by, user_location)
            
            if results["total"] > 0:
                results["searchLevel"] = 3
                results["searchType"] = "category_match"
                results["suggestion"] = "No exact matches. Showing all products in this category."
                return results
        
        # === LEVEL 4: Trending/Popular products ===
        trending_query = {"isActive": True, "status": "active"}
        results = await execute_query(db, trending_query, page, limit, "recent", user_location)
        results["searchLevel"] = 4
        results["searchType"] = "trending"
        results["suggestion"] = f"No results for '{parsed.original}'. Showing trending products."
        
        return results
    
    async def execute_query(
        db,
        query: Dict,
        page: int,
        limit: int,
        sort_by: str,
        user_location: Optional[GeoLocation]
    ) -> Dict[str, Any]:
        """Execute the search query and return formatted results."""
        
        skip = (page - 1) * limit
        
        # Determine sort order
        sort_options = {
            "relevance": [("updatedAt", -1)],  # Default to recent
            "price_asc": [("pricingTiers.0.pricePerUnit", 1)],
            "price_desc": [("pricingTiers.0.pricePerUnit", -1)],
            "recent": [("createdAt", -1)],
            "rating": [("sellerRating", -1), ("updatedAt", -1)],
        }
        sort = sort_options.get(sort_by, sort_options["relevance"])
        
        # Execute query
        total = await db.sellerListings.count_documents(query)
        
        pipeline = [
            {"$match": query},
            {"$sort": dict(sort)},
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
            # Lookup category
            {"$lookup": {
                "from": "categories",
                "localField": "categoryId",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        ]
        
        listings = await db.sellerListings.aggregate(pipeline).to_list(limit)
        
        # Format results
        formatted = []
        for listing in listings:
            item = format_listing_for_search(listing, user_location)
            formatted.append(item)
        
        # Sort by distance if user location provided and sort_by is "nearest"
        if user_location and sort_by == "nearest":
            formatted.sort(key=lambda x: x.get("distance_km", 99999))
        
        return {
            "listings": formatted,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "hasMore": skip + len(formatted) < total
        }
    
    def format_listing_for_search(listing: Dict, user_location: Optional[GeoLocation]) -> Dict:
        """Format a listing for search results."""
        product = listing.get("product", {})
        seller = listing.get("seller", {})
        category = listing.get("category", {})
        profile = seller.get("profile", {})
        
        # Calculate distance if user location available
        distance_km = None
        if user_location and profile.get("latitude") and profile.get("longitude"):
            distance_km = geocode_service.calculate_distance_km(
                user_location.latitude,
                user_location.longitude,
                profile["latitude"],
                profile["longitude"]
            )
        elif user_location and profile.get("pincode"):
            # Try to get seller coordinates from pincode
            seller_loc = geocode_service.get_coordinates(pincode=profile["pincode"])
            if seller_loc:
                distance_km = geocode_service.calculate_distance_km(
                    user_location.latitude,
                    user_location.longitude,
                    seller_loc.latitude,
                    seller_loc.longitude
                )
        
        # Get price from first tier
        price = None
        pricing_tiers = listing.get("pricingTiers", [])
        if pricing_tiers:
            price = pricing_tiers[0].get("pricePerUnit")
        
        return {
            "_id": str(listing["_id"]),
            "productId": str(listing.get("productId", "")),
            "productName": product.get("name", listing.get("productName", "")),
            "categoryId": str(listing.get("categoryId", "")),
            "categoryName": category.get("name", ""),
            "description": listing.get("description", ""),
            "images": listing.get("images", []),
            "price": price,
            "currency": listing.get("currency", "INR"),
            "pricingTiers": pricing_tiers,
            "moq": listing.get("moq", 1),
            "stock": listing.get("stock", 0),
            "leadTime": listing.get("leadTime"),
            "searchableAttributes": listing.get("searchableAttributes", {}),
            "attributeLabels": listing.get("attributeLabels", {}),
            "seller": {
                "_id": str(seller.get("_id", listing.get("sellerId", ""))),
                "businessName": profile.get("businessName", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "verified": seller.get("gst", {}).get("verified", False),
            },
            "distance_km": round(distance_km, 1) if distance_km else None,
        }
    
    def generate_attribute_suggestions(parsed: ParsedQuery) -> List[Dict]:
        """Generate suggestions based on extracted attributes."""
        suggestions = []
        
        if parsed.extracted_attributes.get('power_hp'):
            hp = parsed.extracted_attributes['power_hp']
            suggestions.append({
                "type": "attribute",
                "text": f"{hp} hp motor",
                "icon": "zap"
            })
        
        if parsed.extracted_attributes.get('voltage'):
            v = parsed.extracted_attributes['voltage']
            suggestions.append({
                "type": "attribute", 
                "text": f"{int(v)}v motor",
                "icon": "zap"
            })
        
        return suggestions
    
    async def log_search_analytics(db, query: str, parsed: ParsedQuery, results_count: int):
        """Log search for analytics."""
        try:
            await db.searchAnalytics.insert_one({
                "query": query,
                "normalizedQuery": parsed.normalized_text,
                "extractedAttributes": parsed.extracted_attributes,
                "categoryHint": parsed.category_hint,
                "locationHint": parsed.location_hint,
                "resultsCount": results_count,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Failed to log search analytics: {e}")
    
    return router
