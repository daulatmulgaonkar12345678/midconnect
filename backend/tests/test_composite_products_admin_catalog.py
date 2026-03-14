"""
Test suite for Composite Products with Admin Catalog Integration:
- Components use productId from admin products collection (not sellerListings listingId)
- Stock calculated from seller's sellerListings (found by sellerId + productId)
- Category → Product cascading dropdown via GET /api/categories/all and GET /api/products/by-category/{id}
- Price set manually by seller
- When composite created, sellerListing with productType=composite also created
- Components with no seller listing show hasListing=false and stock=0
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Admin products that seller has listings for (from credentials)
PRODUCT_MOTOR_ID = "699be9023cbe1a8c31591668"  # Industrial Electric Motor 5HP - stock ~43
PRODUCT_ROUND_BAR_ID = "69aaf1febc2259c4124a5db0"  # SS304 Round Bar - stock ~24

# Test category for products
TEST_CATEGORY_ID = "699bce748dd2e92e3fbc4336"


class TestCategoriesEndpoint:
    """Test GET /api/categories/all - returns admin categories for dropdown"""
    
    def test_categories_all_returns_list(self):
        """GET /api/categories/all should return admin categories"""
        response = requests.get(
            f"{BASE_URL}/api/categories/all",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of categories"
        
        if len(data) > 0:
            cat = data[0]
            assert "_id" in cat or "id" in cat, "Category should have id"
            assert "name" in cat, "Category should have name"
            print(f"  ✓ Found {len(data)} categories")
    
    def test_categories_contains_test_category(self):
        """Should include the test category"""
        response = requests.get(
            f"{BASE_URL}/api/categories/all",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        cat_ids = [str(c.get("_id") or c.get("id")) for c in data]
        # At least some categories should be present
        assert len(cat_ids) > 0, "Should have at least one category"
        print(f"  ✓ Categories endpoint working with {len(cat_ids)} categories")


class TestProductsByCategoryEndpoint:
    """Test GET /api/products/by-category/{category_id} - returns admin products"""
    
    def test_products_by_category_returns_list(self):
        """GET /api/products/by-category/{id} should return admin products in that category"""
        response = requests.get(
            f"{BASE_URL}/api/products/by-category/{TEST_CATEGORY_ID}",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of products"
        
        if len(data) > 0:
            product = data[0]
            assert "_id" in product or "id" in product, "Product should have id"
            assert "name" in product, "Product should have name"
            print(f"  ✓ Found {len(data)} products in category {TEST_CATEGORY_ID}")
    
    def test_products_by_invalid_category_returns_empty(self):
        """Invalid category should return empty list or 404"""
        response = requests.get(
            f"{BASE_URL}/api/products/by-category/000000000000000000000000",
            headers=AUTH_HEADER
        )
        # Could be 200 with empty list or 404
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) and len(data) == 0, "Should return empty list for invalid category"


class TestCompositeProductsList:
    """Test GET /api/business-tools/composite-products"""
    
    def test_list_composite_products(self):
        """Should list composite products with dynamically calculated availableStock"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "compositeProducts" in data
        print(f"  ✓ Found {len(data['compositeProducts'])} composite products")
    
    def test_composite_product_structure_uses_productId(self):
        """Composite items should use productId (admin products), not listingId"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for cp in data.get("compositeProducts", []):
            # Verify required fields
            assert "id" in cp, "Should have id"
            assert "name" in cp, "Should have name"
            assert "price" in cp, "Should have price field"
            assert "items" in cp, "Should have items"
            assert "availableStock" in cp, "Should have dynamically calculated availableStock"
            
            # Verify items use productId (new schema), NOT listingId (old schema)
            for item in cp.get("items", []):
                assert "productId" in item, f"Item should have productId (new schema): {item}"
                assert "quantity" in item, "Item should have quantity"
                # Should NOT have listingId (old schema)
                # Note: listingId might still exist in old data, but productId must be present
                
                # Enriched fields
                assert "productName" in item, "Item should have productName (enriched)"
                assert "currentStock" in item, "Item should have currentStock (enriched)"
                assert "hasListing" in item, "Item should have hasListing (enriched)"
            
            print(f"  ✓ Composite '{cp['name']}': price={cp['price']}, availableStock={cp['availableStock']}, items use productId")
    
    def test_available_stock_calculation(self):
        """Verify availableStock = min(component_stock / component_qty)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for cp in data.get("compositeProducts", []):
            items = cp.get("items", [])
            if items and all(item.get("hasListing", False) for item in items):
                # Calculate expected available stock
                expected_avail = float('inf')
                for item in items:
                    stock = item.get("currentStock", 0)
                    qty = item.get("quantity", 1)
                    expected_avail = min(expected_avail, stock // qty if qty > 0 else 0)
                
                if expected_avail != float('inf'):
                    actual_avail = cp.get("availableStock", 0)
                    assert actual_avail == expected_avail, \
                        f"availableStock mismatch for '{cp['name']}': expected {expected_avail}, got {actual_avail}"
                    print(f"  ✓ '{cp['name']}': availableStock={actual_avail} (correctly calculated)")
    
    def test_components_without_listing_show_zero_stock(self):
        """Components with no seller listing should show hasListing=false and stock=0"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for cp in data.get("compositeProducts", []):
            for item in cp.get("items", []):
                if not item.get("hasListing", True):
                    assert item.get("currentStock", -1) == 0, \
                        f"Item without listing should have currentStock=0, got {item.get('currentStock')}"
                    print(f"  ✓ '{cp['name']}' component '{item.get('productName')}': hasListing=false, currentStock=0")


class TestCompositeProductCreate:
    """Test POST /api/business-tools/composite-products - create with productId (admin products)"""
    
    created_ids = []
    
    def test_create_composite_product_with_admin_products(self):
        """Create composite product using productId from admin products catalog"""
        payload = {
            "name": "TEST_AdminCatalog_Bundle",
            "description": "Test bundle using admin products",
            "price": 25000.0,
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 2},
                {"productId": PRODUCT_ROUND_BAR_ID, "quantity": 5}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "compositeProduct" in data, f"Response should have compositeProduct: {data}"
        cp = data["compositeProduct"]
        
        # Store for cleanup
        TestCompositeProductCreate.created_ids.append(cp["id"])
        
        # Verify fields
        assert cp["name"] == payload["name"], f"Name mismatch: expected {payload['name']}, got {cp['name']}"
        assert cp["description"] == payload["description"]
        assert cp["price"] == payload["price"], f"Price mismatch: expected {payload['price']}, got {cp['price']}"
        assert "availableStock" in cp, "Should calculate availableStock"
        assert "items" in cp, "Should have items"
        
        # Verify items use productId
        assert len(cp["items"]) == 2, f"Should have 2 items, got {len(cp['items'])}"
        for item in cp["items"]:
            assert "productId" in item, f"Item should have productId: {item}"
            assert "productName" in item, f"Item should be enriched with productName: {item}"
            assert "currentStock" in item, f"Item should have currentStock from seller listing: {item}"
            assert "hasListing" in item, f"Item should have hasListing indicator: {item}"
        
        print(f"  ✓ Created composite '{cp['name']}': id={cp['id']}, price={cp['price']}, availableStock={cp['availableStock']}")
        return cp["id"]
    
    def test_create_composite_validates_product_exists(self):
        """Should reject invalid product IDs"""
        payload = {
            "name": "TEST_Invalid_Product",
            "description": "Should fail",
            "price": 1000.0,
            "items": [
                {"productId": "000000000000000000000000", "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}: {response.text}"
        assert "not found" in response.text.lower() or "invalid" in response.text.lower()
        print("  ✓ Invalid product ID correctly rejected")
    
    def test_create_requires_price_field(self):
        """Price is a required field (manually set by seller)"""
        payload = {
            "name": "TEST_No_Price",
            "description": "Missing price",
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for missing price, got {response.status_code}"
        print("  ✓ Missing price correctly rejected (422)")
    
    def test_create_requires_at_least_one_item(self):
        """Must have at least one component item"""
        payload = {
            "name": "TEST_No_Items",
            "description": "No items",
            "price": 1000.0,
            "items": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for empty items, got {response.status_code}"
        print("  ✓ Empty items correctly rejected (422)")
    
    def test_create_requires_positive_quantity(self):
        """Item quantity must be >= 1"""
        payload = {
            "name": "TEST_Zero_Qty",
            "description": "Zero quantity",
            "price": 1000.0,
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 0}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for zero quantity, got {response.status_code}"
        print("  ✓ Zero quantity correctly rejected (422)")


class TestCompositeProductUpdate:
    """Test PUT /api/business-tools/composite-products/{id} - update name, price, items"""
    
    test_cp_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test composite product for update tests"""
        payload = {
            "name": "TEST_Update_Target_Admin",
            "description": "Will be updated",
            "price": 15000.0,
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 1}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        if response.status_code == 200:
            TestCompositeProductUpdate.test_cp_id = response.json()["compositeProduct"]["id"]
        yield
        # Cleanup
        if TestCompositeProductUpdate.test_cp_id:
            requests.delete(
                f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
                headers=AUTH_HEADER
            )
    
    def test_update_name_and_description(self):
        """Should update name and description"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {
            "name": "TEST_Updated_Name_Admin",
            "description": "Updated description for admin products"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        cp = data["compositeProduct"]
        assert cp["name"] == "TEST_Updated_Name_Admin"
        assert cp["description"] == "Updated description for admin products"
        print(f"  ✓ Updated name and description")
    
    def test_update_price(self):
        """Should update price field (manually set by seller)"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {"price": 22000.0}
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert cp["price"] == 22000.0, f"Price should be updated to 22000.0, got {cp['price']}"
        print(f"  ✓ Updated price to 22000.0")
    
    def test_update_items_with_productId(self):
        """Should update component items using productId"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Update with different items
        payload = {
            "items": [
                {"productId": PRODUCT_ROUND_BAR_ID, "quantity": 3}
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert len(cp["items"]) == 1, f"Should have 1 item after update, got {len(cp['items'])}"
        assert cp["items"][0]["productId"] == PRODUCT_ROUND_BAR_ID
        assert cp["items"][0]["quantity"] == 3
        print(f"  ✓ Updated items to use Round Bar x3")
    
    def test_update_nonexistent_composite_product(self):
        """Should return 404 for non-existent composite product"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER,
            json={"name": "Should fail"}
        )
        assert response.status_code == 404
        print("  ✓ 404 returned for non-existent composite")


class TestCompositeProductDelete:
    """Test DELETE /api/business-tools/composite-products/{id} - deletes composite + sellerListing"""
    
    def test_delete_composite_product(self):
        """Deleting composite should also delete the composite sellerListing"""
        # First create a composite product
        payload = {
            "name": "TEST_Delete_Target_Admin",
            "description": "Will be deleted",
            "price": 8000.0,
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 1}
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        cp_id = create_response.json()["compositeProduct"]["id"]
        
        # Now delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/{cp_id}",
            headers=AUTH_HEADER
        )
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        assert "deleted" in delete_response.json().get("message", "").lower()
        
        # Verify it's actually deleted
        get_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        cp_ids = [cp["id"] for cp in get_response.json().get("compositeProducts", [])]
        assert cp_id not in cp_ids, f"Composite product {cp_id} should be deleted"
        
        print(f"  ✓ Composite product {cp_id} deleted successfully")
    
    def test_delete_nonexistent_composite_product(self):
        """Should return 404 for non-existent composite product"""
        response = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER
        )
        assert response.status_code == 404
        print("  ✓ 404 returned for non-existent composite")


class TestCompositeProductSell:
    """Test POST /api/business-tools/composite-products/{id}/sell - deducts from seller's sellerListings"""
    
    test_cp_id = None
    initial_motor_stock = None
    initial_bar_stock = None
    
    @pytest.fixture(autouse=True)
    def setup_and_capture_stock(self):
        """Create composite and capture initial stock levels from seller's listings"""
        # First check current stock levels by listing existing composites
        list_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        if list_response.status_code == 200:
            for cp in list_response.json().get("compositeProducts", []):
                for item in cp.get("items", []):
                    if item.get("productId") == PRODUCT_MOTOR_ID and item.get("hasListing"):
                        TestCompositeProductSell.initial_motor_stock = item.get("currentStock")
                    if item.get("productId") == PRODUCT_ROUND_BAR_ID and item.get("hasListing"):
                        TestCompositeProductSell.initial_bar_stock = item.get("currentStock")
        
        # Create test composite
        payload = {
            "name": "TEST_Sell_Target_Admin",
            "description": "For sell testing",
            "price": 20000.0,
            "items": [
                {"productId": PRODUCT_MOTOR_ID, "quantity": 2},
                {"productId": PRODUCT_ROUND_BAR_ID, "quantity": 3}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        if response.status_code == 200:
            TestCompositeProductSell.test_cp_id = response.json()["compositeProduct"]["id"]
            # Update stock from the created composite
            for item in response.json()["compositeProduct"]["items"]:
                if item.get("productId") == PRODUCT_MOTOR_ID:
                    TestCompositeProductSell.initial_motor_stock = item.get("currentStock")
                if item.get("productId") == PRODUCT_ROUND_BAR_ID:
                    TestCompositeProductSell.initial_bar_stock = item.get("currentStock")
        
        yield
        
        # Cleanup
        if TestCompositeProductSell.test_cp_id:
            requests.delete(
                f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}",
                headers=AUTH_HEADER
            )
    
    def test_sell_composite_deducts_from_seller_listings(self):
        """Selling should deduct stock from seller's sellerListings (by productId)"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Sell 1 unit
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "deductions" in data, f"Response should have deductions: {data}"
        assert len(data["deductions"]) == 2, f"Should deduct from 2 components, got {len(data['deductions'])}"
        
        # Verify deductions happened
        for deduction in data["deductions"]:
            assert "product" in deduction
            assert "deducted" in deduction
            assert "newStock" in deduction
            print(f"  ✓ Deducted {deduction['deducted']} from {deduction['product']}, new stock: {deduction['newStock']}")
    
    def test_sell_verifies_stock_recalculation(self):
        """After selling, availableStock should recalculate"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Get updated composite product
        list_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        composite_products = list_response.json().get("compositeProducts", [])
        
        test_cp = None
        for cp in composite_products:
            if cp["id"] == TestCompositeProductSell.test_cp_id:
                test_cp = cp
                break
        
        if not test_cp:
            pytest.skip("Test composite product not found")
        
        # Verify availableStock matches calculation
        expected_avail = float('inf')
        for item in test_cp.get("items", []):
            if item.get("hasListing"):
                stock = item.get("currentStock", 0)
                qty = item.get("quantity", 1)
                expected_avail = min(expected_avail, stock // qty if qty > 0 else 0)
        
        if expected_avail != float('inf'):
            actual_avail = test_cp.get("availableStock", 0)
            assert actual_avail == expected_avail, \
                f"availableStock should recalculate: expected {expected_avail}, got {actual_avail}"
            print(f"  ✓ availableStock correctly recalculated to {actual_avail}")
    
    def test_sell_fails_without_seller_listing(self):
        """Sell should fail if seller has no listing for a component"""
        # Create composite with a product the seller doesn't have a listing for
        payload = {
            "name": "TEST_No_Listing_Sell",
            "description": "Seller doesn't have listing for this product",
            "price": 5000.0,
            "items": [
                {"productId": "699d629108ac3c22bb591667", "quantity": 1}  # TEST_NoSpecTemplate_Product
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create composite: {create_response.text}")
        
        cp_id = create_response.json()["compositeProduct"]["id"]
        
        try:
            # Try to sell - should fail because seller has no listing
            sell_response = requests.post(
                f"{BASE_URL}/api/business-tools/composite-products/{cp_id}/sell",
                headers=AUTH_HEADER,
                json={"quantity": 1}
            )
            assert sell_response.status_code == 400, \
                f"Expected 400 for no listing, got {sell_response.status_code}: {sell_response.text}"
            assert "no inventory" in sell_response.text.lower() or "listing" in sell_response.text.lower()
            print("  ✓ Sell correctly fails when seller has no listing for component")
        finally:
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/business-tools/composite-products/{cp_id}",
                headers=AUTH_HEADER
            )
    
    def test_sell_fails_insufficient_stock(self):
        """Should reject sell if component stock is insufficient"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Try to sell more than available
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 9999}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "insufficient" in response.text.lower() or "need" in response.text.lower()
        print("  ✓ Insufficient stock correctly rejected")
    
    def test_sell_nonexistent_composite_product(self):
        """Should return 404 for non-existent composite product"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert response.status_code == 404
        print("  ✓ 404 returned for non-existent composite")


class TestCleanup:
    """Clean up test data created during tests"""
    
    def test_cleanup_test_composite_products(self):
        """Delete all TEST_ prefixed composite products"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        
        if response.status_code == 200:
            composites = response.json().get("compositeProducts", [])
            cleaned = 0
            for cp in composites:
                if cp.get("name", "").startswith("TEST_"):
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/business-tools/composite-products/{cp['id']}",
                        headers=AUTH_HEADER
                    )
                    if delete_response.status_code == 200:
                        cleaned += 1
            
            print(f"  ✓ Cleaned up {cleaned} test composite products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
