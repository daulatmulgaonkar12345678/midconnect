"""
Automation Router - Workflow Automation Engine (Phase 4 Lite)
Handles automation rule CRUD and execution.
Rules can ONLY trigger on custom panels (not system modules).
Document Builder is READ-ONLY — never triggers automation.
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

MAX_RULES_PER_BUSINESS = 50
ALLOWED_OPERATORS = {"equals", "not_equals", "greater_than", "less_than", "contains", "not_empty", "is_empty"}
ALLOWED_OPERATIONS = {"increment", "decrement", "set_value", "create_record"}
BLOCKED_SYSTEM_FIELDS = {"_id", "sellerId", "createdAt", "updatedAt", "createdBy"}


class AutomationCondition(BaseModel):
    field: str = Field(..., min_length=1)
    operator: str = Field(..., description="equals, not_equals, greater_than, less_than, contains, not_empty, is_empty")
    value: Optional[str] = None


class AutomationAction(BaseModel):
    type: str = Field(..., description="update_related or create_record")
    target_panel_id: str = Field(..., min_length=1)
    target_panel_type: str = Field(default="custom", description="custom or system")
    relation_field: str = Field(..., min_length=1, description="Field key in trigger panel that links to target")
    operation: Optional[str] = None  # increment, decrement, set_value
    field: Optional[str] = None  # target field to update
    value_from: Optional[str] = None  # source field in trigger record


class CreateRuleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_panel_id: str = Field(...)
    condition: AutomationCondition
    actions: List[AutomationAction] = Field(..., min_length=1, max_length=5)
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    condition: Optional[AutomationCondition] = None
    actions: Optional[List[AutomationAction]] = None
    is_active: Optional[bool] = None


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
        """Ensure trigger panel is a custom panel, NOT a system module."""
        try:
            panel = await db.panels.find_one(
                {"_id": ObjectId(panel_id), "sellerId": ObjectId(seller_id)},
                {"_id": 1, "name": 1, "fields": 1}
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid trigger panel ID.")
        if not panel:
            raise HTTPException(status_code=404, detail="Trigger panel not found. Automation only works on custom panels.")
        return panel

    async def validate_actions(seller_id: str, trigger_panel: dict, actions: list):
        """Validate each action: target exists, relation exists, operation is safe."""
        trigger_fields = {f["key"]: f for f in trigger_panel.get("fields", [])}

        for i, action in enumerate(actions):
            act = action if isinstance(action, dict) else action.model_dump()

            # Validate relation_field exists in trigger panel
            rel_field = act.get("relation_field", "")
            if rel_field not in trigger_fields:
                raise HTTPException(status_code=400, detail=f"Action {i+1}: relation_field '{rel_field}' not found in trigger panel.")
            rf = trigger_fields[rel_field]
            if rf.get("type") != "relation":
                raise HTTPException(status_code=400, detail=f"Action {i+1}: field '{rel_field}' is not a relation field.")

            action_type = act.get("type", "")
            if action_type not in ("update_related", "create_record"):
                raise HTTPException(status_code=400, detail=f"Action {i+1}: invalid action type '{action_type}'.")

            if action_type == "update_related":
                op = act.get("operation", "")
                if op not in ALLOWED_OPERATIONS:
                    raise HTTPException(status_code=400, detail=f"Action {i+1}: invalid operation '{op}'.")
                if not act.get("field"):
                    raise HTTPException(status_code=400, detail=f"Action {i+1}: target 'field' is required.")
                if act.get("field") in BLOCKED_SYSTEM_FIELDS:
                    raise HTTPException(status_code=400, detail=f"Action {i+1}: cannot modify system field '{act['field']}'.")
                if not act.get("value_from"):
                    raise HTTPException(status_code=400, detail=f"Action {i+1}: 'value_from' is required.")
                if act["value_from"] not in trigger_fields:
                    raise HTTPException(status_code=400, detail=f"Action {i+1}: value_from field '{act['value_from']}' not found in trigger panel.")

    # ── LIST RULES ──
    @router.get("/automation/rules")
    async def list_rules(authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        cursor = db.automation_rules.find(
            {"sellerId": ObjectId(seller_id)},
        ).sort("createdAt", -1)
        rules = await cursor.to_list(MAX_RULES_PER_BUSINESS)

        # Enrich with panel names
        panel_ids = set()
        for r in rules:
            panel_ids.add(r.get("trigger_panel_id"))
            for a in r.get("actions", []):
                panel_ids.add(a.get("target_panel_id"))

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
            for a in r.get("actions", []):
                a["target_panel_name"] = panel_names.get(a.get("target_panel_id"), "Unknown")

        return {"rules": serialized, "count": len(serialized), "limit": MAX_RULES_PER_BUSINESS}

    # ── CREATE RULE ──
    @router.post("/automation/rules")
    async def create_rule(data: CreateRuleRequest, authorization: str = Header(...)):
        user = await get_current_user(authorization)
        require_admin(user)
        seller_id = await get_seller_id(user)

        count = await db.automation_rules.count_documents({"sellerId": ObjectId(seller_id)})
        if count >= MAX_RULES_PER_BUSINESS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_RULES_PER_BUSINESS} automation rules allowed.")

        if data.condition.operator not in ALLOWED_OPERATORS:
            raise HTTPException(status_code=400, detail=f"Invalid operator: {data.condition.operator}")

        trigger_panel = await validate_trigger_panel(seller_id, data.trigger_panel_id)
        await validate_actions(seller_id, trigger_panel, [a.model_dump() for a in data.actions])

        now = datetime.now(timezone.utc)
        doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name.strip(),
            "trigger_panel_id": data.trigger_panel_id,
            "trigger_panel_type": "custom",
            "condition": data.condition.model_dump(),
            "actions": [a.model_dump() for a in data.actions],
            "is_active": data.is_active,
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
        if data.condition is not None:
            if data.condition.operator not in ALLOWED_OPERATORS:
                raise HTTPException(status_code=400, detail=f"Invalid operator: {data.condition.operator}")
            update["condition"] = data.condition.model_dump()
        if data.actions is not None:
            trigger_panel = await validate_trigger_panel(seller_id, rule["trigger_panel_id"])
            await validate_actions(seller_id, trigger_panel, [a.model_dump() for a in data.actions])
            update["actions"] = [a.model_dump() for a in data.actions]

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

    # ── GET RULE EXECUTION LOG ──
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
    # EXECUTION ENGINE — called from panel_router
    # ══════════════════════════════════════

    async def execute_automation(record_data: dict, panel_id: str, record_id: str, seller_id: str, user_id: str, event_type: str = "record_created"):
        """Check and execute automation rules for a panel event. ONLY custom panels."""
        try:
            rules = await db.automation_rules.find({
                "sellerId": ObjectId(seller_id),
                "trigger_panel_id": panel_id,
                "is_active": True,
            }).to_list(MAX_RULES_PER_BUSINESS)

            if not rules:
                return

            for rule in rules:
                condition = rule.get("condition", {})
                if not check_condition(record_data, condition):
                    continue

                for action in rule.get("actions", []):
                    try:
                        await execute_action(action, record_data, record_id, panel_id, seller_id, user_id, rule)
                    except Exception as e:
                        logger.error(f"Automation action failed: {e} (rule: {rule.get('name')})")
                        await db.automation_logs.insert_one({
                            "sellerId": ObjectId(seller_id),
                            "ruleId": rule["_id"],
                            "ruleName": rule.get("name", ""),
                            "trigger_panel_id": panel_id,
                            "record_id": record_id,
                            "event": event_type,
                            "status": "error",
                            "error": str(e),
                            "timestamp": datetime.now(timezone.utc),
                        })

        except Exception as e:
            logger.error(f"Automation engine error: {e}")

    def check_condition(record_data: dict, condition: dict) -> bool:
        """Evaluate a single condition against record data."""
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

    async def execute_action(action: dict, record_data: dict, record_id: str, panel_id: str, seller_id: str, user_id: str, rule: dict):
        """Execute a single automation action with strict safety checks."""
        action_type = action.get("type", "")
        relation_field = action.get("relation_field", "")
        target_panel_id = action.get("target_panel_id", "")
        target_panel_type = action.get("target_panel_type", "custom")

        # Get the related entity ID from the record
        related_id = record_data.get(relation_field)
        if not related_id:
            logger.warning(f"Automation: relation field '{relation_field}' is empty, skipping.")
            return

        now = datetime.now(timezone.utc)

        if action_type == "update_related":
            operation = action.get("operation", "")
            target_field = action.get("field", "")
            value_from = action.get("value_from", "")
            source_value = record_data.get(value_from)

            if source_value is None:
                logger.warning(f"Automation: value_from '{value_from}' is empty, skipping.")
                return

            # Find and update the target record based on target panel type
            if target_panel_type == "system":
                await update_system_record(target_panel_id, related_id, target_field, operation, source_value, seller_id)
            else:
                # Custom panel record
                target_record = await db.panel_records.find_one({
                    "_id": ObjectId(related_id),
                    "panelId": ObjectId(target_panel_id),
                    "sellerId": ObjectId(seller_id),
                })
                if not target_record:
                    logger.warning(f"Automation: target record {related_id} not found.")
                    return

                update_op = build_update_operation(target_field, operation, source_value, target_record.get("data", {}))
                if update_op:
                    await db.panel_records.update_one(
                        {"_id": ObjectId(related_id)},
                        {"$set": {f"data.{target_field}": update_op, "updatedAt": now}}
                    )

            # Log success
            await db.automation_logs.insert_one({
                "sellerId": ObjectId(seller_id),
                "ruleId": rule["_id"],
                "ruleName": rule.get("name", ""),
                "trigger_panel_id": panel_id,
                "record_id": record_id,
                "target_panel_id": target_panel_id,
                "target_record_id": related_id,
                "action": action_type,
                "operation": operation,
                "field": target_field,
                "value_applied": str(source_value),
                "event": "executed",
                "status": "success",
                "executedBy": user_id,
                "timestamp": now,
            })

            # Increment execution count
            await db.automation_rules.update_one(
                {"_id": rule["_id"]},
                {"$inc": {"execution_count": 1}, "$set": {"last_executed": now}}
            )

        elif action_type == "create_record":
            # Create a new record in the target panel
            value_from = action.get("value_from", "")
            source_value = record_data.get(value_from, "")

            new_data = {
                relation_field: related_id,
            }
            if value_from and source_value:
                new_data[action.get("field", "value")] = source_value

            new_record = {
                "panelId": ObjectId(target_panel_id),
                "sellerId": ObjectId(seller_id),
                "data": new_data,
                "createdBy": user_id,
                "createdAt": now,
                "updatedAt": now,
                "_automated": True,
            }
            result = await db.panel_records.insert_one(new_record)

            await db.automation_logs.insert_one({
                "sellerId": ObjectId(seller_id),
                "ruleId": rule["_id"],
                "ruleName": rule.get("name", ""),
                "trigger_panel_id": panel_id,
                "record_id": record_id,
                "target_panel_id": target_panel_id,
                "target_record_id": str(result.inserted_id),
                "action": action_type,
                "event": "executed",
                "status": "success",
                "executedBy": user_id,
                "timestamp": now,
            })

            await db.automation_rules.update_one(
                {"_id": rule["_id"]},
                {"$inc": {"execution_count": 1}, "$set": {"last_executed": now}}
            )

    async def update_system_record(target_module: str, record_id: str, field: str, operation: str, value, seller_id: str):
        """Update a system module record with strict safety controls."""
        try:
            numeric_val = float(value)
        except (ValueError, TypeError):
            numeric_val = None

        if target_module == "inventory":
            # Only allow quantity/stock updates on sellerListings
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

    def build_update_operation(field: str, operation: str, source_value, current_data: dict):
        """Compute the new value for a field based on operation."""
        current = current_data.get(field, 0)
        return apply_operation(current, operation, source_value)

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

    # Expose execute_automation for panel_router to call
    router.execute_automation = execute_automation

    return router
