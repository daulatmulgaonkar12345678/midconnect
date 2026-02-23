"""
ADMIN ANALYTICS ROUTER - Phase A.1
==================================

Admin-only endpoints for marketplace analytics.
All endpoints require admin role.

Endpoints:
- GET /admin/analytics/overview
- GET /admin/analytics/revenue
- GET /admin/analytics/quotes
- GET /admin/analytics/leads
- GET /admin/analytics/products
- GET /admin/analytics/audit-logs
- POST /admin/analytics/run-aggregation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


def create_admin_analytics_router(db, require_admin):
    """
    Factory function to create admin analytics router.
    
    Args:
        db: MongoDB database instance
        require_admin: Dependency to require admin role
    """
    router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])
    
    # Import services
    from services.admin_analytics_service import AdminAnalyticsService
    from services.admin_audit_service import AdminAuditService, AuditAction
    
    @router.get("/overview")
    async def get_overview(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get marketplace overview metrics.
        
        Returns:
        - Total Users (sellers, buyers breakdown)
        - Subscription breakdown (free, trial, pro, enterprise)
        - Inquiry stats
        - Quote stats
        - Performance metrics
        """
        service = AdminAnalyticsService(db)
        return await service.get_overview()
    
    @router.get("/revenue")
    async def get_revenue_analytics(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get revenue intelligence metrics.
        
        Returns:
        - Active paid subscriptions
        - Projected MRR
        - Manual vs payment activations
        - Upgrade conversion rate
        - Free sellers at lead limit
        """
        service = AdminAnalyticsService(db)
        return await service.get_revenue_analytics()
    
    @router.get("/quotes")
    async def get_quote_analytics(
        include_leaderboard: bool = Query(True, description="Include seller leaderboard"),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get quote analytics.
        
        Returns:
        - Quote counts by status
        - Acceptance/Rejection/Expiry rates
        - Average quote value
        - Top 10 sellers leaderboard (admin only)
        """
        service = AdminAnalyticsService(db)
        return await service.get_quote_analytics(include_leaderboard=include_leaderboard)
    
    @router.get("/leads")
    async def get_leads_analytics(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get lead/inquiry analytics.
        
        Returns:
        - Lead funnel (pending → accepted → converted)
        - Response time distribution
        - Daily trend
        """
        service = AdminAnalyticsService(db)
        return await service.get_leads_analytics()
    
    @router.get("/products")
    async def get_product_analytics(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get product analytics.
        
        Returns:
        - Most inquired products
        - Highest conversion products
        - Highest expiry products
        - Highest value products
        """
        service = AdminAnalyticsService(db)
        return await service.get_product_analytics()
    
    @router.get("/audit-logs")
    async def get_audit_logs(
        admin_id: Optional[str] = Query(None, description="Filter by admin ID"),
        action: Optional[str] = Query(None, description="Filter by action type"),
        target_type: Optional[str] = Query(None, description="Filter by target type"),
        days: int = Query(30, ge=1, le=90, description="Days to look back"),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get admin audit logs.
        
        Returns paginated audit trail with filters.
        """
        service = AdminAuditService(db)
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        admin_oid = ObjectId(admin_id) if admin_id else None
        
        return await service.get_audit_logs(
            admin_id=admin_oid,
            action=action,
            target_type=target_type,
            start_date=start_date,
            page=page,
            limit=limit
        )
    
    @router.get("/audit-logs/entity/{target_type}/{target_id}")
    async def get_entity_audit_trail(
        target_type: str,
        target_id: str,
        current_user: dict = Depends(require_admin)
    ):
        """
        Get audit trail for a specific entity.
        """
        service = AdminAuditService(db)
        
        try:
            target_oid = ObjectId(target_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid target ID")
        
        return await service.get_entity_audit_trail(target_type, target_oid)
    
    @router.post("/run-aggregation")
    async def run_manual_aggregation(
        request: Request,
        current_user: dict = Depends(require_admin)
    ):
        """
        Manually trigger monthly aggregation job.
        
        Note: This is normally run via nightly cron.
        """
        from cron.monthly_aggregation_cron import run_monthly_aggregation
        
        # Log the action
        audit_service = AdminAuditService(db)
        await audit_service.log(
            admin_id=current_user["_id"],
            action=AuditAction.CRON_JOB_MANUAL_RUN,
            target_type="system",
            target_id=None,
            details={"job": "monthly_aggregation"},
            ip_address=request.client.host if request.client else None
        )
        
        # Run aggregation
        try:
            result = await run_monthly_aggregation()
            return {
                "success": True,
                "message": "Monthly aggregation completed",
                "duration": result.get("duration")
            }
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/seller/{seller_id}/performance")
    async def get_seller_performance(
        seller_id: str,
        current_user: dict = Depends(require_admin)
    ):
        """
        Get detailed performance metrics for a specific seller.
        Admin can view any seller's performance.
        """
        from services.seller_performance_service import SellerPerformanceService
        
        try:
            seller_oid = ObjectId(seller_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        # Verify seller exists
        seller = await db.users.find_one({"_id": seller_oid, "roles": "seller"})
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        service = SellerPerformanceService(db)
        return await service.calculate_seller_score(seller_oid)
    
    @router.get("/health")
    async def analytics_health(
        current_user: dict = Depends(require_admin)
    ):
        """
        Check analytics service health and index status.
        """
        # Check indexes
        indexes = {}
        
        try:
            indexes["users"] = await db.users.index_information()
            indexes["subscriptions"] = await db.subscriptions.index_information()
            indexes["inquiries"] = await db.inquiries.index_information()
            indexes["quotes"] = await db.quotes.index_information()
            indexes["sellerMonthlyStats"] = await db.sellerMonthlyStats.index_information()
        except Exception as e:
            logger.error(f"Index check failed: {e}")
        
        # Check collection counts
        counts = {
            "users": await db.users.count_documents({}),
            "subscriptions": await db.subscriptions.count_documents({}),
            "inquiries": await db.inquiries.count_documents({}),
            "quotes": await db.quotes.count_documents({}),
            "sellerMonthlyStats": await db.sellerMonthlyStats.count_documents({}),
            "adminAuditLogs": await db.adminAuditLogs.count_documents({})
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collections": counts,
            "indexCount": {k: len(v) for k, v in indexes.items()}
        }
    
    return router
