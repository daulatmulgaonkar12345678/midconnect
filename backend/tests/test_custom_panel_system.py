"""
Test Custom Panel System (Phase 1) - Advanced Business Tools
Tests panel CRUD, field management, access control, and validation limits.
Uses dev-test-token for authentication (Firebase bypass in dev mode).
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-perms-modal.preview.emergentagent.com')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Test data tracking for cleanup
created_panel_ids = []


class TestAccessLevel:
    """Test access level endpoint"""
    
    def test_get_access_level_returns_advanced_for_dev_user(self):
        """GET /api/business-tools/access-level returns access level and limits"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "level" in data, "Response should contain 'level'"
        assert "limits" in data, "Response should contain 'limits'"
        assert data["level"] == "advanced", f"Expected 'advanced' for dev-test user, got {data['level']}"
        assert data["limits"]["maxPanels"] == 10, "Max panels should be 10"
        assert data["limits"]["maxFieldsPerPanel"] == 20, "Max fields per panel should be 20"
        print(f"✓ Access level: {data['level']}, limits: {data['limits']}")
    
    def test_access_level_requires_auth(self):
        """Access level endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("✓ Access level requires authentication")


class TestPanelCRUD:
    """Test panel create, read, update, delete operations"""
    
    def test_create_panel_with_all_field_types(self):
        """POST /api/business-tools/panels creates a panel with all field types"""
        panel_data = {
            "name": f"TEST_QC_Panel_{int(time.time())}",
            "description": "Quality Control tracking panel",
            "icon": "clipboard-check",
            "color": "green",
            "fields": [
                {"key": "text_field", "label": "Product Name", "type": "text", "required": True},
                {"key": "number_field", "label": "Quantity", "type": "number", "required": False},
                {"key": "date_field", "label": "Inspection Date", "type": "date", "required": True},
                {"key": "dropdown_field", "label": "QC Status", "type": "dropdown", "required": True, "options": ["Pass", "Fail", "Pending"]},
                {"key": "multiselect_field", "label": "Issues Found", "type": "multiselect", "required": False, "options": ["Scratch", "Dent", "Color Mismatch", "Size Issue"]},
                {"key": "boolean_field", "label": "Approved", "type": "boolean", "required": False},
                {"key": "longtext_field", "label": "Notes", "type": "longtext", "required": False},
                {"key": "relation_field", "label": "Related Inventory", "type": "relation", "required": False, "relatedPanel": "inventory", "relationType": "many_to_one"}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain panel 'id'"
        assert data["name"] == panel_data["name"], "Panel name should match"
        assert data["description"] == panel_data["description"], "Description should match"
        assert data["icon"] == panel_data["icon"], "Icon should match"
        assert data["color"] == panel_data["color"], "Color should match"
        assert len(data["fields"]) == 8, f"Expected 8 fields, got {len(data['fields'])}"
        
        # Verify all field types are present
        field_types = {f["type"] for f in data["fields"]}
        expected_types = {"text", "number", "date", "dropdown", "multiselect", "boolean", "longtext", "relation"}
        assert field_types == expected_types, f"Missing field types: {expected_types - field_types}"
        
        created_panel_ids.append(data["id"])
        print(f"✓ Created panel with ID: {data['id']}, all 8 field types present")
        return data["id"]
    
    def test_list_panels(self):
        """GET /api/business-tools/panels returns list of panels"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "panels" in data, "Response should contain 'panels'"
        assert "count" in data, "Response should contain 'count'"
        assert "limit" in data, "Response should contain 'limit'"
        assert isinstance(data["panels"], list), "Panels should be a list"
        print(f"✓ Listed {data['count']} panels (limit: {data['limit']})")
    
    def test_get_single_panel(self):
        """GET /api/business-tools/panels/{id} returns panel with all field details"""
        # First create a panel
        panel_data = {
            "name": f"TEST_Single_Panel_{int(time.time())}",
            "description": "Test single panel retrieval",
            "fields": [
                {"key": "test_field", "label": "Test Field", "type": "text", "required": True}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Get the panel
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == panel_id, "Panel ID should match"
        assert data["name"] == panel_data["name"], "Panel name should match"
        assert "fields" in data, "Response should contain 'fields'"
        assert len(data["fields"]) == 1, "Should have 1 field"
        assert data["fields"][0]["key"] == "test_field", "Field key should match"
        print(f"✓ Retrieved panel {panel_id} with all details")
    
    def test_update_panel_metadata(self):
        """PUT /api/business-tools/panels/{id} updates panel name/description/color"""
        # Create a panel
        panel_data = {
            "name": f"TEST_Update_Panel_{int(time.time())}",
            "description": "Original description",
            "color": "blue"
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Update the panel
        update_data = {
            "name": f"TEST_Updated_Panel_{int(time.time())}",
            "description": "Updated description",
            "color": "purple"
        }
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["name"] == update_data["name"], "Name should be updated"
        assert data["description"] == update_data["description"], "Description should be updated"
        assert data["color"] == update_data["color"], "Color should be updated"
        print(f"✓ Updated panel {panel_id} metadata successfully")
    
    def test_delete_panel(self):
        """DELETE /api/business-tools/panels/{id} deletes a panel"""
        # Create a panel
        panel_data = {"name": f"TEST_Delete_Panel_{int(time.time())}"}
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        
        # Delete the panel
        response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        assert get_response.status_code == 404, "Panel should not exist after deletion"
        print(f"✓ Deleted panel {panel_id} successfully")


class TestFieldManagement:
    """Test field add, delete, and reorder operations"""
    
    def test_add_field_to_existing_panel(self):
        """POST /api/business-tools/panels/{id}/fields adds a new field"""
        # Create a panel
        panel_data = {"name": f"TEST_AddField_Panel_{int(time.time())}"}
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Add a field
        field_data = {
            "key": "new_field",
            "label": "New Field",
            "type": "text",
            "required": True
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields", headers=AUTH_HEADER, json=field_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify field was added
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        data = get_response.json()
        assert len(data["fields"]) == 1, "Should have 1 field"
        assert data["fields"][0]["key"] == "new_field", "Field key should match"
        print(f"✓ Added field to panel {panel_id}")
    
    def test_delete_field_from_panel(self):
        """DELETE /api/business-tools/panels/{id}/fields/{key} removes a field"""
        # Create a panel with a field
        panel_data = {
            "name": f"TEST_DeleteField_Panel_{int(time.time())}",
            "fields": [
                {"key": "field_to_delete", "label": "Delete Me", "type": "text"},
                {"key": "field_to_keep", "label": "Keep Me", "type": "text"}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Delete a field
        response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields/field_to_delete", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify field was deleted
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        data = get_response.json()
        assert len(data["fields"]) == 1, "Should have 1 field remaining"
        assert data["fields"][0]["key"] == "field_to_keep", "Remaining field should be 'field_to_keep'"
        print(f"✓ Deleted field from panel {panel_id}")
    
    def test_reorder_fields(self):
        """PUT /api/business-tools/panels/{id}/fields-order reorders fields"""
        # Create a panel with multiple fields
        panel_data = {
            "name": f"TEST_Reorder_Panel_{int(time.time())}",
            "fields": [
                {"key": "field_a", "label": "Field A", "type": "text"},
                {"key": "field_b", "label": "Field B", "type": "text"},
                {"key": "field_c", "label": "Field C", "type": "text"}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Reorder fields (reverse order)
        reorder_data = {"fieldKeys": ["field_c", "field_b", "field_a"]}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields-order", headers=AUTH_HEADER, json=reorder_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify order
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        data = get_response.json()
        field_keys = [f["key"] for f in data["fields"]]
        assert field_keys == ["field_c", "field_b", "field_a"], f"Fields should be reordered, got {field_keys}"
        print(f"✓ Reordered fields in panel {panel_id}")


class TestLinkableTargets:
    """Test linkable targets endpoint for relation fields"""
    
    def test_get_linkable_targets(self):
        """GET /api/business-tools/panels/linkable-targets returns system modules and custom panels"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "targets" in data, "Response should contain 'targets'"
        assert isinstance(data["targets"], list), "Targets should be a list"
        
        # Check for system modules
        target_ids = {t["id"] for t in data["targets"]}
        assert "inventory" in target_ids, "Should include 'inventory' system module"
        assert "invoices" in target_ids, "Should include 'invoices' system module"
        
        # Check target structure
        for target in data["targets"]:
            assert "id" in target, "Target should have 'id'"
            assert "name" in target, "Target should have 'name'"
            assert "type" in target, "Target should have 'type'"
            assert target["type"] in ["system", "panel"], f"Type should be 'system' or 'panel', got {target['type']}"
        
        print(f"✓ Got {len(data['targets'])} linkable targets")


class TestValidation:
    """Test validation rules and limits"""
    
    def test_duplicate_panel_name_rejected(self):
        """Duplicate panel name is rejected (400)"""
        unique_name = f"TEST_Duplicate_Panel_{int(time.time())}"
        
        # Create first panel
        panel_data = {"name": unique_name}
        create_response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_response.status_code == 200, f"First create failed: {create_response.text}"
        panel_id = create_response.json()["id"]
        created_panel_ids.append(panel_id)
        
        # Try to create duplicate
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for duplicate name, got {response.status_code}: {response.text}"
        assert "already exists" in response.json().get("detail", "").lower(), "Error should mention duplicate"
        print("✓ Duplicate panel name correctly rejected")
    
    def test_dropdown_requires_options(self):
        """Dropdown field requires options"""
        panel_data = {
            "name": f"TEST_NoOptions_Panel_{int(time.time())}",
            "fields": [
                {"key": "bad_dropdown", "label": "Bad Dropdown", "type": "dropdown"}  # No options
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for dropdown without options, got {response.status_code}: {response.text}"
        assert "options" in response.json().get("detail", "").lower(), "Error should mention options"
        print("✓ Dropdown without options correctly rejected")
    
    def test_multiselect_requires_options(self):
        """Multiselect field requires options"""
        panel_data = {
            "name": f"TEST_NoOptions_Multi_{int(time.time())}",
            "fields": [
                {"key": "bad_multi", "label": "Bad Multi", "type": "multiselect"}  # No options
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for multiselect without options, got {response.status_code}: {response.text}"
        assert "options" in response.json().get("detail", "").lower(), "Error should mention options"
        print("✓ Multiselect without options correctly rejected")
    
    def test_relation_requires_related_panel(self):
        """Relation field requires relatedPanel"""
        panel_data = {
            "name": f"TEST_NoRelated_Panel_{int(time.time())}",
            "fields": [
                {"key": "bad_relation", "label": "Bad Relation", "type": "relation"}  # No relatedPanel
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for relation without relatedPanel, got {response.status_code}: {response.text}"
        assert "relatedpanel" in response.json().get("detail", "").lower(), "Error should mention relatedPanel"
        print("✓ Relation without relatedPanel correctly rejected")
    
    def test_max_fields_per_panel_limit(self):
        """Max 20 fields per panel limit enforced"""
        # Create 21 fields (exceeds limit)
        fields = [{"key": f"field_{i}", "label": f"Field {i}", "type": "text"} for i in range(21)]
        panel_data = {
            "name": f"TEST_TooManyFields_{int(time.time())}",
            "fields": fields
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for too many fields, got {response.status_code}: {response.text}"
        assert "20" in response.json().get("detail", ""), "Error should mention 20 field limit"
        print("✓ Max 20 fields limit correctly enforced")


class TestMyPermissions:
    """Test my-permissions endpoint includes businessToolAccess"""
    
    def test_my_permissions_includes_business_tool_access(self):
        """GET /api/business-tools/my-permissions includes businessToolAccess field"""
        response = requests.get(f"{BASE_URL}/api/business-tools/my-permissions", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "businessToolAccess" in data, "Response should contain 'businessToolAccess'"
        assert data["businessToolAccess"] in ["none", "standard", "advanced"], f"Invalid access level: {data['businessToolAccess']}"
        print(f"✓ my-permissions includes businessToolAccess: {data['businessToolAccess']}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_panels(self):
        """Clean up all TEST_ prefixed panels"""
        # List all panels
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
        if response.status_code == 200:
            panels = response.json().get("panels", [])
            for panel in panels:
                if panel.get("name", "").startswith("TEST_"):
                    delete_response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)
                    if delete_response.status_code == 200:
                        print(f"  Cleaned up panel: {panel['name']}")
        
        # Also clean up tracked panels
        for panel_id in created_panel_ids:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
            except:
                pass
        
        print("✓ Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
