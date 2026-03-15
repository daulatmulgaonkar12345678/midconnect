"""
Purchase Order Router - Create, manage, and send purchase orders to suppliers.
Supports: PDF generation, WhatsApp sending, status tracking, auto PO numbering.
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging
import urllib.parse

from services.po_pdf_service import generate_po_pdf
from models.business_tools import Permission

logger = logging.getLogger(__name__)


class POItemCreate(BaseModel):
    listingId: str
    productName: str
    sku: Optional[str] = ""
    description: Optional[str] = ""
    specification: Optional[str] = ""
    quantity: int = Field(..., gt=0)
    rate: float = Field(..., ge=0)


class POCreate(BaseModel):
    supplierId: str
    items: List[POItemCreate]
    deliveryNotes: Optional[str] = None
    alertId: Optional[str] = None


class POStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(sent|confirmed|received|cancelled)$")


def init_po_router(db, verify_token_func, activity_log_service=None):
    router = APIRouter(tags=["Purchase Orders"])

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
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        decoded = await verify_token_func(token)
        user = await db.users.find_one({"firebaseUid": decoded["uid"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    async def get_seller_id(user):
        if user.get("accountType") == "seller":
            return str(user["_id"])
        elif user.get("accountType") == "employee":
            return str(user.get("employerId", user["_id"]))
        raise HTTPException(status_code=403, detail="Not authorized")

    async def require_permission(user, permission):
        if user.get("accountType") == "seller":
            return
        if user.get("accountType") == "employee":
            role_id = user.get("roleId")
            if role_id:
                role = await db.seller_roles.find_one({"_id": role_id})
                if role and permission in role.get("permissions", []):
                    return
        raise HTTPException(status_code=403, detail="Permission denied")

    async def generate_po_number(seller_id: str) -> str:
        """Generate next PO number: PO-{YEAR}-{SEQUENCE}"""
        year = datetime.now(timezone.utc).year
        seller_oid = ObjectId(seller_id)

        result = await db.po_counters.find_one_and_update(
            {"sellerId": seller_oid, "year": year},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=True
        )
        seq = result["sequence"]
        return f"PO-{year}-{seq:04d}"

    # ==========================================
    # CREATE PURCHASE ORDER
    # ==========================================

    @router.post("/purchase-orders")
    async def create_purchase_order(data: POCreate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        # Validate supplier
        try:
            supplier_oid = ObjectId(data.supplierId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid supplier ID")

        supplier = await db.seller_suppliers.find_one({"_id": supplier_oid, "sellerId": ObjectId(seller_id)})
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        now = datetime.now(timezone.utc)
        po_number = await generate_po_number(seller_id)

        # Build items
        items = []
        total_amount = 0
        for item_data in data.items:
            item_total = item_data.quantity * item_data.rate
            total_amount += item_total
            items.append({
                "listingId": ObjectId(item_data.listingId),
                "productName": item_data.productName,
                "sku": item_data.sku or "",
                "description": item_data.description or "",
                "specification": item_data.specification or "",
                "quantity": item_data.quantity,
                "rate": item_data.rate,
                "total": round(item_total, 2),
            })

        po_doc = {
            "sellerId": ObjectId(seller_id),
            "supplierId": supplier_oid,
            "poNumber": po_number,
            "items": items,
            "totalAmount": round(total_amount, 2),
            "status": "draft",
            "deliveryNotes": data.deliveryNotes,
            "createdBy": str(user["_id"]),
            "createdAt": now,
            "updatedAt": now,
        }

        result = await db.purchase_orders.insert_one(po_doc)
        po_doc["_id"] = result.inserted_id

        # If created from a low stock alert, mark alert as ordered
        if data.alertId:
            try:
                await db.low_stock_alerts.update_one(
                    {"_id": ObjectId(data.alertId), "sellerId": ObjectId(seller_id)},
                    {"$set": {"status": "ordered", "updatedAt": now}}
                )
            except Exception:
                pass

        return {"message": "Purchase order created", "purchaseOrder": serialize_doc(po_doc)}

    # ==========================================
    # LIST PURCHASE ORDERS
    # ==========================================

    @router.get("/purchase-orders")
    async def list_purchase_orders(
        authorization: str = Header(...),
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
        search: Optional[str] = None
    ):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        query: dict = {"sellerId": ObjectId(seller_id)}
        if status:
            query["status"] = status
        if search:
            query["$or"] = [
                {"poNumber": {"$regex": search, "$options": "i"}},
            ]

        total = await db.purchase_orders.count_documents(query)
        pos = await db.purchase_orders.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with supplier name
        enriched = []
        for po in pos:
            doc = serialize_doc(po)
            supplier = await db.seller_suppliers.find_one({"_id": po.get("supplierId")})
            doc["supplierName"] = supplier.get("supplierName", "Unknown") if supplier else "Unknown"
            doc["supplierPhone"] = supplier.get("phone", "") if supplier else ""
            doc["itemCount"] = len(po.get("items", []))
            enriched.append(doc)

        return {"purchaseOrders": enriched, "total": total}

    # ==========================================
    # GET SINGLE PURCHASE ORDER
    # ==========================================

    @router.get("/purchase-orders/{po_id}")
    async def get_purchase_order(po_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            po = await db.purchase_orders.find_one({"_id": ObjectId(po_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid PO ID")
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        supplier = await db.seller_suppliers.find_one({"_id": po.get("supplierId")})
        doc = serialize_doc(po)
        doc["supplierName"] = supplier.get("supplierName", "Unknown") if supplier else "Unknown"
        doc["supplierPhone"] = supplier.get("phone", "") if supplier else ""
        return {"purchaseOrder": doc}

    # ==========================================
    # UPDATE PO STATUS
    # ==========================================

    @router.put("/purchase-orders/{po_id}/status")
    async def update_po_status(po_id: str, data: POStatusUpdate, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            po_oid = ObjectId(po_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid PO ID")

        po = await db.purchase_orders.find_one({"_id": po_oid, "sellerId": ObjectId(seller_id)})
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        await db.purchase_orders.update_one(
            {"_id": po_oid},
            {"$set": {"status": data.status, "updatedAt": datetime.now(timezone.utc)}}
        )

        return {"message": f"PO status updated to {data.status}"}

    # ==========================================
    # GENERATE PO PDF
    # ==========================================

    @router.get("/purchase-orders/{po_id}/pdf")
    async def get_po_pdf(po_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            po = await db.purchase_orders.find_one({"_id": ObjectId(po_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid PO ID")
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # Seller data
        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        gst = (seller_user.get("gst") or {}) if seller_user else {}
        seller_data = {
            "businessName": profile.get("businessName", ""),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "phone": profile.get("phone", ""),
            "email": seller_user.get("email", "") if seller_user else "",
            "gstNumber": gst.get("number", ""),
            "sellerLogoUrl": profile.get("sellerLogoUrl", ""),
        }

        # Supplier data
        supplier = await db.seller_suppliers.find_one({"_id": po.get("supplierId")})
        supplier_data = serialize_doc(supplier) if supplier else {}

        pdf_bytes = generate_po_pdf(po, seller_data, supplier_data)
        po_number = po.get("poNumber", "PO")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{po_number}.pdf"'}
        )

    # ==========================================
    # WHATSAPP LINK FOR PO
    # ==========================================

    @router.get("/purchase-orders/{po_id}/whatsapp-link")
    async def get_po_whatsapp_link(po_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        seller_id = await get_seller_id(user)

        try:
            po = await db.purchase_orders.find_one({"_id": ObjectId(po_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid PO ID")
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        supplier = await db.seller_suppliers.find_one({"_id": po.get("supplierId")})
        if not supplier or not supplier.get("phone"):
            raise HTTPException(status_code=400, detail="Supplier phone not available")

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        business_name = profile.get("businessName", "Seller")

        # Build message
        items = po.get("items", [])
        msg = "Hello,\n\nPlease find the purchase order for the following material.\n\n"
        msg += f"PO Number: {po.get('poNumber', '')}\n\n"

        for item in items:
            msg += f"Product: {item.get('productName', '')}\n"
            if item.get("sku"):
                msg += f"SKU: {item['sku']}\n"
            if item.get("specification"):
                msg += f"\nSpecification:\n{item['specification']}\n"
            if item.get("description"):
                msg += f"\nDescription:\n{item['description']}\n"
            msg += f"\nRequired Quantity: {item.get('quantity', 0)} Nos\n\n"

        msg += "A PDF copy of the purchase order is available for download.\n\n"
        msg += f"Please confirm availability and delivery timeline.\n\nRegards\n{business_name}"

        phone = supplier["phone"].replace(" ", "").replace("-", "").replace("+", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        wa_link = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"

        # Update status to sent if still draft
        if po.get("status") == "draft":
            await db.purchase_orders.update_one(
                {"_id": po["_id"]},
                {"$set": {"status": "sent", "updatedAt": datetime.now(timezone.utc)}}
            )

        return {"whatsappLink": wa_link, "message": msg, "supplierPhone": supplier["phone"]}

    return router
