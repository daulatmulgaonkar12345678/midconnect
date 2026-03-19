"""
Reports Router - Sales analytics from invoice + inventory data
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from models.business_tools import Permission
from utils.permissions import authenticate_user, resolve_seller_id, require_user_permission

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
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user: dict) -> str:
        return resolve_seller_id(user)

    async def require_permission(user: dict, permission: str):
        return await require_user_permission(db, user, permission)

    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    # Active invoice statuses for reports (all except cancelled)
    REPORT_STATUSES = ["draft", "sent", "viewed", "partially_paid", "paid", "overdue"]

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
            end = now + timedelta(days=1)
        else:
            end = end + timedelta(days=1)

        match_stage = {
            "sellerId": ObjectId(seller_id),
            "createdAt": {"$gte": start, "$lt": end},
            "status": {"$in": REPORT_STATUSES}
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
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lt": end}, "status": {"$in": REPORT_STATUSES}}},
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
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lt": end}, "status": {"$in": REPORT_STATUSES}}},
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
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        match_stage = {
            "sellerId": ObjectId(seller_id),
            "createdAt": {"$gte": start, "$lt": end},
            "status": {"$in": REPORT_STATUSES}
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
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lt": end}, "status": {"$in": REPORT_STATUSES}}},
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

    # ─── OUTSTANDING / RECEIVABLES REPORT ───
    OUTSTANDING_STATUSES = ["sent", "viewed", "partially_paid", "overdue"]
    DEFAULT_PAYMENT_DAYS = 30

    @router.get("/reports/outstanding")
    async def outstanding_report(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        buyerId: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Outstanding receivables with aging buckets."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate)
        end = parse_date(endDate)

        match_stage: dict = {
            "sellerId": ObjectId(seller_id),
            "status": {"$in": OUTSTANDING_STATUSES}
        }
        if start or end:
            date_filter = {}
            if start:
                date_filter["$gte"] = start
            if end:
                date_filter["$lt"] = end + timedelta(days=1)
            match_stage["date"] = date_filter

        if buyerId:
            try:
                match_stage["buyerId"] = ObjectId(buyerId)
            except Exception:
                pass

        # Aggregation: join buyer info, compute aging
        pipeline = [
            {"$match": match_stage},
            {"$lookup": {
                "from": "seller_buyers",
                "localField": "buyerId",
                "foreignField": "_id",
                "as": "buyer"
            }},
            {"$unwind": {"path": "$buyer", "preserveNullAndEmptyArrays": True}},
            {"$addFields": {
                "buyerName": {"$ifNull": ["$buyer.buyerName", "Unknown"]},
                "company": {"$ifNull": ["$buyer.company", ""]},
                "dueDate": {"$add": ["$date", DEFAULT_PAYMENT_DAYS * 24 * 60 * 60 * 1000]},
                "paidAmount": {"$ifNull": ["$totalPaid", 0]},
                "pending": {"$ifNull": ["$pendingAmount", "$total"]}
            }},
            {"$addFields": {
                "daysOverdue": {
                    "$max": [0, {"$divide": [
                        {"$subtract": [now, "$dueDate"]},
                        86400000  # ms per day
                    ]}]
                }
            }},
            {"$addFields": {
                "daysOverdue": {"$floor": "$daysOverdue"},
                "agingBucket": {"$switch": {
                    "branches": [
                        {"case": {"$lte": ["$daysOverdue", 0]}, "then": "current"},
                        {"case": {"$lte": ["$daysOverdue", 30]}, "then": "0-30"},
                        {"case": {"$lte": ["$daysOverdue", 60]}, "then": "31-60"},
                        {"case": {"$lte": ["$daysOverdue", 90]}, "then": "61-90"},
                    ],
                    "default": "90+"
                }},
                "displayStatus": {"$switch": {
                    "branches": [
                        {"case": {"$eq": ["$status", "partially_paid"]}, "then": "Partial"},
                        {"case": {"$eq": ["$status", "paid"]}, "then": "Paid"},
                    ],
                    "default": "Unpaid"
                }}
            }},
            {"$project": {
                "_id": 0,
                "invoiceId": {"$toString": "$_id"},
                "invoiceNumber": 1,
                "buyerId": {"$toString": "$buyerId"},
                "buyerName": 1,
                "company": 1,
                "invoiceDate": "$date",
                "dueDate": 1,
                "totalAmount": "$total",
                "paidAmount": 1,
                "pendingAmount": "$pending",
                "daysOverdue": 1,
                "agingBucket": 1,
                "status": "$displayStatus"
            }},
            {"$sort": {"daysOverdue": -1}}
        ]

        all_items = await db.invoices.aggregate(pipeline).to_list(5000)

        # Summary calculations
        total_receivable = sum(i.get("pendingAmount", 0) for i in all_items)
        overdue_items = [i for i in all_items if i.get("daysOverdue", 0) > 0]
        overdue_amount = sum(i.get("pendingAmount", 0) for i in overdue_items)
        unique_buyers = len(set(i.get("buyerId", "") for i in all_items))

        # Aging bucket breakdown
        buckets = {"current": 0, "0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        bucket_counts = {"current": 0, "0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        for item in all_items:
            b = item.get("agingBucket", "current")
            buckets[b] = buckets.get(b, 0) + item.get("pendingAmount", 0)
            bucket_counts[b] = bucket_counts.get(b, 0) + 1

        # Serialize dates
        for item in all_items:
            if isinstance(item.get("invoiceDate"), datetime):
                item["invoiceDate"] = item["invoiceDate"].isoformat()
            if isinstance(item.get("dueDate"), datetime):
                item["dueDate"] = item["dueDate"].isoformat()

        # Pagination
        total_count = len(all_items)
        start_idx = (page - 1) * limit
        paginated = all_items[start_idx:start_idx + limit]

        return {
            "summary": {
                "totalReceivable": round(total_receivable, 2),
                "overdueAmount": round(overdue_amount, 2),
                "totalBuyers": unique_buyers,
                "totalInvoices": total_count
            },
            "aging": {
                "buckets": {k: round(v, 2) for k, v in buckets.items()},
                "counts": bucket_counts
            },
            "items": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    # ─── PURCHASE REPORT ───
    PURCHASE_STATUSES = ["sent", "confirmed", "partially_received", "received"]

    @router.get("/reports/purchase")
    async def purchase_report(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        supplierId: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Purchase order report for confirmed/received POs."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=30))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        match_stage: dict = {
            "sellerId": ObjectId(seller_id),
            "status": {"$in": PURCHASE_STATUSES},
            "createdAt": {"$gte": start, "$lt": end}
        }
        if supplierId:
            try:
                match_stage["supplierId"] = ObjectId(supplierId)
            except Exception:
                pass

        # Summary aggregation
        summary_pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "totalPurchaseValue": {"$sum": "$totalAmount"},
                "totalQuantity": {"$sum": "$itemCount"},
                "orderCount": {"$sum": 1},
                "suppliers": {"$addToSet": "$supplierId"}
            }}
        ]
        summary_result = await db.purchase_orders.aggregate(summary_pipeline).to_list(1)
        summary = summary_result[0] if summary_result else {}
        total_purchase = summary.get("totalPurchaseValue", 0)
        total_qty = summary.get("totalQuantity", 0)
        order_count = summary.get("orderCount", 0)
        total_suppliers = len(summary.get("suppliers", []))
        avg_order_value = round(total_purchase / order_count, 2) if order_count > 0 else 0

        # Detail query with pagination
        detail_pipeline = [
            {"$match": match_stage},
            {"$project": {
                "_id": 0,
                "poId": {"$toString": "$_id"},
                "poNumber": 1,
                "supplierId": {"$toString": "$supplierId"},
                "supplierName": 1,
                "supplierPhone": {"$ifNull": ["$supplierPhone", ""]},
                "status": 1,
                "totalAmount": 1,
                "itemCount": 1,
                "createdAt": 1,
                "items": 1
            }},
            {"$sort": {"createdAt": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit}
        ]
        items = await db.purchase_orders.aggregate(detail_pipeline).to_list(limit)

        # Serialize dates + items
        for item in items:
            if isinstance(item.get("createdAt"), datetime):
                item["createdAt"] = item["createdAt"].isoformat()
            # Flatten item details for display
            item_names = [it.get("productName", "") for it in (item.get("items") or [])]
            item["productNames"] = ", ".join(filter(None, item_names))
            del item["items"]

        # Count for pagination
        total_count = await db.purchase_orders.count_documents(match_stage)

        return {
            "summary": {
                "totalPurchaseValue": round(total_purchase, 2),
                "totalQuantity": total_qty,
                "totalSuppliers": total_suppliers,
                "orderCount": order_count,
                "avgOrderValue": avg_order_value
            },
            "items": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    # ─── STOCK MOVEMENT REPORT ───

    @router.get("/reports/stock-movement")
    async def stock_movement_report(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        listingId: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Stock movement report with opening/closing stock calculations."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=30))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        seller_oid = ObjectId(seller_id)
        base_match: dict = {"sellerId": seller_oid}
        if listingId:
            try:
                base_match["listingId"] = ObjectId(listingId)
            except Exception:
                pass

        # Use $facet for opening stock + in-range movements in a single query
        pipeline = [
            {"$match": base_match},
            {"$facet": {
                "opening": [
                    {"$match": {"createdAt": {"$lt": start}}},
                    {"$sort": {"createdAt": -1}},
                    {"$group": {
                        "_id": "$listingId",
                        "productName": {"$first": "$productName"},
                        "openingStock": {"$first": "$newStock"}
                    }}
                ],
                "firstInRange": [
                    {"$match": {"createdAt": {"$gte": start, "$lt": end}}},
                    {"$sort": {"createdAt": 1}},
                    {"$group": {
                        "_id": "$listingId",
                        "productName": {"$first": "$productName"},
                        "firstPreviousStock": {"$first": "$previousStock"}
                    }}
                ],
                "movements": [
                    {"$match": {"createdAt": {"$gte": start, "$lt": end}}},
                    {"$group": {
                        "_id": "$listingId",
                        "productName": {"$first": "$productName"},
                        "inward": {"$sum": {"$cond": [
                            {"$in": ["$changeType", ["purchase", "purchase_receipt"]]},
                            {"$abs": "$quantity"}, 0
                        ]}},
                        "outward": {"$sum": {"$cond": [
                            {"$eq": ["$changeType", "sale"]},
                            {"$abs": "$quantity"}, 0
                        ]}},
                        "adjustmentPositive": {"$sum": {"$cond": [
                            {"$and": [
                                {"$in": ["$changeType", ["adjustment", "damage"]]},
                                {"$gt": ["$quantity", 0]}
                            ]},
                            "$quantity", 0
                        ]}},
                        "adjustmentNegative": {"$sum": {"$cond": [
                            {"$and": [
                                {"$in": ["$changeType", ["adjustment", "damage"]]},
                                {"$lt": ["$quantity", 0]}
                            ]},
                            "$quantity", 0
                        ]}},
                        "logCount": {"$sum": 1}
                    }}
                ]
            }}
        ]

        result = await db.inventory_logs.aggregate(pipeline).to_list(1)
        if not result:
            return {
                "summary": {"totalInward": 0, "totalOutward": 0, "netMovement": 0, "totalProducts": 0},
                "items": [],
                "pagination": {"page": page, "limit": limit, "total": 0, "pages": 1}
            }

        data = result[0]
        opening_map = {str(o["_id"]): o for o in data.get("opening", [])}
        first_map = {str(f["_id"]): f for f in data.get("firstInRange", [])}
        movements = data.get("movements", [])

        # Merge all product IDs
        all_product_ids = set()
        for o in data.get("opening", []):
            all_product_ids.add(str(o["_id"]))
        for f in data.get("firstInRange", []):
            all_product_ids.add(str(f["_id"]))
        for m in movements:
            all_product_ids.add(str(m["_id"]))

        movement_map = {str(m["_id"]): m for m in movements}

        items = []
        total_inward = 0
        total_outward = 0
        total_adj = 0

        for pid in all_product_ids:
            opening_data = opening_map.get(pid)
            first_data = first_map.get(pid)
            mov = movement_map.get(pid, {})

            # Determine opening stock
            if opening_data:
                opening_stock = opening_data["openingStock"]
            elif first_data:
                opening_stock = first_data["firstPreviousStock"]
            else:
                opening_stock = 0

            product_name = (
                (mov.get("productName")) or
                (opening_data.get("productName") if opening_data else None) or
                (first_data.get("productName") if first_data else None) or
                "Unknown"
            )

            inward = mov.get("inward", 0)
            outward = mov.get("outward", 0)
            adj_pos = mov.get("adjustmentPositive", 0)
            adj_neg = mov.get("adjustmentNegative", 0)
            adjustment = adj_pos + adj_neg  # adj_neg is already negative

            closing_stock = opening_stock + inward - outward + adjustment

            total_inward += inward
            total_outward += outward
            total_adj += adjustment

            items.append({
                "listingId": pid,
                "productName": product_name,
                "openingStock": opening_stock,
                "inward": inward,
                "outward": outward,
                "adjustment": adjustment,
                "closingStock": closing_stock,
                "logCount": mov.get("logCount", 0)
            })

        # Sort by outward (most active) descending
        items.sort(key=lambda x: x["outward"], reverse=True)

        # Pagination
        total_count = len(items)
        start_idx = (page - 1) * limit
        paginated = items[start_idx:start_idx + limit]

        return {
            "summary": {
                "totalInward": total_inward,
                "totalOutward": total_outward,
                "netMovement": total_inward - total_outward + total_adj,
                "totalProducts": total_count
            },
            "items": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    return router
