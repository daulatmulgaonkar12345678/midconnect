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
    OUTSTANDING_STATUSES = ["sent", "viewed", "partially_paid", "overdue"]

    # ─── REPORTS OVERVIEW (lightweight dashboard widget) ───

    @router.get("/reports/overview")
    async def reports_overview(authorization: str = Header(...)):
        """Lightweight aggregation for the Business Insights dashboard widget."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        seller_oid = ObjectId(seller_id)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Run all aggregations in parallel-ish (sequential but lightweight)
        # 1. Outstanding totals
        outstanding_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$in": OUTSTANDING_STATUSES}}},
            {"$group": {
                "_id": None,
                "totalOutstanding": {"$sum": {"$ifNull": ["$pendingAmount", "$total"]}},
                "count": {"$sum": 1}
            }}
        ]
        outstanding_result = await db.invoices.aggregate(outstanding_pipeline).to_list(1)
        outstanding = outstanding_result[0] if outstanding_result else {}

        # 2. Overdue 90+ days
        cutoff_90 = now - timedelta(days=90 + 30)  # invoice date + 30 day payment = 120 days ago
        overdue_count = await db.invoices.count_documents({
            "sellerId": seller_oid,
            "status": {"$in": OUTSTANDING_STATUSES},
            "date": {"$lt": cutoff_90}
        })

        # 3. Low stock count
        low_stock_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": "active"}},
            {"$match": {"$expr": {"$lte": ["$stock", {"$ifNull": ["$lowStockAlert", 10]}]}}},
            {"$count": "count"}
        ]
        low_stock_result = await db.sellerListings.aggregate(low_stock_pipeline).to_list(1)
        low_stock_count = low_stock_result[0]["count"] if low_stock_result else 0

        # 4. Top product this month
        top_product_pipeline = [
            {"$match": {
                "sellerId": seller_oid,
                "createdAt": {"$gte": month_start},
                "status": {"$in": REPORT_STATUSES}
            }},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "qtySold": {"$sum": "$items.quantity"},
                "revenue": {"$sum": "$items.total"}
            }},
            {"$sort": {"revenue": -1}},
            {"$limit": 1}
        ]
        top_product_result = await db.invoices.aggregate(top_product_pipeline).to_list(1)
        top_product = top_product_result[0] if top_product_result else None

        # 5. This month sales
        monthly_pipeline = [
            {"$match": {
                "sellerId": seller_oid,
                "createdAt": {"$gte": month_start},
                "status": {"$in": REPORT_STATUSES}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}}
        ]
        monthly_result = await db.invoices.aggregate(monthly_pipeline).to_list(1)
        this_month = monthly_result[0] if monthly_result else {}

        # 6. Last month sales (for growth %)
        prev_pipeline = [
            {"$match": {
                "sellerId": seller_oid,
                "createdAt": {"$gte": prev_month_start, "$lt": month_start},
                "status": {"$in": REPORT_STATUSES}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        prev_result = await db.invoices.aggregate(prev_pipeline).to_list(1)
        last_month_total = prev_result[0]["total"] if prev_result else 0

        this_month_total = this_month.get("total", 0)
        growth = round(((this_month_total - last_month_total) / last_month_total * 100) if last_month_total > 0 else 0, 1)

        return {
            "totalOutstanding": round(outstanding.get("totalOutstanding", 0), 2),
            "outstandingCount": outstanding.get("count", 0),
            "overdueInvoices": overdue_count,
            "lowStockCount": low_stock_count,
            "topProduct": {
                "name": top_product["_id"] if top_product else None,
                "qtySold": top_product["qtySold"] if top_product else 0,
                "revenue": round(top_product["revenue"], 2) if top_product else 0
            },
            "monthlySales": round(this_month_total, 2),
            "monthlyInvoiceCount": this_month.get("count", 0),
            "growthPercentage": growth
        }

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
        """Top selling products from invoice items, with HSN and GST for CA accounting."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        # Build productName → hsnCode map from sellerListings
        hsn_pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id)}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "prod"}},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {"productName": "$prod.name", "hsnCode": 1}}
        ]
        listings = await db.sellerListings.aggregate(hsn_pipeline).to_list(500)
        hsn_map = {}
        for ls in listings:
            name = ls.get("productName")
            hsn = ls.get("hsnCode")
            if name and hsn:
                hsn_map[name] = hsn

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": start, "$lt": end}, "status": {"$in": REPORT_STATUSES}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "totalQuantity": {"$sum": "$items.quantity"},
                "totalRevenue": {"$sum": "$items.total"},
                "totalGst": {"$sum": {"$ifNull": ["$items.gstAmount", 0]}},
                "gstPercent": {"$first": {"$ifNull": ["$items.gstPercent", 0]}},
                "invoiceCount": {"$sum": 1}
            }},
            {"$sort": {"totalRevenue": -1}},
            {"$limit": limit}
        ]

        results = await db.invoices.aggregate(pipeline).to_list(limit)
        products = []
        for r in results:
            name = r["_id"] or "Unknown"
            revenue = round(r["totalRevenue"], 2)
            gst = round(r["totalGst"], 2)
            taxable = round(revenue - gst, 2)
            products.append({
                "productName": name,
                "hsnCode": hsn_map.get(name, ""),
                "totalQuantity": r["totalQuantity"],
                "taxableValue": taxable,
                "gstPercent": r["gstPercent"],
                "totalGst": gst,
                "totalRevenue": revenue,
                "invoiceCount": r["invoiceCount"]
            })

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

    # ─── BUYER LEDGER REPORT ───

    @router.get("/reports/buyer-ledger")
    async def buyer_ledger(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        buyerId: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Buyer ledger: aggregated sales, payments, pending per buyer."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        match_stage: dict = {
            "sellerId": ObjectId(seller_id),
            "createdAt": {"$gte": start, "$lt": end},
            "status": {"$in": REPORT_STATUSES}
        }
        if buyerId:
            try:
                match_stage["buyerId"] = ObjectId(buyerId)
            except Exception:
                pass

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$buyerId",
                "totalSales": {"$sum": "$total"},
                "totalPaid": {"$sum": {"$ifNull": ["$totalPaid", 0]}},
                "totalPending": {"$sum": {"$ifNull": ["$pendingAmount", "$total"]}},
                "invoiceCount": {"$sum": 1},
                "lastInvoiceDate": {"$max": "$createdAt"},
                "lastPaymentDate": {"$max": {"$cond": [
                    {"$gt": [{"$ifNull": ["$totalPaid", 0]}, 0]},
                    "$updatedAt",
                    None
                ]}}
            }},
            {"$sort": {"totalSales": -1}}
        ]

        all_results = await db.invoices.aggregate(pipeline).to_list(5000)

        # Enrich with buyer info - batch lookup
        buyer_ids = [r["_id"] for r in all_results if r.get("_id")]
        buyers_map = {}
        if buyer_ids:
            buyers = await db.seller_buyers.find({"_id": {"$in": buyer_ids}}).to_list(len(buyer_ids))
            buyers_map = {b["_id"]: b for b in buyers}

        items = []
        total_sales = 0
        total_paid = 0
        total_pending = 0
        for r in all_results:
            buyer = buyers_map.get(r["_id"], {})
            entry = {
                "buyerId": str(r["_id"]) if r.get("_id") else "",
                "buyerName": buyer.get("buyerName", "Unknown"),
                "company": buyer.get("company", ""),
                "totalSales": round(r["totalSales"], 2),
                "totalPaid": round(r["totalPaid"], 2),
                "pendingAmount": round(r["totalPending"], 2),
                "invoiceCount": r["invoiceCount"],
                "lastInvoiceDate": r["lastInvoiceDate"].isoformat() if r.get("lastInvoiceDate") else None,
                "lastPaymentDate": r["lastPaymentDate"].isoformat() if r.get("lastPaymentDate") else None
            }
            items.append(entry)
            total_sales += r["totalSales"]
            total_paid += r["totalPaid"]
            total_pending += r["totalPending"]

        total_count = len(items)
        start_idx = (page - 1) * limit
        paginated = items[start_idx:start_idx + limit]

        return {
            "summary": {
                "totalSales": round(total_sales, 2),
                "totalPaid": round(total_paid, 2),
                "totalPending": round(total_pending, 2),
                "totalBuyers": total_count
            },
            "items": paginated,
            "pagination": {
                "page": page, "limit": limit, "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    @router.get("/reports/buyer-ledger/{buyer_id}/transactions")
    async def buyer_transactions(
        buyer_id: str,
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ):
        """Detailed transaction history for a single buyer."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(400, "Invalid buyer ID")

        match_stage = {
            "sellerId": ObjectId(seller_id),
            "buyerId": buyer_oid,
            "createdAt": {"$gte": start, "$lt": end},
            "status": {"$in": REPORT_STATUSES}
        }

        total_count = await db.invoices.count_documents(match_stage)
        invoices = await db.invoices.find(
            match_stage,
            {"_id": 1, "invoiceNumber": 1, "date": 1, "createdAt": 1,
             "total": 1, "totalPaid": 1, "pendingAmount": 1, "status": 1, "items": 1}
        ).sort("createdAt", -1).skip((page - 1) * limit).limit(limit).to_list(limit)

        buyer = await db.seller_buyers.find_one({"_id": buyer_oid})

        transactions = []
        for inv in invoices:
            item_names = ", ".join(it.get("productName", "") for it in (inv.get("items") or []))
            transactions.append({
                "invoiceId": str(inv["_id"]),
                "invoiceNumber": inv.get("invoiceNumber", ""),
                "date": inv.get("date", inv.get("createdAt", "")).isoformat() if isinstance(inv.get("date", inv.get("createdAt")), datetime) else str(inv.get("date", "")),
                "totalAmount": round(inv.get("total", 0), 2),
                "paidAmount": round(inv.get("totalPaid", 0), 2),
                "pendingAmount": round(inv.get("pendingAmount", inv.get("total", 0)), 2),
                "status": inv.get("status", ""),
                "products": item_names
            })

        return {
            "buyer": {
                "buyerId": buyer_id,
                "buyerName": buyer.get("buyerName", "Unknown") if buyer else "Unknown",
                "company": buyer.get("company", "") if buyer else ""
            },
            "transactions": transactions,
            "pagination": {
                "page": page, "limit": limit, "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    # ─── PRODUCT PERFORMANCE REPORT ───

    @router.get("/reports/product-performance")
    async def product_performance(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Product performance: qty sold, revenue, profit, margin, HSN. Includes top & slow movers."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        # Build productName → hsnCode map
        hsn_pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id)}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "prod"}},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {"productName": "$prod.name", "hsnCode": 1}}
        ]
        listings = await db.sellerListings.aggregate(hsn_pipeline).to_list(500)
        hsn_map = {}
        for ls in listings:
            name = ls.get("productName")
            hsn = ls.get("hsnCode")
            if name and hsn:
                hsn_map[name] = hsn

        pipeline = [
            {"$match": {
                "sellerId": ObjectId(seller_id),
                "createdAt": {"$gte": start, "$lt": end},
                "status": {"$in": REPORT_STATUSES}
            }},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "quantitySold": {"$sum": "$items.quantity"},
                "revenue": {"$sum": "$items.total"},
                "cost": {"$sum": {"$multiply": [
                    {"$ifNull": ["$items.purchase_price", 0]},
                    "$items.quantity"
                ]}},
                "invoiceCount": {"$sum": 1}
            }},
            {"$addFields": {
                "profit": {"$subtract": ["$revenue", "$cost"]},
                "profitPercent": {"$cond": [
                    {"$gt": ["$revenue", 0]},
                    {"$multiply": [{"$divide": [{"$subtract": ["$revenue", "$cost"]}, "$revenue"]}, 100]},
                    0
                ]}
            }},
            {"$sort": {"revenue": -1}}
        ]

        all_items = await db.invoices.aggregate(pipeline).to_list(5000)

        # Summary
        total_revenue = sum(i.get("revenue", 0) for i in all_items)
        total_profit = sum(i.get("profit", 0) for i in all_items)
        total_qty = sum(i.get("quantitySold", 0) for i in all_items)

        products = []
        for r in all_items:
            name = r["_id"] or "Unknown"
            products.append({
                "productName": name,
                "hsnCode": hsn_map.get(name, ""),
                "quantitySold": r["quantitySold"],
                "revenue": round(r["revenue"], 2),
                "profit": round(r["profit"], 2),
                "profitPercent": round(r.get("profitPercent", 0), 1),
                "invoiceCount": r["invoiceCount"]
            })

        # Top 5 selling (by revenue)
        top_selling = products[:5] if products else []
        # Slow moving (bottom 5 by qty, exclude zero)
        by_qty = sorted([p for p in products if p["quantitySold"] > 0], key=lambda x: x["quantitySold"])
        slow_moving = by_qty[:5] if by_qty else []

        total_count = len(products)
        start_idx = (page - 1) * limit
        paginated = products[start_idx:start_idx + limit]

        return {
            "summary": {
                "totalProducts": total_count,
                "totalRevenue": round(total_revenue, 2),
                "totalProfit": round(total_profit, 2),
                "totalQuantitySold": total_qty,
                "avgProfitPercent": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 1)
            },
            "topSelling": top_selling,
            "slowMoving": slow_moving,
            "items": paginated,
            "pagination": {
                "page": page, "limit": limit, "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    # ─── CATEGORY REPORT ───

    @router.get("/reports/category-report")
    async def category_report(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None
    ):
        """Sales, revenue, and profit grouped by product category."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=365))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        # Get all invoice items in range
        pipeline = [
            {"$match": {
                "sellerId": ObjectId(seller_id),
                "createdAt": {"$gte": start, "$lt": end},
                "status": {"$in": REPORT_STATUSES}
            }},
            {"$unwind": "$items"},
            {"$project": {
                "productId": "$items.productId",
                "productName": "$items.productName",
                "quantity": "$items.quantity",
                "revenue": "$items.total",
                "cost": {"$multiply": [
                    {"$ifNull": ["$items.purchase_price", 0]},
                    "$items.quantity"
                ]}
            }}
        ]
        items = await db.invoices.aggregate(pipeline).to_list(10000)

        # Build product → category map
        product_ids = set()
        for item in items:
            pid = item.get("productId")
            if pid and pid != "none" and pid != "None":
                try:
                    product_ids.add(ObjectId(pid))
                except Exception:
                    pass

        category_map = {}  # productId (str) → categoryName
        if product_ids:
            products = await db.products.find(
                {"_id": {"$in": list(product_ids)}},
                {"_id": 1, "categoryName": 1, "categoryId": 1}
            ).to_list(len(product_ids))

            # Get category names for those without categoryName
            cat_ids_to_resolve = set()
            for p in products:
                if p.get("categoryName"):
                    category_map[str(p["_id"])] = p["categoryName"]
                elif p.get("categoryId"):
                    cat_ids_to_resolve.add(p["categoryId"])
                    category_map[str(p["_id"])] = str(p["categoryId"])  # temp

            if cat_ids_to_resolve:
                cats = await db.categories.find(
                    {"_id": {"$in": list(cat_ids_to_resolve)}},
                    {"_id": 1, "name": 1}
                ).to_list(len(cat_ids_to_resolve))
                cat_name_map = {str(c["_id"]): c["name"] for c in cats}
                for pid, cval in category_map.items():
                    if cval in cat_name_map:
                        category_map[pid] = cat_name_map[cval]

        # Group by category
        cat_data: dict = {}
        for item in items:
            pid = item.get("productId")
            cat_name = "Uncategorized"
            if pid and str(pid) in category_map:
                cat_name = category_map[str(pid)]

            if cat_name not in cat_data:
                cat_data[cat_name] = {"totalSales": 0, "revenue": 0, "cost": 0, "itemCount": 0}
            cat_data[cat_name]["totalSales"] += item.get("quantity", 0)
            cat_data[cat_name]["revenue"] += item.get("revenue", 0)
            cat_data[cat_name]["cost"] += item.get("cost", 0)
            cat_data[cat_name]["itemCount"] += 1

        categories = []
        total_revenue = 0
        total_profit = 0
        for name, data in cat_data.items():
            profit = data["revenue"] - data["cost"]
            categories.append({
                "categoryName": name,
                "totalSales": data["totalSales"],
                "revenue": round(data["revenue"], 2),
                "profit": round(profit, 2),
                "profitPercent": round((profit / data["revenue"] * 100) if data["revenue"] > 0 else 0, 1),
                "itemCount": data["itemCount"]
            })
            total_revenue += data["revenue"]
            total_profit += profit

        categories.sort(key=lambda x: x["revenue"], reverse=True)

        return {
            "summary": {
                "totalCategories": len(categories),
                "totalRevenue": round(total_revenue, 2),
                "totalProfit": round(total_profit, 2),
                "topCategory": categories[0]["categoryName"] if categories else "N/A"
            },
            "items": categories
        }

    # ─── LOW STOCK ANALYTICS ───

    @router.get("/reports/low-stock-analytics")
    async def low_stock_analytics(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """Low stock analytics: current stock, consumption rate, times hit low."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        start = parse_date(startDate) or (now - timedelta(days=30))
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        days_in_range = max(1, (end - start).days)
        seller_oid = ObjectId(seller_id)

        # Get all active listings with product names
        listings_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": "active"}},
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "prod"
            }},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "productName": {"$ifNull": ["$prod.name", "Unknown"]},
                "stock": {"$ifNull": ["$stock", 0]},
                "lowStockAlert": {"$ifNull": ["$lowStockAlert", 10]}
            }}
        ]
        listings = await db.sellerListings.aggregate(listings_pipeline).to_list(500)
        listing_map = {str(ls["_id"]): ls for ls in listings}

        # Get consumption (sale logs) in date range per listing
        consumption_pipeline = [
            {"$match": {
                "sellerId": seller_oid,
                "changeType": "sale",
                "createdAt": {"$gte": start, "$lt": end}
            }},
            {"$group": {
                "_id": "$listingId",
                "totalSold": {"$sum": {"$abs": "$quantity"}},
                "logCount": {"$sum": 1}
            }}
        ]
        consumption = await db.inventory_logs.aggregate(consumption_pipeline).to_list(1000)
        consumption_map = {str(c["_id"]): c for c in consumption}

        # Count times stock hit low per listing (newStock <= lowStockAlert)
        # We need per-listing lowStockAlert; do it in Python for correctness
        low_hit_pipeline = [
            {"$match": {
                "sellerId": seller_oid,
                "createdAt": {"$gte": start, "$lt": end}
            }},
            {"$group": {
                "_id": "$listingId",
                "logs": {"$push": {"newStock": "$newStock"}}
            }}
        ]
        low_hit_raw = await db.inventory_logs.aggregate(low_hit_pipeline).to_list(1000)
        low_hit_map = {}
        for entry in low_hit_raw:
            lid = str(entry["_id"])
            threshold = listing_map.get(lid, {}).get("lowStockAlert", 10)
            times = sum(1 for log in entry.get("logs", []) if (log.get("newStock") or 0) <= threshold)
            low_hit_map[lid] = times

        # Build results
        items = []
        total_low_stock = 0
        total_out_of_stock = 0
        for lid, listing in listing_map.items():
            cons = consumption_map.get(lid, {})
            total_sold = cons.get("totalSold", 0)
            avg_consumption = round(total_sold / days_in_range, 2)
            current_stock = listing.get("stock", 0)
            min_stock = listing.get("lowStockAlert", 10)
            is_low = current_stock <= min_stock
            is_out = current_stock == 0

            if is_low:
                total_low_stock += 1
            if is_out:
                total_out_of_stock += 1

            items.append({
                "listingId": lid,
                "productName": listing.get("productName", "Unknown"),
                "minStock": min_stock,
                "currentStock": current_stock,
                "timesHitLow": low_hit_map.get(lid, 0),
                "avgConsumption": avg_consumption,
                "totalSold": total_sold,
                "isLowStock": is_low,
                "isOutOfStock": is_out,
                "daysOfStock": round(current_stock / avg_consumption, 0) if avg_consumption > 0 else 999
            })

        # Sort: out of stock first, then low stock, then by daysOfStock ascending
        items.sort(key=lambda x: (0 if x["isOutOfStock"] else (1 if x["isLowStock"] else 2), x["daysOfStock"]))

        total_count = len(items)
        start_idx = (page - 1) * limit
        paginated = items[start_idx:start_idx + limit]

        return {
            "summary": {
                "totalProducts": total_count,
                "lowStockCount": total_low_stock,
                "outOfStockCount": total_out_of_stock,
                "healthyCount": total_count - total_low_stock
            },
            "items": paginated,
            "pagination": {
                "page": page, "limit": limit, "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    # ─── GST SALES REPORT (GSTR-1 COMPATIBLE) ───

    import re
    GSTIN_REGEX = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$")
    STATE_CODE_MAP = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
        "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
        "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
        "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
        "16": "Tripura", "17": "Meghalaya", "18": "Assam",
        "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
        "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
        "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
        "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
        "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
        "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh (New)",
        "38": "Ladakh", "97": "Other Territory"
    }
    REVERSE_STATE = {}
    for code, name in STATE_CODE_MAP.items():
        REVERSE_STATE[name.lower()] = code

    def _gstin_state_code(gstin: str) -> str:
        """Extract 2-digit state code from GSTIN."""
        if gstin and len(gstin) >= 2 and gstin[:2].isdigit():
            return gstin[:2]
        return ""

    def _validate_gstin(gstin: str) -> bool:
        return bool(gstin and GSTIN_REGEX.match(gstin.strip().upper()))

    def _resolve_state(buyer: dict, gstin: str) -> tuple:
        """Returns (state_code, state_name)."""
        # Priority: GSTIN → buyer.state
        if gstin:
            code = _gstin_state_code(gstin)
            if code in STATE_CODE_MAP:
                return code, STATE_CODE_MAP[code]
        state = buyer.get("state", "") or ""
        code = REVERSE_STATE.get(state.lower().strip(), "")
        return code, state

    def _get_seller_state_code(seller: dict) -> str:
        """Get seller state code from GSTIN or state field."""
        gstin = seller.get("gstNumber", "") or seller.get("gstin", "") or ""
        if gstin:
            code = _gstin_state_code(gstin)
            if code:
                return code
        state = seller.get("state", "") or ""
        return REVERSE_STATE.get(state.lower().strip(), "")

    GST_REPORT_STATUSES = ["sent", "viewed", "partially_paid", "paid", "overdue"]

    @router.get("/reports/gst-report")
    async def gst_sales_report(
        authorization: str = Header(...),
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        buyerId: Optional[str] = None,
        gstType: Optional[str] = None,
        page: int = 1,
        limit: int = 100
    ):
        """GSTR-1 compatible invoice-level GST report."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.VIEW_REPORTS.value)
        seller_id = await get_seller_id(user)

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = parse_date(startDate) or month_start
        end = parse_date(endDate)
        end = (end + timedelta(days=1)) if end else (now + timedelta(days=1))

        seller_oid = ObjectId(seller_id)
        match_stage: dict = {
            "sellerId": seller_oid,
            "status": {"$in": GST_REPORT_STATUSES},
            "createdAt": {"$gte": start, "$lt": end}
        }
        if buyerId:
            try:
                match_stage["buyerId"] = ObjectId(buyerId)
            except Exception:
                pass

        # Get seller info for state comparison
        seller = await db.sellers.find_one({"_id": seller_oid}) or {}
        seller_state_code = _get_seller_state_code(seller)

        # Fetch invoices
        invoices = await db.invoices.find(
            match_stage,
            {"_id": 1, "invoiceNumber": 1, "date": 1, "createdAt": 1, "buyerId": 1,
             "subtotal": 1, "total": 1, "gst": 1, "items": 1, "status": 1}
        ).sort("date", -1).to_list(5000)

        # Batch lookup buyers
        buyer_ids = list(set(inv.get("buyerId") for inv in invoices if inv.get("buyerId")))
        buyers_cursor = await db.seller_buyers.find({"_id": {"$in": buyer_ids}}).to_list(len(buyer_ids))
        buyers_map = {b["_id"]: b for b in buyers_cursor}

        # HSN map
        hsn_pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "prod"}},
            {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
            {"$project": {"productName": "$prod.name", "hsnCode": 1}}
        ]
        hsn_listings = await db.sellerListings.aggregate(hsn_pipeline).to_list(500)
        hsn_map = {}
        for ls in hsn_listings:
            name = ls.get("productName")
            hsn = ls.get("hsnCode")
            if name and hsn:
                hsn_map[name] = hsn

        items = []
        summary_b2b = {"count": 0, "taxable": 0, "gst": 0, "total": 0}
        summary_b2c = {"count": 0, "taxable": 0, "gst": 0, "total": 0}
        hsn_agg: dict = {}  # hsn_code → aggregated data

        for inv in invoices:
            buyer = buyers_map.get(inv.get("buyerId"), {})
            buyer_gstin = (buyer.get("gstNumber", "") or "").strip().upper()
            is_valid_gstin = _validate_gstin(buyer_gstin)
            is_b2b = is_valid_gstin
            supply_code, supply_state = _resolve_state(buyer, buyer_gstin if is_valid_gstin else "")
            is_interstate = bool(seller_state_code and supply_code and seller_state_code != supply_code)

            # Calculate per-item GST split
            inv_taxable = 0
            inv_cgst = 0
            inv_sgst = 0
            inv_igst = 0
            inv_gst_total = 0

            for it in (inv.get("items") or []):
                gst_amt = it.get("gstAmount", 0) or 0
                taxable = (it.get("total", 0) or 0) - gst_amt
                if taxable < 0:
                    taxable = 0

                if is_interstate:
                    igst = gst_amt
                    cgst = sgst = 0
                else:
                    cgst = round(gst_amt / 2, 2)
                    sgst = round(gst_amt - cgst, 2)
                    igst = 0

                inv_taxable += taxable
                inv_cgst += cgst
                inv_sgst += sgst
                inv_igst += igst
                inv_gst_total += gst_amt

                # HSN aggregation
                product_name = it.get("productName", "")
                hsn_code = hsn_map.get(product_name, "")
                qty = it.get("quantity", 0) or 0
                hsn_key = hsn_code or f"_no_hsn_{product_name}"
                if hsn_key not in hsn_agg:
                    hsn_agg[hsn_key] = {
                        "hsnCode": hsn_code,
                        "description": product_name,
                        "uqc": "NOS",
                        "quantity": 0,
                        "taxableValue": 0,
                        "cgst": 0, "sgst": 0, "igst": 0
                    }
                hsn_agg[hsn_key]["quantity"] += qty
                hsn_agg[hsn_key]["taxableValue"] += taxable
                hsn_agg[hsn_key]["cgst"] += cgst
                hsn_agg[hsn_key]["sgst"] += sgst
                hsn_agg[hsn_key]["igst"] += igst
                # Use first product name as description if grouped by HSN
                if hsn_code and hsn_agg[hsn_key]["description"] != product_name:
                    pass  # keep first description

            inv_total = inv.get("total", 0) or 0

            # B2C classification
            b2c_type = ""
            if not is_b2b:
                if inv_total > 250000 and is_interstate:
                    b2c_type = "B2C Large"
                else:
                    b2c_type = "B2C Small"

            place_of_supply = f"{supply_state} ({supply_code})" if supply_code else (supply_state or "N/A")
            inv_date = inv.get("date") or inv.get("createdAt")

            row = {
                "invoiceId": str(inv["_id"]),
                "invoiceNumber": inv.get("invoiceNumber", ""),
                "invoiceDate": inv_date.isoformat() if isinstance(inv_date, datetime) else str(inv_date or ""),
                "buyerName": buyer.get("buyerName", "Unknown"),
                "company": buyer.get("company", ""),
                "buyerGstin": buyer_gstin if is_valid_gstin else "",
                "gstinValid": is_valid_gstin,
                "invoiceType": "Tax Invoice",
                "placeOfSupply": place_of_supply,
                "supplyStateCode": supply_code,
                "isB2B": is_b2b,
                "b2cType": b2c_type,
                "taxableValue": round(inv_taxable, 2),
                "gstRate": (inv.get("items") or [{}])[0].get("gstPercent", 0) if inv.get("items") else 0,
                "cgst": round(inv_cgst, 2),
                "sgst": round(inv_sgst, 2),
                "igst": round(inv_igst, 2),
                "totalInvoiceValue": round(inv_total, 2),
                "status": inv.get("status", "")
            }

            # Filter by gstType
            if gstType == "b2b" and not is_b2b:
                continue
            if gstType == "b2c" and is_b2b:
                continue

            items.append(row)

            # Summary
            bucket = summary_b2b if is_b2b else summary_b2c
            bucket["count"] += 1
            bucket["taxable"] += inv_taxable
            bucket["gst"] += inv_gst_total
            bucket["total"] += inv_total

        # Round HSN aggregation
        hsn_items = []
        for entry in hsn_agg.values():
            hsn_items.append({
                "hsnCode": entry["hsnCode"],
                "description": entry["description"],
                "uqc": entry["uqc"],
                "quantity": entry["quantity"],
                "taxableValue": round(entry["taxableValue"], 2),
                "cgst": round(entry["cgst"], 2),
                "sgst": round(entry["sgst"], 2),
                "igst": round(entry["igst"], 2)
            })
        hsn_items.sort(key=lambda x: x["taxableValue"], reverse=True)

        total_count = len(items)
        start_idx = (page - 1) * limit
        paginated = items[start_idx:start_idx + limit]

        return {
            "summary": {
                "b2b": {k: round(v, 2) if isinstance(v, float) else v for k, v in summary_b2b.items()},
                "b2c": {k: round(v, 2) if isinstance(v, float) else v for k, v in summary_b2c.items()},
                "totalInvoices": summary_b2b["count"] + summary_b2c["count"],
                "totalTaxable": round(summary_b2b["taxable"] + summary_b2c["taxable"], 2),
                "totalGst": round(summary_b2b["gst"] + summary_b2c["gst"], 2),
                "totalValue": round(summary_b2b["total"] + summary_b2c["total"], 2)
            },
            "hsnSummary": hsn_items,
            "items": paginated,
            "pagination": {
                "page": page, "limit": limit, "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 1
            }
        }

    return router
