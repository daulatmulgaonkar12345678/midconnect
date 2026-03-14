"""
Composite Products Router
- Product identity (name/category) comes from admin catalog (products collection)
- Components come from seller's own inventory (sellerListings)
- Stock is calculated dynamically from seller's component inventory
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


class ComponentInput(BaseModel):
    listingId: str  # References seller's own sellerListings
    quantity: int = Field(..., ge=1)


class CompositeProductCreateInput(BaseModel):
    categoryId: str  # Admin category
    productId: str   # Admin product (name comes from here)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., ge=0)
    components: List[ComponentInput] = Field(..., min_length=1)


class CompositeProductUpdateInput(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    components: Optional[List[ComponentInput]] = None


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

    async def calc_available_stock(components):
        """Calculate available stock = min(listing_stock / component_qty)."""
        if not components:
            return 0
        avail = float('inf')
        for comp in components:
            lid = comp.get("listingId")
            if isinstance(lid, str):
                lid = ObjectId(lid)
            listing = await db.sellerListings.find_one({"_id": lid})
            stock = listing.get("stock", 0) if listing else 0
            qty = comp.get("quantity", 1)
            avail = min(avail, stock // qty if qty > 0 else 0)
        return int(avail) if avail != float('inf') else 0

    async def enrich_composite(cp, seller_id):
        """Add product name, category, and enriched components to a composite product."""
        # Get admin product name
        product = None
        product_id = cp.get("productId")
        if product_id:
            try:
                if isinstance(product_id, ObjectId):
                    product = await db.products.find_one({"_id": product_id})
                else:
                    product = await db.products.find_one({"_id": ObjectId(str(product_id))})
            except Exception:
                pass
        # If product not found via productId, fallback to composite's name field
        cp["productName"] = product.get("name") if product else (cp.get("name") or "Unknown")

        # Get category name
        cat_id = cp.get("categoryId") or (product.get("categoryId") if product else None)
        if cat_id:
            try:
                if isinstance(cat_id, str):
                    cat_id = ObjectId(cat_id)
                cat = await db.categories.find_one({"_id": cat_id})
            except Exception:
                cat = None
            cp["categoryName"] = cat.get("name", "") if cat else ""
        else:
            cp["categoryName"] = ""

        # Get components
        components = await db.composite_product_items.find({"compositeProductId": cp["_id"]}).to_list(50)
        enriched_components = []
        for comp in components:
            lid = comp.get("listingId")
            listing = None
            if lid:
                try:
                    if isinstance(lid, str):
                        lid = ObjectId(lid)
                    listing = await db.sellerListings.find_one({"_id": lid})
                except Exception:
                    pass
            comp_product_name = "Unknown"
            current_stock = 0
            if listing:
                current_stock = listing.get("stock", 0)
                prod = await db.products.find_one({"_id": listing.get("productId")})
                if prod:
                    comp_product_name = prod.get("name", "Unknown")

            enriched_components.append({
                "listingId": str(lid) if lid else None,
                "quantity": comp.get("quantity", 1),
                "productName": comp_product_name,
                "currentStock": current_stock
            })

        cp["components"] = enriched_components
        cp["availableStock"] = await calc_available_stock(components)
        return cp

    # ===== Seller's inventory for component selection =====

    @router.get("/composite-products/seller-inventory")
    async def get_seller_inventory(authorization: str = Header(...)):
        """Get seller's own listings for component selection (excludes composites)."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        listings = await db.sellerListings.find({
            "sellerId": ObjectId(seller_id),
            "status": {"$in": ["active", "paused"]},
            "productType": {"$ne": "composite"}
        }).to_list(500)

        items = []
        for listing in listings:
            prod = await db.products.find_one({"_id": listing.get("productId")})
            if not prod:
                continue
            items.append({
                "listingId": str(listing["_id"]),
                "productName": prod.get("name", "Unknown"),
                "stock": listing.get("stock", 0),
                "sku": listing.get("sku", "")
            })

        return {"inventory": items}

    # ===== CRUD =====

    @router.get("/composite-products")
    async def list_composite_products(authorization: str = Header(...), search: Optional[str] = None):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        query = {"sellerId": ObjectId(seller_id)}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
            ]

        products = await db.composite_products.find(query).sort("createdAt", -1).to_list(100)

        enriched = []
        for prod in products:
            enriched.append(await enrich_composite(prod, seller_id))

        return {"compositeProducts": serialize_doc(enriched)}

    @router.post("/composite-products")
    async def create_composite_product(data: CompositeProductCreateInput, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        # Validate admin category exists
        try:
            category = await db.categories.find_one({"_id": ObjectId(data.categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")

        # Validate admin product exists
        try:
            product = await db.products.find_one({"_id": ObjectId(data.productId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        if not product:
            raise HTTPException(status_code=400, detail="Product not found in catalog")

        # Validate all component listings belong to this seller
        for comp in data.components:
            try:
                listing = await db.sellerListings.find_one({
                    "_id": ObjectId(comp.listingId),
                    "sellerId": ObjectId(seller_id),
                    "productType": {"$ne": "composite"}
                })
                if not listing:
                    raise HTTPException(status_code=400, detail=f"Inventory item {comp.listingId} not found")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid listing ID: {comp.listingId}")

        now = datetime.now(timezone.utc)
        product_name = product.get("name", "Composite Product")

        # Create composite product record
        cp_doc = {
            "sellerId": ObjectId(seller_id),
            "categoryId": ObjectId(data.categoryId),
            "productId": ObjectId(data.productId),
            "name": product_name,
            "description": data.description,
            "price": data.price,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.composite_products.insert_one(cp_doc)
        cp_id = result.inserted_id

        # Create component items
        for comp in data.components:
            await db.composite_product_items.insert_one({
                "compositeProductId": cp_id,
                "listingId": ObjectId(comp.listingId),
                "quantity": comp.quantity
            })

        # Create sellerListing with productType="composite"
        # Use compositeProductId as productId to avoid unique index conflict
        # (seller may already have a regular listing for the admin product)
        composite_listing = {
            "sellerId": ObjectId(seller_id),
            "productId": cp_id,  # Use composite product ID to avoid unique constraint
            "categoryId": ObjectId(data.categoryId),
            "productType": "composite",
            "compositeProductId": cp_id,
            "description": data.description,
            "status": "active",
            "isActive": True,
            "stock": 0,
            "createdAt": now,
            "updatedAt": now
        }
        await db.sellerListings.insert_one(composite_listing)

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_created", "composite_products", str(cp_id), product_name)

        cp_doc["_id"] = cp_id
        enriched = await enrich_composite(cp_doc, seller_id)
        return {"message": "Composite product created", "compositeProduct": serialize_doc(enriched)}

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
        if data.description is not None:
            update_fields["description"] = data.description
        if data.price is not None:
            update_fields["price"] = data.price

        await db.composite_products.update_one({"_id": cp_oid}, {"$set": update_fields})

        # Also update the composite sellerListing
        listing_update = {"updatedAt": datetime.now(timezone.utc)}
        if data.description is not None:
            listing_update["description"] = data.description
        await db.sellerListings.update_one(
            {"compositeProductId": cp_oid, "productType": "composite"},
            {"$set": listing_update}
        )

        if data.components is not None:
            for comp in data.components:
                listing = await db.sellerListings.find_one({
                    "_id": ObjectId(comp.listingId),
                    "sellerId": ObjectId(seller_id),
                    "productType": {"$ne": "composite"}
                })
                if not listing:
                    raise HTTPException(status_code=400, detail=f"Inventory item {comp.listingId} not found")

            await db.composite_product_items.delete_many({"compositeProductId": cp_oid})
            for comp in data.components:
                await db.composite_product_items.insert_one({
                    "compositeProductId": cp_oid,
                    "listingId": ObjectId(comp.listingId),
                    "quantity": comp.quantity
                })

        updated = await db.composite_products.find_one({"_id": cp_oid})
        enriched = await enrich_composite(updated, seller_id)
        return {"message": "Composite product updated", "compositeProduct": serialize_doc(enriched)}

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
        """Sell a composite product - deducts stock from seller's component inventory."""
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

        components = await db.composite_product_items.find({"compositeProductId": cp_oid}).to_list(50)
        if not components:
            raise HTTPException(status_code=400, detail="Composite product has no components")

        # Validate stock availability
        for comp in components:
            listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
            if not listing:
                raise HTTPException(status_code=400, detail="Component inventory item not found")
            required = comp["quantity"] * data.quantity
            current_stock = listing.get("stock", 0)
            if current_stock < required:
                prod = await db.products.find_one({"_id": listing.get("productId")})
                pname = prod["name"] if prod else "Unknown"
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {pname}: need {required}, have {current_stock}"
                )

        # Deduct stock
        now = datetime.now(timezone.utc)
        deductions = []
        for comp in components:
            listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
            prev_stock = listing.get("stock", 0)
            deduct_qty = comp["quantity"] * data.quantity
            new_stock = max(0, prev_stock - deduct_qty)

            await db.sellerListings.update_one(
                {"_id": comp["listingId"]},
                {"$set": {"stock": new_stock, "updatedAt": now}}
            )

            prod = await db.products.find_one({"_id": listing.get("productId")})
            pname = prod["name"] if prod else "Unknown"

            await db.inventory_logs.insert_one({
                "sellerId": ObjectId(seller_id),
                "listingId": comp["listingId"],
                "productName": pname,
                "changeType": "sale",
                "quantity": -deduct_qty,
                "previousStock": prev_stock,
                "newStock": new_stock,
                "note": f"Composite sale: {cp['name']} x{data.quantity}",
                "createdBy": str(user["_id"]),
                "createdAt": now
            })
            deductions.append({"product": pname, "deducted": deduct_qty, "newStock": new_stock})

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_sold", "composite_products", str(cp_oid), f"{cp['name']} x{data.quantity}")

        return {"message": f"Sold {data.quantity} x {cp['name']}", "deductions": deductions}

    return router
