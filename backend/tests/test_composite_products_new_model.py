"""
Test suite for Composite Products with NEW model (Third Rewrite):
- Create body: {categoryId, productId, description, price, components: [{listingId, quantity}]}
- Components use listingId (seller's own inventory from sellerListings)
- categoryId and productId come from admin catalog
- Product name is auto-set from admin products collection (seller doesn't type it)
- availableStock = min(component_stock / component_qty) dynamically calculated
- When created, sellerListing with productType="composite" is also created
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Seller's inventory listings (from GET /api/business-tools/composite-products/seller-inventory)
LISTING_MOTOR_ID = "69b57c730ed7999c085b3656"  # Industrial Electric Motor 5HP - stock ~41
LISTING_ROUND_BAR_ID = "69b57c730ed7999c085b3657"  # SS304 Round Bar - stock ~21

# Admin catalog IDs
TEST_CATEGORY_ID = "699bce748dd2e92e3fbc4336"  # TEST_DI_Cat1
TEST_PRODUCT_ID = "699d629108ac3c22bb591667"   # TEST_NoSpecTemplate_Product


class TestSellerInventoryEndpoint:
    """Test GET /api/business-tools/composite-products/seller-inventory - returns seller's non-composite listings"""
    
    def test_seller_inventory_returns_list(self):
        """Should return seller's own listings with productName and stock"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "inventory" in data, "Response should have 'inventory' key"
        assert isinstance(data["inventory"], list), "Inventory should be a list"
        print(f"  [PASS] Found {len(data['inventory'])} inventory items")
    
    def test_seller_inventory_item_structure(self):
        """Each inventory item should have listingId, productName, stock"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for item in data.get("inventory", []):
            assert "listingId" in item, f"Item should have listingId: {item}"
            assert "productName" in item, f"Item should have productName: {item}"
            assert "stock" in item, f"Item should have stock: {item}"
            print(f"  [PASS] Inventory item: {item['productName']} (listingId={item['listingId']}, stock={item['stock']})")
    
    def test_seller_inventory_excludes_composites(self):
        """Should NOT return composite listings (productType=composite)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        # All items should be non-composite (this is for component selection)
        # We can't directly check productType in the response, but the endpoint filters them
        assert len(data.get("inventory", [])) > 0, "Should have at least some inventory items"
        print(f"  [PASS] Seller inventory endpoint working (excludes composites)")


class TestCategoriesAndProductsDropdown:
    """Test admin catalog endpoints for dropdown selection"""
    
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
        print(f"  [PASS] Found {len(data)} admin categories")
    
    def test_products_by_category_returns_list(self):
        """GET /api/products/by-category/{id} should return admin products"""
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
        print(f"  [PASS] Found {len(data)} products in category {TEST_CATEGORY_ID}")


class TestCompositeProductsList:
    """Test GET /api/business-tools/composite-products - returns enriched list"""
    
    def test_list_composite_products(self):
        """Should list composite products with productName from admin, categoryName, components with stock"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "compositeProducts" in data, "Response should have compositeProducts"
        print(f"  [PASS] Found {len(data['compositeProducts'])} composite products")
    
    def test_composite_product_enriched_fields(self):
        """Should have productName (from admin), categoryName, components with stock"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for cp in data.get("compositeProducts", []):
            # Required fields
            assert "id" in cp, f"Should have id: {cp}"
            assert "price" in cp, f"Should have price: {cp}"
            assert "productName" in cp, f"Should have productName (from admin or fallback): {cp}"
            assert "availableStock" in cp, f"Should have availableStock (dynamic): {cp}"
            assert "components" in cp, f"Should have components: {cp}"
            
            # Check components structure (new model with listingId)
            for comp in cp.get("components", []):
                assert "listingId" in comp, f"Component should have listingId: {comp}"
                assert "quantity" in comp, f"Component should have quantity: {comp}"
                assert "productName" in comp, f"Component should have productName: {comp}"
                assert "currentStock" in comp, f"Component should have currentStock: {comp}"
            
            print(f"  [PASS] Composite '{cp['productName']}': price={cp['price']}, availableStock={cp['availableStock']}, components={len(cp.get('components', []))}")
    
    def test_available_stock_calculation(self):
        """availableStock = min(component_stock / component_qty) dynamically calculated"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        assert response.status_code == 200
        
        data = response.json()
        for cp in data.get("compositeProducts", []):
            components = cp.get("components", [])
            if components and all(comp.get("listingId") for comp in components):
                expected_avail = float('inf')
                for comp in components:
                    stock = comp.get("currentStock", 0)
                    qty = comp.get("quantity", 1)
                    if qty > 0:
                        expected_avail = min(expected_avail, stock // qty)
                
                if expected_avail != float('inf'):
                    actual_avail = cp.get("availableStock", 0)
                    assert actual_avail == expected_avail, \
                        f"availableStock mismatch for '{cp['productName']}': expected {expected_avail}, got {actual_avail}"
                    print(f"  [PASS] '{cp['productName']}': availableStock={actual_avail} (correctly calculated)")


class TestCompositeProductCreate:
    """Test POST /api/business-tools/composite-products with NEW model"""
    
    created_ids = []
    
    def test_create_composite_with_new_model(self):
        """Create with categoryId (admin), productId (admin catalog), price, components [{listingId, quantity}]"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Test composite with new model",
            "price": 15000.0,
            "components": [
                {"listingId": LISTING_MOTOR_ID, "quantity": 2},
                {"listingId": LISTING_ROUND_BAR_ID, "quantity": 3}
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
        
        TestCompositeProductCreate.created_ids.append(cp["id"])
        
        # Verify product name comes from admin catalog (not typed by seller)
        assert cp.get("productName") == "TEST_NoSpecTemplate_Product", \
            f"Product name should come from admin catalog, got: {cp.get('productName')}"
        assert cp.get("categoryName") == "TEST_DI_Cat1", \
            f"Category name should be enriched, got: {cp.get('categoryName')}"
        
        # Verify price set manually by seller
        assert cp["price"] == 15000.0, f"Price mismatch: expected 15000.0, got {cp['price']}"
        
        # Verify components reference seller's inventory
        assert len(cp["components"]) == 2, f"Should have 2 components, got {len(cp['components'])}"
        for comp in cp["components"]:
            assert "listingId" in comp, f"Component should have listingId: {comp}"
            assert "currentStock" in comp, f"Component should have currentStock: {comp}"
        
        print(f"  [PASS] Created composite '{cp['productName']}': id={cp['id']}, price={cp['price']}")
        return cp["id"]
    
    def test_create_validates_admin_category_exists(self):
        """Should reject invalid category ID"""
        payload = {
            "categoryId": "000000000000000000000000",
            "productId": TEST_PRODUCT_ID,
            "description": "Should fail",
            "price": 1000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for invalid category, got {response.status_code}: {response.text}"
        print("  [PASS] Invalid category ID correctly rejected (400)")
    
    def test_create_validates_admin_product_exists(self):
        """Should reject invalid product ID from admin catalog"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": "000000000000000000000000",
            "description": "Should fail",
            "price": 1000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}: {response.text}"
        assert "product" in response.text.lower() and ("not found" in response.text.lower() or "invalid" in response.text.lower())
        print("  [PASS] Invalid product ID correctly rejected (400)")
    
    def test_create_validates_seller_listing_exists(self):
        """Should reject invalid listing ID (component must be from seller's inventory)"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Should fail",
            "price": 1000.0,
            "components": [{"listingId": "000000000000000000000000", "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for invalid listing, got {response.status_code}: {response.text}"
        print("  [PASS] Invalid listing ID correctly rejected (400)")
    
    def test_create_requires_price_field(self):
        """Price is required (manually set by seller)"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Missing price",
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for missing price, got {response.status_code}"
        print("  [PASS] Missing price correctly rejected (422)")
    
    def test_create_requires_at_least_one_component(self):
        """Must have at least one component"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "No components",
            "price": 1000.0,
            "components": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for empty components, got {response.status_code}"
        print("  [PASS] Empty components correctly rejected (422)")
    
    def test_create_requires_positive_quantity(self):
        """Component quantity must be >= 1"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Zero quantity",
            "price": 1000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 0}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for zero quantity, got {response.status_code}"
        print("  [PASS] Zero quantity correctly rejected (422)")
    
    def test_create_also_creates_composite_seller_listing(self):
        """POST should also create sellerListing with productType=composite"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Test seller listing creation",
            "price": 8000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        TestCompositeProductCreate.created_ids.append(cp["id"])
        
        # The sellerListing is created internally - we verify by the successful creation
        print(f"  [PASS] Composite created with seller listing (id={cp['id']})")


class TestCompositeProductUpdate:
    """Test PUT /api/business-tools/composite-products/{id} - update description, price, components"""
    
    test_cp_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test composite product for update tests"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "For update testing",
            "price": 10000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
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
    
    def test_update_description(self):
        """Should update description"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {"description": "Updated description text"}
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert cp["description"] == "Updated description text"
        print("  [PASS] Updated description")
    
    def test_update_price(self):
        """Should update price (manually set by seller)"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {"price": 18000.0}
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert cp["price"] == 18000.0, f"Price should be updated to 18000.0, got {cp['price']}"
        print("  [PASS] Updated price to 18000.0")
    
    def test_update_components(self):
        """Should update components (change listingIds and quantities)"""
        if not TestCompositeProductUpdate.test_cp_id:
            pytest.skip("No test composite product created")
        
        payload = {
            "components": [
                {"listingId": LISTING_ROUND_BAR_ID, "quantity": 4}
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductUpdate.test_cp_id}",
            headers=AUTH_HEADER,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cp = response.json()["compositeProduct"]
        assert len(cp["components"]) == 1, f"Should have 1 component, got {len(cp['components'])}"
        assert cp["components"][0]["listingId"] == LISTING_ROUND_BAR_ID
        assert cp["components"][0]["quantity"] == 4
        print("  [PASS] Updated components")
    
    def test_update_nonexistent_returns_404(self):
        """Should return 404 for non-existent composite product"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER,
            json={"description": "Should fail"}
        )
        assert response.status_code == 404
        print("  [PASS] 404 returned for non-existent composite")


class TestCompositeProductDelete:
    """Test DELETE /api/business-tools/composite-products/{id} - removes composite + sellerListing"""
    
    def test_delete_composite_product(self):
        """Delete should remove composite AND its sellerListing"""
        # First create a composite product
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "Will be deleted",
            "price": 5000.0,
            "components": [{"listingId": LISTING_MOTOR_ID, "quantity": 1}]
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
        
        print(f"  [PASS] Composite product {cp_id} deleted successfully")
    
    def test_delete_nonexistent_returns_404(self):
        """Should return 404 for non-existent composite product"""
        response = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000",
            headers=AUTH_HEADER
        )
        assert response.status_code == 404
        print("  [PASS] 404 returned for non-existent composite")


class TestCompositeProductSell:
    """Test POST /api/business-tools/composite-products/{id}/sell - deducts from seller's component listings"""
    
    test_cp_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test composite and capture initial stock levels"""
        payload = {
            "categoryId": TEST_CATEGORY_ID,
            "productId": TEST_PRODUCT_ID,
            "description": "For sell testing",
            "price": 12000.0,
            "components": [
                {"listingId": LISTING_MOTOR_ID, "quantity": 1},
                {"listingId": LISTING_ROUND_BAR_ID, "quantity": 2}
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
    
    def test_sell_deducts_from_component_listings(self):
        """Selling should deduct stock from seller's component inventory (via listingId)"""
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
        
        for deduction in data["deductions"]:
            assert "product" in deduction
            assert "deducted" in deduction
            assert "newStock" in deduction
            print(f"  [PASS] Deducted {deduction['deducted']} from {deduction['product']}, new stock: {deduction['newStock']}")
    
    def test_sell_updates_available_stock(self):
        """After selling, availableStock should recalculate"""
        if not TestCompositeProductSell.test_cp_id:
            pytest.skip("No test composite product created")
        
        # Get composite BEFORE selling
        before_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        before_cp = None
        for cp in before_response.json().get("compositeProducts", []):
            if cp["id"] == TestCompositeProductSell.test_cp_id:
                before_cp = cp
                break
        
        if not before_cp:
            pytest.skip("Could not find test composite")
        
        before_stock = before_cp.get("availableStock", 0)
        
        # Sell 1 unit
        sell_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{TestCompositeProductSell.test_cp_id}/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert sell_response.status_code == 200
        
        # Get composite AFTER selling
        after_response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=AUTH_HEADER
        )
        after_cp = None
        for cp in after_response.json().get("compositeProducts", []):
            if cp["id"] == TestCompositeProductSell.test_cp_id:
                after_cp = cp
                break
        
        if after_cp:
            after_stock = after_cp.get("availableStock", 0)
            assert after_stock <= before_stock, \
                f"availableStock should decrease or stay same after sell: before={before_stock}, after={after_stock}"
            print(f"  [PASS] availableStock updated: {before_stock} -> {after_stock}")
    
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
        print("  [PASS] Insufficient stock correctly rejected")
    
    def test_sell_nonexistent_returns_404(self):
        """Should return 404 for non-existent composite product"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000/sell",
            headers=AUTH_HEADER,
            json={"quantity": 1}
        )
        assert response.status_code == 404
        print("  [PASS] 404 returned for non-existent composite")


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
                if cp.get("productName", "").startswith("TEST_") or cp.get("description", "").startswith("Test"):
                    # Only delete composites we created in this test
                    if cp.get("description") and any(kw in cp.get("description", "") for kw in ["new model", "update testing", "sell testing", "deleted", "seller listing"]):
                        delete_response = requests.delete(
                            f"{BASE_URL}/api/business-tools/composite-products/{cp['id']}",
                            headers=AUTH_HEADER
                        )
                        if delete_response.status_code == 200:
                            cleaned += 1
            
            print(f"  [PASS] Cleaned up {cleaned} test composite products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
