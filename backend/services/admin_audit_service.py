"""
ADMIN AUDIT LOG SERVICE - Phase A.10
====================================

RBAC Hardening + Comprehensive Audit Logging

Audit logging is MANDATORY for:
- Ranking config changes
- Subscription activation
- Seller suspension
- GST approval/rejection
- Manual lead override
- Admin actions

Collection: admin_audit_logs
"""

from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any, Optional, Literal
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Auditable actions."""
    # Subscription
    SUBSCRIPTION_ACTIVATE = "subscription.activate"
    SUBSCRIPTION_EXTEND = "subscription.extend"
    SUBSCRIPTION_CANCEL = "subscription.cancel"
    SUBSCRIPTION_MANUAL_OVERRIDE = "subscription.manual_override"
    
    # Seller Management
    SELLER_SUSPEND = "seller.suspend"
    SELLER_UNSUSPEND = "seller.unsuspend"
    SELLER_WARN = "seller.warn"
    SELLER_BAN = "seller.ban"
    
    # GST Verification
    GST_APPROVE = "gst.approve"
    GST_REJECT = "gst.reject"
    GST_REQUEST_RESUBMIT = "gst.request_resubmit"
    
    # Ranking
    RANKING_CONFIG_UPDATE = "ranking.config_update"
    RANKING_MANUAL_BOOST = "ranking.manual_boost"
    RANKING_MANUAL_PENALTY = "ranking.manual_penalty"
    
    # Lead Management
    LEAD_MANUAL_OVERRIDE = "lead.manual_override"
    LEAD_LIMIT_INCREASE = "lead.limit_increase"
    
    # Quote Management
    QUOTE_MANUAL_EXPIRE = "quote.manual_expire"
    QUOTE_MANUAL_STATUS_CHANGE = "quote.manual_status_change"
    
    # User Management
    USER_ROLE_CHANGE = "user.role_change"
    USER_STATUS_CHANGE = "user.status_change"
    
    # System
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    CRON_JOB_MANUAL_RUN = "cron.manual_run"


class AdminAuditService:
    """
    Admin Audit Log Service.
    
    Provides:
    - Comprehensive audit logging
    - RBAC enforcement helpers
    - Audit trail queries
    
    All admin actions must be logged via this service.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create indexes for audit log queries."""
        # Time-based queries
        await self.db.adminAuditLogs.create_index(
            [("timestamp", -1)],
            name="audit_timestamp_idx"
        )
        
        # Admin lookups
        await self.db.adminAuditLogs.create_index(
            [("adminId", 1), ("timestamp", -1)],
            name="audit_admin_idx"
        )
        
        # Action type queries
        await self.db.adminAuditLogs.create_index(
            [("action", 1), ("timestamp", -1)],
            name="audit_action_idx"
        )
        
        # Target entity queries
        await self.db.adminAuditLogs.create_index(
            [("targetType", 1), ("targetId", 1)],
            name="audit_target_idx"
        )
        
        logger.info("Audit log indexes ensured")
    
    async def log(
        self,
        admin_id: ObjectId,
        action: AuditAction,
        target_type: str,
        target_id: Optional[ObjectId],
        details: Dict[str, Any],
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Log an admin action.
        
        Args:
            admin_id: ID of admin performing action
            action: Action type from AuditAction enum
            target_type: Type of target (user, seller, subscription, etc.)
            target_id: ID of target entity
            details: Additional context about the action
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            ip_address: Admin's IP address
            user_agent: Admin's browser/client
            
        Returns:
            Audit log entry ID
        """
        now = datetime.now(timezone.utc)
        
        # Get admin info
        admin = await self.db.users.find_one(
            {"_id": admin_id},
            {"email": 1, "profile.businessName": 1}
        )
        admin_email = admin.get("email", "Unknown") if admin else "Unknown"
        
        audit_entry = {
            "_id": ObjectId(),
            "timestamp": now,
            "adminId": admin_id,
            "adminEmail": admin_email,
            "action": action.value if isinstance(action, AuditAction) else action,
            "targetType": target_type,
            "targetId": target_id,
            "details": details,
            "oldValue": old_value,
            "newValue": new_value,
            "metadata": {
                "ipAddress": ip_address,
                "userAgent": user_agent
            }
        }
        
        await self.db.adminAuditLogs.insert_one(audit_entry)
        
        logger.info(f"Audit: {admin_email} performed {action} on {target_type}/{target_id}")
        
        return str(audit_entry["_id"])
    
    async def log_ranking_config_change(
        self,
        admin_id: ObjectId,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> str:
        """Log ranking configuration change."""
        return await self.log(
            admin_id=admin_id,
            action=AuditAction.RANKING_CONFIG_UPDATE,
            target_type="system",
            target_id=None,
            details={
                "description": "Ranking weights configuration updated",
                "changedFields": list(set(old_config.keys()) | set(new_config.keys()))
            },
            old_value=old_config,
            new_value=new_config,
            ip_address=ip_address
        )
    
    async def log_subscription_activation(
        self,
        admin_id: ObjectId,
        seller_id: ObjectId,
        plan_name: str,
        duration_days: int,
        source: str,
        ip_address: Optional[str] = None
    ) -> str:
        """Log subscription activation."""
        return await self.log(
            admin_id=admin_id,
            action=AuditAction.SUBSCRIPTION_ACTIVATE,
            target_type="seller",
            target_id=seller_id,
            details={
                "planName": plan_name,
                "durationDays": duration_days,
                "activationSource": source
            },
            ip_address=ip_address
        )
    
    async def log_seller_suspension(
        self,
        admin_id: ObjectId,
        seller_id: ObjectId,
        reason: str,
        duration: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log seller suspension."""
        return await self.log(
            admin_id=admin_id,
            action=AuditAction.SELLER_SUSPEND,
            target_type="seller",
            target_id=seller_id,
            details={
                "reason": reason,
                "duration": duration or "indefinite"
            },
            ip_address=ip_address
        )
    
    async def log_gst_decision(
        self,
        admin_id: ObjectId,
        seller_id: ObjectId,
        decision: Literal["approve", "reject", "request_resubmit"],
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log GST verification decision."""
        action_map = {
            "approve": AuditAction.GST_APPROVE,
            "reject": AuditAction.GST_REJECT,
            "request_resubmit": AuditAction.GST_REQUEST_RESUBMIT
        }
        
        return await self.log(
            admin_id=admin_id,
            action=action_map[decision],
            target_type="seller",
            target_id=seller_id,
            details={
                "decision": decision,
                "reason": reason
            },
            ip_address=ip_address
        )
    
    async def get_audit_logs(
        self,
        admin_id: Optional[ObjectId] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[ObjectId] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Query audit logs with filters.
        """
        query = {}
        
        if admin_id:
            query["adminId"] = admin_id
        if action:
            query["action"] = action
        if target_type:
            query["targetType"] = target_type
        if target_id:
            query["targetId"] = target_id
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        # Count total
        total = await self.db.adminAuditLogs.count_documents(query)
        
        # Get logs
        skip = (page - 1) * limit
        cursor = self.db.adminAuditLogs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(limit)
        
        return {
            "logs": [self._serialize_log(log) for log in logs],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    async def get_recent_admin_actions(
        self,
        admin_id: ObjectId,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent actions by a specific admin."""
        cursor = self.db.adminAuditLogs.find(
            {"adminId": admin_id}
        ).sort("timestamp", -1).limit(limit)
        
        logs = await cursor.to_list(limit)
        return [self._serialize_log(log) for log in logs]
    
    async def get_entity_audit_trail(
        self,
        target_type: str,
        target_id: ObjectId
    ) -> List[Dict[str, Any]]:
        """Get all audit entries for a specific entity."""
        cursor = self.db.adminAuditLogs.find({
            "targetType": target_type,
            "targetId": target_id
        }).sort("timestamp", -1)
        
        logs = await cursor.to_list(100)
        return [self._serialize_log(log) for log in logs]
    
    def _serialize_log(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize audit log for API response."""
        return {
            "id": str(log["_id"]),
            "timestamp": log["timestamp"].isoformat() if log.get("timestamp") else None,
            "adminId": str(log["adminId"]) if log.get("adminId") else None,
            "adminEmail": log.get("adminEmail"),
            "action": log.get("action"),
            "targetType": log.get("targetType"),
            "targetId": str(log["targetId"]) if log.get("targetId") else None,
            "details": log.get("details"),
            "oldValue": log.get("oldValue"),
            "newValue": log.get("newValue")
        }


# RBAC Helper Functions

def require_role(user: Dict[str, Any], required_roles: list) -> bool:
    """
    Check if user has required role.
    
    Args:
        user: User document with 'roles' field
        required_roles: List of acceptable roles
        
    Returns:
        True if user has at least one required role
    """
    user_roles = user.get("roles", [])
    return any(role in user_roles for role in required_roles)


def is_admin(user: Dict[str, Any]) -> bool:
    """Check if user is admin."""
    return "admin" in user.get("roles", []) or user.get("isAdmin", False)


def is_seller(user: Dict[str, Any]) -> bool:
    """Check if user is seller."""
    return "seller" in user.get("roles", [])


def is_buyer(user: Dict[str, Any]) -> bool:
    """Check if user is buyer."""
    return "buyer" in user.get("roles", [])


def can_access_seller_data(user: Dict[str, Any], seller_id: ObjectId) -> bool:
    """
    Check if user can access seller data.
    
    Rules:
    - Admin: Can access all
    - Seller: Can access only own data
    - Buyer: Cannot access seller data
    """
    if is_admin(user):
        return True
    
    if is_seller(user):
        return str(user.get("_id")) == str(seller_id)
    
    return False


def can_access_quote(user: Dict[str, Any], quote: Dict[str, Any]) -> bool:
    """
    Check if user can access quote.
    
    Rules:
    - Admin: Can access all
    - Seller: Can access quotes they created
    - Buyer: Can access quotes addressed to them
    """
    if is_admin(user):
        return True
    
    user_id = str(user.get("_id"))
    
    if is_seller(user) and str(quote.get("sellerId")) == user_id:
        return True
    
    if is_buyer(user) and str(quote.get("buyerId")) == user_id:
        return True
    
    return False


async def get_admin_audit_service(db) -> AdminAuditService:
    """Factory function for admin audit service."""
    service = AdminAuditService(db)
    return service
