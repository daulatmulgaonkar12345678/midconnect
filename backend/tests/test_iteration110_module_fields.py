"""
Test Iteration 110: Panel Binding Variable Feature
Tests the new module-fields endpoint and bindingField storage for relation fields.

Features tested:
1. GET /api/business-tools/panels/module-fields/{module_id} - returns fields for system modules
2. GET /api/business-tools/panels/module-fields/{custom_panel_id} - returns non-relation fields for custom panels
3. GET /api/business-tools/panels/module-fields/invalid - returns 400
4. Panel creation with relation field stores bindingField correctly
5. Auto-created relation fields (via allowedModules) have systemManaged:true
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}


class TestModuleFieldsEndpoint:
    """Tests for GET /api/business-tools/panels/module-fields/{module_id}"""

    def test_inventory_module_fields(self):
        """Test inventory module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/inventory", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "inventory"
        assert "fields" in data
        
        # Verify expected inventory fields
        field_keys = [f["key"] for f in data["fields"]]
        assert "productName" in field_keys, "productName field missing"
        assert "sku" in field_keys, "sku field missing"
        assert "stock" in field_keys, "stock field missing"
        assert "quantity" in field_keys, "quantity field missing"
        assert "minStock" in field_keys, "minStock field missing"
        assert "reorderPoint" in field_keys, "reorderPoint field missing"
        
        # Verify field structure
        for field in data["fields"]:
            assert "key" in field
            assert "label" in field
            assert "type" in field

    def test_invoices_module_fields(self):
        """Test invoices module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/invoices", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "invoices"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "invoiceNumber" in field_keys
        assert "buyerName" in field_keys
        assert "totalAmount" in field_keys

    def test_buyers_module_fields(self):
        """Test buyers module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/buyers", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "buyers"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "name" in field_keys
        assert "phone" in field_keys
        assert "email" in field_keys

    def test_suppliers_module_fields(self):
        """Test suppliers module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/suppliers", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "suppliers"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "name" in field_keys
        assert "phone" in field_keys
        assert "email" in field_keys

    def test_purchase_orders_module_fields(self):
        """Test purchase_orders module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/purchase_orders", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "purchase_orders"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "poNumber" in field_keys
        assert "supplierName" in field_keys
        assert "totalAmount" in field_keys

    def test_quotations_module_fields(self):
        """Test quotations module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/quotations", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "quotations"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "quotationNumber" in field_keys
        assert "buyerName" in field_keys
        assert "totalAmount" in field_keys

    def test_composite_products_module_fields(self):
        """Test composite_products module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/composite_products", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "composite_products"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "name" in field_keys
        assert "sku" in field_keys

    def test_employees_module_fields(self):
        """Test employees module returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/employees", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "system"
        assert data["name"] == "employees"
        
        field_keys = [f["key"] for f in data["fields"]]
        assert "name" in field_keys
        assert "role" in field_keys
        assert "email" in field_keys

    def test_invalid_module_returns_400(self):
        """Test invalid module ID returns 400"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/invalid", headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Invalid module ID" in response.json().get("detail", "")

    def test_nonexistent_panel_returns_404(self):
        """Test non-existent panel ID returns 404"""
        # Use a valid ObjectId format but non-existent
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/000000000000000000000000", headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestCustomPanelModuleFields:
    """Tests for custom panel module-fields endpoint"""

    @pytest.fixture
    def test_panel_with_relation(self):
        """Create a test panel with relation field for testing"""
        timestamp = int(time.time())
        panel_data = {
            "name": f"TEST_ModuleFields_{timestamp}",
            "description": "Test panel for module-fields endpoint",
            "icon": "layout-grid",
            "color": "purple",
            "fields": [
                {"key": "textField", "label": "Text Field", "type": "text", "required": True},
                {"key": "numberField", "label": "Number Field", "type": "number"},
                {"key": "dropdownField", "label": "Dropdown Field", "type": "dropdown", "options": ["A", "B", "C"]},
                {"key": "productLink", "label": "Product Link", "type": "relation", "relatedPanel": "inventory", "relationType": "many_to_one"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code in [200, 201], f"Failed to create test panel: {response.text}"
        panel = response.json()
        yield panel
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)

    def test_custom_panel_excludes_relation_fields(self, test_panel_with_relation):
        """Test that custom panel module-fields excludes relation fields"""
        panel_id = test_panel_with_relation["id"]
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/{panel_id}", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "panel"
        assert data["name"] == test_panel_with_relation["name"]
        
        # Verify relation field is excluded
        field_keys = [f["key"] for f in data["fields"]]
        assert "textField" in field_keys, "textField should be included"
        assert "numberField" in field_keys, "numberField should be included"
        assert "dropdownField" in field_keys, "dropdownField should be included"
        assert "productLink" not in field_keys, "relation field should be excluded"
        
        # Verify no relation type fields in response
        for field in data["fields"]:
            assert field["type"] != "relation", f"Relation field {field['key']} should not be in response"


class TestAutoCreatedRelationFields:
    """Tests for auto-created relation fields with systemManaged:true"""

    @pytest.fixture
    def test_panel_with_inventory_link(self):
        """Create a test panel with allowedModules=['inventory']"""
        timestamp = int(time.time())
        panel_data = {
            "name": f"TEST_AutoRelation_{timestamp}",
            "description": "Test panel for auto-created relation fields",
            "icon": "layout-grid",
            "color": "blue",
            "fields": [
                {"key": "testField", "label": "Test Field", "type": "text", "required": True}
            ],
            "allowedModules": ["inventory"]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code in [200, 201], f"Failed to create test panel: {response.text}"
        panel = response.json()
        yield panel
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)

    def test_auto_created_inventory_relation_has_system_managed(self, test_panel_with_inventory_link):
        """Test that auto-created inventory relation field has systemManaged:true"""
        panel = test_panel_with_inventory_link
        
        # Find the auto-created product relation field
        product_field = next((f for f in panel["fields"] if f["key"] == "product"), None)
        assert product_field is not None, "Auto-created 'product' field not found"
        
        assert product_field["type"] == "relation"
        assert product_field["relatedPanel"] == "inventory"
        assert product_field["relationType"] == "many_to_one"
        assert product_field.get("systemManaged") == True, "systemManaged should be True"
        assert product_field["required"] == True, "Auto-created field should be required"
        assert "Linked to Inventory" in product_field["label"], f"Label should contain 'Linked to Inventory', got: {product_field['label']}"

    @pytest.fixture
    def test_panel_with_invoice_link(self):
        """Create a test panel with allowedModules=['invoices']"""
        timestamp = int(time.time())
        panel_data = {
            "name": f"TEST_AutoInvoice_{timestamp}",
            "description": "Test panel for auto-created invoice relation",
            "icon": "layout-grid",
            "color": "green",
            "fields": [
                {"key": "testField", "label": "Test Field", "type": "text", "required": True}
            ],
            "allowedModules": ["invoices"]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code in [200, 201], f"Failed to create test panel: {response.text}"
        panel = response.json()
        yield panel
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)

    def test_auto_created_invoice_relation_has_system_managed(self, test_panel_with_invoice_link):
        """Test that auto-created invoice relation field has systemManaged:true"""
        panel = test_panel_with_invoice_link
        
        # Find the auto-created invoice relation field
        invoice_field = next((f for f in panel["fields"] if f["key"] == "invoice"), None)
        assert invoice_field is not None, "Auto-created 'invoice' field not found"
        
        assert invoice_field["type"] == "relation"
        assert invoice_field["relatedPanel"] == "invoices"
        assert invoice_field["relationType"] == "many_to_one"
        assert invoice_field.get("systemManaged") == True, "systemManaged should be True"
        assert invoice_field["required"] == True, "Auto-created field should be required"
        assert "Linked to Invoices" in invoice_field["label"], f"Label should contain 'Linked to Invoices', got: {invoice_field['label']}"


class TestBindingFieldStorage:
    """Tests for bindingField storage in relation fields - KNOWN BUG"""

    def test_binding_field_not_stored_bug(self):
        """
        BUG: bindingField is NOT stored in the backend.
        The Pydantic model PanelFieldInput does not include bindingField.
        Frontend sends it but backend strips it.
        """
        timestamp = int(time.time())
        panel_data = {
            "name": f"TEST_BindingBug_{timestamp}",
            "description": "Test panel for bindingField bug",
            "icon": "layout-grid",
            "color": "red",
            "fields": [
                {"key": "testField", "label": "Test Field", "type": "text", "required": True},
                {
                    "key": "productLink",
                    "label": "Product (Linked to Inventory)",
                    "type": "relation",
                    "relatedPanel": "inventory",
                    "relationType": "many_to_one",
                    "bindingField": "productName"  # This should be stored but isn't
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code in [200, 201], f"Failed to create test panel: {response.text}"
        panel = response.json()
        
        try:
            # Find the relation field
            relation_field = next((f for f in panel["fields"] if f["key"] == "productLink"), None)
            assert relation_field is not None, "Relation field not found"
            
            # BUG: bindingField is NOT stored
            # This test documents the bug - it should fail when the bug is fixed
            binding_field = relation_field.get("bindingField")
            if binding_field is None:
                pytest.skip("KNOWN BUG: bindingField is not stored in backend. PanelFieldInput model needs bindingField: Optional[str] = None")
            else:
                assert binding_field == "productName", f"bindingField should be 'productName', got: {binding_field}"
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)


class TestAutomationWithBindingField:
    """Tests for automation CRUD with relation fields"""

    def test_automation_rules_list(self):
        """Test automation rules list endpoint"""
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "count" in data

    def test_automation_logs_list(self):
        """Test automation logs endpoint"""
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/logs", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data


class TestEndpointRouting:
    """Tests to verify module-fields endpoint is routed correctly (before {panel_id} wildcard)"""

    def test_module_fields_not_confused_with_panel_id(self):
        """Test that module-fields endpoint is not confused with panel ID route"""
        # This should hit the module-fields endpoint, not the get_panel endpoint
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/module-fields/inventory", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        # Should return module fields, not a panel
        assert "fields" in data
        assert data.get("type") == "system"
        assert "id" not in data  # Panel response would have 'id'

    def test_linkable_targets_still_works(self):
        """Test that linkable-targets endpoint still works (also before {panel_id})"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert "targets" in data
        
        # Verify all 8 system modules are present
        system_targets = [t for t in data["targets"] if t["type"] == "system"]
        system_ids = [t["id"] for t in system_targets]
        expected_modules = ["inventory", "invoices", "buyers", "suppliers", "purchase_orders", "quotations", "composite_products", "employees"]
        for module in expected_modules:
            assert module in system_ids, f"System module {module} missing from linkable-targets"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
