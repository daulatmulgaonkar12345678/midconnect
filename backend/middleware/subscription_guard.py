"""
SUBSCRIPTION GUARD — Central Subscription Enforcement
======================================================
Reusable functions to enforce subscription status and feature limits
across all routes. Import and call in any route handler.

Usage:
    from middleware.subscription_guard import enforce_subscription, check_resource_limit

    # In a write endpoint:
    sub = await enforce_subscription(db, user, feature="create_panel")

    # For resource limits (panels, rules, etc.):
    await check_resource_limit(db, user, "create_panel", current_count=panel_count)

    # For read-only (GET) endpoints — only blocks if hard lockout needed:
    sub = await enforce_subscription(db, user, write_operation=False)
"""

from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime, timezone
import hashlib
import logging

from config.plan_features import PLAN_FEATURES, FEATURE_MAP, get_plan_config

logger = logging.getLogger(__name__)


async def get_user_subscription(db, user: dict) -> dict:
    """
    Get effective subscription for a user.
    Handles employees (uses company owner's subscription).
    Returns: {plan, status, isExpired, config, endDate, subscriptionId}
    """
    from utils.permissions import resolve_seller_id, is_platform_admin

    # Admin bypass
    if is_platform_admin(user):
        return {
            "plan": "enterprise",
            "status": "active",
            "isExpired": False,
            "config": PLAN_FEATURES["enterprise"],
            "endDate": None,
            "subscriptionId": None,
        }

    seller_id = resolve_seller_id(user)

    from services.subscription_service import get_effective_subscription
    sub = await get_effective_subscription(db, ObjectId(seller_id))

    plan = sub.get("plan", "free")
    status = sub.get("status", "free")
    is_expired = status in ("expired", "cancelled", "suspended")

    return {
        "plan": plan,
        "status": status,
        "isExpired": is_expired,
        "config": get_plan_config(plan if not is_expired else "free"),
        "endDate": sub.get("endDate"),
        "subscriptionId": sub.get("subscriptionId"),
    }


async def enforce_subscription(db, user: dict, feature: str = None, write_operation: bool = True) -> dict:
    """
    Central subscription enforcement. Call in any route handler.

    Rules:
    - Expired + write operation → BLOCKED (read-only mode)
    - Feature not in plan → BLOCKED
    - Otherwise → ALLOWED

    Args:
        db: MongoDB database
        user: Authenticated user dict
        feature: Feature key from FEATURE_MAP (e.g., "create_panel", "export_excel")
        write_operation: True for POST/PUT/DELETE, False for GET

    Returns:
        Subscription info dict if allowed

    Raises:
        HTTPException 403 if blocked
    """
    sub_info = await get_user_subscription(db, user)

    # RULE 1: Expired + write → BLOCKED
    if sub_info["isExpired"] and write_operation:
        logger.warning(f"[SUB_GUARD] BLOCKED expired user {user.get('_id')} write op. feature={feature}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "SUBSCRIPTION_EXPIRED",
                "message": "Your plan has expired. Renew to continue editing.",
                "currentPlan": sub_info["plan"],
                "status": sub_info["status"],
                "upgradeUrl": "/seller/subscription",
            }
        )

    # RULE 2: Feature check
    if feature:
        config = sub_info["config"]
        feature_key = FEATURE_MAP.get(feature)

        if feature_key:
            feature_value = config.get(feature_key)

            # Boolean features (export, automation, pdfExport)
            if isinstance(feature_value, bool) and not feature_value:
                logger.warning(f"[SUB_GUARD] BLOCKED feature={feature} for plan={sub_info['plan']} user={user.get('_id')}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "FEATURE_NOT_AVAILABLE",
                        "message": f"This feature is not available on your {sub_info['config'].get('label', sub_info['plan'])} plan. Please upgrade.",
                        "feature": feature,
                        "currentPlan": sub_info["plan"],
                        "upgradeUrl": "/seller/subscription",
                    }
                )

    return sub_info


async def check_resource_limit(db, user: dict, feature: str, current_count: int) -> dict:
    """
    Check if user can create more of a resource (panels, rules, invoices).
    Calls enforce_subscription first, then checks numeric limit.

    Args:
        db: MongoDB database
        user: Authenticated user dict
        feature: Feature key (e.g., "create_panel")
        current_count: Current resource count for this user

    Returns:
        Subscription info dict

    Raises:
        HTTPException 403 if limit reached or subscription blocked
    """
    sub_info = await enforce_subscription(db, user, feature=feature, write_operation=True)

    config = sub_info["config"]
    feature_key = FEATURE_MAP.get(feature)

    if not feature_key:
        return sub_info

    limit = config.get(feature_key, 0)

    # -1 means unlimited
    if limit == -1:
        return sub_info

    if current_count >= limit:
        plan_label = config.get("label", sub_info["plan"])
        logger.warning(f"[SUB_GUARD] LIMIT_REACHED feature={feature} count={current_count}/{limit} plan={sub_info['plan']} user={user.get('_id')}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "LIMIT_REACHED",
                "message": f"You've reached the limit of {limit} for your {plan_label} plan. Upgrade to increase your limit.",
                "feature": feature,
                "limit": limit,
                "current": current_count,
                "currentPlan": sub_info["plan"],
                "upgradeUrl": "/seller/subscription",
            }
        )

    return sub_info


# ── Session Control ──

async def enforce_session_limit(db, user: dict, device_fingerprint: str) -> None:
    """
    Track and enforce device/session limits.

    Logic:
    1. Upsert current device session
    2. Count active sessions (active in last 30 min)
    3. If count > plan limit, invalidate oldest sessions
    4. If THIS session was invalidated, block access

    Args:
        db: MongoDB database
        user: Authenticated user dict
        device_fingerprint: Hash of user-agent or device info
    """
    from utils.permissions import is_platform_admin

    if is_platform_admin(user):
        return

    user_id = user.get("_id")
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    now = datetime.now(timezone.utc)

    # Upsert this device session
    await db.active_sessions.update_one(
        {"userId": user_id, "deviceFingerprint": device_fingerprint},
        {"$set": {
            "lastActive": now,
            "updatedAt": now,
        }, "$setOnInsert": {
            "userId": user_id,
            "deviceFingerprint": device_fingerprint,
            "createdAt": now,
            "isValid": True,
        }},
        upsert=True,
    )

    # Get plan session limit
    sub_info = await get_user_subscription(db, user)
    max_sessions = sub_info["config"].get("maxSessions", 1)

    # Count active sessions (active in last 30 min)
    from datetime import timedelta
    cutoff = now - timedelta(minutes=30)
    active_sessions = await db.active_sessions.find(
        {"userId": user_id, "lastActive": {"$gte": cutoff}, "isValid": True}
    ).sort("lastActive", -1).to_list(max_sessions + 5)

    if len(active_sessions) > max_sessions:
        # Keep newest max_sessions, invalidate the rest
        to_keep = {str(s["_id"]) for s in active_sessions[:max_sessions]}
        to_invalidate = [s["_id"] for s in active_sessions if str(s["_id"]) not in to_keep]

        if to_invalidate:
            await db.active_sessions.update_many(
                {"_id": {"$in": to_invalidate}},
                {"$set": {"isValid": False, "invalidatedAt": now}}
            )
            logger.info(f"[SESSION] Invalidated {len(to_invalidate)} old sessions for user {user_id}")

    # Check if THIS session is still valid
    this_session = await db.active_sessions.find_one(
        {"userId": user_id, "deviceFingerprint": device_fingerprint}
    )
    if this_session and not this_session.get("isValid", True):
        logger.warning(f"[SESSION] BLOCKED invalid session for user {user_id}, device={device_fingerprint[:8]}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "SESSION_LIMIT_EXCEEDED",
                "message": "You are logged in on too many devices. Please log out from another device.",
                "maxSessions": max_sessions,
            }
        )


def get_device_fingerprint(user_agent: str = "", client_ip: str = "") -> str:
    """Generate a stable device fingerprint from user-agent."""
    raw = f"{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
