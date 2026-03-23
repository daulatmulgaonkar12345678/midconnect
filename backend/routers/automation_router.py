"""
Automation Router - Workflow Automation Engine (Phase 4 Multi-Target)

Architecture:
  - Panels = Data Layer (schema + records only)
  - Rules = Workflow Layer (triggers, conditions, multi-target actions)
  - Data always flows from Source Panel → Target Panels (single source of truth)
  - No target panel acts as parent or triggers chains automatically

Supports:
  - One source panel per rule
  - Multiple target panels per rule (custom + system)
  - Per-target field mapping (source field, default value, reference)
  - Per-target field visibility (visible/editable toggles)
  - Trigger types: on_create, on_update, condition_based
  - Action types per target: create_record, create_records_per_item, update_record
  - Duplicate prevention, execution logging
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

MAX_RULES_PER_BUSINESS = 50
MAX_TARGETS_PER_RULE = 10
MAX_FIELD_MAPPINGS = 30
ALLOWED_OPERATORS = {"equals", "not_equals", "greater_than", "less_than", "contains", "not_empty", "is_empty"}
ALLOWED_TRIGGER_TYPES = {"on_create", "on_update", "condition_based"}
ALLOWED_ACTION_TYPES = {"update_record", "create_record", "create_records_per_item"}
ALLOWED_UPDATE_OPS = {"increment", "decrement", "set_value"}
ALLOWED_DATA_MODES = {"smart_sync", "manual_only", "full_copy"}
BLOCKED_SYSTEM_FIELDS = {"_id", "sellerId", "createdAt", "updatedAt", "createdBy"}
SYSTEM_MODULE_IDS = {"inventory", "invoices", "buyers", "suppliers", "purchase_orders", "quotations", "composite_products", "employees"}


# ── Pydantic Models ──

class AutomationCondition(BaseModel):
    field: str = Field(default="", description="Field to evaluate")
    operator: str = Field(default="equals")
    value: Optional[str] = None


class FieldMapping(BaseModel):
    target_field: str = Field(..., min_length=1)
    source_field: Optional[str] = None
    default_value: Optional[str] = None
    mapping_type: str = Field(default="field", description="field | default | reference")


class FieldVisibility(BaseModel):
    field: str
    visible: bool = True
    editable: bool = True


class RuleTarget(BaseModel):
    target_panel_id: str = Field(...)
    action_type: str = Field(default="create_record")
    data_mode: str = Field(default="smart_sync", description="smart_sync | manual_only | full_copy")
    relation_field: Optional[str] = None
    # For update_record — MATCH + UPDATE
    match_target_field: Optional[str] = None   # e.g., "product_name" in inventory
    match_source_field: Optional[str] = None   # e.g., "product_name" in QC
    update_operation: Optional[str] = None
    update_field: Optional[str] = None
    update_value_from: Optional[str] = None
    # For create actions
    field_mappings: Optional[List[FieldMapping]] = None
    field_visibility: Optional[List[FieldVisibility]] = None


class CreateRuleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_panel_id: str = Field(...)
    trigger_type: str = Field(default="on_create")
    condition: Optional[AutomationCondition] = None
    targets: List[RuleTarget] = Field(..., min_length=1)
    is_active: bool = True
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    condition: Optional[AutomationCondition] = None
    targets: Optional[List[RuleTarget]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


def init_automation_router(db, verify_token_func):
    from utils.permissions import authenticate_user, resolve_seller_id, is_platform_admin

    router = APIRouter(tags=["Automation"])

    def serialize_doc(doc):
        if doc is None:
            return None
        if isinstance(doc, ObjectId):
            return str(doc)
        if isinstance(doc, datetime):
            return doc.isoformat()
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
            uid = user.get("_id") or user.get("id")
            return str(uid)
        return sid

    def require_admin(user: dict):
        if user.get("companyId") and user.get("employeeStatus") == "active":
            raise HTTPException(status_code=403, detail="Only the business admin can manage automation rules.")
        access_level = user.get("businessToolAccess", "standard")
        if access_level != "advanced" and not is_platform_admin(user):
            raise HTTPException(status_code=403, detail="Advanced access required.")

    async def validate_trigger_panel(seller_id: str, panel_id: str):
        if panel_id in SYSTEM_MODULE_IDS:
            return {"_id": panel_id, "name": panel_id, "fields": []}
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)},
                {"_id": 1, "name": 1, "fields": 1, "allowedModules": 1, "allowedPanels": 1}
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid trigger panel ID.")
        if not panel:
            raise HTTPException(status_code=404, detail="Trigger panel not found.")
        return panel

    async def validate_target_id(seller_id: str, panel_id: str):
        if panel_id in SYSTEM_MODULE_IDS:
            return True
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)},
                {"_id": 1}
            )
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid target panel ID: {panel_id}")
        if not panel:
            raise HTTPException(status_code=404, detail=f"Target panel not found: {panel_id}")
        return True

    def validate_target(t: RuleTarget):
        if t.action_type not in ALLOWED_ACTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid action type: {t.action_type}")
        if t.data_mode not in ALLOWED_DATA_MODES:
            raise HTTPException(status_code=400, detail=f"Invalid data_mode: {t.data_mode}. Use: smart_sync, manual_only, full_copy")
        if t.action_type == "update_record":
            if not t.match_target_field:
                raise HTTPException(status_code=400, detail="match_target_field required: which field in target identifies the record.")
            if not t.match_source_field:
                raise HTTPException(status_code=400, detail="match_source_field required: which source field contains the match value.")
            if not t.update_operation or t.update_operation not in ALLOWED_UPDATE_OPS:
                raise HTTPException(status_code=400, detail="Valid update_operation required.")
            if not t.update_field:
                raise HTTPException(status_code=400, detail="update_field required for update_record.")
            if t.update_field in BLOCKED_SYSTEM_FIELDS:
                raise HTTPException(status_code=400, detail=f"Cannot modify system field '{t.update_field}'.")
            if not t.update_value_from:
                raise HTTPException(status_code=400, detail="update_value_from required for update_record.")
        if t.action_type in ("create_record", "create_records_per_item"):
            # manual_only requires explicit mappings; smart_sync/full_copy can work without
            if t.data_mode == "manual_only":
                if not t.field_mappings or len(t.field_mappings) == 0:
                    raise HTTPException(status_code=400, detail="field_mappings required for manual_only mode.")
            if t.field_mappings and len(t.field_mappings) > MAX_FIELD_MAPPINGS:
                raise HTTPException(status_code=400, detail=f"Maximum {MAX_FIELD_MAPPINGS} field mappings.")

    async def get_panel_name(panel_id: str) -> str:
        if panel_id in SYSTEM_MODULE_IDS:
            labels = {"inventory": "Inventory", "invoices": "Invoices", "buyers": "Buyers",
                      "suppliers": "Suppliers", "purchase_orders": "Purchase Orders",
                      "quotations": "Quotations", "composite_products": "Composite Products", "employees": "Employees"}
            return labels.get(panel_id, panel_id)
        try:
            p = await db.panels.find_one({"_id": ObjectId(panel_id)}, {"name": 1})
            return p["name"] if p else "Unknown"
        except Exception:
            return "Unknown"

    # ── LIST RULES ──
    @router.get("/automation/rules")
    async def list_rules(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        rules = await db.automation_rules.find(
            {"sellerId": ObjectId(seller_id)},
        ).sort([("priority", 1), ("createdAt", -1)]).to_list(MAX_RULES_PER_BUSINESS)

        serialized = serialize_doc(rules)

        # Enrich with panel names
        for r in serialized:
            r["trigger_panel_name"] = await get_panel_name(r.get("trigger_panel_id", ""))
            for t in r.get("targets", []):
                t["target_panel_name"] = await get_panel_name(t.get("target_panel_id", ""))

        return {"rules": serialized, "count": len(serialized), "limit": MAX_RULES_PER_BUSINESS}

    # ── CREATE RULE ──
    @router.post("/automation/rules")
    async def create_rule(data: CreateRuleRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        count = await db.automation_rules.count_documents({"sellerId": ObjectId(seller_id)})
        if count >= MAX_RULES_PER_BUSINESS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_RULES_PER_BUSINESS} rules allowed.")

        if data.trigger_type not in ALLOWED_TRIGGER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid trigger type: {data.trigger_type}")
        if data.trigger_type == "condition_based" and not data.condition:
            raise HTTPException(status_code=400, detail="Condition required for condition_based trigger.")
        if data.condition and data.condition.operator and data.condition.operator not in ALLOWED_OPERATORS:
            raise HTTPException(status_code=400, detail=f"Invalid operator: {data.condition.operator}")
        if len(data.targets) > MAX_TARGETS_PER_RULE:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_TARGETS_PER_RULE} targets per rule.")

        await validate_trigger_panel(seller_id, data.trigger_panel_id)

        for t in data.targets:
            await validate_target_id(seller_id, t.target_panel_id)
            validate_target(t)

        now = datetime.now(timezone.utc)
        doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name.strip(),
            "trigger_panel_id": data.trigger_panel_id,
            "trigger_type": data.trigger_type,
            "condition": data.condition.model_dump() if data.condition else None,
            "targets": [t.model_dump() for t in data.targets],
            "is_active": data.is_active,
            "priority": data.priority,
            "execution_count": 0,
            "last_executed": None,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await db.automation_rules.insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.info(f"Rule created: {data.name} ({len(data.targets)} targets)")
        return serialize_doc(doc)

    # ── UPDATE RULE ──
    @router.put("/automation/rules/{rule_id}")
    async def update_rule(rule_id: str, data: UpdateRuleRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        try:
            rule = await db.automation_rules.find_one({"_id": ObjectId(rule_id), "sellerId": ObjectId(seller_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid rule ID.")
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found.")

        update = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            update["name"] = data.name.strip()
        if data.is_active is not None:
            update["is_active"] = data.is_active
        if data.trigger_type is not None:
            if data.trigger_type not in ALLOWED_TRIGGER_TYPES:
                raise HTTPException(status_code=400, detail="Invalid trigger type.")
            update["trigger_type"] = data.trigger_type
        if data.condition is not None:
            update["condition"] = data.condition.model_dump()
        if data.targets is not None:
            for t in data.targets:
                await validate_target_id(seller_id, t.target_panel_id)
                validate_target(t)
            update["targets"] = [t.model_dump() for t in data.targets]
        if data.priority is not None:
            update["priority"] = data.priority

        await db.automation_rules.update_one({"_id": ObjectId(rule_id)}, {"$set": update})
        return {"message": "Rule updated"}

    # ── DELETE RULE ──
    @router.delete("/automation/rules/{rule_id}")
    async def delete_rule(rule_id: str, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)
        result = await db.automation_rules.delete_one({"_id": ObjectId(rule_id), "sellerId": ObjectId(seller_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Rule not found.")
        return {"message": "Rule deleted"}

    # ── LOGS ──
    @router.get("/automation/logs")
    async def get_logs(authorization: str = Header(...), limit: int = 50):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)
        logs = await db.automation_logs.find(
            {"sellerId": ObjectId(seller_id)}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        return {"logs": serialize_doc(logs)}

    # ── PREVIEW (dry-run data output) ──
    class PreviewRequest(BaseModel):
        trigger_panel_id: str
        targets: List[RuleTarget]
        sample_data: Optional[dict] = None

    @router.post("/automation/preview")
    async def preview_rule(data: PreviewRequest, authorization: str = Header(...)):
        """Preview what data each target would receive given sample source data.
        Uses the first record from the source panel if no sample_data provided."""
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        # Get sample data from source panel
        source_data = data.sample_data
        if not source_data:
            sample_record = await db.panel_records.find_one(
                {"panelId": ObjectId(data.trigger_panel_id), "sellerId": ObjectId(seller_id)},
                {"_id": 0, "data": 1}
            )
            source_data = sample_record.get("data", {}) if sample_record else {}

        if not source_data:
            return {"previews": [], "message": "No sample data available. Add a record to this panel first."}

        previews = []
        for t in data.targets:
            target_dict = t.model_dump()
            target_panel_id = t.target_panel_id
            target_field_keys = await get_target_field_keys(target_panel_id, seller_id)
            target_name = await get_panel_name(target_panel_id)

            if t.action_type == "update_record":
                match_tf = t.match_target_field or "(not set)"
                match_sf = t.match_source_field or t.relation_field or "(not set)"
                match_val = source_data.get(match_sf, "?") if match_sf != "(not set)" else "?"

                # Check if source field is a relation → value is an ID
                sf_info = await get_source_field_info(data.trigger_panel_id, match_sf) if match_sf != "(not set)" else {}
                is_relation = sf_info.get("type") == "relation"
                resolved_val = f"{match_val} (relation ID)" if is_relation else match_val

                update_val = source_data.get(t.update_value_from or "", "?")
                previews.append({
                    "target_panel_id": target_panel_id,
                    "target_panel_name": target_name,
                    "action_type": t.action_type,
                    "match": {
                        "target_field": match_tf,
                        "source_field": match_sf,
                        "resolved_value": resolved_val,
                        "is_relation_id": is_relation,
                    },
                    "update": {
                        "target_field": t.update_field or "(not set)",
                        "operation": t.update_operation or "set_value",
                        "source_field": t.update_value_from or "(not set)",
                        "resolved_value": update_val,
                    },
                    "preview_data": {
                        "match": {match_tf: resolved_val},
                        "update": {t.update_field or "?": f"{t.update_operation}({update_val})"},
                    },
                })
            else:
                mapped = build_mapped_data(target_dict, source_data, "preview_record_id", data.trigger_panel_id, target_field_keys)
                previews.append({
                    "target_panel_id": target_panel_id,
                    "target_panel_name": target_name,
                    "action_type": t.action_type,
                    "data_mode": t.data_mode,
                    "preview_data": mapped,
                    "fields_count": len(mapped),
                })

        return {"previews": previews, "source_data_keys": list(source_data.keys())}


    # ══════════════════════════════════════
    # EXECUTION ENGINE
    # ══════════════════════════════════════

    async def execute_automation(record_data: dict, panel_id: str, record_id: str, seller_id: str, user_id: str, event_type: str = "record_created", _visited_rules: set = None):
        """Entry point: find and execute matching rules for source panel event.
        Data always originates from the SOURCE panel (single source of truth)."""
        if _visited_rules is None:
            _visited_rules = set()

        try:
            valid_triggers = set()
            if event_type == "record_created":
                valid_triggers = {"on_create", "condition_based"}
            elif event_type == "record_updated":
                valid_triggers = {"on_update", "condition_based"}

            rules = await db.automation_rules.find({
                "sellerId": ObjectId(seller_id),
                "trigger_panel_id": panel_id,
                "is_active": True,
                "trigger_type": {"$in": list(valid_triggers)},
            }).sort("priority", 1).to_list(MAX_RULES_PER_BUSINESS)

            if not rules:
                return

            for rule in rules:
                rule_id_str = str(rule["_id"])

                if rule_id_str in _visited_rules:
                    logger.warning(f"Loop prevented: rule '{rule.get('name')}' already executed.")
                    await log_execution(seller_id, rule, panel_id, record_id, event_type, "skipped", "Loop prevented", None)
                    continue

                condition = rule.get("condition")
                if condition and condition.get("field"):
                    if not check_condition(record_data, condition):
                        continue

                _visited_rules.add(rule_id_str)

                # Execute ALL targets in this rule using SOURCE data only
                for target_config in rule.get("targets", []):
                    try:
                        await execute_target(
                            rule, target_config, record_data, record_id,
                            panel_id, seller_id, user_id, event_type
                        )
                    except Exception as e:
                        logger.error(f"Target execution failed: {e} (rule: {rule.get('name')}, target: {target_config.get('target_panel_id')})")
                        await log_execution(seller_id, rule, panel_id, record_id, event_type, "error", str(e), target_config.get("target_panel_id"))

                await db.automation_rules.update_one(
                    {"_id": rule["_id"]},
                    {"$inc": {"execution_count": 1}, "$set": {"last_executed": datetime.now(timezone.utc)}}
                )

        except Exception as e:
            logger.error(f"Automation engine error: {e}")

    async def get_source_field_info(panel_id: str, field_key: str) -> dict:
        """Get field definition from source panel to determine if it's a relation."""
        try:
            if panel_id in SYSTEM_MODULE_IDS:
                for f in SYSTEM_MODULE_FIELDS.get(panel_id, []):
                    if f.get("key") == field_key:
                        return f
                return {}
            panel = await db.panels.find_one(
                {"_id": ObjectId(panel_id)},
                {"fields": 1}
            )
            if panel:
                for f in panel.get("fields", []):
                    if f.get("key") == field_key:
                        return f
        except Exception:
            pass
        return {}

    async def resolve_match_value(source_data: dict, match_source_field: str, source_panel_id: str):
        """Extract the match value from source data.
        If the source field is a relation, the stored value IS the target record's ObjectId.
        Returns (match_value, is_relation_id)."""
        raw_value = source_data.get(match_source_field)
        if raw_value is None or raw_value == "":
            return None, False

        field_info = await get_source_field_info(source_panel_id, match_source_field)
        is_relation = field_info.get("type") == "relation"

        return str(raw_value), is_relation

    async def execute_target(rule: dict, target: dict, source_data: dict, source_record_id: str, source_panel_id: str, seller_id: str, user_id: str, event_type: str):
        """Execute a single target action. Data comes ONLY from source_data (parent panel)."""
        action_type = target.get("action_type", "create_record")
        target_panel_id = target.get("target_panel_id", "")
        relation_field = target.get("relation_field", "")
        now = datetime.now(timezone.utc)

        if action_type == "update_record":
            # ── MATCH: Find the target record ──
            match_target_field = target.get("match_target_field", "")
            match_source_field = target.get("match_source_field", "")

            # Backward compat
            if not match_source_field and relation_field:
                match_source_field = relation_field

            if not match_source_field:
                raise Exception("MATCH config missing: match_source_field is required.")
            if not match_target_field:
                raise Exception("MATCH config missing: match_target_field is required.")

            # Resolve match value — relation fields store ObjectId, data fields store values
            match_value, is_relation_id = await resolve_match_value(source_data, match_source_field, source_panel_id)
            if not match_value:
                raise Exception(f"MATCH failed: Source field '{match_source_field}' is empty in source record.")

            # ── UPDATE: Get the value to apply ──
            operation = target.get("update_operation", "set_value")
            update_field = target.get("update_field", "")
            value_from = target.get("update_value_from", "")

            if not update_field:
                raise Exception("UPDATE config missing: update_field is required.")
            if not value_from:
                raise Exception("UPDATE config missing: update_value_from is required.")

            source_value = source_data.get(value_from)
            if source_value is None:
                raise Exception(f"UPDATE failed: Source field '{value_from}' is empty.")

            # Validate numeric for increment/decrement
            if operation in ("increment", "decrement"):
                try:
                    float(source_value)
                except (ValueError, TypeError):
                    raise Exception(f"UPDATE failed: '{value_from}' value '{source_value}' is not numeric. Increment/decrement requires a number.")

            # ── Execute on system module ──
            if target_panel_id in SYSTEM_MODULE_IDS:
                await update_system_record(target_panel_id, match_target_field, match_value, is_relation_id, update_field, operation, source_value, seller_id)
            else:
                # ── Execute on custom panel ──
                query = {"panelId": ObjectId(target_panel_id), "sellerId": ObjectId(seller_id)}

                if is_relation_id:
                    # Source field is a relation → match_value is an ObjectId → find by _id
                    query["_id"] = ObjectId(match_value)
                elif match_target_field == "_id":
                    query["_id"] = ObjectId(match_value)
                else:
                    # Match by data field value
                    query[f"data.{match_target_field}"] = match_value

                target_record = await db.panel_records.find_one(query)
                if not target_record:
                    raise Exception(f"MATCH failed: No record found in target where {match_target_field} = {match_value}")
                new_val = apply_operation(target_record.get("data", {}).get(update_field, 0), operation, source_value)
                await db.panel_records.update_one(
                    {"_id": target_record["_id"]},
                    {"$set": {f"data.{update_field}": new_val, "updatedAt": now}}
                )

            await log_execution(seller_id, rule, source_panel_id, source_record_id, event_type, "success",
                f"Updated {update_field} ({operation})", target_panel_id)

        elif action_type == "create_record":
            target_field_keys = await get_target_field_keys(target_panel_id, seller_id)
            target_field_defs = await get_target_field_defs(target_panel_id, seller_id)
            mapped_data = build_mapped_data(target, source_data, source_record_id, source_panel_id, target_field_keys)
            # Auto-link relation fields back to the source panel/module
            auto_link_relations(mapped_data, target_field_defs, source_panel_id, source_record_id)
            entity_id = source_data.get(relation_field, "") if relation_field else source_record_id

            dup = await db.panel_records.find_one({
                "panelId": ObjectId(target_panel_id) if target_panel_id not in SYSTEM_MODULE_IDS else target_panel_id,
                "sellerId": ObjectId(seller_id),
                "entity_id": entity_id,
                "parent_id": source_record_id,
                "source_rule": str(rule["_id"]),
            })
            if dup:
                await log_execution(seller_id, rule, source_panel_id, source_record_id, event_type, "skipped", "Duplicate prevented", target_panel_id)
                return

            new_record = {
                "panelId": ObjectId(target_panel_id) if target_panel_id not in SYSTEM_MODULE_IDS else target_panel_id,
                "sellerId": ObjectId(seller_id),
                "data": mapped_data,
                "entity_id": entity_id,
                "parent_id": source_record_id,
                "source_panel": source_panel_id,
                "source_rule": str(rule["_id"]),
                "createdBy": "automation",
                "createdAt": now,
                "updatedAt": now,
            }
            result = await db.panel_records.insert_one(new_record)
            await log_execution(seller_id, rule, source_panel_id, source_record_id, event_type, "success",
                "Created record", target_panel_id, str(result.inserted_id))

        elif action_type == "create_records_per_item":
            items = extract_line_items(source_data)
            if not items:
                await log_execution(seller_id, rule, source_panel_id, source_record_id, event_type, "skipped", "No line items", target_panel_id)
                return

            created = 0
            target_field_defs_items = await get_target_field_defs(target_panel_id, seller_id)
            for item in items:
                # Merge item with source — but source is always parent
                item_data = {**source_data, **item}
                target_field_keys = await get_target_field_keys(target_panel_id, seller_id)
                mapped_data = build_mapped_data(target, item_data, source_record_id, source_panel_id, target_field_keys)
                auto_link_relations(mapped_data, target_field_defs_items, source_panel_id, source_record_id)
                item_entity_id = item.get("productId") or item.get("product_id") or ""

                dup = await db.panel_records.find_one({
                    "panelId": ObjectId(target_panel_id) if target_panel_id not in SYSTEM_MODULE_IDS else target_panel_id,
                    "sellerId": ObjectId(seller_id),
                    "entity_id": item_entity_id,
                    "parent_id": source_record_id,
                    "source_rule": str(rule["_id"]),
                })
                if dup:
                    continue

                new_record = {
                    "panelId": ObjectId(target_panel_id) if target_panel_id not in SYSTEM_MODULE_IDS else target_panel_id,
                    "sellerId": ObjectId(seller_id),
                    "data": mapped_data,
                    "entity_id": item_entity_id,
                    "parent_id": source_record_id,
                    "source_panel": source_panel_id,
                    "source_rule": str(rule["_id"]),
                    "createdBy": "automation",
                    "createdAt": now,
                    "updatedAt": now,
                }
                await db.panel_records.insert_one(new_record)
                created += 1

            await log_execution(seller_id, rule, source_panel_id, source_record_id, event_type, "success",
                f"Created {created}/{len(items)} records", target_panel_id)

    # ── System module field definitions (for execution-time smart sync / full copy) ──
    SYSTEM_MODULE_FIELDS = {
        "inventory": [
            {"key": "productName", "label": "Product Name", "type": "text"},
            {"key": "sku", "label": "SKU", "type": "text"},
            {"key": "category", "label": "Category", "type": "text"},
            {"key": "stock", "label": "Stock", "type": "number"},
            {"key": "quantity", "label": "Quantity", "type": "number"},
            {"key": "minStock", "label": "Min Stock", "type": "number"},
            {"key": "reorderPoint", "label": "Reorder Point", "type": "number"},
        ],
        "invoices": [
            {"key": "invoiceNumber", "label": "Invoice Number", "type": "text"},
            {"key": "buyerName", "label": "Buyer Name", "type": "text"},
            {"key": "totalAmount", "label": "Total Amount", "type": "number"},
        ],
        "buyers": [
            {"key": "name", "label": "Name", "type": "text"},
            {"key": "phone", "label": "Phone", "type": "text"},
            {"key": "email", "label": "Email", "type": "text"},
        ],
        "suppliers": [
            {"key": "name", "label": "Name", "type": "text"},
            {"key": "phone", "label": "Phone", "type": "text"},
            {"key": "email", "label": "Email", "type": "text"},
        ],
        "purchase_orders": [
            {"key": "poNumber", "label": "PO Number", "type": "text"},
            {"key": "supplierName", "label": "Supplier Name", "type": "text"},
            {"key": "totalAmount", "label": "Total Amount", "type": "number"},
        ],
        "quotations": [
            {"key": "quotationNumber", "label": "Quotation Number", "type": "text"},
            {"key": "buyerName", "label": "Buyer Name", "type": "text"},
            {"key": "totalAmount", "label": "Total Amount", "type": "number"},
        ],
        "composite_products": [
            {"key": "name", "label": "Name", "type": "text"},
            {"key": "sku", "label": "SKU", "type": "text"},
        ],
        "employees": [
            {"key": "name", "label": "Name", "type": "text"},
            {"key": "role", "label": "Role", "type": "text"},
            {"key": "email", "label": "Email", "type": "text"},
        ],
    }
    SYSTEM_MODULE_FIELD_KEYS = {
        mid: {f["key"] for f in fields} for mid, fields in SYSTEM_MODULE_FIELDS.items()
    }

    async def get_target_field_keys(target_panel_id: str, seller_id: str) -> set:
        """Get the set of valid field keys for a target panel at execution time.
        Includes ALL field types (including relation fields) for smart sync matching."""
        if target_panel_id in SYSTEM_MODULE_FIELD_KEYS:
            return SYSTEM_MODULE_FIELD_KEYS[target_panel_id]
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(target_panel_id), "sellerId": ObjectId(seller_id)},
                {"fields": 1}
            )
            if panel:
                return {f["key"] for f in panel.get("fields", [])}
        except Exception:
            pass
        return set()

    async def get_target_field_defs(target_panel_id: str, seller_id: str) -> list:
        """Get full field definitions for a target panel (needed for relation auto-linking)."""
        if target_panel_id in SYSTEM_MODULE_IDS:
            return SYSTEM_MODULE_FIELDS.get(target_panel_id, [])
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(target_panel_id), "sellerId": ObjectId(seller_id)},
                {"fields": 1}
            )
            if panel:
                return panel.get("fields", [])
        except Exception:
            pass
        return []

    def auto_link_relations(mapped_data: dict, target_fields: list, source_panel_id: str, source_record_id: str):
        """Auto-populate relation fields that link back to the source panel/module.
        If a target field is type=relation and its relatedPanel matches the source, fill with source_record_id.
        This OVERRIDES any smart_sync text value — relation fields must store ObjectIds."""
        for f in target_fields:
            fkey = f.get("key", "")
            if f.get("type") != "relation" or not fkey:
                continue
            related = f.get("relatedPanel", "")
            if not related:
                continue
            # If this relation points to the source panel → auto-link with ObjectId
            if related == source_panel_id:
                mapped_data[fkey] = source_record_id

    def _normalize_key(key: str) -> str:
        """Normalize field key for fuzzy matching: camelCase → lowercase, snake_case → lowercase, strip underscores."""
        import re
        # Convert camelCase to snake_case first, then lowercase
        s1 = re.sub(r'([A-Z])', r'_\1', key).lower()
        # Remove all underscores and spaces for comparison
        return re.sub(r'[_\s-]', '', s1)

    def build_mapped_data(target: dict, source_data: dict, source_record_id: str, source_panel_id: str, target_field_keys: set = None) -> dict:
        """Build the data dict for a new record based on data_mode.

        Modes:
          manual_only  — only explicit field_mappings
          smart_sync   — explicit mappings first, then auto-fill matching field names (including normalized matching)
          full_copy    — for each target field that exists in source, copy value
        """
        data_mode = target.get("data_mode", "smart_sync")
        mapped = {}

        # Step 1: Always apply explicit field_mappings (highest priority)
        for fm in (target.get("field_mappings") or []):
            tf = fm.get("target_field", "")
            if not tf:
                continue
            mt = fm.get("mapping_type", "field")
            if mt == "field" and fm.get("source_field"):
                mapped[tf] = source_data.get(fm["source_field"])
            elif mt == "default" and fm.get("default_value") is not None:
                mapped[tf] = fm["default_value"]
            elif mt == "reference":
                if fm.get("source_field") == "_parent_id":
                    mapped[tf] = source_record_id
                elif fm.get("source_field") == "_source_panel":
                    mapped[tf] = source_panel_id
                elif fm.get("source_field"):
                    mapped[tf] = source_data.get(fm["source_field"])

        # Step 2: Apply mode-specific logic
        if data_mode == "manual_only":
            # Only explicit mappings — already done
            pass

        elif data_mode in ("smart_sync", "full_copy") and target_field_keys:
            # Build normalized lookup for source data
            norm_source = {}
            for skey, sval in source_data.items():
                norm_source[_normalize_key(skey)] = (skey, sval)

            for tkey in target_field_keys:
                if tkey in mapped:
                    continue
                # Exact match first
                if tkey in source_data:
                    mapped[tkey] = source_data[tkey]
                    continue
                # Normalized match (camelCase ↔ snake_case)
                norm_t = _normalize_key(tkey)
                if norm_t in norm_source:
                    _, sval = norm_source[norm_t]
                    mapped[tkey] = sval

        return mapped

    def extract_line_items(data: dict) -> list:
        items = data.get("items")
        if isinstance(items, list) and items:
            return items
        items = data.get("line_items")
        if isinstance(items, list) and items:
            return items
        if data.get("productId") or data.get("product_id"):
            return [data]
        return []

    def check_condition(data: dict, cond: dict) -> bool:
        field = cond.get("field", "")
        op = cond.get("operator", "")
        expected = cond.get("value", "")
        actual = data.get(field)
        if op == "equals":
            return str(actual) == str(expected) if actual is not None else False
        elif op == "not_equals":
            return str(actual) != str(expected) if actual is not None else True
        elif op == "greater_than":
            try:
                return float(actual) > float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "less_than":
            try:
                return float(actual) < float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "contains":
            return str(expected).lower() in str(actual or "").lower()
        elif op == "not_empty":
            return actual is not None and actual != "" and actual != []
        elif op == "is_empty":
            return actual is None or actual == "" or actual == []
        return False

    def apply_operation(current, operation: str, value):
        if operation == "set_value":
            return value
        try:
            c = float(current or 0)
            v = float(value)
            if operation == "increment":
                return c + v
            elif operation == "decrement":
                return max(0, c - v)
        except (ValueError, TypeError):
            pass
        return value

    async def update_system_record(module: str, match_target_field: str, match_value: str, is_relation_id: bool, update_field: str, op: str, value, seller_id: str):
        """Find a system record by MATCH condition, then UPDATE the target field.

        If is_relation_id=True, match_value is an ObjectId → find by _id.
        Otherwise, match by the specified target field value.
        """
        try:
            nv = float(value)
        except (ValueError, TypeError):
            nv = None

        if module == "inventory":
            safe_update = {"stock", "quantity", "minStock", "reorderPoint"}
            if update_field not in safe_update:
                raise Exception(f"Cannot modify '{update_field}' on inventory. Allowed: {safe_update}")

            query = {"sellerId": ObjectId(seller_id)}

            if is_relation_id:
                # Source field is a relation to inventory → value is the sellerListing ObjectId
                query["_id"] = ObjectId(match_value)
            elif match_target_field in ("_id", "id"):
                query["_id"] = ObjectId(match_value)
            elif match_target_field == "productName":
                query["productName"] = match_value
            elif match_target_field == "sku":
                query["sku"] = match_value
            else:
                query[match_target_field] = match_value

            listing = await db.sellerListings.find_one(query)
            if not listing:
                raise Exception(f"MATCH failed: No inventory record where {match_target_field} = {match_value}")

            new_val = apply_operation(listing.get(update_field, 0), op, nv or value)
            await db.sellerListings.update_one(
                {"_id": listing["_id"]},
                {"$set": {update_field: new_val, "updatedAt": datetime.now(timezone.utc)}}
            )
        else:
            raise Exception(f"System module '{module}' not yet supported for updates.")

    async def log_execution(seller_id, rule, source_panel_id, record_id, event_type, status, message="", target_panel_id=None, target_record_id=None):
        await db.automation_logs.insert_one({
            "sellerId": ObjectId(seller_id),
            "ruleId": rule["_id"],
            "ruleName": rule.get("name", ""),
            "trigger_panel_id": source_panel_id,
            "record_id": record_id,
            "target_panel_id": target_panel_id,
            "target_record_id": target_record_id,
            "event": event_type,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
        })

    router.execute_automation = execute_automation
    return router
