"""
QUOTE ANALYTICS SERVICE - PHASE 7
=================================

Track and aggregate quote lifecycle metrics per spec:
- Inquiry accepted count
- Quote sent count
- whatsappRedirectUsed count
- Quote viewed rate
- Acceptance rate
- Expiry rate

Store aggregated metrics per seller monthly.
Do NOT yet integrate ranking boost from conversion.
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class QuoteAnalyticsService:
    """
    Analytics service for quote lifecycle tracking.
    
    Metrics tracked:
    - inquiry_accepted: Lead count when inquiry status → accepted
    - quote_sent: When seller creates a quote
    - whatsapp_redirect_used: When seller clicks WhatsApp button
    - quote_viewed: When buyer first views a quote
    - quote_accepted: When buyer accepts a quote
    - quote_rejected: When buyer rejects a quote
    - quote_expired: When quote auto-expires
    
    All metrics stored in quoteAnalytics collection with seller/month aggregation.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create indexes for analytics queries."""
        # Event lookup
        await self.db.quoteAnalytics.create_index(
            [("event", 1), ("createdAt", -1)],
            name="event_time_idx"
        )
        
        # Seller analytics
        await self.db.quoteAnalytics.create_index(
            [("data.sellerId", 1), ("createdAt", -1)],
            name="seller_analytics_idx"
        )
        
        # Monthly aggregation
        await self.db.sellerMonthlyStats.create_index(
            [("sellerId", 1), ("month", 1)],
            name="seller_month_unique",
            unique=True
        )
    
    async def track_event(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Track an analytics event.
        
        Events:
        - inquiry_accepted
        - quote_sent
        - whatsapp_redirect_used
        - quote_viewed
        - quote_accepted
        - quote_rejected
        - quote_expired
        """
        doc = {
            "event": event,
            "data": data,
            "createdAt": datetime.now(timezone.utc)
        }
        
        await self.db.quoteAnalytics.insert_one(doc)
        
        # Update monthly stats if seller is tracked
        seller_id = data.get("sellerId")
        if seller_id:
            await self._update_monthly_stats(seller_id, event)
    
    async def _update_monthly_stats(
        self,
        seller_id: str,
        event: str
    ) -> None:
        """
        Update monthly aggregated stats for seller.
        
        Uses upsert to create or increment counters.
        """
        now = datetime.now(timezone.utc)
        month_key = f"{now.year}-{now.month:02d}"
        
        # Map event to field
        field_map = {
            "inquiry_accepted": "inquiriesAccepted",
            "quote_sent": "quotesSent",
            "whatsapp_redirect_used": "whatsappRedirectsUsed",
            "quote_viewed": "quotesViewed",
            "quote_accepted": "quotesAccepted",
            "quote_rejected": "quotesRejected",
            "quote_expired": "quotesExpired"
        }
        
        field = field_map.get(event)
        if not field:
            return
        
        try:
            seller_oid = ObjectId(seller_id) if isinstance(seller_id, str) else seller_id
        except:
            return
        
        await self.db.sellerMonthlyStats.update_one(
            {"sellerId": seller_oid, "month": month_key},
            {
                "$inc": {field: 1},
                "$set": {"updatedAt": now},
                "$setOnInsert": {"createdAt": now}
            },
            upsert=True
        )
    
    async def get_seller_stats(
        self,
        seller_id: ObjectId,
        months: int = 1
    ) -> Dict[str, Any]:
        """
        Get seller's quote statistics for the specified number of months.
        """
        now = datetime.now(timezone.utc)
        
        # Calculate start month
        if months == 1:
            month_key = f"{now.year}-{now.month:02d}"
            query = {"sellerId": seller_id, "month": month_key}
        else:
            # Build list of month keys
            month_keys = []
            current = now
            for i in range(months):
                month_keys.append(f"{current.year}-{current.month:02d}")
                # Go back one month
                if current.month == 1:
                    current = current.replace(year=current.year - 1, month=12)
                else:
                    current = current.replace(month=current.month - 1)
            query = {"sellerId": seller_id, "month": {"$in": month_keys}}
        
        # Aggregate stats
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "inquiriesAccepted": {"$sum": "$inquiriesAccepted"},
                "quotesSent": {"$sum": "$quotesSent"},
                "whatsappRedirectsUsed": {"$sum": "$whatsappRedirectsUsed"},
                "quotesViewed": {"$sum": "$quotesViewed"},
                "quotesAccepted": {"$sum": "$quotesAccepted"},
                "quotesRejected": {"$sum": "$quotesRejected"},
                "quotesExpired": {"$sum": "$quotesExpired"}
            }}
        ]
        
        result = await self.db.sellerMonthlyStats.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "period": f"Last {months} month(s)",
                "inquiriesAccepted": 0,
                "quotesSent": 0,
                "whatsappRedirectsUsed": 0,
                "quotesViewed": 0,
                "quotesAccepted": 0,
                "quotesRejected": 0,
                "quotesExpired": 0,
                "viewRate": 0,
                "acceptanceRate": 0,
                "expiryRate": 0,
                "whatsappUsageRate": 0
            }
        
        stats = result[0]
        total_sent = stats.get("quotesSent", 0) or 1  # Avoid division by zero
        
        return {
            "period": f"Last {months} month(s)",
            "inquiriesAccepted": stats.get("inquiriesAccepted", 0),
            "quotesSent": stats.get("quotesSent", 0),
            "whatsappRedirectsUsed": stats.get("whatsappRedirectsUsed", 0),
            "quotesViewed": stats.get("quotesViewed", 0),
            "quotesAccepted": stats.get("quotesAccepted", 0),
            "quotesRejected": stats.get("quotesRejected", 0),
            "quotesExpired": stats.get("quotesExpired", 0),
            "viewRate": round((stats.get("quotesViewed", 0) / total_sent) * 100, 1),
            "acceptanceRate": round((stats.get("quotesAccepted", 0) / total_sent) * 100, 1),
            "expiryRate": round((stats.get("quotesExpired", 0) / total_sent) * 100, 1),
            "whatsappUsageRate": round((stats.get("whatsappRedirectsUsed", 0) / total_sent) * 100, 1)
        }
    
    async def get_platform_stats(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get platform-wide quote statistics.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {
                "_id": "$event",
                "count": {"$sum": 1}
            }}
        ]
        
        result = await self.db.quoteAnalytics.aggregate(pipeline).to_list(100)
        
        # Convert to dict
        event_counts = {r["_id"]: r["count"] for r in result}
        
        total_sent = event_counts.get("quote_sent", 0) or 1
        
        return {
            "period": f"Last {days} days",
            "inquiriesAccepted": event_counts.get("inquiry_accepted", 0),
            "quotesSent": event_counts.get("quote_sent", 0),
            "whatsappRedirectsUsed": event_counts.get("whatsapp_redirect_used", 0),
            "quotesViewed": event_counts.get("quote_viewed", 0),
            "quotesAccepted": event_counts.get("quote_accepted", 0),
            "quotesRejected": event_counts.get("quote_rejected", 0),
            "quotesExpired": event_counts.get("quote_expired", 0),
            "viewRate": round((event_counts.get("quote_viewed", 0) / total_sent) * 100, 1),
            "acceptanceRate": round((event_counts.get("quote_accepted", 0) / total_sent) * 100, 1),
            "expiryRate": round((event_counts.get("quote_expired", 0) / total_sent) * 100, 1),
            "whatsappUsageRate": round((event_counts.get("whatsapp_redirect_used", 0) / total_sent) * 100, 1)
        }


async def get_quote_analytics_service(db) -> QuoteAnalyticsService:
    """Factory function for analytics service."""
    service = QuoteAnalyticsService(db)
    return service
