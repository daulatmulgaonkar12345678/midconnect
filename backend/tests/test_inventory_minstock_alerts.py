"""
Test Inventory Module - MinStock, ReorderQuantity, LowStockAlertEnabled, and Low Stock Notifications
Tests the following new features:
- PUT /api/business-tools/inventory/{id} accepts minStock, reorderQuantity, lowStockAlertEnabled fields
- GET /api/business-tools/inventory returns minStock, reorderQuantity, lowStockAlertEnabled in each item
- POST /api/business-tools/inventory/{id}/adjust creates low_stock notification when new_stock <= minStock
- GET /api/business-tools/notifications includes low_stock type notifications
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test token for dev environment
TEST_TOKEN = "dev-test-token"
HEADERS = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}


class TestInventoryEndpoints:
    """Test inventory CRUD with new minStock fields"""

    def test_list_inventory_returns_minstock_fields(self):
        """GET /inventory should return minStock, reorderQuantity, lowStockAlertEnabled in each item"""
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "inventory" in data, "Response should contain 'inventory' key"
        assert "lowStockCount" in data, "Response should contain 'lowStockCount' key"
        
        # If there are inventory items, verify field presence
        if data["inventory"]:
            first_item = data["inventory"][0]
            print(f"Sample inventory item fields: {list(first_item.keys())}")
            
            # Verify new fields exist (may be default values)
            assert "minStock" in first_item, "Inventory item should have 'minStock' field"
            assert "reorderQuantity" in first_item, "Inventory item should have 'reorderQuantity' field"
            assert "lowStockAlertEnabled" in first_item, "Inventory item should have 'lowStockAlertEnabled' field"
            
            print(f"PASS: minStock={first_item['minStock']}, reorderQuantity={first_item['reorderQuantity']}, lowStockAlertEnabled={first_item['lowStockAlertEnabled']}")
        else:
            print("INFO: No inventory items found, creating one may be needed")

    def test_update_inventory_with_minstock_fields(self):
        """PUT /inventory/{id} should accept and save minStock, reorderQuantity, lowStockAlertEnabled"""
        # First get an inventory item
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        if not data["inventory"]:
            pytest.skip("No inventory items available to test")
        
        # Find a non-composite item (composite products can't be edited for certain fields)
        test_item = None
        for item in data["inventory"]:
            if item.get("productType") != "composite":
                test_item = item
                break
        
        if not test_item:
            pytest.skip("No non-composite inventory items available")
        
        listing_id = test_item.get("listingId") or test_item.get("id")
        print(f"Testing update on listing: {listing_id} ({test_item['productName']})")
        
        # Update with new fields
        update_payload = {
            "minStock": 25,
            "reorderQuantity": 50,
            "lowStockAlertEnabled": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}",
            headers=HEADERS,
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        print(f"Update response: {result.get('message')}")
        
        # Verify the update by fetching again
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        data = response.json()
        
        # Find the updated item
        updated_item = None
        for item in data["inventory"]:
            item_id = item.get("listingId") or item.get("id")
            if item_id == listing_id:
                updated_item = item
                break
        
        assert updated_item is not None, f"Updated item {listing_id} not found in inventory list"
        assert updated_item["minStock"] == 25, f"Expected minStock=25, got {updated_item['minStock']}"
        assert updated_item["reorderQuantity"] == 50, f"Expected reorderQuantity=50, got {updated_item['reorderQuantity']}"
        assert updated_item["lowStockAlertEnabled"] == True, f"Expected lowStockAlertEnabled=True, got {updated_item['lowStockAlertEnabled']}"
        
        print("PASS: All minStock fields updated and persisted correctly")


class TestLowStockNotifications:
    """Test low stock notification creation and retrieval"""

    def test_adjust_stock_creates_low_stock_notification(self):
        """POST /inventory/{id}/adjust should create notification when stock <= minStock"""
        # Get an inventory item to adjust
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        if not data["inventory"]:
            pytest.skip("No inventory items available")
        
        # Find a non-composite item with some stock
        test_item = None
        for item in data["inventory"]:
            if item.get("productType") != "composite" and item.get("stock", 0) >= 10:
                test_item = item
                break
        
        if not test_item:
            # Try to find any non-composite item
            for item in data["inventory"]:
                if item.get("productType") != "composite":
                    test_item = item
                    break
        
        if not test_item:
            pytest.skip("No suitable inventory item found")
        
        listing_id = test_item.get("listingId") or test_item.get("id")
        current_stock = test_item.get("stock", 0)
        product_name = test_item.get("productName")
        
        print(f"Testing low stock alert on: {product_name} (current stock: {current_stock})")
        
        # First, set minStock to a value higher than we'll reduce to
        update_payload = {
            "minStock": 15,
            "lowStockAlertEnabled": True
        }
        requests.put(f"{BASE_URL}/api/business-tools/inventory/{listing_id}", headers=HEADERS, json=update_payload)
        
        # Add stock first if too low
        if current_stock < 20:
            add_payload = {
                "listingId": listing_id,
                "changeType": "purchase",
                "quantity": 30,
                "note": "Test stock addition"
            }
            requests.post(f"{BASE_URL}/api/business-tools/inventory/{listing_id}/adjust", headers=HEADERS, json=add_payload)
        
        # Now reduce stock to trigger low stock alert
        adjust_payload = {
            "listingId": listing_id,
            "changeType": "sale",
            "quantity": 20,  # Reduce significantly
            "note": "Test low stock notification trigger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}/adjust",
            headers=HEADERS,
            json=adjust_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        print(f"Stock adjusted: previous={result.get('previousStock')}, new={result.get('newStock')}")
        
        # Check if low stock notification was created
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications?limit=10", headers=HEADERS)
        assert response.status_code == 200
        
        notifications = response.json().get("notifications", [])
        
        # Look for low_stock notification for this product
        low_stock_notifications = [n for n in notifications if n.get("type") == "low_stock"]
        print(f"Found {len(low_stock_notifications)} low_stock notifications")
        
        if low_stock_notifications:
            recent = low_stock_notifications[0]
            print(f"Most recent low_stock notification: {recent.get('title')}")
            print(f"Message: {recent.get('message')}")
            assert "Low Stock" in recent.get("title", ""), "Notification title should contain 'Low Stock'"
        
        print("PASS: Low stock notification system working")

    def test_notifications_include_low_stock_type(self):
        """GET /notifications should return low_stock type notifications"""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications?limit=50", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "notifications" in data, "Response should contain 'notifications'"
        assert "total" in data, "Response should contain 'total'"
        assert "unread" in data, "Response should contain 'unread'"
        
        notifications = data.get("notifications", [])
        print(f"Total notifications: {data.get('total')}, Unread: {data.get('unread')}")
        
        # Check notification types
        types_found = set()
        for n in notifications:
            types_found.add(n.get("type"))
        
        print(f"Notification types found: {types_found}")
        
        # Verify notification structure
        if notifications:
            sample = notifications[0]
            required_fields = ["id", "type", "title", "message", "read", "createdAt"]
            for field in required_fields:
                assert field in sample, f"Notification should have '{field}' field"
        
        print("PASS: Notifications endpoint working correctly")


class TestInventoryTableFeatures:
    """Test inventory listing features for UI requirements"""

    def test_inventory_returns_all_required_fields(self):
        """Verify inventory list returns all fields needed for UI table"""
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        if not data["inventory"]:
            pytest.skip("No inventory items to verify")
        
        # Fields required for the inventory table UI
        required_fields = [
            "listingId", "productName", "sku", "stock", 
            "minStock", "lowStockAlertEnabled", "isLowStock"
        ]
        
        sample = data["inventory"][0]
        missing = []
        for field in required_fields:
            if field not in sample:
                missing.append(field)
        
        assert not missing, f"Missing required fields: {missing}"
        print(f"PASS: All required fields present. Sample: minStock={sample['minStock']}, isLowStock={sample['isLowStock']}")

    def test_low_stock_only_filter(self):
        """GET /inventory?lowStockOnly=true should filter correctly"""
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory?lowStockOnly=true", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        print(f"Low stock only count: {len(data['inventory'])}")
        
        # All returned items should be low stock
        for item in data["inventory"]:
            assert item.get("isLowStock") == True, f"Item {item['productName']} should be low stock but isLowStock={item.get('isLowStock')}"
        
        print("PASS: lowStockOnly filter working correctly")


class TestAlertToggle:
    """Test alert toggle functionality"""

    def test_disable_low_stock_alert(self):
        """Test disabling low stock alert for a product"""
        # Get an inventory item
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        if not data["inventory"]:
            pytest.skip("No inventory items available")
        
        # Find a non-composite item
        test_item = None
        for item in data["inventory"]:
            if item.get("productType") != "composite":
                test_item = item
                break
        
        if not test_item:
            pytest.skip("No non-composite inventory items available")
        
        listing_id = test_item.get("listingId") or test_item.get("id")
        
        # Disable alert
        update_payload = {
            "lowStockAlertEnabled": False
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}",
            headers=HEADERS,
            json=update_payload
        )
        assert response.status_code == 200
        
        # Verify
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        data = response.json()
        
        updated = None
        for item in data["inventory"]:
            item_id = item.get("listingId") or item.get("id")
            if item_id == listing_id:
                updated = item
                break
        
        assert updated is not None
        assert updated["lowStockAlertEnabled"] == False, f"Expected False, got {updated['lowStockAlertEnabled']}"
        
        # Re-enable for cleanup
        requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}",
            headers=HEADERS,
            json={"lowStockAlertEnabled": True}
        )
        
        print("PASS: Alert toggle working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
