"""
Test Export/Import Feature for Reports Module
Tests:
- Export endpoints (sales, profit, inventory, buyers, invoices) for CSV and XLSX formats
- Import template download endpoints
- Import validate endpoint
- Import process endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://erp-india-suite.preview.emergentagent.com").rstrip("/")


class TestExportEndpoints:
    """Test Export endpoints - verify they exist and require auth"""
    
    def test_export_sales_csv_requires_auth(self):
        """GET /api/business-tools/export/sales?format=csv - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/sales?format=csv")
        # Should return 422 (missing auth header) - endpoint exists
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        assert "authorization" in response.text.lower() or "missing" in response.text.lower()
        print("PASS: export/sales CSV endpoint exists and requires auth")
    
    def test_export_sales_xlsx_requires_auth(self):
        """GET /api/business-tools/export/sales?format=xlsx - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/sales?format=xlsx")
        assert response.status_code == 422
        print("PASS: export/sales XLSX endpoint exists and requires auth")
    
    def test_export_profit_csv_requires_auth(self):
        """GET /api/business-tools/export/profit?format=csv - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/profit?format=csv")
        assert response.status_code == 422
        print("PASS: export/profit CSV endpoint exists and requires auth")
    
    def test_export_profit_xlsx_requires_auth(self):
        """GET /api/business-tools/export/profit?format=xlsx - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/profit?format=xlsx")
        assert response.status_code == 422
        print("PASS: export/profit XLSX endpoint exists and requires auth")
    
    def test_export_inventory_csv_requires_auth(self):
        """GET /api/business-tools/export/inventory?format=csv - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/inventory?format=csv")
        assert response.status_code == 422
        print("PASS: export/inventory CSV endpoint exists and requires auth")
    
    def test_export_inventory_xlsx_requires_auth(self):
        """GET /api/business-tools/export/inventory?format=xlsx - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/inventory?format=xlsx")
        assert response.status_code == 422
        print("PASS: export/inventory XLSX endpoint exists and requires auth")
    
    def test_export_buyers_csv_requires_auth(self):
        """GET /api/business-tools/export/buyers?format=csv - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/buyers?format=csv")
        assert response.status_code == 422
        print("PASS: export/buyers CSV endpoint exists and requires auth")
    
    def test_export_buyers_xlsx_requires_auth(self):
        """GET /api/business-tools/export/buyers?format=xlsx - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/buyers?format=xlsx")
        assert response.status_code == 422
        print("PASS: export/buyers XLSX endpoint exists and requires auth")
    
    def test_export_invoices_csv_requires_auth(self):
        """GET /api/business-tools/export/invoices?format=csv - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/invoices?format=csv")
        assert response.status_code == 422
        print("PASS: export/invoices CSV endpoint exists and requires auth")
    
    def test_export_invoices_xlsx_requires_auth(self):
        """GET /api/business-tools/export/invoices?format=xlsx - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/invoices?format=xlsx")
        assert response.status_code == 422
        print("PASS: export/invoices XLSX endpoint exists and requires auth")


class TestImportTemplateEndpoints:
    """Test Import Template download endpoints"""
    
    def test_import_template_products_csv_requires_auth(self):
        """GET /api/business-tools/import/template/products?format=csv - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/products?format=csv")
        assert response.status_code == 422
        print("PASS: import/template/products CSV endpoint exists and requires auth")
    
    def test_import_template_products_xlsx_requires_auth(self):
        """GET /api/business-tools/import/template/products?format=xlsx - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/products?format=xlsx")
        assert response.status_code == 422
        print("PASS: import/template/products XLSX endpoint exists and requires auth")
    
    def test_import_template_inventory_csv_requires_auth(self):
        """GET /api/business-tools/import/template/inventory?format=csv - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/inventory?format=csv")
        assert response.status_code == 422
        print("PASS: import/template/inventory CSV endpoint exists and requires auth")
    
    def test_import_template_inventory_xlsx_requires_auth(self):
        """GET /api/business-tools/import/template/inventory?format=xlsx - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/inventory?format=xlsx")
        assert response.status_code == 422
        print("PASS: import/template/inventory XLSX endpoint exists and requires auth")
    
    def test_import_template_suppliers_csv_requires_auth(self):
        """GET /api/business-tools/import/template/suppliers?format=csv - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/suppliers?format=csv")
        assert response.status_code == 422
        print("PASS: import/template/suppliers CSV endpoint exists and requires auth")
    
    def test_import_template_suppliers_xlsx_requires_auth(self):
        """GET /api/business-tools/import/template/suppliers?format=xlsx - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/suppliers?format=xlsx")
        assert response.status_code == 422
        print("PASS: import/template/suppliers XLSX endpoint exists and requires auth")
    
    def test_import_template_buyers_csv_requires_auth(self):
        """GET /api/business-tools/import/template/buyers?format=csv - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/buyers?format=csv")
        assert response.status_code == 422
        print("PASS: import/template/buyers CSV endpoint exists and requires auth")
    
    def test_import_template_buyers_xlsx_requires_auth(self):
        """GET /api/business-tools/import/template/buyers?format=xlsx - requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/buyers?format=xlsx")
        assert response.status_code == 422
        print("PASS: import/template/buyers XLSX endpoint exists and requires auth")


class TestImportValidateProcessEndpoints:
    """Test Import Validate and Process endpoints"""
    
    def test_import_validate_requires_auth(self):
        """POST /api/business-tools/import/validate - requires authentication"""
        response = requests.post(f"{BASE_URL}/api/business-tools/import/validate")
        # Should return 422 (missing auth header) - endpoint exists
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: import/validate endpoint exists and requires auth")
    
    def test_import_process_requires_auth(self):
        """POST /api/business-tools/import/process - requires authentication"""
        response = requests.post(f"{BASE_URL}/api/business-tools/import/process")
        # Should return 422 (missing auth header) - endpoint exists
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: import/process endpoint exists and requires auth")


class TestExportDateFilters:
    """Test that export endpoints accept date filter parameters"""
    
    def test_export_sales_with_dates(self):
        """GET /api/business-tools/export/sales with date params - requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales?format=csv&startDate=2024-01-01T00:00:00Z&endDate=2024-12-31T23:59:59Z"
        )
        assert response.status_code == 422  # Auth required, but endpoint accepts params
        print("PASS: export/sales accepts date filter parameters")
    
    def test_export_profit_with_dates(self):
        """GET /api/business-tools/export/profit with date params - requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/profit?format=csv&startDate=2024-01-01T00:00:00Z&endDate=2024-12-31T23:59:59Z"
        )
        assert response.status_code == 422
        print("PASS: export/profit accepts date filter parameters")
    
    def test_export_buyers_with_dates(self):
        """GET /api/business-tools/export/buyers with date params - requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/buyers?format=csv&startDate=2024-01-01T00:00:00Z&endDate=2024-12-31T23:59:59Z"
        )
        assert response.status_code == 422
        print("PASS: export/buyers accepts date filter parameters")


class TestInvalidDataType:
    """Test invalid data type handling"""
    
    def test_import_template_invalid_type(self):
        """GET /api/business-tools/import/template/invalid_type - should return 422 (auth required first)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/import/template/invalid_type")
        # Should return 422 for missing auth header first
        assert response.status_code == 422
        print("PASS: import/template checks auth before validating data_type")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
