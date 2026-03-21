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

MAX_RECORDS_PER_PAGE = 50

VALID_FIELD_TYPES = {"text", "number", "date", "dropdown", "multiselect", "boolean", "longtext", "relation"}
VALID_RELATION_TYPES = {"many_to_one", "one_to_one"}
SYSTEM_LINKABLE = {"inventory", "invoices"}  # Built-in modules that can be linked


# ── Pydantic Models ──

class PanelFieldInput(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., description="text, number, date, dropdown, multiselect, boolean, longtext, relation")
    required: bool = False
    unique: bool = False
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
    allowedModules: Optional[List[str]] = Field(default_factory=list)


class UpdatePanelRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    allowedModules: Optional[List[str]] = None


class AddFieldRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    type: str
    required: bool = False
    unique: bool = False
    options: Optional[List[str]] = None
    relatedPanel: Optional[str] = None
    relationType: Optional[str] = None


class UpdateFieldRequest(BaseModel):
    label: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[List[str]] = None
    disabled: Optional[bool] = None


class ReorderFieldsRequest(BaseModel):
    fieldKeys: List[str]


class CreateRecordRequest(BaseModel):
    data: dict


class UpdateRecordRequest(BaseModel):
    data: dict


def init_panel_router(db, verify_token_func):
    from utils.permissions import authenticate_user, resolve_seller_id, is_platform_admin, normalize_permissions

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
             "fields": 1, "allowedModules": 1, "createdAt": 1, "updatedAt": 1}
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

    # ── RELATED RECORDS (for panel data integration with modules) ──
    @router.get("/panels/related-records")
    async def get_related_records(
        module: str,
        entityId: str,
        authorization: str = Header(...)
    ):
        """Find panel records related to a specific entity (e.g. inventory product)."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        # Find panels with relation fields pointing to this module
        panels_with_relations = await db.panels.find({
            "sellerId": ObjectId(seller_id),
            "fields.type": "relation",
            "fields.relatedPanel": module,
        }).to_list(20)

        result = []
        for panel in panels_with_relations:
            panel_id = str(panel["_id"])

            # Check employee permission for this panel
            if user.get("companyId") and user.get("employeeStatus") == "active":
                perms = normalize_permissions(user.get("employeePermissions", {}))
                panel_perms = perms.get("panels", {}).get(panel_id, {})
                if not panel_perms.get("canView"):
                    continue

            # Find relation field keys for this module
            relation_keys = [
                f["key"] for f in panel.get("fields", [])
                if f["type"] == "relation" and f.get("relatedPanel") == module
            ]
            if not relation_keys:
                continue

            # Find records matching the entityId
            query = {
                "panelId": panel["_id"],
                "sellerId": ObjectId(seller_id),
                "$or": [{f"data.{key}": entityId} for key in relation_keys]
            }
            records = await db.panel_records.find(query).limit(20).to_list(20)

            if records:
                resolved_records = []
                for rec in records:
                    display = {}
                    for f in panel.get("fields", []):
                        val = rec.get("data", {}).get(f["key"])
                        if val is not None and f["type"] != "relation":
                            display[f.get("label", f["key"])] = val
                    resolved_records.append({
                        "id": str(rec["_id"]),
                        "data": display,
                    })

                result.append({
                    "panelId": panel_id,
                    "panelName": panel.get("name", "Panel"),
                    "panelColor": panel.get("color", "blue"),
                    "records": resolved_records,
                })

        return {"groups": result}

    # ── GET SINGLE PANEL ──
    @router.get("/panels/{panel_id}")
    async def get_panel(panel_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "view")
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
            "allowedModules": data.allowedModules or [],
            "createdAt": now,
            "updatedAt": now,
        }

        # Auto-add required inventory relation field if linked to inventory
        if "inventory" in (data.allowedModules or []):
            has_inv_relation = any(
                f["type"] == "relation" and f.get("relatedPanel") == "inventory"
                for f in fields
            )
            if not has_inv_relation:
                inv_field = {
                    "key": "product",
                    "label": "Product",
                    "type": "relation",
                    "required": True,
                    "unique": False,
                    "relatedPanel": "inventory",
                    "relationType": "many_to_one",
                    "options": None,
                    "order": 0,
                }
                # Shift existing field orders
                for f in doc["fields"]:
                    f["order"] = f.get("order", 0) + 1
                doc["fields"].insert(0, inv_field)

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
        if data.allowedModules is not None:
            update["allowedModules"] = data.allowedModules
            # Auto-add inventory relation field if newly linking to inventory
            if "inventory" in data.allowedModules:
                current_fields = panel.get("fields", [])
                has_inv_relation = any(
                    f["type"] == "relation" and f.get("relatedPanel") == "inventory"
                    for f in current_fields
                )
                if not has_inv_relation:
                    inv_field = {
                        "key": "product", "label": "Product", "type": "relation",
                        "required": True, "unique": False,
                        "relatedPanel": "inventory", "relationType": "many_to_one",
                        "options": None, "order": 0,
                    }
                    for f in current_fields:
                        f["order"] = f.get("order", 0) + 1
                    current_fields.insert(0, inv_field)
                    update["fields"] = current_fields

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
        if data.disabled is not None:
            update_ops[f"fields.{field_idx}.disabled"] = data.disabled

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

        # Block deletion if any record has data for this field
        has_data = await db.panel_records.find_one({
            "panelId": ObjectId(panel_id),
            "sellerId": ObjectId(seller_id),
            f"data.{field_key}": {"$exists": True, "$nin": [None, ""]}
        })
        if has_data:
            raise HTTPException(status_code=400, detail=f"Cannot delete field '{field_key}': records contain data for this field. Disable it instead.")

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

    # ═══════════════════════════════════════════
    # RECORD CRUD — Phase 2
    # ═══════════════════════════════════════════

    def check_panel_access(user: dict, panel_id: str, action: str = "view"):
        """Unified panel access check. Admin/seller with advanced access and employees with panel permissions."""
        if user.get("accountType") == "buyer":
            raise HTTPException(status_code=403, detail="Buyers cannot access panels.")
        if is_platform_admin(user):
            return
        # Employee with panel permissions
        if user.get("companyId") and user.get("employeeStatus") == "active":
            perms = normalize_permissions(user.get("employeePermissions", {}))
            panel_perms = perms.get("panels", {}).get(panel_id, {})
            perm_map = {"view": "canView", "create": "canCreate", "edit": "canEdit"}
            perm_key = perm_map.get(action, "canView")
            if not panel_perms.get(perm_key):
                raise HTTPException(status_code=403, detail=f"You don't have {action} permission for this panel")
            return
        # Seller admin - require advanced access
        require_advanced_access(user)

    async def resolve_relation_display(seller_id: str, field: dict, value):
        """Resolve a relation value to a display label."""
        if not value:
            return None
        target = field.get("relatedPanel", "")
        try:
            if target == "inventory":
                doc = await db.products.find_one({"_id": ObjectId(value), "sellerId": ObjectId(seller_id)}, {"name": 1, "sku": 1})
                if doc:
                    return {"id": str(doc["_id"]), "label": doc.get("name", ""), "sku": doc.get("sku", "")}
            elif target == "invoices":
                doc = await db.invoices.find_one({"_id": ObjectId(value), "sellerId": ObjectId(seller_id)}, {"invoiceNumber": 1, "buyerName": 1})
                if doc:
                    return {"id": str(doc["_id"]), "label": doc.get("invoiceNumber", ""), "buyerName": doc.get("buyerName", "")}
            else:
                # Custom panel
                doc = await db.panel_records.find_one({"_id": ObjectId(value), "panelId": ObjectId(target), "sellerId": ObjectId(seller_id)})
                if doc:
                    data = doc.get("data", {})
                    # Use first text field as label
                    linked_panel = await db.panels.find_one({"_id": ObjectId(target)}, {"fields": 1, "name": 1})
                    label = ""
                    if linked_panel:
                        for f in linked_panel.get("fields", []):
                            if f["type"] in ("text", "dropdown") and data.get(f["key"]):
                                label = str(data[f["key"]])
                                break
                    return {"id": str(doc["_id"]), "label": label or str(doc["_id"])[:8]}
        except Exception:
            pass
        return {"id": str(value), "label": str(value)[:12]}

    async def validate_record_data(panel: dict, data: dict, seller_id: str, exclude_record_id: str = None):
        """Validate record data against panel field definitions."""
        fields = panel.get("fields", [])
        errors = []

        for f in fields:
            key = f["key"]
            val = data.get(key)
            is_disabled = f.get("disabled", False)
            if is_disabled:
                continue

            if f.get("required") and (val is None or val == "" or val == []):
                errors.append(f"Field '{f['label']}' is required")
                continue

            if val is None or val == "":
                continue

            ftype = f["type"]
            if ftype == "number":
                try:
                    float(val)
                except (ValueError, TypeError):
                    errors.append(f"Field '{f['label']}' must be a number")

            elif ftype == "dropdown":
                opts = f.get("options", [])
                if opts and str(val) not in opts:
                    errors.append(f"Field '{f['label']}' must be one of: {', '.join(opts)}")

            elif ftype == "multiselect":
                if not isinstance(val, list):
                    errors.append(f"Field '{f['label']}' must be a list")
                else:
                    opts = f.get("options", [])
                    if opts:
                        invalid = [v for v in val if v not in opts]
                        if invalid:
                            errors.append(f"Field '{f['label']}' has invalid options: {', '.join(invalid)}")

            elif ftype == "boolean":
                if not isinstance(val, bool):
                    errors.append(f"Field '{f['label']}' must be true or false")

            elif ftype == "relation":
                target = f.get("relatedPanel", "")
                if target and val:
                    exists = False
                    try:
                        if target == "inventory":
                            exists = bool(await db.products.find_one({"_id": ObjectId(val), "sellerId": ObjectId(seller_id)}, {"_id": 1}))
                        elif target == "invoices":
                            exists = bool(await db.invoices.find_one({"_id": ObjectId(val), "sellerId": ObjectId(seller_id)}, {"_id": 1}))
                        else:
                            exists = bool(await db.panel_records.find_one({"_id": ObjectId(val), "panelId": ObjectId(target), "sellerId": ObjectId(seller_id)}, {"_id": 1}))
                    except Exception:
                        pass
                    if not exists:
                        errors.append(f"Field '{f['label']}' references a non-existent record")

                    if f.get("relationType") == "one_to_one" and val:
                        dup_query = {
                            "panelId": ObjectId(str(panel["_id"])),
                            "sellerId": ObjectId(seller_id),
                            f"data.{key}": val
                        }
                        if exclude_record_id:
                            dup_query["_id"] = {"$ne": ObjectId(exclude_record_id)}
                        existing = await db.panel_records.find_one(dup_query, {"_id": 1})
                        if existing:
                            errors.append(f"Field '{f['label']}' already has a one-to-one link to this record")

            # Unique field validation
            if f.get("unique") and val is not None and val != "":
                dup_query = {
                    "panelId": ObjectId(str(panel["_id"])),
                    "sellerId": ObjectId(seller_id),
                    f"data.{key}": val,
                }
                if exclude_record_id:
                    dup_query["_id"] = {"$ne": ObjectId(exclude_record_id)}
                dup = await db.panel_records.find_one(dup_query, {"_id": 1})
                if dup:
                    errors.append(f"Field '{f['label']}' value '{val}' already exists. Must be unique.")

        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

    # ── LIST RECORDS ──
    @router.get("/panels/{panel_id}/records")
    async def list_records(
        panel_id: str,
        page: int = 1,
        search: str = "",
        authorization: str = Header(...)
    ):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "view")
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        query = {"panelId": ObjectId(panel_id), "sellerId": ObjectId(seller_id)}
        if search:
            # Search across text fields
            text_keys = [f"data.{f['key']}" for f in panel.get("fields", []) if f["type"] in ("text", "longtext", "dropdown")]
            if text_keys:
                query["$or"] = [{k: {"$regex": search, "$options": "i"}} for k in text_keys]

        total = await db.panel_records.count_documents(query)
        skip = (max(1, page) - 1) * MAX_RECORDS_PER_PAGE

        cursor = db.panel_records.find(query).sort("createdAt", -1).skip(skip).limit(MAX_RECORDS_PER_PAGE)
        records = await cursor.to_list(MAX_RECORDS_PER_PAGE)

        # Resolve relation fields for display
        relation_fields = [f for f in panel.get("fields", []) if f["type"] == "relation"]
        serialized = []
        for rec in records:
            sr = serialize_doc(rec)
            sr["_resolved"] = {}
            for rf in relation_fields:
                val = rec.get("data", {}).get(rf["key"])
                if val:
                    sr["_resolved"][rf["key"]] = await resolve_relation_display(seller_id, rf, val)
            serialized.append(sr)

        return {
            "records": serialized,
            "total": total,
            "page": page,
            "pages": max(1, (total + MAX_RECORDS_PER_PAGE - 1) // MAX_RECORDS_PER_PAGE),
            "panelName": panel["name"],
        }

    # ── GET SINGLE RECORD ──
    @router.get("/panels/{panel_id}/records/{record_id}")
    async def get_record(panel_id: str, record_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "view")
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        record = await db.panel_records.find_one({"_id": ObjectId(record_id), "panelId": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        sr = serialize_doc(record)
        sr["_resolved"] = {}
        for rf in panel.get("fields", []):
            if rf["type"] == "relation":
                val = record.get("data", {}).get(rf["key"])
                if val:
                    sr["_resolved"][rf["key"]] = await resolve_relation_display(seller_id, rf, val)

        return {"record": sr, "panel": serialize_doc(panel)}

    # ── CREATE RECORD ──
    @router.post("/panels/{panel_id}/records")
    async def create_record(panel_id: str, data: CreateRecordRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "create")
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        await validate_record_data(panel, data.data, seller_id, exclude_record_id=None)

        field_keys = {f["key"] for f in panel.get("fields", []) if not f.get("disabled")}
        clean_data = {k: v for k, v in data.data.items() if k in field_keys}

        now = datetime.now(timezone.utc)
        user_id = str(user.get("_id") or user.get("id"))

        doc = {
            "panelId": ObjectId(panel_id),
            "sellerId": ObjectId(seller_id),
            "data": clean_data,
            "createdBy": user_id,
            "createdAt": now,
            "updatedAt": now,
        }
        result = await db.panel_records.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Activity log
        log_entry = {
            "type": "PANEL_RECORD_CREATED",
            "panelId": ObjectId(panel_id),
            "panelName": panel.get("name", ""),
            "recordId": result.inserted_id,
            "sellerId": ObjectId(seller_id),
            "createdBy": user_id,
            "timestamp": now,
        }
        # Include product reference if panel is linked to inventory
        relation_fields = [f for f in panel.get("fields", []) if f["type"] == "relation" and f.get("relatedPanel") == "inventory"]
        for rf in relation_fields:
            if clean_data.get(rf["key"]):
                log_entry["productId"] = clean_data[rf["key"]]
                break
        # Include unique fields in log (e.g. QC number)
        for f in panel.get("fields", []):
            if f.get("unique") and clean_data.get(f["key"]):
                log_entry[f["key"]] = clean_data[f["key"]]
        await db.panel_activity_logs.insert_one(log_entry)

        logger.info(f"Record created in panel {panel_id} by {user_id}")
        return serialize_doc(doc)

    # ── UPDATE RECORD ──
    @router.put("/panels/{panel_id}/records/{record_id}")
    async def update_record(panel_id: str, record_id: str, data: UpdateRecordRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "edit")
        seller_id = await get_seller_id(user)

        panel = await db.panels.find_one({"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")

        record = await db.panel_records.find_one({"_id": ObjectId(record_id), "panelId": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        await validate_record_data(panel, data.data, seller_id, exclude_record_id=record_id)

        field_keys = {f["key"] for f in panel.get("fields", []) if not f.get("disabled")}
        clean_data = {k: v for k, v in data.data.items() if k in field_keys}

        await db.panel_records.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"data": clean_data, "updatedAt": datetime.now(timezone.utc)}}
        )
        logger.info(f"Record {record_id} updated in panel {panel_id}")
        return {"message": "Record updated"}

    # ── DELETE RECORD ──
    @router.delete("/panels/{panel_id}/records/{record_id}")
    async def delete_record(panel_id: str, record_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "edit")
        seller_id = await get_seller_id(user)

        record = await db.panel_records.find_one({"_id": ObjectId(record_id), "panelId": ObjectId(panel_id), "sellerId": ObjectId(seller_id)})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if any other panel record has a relation pointing to this record
        # Check all panels' relation fields that target this panel
        panels_with_relations = db.panels.find({
            "sellerId": ObjectId(seller_id),
            "fields.type": "relation",
            "fields.relatedPanel": panel_id
        })
        async for p in panels_with_relations:
            for f in p.get("fields", []):
                if f.get("type") == "relation" and f.get("relatedPanel") == panel_id:
                    linked = await db.panel_records.find_one({
                        "panelId": p["_id"],
                        "sellerId": ObjectId(seller_id),
                        f"data.{f['key']}": record_id
                    })
                    if linked:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot delete: this record is linked from panel '{p['name']}'. Remove the link first."
                        )

        await db.panel_records.delete_one({"_id": ObjectId(record_id)})
        logger.info(f"Record {record_id} deleted from panel {panel_id}")
        return {"message": "Record deleted"}

    # ── RELATION LOOKUP: search linkable entities ──
    @router.get("/panels/{panel_id}/relation-lookup")
    async def relation_lookup(
        panel_id: str,
        target: str = "",
        search: str = "",
        authorization: str = Header(...)
    ):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "view")
        seller_id = await get_seller_id(user)

        results = []
        limit = 20

        if target == "inventory":
            q = {"sellerId": ObjectId(seller_id)}
            if search:
                q["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"sku": {"$regex": search, "$options": "i"}},
                ]
            cursor = db.products.find(q, {"_id": 1, "name": 1, "sku": 1}).limit(limit)
            async for doc in cursor:
                results.append({"id": str(doc["_id"]), "label": doc.get("name", ""), "sub": doc.get("sku", "")})

        elif target == "invoices":
            q = {"sellerId": ObjectId(seller_id)}
            if search:
                q["$or"] = [
                    {"invoiceNumber": {"$regex": search, "$options": "i"}},
                    {"buyerName": {"$regex": search, "$options": "i"}},
                ]
            cursor = db.invoices.find(q, {"_id": 1, "invoiceNumber": 1, "buyerName": 1}).sort("createdAt", -1).limit(limit)
            async for doc in cursor:
                results.append({"id": str(doc["_id"]), "label": doc.get("invoiceNumber", ""), "sub": doc.get("buyerName", "")})

        else:
            # Custom panel records
            linked_panel = await db.panels.find_one({"_id": ObjectId(target), "sellerId": ObjectId(seller_id)})
            if linked_panel:
                q = {"panelId": ObjectId(target), "sellerId": ObjectId(seller_id)}
                if search:
                    text_keys = [f"data.{f['key']}" for f in linked_panel.get("fields", []) if f["type"] in ("text", "dropdown")]
                    if text_keys:
                        q["$or"] = [{k: {"$regex": search, "$options": "i"}} for k in text_keys]
                cursor = db.panel_records.find(q).sort("createdAt", -1).limit(limit)
                async for doc in cursor:
                    data = doc.get("data", {})
                    label = ""
                    for f in linked_panel.get("fields", []):
                        if f["type"] in ("text", "dropdown") and data.get(f["key"]):
                            label = str(data[f["key"]])
                            break
                    results.append({"id": str(doc["_id"]), "label": label or str(doc["_id"])[:8], "sub": ""})

        return {"results": results}

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

    # ── PANEL ACTIVITY LOGS ──
    @router.get("/panels/{panel_id}/activity-logs")
    async def get_panel_activity_logs(panel_id: str, authorization: str = Header(...), limit: int = 50):
        user = await get_current_user(authorization)
        check_panel_access(user, panel_id, "view")
        seller_id = await get_seller_id(user)

        cursor = db.panel_activity_logs.find(
            {"panelId": ObjectId(panel_id), "sellerId": ObjectId(seller_id)},
            {"_id": 0, "type": 1, "panelName": 1, "recordId": 1, "productId": 1,
             "createdBy": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(limit)

        for log in logs:
            if "recordId" in log:
                log["recordId"] = str(log["recordId"])
        return {"logs": serialize_doc(logs)}

    return router
