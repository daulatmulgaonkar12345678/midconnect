"""
SELLER PERFORMANCE ROUTER - Phase A.3
=====================================

Seller-facing performance endpoints.
Sellers can only see their own data + marketplace averages.

Endpoints:
- GET /seller/performance - Own performance score
- GET /seller/performance/trend - 30-day trend
- GET /seller/performance/lead-stats - Lead usage stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_seller_performance_router(db, get_current_user):
    """
    Factory function to create seller performance router.
    
    Args:
        db: MongoDB database instance
        get_current_user: Dependency to get current authenticated user
    """
    router = APIRouter(prefix="/seller/performance", tags=["Seller Performance"])
    
    # Import services
    from services.seller_performance_service import SellerPerformanceService
    from services.lead_service import get_lead_stats, can_accept_lead
    
    def require_seller(current_user: dict = Depends(get_current_user)):
        """Require seller role."""
        if "seller" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Seller role required")
        return current_user
    
    @router.get("")
    async def get_my_performance(
        current_user: dict = Depends(require_seller)
    ):
        """
        Get seller's own performance score and metrics.
        
        Returns:
        - Overall score (0-100)
        - Performance tier
        - Breakdown by category
        - Improvement suggestions
        - Marketplace averages (anonymized)
        
        Seller sees:
        - Own metrics only
        - Marketplace averages for comparison
        
        Seller does NOT see:
        - Other seller data
        - Ranking weights
        - Competitor metrics
        """
        service = SellerPerformanceService(db)
        
        try:
            result = await service.calculate_seller_score(
                current_user["_id"],
                include_suggestions=True
            )
            return result
        except Exception as e:
            logger.error(f"Performance calculation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate performance")
    
    @router.get("/trend")
    async def get_performance_trend(
        days: int = Query(30, ge=7, le=90, description="Days of trend data"),
        current_user: dict = Depends(require_seller)
    ):
        """
        Get seller's performance trend over time.
        
        Returns daily metrics:
        - Quotes created
        - Quotes accepted
        - Total value
        """
        service = SellerPerformanceService(db)
        
        try:
            trend = await service.get_seller_trend(
                current_user["_id"],
                days=days
            )
            return {
                "sellerId": str(current_user["_id"]),
                "period": f"{days} days",
                "trend": trend
            }
        except Exception as e:
            logger.error(f"Trend calculation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get trend data")
    
    @router.get("/lead-stats")
    async def get_lead_usage_stats(
        current_user: dict = Depends(require_seller)
    ):
        """
        Get seller's lead usage statistics.
        
        Returns:
        - Current month usage
        - Plan limit
        - Remaining leads
        - Days until reset
        """
        try:
            stats = await get_lead_stats(db, current_user["_id"])
            can_accept = await can_accept_lead(db, current_user["_id"])
            
            return {
                "sellerId": str(current_user["_id"]),
                "leadStats": stats,
                "canAcceptNewLead": can_accept["canAccept"],
                "limitMessage": can_accept.get("message"),
                "upgradeUrl": can_accept.get("upgradeUrl")
            }
        except Exception as e:
            logger.error(f"Lead stats error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get lead stats")
    
    @router.get("/summary")
    async def get_performance_summary(
        current_user: dict = Depends(require_seller)
    ):
        """
        Get a quick performance summary for dashboard display.
        
        Returns lightweight metrics suitable for dashboard widgets.
        """
        service = SellerPerformanceService(db)
        
        try:
            full_score = await service.calculate_seller_score(
                current_user["_id"],
                include_suggestions=False
            )
            
            # Return simplified summary
            return {
                "score": full_score["score"],
                "tier": full_score["tier"],
                "tierColor": full_score["tierColor"],
                "metrics": {
                    "responseTimeHours": full_score["metrics"].get("avgResponseTimeHours", 0),
                    "acceptanceRate": full_score["metrics"].get("acceptanceRate", 0),
                    "totalQuotes": full_score["metrics"].get("totalQuotes", 0),
                    "acceptedQuotes": full_score["metrics"].get("acceptedQuotes", 0)
                }
            }
        except Exception as e:
            logger.error(f"Summary calculation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get summary")
    
    @router.get("/monthly-stats")
    async def get_monthly_stats(
        months: int = Query(3, ge=1, le=12, description="Number of months"),
        current_user: dict = Depends(require_seller)
    ):
        """
        Get seller's monthly aggregated stats.
        
        Uses pre-computed monthly stats from nightly aggregation.
        """
        now = datetime.now(timezone.utc)
        month_keys = []
        
        current = now
        for i in range(months):
            month_keys.append(f"{current.year}-{current.month:02d}")
            # Go back one month
            if current.month == 1:
                current = current.replace(year=current.year - 1, month=12)
            else:
                current = current.replace(month=current.month - 1)
        
        # Query monthly stats
        stats = await db.sellerMonthlyStats.find({
            "sellerId": current_user["_id"],
            "month": {"$in": month_keys}
        }).sort("month", -1).to_list(months)
        
        return {
            "sellerId": str(current_user["_id"]),
            "months": months,
            "stats": [
                {
                    "month": s["month"],
                    "inquiries": s.get("inquiries", {}),
                    "quotes": s.get("quotes", {}),
                    "values": s.get("values", {})
                }
                for s in stats
            ]
        }
    
    return router
