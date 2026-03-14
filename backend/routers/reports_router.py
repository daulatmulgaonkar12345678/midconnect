"""
Reports Router - Sales analytics from invoice + inventory data
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from models.business_tools import Permission

logger = logging.getLogger(__name__)


def init_reports_router(db, verify_token_func):
    router = APIRouter(tags=["Reports"])

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

    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    @router.get("/reports/sales-summary")
    async def sales_summary(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        period: str = "monthly"  # monthly, quarterly
    ):
        """Get sales summary from invoices."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate)
        end = parse_date(endDate)

        if not start:
            start = now - timedelta(days=365)
        if not end:
            end = now

        match_stage = {
            "sellerId": ObjectId(seller_id),
            "createdAt": {"$gte": start, "$lte": end},
            "status": {"$in": ["draft", "sent", "paid"]}
        }

        # Group by period
        if period == "quarterly":
            group_id = {
                "year": {"$year": "$createdAt"},
                "quarter": {"$ceil": {"$divide": [{"$month": "$createdAt"}, 3]}}
            }
        else:
            group_id = {
                "year": {"$year": "$createdAt"},
                "month": {"$month": "$createdAt"}
            }

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": group_id,
                "totalSales": {"$sum": "$total"},
                "totalGst": {"$sum": "$gst"},
                "invoiceCount": {"$sum": 1},
                "avgInvoiceValue": {"$avg": "$total"}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1} if period == "monthly" else {"_id.year": 1, "_id.quarter": 1}}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(100)

        # Overall totals
        totals_pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "totalRevenue": {"$sum": "$total"},
                "totalGst": {"$sum": "$gst"},
                "invoiceCount": {"$sum": 1},
                "avgInvoiceValue": {"$avg": "$total"},
                "paidAmount": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, "$total", 0]}},
                "paidCount": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}}
            }}
        ]
        totals = await db.invoices.aggregate(totals_pipeline).to_list(1)
        overall = totals[0] if totals else {"totalRevenue": 0, "totalGst": 0, "invoiceCount": 0, "avgInvoiceValue": 0, "paidAmount": 0, "paidCount": 0}
        if "_id" in overall:
            del overall["_id"]

        # Format period data
        period_data = []
        for r in results:
            entry = {
                "year": r["_id"]["year"],
                "totalSales": round(r["totalSales"], 2),
                "totalGst": round(r["totalGst"], 2),
                "invoiceCount": r["invoiceCount"],
                "avgInvoiceValue": round(r.get("avgInvoiceValue", 0), 2)
            }
            if period == "quarterly":
                entry["quarter"] = r["_id"]["quarter"]
                entry["label"] = f"Q{r['_id']['quarter']} {r['_id']['year']}"
            else:
                entry["month"] = r["_id"]["month"]
                months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                entry["label"] = f"{months[r['_id']['month']]} {r['_id']['year']}"
            period_data.append(entry)

        return {
            "overall": {k: round(v, 2) if isinstance(v, float) else v for k, v in overall.items()},
            "periods": period_data
        }

    @router.get("/reports/product-sales")
    async def product_sales(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        limit: int = 20
    ):
        """Top selling products from invoice items."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate) or now

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lte": end}, "status": {"$in": ["draft", "sent", "paid"]}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "totalQuantity": {"$sum": "$items.quantity"},
                "totalRevenue": {"$sum": "$items.total"},
                "invoiceCount": {"$sum": 1}
            }},
            {"$sort": {"totalRevenue": -1}},
            {"$limit": limit}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(limit)
        products = [{"productName": r["_id"], "totalQuantity": r["totalQuantity"], "totalRevenue": round(r["totalRevenue"], 2), "invoiceCount": r["invoiceCount"]} for r in results]

        return {"products": products}

    @router.get("/reports/inventory-status")
    async def inventory_status(authorization: str = Header(...)):
        """Current inventory overview."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "prod"}},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "productName": "$prod.name",
                "stock": {"$ifNull": ["$stock", 0]},
                "lowStockAlert": {"$ifNull": ["$lowStockAlert", 10]},
                "isLowStock": {"$lte": [{"$ifNull": ["$stock", 0]}, {"$ifNull": ["$lowStockAlert", 10]}]},
                "sku": 1
            }}
        ]

        items = await db.sellerListings.aggregate(pipeline).to_list(200)

        total_items = len(items)
        low_stock = sum(1 for i in items if i.get("isLowStock"))
        out_of_stock = sum(1 for i in items if i.get("stock", 0) == 0)
        total_stock = sum(i.get("stock", 0) for i in items)

        return {
            "summary": {"totalItems": total_items, "lowStock": low_stock, "outOfStock": out_of_stock, "totalStockUnits": total_stock},
            "items": serialize_doc(items)
        }

    @router.get("/reports/top-buyers")
    async def top_buyers(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        limit: int = 10
    ):
        """Top buyers by invoice total."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate) or now

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lte": end}, "status": {"$in": ["draft", "sent", "paid"]}}},
            {"$group": {
                "_id": "$buyerId",
                "totalSpent": {"$sum": "$total"},
                "invoiceCount": {"$sum": 1},
                "lastInvoiceDate": {"$max": "$createdAt"}
            }},
            {"$sort": {"totalSpent": -1}},
            {"$limit": limit}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(limit)

        buyers = []
        for r in results:
            buyer = await db.seller_buyers.find_one({"_id": r["_id"]})
            buyers.append({
                "buyerId": str(r["_id"]),
                "buyerName": buyer.get("buyerName", "Unknown") if buyer else "Unknown",
                "company": buyer.get("company", "") if buyer else "",
                "totalSpent": round(r["totalSpent"], 2),
                "invoiceCount": r["invoiceCount"],
                "lastInvoiceDate": r["lastInvoiceDate"].isoformat() if r.get("lastInvoiceDate") else None
            })

        return {"buyers": buyers}

    @router.get("/reports/profit-summary")
    async def profit_summary(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        period: str = "monthly"
    ):
        """Profit summary: revenue - cost per period from invoice items."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate) or now

        match_stage = {
            "sellerId": ObjectId(seller_id),
            "createdAt": {"$gte": start, "$lte": end},
            "status": {"$in": ["draft", "sent", "paid"]}
        }

        if period == "quarterly":
            group_id = {
                "year": {"$year": "$createdAt"},
                "quarter": {"$ceil": {"$divide": [{"$month": "$createdAt"}, 3]}}
            }
        else:
            group_id = {
                "year": {"$year": "$createdAt"},
                "month": {"$month": "$createdAt"}
            }

        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$items"},
            {"$group": {
                "_id": group_id,
                "revenue": {"$sum": "$items.total"},
                "cost": {"$sum": {"$multiply": [
                    {"$ifNull": ["$items.purchase_price", 0]},
                    "$items.quantity"
                ]}},
                "invoiceCount": {"$sum": 1},
                "totalQuantity": {"$sum": "$items.quantity"}
            }},
            {"$addFields": {
                "profit": {"$subtract": ["$revenue", "$cost"]},
                "margin": {"$cond": [
                    {"$gt": ["$revenue", 0]},
                    {"$multiply": [{"$divide": [{"$subtract": ["$revenue", "$cost"]}, "$revenue"]}, 100]},
                    0
                ]}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1} if period == "monthly" else {"_id.year": 1, "_id.quarter": 1}}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(100)

        # Overall totals
        totals_pipeline = [
            {"$match": match_stage},
            {"$unwind": "$items"},
            {"$group": {
                "_id": None,
                "totalRevenue": {"$sum": "$items.total"},
                "totalCost": {"$sum": {"$multiply": [
                    {"$ifNull": ["$items.purchase_price", 0]},
                    "$items.quantity"
                ]}},
                "totalQuantity": {"$sum": "$items.quantity"},
                "invoiceCount": {"$sum": 1}
            }}
        ]
        totals = await db.invoices.aggregate(totals_pipeline).to_list(1)
        overall = totals[0] if totals else {"totalRevenue": 0, "totalCost": 0, "totalQuantity": 0, "invoiceCount": 0}
        if "_id" in overall:
            del overall["_id"]
        overall["totalProfit"] = round(overall.get("totalRevenue", 0) - overall.get("totalCost", 0), 2)
        rev = overall.get("totalRevenue", 0)
        overall["profitMargin"] = round((overall["totalProfit"] / rev * 100) if rev > 0 else 0, 2)

        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        period_data = []
        for r in results:
            entry = {
                "year": r["_id"]["year"],
                "revenue": round(r["revenue"], 2),
                "cost": round(r["cost"], 2),
                "profit": round(r["profit"], 2),
                "margin": round(r.get("margin", 0), 2),
                "invoiceCount": r["invoiceCount"],
                "totalQuantity": r["totalQuantity"]
            }
            if period == "quarterly":
                entry["quarter"] = r["_id"]["quarter"]
                entry["label"] = f"Q{r['_id']['quarter']} {r['_id']['year']}"
            else:
                entry["month"] = r["_id"]["month"]
                entry["label"] = f"{months[r['_id']['month']]} {r['_id']['year']}"
            period_data.append(entry)

        return {"overall": {k: round(v, 2) if isinstance(v, float) else v for k, v in overall.items()}, "periods": period_data}

    @router.get("/reports/product-profit")
    async def product_profit(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        limit: int = 20
    ):
        """Per-product profit breakdown from invoice items."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate) or now

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lte": end}, "status": {"$in": ["draft", "sent", "paid"]}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "totalQuantity": {"$sum": "$items.quantity"},
                "totalRevenue": {"$sum": "$items.total"},
                "totalCost": {"$sum": {"$multiply": [
                    {"$ifNull": ["$items.purchase_price", 0]},
                    "$items.quantity"
                ]}},
                "invoiceCount": {"$sum": 1}
            }},
            {"$addFields": {
                "profit": {"$subtract": ["$totalRevenue", "$totalCost"]},
                "margin": {"$cond": [
                    {"$gt": ["$totalRevenue", 0]},
                    {"$multiply": [{"$divide": [{"$subtract": ["$totalRevenue", "$totalCost"]}, "$totalRevenue"]}, 100]},
                    0
                ]}
            }},
            {"$sort": {"profit": -1}},
            {"$limit": limit}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(limit)
        products = [{
            "productName": r["_id"],
            "totalQuantity": r["totalQuantity"],
            "totalRevenue": round(r["totalRevenue"], 2),
            "totalCost": round(r["totalCost"], 2),
            "profit": round(r["profit"], 2),
            "margin": round(r.get("margin", 0), 2),
            "invoiceCount": r["invoiceCount"]
        } for r in results]

        return {"products": products}

    @router.get("/reports/inventory-value")
    async def inventory_value(authorization: str = Header(...)):
        """Inventory value report: purchase_price * stock for each listing."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "prod"}},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "productName": "$prod.name",
                "productType": {"$ifNull": ["$productType", "single"]},
                "stock": {"$ifNull": ["$stock", 0]},
                "purchase_price": {"$ifNull": ["$purchase_price", 0]},
                "selling_price": {"$ifNull": ["$selling_price", 0]},
                "stockValue": {"$multiply": [{"$ifNull": ["$purchase_price", 0]}, {"$ifNull": ["$stock", 0]}]},
                "potentialRevenue": {"$multiply": [{"$ifNull": ["$selling_price", 0]}, {"$ifNull": ["$stock", 0]}]}
            }},
            {"$sort": {"stockValue": -1}}
        ]

        items = await db.sellerListings.aggregate(pipeline).to_list(200)
        total_value = sum(i.get("stockValue", 0) for i in items)
        total_potential = sum(i.get("potentialRevenue", 0) for i in items)
        total_stock = sum(i.get("stock", 0) for i in items)

        return {
            "summary": {
                "totalInventoryValue": round(total_value, 2),
                "totalPotentialRevenue": round(total_potential, 2),
                "totalPotentialProfit": round(total_potential - total_value, 2),
                "totalItems": len(items),
                "totalStockUnits": total_stock
            },
            "items": serialize_doc(items)
        }

    return router
