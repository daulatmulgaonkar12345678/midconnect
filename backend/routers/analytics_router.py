"""
Product Analytics Router - Chart data endpoints for supplier prices,
purchase quantities, inventory stock trends, and supplier comparisons.
"""

from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from models.business_tools import Permission

logger = logging.getLogger(__name__)


def init_analytics_router(db, verify_token_func):
    router = APIRouter(tags=["Product Analytics"])

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

    def parse_date_range(period: Optional[str], start_date: Optional[str], end_date: Optional[str]):
        """Parse date range from period shorthand or explicit dates."""
        now = datetime.now(timezone.utc)
        if start_date and end_date:
            try:
                sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                return sd, ed
            except Exception:
                pass
        if period == "7d":
            return now - timedelta(days=7), now
        elif period == "30d":
            return now - timedelta(days=30), now
        elif period == "3m":
            return now - timedelta(days=90), now
        elif period == "6m":
            return now - timedelta(days=180), now
        elif period == "1y":
            return now - timedelta(days=365), now
        return now - timedelta(days=90), now  # default 3 months

    def get_group_format(start: datetime, end: datetime):
        """Decide grouping granularity based on date range."""
        days = (end - start).days
        if days <= 31:
            return "%Y-%m-%d", "day"
        return "%Y-%m", "month"

    # ==========================================
    # PRODUCT LIST (for dropdown)
    # ==========================================

    @router.get("/analytics/products")
    async def get_analytics_products(authorization: str = Header(...)):
        """Get seller's products for analytics dropdown."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "pd"}},
            {"$unwind": {"path": "$pd", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "listingId": "$_id",
                "productName": "$pd.name",
                "sku": {"$ifNull": ["$sku", ""]},
                "stock": {"$ifNull": ["$stock", 0]},
                "minStock": {"$ifNull": ["$minStock", 0]},
            }},
            {"$sort": {"productName": 1}}
        ]
        items = await db.sellerListings.aggregate(pipeline).to_list(500)
        return {"products": [{"listingId": str(i["listingId"]), "productName": i.get("productName", ""), "sku": i.get("sku", ""), "stock": i.get("stock", 0), "minStock": i.get("minStock", 0)} for i in items]}

    # ==========================================
    # 1. SUPPLIER PRICE TREND (Line Chart)
    # ==========================================

    @router.get("/analytics/price-trend")
    async def get_price_trend(
        authorization: str = Header(...),
        listing_id: str = Query(...),
        period: Optional[str] = "3m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Price trend per supplier over time for a product."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        sd, ed = parse_date_range(period, start_date, end_date)
        fmt, _ = get_group_format(sd, ed)

        listing_oid = ObjectId(listing_id)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": sd, "$lte": ed}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_oid}},
            {"$lookup": {"from": "seller_suppliers", "localField": "supplierId", "foreignField": "_id", "as": "sup"}},
            {"$unwind": {"path": "$sup", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": {
                    "period": {"$dateToString": {"format": fmt, "date": "$createdAt"}},
                    "supplierId": "$supplierId"
                },
                "supplierName": {"$first": "$sup.supplierName"},
                "avgRate": {"$avg": "$items.rate"},
                "minRate": {"$min": "$items.rate"},
                "maxRate": {"$max": "$items.rate"},
            }},
            {"$sort": {"_id.period": 1}},
        ]

        results = await db.purchase_orders.aggregate(pipeline).to_list(500)

        # Group by supplier for multi-line chart
        suppliers_map: dict = {}
        for r in results:
            sid = str(r["_id"]["supplierId"])
            if sid not in suppliers_map:
                suppliers_map[sid] = {"supplierName": r.get("supplierName", "Unknown"), "data": []}
            suppliers_map[sid]["data"].append({
                "period": r["_id"]["period"],
                "avgRate": round(r["avgRate"], 2),
                "minRate": round(r["minRate"], 2),
                "maxRate": round(r["maxRate"], 2),
            })

        return {"suppliers": list(suppliers_map.values())}

    # ==========================================
    # 2. PURCHASE QUANTITY TREND (Bar Chart)
    # ==========================================

    @router.get("/analytics/purchase-trend")
    async def get_purchase_trend(
        authorization: str = Header(...),
        listing_id: str = Query(...),
        period: Optional[str] = "3m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Purchase quantity over time for a product."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        sd, ed = parse_date_range(period, start_date, end_date)
        fmt, _ = get_group_format(sd, ed)

        listing_oid = ObjectId(listing_id)

        pipeline = [
            {"$match": {"sellerId": ObjectId(seller_id), "createdAt": {"$gte": sd, "$lte": ed}, "status": {"$ne": "cancelled"}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_oid}},
            {"$group": {
                "_id": {"$dateToString": {"format": fmt, "date": "$createdAt"}},
                "totalQuantity": {"$sum": "$items.quantity"},
                "totalAmount": {"$sum": "$items.total"},
                "orderCount": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]

        results = await db.purchase_orders.aggregate(pipeline).to_list(500)

        return {"data": [{"period": r["_id"], "quantity": r["totalQuantity"], "amount": round(r["totalAmount"], 2), "orders": r["orderCount"]} for r in results]}

    # ==========================================
    # 3. INVENTORY STOCK TREND (Line Chart)
    # ==========================================

    @router.get("/analytics/stock-trend")
    async def get_stock_trend(
        authorization: str = Header(...),
        listing_id: str = Query(...),
        period: Optional[str] = "3m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Stock level changes over time from inventory logs."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        sd, ed = parse_date_range(period, start_date, end_date)

        listing_oid = ObjectId(listing_id)

        # Get individual log entries to show stock movement
        logs = await db.inventory_logs.find({
            "sellerId": ObjectId(seller_id),
            "listingId": listing_oid,
            "createdAt": {"$gte": sd, "$lte": ed}
        }).sort("createdAt", 1).to_list(500)

        data = []
        for log in logs:
            data.append({
                "date": log["createdAt"].isoformat() if isinstance(log["createdAt"], datetime) else str(log["createdAt"]),
                "stock": log.get("newStock", 0),
                "change": log.get("quantity", 0),
                "type": log.get("changeType", ""),
                "note": log.get("note", ""),
            })

        # Also get current stock as latest point
        listing = await db.sellerListings.find_one({"_id": listing_oid})
        current_stock = listing.get("stock", 0) if listing else 0
        min_stock = listing.get("minStock", 0) if listing else 0

        return {"data": data, "currentStock": current_stock, "minStock": min_stock}

    # ==========================================
    # 4. SUPPLIER PRICE COMPARISON (Bar Chart)
    # ==========================================

    @router.get("/analytics/supplier-comparison")
    async def get_supplier_comparison(
        authorization: str = Header(...),
        listing_id: str = Query(...)
    ):
        """Compare supplier rates for a product."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        listing_oid = ObjectId(listing_id)

        sp_items = await db.supplier_products.find({
            "sellerId": ObjectId(seller_id),
            "listingId": listing_oid
        }).to_list(100)

        suppliers = []
        min_rate = float('inf')
        for sp in sp_items:
            supplier = await db.seller_suppliers.find_one({"_id": sp["supplierId"]})
            if supplier:
                rate = sp["rate"]
                if rate < min_rate:
                    min_rate = rate
                suppliers.append({
                    "supplierId": str(supplier["_id"]),
                    "supplierName": supplier.get("supplierName", "Unknown"),
                    "rate": rate,
                })

        # Mark best price
        for s in suppliers:
            s["isBestPrice"] = s["rate"] == min_rate and len(suppliers) > 1

        suppliers.sort(key=lambda x: x["rate"])
        return {"suppliers": suppliers}

    # ==========================================
    # ANALYTICS SUMMARY
    # ==========================================

    @router.get("/analytics/summary")
    async def get_analytics_summary(
        authorization: str = Header(...),
        listing_id: str = Query(...)
    ):
        """Quick summary stats for a product."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        listing_oid = ObjectId(listing_id)
        seller_oid = ObjectId(seller_id)

        # Total POs for this product
        po_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$ne": "cancelled"}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_oid}},
            {"$group": {
                "_id": None,
                "totalOrders": {"$sum": 1},
                "totalQty": {"$sum": "$items.quantity"},
                "totalSpend": {"$sum": "$items.total"},
                "avgRate": {"$avg": "$items.rate"},
            }}
        ]
        po_stats = await db.purchase_orders.aggregate(po_pipeline).to_list(1)
        po_stat = po_stats[0] if po_stats else {"totalOrders": 0, "totalQty": 0, "totalSpend": 0, "avgRate": 0}

        # Supplier count
        sp_count = await db.supplier_products.count_documents({"sellerId": seller_oid, "listingId": listing_oid})

        # Current stock
        listing = await db.sellerListings.find_one({"_id": listing_oid})
        current_stock = listing.get("stock", 0) if listing else 0
        min_stock = listing.get("minStock", 0) if listing else 0

        return {
            "totalOrders": po_stat.get("totalOrders", 0),
            "totalQuantity": po_stat.get("totalQty", 0),
            "totalSpend": round(po_stat.get("totalSpend", 0), 2),
            "avgRate": round(po_stat.get("avgRate", 0), 2),
            "supplierCount": sp_count,
            "currentStock": current_stock,
            "minStock": min_stock,
        }

    return router
