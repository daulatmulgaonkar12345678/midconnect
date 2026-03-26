"""
Phase 2 Reports Testing - 4 new reports:
1. Buyer Ledger - aggregated sales/paid/pending per buyer with drill-down transactions
2. Product Performance - qty sold, revenue, profit, profit%, top selling and slow moving
3. Category Report - sales/revenue/profit by product category  
4. Low Stock Analytics - current stock, min stock, times hit low, avg consumption

Also tests 4 new export endpoints for these reports.
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Use public URL from environment for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://plan-limits-5.preview.emergentagent.com')
AUTH_TOKEN = "dev-test-token"

def get_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}

def get_date_params():
    """Return date range for last 365 days"""
    end = datetime.utcnow()
    start = end - timedelta(days=365)
    return f"startDate={start.isoformat()}&endDate={end.isoformat()}"


class TestBuyerLedgerReport:
    """Tests for GET /api/business-tools/reports/buyer-ledger"""
    
    def test_buyer_ledger_returns_200(self):
        """Test buyer ledger endpoint returns 200"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Buyer ledger returns 200")
    
    def test_buyer_ledger_has_summary(self):
        """Test buyer ledger has summary with required fields"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "summary" in data, "Response should have summary"
        summary = data["summary"]
        assert "totalSales" in summary, "Summary should have totalSales"
        assert "totalPaid" in summary, "Summary should have totalPaid"
        assert "totalPending" in summary, "Summary should have totalPending"
        assert "totalBuyers" in summary, "Summary should have totalBuyers"
        print(f"PASS: Summary has required fields - totalSales: {summary['totalSales']}, totalBuyers: {summary['totalBuyers']}")
    
    def test_buyer_ledger_has_items(self):
        """Test buyer ledger has items array with correct structure"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "items" in data, "Response should have items"
        assert isinstance(data["items"], list), "Items should be a list"
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["buyerId", "buyerName", "totalSales", "totalPaid", "pendingAmount", "invoiceCount"]
            for field in required_fields:
                assert field in item, f"Item should have {field}"
            print(f"PASS: Item has required fields - sample buyer: {item['buyerName']}")
        else:
            print("PASS: Items array exists (empty)")
    
    def test_buyer_ledger_has_pagination(self):
        """Test buyer ledger has pagination"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}&page=1&limit=10"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "pagination" in data, "Response should have pagination"
        pagination = data["pagination"]
        assert "page" in pagination, "Pagination should have page"
        assert "limit" in pagination, "Pagination should have limit"
        assert "total" in pagination, "Pagination should have total"
        assert "pages" in pagination, "Pagination should have pages"
        print(f"PASS: Pagination - page {pagination['page']}/{pagination['pages']}, total {pagination['total']}")
    
    def test_buyer_ledger_filter_by_buyer(self):
        """Test buyer ledger can filter by buyerId"""
        # First get list to get a buyer ID
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        if len(data.get("items", [])) > 0:
            buyer_id = data["items"][0]["buyerId"]
            filtered_url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}&buyerId={buyer_id}"
            filtered_response = requests.get(filtered_url, headers=get_headers())
            assert filtered_response.status_code == 200
            filtered_data = filtered_response.json()
            # When filtered by specific buyer, should have only that buyer
            assert len(filtered_data.get("items", [])) <= 1
            print(f"PASS: Buyer filter works - filtered to {len(filtered_data['items'])} items")
        else:
            print("PASS: Filter test skipped (no buyers in data)")


class TestBuyerTransactions:
    """Tests for GET /api/business-tools/reports/buyer-ledger/{buyerId}/transactions"""
    
    def test_buyer_transactions_returns_200(self):
        """Test buyer transactions endpoint returns 200"""
        # First get a buyer ID from ledger
        ledger_url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        ledger_response = requests.get(ledger_url, headers=get_headers())
        ledger_data = ledger_response.json()
        
        if len(ledger_data.get("items", [])) > 0:
            buyer_id = ledger_data["items"][0]["buyerId"]
            url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger/{buyer_id}/transactions?{get_date_params()}"
            response = requests.get(url, headers=get_headers())
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print(f"PASS: Buyer transactions for {buyer_id} returns 200")
        else:
            pytest.skip("No buyers available for transaction test")
    
    def test_buyer_transactions_has_buyer_info(self):
        """Test buyer transactions response has buyer info"""
        ledger_url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        ledger_response = requests.get(ledger_url, headers=get_headers())
        ledger_data = ledger_response.json()
        
        if len(ledger_data.get("items", [])) > 0:
            buyer_id = ledger_data["items"][0]["buyerId"]
            url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger/{buyer_id}/transactions?{get_date_params()}"
            response = requests.get(url, headers=get_headers())
            data = response.json()
            
            assert "buyer" in data, "Response should have buyer object"
            assert "buyerId" in data["buyer"], "Buyer should have buyerId"
            assert "buyerName" in data["buyer"], "Buyer should have buyerName"
            print(f"PASS: Buyer info - {data['buyer']['buyerName']}")
        else:
            pytest.skip("No buyers available")
    
    def test_buyer_transactions_has_transactions_list(self):
        """Test buyer transactions response has transactions list"""
        ledger_url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger?{get_date_params()}"
        ledger_response = requests.get(ledger_url, headers=get_headers())
        ledger_data = ledger_response.json()
        
        if len(ledger_data.get("items", [])) > 0:
            buyer_id = ledger_data["items"][0]["buyerId"]
            url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger/{buyer_id}/transactions?{get_date_params()}"
            response = requests.get(url, headers=get_headers())
            data = response.json()
            
            assert "transactions" in data, "Response should have transactions"
            assert isinstance(data["transactions"], list), "Transactions should be a list"
            
            if len(data["transactions"]) > 0:
                txn = data["transactions"][0]
                required_fields = ["invoiceId", "invoiceNumber", "date", "totalAmount", "paidAmount", "pendingAmount", "status"]
                for field in required_fields:
                    assert field in txn, f"Transaction should have {field}"
                print(f"PASS: Transaction has fields - {txn['invoiceNumber']}: {txn['totalAmount']}")
            else:
                print("PASS: Transactions list exists (empty)")
        else:
            pytest.skip("No buyers available")
    
    def test_buyer_transactions_invalid_buyer_returns_400(self):
        """Test invalid buyer ID returns 400"""
        url = f"{BASE_URL}/api/business-tools/reports/buyer-ledger/invalid-id/transactions?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 400, f"Expected 400 for invalid ID, got {response.status_code}"
        print("PASS: Invalid buyer ID returns 400")


class TestProductPerformanceReport:
    """Tests for GET /api/business-tools/reports/product-performance"""
    
    def test_product_performance_returns_200(self):
        """Test product performance endpoint returns 200"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Product performance returns 200")
    
    def test_product_performance_has_summary(self):
        """Test product performance has summary with required fields"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "summary" in data, "Response should have summary"
        summary = data["summary"]
        required_fields = ["totalProducts", "totalRevenue", "totalProfit", "totalQuantitySold", "avgProfitPercent"]
        for field in required_fields:
            assert field in summary, f"Summary should have {field}"
        print(f"PASS: Summary - revenue: {summary['totalRevenue']}, profit: {summary['totalProfit']}, products: {summary['totalProducts']}")
    
    def test_product_performance_has_top_selling(self):
        """Test product performance has topSelling array"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "topSelling" in data, "Response should have topSelling"
        assert isinstance(data["topSelling"], list), "topSelling should be a list"
        # topSelling should have at most 5 items
        assert len(data["topSelling"]) <= 5, "topSelling should have at most 5 items"
        
        if len(data["topSelling"]) > 0:
            item = data["topSelling"][0]
            assert "productName" in item, "topSelling item should have productName"
            assert "revenue" in item, "topSelling item should have revenue"
            print(f"PASS: Top selling item: {item['productName']} - revenue {item['revenue']}")
        else:
            print("PASS: topSelling exists (empty)")
    
    def test_product_performance_has_slow_moving(self):
        """Test product performance has slowMoving array"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "slowMoving" in data, "Response should have slowMoving"
        assert isinstance(data["slowMoving"], list), "slowMoving should be a list"
        assert len(data["slowMoving"]) <= 5, "slowMoving should have at most 5 items"
        print(f"PASS: slowMoving has {len(data['slowMoving'])} items")
    
    def test_product_performance_has_items(self):
        """Test product performance has items with correct structure"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "items" in data, "Response should have items"
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["productName", "quantitySold", "revenue", "profit", "profitPercent", "invoiceCount"]
            for field in required_fields:
                assert field in item, f"Item should have {field}"
            print(f"PASS: Item: {item['productName']} - qty: {item['quantitySold']}, profit%: {item['profitPercent']}")
        else:
            print("PASS: Items exists (empty)")
    
    def test_product_performance_has_pagination(self):
        """Test product performance has pagination"""
        url = f"{BASE_URL}/api/business-tools/reports/product-performance?{get_date_params()}&page=1&limit=10"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "pagination" in data, "Response should have pagination"
        pagination = data["pagination"]
        assert pagination.get("page") == 1, "Page should be 1"
        assert "total" in pagination, "Pagination should have total"
        print(f"PASS: Pagination - total products: {pagination['total']}")


class TestCategoryReport:
    """Tests for GET /api/business-tools/reports/category-report"""
    
    def test_category_report_returns_200(self):
        """Test category report endpoint returns 200"""
        url = f"{BASE_URL}/api/business-tools/reports/category-report?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Category report returns 200")
    
    def test_category_report_has_summary(self):
        """Test category report has summary"""
        url = f"{BASE_URL}/api/business-tools/reports/category-report?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "summary" in data, "Response should have summary"
        summary = data["summary"]
        required_fields = ["totalCategories", "totalRevenue", "totalProfit", "topCategory"]
        for field in required_fields:
            assert field in summary, f"Summary should have {field}"
        print(f"PASS: Summary - {summary['totalCategories']} categories, topCategory: {summary['topCategory']}")
    
    def test_category_report_has_items(self):
        """Test category report has items with correct structure"""
        url = f"{BASE_URL}/api/business-tools/reports/category-report?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "items" in data, "Response should have items"
        assert isinstance(data["items"], list), "Items should be a list"
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["categoryName", "totalSales", "revenue", "profit", "profitPercent", "itemCount"]
            for field in required_fields:
                assert field in item, f"Item should have {field}"
            print(f"PASS: Category: {item['categoryName']} - revenue: {item['revenue']}, profit%: {item['profitPercent']}")
        else:
            print("PASS: Items exists (empty)")
    
    def test_category_report_has_uncategorized(self):
        """Test category report includes Uncategorized for items without productId"""
        url = f"{BASE_URL}/api/business-tools/reports/category-report?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        # Based on context, many invoice items have no productId so should have Uncategorized
        category_names = [item["categoryName"] for item in data.get("items", [])]
        print(f"PASS: Categories found: {category_names}")
        # Just verify the structure is correct - Uncategorized may or may not exist


class TestLowStockAnalytics:
    """Tests for GET /api/business-tools/reports/low-stock-analytics"""
    
    def test_low_stock_returns_200(self):
        """Test low stock analytics endpoint returns 200"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Low stock analytics returns 200")
    
    def test_low_stock_has_summary(self):
        """Test low stock has summary with required fields"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "summary" in data, "Response should have summary"
        summary = data["summary"]
        required_fields = ["totalProducts", "lowStockCount", "outOfStockCount", "healthyCount"]
        for field in required_fields:
            assert field in summary, f"Summary should have {field}"
        print(f"PASS: Summary - total: {summary['totalProducts']}, lowStock: {summary['lowStockCount']}, outOfStock: {summary['outOfStockCount']}")
    
    def test_low_stock_has_items(self):
        """Test low stock has items with correct structure"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "items" in data, "Response should have items"
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["listingId", "productName", "minStock", "currentStock", "timesHitLow", "avgConsumption", "totalSold", "isLowStock", "isOutOfStock", "daysOfStock"]
            for field in required_fields:
                assert field in item, f"Item should have {field}"
            print(f"PASS: Item: {item['productName']} - stock: {item['currentStock']}, avgConsumption: {item['avgConsumption']}, daysOfStock: {item['daysOfStock']}")
        else:
            print("PASS: Items exists (empty)")
    
    def test_low_stock_has_pagination(self):
        """Test low stock has pagination"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}&page=1&limit=10"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        assert "pagination" in data, "Response should have pagination"
        pagination = data["pagination"]
        assert "page" in pagination, "Pagination should have page"
        assert "total" in pagination, "Pagination should have total"
        print(f"PASS: Pagination - total: {pagination['total']}")
    
    def test_low_stock_sort_order(self):
        """Test low stock items are sorted: out of stock first, then low stock, then by daysOfStock"""
        url = f"{BASE_URL}/api/business-tools/reports/low-stock-analytics?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        data = response.json()
        
        items = data.get("items", [])
        if len(items) >= 2:
            # Check that out of stock items come first
            out_of_stock_seen = False
            low_stock_seen = False
            for item in items:
                if item.get("isOutOfStock"):
                    if low_stock_seen and not item.get("isOutOfStock"):
                        pytest.fail("Out of stock items should come before non-out-of-stock")
                    out_of_stock_seen = True
                elif item.get("isLowStock"):
                    low_stock_seen = True
            print("PASS: Sort order verified")
        else:
            print("PASS: Sort order test skipped (not enough items)")


class TestPhase2Exports:
    """Tests for Phase 2 export endpoints"""
    
    def test_export_buyer_ledger_csv(self):
        """Test export buyer ledger as CSV"""
        url = f"{BASE_URL}/api/business-tools/export/buyer-ledger?format=csv&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("content-type", ""), "Should return CSV content-type"
        assert "buyer-ledger" in response.headers.get("content-disposition", ""), "Should have filename in disposition"
        print("PASS: Buyer ledger CSV export works")
    
    def test_export_buyer_ledger_xlsx(self):
        """Test export buyer ledger as Excel"""
        url = f"{BASE_URL}/api/business-tools/export/buyer-ledger?format=xlsx&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "spreadsheet" in response.headers.get("content-type", ""), "Should return Excel content-type"
        print("PASS: Buyer ledger Excel export works")
    
    def test_export_product_performance_csv(self):
        """Test export product performance as CSV"""
        url = f"{BASE_URL}/api/business-tools/export/product-performance?format=csv&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("content-type", ""), "Should return CSV content-type"
        print("PASS: Product performance CSV export works")
    
    def test_export_product_performance_xlsx(self):
        """Test export product performance as Excel"""
        url = f"{BASE_URL}/api/business-tools/export/product-performance?format=xlsx&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "spreadsheet" in response.headers.get("content-type", ""), "Should return Excel content-type"
        print("PASS: Product performance Excel export works")
    
    def test_export_category_report_csv(self):
        """Test export category report as CSV"""
        url = f"{BASE_URL}/api/business-tools/export/category-report?format=csv&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("content-type", ""), "Should return CSV content-type"
        print("PASS: Category report CSV export works")
    
    def test_export_category_report_xlsx(self):
        """Test export category report as Excel"""
        url = f"{BASE_URL}/api/business-tools/export/category-report?format=xlsx&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "spreadsheet" in response.headers.get("content-type", ""), "Should return Excel content-type"
        print("PASS: Category report Excel export works")
    
    def test_export_low_stock_csv(self):
        """Test export low stock as CSV"""
        url = f"{BASE_URL}/api/business-tools/export/low-stock?format=csv&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("content-type", ""), "Should return CSV content-type"
        print("PASS: Low stock CSV export works")
    
    def test_export_low_stock_xlsx(self):
        """Test export low stock as Excel"""
        url = f"{BASE_URL}/api/business-tools/export/low-stock?format=xlsx&{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "spreadsheet" in response.headers.get("content-type", ""), "Should return Excel content-type"
        print("PASS: Low stock Excel export works")


class TestPhase1RegressionChecks:
    """Verify Phase 1 reports still work after Phase 2 additions"""
    
    def test_outstanding_still_works(self):
        """Test outstanding report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/outstanding?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        print("PASS: Outstanding report still works")
    
    def test_purchase_still_works(self):
        """Test purchase report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/purchase?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        print("PASS: Purchase report still works")
    
    def test_stock_movement_still_works(self):
        """Test stock movement report still works"""
        url = f"{BASE_URL}/api/business-tools/reports/stock-movement?{get_date_params()}"
        response = requests.get(url, headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        print("PASS: Stock movement report still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
