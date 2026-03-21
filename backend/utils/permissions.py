"""
Shared permission utilities for all routers.
Single source of truth for auth, role checks, and seller scoping.
"""

from fastapi import HTTPException
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


def normalize_permissions(perms: dict) -> dict:
    """Convert old {module: {view, action}} format to new {modules: {}, panels: {}} format."""
    if not perms:
        return {"modules": {}, "panels": {}}
    if "modules" in perms:
        return perms
    # Old format: { "inventory": {"view": true, "action": true}, ... }
    modules = {}
    for key, val in perms.items():
        if isinstance(val, dict) and ("view" in val or "action" in val):
            modules[key] = val.get("view", False)
        elif isinstance(val, bool):
            modules[key] = val
    return {"modules": modules, "panels": {}}


def is_platform_admin(user: dict) -> bool:
    """Check if user is a platform admin."""
    return user.get("isAdmin") is True or "admin" in user.get("roles", [])


def get_account_type(user: dict) -> str:
    """Get account type with safe default."""
    if is_platform_admin(user):
        return "admin"
    return user.get("accountType", "seller")


def resolve_seller_id(user: dict) -> str:
    """
    Get seller ID for the current user.
    - seller: returns own _id
    - employee (linked via companyId): returns companyId
    - admin: returns None (admin sees all)
    """
    account_type = get_account_type(user)

    if account_type == "admin":
        return None

    company_id = user.get("companyId")
    employee_status = user.get("employeeStatus")
    if company_id and employee_status in ("active", "disabled"):
        return str(company_id)

    if account_type == "employee":
        seller_id = user.get("sellerId")
        if not seller_id:
            raise HTTPException(status_code=403, detail="Employee not linked to seller")
        return str(seller_id)

    return str(user.get("_id"))


async def check_user_permission(db, user: dict, permission: str) -> bool:
    """
    Check if user has a specific permission.
    Supports both old and new permission formats.
    """
    if is_platform_admin(user):
        return True

    account_type = user.get("accountType", "seller")
    if account_type == "seller":
        return True

    emp_perms = user.get("employeePermissions")
    emp_status = user.get("employeeStatus")
    if emp_perms and emp_status == "active":
        perm_map = {
            "create_invoice": "invoices",
            "manage_buyers": "buyers",
            "manage_suppliers": "suppliers",
            "manage_inventory": "inventory",
            "manage_listings": "inventory",
            "view_reports": "reports",
            "view_enquiries": "dashboard",
            "view_purchase_price": "inventory",
            "manage_employees": "employees",
            "manage_roles": "employees",
        }
        module = perm_map.get(permission)
        if module:
            normalized = normalize_permissions(emp_perms)
            return normalized.get("modules", {}).get(module, False) is True
        return False

    role_id = user.get("roleId")
    if not role_id:
        return False

    try:
        role = await db.roles.find_one({"_id": ObjectId(str(role_id)), "isActive": True})
        if role and permission in role.get("permissions", []):
            return True
    except Exception:
        pass

    return False


async def require_user_permission(db, user: dict, permission: str):
    """Require a specific permission or raise 403."""
    has_perm = await check_user_permission(db, user, permission)
    if not has_perm:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {permission} required"
        )


async def authenticate_user(db, verify_token_func, authorization: str) -> dict:
    """
    Verify auth token and return user from database.
    Shared across all routers.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        decoded_token = await verify_token_func(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not decoded_token:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.users.find_one({"firebaseUid": firebase_uid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("accountStatus") == "deleted":
        raise HTTPException(status_code=403, detail="Account has been deactivated")

    if user.get("accountType") == "employee" and user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Employee account is inactive")

    if user.get("employeeStatus") == "disabled" and user.get("companyId"):
        raise HTTPException(status_code=403, detail="Employee account is disabled")

    return user
