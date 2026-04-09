"""
Phase 3 Reports Testing - Business Insights Overview Widget
Tests the new GET /api/business-tools/reports/overview endpoint that powers
the Business Insights dashboard widget on the Business Tools dashboard.

Tests:
1. Overview endpoint returns correct 8-field structure
2. totalOutstanding (sum of pending amounts for outstanding invoices)
3. outstandingCount (count of outstanding invoices)
4. overdueInvoices (90+ days overdue count)
5. lowStockCount (products below minimum stock)
6. topProduct (name, qtySold, revenue)
7. monthlySales (this month total)
8. monthlyInvoiceCount (this month count)
9. growthPercentage (vs last month)
10. Regression tests for Phase 1 & 2 endpoints
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Use public URL from environment for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-emp-mgmt.preview.emergentagent.com')
AUTH_TOKEN = "dev-test-token"

def get_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}

def get_date_params():
    """Return date range for last 365 days"""
    end = datetime.utcnow()
    start = end - timedelta(days=365)
    return f"startDate={start.isoformat()}&endDate={end.isoformat()}"


class TestOverviewEndpoint:
    """Tests for GET /api/business-tools/reports/overview - Business Insights widget API"""
    
    def test_overview_returns_200(self):
        """Test overview endpoint returns 200"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Overview endpoint returns 200")
    
    def test_overview_has_all_8_fields(self):
        """Test overview returns all 8 required fields"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        
        # All 8 required fields from PRD
        required_fields = [
            "totalOutstanding",
            "outstandingCount",
            "overdueInvoices",
            "lowStockCount",
            "topProduct",
            "monthlySales",
            "monthlyInvoiceCount",
            "growthPercentage"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"PASS: All 8 fields present - {list(data.keys())}")
    
    def test_overview_total_outstanding_is_number(self):
        """Test totalOutstanding is a number (sum of pending amounts)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("totalOutstanding"), (int, float)), "totalOutstanding should be a number"
        assert data.get("totalOutstanding") >= 0, "totalOutstanding should be non-negative"
        print(f"PASS: totalOutstanding = {data['totalOutstanding']}")
    
    def test_overview_outstanding_count_is_integer(self):
        """Test outstandingCount is an integer (count of outstanding invoices)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("outstandingCount"), int), "outstandingCount should be an integer"
        assert data.get("outstandingCount") >= 0, "outstandingCount should be non-negative"
        print(f"PASS: outstandingCount = {data['outstandingCount']}")
    
    def test_overview_overdue_invoices_is_integer(self):
        """Test overdueInvoices is an integer (90+ days overdue count)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("overdueInvoices"), int), "overdueInvoices should be an integer"
        assert data.get("overdueInvoices") >= 0, "overdueInvoices should be non-negative"
        print(f"PASS: overdueInvoices = {data['overdueInvoices']}")
    
    def test_overview_low_stock_count_is_integer(self):
        """Test lowStockCount is an integer (products below min stock)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("lowStockCount"), int), "lowStockCount should be an integer"
        assert data.get("lowStockCount") >= 0, "lowStockCount should be non-negative"
        print(f"PASS: lowStockCount = {data['lowStockCount']}")
    
    def test_overview_top_product_structure(self):
        """Test topProduct has name, qtySold, revenue fields"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        top_product = data.get("topProduct")
        assert isinstance(top_product, dict), "topProduct should be an object"
        
        # name can be null if no sales this month
        assert "name" in top_product, "topProduct should have 'name' field"
        assert "qtySold" in top_product, "topProduct should have 'qtySold' field"
        assert "revenue" in top_product, "topProduct should have 'revenue' field"
        
        # qtySold and revenue should be numbers
        assert isinstance(top_product.get("qtySold"), (int, float)), "qtySold should be a number"
        assert isinstance(top_product.get("revenue"), (int, float)), "revenue should be a number"
        
        print(f"PASS: topProduct = {top_product}")
    
    def test_overview_monthly_sales_is_number(self):
        """Test monthlySales is a number (this month total)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("monthlySales"), (int, float)), "monthlySales should be a number"
        assert data.get("monthlySales") >= 0, "monthlySales should be non-negative"
        print(f"PASS: monthlySales = {data['monthlySales']}")
    
    def test_overview_monthly_invoice_count_is_integer(self):
        """Test monthlyInvoiceCount is an integer"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("monthlyInvoiceCount"), int), "monthlyInvoiceCount should be an integer"
        assert data.get("monthlyInvoiceCount") >= 0, "monthlyInvoiceCount should be non-negative"
        print(f"PASS: monthlyInvoiceCount = {data['monthlyInvoiceCount']}")
    
    def test_overview_growth_percentage_is_number(self):
        """Test growthPercentage is a number (can be negative)"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert isinstance(data.get("growthPercentage"), (int, float)), "growthPercentage should be a number"
        # Growth can be negative (decline) so no non-negative check
        print(f"PASS: growthPercentage = {data['growthPercentage']}%")
    
    def test_overview_requires_auth(self):
        """Test overview endpoint requires authentication"""
        url = f"{BASE_URL}/api/business-tools/reports/overview"
        response = requests.get(url)  # No auth header
        # Should return 401 or 422 (missing header)
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("PASS: Endpoint requires authentication")


class TestPhase1RegressionWithPhase3:
    """Verify Phase 1 reports still work after Phase 3 additions"""
    
    def test_outstanding_report_still_works(self):
        """Test outstanding report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/outstanding?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "summary" in data
        assert "aging" in data
        assert "items" in data
        assert "pagination" in data
        print("PASS: Outstanding report still works")
    
    def test_purchase_report_still_works(self):
        """Test purchase report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/purchase?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Purchase report still works")
    
    def test_stock_movement_still_works(self):
        """Test stock movement report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/stock-movement?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Stock movement report still works")


class TestPhase2RegressionWithPhase3:
    """Verify Phase 2 reports still work after Phase 3 additions"""
    
    def test_buyer_ledger_still_works(self):
        """Test buyer ledger report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Buyer ledger still works")
    
    def test_product_performance_still_works(self):
        """Test product performance report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "topSelling" in data
        assert "slowMoving" in data
        print("PASS: Product performance still works")
    
    def test_category_report_still_works(self):
        """Test category report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/category-report?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Category report still works")
    
    def test_low_stock_analytics_still_works(self):
        """Test low stock analytics report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Low stock analytics still works")


class TestOriginalReportsRegression:
    """Verify original report endpoints still work"""
    
    def test_sales_summary(self):
        """Test sales summary still works"""
        url = f"{BASE_URL}/api/business-tools/reports/sales-summary?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "periods" in data
        print("PASS: Sales summary still works")
    
    def test_profit_summary(self):
        """Test profit summary still works"""
        url = f"{BASE_URL}/api/business-tools/reports/profit-summary?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        print("PASS: Profit summary still works")
    
    def test_inventory_status(self):
        """Test inventory status still works"""
        url = f"{BASE_URL}/api/business-tools/reports/inventory-status"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Inventory status still works")
    
    def test_top_buyers(self):
        """Test top buyers still works"""
        url = f"{BASE_URL}/api/business-tools/reports/top-buyers?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "buyers" in data
        print("PASS: Top buyers still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
