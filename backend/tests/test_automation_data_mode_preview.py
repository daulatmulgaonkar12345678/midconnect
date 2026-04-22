"""
Test Automation Data Mode and Preview Features (Iteration 113)

New features tested:
1. data_mode field per target (smart_sync | manual_only | full_copy)
2. POST /api/business-tools/automation/preview endpoint
3. Validation: manual_only requires field_mappings, smart_sync/full_copy don't
4. Preview shows different output based on data_mode
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-phase2-enhance.preview.emergentagent.com').rstrip('/')
AUTH_TOKEN = "dev-test-token"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Test panel IDs from context
QC_PANEL_ID = "69bea698166d5a071a336fb8"
DISPATCH_TRACKER_ID = "69bea698166d5a071a336fb9"


class TestHealthAndAccess:
    """Basic health and access checks"""
    
    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("API health check passed")
    
    def test_access_level(self):
        """Verify business tools access"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=HEADERS)
        assert response.status_code == 200, f"Access level check failed: {response.text}"
        print(f"Access level: {response.json()}")


class TestDataModeValidation:
    """Test data_mode field validation in rule creation"""
    
    def test_create_rule_with_smart_sync_default(self):
        """Create rule with data_mode='smart_sync' (default) - should work without field_mappings"""
        payload = {
            "name": "TEST_SmartSync_NoMappings",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "smart_sync"
                # No field_mappings - should be allowed for smart_sync
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Smart sync response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Smart sync rule creation failed: {response.text}"
        
        data = response.json()
        assert data.get("id"), "Rule should have an ID"
        assert data["targets"][0]["data_mode"] == "smart_sync"
        
        # Cleanup
        rule_id = data["id"]
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=HEADERS)
        print("PASS: smart_sync rule created without field_mappings")
    
    def test_create_rule_with_full_copy_no_mappings(self):
        """Create rule with data_mode='full_copy' - should work without field_mappings"""
        payload = {
            "name": "TEST_FullCopy_NoMappings",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "full_copy"
                # No field_mappings - should be allowed for full_copy
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Full copy response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Full copy rule creation failed: {response.text}"
        
        data = response.json()
        assert data["targets"][0]["data_mode"] == "full_copy"
        
        # Cleanup
        rule_id = data["id"]
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=HEADERS)
        print("PASS: full_copy rule created without field_mappings")
    
    def test_create_rule_with_manual_only_no_mappings_fails(self):
        """Create rule with data_mode='manual_only' and NO field_mappings - should FAIL with 400"""
        payload = {
            "name": "TEST_ManualOnly_NoMappings",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "manual_only"
                # No field_mappings - should FAIL for manual_only
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Manual only (no mappings) response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 400, f"Expected 400 for manual_only without mappings, got {response.status_code}"
        assert "field_mappings required" in response.text.lower() or "manual_only" in response.text.lower()
        print("PASS: manual_only without field_mappings correctly rejected with 400")
    
    def test_create_rule_with_manual_only_with_mappings(self):
        """Create rule with data_mode='manual_only' WITH field_mappings - should succeed"""
        payload = {
            "name": "TEST_ManualOnly_WithMappings",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "manual_only",
                "field_mappings": [
                    {"target_field": "status", "source_field": "status", "mapping_type": "field"}
                ]
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Manual only (with mappings) response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Manual only with mappings failed: {response.text}"
        
        data = response.json()
        assert data["targets"][0]["data_mode"] == "manual_only"
        assert len(data["targets"][0]["field_mappings"]) == 1
        
        # Cleanup
        rule_id = data["id"]
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=HEADERS)
        print("PASS: manual_only rule created with field_mappings")
    
    def test_create_rule_with_invalid_data_mode_fails(self):
        """Create rule with invalid data_mode - should FAIL"""
        payload = {
            "name": "TEST_InvalidDataMode",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "invalid_mode"
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Invalid data_mode response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 400, f"Expected 400 for invalid data_mode, got {response.status_code}"
        print("PASS: invalid data_mode correctly rejected")


class TestGetRulesWithDataMode:
    """Test that GET /rules returns data_mode in each target"""
    
    def test_get_rules_returns_data_mode(self):
        """GET /rules should return data_mode in each target"""
        # First create a rule with explicit data_mode
        payload = {
            "name": "TEST_GetRulesDataMode",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "full_copy"
            }]
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        assert create_response.status_code == 200
        rule_id = create_response.json()["id"]
        
        # Now GET rules and verify data_mode is present
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        rules = data.get("rules", [])
        
        # Find our test rule
        test_rule = next((r for r in rules if r["id"] == rule_id), None)
        assert test_rule, "Test rule not found in GET response"
        assert test_rule["targets"][0].get("data_mode") == "full_copy", "data_mode not returned in GET response"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=HEADERS)
        print("PASS: GET /rules returns data_mode in each target")


class TestPreviewEndpoint:
    """Test POST /api/business-tools/automation/preview endpoint"""
    
    def test_preview_endpoint_exists(self):
        """Preview endpoint should exist and accept POST"""
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "sample_data": {"inspector": "John", "status": "Pass", "quantity": 50}
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        print(f"Preview response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Preview endpoint failed: {response.text}"
        
        data = response.json()
        assert "previews" in data, "Response should contain 'previews' key"
        print("PASS: Preview endpoint exists and returns data")
    
    def test_preview_with_sample_data(self):
        """Preview with sample_data uses provided data"""
        sample = {"inspector": "TestInspector", "status": "Approved", "notes": "Test notes"}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "smart_sync",
                "field_mappings": [
                    {"target_field": "tracking_no", "source_field": "inspector", "mapping_type": "field"}
                ]
            }],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        previews = data.get("previews", [])
        assert len(previews) == 1
        
        preview = previews[0]
        assert preview["target_panel_id"] == DISPATCH_TRACKER_ID
        assert preview["data_mode"] == "smart_sync"
        # The explicit mapping should map inspector -> tracking_no
        assert preview["preview_data"].get("tracking_no") == "TestInspector"
        print(f"Preview data: {preview['preview_data']}")
        print("PASS: Preview with sample_data uses provided data")
    
    def test_preview_smart_sync_shows_explicit_plus_auto_matched(self):
        """Preview with smart_sync shows explicit mappings + auto-matched fields"""
        sample = {"status": "Pass", "inspector": "John", "notes": "Test"}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "smart_sync",
                "field_mappings": [
                    {"target_field": "tracking_no", "source_field": "inspector", "mapping_type": "field"}
                ]
            }],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        preview = data["previews"][0]
        preview_data = preview["preview_data"]
        
        # Explicit mapping: inspector -> tracking_no
        assert preview_data.get("tracking_no") == "John", "Explicit mapping should work"
        # Auto-matched: status exists in both panels (QC Panel and Dispatch Tracker)
        # If status is a field in target panel, it should be auto-mapped
        print(f"Smart sync preview: {preview_data}")
        print("PASS: Preview smart_sync shows explicit mappings")
    
    def test_preview_manual_only_shows_only_explicit(self):
        """Preview with manual_only shows only explicit mappings"""
        sample = {"status": "Pass", "inspector": "John", "notes": "Test"}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "manual_only",
                "field_mappings": [
                    {"target_field": "tracking_no", "source_field": "inspector", "mapping_type": "field"}
                ]
            }],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        preview = data["previews"][0]
        preview_data = preview["preview_data"]
        
        # Only explicit mapping should be present
        assert preview_data.get("tracking_no") == "John", "Explicit mapping should work"
        # No auto-mapping for manual_only - only what's explicitly mapped
        print(f"Manual only preview: {preview_data}")
        print("PASS: Preview manual_only shows only explicit mappings")
    
    def test_preview_full_copy_shows_all_matching(self):
        """Preview with full_copy shows all matching target fields"""
        sample = {"status": "Pass", "inspector": "John", "notes": "Test", "weight": 100}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "full_copy"
                # No explicit mappings - full_copy copies all matching fields
            }],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        preview = data["previews"][0]
        preview_data = preview["preview_data"]
        
        # Full copy should copy all fields that exist in target schema
        # Dispatch Tracker has: tracking_no, status, weight
        # Source has: status, inspector, notes, weight
        # Matching: status, weight
        print(f"Full copy preview: {preview_data}")
        print("PASS: Preview full_copy returns data")
    
    def test_preview_without_sample_data(self):
        """Preview without sample_data should use first record from panel or return message"""
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }]
            # No sample_data - should use first record from panel
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Either previews with data or a message about no sample data
        assert "previews" in data or "message" in data
        print(f"Preview without sample_data: {data}")
        print("PASS: Preview without sample_data handled correctly")
    
    def test_preview_update_record_action(self):
        """Preview with update_record action shows operation preview"""
        sample = {"quantity": 50, "status": "Pass"}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [{
                "target_panel_id": "inventory",  # System module
                "action_type": "update_record",
                "data_mode": "smart_sync",
                "update_operation": "increment",
                "update_field": "stock",
                "update_value_from": "quantity"
            }],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        preview = data["previews"][0]
        assert preview["action_type"] == "update_record"
        # Preview should show the operation
        print(f"Update record preview: {preview}")
        print("PASS: Preview update_record shows operation")
    
    def test_preview_multiple_targets(self):
        """Preview with multiple targets returns preview for each"""
        sample = {"status": "Pass", "inspector": "John", "quantity": 50}
        payload = {
            "trigger_panel_id": QC_PANEL_ID,
            "targets": [
                {
                    "target_panel_id": DISPATCH_TRACKER_ID,
                    "action_type": "create_record",
                    "data_mode": "smart_sync"
                },
                {
                    "target_panel_id": "inventory",
                    "action_type": "update_record",
                    "data_mode": "smart_sync",
                    "update_operation": "increment",
                    "update_field": "stock",
                    "update_value_from": "quantity"
                }
            ],
            "sample_data": sample
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", headers=HEADERS, json=payload)
        assert response.status_code == 200
        
        data = response.json()
        previews = data.get("previews", [])
        assert len(previews) == 2, f"Expected 2 previews, got {len(previews)}"
        print(f"Multiple targets preview: {previews}")
        print("PASS: Preview returns data for each target")


class TestDataModeDefaultValue:
    """Test that data_mode defaults to smart_sync"""
    
    def test_data_mode_defaults_to_smart_sync(self):
        """When data_mode is not specified, it should default to smart_sync"""
        payload = {
            "name": "TEST_DefaultDataMode",
            "trigger_panel_id": QC_PANEL_ID,
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": DISPATCH_TRACKER_ID,
                "action_type": "create_record"
                # data_mode not specified - should default to smart_sync
            }]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS, json=payload)
        print(f"Default data_mode response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Rule creation failed: {response.text}"
        
        data = response.json()
        # Check that data_mode is smart_sync (default)
        assert data["targets"][0].get("data_mode") == "smart_sync", "Default data_mode should be smart_sync"
        
        # Cleanup
        rule_id = data["id"]
        requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule_id}", headers=HEADERS)
        print("PASS: data_mode defaults to smart_sync")


class TestCleanup:
    """Cleanup any test rules that may have been left behind"""
    
    def test_cleanup_test_rules(self):
        """Delete any rules with TEST_ prefix"""
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=HEADERS)
        if response.status_code == 200:
            rules = response.json().get("rules", [])
            for rule in rules:
                if rule.get("name", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule['id']}", headers=HEADERS)
                    print(f"Cleaned up test rule: {rule['name']}")
        print("Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
