"""
Test HSN Code feature in Sales Reports for CA compliance
- Tests GET /api/business-tools/reports/product-sales returns hsnCode, gstPercent, totalGst, taxableValue
- Tests GET /api/business-tools/reports/product-performance returns hsnCode 
- Tests GET /api/business-tools/export/sales includes HSN Code column
- Tests GET /api/business-tools/export/product-performance includes HSN Code column
- Regression tests for existing report endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_TOKEN = "dev-test-token"  # Used by previous testing iterations

class TestProductSalesHSN:
    """Test product-sales endpoint returns HSN and GST fields"""
    
    def test_product_sales_returns_200(self):
        """Basic connectivity test"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "products" in data, "Response should contain 'products' key"
        print(f"PASS: product-sales returns 200 with {len(data.get('products', []))} products")

    def test_product_sales_has_hsn_field(self):
        """Verify hsnCode field exists in each product"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        # Even if empty, structure should be valid
        for product in products:
            assert "hsnCode" in product, f"Product missing 'hsnCode' field: {product}"
            # hsnCode can be empty string if not set
            assert isinstance(product["hsnCode"], str), f"hsnCode should be string: {product}"
        
        print(f"PASS: All {len(products)} products have hsnCode field")

    def test_product_sales_has_gst_fields(self):
        """Verify gstPercent, totalGst, taxableValue fields exist"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        for product in products:
            # Check all GST-related fields exist
            assert "gstPercent" in product, f"Product missing 'gstPercent': {product}"
            assert "totalGst" in product, f"Product missing 'totalGst': {product}"
            assert "taxableValue" in product, f"Product missing 'taxableValue': {product}"
            
            # Type checks
            assert isinstance(product["gstPercent"], (int, float)), f"gstPercent should be numeric: {product}"
            assert isinstance(product["totalGst"], (int, float)), f"totalGst should be numeric: {product}"
            assert isinstance(product["taxableValue"], (int, float)), f"taxableValue should be numeric: {product}"
        
        print(f"PASS: All {len(products)} products have gstPercent, totalGst, taxableValue fields")

    def test_product_sales_taxable_value_calculation(self):
        """Verify taxableValue = totalRevenue - totalGst"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        for product in products:
            revenue = product.get("totalRevenue", 0)
            gst = product.get("totalGst", 0)
            taxable = product.get("taxableValue", 0)
            
            # taxableValue should be revenue - gst (with some floating point tolerance)
            expected_taxable = round(revenue - gst, 2)
            assert abs(taxable - expected_taxable) < 0.01, \
                f"taxableValue mismatch: {taxable} != {expected_taxable} (revenue={revenue}, gst={gst})"
        
        print(f"PASS: taxableValue calculation correct for all {len(products)} products")

    def test_product_sales_full_structure(self):
        """Verify complete response structure with all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        expected_fields = ["productName", "hsnCode", "totalQuantity", "taxableValue", 
                          "gstPercent", "totalGst", "totalRevenue", "invoiceCount"]
        
        for product in products:
            for field in expected_fields:
                assert field in product, f"Product missing field '{field}': {product.keys()}"
        
        print(f"PASS: All {len(products)} products have complete structure with {len(expected_fields)} fields")


class TestProductPerformanceHSN:
    """Test product-performance endpoint returns HSN field"""
    
    def test_product_performance_returns_200(self):
        """Basic connectivity test"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-performance",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        print(f"PASS: product-performance returns 200 with {len(data.get('items', []))} items")

    def test_product_performance_has_hsn_field(self):
        """Verify hsnCode field exists in each product performance item"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-performance",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            assert "hsnCode" in item, f"Item missing 'hsnCode' field: {item}"
            assert isinstance(item["hsnCode"], str), f"hsnCode should be string: {item}"
        
        # Also check topSelling and slowMoving arrays
        for item in data.get("topSelling", []):
            assert "hsnCode" in item, f"topSelling item missing hsnCode: {item}"
        
        for item in data.get("slowMoving", []):
            assert "hsnCode" in item, f"slowMoving item missing hsnCode: {item}"
        
        print(f"PASS: All product-performance items have hsnCode field")

    def test_product_performance_full_structure(self):
        """Verify complete response structure"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-performance",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level structure
        assert "summary" in data, "Response missing 'summary'"
        assert "items" in data, "Response missing 'items'"
        assert "topSelling" in data, "Response missing 'topSelling'"
        assert "slowMoving" in data, "Response missing 'slowMoving'"
        assert "pagination" in data, "Response missing 'pagination'"
        
        expected_item_fields = ["productName", "hsnCode", "quantitySold", "revenue", 
                               "profit", "profitPercent", "invoiceCount"]
        
        for item in data.get("items", []):
            for field in expected_item_fields:
                assert field in item, f"Item missing field '{field}': {item.keys()}"
        
        print("PASS: product-performance has complete structure with hsnCode in items")


class TestSalesExportHSN:
    """Test sales export includes HSN Code column"""
    
    def test_export_sales_csv_returns_200(self):
        """Export sales as CSV works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", "")
        print("PASS: export/sales CSV returns 200")

    def test_export_sales_has_hsn_header(self):
        """Verify HSN column is in the CSV headers"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        content = response.text
        lines = content.strip().split('\n')
        assert len(lines) > 0, "CSV should have at least header row"
        
        header_line = lines[0]
        # Check for HSN column (case insensitive match)
        headers_lower = header_line.lower()
        assert "hsn" in headers_lower, f"CSV headers missing HSN column: {header_line}"
        
        print(f"PASS: export/sales CSV has HSN column. Headers: {header_line}")

    def test_export_sales_has_gst_percent_header(self):
        """Verify GST % column is in the CSV headers"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        content = response.text
        lines = content.strip().split('\n')
        header_line = lines[0]
        
        # Check for GST % column
        assert "gst" in header_line.lower(), f"CSV headers missing GST column: {header_line}"
        
        print(f"PASS: export/sales CSV has GST columns. Headers: {header_line}")

    def test_export_sales_expected_column_order(self):
        """Verify expected columns in sales export"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        content = response.text
        lines = content.strip().split('\n')
        header_line = lines[0]
        
        # Expected headers from export_import_router.py line 136
        expected_headers = ["Invoice No", "Date", "Buyer Name", "GSTIN", "Product", 
                          "HSN", "Qty", "Rate", "Taxable Amount", "GST %", 
                          "CGST", "SGST", "IGST", "Total Amount", "Payment Status"]
        
        for expected in expected_headers:
            assert expected.lower() in header_line.lower(), \
                f"CSV missing expected column '{expected}'. Headers: {header_line}"
        
        print(f"PASS: export/sales CSV has all {len(expected_headers)} expected columns")


class TestProductPerformanceExportHSN:
    """Test product-performance export includes HSN Code column"""
    
    def test_export_product_performance_returns_200(self):
        """Export product-performance as CSV works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/product-performance?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: export/product-performance CSV returns 200")

    def test_export_product_performance_has_hsn_header(self):
        """Verify HSN Code column is in the CSV headers"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/product-performance?format=csv",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        content = response.text
        lines = content.strip().split('\n')
        header_line = lines[0]
        
        # Check for HSN column
        assert "hsn" in header_line.lower(), f"CSV headers missing HSN column: {header_line}"
        
        # Expected headers from export_import_router.py line 619
        expected_headers = ["Product Name", "HSN Code", "Quantity Sold", "Revenue", "Profit", "Profit %"]
        for expected in expected_headers:
            assert expected.lower() in header_line.lower(), \
                f"Missing column '{expected}'. Headers: {header_line}"
        
        print(f"PASS: export/product-performance CSV has HSN Code column. Headers: {header_line}")


class TestRegressionExistingReports:
    """Regression tests for existing report endpoints still working"""
    
    def test_outstanding_report(self):
        """Outstanding report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Outstanding failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: outstanding report works")

    def test_purchase_report(self):
        """Purchase report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Purchase failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        print("PASS: purchase report works")

    def test_stock_movement_report(self):
        """Stock movement report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Stock movement failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        print("PASS: stock-movement report works")

    def test_buyer_ledger_report(self):
        """Buyer ledger report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/buyer-ledger",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Buyer ledger failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        print("PASS: buyer-ledger report works")

    def test_category_report(self):
        """Category report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/category-report",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Category failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        print("PASS: category-report works")

    def test_low_stock_report(self):
        """Low stock analytics still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/low-stock-analytics",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Low stock failed: {response.status_code}"
        data = response.json()
        assert "summary" in data
        print("PASS: low-stock-analytics works")

    def test_overview_report(self):
        """Overview report still works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/overview",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Overview failed: {response.status_code}"
        data = response.json()
        # Check all 8 fields from Phase 3
        expected_fields = ["totalOutstanding", "outstandingCount", "overdueInvoices", 
                          "lowStockCount", "topProduct", "monthlySales", 
                          "monthlyInvoiceCount", "growthPercentage"]
        for field in expected_fields:
            assert field in data, f"Overview missing field: {field}"
        print("PASS: overview report works with all 8 fields")


class TestAuthRequired:
    """Test that endpoints require authentication"""
    
    def test_product_sales_requires_auth(self):
        """product-sales requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/product-sales")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("PASS: product-sales requires auth")

    def test_product_performance_requires_auth(self):
        """product-performance requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/product-performance")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("PASS: product-performance requires auth")

    def test_export_sales_requires_auth(self):
        """export/sales requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/sales")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("PASS: export/sales requires auth")

    def test_export_product_performance_requires_auth(self):
        """export/product-performance requires auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/export/product-performance")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("PASS: export/product-performance requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
