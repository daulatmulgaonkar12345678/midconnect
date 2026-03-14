"""
Activity Log Router - View activity logs for audit
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
import logging

from models.business_tools import Permission

logger = logging.getLogger(__name__)


def init_activity_log_router(db, verify_token_func):
    router = APIRouter(tags=["Activity Logs"])

    def serialize_doc(doc):
        if doc is None:
            return None
        if isinstance(doc, list):
            return [serialize_doc(d) for d in doc]
        if isinstance(doc, dict):
            result = {}
            for key, value in doc.items():
                if key == "_id":
                    result["id"] = str(value)
                elif isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, dict):
                    result[key] = serialize_doc(value)
                elif isinstance(value, list):
                    result[key] = serialize_doc(value)
                else:
                    result[key] = value
            return result
        return doc

    async def get_current_user(authorization: str):
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
        if user.get("accountType") == "employee" and user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Employee account is inactive")
        return user

    async def get_seller_id(user: dict) -> str:
        if user.get("accountType") == "employee":
            sid = user.get("sellerId")
            if not sid:
                raise HTTPException(status_code=403, detail="Employee not linked to seller")
            return str(sid)
        return str(user.get("_id"))

    @router.get("/activity-logs")
    async def list_activity_logs(
        authorization: str = Header(...),
        module: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List activity logs. Only seller admin or employees with manage_roles permission can view."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        # Only admin or those with manage_roles can view logs
        if user.get("accountType") == "employee":
            role_id = user.get("roleId")
            if role_id:
                role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
                if not role or Permission.MANAGE_ROLES.value not in role.get("permissions", []):
                    raise HTTPException(status_code=403, detail="Permission denied: only admins can view activity logs")
            else:
                raise HTTPException(status_code=403, detail="Permission denied")

        query = {"sellerId": ObjectId(seller_id)}
        if module:
            query["module"] = module
        if action:
            query["action"] = action

        total = await db.activity_logs.count_documents(query)
        logs = await db.activity_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with user names
        for log in logs:
            if log.get("userId"):
                try:
                    u = await db.users.find_one({"_id": log["userId"]})
                    log["userName"] = u.get("name") or u.get("email", "Unknown") if u else "Unknown"
                except Exception:
                    log["userName"] = "Unknown"
            else:
                log["userName"] = "System"

        return {"logs": serialize_doc(logs), "total": total}

    return router
