"""
ENTERPRISE SUBSCRIPTION SERVICE
SSOT: subscriptions collection

Business Rules:
- Active pro/enterprise: Unlimited leads
- Active trial: Defined limit
- Expired/cancelled/free: 5 leads per month
- Monthly reset on first of each month

No legacy fallbacks. No hacks. Production-grade.
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

FREE_MONTHLY_LIMIT = 5


async def get_effective_subscription(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Get the effective subscription state for a user.
    
    SSOT: Uses subscriptions collection ONLY.
    
    Returns:
        {
            "plan": "free" | "trial" | "pro" | "enterprise",
            "limit": int (-1 for unlimited),
            "isUnlimited": bool,
            "status": "free" | "active" | "trial" | "expired" | "cancelled",
            "subscriptionId": str | None
        }
    """
    now = datetime.now(timezone.utc)
    
    # Find active or trial subscription
    sub = await db.subscriptions.find_one({
        "userId": user_id,
        "status": {"$in": ["active", "trial"]}
    })
    
    # No active subscription → free plan
    if not sub:
        return {
            "plan": "free",
            "limit": FREE_MONTHLY_LIMIT,
            "isUnlimited": False,
            "status": "free",
            "subscriptionId": None
        }
    
    # Check expiry
    end_date = sub.get("endDate")
    if end_date and end_date < now:
        # Mark as expired in DB
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": "expired", "updatedAt": now}}
        )
        logger.info(f"Subscription expired for user {user_id}")
        
        # Expired → fallback to free (5/month)
        return {
            "plan": "free",
            "limit": FREE_MONTHLY_LIMIT,
            "isUnlimited": False,
            "status": "expired",
            "subscriptionId": str(sub["_id"])
        }
    
    plan = sub.get("planName", "free")
    
    # Pro and Enterprise are unlimited
    if plan in ["pro", "enterprise"]:
        return {
            "plan": plan,
            "limit": -1,
            "isUnlimited": True,
            "status": "active",
            "subscriptionId": str(sub["_id"])
        }
    
    # Trial or other plans have defined limits
    limit = sub.get("enquiryLimit", FREE_MONTHLY_LIMIT)
    
    return {
        "plan": plan,
        "limit": limit,
        "isUnlimited": False,
        "status": sub.get("status", "active"),
        "subscriptionId": str(sub["_id"])
    }


async def check_and_update_monthly_usage(db, user_id: ObjectId) -> int:
    """
    Check and update monthly usage counter.
    Resets on the first of each month.
    
    Returns: Current enquiries used this month
    """
    now = datetime.now(timezone.utc)
    
    sub = await db.subscriptions.find_one({"userId": user_id})
    
    if not sub:
        # No subscription record - return 0 (will use free tier defaults)
        return 0
    
    reset_date = sub.get("enquiriesResetAt")
    
    # Calculate next month's first day
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    
    # If never set → initialize
    if not reset_date:
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "enquiriesResetAt": next_month,
                "enquiriesUsed": 0,
                "updatedAt": now
            }}
        )
        return 0
    
    # If month reset passed → reset counter
    if reset_date < now:
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "enquiriesResetAt": next_month,
                "enquiriesUsed": 0,
                "updatedAt": now
            }}
        )
        logger.info(f"Monthly usage reset for user {user_id}")
        return 0
    
    return sub.get("enquiriesUsed", 0)


async def increment_enquiry_usage(db, user_id: ObjectId) -> int:
    """
    Increment the enquiry usage counter.
    Returns: New usage count
    """
    now = datetime.now(timezone.utc)
    
    result = await db.subscriptions.find_one_and_update(
        {"userId": user_id},
        {
            "$inc": {"enquiriesUsed": 1},
            "$set": {"updatedAt": now}
        },
        return_document=True
    )
    
    if result:
        return result.get("enquiriesUsed", 1)
    return 1


async def can_accept_inquiry(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Check if seller can accept a new inquiry.
    
    Returns:
        {
            "canAccept": bool,
            "reason": str | None,
            "subscription": {...},
            "usage": {
                "used": int,
                "limit": int,
                "remaining": int
            }
        }
    """
    subscription = await get_effective_subscription(db, user_id)
    used = await check_and_update_monthly_usage(db, user_id)
    
    # Unlimited plans can always accept
    if subscription["isUnlimited"]:
        return {
            "canAccept": True,
            "reason": None,
            "subscription": subscription,
            "usage": {
                "used": used,
                "limit": -1,
                "remaining": -1
            }
        }
    
    # Check limit
    limit = subscription["limit"]
    remaining = max(0, limit - used)
    
    if used >= limit:
        return {
            "canAccept": False,
            "reason": "Monthly enquiry limit reached",
            "subscription": subscription,
            "usage": {
                "used": used,
                "limit": limit,
                "remaining": 0
            }
        }
    
    return {
        "canAccept": True,
        "reason": None,
        "subscription": subscription,
        "usage": {
            "used": used,
            "limit": limit,
            "remaining": remaining
        }
    }


async def get_subscription_status_for_seller(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Get complete subscription status for seller dashboard.
    
    Returns frontend-ready subscription data.
    """
    subscription = await get_effective_subscription(db, user_id)
    used = await check_and_update_monthly_usage(db, user_id)
    
    now = datetime.now(timezone.utc)
    
    # Get raw subscription for dates
    raw_sub = await db.subscriptions.find_one({"userId": user_id})
    
    # Calculate days remaining
    days_remaining = None
    if raw_sub and raw_sub.get("endDate"):
        delta = raw_sub["endDate"] - now
        days_remaining = max(0, delta.days)
    
    # Calculate reset date
    reset_date = None
    if raw_sub and raw_sub.get("enquiriesResetAt"):
        reset_date = raw_sub["enquiriesResetAt"].strftime("%B 1, %Y")
    
    # Determine badge text
    if subscription["status"] == "active" and subscription["plan"] == "pro":
        badge = "Pro Active"
    elif subscription["status"] == "active" and subscription["plan"] == "enterprise":
        badge = "Enterprise Active"
    elif subscription["status"] == "trial":
        badge = f"Trial ({days_remaining} days left)" if days_remaining else "Trial"
    elif subscription["status"] == "expired":
        badge = "Expired – Free Mode (5/month)"
    else:
        badge = "Free Plan (5/month)"
    
    return {
        "subscription": {
            "planName": subscription["plan"],
            "status": subscription["status"],
            "isUnlimited": subscription["isUnlimited"],
            "daysRemaining": days_remaining,
            "isExpiringSoon": days_remaining is not None and days_remaining <= 7,
            "badge": badge
        },
        "usage": {
            "used": used,
            "limit": subscription["limit"],
            "remaining": -1 if subscription["isUnlimited"] else max(0, subscription["limit"] - used),
            "resetsOn": reset_date
        },
        "features": {
            "canAcceptInquiries": True,  # Always can accept (up to limit)
            "unlimitedInquiries": subscription["isUnlimited"],
            "verifiedBadge": subscription["plan"] in ["pro", "enterprise"],
            "prioritySupport": subscription["plan"] in ["pro", "enterprise"]
        }
    }
