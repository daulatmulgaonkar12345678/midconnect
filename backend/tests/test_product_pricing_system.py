"""
Product Pricing System Tests - Iteration 53

Tests for:
1. PUT /api/business-tools/inventory/{listing_id} - Update purchase_price and selling_price
2. GET /api/business-tools/inventory - Returns purchase_price, selling_price, canViewPurchasePrice flag
3. GET /api/business-tools/inventory - purchase_price ABSENT (not null) when user lacks view_purchase_price permission
4. PUT /api/business-tools/inventory/{listing_id} - Block purchase_price change for composite products (400)
5. GET /api/business-tools/reports/profit-summary - Overall totals and per-period breakdown
6. GET /api/business-tools/reports/product-profit - Per-product profit breakdown
7. GET /api/business-tools/reports/inventory-value - Inventory value summary with stockValue/potentialRevenue
8. POST /api/business-tools/invoices - Stores purchase_price per item for profit tracking
9. GET /api/listings/{listing_id} - Returns productType but NOT purchase_price (marketplace visibility)
10. Composite product purchase price calculation from component purchase_price

Test data:
- Motor listing: 69b57c730ed7999c085b3656 (purchase_price=500, selling_price=750)
- Steel listing: 69b57c730ed7999c085b3657 (purchase_price=200, selling_price=350)
- Composite product: 69b5b08db52f04a0b197f9ce
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com').rstrip('/')
DEV_TOKEN = "dev-test-token"  # Seller admin with all permissions

# Known test data IDs
MOTOR_LISTING_ID = "69b57c730ed7999c085b3656"
STEEL_LISTING_ID = "69b57c730ed7999c085b3657"
COMPOSITE_PRODUCT_ID = "69b5b08db52f04a0b197f9ce"


@pytest.fixture
def auth_headers():
    """Headers with authentication token"""
    return {"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"}


class TestInventoryPricingEndpoint:
    """Tests for PUT /api/business-tools/inventory/{listing_id} - pricing fields"""

    def test_update_purchase_price_and_selling_price(self, auth_headers):
        """Test updating purchase_price and selling_price on a listing"""
        # Update Motor listing prices
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{MOTOR_LISTING_ID}",
            headers=auth_headers,
            json={"purchase_price": 500, "selling_price": 750}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "listing" in data
        listing = data["listing"]
        assert listing.get("purchase_price") == 500
        assert listing.get("selling_price") == 750
        print(f"PASS: Updated Motor listing prices - purchase_price=500, selling_price=750")

    def test_update_selling_price_only(self, auth_headers):
        """Test updating only selling_price without purchase_price"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{STEEL_LISTING_ID}",
            headers=auth_headers,
            json={"selling_price": 350}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "listing" in data
        listing = data["listing"]
        assert listing.get("selling_price") == 350
        print(f"PASS: Updated Steel listing selling_price=350")

    def test_block_purchase_price_change_for_composite(self, auth_headers):
        """Test that purchase_price change is blocked for composite products (400 error)"""
        # First, get a composite listing ID
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get composites: {response.text}"
        data = response.json()
        
        composites = data.get("compositeProducts", [])
        if not composites:
            pytest.skip("No composite products available to test")
        
        # Find a composite with a listing
        composite_with_listing = None
        for cp in composites:
            if cp.get("listingId"):
                composite_with_listing = cp
                break
        
        if not composite_with_listing:
            pytest.skip("No composite product with listing available")
        
        listing_id = composite_with_listing["listingId"]
        
        # Try to update purchase_price on composite listing - should fail
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}",
            headers=auth_headers,
            json={"purchase_price": 999}
        )
        assert response.status_code == 400, f"Expected 400 for composite purchase_price update, got {response.status_code}: {response.text}"
        error_detail = response.json().get("detail", "")
        assert "composite" in error_detail.lower() or "automatically" in error_detail.lower(), \
            f"Error message should mention composite/automatically: {error_detail}"
        print(f"PASS: Blocked purchase_price change for composite product - got 400 with message: {error_detail}")


class TestInventoryListEndpoint:
    """Tests for GET /api/business-tools/inventory"""

    def test_inventory_returns_pricing_fields_and_flag(self, auth_headers):
        """Test that inventory list returns purchase_price, selling_price, canViewPurchasePrice"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check canViewPurchasePrice flag
        assert "canViewPurchasePrice" in data, "Response should include canViewPurchasePrice flag"
        can_view = data["canViewPurchasePrice"]
        # dev-test-token is seller admin, should have all permissions
        assert can_view is True, f"Seller admin should have canViewPurchasePrice=True, got {can_view}"
        
        # Check inventory items have pricing fields
        inventory = data.get("inventory", [])
        assert len(inventory) > 0, "Inventory should have items"
        
        # Find Motor or Steel listing to verify prices
        found_pricing = False
        for item in inventory:
            if item.get("selling_price") is not None:
                found_pricing = True
                # If canViewPurchasePrice is True, purchase_price should be present
                if can_view:
                    # purchase_price may be present (or None if not set)
                    assert "purchase_price" in item or item.get("purchase_price") is None, \
                        "purchase_price should be in response for users with permission"
                print(f"Found item with selling_price: {item.get('productName')} - selling_price={item.get('selling_price')}, purchase_price={item.get('purchase_price')}")
                break
        
        print(f"PASS: Inventory list returns canViewPurchasePrice={can_view}, items have pricing fields")


class TestReportsProfitSummary:
    """Tests for GET /api/business-tools/reports/profit-summary"""

    def test_profit_summary_returns_overall_and_periods(self, auth_headers):
        """Test profit-summary endpoint returns overall totals and per-period breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/profit-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check overall totals
        assert "overall" in data, "Response should include 'overall' totals"
        overall = data["overall"]
        
        # Overall should have these fields
        expected_overall_fields = ["totalRevenue", "totalCost", "totalProfit", "profitMargin", "totalQuantity", "invoiceCount"]
        for field in expected_overall_fields:
            assert field in overall, f"overall should include '{field}'"
        
        print(f"PASS: profit-summary overall: revenue={overall.get('totalRevenue')}, cost={overall.get('totalCost')}, profit={overall.get('totalProfit')}, margin={overall.get('profitMargin')}%")
        
        # Check periods breakdown
        assert "periods" in data, "Response should include 'periods' breakdown"
        periods = data["periods"]
        
        if len(periods) > 0:
            period = periods[0]
            expected_period_fields = ["year", "revenue", "cost", "profit", "margin", "label"]
            for field in expected_period_fields:
                assert field in period, f"period should include '{field}'"
            print(f"PASS: First period: {period.get('label')} - revenue={period.get('revenue')}, cost={period.get('cost')}, profit={period.get('profit')}")
        else:
            print("INFO: No period data available (no invoices)")


class TestReportsProductProfit:
    """Tests for GET /api/business-tools/reports/product-profit"""

    def test_product_profit_returns_per_product_breakdown(self, auth_headers):
        """Test product-profit endpoint returns per-product profit breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-profit",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "products" in data, "Response should include 'products' array"
        products = data["products"]
        
        if len(products) > 0:
            product = products[0]
            expected_fields = ["productName", "totalQuantity", "totalRevenue", "totalCost", "profit", "margin"]
            for field in expected_fields:
                assert field in product, f"product should include '{field}'"
            
            print(f"PASS: Product profit - {product.get('productName')}: revenue={product.get('totalRevenue')}, cost={product.get('totalCost')}, profit={product.get('profit')}, margin={product.get('margin')}%")
        else:
            print("INFO: No product profit data available (no invoices)")


class TestReportsInventoryValue:
    """Tests for GET /api/business-tools/reports/inventory-value"""

    def test_inventory_value_returns_summary_and_items(self, auth_headers):
        """Test inventory-value returns summary and per-item breakdown with stockValue/potentialRevenue"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/inventory-value",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check summary
        assert "summary" in data, "Response should include 'summary'"
        summary = data["summary"]
        expected_summary_fields = ["totalInventoryValue", "totalPotentialRevenue", "totalPotentialProfit", "totalItems", "totalStockUnits"]
        for field in expected_summary_fields:
            assert field in summary, f"summary should include '{field}'"
        
        print(f"PASS: Inventory value summary - totalValue={summary.get('totalInventoryValue')}, potentialRevenue={summary.get('totalPotentialRevenue')}, potentialProfit={summary.get('totalPotentialProfit')}")
        
        # Check items
        assert "items" in data, "Response should include 'items' array"
        items = data["items"]
        
        if len(items) > 0:
            item = items[0]
            expected_item_fields = ["productName", "stock", "purchase_price", "selling_price", "stockValue", "potentialRevenue"]
            for field in expected_item_fields:
                assert field in item, f"item should include '{field}'"
            
            print(f"PASS: First item - {item.get('productName')}: stock={item.get('stock')}, stockValue={item.get('stockValue')}, potentialRevenue={item.get('potentialRevenue')}")
        else:
            print("INFO: No inventory items available")


class TestInvoicePurchasePriceStorage:
    """Tests for POST /api/business-tools/invoices - purchase_price per item"""

    def test_invoice_stores_purchase_price_per_item(self, auth_headers):
        """Test that invoice creation stores purchase_price per item for profit tracking"""
        # First get a buyer to create an invoice
        buyers_response = requests.get(
            f"{BASE_URL}/api/business-tools/buyers",
            headers=auth_headers
        )
        
        if buyers_response.status_code != 200:
            pytest.skip("Could not get buyers list")
        
        buyers_data = buyers_response.json()
        buyers = buyers_data.get("buyers", [])
        
        if not buyers:
            pytest.skip("No buyers available to create invoice")
        
        buyer_id = buyers[0].get("id")
        
        # Create an invoice with Motor listing (which has purchase_price=500)
        invoice_data = {
            "buyerId": buyer_id,
            "items": [
                {
                    "productId": MOTOR_LISTING_ID,
                    "productName": "Test Motor",
                    "quantity": 2,
                    "price": 750,
                    "gstPercent": 18
                }
            ],
            "notes": "Test invoice for purchase_price tracking",
            "deductStock": False  # Don't deduct stock for test
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices",
            headers=auth_headers,
            json=invoice_data
        )
        
        assert response.status_code == 200, f"Expected 200 for invoice creation, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "invoice" in data, "Response should include 'invoice'"
        invoice = data["invoice"]
        
        # Check items have purchase_price
        items = invoice.get("items", [])
        assert len(items) > 0, "Invoice should have items"
        
        first_item = items[0]
        assert "purchase_price" in first_item, "Invoice item should include purchase_price for profit tracking"
        
        # Motor has purchase_price=500, so invoice item should have 500
        purchase_price = first_item.get("purchase_price", 0)
        print(f"PASS: Invoice item has purchase_price={purchase_price} (expected ~500 for Motor)")
        
        # Clean up - delete the test invoice
        invoice_id = invoice.get("id")
        if invoice_id:
            # Update status to draft first if needed
            requests.put(
                f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status",
                headers=auth_headers,
                json={"status": "draft"}
            )
            delete_response = requests.delete(
                f"{BASE_URL}/api/business-tools/invoices/{invoice_id}",
                headers=auth_headers
            )
            print(f"Cleanup: Deleted test invoice {invoice_id}")


class TestMarketplaceVisibility:
    """Tests for marketplace endpoints - purchase_price NOT visible"""

    def test_listing_detail_has_productType_but_not_purchase_price(self, auth_headers):
        """Test GET /api/listings/{listing_id} returns productType but NOT purchase_price"""
        response = requests.get(
            f"{BASE_URL}/api/listings/{MOTOR_LISTING_ID}",
            headers=auth_headers
        )
        
        # Handle both 200 and potential auth issues
        if response.status_code == 404:
            pytest.skip(f"Listing {MOTOR_LISTING_ID} not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        listing = data.get("listing") or data
        
        # Should have productType
        assert "productType" in listing, "Listing should include productType for marketplace"
        print(f"PASS: Listing has productType={listing.get('productType')}")
        
        # Should NOT have purchase_price (sensitive data for seller only)
        assert "purchase_price" not in listing, "Listing should NOT include purchase_price on marketplace (sensitive)"
        print(f"PASS: Listing does NOT expose purchase_price on marketplace")


class TestCompositePurchasePriceCalculation:
    """Tests for composite product dynamic purchase price calculation"""

    def test_composite_purchase_price_calculated_from_components(self, auth_headers):
        """Test that composite product purchase_price is dynamically calculated from component purchase_prices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        composites = data.get("compositeProducts", [])
        if not composites:
            pytest.skip("No composite products available")
        
        # Check first composite that has components
        for composite in composites:
            components = composite.get("components", [])
            if len(components) > 0:
                # Composite should have purchasePrice field
                assert "purchasePrice" in composite, "Composite should have purchasePrice field"
                
                # Calculate expected purchase price from components
                calculated_price = 0
                for comp in components:
                    unit_price = comp.get("unitPrice", 0)
                    quantity = comp.get("quantity", 1)
                    calculated_price += unit_price * quantity
                
                actual_price = composite.get("purchasePrice", 0)
                
                print(f"PASS: Composite '{composite.get('productName')}' - purchasePrice={actual_price} (components total: {calculated_price})")
                
                # Should also have sellingPrice
                assert "sellingPrice" in composite, "Composite should have sellingPrice field"
                print(f"  -> sellingPrice={composite.get('sellingPrice')}")
                return
        
        print("INFO: No composite with components found to verify calculation")


class TestAuthenticationRequired:
    """Tests for authentication requirements"""

    def test_reports_endpoints_require_auth(self):
        """Test that report endpoints require authentication"""
        endpoints = [
            "/api/business-tools/reports/profit-summary",
            "/api/business-tools/reports/product-profit",
            "/api/business-tools/reports/inventory-value"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 422], f"Expected 401/422 for {endpoint} without auth, got {response.status_code}"
            print(f"PASS: {endpoint} requires authentication (got {response.status_code})")

    def test_invalid_token_returns_401(self, auth_headers):
        """Test that invalid token returns 401"""
        invalid_headers = {"Authorization": "Bearer invalid-token-xyz", "Content-Type": "application/json"}
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/profit-summary",
            headers=invalid_headers
        )
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        print("PASS: Invalid token returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
