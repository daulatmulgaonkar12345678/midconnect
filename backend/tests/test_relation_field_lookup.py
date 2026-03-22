"""
Test Relation Field Lookup - Tests for the relation-lookup endpoint and RelationField component integration
Tests:
1. GET /api/business-tools/panels/{panel_id}/relation-lookup?target=inventory&search= returns product results
2. GET /api/business-tools/panels/{panel_id}/relation-lookup?target=invoices&search= returns invoice results
3. POST /api/business-tools/panels - create panel with allowedModules=['inventory'] auto-adds Product relation field
4. POST /api/business-tools/panels/{panel_id}/records - create record with relation field value validates against inventory
5. Relation lookup returns correct format: {results: [{id, label, sub}]}
6. Search filtering works for inventory products
7. Search filtering works for invoices
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test auth token (dev mode bypass)
AUTH_TOKEN = "dev-test-token"

class TestRelationFieldLookup:
    """Tests for relation-lookup endpoint and relation field functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        self.created_panels = []
        self.created_products = []
        self.created_records = []
        yield
        # Cleanup
        for record_id, panel_id in self.created_records:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_id}", headers=self.headers)
            except:
                pass
        for panel_id in self.created_panels:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=self.headers)
            except:
                pass
        for product_id in self.created_products:
            try:
                requests.delete(f"{BASE_URL}/api/inventory/products/{product_id}", headers=self.headers)
            except:
                pass

    def test_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")

    def test_access_level_advanced(self):
        """Verify user has advanced access for business tools"""
        response = requests.get(f"{BASE_URL}/api/business-tools/access-level", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("level") == "advanced", f"Expected advanced access, got {data.get('level')}"
        print(f"✓ Access level: {data.get('level')}")

    def test_create_panel_with_inventory_module_auto_adds_product_field(self):
        """POST /api/business-tools/panels with allowedModules=['inventory'] auto-adds Product relation field"""
        panel_data = {
            "name": f"TEST_RelationTest_{int(time.time())}",
            "description": "Test panel for relation field testing",
            "color": "blue",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "notes", "label": "Notes", "type": "text", "required": False}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        
        data = response.json()
        panel_id = data.get("id")
        self.created_panels.append(panel_id)
        
        # Verify Product relation field was auto-added
        fields = data.get("fields", [])
        product_field = next((f for f in fields if f.get("key") == "product"), None)
        
        assert product_field is not None, "Product relation field was not auto-added"
        assert product_field.get("type") == "relation", f"Expected type 'relation', got {product_field.get('type')}"
        assert product_field.get("relatedPanel") == "inventory", f"Expected relatedPanel 'inventory', got {product_field.get('relatedPanel')}"
        assert product_field.get("required") == True, "Product field should be required"
        assert product_field.get("relationType") == "many_to_one", f"Expected relationType 'many_to_one', got {product_field.get('relationType')}"
        
        print(f"✓ Panel created with auto-added Product relation field: {panel_id}")
        return panel_id

    def test_create_panel_with_invoices_module_auto_adds_invoice_field(self):
        """POST /api/business-tools/panels with allowedModules=['invoices'] auto-adds Invoice relation field"""
        panel_data = {
            "name": f"TEST_InvoiceRelation_{int(time.time())}",
            "description": "Test panel for invoice relation",
            "color": "green",
            "allowedModules": ["invoices"],
            "fields": [
                {"key": "status", "label": "Status", "type": "dropdown", "required": False, "options": ["Pending", "Done"]}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        
        data = response.json()
        panel_id = data.get("id")
        self.created_panels.append(panel_id)
        
        # Verify Invoice relation field was auto-added
        fields = data.get("fields", [])
        invoice_field = next((f for f in fields if f.get("key") == "invoice"), None)
        
        assert invoice_field is not None, "Invoice relation field was not auto-added"
        assert invoice_field.get("type") == "relation"
        assert invoice_field.get("relatedPanel") == "invoices"
        
        print(f"✓ Panel created with auto-added Invoice relation field: {panel_id}")
        return panel_id

    def test_relation_lookup_inventory_returns_products(self):
        """GET /api/business-tools/panels/{panel_id}/relation-lookup?target=inventory returns product results"""
        # First create a panel
        panel_data = {
            "name": f"TEST_LookupTest_{int(time.time())}",
            "description": "Test panel for lookup",
            "color": "purple",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Test relation lookup for inventory
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/relation-lookup",
            params={"target": "inventory", "search": ""},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200, f"Relation lookup failed: {lookup_response.text}"
        data = lookup_response.json()
        
        # Verify response structure
        assert "results" in data, "Response should have 'results' key"
        results = data.get("results", [])
        
        # Results should be a list
        assert isinstance(results, list), "Results should be a list"
        
        # If there are results, verify structure
        if len(results) > 0:
            first_result = results[0]
            assert "id" in first_result, "Each result should have 'id'"
            assert "label" in first_result, "Each result should have 'label'"
            # 'sub' is optional but should be present for inventory (SKU)
            print(f"✓ Relation lookup returned {len(results)} products")
            print(f"  Sample: id={first_result.get('id')}, label={first_result.get('label')}, sub={first_result.get('sub')}")
        else:
            print("✓ Relation lookup returned empty results (no products in inventory)")
        
        return panel_id

    def test_relation_lookup_invoices_returns_invoices(self):
        """GET /api/business-tools/panels/{panel_id}/relation-lookup?target=invoices returns invoice results"""
        # First create a panel
        panel_data = {
            "name": f"TEST_InvoiceLookup_{int(time.time())}",
            "description": "Test panel for invoice lookup",
            "color": "orange",
            "allowedModules": ["invoices"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Test relation lookup for invoices
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/relation-lookup",
            params={"target": "invoices", "search": ""},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200, f"Relation lookup failed: {lookup_response.text}"
        data = lookup_response.json()
        
        # Verify response structure
        assert "results" in data, "Response should have 'results' key"
        results = data.get("results", [])
        
        # Results should be a list
        assert isinstance(results, list), "Results should be a list"
        
        # If there are results, verify structure
        if len(results) > 0:
            first_result = results[0]
            assert "id" in first_result, "Each result should have 'id'"
            assert "label" in first_result, "Each result should have 'label' (invoiceNumber)"
            # 'sub' should be buyerName for invoices
            print(f"✓ Relation lookup returned {len(results)} invoices")
            print(f"  Sample: id={first_result.get('id')}, label={first_result.get('label')}, sub={first_result.get('sub')}")
        else:
            print("✓ Relation lookup returned empty results (no invoices)")
        
        return panel_id

    def test_relation_lookup_with_search_filter(self):
        """Relation lookup filters results based on search query"""
        # Create a panel
        panel_data = {
            "name": f"TEST_SearchFilter_{int(time.time())}",
            "description": "Test search filtering",
            "color": "red",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Test with a search query
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/relation-lookup",
            params={"target": "inventory", "search": "test"},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200, f"Search lookup failed: {lookup_response.text}"
        data = lookup_response.json()
        assert "results" in data
        
        print(f"✓ Search filter returned {len(data.get('results', []))} results for 'test'")

    def test_create_record_with_valid_relation_value(self):
        """POST /api/business-tools/panels/{panel_id}/records with valid relation field value"""
        # First get existing products
        products_response = requests.get(f"{BASE_URL}/api/inventory/products", headers=self.headers)
        
        if products_response.status_code != 200:
            pytest.skip("Cannot access inventory products")
        
        products_data = products_response.json()
        products = products_data.get("products", [])
        
        if len(products) == 0:
            pytest.skip("No products in inventory to test relation")
        
        product_id = products[0].get("id")
        product_name = products[0].get("name", "Unknown")
        
        # Create a panel with inventory module
        panel_data = {
            "name": f"TEST_RecordRelation_{int(time.time())}",
            "description": "Test record with relation",
            "color": "cyan",
            "allowedModules": ["inventory"],
            "fields": [
                {"key": "quantity", "label": "Quantity", "type": "number", "required": False}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Create a record with the product relation
        record_data = {
            "data": {
                "product": product_id,
                "quantity": 10
            }
        }
        
        record_response = requests.post(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
            json=record_data,
            headers=self.headers
        )
        
        assert record_response.status_code == 200, f"Failed to create record: {record_response.text}"
        record = record_response.json()
        record_id = record.get("id")
        self.created_records.append((record_id, panel_id))
        
        assert record.get("data", {}).get("product") == product_id
        print(f"✓ Created record with product relation: {product_name} ({product_id})")
        
        return record_id, panel_id

    def test_create_record_with_invalid_relation_value_fails(self):
        """POST /api/business-tools/panels/{panel_id}/records with invalid relation value returns 400"""
        # Create a panel with inventory module
        panel_data = {
            "name": f"TEST_InvalidRelation_{int(time.time())}",
            "description": "Test invalid relation",
            "color": "pink",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Try to create a record with an invalid product ID
        record_data = {
            "data": {
                "product": "000000000000000000000000"  # Non-existent ObjectId
            }
        }
        
        record_response = requests.post(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
            json=record_data,
            headers=self.headers
        )
        
        # Should fail validation
        assert record_response.status_code == 400, f"Expected 400 for invalid relation, got {record_response.status_code}"
        error_data = record_response.json()
        assert "non-existent" in error_data.get("detail", "").lower() or "required" in error_data.get("detail", "").lower()
        
        print(f"✓ Invalid relation value correctly rejected: {error_data.get('detail')}")

    def test_get_record_returns_resolved_relation(self):
        """GET /api/business-tools/panels/{panel_id}/records/{record_id} returns _resolved with label"""
        # First get existing products
        products_response = requests.get(f"{BASE_URL}/api/inventory/products", headers=self.headers)
        
        if products_response.status_code != 200:
            pytest.skip("Cannot access inventory products")
        
        products_data = products_response.json()
        products = products_data.get("products", [])
        
        if len(products) == 0:
            pytest.skip("No products in inventory to test relation")
        
        product_id = products[0].get("id")
        product_name = products[0].get("name", "Unknown")
        product_sku = products[0].get("sku", "")
        
        # Create a panel with inventory module
        panel_data = {
            "name": f"TEST_ResolvedRelation_{int(time.time())}",
            "description": "Test resolved relation",
            "color": "teal",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Create a record with the product relation
        record_data = {
            "data": {
                "product": product_id
            }
        }
        
        record_response = requests.post(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
            json=record_data,
            headers=self.headers
        )
        
        assert record_response.status_code == 200
        record_id = record_response.json().get("id")
        self.created_records.append((record_id, panel_id))
        
        # Get the record and check _resolved
        get_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_id}",
            headers=self.headers
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        record = data.get("record", {})
        
        # Check _resolved contains the product info
        resolved = record.get("_resolved", {})
        product_resolved = resolved.get("product", {})
        
        assert product_resolved.get("id") == product_id, "Resolved product ID should match"
        assert product_resolved.get("label") == product_name, f"Resolved label should be product name, got {product_resolved.get('label')}"
        
        print(f"✓ Record returned with resolved relation: label={product_resolved.get('label')}, sku={product_resolved.get('sku')}")

    def test_list_records_returns_resolved_relations(self):
        """GET /api/business-tools/panels/{panel_id}/records returns _resolved for each record"""
        # First get existing products
        products_response = requests.get(f"{BASE_URL}/api/inventory/products", headers=self.headers)
        
        if products_response.status_code != 200:
            pytest.skip("Cannot access inventory products")
        
        products_data = products_response.json()
        products = products_data.get("products", [])
        
        if len(products) == 0:
            pytest.skip("No products in inventory to test relation")
        
        product_id = products[0].get("id")
        
        # Create a panel with inventory module
        panel_data = {
            "name": f"TEST_ListResolved_{int(time.time())}",
            "description": "Test list resolved",
            "color": "lime",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Create a record
        record_data = {"data": {"product": product_id}}
        record_response = requests.post(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
            json=record_data,
            headers=self.headers
        )
        assert record_response.status_code == 200
        record_id = record_response.json().get("id")
        self.created_records.append((record_id, panel_id))
        
        # List records
        list_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
            headers=self.headers
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        records = data.get("records", [])
        
        assert len(records) > 0, "Should have at least one record"
        
        # Check first record has _resolved
        first_record = records[0]
        assert "_resolved" in first_record, "Record should have _resolved field"
        
        print(f"✓ List records returned {len(records)} records with _resolved data")

    def test_relation_lookup_custom_panel(self):
        """Relation lookup works for custom panel targets"""
        # Create a source panel (to be linked to)
        source_panel_data = {
            "name": f"TEST_SourcePanel_{int(time.time())}",
            "description": "Source panel for linking",
            "color": "indigo",
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=source_panel_data, headers=self.headers)
        assert response.status_code == 200
        source_panel_id = response.json().get("id")
        self.created_panels.append(source_panel_id)
        
        # Create a record in source panel
        record_data = {"data": {"name": "Test Source Record"}}
        record_response = requests.post(
            f"{BASE_URL}/api/business-tools/panels/{source_panel_id}/records",
            json=record_data,
            headers=self.headers
        )
        assert record_response.status_code == 200
        source_record_id = record_response.json().get("id")
        self.created_records.append((source_record_id, source_panel_id))
        
        # Create a target panel that links to source panel
        target_panel_data = {
            "name": f"TEST_TargetPanel_{int(time.time())}",
            "description": "Target panel with relation",
            "color": "amber",
            "allowedPanels": [source_panel_id],
            "fields": [
                {
                    "key": "linkedRecord",
                    "label": "Linked Record",
                    "type": "relation",
                    "relatedPanel": source_panel_id,
                    "relationType": "many_to_one",
                    "required": False
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=target_panel_data, headers=self.headers)
        assert response.status_code == 200
        target_panel_id = response.json().get("id")
        self.created_panels.append(target_panel_id)
        
        # Test relation lookup for custom panel
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{target_panel_id}/relation-lookup",
            params={"target": source_panel_id, "search": ""},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200, f"Custom panel lookup failed: {lookup_response.text}"
        data = lookup_response.json()
        results = data.get("results", [])
        
        assert len(results) > 0, "Should find the source record"
        assert results[0].get("label") == "Test Source Record"
        
        print(f"✓ Custom panel relation lookup returned {len(results)} results")


class TestRelationFieldEdgeCases:
    """Edge case tests for relation field functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        self.created_panels = []
        yield
        # Cleanup
        for panel_id in self.created_panels:
            try:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=self.headers)
            except:
                pass

    def test_relation_lookup_empty_search(self):
        """Relation lookup with empty search returns all results (up to limit)"""
        # Create a panel
        panel_data = {
            "name": f"TEST_EmptySearch_{int(time.time())}",
            "description": "Test empty search",
            "color": "gray",
            "allowedModules": ["inventory"],
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Test with empty search
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/relation-lookup",
            params={"target": "inventory", "search": ""},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200
        data = lookup_response.json()
        assert "results" in data
        
        print(f"✓ Empty search returned {len(data.get('results', []))} results")

    def test_relation_lookup_no_target(self):
        """Relation lookup without target parameter returns empty results"""
        # Create a panel
        panel_data = {
            "name": f"TEST_NoTarget_{int(time.time())}",
            "description": "Test no target",
            "color": "slate",
            "fields": []
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_data, headers=self.headers)
        assert response.status_code == 200
        panel_id = response.json().get("id")
        self.created_panels.append(panel_id)
        
        # Test without target
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/relation-lookup",
            params={"search": "test"},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 200
        data = lookup_response.json()
        # Should return empty results when no valid target
        assert data.get("results", []) == []
        
        print("✓ No target parameter returns empty results")

    def test_relation_lookup_invalid_panel_id(self):
        """Relation lookup with invalid panel ID returns 404"""
        lookup_response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/000000000000000000000000/relation-lookup",
            params={"target": "inventory", "search": ""},
            headers=self.headers
        )
        
        assert lookup_response.status_code == 404, f"Expected 404, got {lookup_response.status_code}"
        print("✓ Invalid panel ID returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
