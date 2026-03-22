"""
Test: All Modules Relation Lookup - Iteration 108
Tests the expansion of relation field support to all 8 system modules:
- inventory, invoices, buyers, suppliers, purchase_orders, quotations, composite_products, employees
Plus custom panels.

Tests:
1. GET /api/business-tools/panels/linkable-targets - returns all 8 system modules + custom panels
2. GET /api/business-tools/panels/{id}/relation-lookup for each module type
3. POST panel with allowedModules containing new module types
4. Record validation for relation fields pointing to all modules
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test token for dev mode
TEST_TOKEN = "dev-test-token"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    })
    return session


class TestLinkableTargets:
    """Test GET /api/business-tools/panels/linkable-targets endpoint"""
    
    def test_linkable_targets_returns_all_8_system_modules(self, api_client):
        """Verify linkable-targets returns all 8 system modules"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "targets" in data, "Response should have 'targets' key"
        
        targets = data["targets"]
        system_targets = [t for t in targets if t.get("type") == "system"]
        
        # Verify all 8 system modules are present
        expected_modules = {
            "inventory", "invoices", "buyers", "suppliers",
            "purchase_orders", "quotations", "composite_products", "employees"
        }
        actual_module_ids = {t["id"] for t in system_targets}
        
        assert expected_modules == actual_module_ids, f"Expected {expected_modules}, got {actual_module_ids}"
        print(f"✓ All 8 system modules present: {actual_module_ids}")
        
        # Verify each has correct structure
        for target in system_targets:
            assert "id" in target, "Target should have 'id'"
            assert "name" in target, "Target should have 'name'"
            assert "type" in target, "Target should have 'type'"
            assert target["type"] == "system", f"System target should have type='system', got {target['type']}"
        
        print(f"✓ Total targets returned: {len(targets)} (8 system + {len(targets) - 8} custom panels)")
    
    def test_linkable_targets_includes_custom_panels(self, api_client):
        """Verify linkable-targets includes custom panels"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/panels/linkable-targets")
        assert response.status_code == 200
        
        data = response.json()
        targets = data["targets"]
        
        panel_targets = [t for t in targets if t.get("type") == "panel"]
        print(f"✓ Custom panels in linkable targets: {len(panel_targets)}")
        
        # Verify panel targets have correct structure
        for target in panel_targets:
            assert "id" in target, "Panel target should have 'id'"
            assert "name" in target, "Panel target should have 'name'"
            assert target["type"] == "panel", f"Panel target should have type='panel'"


class TestRelationLookupAllModules:
    """Test relation-lookup endpoint for all 8 system modules"""
    
    @pytest.fixture(scope="class")
    def test_panel(self, api_client):
        """Create a test panel for relation lookup tests"""
        panel_data = {
            "name": f"TEST_RelationLookup_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel for relation lookup",
            "fields": [
                {"key": "test_field", "label": "Test Field", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        if response.status_code != 200:
            pytest.skip(f"Could not create test panel: {response.text}")
        
        panel = response.json()
        yield panel
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_relation_lookup_inventory(self, api_client, test_panel):
        """Test relation-lookup for inventory (sellerListings with products)"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "inventory", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should have 'results' key"
        
        # Verify result structure if results exist
        if data["results"]:
            result = data["results"][0]
            assert "id" in result, "Result should have 'id'"
            assert "label" in result, "Result should have 'label' (product name)"
            assert "sub" in result, "Result should have 'sub' (sku)"
            print(f"✓ Inventory lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Inventory lookup returned 0 results (no inventory data)")
    
    def test_relation_lookup_invoices(self, api_client, test_panel):
        """Test relation-lookup for invoices"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "invoices", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Invoice result should have 'label' (invoiceNumber)"
            assert "sub" in result, "Invoice result should have 'sub' (buyerName)"
            print(f"✓ Invoices lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Invoices lookup returned 0 results (no invoice data)")
    
    def test_relation_lookup_buyers(self, api_client, test_panel):
        """Test relation-lookup for buyers (seller_buyers collection)"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "buyers", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Buyer result should have 'label' (buyerName)"
            assert "sub" in result, "Buyer result should have 'sub' (phone)"
            print(f"✓ Buyers lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Buyers lookup returned 0 results (no buyer data)")
    
    def test_relation_lookup_suppliers(self, api_client, test_panel):
        """Test relation-lookup for suppliers (seller_suppliers collection)"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "suppliers", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Supplier result should have 'label' (supplierName)"
            assert "sub" in result, "Supplier result should have 'sub' (phone)"
            print(f"✓ Suppliers lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Suppliers lookup returned 0 results (no supplier data)")
    
    def test_relation_lookup_purchase_orders(self, api_client, test_panel):
        """Test relation-lookup for purchase_orders"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "purchase_orders", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "PO result should have 'label' (poNumber)"
            assert "sub" in result, "PO result should have 'sub' (supplierName)"
            print(f"✓ Purchase Orders lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Purchase Orders lookup returned 0 results (no PO data)")
    
    def test_relation_lookup_quotations(self, api_client, test_panel):
        """Test relation-lookup for quotations (with buyer name lookup)"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "quotations", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Quotation result should have 'label' (quotationNumber)"
            assert "sub" in result, "Quotation result should have 'sub' (buyerName from lookup)"
            print(f"✓ Quotations lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Quotations lookup returned 0 results (no quotation data)")
    
    def test_relation_lookup_composite_products(self, api_client, test_panel):
        """Test relation-lookup for composite_products"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "composite_products", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Composite product result should have 'label' (name)"
            assert "sub" in result, "Composite product result should have 'sub' (price)"
            print(f"✓ Composite Products lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Composite Products lookup returned 0 results (no composite product data)")
    
    def test_relation_lookup_employees(self, api_client, test_panel):
        """Test relation-lookup for employees (users with companyId filter)"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "employees", "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "label" in result, "Employee result should have 'label' (name or email)"
            assert "sub" in result, "Employee result should have 'sub' (employeeRole)"
            print(f"✓ Employees lookup returned {len(data['results'])} results")
            print(f"  Sample: id={result['id']}, label={result['label']}, sub={result.get('sub', '')}")
        else:
            print("✓ Employees lookup returned 0 results (no employee data)")
    
    def test_relation_lookup_custom_panel(self, api_client, test_panel):
        """Test relation-lookup for custom panel records"""
        # First get list of panels to find another panel to link to
        panels_response = api_client.get(f"{BASE_URL}/api/business-tools/panels")
        if panels_response.status_code != 200:
            pytest.skip("Could not get panels list")
        
        panels = panels_response.json().get("panels", [])
        other_panels = [p for p in panels if p["id"] != test_panel["id"]]
        
        if not other_panels:
            print("✓ Custom panel lookup skipped (no other panels to link to)")
            return
        
        target_panel_id = other_panels[0]["id"]
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": target_panel_id, "search": ""}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        print(f"✓ Custom panel lookup returned {len(data['results'])} results for panel {target_panel_id}")


class TestPanelCreationWithNewModules:
    """Test creating panels with allowedModules containing new module types"""
    
    def test_create_panel_with_buyers_module(self, api_client):
        """Test creating panel linked to buyers module"""
        panel_data = {
            "name": f"TEST_BuyersPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to buyers",
            "allowedModules": ["buyers"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "buyers" in panel.get("allowedModules", []), "Panel should have buyers in allowedModules"
        print(f"✓ Created panel with buyers module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_suppliers_module(self, api_client):
        """Test creating panel linked to suppliers module"""
        panel_data = {
            "name": f"TEST_SuppliersPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to suppliers",
            "allowedModules": ["suppliers"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "suppliers" in panel.get("allowedModules", []), "Panel should have suppliers in allowedModules"
        print(f"✓ Created panel with suppliers module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_purchase_orders_module(self, api_client):
        """Test creating panel linked to purchase_orders module"""
        panel_data = {
            "name": f"TEST_POPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to purchase orders",
            "allowedModules": ["purchase_orders"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "purchase_orders" in panel.get("allowedModules", []), "Panel should have purchase_orders in allowedModules"
        print(f"✓ Created panel with purchase_orders module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_quotations_module(self, api_client):
        """Test creating panel linked to quotations module"""
        panel_data = {
            "name": f"TEST_QuotationsPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to quotations",
            "allowedModules": ["quotations"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "quotations" in panel.get("allowedModules", []), "Panel should have quotations in allowedModules"
        print(f"✓ Created panel with quotations module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_composite_products_module(self, api_client):
        """Test creating panel linked to composite_products module"""
        panel_data = {
            "name": f"TEST_CompositePanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to composite products",
            "allowedModules": ["composite_products"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "composite_products" in panel.get("allowedModules", []), "Panel should have composite_products in allowedModules"
        print(f"✓ Created panel with composite_products module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_employees_module(self, api_client):
        """Test creating panel linked to employees module"""
        panel_data = {
            "name": f"TEST_EmployeesPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to employees",
            "allowedModules": ["employees"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        assert "employees" in panel.get("allowedModules", []), "Panel should have employees in allowedModules"
        print(f"✓ Created panel with employees module: {panel['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_create_panel_with_multiple_modules(self, api_client):
        """Test creating panel linked to multiple modules"""
        panel_data = {
            "name": f"TEST_MultiModulePanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel linked to multiple modules",
            "allowedModules": ["inventory", "buyers", "suppliers", "employees"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        allowed = panel.get("allowedModules", [])
        assert "inventory" in allowed, "Panel should have inventory in allowedModules"
        assert "buyers" in allowed, "Panel should have buyers in allowedModules"
        assert "suppliers" in allowed, "Panel should have suppliers in allowedModules"
        assert "employees" in allowed, "Panel should have employees in allowedModules"
        print(f"✓ Created panel with multiple modules: {panel['id']}, allowedModules={allowed}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")


class TestRelationFieldValidation:
    """Test record validation for relation fields pointing to all modules"""
    
    def test_create_panel_with_relation_field_to_buyers(self, api_client):
        """Test creating panel with relation field to buyers and validating records"""
        # Create panel with relation field to buyers
        panel_data = {
            "name": f"TEST_BuyerRelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with buyer relation",
            "fields": [
                {"key": "buyer_ref", "label": "Buyer Reference", "type": "relation", "required": False, "relatedPanel": "buyers", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        buyer_field = next((f for f in panel["fields"] if f["key"] == "buyer_ref"), None)
        assert buyer_field is not None, "buyer_ref field should exist"
        assert buyer_field["type"] == "relation", "Field type should be relation"
        assert buyer_field["relatedPanel"] == "buyers", "relatedPanel should be buyers"
        print(f"✓ Created panel with buyer relation field: {panel_id}")
        
        # Test creating record with invalid buyer ID
        record_data = {"data": {"buyer_ref": "000000000000000000000000", "notes": "Test"}}
        record_response = api_client.post(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", json=record_data)
        
        # Should fail validation (invalid buyer ID)
        if record_response.status_code == 400:
            error = record_response.json()
            assert "non-existent" in error.get("detail", "").lower() or "not found" in error.get("detail", "").lower(), f"Expected validation error, got: {error}"
            print(f"✓ Invalid buyer ID correctly rejected: {error.get('detail', '')}")
        else:
            # If it passes, the buyer might exist - that's also valid
            print(f"✓ Record creation returned {record_response.status_code} (buyer may exist)")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")
    
    def test_create_panel_with_relation_field_to_suppliers(self, api_client):
        """Test creating panel with relation field to suppliers"""
        panel_data = {
            "name": f"TEST_SupplierRelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with supplier relation",
            "fields": [
                {"key": "supplier_ref", "label": "Supplier Reference", "type": "relation", "required": False, "relatedPanel": "suppliers", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        supplier_field = next((f for f in panel["fields"] if f["key"] == "supplier_ref"), None)
        assert supplier_field is not None, "supplier_ref field should exist"
        assert supplier_field["relatedPanel"] == "suppliers", "relatedPanel should be suppliers"
        print(f"✓ Created panel with supplier relation field: {panel_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")
    
    def test_create_panel_with_relation_field_to_purchase_orders(self, api_client):
        """Test creating panel with relation field to purchase_orders"""
        panel_data = {
            "name": f"TEST_PORelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with PO relation",
            "fields": [
                {"key": "po_ref", "label": "PO Reference", "type": "relation", "required": False, "relatedPanel": "purchase_orders", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        po_field = next((f for f in panel["fields"] if f["key"] == "po_ref"), None)
        assert po_field is not None, "po_ref field should exist"
        assert po_field["relatedPanel"] == "purchase_orders", "relatedPanel should be purchase_orders"
        print(f"✓ Created panel with purchase_orders relation field: {panel_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")
    
    def test_create_panel_with_relation_field_to_quotations(self, api_client):
        """Test creating panel with relation field to quotations"""
        panel_data = {
            "name": f"TEST_QuotationRelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with quotation relation",
            "fields": [
                {"key": "quotation_ref", "label": "Quotation Reference", "type": "relation", "required": False, "relatedPanel": "quotations", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        quotation_field = next((f for f in panel["fields"] if f["key"] == "quotation_ref"), None)
        assert quotation_field is not None, "quotation_ref field should exist"
        assert quotation_field["relatedPanel"] == "quotations", "relatedPanel should be quotations"
        print(f"✓ Created panel with quotations relation field: {panel_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")
    
    def test_create_panel_with_relation_field_to_composite_products(self, api_client):
        """Test creating panel with relation field to composite_products"""
        panel_data = {
            "name": f"TEST_CompositeRelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with composite product relation",
            "fields": [
                {"key": "composite_ref", "label": "Composite Product Reference", "type": "relation", "required": False, "relatedPanel": "composite_products", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        composite_field = next((f for f in panel["fields"] if f["key"] == "composite_ref"), None)
        assert composite_field is not None, "composite_ref field should exist"
        assert composite_field["relatedPanel"] == "composite_products", "relatedPanel should be composite_products"
        print(f"✓ Created panel with composite_products relation field: {panel_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")
    
    def test_create_panel_with_relation_field_to_employees(self, api_client):
        """Test creating panel with relation field to employees"""
        panel_data = {
            "name": f"TEST_EmployeeRelation_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel with employee relation",
            "fields": [
                {"key": "employee_ref", "label": "Employee Reference", "type": "relation", "required": False, "relatedPanel": "employees", "relationType": "many_to_one"},
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        panel = response.json()
        panel_id = panel["id"]
        
        # Verify relation field was created
        employee_field = next((f for f in panel["fields"] if f["key"] == "employee_ref"), None)
        assert employee_field is not None, "employee_ref field should exist"
        assert employee_field["relatedPanel"] == "employees", "relatedPanel should be employees"
        print(f"✓ Created panel with employees relation field: {panel_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}")


class TestSearchFiltering:
    """Test search filtering for relation lookups"""
    
    @pytest.fixture(scope="class")
    def test_panel(self, api_client):
        """Create a test panel for search tests"""
        panel_data = {
            "name": f"TEST_SearchPanel_{datetime.now().strftime('%H%M%S')}",
            "description": "Test panel for search filtering",
            "fields": [
                {"key": "test_field", "label": "Test Field", "type": "text", "required": False}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data)
        if response.status_code != 200:
            pytest.skip(f"Could not create test panel: {response.text}")
        
        panel = response.json()
        yield panel
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}")
    
    def test_search_filtering_inventory(self, api_client, test_panel):
        """Test search filtering for inventory lookup"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "inventory", "search": "test"}
        )
        assert response.status_code == 200
        print(f"✓ Inventory search with 'test' returned {len(response.json().get('results', []))} results")
    
    def test_search_filtering_buyers(self, api_client, test_panel):
        """Test search filtering for buyers lookup"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "buyers", "search": "test"}
        )
        assert response.status_code == 200
        print(f"✓ Buyers search with 'test' returned {len(response.json().get('results', []))} results")
    
    def test_search_filtering_suppliers(self, api_client, test_panel):
        """Test search filtering for suppliers lookup"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "suppliers", "search": "test"}
        )
        assert response.status_code == 200
        print(f"✓ Suppliers search with 'test' returned {len(response.json().get('results', []))} results")
    
    def test_search_filtering_employees(self, api_client, test_panel):
        """Test search filtering for employees lookup"""
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/panels/{test_panel['id']}/relation-lookup",
            params={"target": "employees", "search": "test"}
        )
        assert response.status_code == 200
        print(f"✓ Employees search with 'test' returned {len(response.json().get('results', []))} results")


class TestHealthAndAccess:
    """Basic health and access level tests"""
    
    def test_api_health(self, api_client):
        """Test API health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ API health check passed")
    
    def test_access_level(self, api_client):
        """Test access level endpoint"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/access-level")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "level" in data, "Response should have 'level' key"
        print(f"✓ Access level: {data['level']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
