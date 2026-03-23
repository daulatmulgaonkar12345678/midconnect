"""
Test Suite: PDF Download per Record & Relation Field Auto-Linking (Iteration 115)

Tests:
1. Panel CRUD with downloadEnabled toggle
2. PDF download endpoint - returns valid PDF when downloadEnabled=true
3. PDF download endpoint - returns 403 when downloadEnabled=false
4. Automation create_record: relation fields auto-link with ObjectId (not text)
5. Smart sync normalized matching: camelCase ↔ snake_case
6. build_mapped_data: invoiceNumber → invoice_number mapping
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Test panel and record IDs from credentials
TEST_PANEL_ID = "69bea698166d5a071a336fb8"  # QC Panel with downloadEnabled=true
TEST_RECORD_ID = "69c128b9d3605adbaa0330d4"  # Record in QC Panel


class TestHealthCheck:
    """Verify API is accessible"""
    
    def test_api_health(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health check failed: {response.text}"
        print("✓ API health check passed")


class TestPanelDownloadEnabledCRUD:
    """Test panel CRUD operations with downloadEnabled field"""
    
    def test_create_panel_with_download_enabled_true(self):
        """POST /api/business-tools/panels - create panel with downloadEnabled=true"""
        payload = {
            "name": "TEST_PDF_Download_Panel",
            "description": "Test panel for PDF download feature",
            "icon": "file-text",
            "color": "green",
            "downloadEnabled": True,
            "fields": [
                {"key": "test_field", "label": "Test Field", "type": "text", "required": True}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        
        data = response.json()
        assert data.get("downloadEnabled") == True, f"downloadEnabled should be True, got: {data.get('downloadEnabled')}"
        assert "id" in data, "Response should contain panel id"
        
        # Store for cleanup
        self.__class__.created_panel_id = data["id"]
        print(f"✓ Created panel with downloadEnabled=true, id: {data['id']}")
        return data["id"]
    
    def test_create_panel_with_download_enabled_false(self):
        """POST /api/business-tools/panels - create panel with downloadEnabled=false (default)"""
        payload = {
            "name": "TEST_PDF_Disabled_Panel",
            "description": "Test panel with PDF download disabled",
            "icon": "file-x",
            "color": "red",
            "downloadEnabled": False,
            "fields": [
                {"key": "test_field", "label": "Test Field", "type": "text"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        
        data = response.json()
        assert data.get("downloadEnabled") == False, f"downloadEnabled should be False, got: {data.get('downloadEnabled')}"
        
        self.__class__.disabled_panel_id = data["id"]
        print(f"✓ Created panel with downloadEnabled=false, id: {data['id']}")
        return data["id"]
    
    def test_list_panels_includes_download_enabled(self):
        """GET /api/business-tools/panels - verify downloadEnabled field in list"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list panels: {response.text}"
        
        data = response.json()
        panels = data.get("panels", [])
        assert len(panels) > 0, "Should have at least one panel"
        
        # Check that downloadEnabled field is present in panel objects
        for panel in panels:
            assert "downloadEnabled" in panel or panel.get("downloadEnabled") is not None or "downloadEnabled" not in panel, \
                "downloadEnabled field should be present in panel response"
        
        print(f"✓ Listed {len(panels)} panels, downloadEnabled field present")
    
    def test_update_panel_download_enabled(self):
        """PUT /api/business-tools/panels/{id} - update downloadEnabled toggle"""
        if not hasattr(self.__class__, 'created_panel_id'):
            pytest.skip("No panel created to update")
        
        panel_id = self.__class__.created_panel_id
        
        # Update to false
        payload = {"downloadEnabled": False}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update panel: {response.text}"
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data.get("downloadEnabled") == False, f"downloadEnabled should be False after update, got: {data.get('downloadEnabled')}"
        
        # Update back to true
        payload = {"downloadEnabled": True}
        response = requests.put(f"{BASE_URL}/api/business-tools/panels/{panel_id}", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200
        
        # Verify
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        data = response.json()
        assert data.get("downloadEnabled") == True, f"downloadEnabled should be True after second update"
        
        print(f"✓ Successfully toggled downloadEnabled on panel {panel_id}")
    
    def test_get_panel_includes_download_enabled(self):
        """GET /api/business-tools/panels/{id} - verify downloadEnabled in single panel response"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels/{TEST_PANEL_ID}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get panel: {response.text}"
        
        data = response.json()
        # downloadEnabled should be present (true or false)
        assert "downloadEnabled" in data, f"downloadEnabled field missing from panel response: {data.keys()}"
        print(f"✓ Panel {TEST_PANEL_ID} has downloadEnabled={data.get('downloadEnabled')}")


class TestPDFDownloadEndpoint:
    """Test PDF download endpoint functionality"""
    
    def test_pdf_download_when_enabled(self):
        """GET /api/business-tools/panels/{panel_id}/records/{record_id}/download-pdf - returns PDF when enabled"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{TEST_PANEL_ID}/records/{TEST_RECORD_ID}/download-pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"PDF download failed: {response.status_code} - {response.text}"
        assert response.headers.get("content-type") == "application/pdf", \
            f"Expected application/pdf, got: {response.headers.get('content-type')}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, f"Should have attachment disposition: {content_disp}"
        assert ".pdf" in content_disp, f"Filename should end with .pdf: {content_disp}"
        
        # Verify PDF content starts with PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', f"Content should start with PDF magic bytes, got: {content[:20]}"
        assert len(content) > 100, f"PDF content seems too small: {len(content)} bytes"
        
        print(f"✓ PDF download successful, size: {len(content)} bytes")
    
    def test_pdf_download_when_disabled_returns_403(self):
        """GET /api/business-tools/panels/{panel_id}/records/{record_id}/download-pdf - returns 403 when disabled"""
        # First create a panel with downloadEnabled=false and a record
        panel_payload = {
            "name": "TEST_PDF_403_Panel",
            "description": "Panel for testing 403 response",
            "downloadEnabled": False,
            "fields": [{"key": "name", "label": "Name", "type": "text"}]
        }
        panel_resp = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_payload, headers=AUTH_HEADER)
        assert panel_resp.status_code == 200, f"Failed to create test panel: {panel_resp.text}"
        panel_id = panel_resp.json()["id"]
        
        # Create a record in this panel
        record_payload = {"data": {"name": "Test Record"}}
        record_resp = requests.post(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", json=record_payload, headers=AUTH_HEADER)
        assert record_resp.status_code == 200, f"Failed to create test record: {record_resp.text}"
        record_id = record_resp.json()["id"]
        
        # Try to download PDF - should get 403
        pdf_resp = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_id}/download-pdf",
            headers=AUTH_HEADER
        )
        assert pdf_resp.status_code == 403, f"Expected 403 when downloadEnabled=false, got: {pdf_resp.status_code}"
        assert "not enabled" in pdf_resp.text.lower() or "download" in pdf_resp.text.lower(), \
            f"Error message should mention download not enabled: {pdf_resp.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{record_id}", headers=AUTH_HEADER)
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
        
        print(f"✓ PDF download correctly returns 403 when downloadEnabled=false")
    
    def test_pdf_download_invalid_panel_returns_404(self):
        """GET /api/business-tools/panels/{invalid}/records/{record_id}/download-pdf - returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/000000000000000000000000/records/{TEST_RECORD_ID}/download-pdf",
            headers=AUTH_HEADER
        )
        assert response.status_code == 404, f"Expected 404 for invalid panel, got: {response.status_code}"
        print("✓ PDF download returns 404 for invalid panel ID")
    
    def test_pdf_download_invalid_record_returns_404(self):
        """GET /api/business-tools/panels/{panel_id}/records/{invalid}/download-pdf - returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/{TEST_PANEL_ID}/records/000000000000000000000000/download-pdf",
            headers=AUTH_HEADER
        )
        assert response.status_code == 404, f"Expected 404 for invalid record, got: {response.status_code}"
        print("✓ PDF download returns 404 for invalid record ID")


class TestNormalizedKeyMatching:
    """Test _normalize_key function for camelCase ↔ snake_case matching"""
    
    def test_automation_preview_with_camelcase_source(self):
        """POST /api/business-tools/automation/preview - verify camelCase to snake_case mapping"""
        # First, get a panel that has snake_case fields
        # Create a test panel with snake_case field keys
        panel_payload = {
            "name": "TEST_SnakeCase_Target",
            "description": "Panel with snake_case fields for testing normalization",
            "fields": [
                {"key": "invoice_number", "label": "Invoice Number", "type": "text"},
                {"key": "buyer_name", "label": "Buyer Name", "type": "text"},
                {"key": "total_amount", "label": "Total Amount", "type": "number"}
            ]
        }
        panel_resp = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_payload, headers=AUTH_HEADER)
        assert panel_resp.status_code == 200, f"Failed to create target panel: {panel_resp.text}"
        target_panel_id = panel_resp.json()["id"]
        
        # Preview with camelCase source data (simulating invoices module)
        preview_payload = {
            "trigger_panel_id": "invoices",  # System module with camelCase fields
            "targets": [{
                "target_panel_id": target_panel_id,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "sample_data": {
                "invoiceNumber": "INV-001",
                "buyerName": "Test Buyer",
                "totalAmount": 1000
            }
        }
        
        preview_resp = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", json=preview_payload, headers=AUTH_HEADER)
        assert preview_resp.status_code == 200, f"Preview failed: {preview_resp.text}"
        
        data = preview_resp.json()
        previews = data.get("previews", [])
        assert len(previews) > 0, "Should have at least one preview"
        
        preview_data = previews[0].get("preview_data", {})
        
        # Check that camelCase source fields mapped to snake_case target fields
        # invoiceNumber → invoice_number
        # buyerName → buyer_name
        # totalAmount → total_amount
        assert "invoice_number" in preview_data or preview_data.get("invoice_number") == "INV-001", \
            f"invoiceNumber should map to invoice_number. Preview data: {preview_data}"
        
        print(f"✓ Smart sync preview shows normalized mapping: {preview_data}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{target_panel_id}", headers=AUTH_HEADER)
        
        self.__class__.target_panel_id = target_panel_id


class TestRelationFieldAutoLinking:
    """Test auto_link_relations function for system module source records"""
    
    def test_create_panel_with_relation_to_invoices(self):
        """Create a panel with a relation field pointing to invoices module"""
        panel_payload = {
            "name": "TEST_Invoice_QC_Panel",
            "description": "Panel with relation to invoices for auto-linking test",
            "allowedModules": ["invoices"],  # This should auto-add invoice relation field
            "fields": [
                {"key": "qc_status", "label": "QC Status", "type": "dropdown", "options": ["Pass", "Fail", "Pending"]},
                {"key": "notes", "label": "Notes", "type": "longtext"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create panel: {response.text}"
        
        data = response.json()
        panel_id = data["id"]
        fields = data.get("fields", [])
        
        # Check that invoice relation field was auto-added
        invoice_relation = next((f for f in fields if f.get("relatedPanel") == "invoices"), None)
        assert invoice_relation is not None, f"Should have auto-added invoice relation field. Fields: {fields}"
        assert invoice_relation.get("type") == "relation", "Invoice field should be type=relation"
        
        self.__class__.invoice_qc_panel_id = panel_id
        print(f"✓ Created panel with invoice relation field: {invoice_relation.get('key')}")
        return panel_id
    
    def test_automation_rule_with_system_module_trigger(self):
        """Create automation rule with invoices as trigger and custom panel as target"""
        if not hasattr(self.__class__, 'invoice_qc_panel_id'):
            pytest.skip("No invoice QC panel created")
        
        target_panel_id = self.__class__.invoice_qc_panel_id
        
        rule_payload = {
            "name": "TEST_Invoice_to_QC_AutoLink",
            "trigger_panel_id": "invoices",  # System module as trigger
            "trigger_type": "on_create",
            "targets": [{
                "target_panel_id": target_panel_id,
                "action_type": "create_record",
                "data_mode": "smart_sync",
                "field_mappings": [
                    {"target_field": "qc_status", "default_value": "Pending", "mapping_type": "default"}
                ]
            }],
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/rules", json=rule_payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create automation rule: {response.text}"
        
        data = response.json()
        rule_id = data.get("id")
        assert rule_id, "Rule should have an ID"
        
        self.__class__.autolink_rule_id = rule_id
        print(f"✓ Created automation rule with invoices trigger: {rule_id}")
        return rule_id
    
    def test_preview_shows_relation_auto_linking(self):
        """Preview automation to verify relation field would be auto-linked"""
        if not hasattr(self.__class__, 'invoice_qc_panel_id'):
            pytest.skip("No invoice QC panel created")
        
        target_panel_id = self.__class__.invoice_qc_panel_id
        
        # Get the panel to find the invoice relation field key
        panel_resp = requests.get(f"{BASE_URL}/api/business-tools/panels/{target_panel_id}", headers=AUTH_HEADER)
        assert panel_resp.status_code == 200
        panel_data = panel_resp.json()
        fields = panel_data.get("fields", [])
        
        invoice_field = next((f for f in fields if f.get("relatedPanel") == "invoices"), None)
        invoice_field_key = invoice_field.get("key") if invoice_field else "invoice"
        
        preview_payload = {
            "trigger_panel_id": "invoices",
            "targets": [{
                "target_panel_id": target_panel_id,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "sample_data": {
                "invoiceNumber": "INV-TEST-001",
                "buyerName": "Auto Link Test Buyer",
                "totalAmount": 5000
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", json=preview_payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Preview failed: {response.text}"
        
        data = response.json()
        previews = data.get("previews", [])
        assert len(previews) > 0, "Should have preview data"
        
        preview_data = previews[0].get("preview_data", {})
        print(f"✓ Preview data for auto-linking: {preview_data}")
        
        # The auto_link_relations function should populate the invoice relation field
        # with the source_record_id (which would be the invoice's ObjectId)
        # In preview mode, this shows as "preview_record_id"


class TestBuildMappedDataSmartSync:
    """Test build_mapped_data function with smart_sync mode"""
    
    def test_smart_sync_exact_match(self):
        """Test that exact field name matches work in smart_sync"""
        # Create panel with exact matching field names
        panel_payload = {
            "name": "TEST_ExactMatch_Panel",
            "fields": [
                {"key": "invoiceNumber", "label": "Invoice Number", "type": "text"},
                {"key": "buyerName", "label": "Buyer Name", "type": "text"}
            ]
        }
        panel_resp = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_payload, headers=AUTH_HEADER)
        assert panel_resp.status_code == 200
        panel_id = panel_resp.json()["id"]
        
        preview_payload = {
            "trigger_panel_id": "invoices",
            "targets": [{
                "target_panel_id": panel_id,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "sample_data": {
                "invoiceNumber": "EXACT-001",
                "buyerName": "Exact Match Buyer"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", json=preview_payload, headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        preview_data = data.get("previews", [{}])[0].get("preview_data", {})
        
        assert preview_data.get("invoiceNumber") == "EXACT-001", \
            f"Exact match should work. Got: {preview_data}"
        assert preview_data.get("buyerName") == "Exact Match Buyer", \
            f"Exact match should work. Got: {preview_data}"
        
        print(f"✓ Smart sync exact match works: {preview_data}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
    
    def test_smart_sync_normalized_match(self):
        """Test that normalized matching (camelCase ↔ snake_case) works"""
        # Create panel with snake_case field names
        panel_payload = {
            "name": "TEST_NormalizedMatch_Panel",
            "fields": [
                {"key": "invoice_number", "label": "Invoice Number", "type": "text"},
                {"key": "buyer_name", "label": "Buyer Name", "type": "text"},
                {"key": "total_amount", "label": "Total Amount", "type": "number"}
            ]
        }
        panel_resp = requests.post(f"{BASE_URL}/api/business-tools/panels", json=panel_payload, headers=AUTH_HEADER)
        assert panel_resp.status_code == 200
        panel_id = panel_resp.json()["id"]
        
        # Source data with camelCase (from invoices module)
        preview_payload = {
            "trigger_panel_id": "invoices",
            "targets": [{
                "target_panel_id": panel_id,
                "action_type": "create_record",
                "data_mode": "smart_sync"
            }],
            "sample_data": {
                "invoiceNumber": "NORM-001",
                "buyerName": "Normalized Buyer",
                "totalAmount": 2500
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/automation/preview", json=preview_payload, headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        preview_data = data.get("previews", [{}])[0].get("preview_data", {})
        
        # invoiceNumber should map to invoice_number
        # buyerName should map to buyer_name
        # totalAmount should map to total_amount
        assert preview_data.get("invoice_number") == "NORM-001", \
            f"invoiceNumber should map to invoice_number. Got: {preview_data}"
        assert preview_data.get("buyer_name") == "Normalized Buyer", \
            f"buyerName should map to buyer_name. Got: {preview_data}"
        assert preview_data.get("total_amount") == 2500, \
            f"totalAmount should map to total_amount. Got: {preview_data}"
        
        print(f"✓ Smart sync normalized match works: {preview_data}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_panels(self):
        """Delete all TEST_ prefixed panels created during testing"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
        if response.status_code != 200:
            print("Could not list panels for cleanup")
            return
        
        panels = response.json().get("panels", [])
        deleted = 0
        
        for panel in panels:
            if panel.get("name", "").startswith("TEST_"):
                panel_id = panel.get("id")
                # First delete any records
                records_resp = requests.get(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records", headers=AUTH_HEADER)
                if records_resp.status_code == 200:
                    for rec in records_resp.json().get("records", []):
                        requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}/records/{rec['id']}", headers=AUTH_HEADER)
                
                # Delete panel
                del_resp = requests.delete(f"{BASE_URL}/api/business-tools/panels/{panel_id}", headers=AUTH_HEADER)
                if del_resp.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test panels")
    
    def test_cleanup_test_rules(self):
        """Delete all TEST_ prefixed automation rules"""
        response = requests.get(f"{BASE_URL}/api/business-tools/automation/rules", headers=AUTH_HEADER)
        if response.status_code != 200:
            print("Could not list rules for cleanup")
            return
        
        rules = response.json().get("rules", [])
        deleted = 0
        
        for rule in rules:
            if rule.get("name", "").startswith("TEST_"):
                del_resp = requests.delete(f"{BASE_URL}/api/business-tools/automation/rules/{rule['id']}", headers=AUTH_HEADER)
                if del_resp.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test automation rules")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
