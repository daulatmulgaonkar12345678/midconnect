"""
MONTHLY AGGREGATION CRON - Phase A.9
====================================

Nightly cron job to precompute monthly stats.
Avoids heavy runtime aggregations.

Collections created:
- seller_monthly_stats
- product_monthly_stats  
- platform_monthly_stats

Run: Daily at midnight UTC
"""

import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("monthly_aggregation_cron")


async def aggregate_seller_monthly_stats(db):
    """
    Aggregate seller stats for current month.
    Updates seller_monthly_stats collection.
    """
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    # Get all active sellers
    sellers = await db.users.find(
        {"roles": "seller"},
        {"_id": 1}
    ).to_list(10000)
    
    logger.info(f"Aggregating stats for {len(sellers)} sellers...")
    
    for seller in sellers:
        seller_id = seller["_id"]
        
        try:
            # Inquiry stats
            inquiry_stats = await db.inquiries.aggregate([
                {"$match": {
                    "sellerId": seller_id,
                    "createdAt": {"$gte": month_start}
                }},
                {"$facet": {
                    "total": [{"$count": "count"}],
                    "accepted": [
                        {"$match": {"status": "accepted"}},
                        {"$count": "count"}
                    ],
                    "avgResponse": [
                        {"$match": {
                            "status": "accepted",
                            "acceptedAt": {"$exists": True}
                        }},
                        {"$project": {
                            "hours": {
                                "$divide": [
                                    {"$subtract": ["$acceptedAt", "$createdAt"]},
                                    3600000
                                ]
                            }
                        }},
                        {"$group": {
                            "_id": None,
                            "avg": {"$avg": "$hours"}
                        }}
                    ]
                }}
            ]).to_list(1)
            
            inq_data = inquiry_stats[0] if inquiry_stats else {}
            
            # Quote stats
            quote_stats = await db.quotes.aggregate([
                {"$match": {
                    "sellerId": seller_id,
                    "createdAt": {"$gte": month_start}
                }},
                {"$facet": {
                    "total": [{"$count": "count"}],
                    "byStatus": [
                        {"$group": {
                            "_id": "$status",
                            "count": {"$sum": 1},
                            "value": {"$sum": "$totalPrice"}
                        }}
                    ],
                    "whatsapp": [
                        {"$match": {"whatsappRedirectUsed": True}},
                        {"$count": "count"}
                    ]
                }}
            ]).to_list(1)
            
            quote_data = quote_stats[0] if quote_stats else {}
            status_data = {r["_id"]: r for r in quote_data.get("byStatus", [])}
            
            # Build stats document
            stats = {
                "sellerId": seller_id,
                "month": month_key,
                "inquiries": {
                    "total": _extract_count(inq_data.get("total", [])),
                    "accepted": _extract_count(inq_data.get("accepted", [])),
                    "avgResponseHours": (
                        inq_data.get("avgResponse", [{}])[0].get("avg", 0)
                        if inq_data.get("avgResponse") else 0
                    )
                },
                "quotes": {
                    "total": _extract_count(quote_data.get("total", [])),
                    "sent": status_data.get("sent", {}).get("count", 0),
                    "viewed": status_data.get("viewed", {}).get("count", 0),
                    "accepted": status_data.get("accepted", {}).get("count", 0),
                    "rejected": status_data.get("rejected", {}).get("count", 0),
                    "expired": status_data.get("expired", {}).get("count", 0),
                    "whatsappUsed": _extract_count(quote_data.get("whatsapp", []))
                },
                "values": {
                    "totalQuoteValue": sum(s.get("value", 0) for s in status_data.values()),
                    "acceptedValue": status_data.get("accepted", {}).get("value", 0)
                },
                "updatedAt": now
            }
            
            # Upsert
            await db.sellerMonthlyStats.update_one(
                {"sellerId": seller_id, "month": month_key},
                {"$set": stats, "$setOnInsert": {"createdAt": now}},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error aggregating seller {seller_id}: {e}")
            continue
    
    logger.info(f"Seller monthly stats aggregation complete")


async def aggregate_product_monthly_stats(db):
    """
    Aggregate product stats for current month.
    Updates product_monthly_stats collection.
    """
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    # Product inquiry aggregation
    product_pipeline = [
        {"$match": {"createdAt": {"$gte": month_start}}},
        {"$group": {
            "_id": "$productId",
            "productName": {"$first": "$productName"},
            "totalInquiries": {"$sum": 1},
            "acceptedInquiries": {
                "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
            }
        }}
    ]
    
    inquiry_products = await db.inquiries.aggregate(product_pipeline).to_list(1000)
    
    # Product quote aggregation
    quote_pipeline = [
        {"$match": {"createdAt": {"$gte": month_start}}},
        {"$group": {
            "_id": "$productId",
            "totalQuotes": {"$sum": 1},
            "acceptedQuotes": {
                "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
            },
            "expiredQuotes": {
                "$sum": {"$cond": [{"$eq": ["$status", "expired"]}, 1, 0]}
            },
            "totalValue": {"$sum": "$totalPrice"},
            "avgValue": {"$avg": "$totalPrice"}
        }}
    ]
    
    quote_products = await db.quotes.aggregate(quote_pipeline).to_list(1000)
    quote_map = {r["_id"]: r for r in quote_products}
    
    for product in inquiry_products:
        product_id = product["_id"]
        if not product_id:
            continue
            
        quote_data = quote_map.get(product_id, {})
        
        stats = {
            "productId": product_id,
            "productName": product.get("productName", "Unknown"),
            "month": month_key,
            "inquiries": {
                "total": product["totalInquiries"],
                "accepted": product["acceptedInquiries"]
            },
            "quotes": {
                "total": quote_data.get("totalQuotes", 0),
                "accepted": quote_data.get("acceptedQuotes", 0),
                "expired": quote_data.get("expiredQuotes", 0)
            },
            "values": {
                "totalValue": round(quote_data.get("totalValue", 0), 2),
                "avgValue": round(quote_data.get("avgValue", 0), 2)
            },
            "rates": {
                "conversionRate": round(
                    (quote_data.get("acceptedQuotes", 0) / quote_data.get("totalQuotes", 1) * 100)
                    if quote_data.get("totalQuotes", 0) > 0 else 0,
                    2
                ),
                "expiryRate": round(
                    (quote_data.get("expiredQuotes", 0) / quote_data.get("totalQuotes", 1) * 100)
                    if quote_data.get("totalQuotes", 0) > 0 else 0,
                    2
                )
            },
            "updatedAt": now
        }
        
        await db.productMonthlyStats.update_one(
            {"productId": product_id, "month": month_key},
            {"$set": stats, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
    
    logger.info(f"Product monthly stats aggregation complete for {len(inquiry_products)} products")


async def aggregate_platform_monthly_stats(db):
    """
    Aggregate platform-wide stats for current month.
    Updates platform_monthly_stats collection.
    """
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    # User stats
    user_stats = await db.users.aggregate([
        {"$facet": {
            "total": [{"$count": "count"}],
            "sellers": [
                {"$match": {"roles": "seller"}},
                {"$count": "count"}
            ],
            "buyers": [
                {"$match": {"roles": "buyer"}},
                {"$count": "count"}
            ],
            "newThisMonth": [
                {"$match": {"createdAt": {"$gte": month_start}}},
                {"$count": "count"}
            ]
        }}
    ]).to_list(1)
    
    user_data = user_stats[0] if user_stats else {}
    
    # Subscription stats
    sub_stats = await db.subscriptions.aggregate([
        {"$match": {"status": {"$in": ["active", "trial"]}}},
        {"$group": {
            "_id": "$planName",
            "count": {"$sum": 1}
        }}
    ]).to_list(10)
    
    plan_counts = {r["_id"]: r["count"] for r in sub_stats}
    
    # Inquiry stats this month
    inquiry_stats = await db.inquiries.aggregate([
        {"$match": {"createdAt": {"$gte": month_start}}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "accepted": [
                {"$match": {"status": "accepted"}},
                {"$count": "count"}
            ]
        }}
    ]).to_list(1)
    
    inq_data = inquiry_stats[0] if inquiry_stats else {}
    
    # Quote stats this month
    quote_stats = await db.quotes.aggregate([
        {"$match": {"createdAt": {"$gte": month_start}}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "byStatus": [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "value": {"$sum": "$totalPrice"}
                }}
            ]
        }}
    ]).to_list(1)
    
    quote_data = quote_stats[0] if quote_stats else {}
    status_counts = {r["_id"]: r for r in quote_data.get("byStatus", [])}
    
    # Listing stats
    listing_count = await db.sellerListings.count_documents({"isActive": True})
    
    # Build platform stats
    total_quotes = _extract_count(quote_data.get("total", []))
    accepted_quotes = status_counts.get("accepted", {}).get("count", 0)
    
    stats = {
        "month": month_key,
        "users": {
            "total": _extract_count(user_data.get("total", [])),
            "sellers": _extract_count(user_data.get("sellers", [])),
            "buyers": _extract_count(user_data.get("buyers", [])),
            "newThisMonth": _extract_count(user_data.get("newThisMonth", []))
        },
        "subscriptions": {
            "free": max(0, _extract_count(user_data.get("sellers", [])) - sum(plan_counts.values())),
            "trial": plan_counts.get("trial", 0),
            "pro": plan_counts.get("pro", 0),
            "enterprise": plan_counts.get("enterprise", 0)
        },
        "inquiries": {
            "total": _extract_count(inq_data.get("total", [])),
            "accepted": _extract_count(inq_data.get("accepted", []))
        },
        "quotes": {
            "total": total_quotes,
            "sent": status_counts.get("sent", {}).get("count", 0),
            "viewed": status_counts.get("viewed", {}).get("count", 0),
            "accepted": accepted_quotes,
            "rejected": status_counts.get("rejected", {}).get("count", 0),
            "expired": status_counts.get("expired", {}).get("count", 0)
        },
        "values": {
            "totalQuoteValue": sum(s.get("value", 0) for s in status_counts.values()),
            "acceptedValue": status_counts.get("accepted", {}).get("value", 0)
        },
        "rates": {
            "quoteAcceptanceRate": round(
                (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0,
                2
            ),
            "quoteExpiryRate": round(
                (status_counts.get("expired", {}).get("count", 0) / total_quotes * 100)
                if total_quotes > 0 else 0,
                2
            )
        },
        "listings": {
            "active": listing_count
        },
        "updatedAt": now
    }
    
    await db.platformMonthlyStats.update_one(
        {"month": month_key},
        {"$set": stats, "$setOnInsert": {"createdAt": now}},
        upsert=True
    )
    
    logger.info(f"Platform monthly stats aggregation complete for {month_key}")


def _extract_count(result: list) -> int:
    """Extract count from facet result."""
    if result and len(result) > 0:
        return result[0].get("count", 0)
    return 0


async def ensure_indexes(db):
    """Create indexes for monthly stats collections."""
    # Seller monthly stats
    await db.sellerMonthlyStats.create_index(
        [("sellerId", 1), ("month", 1)],
        name="seller_month_unique",
        unique=True
    )
    
    # Product monthly stats
    await db.productMonthlyStats.create_index(
        [("productId", 1), ("month", 1)],
        name="product_month_unique",
        unique=True
    )
    
    # Platform monthly stats
    await db.platformMonthlyStats.create_index(
        [("month", 1)],
        name="platform_month_unique",
        unique=True
    )
    
    logger.info("Monthly stats indexes ensured")


async def run_monthly_aggregation():
    """
    Main aggregation job.
    Run nightly via cron.
    """
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        logger.info("Starting monthly aggregation job...")
        start_time = datetime.now(timezone.utc)
        
        # Ensure indexes
        await ensure_indexes(db)
        
        # Run aggregations
        await aggregate_seller_monthly_stats(db)
        await aggregate_product_monthly_stats(db)
        await aggregate_platform_monthly_stats(db)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Monthly aggregation complete in {duration:.2f}s")
        
        return {
            "success": True,
            "duration": duration
        }
        
    except Exception as e:
        logger.error(f"Monthly aggregation failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    result = asyncio.run(run_monthly_aggregation())
    print(f"Aggregation result: {result}")
