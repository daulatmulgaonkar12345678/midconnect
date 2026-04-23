"""
Test Custom Panel System Phase 2 - Record CRUD, Relations, Field Editing
Tests record lifecycle, relation lookup, soft disable, field deletion protection.
Uses dev-test-token for authentication (Firebase bypass in dev mode).
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Test data tracking for cleanup
created_panel_ids = []
created_record_ids = []


def unique_name(prefix):
    """Generate a unique name using UUID"""
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}"


def cleanup_test_panels():
    """Clean up all TEST_ prefixed panels"""
    response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
    if response.status_code == 200:
        panels = response.json().get("panels", [])
        for panel in panels:
            if panel.get("name", "").startswith("TEST_"):
                # First delete all records in the panel
                records_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records", headers=AUTH_HEADER)
                if records_res.status_code == 200:
                    for rec in records_res.json().get("records", []):
                        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}/records/{rec['id']}", headers=AUTH_HEADER)
                # Then delete the panel
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel['id']}", headers=AUTH_HEADER)


# Run cleanup before tests start
cleanup_test_panels()


class TestRecordCRUD:
    """Test record create, read, update, delete operations"""
    
    @pytest.fixture(autouse=True)
    def setup_panel(self):
        """Create a test panel with various field types for record testing"""
        panel_data = {
            "name": unique_name("Records_Panel"),
            "description": "Panel for testing record CRUD",
            "fields": [
                {"key": "title", "label": "Title", "type": "text", "required": True},
                {"key": "quantity", "label": "Quantity", "type": "number", "required": False},
                {"key": "status", "label": "Status", "type": "dropdown", "required": True, "options": ["Active", "Pending", "Completed"]},
                {"key": "tags", "label": "Tags", "type": "multiselect", "required": False, "options": ["Urgent", "Review", "Approved"]},
                {"key": "is_verified", "label": "Verified", "type": "boolean", "required": False},
                {"key": "notes", "label": "Notes", "type": "longtext", "required": False},
                {"key": "due_date", "label": "Due Date", "type": "date", "required": False}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        yield
        # Cleanup panel after test
        try:
            # Delete records first
            records_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER)
            if records_res.status_code == 200:
                for rec in records_res.json().get("records", []):
                    requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{rec['id']}", headers=AUTH_HEADER)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_create_record_with_valid_data(self):
        """POST /api/business-tools/panels/{id}/records creates a record with valid data"""
        record_data = {
            "data": {
                "title": "Test Record 1",
                "quantity": 100,
                "status": "Active",
                "tags": ["Urgent", "Review"],
                "is_verified": True,
                "notes": "This is a test record with all fields populated",
                "due_date": "2026-02-15"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain record 'id'"
        assert data["data"]["title"] == "Test Record 1", "Title should match"
        assert data["data"]["quantity"] == 100, "Quantity should match"
        assert data["data"]["status"] == "Active", "Status should match"
        assert data["data"]["tags"] == ["Urgent", "Review"], "Tags should match"
        assert data["data"]["is_verified"] == True, "is_verified should be True"
        
        created_record_ids.append((self.panel_id, data["id"]))
        print(f"✓ Created record with ID: {data['id']}")
    
    def test_create_record_rejects_missing_required_fields(self):
        """POST /api/business-tools/panels/{id}/records rejects missing required fields"""
        # Missing 'title' which is required
        record_data = {
            "data": {
                "quantity": 50,
                "status": "Active"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for missing required field, got {response.status_code}: {response.text}"
        assert "required" in response.json().get("detail", "").lower(), "Error should mention required field"
        print("✓ Missing required field correctly rejected")
    
    def test_create_record_rejects_missing_required_dropdown(self):
        """POST /api/business-tools/panels/{id}/records rejects missing required dropdown"""
        # Missing 'status' which is required dropdown
        record_data = {
            "data": {
                "title": "Test Record"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for missing required dropdown, got {response.status_code}: {response.text}"
        assert "required" in response.json().get("detail", "").lower(), "Error should mention required field"
        print("✓ Missing required dropdown correctly rejected")
    
    def test_create_record_validates_dropdown_options(self):
        """POST /api/business-tools/panels/{id}/records validates dropdown options"""
        record_data = {
            "data": {
                "title": "Test Record",
                "status": "InvalidOption"  # Not in ["Active", "Pending", "Completed"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for invalid dropdown option, got {response.status_code}: {response.text}"
        assert "must be one of" in response.json().get("detail", "").lower(), "Error should mention valid options"
        print("✓ Invalid dropdown option correctly rejected")
    
    def test_create_record_validates_multiselect_options(self):
        """POST /api/business-tools/panels/{id}/records validates multiselect options"""
        record_data = {
            "data": {
                "title": "Test Record",
                "status": "Active",
                "tags": ["Urgent", "InvalidTag"]  # "InvalidTag" not in options
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for invalid multiselect option, got {response.status_code}: {response.text}"
        assert "invalid" in response.json().get("detail", "").lower(), "Error should mention invalid options"
        print("✓ Invalid multiselect option correctly rejected")
    
    def test_create_record_validates_boolean_type(self):
        """POST /api/business-tools/panels/{id}/records validates boolean type"""
        record_data = {
            "data": {
                "title": "Test Record",
                "status": "Active",
                "is_verified": "yes"  # Should be boolean, not string
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for invalid boolean, got {response.status_code}: {response.text}"
        assert "true or false" in response.json().get("detail", "").lower(), "Error should mention boolean requirement"
        print("✓ Invalid boolean type correctly rejected")
    
    def test_create_record_validates_number_type(self):
        """POST /api/business-tools/panels/{id}/records validates number type"""
        record_data = {
            "data": {
                "title": "Test Record",
                "status": "Active",
                "quantity": "not-a-number"  # Should be numeric
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert response.status_code == 400, f"Expected 400 for invalid number, got {response.status_code}: {response.text}"
        assert "number" in response.json().get("detail", "").lower(), "Error should mention number requirement"
        print("✓ Invalid number type correctly rejected")


class TestRecordListAndSearch:
    """Test record listing and search functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_panel_with_records(self):
        """Create a test panel with multiple records for list/search testing"""
        panel_data = {
            "name": unique_name("Search_Panel"),
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "category", "label": "Category", "type": "dropdown", "required": False, "options": ["Electronics", "Furniture", "Clothing"]},
                {"key": "description", "label": "Description", "type": "longtext", "required": False}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        
        # Create multiple records
        records = [
            {"data": {"name": "Laptop Pro", "category": "Electronics", "description": "High-end laptop"}},
            {"data": {"name": "Office Chair", "category": "Furniture", "description": "Ergonomic chair"}},
            {"data": {"name": "Winter Jacket", "category": "Clothing", "description": "Warm jacket"}},
            {"data": {"name": "Smartphone", "category": "Electronics", "description": "Latest phone model"}},
            {"data": {"name": "Desk Lamp", "category": "Furniture", "description": "LED desk lamp"}}
        ]
        
        self.record_ids = []
        for rec in records:
            res = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=rec)
            if res.status_code == 200:
                self.record_ids.append(res.json()["id"])
                created_record_ids.append((self.panel_id, res.json()["id"]))
        
        yield
        # Cleanup
        try:
            for rid in self.record_ids:
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{rid}", headers=AUTH_HEADER)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_list_records_with_pagination(self):
        """GET /api/business-tools/panels/{id}/records lists records with pagination"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records?page=1", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "records" in data, "Response should contain 'records'"
        assert "total" in data, "Response should contain 'total'"
        assert "page" in data, "Response should contain 'page'"
        assert "pages" in data, "Response should contain 'pages'"
        assert "panelName" in data, "Response should contain 'panelName'"
        assert isinstance(data["records"], list), "Records should be a list"
        assert data["total"] >= 5, f"Should have at least 5 records, got {data['total']}"
        print(f"✓ Listed {len(data['records'])} records (total: {data['total']}, page: {data['page']}/{data['pages']})")
    
    def test_list_records_supports_search(self):
        """GET /api/business-tools/panels/{id}/records supports search"""
        # Search for "Laptop"
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records?search=Laptop", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert len(data["records"]) >= 1, "Should find at least 1 record matching 'Laptop'"
        
        # Verify search result contains "Laptop"
        found_laptop = any("Laptop" in rec["data"].get("name", "") for rec in data["records"])
        assert found_laptop, "Search results should contain 'Laptop'"
        print(f"✓ Search for 'Laptop' returned {len(data['records'])} records")
    
    def test_search_across_text_fields(self):
        """Search works across text, longtext, and dropdown fields"""
        # Search for "Electronics" (category dropdown)
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records?search=Electronics", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert len(data["records"]) >= 2, "Should find at least 2 Electronics records"
        print(f"✓ Search for 'Electronics' returned {len(data['records'])} records")
    
    def test_search_in_longtext_field(self):
        """Search works in longtext fields"""
        # Search for "Ergonomic" (in description)
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records?search=Ergonomic", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert len(data["records"]) >= 1, "Should find at least 1 record with 'Ergonomic' in description"
        print(f"✓ Search for 'Ergonomic' in longtext returned {len(data['records'])} records")


class TestRecordGetUpdateDelete:
    """Test single record get, update, and delete"""
    
    @pytest.fixture(autouse=True)
    def setup_panel_with_record(self):
        """Create a test panel with a record"""
        panel_data = {
            "name": unique_name("CRUD_Panel"),
            "fields": [
                {"key": "title", "label": "Title", "type": "text", "required": True},
                {"key": "status", "label": "Status", "type": "dropdown", "required": False, "options": ["Draft", "Published", "Archived"]}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        
        # Create a record
        record_data = {"data": {"title": "Original Title", "status": "Draft"}}
        res = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert res.status_code == 200, f"Record creation failed: {res.text}"
        self.record_id = res.json()["id"]
        created_record_ids.append((self.panel_id, self.record_id))
        
        yield
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_get_single_record(self):
        """GET /api/business-tools/panels/{id}/records/{rid} returns single record"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "record" in data, "Response should contain 'record'"
        assert "panel" in data, "Response should contain 'panel'"
        assert data["record"]["id"] == self.record_id, "Record ID should match"
        assert data["record"]["data"]["title"] == "Original Title", "Title should match"
        print(f"✓ Retrieved single record {self.record_id}")
    
    def test_update_record(self):
        """PUT /api/business-tools/panels/{id}/records/{rid} updates record data"""
        update_data = {
            "data": {
                "title": "Updated Title",
                "status": "Published"
            }
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER)
        data = get_response.json()
        assert data["record"]["data"]["title"] == "Updated Title", "Title should be updated"
        assert data["record"]["data"]["status"] == "Published", "Status should be updated"
        print(f"✓ Updated record {self.record_id}")
    
    def test_delete_record(self):
        """DELETE /api/business-tools/panels/{id}/records/{rid} deletes a record"""
        # Create a record to delete
        record_data = {"data": {"title": "To Be Deleted", "status": "Draft"}}
        create_res = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        delete_record_id = create_res.json()["id"]
        
        # Delete the record
        response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{delete_record_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{delete_record_id}", headers=AUTH_HEADER)
        assert get_response.status_code == 404, "Record should not exist after deletion"
        print(f"✓ Deleted record {delete_record_id}")


class TestRelationLookup:
    """Test relation lookup for inventory and invoices"""
    
    @pytest.fixture(autouse=True)
    def setup_panel(self):
        """Create a test panel for relation lookup testing"""
        panel_data = {
            "name": unique_name("Relation_Panel"),
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "product_link", "label": "Product", "type": "relation", "relatedPanel": "inventory", "relationType": "many_to_one"},
                {"key": "invoice_link", "label": "Invoice", "type": "relation", "relatedPanel": "invoices", "relationType": "many_to_one"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        yield
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_relation_lookup_inventory(self):
        """GET /api/business-tools/panels/{id}/relation-lookup?target=inventory returns product list"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/relation-lookup?target=inventory", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should contain 'results'"
        assert isinstance(data["results"], list), "Results should be a list"
        
        # Check result structure if there are products
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result, "Result should have 'id'"
            assert "label" in result, "Result should have 'label'"
            print(f"✓ Inventory lookup returned {len(data['results'])} products")
        else:
            print("✓ Inventory lookup returned 0 products (empty inventory)")
    
    def test_relation_lookup_invoices(self):
        """GET /api/business-tools/panels/{id}/relation-lookup?target=invoices returns invoice list"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/relation-lookup?target=invoices", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should contain 'results'"
        assert isinstance(data["results"], list), "Results should be a list"
        
        # Check result structure if there are invoices
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result, "Result should have 'id'"
            assert "label" in result, "Result should have 'label'"
            print(f"✓ Invoice lookup returned {len(data['results'])} invoices")
        else:
            print("✓ Invoice lookup returned 0 invoices (no invoices)")
    
    def test_relation_lookup_with_search(self):
        """Relation lookup supports search parameter"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/relation-lookup?target=inventory&search=test", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should contain 'results'"
        print(f"✓ Inventory lookup with search returned {len(data['results'])} results")


class TestFieldSoftDisable:
    """Test field soft disable functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_panel_with_record(self):
        """Create a test panel with a record for soft disable testing"""
        panel_data = {
            "name": unique_name("Disable_Panel"),
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "old_field", "label": "Old Field", "type": "text", "required": False}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        
        # Create a record with data in old_field
        record_data = {"data": {"name": "Test Item", "old_field": "Some old data"}}
        res = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert res.status_code == 200, f"Record creation failed: {res.text}"
        self.record_id = res.json()["id"]
        created_record_ids.append((self.panel_id, self.record_id))
        
        yield
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_update_field_with_disabled_flag(self):
        """PUT /api/business-tools/panels/{id}/fields/{key} supports disabled flag"""
        # Disable the old_field
        update_data = {"disabled": True}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/old_field", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify field is disabled
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        panel = get_response.json()
        old_field = next((f for f in panel["fields"] if f["key"] == "old_field"), None)
        assert old_field is not None, "old_field should exist"
        assert old_field.get("disabled") == True, "old_field should be disabled"
        print("✓ Field disabled flag set successfully")
    
    def test_update_field_label(self):
        """PUT /api/business-tools/panels/{id}/fields/{key} updates label"""
        update_data = {"label": "Updated Label"}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/name", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify label is updated
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        panel = get_response.json()
        name_field = next((f for f in panel["fields"] if f["key"] == "name"), None)
        assert name_field["label"] == "Updated Label", "Label should be updated"
        print("✓ Field label updated successfully")
    
    def test_update_field_required(self):
        """PUT /api/business-tools/panels/{id}/fields/{key} toggles required"""
        # First make old_field required
        update_data = {"required": True}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/old_field", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify required is set
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        panel = get_response.json()
        old_field = next((f for f in panel["fields"] if f["key"] == "old_field"), None)
        assert old_field["required"] == True, "Field should be required"
        print("✓ Field required flag toggled successfully")
    
    def test_update_dropdown_options(self):
        """PUT /api/business-tools/panels/{id}/fields/{key} updates options"""
        # First add a dropdown field
        add_field = {"key": "priority", "label": "Priority", "type": "dropdown", "options": ["Low", "Medium", "High"]}
        requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields", headers=AUTH_HEADER, json=add_field)
        
        # Update options
        update_data = {"options": ["Low", "Medium", "High", "Critical"]}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/priority", headers=AUTH_HEADER, json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify options are updated
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        panel = get_response.json()
        priority_field = next((f for f in panel["fields"] if f["key"] == "priority"), None)
        assert "Critical" in priority_field["options"], "Options should include 'Critical'"
        print("✓ Dropdown options updated successfully")


class TestFieldDeletionProtection:
    """Test field deletion is blocked when records have data"""
    
    @pytest.fixture(autouse=True)
    def setup_panel_with_record(self):
        """Create a test panel with a record for deletion protection testing"""
        panel_data = {
            "name": unique_name("DeleteProtect_Panel"),
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "field_with_data", "label": "Field With Data", "type": "text", "required": False},
                {"key": "empty_field", "label": "Empty Field", "type": "text", "required": False}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert response.status_code == 200, f"Panel creation failed: {response.text}"
        self.panel_id = response.json()["id"]
        created_panel_ids.append(self.panel_id)
        
        # Create a record with data in field_with_data but not in empty_field
        record_data = {"data": {"name": "Test Item", "field_with_data": "Important data"}}
        res = requests.post(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records", headers=AUTH_HEADER, json=record_data)
        assert res.status_code == 200, f"Record creation failed: {res.text}"
        self.record_id = res.json()["id"]
        created_record_ids.append((self.panel_id, self.record_id))
        
        yield
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/records/{self.record_id}", headers=AUTH_HEADER)
            requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        except:
            pass
    
    def test_delete_field_blocked_when_records_have_data(self):
        """DELETE /api/business-tools/panels/{id}/fields/{key} blocks deletion when records have data"""
        response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/field_with_data", headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for field with data, got {response.status_code}: {response.text}"
        assert "disable" in response.json().get("detail", "").lower() or "data" in response.json().get("detail", "").lower(), \
            "Error should mention disabling or data protection"
        print("✓ Field deletion correctly blocked when records have data")
    
    def test_delete_empty_field_allowed(self):
        """DELETE /api/business-tools/panels/{id}/fields/{key} allows deletion of empty field"""
        response = requests.delete(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}/fields/empty_field", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200 for empty field deletion, got {response.status_code}: {response.text}"
        
        # Verify field is deleted
        get_response = requests.get(f"{BASE_URL}/api/business-tools/panels/{self.panel_id}", headers=AUTH_HEADER)
        panel = get_response.json()
        field_keys = [f["key"] for f in panel["fields"]]
        assert "empty_field" not in field_keys, "empty_field should be deleted"
        print("✓ Empty field deletion allowed")


class TestFullLifecycle:
    """Test full lifecycle: create panel → add fields → create records → update → search → delete"""
    
    def test_full_panel_record_lifecycle(self):
        """Full lifecycle test - create panel, add fields, create records, update, search, delete"""
        # 1. Create panel
        panel_data = {
            "name": unique_name("Lifecycle_Panel"),
            "description": "Full lifecycle test panel",
            "fields": [
                {"key": "item_name", "label": "Item Name", "type": "text", "required": True},
                {"key": "quantity", "label": "Quantity", "type": "number", "required": False}
            ]
        }
        create_res = requests.post(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER, json=panel_data)
        assert create_res.status_code == 200, f"Panel creation failed: {create_res.text}"
        panel_id = create_res.json()["id"]
        created_panel_ids.append(panel_id)
        print(f"  1. Created panel: {panel_id}")
        
        try:
            # 2. Add a new field
            add_field = {"key": "status", "label": "Status", "type": "dropdown", "options": ["New", "In Progress", "Done"]}
            add_res = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields", headers=AUTH_HEADER, json=add_field)
            assert add_res.status_code == 200, f"Add field failed: {add_res.text}"
            print("  2. Added status field")
            
            # 3. Create records
            records_data = [
                {"data": {"item_name": "Widget A", "quantity": 100, "status": "New"}},
                {"data": {"item_name": "Widget B", "quantity": 50, "status": "In Progress"}},
                {"data": {"item_name": "Gadget C", "quantity": 75, "status": "Done"}}
            ]
            record_ids = []
            for rec in records_data:
                rec_res = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", headers=AUTH_HEADER, json=rec)
                assert rec_res.status_code == 200, f"Record creation failed: {rec_res.text}"
                record_ids.append(rec_res.json()["id"])
                created_record_ids.append((panel_id, rec_res.json()["id"]))
            print(f"  3. Created {len(record_ids)} records")
            
            # 4. List records
            list_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", headers=AUTH_HEADER)
            assert list_res.status_code == 200, f"List records failed: {list_res.text}"
            assert list_res.json()["total"] == 3, "Should have 3 records"
            print("  4. Listed records (total: 3)")
            
            # 5. Search records
            search_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records?search=Widget", headers=AUTH_HEADER)
            assert search_res.status_code == 200, f"Search failed: {search_res.text}"
            assert len(search_res.json()["records"]) == 2, "Should find 2 Widget records"
            print("  5. Search for 'Widget' returned 2 records")
            
            # 6. Update a record
            update_res = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_ids[0]}", 
                                      headers=AUTH_HEADER, json={"data": {"item_name": "Widget A Updated", "quantity": 150, "status": "Done"}})
            assert update_res.status_code == 200, f"Update failed: {update_res.text}"
            print("  6. Updated first record")
            
            # 7. Verify update
            get_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_ids[0]}", headers=AUTH_HEADER)
            assert get_res.json()["record"]["data"]["item_name"] == "Widget A Updated", "Record should be updated"
            print("  7. Verified update")
            
            # 8. Soft disable a field
            disable_res = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields/quantity", 
                                       headers=AUTH_HEADER, json={"disabled": True})
            assert disable_res.status_code == 200, f"Disable field failed: {disable_res.text}"
            print("  8. Soft disabled 'quantity' field")
            
            # 9. Try to delete field with data (should fail)
            delete_field_res = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/fields/item_name", headers=AUTH_HEADER)
            assert delete_field_res.status_code == 400, "Should not be able to delete field with data"
            print("  9. Field deletion correctly blocked (has data)")
            
            # 10. Delete a record
            delete_rec_res = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_ids[2]}", headers=AUTH_HEADER)
            assert delete_rec_res.status_code == 200, f"Delete record failed: {delete_rec_res.text}"
            print("  10. Deleted third record")
            
            # 11. Verify record count
            final_list = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", headers=AUTH_HEADER)
            assert final_list.json()["total"] == 2, "Should have 2 records after deletion"
            print("  11. Verified 2 records remaining")
            
            print("✓ Full lifecycle test completed successfully")
        finally:
            # Cleanup
            try:
                records_res = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", headers=AUTH_HEADER)
                if records_res.status_code == 200:
                    for rec in records_res.json().get("records", []):
                        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{rec['id']}", headers=AUTH_HEADER)
                requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
            except:
                pass


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_records_and_panels(self):
        """Clean up all TEST_ prefixed panels and their records"""
        cleanup_test_panels()
        print("✓ Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
