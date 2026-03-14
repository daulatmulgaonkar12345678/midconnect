"""
Invoice Router - Complete billing, payment tracking, and invoice lifecycle management.
Supports: multiple partial payments, payment history, auto-calculated pending amounts.
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
import logging

from models.business_tools import InvoiceCreate, InvoiceStatusUpdate, PaymentEntryCreate, Permission
from services.invoice_pdf_service import generate_invoice_pdf

logger = logging.getLogger(__name__)

VALID_STATUSES = {"draft", "sent", "viewed", "partially_paid", "paid", "overdue", "cancelled"}
PAYMENT_METHODS = {"upi", "bank_transfer", "cash", "cheque", "other"}


def init_invoice_router(db, verify_token_func, activity_log_service, composite_router=None):
    router = APIRouter(tags=["Invoices"])

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
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
        if not role or permission not in role.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")

    async def get_next_invoice_number(seller_id: str) -> str:
        result = await db.sellers.find_one_and_update(
            {"userId": ObjectId(seller_id)},
            {"$inc": {"invoiceCounter": 1}},
            return_document=True
        )
        counter = result.get("invoiceCounter", 1) if result else 1
        short_id = seller_id[-6:].upper()
        return f"INV-{short_id}-{counter:04d}"

    async def recalc_payment_status(invoice_id):
        """Recalculate totalPaid, pendingAmount, and auto-update status."""
        if isinstance(invoice_id, str):
            invoice_id = ObjectId(invoice_id)
        inv = await db.invoices.find_one({"_id": invoice_id})
        if not inv:
            return
        grand_total = inv.get("total", 0)
        payments = await db.invoice_payments.find({"invoiceId": invoice_id}).to_list(500)
        total_paid = round(sum(p.get("amount", 0) for p in payments), 2)
        pending = round(max(0, grand_total - total_paid), 2)

        update = {
            "totalPaid": total_paid,
            "pendingAmount": pending,
            "updatedAt": datetime.now(timezone.utc)
        }

        current_status = inv.get("status", "draft")
        # Auto-update status based on payment
        if total_paid >= grand_total and grand_total > 0:
            update["status"] = "paid"
        elif total_paid > 0:
            update["status"] = "partially_paid"
        elif current_status in ("partially_paid", "paid"):
            # If all payments removed, revert to sent
            update["status"] = "sent"

        await db.invoices.update_one({"_id": invoice_id}, {"$set": update})

    # ==========================================
    # INVOICE PRODUCTS (for dropdown)
    # ==========================================

    @router.get("/invoice-products")
    async def get_invoice_products(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        listings = await db.sellerListings.find({
            "sellerId": ObjectId(seller_id),
            "status": {"$in": ["active", "paused"]}
        }).to_list(500)

        items = []
        for listing in listings:
            prod = await db.products.find_one({"_id": listing.get("productId")})
            if not prod:
                continue
            tiers = listing.get("pricingTiers", [])
            price = listing.get("selling_price") or (tiers[0].get("pricePerUnit", 0) if tiers else 0)
            specs = prod.get("specifications", {})
            spec_list = []
            if isinstance(specs, dict):
                for k, v in specs.items():
                    if v:
                        spec_list.append({"key": str(k), "value": str(v)})
            elif isinstance(specs, list):
                for s in specs:
                    if isinstance(s, dict):
                        spec_list.append({"key": str(s.get("key", s.get("name", ""))), "value": str(s.get("value", ""))})
            items.append({
                "id": str(listing["_id"]),
                "productName": prod.get("name", "Unknown"),
                "productType": listing.get("productType", "single"),
                "stock": listing.get("stock", 0),
                "price": price,
                "specifications": spec_list
            })
        return {"products": items}

    # ==========================================
    # INVOICE CRUD
    # ==========================================

    @router.get("/invoices")
    async def list_invoices(
        authorization: str = Header(...),
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        query = {"sellerId": ObjectId(seller_id)}
        if status and status != "all":
            query["status"] = status

        invoices = await db.invoices.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        result = []
        for inv in invoices:
            buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
            inv["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
            inv["buyerPhone"] = buyer.get("phone", "") if buyer else ""
            inv["totalPaid"] = inv.get("totalPaid", 0)
            inv["pendingAmount"] = inv.get("pendingAmount", inv.get("total", 0))
            result.append(inv)
        return {"invoices": serialize_doc(result)}

    @router.post("/invoices")
    async def create_invoice(data: InvoiceCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        buyer = await db.seller_buyers.find_one({"_id": ObjectId(data.buyerId), "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        invoice_items = []
        subtotal = 0.0

        for item in data.items:
            product_name = item.productName or "Item"
            if item.productId:
                try:
                    listing = await db.sellerListings.find_one({
                        "_id": ObjectId(item.productId),
                        "sellerId": ObjectId(seller_id)
                    })
                    if listing:
                        prod = await db.products.find_one({"_id": listing.get("productId")})
                        if prod:
                            product_name = prod.get("name", product_name)
                        if data.deductStock:
                            if listing.get("productType") == "composite":
                                cp_id = listing.get("compositeProductId")
                                if cp_id:
                                    components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
                                    for comp in components:
                                        comp_listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
                                        if not comp_listing:
                                            raise HTTPException(status_code=400, detail=f"Component not found for {product_name}")
                                        required = comp["quantity"] * item.quantity
                                        if comp_listing.get("stock", 0) < required:
                                            comp_prod = await db.products.find_one({"_id": comp_listing.get("productId")})
                                            cn = comp_prod.get("name", "Unknown") if comp_prod else "Unknown"
                                            raise HTTPException(status_code=400, detail=f"Insufficient stock for {cn} in {product_name}")
                            else:
                                if listing.get("stock", 0) < item.quantity:
                                    raise HTTPException(status_code=400, detail=f"Insufficient stock for {product_name}")
                except HTTPException:
                    raise
                except Exception:
                    pass

            line_subtotal = item.price * item.quantity
            gst_amount = round(line_subtotal * item.gstPercent / 100, 2)
            line_total = round(line_subtotal + gst_amount, 2)

            item_purchase_price = 0
            if item.productId:
                try:
                    pp_listing = await db.sellerListings.find_one({"_id": ObjectId(item.productId), "sellerId": ObjectId(seller_id)})
                    if pp_listing:
                        if pp_listing.get("productType") == "composite":
                            cp_id = pp_listing.get("compositeProductId")
                            if cp_id:
                                comps = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
                                for c in comps:
                                    cl = await db.sellerListings.find_one({"_id": c["listingId"]})
                                    if cl:
                                        item_purchase_price += (cl.get("purchase_price") or 0) * c.get("quantity", 1)
                        else:
                            item_purchase_price = pp_listing.get("purchase_price") or 0
                except Exception:
                    pass

            invoice_items.append({
                "productId": item.productId,
                "productName": product_name,
                "quantity": item.quantity,
                "price": item.price,
                "purchase_price": round(item_purchase_price, 2),
                "gstPercent": item.gstPercent,
                "gstAmount": gst_amount,
                "total": line_total,
                "selected_specifications": item.selected_specifications or []
            })
            subtotal += line_subtotal

        subtotal = round(subtotal, 2)
        total_gst = round(sum(i["gstAmount"] for i in invoice_items), 2)
        grand_total = round(subtotal + total_gst, 2)
        invoice_number = await get_next_invoice_number(seller_id)

        now = datetime.now(timezone.utc)
        invoice_doc = {
            "invoiceNumber": invoice_number,
            "sellerId": ObjectId(seller_id),
            "buyerId": ObjectId(data.buyerId),
            "date": now,
            "items": invoice_items,
            "subtotal": subtotal,
            "gst": total_gst,
            "total": grand_total,
            "totalPaid": 0,
            "pendingAmount": grand_total,
            "status": "draft",
            "notes": data.notes,
            "createdBy": str(user["_id"]),
            "createdAt": now,
            "updatedAt": now
        }

        result = await db.invoices.insert_one(invoice_doc)
        invoice_doc["_id"] = result.inserted_id

        # Deduct stock if requested
        if data.deductStock:
            for item in invoice_items:
                if item["productId"]:
                    try:
                        listing = await db.sellerListings.find_one({"_id": ObjectId(item["productId"])})
                        if listing:
                            if listing.get("productType") == "composite":
                                cp_id = listing.get("compositeProductId")
                                if cp_id:
                                    components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
                                    for comp in components:
                                        comp_listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
                                        if comp_listing:
                                            prev_stock = comp_listing.get("stock", 0)
                                            deduct_qty = comp["quantity"] * item["quantity"]
                                            new_stock = max(0, prev_stock - deduct_qty)
                                            await db.sellerListings.update_one({"_id": comp["listingId"]}, {"$set": {"stock": new_stock, "updatedAt": now}})
                                            comp_prod = await db.products.find_one({"_id": comp_listing.get("productId")})
                                            await db.inventory_logs.insert_one({
                                                "sellerId": ObjectId(seller_id), "listingId": comp["listingId"],
                                                "productName": comp_prod.get("name", "Unknown") if comp_prod else "Unknown",
                                                "changeType": "sale", "quantity": -deduct_qty,
                                                "previousStock": prev_stock, "newStock": new_stock,
                                                "note": f"Invoice {invoice_number} (composite: {item['productName']})",
                                                "createdBy": str(user["_id"]), "createdAt": now
                                            })
                                    if composite_router and hasattr(composite_router, 'sync_composite_stock'):
                                        await composite_router.sync_composite_stock(cp_id)
                            else:
                                prev_stock = listing.get("stock", 0)
                                new_stock = max(0, prev_stock - item["quantity"])
                                await db.sellerListings.update_one({"_id": ObjectId(item["productId"])}, {"$set": {"stock": new_stock, "updatedAt": now}})
                                await db.inventory_logs.insert_one({
                                    "sellerId": ObjectId(seller_id), "listingId": ObjectId(item["productId"]),
                                    "productName": item["productName"], "changeType": "sale",
                                    "quantity": -item["quantity"], "previousStock": prev_stock, "newStock": new_stock,
                                    "note": f"Invoice {invoice_number}", "createdBy": str(user["_id"]), "createdAt": now
                                })
                                if composite_router and hasattr(composite_router, 'sync_all_composites_for_component'):
                                    await composite_router.sync_all_composites_for_component(str(item["productId"]))
                    except Exception as e:
                        logger.warning(f"Stock deduction failed for {item['productId']}: {e}")

        await db.seller_buyers.update_one({"_id": ObjectId(data.buyerId)}, {"$inc": {"totalOrders": 1, "totalSpent": grand_total}})
        await activity_log_service.log(seller_id, str(user["_id"]), "invoice_created", "invoices", str(result.inserted_id), invoice_number)

        invoice_doc["buyerName"] = buyer.get("buyerName", "Unknown")
        return {"message": "Invoice created", "invoice": serialize_doc(invoice_doc)}

    @router.get("/invoices/{invoice_id}")
    async def get_invoice(invoice_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv = await db.invoices.find_one({"_id": ObjectId(invoice_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
        inv["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
        inv["buyerDetails"] = serialize_doc(buyer) if buyer else None

        # Include payment history
        payments = await db.invoice_payments.find({"invoiceId": inv["_id"]}).sort("paymentDate", -1).to_list(100)
        inv["payments"] = payments
        inv["totalPaid"] = inv.get("totalPaid", 0)
        inv["pendingAmount"] = inv.get("pendingAmount", inv.get("total", 0))

        return {"invoice": serialize_doc(inv)}

    @router.put("/invoices/{invoice_id}/status")
    async def update_invoice_status(invoice_id: str, data: InvoiceStatusUpdate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        if data.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {', '.join(VALID_STATUSES)}")

        try:
            inv_oid = ObjectId(invoice_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        await db.invoices.update_one({"_id": inv_oid}, {"$set": {"status": data.status, "updatedAt": datetime.now(timezone.utc)}})
        return {"message": f"Invoice status updated to {data.status}"}

    # ==========================================
    # PAYMENT ENTRIES
    # ==========================================

    @router.post("/invoices/{invoice_id}/payments")
    async def add_payment(invoice_id: str, data: PaymentEntryCreate, authorization: str = Header(...)):
        """Add a payment entry to an invoice. Supports partial and multiple payments."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv_oid = ObjectId(invoice_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if inv.get("status") == "cancelled":
            raise HTTPException(status_code=400, detail="Cannot add payment to cancelled invoice")

        pending = inv.get("pendingAmount", inv.get("total", 0))
        if data.amount > pending + 0.01:
            raise HTTPException(status_code=400, detail=f"Payment amount ({data.amount}) exceeds pending amount ({pending})")

        # Parse payment date
        payment_date = datetime.now(timezone.utc)
        if data.paymentDate:
            try:
                payment_date = datetime.fromisoformat(data.paymentDate.replace("Z", "+00:00"))
            except Exception:
                try:
                    payment_date = datetime.strptime(data.paymentDate[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass

        now = datetime.now(timezone.utc)
        payment_doc = {
            "invoiceId": inv_oid,
            "sellerId": ObjectId(seller_id),
            "amount": round(data.amount, 2),
            "paymentDate": payment_date,
            "paymentMethod": data.paymentMethod,
            "accountName": data.accountName,
            "accountType": data.accountType,
            "referenceNumber": data.referenceNumber,
            "notes": data.notes,
            "receiptUrls": [],
            "createdBy": str(user["_id"]),
            "createdAt": now
        }

        result = await db.invoice_payments.insert_one(payment_doc)
        payment_doc["_id"] = result.inserted_id

        # Recalculate invoice payment status
        await recalc_payment_status(inv_oid)

        return {"message": "Payment recorded", "payment": serialize_doc(payment_doc)}

    @router.get("/invoices/{invoice_id}/payments")
    async def list_payments(invoice_id: str, authorization: str = Header(...)):
        """Get all payment entries for an invoice."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv_oid = ObjectId(invoice_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        payments = await db.invoice_payments.find({"invoiceId": inv_oid}).sort("paymentDate", -1).to_list(100)

        return {
            "payments": serialize_doc(payments),
            "summary": {
                "grandTotal": inv.get("total", 0),
                "totalPaid": inv.get("totalPaid", 0),
                "pendingAmount": inv.get("pendingAmount", inv.get("total", 0)),
                "paymentCount": len(payments),
                "status": inv.get("status", "draft")
            }
        }

    @router.delete("/invoices/{invoice_id}/payments/{payment_id}")
    async def delete_payment(invoice_id: str, payment_id: str, authorization: str = Header(...)):
        """Delete a payment entry and recalculate invoice status."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv_oid = ObjectId(invoice_id)
            pay_oid = ObjectId(payment_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        payment = await db.invoice_payments.find_one({"_id": pay_oid, "invoiceId": inv_oid})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        await db.invoice_payments.delete_one({"_id": pay_oid})
        await recalc_payment_status(inv_oid)

        return {"message": "Payment deleted"}

    # ==========================================
    # PDF & DELETE
    # ==========================================

    @router.get("/invoices/{invoice_id}/pdf")
    async def get_invoice_pdf(invoice_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv = await db.invoices.find_one({"_id": ObjectId(invoice_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        seller = await db.users.find_one({"_id": ObjectId(seller_id)})
        if not seller:
            seller = {}
        seller_extra = await db.sellers.find_one({"userId": ObjectId(seller_id)})
        if seller_extra:
            seller.update({k: v for k, v in seller_extra.items() if k not in ("_id",) and v})

        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
        if not buyer:
            buyer = {}

        pdf_bytes = generate_invoice_pdf(inv, seller, buyer)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="invoice-{inv.get("invoiceNumber", "")}.pdf"'}
        )

    @router.delete("/invoices/{invoice_id}")
    async def delete_invoice(invoice_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        try:
            inv_oid = ObjectId(invoice_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if inv.get("status") not in ["draft", "cancelled"]:
            raise HTTPException(status_code=400, detail="Can only delete draft or cancelled invoices")

        # Also delete associated payments
        await db.invoice_payments.delete_many({"invoiceId": inv_oid})
        await db.invoices.delete_one({"_id": inv_oid})
        return {"message": "Invoice deleted"}

    return router
