"""
Shared permission utilities for all routers.
Single source of truth for auth, role checks, and seller scoping.
"""

from fastapi import HTTPException
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


def normalize_permissions(perms: dict) -> dict:
    """Convert any permission format to the canonical format:
    {modules: {key: {view: bool, edit: bool}}, panels: {id: {canView, canCreate, canEdit}}}

    Handles:
    1. Old format: {inventory: {view: true, action: true}}
    2. Boolean format: {modules: {inventory: true}}
    3. New format: {modules: {inventory: {view: true, edit: true}}, panels: {...}}
    """
    if not perms:
        return {"modules": {}, "panels": {}}

    if "modules" in perms:
        raw_modules = perms.get("modules", {})
        normalized_modules = {}
        for key, val in raw_modules.items():
            if isinstance(val, dict) and ("view" in val or "edit" in val):
                normalized_modules[key] = {"view": val.get("view", False), "edit": val.get("edit", False)}
            elif isinstance(val, bool):
                normalized_modules[key] = {"view": val, "edit": val}
            else:
                normalized_modules[key] = {"view": False, "edit": False}
        return {"modules": normalized_modules, "panels": perms.get("panels", {})}

    # Old format: { "inventory": {"view": true, "action": true}, ... }
    modules = {}
    for key, val in perms.items():
        if isinstance(val, dict) and ("view" in val or "action" in val):
            modules[key] = {"view": val.get("view", False), "edit": val.get("action", False)}
        elif isinstance(val, bool):
            modules[key] = {"view": val, "edit": val}
    return {"modules": modules, "panels": {}}


def is_platform_admin(user: dict) -> bool:
    return user.get("isAdmin") is True or "admin" in user.get("roles", [])


def get_account_type(user: dict) -> str:
    if is_platform_admin(user):
        return "admin"
    return user.get("accountType", "seller")


def resolve_seller_id(user: dict) -> str:
    account_type = get_account_type(user)
    
    # For platform admins who are also sellers, use their _id as seller ID
    # This allows admins to manage their own business tools
    if account_type == "admin":
        # Check if admin has seller role or accountType
        roles = user.get("roles", [])
        if "seller" in roles or user.get("accountType") == "seller":
            return str(user.get("_id"))
        # Pure admin without seller role - use their _id for business tools
        return str(user.get("_id"))

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
    if is_platform_admin(user):
        return True

    account_type = user.get("accountType", "seller")
    if account_type == "seller":
        return True

    emp_perms = user.get("employeePermissions")
    emp_status = user.get("employeeStatus")
    if emp_perms and emp_status == "active":
        perm_map = {
            "create_invoice": ("invoices", "edit"),
            "manage_buyers": ("buyers", "edit"),
            "manage_suppliers": ("suppliers", "edit"),
            "manage_inventory": ("inventory", "edit"),
            "manage_listings": ("inventory", "edit"),
            "view_reports": ("reports", "view"),
            "view_enquiries": ("dashboard", "view"),
            "view_purchase_price": ("inventory", "view"),
            "manage_employees": ("employees", "edit"),
            "manage_roles": ("employees", "edit"),
        }
        mapping = perm_map.get(permission)
        if mapping:
            module, level = mapping
            normalized = normalize_permissions(emp_perms)
            mod_perms = normalized.get("modules", {}).get(module, {})
            if isinstance(mod_perms, dict):
                return mod_perms.get(level, False) is True
            if isinstance(mod_perms, bool):
                return mod_perms
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
    has_perm = await check_user_permission(db, user, permission)
    if not has_perm:
        raise HTTPException(status_code=403, detail=f"Permission denied: {permission} required")


async def authenticate_user(db, verify_token_func, authorization: str) -> dict:
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
    
    # EMPLOYEE ACCESS ENFORCEMENT: Check if boss's maxEmployees allows employee access
    company_id = user.get("companyId") or user.get("companyOwnerId")
    employee_status = user.get("employeeStatus")
    if company_id and employee_status in ("active", "disabled"):
        if not is_platform_admin(user):
            try:
                from config.plan_features import get_effective_limits
                boss_user = {"_id": company_id, "roles": ["seller"], "isSeller": True}
                limits = await get_effective_limits(db, boss_user)
                max_employees = limits.get("maxEmployees", 0)
                if max_employees == 0:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "EMPLOYEE_ACCESS_BLOCKED",
                            "message": "Your employer's subscription does not include employee access. Please contact your employer to upgrade their plan.",
                        }
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"[EMPLOYEE_GUARD] Error checking employee limits: {e}")
    
    return user
