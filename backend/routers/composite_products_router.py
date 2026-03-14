"""
Composite Products Router
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
import logging

from models.business_tools import (
    CompositeProductCreate, CompositeProductUpdate, CompositeProductSell, Permission
)

logger = logging.getLogger(__name__)


def init_composite_products_router(db, verify_token_func, activity_log_service):
    router = APIRouter(tags=["Composite Products"])

    def serialize_doc(doc):
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
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        try:
            decoded_token = await verify_token_func(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if not decoded_token:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = await db.users.find_one({"firebaseUid": firebase_uid})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("accountType") == "employee" and user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Employee account is inactive")
        return user

    async def get_seller_id(user: dict) -> str:
        if user.get("accountType") == "employee":
            sid = user.get("sellerId")
            if not sid:
                raise HTTPException(status_code=403, detail="Employee not linked to seller")
            return str(sid)
        return str(user.get("_id"))

    async def require_permission(user: dict, permission: str):
        if user.get("accountType", "seller") == "seller":
            return
        role_id = user.get("roleId")
        if not role_id:
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission} required")
        role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
        if not role or permission not in role.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission} required")

    @router.get("/composite-products")
    async def list_composite_products(authorization: str = Header(...), search: Optional[str] = None):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        query = {"sellerId": ObjectId(seller_id)}
        if search:
            query["name"] = {"$regex": search, "$options": "i"}

        products = await db.composite_products.find(query).sort("createdAt", -1).to_list(100)

        # Enrich with items
        for prod in products:
            items = await db.composite_product_items.find({"compositeProductId": prod["_id"]}).to_list(50)
            # Get product names
            for item in items:
                listing = await db.sellerListings.find_one({"_id": item.get("productId")})
                if listing:
                    p = await db.products.find_one({"_id": listing.get("productId")})
                    item["productName"] = p["name"] if p else "Unknown"
                    item["currentStock"] = listing.get("stock", 0)
                else:
                    item["productName"] = "Unknown"
                    item["currentStock"] = 0
            prod["items"] = items

        return {"compositeProducts": serialize_doc(products)}

    @router.post("/composite-products")
    async def create_composite_product(data: CompositeProductCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        # Validate all product IDs exist as seller listings
        for item in data.items:
            try:
                listing = await db.sellerListings.find_one({
                    "_id": ObjectId(item.productId),
                    "sellerId": ObjectId(seller_id)
                })
                if not listing:
                    raise HTTPException(status_code=400, detail=f"Listing {item.productId} not found")
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.productId}")

        now = datetime.now(timezone.utc)
        cp_doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name,
            "description": data.description,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.composite_products.insert_one(cp_doc)
        cp_id = result.inserted_id

        # Create items
        for item in data.items:
            await db.composite_product_items.insert_one({
                "compositeProductId": cp_id,
                "productId": ObjectId(item.productId),
                "quantity": item.quantity
            })

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_created", "composite_products", str(cp_id), data.name)

        cp_doc["_id"] = cp_id
        return {"message": "Composite product created", "compositeProduct": serialize_doc(cp_doc)}

    @router.put("/composite-products/{cp_id}")
    async def update_composite_product(cp_id: str, data: CompositeProductUpdate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            cp_oid = ObjectId(cp_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid composite product ID")

        cp = await db.composite_products.find_one({"_id": cp_oid, "sellerId": ObjectId(seller_id)})
        if not cp:
            raise HTTPException(status_code=404, detail="Composite product not found")

        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.description is not None:
            update_fields["description"] = data.description

        await db.composite_products.update_one({"_id": cp_oid}, {"$set": update_fields})

        # Update items if provided
        if data.items is not None:
            await db.composite_product_items.delete_many({"compositeProductId": cp_oid})
            for item in data.items:
                listing = await db.sellerListings.find_one({"_id": ObjectId(item.productId), "sellerId": ObjectId(seller_id)})
                if not listing:
                    raise HTTPException(status_code=400, detail=f"Listing {item.productId} not found")
                await db.composite_product_items.insert_one({
                    "compositeProductId": cp_oid,
                    "productId": ObjectId(item.productId),
                    "quantity": item.quantity
                })

        updated = await db.composite_products.find_one({"_id": cp_oid})
        return {"message": "Composite product updated", "compositeProduct": serialize_doc(updated)}

    @router.delete("/composite-products/{cp_id}")
    async def delete_composite_product(cp_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            cp_oid = ObjectId(cp_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid composite product ID")

        cp = await db.composite_products.find_one({"_id": cp_oid, "sellerId": ObjectId(seller_id)})
        if not cp:
            raise HTTPException(status_code=404, detail="Composite product not found")

        await db.composite_product_items.delete_many({"compositeProductId": cp_oid})
        await db.composite_products.delete_one({"_id": cp_oid})

        return {"message": "Composite product deleted"}

    @router.post("/composite-products/{cp_id}/sell")
    async def sell_composite_product(cp_id: str, data: CompositeProductSell, authorization: str = Header(...)):
        """Sell a composite product - deducts stock from all component products."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            cp_oid = ObjectId(cp_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid composite product ID")

        cp = await db.composite_products.find_one({"_id": cp_oid, "sellerId": ObjectId(seller_id)})
        if not cp:
            raise HTTPException(status_code=404, detail="Composite product not found")

        items = await db.composite_product_items.find({"compositeProductId": cp_oid}).to_list(50)
        if not items:
            raise HTTPException(status_code=400, detail="Composite product has no components")

        # Validate stock availability for all components
        for item in items:
            listing = await db.sellerListings.find_one({"_id": item["productId"]})
            if not listing:
                raise HTTPException(status_code=400, detail="Component listing not found")
            required = item["quantity"] * data.quantity
            current_stock = listing.get("stock", 0)
            if current_stock < required:
                product = await db.products.find_one({"_id": listing.get("productId")})
                pname = product["name"] if product else "Unknown"
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {pname}: need {required}, have {current_stock}"
                )

        # Deduct stock for all components
        now = datetime.now(timezone.utc)
        deductions = []
        for item in items:
            listing = await db.sellerListings.find_one({"_id": item["productId"]})
            prev_stock = listing.get("stock", 0)
            deduct_qty = item["quantity"] * data.quantity
            new_stock = max(0, prev_stock - deduct_qty)

            await db.sellerListings.update_one(
                {"_id": item["productId"]},
                {"$set": {"stock": new_stock, "updatedAt": now}}
            )

            product = await db.products.find_one({"_id": listing.get("productId")})
            pname = product["name"] if product else "Unknown"

            # Create inventory log
            await db.inventory_logs.insert_one({
                "sellerId": ObjectId(seller_id),
                "listingId": item["productId"],
                "productName": pname,
                "changeType": "sale",
                "quantity": -deduct_qty,
                "previousStock": prev_stock,
                "newStock": new_stock,
                "note": f"Composite product sale: {cp['name']} x{data.quantity}",
                "createdBy": str(user["_id"]),
                "createdAt": now
            })
            deductions.append({"product": pname, "deducted": deduct_qty, "newStock": new_stock})

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_sold", "composite_products", str(cp_oid), f"{cp['name']} x{data.quantity}")

        return {"message": f"Sold {data.quantity} x {cp['name']}", "deductions": deductions}

    return router
