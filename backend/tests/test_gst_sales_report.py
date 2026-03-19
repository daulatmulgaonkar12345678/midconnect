"""
GST Sales Report (GSTR-1 Compatible) - Backend API Tests
Tests for the new GST Report endpoint and Excel export functionality

Features tested:
1. GET /api/business-tools/reports/gst-report endpoint
2. B2B/B2C classification based on GSTIN
3. GST split (CGST/SGST vs IGST) based on interstate/intrastate
4. HSN Summary aggregation
5. Filters: gstType, buyerId, date range
6. GET /api/business-tools/export/gst-report Excel export
7. Regression: existing report endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Dev test token for seller auth
AUTH_HEADERS = {"Authorization": "Bearer dev-test-token"}


class TestGstReportBasic:
    """Basic GST report endpoint tests"""

    def test_gst_report_endpoint_exists(self):
        """Test that GST report endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"GST report endpoint failed: {response.status_code} {response.text[:200]}"

    def test_gst_report_returns_required_fields(self):
        """Test that GST report returns all required fields in response"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check summary fields
        assert "summary" in data, "Missing 'summary' in response"
        summary = data["summary"]
        assert "b2b" in summary, "Missing 'b2b' in summary"
        assert "b2c" in summary, "Missing 'b2c' in summary"
        assert "totalInvoices" in summary, "Missing 'totalInvoices' in summary"
        assert "totalTaxable" in summary, "Missing 'totalTaxable' in summary"
        assert "totalGst" in summary, "Missing 'totalGst' in summary"
        assert "totalValue" in summary, "Missing 'totalValue' in summary"
        
        # Check hsnSummary
        assert "hsnSummary" in data, "Missing 'hsnSummary' in response"
        assert isinstance(data["hsnSummary"], list), "hsnSummary should be a list"
        
        # Check items
        assert "items" in data, "Missing 'items' in response"
        assert isinstance(data["items"], list), "items should be a list"
        
        # Check pagination
        assert "pagination" in data, "Missing 'pagination' in response"

    def test_gst_report_b2b_b2c_breakdown(self):
        """Test that B2B/B2C breakdown has correct fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        # B2B breakdown fields
        b2b = data["summary"]["b2b"]
        assert "count" in b2b, "Missing 'count' in b2b"
        assert "taxable" in b2b, "Missing 'taxable' in b2b"
        assert "gst" in b2b, "Missing 'gst' in b2b"
        assert "total" in b2b, "Missing 'total' in b2b"
        
        # B2C breakdown fields
        b2c = data["summary"]["b2c"]
        assert "count" in b2c, "Missing 'count' in b2c"
        assert "taxable" in b2c, "Missing 'taxable' in b2c"
        assert "gst" in b2c, "Missing 'gst' in b2c"
        assert "total" in b2c, "Missing 'total' in b2c"


class TestGstReportInvoiceFields:
    """Test invoice-level data fields"""

    def test_invoice_items_have_required_fields(self):
        """Test that invoice items have all required GSTR-1 fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = [
                "invoiceId", "invoiceNumber", "invoiceDate", "buyerName",
                "placeOfSupply", "isB2B", "taxableValue", 
                "cgst", "sgst", "igst", "totalInvoiceValue"
            ]
            for field in required_fields:
                assert field in item, f"Missing '{field}' in invoice item"
            
            # Check buyerGstin is present (can be empty for B2C)
            assert "buyerGstin" in item, "Missing 'buyerGstin' in invoice item"
            
            # Check numeric types
            assert isinstance(item["taxableValue"], (int, float)), "taxableValue should be numeric"
            assert isinstance(item["cgst"], (int, float)), "cgst should be numeric"
            assert isinstance(item["sgst"], (int, float)), "sgst should be numeric"
            assert isinstance(item["igst"], (int, float)), "igst should be numeric"
            assert isinstance(item["totalInvoiceValue"], (int, float)), "totalInvoiceValue should be numeric"
            assert isinstance(item["isB2B"], bool), "isB2B should be boolean"

    def test_gst_split_logic_intrastate(self):
        """Test CGST+SGST for intrastate (not both IGST and CGST/SGST)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            cgst = item.get("cgst", 0)
            sgst = item.get("sgst", 0)
            igst = item.get("igst", 0)
            
            # Either CGST+SGST or IGST, not both (one side should be 0)
            if cgst > 0 or sgst > 0:
                assert igst == 0, f"Invoice {item['invoiceNumber']}: Has CGST/SGST but also IGST (should be 0)"
            if igst > 0:
                assert cgst == 0 and sgst == 0, f"Invoice {item['invoiceNumber']}: Has IGST but also CGST/SGST (should be 0)"


class TestGstReportHsnSummary:
    """Test HSN Summary aggregation"""

    def test_hsn_summary_fields(self):
        """Test HSN summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["hsnSummary"]) > 0:
            hsn_item = data["hsnSummary"][0]
            required_fields = [
                "hsnCode", "description", "uqc", "quantity",
                "taxableValue", "cgst", "sgst", "igst"
            ]
            for field in required_fields:
                assert field in hsn_item, f"Missing '{field}' in HSN summary item"
            
            # Check numeric types
            assert isinstance(hsn_item["quantity"], (int, float)), "quantity should be numeric"
            assert isinstance(hsn_item["taxableValue"], (int, float)), "taxableValue should be numeric"


class TestGstReportFilters:
    """Test GST report filters"""

    def test_gst_type_filter_b2b(self):
        """Test gstType=b2b returns only B2B invoices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report?gstType=b2b",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item["isB2B"] == True, f"Invoice {item['invoiceNumber']} is not B2B but returned with gstType=b2b"

    def test_gst_type_filter_b2c(self):
        """Test gstType=b2c returns only B2C invoices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report?gstType=b2c",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item["isB2B"] == False, f"Invoice {item['invoiceNumber']} is B2B but returned with gstType=b2c"

    def test_date_range_filter(self):
        """Test date range filtering"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report?startDate=2024-01-01&endDate=2024-12-31",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        # Just checking endpoint works with date params
        assert "items" in data

    def test_buyer_filter(self):
        """Test buyer filtering works (no error)"""
        # First get a buyer ID
        buyers_response = requests.get(
            f"{BASE_URL}/api/business-tools/buyers?limit=1",
            headers=AUTH_HEADERS
        )
        if buyers_response.status_code == 200:
            buyers = buyers_response.json().get("buyers", [])
            if buyers:
                buyer_id = buyers[0].get("_id") or buyers[0].get("id")
                if buyer_id:
                    response = requests.get(
                        f"{BASE_URL}/api/business-tools/reports/gst-report?buyerId={buyer_id}",
                        headers=AUTH_HEADERS
                    )
                    assert response.status_code == 200, f"Buyer filter failed: {response.text[:200]}"


class TestGstReportExcelExport:
    """Test GST Report Excel Export"""

    def test_gst_export_endpoint_exists(self):
        """Test that GST export endpoint returns Excel file"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"GST export endpoint failed: {response.status_code}"
        
        # Check content type is Excel
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type.lower() or "excel" in content_type.lower() or "officedocument" in content_type.lower(), \
            f"Expected Excel content-type, got: {content_type}"

    def test_gst_export_has_filename(self):
        """Test that export has proper filename header"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "filename=" in content_disposition or "attachment" in content_disposition, \
            f"Expected filename in Content-Disposition, got: {content_disposition}"

    def test_gst_export_with_filters(self):
        """Test GST export with gstType filter"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/gst-report?gstType=b2b",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200


class TestGstReportValidation:
    """Test GSTIN validation and classification"""

    def test_b2b_classification_with_gstin(self):
        """Test that invoices with valid GSTIN are classified as B2B"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            if item.get("buyerGstin"):
                # If GSTIN is present (valid), should be B2B
                assert item["isB2B"] == True, f"Invoice {item['invoiceNumber']} has GSTIN but isB2B is False"
            # Note: Empty GSTIN means B2C

    def test_cancelled_invoices_excluded(self):
        """Test that cancelled invoices are excluded from GST report"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/gst-report",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item.get("status") != "cancelled", \
                f"Invoice {item['invoiceNumber']} is cancelled but included in GST report"
            assert item.get("status") != "draft", \
                f"Invoice {item['invoiceNumber']} is draft but included in GST report"


class TestRegressionReportEndpoints:
    """Regression tests for existing report endpoints"""

    def test_outstanding_report_works(self):
        """Regression: Outstanding report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"Outstanding report failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        assert "items" in data

    def test_sales_summary_report_works(self):
        """Regression: Sales summary still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/sales-summary",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"Sales summary failed: {response.status_code}"
        data = response.json()
        assert "overall" in data
        assert "periods" in data

    def test_product_sales_report_works(self):
        """Regression: Product sales still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"Product sales failed: {response.status_code}"
        data = response.json()
        assert "products" in data

    def test_reports_overview_works(self):
        """Regression: Reports overview still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/overview",
            headers=AUTH_HEADERS
        )
        assert response.status_code == 200, f"Reports overview failed: {response.status_code}"


class TestGstReportAuthRequired:
    """Test that GST report requires authentication"""

    def test_gst_report_requires_auth(self):
        """Test that GST report returns 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/gst-report")
        assert response.status_code in [401, 422], \
            f"GST report should require auth, got: {response.status_code}"

    def test_gst_export_requires_auth(self):
        """Test that GST export returns 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/gst-report")
        assert response.status_code in [401, 422], \
            f"GST export should require auth, got: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
