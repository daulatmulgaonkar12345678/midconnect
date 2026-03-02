"""
ENTERPRISE RESOLVER SERVICE
============================
Central source of truth for product and category resolution.

Supports:
- ObjectId lookup (primary, indexed)
- Slug lookup (SEO, indexed)
- Legacy ID lookup (redirects)

ARCHITECTURE RULES:
1. Always resolve to _id internally
2. Never use slug for internal queries
3. Use lean queries everywhere
4. Cache resolved entities

This resolver is the SINGLE ENTRY POINT for all product/category lookups.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from datetime import datetime, timezone

logger = logging.getLogger("resolver_service")


class EnterpriseResolver:
    """
    Central resolver for products and categories.
    
    Supports multiple identifier types:
    - ObjectId (primary, fastest)
    - Slug (SEO-friendly)
    - Legacy ID (for redirects)
    
    Returns lean documents with only needed fields.
    """
    
    # Default projection for lean queries
    PRODUCT_FIELDS = {
        "_id": 1,
        "name": 1,
        "slug": 1,
        "categoryId": 1,
        "categoryName": 1,
        "description": 1,
        "coverImageUrl": 1,
        "images": 1,
        "seoTitle": 1,
        "seoDescription": 1,
        "seoContent": 1,
        "specifications": 1,
        "normalizedSpecs": 1,
        "unit": 1,
        "family": 1,
        "variant": 1,
        "isActive": 1,
        "createdAt": 1,
        "updatedAt": 1
    }
    
    CATEGORY_FIELDS = {
        "_id": 1,
        "name": 1,
        "slug": 1,
        "description": 1,
        "image": 1,
        "icon": 1,
        "seoTitle": 1,
        "seoDescription": 1,
        "seoContent": 1,
        "isActive": 1
    }
    
    LISTING_FIELDS = {
        "_id": 1,
        "productId": 1,
        "sellerId": 1,
        "pricingTiers": 1,
        "moq": 1,
        "leadTime": 1,
        "stock": 1,
        "images": 1,
        "searchableAttributes": 1,
        "specifications": 1,
        "status": 1
    }
    
    def __init__(self, db):
        self.db = db
        self._cache = {}  # Simple in-memory cache (use Redis in production)
    
    # ==================== PRODUCT RESOLVER ====================
    
    async def resolve_product(
        self, 
        identifier: str,
        fields: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve product by any identifier type.
        
        Priority:
        1. ObjectId (fastest, indexed)
        2. Slug (SEO, indexed)
        3. Legacy ID (for redirects)
        
        Args:
            identifier: ObjectId, slug, or legacy ID
            fields: Optional projection (defaults to PRODUCT_FIELDS)
        
        Returns:
            Lean product document or None
        """
        if not identifier:
            return None
        
        projection = fields or self.PRODUCT_FIELDS
        product = None
        
        # Try 1: ObjectId (fastest)
        if len(identifier) == 24:
            try:
                oid = ObjectId(identifier)
                product = await self.db.products.find_one(
                    {"_id": oid},
                    projection
                )
            except Exception:
                pass
        
        # Try 2: Slug (indexed)
        if not product:
            product = await self.db.products.find_one(
                {"slug": identifier},
                projection
            )
        
        # Try 3: Legacy ID (for redirects)
        if not product:
            product = await self.db.products.find_one(
                {"legacyIds": identifier},
                projection
            )
        
        # Try 4: Legacy Slug (for redirects)
        if not product:
            product = await self.db.products.find_one(
                {"legacySlugs": identifier},
                projection
            )
        
        return product
    
    async def resolve_product_id(self, identifier: str) -> Optional[ObjectId]:
        """
        Resolve to product ObjectId only.
        
        Use this when you only need the _id for further queries.
        Faster than full product resolution.
        """
        product = await self.resolve_product(identifier, {"_id": 1})
        return product["_id"] if product else None
    
    async def get_product_with_redirect(
        self, 
        identifier: str
    ) -> Tuple[Optional[Dict], bool, Optional[str]]:
        """
        Resolve product with redirect information.
        
        Returns:
            (product, needs_redirect, canonical_slug)
        """
        product = await self.resolve_product(identifier)
        
        if not product:
            return None, False, None
        
        canonical_slug = product.get("slug")
        needs_redirect = identifier != canonical_slug
        
        return product, needs_redirect, canonical_slug
    
    # ==================== CATEGORY RESOLVER ====================
    
    async def resolve_category(
        self, 
        identifier: str,
        fields: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve category by any identifier type.
        """
        if not identifier:
            return None
        
        projection = fields or self.CATEGORY_FIELDS
        category = None
        
        # Try 1: ObjectId
        if len(identifier) == 24:
            try:
                oid = ObjectId(identifier)
                category = await self.db.categories.find_one(
                    {"_id": oid},
                    projection
                )
            except Exception:
                pass
        
        # Try 2: Slug
        if not category:
            category = await self.db.categories.find_one(
                {"slug": identifier},
                projection
            )
        
        # Try 3: Legacy ID
        if not category:
            category = await self.db.categories.find_one(
                {"legacyIds": identifier},
                projection
            )
        
        return category
    
    async def resolve_category_id(self, identifier: str) -> Optional[ObjectId]:
        """Resolve to category ObjectId only."""
        category = await self.resolve_category(identifier, {"_id": 1})
        return category["_id"] if category else None
    
    # ==================== LISTING RESOLVER ====================
    
    async def get_product_listings(
        self,
        product_id: ObjectId,
        status: str = "active",
        sort_by: str = "price",
        sort_order: int = 1,
        limit: int = 100,
        fields: Dict = None
    ) -> List[Dict[str, Any]]:
        """
        Get seller listings for a product.
        
        ALWAYS use product_id (ObjectId), never slug.
        This is indexed and fast.
        """
        projection = fields or self.LISTING_FIELDS
        
        query = {"productId": product_id}
        if status:
            query["status"] = status
        
        # Sort mapping
        sort_field = {
            "price": "pricingTiers.0.pricePerUnit",
            "created": "createdAt",
            "rating": "sellerRating"
        }.get(sort_by, "pricingTiers.0.pricePerUnit")
        
        cursor = self.db.sellerListings.find(query, projection)
        cursor = cursor.sort(sort_field, sort_order).limit(limit)
        
        return await cursor.to_list(limit)
    
    # ==================== ENTERPRISE AGGREGATION ====================
    
    async def get_enterprise_product_data(
        self,
        product_id: ObjectId,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Single aggregation for enterprise product page.
        
        NO N+1 queries - everything in one pipeline.
        
        Returns:
            - Product details
            - Seller listings with seller info
            - Statistics (seller count, min price, etc.)
        """
        skip = (page - 1) * limit
        
        pipeline = [
            # Stage 1: Match product
            {"$match": {"_id": product_id}},
            
            # Stage 2: Lookup active listings
            {"$lookup": {
                "from": "sellerListings",
                "let": {"productId": "$_id"},
                "pipeline": [
                    {"$match": {
                        "$expr": {"$eq": ["$productId", "$$productId"]},
                        "status": "active"
                    }},
                    {"$sort": {"pricingTiers.0.pricePerUnit": 1}},
                    {"$skip": skip},
                    {"$limit": limit},
                    # Lookup seller data
                    {"$lookup": {
                        "from": "users",
                        "localField": "sellerId",
                        "foreignField": "_id",
                        "as": "seller"
                    }},
                    {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
                    {"$project": {
                        "_id": 1,
                        "sellerId": 1,
                        "pricingTiers": 1,
                        "moq": 1,
                        "leadTime": 1,
                        "stock": 1,
                        "images": {"$slice": ["$images", 3]},
                        "searchableAttributes": 1,
                        "specifications": 1,
                        "companyName": {"$ifNull": ["$seller.profile.businessName", "Verified Seller"]},
                        "city": "$seller.profile.city",
                        "state": "$seller.profile.state",
                        "badgeType": {"$ifNull": ["$seller.badgeType", "none"]},
                        "sellerVerified": {"$ifNull": ["$seller.isVerified", False]}
                    }}
                ],
                "as": "listings"
            }},
            
            # Stage 3: Count total listings (for pagination)
            {"$lookup": {
                "from": "sellerListings",
                "let": {"productId": "$_id"},
                "pipeline": [
                    {"$match": {
                        "$expr": {"$eq": ["$productId", "$$productId"]},
                        "status": "active"
                    }},
                    {"$count": "total"}
                ],
                "as": "totalCount"
            }},
            
            # Stage 4: Get category info
            {"$lookup": {
                "from": "categories",
                "localField": "categoryId",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
            
            # Stage 5: Project final shape
            {"$project": {
                "product": {
                    "_id": "$_id",
                    "name": "$name",
                    "slug": "$slug",
                    "description": "$description",
                    "coverImageUrl": "$coverImageUrl",
                    "images": "$images",
                    "unit": "$unit",
                    "family": "$family",
                    "variant": "$variant",
                    "specifications": "$specifications",
                    "normalizedSpecs": "$normalizedSpecs",
                    "seoTitle": "$seoTitle",
                    "seoDescription": "$seoDescription"
                },
                "category": {
                    "_id": "$category._id",
                    "name": "$category.name",
                    "slug": "$category.slug"
                },
                "sellers": "$listings",
                "totalSellers": {"$ifNull": [{"$arrayElemAt": ["$totalCount.total", 0]}, 0]},
                "page": {"$literal": page},
                "limit": {"$literal": limit}
            }}
        ]
        
        results = await self.db.products.aggregate(pipeline).to_list(1)
        
        if not results:
            return None
        
        result = results[0]
        
        # Calculate stats
        sellers = result.get("sellers", [])
        all_prices = []
        for seller in sellers:
            for tier in seller.get("pricingTiers", []):
                price = tier.get("pricePerUnit") or tier.get("price")
                if price:
                    all_prices.append(float(price))
        
        result["stats"] = {
            "sellerCount": result.get("totalSellers", 0),
            "minPrice": min(all_prices) if all_prices else None,
            "maxPrice": max(all_prices) if all_prices else None,
            "hasNextPage": (page * limit) < result.get("totalSellers", 0)
        }
        
        return result


# Factory function
def create_resolver(db):
    """Create resolver instance."""
    return EnterpriseResolver(db)
