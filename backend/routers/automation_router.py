"""
Automation Router - Workflow Automation Engine (Phase 4 Full)
Handles automation rule CRUD and execution.
Supports: trigger types, action types (update/create/create_per_item),
field mapping, default values, duplicate prevention, record linking,
field visibility, and event chaining with infinite loop protection.
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

MAX_RULES_PER_BUSINESS = 50
MAX_FIELD_MAPPINGS = 30
ALLOWED_OPERATORS = {"equals", "not_equals", "greater_than", "less_than", "contains", "not_empty", "is_empty"}
ALLOWED_TRIGGER_TYPES = {"on_create", "on_update", "condition_based"}
ALLOWED_ACTION_TYPES = {"update_record", "create_record", "create_records_per_item"}
ALLOWED_UPDATE_OPS = {"increment", "decrement", "set_value"}
BLOCKED_SYSTEM_FIELDS = {"_id", "sellerId", "createdAt", "updatedAt", "createdBy"}


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


class CreateRuleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_panel_id: str = Field(...)
    trigger_type: str = Field(default="on_create", description="on_create | on_update | condition_based")
    condition: Optional[AutomationCondition] = None
    action_type: str = Field(default="create_record", description="update_record | create_record | create_records_per_item")
    target_panel_id: str = Field(...)
    relation_field: str = Field(...)
    # For update_record actions
    update_operation: Optional[str] = None
    update_field: Optional[str] = None
    update_value_from: Optional[str] = None
    # For create actions
    field_mappings: Optional[List[FieldMapping]] = None
    field_visibility: Optional[List[FieldVisibility]] = None
    is_active: bool = True
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    condition: Optional[AutomationCondition] = None
    action_type: Optional[str] = None
    target_panel_id: Optional[str] = None
    relation_field: Optional[str] = None
    update_operation: Optional[str] = None
    update_field: Optional[str] = None
    update_value_from: Optional[str] = None
    field_mappings: Optional[List[FieldMapping]] = None
    field_visibility: Optional[List[FieldVisibility]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


def init_automation_router(db, verify_token_func):
    from utils.permissions import authenticate_user, resolve_seller_id, is_platform_admin

    router = APIRouter(tags=["Automation"])

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
        """Ensure trigger panel is a custom panel."""
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

    SYSTEM_MODULE_IDS = {"inventory", "invoices", "buyers", "suppliers", "purchase_orders", "quotations", "composite_products", "employees"}

    async def validate_target_panel(seller_id: str, panel_id: str):
        """Validate target panel exists (custom panel or system module)."""
        # System modules are valid targets
        if panel_id in SYSTEM_MODULE_IDS:
            return {"_id": panel_id, "name": panel_id, "type": "system"}
        # Custom panel
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)},
                {"_id": 1, "name": 1, "fields": 1}
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid target panel ID.")
        if not panel:
            raise HTTPException(status_code=404, detail="Target panel not found.")
        return panel

    def validate_rule_data(data):
        """Validate rule configuration."""
        if data.trigger_type not in ALLOWED_TRIGGER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid trigger type: {data.trigger_type}")
        if data.action_type not in ALLOWED_ACTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid action type: {data.action_type}")
        if data.trigger_type == "condition_based" and not data.condition:
            raise HTTPException(status_code=400, detail="Condition is required for condition_based trigger.")
        if data.condition and data.condition.operator not in ALLOWED_OPERATORS:
            raise HTTPException(status_code=400, detail=f"Invalid operator: {data.condition.operator}")
        if data.action_type == "update_record":
            if not data.update_operation or data.update_operation not in ALLOWED_UPDATE_OPS:
                raise HTTPException(status_code=400, detail="Valid update_operation required for update_record.")
            if not data.update_field:
                raise HTTPException(status_code=400, detail="update_field required for update_record.")
            if data.update_field in BLOCKED_SYSTEM_FIELDS:
                raise HTTPException(status_code=400, detail=f"Cannot modify system field '{data.update_field}'.")
            if not data.update_value_from:
                raise HTTPException(status_code=400, detail="update_value_from required for update_record.")
        if data.action_type in ("create_record", "create_records_per_item"):
            if not data.field_mappings or len(data.field_mappings) == 0:
                raise HTTPException(status_code=400, detail="field_mappings required for create actions.")
            if len(data.field_mappings) > MAX_FIELD_MAPPINGS:
                raise HTTPException(status_code=400, detail=f"Maximum {MAX_FIELD_MAPPINGS} field mappings allowed.")

    # ── LIST RULES ──
    @router.get("/automation/rules")
    async def list_rules(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        cursor = db.automation_rules.find(
            {"sellerId": ObjectId(seller_id)},
        ).sort([("priority", 1), ("createdAt", -1)])
        rules = await cursor.to_list(MAX_RULES_PER_BUSINESS)

        # Enrich with panel names
        panel_ids = set()
        for r in rules:
            panel_ids.add(r.get("trigger_panel_id"))
            panel_ids.add(r.get("target_panel_id"))

        panel_names = {}
        for pid in panel_ids:
            if not pid:
                continue
            try:
                p = await db.panels.find_one({"_id": ObjectId(pid)}, {"name": 1})
                if p:
                    panel_names[pid] = p["name"]
            except Exception:
                pass

        serialized = serialize_doc(rules)
        for r in serialized:
            r["trigger_panel_name"] = panel_names.get(r.get("trigger_panel_id"), "Unknown")
            r["target_panel_name"] = panel_names.get(r.get("target_panel_id"), "Unknown")

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

        validate_rule_data(data)
        trigger_panel = await validate_trigger_panel(seller_id, data.trigger_panel_id)

        # Validate relation_field exists in trigger panel
        trigger_fields = {f["key"]: f for f in trigger_panel.get("fields", [])}
        if data.relation_field not in trigger_fields:
            raise HTTPException(status_code=400, detail=f"Relation field '{data.relation_field}' not found in trigger panel.")
        rf = trigger_fields[data.relation_field]
        if rf.get("type") != "relation":
            raise HTTPException(status_code=400, detail=f"Field '{data.relation_field}' is not a relation field.")

        # For create actions, validate target panel
        if data.action_type in ("create_record", "create_records_per_item"):
            await validate_target_panel(seller_id, data.target_panel_id)

        now = datetime.now(timezone.utc)
        doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name.strip(),
            "trigger_panel_id": data.trigger_panel_id,
            "trigger_type": data.trigger_type,
            "condition": data.condition.model_dump() if data.condition else None,
            "action_type": data.action_type,
            "target_panel_id": data.target_panel_id,
            "relation_field": data.relation_field,
            "update_operation": data.update_operation,
            "update_field": data.update_field,
            "update_value_from": data.update_value_from,
            "field_mappings": [fm.model_dump() for fm in data.field_mappings] if data.field_mappings else [],
            "field_visibility": [fv.model_dump() for fv in data.field_visibility] if data.field_visibility else [],
            "is_active": data.is_active,
            "priority": data.priority,
            "execution_count": 0,
            "last_executed": None,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await db.automation_rules.insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.info(f"Automation rule created: {data.name} for seller {seller_id}")
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
                raise HTTPException(status_code=400, detail=f"Invalid trigger type: {data.trigger_type}")
            update["trigger_type"] = data.trigger_type
        if data.condition is not None:
            if data.condition.operator and data.condition.operator not in ALLOWED_OPERATORS:
                raise HTTPException(status_code=400, detail=f"Invalid operator: {data.condition.operator}")
            update["condition"] = data.condition.model_dump()
        if data.action_type is not None:
            if data.action_type not in ALLOWED_ACTION_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid action type: {data.action_type}")
            update["action_type"] = data.action_type
        if data.target_panel_id is not None:
            update["target_panel_id"] = data.target_panel_id
        if data.relation_field is not None:
            update["relation_field"] = data.relation_field
        if data.update_operation is not None:
            update["update_operation"] = data.update_operation
        if data.update_field is not None:
            update["update_field"] = data.update_field
        if data.update_value_from is not None:
            update["update_value_from"] = data.update_value_from
        if data.field_mappings is not None:
            update["field_mappings"] = [fm.model_dump() for fm in data.field_mappings]
        if data.field_visibility is not None:
            update["field_visibility"] = [fv.model_dump() for fv in data.field_visibility]
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

    # ── GET EXECUTION LOGS ──
    @router.get("/automation/logs")
    async def get_automation_logs(authorization: str = Header(...), limit: int = 50):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        cursor = db.automation_logs.find(
            {"sellerId": ObjectId(seller_id)},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(limit)
        return {"logs": serialize_doc(logs)}

    # ══════════════════════════════════════
    # EXECUTION ENGINE
    # ══════════════════════════════════════

    async def execute_automation(record_data: dict, panel_id: str, record_id: str, seller_id: str, user_id: str, event_type: str = "record_created", _visited_rules: set = None):
        """Main entry: check and execute automation rules for a panel event."""
        if _visited_rules is None:
            _visited_rules = set()

        try:
            # Map event to trigger types
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

                # Infinite loop guard
                if rule_id_str in _visited_rules:
                    logger.warning(f"Loop detected: rule '{rule.get('name')}' already executed. Skipping.")
                    await log_execution(seller_id, rule, panel_id, record_id, event_type, "skipped", "Infinite loop prevented")
                    continue

                # Check condition if present
                condition = rule.get("condition")
                if condition and condition.get("field"):
                    if not check_condition(record_data, condition):
                        continue

                _visited_rules.add(rule_id_str)

                try:
                    await execute_rule(rule, record_data, record_id, panel_id, seller_id, user_id, event_type, _visited_rules)
                except Exception as e:
                    logger.error(f"Rule execution failed: {e} (rule: {rule.get('name')})")
                    await log_execution(seller_id, rule, panel_id, record_id, event_type, "error", str(e))

        except Exception as e:
            logger.error(f"Automation engine error: {e}")

    async def execute_rule(rule: dict, record_data: dict, record_id: str, panel_id: str, seller_id: str, user_id: str, event_type: str, _visited_rules: set):
        """Execute a single rule based on its action_type."""
        action_type = rule.get("action_type", "update_record")
        relation_field = rule.get("relation_field", "")
        target_panel_id = rule.get("target_panel_id", "")
        now = datetime.now(timezone.utc)

        related_id = record_data.get(relation_field)

        if action_type == "update_record":
            # Update existing record via relation
            if not related_id:
                logger.warning(f"Automation: relation field '{relation_field}' empty, skipping update.")
                return

            operation = rule.get("update_operation", "set_value")
            target_field = rule.get("update_field", "")
            value_from = rule.get("update_value_from", "")
            source_value = record_data.get(value_from)

            if source_value is None:
                logger.warning(f"Automation: value_from '{value_from}' is empty, skipping.")
                return

            # Check if target is a system module or custom panel
            target_panel = await db.panels.find_one({"_id": ObjectId(target_panel_id)})
            if target_panel:
                # Custom panel update
                target_record = await db.panel_records.find_one({
                    "_id": ObjectId(related_id),
                    "panelId": ObjectId(target_panel_id),
                    "sellerId": ObjectId(seller_id),
                })
                if not target_record:
                    logger.warning(f"Target record {related_id} not found.")
                    return
                new_val = apply_operation(target_record.get("data", {}).get(target_field, 0), operation, source_value)
                await db.panel_records.update_one(
                    {"_id": ObjectId(related_id)},
                    {"$set": {f"data.{target_field}": new_val, "updatedAt": now}}
                )
            else:
                # System module update (inventory)
                await update_system_record(target_panel_id, related_id, target_field, operation, source_value, seller_id)

            await log_execution(seller_id, rule, panel_id, record_id, event_type, "success",
                f"Updated {target_field} ({operation}) with {source_value}", target_panel_id=target_panel_id, target_record_id=related_id)
            await db.automation_rules.update_one({"_id": rule["_id"]}, {"$inc": {"execution_count": 1}, "$set": {"last_executed": now}})

        elif action_type == "create_record":
            # Create a single record in target panel with field mappings
            mapped_data = build_mapped_data(rule, record_data, record_id, panel_id)

            # Duplicate prevention: check entity_id + parent_id
            entity_id = record_data.get(relation_field, "")
            dup = await db.panel_records.find_one({
                "panelId": ObjectId(target_panel_id),
                "sellerId": ObjectId(seller_id),
                "entity_id": entity_id,
                "parent_id": record_id,
                "source_rule": str(rule["_id"]),
            })
            if dup:
                logger.info(f"Duplicate prevented: record already exists for entity {entity_id} + parent {record_id}")
                await log_execution(seller_id, rule, panel_id, record_id, event_type, "skipped", "Duplicate prevented")
                return

            new_record = {
                "panelId": ObjectId(target_panel_id),
                "sellerId": ObjectId(seller_id),
                "data": mapped_data,
                "entity_id": entity_id,
                "parent_id": record_id,
                "source_panel": panel_id,
                "source_rule": str(rule["_id"]),
                "createdBy": "automation",
                "createdAt": now,
                "updatedAt": now,
            }
            result = await db.panel_records.insert_one(new_record)

            await log_execution(seller_id, rule, panel_id, record_id, event_type, "success",
                f"Created record in target panel", target_panel_id=target_panel_id, target_record_id=str(result.inserted_id))
            await db.automation_rules.update_one({"_id": rule["_id"]}, {"$inc": {"execution_count": 1}, "$set": {"last_executed": now}})

            # Trigger chained automations on the new record
            try:
                await execute_automation(mapped_data, target_panel_id, str(result.inserted_id), seller_id, user_id, "record_created", _visited_rules)
            except Exception as e:
                logger.error(f"Chained automation error: {e}")

        elif action_type == "create_records_per_item":
            # Extract line items from source record and create one record per item
            items = extract_line_items(record_data)

            if not items:
                logger.warning(f"No line items found in record {record_id}")
                await log_execution(seller_id, rule, panel_id, record_id, event_type, "skipped", "No line items found")
                return

            created_count = 0
            for item in items:
                # Merge item data with record data for mapping
                item_data = {**record_data, **item}

                mapped_data = build_mapped_data(rule, item_data, record_id, panel_id)

                # Duplicate prevention per item
                item_entity_id = item.get("productId") or item.get("product_id") or item_data.get(relation_field, "")
                dup = await db.panel_records.find_one({
                    "panelId": ObjectId(target_panel_id),
                    "sellerId": ObjectId(seller_id),
                    "entity_id": item_entity_id,
                    "parent_id": record_id,
                    "source_rule": str(rule["_id"]),
                })
                if dup:
                    logger.info(f"Duplicate prevented for item entity {item_entity_id}")
                    continue

                new_record = {
                    "panelId": ObjectId(target_panel_id),
                    "sellerId": ObjectId(seller_id),
                    "data": mapped_data,
                    "entity_id": item_entity_id,
                    "parent_id": record_id,
                    "source_panel": panel_id,
                    "source_rule": str(rule["_id"]),
                    "createdBy": "automation",
                    "createdAt": now,
                    "updatedAt": now,
                }
                result = await db.panel_records.insert_one(new_record)
                created_count += 1

                # Trigger chained automations
                try:
                    await execute_automation(mapped_data, target_panel_id, str(result.inserted_id), seller_id, user_id, "record_created", _visited_rules)
                except Exception as e:
                    logger.error(f"Chained automation error for item: {e}")

            await log_execution(seller_id, rule, panel_id, record_id, event_type, "success",
                f"Created {created_count} records from {len(items)} items", target_panel_id=target_panel_id)
            await db.automation_rules.update_one({"_id": rule["_id"]}, {"$inc": {"execution_count": 1}, "$set": {"last_executed": now}})

    def build_mapped_data(rule: dict, source_data: dict, source_record_id: str, source_panel_id: str) -> dict:
        """Build target record data from field mappings + defaults."""
        mapped = {}
        for fm in rule.get("field_mappings", []):
            target = fm.get("target_field", "")
            mtype = fm.get("mapping_type", "field")

            if mtype == "field" and fm.get("source_field"):
                mapped[target] = source_data.get(fm["source_field"])
            elif mtype == "default" and fm.get("default_value") is not None:
                mapped[target] = fm["default_value"]
            elif mtype == "reference":
                if fm.get("source_field") == "_parent_id":
                    mapped[target] = source_record_id
                elif fm.get("source_field") == "_source_panel":
                    mapped[target] = source_panel_id
                elif fm.get("source_field"):
                    mapped[target] = source_data.get(fm["source_field"])

        return mapped

    def extract_line_items(record_data: dict) -> list:
        """Extract line items from a record. Supports invoice-style items array
        and also flat records (treated as single item)."""
        # Check for items array (invoice pattern)
        items = record_data.get("items")
        if isinstance(items, list) and len(items) > 0:
            return items

        # Check for line_items key
        items = record_data.get("line_items")
        if isinstance(items, list) and len(items) > 0:
            return items

        # If record has productId directly, treat as single item
        if record_data.get("productId") or record_data.get("product_id"):
            return [record_data]

        return []

    def check_condition(record_data: dict, condition: dict) -> bool:
        """Evaluate condition against record data."""
        field = condition.get("field", "")
        operator = condition.get("operator", "")
        expected = condition.get("value", "")
        actual = record_data.get(field)

        if operator == "equals":
            return str(actual) == str(expected) if actual is not None else False
        elif operator == "not_equals":
            return str(actual) != str(expected) if actual is not None else True
        elif operator == "greater_than":
            try:
                return float(actual) > float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual) < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "contains":
            return str(expected).lower() in str(actual or "").lower()
        elif operator == "not_empty":
            return actual is not None and actual != "" and actual != []
        elif operator == "is_empty":
            return actual is None or actual == "" or actual == []
        return False

    def apply_operation(current, operation: str, value):
        """Apply increment/decrement/set operation."""
        if operation == "set_value":
            return value
        try:
            current_num = float(current or 0)
            val_num = float(value)
            if operation == "increment":
                return current_num + val_num
            elif operation == "decrement":
                return max(0, current_num - val_num)
        except (ValueError, TypeError):
            pass
        return value

    async def update_system_record(target_module: str, record_id: str, field: str, operation: str, value, seller_id: str):
        """Update a system module record."""
        try:
            numeric_val = float(value)
        except (ValueError, TypeError):
            numeric_val = None

        if target_module == "inventory":
            safe_fields = {"stock", "quantity", "minStock", "reorderPoint"}
            if field not in safe_fields:
                raise Exception(f"Cannot modify field '{field}' on inventory. Allowed: {safe_fields}")
            listing = await db.sellerListings.find_one({"_id": ObjectId(record_id), "sellerId": ObjectId(seller_id)})
            if not listing:
                raise Exception(f"Inventory listing {record_id} not found.")
            current = listing.get(field, 0)
            new_val = apply_operation(current, operation, numeric_val or value)
            await db.sellerListings.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": {field: new_val, "updatedAt": datetime.now(timezone.utc)}}
            )
        else:
            raise Exception(f"System module '{target_module}' automation not yet supported.")

    async def log_execution(seller_id, rule, panel_id, record_id, event_type, status, message="", target_panel_id=None, target_record_id=None):
        """Log automation execution result."""
        await db.automation_logs.insert_one({
            "sellerId": ObjectId(seller_id),
            "ruleId": rule["_id"],
            "ruleName": rule.get("name", ""),
            "trigger_panel_id": panel_id,
            "record_id": record_id,
            "target_panel_id": target_panel_id,
            "target_record_id": target_record_id,
            "action_type": rule.get("action_type", ""),
            "event": event_type,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
        })

    # Expose for panel_router
    router.execute_automation = execute_automation

    return router
