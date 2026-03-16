"""
Business Tools Home Dashboard Router
Provides summary widgets and quick chart data for the home page.
"""

from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from utils.permissions import authenticate_user, resolve_seller_id

logger = logging.getLogger(__name__)


def init_home_router(db, verify_token_func):
    router = APIRouter(tags=["Business Tools Home"])

    async def get_current_user(authorization: str):
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user):
        return resolve_seller_id(user)

    @router.get("/home/summary")
    async def get_home_summary(authorization: str = Header(...)):
        """Summary widget data for Business Tools Home."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        seller_oid = ObjectId(seller_id)

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_products = await db.sellerListings.count_documents({
            "sellerId": seller_oid, "status": {"$in": ["active", "paused"]}
        })

        low_stock_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$in": ["active", "paused"]}, "minStock": {"$gt": 0}}},
            {"$match": {"$expr": {"$lt": ["$stock", "$minStock"]}}},
            {"$count": "count"}
        ]
        low_stock_result = await db.sellerListings.aggregate(low_stock_pipeline).to_list(1)
        low_stock_items = low_stock_result[0]["count"] if low_stock_result else 0

        pending_pos = await db.purchase_orders.count_documents({
            "sellerId": seller_oid, "status": {"$in": ["pending", "sent"]}
        })

        total_suppliers = await db.seller_suppliers.count_documents({"sellerId": seller_oid})

        today_sales_pipeline = [
            {"$match": {"sellerId": seller_oid, "createdAt": {"$gte": today_start}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}}
        ]
        today_result = await db.invoices.aggregate(today_sales_pipeline).to_list(1)
        today_sales = round(today_result[0]["total"], 2) if today_result else 0
        today_count = today_result[0]["count"] if today_result else 0

        revenue_pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        rev_result = await db.invoices.aggregate(revenue_pipeline).to_list(1)
        total_revenue = round(rev_result[0]["total"], 2) if rev_result else 0

        return {
            "totalProducts": total_products,
            "lowStockItems": low_stock_items,
            "pendingPOs": pending_pos,
            "totalSuppliers": total_suppliers,
            "todaySales": today_sales,
            "todaySalesCount": today_count,
            "totalRevenue": total_revenue,
        }

    @router.get("/home/charts")
    async def get_home_charts(authorization: str = Header(...)):
        """Quick chart data for Business Tools Home."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        seller_oid = ObjectId(seller_id)

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # 1. Sales Trend (last 30 days) - from invoices
        sales_pipeline = [
            {"$match": {"sellerId": seller_oid, "createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "total": {"$sum": "$total"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        sales_data = await db.invoices.aggregate(sales_pipeline).to_list(31)
        sales_trend = [{"date": r["_id"], "amount": round(r["total"], 2), "orders": r["count"]} for r in sales_data]

        # 2. Purchase Trend (last 30 days) - from purchase_orders
        purchase_pipeline = [
            {"$match": {"sellerId": seller_oid, "createdAt": {"$gte": thirty_days_ago}, "status": {"$ne": "cancelled"}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "amount": {"$sum": "$totalAmount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        purchase_data = await db.purchase_orders.aggregate(purchase_pipeline).to_list(31)
        purchase_trend = [{"date": r["_id"], "amount": round(r["amount"], 2), "orders": r["count"]} for r in purchase_data]

        # 3. Top Selling Products (by invoice quantity)
        top_products_pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.productName",
                "totalQty": {"$sum": "$items.quantity"},
                "totalRevenue": {"$sum": "$items.total"},
            }},
            {"$sort": {"totalQty": -1}},
            {"$limit": 8},
        ]
        top_products_data = await db.invoices.aggregate(top_products_pipeline).to_list(8)
        top_products = [{"name": r["_id"] or "Unknown", "quantity": r["totalQty"], "revenue": round(r["totalRevenue"], 2)} for r in top_products_data]

        # 4. Stock Distribution by Category
        stock_pipeline = [
            {"$match": {"sellerId": seller_oid, "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "product"}},
            {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "categories", "localField": "product.categoryId", "foreignField": "_id", "as": "cat"}},
            {"$unwind": {"path": "$cat", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": {"$ifNull": ["$cat.name", "Uncategorized"]},
                "totalStock": {"$sum": {"$ifNull": ["$stock", 0]}},
                "productCount": {"$sum": 1},
            }},
            {"$sort": {"totalStock": -1}},
        ]
        stock_data = await db.sellerListings.aggregate(stock_pipeline).to_list(20)
        stock_distribution = [{"category": r["_id"], "stock": r["totalStock"], "products": r["productCount"]} for r in stock_data]

        return {
            "salesTrend": sales_trend,
            "purchaseTrend": purchase_trend,
            "topProducts": top_products,
            "stockDistribution": stock_distribution,
        }

    return router
