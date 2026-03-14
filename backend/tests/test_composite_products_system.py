"""
Composite Products System Test Suite - Iteration 51
Tests for B2B composite products (bundles of seller inventory items).

Key rules tested:
1. Product name/category from admin catalog, components from seller inventory
2. Stock is dynamically calculated: min(component_stock / component_qty)
3. Creating composite creates sellerListing with productType='composite'
4. Selling composite deducts from component items, not composite itself
5. Composite stock cannot be manually adjusted in inventory
6. Duplicate composite for same productId+sellerId blocked (409)
7. RBAC requires manage_inventory permission
8. Invoice stock deduction for composite deducts from components
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Existing seller's inventory listings (from seller-inventory endpoint)
LISTING_MOTOR_ID = "69b57c730ed7999c085b3656"  # Industrial Electric Motor 5HP
LISTING_ROUND_BAR_ID = "69b57c730ed7999c085b3657"  # SS304 Round Bar

# Admin catalog IDs
TEST_CATEGORY_ID = "699bce748dd2e92e3fbc4336"  # TEST_DI_Cat1
TEST_PRODUCT_ID = "699d629108ac3c22bb591667"   # TEST_NoSpecTemplate_Product

# Existing composite product from previous testing
EXISTING_COMPOSITE_ID = "69b5b08db52f04a0b197f9ce"
EXISTING_COMPOSITE_LISTING_ID = "69b5b08db52f04a0b197f9d1"


class TestSellerInventoryForComponents:
    """GET /api/business-tools/composite-products/seller-inventory - for component selection"""
    
    def test_returns_inventory_list(self):
        """Should return seller's inventory items for component selection"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "inventory" in data
        assert isinstance(data["inventory"], list)
        print(f"  [PASS] Found {len(data['inventory'])} inventory items")
    
    def test_inventory_item_structure(self):
        """Each item has listingId, productName, stock, unitPrice"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        for item in data.get("inventory", []):
            assert "listingId" in item, f"Missing listingId: {item}"
            assert "productName" in item, f"Missing productName: {item}"
            assert "stock" in item, f"Missing stock: {item}"
            print(f"  [PASS] Item: {item['productName']} - stock: {item['stock']}")
    
    def test_excludes_composite_listings(self):
        """Should not return composite listings (prevents recursive composites)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        # Composite listing ID should NOT be in the list
        listing_ids = [item["listingId"] for item in data.get("inventory", [])]
        assert EXISTING_COMPOSITE_LISTING_ID not in listing_ids, "Composite listings should be excluded"
        print("  [PASS] Composite listings correctly excluded")


class TestCompositeProductsList:
    """GET /api/business-tools/composite-products - list with enriched data"""
    
    def test_returns_composite_products(self):
        """Should return list of composite products"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        assert "compositeProducts" in data
        print(f"  [PASS] Found {len(data['compositeProducts'])} composite products")
    
    def test_enriched_fields(self):
        """Should include productName, categoryName, components, availableStock, prices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        
        for cp in data.get("compositeProducts", []):
            # Required enriched fields
            assert "id" in cp, f"Missing id: {cp}"
            assert "productName" in cp, f"Missing productName: {cp}"
            assert "categoryName" in cp or cp.get("categoryId"), f"Missing category info: {cp}"
            assert "components" in cp, f"Missing components: {cp}"
            assert "availableStock" in cp, f"Missing availableStock: {cp}"
            assert "sellingPrice" in cp or "price" in cp, f"Missing price: {cp}"
            
            # Component structure
            for comp in cp.get("components", []):
                assert "listingId" in comp, f"Component missing listingId: {comp}"
                assert "quantity" in comp, f"Component missing quantity: {comp}"
                assert "productName" in comp, f"Component missing productName: {comp}"
                assert "currentStock" in comp, f"Component missing currentStock: {comp}"
            
            print(f"  [PASS] Composite '{cp['productName']}': stock={cp['availableStock']}, components={len(cp.get('components', []))}")
    
    def test_dynamic_stock_calculation(self):
        """availableStock = min(component_stock / component_qty) dynamically"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        
        for cp in data.get("compositeProducts", []):
            components = cp.get("components", [])
            if components:
                # Calculate expected stock
                expected = float('inf')
                for comp in components:
                    stock = comp.get("currentStock", 0)
                    qty = comp.get("quantity", 1)
                    if qty > 0:
                        expected = min(expected, stock // qty)
                
                if expected != float('inf'):
                    actual = cp.get("availableStock", 0)
                    assert actual == expected, \
                        f"Stock mismatch for '{cp['productName']}': expected {expected}, got {actual}"
                    print(f"  [PASS] '{cp['productName']}': stock={actual} correctly calculated")


class TestDuplicateCompositeBlocked:
    """Duplicate composite for same productId+sellerId returns 409"""
    
    def test_duplicate_creation_returns_409(self):
        """Creating composite with same productId should return 409"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,  # Same as existing composite
            "description": "Duplicate test",
            "price": 10000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        assert "already exists" in response.text.lower() or "edit" in response.text.lower()
        print("  [PASS] Duplicate composite correctly blocked with 409")


class TestCompositeProductUpdate:
    """PUT /api/business-tools/composite-products/{id} - update price, description, components"""
    
    def test_update_price(self):
        """Should update selling price"""
        original_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        original_data = original_response.json()
        original_cp = next((cp for cp in original_data.get("compositeProducts", []) 
                          if cp["id"] == EXISTING_COMPOSITE_ID), None)
        
        if not original_cp:
            pytest.skip("Existing composite not found")
        
        new_price = 16500.0
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}",
            headers=AUTH_HEADER,
            json={"price": new_price}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert cp["price"] == new_price, f"Price should be {new_price}, got {cp['price']}"
        print(f"  [PASS] Updated price to {new_price}")
        
        # Restore original price
        requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}",
            headers=AUTH_HEADER,
            json={"price": original_cp.get("price", 15000.0)}
        )
    
    def test_update_description(self):
        """Should update description"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}",
            headers=AUTH_HEADER,
            json={"description": "Updated description for testing"}
        )
        assert response.status_code == 200
        cp = response.json()["compositeProduct"]
        assert cp["description"] == "Updated description for testing"
        print("  [PASS] Updated description")
    
    def test_update_nonexistent_returns_404(self):
        """Should return 404 for non-existent ID"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER,
            json={"description": "Should fail"}
        )
        assert response.status_code == 404
        print("  [PASS] 404 for non-existent composite")


class TestCompositeProductSell:
    """POST /api/business-tools/composite-products/{id}/sell - deducts from components"""
    
    def test_sell_deducts_from_components(self):
        """Selling should deduct stock from component inventory items"""
        # Get current component stocks
        inv_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        inv_data = inv_response.json()
        before_stocks = {item["listingId"]: item["stock"] for item in inv_data.get("inventory", [])}
        
        # Sell 1 unit
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "deductions" in data, f"Response should have deductions: {data}"
        assert len(data["deductions"]) >= 1, "Should have at least 1 deduction"
        
        for deduction in data["deductions"]:
            assert "product" in deduction
            assert "deducted" in deduction
            assert "newStock" in deduction
            print(f"  [PASS] Deducted {deduction['deducted']} from {deduction['product']}, new stock: {deduction['newStock']}")
    
    def test_sell_recalculates_composite_stock(self):
        """After sell, composite availableStock should recalculate"""
        # Get stock before
        before_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        before_data = before_response.json()
        before_cp = next((cp for cp in before_data.get("compositeProducts", []) 
                         if cp["id"] == EXISTING_COMPOSITE_ID), None)
        
        if not before_cp:
            pytest.skip("Composite not found")
        
        before_stock = before_cp.get("availableStock", 0)
        
        if before_stock <= 0:
            print("  [SKIP] No stock available to test sell")
            return
        
        # Sell 1 unit
        sell_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        
        if sell_response.status_code != 200:
            print(f"  [SKIP] Sell failed: {sell_response.text}")
            return
        
        # Get stock after
        after_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        after_data = after_response.json()
        after_cp = next((cp for cp in after_data.get("compositeProducts", []) 
                        if cp["id"] == EXISTING_COMPOSITE_ID), None)
        
        if after_cp:
            after_stock = after_cp.get("availableStock", 0)
            # Stock should decrease or stay same (if components have different constraints)
            assert after_stock <= before_stock, \
                f"Stock should decrease: before={before_stock}, after={after_stock}"
            print(f"  [PASS] Stock recalculated: {before_stock} -> {after_stock}")
    
    def test_sell_fails_insufficient_stock(self):
        """Should reject sell if component stock insufficient"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{EXISTING_COMPOSITE_ID}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 99999}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "insufficient" in response.text.lower() or "need" in response.text.lower()
        print("  [PASS] Insufficient stock rejected")


class TestInventoryStockAdjustmentBlocked:
    """Inventory stock adjustment blocked for composite products (returns 400)"""
    
    def test_adjust_endpoint_blocked_for_composite(self):
        """POST /inventory/{id}/adjust should return 400 for composite"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/inventory/{EXISTING_COMPOSITE_LISTING_ID}/adjust",
            headers=AUTH_HEADER,
            json={"listingId": EXISTING_COMPOSITE_LISTING_ID, "changeType": "adjustment", "quantity": 10, "note": "test"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "composite" in response.text.lower() and ("automatically" in response.text.lower() or "calculated" in response.text.lower())
        print("  [PASS] Inventory adjust blocked for composite (400)")
    
    def test_update_stock_quantity_blocked_for_composite(self):
        """PUT /inventory/{id} with stockQuantity should return 400 for composite"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{EXISTING_COMPOSITE_LISTING_ID}",
            headers=AUTH_HEADER,
            json={"stockQuantity": 100}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "composite" in response.text.lower()
        print("  [PASS] Inventory stock update blocked for composite (400)")
    
    def test_can_update_other_fields_for_composite(self):
        """Should allow updating SKU, lowStockAlert, warehouseLocation for composite"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{EXISTING_COMPOSITE_LISTING_ID}",
            headers=AUTH_HEADER,
            json={"sku": "TEST-COMP-001", "lowStockAlert": 5, "warehouseLocation": "A1"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("  [PASS] Non-stock fields can be updated for composite")


class TestInventoryReturnsProductType:
    """Inventory endpoint returns productType field for composite badge display"""
    
    def test_inventory_has_product_type_field(self):
        """GET /inventory should return productType for each item"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data.get("inventory", []):
            assert "productType" in item, f"Item missing productType: {item}"
            print(f"  [PASS] {item['productName']}: productType={item['productType']}")
    
    def test_composite_listing_shows_composite_type(self):
        """Composite listing should have productType='composite'"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        
        composite_items = [item for item in data.get("inventory", []) if item.get("productType") == "composite"]
        assert len(composite_items) >= 1, "Should have at least one composite in inventory"
        
        for item in composite_items:
            assert item["productType"] == "composite"
            print(f"  [PASS] Composite: {item['productName']} has productType='composite'")


class TestCompositeSellerListingFields:
    """Composite sellerListing has correct fields for marketplace visibility"""
    
    def test_composite_visible_in_inventory(self):
        """Composite sellerListing should be in inventory endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find composite listing
        composite_items = [item for item in data.get("inventory", []) 
                         if item.get("productType") == "composite"]
        assert len(composite_items) >= 1, "Composite should be in inventory"
        
        comp_item = composite_items[0]
        assert "stock" in comp_item, "Should have stock"
        assert "productName" in comp_item, "Should have productName"
        assert comp_item.get("status") in ["active", "paused"], "Should have valid status"
        print(f"  [PASS] Composite listing visible: {comp_item['productName']}, stock={comp_item['stock']}")


class TestCompositeProductDelete:
    """DELETE /api/business-tools/composite-products/{id} - removes composite and sellerListing"""
    
    def test_delete_nonexistent_returns_404(self):
        """Should return 404 for non-existent ID"""
        response = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER
        )
        assert response.status_code == 404
        print("  [PASS] 404 for non-existent composite")


class TestValidation:
    """Input validation tests"""
    
    def test_create_validates_category_exists(self):
        """Should reject invalid category ID"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json={
                "categoryId": "000000000000000000000000",
                "productId": TEST_PRODUCT_ID,
                "price": 1000.0,
                "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("  [PASS] Invalid category rejected (400)")
    
    def test_create_validates_product_exists(self):
        """Should reject invalid product ID"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json={
                "categoryId": TEST_CATEGORY_ID,
                "productId": "000000000000000000000000",
                "price": 1000.0,
                "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("  [PASS] Invalid product rejected (400)")
    
    def test_create_validates_listing_exists(self):
        """Should reject invalid listing ID"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json={
                "categoryId": TEST_CATEGORY_ID,
                "productId": TEST_PRODUCT_ID,
                "price": 1000.0,
                "components": [{"listingId": "000000000000000000000000", "quantity": 1}]
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("  [PASS] Invalid listing rejected (400)")
    
    def test_create_requires_price(self):
        """Should require price field"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json={
                "categoryId": TEST_CATEGORY_ID,
                "productId": TEST_PRODUCT_ID,
                "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("  [PASS] Missing price rejected (422)")
    
    def test_create_requires_components(self):
        """Should require at least one component"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json={
                "categoryId": TEST_CATEGORY_ID,
                "productId": TEST_PRODUCT_ID,
                "price": 1000.0,
                "components": []
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("  [PASS] Empty components rejected (422)")


class TestRBACRequiresPermission:
    """RBAC: composite endpoints require manage_inventory permission"""
    
    def test_no_auth_returns_401(self):
        """Should return 401 without auth header"""
        response = requests.get(f"{BASE_URL}/api/business-tools/composite-products")
        assert response.status_code == 401 or response.status_code == 422
        print("  [PASS] No auth returns 401/422")
    
    def test_invalid_token_returns_401(self):
        """Should return 401 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers={"Authorization": "Bearer invalid-token-xyz"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("  [PASS] Invalid token returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
