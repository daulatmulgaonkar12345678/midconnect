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
from utils.permissions import authenticate_user, resolve_seller_id, require_user_permission
from utils.gst import calculate_gst, INDIAN_STATES

logger = logging.getLogger(__name__)

VALID_STATUSES = {"draft", "sent", "viewed", "partially_paid", "paid", "overdue", "cancelled"}
PAYMENT_METHODS = {"upi", "bank_transfer", "cash", "cheque", "other"}
RECEIPT_REQUIRED_METHODS = {"upi", "bank_transfer", "cheque"}


def init_invoice_router(db, verify_token_func, activity_log_service, composite_router=None, automation_executor=None):
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
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user: dict) -> str:
        return resolve_seller_id(user)

    async def require_permission(user: dict, permission: str):
        return await require_user_permission(db, user, permission)

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
            stock = listing.get("stock", 0)
            # Calculate reserved stock from pending orders
            reserved_pipeline = [
                {"$match": {
                    "sellerId": ObjectId(seller_id),
                    "listingId": listing["_id"],
                    "status": {"$in": ["pending", "partially_fulfilled"]}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
            ]
            reserved_result = await db.pending_orders.aggregate(reserved_pipeline).to_list(1)
            reserved = reserved_result[0]["total"] if reserved_result else 0
            available = max(0, stock - reserved)

            items.append({
                "id": str(listing["_id"]),
                "productName": prod.get("name", "Unknown"),
                "productType": listing.get("productType", "single"),
                "stock": stock,
                "reservedStock": reserved,
                "availableStock": available,
                "price": price,
                "gstRate": listing.get("gstRate", 0),
                "hsnCode": listing.get("hsnCode", ""),
                "description": listing.get("description", ""),
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

    # ─── Stock Check Before Invoice ───

    @router.post("/invoices/check-stock")
    async def check_invoice_stock(data: InvoiceCreate, authorization: str = Header(...)):
        """Pre-check stock availability for invoice items."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        shortages = []
        for item in data.items:
            if not item.productId or not data.deductStock:
                continue
            try:
                listing = await db.sellerListings.find_one({
                    "_id": ObjectId(item.productId),
                    "sellerId": ObjectId(seller_id)
                })
                if listing:
                    prod = await db.products.find_one({"_id": listing.get("productId")})
                    product_name = prod.get("name", item.productName or "Item") if prod else (item.productName or "Item")
                    stock = listing.get("stock", 0)

                    # Calculate reserved stock from pending orders
                    pipeline = [
                        {"$match": {
                            "sellerId": ObjectId(seller_id),
                            "listingId": listing["_id"],
                            "status": {"$in": ["pending", "partially_fulfilled"]}
                        }},
                        {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
                    ]
                    reserved_result = await db.pending_orders.aggregate(pipeline).to_list(1)
                    reserved = reserved_result[0]["total"] if reserved_result else 0
                    available = max(0, stock - reserved)

                    if item.quantity > available:
                        shortages.append({
                            "productId": item.productId,
                            "productName": product_name,
                            "requestedQty": item.quantity,
                            "totalStock": stock,
                            "reservedStock": reserved,
                            "availableStock": available,
                            "shortage": item.quantity - available,
                        })
            except Exception:
                pass

        return {"hasShortage": len(shortages) > 0, "shortages": shortages}

    @router.post("/invoices")
    async def create_invoice(data: InvoiceCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        buyer = await db.seller_buyers.find_one({"_id": ObjectId(data.buyerId), "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        # Get seller and buyer states for GST calculation
        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        seller_state = (seller_user or {}).get("profile", {}).get("state", "")
        buyer_state = buyer.get("state", "")
        gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"

        # Use placeOfSupply if provided, else buyer state
        place_of_supply = data.placeOfSupply or buyer_state

        invoice_items = []
        subtotal = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0

        for item in data.items:
            product_name = item.productName or "Item"
            item_hsn = item.hsnCode or ""
            item_description = ""
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
                        # Use listing's HSN/GST if not overridden
                        if not item_hsn:
                            item_hsn = listing.get("hsnCode", "")
                        item_description = listing.get("description", "")
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
                                current_stock = listing.get("stock", 0)
                                # Calculate available stock (accounting for reservations)
                                res_pipe = [
                                    {"$match": {"sellerId": ObjectId(seller_id), "listingId": listing["_id"], "status": {"$in": ["pending", "partially_fulfilled"]}}},
                                    {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
                                ]
                                res_r = await db.pending_orders.aggregate(res_pipe).to_list(1)
                                reserved_for_check = res_r[0]["total"] if res_r else 0
                                available_for_check = max(0, current_stock - reserved_for_check)
                                if available_for_check < item.quantity:
                                    if not data.allowPartialFulfillment:
                                        raise HTTPException(status_code=400, detail=f"Insufficient stock for {product_name}. Available: {available_for_check}, Requested: {item.quantity}")
                except HTTPException:
                    raise
                except Exception:
                    pass

            # Calculate GST breakdown using tax engine
            base = round(item.price * item.quantity, 2)
            disc_type = getattr(item, 'discountType', '%') or '%'
            disc_amt = round(base * item.discount / 100, 2) if disc_type == "%" else round(item.discount, 2)
            line_subtotal = max(round(base - disc_amt, 2), 0)
            gst_breakdown = calculate_gst(line_subtotal, item.gstPercent, seller_state, place_of_supply, gst_enabled)

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
                "description": item_description,
                "hsnCode": item_hsn,
                "quantity": item.quantity,
                "price": item.price,
                "discount": item.discount,
                "discountType": disc_type,
                "discountAmount": disc_amt,
                "purchase_price": round(item_purchase_price, 2),
                "gstPercent": item.gstPercent,
                "taxableAmount": gst_breakdown["taxableAmount"],
                "cgst": gst_breakdown["cgst"],
                "cgstRate": gst_breakdown["cgstRate"],
                "sgst": gst_breakdown["sgst"],
                "sgstRate": gst_breakdown["sgstRate"],
                "igst": gst_breakdown["igst"],
                "igstRate": gst_breakdown["igstRate"],
                "gstAmount": gst_breakdown["totalTax"],
                "total": gst_breakdown["totalAmount"],
                "selected_specifications": item.selected_specifications or []
            })
            subtotal += line_subtotal
            total_cgst += gst_breakdown["cgst"]
            total_sgst += gst_breakdown["sgst"]
            total_igst += gst_breakdown["igst"]

        subtotal = round(subtotal, 2)
        total_gst = round(total_cgst + total_sgst + total_igst, 2)

        # ── Additional Charges ──
        additional_charges = []
        freight_amount = 0.0
        other_charges_total = 0.0
        for ch in (data.additionalCharges or []):
            if ch.type == "fixed":
                amt = round(ch.value, 2)
            else:
                amt = round((subtotal + total_gst) * ch.value / 100, 2)
            additional_charges.append({"name": ch.name, "type": ch.type, "value": ch.value, "amount": amt})
            if ch.name.lower() == "freight":
                freight_amount = amt
            else:
                other_charges_total += amt

        # TCS calculation (on subtotal + GST, not on freight)
        tcs_amount = 0.0
        tcs_percent = 0.0
        if data.tcsEnabled and data.tcsPercent > 0:
            tcs_percent = round(data.tcsPercent, 2)
            tcs_amount = round((subtotal + total_gst) * tcs_percent / 100, 2)

        # Pre-round total
        pre_round_total = subtotal + total_gst + freight_amount + other_charges_total + tcs_amount

        # Auto round off to nearest rupee
        rounded_total = round(pre_round_total)
        round_off = round(rounded_total - pre_round_total, 2)
        grand_total = rounded_total

        invoice_number = await get_next_invoice_number(seller_id)

        # Determine tax type
        seller_state_norm = seller_state.strip().lower() if seller_state else ""
        pos_norm = place_of_supply.strip().lower() if place_of_supply else ""
        tax_type = "intra" if seller_state_norm and pos_norm and seller_state_norm == pos_norm else "inter"

        now = datetime.now(timezone.utc)
        invoice_doc = {
            "invoiceNumber": invoice_number,
            "sellerId": ObjectId(seller_id),
            "buyerId": ObjectId(data.buyerId),
            "date": now,
            "dueDays": data.dueDays,
            "items": invoice_items,
            "subtotal": subtotal,
            "cgst": round(total_cgst, 2),
            "sgst": round(total_sgst, 2),
            "igst": round(total_igst, 2),
            "gst": total_gst,
            "total": grand_total,
            "totalPaid": 0,
            "pendingAmount": grand_total,
            "status": "draft",
            "notes": data.notes,
            "poNumber": data.poNumber or "",
            "challanNumber": data.challanNumber or "",
            "placeOfSupply": place_of_supply,
            "sellerState": seller_state,
            "buyerState": buyer_state,
            "taxType": tax_type,
            "transport": data.transport.model_dump() if data.transport else {},
            "termsAndConditions": data.termsAndConditions or "",
            "shippingAddress": data.shippingAddress.model_dump() if data.shippingAddress else {},
            "paymentTerms": data.paymentTerms or "",
            "additionalCharges": additional_charges,
            "freight": freight_amount,
            "tcsEnabled": data.tcsEnabled,
            "tcsPercent": tcs_percent,
            "tcsAmount": tcs_amount,
            "roundOff": round_off,
            "linkedPanels": [{"panelId": lp.panelId, "recordId": lp.recordId} for lp in (data.linkedPanels or [])],
            "createdBy": str(user["_id"]),
            "createdAt": now,
            "updatedAt": now
        }

        result = await db.invoices.insert_one(invoice_doc)
        invoice_doc["_id"] = result.inserted_id

        # Deduct stock if requested + create pending orders for shortages
        pending_orders_created = []
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
                                requested_qty = item["quantity"]

                                # Calculate available stock (considering reservations from existing pending orders)
                                reserved_pipeline = [
                                    {"$match": {
                                        "sellerId": ObjectId(seller_id),
                                        "listingId": ObjectId(item["productId"]),
                                        "status": {"$in": ["pending", "partially_fulfilled"]}
                                    }},
                                    {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
                                ]
                                reserved_result = await db.pending_orders.aggregate(reserved_pipeline).to_list(1)
                                reserved_qty = reserved_result[0]["total"] if reserved_result else 0
                                available_stock = max(0, prev_stock - reserved_qty)

                                # Partial fulfillment: only deduct what's truly available
                                if data.allowPartialFulfillment and available_stock < requested_qty:
                                    actual_deduct = available_stock
                                    shortage = requested_qty - available_stock
                                elif available_stock < requested_qty:
                                    if not data.allowPartialFulfillment:
                                        raise HTTPException(status_code=400, detail=f"Insufficient stock for {item['productName']}. Available: {available_stock}, Requested: {requested_qty}")
                                    actual_deduct = available_stock
                                    shortage = requested_qty - available_stock
                                else:
                                    actual_deduct = requested_qty
                                    shortage = 0

                                if actual_deduct > 0:
                                    new_stock = max(0, prev_stock - actual_deduct)
                                    await db.sellerListings.update_one({"_id": ObjectId(item["productId"])}, {"$set": {"stock": new_stock, "updatedAt": now}})
                                    await db.inventory_logs.insert_one({
                                        "sellerId": ObjectId(seller_id), "listingId": ObjectId(item["productId"]),
                                        "productName": item["productName"], "changeType": "sale",
                                        "quantity": -actual_deduct, "previousStock": prev_stock, "newStock": new_stock,
                                        "note": f"Invoice {invoice_number}" + (f" (partial: {actual_deduct}/{requested_qty})" if shortage > 0 else ""),
                                        "createdBy": str(user["_id"]), "createdAt": now
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

                                # Create pending order for shortage
                                if shortage > 0:
                                    pending_doc = {
                                        "sellerId": ObjectId(seller_id),
                                        "buyerId": ObjectId(data.buyerId),
                                        "listingId": ObjectId(item["productId"]),
                                        "invoiceId": result.inserted_id,
                                        "referenceInvoiceNumber": invoice_number,
                                        "productName": item["productName"],
                                        "sku": listing.get("sku", ""),
                                        "orderedQty": requested_qty,
                                        "fulfilledQty": actual_deduct,
                                        "pendingQty": shortage,
                                        "price": item["price"],
                                        "gstPercent": item["gstPercent"],
                                        "purchasePrice": item.get("purchase_price", 0),
                                        "specifications": item.get("selected_specifications", []),
                                        "status": "pending" if actual_deduct == 0 else "partially_fulfilled",
                                        "fulfilmentInvoiceIds": [],
                                        "createdAt": now,
                                        "updatedAt": now,
                                    }
                                    po_result = await db.pending_orders.insert_one(pending_doc)
                                    pending_orders_created.append({
                                        "id": str(po_result.inserted_id),
                                        "productName": item["productName"],
                                        "pendingQty": shortage,
                                        "fulfilledQty": actual_deduct,
                                    })
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

        # ── Fire automation rules for system module "invoices" ──
        auto_exec = getattr(router, 'automation_executor', None) or automation_executor
        if auto_exec:
            try:
                auto_data = {
                    "invoiceNumber": invoice_doc.get("invoiceNumber", ""),
                    "buyerName": buyer.get("buyerName", ""),
                    "totalAmount": invoice_doc.get("total", 0),
                }
                await auto_exec(auto_data, "invoices", str(result.inserted_id), seller_id, str(user["_id"]), "record_created")
            except Exception as e:
                logger.warning(f"Automation trigger failed for invoice {invoice_doc.get('invoiceNumber')}: {e}")

        response = {"message": "Invoice created", "invoice": serialize_doc(invoice_doc)}
        if pending_orders_created:
            response["pendingOrders"] = pending_orders_created
            response["message"] = f"Invoice created with {len(pending_orders_created)} pending order(s)"
        return response

    # ==========================================
    # OFFLINE DRAFT SYNC ENDPOINT
    # ==========================================

    @router.post("/invoices/sync-offline-draft")
    async def sync_offline_draft(data: InvoiceCreate, authorization: str = Header(...)):
        """
        Sync an offline-created draft invoice to the server.
        Server always creates a NEW invoice with real ID and invoice number.
        Client temp IDs are completely ignored.
        """
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        buyer = await db.seller_buyers.find_one({"_id": ObjectId(data.buyerId), "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        # Get seller and buyer states for GST calculation
        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        seller_state = (seller_user or {}).get("profile", {}).get("state", "")
        buyer_state = buyer.get("state", "")
        gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"
        place_of_supply = data.placeOfSupply or buyer_state

        invoice_items = []
        subtotal = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0

        for item in data.items:
            product_name = item.productName or "Item"
            item_hsn = item.hsnCode or ""
            item_description = ""
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
                        if not item_hsn:
                            item_hsn = listing.get("hsnCode", "")
                        item_description = listing.get("description", "")
                except Exception:
                    pass

            base2 = round(item.price * item.quantity, 2)
            disc_type2 = getattr(item, 'discountType', '%') or '%'
            disc_amt2 = round(base2 * item.discount / 100, 2) if disc_type2 == "%" else round(item.discount, 2)
            line_subtotal = max(round(base2 - disc_amt2, 2), 0)
            gst_breakdown = calculate_gst(line_subtotal, item.gstPercent, seller_state, place_of_supply, gst_enabled)

            item_purchase_price = 0
            if item.productId:
                try:
                    pp_listing = await db.sellerListings.find_one({"_id": ObjectId(item.productId), "sellerId": ObjectId(seller_id)})
                    if pp_listing:
                        item_purchase_price = pp_listing.get("purchase_price") or 0
                except Exception:
                    pass

            invoice_items.append({
                "productId": item.productId,
                "productName": product_name,
                "description": item_description,
                "hsnCode": item_hsn,
                "quantity": item.quantity,
                "price": item.price,
                "discount": item.discount,
                "discountType": disc_type2,
                "discountAmount": disc_amt2,
                "purchase_price": round(item_purchase_price, 2),
                "gstPercent": item.gstPercent,
                "taxableAmount": gst_breakdown["taxableAmount"],
                "cgst": gst_breakdown["cgst"],
                "cgstRate": gst_breakdown["cgstRate"],
                "sgst": gst_breakdown["sgst"],
                "sgstRate": gst_breakdown["sgstRate"],
                "igst": gst_breakdown["igst"],
                "igstRate": gst_breakdown["igstRate"],
                "gstAmount": gst_breakdown["totalTax"],
                "total": gst_breakdown["totalAmount"],
                "selected_specifications": item.selected_specifications or []
            })
            subtotal += line_subtotal
            total_cgst += gst_breakdown["cgst"]
            total_sgst += gst_breakdown["sgst"]
            total_igst += gst_breakdown["igst"]

        subtotal = round(subtotal, 2)
        total_gst = round(total_cgst + total_sgst + total_igst, 2)

        additional_charges = []
        freight_amount = 0.0
        other_charges_total = 0.0
        for ch in (data.additionalCharges or []):
            if ch.type == "fixed":
                amt = round(ch.value, 2)
            else:
                amt = round((subtotal + total_gst) * ch.value / 100, 2)
            additional_charges.append({"name": ch.name, "type": ch.type, "value": ch.value, "amount": amt})
            if ch.name.lower() == "freight":
                freight_amount = amt
            else:
                other_charges_total += amt

        tcs_amount = 0.0
        tcs_percent = 0.0
        if data.tcsEnabled and data.tcsPercent > 0:
            tcs_percent = round(data.tcsPercent, 2)
            tcs_amount = round((subtotal + total_gst) * tcs_percent / 100, 2)

        pre_round_total = subtotal + total_gst + freight_amount + other_charges_total + tcs_amount
        rounded_total = round(pre_round_total)
        round_off = round(rounded_total - pre_round_total, 2)
        grand_total = rounded_total

        # Server generates the REAL invoice number
        invoice_number = await get_next_invoice_number(seller_id)

        seller_state_norm = seller_state.strip().lower() if seller_state else ""
        pos_norm = place_of_supply.strip().lower() if place_of_supply else ""
        tax_type = "intra" if seller_state_norm and pos_norm and seller_state_norm == pos_norm else "inter"

        now = datetime.now(timezone.utc)
        invoice_doc = {
            "invoiceNumber": invoice_number,
            "sellerId": ObjectId(seller_id),
            "buyerId": ObjectId(data.buyerId),
            "date": now,
            "dueDays": data.dueDays,
            "items": invoice_items,
            "subtotal": subtotal,
            "cgst": round(total_cgst, 2),
            "sgst": round(total_sgst, 2),
            "igst": round(total_igst, 2),
            "gst": total_gst,
            "total": grand_total,
            "totalPaid": 0,
            "pendingAmount": grand_total,
            "status": "draft",
            "notes": data.notes,
            "poNumber": data.poNumber or "",
            "challanNumber": data.challanNumber or "",
            "placeOfSupply": place_of_supply,
            "sellerState": seller_state,
            "buyerState": buyer_state,
            "taxType": tax_type,
            "transport": data.transport.model_dump() if data.transport else {},
            "termsAndConditions": data.termsAndConditions or "",
            "shippingAddress": data.shippingAddress.model_dump() if data.shippingAddress else {},
            "paymentTerms": data.paymentTerms or "",
            "additionalCharges": additional_charges,
            "freight": freight_amount,
            "tcsEnabled": data.tcsEnabled,
            "tcsPercent": tcs_percent,
            "tcsAmount": tcs_amount,
            "roundOff": round_off,
            "offlineSynced": True,
            "createdBy": str(user["_id"]),
            "createdAt": now,
            "updatedAt": now
        }

        result = await db.invoices.insert_one(invoice_doc)
        invoice_doc["_id"] = result.inserted_id
        invoice_doc["buyerName"] = buyer.get("buyerName", "Unknown")

        # Stock deduction is skipped for offline synced invoices for safety
        # The seller should manually review stock after sync

        logger.info(f"Offline draft synced → {invoice_number} for seller {seller_id}")
        return {"message": "Offline draft synced successfully", "invoice": serialize_doc(invoice_doc)}



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

        # Resolve linked panel data
        linked_panel_data = []
        for lp in inv.get("linkedPanels", []):
            try:
                panel = await db.panels.find_one({"_id": ObjectId(lp["panelId"])}, {"name": 1, "fields": 1, "color": 1})
                if not panel:
                    continue
                record = await db.panel_records.find_one({"_id": ObjectId(lp["recordId"])})
                if not record:
                    continue
                display = {}
                for f in panel.get("fields", []):
                    val = record.get("data", {}).get(f["key"])
                    if val is not None and f["type"] != "relation":
                        display[f.get("label", f["key"])] = val
                linked_panel_data.append({
                    "panelId": str(panel["_id"]),
                    "panelName": panel.get("name", "Panel"),
                    "panelColor": panel.get("color", "blue"),
                    "recordId": str(record["_id"]),
                    "data": display,
                })
            except Exception:
                pass
        inv["linkedPanelData"] = linked_panel_data

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

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        seller_biz_name = ((seller_user or {}).get("profile") or {}).get("businessName", "Seller")

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
                from utils.whatsapp_messages import payment_reminder_soft, payment_reminder_strict, build_doc_url
                import secrets as _secrets
                # Generate secure document share link for this invoice
                _now = datetime.now(timezone.utc)
                _token = _secrets.token_urlsafe(32)
                await db.document_shares.insert_one({
                    "token": _token,
                    "sellerId": inv.get("sellerId"),
                    "documentType": "invoice",
                    "documentId": str(inv["_id"]),
                    "recipientPhone": buyer_phone,
                    "expiresAt": _now + timedelta(days=30),
                    "createdAt": _now,
                })
                _doc_url = build_doc_url(_token)
                due_date_str = inv.get("dueDate", "")
                if isinstance(due_date_str, datetime):
                    due_date_str = due_date_str.strftime("%d %b %Y")
                elif not due_date_str:
                    due_date_str = "N/A"
                if applicable_reminder <= 7:
                    msg = payment_reminder_soft(
                        invoice_number=inv_num, pending_amount=pending,
                        due_date=due_date_str, doc_url=_doc_url,
                        business_name=seller_biz_name, buyer_name=buyer_name,
                    )
                else:
                    msg = payment_reminder_strict(
                        invoice_number=inv_num, pending_amount=pending,
                        due_date=due_date_str, doc_url=_doc_url,
                        business_name=seller_biz_name, buyer_name=buyer_name,
                    )

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
        inv_num = inv.get("invoiceNumber", "")

        # Get seller business name
        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        business_name = profile.get("businessName", "Seller")

        # Generate secure document share link for this invoice
        from utils.whatsapp_messages import invoice_message, payment_reminder_soft, payment_reminder_strict, build_doc_url
        import secrets as _secrets
        now_utc = datetime.now(timezone.utc)
        token = _secrets.token_urlsafe(32)
        await db.document_shares.insert_one({
            "token": token,
            "sellerId": ObjectId(seller_id),
            "documentType": "invoice",
            "documentId": str(inv["_id"]),
            "recipientPhone": buyer_phone,
            "expiresAt": now_utc + timedelta(days=30),
            "createdAt": now_utc,
        })
        doc_url = build_doc_url(token)

        if reminder_type == "send_invoice":
            msg = invoice_message(
                invoice_number=inv_num, amount=total,
                doc_url=doc_url, business_name=business_name, buyer_name=buyer_name,
            )
        elif reminder_type == "overdue":
            due_date_str = inv.get("dueDate", "")
            if hasattr(due_date_str, "strftime"):
                due_date_str = due_date_str.strftime("%d %b %Y")
            msg = payment_reminder_strict(
                invoice_number=inv_num, pending_amount=pending,
                due_date=due_date_str or "N/A", doc_url=doc_url,
                business_name=business_name, buyer_name=buyer_name,
            )
        else:
            due_date_str = inv.get("dueDate", "")
            if hasattr(due_date_str, "strftime"):
                due_date_str = due_date_str.strftime("%d %b %Y")
            msg = payment_reminder_soft(
                invoice_number=inv_num, pending_amount=pending,
                due_date=due_date_str or "N/A", doc_url=doc_url,
                business_name=business_name, buyer_name=buyer_name,
            )

        clean_phone = buyer_phone.replace(" ", "").replace("-", "").replace("+", "")
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        wa_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

        # Auto-update status to "sent" if currently draft
        if inv.get("status") == "draft":
            await db.invoices.update_one(
                {"_id": inv_oid, "status": "draft"},
                {"$set": {
                    "status": "sent",
                    "sentAt": datetime.now(timezone.utc),
                    "sentVia": "whatsapp",
                    "updatedAt": datetime.now(timezone.utc)
                }}
            )

        return {"whatsappLink": wa_link, "message": msg, "buyerPhone": buyer_phone}

    @router.put("/invoices/{invoice_id}/mark-sent")
    async def mark_invoice_sent(invoice_id: str, authorization: str = Header(...)):
        """Manually mark a draft invoice as sent."""
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

        if inv.get("status") != "draft":
            return {"message": "Invoice is already sent or in a later status", "status": inv.get("status")}

        now_utc = datetime.now(timezone.utc)
        await db.invoices.update_one(
            {"_id": inv_oid, "status": "draft"},
            {"$set": {
                "status": "sent",
                "sentAt": now_utc,
                "sentVia": "manual",
                "updatedAt": now_utc
            }}
        )

        return {"message": "Invoice marked as sent", "status": "sent", "sentAt": now_utc.isoformat()}

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
                "gstStatus": gst.get("status", "enabled"),
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

        gst_status = data.get("gstStatus")
        if gst_status is not None:
            if user_doc.get("gst") is None:
                await db.users.update_one({"_id": user["_id"]}, {"$set": {"gst": {}}})
            profile_update["gst.status"] = gst_status.strip()

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
