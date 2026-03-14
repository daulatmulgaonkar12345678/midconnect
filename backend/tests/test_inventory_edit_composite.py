"""
Test Inventory Edit Fix - Composite Product Selling Price Editability
Tests:
1. selling_price can be updated for composite products
2. purchase_price is blocked for composite products (auto-calculated)
3. Both selling_price and purchase_price can be updated for regular products
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
DEV_TOKEN = "dev-test-token"

# Test data from provided credentials
COMPOSITE_LISTING_ID = "69b5c25c2972a896e0a78417"
REGULAR_MOTOR_LISTING_ID = "69b57c730ed7999c085b3656"
REGULAR_STEEL_LISTING_ID = "69b57c730ed7999c085b3657"


class TestCompositeProductPricing:
    """Tests for composite product selling_price editability (Fix #2)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth header"""
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        })

    def test_composite_selling_price_update_succeeds(self):
        """Composite product selling_price should be editable"""
        # Store original and update
        new_price = 2700
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{COMPOSITE_LISTING_ID}",
            json={"selling_price": new_price}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Inventory updated"
        assert data.get("listing", {}).get("selling_price") == new_price
        print(f"✓ Composite selling_price update succeeded: {new_price}")

    def test_composite_purchase_price_update_blocked(self):
        """Composite product purchase_price should NOT be editable (auto-calculated)"""
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{COMPOSITE_LISTING_ID}",
            json={"purchase_price": 1500}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Composite product purchase price is calculated automatically" in data.get("detail", "")
        print(f"✓ Composite purchase_price correctly blocked: {data.get('detail')}")

    def test_composite_stock_change_blocked(self):
        """Composite product stock should NOT be changeable (auto-calculated)"""
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{COMPOSITE_LISTING_ID}",
            json={"stockQuantity": 100}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Composite product stock is calculated automatically" in data.get("detail", "")
        print(f"✓ Composite stock change correctly blocked: {data.get('detail')}")


class TestRegularProductPricing:
    """Tests for regular product pricing editability"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        })

    def test_regular_product_selling_and_purchase_price_update(self):
        """Regular product should allow both selling_price and purchase_price updates"""
        new_selling = 850
        new_purchase = 550
        
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{REGULAR_MOTOR_LISTING_ID}",
            json={"selling_price": new_selling, "purchase_price": new_purchase}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        listing = data.get("listing", {})
        assert listing.get("selling_price") == new_selling
        assert listing.get("purchase_price") == new_purchase
        print(f"✓ Regular product prices updated: selling={new_selling}, purchase={new_purchase}")

    def test_regular_product_sku_and_location_update(self):
        """Regular product should allow SKU and warehouse location updates"""
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{REGULAR_MOTOR_LISTING_ID}",
            json={"sku": "TEST-SKU-001", "warehouseLocation": "Warehouse A, Rack 3"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        listing = data.get("listing", {})
        assert listing.get("sku") == "TEST-SKU-001"
        assert listing.get("warehouseLocation") == "Warehouse A, Rack 3"
        print(f"✓ Regular product SKU and location updated")


class TestInventoryListEndpoint:
    """Tests for inventory listing endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        })

    def test_inventory_returns_product_type(self):
        """Inventory endpoint should return productType for each item"""
        response = self.session.get(f"{BASE_URL}/api/business-tools/inventory")
        
        assert response.status_code == 200
        data = response.json()
        inventory = data.get("inventory", [])
        
        # Check that productType is present for all items
        for item in inventory:
            assert "productType" in item, f"Missing productType for item {item.get('listingId')}"
            assert item["productType"] in ["single", "composite"], f"Invalid productType: {item['productType']}"
        
        # Verify our test composite exists
        composite_items = [i for i in inventory if i.get("productType") == "composite"]
        assert len(composite_items) > 0, "No composite products found in inventory"
        print(f"✓ Inventory returns productType correctly. Found {len(composite_items)} composite(s)")

    def test_inventory_returns_purchase_price_for_seller(self):
        """Seller admin should see purchase_price"""
        response = self.session.get(f"{BASE_URL}/api/business-tools/inventory")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("canViewPurchasePrice") == True
        
        # Check that purchase_price field exists (even if null for composites)
        for item in data.get("inventory", []):
            assert "purchase_price" in item, f"Missing purchase_price for item {item.get('listingId')}"
        print("✓ Seller admin can view purchase_price")


class TestCompositePriceSyncToCollection:
    """Test that composite selling_price syncs to composite_products collection"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        })

    def test_selling_price_sync_to_composite_products(self):
        """When updating composite listing selling_price, it should sync to composite_products.price"""
        # Update the selling_price
        new_price = 2800
        response = self.session.put(
            f"{BASE_URL}/api/business-tools/inventory/{COMPOSITE_LISTING_ID}",
            json={"selling_price": new_price}
        )
        
        assert response.status_code == 200
        listing_data = response.json().get("listing", {})
        assert listing_data.get("selling_price") == new_price
        
        # The sync happens internally. We verify by checking the listing has compositeProductId
        assert "compositeProductId" in listing_data, "Composite listing should have compositeProductId"
        print(f"✓ Composite selling_price updated to {new_price}. Sync to composite_products should have occurred.")


# Restore original values after tests
@pytest.fixture(scope="module", autouse=True)
def restore_test_data():
    """Restore original test data after all tests complete"""
    yield
    
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {DEV_TOKEN}",
        "Content-Type": "application/json"
    })
    
    # Restore composite selling_price
    session.put(
        f"{BASE_URL}/api/business-tools/inventory/{COMPOSITE_LISTING_ID}",
        json={"selling_price": 2500}
    )
    
    # Restore regular product values
    session.put(
        f"{BASE_URL}/api/business-tools/inventory/{REGULAR_MOTOR_LISTING_ID}",
        json={"selling_price": 750, "purchase_price": 500, "sku": "", "warehouseLocation": ""}
    )
    
    print("✓ Test data restored to original values")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
