"""
ABUSE MONITORING SERVICE - Phase B.7
====================================

Market Health Monitoring + Abuse Detection

Monitors:
- High expiry sellers (>40%)
- Slow responders (>24 hrs avg)
- Zero conversion sellers
- Suspicious activity
- High complaint reports

Admin can:
- Warn seller
- Suspend seller
- Reduce ranking score manually
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# Abuse thresholds
THRESHOLDS = {
    "high_expiry_rate": 40,       # > 40% expiry rate
    "slow_response_hours": 24,    # > 24 hours avg response
    "min_quotes_for_analysis": 5, # Min quotes to analyze
    "min_leads_for_analysis": 3,  # Min leads to analyze
    "warning_threshold": 3        # Auto-suspend after 3 warnings
}


class AbuseMonitoringService:
    """
    Abuse Monitoring Service.
    
    Detects and reports potential abuse patterns:
    - High expiry sellers
    - Slow responders
    - Zero conversion
    - Suspicious patterns
    
    Provides admin tools for intervention.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_market_health(self) -> Dict[str, Any]:
        """
        Get overall marketplace health metrics.
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Overall quote health
        quote_stats = await self.db.quotes.aggregate([
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                },
                "expired": {
                    "$sum": {"$cond": [{"$eq": ["$status", "expired"]}, 1, 0]}
                },
                "rejected": {
                    "$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}
                }
            }}
        ]).to_list(1)
        
        q_data = quote_stats[0] if quote_stats else {}
        total_quotes = q_data.get("total", 0) or 1
        
        # Seller status counts
        seller_stats = await self.db.users.aggregate([
            {"$match": {"roles": "seller"}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(10)
        
        status_counts = {r["_id"]: r["count"] for r in seller_stats}
        
        # Average response time
        response_stats = await self.db.inquiries.aggregate([
            {"$match": {
                "status": "accepted",
                "acceptedAt": {"$exists": True},
                "createdAt": {"$gte": thirty_days_ago}
            }},
            {"$project": {
                "responseHours": {
                    "$divide": [
                        {"$subtract": ["$acceptedAt", "$createdAt"]},
                        3600000
                    ]
                }
            }},
            {"$group": {
                "_id": None,
                "avgResponse": {"$avg": "$responseHours"},
                "maxResponse": {"$max": "$responseHours"}
            }}
        ]).to_list(1)
        
        resp_data = response_stats[0] if response_stats else {}
        
        return {
            "timestamp": now.isoformat(),
            "period": "30 days",
            "quotes": {
                "total": q_data.get("total", 0),
                "acceptanceRate": round((q_data.get("accepted", 0) / total_quotes * 100), 1),
                "expiryRate": round((q_data.get("expired", 0) / total_quotes * 100), 1),
                "rejectionRate": round((q_data.get("rejected", 0) / total_quotes * 100), 1)
            },
            "sellers": {
                "active": status_counts.get("active", 0) + status_counts.get(None, 0),
                "warned": status_counts.get("warned", 0),
                "suspended": status_counts.get("suspended", 0),
                "banned": status_counts.get("banned", 0)
            },
            "response": {
                "avgResponseHours": round(resp_data.get("avgResponse", 0), 1),
                "maxResponseHours": round(resp_data.get("maxResponse", 0), 1)
            },
            "healthScore": self._calculate_health_score(q_data, resp_data)
        }
    
    def _calculate_health_score(self, quote_data: Dict, response_data: Dict) -> int:
        """
        Calculate marketplace health score (0-100).
        """
        score = 100
        
        total = quote_data.get("total", 0)
        if total == 0:
            return 50  # Neutral for no data
        
        # Deduct for high expiry rate
        expiry_rate = (quote_data.get("expired", 0) / total) * 100
        if expiry_rate > 30:
            score -= 20
        elif expiry_rate > 20:
            score -= 10
        elif expiry_rate > 10:
            score -= 5
        
        # Deduct for low acceptance rate
        acceptance_rate = (quote_data.get("accepted", 0) / total) * 100
        if acceptance_rate < 30:
            score -= 20
        elif acceptance_rate < 50:
            score -= 10
        
        # Deduct for slow response
        avg_response = response_data.get("avgResponse", 0)
        if avg_response > 24:
            score -= 15
        elif avg_response > 12:
            score -= 5
        
        return max(0, min(100, score))
    
    async def get_high_expiry_sellers(
        self,
        threshold: float = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get sellers with high quote expiry rate (>40%).
        """
        if threshold is None:
            threshold = THRESHOLDS["high_expiry_rate"]
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": "$sellerId",
                "totalQuotes": {"$sum": 1},
                "expiredQuotes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "expired"]}, 1, 0]}
                },
                "totalValue": {"$sum": "$totalPrice"}
            }},
            {"$match": {
                "totalQuotes": {"$gte": THRESHOLDS["min_quotes_for_analysis"]}
            }},
            {"$project": {
                "totalQuotes": 1,
                "expiredQuotes": 1,
                "totalValue": 1,
                "expiryRate": {
                    "$multiply": [
                        {"$divide": ["$expiredQuotes", "$totalQuotes"]},
                        100
                    ]
                }
            }},
            {"$match": {"expiryRate": {"$gt": threshold}}},
            {"$sort": {"expiryRate": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.quotes.aggregate(pipeline).to_list(limit)
        
        # Enrich with seller info
        return await self._enrich_seller_results(results, "expiryRate")
    
    async def get_slow_responders(
        self,
        threshold_hours: float = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get sellers with slow response times (>24hrs avg).
        """
        if threshold_hours is None:
            threshold_hours = THRESHOLDS["slow_response_hours"]
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        pipeline = [
            {"$match": {
                "status": "accepted",
                "acceptedAt": {"$exists": True},
                "createdAt": {"$gte": thirty_days_ago}
            }},
            {"$group": {
                "_id": "$sellerId",
                "totalLeads": {"$sum": 1},
                "avgResponseHours": {
                    "$avg": {
                        "$divide": [
                            {"$subtract": ["$acceptedAt", "$createdAt"]},
                            3600000
                        ]
                    }
                },
                "maxResponseHours": {
                    "$max": {
                        "$divide": [
                            {"$subtract": ["$acceptedAt", "$createdAt"]},
                            3600000
                        ]
                    }
                }
            }},
            {"$match": {
                "totalLeads": {"$gte": THRESHOLDS["min_leads_for_analysis"]},
                "avgResponseHours": {"$gt": threshold_hours}
            }},
            {"$sort": {"avgResponseHours": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.inquiries.aggregate(pipeline).to_list(limit)
        
        # Enrich with seller info
        return await self._enrich_seller_results(results, "avgResponseHours")
    
    async def get_zero_conversion_sellers(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get sellers with zero conversion (multiple leads, no accepted quotes).
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Get sellers with quotes but zero acceptance
        pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": "$sellerId",
                "totalQuotes": {"$sum": 1},
                "acceptedQuotes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                }
            }},
            {"$match": {
                "totalQuotes": {"$gte": THRESHOLDS["min_quotes_for_analysis"]},
                "acceptedQuotes": 0
            }},
            {"$sort": {"totalQuotes": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.quotes.aggregate(pipeline).to_list(limit)
        
        # Enrich with seller info
        return await self._enrich_seller_results(results, "totalQuotes")
    
    async def get_suspicious_activity(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Detect suspicious patterns:
        - Very high volume, zero acceptance
        - Rapid status changes
        - Unusual pricing patterns
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        suspicious = []
        
        # Pattern 1: High volume, zero acceptance, fast response (potential fake engagement)
        pattern1 = await self.db.quotes.aggregate([
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": "$sellerId",
                "totalQuotes": {"$sum": 1},
                "acceptedQuotes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                },
                "avgValue": {"$avg": "$totalPrice"}
            }},
            {"$match": {
                "totalQuotes": {"$gte": 10},
                "acceptedQuotes": 0
            }},
            {"$limit": 10}
        ]).to_list(10)
        
        for p in pattern1:
            suspicious.append({
                "sellerId": str(p["_id"]),
                "pattern": "high_volume_zero_conversion",
                "severity": "HIGH",
                "details": {
                    "totalQuotes": p["totalQuotes"],
                    "acceptedQuotes": 0,
                    "avgValue": round(p["avgValue"], 2)
                }
            })
        
        # Pattern 2: Multiple warnings
        warned_sellers = await self.db.users.find({
            "roles": "seller",
            "warnings": {"$exists": True},
            "$expr": {"$gte": [{"$size": "$warnings"}, 2]}
        }).to_list(20)
        
        for s in warned_sellers:
            suspicious.append({
                "sellerId": str(s["_id"]),
                "pattern": "multiple_warnings",
                "severity": "MEDIUM",
                "details": {
                    "warningCount": len(s.get("warnings", [])),
                    "status": s.get("status")
                }
            })
        
        return suspicious[:limit]
    
    async def get_abuse_summary(self) -> Dict[str, Any]:
        """
        Get summary of all abuse indicators.
        """
        high_expiry = await self.get_high_expiry_sellers(limit=10)
        slow_responders = await self.get_slow_responders(limit=10)
        zero_conversion = await self.get_zero_conversion_sellers(limit=10)
        suspicious = await self.get_suspicious_activity(limit=10)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thresholds": THRESHOLDS,
            "alerts": {
                "highExpiry": {
                    "count": len(high_expiry),
                    "sellers": high_expiry
                },
                "slowResponders": {
                    "count": len(slow_responders),
                    "sellers": slow_responders
                },
                "zeroConversion": {
                    "count": len(zero_conversion),
                    "sellers": zero_conversion
                },
                "suspicious": {
                    "count": len(suspicious),
                    "patterns": suspicious
                }
            },
            "totalAlerts": len(high_expiry) + len(slow_responders) + len(zero_conversion) + len(suspicious)
        }
    
    async def _enrich_seller_results(
        self,
        results: List[Dict],
        sort_field: str
    ) -> List[Dict[str, Any]]:
        """
        Enrich aggregation results with seller info.
        """
        if not results:
            return []
        
        seller_ids = [r["_id"] for r in results if r.get("_id")]
        
        sellers = await self.db.users.find(
            {"_id": {"$in": seller_ids}},
            {
                "email": 1,
                "profile.businessName": 1,
                "status": 1,
                "warnings": 1
            }
        ).to_list(100)
        
        seller_map = {str(s["_id"]): s for s in sellers}
        
        enriched = []
        for r in results:
            seller_id = str(r["_id"]) if r.get("_id") else None
            seller = seller_map.get(seller_id, {})
            
            enriched.append({
                "sellerId": seller_id,
                "email": seller.get("email"),
                "businessName": seller.get("profile", {}).get("businessName"),
                "status": seller.get("status", "active"),
                "warningCount": len(seller.get("warnings", [])),
                **{k: v for k, v in r.items() if k != "_id"}
            })
        
        return enriched


async def get_abuse_monitoring_service(db) -> AbuseMonitoringService:
    """Factory function for abuse monitoring service."""
    return AbuseMonitoringService(db)
