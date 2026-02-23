"""
ADMIN GOVERNANCE ROUTER - Phase B
=================================

Admin endpoints for seller governance and abuse monitoring.

Endpoints:
- GET /admin/governance/market-health
- GET /admin/governance/abuse-summary
- GET /admin/governance/high-expiry-sellers
- GET /admin/governance/slow-responders
- GET /admin/governance/zero-conversion
- GET /admin/governance/suspicious-activity
- GET /admin/governance/seller/{id}/summary
- POST /admin/governance/seller/{id}/suspend
- POST /admin/governance/seller/{id}/unsuspend
- POST /admin/governance/seller/{id}/warn
- POST /admin/governance/gst/{id}/approve
- POST /admin/governance/gst/{id}/reject
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
    duration: Optional[str] = Field(None, description="e.g., '7 days', '30 days', 'indefinite'")
    notes: Optional[str] = Field(None, max_length=1000)


class WarnRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
    level: int = Field(1, ge=1, le=3, description="Warning level: 1=info, 2=caution, 3=final")


class GstDecisionRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


def create_admin_governance_router(db, require_admin):
    """
    Factory function to create admin governance router.
    """
    router = APIRouter(prefix="/admin/governance", tags=["Admin Governance"])
    
    from services.seller_governance_service import SellerGovernanceService
    from services.abuse_monitoring_service import AbuseMonitoringService
    from services.admin_audit_service import AdminAuditService, AuditAction
    
    @router.get("/market-health")
    async def get_market_health(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get overall marketplace health metrics.
        """
        service = AbuseMonitoringService(db)
        return await service.get_market_health()
    
    @router.get("/abuse-summary")
    async def get_abuse_summary(
        current_user: dict = Depends(require_admin)
    ):
        """
        Get comprehensive abuse monitoring summary.
        
        Returns all abuse indicators:
        - High expiry sellers
        - Slow responders
        - Zero conversion
        - Suspicious patterns
        """
        service = AbuseMonitoringService(db)
        return await service.get_abuse_summary()
    
    @router.get("/high-expiry-sellers")
    async def get_high_expiry_sellers(
        threshold: float = Query(40, ge=10, le=100, description="Expiry rate threshold %"),
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get sellers with high quote expiry rate.
        """
        service = AbuseMonitoringService(db)
        sellers = await service.get_high_expiry_sellers(threshold=threshold, limit=limit)
        return {
            "threshold": threshold,
            "count": len(sellers),
            "sellers": sellers
        }
    
    @router.get("/slow-responders")
    async def get_slow_responders(
        threshold_hours: float = Query(24, ge=1, le=168, description="Response time threshold in hours"),
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get sellers with slow response times.
        """
        service = AbuseMonitoringService(db)
        sellers = await service.get_slow_responders(threshold_hours=threshold_hours, limit=limit)
        return {
            "thresholdHours": threshold_hours,
            "count": len(sellers),
            "sellers": sellers
        }
    
    @router.get("/zero-conversion")
    async def get_zero_conversion_sellers(
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get sellers with zero conversion rate.
        """
        service = AbuseMonitoringService(db)
        sellers = await service.get_zero_conversion_sellers(limit=limit)
        return {
            "count": len(sellers),
            "sellers": sellers
        }
    
    @router.get("/suspicious-activity")
    async def get_suspicious_activity(
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get suspicious activity patterns.
        """
        service = AbuseMonitoringService(db)
        patterns = await service.get_suspicious_activity(limit=limit)
        return {
            "count": len(patterns),
            "patterns": patterns
        }
    
    @router.get("/seller/{seller_id}/summary")
    async def get_seller_governance_summary(
        seller_id: str,
        current_user: dict = Depends(require_admin)
    ):
        """
        Get complete governance summary for a seller.
        
        Includes:
        - Status and warnings
        - GST verification status
        - Performance metrics
        - Listing counts
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        service = SellerGovernanceService(db)
        summary = await service.get_governance_summary(seller_oid)
        
        if not summary.get("exists", True):
            raise HTTPException(status_code=404, detail="Seller not found")
        
        return summary
    
    @router.post("/seller/{seller_id}/suspend")
    async def suspend_seller(
        seller_id: str,
        request: SuspendRequest,
        req: Request,
        current_user: dict = Depends(require_admin)
    ):
        """
        Suspend a seller.
        
        Effects:
        - Cannot accept leads
        - Cannot create quotes
        - Listings hidden
        - Removed from ranking
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        service = SellerGovernanceService(db)
        result = await service.suspend_seller(
            seller_id=seller_oid,
            admin_id=current_user["_id"],
            reason=request.reason,
            duration=request.duration,
            notes=request.notes
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    @router.post("/seller/{seller_id}/unsuspend")
    async def unsuspend_seller(
        seller_id: str,
        notes: Optional[str] = None,
        current_user: dict = Depends(require_admin)
    ):
        """
        Unsuspend a seller.
        
        Note: Listings must be manually restored.
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        service = SellerGovernanceService(db)
        result = await service.unsuspend_seller(
            seller_id=seller_oid,
            admin_id=current_user["_id"],
            notes=notes
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    @router.post("/seller/{seller_id}/warn")
    async def warn_seller(
        seller_id: str,
        request: WarnRequest,
        current_user: dict = Depends(require_admin)
    ):
        """
        Issue warning to seller.
        
        Warning levels:
        - 1: First warning (informational)
        - 2: Second warning (caution)
        - 3: Final warning (before suspension)
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        service = SellerGovernanceService(db)
        result = await service.warn_seller(
            seller_id=seller_oid,
            admin_id=current_user["_id"],
            reason=request.reason,
            warning_level=request.level
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    
    @router.post("/gst/{seller_id}/approve")
    async def approve_gst(
        seller_id: str,
        req: Request,
        current_user: dict = Depends(require_admin)
    ):
        """
        Approve seller's GST verification.
        
        Effects:
        - GST marked as verified
        - "Verified Seller" badge enabled
        - Ranking boost applied
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        now = datetime.now(timezone.utc)
        
        # Update GST status
        result = await db.users.update_one(
            {"_id": seller_oid, "roles": "seller"},
            {"$set": {
                "gst.isVerified": True,
                "gst.verifiedAt": now,
                "gst.verifiedBy": current_user["_id"],
                "gst.status": "approved"
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Seller not found or already verified")
        
        # Log audit
        audit = AdminAuditService(db)
        await audit.log_gst_decision(
            admin_id=current_user["_id"],
            seller_id=seller_oid,
            decision="approve",
            ip_address=req.client.host if req.client else None
        )
        
        return {
            "success": True,
            "message": "GST verification approved",
            "sellerId": seller_id
        }
    
    @router.post("/gst/{seller_id}/reject")
    async def reject_gst(
        seller_id: str,
        request: GstDecisionRequest,
        req: Request,
        current_user: dict = Depends(require_admin)
    ):
        """
        Reject seller's GST verification.
        """
        try:
            seller_oid = ObjectId(seller_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        now = datetime.now(timezone.utc)
        
        # Update GST status
        result = await db.users.update_one(
            {"_id": seller_oid, "roles": "seller"},
            {"$set": {
                "gst.isVerified": False,
                "gst.status": "rejected",
                "gst.rejectedAt": now,
                "gst.rejectedBy": current_user["_id"],
                "gst.rejectionReason": request.reason
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        # Log audit
        audit = AdminAuditService(db)
        await audit.log_gst_decision(
            admin_id=current_user["_id"],
            seller_id=seller_oid,
            decision="reject",
            reason=request.reason,
            ip_address=req.client.host if req.client else None
        )
        
        return {
            "success": True,
            "message": "GST verification rejected",
            "sellerId": seller_id,
            "reason": request.reason
        }
    
    @router.get("/gst/pending")
    async def get_pending_gst_verifications(
        limit: int = Query(50, ge=1, le=100),
        current_user: dict = Depends(require_admin)
    ):
        """
        Get sellers with pending GST verification.
        """
        sellers = await db.users.find({
            "roles": "seller",
            "gst.number": {"$exists": True},
            "gst.isVerified": {"$ne": True},
            "gst.status": {"$nin": ["rejected"]}
        }).limit(limit).to_list(limit)
        
        return {
            "count": len(sellers),
            "pendingVerifications": [
                {
                    "sellerId": str(s["_id"]),
                    "email": s.get("email"),
                    "businessName": s.get("profile", {}).get("businessName"),
                    "gstNumber": s.get("gst", {}).get("number"),
                    "documentUrl": s.get("gst", {}).get("documentUrl"),
                    "submittedAt": s.get("gst", {}).get("submittedAt")
                }
                for s in sellers
            ]
        }
    
    return router
