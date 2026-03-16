"""
Pending Orders (Backorder) Router
Handles partial fulfillment, pending order tracking, and backorder management.
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel
import logging
import urllib.parse
import secrets
import os

from utils.permissions import authenticate_user, resolve_seller_id, require_user_permission, is_platform_admin

logger = logging.getLogger(__name__)


class FulfilRequest(BaseModel):
    quantity: Optional[int] = None
    deductStock: bool = True


class CancelRequest(BaseModel):
    reason: Optional[str] = None


def init_pending_orders_router(db, verify_token_func, serialize_doc):
    router = APIRouter()

    async def get_current_user(authorization: str):
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user):
        return resolve_seller_id(user)

    async def require_permission(user, permission):
        return await require_user_permission(db, user, permission)

    def normalize_doc(doc):
        """Ensure _id is mapped to id for frontend compatibility."""
        d = serialize_doc(doc)
        if d and "_id" in d:
            d["id"] = d.pop("_id")
        return d

    # ─── Helpers ───

    async def get_reserved_stock(seller_id: str, listing_id: str) -> int:
        """Calculate total reserved stock from pending orders for a listing."""
        pipeline = [
            {"$match": {
                "sellerId": ObjectId(seller_id),
                "listingId": ObjectId(listing_id),
                "status": {"$in": ["pending", "partially_fulfilled"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
        ]
        result = await db.pending_orders.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0

    # ─── LIST PENDING ORDERS ───

    @router.get("/pending-orders")
    async def list_pending_orders(
        authorization: str = Header(...),
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        user = await get_current_user(authorization)
        await require_permission(user, "create_invoice")
        seller_id = await get_seller_id(user)

        is_admin = is_platform_admin(user)
        query = {} if is_admin else {"sellerId": ObjectId(seller_id)}
        if status:
            query["status"] = status

        total = await db.pending_orders.count_documents(query)
        orders = await db.pending_orders.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)

        enriched = []
        for order in orders:
            doc = normalize_doc(order)
            # Enrich with buyer name
            buyer = await db.seller_buyers.find_one({"_id": order.get("buyerId")})
            doc["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
            doc["buyerPhone"] = buyer.get("phone", "") if buyer else ""
            doc["buyerId"] = str(order.get("buyerId")) if order.get("buyerId") else ""
            # Get product name from listing
            listing = await db.sellerListings.find_one({"_id": order.get("listingId")})
            if listing:
                prod = await db.products.find_one({"_id": listing.get("productId")})
                doc["productName"] = prod.get("name", doc.get("productName", "Unknown")) if prod else doc.get("productName", "Unknown")
                doc["currentStock"] = listing.get("stock", 0)
                reserved = await get_reserved_stock(str(order.get("sellerId")), str(order.get("listingId")))
                doc["availableStock"] = max(0, listing.get("stock", 0) - reserved)
                doc["listingId"] = str(order.get("listingId"))
            else:
                doc["currentStock"] = 0
                doc["availableStock"] = 0
                doc["listingId"] = ""
            # Include price/gst for invoice prefill
            doc["price"] = order.get("price", 0)
            doc["gstPercent"] = order.get("gstPercent", 0)
            # Invoice reference
            if order.get("invoiceId"):
                inv = await db.invoices.find_one({"_id": order.get("invoiceId")})
                doc["invoiceNumber"] = inv.get("invoiceNumber", "") if inv else ""
            enriched.append(doc)

        # Counts by status
        pending_count = await db.pending_orders.count_documents({**({} if is_admin else {"sellerId": ObjectId(seller_id)}), "status": "pending"})
        partial_count = await db.pending_orders.count_documents({**({} if is_admin else {"sellerId": ObjectId(seller_id)}), "status": "partially_fulfilled"})

        return {
            "pendingOrders": enriched,
            "total": total,
            "pendingCount": pending_count,
            "partialCount": partial_count,
            "limit": limit,
            "skip": skip
        }

    # ─── GET SINGLE PENDING ORDER ───

    @router.get("/pending-orders/{order_id}")
    async def get_pending_order(order_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, "create_invoice")
        seller_id = await get_seller_id(user)

        try:
            query = {"_id": ObjectId(order_id)}
            if seller_id:
                query["sellerId"] = ObjectId(seller_id)
            order = await db.pending_orders.find_one(query)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if not order:
            raise HTTPException(status_code=404, detail="Pending order not found")

        doc = normalize_doc(order)
        buyer = await db.seller_buyers.find_one({"_id": order.get("buyerId")})
        doc["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
        doc["buyerPhone"] = buyer.get("phone", "") if buyer else ""
        doc["buyerId"] = str(order.get("buyerId")) if order.get("buyerId") else ""

        listing = await db.sellerListings.find_one({"_id": order.get("listingId")})
        if listing:
            prod = await db.products.find_one({"_id": listing.get("productId")})
            doc["productName"] = prod.get("name", doc.get("productName", "Unknown")) if prod else doc.get("productName", "Unknown")
            doc["currentStock"] = listing.get("stock", 0)
            reserved = await get_reserved_stock(str(order.get("sellerId")), str(order.get("listingId")))
            doc["availableStock"] = max(0, listing.get("stock", 0) - reserved)
            doc["listingId"] = str(order.get("listingId"))

        if order.get("invoiceId"):
            inv = await db.invoices.find_one({"_id": order.get("invoiceId")})
            doc["invoiceNumber"] = inv.get("invoiceNumber", "") if inv else ""

        # Fulfillment history
        history = await db.pending_order_fulfillments.find({"pendingOrderId": order["_id"]}).sort("createdAt", -1).to_list(50)
        doc["fulfillmentHistory"] = [normalize_doc(h) for h in history]

        return {"pendingOrder": doc}

    # ─── FULFIL PENDING ORDER ───

    @router.post("/pending-orders/{order_id}/fulfil")
    async def fulfil_pending_order(order_id: str, data: FulfilRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, "create_invoice")
        seller_id = await get_seller_id(user)

        try:
            query = {"_id": ObjectId(order_id)}
            if seller_id:
                query["sellerId"] = ObjectId(seller_id)
            order = await db.pending_orders.find_one(query)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if not order:
            raise HTTPException(status_code=404, detail="Pending order not found")
        if order["status"] in ("completed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Cannot fulfil a {order['status']} order")

        pending_qty = order.get("pendingQty", 0)
        fulfil_qty = data.quantity if data.quantity else pending_qty

        if fulfil_qty <= 0:
            raise HTTPException(status_code=400, detail="Fulfilment quantity must be positive")
        if fulfil_qty > pending_qty:
            raise HTTPException(status_code=400, detail=f"Cannot fulfil more than pending ({pending_qty})")

        # Check stock
        listing = await db.sellerListings.find_one({"_id": order.get("listingId")})
        if not listing:
            raise HTTPException(status_code=404, detail="Product listing not found")

        current_stock = listing.get("stock", 0)
        if data.deductStock and current_stock < fulfil_qty:
            raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {current_stock}, Required: {fulfil_qty}")

        now = datetime.now(timezone.utc)
        order_seller_id = str(order.get("sellerId"))

        # Deduct stock
        if data.deductStock:
            new_stock = current_stock - fulfil_qty
            await db.sellerListings.update_one(
                {"_id": order.get("listingId")},
                {"$set": {"stock": new_stock, "updatedAt": now}}
            )
            prod = await db.products.find_one({"_id": listing.get("productId")})
            await db.inventory_logs.insert_one({
                "sellerId": ObjectId(order_seller_id),
                "listingId": order.get("listingId"),
                "productName": prod.get("name", "Unknown") if prod else "Unknown",
                "changeType": "pending_order_fulfillment",
                "quantity": -fulfil_qty,
                "previousStock": current_stock,
                "newStock": new_stock,
                "note": f"Fulfilled pending order (Ref: {order.get('referenceInvoiceNumber', '')})",
                "createdBy": str(user["_id"]),
                "createdAt": now
            })

        # Update pending order
        new_fulfilled = order.get("fulfilledQty", 0) + fulfil_qty
        new_pending = order.get("orderedQty", 0) - new_fulfilled
        new_status = "completed" if new_pending <= 0 else "partially_fulfilled"

        await db.pending_orders.update_one(
            {"_id": order["_id"]},
            {"$set": {
                "fulfilledQty": new_fulfilled,
                "pendingQty": max(0, new_pending),
                "status": new_status,
                "updatedAt": now
            }}
        )

        # Record fulfillment
        await db.pending_order_fulfillments.insert_one({
            "pendingOrderId": order["_id"],
            "sellerId": ObjectId(order_seller_id),
            "quantity": fulfil_qty,
            "createdBy": str(user["_id"]),
            "createdAt": now
        })

        # Create a new invoice for the fulfilled quantity
        buyer = await db.seller_buyers.find_one({"_id": order.get("buyerId")})
        if buyer:
            # Get next invoice number
            inv_count = await db.invoices.count_documents({"sellerId": ObjectId(order_seller_id)})
            inv_number = f"INV-{inv_count + 1:04d}"

            price = order.get("price", 0)
            gst_pct = order.get("gstPercent", 0)
            line_subtotal = price * fulfil_qty
            gst_amount = round(line_subtotal * gst_pct / 100, 2)
            line_total = round(line_subtotal + gst_amount, 2)

            inv_doc = {
                "invoiceNumber": inv_number,
                "sellerId": ObjectId(order_seller_id),
                "buyerId": order.get("buyerId"),
                "date": now,
                "dueDays": 7,
                "items": [{
                    "productId": str(order.get("listingId")),
                    "productName": order.get("productName", ""),
                    "quantity": fulfil_qty,
                    "price": price,
                    "discount": 0,
                    "purchase_price": order.get("purchasePrice", 0),
                    "gstPercent": gst_pct,
                    "gstAmount": gst_amount,
                    "total": line_total,
                    "selected_specifications": order.get("specifications", [])
                }],
                "subtotal": round(line_subtotal, 2),
                "gst": gst_amount,
                "total": line_total,
                "totalPaid": 0,
                "pendingAmount": line_total,
                "status": "draft",
                "notes": f"Fulfilment of pending order (Ref: {order.get('referenceInvoiceNumber', '')})",
                "createdBy": str(user["_id"]),
                "createdAt": now,
                "updatedAt": now
            }
            inv_result = await db.invoices.insert_one(inv_doc)

            # Link fulfillment invoice
            await db.pending_orders.update_one(
                {"_id": order["_id"]},
                {"$push": {"fulfilmentInvoiceIds": inv_result.inserted_id}}
            )

        return {
            "message": f"Fulfilled {fulfil_qty} units",
            "newStatus": new_status,
            "fulfilledQty": new_fulfilled,
            "pendingQty": max(0, new_pending),
            "invoiceNumber": inv_number if buyer else None
        }

    # ─── CANCEL PENDING ORDER ───

    @router.post("/pending-orders/{order_id}/cancel")
    async def cancel_pending_order(order_id: str, data: CancelRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, "create_invoice")
        seller_id = await get_seller_id(user)

        try:
            query = {"_id": ObjectId(order_id)}
            if seller_id:
                query["sellerId"] = ObjectId(seller_id)
            order = await db.pending_orders.find_one(query)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if not order:
            raise HTTPException(status_code=404, detail="Pending order not found")
        if order["status"] in ("completed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Order already {order['status']}")

        now = datetime.now(timezone.utc)
        await db.pending_orders.update_one(
            {"_id": order["_id"]},
            {"$set": {
                "status": "cancelled",
                "cancelReason": data.reason or "",
                "updatedAt": now
            }}
        )
        return {"message": "Pending order cancelled"}

    # ─── CREATE PO FROM PENDING ORDER ───

    @router.post("/pending-orders/{order_id}/create-po")
    async def create_po_from_pending(order_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, "manage_inventory")
        seller_id = await get_seller_id(user)

        try:
            query = {"_id": ObjectId(order_id)}
            if seller_id:
                query["sellerId"] = ObjectId(seller_id)
            order = await db.pending_orders.find_one(query)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if not order:
            raise HTTPException(status_code=404, detail="Pending order not found")
        if order["status"] in ("completed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Order already {order['status']}")

        order_seller_id = str(order.get("sellerId"))

        # Find a supplier for this product
        suppliers = await db.seller_suppliers.find({"sellerId": ObjectId(order_seller_id)}).to_list(10)
        if not suppliers:
            raise HTTPException(status_code=400, detail="No suppliers found. Please add a supplier first.")

        supplier = suppliers[0]  # Default to first supplier
        now = datetime.now(timezone.utc)

        # Generate PO number
        po_count = await db.purchase_orders.count_documents({"sellerId": ObjectId(order_seller_id)})
        po_number = f"PO-{now.strftime('%Y')}-{po_count + 1:04d}"

        po_doc = {
            "sellerId": ObjectId(order_seller_id),
            "supplierId": supplier["_id"],
            "supplierName": supplier.get("name", ""),
            "supplierPhone": supplier.get("phone", ""),
            "poNumber": po_number,
            "items": [{
                "listingId": order.get("listingId"),
                "productName": order.get("productName", ""),
                "sku": order.get("sku", ""),
                "description": "",
                "specification": "",
                "quantity": order.get("pendingQty", 0),
                "rate": order.get("purchasePrice", 0),
                "total": round(order.get("pendingQty", 0) * order.get("purchasePrice", 0), 2),
            }],
            "totalAmount": round(order.get("pendingQty", 0) * order.get("purchasePrice", 0), 2),
            "status": "draft",
            "deliveryNotes": f"For pending order - Buyer: {order.get('buyerName', '')}",
            "createdBy": str(user["_id"]),
            "createdAt": now,
            "updatedAt": now,
        }
        result = await db.purchase_orders.insert_one(po_doc)

        return {
            "message": f"Purchase order {po_number} created",
            "poId": str(result.inserted_id),
            "poNumber": po_number,
            "supplierName": supplier.get("name", "")
        }

    # ─── NOTIFY BUYER VIA WHATSAPP ───

    @router.post("/pending-orders/{order_id}/notify")
    async def notify_buyer(order_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, "create_invoice")
        seller_id = await get_seller_id(user)

        try:
            query = {"_id": ObjectId(order_id)}
            if seller_id:
                query["sellerId"] = ObjectId(seller_id)
            order = await db.pending_orders.find_one(query)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if not order:
            raise HTTPException(status_code=404, detail="Pending order not found")

        buyer = await db.seller_buyers.find_one({"_id": order.get("buyerId")})
        if not buyer or not buyer.get("phone"):
            raise HTTPException(status_code=400, detail="Buyer phone not available")

        order_seller_id = str(order.get("sellerId"))
        seller_user = await db.users.find_one({"_id": ObjectId(order_seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        business_name = profile.get("businessName", "Seller")

        msg = (
            f"Hello,\n\n"
            f"Your order for {order.get('productName', 'product')} has been partially fulfilled.\n\n"
            f"Pending Quantity: {order.get('pendingQty', 0)}\n\n"
            f"We will notify you once the remaining stock is available.\n\n"
            f"Thank you.\n{business_name}"
        )

        phone = buyer["phone"].replace(" ", "").replace("-", "").replace("+", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        wa_link = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"

        return {"whatsappLink": wa_link, "message": msg, "buyerPhone": buyer["phone"]}

    # ─── RESERVED STOCK API ───

    @router.get("/reserved-stock/{listing_id}")
    async def get_listing_reserved_stock(listing_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        if not seller_id:
            raise HTTPException(status_code=400, detail="Seller context required")

        reserved = await get_reserved_stock(seller_id, listing_id)
        listing = await db.sellerListings.find_one({"_id": ObjectId(listing_id)})
        total_stock = listing.get("stock", 0) if listing else 0

        return {
            "listingId": listing_id,
            "totalStock": total_stock,
            "reservedStock": reserved,
            "availableStock": max(0, total_stock - reserved)
        }

    return router
