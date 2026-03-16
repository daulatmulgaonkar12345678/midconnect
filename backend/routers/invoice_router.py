"""
Invoice Router - Complete billing, payment tracking, and invoice lifecycle management.
Supports: multiple partial payments, payment history, auto-calculated pending amounts,
receipt uploads, overdue detection, smart reminders, WhatsApp follow-ups.
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging
import urllib.parse

from models.business_tools import InvoiceCreate, InvoiceStatusUpdate, PaymentEntryCreate, ReminderSettingsUpdate, Permission
from services.invoice_pdf_service import generate_invoice_pdf, generate_merged_invoice_pdf

logger = logging.getLogger(__name__)

VALID_STATUSES = {"draft", "sent", "viewed", "partially_paid", "paid", "overdue", "cancelled"}
PAYMENT_METHODS = {"upi", "bank_transfer", "cash", "cheque", "other"}
RECEIPT_REQUIRED_METHODS = {"upi", "bank_transfer", "cheque"}


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
        """Generate next invoice number atomically using seller_invoice_counters."""
        seller_oid = ObjectId(seller_id)

        # Ensure counter doc exists
        counter = await db.seller_invoice_counters.find_one({"sellerId": seller_oid})
        if not counter:
            # Bootstrap: get business name from user profile or sellers collection
            business_name = None
            user_doc = await db.users.find_one({"_id": seller_oid})
            if user_doc:
                profile = user_doc.get("profile")
                if isinstance(profile, dict):
                    business_name = profile.get("businessName")
                if not business_name:
                    seller_doc = await db.sellers.find_one({"email": user_doc.get("email")})
                    if seller_doc:
                        business_name = seller_doc.get("businessName")
            if not business_name:
                business_name = f"Seller-{seller_id[-6:]}"

            words = business_name.split()
            abbreviation = ''.join(w[0].upper() for w in words if w and w[0].isalpha()) or 'XX'
            seller_code = seller_id[-6:].upper()

            await db.seller_invoice_counters.update_one(
                {"sellerId": seller_oid},
                {"$setOnInsert": {
                    "sellerId": seller_oid,
                    "sellerAbbreviation": abbreviation,
                    "sellerCode": seller_code,
                    "businessName": business_name,
                    "lastSequence": 0,
                    "createdAt": datetime.now(timezone.utc)
                }},
                upsert=True
            )

        # Atomic increment
        result = await db.seller_invoice_counters.find_one_and_update(
            {"sellerId": seller_oid},
            {"$inc": {"lastSequence": 1}},
            return_document=True
        )

        seq = result["lastSequence"]
        abbr = result["sellerAbbreviation"]
        code = result["sellerCode"]
        return f"INV{abbr}-{code}-{seq:04d}"

    async def ensure_status_consistency(inv: dict) -> dict:
        """Derive status from payment state. Never allow manual status override."""
        total = inv.get("total", 0)
        paid = inv.get("totalPaid", 0)
        pending = inv.get("pendingAmount")
        status = inv.get("status", "draft")

        # Fix pendingAmount if wrong
        correct_pending = round(max(0, total - paid), 2)
        needs_update = {}

        if pending is None or abs((pending or 0) - correct_pending) > 0.01:
            needs_update["pendingAmount"] = correct_pending
            inv["pendingAmount"] = correct_pending

        # Derive correct status (don't touch cancelled/draft with no payments)
        if status != "cancelled":
            if paid >= total and total > 0:
                correct_status = "paid"
            elif paid > 0:
                correct_status = "partially_paid"
            elif status in ("paid", "partially_paid"):
                correct_status = "sent"
            else:
                correct_status = status

            if correct_status != status:
                needs_update["status"] = correct_status
                inv["status"] = correct_status

        if needs_update:
            needs_update["updatedAt"] = datetime.now(timezone.utc)
            await db.invoices.update_one({"_id": inv["_id"]}, {"$set": needs_update})

        return inv

    async def check_overdue_invoices(seller_id: str):
        """Auto-detect and mark overdue invoices."""
        now = datetime.now(timezone.utc)
        invoices = await db.invoices.find({
            "sellerId": ObjectId(seller_id),
            "status": {"$in": ["draft", "sent", "viewed", "partially_paid"]},
        }).to_list(500)
        for inv in invoices:
            due_days = inv.get("dueDays", 7)
            invoice_date = inv.get("date", inv.get("createdAt"))
            if not invoice_date:
                continue
            if isinstance(invoice_date, str):
                try:
                    invoice_date = datetime.fromisoformat(invoice_date.replace("Z", "+00:00"))
                except Exception:
                    continue
            if invoice_date.tzinfo is None:
                invoice_date = invoice_date.replace(tzinfo=timezone.utc)
            due_date = invoice_date + timedelta(days=due_days)
            pending = inv.get("pendingAmount", inv.get("total", 0))
            if now > due_date and pending > 0:
                # Only notify if status is changing to overdue
                if inv.get("status") != "overdue":
                    inv_num = inv.get("invoiceNumber", "")
                    buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
                    buyer_name = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
                    await db.seller_notifications.insert_one({
                        "sellerId": ObjectId(seller_id),
                        "type": "invoice_overdue",
                        "title": f"Invoice {inv_num} is overdue",
                        "message": f"Payment from {buyer_name} for Rs.{pending:,.2f} is past due ({due_days} days).",
                        "referenceId": str(inv["_id"]),
                        "referenceType": "invoice",
                        "read": False,
                        "createdAt": now,
                    })
                await db.invoices.update_one(
                    {"_id": inv["_id"]},
                    {"$set": {"status": "overdue", "updatedAt": now}}
                )

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

        # Auto-detect overdue invoices
        await check_overdue_invoices(seller_id)

        query = {"sellerId": ObjectId(seller_id)}
        if status and status != "all":
            query["status"] = status

        invoices = await db.invoices.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        result = []
        for inv in invoices:
            # Ensure status is derived from payment state
            inv = await ensure_status_consistency(inv)
            buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
            inv["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
            inv["buyerPhone"] = buyer.get("phone", "") if buyer else ""
            inv["totalPaid"] = inv.get("totalPaid", 0)
            inv["pendingAmount"] = inv.get("pendingAmount", inv.get("total", 0))
            inv["dueDays"] = inv.get("dueDays", 7)
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
                "hsnCode": item.hsnCode or "",
                "quantity": item.quantity,
                "price": item.price,
                "discount": item.discount,
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
            "dueDays": data.dueDays,
            "items": invoice_items,
            "subtotal": subtotal,
            "gst": total_gst,
            "total": grand_total,
            "totalPaid": 0,
            "pendingAmount": grand_total,
            "status": "draft",
            "notes": data.notes,
            "poNumber": data.poNumber or "",
            "challanNumber": data.challanNumber or "",
            "placeOfSupply": data.placeOfSupply or "",
            "transport": data.transport.model_dump() if data.transport else {},
            "termsAndConditions": data.termsAndConditions or "",
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
                                            # Low stock alert for component
                                            comp_min = comp_listing.get("minStock", 0)
                                            comp_alert = comp_listing.get("lowStockAlertEnabled", True)
                                            if comp_alert and comp_min > 0 and new_stock <= comp_min:
                                                comp_name = comp_prod.get("name", "Unknown") if comp_prod else "Unknown"
                                                existing_lsa = await db.low_stock_alerts.find_one({
                                                    "sellerId": ObjectId(seller_id), "listingId": comp["listingId"], "status": "pending"
                                                })
                                                if not existing_lsa:
                                                    await db.low_stock_alerts.insert_one({
                                                        "sellerId": ObjectId(seller_id), "listingId": comp["listingId"],
                                                        "productName": comp_name, "currentStock": new_stock,
                                                        "minStock": comp_min, "status": "pending",
                                                        "createdAt": now, "updatedAt": now,
                                                    })
                                                    await db.seller_notifications.insert_one({
                                                        "sellerId": ObjectId(seller_id), "type": "low_stock",
                                                        "title": f"Low Stock Alert: {comp_name}",
                                                        "message": f"Remaining Stock: {new_stock}, Minimum Required: {comp_min}",
                                                        "referenceId": str(comp["listingId"]),
                                                        "referenceType": "inventory", "read": False, "createdAt": now,
                                                    })
                                                else:
                                                    await db.low_stock_alerts.update_one(
                                                        {"_id": existing_lsa["_id"]},
                                                        {"$set": {"currentStock": new_stock, "updatedAt": now}}
                                                    )
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
                                # Low stock alert for regular product
                                prod_min = listing.get("minStock", 0)
                                prod_alert = listing.get("lowStockAlertEnabled", True)
                                if prod_alert and prod_min > 0 and new_stock <= prod_min:
                                    existing_lsa2 = await db.low_stock_alerts.find_one({
                                        "sellerId": ObjectId(seller_id), "listingId": ObjectId(item["productId"]), "status": "pending"
                                    })
                                    if not existing_lsa2:
                                        await db.low_stock_alerts.insert_one({
                                            "sellerId": ObjectId(seller_id), "listingId": ObjectId(item["productId"]),
                                            "productName": item["productName"], "currentStock": new_stock,
                                            "minStock": prod_min, "status": "pending",
                                            "createdAt": now, "updatedAt": now,
                                        })
                                        await db.seller_notifications.insert_one({
                                            "sellerId": ObjectId(seller_id), "type": "low_stock",
                                            "title": f"Low Stock Alert: {item['productName']}",
                                            "message": f"Remaining Stock: {new_stock}, Minimum Required: {prod_min}",
                                            "referenceId": str(item["productId"]),
                                            "referenceType": "inventory", "read": False, "createdAt": now,
                                        })
                                    else:
                                        await db.low_stock_alerts.update_one(
                                            {"_id": existing_lsa2["_id"]},
                                            {"$set": {"currentStock": new_stock, "updatedAt": now}}
                                        )
                                if composite_router and hasattr(composite_router, 'sync_all_composites_for_component'):
                                    await composite_router.sync_all_composites_for_component(str(item["productId"]))
                    except Exception as e:
                        logger.warning(f"Stock deduction failed for {item['productId']}: {e}")

        await db.seller_buyers.update_one({"_id": ObjectId(data.buyerId)}, {"$inc": {"totalOrders": 1, "totalSpent": grand_total}})
        await activity_log_service.log(seller_id, str(user["_id"]), "invoice_created", "invoices", str(result.inserted_id), invoice_number)

        # Create notification for invoice created
        await db.seller_notifications.insert_one({
            "sellerId": ObjectId(seller_id),
            "type": "invoice_created",
            "title": f"Invoice {invoice_number} created",
            "message": f"Invoice for {buyer.get('buyerName', 'Unknown')} - Rs.{grand_total:,.2f}",
            "referenceId": str(result.inserted_id),
            "referenceType": "invoice",
            "read": False,
            "createdAt": now,
        })

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
        inv["buyerPhone"] = buyer.get("phone", "") if buyer else ""
        inv["buyerDetails"] = serialize_doc(buyer) if buyer else None
        inv["dueDays"] = inv.get("dueDays", 7)

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

        # Receipt validation: required for digital payment methods
        receipt_urls = data.receiptUrls or []
        method = data.paymentMethod.lower()
        if method in RECEIPT_REQUIRED_METHODS and len(receipt_urls) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Receipt upload is mandatory for {method.replace('_', ' ')} payments. Please attach at least one receipt."
            )

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
            "receiptUrls": receipt_urls,
            "createdBy": str(user["_id"]),
            "createdAt": now
        }

        result = await db.invoice_payments.insert_one(payment_doc)
        payment_doc["_id"] = result.inserted_id

        # Recalculate invoice payment status
        await recalc_payment_status(inv_oid)

        # Create notification for payment received
        updated_inv = await db.invoices.find_one({"_id": inv_oid})
        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
        buyer_name = buyer.get("buyerName", "Unknown") if buyer else "Unknown"
        inv_num = inv.get("invoiceNumber", "")
        is_fully_paid = updated_inv and updated_inv.get("pendingAmount", 1) <= 0

        notif_type = "payment_received" if is_fully_paid else "partial_payment"
        notif_title = f"Payment of Rs.{data.amount:,.2f} received" if not is_fully_paid else f"Invoice {inv_num} fully paid"
        notif_msg = f"{buyer_name} paid Rs.{data.amount:,.2f} for {inv_num} via {data.paymentMethod.replace('_', ' ')}."
        if not is_fully_paid and updated_inv:
            notif_msg += f" Pending: Rs.{updated_inv.get('pendingAmount', 0):,.2f}"

        await db.seller_notifications.insert_one({
            "sellerId": ObjectId(seller_id),
            "type": notif_type,
            "title": notif_title,
            "message": notif_msg,
            "referenceId": str(inv_oid),
            "referenceType": "invoice",
            "read": False,
            "createdAt": now,
        })

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
    async def get_invoice_pdf(invoice_id: str, authorization: str = Header(...), copy_type: str = "original"):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        valid_copies = ["original", "transporter", "supplier", "office"]
        if copy_type not in valid_copies:
            copy_type = "original"

        try:
            inv = await db.invoices.find_one({"_id": ObjectId(invoice_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        seller = await db.users.find_one({"_id": ObjectId(seller_id)})
        if not seller:
            seller = {}

        # Build seller dict for PDF from user profile
        profile = seller.get("profile") or {}
        gst = seller.get("gst") or {}
        billing = seller.get("billingSettings") or {}
        bank_details = {
            "bankName": billing.get("bankName", ""),
            "accountNumber": billing.get("accountNumber", ""),
            "accountName": billing.get("accountName", ""),
            "ifscCode": billing.get("ifscCode", ""),
            "branch": billing.get("branch", ""),
            "upiId": billing.get("upiId", ""),
        }
        seller_data = {
            "businessName": profile.get("businessName", ""),
            "name": profile.get("businessName", seller.get("email", "")),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "phone": profile.get("phone", ""),
            "email": seller.get("email", ""),
            "gstNumber": gst.get("number", ""),
            "sellerLogoUrl": billing.get("companyLogoUrl", "") or profile.get("sellerLogoUrl", ""),
            "bankDetails": bank_details,
            "invoiceTerms": billing.get("invoiceTerms", ""),
            "invoiceBackgroundImage": billing.get("invoiceBackgroundImage", ""),
        }

        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
        if not buyer:
            buyer = {}

        inv_serialized = serialize_doc([inv])[0]
        pdf_bytes = generate_invoice_pdf(inv_serialized, seller_data, buyer, copy_type=copy_type)
        copy_labels = {"original": "original", "transporter": "transporter", "supplier": "supplier", "office": "office"}
        filename = f"invoice-{inv.get('invoiceNumber', '')}-{copy_labels.get(copy_type, 'original')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    @router.get("/invoices/{invoice_id}/pdf-merged")
    async def get_invoice_pdf_merged(invoice_id: str, authorization: str = Header(...), copies: str = "original,transporter,supplier,office"):
        """Generate a merged PDF with multiple invoice copies (one per page)."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        valid_copies = ["original", "transporter", "supplier", "office"]
        copy_list = [c.strip() for c in copies.split(",") if c.strip() in valid_copies]
        if not copy_list:
            copy_list = ["original"]

        try:
            inv = await db.invoices.find_one({"_id": ObjectId(invoice_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        seller = await db.users.find_one({"_id": ObjectId(seller_id)}) or {}
        profile = seller.get("profile") or {}
        gst = seller.get("gst") or {}
        billing = seller.get("billingSettings") or {}
        bank_details = {
            "bankName": billing.get("bankName", ""),
            "accountNumber": billing.get("accountNumber", ""),
            "accountName": billing.get("accountName", ""),
            "ifscCode": billing.get("ifscCode", ""),
            "branch": billing.get("branch", ""),
            "upiId": billing.get("upiId", ""),
        }
        seller_data = {
            "businessName": profile.get("businessName", ""),
            "name": profile.get("businessName", seller.get("email", "")),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "phone": profile.get("phone", ""),
            "email": seller.get("email", ""),
            "gstNumber": gst.get("number", ""),
            "sellerLogoUrl": billing.get("companyLogoUrl", "") or profile.get("sellerLogoUrl", ""),
            "bankDetails": bank_details,
            "invoiceTerms": billing.get("invoiceTerms", ""),
            "invoiceBackgroundImage": billing.get("invoiceBackgroundImage", ""),
        }
        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")}) or {}
        inv_serialized = serialize_doc([inv])[0]

        if len(copy_list) == 1:
            pdf_bytes = generate_invoice_pdf(inv_serialized, seller_data, buyer, copy_type=copy_list[0])
        else:
            pdf_bytes = generate_merged_invoice_pdf(inv_serialized, seller_data, buyer, copy_list)

        filename = f"invoice-{inv.get('invoiceNumber', '')}-{'_'.join(copy_list)}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )



    @router.post("/invoices/{invoice_id}/eway-bill")
    async def generate_eway_bill(invoice_id: str, authorization: str = Header(...)):
        """Prepare E-Way Bill data from invoice. Returns JSON for GST portal submission."""
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
        profile = (seller or {}).get("profile", {})
        gst = (seller or {}).get("gst", {})
        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")}) or {}
        transport = inv.get("transport", {})

        eway_data = {
            "invoiceNumber": inv.get("invoiceNumber", ""),
            "invoiceDate": inv.get("date").isoformat() if hasattr(inv.get("date"), "isoformat") else str(inv.get("date", "")),
            "supplierGstin": gst.get("number", ""),
            "supplierName": profile.get("businessName", ""),
            "supplierAddress": profile.get("address", ""),
            "supplierState": profile.get("state", ""),
            "recipientGstin": buyer.get("gstNumber", ""),
            "recipientName": buyer.get("buyerName", buyer.get("name", "")),
            "recipientAddress": buyer.get("address", ""),
            "recipientState": buyer.get("state", inv.get("placeOfSupply", "")),
            "totalAmount": inv.get("total", 0),
            "taxableAmount": inv.get("subtotal", 0),
            "gstAmount": inv.get("gst", 0),
            "transporterName": transport.get("transporterName", ""),
            "transporterId": transport.get("transporterId", ""),
            "lrNumber": transport.get("lrNumber", ""),
            "vehicleNumber": transport.get("vehicleNumber", ""),
            "items": [{
                "productName": item.get("productName", ""),
                "hsnCode": item.get("hsnCode", ""),
                "quantity": item.get("quantity", 0),
                "taxableValue": round(item.get("price", 0) * item.get("quantity", 0), 2),
                "gstRate": item.get("gstPercent", 0),
            } for item in inv.get("items", [])],
            "portalUrl": "https://ewaybillgst.gov.in",
            "status": "prepared",
            "message": "E-Way Bill data prepared. Please submit on the GST E-Way Bill portal."
        }
        return eway_data



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

    # ==========================================
    # REMINDER SETTINGS
    # ==========================================

    @router.get("/reminder-settings")
    async def get_reminder_settings(authorization: str = Header(...)):
        """Get seller's reminder configuration."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        settings = await db.seller_reminder_settings.find_one({"sellerId": ObjectId(seller_id)}, {"_id": 0, "sellerId": 0})
        if not settings:
            settings = {"enabled": True, "reminderDays": [3, 7, 15], "customMessages": {}}
        return {"settings": settings}

    @router.put("/reminder-settings")
    async def update_reminder_settings(data: ReminderSettingsUpdate, authorization: str = Header(...)):
        """Update seller's reminder configuration."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        now = datetime.now(timezone.utc)
        await db.seller_reminder_settings.update_one(
            {"sellerId": ObjectId(seller_id)},
            {"$set": {
                "sellerId": ObjectId(seller_id),
                "enabled": data.enabled,
                "reminderDays": sorted(set(data.reminderDays)),
                "customMessages": data.customMessages or {},
                "updatedAt": now
            }},
            upsert=True
        )
        return {"message": "Reminder settings updated"}

    # ==========================================
    # INVOICE REMINDERS (Smart Follow-Up)
    # ==========================================

    @router.get("/invoice-reminders")
    async def get_invoice_reminders(authorization: str = Header(...)):
        """Get invoices that need reminders based on seller's schedule."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        settings = await db.seller_reminder_settings.find_one({"sellerId": ObjectId(seller_id)})
        if not settings:
            settings = {"enabled": True, "reminderDays": [3, 7, 15], "customMessages": {}}

        if not settings.get("enabled", True):
            return {"reminders": [], "enabled": False}

        reminder_days = sorted(settings.get("reminderDays", [3, 7, 15]))
        now = datetime.now(timezone.utc)

        invoices = await db.invoices.find({
            "sellerId": ObjectId(seller_id),
            "status": {"$in": ["sent", "partially_paid", "overdue"]},
            "pendingAmount": {"$gt": 0}
        }).to_list(500)

        reminders = []
        for inv in invoices:
            invoice_date = inv.get("date", inv.get("createdAt"))
            if not invoice_date:
                continue
            if isinstance(invoice_date, str):
                try:
                    invoice_date = datetime.fromisoformat(invoice_date.replace("Z", "+00:00"))
                except Exception:
                    continue
            if invoice_date.tzinfo is None:
                invoice_date = invoice_date.replace(tzinfo=timezone.utc)

            days_since = (now - invoice_date).days

            applicable_reminder = None
            for day in sorted(reminder_days, reverse=True):
                if days_since >= day:
                    applicable_reminder = day
                    break

            if applicable_reminder is None:
                continue

            buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
            buyer_name = buyer.get("buyerName", "Customer") if buyer else "Customer"
            buyer_phone = buyer.get("phone", "") if buyer else ""

            pending = inv.get("pendingAmount", 0)
            total = inv.get("total", 0)
            paid = inv.get("totalPaid", 0)
            inv_num = inv.get("invoiceNumber", "")

            custom_msgs = settings.get("customMessages", {})
            msg = custom_msgs.get(str(applicable_reminder))
            if not msg:
                if applicable_reminder <= 3:
                    msg = f"Hello {buyer_name},\n\nThis is a friendly reminder regarding Invoice {inv_num}.\n\nPending Amount: Rs.{pending:,.2f}\n\nKindly process the payment at your convenience.\n\nThank you."
                elif applicable_reminder <= 7:
                    msg = f"Hello {buyer_name},\n\nThis is regarding Invoice {inv_num}.\n\nTotal Amount: Rs.{total:,.2f}\nAmount Paid: Rs.{paid:,.2f}\nPending Amount: Rs.{pending:,.2f}\n\nKindly clear the pending payment.\n\nThank you."
                else:
                    msg = f"Hello {buyer_name},\n\nYour payment for Invoice {inv_num} is overdue.\n\nPending Amount: Rs.{pending:,.2f}\n\nKindly clear the payment at the earliest.\n\nThank you."

            wa_link = None
            if buyer_phone:
                clean_phone = buyer_phone.replace(" ", "").replace("-", "").replace("+", "")
                if not clean_phone.startswith("91") and len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone
                wa_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

            reminders.append({
                "invoiceId": str(inv["_id"]),
                "invoiceNumber": inv_num,
                "buyerName": buyer_name,
                "buyerPhone": buyer_phone,
                "daysSince": days_since,
                "reminderLevel": applicable_reminder,
                "reminderType": "friendly" if applicable_reminder <= 3 else ("due" if applicable_reminder <= 7 else "overdue"),
                "pendingAmount": pending,
                "total": total,
                "totalPaid": paid,
                "message": msg,
                "whatsappLink": wa_link,
                "status": inv.get("status")
            })

        reminders.sort(key=lambda r: r["daysSince"], reverse=True)
        return {"reminders": reminders, "enabled": True}

    # ==========================================
    # WHATSAPP MESSAGE HELPER
    # ==========================================

    @router.get("/invoices/{invoice_id}/whatsapp-link")
    async def get_whatsapp_link(invoice_id: str, authorization: str = Header(...), reminder_type: str = "followup"):
        """Generate a WhatsApp link for an invoice (follow-up, overdue, or send invoice)."""
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

        # Ensure status consistency
        inv = await ensure_status_consistency(inv)

        buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
        buyer_name = buyer.get("buyerName", "Customer") if buyer else "Customer"
        buyer_phone = buyer.get("phone", "") if buyer else ""

        if not buyer_phone:
            raise HTTPException(status_code=400, detail="Buyer phone number not available")

        pending = inv.get("pendingAmount", 0)
        total = inv.get("total", 0)
        paid = inv.get("totalPaid", 0)
        inv_num = inv.get("invoiceNumber", "")

        # Get seller business name
        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        business_name = profile.get("businessName", "Seller")

        if reminder_type == "send_invoice":
            msg = f"Hello {buyer_name},\n\nThank you for your purchase.\n\nInvoice Number: {inv_num}\nTotal Amount: Rs.{total:,.2f}\n\nPlease find the invoice attached.\n\nRegards\n{business_name}"
        elif reminder_type == "overdue":
            msg = f"Hello {buyer_name},\n\nYour payment for Invoice {inv_num} is overdue.\n\nPending Amount: Rs.{pending:,.2f}\n\nKindly clear the payment at the earliest.\n\nThank you."
        else:
            msg = f"Hello {buyer_name},\n\nThis is regarding Invoice {inv_num}.\n\nTotal Amount: Rs.{total:,.2f}\nAmount Paid: Rs.{paid:,.2f}\nPending Amount: Rs.{pending:,.2f}\n\nKindly clear the pending payment.\n\nThank you."

        clean_phone = buyer_phone.replace(" ", "").replace("-", "").replace("+", "")
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        wa_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
        return {"whatsappLink": wa_link, "message": msg, "buyerPhone": buyer_phone}

    # ==========================================
    # SELLER BUSINESS PROFILE
    # ==========================================

    @router.get("/dashboard-metrics")
    async def get_dashboard_metrics(authorization: str = Header(...)):
        """Get seller dashboard overview metrics using aggregated queries."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        seller_oid = ObjectId(seller_id)
        now = datetime.now(timezone.utc)

        # Run overdue check first
        await check_overdue_invoices(seller_id)

        # All metrics in parallel aggregations
        active_statuses = ["draft", "sent", "viewed", "partially_paid", "paid", "overdue"]

        # 1. Total Revenue (sum of total for paid + partially_paid)
        revenue_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$in": ["paid", "partially_paid"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        revenue_result = await db.invoices.aggregate(revenue_pipeline).to_list(1)
        total_revenue = revenue_result[0]["total"] if revenue_result else 0

        # 2. Pending Payments (sum of pendingAmount for unpaid)
        pending_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$in": ["sent", "viewed", "partially_paid", "overdue"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$pendingAmount"}}}
        ]
        pending_result = await db.invoices.aggregate(pending_pipeline).to_list(1)
        pending_payments = pending_result[0]["total"] if pending_result else 0

        # 3. Overdue count
        overdue_count = await db.invoices.count_documents({"sellerId": seller_oid, "status": "overdue"})

        # 4. This month's collections (sum of payment amounts this month)
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_pipeline = [
            {"$match": {"sellerId": seller_oid, "paymentDate": {"$gte": first_of_month}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        month_result = await db.invoice_payments.aggregate(month_pipeline).to_list(1)
        this_month = month_result[0]["total"] if month_result else 0

        # 5. Total invoices (exclude cancelled)
        total_invoices = await db.invoices.count_documents(
            {"sellerId": seller_oid, "status": {"$in": active_statuses}}
        )

        # 6. Quick alerts
        alerts = []
        if overdue_count > 0:
            alerts.append({"type": "overdue", "message": f"You have {overdue_count} overdue invoice{'s' if overdue_count > 1 else ''}", "severity": "high"})
        if pending_payments > 0:
            alerts.append({"type": "pending", "message": f"Rs.{pending_payments:,.2f} in pending payments", "severity": "medium"})

        # Today's payments
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_payments = await db.invoice_payments.count_documents(
            {"sellerId": seller_oid, "paymentDate": {"$gte": today_start}}
        )
        if today_payments > 0:
            alerts.append({"type": "payments_today", "message": f"{today_payments} payment{'s' if today_payments > 1 else ''} received today", "severity": "low"})

        # 7. Unread notification count
        unread_count = await db.seller_notifications.count_documents(
            {"sellerId": seller_oid, "read": False}
        )

        return {
            "totalRevenue": round(total_revenue, 2),
            "pendingPayments": round(pending_payments, 2),
            "overdueInvoices": overdue_count,
            "thisMonthCollections": round(this_month, 2),
            "totalInvoices": total_invoices,
            "alerts": alerts,
            "unreadNotifications": unread_count,
        }

    # ==========================================
    # NOTIFICATIONS
    # ==========================================

    @router.get("/notifications/unread-count")
    async def get_unread_notification_count(authorization: str = Header(...)):
        """Lightweight endpoint for sidebar badge."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        count = await db.seller_notifications.count_documents({"sellerId": ObjectId(seller_id), "read": False})
        return {"unread": count}

    @router.get("/notifications")
    async def get_notifications(
        authorization: str = Header(...),
        limit: int = 50,
        skip: int = 0,
        unread_only: bool = False,
        notification_type: str = ""
    ):
        """Get seller notifications with optional type filter."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        query: dict = {"sellerId": ObjectId(seller_id)}
        if unread_only:
            query["read"] = False
        if notification_type:
            query["type"] = notification_type
        notifications = await db.seller_notifications.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        total = await db.seller_notifications.count_documents({"sellerId": ObjectId(seller_id)} | ({"type": notification_type} if notification_type else {}))
        unread = await db.seller_notifications.count_documents({"sellerId": ObjectId(seller_id), "read": False})
        return {"notifications": serialize_doc(notifications), "total": total, "unread": unread}

    @router.put("/notifications/{notification_id}/read")
    async def mark_notification_read(notification_id: str, authorization: str = Header(...)):
        """Mark a notification as read."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        try:
            nid = ObjectId(notification_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid notification ID")
        await db.seller_notifications.update_one(
            {"_id": nid, "sellerId": ObjectId(seller_id)},
            {"$set": {"read": True, "readAt": datetime.now(timezone.utc)}}
        )
        return {"message": "Notification marked as read"}

    @router.put("/notifications/mark-all-read")
    async def mark_all_notifications_read(authorization: str = Header(...)):
        """Mark all notifications as read."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        now = datetime.now(timezone.utc)
        await db.seller_notifications.update_many(
            {"sellerId": ObjectId(seller_id), "read": False},
            {"$set": {"read": True, "readAt": now}}
        )
        return {"message": "All notifications marked as read"}

    @router.get("/seller-profile")
    async def get_seller_profile(authorization: str = Header(...)):
        """Get seller's business profile for settings/onboarding."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        profile = user.get("profile") or {}
        gst = user.get("gst") or {}
        billing = user.get("billingSettings") or {}

        # Get counter info for abbreviation/code
        counter = await db.seller_invoice_counters.find_one(
            {"sellerId": ObjectId(seller_id)}, {"_id": 0, "sellerId": 0}
        )

        return {
            "profile": {
                "businessName": profile.get("businessName", ""),
                "phone": profile.get("phone", ""),
                "email": user.get("email", ""),
                "address": profile.get("address", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "sellerLogoUrl": profile.get("sellerLogoUrl", ""),
                "gstNumber": gst.get("number", ""),
            },
            "billingSettings": {
                "bankName": billing.get("bankName", ""),
                "accountNumber": billing.get("accountNumber", ""),
                "accountName": billing.get("accountName", ""),
                "ifscCode": billing.get("ifscCode", ""),
                "branch": billing.get("branch", ""),
                "upiId": billing.get("upiId", ""),
                "invoiceTerms": billing.get("invoiceTerms", ""),
                "invoiceBackgroundImage": billing.get("invoiceBackgroundImage", ""),
                "companyLogoUrl": billing.get("companyLogoUrl", ""),
            },
            "invoiceIdentity": {
                "sellerAbbreviation": counter.get("sellerAbbreviation", "") if counter else "",
                "sellerCode": counter.get("sellerCode", "") if counter else "",
                "lastSequence": counter.get("lastSequence", 0) if counter else 0,
            },
            "profileComplete": bool(profile.get("businessName")),
        }

    @router.put("/seller-profile")
    async def update_seller_profile(authorization: str = Header(...), data: dict = {}):
        """Update seller's business profile."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        now = datetime.now(timezone.utc)

        business_name = data.get("businessName", "").strip()
        if not business_name:
            raise HTTPException(status_code=400, detail="Business name is required")

        # Ensure profile object exists first
        user_doc = await db.users.find_one({"_id": user["_id"]})
        if user_doc.get("profile") is None:
            await db.users.update_one({"_id": user["_id"]}, {"$set": {"profile": {}}})

        # Build profile update
        profile_update = {
            "profile.businessName": business_name,
            "profile.phone": data.get("phone", "").strip(),
            "profile.address": data.get("address", "").strip(),
            "profile.city": data.get("city", "").strip(),
            "profile.state": data.get("state", "").strip(),
            "updatedAt": now,
        }

        # Logo URL (only update if provided)
        logo_url = data.get("sellerLogoUrl")
        if logo_url is not None:
            profile_update["profile.sellerLogoUrl"] = logo_url

        # GST (only update if provided)
        gst_number = data.get("gstNumber")
        if gst_number is not None:
            if user_doc.get("gst") is None:
                await db.users.update_one({"_id": user["_id"]}, {"$set": {"gst": {}}})
            profile_update["gst.number"] = gst_number.strip()

        # Billing Settings (only update if provided)
        billing_data = data.get("billingSettings")
        if billing_data and isinstance(billing_data, dict):
            for field in ["bankName", "accountNumber", "accountName", "ifscCode", "branch", "upiId", "invoiceTerms", "invoiceBackgroundImage", "companyLogoUrl"]:
                if field in billing_data:
                    profile_update[f"billingSettings.{field}"] = str(billing_data[field]).strip() if billing_data[field] else ""

        await db.users.update_one({"_id": user["_id"]}, {"$set": profile_update})

        # Sync businessName to seller_invoice_counters
        seller_oid = ObjectId(seller_id)
        counter = await db.seller_invoice_counters.find_one({"sellerId": seller_oid})

        if counter:
            # Regenerate abbreviation only if it was auto-generated from a default name
            # (indicated by: old name starts with "Seller-", or abbreviation is single letter from default)
            update_fields = {"businessName": business_name, "updatedAt": now}
            old_name = counter.get("businessName", "")
            old_abbr = counter.get("sellerAbbreviation", "")
            is_default = old_name.startswith("Seller-") or not old_name or (len(old_abbr) <= 1 and old_name != business_name)
            if is_default:
                words = business_name.split()
                abbreviation = ''.join(w[0].upper() for w in words if w and w[0].isalpha()) or 'XX'
                update_fields["sellerAbbreviation"] = abbreviation

            await db.seller_invoice_counters.update_one(
                {"sellerId": seller_oid},
                {"$set": update_fields}
            )
        else:
            # First time: generate abbreviation and code
            words = business_name.split()
            abbreviation = ''.join(w[0].upper() for w in words if w and w[0].isalpha()) or 'XX'
            seller_code = seller_id[-6:].upper()

            await db.seller_invoice_counters.update_one(
                {"sellerId": seller_oid},
                {"$setOnInsert": {
                    "sellerId": seller_oid,
                    "sellerAbbreviation": abbreviation,
                    "sellerCode": seller_code,
                    "businessName": business_name,
                    "lastSequence": 0,
                    "createdAt": now
                }},
                upsert=True
            )

        # Get updated data
        updated_user = await db.users.find_one({"_id": user["_id"]})
        updated_counter = await db.seller_invoice_counters.find_one(
            {"sellerId": seller_oid}, {"_id": 0, "sellerId": 0}
        )

        up = updated_user.get("profile") or {}
        ug = updated_user.get("gst") or {}
        return {
            "message": "Profile updated",
            "profile": {
                "businessName": up.get("businessName", ""),
                "phone": up.get("phone", ""),
                "email": updated_user.get("email", ""),
                "address": up.get("address", ""),
                "city": up.get("city", ""),
                "state": up.get("state", ""),
                "sellerLogoUrl": up.get("sellerLogoUrl", ""),
                "gstNumber": ug.get("number", ""),
            },
            "invoiceIdentity": {
                "sellerAbbreviation": updated_counter.get("sellerAbbreviation", "") if updated_counter else "",
                "sellerCode": updated_counter.get("sellerCode", "") if updated_counter else "",
            },
        }

    return router
