"""
Panel Router - Custom Panel System (Advanced Business Tools)
Handles panel CRUD and field management.
Only available to users with businessToolAccess = "advanced".
Panel creation restricted to seller admins (not employees).
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging
import re

logger = logging.getLogger(__name__)

# Limits
MAX_PANELS_PER_BUSINESS = 10
MAX_FIELDS_PER_PANEL = 20

VALID_FIELD_TYPES = {"text", "number", "date", "dropdown", "multiselect", "boolean", "longtext", "relation"}
VALID_RELATION_TYPES = {"many_to_one", "one_to_one"}
SYSTEM_LINKABLE = {"inventory", "invoices"}  # Built-in modules that can be linked


# ── Pydantic Models ──

class PanelFieldInput(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., description="text, number, date, dropdown, multiselect, boolean, longtext, relation")
    required: bool = False
    options: Optional[List[str]] = None
    relatedPanel: Optional[str] = None
    relationType: Optional[str] = None
    order: Optional[int] = 0


class CreatePanelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    icon: Optional[str] = "layout-grid"
    color: Optional[str] = "blue"
    fields: Optional[List[PanelFieldInput]] = []


class UpdatePanelRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class AddFieldRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    type: str
    required: bool = False
    options: Optional[List[str]] = None
    relatedPanel: Optional[str] = None
    relationType: Optional[str] = None


class UpdateFieldRequest(BaseModel):
    label: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[List[str]] = None


class ReorderFieldsRequest(BaseModel):
    fieldKeys: List[str]


def init_panel_router(db, verify_token_func):
    from utils.permissions import authenticate_user, resolve_seller_id, is_platform_admin

    router = APIRouter(tags=["Panels"])

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

    async def get_current_user(authorization: str = Header(...)):
        return await authenticate_user(db, verify_token_func, authorization)

    async def get_seller_id(user: dict) -> str:
        sid = resolve_seller_id(user)
        if sid is None:
            # Platform admin: use their own user ID for panel ownership
            uid = user.get("_id") or user.get("id")
            return str(uid)
        return sid

    def require_advanced_access(user: dict):
        """Check that the user has advanced business tool access."""
        access_level = user.get("businessToolAccess", "standard")
        if access_level != "advanced" and not is_platform_admin(user):
            raise HTTPException(status_code=403, detail="Advanced access required. Contact platform admin to upgrade.")

    def require_seller_admin(user: dict):
        """Only seller admin (not employee) can create/modify panel structure."""
        if user.get("companyId") and user.get("employeeStatus") == "active":
            raise HTTPException(status_code=403, detail="Only the business admin can manage panel structure.")
        if not is_platform_admin(user) and user.get("accountType") not in (None, "seller"):
            raise HTTPException(status_code=403, detail="Only the business admin can manage panel structure.")

    def make_slug(name: str) -> str:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip()).strip('-')
        return slug or "panel"

    def validate_field(field: dict):
        if field["type"] not in VALID_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid field type: {field['type']}. Must be one of {VALID_FIELD_TYPES}")
        if field["type"] in ("dropdown", "multiselect") and not field.get("options"):
            raise HTTPException(status_code=400, detail=f"Field '{field['key']}' requires options for {field['type']} type")
        if field["type"] == "relation":
            if not field.get("relatedPanel"):
                raise HTTPException(status_code=400, detail=f"Field '{field['key']}' requires relatedPanel for relation type")
            rt = field.get("relationType", "many_to_one")
            if rt not in VALID_RELATION_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid relationType: {rt}")

    # ── LIST PANELS ──
    @router.get("/panels")
    async def list_panels(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        seller_id = await get_seller_id(user)

        cursor = db.panels.find(
            {"sellerId": ObjectId(seller_id)},
            {"_id": 1, "name": 1, "slug": 1, "description": 1, "icon": 1, "color": 1,
             "fields": 1, "createdAt": 1, "updatedAt": 1}
        ).sort("createdAt", 1)
        panels = await cursor.to_list(MAX_PANELS_PER_BUSINESS + 5)
        return {"panels": serialize_doc(panels), "count": len(panels), "limit": MAX_PANELS_PER_BUSINESS}

    # ── LINKABLE TARGETS (for relation fields) — must be before {panel_id} routes ──
    @router.get("/panels/linkable-targets")
    async def get_linkable_targets(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        seller_id = await get_seller_id(user)

        targets = [
            {"id": "inventory", "name": "Inventory", "type": "system"},
            {"id": "invoices", "name": "Invoices", "type": "system"},
        ]

        panels = await db.panels.find(
            {"sellerId": ObjectId(seller_id)},
            {"_id": 1, "name": 1}
        ).to_list(MAX_PANELS_PER_BUSINESS)

        for p in panels:
            targets.append({"id": str(p["_id"]), "name": p["name"], "type": "panel"})

        return {"targets": targets}

    # ── GET SINGLE PANEL ──
    @router.get("/panels/{panel_id}")
    async def get_panel(panel_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        seller_id = await get_seller_id(user)

        try:
            panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid panel ID")

        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        return serialize_doc(panel)

    # ── CREATE PANEL ──
    @router.post("/panels")
    async def create_panel(data: CreatePanelRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        # Check limit
        count = await db.panels.count_documents({"sellerId": ObjectId(seller_id)})
        if count >= MAX_PANELS_PER_BUSINESS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_PANELS_PER_BUSINESS} panels allowed per business.")

        # Check duplicate name
        existing = await db.panels.find_one({"sellerId": ObjectId(seller_id), "name": {"$regex": f"^{re.escape(data.name.strip())}$", "$options": "i"}})
        if existing:
            raise HTTPException(status_code=400, detail="A panel with this name already exists.")

        # Validate fields
        fields = []
        seen_keys = set()
        for i, f in enumerate(data.fields or []):
            if len(fields) >= MAX_FIELDS_PER_PANEL:
                raise HTTPException(status_code=400, detail=f"Maximum {MAX_FIELDS_PER_PANEL} fields allowed per panel.")
            fd = f.model_dump()
            validate_field(fd)
            if fd["key"] in seen_keys:
                raise HTTPException(status_code=400, detail=f"Duplicate field key: {fd['key']}")
            seen_keys.add(fd["key"])
            fd["order"] = i
            fields.append(fd)

        now = datetime.now(timezone.utc)
        slug = make_slug(data.name)

        # Ensure slug uniqueness
        slug_exists = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": slug})
        if slug_exists:
            slug = f"{slug}-{int(now.timestamp()) % 10000}"

        doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name.strip(),
            "slug": slug,
            "description": (data.description or "").strip(),
            "icon": data.icon or "layout-grid",
            "color": data.color or "blue",
            "fields": fields,
            "createdAt": now,
            "updatedAt": now,
        }
        result = await db.panels.insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.info(f"Panel created: {data.name} for seller {seller_id}")
        return serialize_doc(doc)

    # ── UPDATE PANEL (name, description, icon, color) ──
    @router.put("/panels/{panel_id}")
    async def update_panel(panel_id: str, data: UpdatePanelRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        try:
            panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid panel ID")
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        update = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            # Check duplicate
            existing = await db.panels.find_one({
                "sellerId": ObjectId(seller_id),
                "name": {"$regex": f"^{re.escape(data.name.strip())}$", "$options": "i"},
                "_id": {"$ne": ObjectId(panel_id)}
            })
            if existing:
                raise HTTPException(status_code=400, detail="A panel with this name already exists.")
            update["name"] = data.name.strip()
            update["slug"] = make_slug(data.name)
        if data.description is not None:
            update["description"] = data.description.strip()
        if data.icon is not None:
            update["icon"] = data.icon
        if data.color is not None:
            update["color"] = data.color

        await db.panels.update_one({"_id": ObjectId(panel_id)}, {"$set": update})
        logger.info(f"Panel {panel_id} updated")
        return {"message": "Panel updated"}

    # ── DELETE PANEL ──
    @router.delete("/panels/{panel_id}")
    async def delete_panel(panel_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        try:
            panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid panel ID")
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        # Check for linked records
        record_count = await db.panel_records.count_documents({"panelId": ObjectId(panel_id)})
        if record_count > 0:
            raise HTTPException(status_code=400, detail=f"Cannot delete panel with {record_count} existing records. Delete records first.")

        # Check if other panels have relation fields pointing to this panel
        referencing = await db.panels.find_one({
            "sellerId": ObjectId(seller_id),
            "fields.relatedPanel": panel_id,
            "_id": {"$ne": ObjectId(panel_id)}
        })
        if referencing:
            raise HTTPException(status_code=400, detail=f"Cannot delete: panel '{referencing['name']}' has a relation field linked to this panel.")

        await db.panels.delete_one({"_id": ObjectId(panel_id)})
        logger.info(f"Panel {panel_id} deleted")
        return {"message": "Panel deleted"}

    # ── ADD FIELD TO PANEL ──
    @router.post("/panels/{panel_id}/fields")
    async def add_field(panel_id: str, data: AddFieldRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        fields = panel.get("fields", [])
        if len(fields) >= MAX_FIELDS_PER_PANEL:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_FIELDS_PER_PANEL} fields allowed per panel.")

        # Check duplicate key
        if any(f["key"] == data.key for f in fields):
            raise HTTPException(status_code=400, detail=f"Field key '{data.key}' already exists in this panel.")

        fd = data.model_dump()
        validate_field(fd)
        fd["order"] = len(fields)

        await db.panels.update_one(
            {"_id": ObjectId(panel_id)},
            {"$push": {"fields": fd}, "$set": {"updatedAt": datetime.now(timezone.utc)}}
        )
        logger.info(f"Field '{data.key}' added to panel {panel_id}")
        return {"message": "Field added", "field": fd}

    # ── UPDATE FIELD ──
    @router.put("/panels/{panel_id}/fields/{field_key}")
    async def update_field(panel_id: str, field_key: str, data: UpdateFieldRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        fields = panel.get("fields", [])
        field_idx = next((i for i, f in enumerate(fields) if f["key"] == field_key), None)
        if field_idx is None:
            raise HTTPException(status_code=404, detail=f"Field '{field_key}' not found")

        update_ops = {"updatedAt": datetime.now(timezone.utc)}
        if data.label is not None:
            update_ops[f"fields.{field_idx}.label"] = data.label
        if data.required is not None:
            update_ops[f"fields.{field_idx}.required"] = data.required
        if data.options is not None:
            update_ops[f"fields.{field_idx}.options"] = data.options

        await db.panels.update_one({"_id": ObjectId(panel_id)}, {"$set": update_ops})
        return {"message": "Field updated"}

    # ── DELETE FIELD ──
    @router.delete("/panels/{panel_id}/fields/{field_key}")
    async def delete_field(panel_id: str, field_key: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        fields = panel.get("fields", [])
        if not any(f["key"] == field_key for f in fields):
            raise HTTPException(status_code=404, detail=f"Field '{field_key}' not found")

        new_fields = [f for f in fields if f["key"] != field_key]
        # Re-order
        for i, f in enumerate(new_fields):
            f["order"] = i

        await db.panels.update_one(
            {"_id": ObjectId(panel_id)},
            {"$set": {"fields": new_fields, "updatedAt": datetime.now(timezone.utc)}}
        )
        return {"message": "Field deleted"}

    # ── REORDER FIELDS ──
    @router.put("/panels/{panel_id}/fields-order")
    async def reorder_fields(panel_id: str, data: ReorderFieldsRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_advanced_access(user)
        require_seller_admin(user)
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        fields = panel.get("fields", [])
        field_map = {f["key"]: f for f in fields}
        reordered = []
        for i, key in enumerate(data.fieldKeys):
            if key not in field_map:
                raise HTTPException(status_code=400, detail=f"Field key '{key}' not found")
            f = field_map[key]
            f["order"] = i
            reordered.append(f)

        # Add any fields not in the reorder list at the end
        for f in fields:
            if f["key"] not in data.fieldKeys:
                f["order"] = len(reordered)
                reordered.append(f)

        await db.panels.update_one(
            {"_id": ObjectId(panel_id)},
            {"$set": {"fields": reordered, "updatedAt": datetime.now(timezone.utc)}}
        )
        return {"message": "Fields reordered"}

    # ── SUPER ADMIN: SET ACCESS LEVEL ──
    @router.put("/admin/set-access-level")
    async def set_access_level(authorization: str = Header(...), data: dict = {}):
        user = await get_current_user(authorization)
        if not is_platform_admin(user):
            raise HTTPException(status_code=403, detail="Platform admin only")

        user_id = data.get("userId")
        level = data.get("level")
        if not user_id or level not in ("none", "standard", "advanced"):
            raise HTTPException(status_code=400, detail="userId and level (none/standard/advanced) required")

        try:
            result = await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"businessToolAccess": level, "updatedAt": datetime.now(timezone.utc)}}
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"Access level set to '{level}' for user {user_id}")
        return {"message": f"Access level set to '{level}'"}

    # ── GET ACCESS LEVEL ──
    @router.get("/access-level")
    async def get_access_level(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        level = user.get("businessToolAccess", "standard")
        if is_platform_admin(user):
            level = "advanced"
        return {"level": level, "limits": {"maxPanels": MAX_PANELS_PER_BUSINESS, "maxFieldsPerPanel": MAX_FIELDS_PER_PANEL}}

    return router
