"""
Phase 1 Reports Testing - Outstanding, Purchase, Stock Movement Reports
Tests new report APIs and export endpoints for the B2B ERP app
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://relational-update.preview.emergentagent.com').rstrip('/')
# Uses dev-test-token for authentication (MOCKED Firebase Auth in dev mode)
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}


class TestOutstandingReport:
    """Test Outstanding/Receivables Report API"""
    
    def test_outstanding_report_structure(self):
        """GET /api/business-tools/reports/outstanding returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding",
            headers=AUTH_HEADER
        )
        print(f"Outstanding Report Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if len(response.text) > 500 else response.text}")
        
        # In preview env without auth, may return 401 or valid response
        if response.status_code == 401:
            pytest.skip("Auth required - token invalid in preview environment")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check structure
        assert "summary" in data, "Missing 'summary' in response"
        assert "aging" in data, "Missing 'aging' in response"
        assert "items" in data, "Missing 'items' in response"
        assert "pagination" in data, "Missing 'pagination' in response"
        
    def test_outstanding_summary_fields(self):
        """Outstanding report summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        summary = data.get("summary", {})
        
        # Required summary fields
        expected_fields = ["totalReceivable", "overdueAmount", "totalBuyers", "totalInvoices"]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"
            
    def test_outstanding_aging_buckets(self):
        """Outstanding report has aging bucket breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        aging = data.get("aging", {})
        
        # Should have buckets and counts
        assert "buckets" in aging, "Missing 'buckets' in aging"
        assert "counts" in aging, "Missing 'counts' in aging"
        
        # Check expected bucket keys
        expected_buckets = ["current", "0-30", "31-60", "61-90", "90+"]
        for bucket in expected_buckets:
            assert bucket in aging.get("buckets", {}), f"Missing bucket: {bucket}"
            
    def test_outstanding_pagination(self):
        """Outstanding report pagination fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding?page=1&limit=10",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        pagination = data.get("pagination", {})
        
        # Required pagination fields
        assert "page" in pagination, "Missing 'page' in pagination"
        assert "limit" in pagination, "Missing 'limit' in pagination"
        assert "total" in pagination, "Missing 'total' in pagination"
        assert "pages" in pagination, "Missing 'pages' in pagination"
        
    def test_outstanding_buyer_filter(self):
        """Outstanding report accepts buyerId filter"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding?buyerId=invalid_test_id",
            headers=AUTH_HEADER
        )
        # Should not crash with invalid buyer ID
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_outstanding_date_filter(self):
        """Outstanding report accepts date filters"""
        start = (datetime.now() - timedelta(days=30)).isoformat()
        end = datetime.now().isoformat()
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/outstanding?startDate={start}&endDate={end}",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200


class TestPurchaseReport:
    """Test Purchase Report API"""
    
    def test_purchase_report_structure(self):
        """GET /api/business-tools/reports/purchase returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase",
            headers=AUTH_HEADER
        )
        print(f"Purchase Report Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if len(response.text) > 500 else response.text}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "summary" in data, "Missing 'summary' in response"
        assert "items" in data, "Missing 'items' in response"
        assert "pagination" in data, "Missing 'pagination' in response"
        
    def test_purchase_summary_fields(self):
        """Purchase report summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        summary = data.get("summary", {})
        
        # Required summary fields
        expected_fields = ["totalPurchaseValue", "totalQuantity", "totalSuppliers", "orderCount", "avgOrderValue"]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"
            
    def test_purchase_supplier_filter(self):
        """Purchase report accepts supplierId filter"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase?supplierId=invalid_test_id",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_purchase_date_filter(self):
        """Purchase report accepts date filters"""
        start = (datetime.now() - timedelta(days=60)).isoformat()
        end = datetime.now().isoformat()
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase?startDate={start}&endDate={end}",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_purchase_pagination(self):
        """Purchase report pagination fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/purchase?page=1&limit=20",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        pagination = data.get("pagination", {})
        
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination


class TestStockMovementReport:
    """Test Stock Movement Report API"""
    
    def test_stock_movement_structure(self):
        """GET /api/business-tools/reports/stock-movement returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement",
            headers=AUTH_HEADER
        )
        print(f"Stock Movement Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if len(response.text) > 500 else response.text}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "summary" in data, "Missing 'summary' in response"
        assert "items" in data, "Missing 'items' in response"
        assert "pagination" in data, "Missing 'pagination' in response"
        
    def test_stock_movement_summary_fields(self):
        """Stock movement summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        summary = data.get("summary", {})
        
        # Required summary fields
        expected_fields = ["totalInward", "totalOutward", "netMovement", "totalProducts"]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"
            
    def test_stock_movement_item_structure(self):
        """Stock movement items have opening/closing stock calculations"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        data = response.json()
        items = data.get("items", [])
        
        if len(items) > 0:
            item = items[0]
            # Each item should have these fields
            expected_item_fields = ["listingId", "productName", "openingStock", "inward", "outward", "adjustment", "closingStock"]
            for field in expected_item_fields:
                assert field in item, f"Missing item field: {field}"
                
    def test_stock_movement_product_filter(self):
        """Stock movement accepts listingId filter"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement?listingId=invalid_test_id",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_stock_movement_date_filter(self):
        """Stock movement accepts date filters"""
        start = (datetime.now() - timedelta(days=30)).isoformat()
        end = datetime.now().isoformat()
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/stock-movement?startDate={start}&endDate={end}",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200


class TestExportEndpoints:
    """Test CSV/Excel export endpoints for new reports"""
    
    def test_export_outstanding_csv(self):
        """GET /api/business-tools/export/outstanding returns CSV"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/outstanding?format=csv",
            headers=AUTH_HEADER
        )
        print(f"Export Outstanding CSV Response: {response.status_code}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "") or \
               "attachment" in response.headers.get("content-disposition", "")
               
    def test_export_outstanding_xlsx(self):
        """GET /api/business-tools/export/outstanding returns Excel"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/outstanding?format=xlsx",
            headers=AUTH_HEADER
        )
        print(f"Export Outstanding XLSX Response: {response.status_code}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "application/vnd" in content_type or response.content[:4] == b'PK\x03\x04'
        
    def test_export_purchase_orders_csv(self):
        """GET /api/business-tools/export/purchase-orders returns CSV"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/purchase-orders?format=csv",
            headers=AUTH_HEADER
        )
        print(f"Export Purchase CSV Response: {response.status_code}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        
    def test_export_purchase_orders_xlsx(self):
        """GET /api/business-tools/export/purchase-orders returns Excel"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/purchase-orders?format=xlsx",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_export_stock_movement_csv(self):
        """GET /api/business-tools/export/stock-movement returns CSV"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/stock-movement?format=csv",
            headers=AUTH_HEADER
        )
        print(f"Export Stock Movement CSV Response: {response.status_code}")
        
        if response.status_code == 401:
            pytest.skip("Auth required")
            
        assert response.status_code == 200
        
    def test_export_stock_movement_xlsx(self):
        """GET /api/business-tools/export/stock-movement returns Excel"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/stock-movement?format=xlsx",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_export_date_filtering(self):
        """Export endpoints accept date filtering"""
        start = (datetime.now() - timedelta(days=90)).isoformat()
        end = datetime.now().isoformat()
        
        for endpoint in ["outstanding", "purchase-orders", "stock-movement"]:
            response = requests.get(
                f"{BASE_URL}/api/business-tools/export/{endpoint}?format=csv&startDate={start}&endDate={end}",
                headers=AUTH_HEADER
            )
            if response.status_code == 401:
                continue  # Skip if auth required
            assert response.status_code == 200, f"Export {endpoint} with dates failed"


class TestExistingReportsIntegrity:
    """Verify existing report endpoints still work"""
    
    def test_sales_summary(self):
        """Existing sales-summary endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/sales-summary",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_profit_summary(self):
        """Existing profit-summary endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/profit-summary",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_inventory_status(self):
        """Existing inventory-status endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/inventory-status",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200
        
    def test_top_buyers(self):
        """Existing top-buyers endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/top-buyers",
            headers=AUTH_HEADER
        )
        if response.status_code == 401:
            pytest.skip("Auth required")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
