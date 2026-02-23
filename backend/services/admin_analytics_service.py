"""
ADMIN ANALYTICS SERVICE - Phase A.1
=====================================

Marketplace Control Center Analytics
All metrics computed via aggregation pipelines (SSOT)
No cached fake counts - real-time accuracy

Endpoints:
- GET /admin/analytics/overview
- GET /admin/analytics/revenue
- GET /admin/analytics/quotes
- GET /admin/analytics/leads
- GET /admin/analytics/products

30-day rolling window for time-based metrics.
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Plan pricing constants (for projected MRR)
PLAN_PRICING = {
    "free": 0,
    "trial": 0,
    "pro": 2999,      # INR per month
    "enterprise": 9999  # INR per month
}


class AdminAnalyticsService:
    """
    Admin Analytics Service - SSOT based.
    
    All metrics derived from aggregation pipelines.
    No denormalized counters.
    Optimized with proper indexes.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create indexes for analytics queries."""
        # Users indexes
        await self.db.users.create_index([("roles", 1)], name="roles_idx")
        await self.db.users.create_index([("status", 1)], name="status_idx")
        await self.db.users.create_index([("createdAt", -1)], name="created_at_idx")
        
        # Subscriptions indexes
        await self.db.subscriptions.create_index(
            [("status", 1), ("planName", 1)],
            name="sub_status_plan_idx"
        )
        
        # Inquiries indexes
        await self.db.inquiries.create_index(
            [("status", 1), ("createdAt", -1)],
            name="inq_status_created_idx"
        )
        await self.db.inquiries.create_index(
            [("sellerId", 1), ("status", 1), ("acceptedAt", -1)],
            name="inq_seller_status_idx"
        )
        
        # Quotes indexes
        await self.db.quotes.create_index(
            [("status", 1), ("createdAt", -1)],
            name="quote_status_created_idx"
        )
        await self.db.quotes.create_index(
            [("sellerId", 1), ("status", 1)],
            name="quote_seller_status_idx"
        )
        
        # Listings indexes
        await self.db.sellerListings.create_index(
            [("isActive", 1)],
            name="listing_active_idx"
        )
        
        logger.info("Analytics indexes ensured")
    
    async def get_overview(self) -> Dict[str, Any]:
        """
        GET /admin/analytics/overview
        
        Returns:
        - Total Users
        - Active Sellers (Free, Pro, Enterprise breakdown)
        - Total Inquiries
        - Total Quotes
        - Quote Acceptance Rate
        - Avg Response Time
        - Active Listings
        - Suspended Sellers
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # User counts pipeline
        user_pipeline = [
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
                "suspended": [
                    {"$match": {"status": "suspended"}},
                    {"$count": "count"}
                ],
                "newThisMonth": [
                    {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
                    {"$count": "count"}
                ]
            }}
        ]
        
        user_result = await self.db.users.aggregate(user_pipeline).to_list(1)
        user_stats = user_result[0] if user_result else {}
        
        # Subscription breakdown pipeline
        sub_pipeline = [
            {"$match": {"status": {"$in": ["active", "trial"]}}},
            {"$group": {
                "_id": "$planName",
                "count": {"$sum": 1}
            }}
        ]
        
        sub_result = await self.db.subscriptions.aggregate(sub_pipeline).to_list(100)
        plan_counts = {r["_id"]: r["count"] for r in sub_result}
        
        # Inquiry stats
        inquiry_pipeline = [
            {"$facet": {
                "total": [{"$count": "count"}],
                "pending": [
                    {"$match": {"status": "pending"}},
                    {"$count": "count"}
                ],
                "accepted": [
                    {"$match": {"status": "accepted"}},
                    {"$count": "count"}
                ],
                "thisMonth": [
                    {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
                    {"$count": "count"}
                ]
            }}
        ]
        
        inquiry_result = await self.db.inquiries.aggregate(inquiry_pipeline).to_list(1)
        inquiry_stats = inquiry_result[0] if inquiry_result else {}
        
        # Quote stats
        quote_pipeline = [
            {"$facet": {
                "total": [{"$count": "count"}],
                "sent": [
                    {"$match": {"status": "sent"}},
                    {"$count": "count"}
                ],
                "viewed": [
                    {"$match": {"status": "viewed"}},
                    {"$count": "count"}
                ],
                "accepted": [
                    {"$match": {"status": "accepted"}},
                    {"$count": "count"}
                ],
                "rejected": [
                    {"$match": {"status": "rejected"}},
                    {"$count": "count"}
                ],
                "expired": [
                    {"$match": {"status": "expired"}},
                    {"$count": "count"}
                ]
            }}
        ]
        
        quote_result = await self.db.quotes.aggregate(quote_pipeline).to_list(1)
        quote_stats = quote_result[0] if quote_result else {}
        
        # Response time calculation (accepted inquiries only)
        response_time_pipeline = [
            {"$match": {
                "status": "accepted",
                "acceptedAt": {"$exists": True},
                "createdAt": {"$exists": True}
            }},
            {"$project": {
                "responseTime": {
                    "$divide": [
                        {"$subtract": ["$acceptedAt", "$createdAt"]},
                        3600000  # Convert to hours
                    ]
                }
            }},
            {"$group": {
                "_id": None,
                "avgResponseTime": {"$avg": "$responseTime"}
            }}
        ]
        
        response_result = await self.db.inquiries.aggregate(response_time_pipeline).to_list(1)
        avg_response_time = response_result[0]["avgResponseTime"] if response_result else 0
        
        # Active listings count
        active_listings = await self.db.sellerListings.count_documents({"isActive": True})
        
        # Calculate rates
        total_quotes = self._extract_count(quote_stats.get("total", []))
        accepted_quotes = self._extract_count(quote_stats.get("accepted", []))
        
        total_sellers = self._extract_count(user_stats.get("sellers", []))
        
        # Free sellers = sellers without active paid subscription
        paid_sellers = plan_counts.get("pro", 0) + plan_counts.get("enterprise", 0)
        free_sellers = max(0, total_sellers - paid_sellers - plan_counts.get("trial", 0))
        
        return {
            "timestamp": now.isoformat(),
            "period": "30 days",
            "users": {
                "total": self._extract_count(user_stats.get("total", [])),
                "sellers": total_sellers,
                "buyers": self._extract_count(user_stats.get("buyers", [])),
                "newThisMonth": self._extract_count(user_stats.get("newThisMonth", [])),
                "suspended": self._extract_count(user_stats.get("suspended", []))
            },
            "sellers": {
                "total": total_sellers,
                "free": free_sellers,
                "trial": plan_counts.get("trial", 0),
                "pro": plan_counts.get("pro", 0),
                "enterprise": plan_counts.get("enterprise", 0),
                "suspended": self._extract_count(user_stats.get("suspended", []))
            },
            "inquiries": {
                "total": self._extract_count(inquiry_stats.get("total", [])),
                "pending": self._extract_count(inquiry_stats.get("pending", [])),
                "accepted": self._extract_count(inquiry_stats.get("accepted", [])),
                "thisMonth": self._extract_count(inquiry_stats.get("thisMonth", []))
            },
            "quotes": {
                "total": total_quotes,
                "sent": self._extract_count(quote_stats.get("sent", [])),
                "viewed": self._extract_count(quote_stats.get("viewed", [])),
                "accepted": accepted_quotes,
                "rejected": self._extract_count(quote_stats.get("rejected", [])),
                "expired": self._extract_count(quote_stats.get("expired", [])),
                "acceptanceRate": round((accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0, 2)
            },
            "performance": {
                "avgResponseTimeHours": round(avg_response_time, 2),
                "activeListings": active_listings
            }
        }
    
    async def get_revenue_analytics(self) -> Dict[str, Any]:
        """
        GET /admin/analytics/revenue
        
        Returns:
        - Active Paid Subscriptions
        - Projected MRR (based on plan pricing)
        - Manual Activations count
        - Upgrade Conversion Rate
        - Free sellers hitting 5-lead limit
        - Leads blocked due to plan limit
        """
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Active subscriptions by plan and source
        sub_pipeline = [
            {"$match": {"status": {"$in": ["active", "trial"]}}},
            {"$group": {
                "_id": {
                    "plan": "$planName",
                    "source": {"$ifNull": ["$activationSource", "unknown"]}
                },
                "count": {"$sum": 1}
            }}
        ]
        
        sub_result = await self.db.subscriptions.aggregate(sub_pipeline).to_list(100)
        
        # Calculate MRR and counts
        plan_counts = {}
        source_counts = {"manual": 0, "payment": 0, "unknown": 0}
        projected_mrr = 0
        
        for r in sub_result:
            plan = r["_id"]["plan"]
            source = r["_id"]["source"]
            count = r["count"]
            
            plan_counts[plan] = plan_counts.get(plan, 0) + count
            source_counts[source] = source_counts.get(source, 0) + count
            
            if plan in PLAN_PRICING:
                projected_mrr += PLAN_PRICING[plan] * count
        
        # Free sellers who hit lead limit this month
        lead_limit_pipeline = [
            {"$match": {
                "sellerId": {"$exists": True},
                "status": "accepted",
                "acceptedAt": {"$gte": month_start}
            }},
            {"$group": {
                "_id": "$sellerId",
                "acceptedCount": {"$sum": 1}
            }},
            {"$match": {"acceptedCount": {"$gte": 5}}}
        ]
        
        lead_limit_result = await self.db.inquiries.aggregate(lead_limit_pipeline).to_list(1000)
        
        # Filter to only free sellers
        seller_ids = [r["_id"] for r in lead_limit_result]
        
        # Find which of these don't have paid subscription
        free_at_limit = 0
        if seller_ids:
            paid_subs = await self.db.subscriptions.distinct(
                "userId",
                {
                    "userId": {"$in": seller_ids},
                    "status": {"$in": ["active", "trial"]},
                    "planName": {"$in": ["pro", "enterprise", "trial"]}
                }
            )
            paid_set = set(str(s) for s in paid_subs)
            free_at_limit = sum(1 for s in seller_ids if str(s) not in paid_set)
        
        # Upgrade conversion rate (free → paid this month)
        upgrades_pipeline = [
            {"$match": {
                "status": "active",
                "planName": {"$in": ["pro", "enterprise"]},
                "startDate": {"$gte": month_start}
            }},
            {"$count": "count"}
        ]
        
        upgrades_result = await self.db.subscriptions.aggregate(upgrades_pipeline).to_list(1)
        upgrades_this_month = upgrades_result[0]["count"] if upgrades_result else 0
        
        # Total free sellers for conversion rate
        total_free = await self.db.users.count_documents({
            "roles": "seller"
        }) - plan_counts.get("pro", 0) - plan_counts.get("enterprise", 0)
        
        conversion_rate = (upgrades_this_month / total_free * 100) if total_free > 0 else 0
        
        return {
            "timestamp": now.isoformat(),
            "period": "current_month",
            "subscriptions": {
                "active": {
                    "total": sum(plan_counts.values()),
                    "trial": plan_counts.get("trial", 0),
                    "pro": plan_counts.get("pro", 0),
                    "enterprise": plan_counts.get("enterprise", 0)
                },
                "bySource": {
                    "manual": source_counts.get("manual", 0),
                    "payment": source_counts.get("payment", 0),
                    "unknown": source_counts.get("unknown", 0)
                }
            },
            "revenue": {
                "projectedMRR": projected_mrr,
                "projectedMRRFormatted": f"₹{projected_mrr:,.0f}",
                "note": "Projected based on active plans. Payment gateway not yet integrated."
            },
            "conversion": {
                "upgradesThisMonth": upgrades_this_month,
                "conversionRate": round(conversion_rate, 2),
                "totalFreeSellers": max(0, total_free)
            },
            "leadLimits": {
                "freeSellersAtLimit": free_at_limit,
                "leadLimitForFree": 5,
                "note": "Sellers who reached 5-lead monthly limit on free plan"
            }
        }
    
    async def get_quote_analytics(self, include_leaderboard: bool = True) -> Dict[str, Any]:
        """
        GET /admin/analytics/quotes
        
        Returns:
        - Total Quotes Sent/Accepted/Rejected/Expired
        - Acceptance Rate %
        - Expiry Rate %
        - Average Quote Value
        - Average Validity Period
        - Top 10 Sellers Leaderboard (admin only)
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Quote stats pipeline
        stats_pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$facet": {
                "totals": [
                    {"$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "totalValue": {"$sum": "$totalPrice"}
                    }}
                ],
                "avgValues": [
                    {"$group": {
                        "_id": None,
                        "avgQuoteValue": {"$avg": "$totalPrice"},
                        "avgValidityDays": {"$avg": "$validityDays"},
                        "totalQuotes": {"$sum": 1}
                    }}
                ]
            }}
        ]
        
        stats_result = await self.db.quotes.aggregate(stats_pipeline).to_list(1)
        stats = stats_result[0] if stats_result else {}
        
        # Process totals
        status_counts = {}
        status_values = {}
        for r in stats.get("totals", []):
            status_counts[r["_id"]] = r["count"]
            status_values[r["_id"]] = r["totalValue"]
        
        total_quotes = sum(status_counts.values())
        accepted = status_counts.get("accepted", 0)
        expired = status_counts.get("expired", 0)
        rejected = status_counts.get("rejected", 0)
        
        avg_data = stats.get("avgValues", [{}])[0] if stats.get("avgValues") else {}
        
        result = {
            "timestamp": now.isoformat(),
            "period": "30 days",
            "quotes": {
                "total": total_quotes,
                "sent": status_counts.get("sent", 0),
                "viewed": status_counts.get("viewed", 0),
                "accepted": accepted,
                "rejected": rejected,
                "expired": expired
            },
            "rates": {
                "acceptanceRate": round((accepted / total_quotes * 100) if total_quotes > 0 else 0, 2),
                "rejectionRate": round((rejected / total_quotes * 100) if total_quotes > 0 else 0, 2),
                "expiryRate": round((expired / total_quotes * 100) if total_quotes > 0 else 0, 2),
                "viewRate": round(((status_counts.get("viewed", 0) + accepted + rejected) / total_quotes * 100) if total_quotes > 0 else 0, 2)
            },
            "values": {
                "totalValue": round(sum(status_values.values()), 2),
                "acceptedValue": round(status_values.get("accepted", 0), 2),
                "avgQuoteValue": round(avg_data.get("avgQuoteValue", 0), 2),
                "avgValidityDays": round(avg_data.get("avgValidityDays", 0), 1)
            }
        }
        
        # Seller leaderboard (admin only)
        if include_leaderboard:
            leaderboard = await self._get_seller_leaderboard(thirty_days_ago)
            result["leaderboard"] = leaderboard
        
        return result
    
    async def _get_seller_leaderboard(self, since: datetime) -> Dict[str, List]:
        """
        Top 10 sellers by various metrics.
        ADMIN ONLY - not exposed to sellers.
        """
        # Top by acceptance rate
        acceptance_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {
                "_id": "$sellerId",
                "totalQuotes": {"$sum": 1},
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                }
            }},
            {"$match": {"totalQuotes": {"$gte": 3}}},  # Min 3 quotes
            {"$project": {
                "totalQuotes": 1,
                "accepted": 1,
                "acceptanceRate": {
                    "$multiply": [
                        {"$divide": ["$accepted", "$totalQuotes"]},
                        100
                    ]
                }
            }},
            {"$sort": {"acceptanceRate": -1}},
            {"$limit": 10}
        ]
        
        acceptance_result = await self.db.quotes.aggregate(acceptance_pipeline).to_list(10)
        
        # Enrich with seller names
        seller_ids = [r["_id"] for r in acceptance_result]
        sellers = {}
        if seller_ids:
            seller_docs = await self.db.users.find(
                {"_id": {"$in": seller_ids}},
                {"profile.businessName": 1, "email": 1}
            ).to_list(100)
            sellers = {
                s["_id"]: s.get("profile", {}).get("businessName") or s.get("email", "Unknown")
                for s in seller_docs
            }
        
        # Top by response time
        response_pipeline = [
            {"$match": {
                "status": "accepted",
                "acceptedAt": {"$exists": True},
                "createdAt": {"$gte": since}
            }},
            {"$group": {
                "_id": "$sellerId",
                "avgResponseHours": {
                    "$avg": {
                        "$divide": [
                            {"$subtract": ["$acceptedAt", "$createdAt"]},
                            3600000
                        ]
                    }
                },
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gte": 3}}},
            {"$sort": {"avgResponseHours": 1}},
            {"$limit": 10}
        ]
        
        response_result = await self.db.inquiries.aggregate(response_pipeline).to_list(10)
        
        # Top by conversion (quotes accepted / leads accepted)
        conversion_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {
                "_id": "$sellerId",
                "totalQuotes": {"$sum": 1},
                "acceptedQuotes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                },
                "totalValue": {"$sum": "$totalPrice"},
                "acceptedValue": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, "$totalPrice", 0]}
                }
            }},
            {"$match": {"totalQuotes": {"$gte": 3}}},
            {"$project": {
                "totalQuotes": 1,
                "acceptedQuotes": 1,
                "totalValue": 1,
                "acceptedValue": 1,
                "conversionRate": {
                    "$multiply": [
                        {"$divide": ["$acceptedQuotes", "$totalQuotes"]},
                        100
                    ]
                }
            }},
            {"$sort": {"acceptedValue": -1}},
            {"$limit": 10}
        ]
        
        conversion_result = await self.db.quotes.aggregate(conversion_pipeline).to_list(10)
        
        return {
            "byAcceptanceRate": [
                {
                    "sellerId": str(r["_id"]),
                    "sellerName": sellers.get(r["_id"], "Unknown"),
                    "totalQuotes": r["totalQuotes"],
                    "accepted": r["accepted"],
                    "acceptanceRate": round(r["acceptanceRate"], 1)
                }
                for r in acceptance_result
            ],
            "byResponseTime": [
                {
                    "sellerId": str(r["_id"]),
                    "sellerName": sellers.get(r["_id"], "Unknown"),
                    "avgResponseHours": round(r["avgResponseHours"], 1),
                    "inquiriesHandled": r["count"]
                }
                for r in response_result
            ],
            "byConversion": [
                {
                    "sellerId": str(r["_id"]),
                    "sellerName": sellers.get(r["_id"], "Unknown"),
                    "totalQuotes": r["totalQuotes"],
                    "acceptedQuotes": r["acceptedQuotes"],
                    "acceptedValue": round(r["acceptedValue"], 2),
                    "conversionRate": round(r["conversionRate"], 1)
                }
                for r in conversion_result
            ]
        }
    
    async def get_product_analytics(self) -> Dict[str, Any]:
        """
        GET /admin/analytics/products
        
        Returns:
        - Most Inquired Products
        - Most Converted Products
        - Highest Expiry Products
        - Avg Quote Value per Product
        - Category Conversion Rate
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Most inquired products
        inquired_pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": "$productId",
                "productName": {"$first": "$productName"},
                "inquiryCount": {"$sum": 1},
                "acceptedCount": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                }
            }},
            {"$sort": {"inquiryCount": -1}},
            {"$limit": 10}
        ]
        
        inquired_result = await self.db.inquiries.aggregate(inquired_pipeline).to_list(10)
        
        # Product quote stats
        quote_product_pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": "$productId",
                "productName": {"$first": "$productName"},
                "totalQuotes": {"$sum": 1},
                "accepted": {
                    "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                },
                "expired": {
                    "$sum": {"$cond": [{"$eq": ["$status", "expired"]}, 1, 0]}
                },
                "totalValue": {"$sum": "$totalPrice"},
                "avgValue": {"$avg": "$totalPrice"}
            }},
            {"$project": {
                "productName": 1,
                "totalQuotes": 1,
                "accepted": 1,
                "expired": 1,
                "totalValue": 1,
                "avgValue": 1,
                "conversionRate": {
                    "$cond": [
                        {"$gt": ["$totalQuotes", 0]},
                        {"$multiply": [{"$divide": ["$accepted", "$totalQuotes"]}, 100]},
                        0
                    ]
                },
                "expiryRate": {
                    "$cond": [
                        {"$gt": ["$totalQuotes", 0]},
                        {"$multiply": [{"$divide": ["$expired", "$totalQuotes"]}, 100]},
                        0
                    ]
                }
            }}
        ]
        
        quote_product_result = await self.db.quotes.aggregate(quote_product_pipeline).to_list(100)
        
        # Sort for different rankings
        by_conversion = sorted(quote_product_result, key=lambda x: x.get("conversionRate", 0), reverse=True)[:10]
        by_expiry = sorted(quote_product_result, key=lambda x: x.get("expiryRate", 0), reverse=True)[:10]
        by_value = sorted(quote_product_result, key=lambda x: x.get("avgValue", 0), reverse=True)[:10]
        
        return {
            "timestamp": now.isoformat(),
            "period": "30 days",
            "mostInquired": [
                {
                    "productId": str(r["_id"]) if r["_id"] else None,
                    "productName": r.get("productName", "Unknown"),
                    "inquiryCount": r["inquiryCount"],
                    "acceptedCount": r["acceptedCount"]
                }
                for r in inquired_result
            ],
            "highestConversion": [
                {
                    "productId": str(r["_id"]) if r["_id"] else None,
                    "productName": r.get("productName", "Unknown"),
                    "totalQuotes": r["totalQuotes"],
                    "accepted": r["accepted"],
                    "conversionRate": round(r["conversionRate"], 1)
                }
                for r in by_conversion
            ],
            "highestExpiry": [
                {
                    "productId": str(r["_id"]) if r["_id"] else None,
                    "productName": r.get("productName", "Unknown"),
                    "totalQuotes": r["totalQuotes"],
                    "expired": r["expired"],
                    "expiryRate": round(r["expiryRate"], 1)
                }
                for r in by_expiry
            ],
            "highestValue": [
                {
                    "productId": str(r["_id"]) if r["_id"] else None,
                    "productName": r.get("productName", "Unknown"),
                    "avgQuoteValue": round(r.get("avgValue", 0), 2),
                    "totalValue": round(r.get("totalValue", 0), 2)
                }
                for r in by_value
            ]
        }
    
    async def get_leads_analytics(self) -> Dict[str, Any]:
        """
        GET /admin/analytics/leads
        
        Returns:
        - Total leads (inquiries)
        - Leads by status
        - Lead response time distribution
        - Lead conversion funnel
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Lead funnel pipeline
        funnel_pipeline = [
            {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
            {"$facet": {
                "byStatus": [
                    {"$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }}
                ],
                "responseTime": [
                    {"$match": {
                        "status": "accepted",
                        "acceptedAt": {"$exists": True}
                    }},
                    {"$project": {
                        "responseHours": {
                            "$divide": [
                                {"$subtract": ["$acceptedAt", "$createdAt"]},
                                3600000
                            ]
                        }
                    }},
                    {"$bucket": {
                        "groupBy": "$responseHours",
                        "boundaries": [0, 1, 4, 12, 24, 48, 168],  # Hours
                        "default": "over_week",
                        "output": {"count": {"$sum": 1}}
                    }}
                ],
                "daily": [
                    {"$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$createdAt"
                            }
                        },
                        "count": {"$sum": 1}
                    }},
                    {"$sort": {"_id": -1}},
                    {"$limit": 30}
                ]
            }}
        ]
        
        result = await self.db.inquiries.aggregate(funnel_pipeline).to_list(1)
        data = result[0] if result else {}
        
        # Process status counts
        status_counts = {r["_id"]: r["count"] for r in data.get("byStatus", [])}
        total = sum(status_counts.values())
        
        # Response time buckets
        response_buckets = {}
        bucket_labels = {
            0: "under_1h",
            1: "1-4h",
            4: "4-12h",
            12: "12-24h",
            24: "24-48h",
            48: "2-7_days",
            "over_week": "over_week"
        }
        for r in data.get("responseTime", []):
            bucket = r["_id"]
            label = bucket_labels.get(bucket, str(bucket))
            response_buckets[label] = r["count"]
        
        return {
            "timestamp": now.isoformat(),
            "period": "30 days",
            "funnel": {
                "total": total,
                "pending": status_counts.get("pending", 0),
                "accepted": status_counts.get("accepted", 0),
                "rejected": status_counts.get("rejected", 0),
                "reported": status_counts.get("reported", 0)
            },
            "conversionRate": round(
                (status_counts.get("accepted", 0) / total * 100) if total > 0 else 0,
                2
            ),
            "responseTimeDistribution": response_buckets,
            "dailyTrend": [
                {"date": r["_id"], "count": r["count"]}
                for r in data.get("daily", [])
            ]
        }
    
    def _extract_count(self, result: list) -> int:
        """Extract count from facet result."""
        if result and len(result) > 0:
            return result[0].get("count", 0)
        return 0


async def get_admin_analytics_service(db) -> AdminAnalyticsService:
    """Factory function for admin analytics service."""
    service = AdminAnalyticsService(db)
    return service
