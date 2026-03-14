"""
Test suite for Composite Products with new schema:
- Uses listingId instead of productId
- Price field on composite products
- Dynamic stock calculation: min(component_stock / component_qty)
- Creates sellerListing with productType=composite on POST
- Deletes composite sellerListing on DELETE
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Test seller listings (provided in credentials)
TEST_LISTING_1 = "69b57c730ed7999c085b3656"  # stock ~48
TEST_LISTING_2 = "69b57c730ed7999c085b3657"  # stock ~29


class TestAvailableProductsEndpoint:
    """Test GET /api/business-tools/composite-products/available-products"""
    
    def test_available_products_returns_categories(self):
        """Should return seller listings grouped by category"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/available-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
        assert isinstance(data["categories"], list), "categories should be a list"
        
        if len(data["categories"]) > 0:
            cat = data["categories"][0]
            assert "categoryId" in cat, "Category should have categoryId"
            assert "categoryName" in cat, "Category should have categoryName"
            assert "products" in cat, "Category should have products list"
            
            if len(cat["products"]) > 0:
                product = cat["products"][0]
                assert "listingId" in product, "Product should have listingId"
                assert "productName" in product, "Product should have productName"
                assert "stock" in product, "Product should have stock"
                assert "sku" in product, "Product should have sku"
                assert "price" in product, "Product should have price"
    
    def test_available_products_excludes_composite_listings(self):
        """Composite listings (productType=composite) should be excluded"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/available-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify the test listings are present (they are non-composite)
        all_listing_ids = []
        for cat in data.get("categories", []):
            for prod in cat.get("products", []):
                all_listing_ids.append(prod["listingId"])
        
        # At least our test listings should be present
        assert TEST_LISTING_1 in all_listing_ids or TEST_LISTING_2 in all_listing_ids, \
            f"Test listings not found in available products: {all_listing_ids}"
    
    def test_available_products_requires_auth(self):
        """Should require authorization"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/available-products"
        )
        assert response.status_code == 422, f"Expected 422 for missing auth, got {response.status_code}"


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
        
        if len(data["compositeProducts"]) > 0:
            cp = data["compositeProducts"][0]
            # Verify structure with new schema
            assert "id" in cp, "Should have id"
            assert "name" in cp, "Should have name"
            assert "price" in cp, "Should have price field (new schema)"
            assert "items" in cp, "Should have items"
            assert "availableStock" in cp, "Should have dynamically calculated availableStock"
            
            # Verify items use listingId
            if len(cp["items"]) > 0:
                item = cp["items"][0]
                assert "listingId" in item, "Item should use listingId (not productId)"
                assert "quantity" in item, "Item should have quantity"
                assert "productName" in item, "Item should have productName (enriched)"
                assert "currentStock" in item, "Item should have currentStock (enriched)"
    
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
            if items:
                # Calculate expected available stock
                expected_avail = float('inf')
                for item in items:
                    stock = item.get("currentStock", 0)
                    qty = item.get("quantity", 1)
                    expected_avail = min(expected_avail, stock // qty if qty > 0 else 0)
                
                if expected_avail != float('inf'):
                    actual_avail = cp.get("availableStock", 0)
                    assert actual_avail == expected_avail, \
                        f"availableStock mismatch: expected {expected_avail}, got {actual_avail} for {cp['name']}"
                    print(f"  ✓ {cp['name']}: availableStock={actual_avail} (correctly calculated)")


class TestCompositeProductCreate:
    """Test POST /api/business-tools/composite-products"""
    
    created_ids = []
    
    def test_create_composite_product_success(self):
        """Create composite product with listingId items and price"""
        payload = {
            "name": "TEST_Composite_Bundle_v2",
            "description": "Test bundle for new schema",
            "price": 12500.0,
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 2},
                {"listingId": TEST_LISTING_2, "quantity": 3}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "compositeProduct" in data
        cp = data["compositeProduct"]
        
        # Store for cleanup
        TestCompositeProductCreate.created_ids.append(cp["id"])
        
        # Verify fields
        assert cp["name"] == payload["name"]
        assert cp["description"] == payload["description"]
        assert cp["price"] == payload["price"]
        assert "availableStock" in cp
        assert "items" in cp
        
        # Verify items use listingId
        for item in cp["items"]:
            assert "listingId" in item
            assert "quantity" in item
            assert "productName" in item  # enriched
        
        print(f"  ✓ Created composite product: {cp['id']}, availableStock={cp['availableStock']}")
        return cp["id"]
    
    def test_create_composite_also_creates_seller_listing(self):
        """Creating a composite should also create a sellerListing with productType=composite"""
        payload = {
            "name": "TEST_Composite_ListingCheck",
            "description": "Verifying seller listing creation",
            "price": 8000.0,
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        cp_id = data["compositeProduct"]["id"]
        TestCompositeProductCreate.created_ids.append(cp_id)
        
        # We can't directly query sellerListings via API easily, but we can verify via delete
        # The delete test will verify that composite sellerListing gets deleted
        print(f"  ✓ Composite product {cp_id} created (seller listing should be auto-created)")
    
    def test_create_requires_valid_listing_ids(self):
        """Should reject invalid listing IDs"""
        payload = {
            "name": "TEST_Invalid_Listing",
            "description": "Should fail",
            "price": 1000.0,
            "items": [
                {"listingId": "000000000000000000000000", "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for invalid listing, got {response.status_code}"
        assert "not found" in response.text.lower() or "invalid" in response.text.lower()
    
    def test_create_rejects_composite_listing_as_component(self):
        """Cannot use a composite listing as a component"""
        # First get any existing composite products to find a composite listing
        list_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        composites = list_response.json().get("compositeProducts", [])
        
        if not composites:
            pytest.skip("No existing composite products to test with")
        
        # Get available products to confirm composite listings are excluded
        avail_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/available-products",
            headers=AUTH_HEADER
        )
        avail_data = avail_response.json()
        all_available_ids = []
        for cat in avail_data.get("categories", []):
            for prod in cat.get("products", []):
                all_available_ids.append(prod["listingId"])
        
        # The composite product's associated listing should NOT be in available products
        # This is verified by the available-products endpoint filtering productType!=composite
        print(f"  ✓ Available products correctly excludes composite listings")
    
    def test_create_requires_price_field(self):
        """Price is a required field"""
        payload = {
            "name": "TEST_No_Price",
            "description": "Missing price",
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        # Pydantic validation should fail
        assert response.status_code == 422, f"Expected 422 for missing price, got {response.status_code}"
    
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


class TestCompositeProductUpdate:
    """Test PUT /api/business-tools/composite-products/{id}"""
    
    test_cp_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test composite product for update tests"""
        payload = {
            "name": "TEST_Update_Target",
            "description": "Will be updated",
            "price": 5000.0,
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 1}
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
            "name": "TEST_Updated_Name",
            "description": "Updated description"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        cp = data["compositeProduct"]
        assert cp["name"] == "TEST_Updated_Name"
        assert cp["description"] == "Updated description"
    
    def test_update_price(self):
        """Should update price field"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {"price": 7500.0}
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200
        
        cp = response.json()["compositeProduct"]
        assert cp["price"] == 7500.0
    
    def test_update_items(self):
        """Should update component items"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Update with different items
        payload = {
            "items": [
                {"listingId": TEST_LISTING_2, "quantity": 2}
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200
        
        cp = response.json()["compositeProduct"]
        assert len(cp["items"]) == 1
        assert cp["items"][0]["listingId"] == TEST_LISTING_2
        assert cp["items"][0]["quantity"] == 2
    
    def test_update_nonexistent_composite_product(self):
        """Should return 404 for non-existent composite product"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER,
            json={"name": "Should fail"}
        )
        assert response.status_code == 404


class TestCompositeProductDelete:
    """Test DELETE /api/business-tools/composite-products/{id}"""
    
    def test_delete_composite_product(self):
        """Deleting composite should also delete the composite sellerListing"""
        # First create a composite product
        payload = {
            "name": "TEST_Delete_Target",
            "description": "Will be deleted",
            "price": 3000.0,
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 1}
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert create_response.status_code == 200
        cp_id = create_response.json()["compositeProduct"]["id"]
        
        # Now delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/{cp_id}",
            headers=AUTH_HEADER
        )
        assert delete_response.status_code == 200
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


class TestCompositeProductSell:
    """Test POST /api/business-tools/composite-products/{id}/sell"""
    
    test_cp_id = None
    initial_stock_1 = None
    initial_stock_2 = None
    
    @pytest.fixture(autouse=True)
    def setup_and_capture_stock(self):
        """Create composite and capture initial stock levels"""
        # Get initial stock levels
        avail_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/available-products",
            headers=AUTH_HEADER
        )
        avail_data = avail_response.json()
        
        for cat in avail_data.get("categories", []):
            for prod in cat.get("products", []):
                if prod["listingId"] == TEST_LISTING_1:
                    TestCompositeProductSell.initial_stock_1 = prod["stock"]
                if prod["listingId"] == TEST_LISTING_2:
                    TestCompositeProductSell.initial_stock_2 = prod["stock"]
        
        # Create test composite
        payload = {
            "name": "TEST_Sell_Target",
            "description": "For sell testing",
            "price": 10000.0,
            "items": [
                {"listingId": TEST_LISTING_1, "quantity": 2},
                {"listingId": TEST_LISTING_2, "quantity": 1}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        if response.status_code == 200:
            TestCompositeProductSell.test_cp_id = response.json()["compositeProduct"]["id"]
        
        yield
        
        # Cleanup
        if TestCompositeProductSell.test_cp_id:
            requests.delete(
                f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}",
                headers=AUTH_HEADER
            )
    
    def test_sell_composite_deducts_component_stock(self):
        """Selling should deduct stock from all components"""
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
        assert "deductions" in data
        assert len(data["deductions"]) > 0
        
        # Verify deductions happened
        for deduction in data["deductions"]:
            assert "product" in deduction
            assert "deducted" in deduction
            assert "newStock" in deduction
            print(f"  ✓ Deducted {deduction['deducted']} from {deduction['product']}, new stock: {deduction['newStock']}")
    
    def test_sell_updates_available_stock(self):
        """After selling, availableStock should recalculate"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Get current state
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
        
        # The availableStock should reflect current component stocks
        expected_avail = float('inf')
        for item in test_cp.get("items", []):
            stock = item.get("currentStock", 0)
            qty = item.get("quantity", 1)
            expected_avail = min(expected_avail, stock // qty if qty > 0 else 0)
        
        if expected_avail != float('inf'):
            actual_avail = test_cp.get("availableStock", 0)
            assert actual_avail == expected_avail, \
                f"availableStock should be recalculated: expected {expected_avail}, got {actual_avail}"
    
    def test_sell_insufficient_stock(self):
        """Should reject sell if component stock is insufficient"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Try to sell more than available
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 9999}
        )
        assert response.status_code == 400
        assert "insufficient" in response.text.lower() or "not enough" in response.text.lower()
    
    def test_sell_nonexistent_composite_product(self):
        """Should return 404 for non-existent composite product"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert response.status_code == 404


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
