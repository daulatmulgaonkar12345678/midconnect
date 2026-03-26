"""
PLAN FEATURES CONFIGURATION — Single Source of Truth
=====================================================
All plan limits, feature gates, and session limits are defined here.
DO NOT hardcode limits anywhere else in the codebase.

Usage:
    from config.plan_features import PLAN_FEATURES, FEATURE_MAP, get_plan_config
"""

# ── Plan Feature Limits ──
# -1 means unlimited

PLAN_FEATURES = {
    "free": {
        "maxPanels": 3,
        "maxRules": 5,
        "maxInvoicesPerMonth": 10,
        "maxEmployees": 0,
        "export": False,
        "pdfExport": False,
        "automation": False,
        "maxSessions": 1,
        "label": "Free",
    },
    "trial": {
        "maxPanels": 5,
        "maxRules": 20,
        "maxInvoicesPerMonth": 50,
        "maxEmployees": 2,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 2,
        "label": "Trial",
    },
    "starter": {
        "maxPanels": 10,
        "maxRules": 50,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": 5,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 3,
        "label": "Starter",
    },
    "standard": {
        "maxPanels": 25,
        "maxRules": 100,
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

# Active paid plans (subscription is considered active for these)
PAID_PLANS = {"starter", "standard", "pro", "enterprise"}
UNLIMITED_INQUIRY_PLANS = {"starter", "standard", "pro", "enterprise"}


def get_plan_config(plan: str) -> dict:
    """Get feature config for a plan. Falls back to free if unknown."""
    return PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
