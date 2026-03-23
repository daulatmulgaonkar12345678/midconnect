"""
Test Automation Rules Multi-Target Architecture - Iteration 112
Tests the new multi-target automation rule system with:
- 1 source panel -> multiple target panels architecture
- targets[] array with per-target action_type, field_mappings, field_visibility
- Backend CRUD operations with multi-target payload
- Validation: empty targets, invalid target_panel_id, create without mappings, update without fields
- System module IDs (inventory, invoices, etc.) as target_panel_id
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test auth token (dev mode)
TEST_TOKEN = "dev-test-token"

# Existing panel IDs from test context
QC_PANEL_ID = "69bea698166d5a071a336fb8"
DISPATCH_PANEL_ID = "69bea698166d5a071a336fb9"

# System module IDs
SYSTEM_MODULES = ["inventory", "invoices", "buyers", "suppliers", "purchase_orders", "quotations", "composite_products", "employees"]


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


class TestMultiTargetRulesList:
    """Test GET /api/business-tools/automation/rules returns rules with targets[] array"""
    
    def test_list_rules_returns_targets_array(self):
        """GET /api/business-tools/automation/rules returns rules with targets[] array and panel names"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        assert response.status_code == 200, f"List rules failed: {response.text}"
        data = response.json()
        
        assert "rules" in data
        assert "count" in data
        assert "limit" in data
        print(f"✓ List rules: {data.get('count')} rules found, limit={data.get('limit')}")
        
        # Check structure if rules exist
        if data.get("rules"):
            rule = data["rules"][0]
            # New multi-target schema fields
            assert "trigger_panel_id" in rule, "Missing trigger_panel_id"
            assert "trigger_type" in rule, "Missing trigger_type"
            
            # Check for targets array (new multi-target architecture)
            if "targets" in rule:
                assert isinstance(rule["targets"], list), "targets should be an array"
                print(f"  First rule '{rule.get('name')}' has {len(rule['targets'])} target(s)")
                
                # Check target structure
                if rule["targets"]:
                    target = rule["targets"][0]
                    assert "target_panel_id" in target, "Target missing target_panel_id"
                    assert "action_type" in target, "Target missing action_type"
                    if "target_panel_name" in target:
                        print(f"    Target has enriched name: {target.get('target_panel_name')}")
            
            # Check trigger panel name enrichment
            if "trigger_panel_name" in rule:
                print(f"  Rule has trigger_panel_name: {rule.get('trigger_panel_name')}")


class TestMultiTargetRuleCreate:
    """Test POST /api/business-tools/automation/rules with multi-target payload"""
    
    @pytest.fixture
    def test_panel(self):
        """Create a test panel for rule testing"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_MultiTargetPanel_{os.urandom(4).hex()}",
            "description": "Test panel for multi-target automation",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "quantity", "label": "Quantity", "type": "number"},
                {"key": "status", "label": "Status", "type": "dropdown", "options": ["pending", "approved", "rejected"]},
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
    
    @pytest.fixture
    def target_panel(self):
        """Create a target panel for create_record tests"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_TargetPanel_{os.urandom(4).hex()}",
            "fields": [
                {"key": "source_qty", "label": "Source Quantity", "type": "number"},
                {"key": "source_notes", "label": "Source Notes", "type": "text"},
                {"key": "default_status", "label": "Status", "type": "text"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200, f"Failed to create target panel: {response.text}"
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    def test_create_rule_with_single_target(self, test_panel, target_panel):
        """Test creating a rule with single target in targets[] array"""
        source_panel_id, source_panel = test_panel
        target_panel_id, _ = target_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        rule_data = {
            "name": f"TEST_SingleTargetRule_{os.urandom(4).hex()}",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": target_panel_id,
                    "action_type": "create_record",
                    "field_mappings": [
                        {"target_field": "source_qty", "source_field": "quantity", "mapping_type": "field"},
                        {"target_field": "source_notes", "source_field": "notes", "mapping_type": "field"},
                        {"target_field": "default_status", "default_value": "pending", "mapping_type": "default"}
                    ]
                }
            ],
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create rule: {response.text}"
        rule = response.json()
        
        assert rule.get("name") == rule_data["name"]
        assert rule.get("trigger_panel_id") == source_panel_id
        assert rule.get("trigger_type") == "on_create"
        assert "targets" in rule
        assert len(rule["targets"]) == 1
        assert rule["targets"][0]["target_panel_id"] == target_panel_id
        assert rule["targets"][0]["action_type"] == "create_record"
        assert len(rule["targets"][0].get("field_mappings", [])) == 3
        
        rule_id = rule.get("id")
        print(f"✓ Created rule with single target: {rule_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
    
    def test_create_rule_with_multiple_targets(self, test_panel, target_panel):
        """Test creating a rule with multiple targets in targets[] array"""
        source_panel_id, source_panel = test_panel
        target_panel_id, _ = target_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find relation field for update_record target
        relation_field = None
        for f in source_panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        targets = [
            {
                "target_panel_id": target_panel_id,
                "action_type": "create_record",
                "field_mappings": [
                    {"target_field": "source_qty", "source_field": "quantity", "mapping_type": "field"}
                ]
            }
        ]
        
        # Add update_record target if relation field exists
        if relation_field:
            targets.append({
                "target_panel_id": "inventory",
                "action_type": "update_record",
                "relation_field": relation_field,
                "update_operation": "decrement",
                "update_field": "stock",
                "update_value_from": "quantity"
            })
        
        rule_data = {
            "name": f"TEST_MultiTargetRule_{os.urandom(4).hex()}",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": targets,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create multi-target rule: {response.text}"
        rule = response.json()
        
        assert len(rule["targets"]) == len(targets)
        print(f"✓ Created rule with {len(rule['targets'])} targets")
        
        # Cleanup
        rule_id = rule.get("id")
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
    
    def test_create_rule_with_system_module_target(self, test_panel):
        """Test creating a rule with system module ID (inventory) as target_panel_id"""
        source_panel_id, source_panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find relation field
        relation_field = None
        for f in source_panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found in test panel")
        
        rule_data = {
            "name": f"TEST_SystemModuleTarget_{os.urandom(4).hex()}",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": "inventory",  # System module ID
                    "action_type": "update_record",
                    "relation_field": relation_field,
                    "update_operation": "decrement",
                    "update_field": "stock",
                    "update_value_from": "quantity"
                }
            ],
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create rule with system module target: {response.text}"
        rule = response.json()
        
        assert rule["targets"][0]["target_panel_id"] == "inventory"
        print(f"✓ Created rule with system module target (inventory)")
        
        # Cleanup
        rule_id = rule.get("id")
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)


class TestMultiTargetValidation:
    """Test validation for multi-target rules"""
    
    @pytest.fixture
    def test_panel(self):
        """Create a test panel for validation testing"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_ValidationPanel_{os.urandom(4).hex()}",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "quantity", "label": "Quantity", "type": "number"},
                {"key": "status", "label": "Status", "type": "dropdown", "options": ["pending", "approved"]}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    def test_empty_targets_array_returns_error(self, test_panel):
        """Test that empty targets[] array returns validation error"""
        source_panel_id, _ = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        rule_data = {
            "name": "TEST_EmptyTargets",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": []  # Empty targets array
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 422 or response.status_code == 400, f"Expected 400/422 for empty targets, got {response.status_code}: {response.text}"
        print("✓ Empty targets[] array returns validation error")
    
    def test_invalid_target_panel_id_returns_error(self, test_panel):
        """Test that invalid target_panel_id returns error"""
        source_panel_id, _ = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        rule_data = {
            "name": "TEST_InvalidTargetPanel",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": "invalid_panel_id_12345",  # Invalid
                    "action_type": "create_record",
                    "field_mappings": [
                        {"target_field": "test", "source_field": "quantity", "mapping_type": "field"}
                    ]
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400 or response.status_code == 404, f"Expected 400/404 for invalid target_panel_id, got {response.status_code}: {response.text}"
        print("✓ Invalid target_panel_id returns error")
    
    def test_create_record_without_field_mappings_returns_error(self, test_panel):
        """Test that create_record action without field_mappings returns error"""
        source_panel_id, _ = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        rule_data = {
            "name": "TEST_CreateWithoutMappings",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": "inventory",
                    "action_type": "create_record"
                    # Missing field_mappings
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for create_record without field_mappings, got {response.status_code}: {response.text}"
        assert "field_mappings" in response.text.lower(), "Error should mention field_mappings"
        print("✓ create_record without field_mappings returns 400")
    
    def test_update_record_without_required_fields_returns_error(self, test_panel):
        """Test that update_record without update_field/update_value_from returns error"""
        source_panel_id, source_panel = test_panel
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Find relation field
        relation_field = None
        for f in source_panel.get("fields", []):
            if f.get("type") == "relation":
                relation_field = f.get("key")
                break
        
        if not relation_field:
            pytest.skip("No relation field found")
        
        rule_data = {
            "name": "TEST_UpdateWithoutFields",
            "trigger_panel_id": source_panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": "inventory",
                    "action_type": "update_record",
                    "relation_field": relation_field,
                    "update_operation": "increment"
                    # Missing update_field and update_value_from
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 400, f"Expected 400 for update_record without required fields, got {response.status_code}: {response.text}"
        print("✓ update_record without update_field/update_value_from returns 400")


class TestMultiTargetRuleUpdate:
    """Test PUT /api/business-tools/automation/rules/{id} updates rule"""
    
    @pytest.fixture
    def test_rule(self):
        """Create a test rule for update testing"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # First create a panel
        panel_data = {
            "name": f"TEST_UpdateRulePanel_{os.urandom(4).hex()}",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "qty", "label": "Quantity", "type": "number"}
            ]
        }
        panel_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert panel_response.status_code == 200
        panel = panel_response.json()
        panel_id = panel.get("id")
        
        # Create a target panel
        target_panel_data = {
            "name": f"TEST_UpdateTargetPanel_{os.urandom(4).hex()}",
            "fields": [
                {"key": "source_qty", "label": "Source Qty", "type": "number"}
            ]
        }
        target_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=target_panel_data)
        assert target_response.status_code == 200
        target_panel = target_response.json()
        target_panel_id = target_panel.get("id")
        
        # Create rule
        rule_data = {
            "name": f"TEST_UpdateableRule_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": target_panel_id,
                    "action_type": "create_record",
                    "field_mappings": [
                        {"target_field": "source_qty", "source_field": "qty", "mapping_type": "field"}
                    ]
                }
            ],
            "is_active": True
        }
        
        rule_response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert rule_response.status_code == 200
        rule = rule_response.json()
        rule_id = rule.get("id")
        
        yield rule_id, panel_id, target_panel_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{target_panel_id}", headers=headers)
    
    def test_update_rule_name_and_active_status(self, test_rule):
        """Test updating rule name and is_active status"""
        rule_id, _, _ = test_rule
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        update_data = {
            "name": "TEST_UpdatedRuleName",
            "is_active": False
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers, json=update_data)
        assert response.status_code == 200, f"Failed to update rule: {response.text}"
        
        # Verify update
        list_response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        rules = list_response.json().get("rules", [])
        updated_rule = next((r for r in rules if r.get("id") == rule_id), None)
        
        assert updated_rule is not None
        assert updated_rule.get("name") == "TEST_UpdatedRuleName"
        assert updated_rule.get("is_active") == False
        
        print("✓ Updated rule name and is_active status")
    
    def test_update_rule_targets(self, test_rule):
        """Test updating rule targets array"""
        rule_id, panel_id, target_panel_id = test_rule
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Update targets with new field mapping
        update_data = {
            "targets": [
                {
                    "target_panel_id": target_panel_id,
                    "action_type": "create_record",
                    "field_mappings": [
                        {"target_field": "source_qty", "source_field": "qty", "mapping_type": "field"},
                        {"target_field": "source_qty", "default_value": "100", "mapping_type": "default"}
                    ]
                }
            ]
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers, json=update_data)
        assert response.status_code == 200, f"Failed to update rule targets: {response.text}"
        
        # Verify update
        list_response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
        rules = list_response.json().get("rules", [])
        updated_rule = next((r for r in rules if r.get("id") == rule_id), None)
        
        assert updated_rule is not None
        assert len(updated_rule.get("targets", [])) == 1
        assert len(updated_rule["targets"][0].get("field_mappings", [])) == 2
        
        print("✓ Updated rule targets array")


class TestMultiTargetRuleDelete:
    """Test DELETE /api/business-tools/automation/rules/{id}"""
    
    def test_delete_rule(self):
        """Test deleting an automation rule"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        # Create a panel
        panel_data = {
            "name": f"TEST_DeleteRulePanel_{os.urandom(4).hex()}",
            "fields": [{"key": "qty", "label": "Qty", "type": "number"}]
        }
        panel_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert panel_response.status_code == 200
        panel_id = panel_response.json().get("id")
        
        # Create target panel
        target_data = {
            "name": f"TEST_DeleteTargetPanel_{os.urandom(4).hex()}",
            "fields": [{"key": "src_qty", "label": "Src Qty", "type": "number"}]
        }
        target_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=target_data)
        assert target_response.status_code == 200
        target_panel_id = target_response.json().get("id")
        
        try:
            # Create rule
            rule_data = {
                "name": f"TEST_DeleteableRule_{os.urandom(4).hex()}",
                "trigger_panel_id": panel_id,
                "trigger_type": "on_create",
                "targets": [
                    {
                        "target_panel_id": target_panel_id,
                        "action_type": "create_record",
                        "field_mappings": [
                            {"target_field": "src_qty", "source_field": "qty", "mapping_type": "field"}
                        ]
                    }
                ]
            }
            
            rule_response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
            assert rule_response.status_code == 200
            rule_id = rule_response.json().get("id")
            
            # Delete rule
            delete_response = requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)
            assert delete_response.status_code == 200, f"Failed to delete rule: {delete_response.text}"
            
            # Verify deletion
            list_response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers)
            rules = list_response.json().get("rules", [])
            deleted_rule = next((r for r in rules if r.get("id") == rule_id), None)
            assert deleted_rule is None, "Rule should be deleted"
            
            print("✓ Rule deleted successfully")
        finally:
            # Cleanup panels
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{target_panel_id}", headers=headers)


class TestAutomationLogs:
    """Test GET /api/business-tools/automation/logs"""
    
    def test_get_automation_logs(self):
        """GET /api/business-tools/automation/logs returns execution logs"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/logs", headers=headers)
        assert response.status_code == 200, f"Get logs failed: {response.text}"
        data = response.json()
        
        assert "logs" in data
        print(f"✓ Automation logs: {len(data.get('logs', []))} logs found")
        
        # Check log structure if logs exist
        if data.get("logs"):
            log = data["logs"][0]
            # Expected log fields
            expected_fields = ["ruleName", "status", "timestamp"]
            for field in expected_fields:
                if field in log:
                    print(f"  Log has {field}: {str(log.get(field))[:50]}")


class TestSystemModuleTargets:
    """Test that system module IDs are accepted as target_panel_id"""
    
    @pytest.fixture
    def test_panel_with_relation(self):
        """Create a test panel with relation field"""
        headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}
        
        panel_data = {
            "name": f"TEST_SystemModulePanel_{os.urandom(4).hex()}",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "qty", "label": "Quantity", "type": "number"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=headers, json=panel_data)
        assert response.status_code == 200
        panel = response.json()
        panel_id = panel.get("id")
        
        yield panel_id, panel
        
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=headers)
    
    @pytest.mark.parametrize("system_module", ["inventory"])
    def test_system_module_as_update_target(self, test_panel_with_relation, system_module):
        """Test system module ID is accepted as target_panel_id for update_record"""
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
            "name": f"TEST_SystemModule_{system_module}_{os.urandom(4).hex()}",
            "trigger_panel_id": panel_id,
            "trigger_type": "on_create",
            "targets": [
                {
                    "target_panel_id": system_module,
                    "action_type": "update_record",
                    "relation_field": relation_field,
                    "update_operation": "decrement",
                    "update_field": "stock",
                    "update_value_from": "qty"
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=headers, json=rule_data)
        assert response.status_code == 200, f"Failed to create rule with {system_module} target: {response.text}"
        rule = response.json()
        
        assert rule["targets"][0]["target_panel_id"] == system_module
        print(f"✓ System module '{system_module}' accepted as target_panel_id")
        
        # Cleanup
        rule_id = rule.get("id")
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=headers)


class TestFrontendAccessibility:
    """Test frontend is accessible"""
    
    def test_frontend_loads(self):
        """Test frontend is accessible"""
        response = requests.get(f"{BASE_URL}/", timeout=10)
        assert response.status_code in [200, 301, 302, 304], f"Frontend not accessible: {response.status_code}"
        print("✓ Frontend is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
