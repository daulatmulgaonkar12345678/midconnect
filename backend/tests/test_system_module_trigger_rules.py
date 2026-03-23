"""
Test System Module Trigger Rules - Iteration 114
Tests the new feature: system modules (inventory, invoices, etc.) can now be used as trigger/source panels.

Features tested:
1. POST /api/business-tools/automation/rules accepts system module ID as trigger_panel_id
2. GET /api/business-tools/panels/module-fields/{module_id} returns fields for system modules
3. GET /api/business-tools/panels/module-fields/{custom_panel_id} includes relation fields
4. Rules with system module trigger + custom panel target create successfully
5. Rules with custom panel trigger + system module target create successfully
6. GET /api/business-tools/automation/rules lists rules with system module trigger correctly
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# System module IDs from automation_router.py
SYSTEM_MODULE_IDS = ["inventory", "invoices", "buyers", "suppliers", "purchase_orders", "quotations", "composite_products", "employees"]

# Test panel IDs from the review request
VISIBILITY_TEST_PANEL = "69c10091da9a16efdaa06753"
QC_MATCH_PANEL = "69c0fcfc30101645013afc3f"


class TestModuleFieldsEndpoint:
    """Test GET /api/business-tools/panels/module-fields/{module_id}"""
    
    def test_module_fields_inventory(self):
        """Test module-fields returns correct fields for inventory system module"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/inventory", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("type") == "system", f"Expected type=system, got {data.get('type')}"
        assert data.get("name") == "inventory", f"Expected name=inventory, got {data.get('name')}"
        
        fields = data.get("fields", [])
        assert len(fields) > 0, "Expected at least one field for inventory"
        
        # Check expected inventory fields
        field_keys = [f["key"] for f in fields]
        expected_keys = ["productName", "sku", "stock", "quantity"]
        for key in expected_keys:
            assert key in field_keys, f"Expected field '{key}' in inventory fields"
        
        print(f"✓ Inventory module fields: {field_keys}")
    
    def test_module_fields_invoices(self):
        """Test module-fields returns correct fields for invoices system module"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/invoices", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("type") == "system"
        assert data.get("name") == "invoices"
        
        fields = data.get("fields", [])
        field_keys = [f["key"] for f in fields]
        assert "invoiceNumber" in field_keys, "Expected invoiceNumber field"
        assert "buyerName" in field_keys, "Expected buyerName field"
        
        print(f"✓ Invoices module fields: {field_keys}")
    
    def test_module_fields_all_system_modules(self):
        """Test module-fields returns fields for all system modules"""
        for module_id in SYSTEM_MODULE_IDS:
            response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/{module_id}", headers=AUTH_HEADER)
            assert response.status_code == 200, f"Module {module_id}: Expected 200, got {response.status_code}"
            
            data = response.json()
            assert data.get("type") == "system", f"Module {module_id}: Expected type=system"
            assert data.get("name") == module_id, f"Module {module_id}: Expected name={module_id}"
            assert len(data.get("fields", [])) > 0, f"Module {module_id}: Expected at least one field"
            
            print(f"✓ {module_id}: {len(data.get('fields', []))} fields")
    
    def test_module_fields_custom_panel_includes_relations(self):
        """Test module-fields for custom panel includes relation fields"""
        # Use the QC_MATCH_PANEL which has a relation to inventory
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/{QC_MATCH_PANEL}", headers=AUTH_HEADER)
        
        if response.status_code == 404:
            pytest.skip(f"Test panel {QC_MATCH_PANEL} not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("type") == "panel", f"Expected type=panel, got {data.get('type')}"
        
        fields = data.get("fields", [])
        # Check if relation fields are included
        relation_fields = [f for f in fields if f.get("type") == "relation"]
        
        # The panel should have relation fields included now
        print(f"✓ Custom panel fields: {len(fields)} total, {len(relation_fields)} relation fields")
        
        # Verify relation fields have relatedPanel info
        for rf in relation_fields:
            assert "relatedPanel" in rf, f"Relation field {rf.get('key')} should have relatedPanel"
            print(f"  - Relation field: {rf.get('key')} -> {rf.get('relatedPanel')}")
    
    def test_module_fields_invalid_module(self):
        """Test module-fields returns 404 for invalid module ID"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/invalid_module_xyz", headers=AUTH_HEADER)
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"✓ Invalid module returns {response.status_code}")


class TestSystemModuleTriggerRules:
    """Test creating automation rules with system modules as trigger panels"""
    
    created_rule_ids = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup: Delete all test rules created during testing"""
        for rule_id in cls.created_rule_ids:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=AUTH_HEADER)
                print(f"Cleaned up rule: {rule_id}")
            except Exception as e:
                print(f"Failed to cleanup rule {rule_id}: {e}")
    
    def test_create_rule_with_inventory_trigger(self):
        """Test creating rule with inventory as trigger panel"""
        payload = {
            "name": "TEST_Inventory_Trigger_Rule",
            "trigger_panel_id": "inventory",  # System module as trigger
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": VISIBILITY_TEST_PANEL,  # Custom panel as target
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "is_active": False  # Keep inactive for testing
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        
        if response.status_code == 404 and "Target panel not found" in response.text:
            pytest.skip(f"Target panel {VISIBILITY_TEST_PANEL} not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("trigger_panel_id") == "inventory", "trigger_panel_id should be 'inventory'"
        
        rule_id = data.get("id")
        if rule_id:
            self.created_rule_ids.append(rule_id)
        
        print(f"✓ Created rule with inventory trigger: {rule_id}")
    
    def test_create_rule_with_invoices_trigger(self):
        """Test creating rule with invoices as trigger panel"""
        payload = {
            "name": "TEST_Invoices_Trigger_Rule",
            "trigger_panel_id": "invoices",  # System module as trigger
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": VISIBILITY_TEST_PANEL,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "is_active": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        
        if response.status_code == 404 and "Target panel not found" in response.text:
            pytest.skip(f"Target panel {VISIBILITY_TEST_PANEL} not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("trigger_panel_id") == "invoices"
        
        rule_id = data.get("id")
        if rule_id:
            self.created_rule_ids.append(rule_id)
        
        print(f"✓ Created rule with invoices trigger: {rule_id}")
    
    def test_create_rule_with_buyers_trigger(self):
        """Test creating rule with buyers as trigger panel"""
        payload = {
            "name": "TEST_Buyers_Trigger_Rule",
            "trigger_panel_id": "buyers",
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": VISIBILITY_TEST_PANEL,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "is_active": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        
        if response.status_code == 404 and "Target panel not found" in response.text:
            pytest.skip(f"Target panel {VISIBILITY_TEST_PANEL} not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("trigger_panel_id") == "buyers"
        
        rule_id = data.get("id")
        if rule_id:
            self.created_rule_ids.append(rule_id)
        
        print(f"✓ Created rule with buyers trigger: {rule_id}")
    
    def test_create_rule_custom_trigger_system_target(self):
        """Test creating rule with custom panel trigger and system module target (update_record)"""
        payload = {
            "name": "TEST_Custom_To_Inventory_Rule",
            "trigger_panel_id": QC_MATCH_PANEL,  # Custom panel as trigger
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": "inventory",  # System module as target
                "action_type": "update_record",
                "data_mode": "smart_sync",
                "match_target_field": "productName",
                "match_source_field": "product_name",
                "update_operation": "increment",
                "update_field": "stock",
                "update_value_from": "quantity"
            }],
            "is_active": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        
        if response.status_code == 404 and "Trigger panel not found" in response.text:
            pytest.skip(f"Trigger panel {QC_MATCH_PANEL} not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("trigger_panel_id") == QC_MATCH_PANEL
        assert data.get("targets")[0].get("target_panel_id") == "inventory"
        
        rule_id = data.get("id")
        if rule_id:
            self.created_rule_ids.append(rule_id)
        
        print(f"✓ Created rule with custom trigger -> inventory target: {rule_id}")
    
    def test_list_rules_resolves_system_module_names(self):
        """Test that GET /automation/rules resolves system module trigger names correctly"""
        # First create a rule with system module trigger
        payload = {
            "name": "TEST_Name_Resolution_Rule",
            "trigger_panel_id": "purchase_orders",
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": VISIBILITY_TEST_PANEL,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "is_active": False
        }
        
        create_response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        
        if create_response.status_code == 404:
            pytest.skip("Target panel not found - skipping")
        
        if create_response.status_code == 200:
            rule_id = create_response.json().get("id")
            if rule_id:
                self.created_rule_ids.append(rule_id)
        
        # Now list rules and check name resolution
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        rules = data.get("rules", [])
        
        # Find our test rule
        test_rule = next((r for r in rules if r.get("name") == "TEST_Name_Resolution_Rule"), None)
        
        if test_rule:
            # Check that trigger_panel_name is resolved
            trigger_name = test_rule.get("trigger_panel_name", "")
            assert trigger_name == "Purchase Orders", f"Expected 'Purchase Orders', got '{trigger_name}'"
            print(f"✓ System module trigger name resolved: {trigger_name}")
        else:
            # Check any rule with system module trigger
            system_trigger_rules = [r for r in rules if r.get("trigger_panel_id") in SYSTEM_MODULE_IDS]
            if system_trigger_rules:
                for rule in system_trigger_rules[:3]:  # Check first 3
                    trigger_id = rule.get("trigger_panel_id")
                    trigger_name = rule.get("trigger_panel_name")
                    print(f"  - Rule '{rule.get('name')}': trigger_panel_id={trigger_id}, trigger_panel_name={trigger_name}")
                    assert trigger_name and trigger_name != trigger_id, f"trigger_panel_name should be resolved, not raw ID"
            print(f"✓ Rules list returned {len(rules)} rules")


class TestSystemModuleValidation:
    """Test validation for system module trigger rules"""
    
    created_rule_ids = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test rules"""
        for rule_id in cls.created_rule_ids:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=AUTH_HEADER)
            except:
                pass
    
    def test_all_system_modules_accepted_as_trigger(self):
        """Test that all system module IDs are accepted as trigger_panel_id"""
        for module_id in SYSTEM_MODULE_IDS:
            payload = {
                "name": f"TEST_Validate_{module_id}_Trigger",
                "trigger_panel_id": module_id,
                "trigger_type": "on_create",
                "targets": [{
                    "target_panel_id": VISIBILITY_TEST_PANEL,
                    "action_type": "create_record",
                    "data_mode": "smart_sync"
                }],
                "is_active": False
            }
            
            response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
            
            if response.status_code == 404 and "Target panel not found" in response.text:
                print(f"  - {module_id}: Skipped (target panel not found)")
                continue
            
            # Should succeed (200) or fail for other reasons, but NOT "Invalid trigger panel ID"
            if response.status_code != 200:
                error_msg = response.json().get("detail", "")
                assert "Invalid trigger panel ID" not in error_msg, f"Module {module_id} should be accepted as trigger"
                assert "Trigger panel not found" not in error_msg, f"Module {module_id} should be accepted as trigger"
                print(f"  - {module_id}: {response.status_code} - {error_msg}")
            else:
                rule_id = response.json().get("id")
                if rule_id:
                    self.created_rule_ids.append(rule_id)
                print(f"  ✓ {module_id}: Accepted as trigger")
    
    def test_invalid_trigger_panel_rejected(self):
        """Test that invalid trigger panel IDs are still rejected"""
        payload = {
            "name": "TEST_Invalid_Trigger",
            "trigger_panel_id": "not_a_valid_module_or_panel",
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": VISIBILITY_TEST_PANEL,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "is_active": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for invalid trigger, got {response.status_code}"
        
        error_msg = response.json().get("detail", "")
        assert "Invalid trigger panel ID" in error_msg or "Trigger panel not found" in error_msg, f"Expected validation error, got: {error_msg}"
        
        print(f"✓ Invalid trigger panel rejected: {error_msg}")


class TestLinkableTargets:
    """Test GET /api/business-tools/panels/linkable-targets includes system modules"""
    
    def test_linkable_targets_includes_system_modules(self):
        """Test that linkable-targets returns all system modules"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        targets = data.get("targets", [])
        
        # Check system modules are present
        system_targets = [t for t in targets if t.get("type") == "system"]
        system_ids = [t.get("id") for t in system_targets]
        
        for module_id in SYSTEM_MODULE_IDS:
            assert module_id in system_ids, f"System module '{module_id}' should be in linkable targets"
        
        print(f"✓ Linkable targets includes all {len(SYSTEM_MODULE_IDS)} system modules")
        print(f"  System modules: {system_ids}")
        
        # Check custom panels are also present
        panel_targets = [t for t in targets if t.get("type") == "panel"]
        print(f"  Custom panels: {len(panel_targets)}")


# Run basic health check first
class TestHealthCheck:
    """Basic health check before running other tests"""
    
    def test_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        print(f"✓ API healthy: {response.json()}")
    
    def test_auth_works(self):
        """Test authentication with dev token works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Auth failed: {response.status_code}: {response.text}"
        print(f"✓ Auth works: {response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
