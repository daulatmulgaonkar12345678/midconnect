"""
Composite Products Router
- Product identity (name/category) comes from admin catalog (products collection)
- Components come from seller's own inventory (sellerListings)
- Stock is calculated dynamically from seller's component inventory
- selling_price set by seller, purchase_price auto-calculated from components
- When created, also creates sellerListing with productType="composite" for marketplace visibility
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

from models.business_tools import Permission
from utils.permissions import authenticate_user, resolve_seller_id, require_user_permission

logger = logging.getLogger(__name__)


class ComponentInput(BaseModel):
    listingId: str  # References seller's own sellerListings
    quantity: int = Field(..., ge=1)


class CompositeProductCreateInput(BaseModel):
    categoryId: str  # Admin category
    productId: str   # Admin product (name comes from here)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., ge=0)  # selling_price
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
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user: dict) -> str:
        return resolve_seller_id(user)

    async def require_permission(user: dict, permission: str):
        return await require_user_permission(db, user, permission)

    async def calc_available_stock(components):
        """Calculate available stock = min(listing_stock / component_qty) for each component."""
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

    async def calc_purchase_price(components):
        """Calculate purchase_price = sum(component purchase_price * quantity) dynamically."""
        total = 0.0
        for comp in components:
            lid = comp.get("listingId")
            if isinstance(lid, str):
                lid = ObjectId(lid)
            listing = await db.sellerListings.find_one({"_id": lid})
            if listing:
                price = listing.get("purchase_price") or 0
                total += price * comp.get("quantity", 1)
        return round(total, 2)

    async def sync_composite_stock(cp_id):
        """Recalculate composite product stock and update the sellerListings record."""
        if isinstance(cp_id, str):
            cp_id = ObjectId(cp_id)
        components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
        stock = await calc_available_stock(components)
        purchase_price = await calc_purchase_price(components)
        # Update composite_products record
        await db.composite_products.update_one(
            {"_id": cp_id},
            {"$set": {"calculatedStock": stock, "purchasePrice": purchase_price, "updatedAt": datetime.now(timezone.utc)}}
        )
        # Update the corresponding sellerListings record
        await db.sellerListings.update_one(
            {"compositeProductId": cp_id, "productType": "composite"},
            {"$set": {"stock": stock, "updatedAt": datetime.now(timezone.utc)}}
        )
        return stock, purchase_price

    async def sync_all_composites_for_component(listing_id):
        """When a component's stock changes, recalculate all composites that use it."""
        if isinstance(listing_id, str):
            listing_id = ObjectId(listing_id)
        # Find all composite_product_items that reference this listing
        items = await db.composite_product_items.find({"listingId": listing_id}).to_list(100)
        cp_ids = set(item["compositeProductId"] for item in items)
        for cp_id in cp_ids:
            await sync_composite_stock(cp_id)

    async def enrich_composite(cp, seller_id):
        """Add product name, category, purchase_price, and enriched components."""
        # Get admin product name
        product = None
        product_id = cp.get("productId")
        if product_id:
            try:
                pid = product_id if isinstance(product_id, ObjectId) else ObjectId(str(product_id))
                product = await db.products.find_one({"_id": pid})
            except Exception:
                pass
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
        purchase_price = 0.0
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
            comp_price = 0
            if listing:
                current_stock = listing.get("stock", 0)
                prod = await db.products.find_one({"_id": listing.get("productId")})
                if prod:
                    comp_product_name = prod.get("name", "Unknown")
                comp_price = listing.get("purchase_price") or 0

            qty = comp.get("quantity", 1)
            purchase_price += comp_price * qty
            enriched_components.append({
                "listingId": str(lid) if lid else None,
                "quantity": qty,
                "productName": comp_product_name,
                "currentStock": current_stock,
                "unitPrice": comp_price
            })

        cp["components"] = enriched_components
        cp["availableStock"] = await calc_available_stock(components)
        cp["purchasePrice"] = round(purchase_price, 2)
        cp["sellingPrice"] = cp.get("price", 0)

        # Check if sellerListing exists for marketplace visibility
        linked_listing = await db.sellerListings.find_one({
            "compositeProductId": cp["_id"],
            "productType": "composite"
        })
        cp["hasListing"] = linked_listing is not None
        cp["listingId"] = str(linked_listing["_id"]) if linked_listing else None
        cp["listingStatus"] = linked_listing.get("status") if linked_listing else None

        return cp

    # ===== Helper endpoints =====

    @router.get("/composite-products/seller-inventory")
    async def get_seller_inventory(authorization: str = Header(...)):
        """Get seller's own listings for component selection (excludes composites)."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        listings = await db.sellerListings.find({
            "sellerId": ObjectId(seller_id),
            "status": {"$in": ["active", "paused", "draft"]},
            "productType": {"$ne": "composite"}
        }).to_list(500)

        items = []
        for listing in listings:
            prod = await db.products.find_one({"_id": listing.get("productId")})
            if not prod:
                continue
            tiers = listing.get("pricingTiers", [])
            price = tiers[0].get("pricePerUnit", 0) if tiers else (listing.get("minPrice", 0) or 0)
            items.append({
                "listingId": str(listing["_id"]),
                "productName": prod.get("name", "Unknown"),
                "stock": listing.get("stock", 0),
                "sku": listing.get("sku", ""),
                "unitPrice": price
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

        # Validate all component listings belong to this seller and are not composite
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

        # Check if a composite listing already exists for this product + seller
        existing_composite = await db.sellerListings.find_one({
            "productId": ObjectId(data.productId),
            "sellerId": ObjectId(seller_id),
            "productType": "composite"
        })
        if existing_composite:
            raise HTTPException(status_code=409, detail="A composite product for this catalog item already exists. Edit the existing one instead.")

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

        # Calculate dynamic stock and purchase price
        components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
        calculated_stock = await calc_available_stock(components)

        # Create sellerListing with productType="composite" for marketplace visibility
        # Uses admin productId so marketplace search/category pages find it
        composite_listing = {
            "sellerId": ObjectId(seller_id),
            "productId": ObjectId(data.productId),  # Admin product ID for marketplace
            "categoryId": ObjectId(data.categoryId),
            "productType": "composite",
            "compositeProductId": cp_id,
            "description": data.description,
            "status": "active",
            "isActive": True,
            "stock": calculated_stock,
            "pricingTiers": [{"minQty": 1, "maxQty": None, "pricePerUnit": data.price}],
            "images": product.get("images", []),
            "createdAt": now,
            "updatedAt": now,
            "lastStockUpdate": now,
            "publishedAt": now
        }

        try:
            await db.sellerListings.insert_one(composite_listing)
        except Exception as e:
            # If insert fails (e.g., index conflict), clean up
            await db.composite_product_items.delete_many({"compositeProductId": cp_id})
            await db.composite_products.delete_one({"_id": cp_id})
            logger.error(f"Failed to create composite listing: {e}")
            raise HTTPException(status_code=409, detail="Could not create marketplace listing. A listing for this product may already exist.")

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
        listing_update = {"updatedAt": datetime.now(timezone.utc)}

        if data.description is not None:
            update_fields["description"] = data.description
            listing_update["description"] = data.description
        if data.price is not None:
            update_fields["price"] = data.price
            listing_update["pricingTiers"] = [{"minQty": 1, "maxQty": None, "pricePerUnit": data.price}]

        await db.composite_products.update_one({"_id": cp_oid}, {"$set": update_fields})

        # Update the composite sellerListing
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

        # Recalculate stock
        await sync_composite_stock(cp_oid)

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

    @router.post("/composite-products/{cp_id}/create-listing")
    async def create_composite_listing(cp_id: str, authorization: str = Header(...)):
        """Fallback: manually create a sellerListing for a composite product that is missing one."""
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

        # Check if listing already exists
        existing = await db.sellerListings.find_one({
            "compositeProductId": cp_oid,
            "productType": "composite"
        })
        if existing:
            return {"message": "Listing already exists", "listingId": str(existing["_id"])}

        # Get admin product for images
        product = await db.products.find_one({"_id": cp.get("productId")})

        # Calculate current stock
        components = await db.composite_product_items.find({"compositeProductId": cp_oid}).to_list(50)
        calculated_stock = await calc_available_stock(components)

        now = datetime.now(timezone.utc)
        composite_listing = {
            "sellerId": ObjectId(seller_id),
            "productId": cp.get("productId"),
            "categoryId": cp.get("categoryId"),
            "productType": "composite",
            "compositeProductId": cp_oid,
            "description": cp.get("description", ""),
            "status": "active",
            "isActive": True,
            "stock": calculated_stock,
            "pricingTiers": [{"minQty": 1, "maxQty": None, "pricePerUnit": cp.get("price", 0)}],
            "images": product.get("images", []) if product else [],
            "createdAt": now,
            "updatedAt": now,
            "lastStockUpdate": now,
            "publishedAt": now
        }

        try:
            result = await db.sellerListings.insert_one(composite_listing)
            return {"message": "Marketplace listing created", "listingId": str(result.inserted_id)}
        except Exception as e:
            logger.error(f"Failed to create fallback listing: {e}")
            raise HTTPException(status_code=409, detail="Could not create listing. A listing for this product may already exist.")

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

        # Deduct stock from components
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

        # Recalculate composite stock after deduction
        await sync_composite_stock(cp_oid)

        await activity_log_service.log(seller_id, str(user["_id"]), "composite_product_sold", "composite_products", str(cp_oid), f"{cp['name']} x{data.quantity}")

        return {"message": f"Sold {data.quantity} x {cp['name']}", "deductions": deductions}

    # ===== Utility: recalculate stock for all composites that use a given component =====
    # This is exposed so other routers (inventory, invoice) can call it

    router.sync_all_composites_for_component = sync_all_composites_for_component
    router.sync_composite_stock = sync_composite_stock

    return router
