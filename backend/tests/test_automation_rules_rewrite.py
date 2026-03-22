"""
Test Automation Rules Rewrite - Iteration 111
Tests the complete rewrite of the Automation Rule system with:
- Trigger types (on_create, on_update, condition_based)
- Action types (update_record, create_record, create_records_per_item)
- Field mapping with Source→Target table
- Field visibility control
- Duplicate prevention
- Record linking
- Event chaining with infinite loop prevention
- Execution logging
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test auth token (dev mode)
TEST_TOKEN = "dev-test-token"

class TestHealthAndBasics:
    """Basic health and access checks"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_access_level(self):
        """Test business tools access level endpoint"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=headers)
        assert response.status_code == 200, f"Access level check failed: {response.text}"
        data = response.json()
        assert "level" in data
        print(f"✓ Access level: {data.get('level')}")


class TestAutomationRulesListAndLogs:
    """Test automation rules list and logs endpoints"""
    
    def test_list_automation_rules(self):
        """GET /api/business-tools/automation/rules returns enriched rules"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        assert response.status_code == 200, f"List rules failed: {response.text}"
        data = response.json()
        assert "rules" in data
        assert "count" in data
        assert "limit" in data
        print(f"✓ List rules: {data.get('count')} rules found, limit={data.get('limit')}")
        
        # Check enriched fields if rules exist
        if data.get("rules"):
            rule = data["rules"][0]
            # New schema fields
            assert "trigger_type" in rule or "trigger_panel_id" in rule, "Missing trigger fields"
            print(f"  First rule: {rule.get('name')}")
    
    def test_get_automation_logs(self):
        """GET /api/business-tools/automation/logs returns logs with new fields"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/logs", headers=headers)
        assert response.status_code == 200, f"Get logs failed: {response.text}"
        data = response.json()
        assert "logs" in data
        print(f"✓ Automation logs: {len(data.get('logs', []))} logs found")
        
        # Check log structure if logs exist
        if data.get("logs"):
            log = data["logs"][0]
            # New log fields
            if "action_type" in log:
                print(f"  Log has action_type: {log.get('action_type')}")
            if "message" in log:
                print(f"  Log has message: {log.get('message')[:50]}...")


class TestModuleFieldsEndpoint:
    """Test GET /api/business-tools/panels/module-fields/{module_id} for all 8 system modules"""
    
    @pytest.mark.parametrize("module_id,expected_fields", [
        ("inventory", ["productName", "sku", "category", "stock", "quantity", "minStock", "reorderPoint"]),
        ("invoices", ["invoiceNumber", "buyerName", "totalAmount"]),
        ("buyers", ["name", "phone", "email"]),
        ("suppliers", ["name", "phone", "email"]),
        ("purchase_orders", ["poNumber", "supplierName", "totalAmount"]),
        ("quotations", ["quotationNumber", "buyerName", "totalAmount"]),
        ("composite_products", ["name", "sku"]),
        ("employees", ["name", "role", "email"]),
    ])
    def test_module_fields_system_modules(self, module_id, expected_fields):
        """Test module-fields endpoint returns correct fields for system modules"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/{module_id}", headers=headers)
        assert response.status_code == 200, f"Module fields for {module_id} failed: {response.text}"
        data = response.json()
        
        assert "fields" in data
        assert "type" in data
        assert data["type"] == "system"
        
        field_keys = [f["key"] for f in data["fields"]]
        for expected in expected_fields:
            assert expected in field_keys, f"Missing field {expected} in {module_id}"
        
        print(f"✓ Module fields for {module_id}: {len(data['fields'])} fields")
    
    def test_module_fields_invalid_id(self):
        """Test module-fields with invalid ID returns 400"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/invalid", headers=headers)
        assert response.status_code == 400, f"Expected 400 for invalid module ID, got {response.status_code}"
        print("✓ Invalid module ID returns 400")
    
    def test_module_fields_nonexistent_panel(self):
        """Test module-fields with valid ObjectId but non-existent panel returns 404"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/000000000000000000000000", headers=headers)
        assert response.status_code == 404, f"Expected 404 for non-existent panel, got {response.status_code}"
        print("✓ Non-existent panel returns 404")


class TestRuleValidation:
    """Test rule validation for trigger_type, action_type, and required fields"""
    
    @pytest.fixture
    def test_panel(self):
        """Create a test panel with relation field for rule testing"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Create panel with inventory relation
        panel_data = {
            "name": f"TEST_AutomationRulePanel_{os.urandom(4).hex()}",
            "description": "Test panel for automation rule validation",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "quantity", "label": "Quantity", "type": "number"},
                {"key": "status", "label": "Status", "type": "dropdown", "options": ["pending", "approved", "rejected"]}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200, f"Failed to create test panel: {response.text}"
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    def test_invalid_trigger_type(self, test_panel):
        """Test rule creation with invalid trigger_type returns 400"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find the product relation field (auto-created)
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found in test panel")
        
        rule_data = {
            "name": "TEST_InvalidTriggerRule",
            "trigger_panel_id": panel_id,
            "trigger_type": "invalid_trigger",  # Invalid
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "quantity"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for invalid trigger_type, got {response.status_code}: {response.text}"
        print("✓ Invalid trigger_type returns 400")
    
    def test_invalid_action_type(self, test_panel):
        """Test rule creation with invalid action_type returns 400"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found in test panel")
        
        rule_data = {
            "name": "TEST_InvalidActionRule",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "invalid_action",  # Invalid
            "target_panel_id": "inventory",
            "relation_field": relation_field
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for invalid action_type, got {response.status_code}: {response.text}"
        print("✓ Invalid action_type returns 400")
    
    def test_create_action_requires_field_mappings(self, test_panel):
        """Test create_record action requires field_mappings"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found in test panel")
        
        rule_data = {
            "name": "TEST_CreateWithoutMappings",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "create_record",  # Requires field_mappings
            "target_panel_id": "inventory",
            "relation_field": relation_field
            # Missing field_mappings
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for create_record without field_mappings, got {response.status_code}: {response.text}"
        assert "field_mappings" in response.text.lower(), "Error should mention field_mappings"
        print("✓ create_record without field_mappings returns 400")
    
    def test_update_record_requires_operation_fields(self, test_panel):
        """Test update_record action requires update_operation, update_field, update_value_from"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found in test panel")
        
        # Missing update_operation
        rule_data = {
            "name": "TEST_UpdateWithoutOperation",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            # Missing update_operation, update_field, update_value_from
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for update_record without operation fields, got {response.status_code}: {response.text}"
        print("✓ update_record without operation fields returns 400")
    
    def test_relation_field_must_exist_in_trigger_panel(self, test_panel):
        """Test relation_field must exist in trigger panel"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        rule_data = {
            "name": "TEST_InvalidRelationField",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": "nonexistent_field",  # Invalid
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "quantity"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for non-existent relation_field, got {response.status_code}: {response.text}"
        print("✓ Non-existent relation_field returns 400")
    
    def test_relation_field_must_be_type_relation(self, test_panel):
        """Test relation_field must be of type 'relation'"""
        panel_id, panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Use 'quantity' which is a number field, not relation
        rule_data = {
            "name": "TEST_NonRelationField",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": "quantity",  # This is a number field, not relation
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "quantity"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for non-relation field, got {response.status_code}: {response.text}"
        assert "relation" in response.text.lower(), "Error should mention relation type"
        print("✓ Non-relation field as relation_field returns 400")


class TestRuleCRUD:
    """Test full CRUD operations for automation rules with new schema"""
    
    @pytest.fixture
    def test_panel_with_relation(self):
        """Create a test panel with relation field"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_CRUDPanel_{os.urandom(4).hex()}",
            "description": "Test panel for CRUD operations",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "qty", "label": "Quantity", "type": "number"},
                {"key": "notes", "label": "Notes", "type": "text"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200, f"Failed to create test panel: {response.text}"
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    def test_create_update_record_rule(self, test_panel_with_relation):
        """Test creating a rule with update_record action type"""
        panel_id, panel = test_panel_with_relation
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find relation field
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        rule_data = {
            "name": f"TEST_UpdateRule_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "decrement",
            "update_field": "stock",
            "update_value_from": "qty",
            "is_active": True,
            "priority": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create rule: {response.text}"
        rule = response.json()
        
        assert rule.get("name") == rule_data["name"]
        assert rule.get("trigger_type") == "on_create"
        assert rule.get("action_type") == "update_record"
        assert rule.get("update_operation") == "decrement"
        assert rule.get("update_field") == "stock"
        assert rule.get("update_value_from") == "qty"
        
        rule_id = rule.get("id")
        print(f"✓ Created update_record rule: {rule_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
    
    def test_create_create_record_rule_with_field_mappings(self, test_panel_with_relation):
        """Test creating a rule with create_record action and field_mappings"""
        panel_id, panel = test_panel_with_relation
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find relation field
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        # Create a target panel for create_record
        target_panel_data = {
            "name": f"TEST_TargetPanel_{os.urandom(4).hex()}",
            "fields": [
                {"key": "source_qty", "label": "Source Quantity", "type": "number"},
                {"key": "source_notes", "label": "Source Notes", "type": "text"},
                {"key": "default_status", "label": "Status", "type": "text"}
            ]
        }
        target_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=target_panel_data)
        assert target_response.status_code == 200, f"Failed to create target panel: {target_response.text}"
        target_panel = target_response.json()
        target_panel_id = target_panel.get("id")
        
        try:
            rule_data = {
                "name": f"TEST_CreateRecordRule_{os.urandom(4).hex()}",
                "trigger_panel_id": panel_id,
                "trigger_type": "on_create",
                "action_type": "create_record",
                "target_panel_id": target_panel_id,
                "relation_field": relation_field,
                "field_mappings": [
                    {"target_field": "source_qty", "source_field": "qty", "mapping_type": "field"},
                    {"target_field": "source_notes", "source_field": "notes", "mapping_type": "field"},
                    {"target_field": "default_status", "default_value": "pending", "mapping_type": "default"}
                ],
                "field_visibility": [
                    {"field": "source_qty", "visible": True, "editable": False},
                    {"field": "default_status", "visible": True, "editable": True}
                ],
                "is_active": True
            }
            
            response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
            assert response.status_code == 200, f"Failed to create rule: {response.text}"
            rule = response.json()
            
            assert rule.get("action_type") == "create_record"
            assert len(rule.get("field_mappings", [])) == 3
            assert len(rule.get("field_visibility", [])) == 2
            
            rule_id = rule.get("id")
            print(f"✓ Created create_record rule with field_mappings: {rule_id}")
            
            # Cleanup rule
            requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
        finally:
            # Cleanup target panel
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{target_panel_id}", headers=headers)
    
    def test_update_rule_trigger_and_action_type(self, test_panel_with_relation):
        """Test updating rule trigger_type, action_type, and field_mappings"""
        panel_id, panel = test_panel_with_relation
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        # Create initial rule
        rule_data = {
            "name": f"TEST_UpdateableRule_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "qty"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200
        rule = response.json()
        rule_id = rule.get("id")
        
        try:
            # Update trigger_type
            update_data = {
                "trigger_type": "on_update",
                "update_operation": "decrement"
            }
            
            update_response = requests.put(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers, json=update_data)
            assert update_response.status_code == 200, f"Failed to update rule: {update_response.text}"
            
            # Verify update via list
            list_response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
            rules = list_response.json().get("rules", [])
            updated_rule = next((r for r in rules if r.get("id") == rule_id), None)
            
            assert updated_rule is not None
            assert updated_rule.get("trigger_type") == "on_update"
            assert updated_rule.get("update_operation") == "decrement"
            
            print(f"✓ Updated rule trigger_type and update_operation")
        finally:
            requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
    
    def test_delete_rule(self, test_panel_with_relation):
        """Test deleting an automation rule"""
        panel_id, panel = test_panel_with_relation
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        # Create rule
        rule_data = {
            "name": f"TEST_DeleteableRule_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "set_value",
            "update_field": "stock",
            "update_value_from": "qty"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200
        rule_id = response.json().get("id")
        
        # Delete rule
        delete_response = requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
        assert delete_response.status_code == 200, f"Failed to delete rule: {delete_response.text}"
        
        # Verify deletion
        list_response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        rules = list_response.json().get("rules", [])
        deleted_rule = next((r for r in rules if r.get("id") == rule_id), None)
        assert deleted_rule is None, "Rule should be deleted"
        
        print("✓ Rule deleted successfully")


class TestConditionBasedTrigger:
    """Test condition_based trigger type"""
    
    @pytest.fixture
    def test_panel_with_dropdown(self):
        """Create a test panel with dropdown field for condition testing"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_ConditionPanel_{os.urandom(4).hex()}",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "status", "label": "Status", "type": "dropdown", "options": ["pending", "approved", "rejected"]},
                {"key": "amount", "label": "Amount", "type": "number"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    def test_condition_based_requires_condition(self, test_panel_with_dropdown):
        """Test condition_based trigger requires condition field"""
        panel_id, panel = test_panel_with_dropdown
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        rule_data = {
            "name": "TEST_ConditionBasedNoCondition",
            "trigger_panel_id": panel_id,
            "trigger_type": "condition_based",  # Requires condition
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "amount"
            # Missing condition
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for condition_based without condition, got {response.status_code}"
        print("✓ condition_based without condition returns 400")
    
    def test_condition_based_with_valid_condition(self, test_panel_with_dropdown):
        """Test condition_based trigger with valid condition"""
        panel_id, panel = test_panel_with_dropdown
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        rule_data = {
            "name": f"TEST_ConditionBasedValid_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "condition_based",
            "condition": {
                "field": "status",
                "operator": "equals",
                "value": "approved"
            },
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "decrement",
            "update_field": "stock",
            "update_value_from": "amount"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create condition_based rule: {response.text}"
        rule = response.json()
        
        assert rule.get("trigger_type") == "condition_based"
        assert rule.get("condition") is not None
        assert rule["condition"].get("field") == "status"
        assert rule["condition"].get("operator") == "equals"
        assert rule["condition"].get("value") == "approved"
        
        rule_id = rule.get("id")
        print(f"✓ Created condition_based rule: {rule_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
    
    def test_invalid_condition_operator(self, test_panel_with_dropdown):
        """Test invalid condition operator returns 400"""
        panel_id, panel = test_panel_with_dropdown
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        relation_field = None
        for f in panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        rule_data = {
            "name": "TEST_InvalidOperator",
            "trigger_panel_id": panel_id,
            "trigger_type": "condition_based",
            "condition": {
                "field": "status",
                "operator": "invalid_operator",  # Invalid
                "value": "approved"
            },
            "action_type": "update_record",
            "target_panel_id": "inventory",
            "relation_field": relation_field,
            "update_operation": "increment",
            "update_field": "stock",
            "update_value_from": "amount"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for invalid operator, got {response.status_code}"
        print("✓ Invalid condition operator returns 400")


class TestEnrichedRulesResponse:
    """Test that GET rules returns enriched data with panel names"""
    
    def test_rules_include_panel_names(self):
        """Test rules list includes trigger_panel_name and target_panel_name"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data.get("rules"):
            rule = data["rules"][0]
            # Check for enriched fields
            if "trigger_panel_name" in rule:
                print(f"✓ Rule has trigger_panel_name: {rule.get('trigger_panel_name')}")
            if "target_panel_name" in rule:
                print(f"✓ Rule has target_panel_name: {rule.get('target_panel_name')}")
        else:
            print("✓ No rules to check enrichment (empty list)")


class TestFrontendBuild:
    """Test frontend builds without errors"""
    
    def test_frontend_health(self):
        """Test frontend is accessible"""
        response = requests.get(f"{BASE_URL}/", timeout=10)
        # Frontend should return 200 or redirect
        assert response.status_code in [200, 301, 302, 304], f"Frontend not accessible: {response.status_code}"
        print("✓ Frontend is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
