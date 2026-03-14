"""
Invoice Router - Create invoices, generate PDFs, manage invoice lifecycle
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
import logging

from models.business_tools import InvoiceCreate, InvoiceStatusUpdate, Permission
from services.invoice_pdf_service import generate_invoice_pdf

logger = logging.getLogger(__name__)


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
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission} required")
        role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
        if not role or permission not in role.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission} required")

    async def get_next_invoice_number(seller_id: str) -> str:
        """Generate next invoice number using seller-based counter."""
        result = await db.users.find_one_and_update(
            {"_id": ObjectId(seller_id)},
            {"$inc": {"invoiceCounter": 1}},
            return_document=True
        )
        counter = result.get("invoiceCounter", 1) if result else 1
        # Use short seller ID for readability
        short_id = seller_id[-6:].upper()
        return f"INV-{short_id}-{counter:04d}"

    @router.get("/invoices")
    async def list_invoices(
        authorization: str = Header(...),
        status: Optional[str] = None,
        buyerId: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        query = {"sellerId": ObjectId(seller_id)}
        if status:
            query["status"] = status
        if buyerId:
            try:
                query["buyerId"] = ObjectId(buyerId)
            except Exception:
                pass

        total = await db.invoices.count_documents(query)
        invoices = await db.invoices.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with buyer name
        for inv in invoices:
            buyer = await db.seller_buyers.find_one({"_id": inv.get("buyerId")})
            inv["buyerName"] = buyer.get("buyerName", "Unknown") if buyer else "Unknown"

        return {"invoices": serialize_doc(invoices), "total": total}

    @router.post("/invoices")
    async def create_invoice(data: InvoiceCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        # Validate buyer exists
        try:
            buyer = await db.seller_buyers.find_one({
                "_id": ObjectId(data.buyerId),
                "sellerId": ObjectId(seller_id)
            })
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        if not buyer:
            raise HTTPException(status_code=400, detail="Buyer not found")

        # Process items and calculate totals
        invoice_items = []
        subtotal = 0

        for item in data.items:
            # Get product name from listings or products
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
                        # Validate stock - handle composite products differently
                        if data.deductStock:
                            if listing.get("productType") == "composite":
                                # For composites, validate component stock
                                cp_id = listing.get("compositeProductId")
                                if cp_id:
                                    components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
                                    for comp in components:
                                        comp_listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
                                        if not comp_listing:
                                            raise HTTPException(status_code=400, detail=f"Component inventory item not found for {product_name}")
                                        required = comp["quantity"] * item.quantity
                                        comp_stock = comp_listing.get("stock", 0)
                                        if comp_stock < required:
                                            comp_prod = await db.products.find_one({"_id": comp_listing.get("productId")})
                                            comp_name = comp_prod.get("name", "Unknown") if comp_prod else "Unknown"
                                            raise HTTPException(
                                                status_code=400,
                                                detail=f"Insufficient stock for component {comp_name} in {product_name}: need {required}, have {comp_stock}"
                                            )
                            else:
                                current_stock = listing.get("stock", 0)
                                if current_stock < item.quantity:
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Insufficient stock for {product_name}: need {item.quantity}, have {current_stock}"
                                    )
                except HTTPException:
                    raise
                except Exception:
                    pass

            line_subtotal = item.price * item.quantity
            gst_amount = round(line_subtotal * item.gstPercent / 100, 2)
            line_total = round(line_subtotal + gst_amount, 2)

            invoice_items.append({
                "productId": item.productId,
                "productName": product_name,
                "quantity": item.quantity,
                "price": item.price,
                "gstPercent": item.gstPercent,
                "gstAmount": gst_amount,
                "total": line_total
            })
            subtotal += line_subtotal

        subtotal = round(subtotal, 2)
        total_gst = round(sum(i["gstAmount"] for i in invoice_items), 2)
        grand_total = round(subtotal + total_gst, 2)

        # Generate invoice number
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
                                # Composite: deduct from component items
                                cp_id = listing.get("compositeProductId")
                                if cp_id:
                                    components = await db.composite_product_items.find({"compositeProductId": cp_id}).to_list(50)
                                    for comp in components:
                                        comp_listing = await db.sellerListings.find_one({"_id": comp["listingId"]})
                                        if comp_listing:
                                            prev_stock = comp_listing.get("stock", 0)
                                            deduct_qty = comp["quantity"] * item["quantity"]
                                            new_stock = max(0, prev_stock - deduct_qty)
                                            await db.sellerListings.update_one(
                                                {"_id": comp["listingId"]},
                                                {"$set": {"stock": new_stock, "updatedAt": now}}
                                            )
                                            comp_prod = await db.products.find_one({"_id": comp_listing.get("productId")})
                                            comp_name = comp_prod.get("name", "Unknown") if comp_prod else "Unknown"
                                            await db.inventory_logs.insert_one({
                                                "sellerId": ObjectId(seller_id),
                                                "listingId": comp["listingId"],
                                                "productName": comp_name,
                                                "changeType": "sale",
                                                "quantity": -deduct_qty,
                                                "previousStock": prev_stock,
                                                "newStock": new_stock,
                                                "note": f"Invoice {invoice_number} (composite: {item['productName']})",
                                                "createdBy": str(user["_id"]),
                                                "createdAt": now
                                            })
                                    # Recalculate composite stock
                                    if composite_router and hasattr(composite_router, 'sync_composite_stock'):
                                        await composite_router.sync_composite_stock(cp_id)
                            else:
                                # Regular listing: deduct directly
                                prev_stock = listing.get("stock", 0)
                                new_stock = max(0, prev_stock - item["quantity"])
                                await db.sellerListings.update_one(
                                    {"_id": ObjectId(item["productId"])},
                                    {"$set": {"stock": new_stock, "updatedAt": now}}
                                )
                                await db.inventory_logs.insert_one({
                                    "sellerId": ObjectId(seller_id),
                                    "listingId": ObjectId(item["productId"]),
                                    "productName": item["productName"],
                                    "changeType": "sale",
                                    "quantity": -item["quantity"],
                                    "previousStock": prev_stock,
                                    "newStock": new_stock,
                                    "note": f"Invoice {invoice_number}",
                                    "createdBy": str(user["_id"]),
                                    "createdAt": now
                                })
                                # Recalculate composites that use this component
                                if composite_router and hasattr(composite_router, 'sync_all_composites_for_component'):
                                    await composite_router.sync_all_composites_for_component(str(item["productId"]))
                    except Exception as e:
                        logger.warning(f"Stock deduction failed for {item['productId']}: {e}")

        # Update buyer totals
        await db.seller_buyers.update_one(
            {"_id": ObjectId(data.buyerId)},
            {"$inc": {"totalOrders": 1, "totalSpent": grand_total}}
        )

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

        return {"invoice": serialize_doc(inv)}

    @router.put("/invoices/{invoice_id}/status")
    async def update_invoice_status(invoice_id: str, data: InvoiceStatusUpdate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.CREATE_INVOICE.value)
        seller_id = await get_seller_id(user)

        if data.status not in ["draft", "sent", "paid", "cancelled"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        try:
            inv_oid = ObjectId(invoice_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        inv = await db.invoices.find_one({"_id": inv_oid, "sellerId": ObjectId(seller_id)})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        await db.invoices.update_one({"_id": inv_oid}, {"$set": {"status": data.status, "updatedAt": datetime.now(timezone.utc)}})
        return {"message": f"Invoice status updated to {data.status}"}

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

        # Get seller info
        seller = await db.users.find_one({"_id": ObjectId(seller_id)})
        if not seller:
            seller = {}
        # Also check sellers collection for extra details
        seller_extra = await db.sellers.find_one({"userId": ObjectId(seller_id)})
        if seller_extra:
            seller.update({k: v for k, v in seller_extra.items() if k not in ("_id",) and v})

        # Get buyer info
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

        await db.invoices.delete_one({"_id": inv_oid})
        return {"message": "Invoice deleted"}

    return router
