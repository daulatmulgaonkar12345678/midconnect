"""
Seller Listing Repository

This is the SINGLE POINT OF ENTRY for ALL seller_listings database operations.
ALL routes MUST use this repository - NO direct db.seller_listings access allowed.

STRICT RULES:
1. ALL writes go through this repository
2. ALL reads that need joined data go through this repository
3. NO fallback logic - fail loudly on errors
4. NO legacy field support
5. ALWAYS use ObjectId for ID fields

The repository enforces:
- Canonical schema (ObjectId foreign keys)
- Data validation before writes
- Referential integrity checks
- Audit logging of all mutations
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, WriteError
import logging

from utils.identity import (
    require_objectid,
    to_objectid_safe,
    assert_no_legacy_fields,
    detect_legacy_fields
)
from models.seller_listing import (
    SellerListingCreate,
    SellerListingUpdate,
    SellerListingResponse,
    validate_listing_for_publish
)

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class DuplicateListingError(RepositoryError):
    """Raised when attempting to create a duplicate listing."""
    def __init__(self, seller_id: str, product_id: str):
        self.seller_id = seller_id
        self.product_id = product_id
        super().__init__(f"Seller {seller_id} already has a listing for product {product_id}")


class ListingNotFoundError(RepositoryError):
    """Raised when a listing is not found."""
    def __init__(self, listing_id: str, seller_id: Optional[str] = None):
        self.listing_id = listing_id
        self.seller_id = seller_id
        msg = f"Listing {listing_id} not found"
        if seller_id:
            msg += f" for seller {seller_id}"
        super().__init__(msg)


class SchemaViolationError(RepositoryError):
    """Raised when data violates the canonical schema."""
    def __init__(self, message: str, legacy_fields: List[str] = None):
        self.legacy_fields = legacy_fields or []
        super().__init__(f"Schema violation: {message}")


class SellerListingRepository:
    """
    Repository for seller_listings collection.
    
    This is the ONLY interface for seller_listings database operations.
    All code MUST use this repository - no direct collection access.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection: AsyncIOMotorCollection = db.seller_listings
        self._schema_validated = False
    
    # ==================== INITIALIZATION ====================
    
    async def ensure_indexes(self):
        """Create required indexes for optimal performance."""
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
        await self.collection.create_index("is_active", name="is_active_1")
        await self.collection.create_index(
            [("status", 1), ("productId", 1)],
            name="status_productId"
        )
        await self.collection.create_index("createdAt", name="createdAt_1")
        
        logger.info("[SellerListingRepository] Indexes ensured")
    
    # ==================== CREATE ====================
    
    async def create(
        self,
        seller_id: str,
        product_id: str,
        category_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new seller listing.
        
        This is the ONLY way to create a seller listing. Direct inserts are forbidden.
        
        Args:
            seller_id: Reference to users collection (string, will be converted to ObjectId)
            product_id: Reference to products collection
            category_id: Reference to categories collection
            **kwargs: Additional fields (stock, moq, pricing_tiers, etc.)
            
        Returns:
            Created listing document (serialized)
            
        Raises:
            DuplicateListingError: If seller already has a listing for this product
            SchemaViolationError: If data violates canonical schema
        """
        # Convert IDs to ObjectId - STRICT validation
        seller_oid = require_objectid(seller_id, "sellerId")
        product_oid = require_objectid(product_id, "productId")
        category_oid = require_objectid(category_id, "categoryId")
        
        # Verify referenced documents exist
        seller = await self.db.users.find_one({"_id": seller_oid})
        if not seller:
            raise RepositoryError(f"Seller {seller_id} not found in users collection")
        
        product = await self.db.products.find_one({"_id": product_oid})
        if not product:
            raise RepositoryError(f"Product {product_id} not found in products collection")
        
        category = await self.db.categories.find_one({"_id": category_oid})
        if not category:
            raise RepositoryError(f"Category {category_id} not found in categories collection")
        
        now = datetime.now(timezone.utc)
        status = kwargs.get("status", "draft")
        
        # Normalize pricing tiers
        pricing_tiers = []
        for tier in kwargs.get("pricing_tiers", kwargs.get("pricingTiers", [])):
            pricing_tiers.append({
                "minQty": int(tier.get("minQty", tier.get("min_qty", 1))),
                "maxQty": int(tier["maxQty"]) if tier.get("maxQty") or tier.get("max_qty") else None,
                "pricePerUnit": float(tier.get("pricePerUnit", tier.get("price_per_unit", 0)))
            })
        
        # Build document with CANONICAL schema
        doc = {
            "_id": ObjectId(),
            "sellerId": seller_oid,
            "productId": product_oid,
            "categoryId": category_oid,
            "status": status,
            "is_active": status == "active",
            "stock": int(kwargs.get("stock", 0)),
            "moq": int(kwargs.get("moq", 1)),
            "maxCapacity": int(kwargs.get("max_capacity", kwargs.get("maxCapacity", 0))) or None,
            "leadTime": kwargs.get("lead_time", kwargs.get("leadTime")),
            "currency": kwargs.get("currency", "INR"),
            "pricingTiers": pricing_tiers,
            "sellerRole": kwargs.get("seller_role", kwargs.get("sellerRole")),
            "description": kwargs.get("description"),
            "images": (kwargs.get("images") or [])[:10],
            "specifications": kwargs.get("specifications"),
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": now if status == "active" else None,
        }
        
        # CRITICAL: Verify no legacy fields
        assert_no_legacy_fields(doc, "create listing")
        
        try:
            await self.collection.insert_one(doc)
            logger.info(f"[Repository] Created listing {doc['_id']} for seller={seller_id}, product={product_id}")
            return self._serialize(doc)
            
        except DuplicateKeyError:
            raise DuplicateListingError(seller_id, product_id)
        except WriteError as e:
            # This catches schema validator rejections
            logger.error(f"[Repository] Write rejected by validator: {e}")
            raise SchemaViolationError(f"Database rejected write: {e}")
    
    async def create_from_model(self, model: SellerListingCreate) -> Dict[str, Any]:
        """
        Create a listing from a Pydantic model.
        
        This is the preferred way to create listings from API requests.
        """
        return await self.create(
            seller_id=model.seller_id,
            product_id=model.product_id,
            category_id=model.category_id,
            status=model.status,
            stock=model.stock,
            moq=model.moq,
            max_capacity=model.max_capacity,
            lead_time=model.lead_time,
            currency=model.currency,
            pricing_tiers=[t.to_db_dict() for t in model.pricing_tiers],
            seller_role=model.seller_role,
            description=model.description,
            images=model.images,
            specifications=model.specifications,
        )
    
    # ==================== READ ====================
    
    async def get_by_id(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a listing by ID.
        
        Args:
            listing_id: The listing's ObjectId
            seller_id: Optional - restrict to this seller's listings
            
        Returns:
            Listing document or None
        """
        listing_oid = require_objectid(listing_id, "listingId")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = require_objectid(seller_id, "sellerId")
        
        doc = await self.collection.find_one(query)
        return self._serialize(doc) if doc else None
    
    async def get_by_seller_and_product(
        self,
        seller_id: str,
        product_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a listing for a specific seller and product combination.
        
        This uses the unique compound index for O(1) lookup.
        """
        seller_oid = require_objectid(seller_id, "sellerId")
        product_oid = require_objectid(product_id, "productId")
        
        doc = await self.collection.find_one({
            "sellerId": seller_oid,
            "productId": product_oid
        })
        return self._serialize(doc) if doc else None
    
    async def list_by_seller(
        self,
        seller_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        List all listings for a seller.
        
        Returns paginated results with total count.
        """
        seller_oid = require_objectid(seller_id, "sellerId")
        
        query = {"sellerId": seller_oid}
        if status:
            query["status"] = status
        
        total = await self.collection.count_documents(query)
        docs = await self.collection.find(query)\
            .sort("updatedAt", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "pages": max(1, (total + limit - 1) // limit) if limit > 0 else 1
        }
    
    async def list_by_product(
        self,
        product_id: str,
        status: str = "active",
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        List all listings for a product.
        
        Used for product detail pages showing all sellers.
        """
        product_oid = require_objectid(product_id, "productId")
        
        query = {"productId": product_oid}
        if status:
            query["status"] = status
        
        total = await self.collection.count_documents(query)
        docs = await self.collection.find(query)\
            .sort("createdAt", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "pages": max(1, (total + limit - 1) // limit) if limit > 0 else 1
        }
    
    async def list_for_admin(
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
        List listings with joined product and seller information.
        
        Used by the Admin Listings Panel.
        CANONICAL: Uses $lookup for joins - NO fallback fields.
        """
        match_stage = {}
        
        if product_id:
            match_stage["productId"] = require_objectid(product_id, "productId")
        if seller_id:
            match_stage["sellerId"] = require_objectid(seller_id, "sellerId")
        if status:
            match_stage["status"] = status
        if low_stock_threshold is not None:
            match_stage["stock"] = {"$lte": low_stock_threshold}
        
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        pipeline.extend([
            # Join product info
            {
                "$lookup": {
                    "from": "products",
                    "localField": "productId",
                    "foreignField": "_id",
                    "as": "product"
                }
            },
            {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
            
            # Join seller info
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sellerId",
                    "foreignField": "_id",
                    "as": "seller"
                }
            },
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            
            # Project final shape
            {
                "$project": {
                    "_id": 1,
                    "productId": 1,
                    "sellerId": 1,
                    "categoryId": 1,
                    "status": 1,
                    "is_active": 1,
                    "stock": 1,
                    "moq": 1,
                    "maxCapacity": 1,
                    "leadTime": 1,
                    "currency": 1,
                    "pricingTiers": 1,
                    "sellerRole": 1,
                    "description": 1,
                    "images": 1,
                    "specifications": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "publishedAt": 1,
                    # Joined fields - NO fallback
                    "product_name": "$product.name",
                    "product_slug": "$product.slug",
                    "product_status": "$product.status",
                    "seller_name": "$seller.business_name",
                    "seller_email": "$seller.email",
                    "seller_phone": "$seller.phone"
                }
            },
            
            {"$sort": {sort_by: sort_order}},
            {"$skip": skip},
            {"$limit": limit}
        ])
        
        docs = await self.collection.aggregate(pipeline).to_list(limit)
        total = await self.collection.count_documents(match_stage if match_stage else {})
        
        return {
            "listings": [self._serialize(doc) for doc in docs],
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "pages": max(1, (total + limit - 1) // limit) if limit > 0 else 1
        }
    
    # ==================== UPDATE ====================
    
    async def update(
        self,
        listing_id: str,
        updates: Dict[str, Any],
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a listing's commercial fields.
        
        Args:
            listing_id: The listing's ObjectId
            updates: Fields to update
            seller_id: Optional - restrict to this seller's listings
            
        Returns:
            Updated listing document or None if not found
        """
        listing_oid = require_objectid(listing_id, "listingId")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = require_objectid(seller_id, "sellerId")
        
        # Whitelist allowed fields
        allowed = {
            "status", "stock", "moq", "maxCapacity", "leadTime",
            "pricingTiers", "currency", "sellerRole", "description",
            "images", "specifications"
        }
        
        filtered = {}
        for key in allowed:
            if key in updates:
                value = updates[key]
                
                if key == "pricingTiers" and value is not None:
                    filtered["pricingTiers"] = [
                        {
                            "minQty": int(t.get("minQty", t.get("min_qty", 1))),
                            "maxQty": int(t["maxQty"]) if t.get("maxQty") or t.get("max_qty") else None,
                            "pricePerUnit": float(t.get("pricePerUnit", t.get("price_per_unit", 0)))
                        }
                        for t in value
                    ]
                elif key in ["stock", "moq", "maxCapacity", "leadTime"] and value is not None:
                    filtered[key] = int(value) if value is not None else None
                elif key == "status":
                    filtered["status"] = value
                    filtered["is_active"] = value == "active"
                    if value == "active":
                        filtered["publishedAt"] = datetime.now(timezone.utc)
                elif key == "images" and value is not None:
                    filtered["images"] = value[:10]  # Enforce max
                else:
                    filtered[key] = value
        
        if not filtered:
            return await self.get_by_id(listing_id, seller_id)
        
        filtered["updatedAt"] = datetime.now(timezone.utc)
        
        result = await self.collection.find_one_and_update(
            query,
            {"$set": filtered},
            return_document=True
        )
        
        if result:
            logger.info(f"[Repository] Updated listing {listing_id}")
        
        return self._serialize(result) if result else None
    
    async def update_from_model(
        self,
        listing_id: str,
        model: SellerListingUpdate,
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a listing from a Pydantic model.
        """
        updates = model.to_db_dict()
        return await self.update(listing_id, updates, seller_id)
    
    async def toggle_status(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Toggle listing status between active and inactive."""
        listing_oid = require_objectid(listing_id, "listingId")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = require_objectid(seller_id, "sellerId")
        
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
        
        if result:
            logger.info(f"[Repository] Toggled listing {listing_id} status to {new_status}")
        
        return self._serialize(result) if result else None
    
    async def publish(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Publish a draft listing.
        
        Returns:
            Tuple of (updated_doc, validation_errors)
        """
        doc = await self.get_by_id(listing_id, seller_id)
        if not doc:
            raise ListingNotFoundError(listing_id, seller_id)
        
        if doc.get("status") == "active":
            return doc, []
        
        # Validate for publishing
        errors = validate_listing_for_publish(doc)
        if errors:
            return None, errors
        
        result = await self.update(listing_id, {"status": "active"}, seller_id)
        return result, []
    
    # ==================== DELETE ====================
    
    async def delete(
        self,
        listing_id: str,
        seller_id: Optional[str] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete or archive a listing.
        
        Args:
            listing_id: The listing's ObjectId
            seller_id: Optional - restrict to this seller's listings
            hard_delete: If True, permanently remove; if False, set status to archived
            
        Returns:
            True if operation succeeded
        """
        listing_oid = require_objectid(listing_id, "listingId")
        
        query = {"_id": listing_oid}
        if seller_id:
            query["sellerId"] = require_objectid(seller_id, "sellerId")
        
        if hard_delete:
            result = await self.collection.delete_one(query)
            if result.deleted_count > 0:
                logger.info(f"[Repository] Hard deleted listing {listing_id}")
                return True
        else:
            result = await self.collection.update_one(
                query,
                {
                    "$set": {
                        "status": "archived",
                        "is_active": False,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            if result.modified_count > 0:
                logger.info(f"[Repository] Archived listing {listing_id}")
                return True
        
        return False
    
    # ==================== AGGREGATIONS ====================
    
    async def count_active_sellers_for_product(self, product_id: str) -> int:
        """Count active sellers for a product."""
        product_oid = require_objectid(product_id, "productId")
        
        return await self.collection.count_documents({
            "productId": product_oid,
            "status": "active"
        })
    
    async def get_lowest_price_for_product(self, product_id: str) -> Optional[float]:
        """Get lowest price across all active listings for a product."""
        product_oid = require_objectid(product_id, "productId")
        
        pipeline = [
            {"$match": {"productId": product_oid, "status": "active"}},
            {"$unwind": "$pricingTiers"},
            {"$group": {"_id": None, "lowest": {"$min": "$pricingTiers.pricePerUnit"}}}
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(1)
        return result[0]["lowest"] if result else None
    
    async def get_product_aggregates(self, product_id: str) -> Dict[str, Any]:
        """Get all dynamic aggregates for a product."""
        product_oid = require_objectid(product_id, "productId")
        
        pipeline = [
            {"$match": {"productId": product_oid, "status": "active"}},
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
        
        result = await self.collection.aggregate(pipeline).to_list(1)
        
        return result[0] if result else {
            "seller_count": 0,
            "lowest_price": None,
            "stock_total": 0
        }
    
    async def get_seller_stats(self, seller_id: str) -> Dict[str, Any]:
        """Get listing statistics for a seller."""
        seller_oid = require_objectid(seller_id, "sellerId")
        
        pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(10)
        
        stats = {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "draft": 0,
            "paused": 0,
            "archived": 0
        }
        
        for item in results:
            status = item["_id"]
            count = item["count"]
            if status in stats:
                stats[status] = count
            stats["total"] += count
        
        return stats
    
    # ==================== BULK OPERATIONS ====================
    
    async def bulk_update_status(
        self,
        seller_id: str,
        new_status: str
    ) -> int:
        """
        Update status for all of a seller's listings.
        
        Returns count of modified documents.
        """
        seller_oid = require_objectid(seller_id, "sellerId")
        
        result = await self.collection.update_many(
            {"sellerId": seller_oid},
            {
                "$set": {
                    "status": new_status,
                    "is_active": new_status == "active",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"[Repository] Bulk updated {result.modified_count} listings for seller {seller_id}")
        return result.modified_count
    
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
