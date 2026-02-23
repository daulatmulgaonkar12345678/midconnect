"""
QUOTE EXPIRY CRON JOB - PHASE 6
===============================

Hourly cron job to expire quotes past their validity date.

Per spec:
- If status = sent or viewed AND validityDate < now
- Then status = expired
- Notify both parties (future: email/push)
- Prevent acceptance if expired
"""

import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("quote_expiry_cron")


async def run_expiry_job():
    """
    Main expiry job function.
    
    Called hourly by cron or can be triggered manually via admin endpoint.
    """
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        now = datetime.now(timezone.utc)
        
        # Find and expire quotes
        result = await db.quotes.update_many(
            {
                "status": {"$in": ["sent", "viewed"]},
                "validityDate": {"$lt": now}
            },
            {"$set": {
                "status": "expired",
                "updatedAt": now
            }}
        )
        
        expired_count = result.modified_count
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} quotes")
            
            # Track analytics
            await db.quoteAnalytics.insert_one({
                "event": "quotes_expired_batch",
                "data": {
                    "count": expired_count,
                    "timestamp": now.isoformat()
                },
                "createdAt": now
            })
            
            # Update monthly stats for affected sellers
            expired_quotes = await db.quotes.find({
                "status": "expired",
                "updatedAt": {"$gte": now.replace(second=0, microsecond=0)}
            }).to_list(1000)
            
            seller_ids = set()
            for q in expired_quotes:
                seller_id = q.get("sellerId")
                if seller_id:
                    seller_ids.add(seller_id)
            
            month_key = f"{now.year}-{now.month:02d}"
            
            for seller_id in seller_ids:
                await db.sellerMonthlyStats.update_one(
                    {"sellerId": seller_id, "month": month_key},
                    {
                        "$inc": {"quotesExpired": 1},
                        "$set": {"updatedAt": now},
                        "$setOnInsert": {"createdAt": now}
                    },
                    upsert=True
                )
            
            # TODO: Send notifications to buyers and sellers
            # For now, just log the action
            logger.info(f"Updated stats for {len(seller_ids)} sellers")
        else:
            logger.info("No quotes to expire")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"Expiry job failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    # Run the job
    expired = asyncio.run(run_expiry_job())
    print(f"Expired {expired} quotes")
