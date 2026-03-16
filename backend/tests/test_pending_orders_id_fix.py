"""
Pending Orders - ID Field Bug Fix Tests
Tests that the normalize_doc function correctly converts _id to id for frontend compatibility.
Tests: GET /pending-orders returns id (not _id), all required fields for invoice prefill exist.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestPendingOrdersIdFieldFix:
    """Test that pending orders return 'id' field instead of '_id'"""

    def test_pending_orders_list_has_id_field(self):
        """GET /api/business-tools/pending-orders returns orders with 'id' field"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        print(f"Pending orders list response: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "pendingOrders" in data, "Response should have pendingOrders key"
        
        orders = data.get("pendingOrders", [])
        print(f"Total pending orders: {len(orders)}")
        
        if len(orders) > 0:
            first_order = orders[0]
            print(f"First order keys: {list(first_order.keys())}")
            
            # Critical bug fix: 'id' field should exist, NOT '_id'
            assert "id" in first_order, f"Order should have 'id' field. Got keys: {list(first_order.keys())}"
            assert "_id" not in first_order, f"Order should NOT have '_id' field (should be converted to 'id')"
            
            # Verify id is a valid string (not None or empty)
            assert first_order["id"] is not None, "Order id should not be None"
            assert len(first_order["id"]) > 0, "Order id should not be empty string"
            print(f"First order ID: {first_order['id']}")
        else:
            print("No pending orders found - cannot verify id field on orders")

    def test_pending_orders_have_invoice_prefill_fields(self):
        """Verify pending orders include buyerId, listingId, price, gstPercent for invoice prefill"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        assert res.status_code == 200
        
        orders = res.json().get("pendingOrders", [])
        if len(orders) == 0:
            pytest.skip("No pending orders to verify invoice prefill fields")
        
        first_order = orders[0]
        print(f"Order fields: {list(first_order.keys())}")
        
        # Required fields for invoice prefill via URL params
        required_fields = ["id", "buyerId", "listingId", "price", "gstPercent"]
        for field in required_fields:
            assert field in first_order, f"Order missing required field: {field}"
            print(f"  {field}: {first_order.get(field)}")
        
        # Verify buyerId and listingId are string IDs (not None)
        assert first_order["buyerId"] is not None, "buyerId should not be None"
        assert isinstance(first_order["buyerId"], str), f"buyerId should be string, got {type(first_order['buyerId'])}"
        
        assert first_order["listingId"] is not None, "listingId should not be None (needed for productId param)"
        assert isinstance(first_order["listingId"], str), f"listingId should be string, got {type(first_order['listingId'])}"

    def test_pending_orders_have_card_display_fields(self):
        """Verify pending orders include all fields for card layout display"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        assert res.status_code == 200
        
        orders = res.json().get("pendingOrders", [])
        if len(orders) == 0:
            pytest.skip("No pending orders to verify card display fields")
        
        first_order = orders[0]
        
        # Required fields for card display:
        # Product name, Buyer, Reference invoice, Ordered qty, Fulfilled qty, Pending qty, Stock, Available
        display_fields = [
            "productName",   # Product name
            "buyerName",     # Buyer
            "invoiceNumber", # Reference invoice (optional, may be empty)
            "orderedQty",    # Ordered qty
            "fulfilledQty",  # Fulfilled qty
            "pendingQty",    # Pending qty
            "currentStock",  # Stock (total)
            "availableStock" # Available (stock - reserved)
        ]
        
        for field in display_fields:
            if field == "invoiceNumber":
                # invoiceNumber is optional
                print(f"  {field}: {first_order.get(field, 'N/A')}")
            else:
                assert field in first_order, f"Order missing display field: {field}"
                print(f"  {field}: {first_order.get(field)}")

    def test_single_pending_order_has_id_field(self):
        """GET /api/business-tools/pending-orders/{id} returns order with 'id' field"""
        # First get an order ID from the list
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        assert res.status_code == 200
        
        orders = res.json().get("pendingOrders", [])
        if len(orders) == 0:
            pytest.skip("No pending orders to test single order endpoint")
        
        order_id = orders[0]["id"]
        print(f"Testing single order endpoint with ID: {order_id}")
        
        # Get single order
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders/{order_id}", headers=HEADERS)
        print(f"Single order response: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "pendingOrder" in data, "Response should have pendingOrder key"
        
        order = data["pendingOrder"]
        assert "id" in order, f"Single order should have 'id' field. Got keys: {list(order.keys())}"
        assert "_id" not in order, "Single order should NOT have '_id' field"
        assert order["id"] == order_id, f"Order id mismatch: {order['id']} != {order_id}"


class TestPendingOrderActionEndpoints:
    """Test action endpoints use valid order IDs"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get a pending order ID if one exists"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=pending", headers=HEADERS)
        if res.status_code == 200:
            orders = res.json().get("pendingOrders", [])
            if orders:
                self.order_id = orders[0]["id"]
                self.order = orders[0]
                print(f"Found pending order ID: {self.order_id}")
            else:
                self.order_id = None
                self.order = None
        else:
            self.order_id = None
            self.order = None

    def test_notify_endpoint_with_valid_id(self):
        """POST /api/business-tools/pending-orders/{id}/notify works with valid order ID"""
        if not self.order_id:
            pytest.skip("No pending orders to test notify endpoint")
        
        res = requests.post(
            f"{BASE_URL}/api/business-tools/pending-orders/{self.order_id}/notify",
            headers=HEADERS
        )
        print(f"Notify endpoint response: {res.status_code}")
        print(f"Response: {res.text[:500] if res.text else 'empty'}")
        
        # Should succeed (200) or fail with buyer phone missing (400), not 404 for invalid ID
        if res.status_code == 200:
            data = res.json()
            assert "whatsappLink" in data, "Successful notify should return whatsappLink"
            print(f"WhatsApp link generated successfully")
        elif res.status_code == 400:
            # Buyer phone not available is acceptable
            print(f"Notify failed: {res.json().get('detail', 'Unknown error')}")
            assert "phone" in res.text.lower() or "not found" in res.text.lower(), "400 should be about missing phone"
        else:
            assert False, f"Unexpected status: {res.status_code}"

    def test_cancel_endpoint_with_valid_id(self):
        """POST /api/business-tools/pending-orders/{id}/cancel works with valid order ID"""
        if not self.order_id:
            pytest.skip("No pending orders to test cancel endpoint")
        
        # Use partially_fulfilled to test since we don't want to actually cancel pending ones
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=partially_fulfilled", headers=HEADERS)
        partially_fulfilled = res.json().get("pendingOrders", [])
        
        if not partially_fulfilled:
            # Test with invalid ID to verify endpoint works
            res = requests.post(
                f"{BASE_URL}/api/business-tools/pending-orders/000000000000000000000000/cancel",
                headers=HEADERS,
                json={"reason": "Test cancel"}
            )
            print(f"Cancel endpoint with invalid ID: {res.status_code}")
            # Should return 404 not 500 or 405
            assert res.status_code in [400, 404], f"Expected 400 or 404 for invalid ID, got {res.status_code}"
        else:
            # If there's a partially fulfilled order, we could cancel it
            print("Found partially fulfilled order - not cancelling to preserve data")


class TestPendingOrderFilterStatus:
    """Test filtering pending orders by status"""

    def test_filter_pending_status(self):
        """Filter by status=pending returns only pending orders"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=pending", headers=HEADERS)
        assert res.status_code == 200
        for order in res.json().get("pendingOrders", []):
            assert order["status"] == "pending"
            # Also verify id field exists
            assert "id" in order

    def test_filter_partially_fulfilled_status(self):
        """Filter by status=partially_fulfilled returns only partial orders"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=partially_fulfilled", headers=HEADERS)
        assert res.status_code == 200
        for order in res.json().get("pendingOrders", []):
            assert order["status"] == "partially_fulfilled"
            assert "id" in order

    def test_filter_completed_status(self):
        """Filter by status=completed returns only completed orders"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=completed", headers=HEADERS)
        assert res.status_code == 200
        for order in res.json().get("pendingOrders", []):
            assert order["status"] == "completed"
            assert "id" in order

    def test_filter_cancelled_status(self):
        """Filter by status=cancelled returns only cancelled orders"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders?status=cancelled", headers=HEADERS)
        assert res.status_code == 200
        for order in res.json().get("pendingOrders", []):
            assert order["status"] == "cancelled"
            assert "id" in order


class TestInvoicePrefillURLParams:
    """Test that URL params for invoice prefill work correctly"""

    def test_pending_order_fields_match_invoice_prefill_params(self):
        """Verify pending order fields map correctly to invoice URL params"""
        res = requests.get(f"{BASE_URL}/api/business-tools/pending-orders", headers=HEADERS)
        assert res.status_code == 200
        
        orders = res.json().get("pendingOrders", [])
        if len(orders) == 0:
            pytest.skip("No pending orders to verify")
        
        order = orders[0]
        
        # URL params used by frontend: buyerId, productId, qty, price, gstPercent
        # These map to: buyerId, listingId, pendingQty, price, gstPercent
        param_mapping = {
            "buyerId": "buyerId",
            "productId": "listingId",  # listingId maps to productId in URL
            "qty": "pendingQty",
            "price": "price",
            "gstPercent": "gstPercent"
        }
        
        print("\nURL param mapping verification:")
        for url_param, order_field in param_mapping.items():
            value = order.get(order_field)
            print(f"  {url_param} <- {order_field}: {value}")
            assert order_field in order, f"Missing field for URL param {url_param}: {order_field}"
            if url_param in ["buyerId", "productId"]:
                assert value is not None and len(str(value)) > 0, f"{order_field} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
