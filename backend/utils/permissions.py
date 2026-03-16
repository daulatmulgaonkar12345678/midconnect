"""
Shared permission utilities for all routers.
Single source of truth for auth, role checks, and seller scoping.
"""

from fastapi import HTTPException
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


def is_platform_admin(user: dict) -> bool:
    """Check if user is a platform admin."""
    return user.get("isAdmin") is True or "admin" in user.get("roles", [])


def get_account_type(user: dict) -> str:
    """Get account type with safe default. Returns 'admin', 'employee', or 'seller'."""
    if is_platform_admin(user):
        return "admin"
    return user.get("accountType", "seller")


def resolve_seller_id(user: dict) -> str:
    """
    Get seller ID for the current user.
    - seller: returns own _id
    - employee: returns linked sellerId
    - admin: returns None (admin sees all)
    Raises 403 if employee is not linked.
    """
    account_type = get_account_type(user)

    if account_type == "admin":
        return None

    if account_type == "employee":
        seller_id = user.get("sellerId")
        if not seller_id:
            raise HTTPException(status_code=403, detail="Employee not linked to seller")
        return str(seller_id)

    # Default: seller
    return str(user.get("_id"))


async def check_user_permission(db, user: dict, permission: str) -> bool:
    """
    Check if user has a specific permission.
    - Platform admins: all permissions
    - Sellers: all permissions
    - Employees: check role permissions in db.roles collection
    """
    if is_platform_admin(user):
        return True

    account_type = user.get("accountType", "seller")

    if account_type == "seller":
        return True

    # Employee - check role permissions
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

    return user
