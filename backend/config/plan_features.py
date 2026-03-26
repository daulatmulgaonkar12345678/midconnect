"""
PLAN FEATURES CONFIGURATION — Single Source of Truth
=====================================================
All plan limits, feature gates, and session limits are defined here.
DO NOT hardcode limits anywhere else in the codebase.

Plans: free, standard, pro, enterprise (NO trial, NO starter)

Usage:
    from config.plan_features import PLAN_CONFIG, FEATURE_MAP, get_plan_config, get_effective_limits
"""

from typing import Dict, Any

# ── Plan Feature Limits ──
# -1 means unlimited

PLAN_CONFIG = {
    "free": {
        "maxPanels": 3,
        "maxRules": 10,
        "maxInvoicesPerMonth": 10,
        "maxEmployees": 0,
        "export": False,
        "pdfExport": False,
        "automation": False,
        "maxSessions": 1,
        "label": "Free",
    },
    "standard": {
        "maxPanels": 10,
        "maxRules": 50,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": 15,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 3,
        "label": "Standard",
    },
    "pro": {
        "maxPanels": 50,
        "maxRules": 200,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": -1,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 5,
        "label": "Pro",
    },
    "enterprise": {
        "maxPanels": -1,
        "maxRules": -1,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": -1,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 10,
        "label": "Enterprise",
    },
}

# Backward compat alias
PLAN_FEATURES = PLAN_CONFIG

# Valid plan names
VALID_PLANS = list(PLAN_CONFIG.keys())

# ── Feature → Config Key Map ──
FEATURE_MAP = {
    "create_panel": "maxPanels",
    "create_rule": "maxRules",
    "create_invoice": "maxInvoicesPerMonth",
    "add_employee": "maxEmployees",
    "export_excel": "export",
    "export_pdf": "pdfExport",
    "run_automation": "automation",
}

# Active paid plans
PAID_PLANS = {"standard", "pro", "enterprise"}
UNLIMITED_INQUIRY_PLANS = {"standard", "pro", "enterprise"}


def get_plan_config(plan: str) -> dict:
    """Get default feature config for a plan. Falls back to free if unknown."""
    if plan not in PLAN_CONFIG:
        plan = "free"
    return PLAN_CONFIG[plan]


async def get_effective_limits(db, user: dict) -> Dict[str, Any]:
    """
    Core limit resolver. Merges plan defaults with per-seller overrides.

    Logic:
    1. Resolve the seller's plan from subscription
    2. Get default limits from PLAN_CONFIG
    3. Fetch overrides from subscription doc
    4. Merge: override takes priority over default
    5. Return effective limits + plan metadata

    Used everywhere for limit checks — panels, rules, exports, etc.
    """
    from utils.permissions import resolve_seller_id, is_platform_admin

    # Admin bypass — enterprise everything
    if is_platform_admin(user):
        return {
            **PLAN_CONFIG["enterprise"],
            "plan": "enterprise",
            "isExpired": False,
            "status": "active",
        }

    seller_id = resolve_seller_id(user)

    from bson import ObjectId
    if isinstance(seller_id, str):
        seller_id_oid = ObjectId(seller_id)
    else:
        seller_id_oid = seller_id

    # Get subscription doc
    sub = await db.subscriptions.find_one({"userId": seller_id_oid})

    if not sub:
        return {
            **PLAN_CONFIG["free"],
            "plan": "free",
            "isExpired": False,
            "status": "free",
        }

    plan = sub.get("planName", "free")
    status = sub.get("status", "free")

    # Validate plan
    if plan not in PLAN_CONFIG:
        plan = "free"

    # Check expiry
    is_expired = status in ("expired", "cancelled", "suspended")
    if is_expired:
        effective_plan = "free"
    else:
        # Check endDate for auto-expiry
        from datetime import datetime, timezone
        end_date = sub.get("endDate")
        if end_date and plan != "free":
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            if end_date < datetime.now(timezone.utc):
                is_expired = True
                status = "expired"
                effective_plan = "free"
            else:
                effective_plan = plan
        else:
            effective_plan = plan

    # Default limits from plan
    default_limits = dict(PLAN_CONFIG.get(effective_plan, PLAN_CONFIG["free"]))

    # Merge overrides (per-seller customization by admin)
    overrides = sub.get("overrides", {})
    if overrides:
        for key, value in overrides.items():
            if key in default_limits:
                default_limits[key] = value

    # Attach metadata
    default_limits["plan"] = plan
    default_limits["isExpired"] = is_expired
    default_limits["status"] = status

    return default_limits
