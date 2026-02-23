"""
UNIFIED SUBSCRIPTION ENGINE
============================

SSOT for subscription management.
Supports both manual (admin) and payment-based activation.

Features:
- Single active subscription per user
- Idempotent payment processing
- Extension logic (extends existing subscription)
- No duplicate subscriptions
- Audit trail via subscriptionHistory

Schema:
{
    "_id": ObjectId,
    "userId": ObjectId,
    "planName": "free" | "trial" | "pro" | "enterprise",
    "status": "active" | "expired" | "suspended",
    "startDate": ISODate,
    "endDate": ISODate | null,
    "activationSource": "admin" | "payment" | "system",
    "paymentId": string | null,
    "activatedBy": ObjectId | null,
    "enquiryLimit": int,
    "enquiriesUsed": int,
    "enquiriesResetAt": ISODate,
    "createdAt": ISODate,
    "updatedAt": ISODate
}
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, Optional, Literal
import logging

logger = logging.getLogger(__name__)

# Plan configuration
PLAN_CONFIG = {
    "free": {
        "enquiry_limit": 5,
        "default_duration_days": 0,
        "subscription_weight": 0
    },
    "trial": {
        "enquiry_limit": -1,  # Unlimited during trial
        "default_duration_days": 14,
        "subscription_weight": 5
    },
    "pro": {
        "enquiry_limit": -1,  # Unlimited
        "default_duration_days": 30,
        "subscription_weight": 15
    },
    "enterprise": {
        "enquiry_limit": -1,  # Unlimited
        "default_duration_days": 365,
        "subscription_weight": 25
    }
}


class SubscriptionEngine:
    """
    Unified subscription management engine.
    
    Usage:
        engine = SubscriptionEngine(db)
        result = await engine.activate_or_extend(
            user_id=user_id,
            plan_name="pro",
            duration_days=30,
            source="payment",
            payment_id="pay_xyz123"
        )
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create required indexes for subscription collection."""
        # Compound index for user + status lookups
        await self.db.subscriptions.create_index(
            [("userId", 1), ("status", 1)],
            name="user_active_subscription_idx"
        )
        
        # Unique index for payment idempotency
        await self.db.subscriptions.create_index(
            [("paymentId", 1)],
            name="payment_idempotency_idx",
            unique=True,
            sparse=True  # Only index documents with paymentId
        )
        
        logger.info("Subscription indexes ensured")
    
    async def get_active_subscription(self, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get the active subscription for a user.
        
        Returns None if no active subscription found.
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        now = datetime.now(timezone.utc)
        
        # Find subscription with active/trial status
        sub = await self.db.subscriptions.find_one({
            "userId": user_id,
            "status": {"$in": ["active", "trial"]}
        })
        
        if not sub:
            # Check for any subscription (might be expired)
            sub = await self.db.subscriptions.find_one({"userId": user_id})
        
        if not sub:
            return None
        
        # Check if expired
        end_date = sub.get("endDate")
        if end_date:
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            if end_date < now and sub.get("status") in ["active", "trial"]:
                # Mark as expired
                await self.db.subscriptions.update_one(
                    {"_id": sub["_id"]},
                    {"$set": {"status": "expired", "updatedAt": now}}
                )
                sub["status"] = "expired"
        
        return sub
    
    async def activate_or_extend(
        self,
        user_id: ObjectId,
        plan_name: Literal["free", "trial", "pro", "enterprise"],
        duration_days: Optional[int] = None,
        source: Literal["admin", "payment", "system"] = "admin",
        payment_id: Optional[str] = None,
        activated_by: Optional[ObjectId] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Activate a new subscription or extend existing one.
        
        Logic:
        - If existing active subscription: extend endDate
        - If no subscription or expired: create/update to new plan
        - Never create duplicate active subscriptions
        - Idempotent for payment_id
        
        Args:
            user_id: User ObjectId
            plan_name: Subscription plan
            duration_days: Override default duration (optional)
            source: "admin", "payment", or "system"
            payment_id: Payment gateway ID (for payment source)
            activated_by: Admin user ID (for admin source)
            notes: Optional notes
        
        Returns:
            {
                "success": bool,
                "subscription": {...},
                "action": "created" | "extended" | "reactivated" | "idempotent",
                "message": str
            }
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        now = datetime.now(timezone.utc)
        
        # Idempotency check for payment
        if payment_id:
            existing_payment = await self.db.subscriptions.find_one({"paymentId": payment_id})
            if existing_payment:
                logger.info(f"Payment {payment_id} already processed - idempotent return")
                return {
                    "success": True,
                    "subscription": existing_payment,
                    "action": "idempotent",
                    "message": "Payment already processed"
                }
        
        # Get plan config
        config = PLAN_CONFIG.get(plan_name, PLAN_CONFIG["free"])
        duration = duration_days if duration_days is not None else config["default_duration_days"]
        
        # Calculate reset date (first of next month)
        if now.month == 12:
            next_reset = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_reset = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        # Get existing subscription
        existing = await self.db.subscriptions.find_one({"userId": user_id})
        
        if existing:
            # Extend or reactivate existing subscription
            return await self._extend_subscription(
                existing=existing,
                plan_name=plan_name,
                duration=duration,
                source=source,
                payment_id=payment_id,
                activated_by=activated_by,
                notes=notes,
                config=config,
                next_reset=next_reset,
                now=now
            )
        else:
            # Create new subscription
            return await self._create_subscription(
                user_id=user_id,
                plan_name=plan_name,
                duration=duration,
                source=source,
                payment_id=payment_id,
                activated_by=activated_by,
                notes=notes,
                config=config,
                next_reset=next_reset,
                now=now
            )
    
    async def _create_subscription(
        self,
        user_id: ObjectId,
        plan_name: str,
        duration: int,
        source: str,
        payment_id: Optional[str],
        activated_by: Optional[ObjectId],
        notes: Optional[str],
        config: Dict,
        next_reset: datetime,
        now: datetime
    ) -> Dict[str, Any]:
        """Create a new subscription."""
        
        # Calculate end date
        end_date = None if plan_name == "free" or duration == 0 else now + timedelta(days=duration)
        
        subscription_doc = {
            "userId": user_id,
            "planName": plan_name,
            "status": "active" if plan_name != "free" else "free",
            "startDate": now,
            "endDate": end_date,
            "durationDays": duration,
            "activationSource": source,
            "paymentId": payment_id,
            "activatedBy": activated_by,
            "enquiryLimit": config["enquiry_limit"],
            "enquiriesUsed": 0,
            "enquiriesResetAt": next_reset,
            "notes": notes or "",
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await self.db.subscriptions.insert_one(subscription_doc)
        subscription_doc["_id"] = result.inserted_id
        
        # Record history
        await self._record_history(
            user_id=user_id,
            action="created",
            old_subscription=None,
            new_subscription=subscription_doc,
            activated_by=activated_by,
            source=source,
            payment_id=payment_id,
            notes=notes
        )
        
        logger.info(f"Created {plan_name} subscription for user {user_id} via {source}")
        
        return {
            "success": True,
            "subscription": subscription_doc,
            "action": "created",
            "message": f"{plan_name.capitalize()} subscription created"
        }
    
    async def _extend_subscription(
        self,
        existing: Dict,
        plan_name: str,
        duration: int,
        source: str,
        payment_id: Optional[str],
        activated_by: Optional[ObjectId],
        notes: Optional[str],
        config: Dict,
        next_reset: datetime,
        now: datetime
    ) -> Dict[str, Any]:
        """Extend or reactivate existing subscription."""
        
        old_status = existing.get("status")
        old_plan = existing.get("planName")
        old_end = existing.get("endDate")
        
        # Determine new end date
        if plan_name == "free":
            new_end_date = None
        elif old_status == "active" and old_end:
            # Make timezone aware
            if old_end.tzinfo is None:
                old_end = old_end.replace(tzinfo=timezone.utc)
            # Extend from max(old_end, now)
            base_date = max(old_end, now)
            new_end_date = base_date + timedelta(days=duration)
        else:
            # Reactivating expired/cancelled - start fresh
            new_end_date = now + timedelta(days=duration) if duration > 0 else None
        
        # Determine action type
        if old_status in ["expired", "cancelled", "suspended"]:
            action = "reactivated"
            # Reset usage on reactivation
            enquiries_used = 0
        elif old_plan != plan_name:
            action = "upgraded" if PLAN_CONFIG.get(plan_name, {}).get("subscription_weight", 0) > PLAN_CONFIG.get(old_plan, {}).get("subscription_weight", 0) else "changed"
            enquiries_used = existing.get("enquiriesUsed", 0)
        else:
            action = "extended"
            enquiries_used = existing.get("enquiriesUsed", 0)
        
        update_doc = {
            "planName": plan_name,
            "status": "active" if plan_name != "free" else "free",
            "endDate": new_end_date,
            "durationDays": duration,
            "activationSource": source,
            "enquiryLimit": config["enquiry_limit"],
            "enquiriesUsed": enquiries_used,
            "updatedAt": now
        }
        
        # Only update paymentId if provided
        if payment_id:
            update_doc["paymentId"] = payment_id
        
        if activated_by:
            update_doc["activatedBy"] = activated_by
        
        if notes:
            update_doc["notes"] = notes
        
        await self.db.subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": update_doc}
        )
        
        # Merge for return
        updated_subscription = {**existing, **update_doc}
        
        # Record history
        await self._record_history(
            user_id=existing["userId"],
            action=action,
            old_subscription=existing,
            new_subscription=updated_subscription,
            activated_by=activated_by,
            source=source,
            payment_id=payment_id,
            notes=notes
        )
        
        logger.info(f"{action.capitalize()} subscription for user {existing['userId']} to {plan_name} via {source}")
        
        return {
            "success": True,
            "subscription": updated_subscription,
            "action": action,
            "message": f"Subscription {action}"
        }
    
    async def _record_history(
        self,
        user_id: ObjectId,
        action: str,
        old_subscription: Optional[Dict],
        new_subscription: Dict,
        activated_by: Optional[ObjectId],
        source: str,
        payment_id: Optional[str],
        notes: Optional[str]
    ):
        """Record subscription change in history collection."""
        now = datetime.now(timezone.utc)
        
        history_doc = {
            "userId": user_id,
            "action": action,
            "oldSubscription": old_subscription,
            "newSubscription": {k: v for k, v in new_subscription.items() if k != "_id"},
            "activatedBy": activated_by,
            "activationSource": source,
            "paymentId": payment_id,
            "notes": notes,
            "createdAt": now
        }
        
        await self.db.subscriptionHistory.insert_one(history_doc)
    
    async def check_payment_processed(self, payment_id: str) -> bool:
        """Check if a payment has already been processed (idempotency check)."""
        existing = await self.db.subscriptions.find_one({"paymentId": payment_id})
        return existing is not None
    
    async def get_subscription_for_ranking(self, seller_ids: list) -> Dict[str, str]:
        """
        Batch load subscription plans for ranking engine.
        
        Args:
            seller_ids: List of seller ObjectIds (as strings)
        
        Returns:
            Dict mapping seller_id -> plan_name
        """
        if not seller_ids:
            return {}
        
        # Convert to ObjectIds
        oids = [ObjectId(sid) for sid in seller_ids if ObjectId.is_valid(sid)]
        
        if not oids:
            return {}
        
        # Batch query
        cursor = self.db.subscriptions.find(
            {
                "userId": {"$in": oids},
                "status": {"$in": ["active", "trial"]}
            },
            {"userId": 1, "planName": 1, "status": 1, "endDate": 1}
        )
        
        now = datetime.now(timezone.utc)
        result = {}
        
        async for sub in cursor:
            user_id = str(sub["userId"])
            
            # Check if expired
            end_date = sub.get("endDate")
            if end_date:
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                if end_date < now:
                    result[user_id] = "free"  # Expired
                    continue
            
            result[user_id] = sub.get("planName", "free")
        
        return result


# Helper function for backward compatibility
async def get_subscription_engine(db) -> SubscriptionEngine:
    """Factory function to get subscription engine instance."""
    engine = SubscriptionEngine(db)
    return engine
