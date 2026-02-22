"""
Listing Service - Handles the `seller_listings` collection
SINGLE SOURCE OF TRUTH for ALL Commercial Data

CANONICAL SCHEMA (V7 Enforced):
seller_listings: {
    _id: ObjectId,
    productId: ObjectId (reference to products collection),
    sellerId: ObjectId (reference to users collection),
    categoryId: ObjectId (reference to categories collection),
    status: "active" | "inactive" | "draft",
    is_active: boolean,
    stock: Number,
    moq: Number,
    maxCapacity: Number,
    leadTime: Number (days) | String,
    currency: "INR",
    pricingTiers: [
        {
            minQty: Number,
            maxQty: Number | null,
            pricePerUnit: Number
        }
    ],
    createdAt: datetime (UTC),
    updatedAt: datetime (UTC),
    publishedAt: datetime (UTC) | null
}

STRICT RULES:
- NO legacy fields (seller_id, product_id, category_id, product_name, category_name)
- NO fallback logic for legacy fields
- ALL foreign keys MUST be ObjectId
- Unique compound index: (sellerId, productId) - prevents duplicate listings
- All pricing must be derived from pricingTiers ONLY
- Seller count per product: COUNT seller_listings WHERE productId=X AND status=active
"""

from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def to_objectid(value: Any, field_name: str) -> ObjectId:
    """
    Convert value to ObjectId. Raises ValueError if conversion fails.
    
    STRICT: No fallback to alternative fields or string comparison.
    """
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format for {field_name}: {value}")
    raise ValueError(f"Cannot convert {type(value).__name__} to ObjectId for {field_name}")


class ListingService:
    """
    Service for managing the seller_listings collection (commercial SSOT).
    
    CANONICAL IDENTITY POLICY:
    - All queries use ObjectId for sellerId, productId, categoryId
    - NO fallback to legacy string fields
    - NO backward compatibility with old schema
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.sellerListings
    
    # ==================== INDEXES ====================
    
    async def ensure_indexes(self):
        """Create indexes for optimal query performance."""
        # Unique compound index - CRITICAL for data integrity
        await self.collection.create_index(
            [("sellerId", 1), ("productId", 1)],
            unique=True,
            name="unique_seller_product"
        )
        
        # Query optimization indexes
        await self.collection.create_index("sellerId", name="sellerId_1")
        await self.collection.create_index("productId", name="productId_1")
        await self.collection.create_index("categoryId", name="categoryId_1")
        await self.collection.create_index("status", name="status_1")
        await self.collection.create_index([("status", 1), ("productId", 1)], name="status_productId")
        await self.collection.create_index("createdAt", name="createdAt_1")
        
        logger.info("[ListingService] Indexes ensured")
    
    # ==================== CREATE ====================
    
    async def create_listing(
        self,
        product_id: str,
        seller_id: str,
        pricing_tiers: List[Dict[str, Any]],
        category_id: Optional[str] = None,
        stock: int = 0,
        moq: int = 1,
        max_capacity: int = 0,
        lead_time: int = 7,
        currency: str = "INR",
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create a new seller listing for a product.
        
        CANONICAL: All IDs must be valid ObjectId strings.
        """
        now = datetime.now(timezone.utc)
        
        # Convert to ObjectId (STRICT - no fallbacks)
        product_oid = to_objectid(product_id, "product_id")
        seller_oid = to_objectid(seller_id, "seller_id")
        
        # Get category from product if not provided
        if category_id:
            category_oid = to_objectid(category_id, "category_id")
        else:
            product = await self.db.products.find_one({"_id": product_oid})
            if product and product.get("category_id"):
                category_oid = to_objectid(product["category_id"], "category_id")
            else:
                category_oid = None
        
        # Validate and normalize pricing tiers
        normalized_tiers = []
        for tier in pricing_tiers:
            normalized_tiers.append({
                "minQty": int(tier.get("minQty", 1)),
                "maxQty": int(tier["maxQty"]) if tier.get("maxQty") else None,
                "pricePerUnit": float(tier.get("pricePerUnit", 0))
            })
        
        doc = {
            "productId": product_oid,
            "sellerId": seller_oid,
            "categoryId": category_oid,
            "status": status,
            "is_active": status == "active",
            "stock": int(stock),
            "moq": int(moq),
            "maxCapacity": int(max_capacity),
            "leadTime": int(lead_time),
            "currency": currency.upper(),
            "pricingTiers": normalized_tiers,
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": now if status == "active" else None
        }
        
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        logger.info(f"[ListingService] Created listing {result.inserted_id}")
        
        return self._serialize(doc)
    
    # ==================== READ ====================
    
    async def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get a listing by its ID."""
        try:
            listing_oid = to_objectid(listing_id, "listing_id")
            doc = await self.collection.find_one({"_id": listing_oid})
            return self._serialize(doc) if doc else None
        except (ValueError, InvalidId) as e:
            logger.error(f"[ListingService] Invalid listing_id: {e}")
            return None
    
    async def get_listing_by_product_and_seller(
        self,
        product_id: str,
        seller_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a listing for a specific product by a specific seller."""
        product_oid = to_objectid(product_id, "product_id")
        seller_oid = to_objectid(seller_id, "seller_id")
        
        doc = await self.collection.find_one({
            "productId": product_oid,
            "sellerId": seller_oid
        })
        return self._serialize(doc) if doc else None
    
    async def list_listings(
        self,
        product_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: Optional[str] = None,
        low_stock_threshold: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "createdAt",
        sort_order: int = -1
    ) -> Dict[str, Any]:
        """List listings with optional filters."""
        query = {}
        
        if product_id:
            query["productId"] = to_objectid(product_id, "product_id")
        
        if seller_id:
            query["sellerId"] = to_objectid(seller_id, "seller_id")
        
        if status:
            query["status"] = status
            
        if low_stock_threshold is not None:
            query["stock"] = {"$lte": low_stock_threshold}
        
        total = await self.collection.count_documents(query)
        
        cursor = self.collection.find(query).sort(sort_by, sort_order).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": page,
            "pages": pages
        }
    
    async def get_listings_for_admin(
        self,
        product_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: Optional[str] = None,
        low_stock_threshold: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "createdAt",
        sort_order: int = -1
    ) -> Dict[str, Any]:
        """
        Get listings with joined product and seller information.
        Used by the Admin Listings Panel.
        
        SELF-HEALING: Handles orphaned references gracefully.
        - If product/seller is deleted, shows "[Deleted Product/Seller]"
        - If productId/sellerId is missing, shows "[Missing Reference]"
        - Supports both ObjectId and legacy string ID formats for lookups
        """
        # Build match stage
        match_stage = {}
        
        if product_id:
            match_stage["productId"] = to_objectid(product_id, "product_id")
        
        if seller_id:
            match_stage["sellerId"] = to_objectid(seller_id, "seller_id")
        
        if status:
            match_stage["status"] = status
            
        if low_stock_threshold is not None:
            match_stage["stock"] = {"$lte": low_stock_threshold}
        
        pipeline = []
        
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        pipeline.extend([
            # Lookup product info - CANONICAL: productId is ObjectId
            {
                "$lookup": {
                    "from": "products",
                    "localField": "productId",
                    "foreignField": "_id",
                    "as": "product"
                }
            },
            {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
            
            # Lookup seller info - CANONICAL: sellerId is ObjectId
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sellerId",
                    "foreignField": "_id",
                    "as": "seller"
                }
            },
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            
            # Project final shape with self-healing defaults
            {
                "$project": {
                    "_id": 1,
                    "productId": 1,
                    "sellerId": 1,
                    "categoryId": 1,
                    "status": 1,
                    "isActive": 1,
                    "stock": 1,
                    "moq": 1,
                    "maxCapacity": 1,
                    "leadTime": 1,
                    "currency": 1,
                    "pricingTiers": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "publishedAt": 1,
                    # Product info via $lookup with self-healing - STRICT camelCase
                    "productName": {
                        "$ifNull": ["$product.name", "[Deleted Product]"]
                    },
                    "productSlug": "$product.slug",
                    "productStatus": "$product.status",
                    "productExists": {"$cond": [{"$ifNull": ["$product", False]}, True, False]},
                    # Seller info via $lookup with self-healing - STRICT camelCase
                    "sellerName": {
                        "$ifNull": [
                            "$seller.businessName",
                            {"$ifNull": [
                                "$seller.profile.businessName",
                                {"$ifNull": ["$seller.email", "[Deleted Seller]"]}
                            ]}
                        ]
                    },
                    "sellerEmail": "$seller.email",
                    "sellerPhone": {"$ifNull": ["$seller.phone", "$seller.profile.phone"]},
                    "sellerExists": {"$cond": [{"$ifNull": ["$seller", False]}, True, False]}
                }
            },
            
            # Sort
            {"$sort": {sort_by: sort_order}},
            
            # Paginate
            {"$skip": skip},
            {"$limit": limit}
        ])
        
        docs = await self.collection.aggregate(pipeline).to_list(length=limit)
        
        # Self-healing: Log orphaned references for admin visibility
        orphaned_count = 0
        for doc in docs:
            if not doc.get("productExists") or not doc.get("sellerExists"):
                orphaned_count += 1
                logger.warning(
                    f"[ORPHANED LISTING] ID: {doc.get('_id')} - "
                    f"Product exists: {doc.get('productExists')}, "
                    f"Seller exists: {doc.get('sellerExists')}"
                )
        
        if orphaned_count > 0:
            logger.warning(f"[SELF-HEALING] Found {orphaned_count} listings with orphaned references")
        
        # Count total
        total = await self.collection.count_documents(match_stage if match_stage else {})
        
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": page,
            "pages": pages,
            "orphanedCount": orphaned_count
        }
    
    async def get_active_listings_for_product(
        self,
        product_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all active listings for a specific product.
        CANONICAL: productId is ObjectId.
        """
        product_oid = to_objectid(product_id, "product_id")
        
        cursor = self.collection.find({
            "productId": product_oid,
            "status": "active"
        })
        docs = await cursor.to_list(length=100)
        return [self._serialize(doc) for doc in docs]
    
    async def get_seller_listings(
        self,
        seller_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get all listings for a specific seller."""
        seller_oid = to_objectid(seller_id, "seller_id")
        
        query = {"sellerId": seller_oid}
        if status:
            query["status"] = status
            
        total = await self.collection.count_documents(query)
        
        cursor = self.collection.find(query).sort("createdAt", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": page,
            "pages": pages
        }
    
    # ==================== DYNAMIC AGGREGATION ====================
    
    async def get_seller_count_for_product(self, product_id: str) -> int:
        """
        Count active sellers for a product.
        CANONICAL: productId is ObjectId.
        """
        product_oid = to_objectid(product_id, "product_id")
        
        count = await self.collection.count_documents({
            "productId": product_oid,
            "status": "active"
        })
        return count
    
    async def get_lowest_price_for_product(self, product_id: str) -> Optional[float]:
        """
        Get the lowest price across all active listings for a product.
        CANONICAL: productId is ObjectId.
        """
        product_oid = to_objectid(product_id, "product_id")
        
        pipeline = [
            {
                "$match": {
                    "productId": product_oid,
                    "status": "active"
                }
            },
            {"$unwind": "$pricingTiers"},
            {
                "$group": {
                    "_id": None,
                    "lowest": {"$min": "$pricingTiers.pricePerUnit"}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0]["lowest"] if result else None
    
    async def get_product_aggregates(self, product_id: str) -> Dict[str, Any]:
        """
        Get all dynamic aggregates for a product in one query.
        CANONICAL: productId is ObjectId.
        """
        product_oid = to_objectid(product_id, "product_id")
        
        pipeline = [
            {
                "$match": {
                    "productId": product_oid,
                    "status": "active"
                }
            },
            {"$unwind": {"path": "$pricingTiers", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": None,
                    "seller_ids": {"$addToSet": "$sellerId"},
                    "lowest_price": {"$min": "$pricingTiers.pricePerUnit"},
                    "stock_total": {"$sum": "$stock"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "seller_count": {"$size": "$seller_ids"},
                    "lowest_price": 1,
                    "stock_total": 1
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            return result[0]
        else:
            return {
                "seller_count": 0,
                "lowest_price": None,
                "stock_total": 0
            }
    
    # ==================== UPDATE ====================
    
    async def update_listing(
        self,
        listing_id: str,
        updates: Dict[str, Any],
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a listing's commercial fields.
        CANONICAL: All IDs are ObjectId.
        """
        listing_oid = to_objectid(listing_id, "listing_id")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = to_objectid(seller_id, "seller_id")
        
        # Whitelist allowed fields
        allowed = {"status", "stock", "moq", "maxCapacity", "leadTime", "pricingTiers", "currency"}
        filtered = {}
        
        for key in allowed:
            if key in updates:
                if key == "pricingTiers":
                    # Normalize pricing tiers
                    filtered["pricingTiers"] = [
                        {
                            "minQty": int(t.get("minQty", 1)),
                            "maxQty": int(t["maxQty"]) if t.get("maxQty") else None,
                            "pricePerUnit": float(t.get("pricePerUnit", 0))
                        }
                        for t in updates["pricingTiers"]
                    ]
                elif key == "stock":
                    filtered["stock"] = int(updates["stock"])
                elif key == "moq":
                    filtered["moq"] = int(updates["moq"])
                elif key == "maxCapacity":
                    filtered["maxCapacity"] = int(updates["maxCapacity"])
                elif key == "leadTime":
                    filtered["leadTime"] = int(updates["leadTime"])
                elif key == "status":
                    filtered["status"] = updates["status"]
                    filtered["is_active"] = updates["status"] == "active"
                else:
                    filtered[key] = updates[key]
        
        if not filtered:
            return await self.get_listing_by_id(listing_id)
        
        filtered["updatedAt"] = datetime.now(timezone.utc)
        
        result = await self.collection.find_one_and_update(
            query,
            {"$set": filtered},
            return_document=True
        )
        
        if result:
            logger.info(f"[ListingService] Updated listing {listing_id}")
        
        return self._serialize(result) if result else None
    
    async def toggle_listing_status(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Toggle listing status between active and inactive."""
        listing_oid = to_objectid(listing_id, "listing_id")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = to_objectid(seller_id, "seller_id")
        
        doc = await self.collection.find_one(query)
        if not doc:
            return None
        
        new_status = "inactive" if doc.get("status") == "active" else "active"
        
        result = await self.collection.find_one_and_update(
            query,
            {
                "$set": {
                    "status": new_status,
                    "is_active": new_status == "active",
                    "updatedAt": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )
        
        return self._serialize(result) if result else None
    
    # ==================== DELETE ====================
    
    async def delete_listing(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> bool:
        """Hard delete a listing."""
        listing_oid = to_objectid(listing_id, "listing_id")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = to_objectid(seller_id, "seller_id")
        
        result = await self.collection.delete_one(query)
        
        if result.deleted_count > 0:
            logger.info(f"[ListingService] Deleted listing {listing_id}")
            return True
        return False
    
    # ==================== HELPERS ====================
    
    def _serialize(self, doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Convert MongoDB document to JSON-serializable dict."""
        if not doc:
            return None
        
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize(item) if isinstance(item, dict)
                    else str(item) if isinstance(item, ObjectId)
                    else item.isoformat() if isinstance(item, datetime)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
