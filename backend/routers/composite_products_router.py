"""
Composite Products Router
- Composite products are bundles of admin-created products
- Seller selects Category → Product from admin catalog (same as listing creation)
- Components reference products collection (admin catalog), linked to seller's sellerListings
- Stock is calculated dynamically from seller's inventory
- Price is set manually by seller
- When created, also creates sellerListing with productType="composite"
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

from models.business_tools import Permission

logger = logging.getLogger(__name__)


class CompositeItemInput(BaseModel):
    productId: str  # References admin products collection
    quantity: int = Field(..., ge=1)


class CompositeProductCreateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., ge=0)
    items: List[CompositeItemInput] = Field(..., min_length=1)


class CompositeProductUpdateInput(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    items: Optional[List[CompositeItemInput]] = None


class CompositeProductSellInput(BaseModel):
    quantity: int = Field(1, ge=1)
    note: Optional[str] = Field(None, max_length=500)


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

    async def get_seller_listing(seller_id: str, product_id):
        """Find seller's listing for a given admin product."""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        return await db.sellerListings.find_one({
            "sellerId": ObjectId(seller_id),
            "productId": product_id,
            "productType": {"$ne": "composite"},
            "status": {"$in": ["active", "paused"]}
        })

    async def calc_available_stock(seller_id: str, items):
        """Calculate available stock = min(seller_listing_stock / component_qty)."""
        if not items:
            return 0
        avail = float('inf')
        for item in items:
            product_id = item.get("productId")
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)
            listing = await get_seller_listing(seller_id, product_id)
            stock = listing.get("stock", 0) if listing else 0
            qty_needed = item.get("quantity", 1)
            avail = min(avail, stock // qty_needed if qty_needed > 0 else 0)
        return int(avail) if avail != float('inf') else 0

    async def enrich_items(seller_id: str, items):
        """Add product name, category, and current stock to each item."""
        enriched = []
        for item in items:
            pid = item.get("productId")
            if isinstance(pid, str):
                pid = ObjectId(pid)

            product = await db.products.find_one({"_id": pid})
            product_name = product.get("name", "Unknown") if product else "Unknown"
            category_name = ""
            if product and product.get("categoryId"):
                cat = await db.categories.find_one({"_id": product["categoryId"]})
                category_name = cat.get("name", "") if cat else ""

            listing = await get_seller_listing(seller_id, pid)
            current_stock = listing.get("stock", 0) if listing else 0
            has_listing = listing is not None

            enriched.append({
                "productId": str(pid),
                "quantity": item.get("quantity", 1),
                "productName": product_name,
                "categoryName": category_name,
                "currentStock": current_stock,
                "hasListing": has_listing
            })
        return enriched

    # ===== CRUD =====

    @router.get("/composite-products")
    async def list_composite_products(authorization: str = Header(...), search: Optional[str] = None):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        query = {"sellerId": ObjectId(seller_id)}
        if search:
            query["name"] = {"$regex": search, "$options": "i"}

        products = await db.composite_products.find(query).sort("createdAt", -1).to_list(100)

        for prod in products:
            items = await db.composite_product_items.find({"compositeProductId": prod["_id"]}).to_list(50)
            prod["items"] = await enrich_items(seller_id, items)
            prod["availableStock"] = await calc_available_stock(seller_id, items)

        return {"compositeProducts": serialize_doc(products)}

    @router.post("/composite-products")
    async def create_composite_product(data: CompositeProductCreateInput, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        # Validate all product IDs exist in admin catalog
        for item in data.items:
            try:
                product = await db.products.find_one({"_id": ObjectId(item.productId)})
                if not product:
                    raise HTTPException(status_code=400, detail=f"Product {item.productId} not found in catalog")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.productId}")

        now = datetime.now(timezone.utc)

        # Create composite product record
        cp_doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name,
            "description": data.description,
            "price": data.price,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.composite_products.insert_one(cp_doc)
        cp_id = result.inserted_id

        # Create component items
        for item in data.items:
            await db.composite_product_items.insert_one({
                "compositeProductId": cp_id,
                "productId": ObjectId(item.productId),
                "quantity": item.quantity
            })

        # Create a sellerListing with productType="composite"
        composite_listing = {
            "sellerId": ObjectId(seller_id),
            "productId": cp_id,
            "productType": "composite",
            "compositeProductId": cp_id,
            "status": "active",
            "isActive": True,
            "stock": 0,
            "createdAt": now,
            "updatedAt": now
        }
        await db.sellerListings.insert_one(composite_listing)

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_created", "composite_products", str(cp_id), data.name)

        # Return enriched response
        items = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
        cp_doc["_id"] = cp_id
        cp_doc["items"] = await enrich_items(seller_id, items)
        cp_doc["availableStock"] = await calc_available_stock(seller_id, items)

        return {"message": "Composite product created", "compositeProduct": serialize_doc(cp_doc)}

    @router.put("/composite-products/{cp_id}")
    async def update_composite_product(cp_id: str, data: CompositeProductUpdateInput, authorization: str = Header(...)):
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
        if data.price is not None:
            update_fields["price"] = data.price

        await db.composite_products.update_one({"_id": cp_oid}, {"$set": update_fields})

        if data.items is not None:
            for item in data.items:
                product = await db.products.find_one({"_id": ObjectId(item.productId)})
                if not product:
                    raise HTTPException(status_code=400, detail=f"Product {item.productId} not found")

            await db.composite_product_items.delete_many({"compositeProductId": cp_oid})
            for item in data.items:
                await db.composite_product_items.insert_one({
                    "compositeProductId": cp_oid,
                    "productId": ObjectId(item.productId),
                    "quantity": item.quantity
                })

        updated = await db.composite_products.find_one({"_id": cp_oid})
        items = await db.composite_product_items.find({"compositeProductId": cp_oid}).to_list(50)
        updated["items"] = await enrich_items(seller_id, items)
        updated["availableStock"] = await calc_available_stock(seller_id, items)
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
        await db.sellerListings.delete_many({"compositeProductId": cp_oid, "productType": "composite"})
        await db.composite_products.delete_one({"_id": cp_oid})

        return {"message": "Composite product deleted"}

    @router.post("/composite-products/{cp_id}/sell")
    async def sell_composite_product(cp_id: str, data: CompositeProductSellInput, authorization: str = Header(...)):
        """Sell a composite product - deducts stock from seller's inventory for each component."""
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
            listing = await get_seller_listing(seller_id, item["productId"])
            if not listing:
                product = await db.products.find_one({"_id": item["productId"]})
                pname = product["name"] if product else "Unknown"
                raise HTTPException(status_code=400, detail=f"No inventory listing for {pname}")
            required = item["quantity"] * data.quantity
            current_stock = listing.get("stock", 0)
            if current_stock < required:
                product = await db.products.find_one({"_id": item["productId"]})
                pname = product["name"] if product else "Unknown"
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {pname}: need {required}, have {current_stock}"
                )

        # Deduct stock for all components
        now = datetime.now(timezone.utc)
        deductions = []
        for item in items:
            listing = await get_seller_listing(seller_id, item["productId"])
            prev_stock = listing.get("stock", 0)
            deduct_qty = item["quantity"] * data.quantity
            new_stock = max(0, prev_stock - deduct_qty)

            await db.sellerListings.update_one(
                {"_id": listing["_id"]},
                {"$set": {"stock": new_stock, "updatedAt": now}}
            )

            product = await db.products.find_one({"_id": item["productId"]})
            pname = product["name"] if product else "Unknown"

            await db.inventory_logs.insert_one({
                "sellerId": ObjectId(seller_id),
                "listingId": listing["_id"],
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
