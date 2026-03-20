"""
QUOTATION SYSTEM ROUTER
========================
Full quotation lifecycle: Create, Edit, List, PDF, WhatsApp, Convert to Invoice.

Endpoints:
- GET    /quotations              → List quotations
- POST   /quotations              → Create quotation
- GET    /quotations/{id}         → Get single quotation
- PUT    /quotations/{id}         → Update quotation
- DELETE /quotations/{id}         → Delete quotation
- POST   /quotations/{id}/convert → Convert quotation to invoice
- POST   /quotations/sync-offline → Sync offline-created quotation
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List as PyList
from datetime import datetime, timezone
from bson import ObjectId
from services.quotation_pdf_service import generate_quotation_pdf
import logging

logger = logging.getLogger(__name__)


class QuotationItemCreate(BaseModel):
    productId: str = ""
    productName: str = ""
    description: str = ""
    hsnCode: str = ""
    quantity: float = 1
    price: float = 0
    discount: float = 0
    gstPercent: float = 0
    selected_specifications: PyList[dict] = []


class QuotationCreate(BaseModel):
    buyerId: str
    items: PyList[QuotationItemCreate]
    notes: str = ""
    validityDays: int = 15
    termsAndConditions: str = ""
    placeOfSupply: str = ""


class QuotationUpdate(BaseModel):
    buyerId: Optional[str] = None
    items: Optional[PyList[QuotationItemCreate]] = None
    notes: Optional[str] = None
    validityDays: Optional[int] = None
    termsAndConditions: Optional[str] = None
    status: Optional[str] = None
    placeOfSupply: Optional[str] = None


def init_quotation_router(db, verify_token_func):
    router = APIRouter()

    async def get_current_user(authorization: str):
        from utils.permissions import authenticate_user
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user):
        seller_id = user.get("sellerId") or str(user.get("_id", ""))
        return seller_id

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

    async def get_next_quotation_number(seller_id: str) -> str:
        seller_oid = ObjectId(seller_id)
        counter = await db.seller_quotation_counters.find_one({"sellerId": seller_oid})

        if not counter:
            seller_user = await db.users.find_one({"_id": seller_oid})
            business_name = (seller_user or {}).get("profile", {}).get("businessName", "")
            if not business_name:
                business_name = f"Seller-{seller_id[-6:]}"
            words = business_name.split()
            abbreviation = ''.join(w[0].upper() for w in words if w and w[0].isalpha()) or 'XX'
            seller_code = seller_id[-6:].upper()

            await db.seller_quotation_counters.update_one(
                {"sellerId": seller_oid},
                {"$setOnInsert": {
                    "sellerId": seller_oid,
                    "sellerAbbreviation": abbreviation,
                    "sellerCode": seller_code,
                    "lastSequence": 0,
                    "createdAt": datetime.now(timezone.utc)
                }},
                upsert=True
            )

        result = await db.seller_quotation_counters.find_one_and_update(
            {"sellerId": seller_oid},
            {"$inc": {"lastSequence": 1}},
            return_document=True
        )
        seq = result["lastSequence"]
        abbr = result["sellerAbbreviation"]
        code = result["sellerCode"]
        return f"QUO{abbr}-{code}-{seq:04d}"

    def calculate_gst(taxable, gst_pct, seller_state, place_of_supply, enabled=True):
        if not enabled or gst_pct <= 0:
            return {"taxableAmount": round(taxable, 2), "cgst": 0, "cgstRate": 0, "sgst": 0, "sgstRate": 0, "igst": 0, "igstRate": 0, "totalTax": 0, "totalAmount": round(taxable, 2)}
        ss = (seller_state or "").strip().lower()
        ps = (place_of_supply or "").strip().lower()
        is_intra = ss and ps and ss == ps
        if is_intra:
            half = round(gst_pct / 2, 2)
            cgst = round(taxable * half / 100, 2)
            sgst = round(taxable * half / 100, 2)
            return {"taxableAmount": round(taxable, 2), "cgst": cgst, "cgstRate": half, "sgst": sgst, "sgstRate": half, "igst": 0, "igstRate": 0, "totalTax": round(cgst + sgst, 2), "totalAmount": round(taxable + cgst + sgst, 2)}
        else:
            igst = round(taxable * gst_pct / 100, 2)
            return {"taxableAmount": round(taxable, 2), "cgst": 0, "cgstRate": 0, "sgst": 0, "sgstRate": 0, "igst": igst, "igstRate": gst_pct, "totalTax": igst, "totalAmount": round(taxable + igst, 2)}

    async def build_quotation_items(items, seller_id, seller_state, place_of_supply, gst_enabled):
        q_items = []
        subtotal = total_cgst = total_sgst = total_igst = 0.0

        for item in items:
            product_name = item.productName or "Item"
            hsn = item.hsnCode or ""
            desc = item.description or ""

            if item.productId:
                try:
                    listing = await db.sellerListings.find_one({"_id": ObjectId(item.productId), "sellerId": ObjectId(seller_id)})
                    if listing:
                        prod = await db.products.find_one({"_id": listing.get("productId")})
                        if prod:
                            product_name = prod.get("name", product_name)
                        if not hsn:
                            hsn = listing.get("hsnCode", "")
                        if not desc:
                            desc = listing.get("description", "")
                except Exception:
                    pass

            line_sub = round(item.price * item.quantity - item.discount, 2)
            gst = calculate_gst(line_sub, item.gstPercent, seller_state, place_of_supply, gst_enabled)

            q_items.append({
                "productId": item.productId, "productName": product_name,
                "description": desc, "hsnCode": hsn,
                "quantity": item.quantity, "price": item.price, "discount": item.discount,
                "gstPercent": item.gstPercent,
                "taxableAmount": gst["taxableAmount"],
                "cgst": gst["cgst"], "cgstRate": gst["cgstRate"],
                "sgst": gst["sgst"], "sgstRate": gst["sgstRate"],
                "igst": gst["igst"], "igstRate": gst["igstRate"],
                "gstAmount": gst["totalTax"], "total": gst["totalAmount"],
                "selected_specifications": item.selected_specifications or []
            })
            subtotal += line_sub
            total_cgst += gst["cgst"]
            total_sgst += gst["sgst"]
            total_igst += gst["igst"]

        total_gst = round(total_cgst + total_sgst + total_igst, 2)
        grand_total = round(subtotal + total_gst)
        round_off = round(grand_total - (subtotal + total_gst), 2)
        return q_items, round(subtotal, 2), round(total_cgst, 2), round(total_sgst, 2), round(total_igst, 2), total_gst, grand_total, round_off

    # ── LIST ──
    @router.get("/quotations")
    async def list_quotations(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id)}},
            {"$lookup": {"from": "seller_buyers", "localField": "buyerId", "foreignField": "_id", "as": "buyer"}},
            {"$unwind": {"path": "$buyer", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"createdAt": -1}},
            {"$limit": 200},
            {"$project": {
                "quotationNumber": 1, "date": 1, "status": 1, "subtotal": 1, "gst": 1, "total": 1,
                "validityDays": 1, "notes": 1, "items": 1, "convertedToInvoice": 1, "convertedInvoiceNumber": 1,
                "buyerName": {"$ifNull": ["$buyer.buyerName", "Unknown"]},
                "buyerPhone": {"$ifNull": ["$buyer.phone", ""]},
                "buyerId": 1, "createdAt": 1, "updatedAt": 1,
                "placeOfSupply": 1, "termsAndConditions": 1,
                "cgst": 1, "sgst": 1, "igst": 1, "roundOff": 1,
            }}
        ]
        results = []
        async for doc in db.quotations.aggregate(pipeline):
            results.append(serialize_doc(doc))
        return {"quotations": results}

    # ── CREATE ──
    @router.post("/quotations")
    async def create_quotation(data: QuotationCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        buyer = await db.seller_buyers.find_one({"_id": ObjectId(data.buyerId), "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        seller_state = (seller_user or {}).get("profile", {}).get("state", "")
        gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"
        pos = data.placeOfSupply or buyer.get("state", "")

        q_items, subtotal, cgst, sgst, igst, total_gst, grand_total, round_off = await build_quotation_items(
            data.items, seller_id, seller_state, pos, gst_enabled
        )

        q_number = await get_next_quotation_number(seller_id)
        now = datetime.now(timezone.utc)

        doc = {
            "quotationNumber": q_number, "sellerId": ObjectId(seller_id),
            "buyerId": ObjectId(data.buyerId), "date": now,
            "validityDays": data.validityDays, "items": q_items,
            "subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst,
            "gst": total_gst, "total": grand_total, "roundOff": round_off,
            "status": "draft", "notes": data.notes,
            "termsAndConditions": data.termsAndConditions or "",
            "placeOfSupply": pos, "convertedToInvoice": False,
            "createdBy": str(user["_id"]), "createdAt": now, "updatedAt": now,
        }
        result = await db.quotations.insert_one(doc)
        doc["_id"] = result.inserted_id
        doc["buyerName"] = buyer.get("buyerName", "")
        logger.info(f"Quotation created: {q_number}")
        return {"message": "Quotation created", "quotation": serialize_doc(doc)}

    # ── GET SINGLE ──
    @router.get("/quotations/{quotation_id}")
    async def get_quotation(quotation_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        doc = await db.quotations.find_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Quotation not found")
        buyer = await db.seller_buyers.find_one({"_id": doc.get("buyerId")})
        doc["buyerName"] = buyer.get("buyerName", "") if buyer else ""
        doc["buyerPhone"] = buyer.get("phone", "") if buyer else ""
        return {"quotation": serialize_doc(doc)}

    # ── UPDATE ──
    @router.put("/quotations/{quotation_id}")
    async def update_quotation(quotation_id: str, data: QuotationUpdate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        existing = await db.quotations.find_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Quotation not found")
        if existing.get("convertedToInvoice"):
            raise HTTPException(status_code=400, detail="Cannot edit a converted quotation")

        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        if data.status is not None:
            update_fields["status"] = data.status
        if data.notes is not None:
            update_fields["notes"] = data.notes
        if data.validityDays is not None:
            update_fields["validityDays"] = data.validityDays
        if data.termsAndConditions is not None:
            update_fields["termsAndConditions"] = data.termsAndConditions

        if data.items is not None:
            seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
            seller_state = (seller_user or {}).get("profile", {}).get("state", "")
            gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"
            pos = data.placeOfSupply or existing.get("placeOfSupply", "")

            q_items, subtotal, cgst, sgst, igst, total_gst, grand_total, round_off = await build_quotation_items(
                data.items, seller_id, seller_state, pos, gst_enabled
            )
            update_fields.update({
                "items": q_items, "subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst,
                "gst": total_gst, "total": grand_total, "roundOff": round_off,
            })
            if data.buyerId:
                update_fields["buyerId"] = ObjectId(data.buyerId)
            if data.placeOfSupply:
                update_fields["placeOfSupply"] = data.placeOfSupply

        await db.quotations.update_one({"_id": ObjectId(quotation_id)}, {"$set": update_fields})
        return {"message": "Quotation updated"}

    # ── DELETE ──
    @router.delete("/quotations/{quotation_id}")
    async def delete_quotation(quotation_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        result = await db.quotations.delete_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Quotation not found")
        return {"message": "Quotation deleted"}

    # ── CONVERT TO INVOICE ──
    @router.post("/quotations/{quotation_id}/convert")
    async def convert_to_invoice(quotation_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        quo = await db.quotations.find_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        if not quo:
            raise HTTPException(status_code=404, detail="Quotation not found")
        if quo.get("convertedToInvoice"):
            raise HTTPException(status_code=400, detail="Already converted to invoice")

        items = []
        for item in quo.get("items", []):
            items.append({
                "productId": item.get("productId", ""), "productName": item.get("productName", ""),
                "description": item.get("description", ""), "hsnCode": item.get("hsnCode", ""),
                "quantity": item.get("quantity", 1), "price": item.get("price", 0),
                "discount": item.get("discount", 0), "gstPercent": item.get("gstPercent", 0),
                "selected_specifications": item.get("selected_specifications", []),
            })
        return {
            "prefill": {
                "buyerId": str(quo.get("buyerId", "")),
                "items": items,
                "notes": quo.get("notes", ""),
                "termsAndConditions": quo.get("termsAndConditions", ""),
                "placeOfSupply": quo.get("placeOfSupply", ""),
                "sourceQuotationId": quotation_id,
                "sourceQuotationNumber": quo.get("quotationNumber", ""),
            }
        }

    # ── PDF DOWNLOAD ──
    @router.get("/quotations/{quotation_id}/pdf")
    async def get_quotation_pdf(quotation_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        try:
            quo = await db.quotations.find_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid quotation ID")
        if not quo:
            raise HTTPException(status_code=404, detail="Quotation not found")

        seller = await db.users.find_one({"_id": ObjectId(seller_id)}) or {}
        profile = seller.get("profile") or {}
        gst_info = seller.get("gst") or {}
        billing = seller.get("billingSettings") or {}
        bank_details = {
            "bankName": billing.get("bankName", ""),
            "accountNumber": billing.get("accountNumber", ""),
            "accountName": billing.get("accountName", ""),
            "ifscCode": billing.get("ifscCode", ""),
            "branch": billing.get("branch", ""),
        }
        seller_data = {
            "businessName": profile.get("businessName", ""),
            "name": profile.get("businessName", seller.get("email", "")),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "phone": profile.get("phone", ""),
            "email": seller.get("email", ""),
            "gstNumber": gst_info.get("number", ""),
            "sellerLogoUrl": billing.get("companyLogoUrl", "") or profile.get("sellerLogoUrl", ""),
            "bankDetails": bank_details,
            "invoiceTerms": billing.get("invoiceTerms", ""),
        }

        buyer = await db.seller_buyers.find_one({"_id": quo.get("buyerId")}) or {}
        quo_serialized = serialize_doc(quo)
        is_offline = quo.get("offlineSynced", False)

        pdf_bytes = generate_quotation_pdf(quo_serialized, seller_data, buyer, is_offline=is_offline)
        filename = f"quotation-{quo.get('quotationNumber', '')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # ── STORE CONVERSION PREFILL (fallback for page refresh) ──
    @router.post("/quotations/{quotation_id}/store-prefill")
    async def store_conversion_prefill(quotation_id: str, authorization: str = Header(...)):
        """Store quotation prefill data server-side for reliable conversion across refreshes."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        quo = await db.quotations.find_one({"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)})
        if not quo:
            raise HTTPException(status_code=404, detail="Quotation not found")
        if quo.get("convertedToInvoice"):
            raise HTTPException(status_code=400, detail="Already converted to invoice")

        items = []
        for item in quo.get("items", []):
            items.append({
                "productId": item.get("productId", ""), "productName": item.get("productName", ""),
                "description": item.get("description", ""), "hsnCode": item.get("hsnCode", ""),
                "quantity": item.get("quantity", 1), "price": item.get("price", 0),
                "discount": item.get("discount", 0), "gstPercent": item.get("gstPercent", 0),
                "selected_specifications": item.get("selected_specifications", []),
            })
        prefill = {
            "buyerId": str(quo.get("buyerId", "")),
            "items": items,
            "notes": quo.get("notes", ""),
            "termsAndConditions": quo.get("termsAndConditions", ""),
            "placeOfSupply": quo.get("placeOfSupply", ""),
            "sourceQuotationId": quotation_id,
            "sourceQuotationNumber": quo.get("quotationNumber", ""),
        }
        now = datetime.now(timezone.utc)
        await db.quotation_prefills.update_one(
            {"sellerId": ObjectId(seller_id), "quotationId": ObjectId(quotation_id)},
            {"$set": {"prefill": prefill, "updatedAt": now, "sellerId": ObjectId(seller_id), "quotationId": ObjectId(quotation_id)},
             "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        return {"message": "Prefill stored", "prefill": prefill}

    @router.get("/quotations/get-prefill/{quotation_id}")
    async def get_conversion_prefill(quotation_id: str, authorization: str = Header(...)):
        """Retrieve stored quotation prefill data."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        doc = await db.quotation_prefills.find_one(
            {"sellerId": ObjectId(seller_id), "quotationId": ObjectId(quotation_id)},
            {"_id": 0, "prefill": 1}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="No prefill data found")
        return {"prefill": doc["prefill"]}

    # ── MARK CONVERTED (called after invoice is created) ──
    @router.post("/quotations/{quotation_id}/mark-converted")
    async def mark_quotation_converted(quotation_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        result = await db.quotations.update_one(
            {"_id": ObjectId(quotation_id), "sellerId": ObjectId(seller_id)},
            {"$set": {"convertedToInvoice": True, "status": "converted", "updatedAt": datetime.now(timezone.utc)}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Quotation not found")
        # Cleanup prefill
        await db.quotation_prefills.delete_one({"sellerId": ObjectId(seller_id), "quotationId": ObjectId(quotation_id)})
        return {"message": "Quotation marked as converted"}

    # ── SYNC OFFLINE ──
    @router.post("/quotations/sync-offline")
    async def sync_offline_quotation(data: QuotationCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        buyer = await db.seller_buyers.find_one({"_id": ObjectId(data.buyerId), "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        seller_state = (seller_user or {}).get("profile", {}).get("state", "")
        gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"
        pos = data.placeOfSupply or buyer.get("state", "")

        q_items, subtotal, cgst, sgst, igst, total_gst, grand_total, round_off = await build_quotation_items(
            data.items, seller_id, seller_state, pos, gst_enabled
        )

        q_number = await get_next_quotation_number(seller_id)
        now = datetime.now(timezone.utc)
        doc = {
            "quotationNumber": q_number, "sellerId": ObjectId(seller_id),
            "buyerId": ObjectId(data.buyerId), "date": now, "validityDays": data.validityDays,
            "items": q_items, "subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst,
            "gst": total_gst, "total": grand_total, "roundOff": round_off,
            "status": "draft", "notes": data.notes, "termsAndConditions": data.termsAndConditions or "",
            "placeOfSupply": pos, "convertedToInvoice": False, "offlineSynced": True,
            "createdBy": str(user["_id"]), "createdAt": now, "updatedAt": now,
        }
        result = await db.quotations.insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.info(f"Offline quotation synced → {q_number}")
        return {"message": "Offline quotation synced", "quotation": serialize_doc(doc)}

    return router
