"""
Employee Management Router — Enhanced with:
- 3 tabs: Pending, Active, Unlinked
- Link via email (buyer -> employee conversion)
- Separate module and panel permissions
- Unlink / disable / re-link
- Self-protection (admin can't remove own access)
- Audit logging
- Real-time access push via Socket.IO
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger("employee_mgmt")

# System modules for permissions
SYSTEM_MODULES = [
    "dashboard", "inventory", "invoices", "quotations",
    "purchase_orders", "reports", "buyers", "suppliers",
    "employees", "settings"
]

SYSTEM_MODULE_LABELS = {
    "dashboard": "Dashboard",
    "inventory": "Inventory",
    "invoices": "Invoices",
    "quotations": "Quotations",
    "purchase_orders": "Purchase Orders",
    "reports": "Reports",
    "buyers": "Buyers",
    "suppliers": "Suppliers",
    "employees": "Employees",
    "settings": "Settings",
}

DEFAULT_ROLE_TEMPLATES = {
    "Admin": {"modules": {m: True for m in SYSTEM_MODULES}, "panels": {}},
    "Manager": {"modules": {m: m not in ("employees", "settings") for m in SYSTEM_MODULES}, "panels": {}},
    "Sales Executive": {"modules": {m: m in ("dashboard", "invoices", "quotations", "buyers", "reports") for m in SYSTEM_MODULES}, "panels": {}},
    "Inventory Manager": {"modules": {m: m in ("dashboard", "inventory", "purchase_orders", "suppliers", "reports") for m in SYSTEM_MODULES}, "panels": {}},
    "Accountant": {"modules": {m: m in ("dashboard", "invoices", "reports", "buyers") for m in SYSTEM_MODULES}, "panels": {}},
    "Viewer": {"modules": {m: True for m in SYSTEM_MODULES}, "panels": {}},
}


class PanelPermission(BaseModel):
    canView: bool = False
    canCreate: bool = False
    canEdit: bool = False


class EmployeePermissions(BaseModel):
    modules: Dict[str, bool] = Field(default_factory=dict)
    panels: Dict[str, PanelPermission] = Field(default_factory=dict)


class LinkEmployeeRequest(BaseModel):
    email: str = Field(..., min_length=3)
    role: str = Field(..., min_length=1)
    permissions: EmployeePermissions = Field(default_factory=EmployeePermissions)


class UpdateEmployeeAccessRequest(BaseModel):
    role: Optional[str] = None
    permissions: Optional[EmployeePermissions] = None
    status: Optional[str] = None


def serialize_doc(doc):
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == "_id":
                result["id"] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, dict):
                result[k] = serialize_doc(v)
            elif isinstance(v, list):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc


def init_employee_mgmt_router(db, verify_token_func, resolve_seller_id_func, sio=None):
    from utils.permissions import authenticate_user, normalize_permissions

    router = APIRouter()

    async def get_current_user(authorization: str = Header(...)):
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user: dict) -> str:
        return resolve_seller_id_func(user)

    async def log_action(seller_id, performed_by, action, target_user_id, details=""):
        await db.employee_logs.insert_one({
            "sellerId": ObjectId(seller_id),
            "performedBy": str(performed_by),
            "action": action,
            "targetUserId": str(target_user_id),
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        })

    async def emit_access_update(user_id: str, event_data: dict):
        if sio:
            try:
                await sio.emit("access_updated", event_data, room=f"user_{user_id}")
            except Exception as e:
                logger.warning(f"Failed to emit access_updated: {e}")

    def build_perms_dict(data_perms: EmployeePermissions) -> dict:
        """Convert Pydantic EmployeePermissions to a plain dict for DB storage."""
        return {
            "modules": {k: v for k, v in data_perms.modules.items()},
            "panels": {
                k: {"canView": v.canView, "canCreate": v.canCreate, "canEdit": v.canEdit}
                for k, v in data_perms.panels.items()
            },
        }

    # ── MODULES & ROLE TEMPLATES ──
    @router.get("/employee-mgmt/modules")
    async def get_modules(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        modules = [
            {"id": m, "name": SYSTEM_MODULE_LABELS.get(m, m.replace("_", " ").title())}
            for m in SYSTEM_MODULES
        ]

        panels = []
        if seller_id:
            raw = await db.panels.find(
                {"sellerId": ObjectId(seller_id)},
                {"_id": 1, "name": 1, "color": 1}
            ).to_list(20)
            for p in raw:
                panels.append({
                    "id": str(p["_id"]),
                    "name": p.get("name", "Panel"),
                    "color": p.get("color", "blue"),
                })

        return {"modules": modules, "panels": panels}

    @router.get("/employee-mgmt/role-templates")
    async def get_role_templates(authorization: str = Header(...)):
        await get_current_user(authorization)
        return {"templates": DEFAULT_ROLE_TEMPLATES}

    # ── SEARCH USER BY EMAIL ──
    @router.get("/employee-mgmt/search")
    async def search_user_by_email(email: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        found = await db.users.find_one(
            {"email": email.lower().strip()},
            {"_id": 1, "email": 1, "name": 1, "phone": 1, "accountType": 1,
             "companyId": 1, "employeeStatus": 1, "profile": 1}
        )
        if not found:
            return {"found": False, "message": "No user found with this email. Ask them to register first as a buyer."}

        if found.get("companyId") and str(found["companyId"]) == seller_id:
            return {"found": True, "alreadyLinked": True, "user": serialize_doc(found), "message": "This user is already linked to your company."}

        if found.get("companyId"):
            return {"found": True, "linkedElsewhere": True, "message": "This user is already linked to another company."}

        profile = found.get("profile", {})
        name = found.get("name") or profile.get("businessName") or profile.get("name") or ""
        phone = found.get("phone") or profile.get("phone") or ""

        return {
            "found": True,
            "canLink": True,
            "user": {
                "id": str(found["_id"]),
                "email": found.get("email", ""),
                "name": name,
                "phone": phone,
                "accountType": found.get("accountType", ""),
                "employeeStatus": found.get("employeeStatus", "pending"),
            }
        }

    # ── LINK EMPLOYEE ──
    @router.post("/employee-mgmt/link")
    async def link_employee(data: LinkEmployeeRequest, authorization: str = Header(...)):
        admin = await get_current_user(authorization)
        seller_id = await get_seller_id(admin)

        target = await db.users.find_one({"email": data.email.lower().strip()})
        if not target:
            raise HTTPException(status_code=404, detail="User not found. They must register first.")

        if target.get("companyId") and str(target["companyId"]) != seller_id:
            raise HTTPException(status_code=400, detail="User is already linked to another company.")

        if target.get("companyId") and str(target["companyId"]) == seller_id and target.get("employeeStatus") == "active":
            raise HTTPException(status_code=400, detail="User is already an active employee of your company.")

        perms = build_perms_dict(data.permissions)

        now = datetime.now(timezone.utc)
        update = {
            "companyId": ObjectId(seller_id),
            "employeeRole": data.role,
            "employeeStatus": "active",
            "employeePermissions": perms,
            "linkedAt": now,
            "updatedAt": now,
        }
        await db.users.update_one({"_id": target["_id"]}, {"$set": update})

        target_id = str(target["_id"])
        await log_action(seller_id, str(admin["_id"]), "linked", target_id, f"Role: {data.role}")
        await emit_access_update(target_id, {"type": "linked", "role": data.role, "permissions": perms})

        logger.info(f"Employee linked: {data.email} -> seller {seller_id}, role={data.role}")
        return {"message": f"Employee {data.email} linked successfully", "employeeId": target_id}

    # ── LIST EMPLOYEES (3 tabs) ──
    @router.get("/employee-mgmt/list")
    async def list_employees_enhanced(tab: str = "active", authorization: str = Header(...)):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        if tab == "active":
            query = {"companyId": ObjectId(seller_id), "employeeStatus": {"$in": ["active", "disabled"]}}
        elif tab == "pending":
            query = {
                "$or": [
                    {"companyId": {"$exists": False}},
                    {"companyId": None}
                ],
                "employeeStatus": {"$nin": ["active", "disabled", "unlinked"]},
                "accountType": {"$nin": ["seller", "admin"]},
                "unlinkedFrom": {"$exists": False},
            }
        elif tab == "unlinked":
            query = {"unlinkedFrom": ObjectId(seller_id), "employeeStatus": "unlinked"}
        else:
            raise HTTPException(status_code=400, detail="Invalid tab. Use: active, pending, unlinked")

        cursor = db.users.find(
            query,
            {"_id": 1, "email": 1, "name": 1, "phone": 1, "profile": 1,
             "employeeRole": 1, "employeeStatus": 1, "employeePermissions": 1,
             "linkedAt": 1, "unlinkedAt": 1, "accountType": 1, "createdAt": 1}
        ).sort("updatedAt", -1).limit(100)
        docs = await cursor.to_list(100)

        employees = []
        for d in docs:
            profile = d.get("profile", {})
            raw_perms = d.get("employeePermissions", {})
            employees.append({
                "id": str(d["_id"]),
                "email": d.get("email", ""),
                "name": d.get("name") or profile.get("businessName") or profile.get("name") or "",
                "phone": d.get("phone") or profile.get("phone") or "",
                "role": d.get("employeeRole", "unassigned"),
                "status": d.get("employeeStatus", "pending"),
                "permissions": normalize_permissions(raw_perms),
                "linkedAt": d.get("linkedAt", ""),
                "unlinkedAt": d.get("unlinkedAt", ""),
                "createdAt": d.get("createdAt", ""),
            })

        return {"employees": serialize_doc(employees), "tab": tab, "count": len(employees)}

    # ── UPDATE EMPLOYEE ACCESS ──
    @router.put("/employee-mgmt/{employee_id}")
    async def update_employee_access(employee_id: str, data: UpdateEmployeeAccessRequest, authorization: str = Header(...)):
        admin = await get_current_user(authorization)
        seller_id = await get_seller_id(admin)

        if str(admin["_id"]) == employee_id:
            raise HTTPException(status_code=400, detail="You cannot modify your own access. Ask another admin.")

        emp = await db.users.find_one({"_id": ObjectId(employee_id), "companyId": ObjectId(seller_id)})
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found in your company")

        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        changes = []

        if data.role is not None:
            update_fields["employeeRole"] = data.role
            changes.append(f"role->{data.role}")

        if data.permissions is not None:
            perms = build_perms_dict(data.permissions)
            update_fields["employeePermissions"] = perms
            changes.append("permissions updated")

        if data.status is not None:
            if data.status not in ["active", "disabled"]:
                raise HTTPException(status_code=400, detail="Status must be 'active' or 'disabled'")
            update_fields["employeeStatus"] = data.status
            changes.append(f"status->{data.status}")

        await db.users.update_one({"_id": ObjectId(employee_id)}, {"$set": update_fields})

        await log_action(seller_id, str(admin["_id"]), "permission_updated", employee_id, "; ".join(changes))
        await emit_access_update(employee_id, {
            "type": "access_updated",
            "role": data.role or emp.get("employeeRole"),
            "permissions": update_fields.get("employeePermissions", emp.get("employeePermissions", {})),
            "status": data.status or emp.get("employeeStatus"),
        })

        logger.info(f"Employee {employee_id} access updated: {', '.join(changes)}")
        return {"message": "Access updated", "changes": changes}

    # ── UNLINK EMPLOYEE ──
    @router.post("/employee-mgmt/{employee_id}/unlink")
    async def unlink_employee(employee_id: str, authorization: str = Header(...)):
        admin = await get_current_user(authorization)
        seller_id = await get_seller_id(admin)

        if str(admin["_id"]) == employee_id:
            raise HTTPException(status_code=400, detail="You cannot unlink yourself.")

        emp = await db.users.find_one({"_id": ObjectId(employee_id), "companyId": ObjectId(seller_id)})
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found in your company")

        now = datetime.now(timezone.utc)
        await db.users.update_one({"_id": ObjectId(employee_id)}, {"$set": {
            "companyId": None,
            "employeeRole": "unassigned",
            "employeeStatus": "unlinked",
            "employeePermissions": {"modules": {}, "panels": {}},
            "unlinkedFrom": ObjectId(seller_id),
            "unlinkedAt": now,
            "updatedAt": now,
        }})

        await log_action(seller_id, str(admin["_id"]), "unlinked", employee_id)
        await emit_access_update(employee_id, {"type": "unlinked", "permissions": {"modules": {}, "panels": {}}, "role": "unassigned"})

        logger.info(f"Employee {employee_id} unlinked from seller {seller_id}")
        return {"message": "Employee unlinked. Access revoked immediately."}

    # ── RE-LINK (from unlinked tab) ──
    @router.post("/employee-mgmt/{employee_id}/relink")
    async def relink_employee(employee_id: str, data: LinkEmployeeRequest, authorization: str = Header(...)):
        admin = await get_current_user(authorization)
        seller_id = await get_seller_id(admin)

        emp = await db.users.find_one({"_id": ObjectId(employee_id)})
        if not emp:
            raise HTTPException(status_code=404, detail="User not found")
        if emp.get("companyId") and str(emp["companyId"]) != seller_id:
            raise HTTPException(status_code=400, detail="User linked to another company")

        perms = build_perms_dict(data.permissions)

        now = datetime.now(timezone.utc)
        await db.users.update_one({"_id": ObjectId(employee_id)}, {"$set": {
            "companyId": ObjectId(seller_id),
            "employeeRole": data.role,
            "employeeStatus": "active",
            "employeePermissions": perms,
            "linkedAt": now,
            "updatedAt": now,
        }, "$unset": {"unlinkedFrom": "", "unlinkedAt": ""}})

        await log_action(seller_id, str(admin["_id"]), "relinked", employee_id, f"Role: {data.role}")
        await emit_access_update(employee_id, {"type": "linked", "role": data.role, "permissions": perms})

        return {"message": "Employee re-linked successfully"}

    # ── GET CURRENT EMPLOYEE ACCESS (for real-time sync) ──
    @router.get("/employee-mgmt/my-access")
    async def get_my_access(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        uid = str(user["_id"])
        doc = await db.users.find_one(
            {"_id": user["_id"]},
            {"_id": 0, "employeeRole": 1, "employeeStatus": 1, "employeePermissions": 1,
             "companyId": 1, "accountType": 1, "roles": 1, "profile": 1}
        )
        if not doc:
            return {
                "role": "unassigned", "status": "pending",
                "permissions": {"modules": {}, "panels": {}},
                "isAdmin": False, "permittedPanels": [],
            }

        is_admin = doc.get("accountType") == "seller" or "seller" in (doc.get("roles") or [])

        raw_perms = doc.get("employeePermissions", {})
        perms = normalize_permissions(raw_perms)

        company_name = ""
        company_logo_url = ""
        company_id = doc.get("companyId")

        if is_admin:
            profile = doc.get("profile") or {}
            company_name = profile.get("businessName", "")
            company_logo_url = profile.get("sellerLogoUrl", "")
        elif company_id:
            seller = await db.users.find_one(
                {"_id": company_id},
                {"_id": 0, "profile.businessName": 1, "profile.sellerLogoUrl": 1,
                 "billingSettings.companyLogoUrl": 1}
            )
            if seller:
                sp = seller.get("profile") or {}
                company_name = sp.get("businessName", "")
                company_logo_url = sp.get("sellerLogoUrl", "")
                if not company_logo_url:
                    company_logo_url = (seller.get("billingSettings") or {}).get("companyLogoUrl", "")

        # Fetch permitted panel details for employees
        permitted_panels = []
        if not is_admin and perms.get("panels"):
            panel_ids = []
            for pid, pp in perms["panels"].items():
                if isinstance(pp, dict) and pp.get("canView"):
                    try:
                        panel_ids.append(ObjectId(pid))
                    except Exception:
                        pass
            if panel_ids:
                raw = await db.panels.find(
                    {"_id": {"$in": panel_ids}},
                    {"_id": 1, "name": 1, "color": 1, "slug": 1}
                ).to_list(20)
                for p in raw:
                    permitted_panels.append({
                        "id": str(p["_id"]),
                        "name": p["name"],
                        "color": p.get("color", "blue"),
                        "slug": p.get("slug", ""),
                    })

        return {
            "userId": uid,
            "role": doc.get("employeeRole", "unassigned"),
            "status": doc.get("employeeStatus", "pending"),
            "permissions": perms,
            "companyId": str(doc["companyId"]) if doc.get("companyId") else None,
            "isAdmin": is_admin,
            "companyName": company_name,
            "companyLogoUrl": company_logo_url,
            "permittedPanels": permitted_panels,
        }

    # ── AUDIT LOGS ──
    @router.get("/employee-mgmt/logs")
    async def get_employee_logs(authorization: str = Header(...), limit: int = 50):
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        cursor = db.employee_logs.find(
            {"sellerId": ObjectId(seller_id)},
            {"_id": 0, "performedBy": 1, "action": 1, "targetUserId": 1, "details": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(limit)
        return {"logs": serialize_doc(logs)}

    # ── UNLINK ALL (company delete impact) ──
    @router.post("/employee-mgmt/unlink-all")
    async def unlink_all_employees(authorization: str = Header(...)):
        admin = await get_current_user(authorization)
        seller_id = await get_seller_id(admin)

        now = datetime.now(timezone.utc)
        employees = await db.users.find(
            {"companyId": ObjectId(seller_id), "employeeStatus": {"$in": ["active", "disabled"]}},
            {"_id": 1}
        ).to_list(500)

        if employees:
            emp_ids = [e["_id"] for e in employees]
            await db.users.update_many(
                {"_id": {"$in": emp_ids}},
                {"$set": {
                    "companyId": None, "employeeRole": "unassigned",
                    "employeeStatus": "unlinked",
                    "employeePermissions": {"modules": {}, "panels": {}},
                    "unlinkedFrom": ObjectId(seller_id), "unlinkedAt": now, "updatedAt": now,
                }}
            )
            for emp in employees:
                await emit_access_update(str(emp["_id"]), {"type": "unlinked", "permissions": {"modules": {}, "panels": {}}, "role": "unassigned"})
            await log_action(seller_id, str(admin["_id"]), "unlinked_all", "all", f"Unlinked {len(employees)} employees")

        return {"message": f"Unlinked {len(employees)} employees", "count": len(employees)}

    return router
