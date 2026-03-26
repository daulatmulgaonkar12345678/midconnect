"""
ENTERPRISE SUBSCRIPTION SERVICE
SSOT: subscriptions collection

Business Rules:
- Active standard/pro/enterprise: Unlimited leads (enquiriesUsed does NOT increment)
- Expired/cancelled/free: 5 leads per month (enquiriesUsed increments)
- Monthly reset on first of each month via enquiriesResetAt

No legacy fallbacks. No hacks. Production-grade.

IMPORTANT: This is the ONLY source of truth for subscription logic.
Do NOT use server.py's SUBSCRIPTION_PLANS, get_subscription_status(), 
count_accepted_inquiries_this_month(), or check_can_accept_inquiry().
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
    
    Flow:
    1. Query subscriptions collection for this user
    2. If no subscription or status not active → free
    3. If endDate < now → mark expired in DB, return free
    4. If standard/pro/enterprise → unlimited
    5. Otherwise → use enquiryLimit from DB
    
    Returns:
        {
            "plan": "free" | "standard" | "pro" | "enterprise",
            "limit": int (-1 for unlimited),
            "isUnlimited": bool,
            "status": "free" | "active" | "expired" | "cancelled",
            "subscriptionId": str | None,
            "endDate": datetime | None
        }
    """
    now = datetime.now(timezone.utc)
    
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    # Find subscription for user (any status - we'll check status ourselves)
    sub = await db.subscriptions.find_one({"userId": user_id})
    
    # No subscription record at all → free plan
    if not sub:
        return {
            "plan": "free",
            "limit": FREE_MONTHLY_LIMIT,
            "isUnlimited": False,
            "status": "free",
            "subscriptionId": None,
            "endDate": None
        }
    
    current_status = sub.get("status", "free")
    plan = sub.get("planName", "free")
    end_date = sub.get("endDate")
    
    # If status is already expired/cancelled/suspended → free
    if current_status in ["expired", "cancelled", "suspended"]:
        return {
            "plan": "free",
            "limit": FREE_MONTHLY_LIMIT,
            "isUnlimited": False,
            "status": current_status,
            "subscriptionId": str(sub["_id"]),
            "endDate": end_date
        }
    
    # If plan is free → return free
    if plan == "free":
        return {
            "plan": "free",
            "limit": FREE_MONTHLY_LIMIT,
            "isUnlimited": False,
            "status": "free",
            "subscriptionId": str(sub["_id"]),
            "endDate": None
        }
    
    # For paid plans, check expiry
    if end_date:
        # Make timezone aware if needed
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        if end_date < now:
            # Mark as expired in DB (don't wait for it)
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
                "subscriptionId": str(sub["_id"]),
                "endDate": end_date
            }
    
    # Standard, Pro, Enterprise are unlimited inquiry plans
    if plan in ["standard", "pro", "enterprise"]:
        return {
            "plan": plan,
            "limit": -1,
            "isUnlimited": True,
            "status": "active",
            "subscriptionId": str(sub["_id"]),
            "endDate": end_date
        }
    
    # Fallback for unknown plans
    limit = sub.get("enquiryLimit", FREE_MONTHLY_LIMIT)
    
    return {
        "plan": plan,
        "limit": limit,
        "isUnlimited": False,
        "status": sub.get("status", "active"),
        "subscriptionId": str(sub["_id"]),
        "endDate": end_date
    }


async def check_and_update_monthly_usage(db, user_id: ObjectId) -> int:
    """
    Check and update monthly usage counter.
    Resets on the first of each month.
    
    IMPORTANT: This checks the reset date and resets if needed,
    but does NOT increment the counter. Use increment_enquiry_usage() for that.
    
    Returns: Current enquiries used this month (after any reset)
    """
    now = datetime.now(timezone.utc)
    
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
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
    
    # Make reset_date timezone aware if needed
    if reset_date.tzinfo is None:
        reset_date = reset_date.replace(tzinfo=timezone.utc)
    
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
    
    IMPORTANT: Only call this for NON-UNLIMITED plans.
    For pro/enterprise (unlimited), do NOT call this.
    
    Returns: New usage count
    """
    now = datetime.now(timezone.utc)
    
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    result = await db.subscriptions.find_one_and_update(
        {"userId": user_id},
        {
            "$inc": {"enquiriesUsed": 1},
            "$set": {"updatedAt": now}
        },
        return_document=True
    )
    
    if result:
        new_count = result.get("enquiriesUsed", 1)
        logger.info(f"Incremented enquiry usage for user {user_id} to {new_count}")
        return new_count
    return 1


async def can_accept_inquiry(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Check if seller can accept a new inquiry.
    
    ENTERPRISE SUBSCRIPTION FLOW:
    1. get_effective_subscription() → determines plan and limits
    2. check_and_update_monthly_usage() → gets current usage (handles reset)
    3. If unlimited → canAccept: True
    4. If used >= limit → canAccept: False with detailed error
    5. Otherwise → canAccept: True
    
    Returns:
        {
            "canAccept": bool,
            "reason": str | None (error code like "LIMIT_REACHED"),
            "subscription": {...},
            "usage": {
                "used": int,
                "limit": int,
                "remaining": int (-1 for unlimited)
            },
            "notification": str | None (user-friendly message),
            "upgradeUrl": str | None
        }
    """
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    subscription = await get_effective_subscription(db, user_id)
    used = await check_and_update_monthly_usage(db, user_id)
    
    # Calculate next reset date for error messages
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_reset = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_reset = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    
    reset_days = (next_reset - now).days
    
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
            },
            "notification": None,
            "upgradeUrl": None
        }
    
    # Check limit
    limit = subscription["limit"]
    remaining = max(0, limit - used)
    
    if used >= limit:
        return {
            "canAccept": False,
            "reason": "LIMIT_REACHED",
            "subscription": subscription,
            "usage": {
                "used": used,
                "limit": limit,
                "remaining": 0
            },
            "notification": f"You've reached your monthly limit of {limit} leads. Upgrade to Pro for unlimited access.",
            "upgradeUrl": "/seller/subscription",
            "resetsInDays": reset_days
        }
    
    return {
        "canAccept": True,
        "reason": None,
        "subscription": subscription,
        "usage": {
            "used": used,
            "limit": limit,
            "remaining": remaining
        },
        "notification": None,
        "upgradeUrl": None
    }


async def get_subscription_status_for_seller(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Get complete subscription status for seller dashboard.
    
    Returns frontend-ready subscription data.
    
    This is the ONLY function that should be used for seller subscription UI.
    """
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    subscription = await get_effective_subscription(db, user_id)
    used = await check_and_update_monthly_usage(db, user_id)
    
    now = datetime.now(timezone.utc)
    
    # Get raw subscription for dates
    raw_sub = await db.subscriptions.find_one({"userId": user_id})
    
    # Calculate days remaining
    days_remaining = None
    end_date = subscription.get("endDate")
    if end_date:
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        delta = end_date - now
        days_remaining = max(0, delta.days)
    
    # Calculate reset date
    reset_date = None
    if raw_sub and raw_sub.get("enquiriesResetAt"):
        reset_dt = raw_sub["enquiriesResetAt"]
        if isinstance(reset_dt, datetime):
            reset_date = reset_dt.strftime("%B 1, %Y")
    
    # Determine badge text
    plan = subscription["plan"]
    status = subscription["status"]
    
    if status == "active" and plan == "pro":
        badge = "Pro Active"
    elif status == "active" and plan == "enterprise":
        badge = "Enterprise Active"
    elif status == "active" and plan == "standard":
        badge = f"Standard Active ({days_remaining} days left)" if days_remaining else "Standard Active"
    elif status == "expired":
        badge = "Expired – Free Mode (5/month)"
    else:
        badge = "Free Plan (5/month)"
    
    return {
        "subscription": {
            "planName": plan,
            "status": status,
            "isUnlimited": subscription["isUnlimited"],
            "daysRemaining": days_remaining,
            "isExpiringSoon": days_remaining is not None and days_remaining <= 7,
            "badge": badge,
            "endDate": end_date.isoformat() if end_date else None
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
            "verifiedBadge": plan in ["pro", "enterprise"],
            "prioritySupport": plan in ["pro", "enterprise"]
        },
        "showUpgradeCta": plan == "free" or status == "expired"
    }


async def ensure_subscription_exists(db, user_id: ObjectId) -> Dict[str, Any]:
    """
    Ensure a subscription record exists for the user.
    If not, create a default free subscription.
    
    Used by admin activation to ensure we have a record to update.
    
    Returns the subscription document.
    """
    # Ensure user_id is ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    sub = await db.subscriptions.find_one({"userId": user_id})
    
    if not sub:
        now = datetime.now(timezone.utc)
        # Calculate next month for reset date
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        sub = {
            "userId": user_id,
            "planName": "free",
            "status": "free",
            "startDate": now,
            "endDate": None,
            "enquiryLimit": FREE_MONTHLY_LIMIT,
            "enquiriesUsed": 0,
            "enquiriesResetAt": next_month,
            "createdAt": now,
            "updatedAt": now
        }
        await db.subscriptions.insert_one(sub)
        logger.info(f"Created default subscription for user {user_id}")
    
    return sub
