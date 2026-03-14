"""
Inventory Management Router
Extends sellerListings with inventory tracking
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
import logging

from models.business_tools import (
    InventoryUpdate, InventoryLogCreate, InventoryLogResponse,
    InventoryLogType, Permission
)

logger = logging.getLogger(__name__)


def init_inventory_router(db, verify_token_func, activity_log_service=None, composite_router=None):
    """Initialize the inventory router."""
    
    router = APIRouter(tags=["Inventory"])
    
    def serialize_doc(doc):
        """Convert MongoDB document to JSON-serializable dict."""
        if doc is None:
            return None
        if isinstance(doc, list):
            return [serialize_doc(d) for d in doc]
        if isinstance(doc, dict):
            result = {}
            for key, value in doc.items():
                if key == "_id":
                    result["id"] = str(value)
                elif isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, dict):
                    result[key] = serialize_doc(value)
                elif isinstance(value, list):
                    result[key] = serialize_doc(value)
                else:
                    result[key] = value
            return result
        return doc
    
    async def get_current_user(authorization: str):
        """Get current user from Firebase token."""
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        
        try:
            decoded_token = await verify_token_func(token)
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        if not decoded_token:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get user from database
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user = await db.users.find_one({"firebaseUid": firebase_uid})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check account status
        if user.get("accountStatus") == "deleted":
            raise HTTPException(status_code=403, detail="Account has been deactivated")
        
        # For employees, check if status is active
        if user.get("accountType") == "employee" and user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Employee account is inactive")
        
        return user
    
    async def get_seller_id(user: dict) -> str:
        """Get seller ID for current user."""
        account_type = user.get("accountType", "seller")
        
        if account_type == "employee":
            seller_id = user.get("sellerId")
            if not seller_id:
                raise HTTPException(status_code=403, detail="Employee not linked to seller")
            return str(seller_id)
        else:
            return str(user.get("_id"))
    
    async def check_permission(user: dict, permission: str) -> bool:
        """Check if user has a specific permission."""
        account_type = user.get("accountType", "seller")
        
        if account_type == "seller":
            return True
        
        role_id = user.get("roleId")
        if not role_id:
            return False
        
        try:
            role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
            if role and permission in role.get("permissions", []):
                return True
        except Exception:
            pass
        
        return False
    
    async def require_permission(user: dict, permission: str):
        """Require a specific permission or raise 403."""
        has_perm = await check_permission(user, permission)
        if not has_perm:
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied: {permission} required"
            )
    
    # ===========================================
    # INVENTORY ENDPOINTS
    # ===========================================
    
    @router.get("/inventory")
    async def list_inventory(
        authorization: str = Header(...),
        lowStockOnly: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List inventory for all listings."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)
        
        # Build aggregation pipeline
        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "productData"
            }},
            {"$unwind": {"path": "$productData", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "listingId": "$_id",
                "productId": 1,
                "productType": {"$ifNull": ["$productType", "single"]},
                "productName": "$productData.name",
                "categoryName": "$productData.categoryName",
                "sku": {"$ifNull": ["$sku", ""]},
                "stock": {"$ifNull": ["$stock", 0]},
                "lowStockAlert": {"$ifNull": ["$lowStockAlert", 10]},
                "warehouseLocation": {"$ifNull": ["$warehouseLocation", ""]},
                "minPrice": 1,
                "status": 1,
                "images": {"$slice": ["$images", 1]},
                "isLowStock": {"$lte": ["$stock", {"$ifNull": ["$lowStockAlert", 10]}]}
            }}
        ]
        
        # Add low stock filter
        if lowStockOnly:
            pipeline.append({"$match": {"isLowStock": True}})
        
        # Add search filter
        if search:
            pipeline.append({"$match": {
                "$or": [
                    {"productName": {"$regex": search, "$options": "i"}},
                    {"sku": {"$regex": search, "$options": "i"}}
                ]
            }})
        
        # Count total
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = await db.sellerListings.aggregate(count_pipeline).to_list(1)
        total = count_result[0]["total"] if count_result else 0
        
        # Add pagination and sort
        pipeline.extend([
            {"$sort": {"isLowStock": -1, "productName": 1}},
            {"$skip": skip},
            {"$limit": limit}
        ])
        
        items = await db.sellerListings.aggregate(pipeline).to_list(limit)
        
        return {
            "inventory": serialize_doc(items),
            "total": total,
            "lowStockCount": await db.sellerListings.count_documents({
                "sellerId": ObjectId(seller_id),
                "status": {"$in": ["active", "paused"]},
                "$expr": {"$lte": ["$stock", {"$ifNull": ["$lowStockAlert", 10]}]}
            }),
            "limit": limit,
            "skip": skip
        }
    
    @router.put("/inventory/{listing_id}")
    async def update_inventory(
        listing_id: str,
        data: InventoryUpdate,
        authorization: str = Header(...)
    ):
        """Update inventory for a listing."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # Check listing exists and belongs to seller
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Block stock quantity change for composite products
        if listing.get("productType") == "composite" and data.stockQuantity is not None:
            raise HTTPException(status_code=400, detail="Composite product stock is calculated automatically from components.")
        
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.sku is not None:
            update_fields["sku"] = data.sku
        if data.stockQuantity is not None:
            update_fields["stock"] = data.stockQuantity
        if data.lowStockAlert is not None:
            update_fields["lowStockAlert"] = data.lowStockAlert
        if data.warehouseLocation is not None:
            update_fields["warehouseLocation"] = data.warehouseLocation
        
        await db.sellerListings.update_one({"_id": listing_oid}, {"$set": update_fields})
        
        updated = await db.sellerListings.find_one({"_id": listing_oid})
        
        # Get product name
        product = await db.products.find_one({"_id": updated["productId"]})
        updated["productName"] = product["name"] if product else "Unknown"
        
        return {"message": "Inventory updated", "listing": serialize_doc(updated)}
    
    @router.post("/inventory/{listing_id}/adjust")
    async def adjust_inventory(
        listing_id: str,
        data: InventoryLogCreate,
        authorization: str = Header(...)
    ):
        """Adjust inventory with logging."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # Check listing exists
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Block manual stock adjustment for composite products
        if listing.get("productType") == "composite":
            raise HTTPException(status_code=400, detail="Composite product stock is calculated automatically from components. Adjust component stock instead.")
        
        previous_stock = listing.get("stock", 0)
        
        # Calculate new stock based on change type
        if data.changeType in [InventoryLogType.PURCHASE]:
            new_stock = previous_stock + abs(data.quantity)
        elif data.changeType in [InventoryLogType.SALE, InventoryLogType.DAMAGE]:
            new_stock = max(0, previous_stock - abs(data.quantity))
        else:  # adjustment - can be positive or negative
            new_stock = max(0, previous_stock + data.quantity)
        
        # Update stock
        now = datetime.now(timezone.utc)
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {"stock": new_stock, "updatedAt": now}}
        )
        
        # Get product name for log
        product = await db.products.find_one({"_id": listing["productId"]})
        
        # Create inventory log
        log_doc = {
            "sellerId": ObjectId(seller_id),
            "listingId": listing_oid,
            "productName": product["name"] if product else "Unknown",
            "changeType": data.changeType.value,
            "quantity": data.quantity,
            "previousStock": previous_stock,
            "newStock": new_stock,
            "note": data.note,
            "createdBy": str(user.get("_id")),
            "createdByName": user.get("name") or user.get("email"),
            "createdAt": now
        }
        
        await db.inventory_logs.insert_one(log_doc)
        
        logger.info(f"Inventory adjusted: {listing_id} {data.changeType.value} {data.quantity}")
        
        if activity_log_service:
            await activity_log_service.log(seller_id, str(user.get("_id")), "stock_adjusted", "inventory", str(listing_oid), f"{data.changeType.value}: {data.quantity}")

        # Recalculate composite products that use this component
        if composite_router and hasattr(composite_router, 'sync_all_composites_for_component'):
            await composite_router.sync_all_composites_for_component(str(listing_oid))

        return {
            "message": "Inventory adjusted",
            "previousStock": previous_stock,
            "newStock": new_stock
        }
    
    @router.get("/inventory/{listing_id}/logs")
    async def get_inventory_logs(
        listing_id: str,
        authorization: str = Header(...),
        limit: int = 50
    ):
        """Get inventory adjustment logs for a listing."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # Verify listing belongs to seller
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        logs = await db.inventory_logs.find({
            "listingId": listing_oid
        }).sort("createdAt", -1).limit(limit).to_list(limit)
        
        return {"logs": serialize_doc(logs)}
    
    @router.get("/inventory/low-stock-alerts")
    async def get_low_stock_alerts(authorization: str = Header(...)):
        """Get all low stock items."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)
        
        # Find items where stock <= lowStockAlert
        pipeline = [
            {"$match": {
                "sellerId": ObjectId(seller_id),
                "status": {"$in": ["active", "paused"]},
                "$expr": {"$lte": ["$stock", {"$ifNull": ["$lowStockAlert", 10]}]}
            }},
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "productData"
            }},
            {"$unwind": {"path": "$productData", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "listingId": "$_id",
                "productName": "$productData.name",
                "sku": 1,
                "stock": 1,
                "lowStockAlert": {"$ifNull": ["$lowStockAlert", 10]},
                "images": {"$slice": ["$images", 1]}
            }},
            {"$sort": {"stock": 1}}
        ]
        
        items = await db.sellerListings.aggregate(pipeline).to_list(100)
        
        return {"alerts": serialize_doc(items)}
    
    return router
