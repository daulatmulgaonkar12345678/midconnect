"""
SELLER PERFORMANCE SERVICE - Phase A.3
======================================

Deterministic, rule-based seller performance scoring.
No AI. No randomness. Explainable scoring.

30-day rolling window only.
Recent behavior drives marketplace visibility.

Score Formula (100 points total):
- Response Speed: 25 pts
- Acceptance Rate: 30 pts
- Expiry Rate: 15 pts (inverse - lower is better)
- Subscription Tier: 10 pts
- Lead Consistency: 10 pts
- Quote Completion: 10 pts

Tiers:
- Elite Performer: 90-100
- Strong Performer: 70-89
- Good Performer: 50-69
- Needs Improvement: 30-49
- At Risk: 0-29
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# Score weights (deterministic)
SCORE_WEIGHTS = {
    "responseSpeed": 25,
    "acceptanceRate": 30,
    "expiryRate": 15,
    "subscriptionTier": 10,
    "leadConsistency": 10,
    "quoteCompletion": 10
}

# Subscription tier scores
TIER_SCORES = {
    "enterprise": 10,
    "pro": 7,
    "trial": 4,
    "free": 2
}

# Performance tiers
PERFORMANCE_TIERS = [
    {"min": 90, "name": "Elite Performer", "color": "#10b981"},
    {"min": 70, "name": "Strong Performer", "color": "#3b82f6"},
    {"min": 50, "name": "Good Performer", "color": "#f59e0b"},
    {"min": 30, "name": "Needs Improvement", "color": "#f97316"},
    {"min": 0, "name": "At Risk", "color": "#ef4444"}
]

# Response time benchmarks (hours)
RESPONSE_TIME_BENCHMARKS = {
    "excellent": 2,      # < 2 hours = 25 pts
    "good": 6,           # < 6 hours = 20 pts
    "average": 12,       # < 12 hours = 15 pts
    "slow": 24,          # < 24 hours = 10 pts
    "poor": 48           # < 48 hours = 5 pts
}


class SellerPerformanceService:
    """
    Seller Performance Intelligence Service.
    
    Computes deterministic performance scores based on:
    - 30-day rolling window
    - Rule-based scoring
    - Explainable metrics
    
    Sellers see:
    - Own metrics
    - Marketplace averages (anonymized)
    
    Sellers DO NOT see:
    - Other seller data
    - Ranking weights
    - Competitor metrics
    """
    
    def __init__(self, db):
        self.db = db
        self._marketplace_cache = None
        self._cache_time = None
    
    async def calculate_seller_score(
        self,
        seller_id: ObjectId,
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive seller performance score.
        
        Returns:
        {
            score: 78,
            tier: "Strong Performer",
            tierColor: "#3b82f6",
            metrics: { ... },
            breakdown: { ... },
            suggestions: [ ... ],
            marketplaceAvg: { ... }
        }
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Get raw metrics
        metrics = await self._get_raw_metrics(seller_id, thirty_days_ago)
        
        # Calculate score components
        breakdown = self._calculate_score_breakdown(metrics)
        
        # Total score
        total_score = sum(breakdown.values())
        
        # Determine tier
        tier_info = self._get_tier(total_score)
        
        # Get marketplace averages (for comparison)
        marketplace_avg = await self._get_marketplace_averages(thirty_days_ago)
        
        result = {
            "sellerId": str(seller_id),
            "timestamp": now.isoformat(),
            "period": "30 days",
            "score": round(total_score, 1),
            "maxScore": 100,
            "tier": tier_info["name"],
            "tierColor": tier_info["color"],
            "metrics": metrics,
            "breakdown": {
                "responseSpeed": {
                    "score": breakdown["responseSpeed"],
                    "maxScore": SCORE_WEIGHTS["responseSpeed"],
                    "metric": f"{metrics['avgResponseTimeHours']:.1f} hours"
                },
                "acceptanceRate": {
                    "score": breakdown["acceptanceRate"],
                    "maxScore": SCORE_WEIGHTS["acceptanceRate"],
                    "metric": f"{metrics['acceptanceRate']:.1f}%"
                },
                "expiryRate": {
                    "score": breakdown["expiryRate"],
                    "maxScore": SCORE_WEIGHTS["expiryRate"],
                    "metric": f"{metrics['expiryRate']:.1f}%"
                },
                "subscriptionTier": {
                    "score": breakdown["subscriptionTier"],
                    "maxScore": SCORE_WEIGHTS["subscriptionTier"],
                    "metric": metrics["subscriptionPlan"]
                },
                "leadConsistency": {
                    "score": breakdown["leadConsistency"],
                    "maxScore": SCORE_WEIGHTS["leadConsistency"],
                    "metric": f"{metrics['leadUtilization']:.1f}%"
                },
                "quoteCompletion": {
                    "score": breakdown["quoteCompletion"],
                    "maxScore": SCORE_WEIGHTS["quoteCompletion"],
                    "metric": f"{metrics['quoteCompletionRate']:.1f}%"
                }
            },
            "marketplaceAverage": marketplace_avg
        }
        
        # Add improvement suggestions
        if include_suggestions:
            result["suggestions"] = self._generate_suggestions(
                metrics, breakdown, marketplace_avg, tier_info
            )
        
        return result
    
    async def _get_raw_metrics(
        self,
        seller_id: ObjectId,
        since: datetime
    ) -> Dict[str, Any]:
        """
        Get raw performance metrics for seller.
        """
        # Response time and inquiry stats
        inquiry_pipeline = [
            {"$match": {
                "sellerId": seller_id,
                "createdAt": {"$gte": since}
            }},
            {"$facet": {
                "total": [{"$count": "count"}],
                "accepted": [
                    {"$match": {"status": "accepted"}},
                    {"$count": "count"}
                ],
                "responseTime": [
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
                        "avgHours": {"$avg": "$hours"},
                        "minHours": {"$min": "$hours"},
                        "maxHours": {"$max": "$hours"}
                    }}
                ]
            }}
        ]
        
        inquiry_result = await self.db.inquiries.aggregate(inquiry_pipeline).to_list(1)
        inquiry_data = inquiry_result[0] if inquiry_result else {}
        
        total_inquiries = self._extract_count(inquiry_data.get("total", []))
        accepted_inquiries = self._extract_count(inquiry_data.get("accepted", []))
        
        response_data = inquiry_data.get("responseTime", [{}])[0] if inquiry_data.get("responseTime") else {}
        avg_response = response_data.get("avgHours", 0) if response_data else 0
        
        # Quote stats
        quote_pipeline = [
            {"$match": {
                "sellerId": seller_id,
                "createdAt": {"$gte": since}
            }},
            {"$facet": {
                "total": [{"$count": "count"}],
                "byStatus": [
                    {"$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }}
                ],
                "values": [
                    {"$group": {
                        "_id": None,
                        "totalValue": {"$sum": "$totalPrice"},
                        "avgValue": {"$avg": "$totalPrice"}
                    }}
                ]
            }}
        ]
        
        quote_result = await self.db.quotes.aggregate(quote_pipeline).to_list(1)
        quote_data = quote_result[0] if quote_result else {}
        
        total_quotes = self._extract_count(quote_data.get("total", []))
        status_counts = {r["_id"]: r["count"] for r in quote_data.get("byStatus", [])}
        value_data = quote_data.get("values", [{}])[0] if quote_data.get("values") else {}
        
        # Subscription status
        subscription = await self.db.subscriptions.find_one({
            "userId": seller_id,
            "status": {"$in": ["active", "trial"]}
        })
        
        plan = "free"
        if subscription:
            plan = subscription.get("planName", "free")
        
        # Lead limit (for utilization)
        lead_limits = {"free": 5, "trial": 50, "pro": -1, "enterprise": -1}
        lead_limit = lead_limits.get(plan, 5)
        lead_utilization = 0
        if lead_limit > 0:
            lead_utilization = (accepted_inquiries / lead_limit) * 100
        elif accepted_inquiries > 0:
            lead_utilization = 100  # Unlimited plan, has activity
        
        # Calculate rates
        acceptance_rate = (status_counts.get("accepted", 0) / total_quotes * 100) if total_quotes > 0 else 0
        expiry_rate = (status_counts.get("expired", 0) / total_quotes * 100) if total_quotes > 0 else 0
        rejection_rate = (status_counts.get("rejected", 0) / total_quotes * 100) if total_quotes > 0 else 0
        
        # Quote completion rate (leads that got quotes)
        quote_completion_rate = (total_quotes / accepted_inquiries * 100) if accepted_inquiries > 0 else 0
        
        return {
            "totalInquiries": total_inquiries,
            "acceptedInquiries": accepted_inquiries,
            "avgResponseTimeHours": avg_response,
            "totalQuotes": total_quotes,
            "acceptedQuotes": status_counts.get("accepted", 0),
            "rejectedQuotes": status_counts.get("rejected", 0),
            "expiredQuotes": status_counts.get("expired", 0),
            "acceptanceRate": acceptance_rate,
            "expiryRate": expiry_rate,
            "rejectionRate": rejection_rate,
            "quoteCompletionRate": min(100, quote_completion_rate),  # Cap at 100%
            "totalQuoteValue": value_data.get("totalValue", 0) if value_data else 0,
            "avgQuoteValue": value_data.get("avgValue", 0) if value_data else 0,
            "subscriptionPlan": plan,
            "leadLimit": lead_limit,
            "leadUtilization": min(100, lead_utilization)
        }
    
    def _calculate_score_breakdown(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate score for each component.
        Deterministic, rule-based scoring.
        """
        breakdown = {}
        
        # 1. Response Speed (25 pts)
        avg_response = metrics.get("avgResponseTimeHours", 999)
        if avg_response <= RESPONSE_TIME_BENCHMARKS["excellent"]:
            breakdown["responseSpeed"] = 25
        elif avg_response <= RESPONSE_TIME_BENCHMARKS["good"]:
            breakdown["responseSpeed"] = 20
        elif avg_response <= RESPONSE_TIME_BENCHMARKS["average"]:
            breakdown["responseSpeed"] = 15
        elif avg_response <= RESPONSE_TIME_BENCHMARKS["slow"]:
            breakdown["responseSpeed"] = 10
        elif avg_response <= RESPONSE_TIME_BENCHMARKS["poor"]:
            breakdown["responseSpeed"] = 5
        else:
            breakdown["responseSpeed"] = 0
        
        # No data = neutral score
        if metrics.get("acceptedInquiries", 0) == 0:
            breakdown["responseSpeed"] = 12.5  # Half points for new sellers
        
        # 2. Acceptance Rate (30 pts)
        acceptance_rate = metrics.get("acceptanceRate", 0)
        if acceptance_rate >= 80:
            breakdown["acceptanceRate"] = 30
        elif acceptance_rate >= 60:
            breakdown["acceptanceRate"] = 24
        elif acceptance_rate >= 40:
            breakdown["acceptanceRate"] = 18
        elif acceptance_rate >= 20:
            breakdown["acceptanceRate"] = 12
        else:
            breakdown["acceptanceRate"] = 6
        
        # No quotes = neutral
        if metrics.get("totalQuotes", 0) == 0:
            breakdown["acceptanceRate"] = 15
        
        # 3. Expiry Rate (15 pts - inverse)
        expiry_rate = metrics.get("expiryRate", 0)
        if expiry_rate <= 5:
            breakdown["expiryRate"] = 15
        elif expiry_rate <= 10:
            breakdown["expiryRate"] = 12
        elif expiry_rate <= 20:
            breakdown["expiryRate"] = 9
        elif expiry_rate <= 30:
            breakdown["expiryRate"] = 6
        elif expiry_rate <= 40:
            breakdown["expiryRate"] = 3
        else:
            breakdown["expiryRate"] = 0
        
        # No quotes = neutral
        if metrics.get("totalQuotes", 0) == 0:
            breakdown["expiryRate"] = 7.5
        
        # 4. Subscription Tier (10 pts)
        plan = metrics.get("subscriptionPlan", "free")
        breakdown["subscriptionTier"] = TIER_SCORES.get(plan, 2)
        
        # 5. Lead Consistency (10 pts)
        lead_util = metrics.get("leadUtilization", 0)
        if lead_util >= 80:
            breakdown["leadConsistency"] = 10
        elif lead_util >= 60:
            breakdown["leadConsistency"] = 8
        elif lead_util >= 40:
            breakdown["leadConsistency"] = 6
        elif lead_util >= 20:
            breakdown["leadConsistency"] = 4
        else:
            breakdown["leadConsistency"] = 2
        
        # 6. Quote Completion (10 pts)
        completion = metrics.get("quoteCompletionRate", 0)
        if completion >= 90:
            breakdown["quoteCompletion"] = 10
        elif completion >= 70:
            breakdown["quoteCompletion"] = 8
        elif completion >= 50:
            breakdown["quoteCompletion"] = 6
        elif completion >= 30:
            breakdown["quoteCompletion"] = 4
        else:
            breakdown["quoteCompletion"] = 2
        
        # No inquiries = neutral
        if metrics.get("acceptedInquiries", 0) == 0:
            breakdown["quoteCompletion"] = 5
        
        return breakdown
    
    def _get_tier(self, score: float) -> Dict[str, str]:
        """Get performance tier based on score."""
        for tier in PERFORMANCE_TIERS:
            if score >= tier["min"]:
                return tier
        return PERFORMANCE_TIERS[-1]
    
    async def _get_marketplace_averages(
        self,
        since: datetime
    ) -> Dict[str, Any]:
        """
        Get anonymized marketplace averages.
        Cached for 1 hour to reduce load.
        """
        now = datetime.now(timezone.utc)
        
        # Check cache
        if self._marketplace_cache and self._cache_time:
            if (now - self._cache_time).total_seconds() < 3600:
                return self._marketplace_cache
        
        # Calculate marketplace averages
        response_pipeline = [
            {"$match": {
                "status": "accepted",
                "acceptedAt": {"$exists": True},
                "createdAt": {"$gte": since}
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
                "avgResponseHours": {"$avg": "$hours"}
            }}
        ]
        
        response_result = await self.db.inquiries.aggregate(response_pipeline).to_list(1)
        avg_response = response_result[0]["avgResponseHours"] if response_result else 12
        
        # Quote stats
        quote_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        quote_result = await self.db.quotes.aggregate(quote_pipeline).to_list(10)
        status_counts = {r["_id"]: r["count"] for r in quote_result}
        total_quotes = sum(status_counts.values())
        
        avg_acceptance = (status_counts.get("accepted", 0) / total_quotes * 100) if total_quotes > 0 else 50
        avg_expiry = (status_counts.get("expired", 0) / total_quotes * 100) if total_quotes > 0 else 15
        
        self._marketplace_cache = {
            "avgResponseTimeHours": round(avg_response, 1),
            "avgAcceptanceRate": round(avg_acceptance, 1),
            "avgExpiryRate": round(avg_expiry, 1),
            "note": "Based on all active sellers in the last 30 days"
        }
        self._cache_time = now
        
        return self._marketplace_cache
    
    def _generate_suggestions(
        self,
        metrics: Dict[str, Any],
        breakdown: Dict[str, float],
        marketplace_avg: Dict[str, Any],
        tier_info: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable improvement suggestions.
        
        Focus on:
        - Biggest gaps vs marketplace
        - Low-scoring components
        - Path to next tier
        """
        suggestions = []
        
        # Calculate score needed for next tier
        current_score = sum(breakdown.values())
        next_tier = None
        for tier in PERFORMANCE_TIERS:
            if tier["min"] > current_score:
                next_tier = tier
                break
        
        # Response time suggestion
        if breakdown["responseSpeed"] < 20:
            avg_hours = metrics.get("avgResponseTimeHours", 0)
            marketplace_hrs = marketplace_avg.get("avgResponseTimeHours", 12)
            
            if avg_hours > marketplace_hrs:
                suggestions.append({
                    "category": "Response Speed",
                    "priority": "HIGH",
                    "message": f"Your average response time ({avg_hours:.1f}h) is slower than marketplace average ({marketplace_hrs:.1f}h). Aim to respond within 6 hours for better ranking.",
                    "impact": "+5 to +15 score points"
                })
        
        # Acceptance rate suggestion
        if breakdown["acceptanceRate"] < 24:
            acceptance = metrics.get("acceptanceRate", 0)
            if acceptance < 60:
                suggestions.append({
                    "category": "Quote Acceptance",
                    "priority": "HIGH",
                    "message": f"Your quote acceptance rate ({acceptance:.1f}%) is below 60%. Consider competitive pricing and faster delivery times.",
                    "impact": "+6 to +12 score points"
                })
        
        # Expiry rate suggestion
        if breakdown["expiryRate"] < 12:
            expiry = metrics.get("expiryRate", 0)
            if expiry > 10:
                suggestions.append({
                    "category": "Quote Expiry",
                    "priority": "MEDIUM",
                    "message": f"Your expiry rate ({expiry:.1f}%) is above 10%. Follow up with buyers before quotes expire using WhatsApp.",
                    "impact": "+3 to +6 score points"
                })
        
        # Subscription upgrade suggestion
        plan = metrics.get("subscriptionPlan", "free")
        if plan == "free" and current_score >= 50:
            suggestions.append({
                "category": "Subscription",
                "priority": "MEDIUM",
                "message": "Upgrade to Pro plan for unlimited leads and +5 score boost. You're performing well - don't let lead limits hold you back!",
                "impact": "+5 score points + unlimited leads"
            })
        
        # Quote completion suggestion
        if breakdown["quoteCompletion"] < 6:
            completion = metrics.get("quoteCompletionRate", 0)
            if completion < 70:
                suggestions.append({
                    "category": "Quote Completion",
                    "priority": "MEDIUM",
                    "message": f"You're sending quotes for only {completion:.0f}% of accepted leads. Send quotes promptly to improve conversion.",
                    "impact": "+2 to +4 score points"
                })
        
        # Next tier guidance
        if next_tier:
            points_needed = next_tier["min"] - current_score
            suggestions.append({
                "category": "Next Tier",
                "priority": "INFO",
                "message": f"You need {points_needed:.0f} more points to reach '{next_tier['name']}' tier. Focus on your weakest areas above.",
                "impact": f"Unlock '{next_tier['name']}' badge and improved visibility"
            })
        
        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return suggestions[:5]  # Max 5 suggestions
    
    def _extract_count(self, result: list) -> int:
        """Extract count from facet result."""
        if result and len(result) > 0:
            return result[0].get("count", 0)
        return 0
    
    async def get_seller_trend(
        self,
        seller_id: ObjectId,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily performance trend for seller.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)
        
        # Daily quote stats
        pipeline = [
            {"$match": {
                "sellerId": seller_id,
                "createdAt": {"$gte": since}
            }},
            {"$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$createdAt"
                    }
                },
                "quotes": {"$sum": 1},
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                },
                "value": {"$sum": "$totalPrice"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        result = await self.db.quotes.aggregate(pipeline).to_list(days)
        
        return [
            {
                "date": r["_id"],
                "quotes": r["quotes"],
                "accepted": r["accepted"],
                "value": round(r["value"], 2)
            }
            for r in result
        ]


async def get_seller_performance_service(db) -> SellerPerformanceService:
    """Factory function for seller performance service."""
    service = SellerPerformanceService(db)
    return service
