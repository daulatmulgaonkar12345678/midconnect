"""
SELLER GOVERNANCE SERVICE - Phase B
====================================

Lead Governance Enforcement + Seller Status Management

When seller suspended:
- Cannot accept new leads
- Cannot create quotes
- Removed from ranking
- Listings hidden
- Quote page still accessible historically

All queries must check: if seller.status != active → block
"""

from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any, Optional, List, Literal
import logging

logger = logging.getLogger(__name__)


# Seller statuses
class SellerStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WARNED = "warned"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"


# Suspension reasons
SUSPENSION_REASONS = {
    "high_expiry": "High quote expiry rate (>40%)",
    "slow_response": "Consistently slow response time (>24hrs)",
    "zero_conversion": "Zero conversion after multiple leads",
    "fraud": "Fraudulent activity detected",
    "spam": "Spam or inappropriate content",
    "gst_invalid": "Invalid GST verification",
    "customer_complaints": "Multiple customer complaints",
    "terms_violation": "Terms of service violation",
    "admin_action": "Administrative action"
}


class SellerGovernanceService:
    """
    Seller Governance Service.
    
    Handles:
    - Seller status management (active, suspended, warned, banned)
    - Lead acceptance blocking
    - Listing visibility control
    - Governance enforcement on all operations
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_seller_status(self, seller_id: ObjectId) -> Dict[str, Any]:
        """
        Get seller's current governance status.
        """
        seller = await self.db.users.find_one(
            {"_id": seller_id, "roles": "seller"},
            {
                "status": 1,
                "statusReason": 1,
                "statusUpdatedAt": 1,
                "warnings": 1,
                "gst.isVerified": 1
            }
        )
        
        if not seller:
            return {"exists": False, "status": None}
        
        return {
            "exists": True,
            "status": seller.get("status", SellerStatus.ACTIVE),
            "reason": seller.get("statusReason"),
            "updatedAt": seller.get("statusUpdatedAt"),
            "warnings": seller.get("warnings", []),
            "warningCount": len(seller.get("warnings", [])),
            "isGstVerified": seller.get("gst", {}).get("isVerified", False)
        }
    
    async def can_accept_lead(self, seller_id: ObjectId) -> Dict[str, Any]:
        """
        Check if seller can accept a lead.
        
        Blocked if:
        - Status is suspended or banned
        - Hit lead limit (free plan)
        
        Returns:
        {
            "canAccept": bool,
            "reason": str | None,
            "message": str | None
        }
        """
        status = await self.get_seller_status(seller_id)
        
        if not status["exists"]:
            return {
                "canAccept": False,
                "reason": "SELLER_NOT_FOUND",
                "message": "Seller account not found"
            }
        
        if status["status"] == SellerStatus.SUSPENDED:
            return {
                "canAccept": False,
                "reason": "SUSPENDED",
                "message": f"Your account is suspended: {status.get('reason', 'Contact support')}"
            }
        
        if status["status"] == SellerStatus.BANNED:
            return {
                "canAccept": False,
                "reason": "BANNED",
                "message": "Your account has been permanently banned"
            }
        
        # Also check lead limits via lead_service
        from services.lead_service import can_accept_lead as check_lead_limit
        lead_check = await check_lead_limit(self.db, seller_id)
        
        if not lead_check["canAccept"]:
            return lead_check
        
        return {
            "canAccept": True,
            "reason": None,
            "message": None,
            "status": status["status"]
        }
    
    async def can_create_quote(self, seller_id: ObjectId) -> Dict[str, Any]:
        """
        Check if seller can create quotes.
        
        Blocked if:
        - Status is suspended or banned
        """
        status = await self.get_seller_status(seller_id)
        
        if not status["exists"]:
            return {
                "canCreate": False,
                "reason": "SELLER_NOT_FOUND",
                "message": "Seller account not found"
            }
        
        if status["status"] in [SellerStatus.SUSPENDED, SellerStatus.BANNED]:
            return {
                "canCreate": False,
                "reason": status["status"].upper(),
                "message": f"Your account is {status['status']}. You cannot create quotes."
            }
        
        return {
            "canCreate": True,
            "reason": None,
            "message": None
        }
    
    async def suspend_seller(
        self,
        seller_id: ObjectId,
        admin_id: ObjectId,
        reason: str,
        duration: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suspend a seller.
        
        Effects:
        - Cannot accept leads
        - Cannot create quotes
        - Listings hidden from search
        - Removed from ranking
        """
        now = datetime.now(timezone.utc)
        
        # Update seller status
        result = await self.db.users.update_one(
            {"_id": seller_id, "roles": "seller"},
            {"$set": {
                "status": SellerStatus.SUSPENDED,
                "statusReason": reason,
                "statusUpdatedAt": now,
                "statusUpdatedBy": admin_id,
                "suspensionDuration": duration,
                "suspensionNotes": notes
            }}
        )
        
        if result.modified_count == 0:
            return {"success": False, "message": "Seller not found or already suspended"}
        
        # Hide all seller listings
        await self.db.sellerListings.update_many(
            {"sellerId": seller_id},
            {"$set": {
                "isActive": False,
                "hiddenReason": "seller_suspended",
                "hiddenAt": now
            }}
        )
        
        # Log audit
        from services.admin_audit_service import AdminAuditService, AuditAction
        audit = AdminAuditService(self.db)
        await audit.log(
            admin_id=admin_id,
            action=AuditAction.SELLER_SUSPEND,
            target_type="seller",
            target_id=seller_id,
            details={
                "reason": reason,
                "duration": duration,
                "notes": notes
            }
        )
        
        logger.info(f"Seller {seller_id} suspended by admin {admin_id}: {reason}")
        
        return {
            "success": True,
            "message": "Seller suspended",
            "sellerId": str(seller_id),
            "status": SellerStatus.SUSPENDED
        }
    
    async def unsuspend_seller(
        self,
        seller_id: ObjectId,
        admin_id: ObjectId,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unsuspend a seller.
        
        Effects:
        - Restore ability to accept leads
        - Restore ability to create quotes
        - Listings NOT automatically restored (manual action)
        """
        now = datetime.now(timezone.utc)
        
        result = await self.db.users.update_one(
            {"_id": seller_id, "status": SellerStatus.SUSPENDED},
            {"$set": {
                "status": SellerStatus.ACTIVE,
                "statusReason": None,
                "statusUpdatedAt": now,
                "statusUpdatedBy": admin_id,
                "unsuspensionNotes": notes
            }}
        )
        
        if result.modified_count == 0:
            return {"success": False, "message": "Seller not found or not suspended"}
        
        # Log audit
        from services.admin_audit_service import AdminAuditService, AuditAction
        audit = AdminAuditService(self.db)
        await audit.log(
            admin_id=admin_id,
            action=AuditAction.SELLER_UNSUSPEND,
            target_type="seller",
            target_id=seller_id,
            details={"notes": notes}
        )
        
        logger.info(f"Seller {seller_id} unsuspended by admin {admin_id}")
        
        return {
            "success": True,
            "message": "Seller unsuspended. Listings must be manually restored.",
            "sellerId": str(seller_id),
            "status": SellerStatus.ACTIVE
        }
    
    async def warn_seller(
        self,
        seller_id: ObjectId,
        admin_id: ObjectId,
        reason: str,
        warning_level: int = 1
    ) -> Dict[str, Any]:
        """
        Issue warning to seller.
        
        Warning levels:
        1 - First warning (informational)
        2 - Second warning (caution)
        3 - Final warning (before suspension)
        """
        now = datetime.now(timezone.utc)
        
        warning = {
            "level": warning_level,
            "reason": reason,
            "issuedAt": now,
            "issuedBy": admin_id
        }
        
        result = await self.db.users.update_one(
            {"_id": seller_id, "roles": "seller"},
            {
                "$push": {"warnings": warning},
                "$set": {
                    "status": SellerStatus.WARNED,
                    "statusUpdatedAt": now
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "message": "Seller not found"}
        
        # Get warning count
        seller = await self.db.users.find_one(
            {"_id": seller_id},
            {"warnings": 1}
        )
        warning_count = len(seller.get("warnings", []))
        
        # Log audit
        from services.admin_audit_service import AdminAuditService, AuditAction
        audit = AdminAuditService(self.db)
        await audit.log(
            admin_id=admin_id,
            action=AuditAction.SELLER_WARN,
            target_type="seller",
            target_id=seller_id,
            details={
                "reason": reason,
                "level": warning_level,
                "totalWarnings": warning_count
            }
        )
        
        logger.info(f"Warning #{warning_count} issued to seller {seller_id}")
        
        return {
            "success": True,
            "message": f"Warning level {warning_level} issued",
            "totalWarnings": warning_count,
            "autoSuspendThreshold": 3
        }
    
    async def is_listing_visible(
        self,
        seller_id: ObjectId
    ) -> bool:
        """
        Check if seller's listings should be visible in search.
        
        Hidden if:
        - Status is suspended or banned
        - No active subscription (for some visibility tiers)
        """
        status = await self.get_seller_status(seller_id)
        
        if not status["exists"]:
            return False
        
        if status["status"] in [SellerStatus.SUSPENDED, SellerStatus.BANNED]:
            return False
        
        return True
    
    async def get_governance_summary(
        self,
        seller_id: ObjectId
    ) -> Dict[str, Any]:
        """
        Get complete governance summary for a seller.
        
        Used by admin to review seller account status.
        """
        status = await self.get_seller_status(seller_id)
        
        if not status["exists"]:
            return {"exists": False}
        
        # Get seller details
        seller = await self.db.users.find_one(
            {"_id": seller_id},
            {
                "email": 1,
                "profile": 1,
                "gst": 1,
                "createdAt": 1,
                "status": 1,
                "statusReason": 1,
                "warnings": 1
            }
        )
        
        # Get performance metrics
        from services.seller_performance_service import SellerPerformanceService
        perf_service = SellerPerformanceService(self.db)
        performance = await perf_service.calculate_seller_score(seller_id, include_suggestions=False)
        
        # Get listing count
        listing_count = await self.db.sellerListings.count_documents({
            "sellerId": seller_id
        })
        active_listings = await self.db.sellerListings.count_documents({
            "sellerId": seller_id,
            "isActive": True
        })
        
        return {
            "sellerId": str(seller_id),
            "email": seller.get("email"),
            "businessName": seller.get("profile", {}).get("businessName"),
            "createdAt": seller.get("createdAt").isoformat() if seller.get("createdAt") else None,
            "status": status["status"],
            "statusReason": status["reason"],
            "warningCount": status["warningCount"],
            "warnings": status["warnings"],
            "isGstVerified": status["isGstVerified"],
            "gstNumber": seller.get("gst", {}).get("number"),
            "performance": {
                "score": performance.get("score"),
                "tier": performance.get("tier"),
                "acceptanceRate": performance.get("metrics", {}).get("acceptanceRate"),
                "expiryRate": performance.get("metrics", {}).get("expiryRate"),
                "avgResponseTime": performance.get("metrics", {}).get("avgResponseTimeHours")
            },
            "listings": {
                "total": listing_count,
                "active": active_listings
            }
        }


async def get_seller_governance_service(db) -> SellerGovernanceService:
    """Factory function for seller governance service."""
    return SellerGovernanceService(db)
