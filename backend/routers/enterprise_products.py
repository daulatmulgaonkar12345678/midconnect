"""
ENTERPRISE PRODUCT ENDPOINTS
=============================

New enterprise-grade endpoints for structured product pages:
- GET /products/{id}/enterprise - Full product data with aggregation
- GET /products/{id}/facets - Dynamic filter values
- POST /products/{id}/filter - Structured attribute filtering with RANKING

NO N+1 queries.
NO joins during search.
USES denormalized searchableAttributes.
SUPPORTS enterprise ranking with configurable weights.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from bson import ObjectId
import logging

from services.ranking_service import enterprise_ranker
from config.ranking_config import ranking_config

logger = logging.getLogger("enterprise_products")


class FilterRequest(BaseModel):
    """Request model for structured attribute filtering."""
    attributes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Attribute filters: {'power': {'$gte': 40}, 'voltage': '415'}"
    )
    sortBy: Literal["price", "leadTime", "stock", "updatedAt", "ranking"] = Field(
        default="price",
        description="Sort field. Use 'ranking' for enterprise ranking score"
    )
    order: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort order"
    )
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    # Buyer context for location-based ranking
    buyerCity: Optional[str] = Field(default=None, description="Buyer's city for proximity ranking")
    buyerState: Optional[str] = Field(default=None, description="Buyer's state for proximity ranking")
    # Buyer ID for behavior-based boost (optional, from auth token)
    buyerId: Optional[str] = Field(default=None, description="Buyer ID for personalized behavior boost")
    # Debug mode for ranking breakdown
    debug: bool = Field(default=False, description="Include ranking breakdown in response")


def create_enterprise_product_router(db):
    """Create enterprise product router with optimized endpoints."""
    router = APIRouter(prefix="/products", tags=["Enterprise Products"])
    
    def serialize_doc(doc):
        """Recursively serialize MongoDB documents."""
        if doc is None:
            return None
        if isinstance(doc, ObjectId):
            return str(doc)
        if isinstance(doc, datetime):
            return doc.isoformat()
        if isinstance(doc, list):
            return [serialize_doc(item) for item in doc]
        if isinstance(doc, dict):
            return {k: serialize_doc(v) for k, v in doc.items()}
        return doc
    
    @router.get("/{product_id}/enterprise")
    async def get_product_enterprise(
        product_id: str,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        """
        Enterprise product page endpoint.
        
        SINGLE AGGREGATION - NO N+1 QUERIES.
        
        Returns:
        - Product details
        - Spec template structure
        - Seller count, min price, variant count
        - Paginated seller listings with denormalized attributes
        - Available facets for filtering
        """
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # Get product
        product = await db.products.find_one({"_id": product_oid})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get category
        category = None
        if product.get("categoryId"):
            category = await db.categories.find_one({"_id": product["categoryId"]})
        
        # Get spec template
        spec_template = None
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            template_id = template_ids[0] if isinstance(template_ids[0], ObjectId) else ObjectId(str(template_ids[0]))
            spec_template = await db.specTemplates.find_one({"_id": template_id})
        
        # OPTIMIZED AGGREGATION - Two-phase approach for better performance
        skip = (page - 1) * limit
        
        # Phase 1: Get summary statistics (no $lookup needed)
        summary_pipeline = [
            {"$match": {"productId": product_oid, "status": "active"}},
            {"$facet": {
                "totalCount": [{"$count": "count"}],
                "minPrice": [
                    {"$unwind": "$pricingTiers"},
                    {"$group": {"_id": None, "min": {"$min": "$pricingTiers.pricePerUnit"}}}
                ],
                "variantCount": [
                    {"$group": {"_id": "$variantId"}},
                    {"$count": "count"}
                ],
                "facets": [
                    {"$limit": 1000},  # Sample for facets to improve performance
                    {"$group": {
                        "_id": None,
                        "allAttributes": {"$push": "$searchableAttributes"}
                    }}
                ]
            }}
        ]
        
        # Phase 2: Get paginated listings with seller lookup (only for the page)
        listings_pipeline = [
            {"$match": {"productId": product_oid, "status": "active"}},
            {"$sort": {"pricingTiers.0.pricePerUnit": 1}},
            {"$skip": skip},
            {"$limit": limit},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "sellerData"
            }},
            {"$unwind": {"path": "$sellerData", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "_id": 1,
                "sellerId": 1,
                "variantId": 1,
                "searchableAttributes": 1,
                "attributeLabels": 1,
                "pricingTiers": 1,
                "moq": 1,
                "stock": 1,
                "leadTime": 1,
                "images": {"$slice": ["$images", 2]},
                "description": 1,
                "sellerRole": 1,
                "updatedAt": 1,
                "sellerProfile": {
                    "businessName": {"$ifNull": ["$sellerData.profile.businessName", "$sellerData.businessName"]},
                    "city": "$sellerData.profile.city",
                    "state": "$sellerData.profile.state"
                }
            }}
        ]
        
        # Execute both in parallel
        import asyncio
        summary_task = db.sellerListings.aggregate(summary_pipeline).to_list(1)
        listings_task = db.sellerListings.aggregate(listings_pipeline).to_list(limit)
        
        summary_result, listings = await asyncio.gather(summary_task, listings_task)
        
        if not summary_result:
            summary_result = [{"totalCount": [], "minPrice": [], "variantCount": [], "facets": []}]
        
        agg_result = summary_result[0]
        
        # Extract values
        total_count = agg_result["totalCount"][0]["count"] if agg_result["totalCount"] else 0
        min_price = agg_result["minPrice"][0]["min"] if agg_result["minPrice"] else None
        variant_count = agg_result["variantCount"][0]["count"] if agg_result["variantCount"] else 0
        
        # Build dynamic facets from attribute values
        facets = {}
        if agg_result["facets"] and agg_result["facets"][0]:
            all_attrs = agg_result["facets"][0].get("allAttributes", [])
            for attrs in all_attrs:
                if attrs:
                    for key, value in attrs.items():
                        if key not in facets:
                            facets[key] = set()
                        if value is not None:
                            facets[key].add(value if not isinstance(value, float) else round(value, 2))
            # Convert sets to sorted lists
            facets = {k: sorted(list(v), key=lambda x: (isinstance(x, str), x)) for k, v in facets.items()}
        
        # Format sellers
        sellers = []
        for listing in listings:
            seller_profile = listing.get("sellerProfile", {})
            pricing = listing.get("pricingTiers", [])
            lowest_price = min([t.get("pricePerUnit", 0) for t in pricing]) if pricing else None
            
            sellers.append({
                "listingId": str(listing["_id"]),
                "sellerId": str(listing["sellerId"]),
                "variantId": str(listing.get("variantId")) if listing.get("variantId") else None,
                "companyName": seller_profile.get("businessName") or "Verified Seller",
                "location": f"{seller_profile.get('city', '')}, {seller_profile.get('state', '')}".strip(", "),
                "sellerRole": listing.get("sellerRole", "dealer"),
                "searchableAttributes": listing.get("searchableAttributes", {}),
                "attributeLabels": listing.get("attributeLabels", {}),
                "pricingTiers": serialize_doc(pricing),
                "lowestPrice": lowest_price,
                "moq": listing.get("moq", 1),
                "stock": listing.get("stock", 0),
                "leadTimeDays": listing.get("leadTime"),
                "images": listing.get("images", []),
                "stockStatus": "in_stock" if listing.get("stock", 0) > 0 else "out_of_stock"
            })
        
        # Build response
        return serialize_doc({
            "product": {
                "_id": product["_id"],
                "name": product.get("name"),
                "slug": product.get("slug"),
                "description": product.get("description"),
                "images": product.get("images", []),
                "categoryId": product.get("categoryId"),
                "categoryName": category.get("name") if category else None
            },
            "specTemplate": {
                "templateId": spec_template["_id"] if spec_template else None,
                "name": spec_template.get("name") if spec_template else None,
                "fields": spec_template.get("fields", []) if spec_template else [],
                "version": spec_template.get("version", 1) if spec_template else None
            } if spec_template else None,
            "summary": {
                "sellerCount": total_count,
                "minPrice": min_price,
                "variantCount": variant_count,
                "totalPages": (total_count + limit - 1) // limit if total_count > 0 else 1
            },
            "availableFacets": facets,
            "sellers": sellers,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if total_count > 0 else 1
            }
        })
    
    @router.get("/{product_id}/facets")
    async def get_product_facets(product_id: str):
        """
        Get available filter values for a product.
        
        USES denormalized searchableAttributes - NO JOINS.
        
        Returns dynamic facets based on specTemplate fields.
        """
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # Get product and its spec template
        product = await db.products.find_one({"_id": product_oid})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get spec template for field metadata
        spec_template = None
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            template_id = template_ids[0] if isinstance(template_ids[0], ObjectId) else ObjectId(str(template_ids[0]))
            spec_template = await db.specTemplates.find_one({"_id": template_id})
        
        # Build facet aggregation dynamically
        pipeline = [
            {"$match": {"productId": product_oid, "status": "active"}},
            {"$group": {
                "_id": None,
                "allAttributes": {"$push": "$searchableAttributes"},
                "count": {"$sum": 1}
            }}
        ]
        
        result = await db.sellerListings.aggregate(pipeline).to_list(1)
        
        facets = {}
        facet_metadata = {}
        
        # Extract unique values per attribute
        if result and result[0]:
            all_attrs = result[0].get("allAttributes", [])
            for attrs in all_attrs:
                if attrs:
                    for key, value in attrs.items():
                        if key not in facets:
                            facets[key] = set()
                        if value is not None:
                            facets[key].add(value if not isinstance(value, float) else round(value, 2))
        
        # Add metadata from spec template
        if spec_template and spec_template.get("fields"):
            for field in spec_template["fields"]:
                key = field.get("key")
                if key:
                    facet_metadata[key] = {
                        "label": field.get("label", key),
                        "fieldType": field.get("fieldType", "text"),
                        "unit": field.get("unit"),
                        "filterable": field.get("filterable", True),
                        "options": field.get("options")
                    }
        
        # Build response with sorted values
        facets_response = {}
        for key, values in facets.items():
            sorted_values = sorted(list(values), key=lambda x: (isinstance(x, str), x))
            facets_response[key] = {
                "values": sorted_values,
                "count": len(sorted_values),
                "metadata": facet_metadata.get(key, {"label": key, "fieldType": "text"})
            }
        
        return {
            "productId": product_id,
            "facets": facets_response,
            "totalListings": result[0]["count"] if result else 0,
            "specTemplate": spec_template.get("name") if spec_template else None
        }
    
    @router.post("/{product_id}/filter")
    async def filter_product_listings(
        product_id: str,
        request: FilterRequest
    ):
        """
        Filter seller listings by structured attributes.
        
        NO JOINS - uses denormalized searchableAttributes.
        SINGLE QUERY with index support.
        
        Implements 4-level fallback:
        1. Remove lowest priority filter
        2. Expand numeric range ±10%
        3. Show other variants of same product
        4. Show related category products
        """
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # Build match filter
        match = {
            "productId": product_oid,
            "status": "active"
        }
        
        # Add attribute filters
        original_filters = {}
        if request.attributes:
            for key, condition in request.attributes.items():
                if isinstance(condition, dict):
                    # MongoDB operator: {"$gte": 40}
                    match[f"searchableAttributes.{key}"] = condition
                else:
                    # Exact match
                    match[f"searchableAttributes.{key}"] = condition
                original_filters[key] = condition
        
        # Sort mapping
        sort_field_map = {
            "price": "pricingTiers.0.pricePerUnit",
            "leadTime": "leadTime",
            "stock": "stock",
            "updatedAt": "updatedAt"
        }
        sort_field = sort_field_map.get(request.sortBy, "pricingTiers.0.pricePerUnit")
        sort_order = 1 if request.order == "asc" else -1
        
        skip = (request.page - 1) * request.limit
        
        # Execute query
        results = await db.sellerListings.find(match)\
            .sort(sort_field, sort_order)\
            .skip(skip)\
            .limit(request.limit)\
            .to_list(request.limit)
        
        total = await db.sellerListings.count_documents(match)
        
        fallback_level = 0
        fallback_message = None
        
        # FALLBACK LOGIC if no results
        if total == 0 and original_filters:
            # Level 1: Remove lowest priority filter (last added)
            if len(original_filters) > 1:
                fallback_level = 1
                # Remove last filter
                reduced_filters = dict(list(original_filters.items())[:-1])
                match = {"productId": product_oid, "status": "active"}
                for key, condition in reduced_filters.items():
                    if isinstance(condition, dict):
                        match[f"searchableAttributes.{key}"] = condition
                    else:
                        match[f"searchableAttributes.{key}"] = condition
                
                results = await db.sellerListings.find(match)\
                    .sort(sort_field, sort_order)\
                    .skip(skip)\
                    .limit(request.limit)\
                    .to_list(request.limit)
                total = await db.sellerListings.count_documents(match)
                fallback_message = "Exact match not found. Showing results with fewer filters."
            
            # Level 2: Expand numeric range ±10%
            if total == 0:
                fallback_level = 2
                match = {"productId": product_oid, "status": "active"}
                for key, condition in original_filters.items():
                    if isinstance(condition, dict) and "$gte" in condition:
                        # Expand range
                        original_val = condition.get("$gte", 0)
                        match[f"searchableAttributes.{key}"] = {
                            "$gte": original_val * 0.9,
                            "$lte": original_val * 1.1
                        }
                    elif isinstance(condition, (int, float)):
                        match[f"searchableAttributes.{key}"] = {
                            "$gte": condition * 0.9,
                            "$lte": condition * 1.1
                        }
                
                results = await db.sellerListings.find(match)\
                    .sort(sort_field, sort_order)\
                    .skip(skip)\
                    .limit(request.limit)\
                    .to_list(request.limit)
                total = await db.sellerListings.count_documents(match)
                fallback_message = "Exact match not found. Showing similar specifications (±10%)."
            
            # Level 3: Show other variants of same product
            if total == 0:
                fallback_level = 3
                match = {"productId": product_oid, "status": "active"}
                results = await db.sellerListings.find(match)\
                    .sort(sort_field, sort_order)\
                    .skip(skip)\
                    .limit(request.limit)\
                    .to_list(request.limit)
                total = await db.sellerListings.count_documents(match)
                fallback_message = "Exact match not found. Showing all available variants."
            
            # Level 4: Show related category products
            if total == 0:
                fallback_level = 4
                product = await db.products.find_one({"_id": product_oid})
                if product and product.get("categoryId"):
                    # Get other products in same category
                    related_products = await db.products.find({
                        "categoryId": product["categoryId"],
                        "_id": {"$ne": product_oid}
                    }).limit(5).to_list(5)
                    
                    if related_products:
                        related_ids = [p["_id"] for p in related_products]
                        match = {"productId": {"$in": related_ids}, "status": "active"}
                        results = await db.sellerListings.find(match)\
                            .sort(sort_field, sort_order)\
                            .skip(skip)\
                            .limit(request.limit)\
                            .to_list(request.limit)
                        total = await db.sellerListings.count_documents(match)
                        fallback_message = "No listings found for this product. Showing related products in same category."
        
        # Format results
        formatted = []
        
        # Determine match quality based on fallback level
        match_quality = "exact" if fallback_level == 0 else (
            "partial" if fallback_level <= 2 else "fallback"
        )
        
        # If sorting by ranking, apply enterprise ranking
        if request.sortBy == "ranking":
            # Build buyer context for location-based ranking
            buyer_context = None
            if request.buyerCity or request.buyerState:
                buyer_context = {
                    "city": request.buyerCity,
                    "state": request.buyerState
                }
            
            # Load subscription data for sellers using unified engine
            seller_ids = list(set(str(r.get("sellerId")) for r in results if r.get("sellerId")))
            subscription_cache = {}
            
            if seller_ids:
                # Use subscription engine for consistent logic
                from services.subscription_engine import SubscriptionEngine
                sub_engine = SubscriptionEngine(db)
                subscription_cache = await sub_engine.get_subscription_for_ranking(seller_ids)
            
            # Prepare listings with seller profile data for ranking
            listings_for_ranking = []
            for listing in results:
                listing_dict = dict(listing)
                # Add seller profile if available from lookup
                if "sellerData" in listing:
                    listing_dict["sellerProfile"] = {
                        "city": listing.get("sellerData", {}).get("profile", {}).get("city"),
                        "state": listing.get("sellerData", {}).get("profile", {}).get("state")
                    }
                listings_for_ranking.append(listing_dict)
            
            # Load behavior boosts if buyer is authenticated
            behavior_boost_cache = {}
            if request.buyerId and ObjectId.is_valid(request.buyerId):
                try:
                    from services.buyer_interaction_service import BuyerInteractionService
                    interaction_service = BuyerInteractionService(db)
                    behavior_boost_cache = await interaction_service.get_batch_boosts(
                        buyer_id=ObjectId(request.buyerId),
                        product_id=product_oid,
                        seller_ids=seller_ids
                    )
                except Exception as e:
                    logger.warning(f"Failed to load behavior boosts: {e}")
            
            # Apply ranking
            ranked_results = enterprise_ranker.rank_listings(
                listings=listings_for_ranking,
                buyer_context=buyer_context,
                match_quality=match_quality,
                subscription_cache=subscription_cache,
                behavior_boost_cache=behavior_boost_cache,
                debug=request.debug
            )
            
            # Use ranked results
            results = ranked_results
        
        for listing in results:
            pricing = listing.get("pricingTiers", [])
            lowest = min([t.get("pricePerUnit", 0) for t in pricing]) if pricing else None
            
            result_item = serialize_doc({
                "listingId": listing.get("_id") or listing.get("listingId"),
                "sellerId": listing["sellerId"],
                "variantId": listing.get("variantId"),
                "searchableAttributes": listing.get("searchableAttributes", {}),
                "attributeLabels": listing.get("attributeLabels", {}),
                "pricingTiers": pricing,
                "lowestPrice": lowest,
                "moq": listing.get("moq", 1),
                "stock": listing.get("stock", 0),
                "leadTimeDays": listing.get("leadTime"),
                "images": listing.get("images", [])[:2],
                "sellerRole": listing.get("sellerRole"),
                "rankingScore": listing.get("rankingScore")  # Include if ranked
            })
            
            # Include ranking breakdown in debug mode
            if request.debug and listing.get("rankingBreakdown"):
                result_item["rankingBreakdown"] = listing["rankingBreakdown"]
            
            formatted.append(result_item)
        
        return {
            "results": formatted,
            "total": total,
            "page": request.page,
            "pages": (total + request.limit - 1) // request.limit if total > 0 else 1,
            "fallbackLevel": fallback_level,
            "fallbackMessage": fallback_message,
            "appliedFilters": original_filters,
            "sortedBy": request.sortBy
        }
    
    # ==========================================
    # RANKING CONFIGURATION ENDPOINTS
    # ==========================================
    
    @router.get("/ranking/config")
    async def get_ranking_config():
        """
        Get current ranking weight configuration.
        
        Returns all weights used in the enterprise ranking engine.
        """
        return {
            "weights": ranking_config.get_weights_dict(),
            "maxPossibleScore": ranking_config.get_max_possible_score(),
            "description": {
                "stock_available": "Points for having stock > 0",
                "stock_high": "Bonus for stock > 50 units",
                "subscription_free": "Points for free tier sellers",
                "subscription_trial": "Points for trial tier sellers",
                "subscription_pro": "Points for pro tier sellers (monetization)",
                "subscription_enterprise": "Points for enterprise tier sellers",
                "lead_time_under_3_days": "Points for fast delivery",
                "lead_time_under_7_days": "Points for quick delivery",
                "price_lowest_10_percent": "Points for being in cheapest 10%",
                "price_lowest_20_percent": "Points for being in cheapest 20%",
                "location_same_city": "Points for same city as buyer",
                "location_same_state": "Points for same state as buyer",
                "spec_exact_match": "Points for exact specification match",
                "verified_seller": "Bonus for manufacturer/authorized dealer"
            }
        }
    
    @router.post("/ranking/config")
    async def update_ranking_config(updates: Dict[str, float]):
        """
        Update ranking weight configuration.
        
        Allows A/B testing and tuning of ranking weights.
        
        Example:
        {"subscription_pro": 20, "location_same_state": 12}
        """
        # Validate weight names
        valid_weights = ranking_config.get_weights_dict().keys()
        invalid_keys = [k for k in updates.keys() if k not in valid_weights]
        
        if invalid_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid weight keys: {invalid_keys}. Valid keys: {list(valid_weights)}"
            )
        
        # Apply updates
        ranking_config.update_weights(updates)
        
        return {
            "message": "Ranking weights updated",
            "updatedWeights": updates,
            "currentConfig": ranking_config.get_weights_dict()
        }
    
    @router.post("/ranking/reset")
    async def reset_ranking_config():
        """
        Reset ranking weights to defaults.
        """
        ranking_config.reset_weights()
        return {
            "message": "Ranking weights reset to defaults",
            "currentConfig": ranking_config.get_weights_dict()
        }
    
    return router
