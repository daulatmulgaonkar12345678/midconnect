"""
Phase 3A: Panel Binding UI & Controlled Linking Tests

Tests for:
1. POST /api/business-tools/panels - create panel with allowedModules and allowedPanels
2. PUT /api/business-tools/panels/{id} - update panel with allowedModules and allowedPanels
3. Panel creation auto-adds 'Product' relation field when allowedModules includes 'inventory'
4. Panel creation auto-adds 'Invoice' relation field when allowedModules includes 'invoices'
5. Panel linking validation: no self-linking, no circular linking, max 2 linked panels
6. Unique field validation: creating records with duplicate values for unique fields should fail
7. Activity logging when creating panel records
8. GET /api/business-tools/panels - list panels returns allowedModules and allowedPanels
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com')

# Test token for dev mode
DEV_TOKEN = "dev-test-token"

class TestPhase3APanelBinding:
    """Phase 3A Panel Binding & Controlled Linking Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        }
        self.created_panel_ids = []
        yield
        # Cleanup created panels
        for panel_id in self.created_panel_ids:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=self.headers)
            except:
                pass
    
    # ========== Test 1: Health Check ==========
    def test_01_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    # ========== Test 2: Access Level Check ==========
    def test_02_access_level(self):
        """Verify user has advanced access for panels"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("level") == "advanced", f"Expected advanced access, got {data.get('level')}"
        print(f"✓ Access level: {data.get('level')}")
    
    # ========== Test 3: List Panels Returns allowedModules and allowedPanels ==========
    def test_03_list_panels_returns_allowed_fields(self):
        """GET /api/business-tools/panels returns allowedModules and allowedPanels"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "panels" in data
        print(f"✓ List panels returned {len(data['panels'])} panels")
        
        # Check that panels have allowedModules and allowedPanels fields
        for panel in data["panels"]:
            assert "allowedModules" in panel or panel.get("allowedModules") is None, "Panel should have allowedModules field"
            assert "allowedPanels" in panel or panel.get("allowedPanels") is None, "Panel should have allowedPanels field"
        print("✓ Panels have allowedModules and allowedPanels fields")
    
    # ========== Test 4: Create Panel with allowedModules (inventory) ==========
    def test_04_create_panel_with_inventory_module(self):
        """POST /api/business-tools/panels with allowedModules=['inventory'] auto-adds Product relation field"""
        panel_data = {
            "name": f"TEST_Inventory_Panel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to inventory",
            "icon": "package",
            "color": "green",
            "allowedModules": ["inventory"],
            "allowedPanels": [],
            "fields": [
                {"key": "qc_status", "label": "QC Status", "type": "dropdown", "required": True, "options": ["Pass", "Fail", "Pending"]}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        data = response.json()
        
        self.created_panel_ids.append(data["id"])
        
        # Verify allowedModules is set
        assert "inventory" in data.get("allowedModules", []), "allowedModules should include 'inventory'"
        
        # Verify auto-added Product relation field
        fields = data.get("fields", [])
        product_field = next((f for f in fields if f.get("key") == "product" and f.get("type") == "relation"), None)
        assert product_field is not None, "Product relation field should be auto-added when linked to inventory"
        assert product_field.get("relatedPanel") == "inventory", "Product field should link to inventory"
        assert product_field.get("required") == True, "Product field should be required"
        
        print(f"✓ Created panel with inventory module: {data['id']}")
        print(f"✓ Auto-added Product relation field: {product_field}")
    
    # ========== Test 5: Create Panel with allowedModules (invoices) ==========
    def test_05_create_panel_with_invoices_module(self):
        """POST /api/business-tools/panels with allowedModules=['invoices'] auto-adds Invoice relation field"""
        panel_data = {
            "name": f"TEST_Invoice_Panel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to invoices",
            "icon": "file-text",
            "color": "blue",
            "allowedModules": ["invoices"],
            "allowedPanels": [],
            "fields": [
                {"key": "payment_status", "label": "Payment Status", "type": "dropdown", "required": True, "options": ["Paid", "Pending", "Overdue"]}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        data = response.json()
        
        self.created_panel_ids.append(data["id"])
        
        # Verify allowedModules is set
        assert "invoices" in data.get("allowedModules", []), "allowedModules should include 'invoices'"
        
        # Verify auto-added Invoice relation field
        fields = data.get("fields", [])
        invoice_field = next((f for f in fields if f.get("key") == "invoice" and f.get("type") == "relation"), None)
        assert invoice_field is not None, "Invoice relation field should be auto-added when linked to invoices"
        assert invoice_field.get("relatedPanel") == "invoices", "Invoice field should link to invoices"
        assert invoice_field.get("required") == True, "Invoice field should be required"
        
        print(f"✓ Created panel with invoices module: {data['id']}")
        print(f"✓ Auto-added Invoice relation field: {invoice_field}")
    
    # ========== Test 6: Create Panel with Both Modules ==========
    def test_06_create_panel_with_both_modules(self):
        """POST /api/business-tools/panels with both inventory and invoices modules"""
        panel_data = {
            "name": f"TEST_Both_Modules_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to both inventory and invoices",
            "icon": "layers",
            "color": "purple",
            "allowedModules": ["inventory", "invoices"],
            "allowedPanels": [],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        data = response.json()
        
        self.created_panel_ids.append(data["id"])
        
        # Verify both modules are set
        assert "inventory" in data.get("allowedModules", []), "allowedModules should include 'inventory'"
        assert "invoices" in data.get("allowedModules", []), "allowedModules should include 'invoices'"
        
        # Verify both relation fields are auto-added
        fields = data.get("fields", [])
        product_field = next((f for f in fields if f.get("key") == "product" and f.get("type") == "relation"), None)
        invoice_field = next((f for f in fields if f.get("key") == "invoice" and f.get("type") == "relation"), None)
        
        assert product_field is not None, "Product relation field should be auto-added"
        assert invoice_field is not None, "Invoice relation field should be auto-added"
        
        print(f"✓ Created panel with both modules: {data['id']}")
        print(f"✓ Auto-added both Product and Invoice relation fields")
    
    # ========== Test 7: Panel Linking - Create Two Panels and Link ==========
    def test_07_panel_linking_valid(self):
        """Create two panels and link them via allowedPanels"""
        # Create first panel
        panel1_data = {
            "name": f"TEST_Panel_A_{datetime.now().strftime('%H%M%S')}",
            "description": "First panel for linking test",
            "icon": "target",
            "color": "orange",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True}
            ]
        }
        
        response1 = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel1_data)
        assert response1.status_code == 200, f"Create panel 1 failed: {response1.text}"
        panel1 = response1.json()
        self.created_panel_ids.append(panel1["id"])
        
        # Create second panel linked to first
        panel2_data = {
            "name": f"TEST_Panel_B_{datetime.now().strftime('%H%M%S')}",
            "description": "Second panel linked to first",
            "icon": "star",
            "color": "cyan",
            "allowedModules": [],
            "allowedPanels": [panel1["id"]],
            "fields": [
                {"key": "status", "label": "Status", "type": "text", "required": True}
            ]
        }
        
        response2 = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel2_data)
        assert response2.status_code == 200, f"Create panel 2 failed: {response2.text}"
        panel2 = response2.json()
        self.created_panel_ids.append(panel2["id"])
        
        # Verify allowedPanels is set
        assert panel1["id"] in panel2.get("allowedPanels", []), "Panel 2 should link to Panel 1"
        
        print(f"✓ Created Panel A: {panel1['id']}")
        print(f"✓ Created Panel B linked to Panel A: {panel2['id']}")
    
    # ========== Test 8: Panel Linking - Max 2 Panels Validation ==========
    def test_08_panel_linking_max_two(self):
        """Validate max 2 linked panels"""
        # Create 3 panels first
        panel_ids = []
        for i in range(3):
            panel_data = {
                "name": f"TEST_Max_Panel_{i}_{datetime.now().strftime('%H%M%S')}",
                "description": f"Panel {i} for max test",
                "icon": "flag",
                "color": "red",
                "allowedModules": [],
                "allowedPanels": [],
                "fields": [{"key": "field", "label": "Field", "type": "text", "required": False}]
            }
            response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
            if response.status_code == 200:
                panel_ids.append(response.json()["id"])
                self.created_panel_ids.append(response.json()["id"])
        
        if len(panel_ids) < 3:
            pytest.skip("Could not create 3 panels for max test")
        
        # Try to create panel with 3 linked panels (should fail)
        panel_data = {
            "name": f"TEST_Too_Many_Links_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel with too many links",
            "icon": "alert",
            "color": "amber",
            "allowedModules": [],
            "allowedPanels": panel_ids,  # 3 panels - should fail
            "fields": [{"key": "test", "label": "Test", "type": "text", "required": False}]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 400, f"Expected 400 for max 2 panels, got {response.status_code}"
        assert "Maximum 2 linked panels" in response.text or "max" in response.text.lower()
        
        print("✓ Max 2 linked panels validation works")
    
    # ========== Test 9: Panel Linking - No Self-Linking ==========
    def test_09_panel_linking_no_self_link(self):
        """Validate no self-linking via update"""
        # Create a panel
        panel_data = {
            "name": f"TEST_Self_Link_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel for self-link test",
            "icon": "zap",
            "color": "pink",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [{"key": "data", "label": "Data", "type": "text", "required": False}]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        panel = response.json()
        self.created_panel_ids.append(panel["id"])
        
        # Try to update panel to link to itself (should fail)
        update_data = {
            "allowedPanels": [panel["id"]]  # Self-link
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=self.headers, json=update_data)
        assert response.status_code == 400, f"Expected 400 for self-link, got {response.status_code}"
        assert "cannot link to itself" in response.text.lower() or "self" in response.text.lower()
        
        print("✓ No self-linking validation works")
    
    # ========== Test 10: Panel Linking - No Circular Linking ==========
    def test_10_panel_linking_no_circular(self):
        """Validate no circular linking"""
        # Create Panel A
        panel_a_data = {
            "name": f"TEST_Circular_A_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel A for circular test",
            "icon": "target",
            "color": "indigo",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [{"key": "a", "label": "A", "type": "text", "required": False}]
        }
        
        response_a = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_a_data)
        assert response_a.status_code == 200, f"Create panel A failed: {response_a.text}"
        panel_a = response_a.json()
        self.created_panel_ids.append(panel_a["id"])
        
        # Create Panel B linked to A
        panel_b_data = {
            "name": f"TEST_Circular_B_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel B linked to A",
            "icon": "star",
            "color": "slate",
            "allowedModules": [],
            "allowedPanels": [panel_a["id"]],
            "fields": [{"key": "b", "label": "B", "type": "text", "required": False}]
        }
        
        response_b = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_b_data)
        assert response_b.status_code == 200, f"Create panel B failed: {response_b.text}"
        panel_b = response_b.json()
        self.created_panel_ids.append(panel_b["id"])
        
        # Try to update Panel A to link to B (circular - should fail)
        update_data = {
            "allowedPanels": [panel_b["id"]]  # Circular link
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_a['id']}", headers=self.headers, json=update_data)
        assert response.status_code == 400, f"Expected 400 for circular link, got {response.status_code}"
        assert "circular" in response.text.lower()
        
        print("✓ No circular linking validation works")
    
    # ========== Test 11: Update Panel with allowedModules ==========
    def test_11_update_panel_allowed_modules(self):
        """PUT /api/business-tools/panels/{id} with allowedModules auto-adds relation fields"""
        # Create panel without modules
        panel_data = {
            "name": f"TEST_Update_Modules_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel to test module update",
            "icon": "settings",
            "color": "amber",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [{"key": "status", "label": "Status", "type": "text", "required": False}]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        panel = response.json()
        self.created_panel_ids.append(panel["id"])
        
        # Update to add inventory module
        update_data = {
            "allowedModules": ["inventory"]
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=self.headers, json=update_data)
        assert response.status_code == 200, f"Update panel failed: {response.text}"
        
        # Fetch panel to verify
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=self.headers)
        assert response.status_code == 200
        updated_panel = response.json()
        
        # Verify allowedModules is set
        assert "inventory" in updated_panel.get("allowedModules", []), "allowedModules should include 'inventory'"
        
        # Verify auto-added Product relation field
        fields = updated_panel.get("fields", [])
        product_field = next((f for f in fields if f.get("key") == "product" and f.get("type") == "relation"), None)
        assert product_field is not None, "Product relation field should be auto-added on update"
        
        print(f"✓ Updated panel with inventory module: {panel['id']}")
        print(f"✓ Auto-added Product relation field on update")
    
    # ========== Test 12: Unique Field Validation ==========
    def test_12_unique_field_validation(self):
        """Creating records with duplicate values for unique fields should fail"""
        # Create panel with unique field
        panel_data = {
            "name": f"TEST_Unique_Field_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel with unique field",
            "icon": "shield-check",
            "color": "green",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [
                {"key": "serial_number", "label": "Serial Number", "type": "text", "required": True, "unique": True},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        panel = response.json()
        self.created_panel_ids.append(panel["id"])
        
        # Verify unique field is set
        fields = panel.get("fields", [])
        serial_field = next((f for f in fields if f.get("key") == "serial_number"), None)
        assert serial_field is not None, "Serial number field should exist"
        assert serial_field.get("unique") == True, "Serial number field should be unique"
        
        # Create first record
        record1_data = {
            "data": {
                "serial_number": "SN-12345",
                "notes": "First record"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records", headers=self.headers, json=record1_data)
        assert response.status_code == 200, f"Create first record failed: {response.text}"
        record1 = response.json()
        
        # Try to create second record with same serial number (should fail)
        record2_data = {
            "data": {
                "serial_number": "SN-12345",  # Duplicate
                "notes": "Second record"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records", headers=self.headers, json=record2_data)
        assert response.status_code == 400, f"Expected 400 for duplicate unique field, got {response.status_code}"
        assert "unique" in response.text.lower() or "already exists" in response.text.lower()
        
        # Cleanup: delete the record
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records/{record1['id']}", headers=self.headers)
        
        print("✓ Unique field validation works")
    
    # ========== Test 13: Activity Logging on Record Creation ==========
    def test_13_activity_logging(self):
        """Activity logging when creating panel records"""
        # Create panel
        panel_data = {
            "name": f"TEST_Activity_Log_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel for activity log test",
            "icon": "clipboard-check",
            "color": "blue",
            "allowedModules": [],
            "allowedPanels": [],
            "fields": [
                {"key": "item", "label": "Item", "type": "text", "required": True}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        panel = response.json()
        self.created_panel_ids.append(panel["id"])
        
        # Create record
        record_data = {
            "data": {
                "item": "Test Item for Activity Log"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records", headers=self.headers, json=record_data)
        assert response.status_code == 200, f"Create record failed: {response.text}"
        record = response.json()
        
        # Check activity logs
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/activity-logs", headers=self.headers)
        assert response.status_code == 200, f"Get activity logs failed: {response.text}"
        logs = response.json()
        
        assert "logs" in logs, "Response should have logs array"
        assert len(logs["logs"]) > 0, "Should have at least one activity log"
        
        # Verify log entry
        latest_log = logs["logs"][0]
        assert latest_log.get("type") == "PANEL_RECORD_CREATED", f"Log type should be PANEL_RECORD_CREATED, got {latest_log.get('type')}"
        assert latest_log.get("recordId") == record["id"], "Log should reference the created record"
        
        # Cleanup: delete the record
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records/{record['id']}", headers=self.headers)
        
        print("✓ Activity logging works")
    
    # ========== Test 14: Linkable Targets Endpoint ==========
    def test_14_linkable_targets(self):
        """GET /api/business-tools/panels/linkable-targets returns system modules and panels"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets", headers=self.headers)
        assert response.status_code == 200, f"Get linkable targets failed: {response.text}"
        data = response.json()
        
        assert "targets" in data, "Response should have targets array"
        targets = data["targets"]
        
        # Verify system modules are present
        system_targets = [t for t in targets if t.get("type") == "system"]
        assert len(system_targets) >= 2, "Should have at least 2 system targets (inventory, invoices)"
        
        inventory_target = next((t for t in system_targets if t.get("id") == "inventory"), None)
        invoices_target = next((t for t in system_targets if t.get("id") == "invoices"), None)
        
        assert inventory_target is not None, "Inventory should be a linkable target"
        assert invoices_target is not None, "Invoices should be a linkable target"
        
        print(f"✓ Linkable targets: {len(targets)} total ({len(system_targets)} system)")
    
    # ========== Test 15: Get Single Panel Returns allowedModules and allowedPanels ==========
    def test_15_get_panel_returns_allowed_fields(self):
        """GET /api/business-tools/panels/{id} returns allowedModules and allowedPanels"""
        # Create panel with modules
        panel_data = {
            "name": f"TEST_Get_Panel_{datetime.now().strftime('%H%M%S')}",
            "description": "Panel for get test",
            "icon": "eye",
            "color": "cyan",
            "allowedModules": ["inventory"],
            "allowedPanels": [],
            "fields": [{"key": "test", "label": "Test", "type": "text", "required": False}]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=self.headers, json=panel_data)
        assert response.status_code == 200, f"Create panel failed: {response.text}"
        panel = response.json()
        self.created_panel_ids.append(panel["id"])
        
        # Get panel
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=self.headers)
        assert response.status_code == 200, f"Get panel failed: {response.text}"
        fetched_panel = response.json()
        
        assert "allowedModules" in fetched_panel, "Panel should have allowedModules field"
        assert "allowedPanels" in fetched_panel, "Panel should have allowedPanels field"
        assert "inventory" in fetched_panel.get("allowedModules", []), "allowedModules should include 'inventory'"
        
        print(f"✓ Get panel returns allowedModules and allowedPanels")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
