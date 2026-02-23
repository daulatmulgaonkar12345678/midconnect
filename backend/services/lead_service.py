"""
LEAD SERVICE - PHASE 1: Inquiry Acceptance & Lead Control
=========================================================

Lead Definition (SSOT):
- A lead is counted when inquiry.status changes from "pending" → "accepted"
- Free sellers: max 5 accepted leads per month
- Pro/Enterprise: Unlimited leads

This service is the SINGLE SOURCE OF TRUTH for lead counting and validation.
"""

from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Lead limits by subscription plan
LEAD_LIMITS = {
    "free": 5,
    "trial": 50,  # Trial gets 50 leads
    "pro": -1,    # Unlimited
    "enterprise": -1  # Unlimited
}


async def get_monthly_accepted_leads(db, seller_id: ObjectId) -> int:
    """
    Count accepted inquiries for seller in current month.
    
    SSOT: This is the authoritative count for lead usage.
    """
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    count = await db.inquiries.count_documents({
        "sellerId": seller_id,
        "status": "accepted",
        "acceptedAt": {"$gte": month_start}
    })
    
    return count


async def get_seller_subscription_plan(db, seller_id: ObjectId) -> Dict[str, Any]:
    """
    Get seller's effective subscription plan.
    
    Returns:
        {
            "plan": "free" | "trial" | "pro" | "enterprise",
            "isUnlimited": bool,
            "limit": int (-1 for unlimited),
            "status": "active" | "expired" | "free"
        }
    """
    # Check subscriptions collection first (SSOT for subscription)
    subscription = await db.subscriptions.find_one({
        "userId": seller_id,
        "status": {"$in": ["active", "trial"]}
    })
    
    if subscription:
        plan_name = subscription.get("planName", "free")
        status = subscription.get("status", "free")
        end_date = subscription.get("endDate")
        
        # Check if subscription is still valid
        if end_date:
            if isinstance(end_date, datetime):
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                if end_date < datetime.now(timezone.utc):
                    return {
                        "plan": "free",
                        "isUnlimited": False,
                        "limit": LEAD_LIMITS["free"],
                        "status": "expired"
                    }
        
        limit = LEAD_LIMITS.get(plan_name, LEAD_LIMITS["free"])
        
        return {
            "plan": plan_name,
            "isUnlimited": limit == -1,
            "limit": limit,
            "status": status
        }
    
    # Default to free plan
    return {
        "plan": "free",
        "isUnlimited": False,
        "limit": LEAD_LIMITS["free"],
        "status": "free"
    }


async def can_accept_lead(db, seller_id: ObjectId) -> Dict[str, Any]:
    """
    Check if seller can accept a new lead (inquiry).
    
    Business Rules:
    - Free plan: max 5 accepted inquiries per month
    - Pro/Enterprise: unlimited
    
    Returns:
        {
            "canAccept": bool,
            "reason": str | None,
            "message": str | None,
            "subscription": {...},
            "usage": {"used": int, "limit": int, "remaining": int}
        }
    """
    subscription = await get_seller_subscription_plan(db, seller_id)
    monthly_leads = await get_monthly_accepted_leads(db, seller_id)
    
    limit = subscription["limit"]
    is_unlimited = subscription["isUnlimited"]
    
    # Calculate remaining
    remaining = -1 if is_unlimited else max(0, limit - monthly_leads)
    
    usage = {
        "used": monthly_leads,
        "limit": limit,
        "remaining": remaining
    }
    
    # Check if expired
    if subscription["status"] == "expired":
        return {
            "canAccept": False,
            "reason": "SUBSCRIPTION_EXPIRED",
            "message": "Your subscription has expired. Please renew to continue accepting leads.",
            "subscription": subscription,
            "usage": usage,
            "upgradeUrl": "/seller/subscription"
        }
    
    # Unlimited plan - always allow
    if is_unlimited:
        return {
            "canAccept": True,
            "reason": None,
            "message": None,
            "subscription": subscription,
            "usage": usage
        }
    
    # Check limit for limited plans
    if monthly_leads >= limit:
        return {
            "canAccept": False,
            "reason": "LIMIT_REACHED",
            "message": f"Lead limit reached. Upgrade to unlock unlimited leads.",
            "notification": f"You've reached your monthly limit of {limit} accepted inquiries. Upgrade to Pro for unlimited access.",
            "subscription": subscription,
            "usage": usage,
            "upgradeUrl": "/seller/subscription"
        }
    
    return {
        "canAccept": True,
        "reason": None,
        "message": None,
        "subscription": subscription,
        "usage": usage
    }


async def increment_lead_count(db, seller_id: ObjectId) -> int:
    """
    Increment seller's monthly lead count.
    
    Note: This doesn't actually store a counter - the count is calculated
    from inquiries with status='accepted' and acceptedAt in current month.
    
    This function is for analytics tracking purposes only.
    The actual count is always derived from inquiry status changes.
    
    Returns:
        New count after increment (calculated)
    """
    # Just return the current count + 1
    # The actual increment happens when inquiry.status changes to 'accepted'
    return await get_monthly_accepted_leads(db, seller_id)


async def get_lead_stats(db, seller_id: ObjectId) -> Dict[str, Any]:
    """
    Get comprehensive lead statistics for seller.
    """
    subscription = await get_seller_subscription_plan(db, seller_id)
    monthly_leads = await get_monthly_accepted_leads(db, seller_id)
    
    now = datetime.now(timezone.utc)
    
    # Calculate days until reset (first of next month)
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    
    days_until_reset = (next_month - now).days
    
    return {
        "plan": subscription["plan"],
        "isUnlimited": subscription["isUnlimited"],
        "monthlyUsed": monthly_leads,
        "monthlyLimit": subscription["limit"],
        "remaining": -1 if subscription["isUnlimited"] else max(0, subscription["limit"] - monthly_leads),
        "daysUntilReset": days_until_reset,
        "resetsAt": next_month.isoformat()
    }
