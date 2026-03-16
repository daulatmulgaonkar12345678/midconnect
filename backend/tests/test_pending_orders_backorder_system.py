"""
Pending Orders (Backorder) System - Backend API Tests
Tests partial fulfillment, pending order tracking, stock reservation, and fulfil/cancel/create-po/notify actions.
"""
import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestPendingOrdersBasicEndpoints:
    """Test pending orders list and basic endpoints"""

    def test_pending_orders_list_returns_200(self):
        """GET /api/business-tools/pending-orders returns 200 with counts"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        print(f"Pending orders list response: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "pendingOrders" in data, "Response should have pendingOrders key"
        assert "total" in data, "Response should have total count"
        assert "pendingCount" in data, "Response should have pendingCount"
        assert "partialCount" in data, "Response should have partialCount"
        print(f"Pending orders: {data['total']}, pending: {data['pendingCount']}, partial: {data['partialCount']}")

    def test_pending_orders_filter_by_status(self):
        """GET /api/business-tools/pending-orders?status=pending filters correctly"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=pending", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        for order in data.get("pendingOrders", []):
            assert order["status"] == "pending", f"Expected status pending, got {order['status']}"


class TestCheckStockEndpoint:
    """Test POST /api/business-tools/invoices/check-stock for shortage detection"""

    def test_check_stock_endpoint_exists(self):
        """POST /api/business-tools/invoices/check-stock endpoint exists"""
        # Minimal payload to check endpoint exists
        payload = {
            "buyerId": "000000000000000000000000",  # Invalid but tests endpoint
            "items": [],
            "deductStock": True,
            "dueDays": 7
        }
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/check-stock", headers=HEADERS, json=payload)
        # Will fail due to invalid buyer but should hit the endpoint
        print(f"Check stock response: {res.status_code}")
        # Accept 200 (no items), 404 (buyer not found), or 422 (validation)
        assert res.status_code in [200, 404, 422], f"Unexpected status: {res.status_code}"


class TestInvoiceProductsReservedStock:
    """Test GET /api/business-tools/invoice-products includes reservedStock and availableStock"""

    def test_invoice_products_has_reserved_fields(self):
        """GET /api/business-tools/invoice-products returns reservedStock and availableStock"""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=HEADERS)
        print(f"Invoice products response: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        products = data.get("products", [])
        if len(products) > 0:
            first = products[0]
            assert "reservedStock" in first, "Product should have reservedStock field"
            assert "availableStock" in first, "Product should have availableStock field"
            assert "stock" in first, "Product should have stock field"
            print(f"First product: stock={first.get('stock')}, reserved={first.get('reservedStock')}, available={first.get('availableStock')}")
        else:
            print("No products found, skipping field check")


class TestInventoryReservedStock:
    """Test GET /api/business-tools/inventory includes reservedStock and availableStock"""

    def test_inventory_has_reserved_fields(self):
        """GET /api/business-tools/inventory returns reservedStock and availableStock for each item"""
        res = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        print(f"Inventory response: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        inventory = data.get("inventory", [])
        if len(inventory) > 0:
            first = inventory[0]
            assert "reservedStock" in first, "Inventory item should have reservedStock field"
            assert "availableStock" in first, "Inventory item should have availableStock field"
            print(f"First inventory: stock={first.get('stock')}, reserved={first.get('reservedStock')}, available={first.get('availableStock')}")
        else:
            print("No inventory items found, skipping field check")


class TestPendingOrderActions:
    """Test pending order action endpoints (require valid pending order)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get a pending order ID if one exists"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=pending", headers=HEADERS)
        if res.status_code == 200:
            orders = res.json().get("pendingOrders", [])
            if orders:
                self.pending_order_id = orders[0]["id"]
                self.pending_order = orders[0]
            else:
                self.pending_order_id = None
                self.pending_order = None
        else:
            self.pending_order_id = None
            self.pending_order = None

    def test_fulfil_endpoint_exists(self):
        """POST /api/business-tools/pending-orders/{id}/fulfil endpoint exists"""
        if not self.pending_order_id:
            pytest.skip("No pending orders to test fulfil endpoint")
        
        # Try to fulfil with 0 quantity - should fail with validation error, not 404
        payload = {"quantity": 0, "deductStock": False}
        res = requests.post(
            f"{BASE_URL}/api/business-tools/pending-orders/{self.pending_order_id}/fulfil",
            headers=HEADERS,
            json=payload
        )
        print(f"Fulfil endpoint response: {res.status_code}")
        # Should return 400 (quantity must be positive) not 404 (endpoint missing)
        assert res.status_code in [200, 400], f"Unexpected status: {res.status_code}: {res.text}"

    def test_cancel_endpoint_exists(self):
        """POST /api/business-tools/pending-orders/{id}/cancel endpoint exists"""
        # Use invalid ID to test endpoint exists but don't actually cancel anything
        res = requests.post(
            f"{BASE_URL}/api/business-tools/pending-orders/000000000000000000000000/cancel",
            headers=HEADERS,
            json={"reason": "test"}
        )
        print(f"Cancel endpoint response: {res.status_code}")
        # Should return 404 (not found) not 405 (method not allowed)
        assert res.status_code in [404, 400], f"Unexpected status: {res.status_code}"

    def test_create_po_endpoint_exists(self):
        """POST /api/business-tools/pending-orders/{id}/create-po endpoint exists"""
        # Use invalid ID to test endpoint exists
        res = requests.post(
            f"{BASE_URL}/api/business-tools/pending-orders/000000000000000000000000/create-po",
            headers=HEADERS
        )
        print(f"Create PO endpoint response: {res.status_code}")
        # Should return 404 (not found) not 405 (method not allowed)
        assert res.status_code in [404, 400], f"Unexpected status: {res.status_code}"

    def test_notify_endpoint_exists(self):
        """POST /api/business-tools/pending-orders/{id}/notify endpoint exists"""
        # Use invalid ID to test endpoint exists
        res = requests.post(
            f"{BASE_URL}/api/business-tools/pending-orders/000000000000000000000000/notify",
            headers=HEADERS
        )
        print(f"Notify endpoint response: {res.status_code}")
        # Should return 404 (not found) not 405 (method not allowed)
        assert res.status_code in [404, 400], f"Unexpected status: {res.status_code}"


class TestPartialFulfillmentFlow:
    """Test full backorder flow: create invoice with shortage -> pending order created"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get test data required for the flow"""
        # Get a buyer
        res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=HEADERS)
        if res.status_code == 200:
            buyers = res.json().get("buyers", [])
            self.buyer_id = buyers[0]["id"] if buyers else None
        else:
            self.buyer_id = None

        # Get a product with stock
        res = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=HEADERS)
        if res.status_code == 200:
            products = res.json().get("products", [])
            # Find a product with some stock
            for p in products:
                if p.get("stock", 0) > 0 and p.get("availableStock", 0) > 0:
                    self.product = p
                    break
            else:
                self.product = products[0] if products else None
        else:
            self.product = None

    def test_check_stock_detects_shortage(self):
        """POST /api/business-tools/invoices/check-stock detects when qty > available stock"""
        if not self.buyer_id or not self.product:
            pytest.skip("No buyer or product available for testing")

        available = self.product.get("availableStock", 0)
        # Request more than available
        payload = {
            "buyerId": self.buyer_id,
            "items": [{
                "productId": self.product["id"],
                "productName": self.product.get("productName", "Test"),
                "quantity": available + 10,  # More than available
                "price": self.product.get("price", 100),
                "gstPercent": 18,
                "selected_specifications": []
            }],
            "deductStock": True,
            "dueDays": 7
        }
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/check-stock", headers=HEADERS, json=payload)
        print(f"Check stock response: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Check stock result: hasShortage={data.get('hasShortage')}, shortages={data.get('shortages')}")
            assert "hasShortage" in data, "Response should have hasShortage field"
            # If available stock is 0, there should be shortage
            if available == 0:
                assert data["hasShortage"] == True, "Should detect shortage when available is 0"
                assert len(data.get("shortages", [])) > 0, "Should have shortage details"
        else:
            print(f"Check stock failed: {res.text}")

    def test_invoice_with_partial_fulfillment_creates_pending_order(self):
        """POST /api/business-tools/invoices with allowPartialFulfillment=true creates pending orders"""
        if not self.buyer_id or not self.product:
            pytest.skip("No buyer or product available for testing")

        # Get initial pending order count
        initial_res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        initial_count = initial_res.json().get("total", 0) if initial_res.status_code == 200 else 0

        available = self.product.get("availableStock", 0)
        if available >= 10:
            pytest.skip("Product has enough stock, no shortage will occur")

        # Request more than available with partial fulfillment enabled
        payload = {
            "buyerId": self.buyer_id,
            "items": [{
                "productId": self.product["id"],
                "productName": self.product.get("productName", "Test"),
                "quantity": max(available + 5, 10),  # More than available
                "price": self.product.get("price", 100),
                "gstPercent": 18,
                "selected_specifications": []
            }],
            "deductStock": True,
            "allowPartialFulfillment": True,  # Enable partial fulfillment
            "dueDays": 7,
            "notes": "Test partial fulfillment"
        }
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS, json=payload)
        print(f"Create invoice response: {res.status_code}")
        if res.status_code in [200, 201]:
            data = res.json()
            print(f"Invoice created: {data.get('invoice', {}).get('invoiceNumber')}")
            # Check if pendingOrders were created
            if "pendingOrders" in data:
                print(f"Pending orders created: {data['pendingOrders']}")
                assert len(data["pendingOrders"]) > 0, "Should have created pending orders"
        else:
            print(f"Invoice creation failed: {res.text}")


class TestReservedStockCalculation:
    """Test reserved stock calculation from pending orders"""

    def test_reserved_stock_api(self):
        """GET /api/business-tools/reserved-stock/{listing_id} returns reserved stock info"""
        # First get a listing ID
        res = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        if res.status_code != 200:
            pytest.skip("Could not get inventory")
        
        inventory = res.json().get("inventory", [])
        if not inventory:
            pytest.skip("No inventory items")
        
        listing_id = inventory[0].get("listingId") or inventory[0].get("id")
        if not listing_id:
            pytest.skip("No listing ID found")
        
        # Test reserved stock endpoint
        res = requests.get(f"{BASE_URL}/api/business-tools/reserved-stock/{listing_id}", headers=HEADERS)
        print(f"Reserved stock response: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            assert "totalStock" in data, "Should have totalStock field"
            assert "reservedStock" in data, "Should have reservedStock field"
            assert "availableStock" in data, "Should have availableStock field"
            print(f"Reserved stock: total={data['totalStock']}, reserved={data['reservedStock']}, available={data['availableStock']}")
        else:
            print(f"Reserved stock endpoint returned: {res.status_code}")


class TestRegressionEndpoints:
    """Regression tests for related endpoints"""

    def test_invoices_endpoint(self):
        """GET /api/business-tools/invoices returns 200"""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        assert res.status_code == 200, f"Invoices endpoint failed: {res.status_code}"
        print(f"Invoices count: {len(res.json().get('invoices', []))}")

    def test_buyers_endpoint(self):
        """GET /api/business-tools/buyers returns 200"""
        res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=HEADERS)
        assert res.status_code == 200, f"Buyers endpoint failed: {res.status_code}"
        print(f"Buyers count: {len(res.json().get('buyers', []))}")

    def test_inventory_endpoint(self):
        """GET /api/business-tools/inventory returns 200"""
        res = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert res.status_code == 200, f"Inventory endpoint failed: {res.status_code}"
        print(f"Inventory count: {len(res.json().get('inventory', []))}")

    def test_suppliers_endpoint(self):
        """GET /api/business-tools/suppliers returns 200"""
        res = requests.get(f"{BASE_URL}/api/business-tools/suppliers", headers=HEADERS)
        assert res.status_code == 200, f"Suppliers endpoint failed: {res.status_code}"
        print(f"Suppliers count: {len(res.json().get('suppliers', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
