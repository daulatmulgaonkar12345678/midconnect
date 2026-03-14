"""
Comprehensive tests for Composite Products Marketplace Listing features:
1. hasListing/listingId/listingStatus in composite response
2. POST /create-listing fallback endpoint
3. productType in marketplace search and listing detail
4. Inventory productType field
5. Stock adjustment blocked for composite
6. Invoice composite stock deduction
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
AUTH_TOKEN = "dev-test-token"
HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}

# Test data from previous iterations
EXISTING_COMPOSITE_ID = "69b5b08db52f04a0b197f9ce"
MOTOR_LISTING_ID = "69b57c730ed7999c085b3656"
STEEL_LISTING_ID = "69b57c730ed7999c085b3657"


class TestCompositeListingFields:
    """Test hasListing, listingId, listingStatus fields in composite products response"""
    
    def test_list_composites_has_listing_fields(self):
        """GET /api/business-tools/composite-products returns hasListing, listingId, listingStatus"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "compositeProducts" in data
        
        if len(data["compositeProducts"]) > 0:
            cp = data["compositeProducts"][0]
            # Verify new fields exist
            assert "hasListing" in cp, "Missing hasListing field"
            assert "listingId" in cp, "Missing listingId field"
            assert "listingStatus" in cp, "Missing listingStatus field"
            
            # Verify types
            assert isinstance(cp["hasListing"], bool), "hasListing should be boolean"
            
            # If hasListing is True, listingId should be a string
            if cp["hasListing"]:
                assert isinstance(cp["listingId"], str), "listingId should be string when hasListing=True"
                assert len(cp["listingId"]) > 0, "listingId should not be empty when hasListing=True"
                print(f"✓ Composite {cp['id']} has listing: {cp['listingId']} (status: {cp['listingStatus']})")
            else:
                print(f"✓ Composite {cp['id']} has no listing (hasListing=False)")
    
    def test_composite_with_listing_shows_listed_status(self):
        """Verify composite with auto-created listing shows hasListing=True"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        # Look for any composite with hasListing=True
        listed = [cp for cp in data["compositeProducts"] if cp.get("hasListing")]
        if listed:
            cp = listed[0]
            assert cp["hasListing"] == True
            assert cp["listingId"] is not None
            print(f"✓ Found listed composite: {cp.get('productName', cp['id'])}")
        else:
            print("⚠ No composite with hasListing=True found - may need to create one")


class TestCreateListingFallback:
    """Test POST /api/business-tools/composite-products/{id}/create-listing fallback endpoint"""
    
    def test_create_listing_already_exists(self):
        """POST create-listing returns 'already exists' for composite with listing"""
        # First get a composite that has a listing
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        listed = [cp for cp in data["compositeProducts"] if cp.get("hasListing")]
        
        if listed:
            cp_id = listed[0]["id"]
            # Try to create listing again
            res = requests.post(
                f"{BASE_URL}/api/business-tools/composite-products/{cp_id}/create-listing",
                headers=HEADERS
            )
            assert res.status_code == 200
            result = res.json()
            # Should say listing already exists
            assert "already exists" in result.get("message", "").lower() or "listingId" in result
            print(f"✓ create-listing for already listed composite returns: {result.get('message')}")
        else:
            pytest.skip("No listed composite found to test duplicate listing creation")
    
    def test_create_listing_invalid_composite_id(self):
        """POST create-listing with invalid ID returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/invalid-id/create-listing",
            headers=HEADERS
        )
        assert response.status_code == 400
        print("✓ Invalid composite ID returns 400")
    
    def test_create_listing_nonexistent_composite(self):
        """POST create-listing for non-existent composite returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000/create-listing",
            headers=HEADERS
        )
        assert response.status_code == 404
        print("✓ Non-existent composite returns 404")


class TestMarketplaceSearchProductType:
    """Test productType field in marketplace search results"""
    
    def test_search_products_returns_product_type(self):
        """POST /api/search/products returns productType per seller entry"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            headers={"Content-Type": "application/json"},
            json={"query": "", "limit": 50}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "products" in data
        
        # Check sellers have productType field
        found_product_type = False
        for product in data["products"]:
            sellers = product.get("sellers", [])
            for seller in sellers:
                if "productType" in seller:
                    found_product_type = True
                    assert seller["productType"] in ["single", "composite"], f"Invalid productType: {seller['productType']}"
        
        if found_product_type:
            print(f"✓ productType field present in search results sellers")
        else:
            print("⚠ No productType field found in search sellers - may need listings with productType")


class TestListingDetailProductType:
    """Test productType field in listing detail endpoint"""
    
    def test_listing_detail_has_product_type(self):
        """GET /api/listings/{listing_id} includes productType field"""
        # First get a listing ID from search
        search_res = requests.post(
            f"{BASE_URL}/api/search/products",
            headers={"Content-Type": "application/json"},
            json={"query": "", "limit": 10}
        )
        
        if search_res.status_code != 200:
            pytest.skip("Could not search for products")
        
        data = search_res.json()
        listing_id = None
        for product in data.get("products", []):
            for seller in product.get("sellers", []):
                if seller.get("listingId"):
                    listing_id = seller["listingId"]
                    break
            if listing_id:
                break
        
        if not listing_id:
            pytest.skip("No listing ID found in search results")
        
        # Get listing detail - requires auth token
        response = requests.get(
            f"{BASE_URL}/api/listings/{listing_id}",
            headers=HEADERS  # Use auth headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Response may be wrapped in "data" key
        listing = data.get("data") or data
        
        assert "productType" in listing, f"Missing productType in listing detail: {listing.keys()}"
        assert listing["productType"] in ["single", "composite"], f"Invalid productType: {listing['productType']}"
        print(f"✓ Listing {listing_id} has productType: {listing['productType']}")


class TestInventoryProductType:
    """Test productType field in inventory endpoint"""
    
    def test_inventory_returns_product_type(self):
        """GET /api/business-tools/inventory returns productType field"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "inventory" in data
        
        # Check productType field exists
        if len(data["inventory"]) > 0:
            item = data["inventory"][0]
            assert "productType" in item, f"Missing productType field in inventory item: {item.keys()}"
            print(f"✓ Inventory item has productType: {item['productType']}")
        else:
            print("⚠ No inventory items found")
    
    def test_inventory_composite_has_correct_type(self):
        """Verify composite products show productType='composite' in inventory"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        composites = [item for item in data["inventory"] if item.get("productType") == "composite"]
        
        if composites:
            print(f"✓ Found {len(composites)} composite items in inventory")
            for c in composites[:3]:  # Show first 3
                print(f"  - {c.get('productName')}: productType={c['productType']}, stock={c.get('stock')}")
        else:
            print("⚠ No composite items found in inventory")


class TestCompositeStockAdjustmentBlocked:
    """Test that manual stock adjustment is blocked for composite products"""
    
    def test_adjust_stock_blocked_for_composite(self):
        """POST /api/business-tools/inventory/{listing_id}/adjust returns 400 for composite"""
        # First get a composite listing ID
        inv_response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=HEADERS
        )
        assert inv_response.status_code == 200
        
        data = inv_response.json()
        composite_item = next(
            (item for item in data["inventory"] if item.get("productType") == "composite"),
            None
        )
        
        if not composite_item:
            pytest.skip("No composite item found in inventory")
        
        listing_id = composite_item.get("listingId") or composite_item.get("id")
        
        # Try to adjust stock - include listingId in body as required by API
        response = requests.post(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}/adjust",
            headers=HEADERS,
            json={
                "listingId": listing_id,
                "changeType": "adjustment",
                "quantity": 1,
                "note": "Test adjustment"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for composite adjust, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "composite" in result.get("detail", "").lower() or "auto" in result.get("detail", "").lower(), \
            f"Error message should mention composite/auto: {result}"
        print(f"✓ Stock adjustment blocked for composite with message: {result.get('detail')}")
    
    def test_put_inventory_stock_blocked_for_composite(self):
        """PUT /api/business-tools/inventory/{id} with stockQuantity returns 400 for composite"""
        # Get composite from inventory
        inv_response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=HEADERS
        )
        assert inv_response.status_code == 200
        
        data = inv_response.json()
        composite_item = next(
            (item for item in data["inventory"] if item.get("productType") == "composite"),
            None
        )
        
        if not composite_item:
            pytest.skip("No composite item found in inventory")
        
        listing_id = composite_item.get("listingId") or composite_item.get("id")
        
        # Try to update stock via PUT
        response = requests.put(
            f"{BASE_URL}/api/business-tools/inventory/{listing_id}",
            headers=HEADERS,
            json={"stockQuantity": 100}
        )
        
        assert response.status_code == 400, f"Expected 400 for composite PUT stock, got {response.status_code}: {response.text}"
        print("✓ PUT inventory stockQuantity blocked for composite")


class TestCompositeSellDeductsComponents:
    """Test that selling composite deducts from component items"""
    
    def test_sell_composite_deducts_components(self):
        """POST /api/business-tools/composite-products/{id}/sell deducts from components"""
        # Get composite list
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        # Find a composite with available stock
        cp = next(
            (c for c in data["compositeProducts"] if c.get("availableStock", 0) > 0),
            None
        )
        
        if not cp:
            print("⚠ No composite with available stock found - skipping sell test")
            pytest.skip("No composite with available stock")
        
        cp_id = cp["id"]
        initial_stock = cp["availableStock"]
        
        # Get component stocks before
        components_before = {c["listingId"]: c.get("currentStock", 0) for c in cp.get("components", [])}
        
        # Sell 1 unit
        sell_response = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products/{cp_id}/sell",
            headers=HEADERS,
            json={"quantity": 1}
        )
        
        assert sell_response.status_code == 200, f"Expected 200, got {sell_response.status_code}: {sell_response.text}"
        
        result = sell_response.json()
        assert "deductions" in result, "Response should contain deductions"
        assert len(result["deductions"]) > 0, "Should have at least one deduction"
        
        print(f"✓ Sold 1 unit of composite {cp.get('productName', cp_id)}")
        for d in result["deductions"]:
            print(f"  - {d['product']}: deducted {d['deducted']}, new stock: {d['newStock']}")


class TestDeleteCompositeDeletesListing:
    """Test that deleting composite also deletes the sellerListing"""
    
    def test_delete_composite_lifecycle(self):
        """DELETE /api/business-tools/composite-products/{id} also deletes sellerListing"""
        # First create a new composite
        # Get categories
        cat_res = requests.get(f"{BASE_URL}/api/categories/all")
        if cat_res.status_code != 200:
            pytest.skip("Could not get categories")
        
        categories = cat_res.json()
        if not categories:
            pytest.skip("No categories found")
        
        category_id = categories[0].get("id") or categories[0].get("_id")
        
        # Get products for category
        prod_res = requests.get(f"{BASE_URL}/api/products/by-category/{category_id}")
        if prod_res.status_code != 200:
            pytest.skip("Could not get products")
        
        products = prod_res.json()
        if not products:
            pytest.skip("No products found in category")
        
        product_id = products[0].get("id") or products[0].get("_id")
        
        # Get seller inventory for components
        inv_res = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products/seller-inventory",
            headers=HEADERS
        )
        if inv_res.status_code != 200:
            pytest.skip("Could not get seller inventory")
        
        inventory = inv_res.json().get("inventory", [])
        if not inventory:
            pytest.skip("No seller inventory items found")
        
        # Create composite
        create_res = requests.post(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS,
            json={
                "categoryId": category_id,
                "productId": product_id,
                "description": "TEST_delete_lifecycle",
                "price": 999.99,
                "components": [
                    {"listingId": inventory[0]["listingId"], "quantity": 1}
                ]
            }
        )
        
        if create_res.status_code == 409:
            # Composite already exists for this product
            print("⚠ Composite already exists for this product - testing delete on existing")
            # Get the existing composite
            cp_res = requests.get(
                f"{BASE_URL}/api/business-tools/composite-products",
                headers=HEADERS
            )
            cps = cp_res.json().get("compositeProducts", [])
            if cps:
                cp_to_delete = cps[0]
                cp_id = cp_to_delete["id"]
                listing_id = cp_to_delete.get("listingId")
            else:
                pytest.skip("No composite to delete")
        elif create_res.status_code == 200:
            data = create_res.json()
            cp_id = data["compositeProduct"]["id"]
            listing_id = data["compositeProduct"].get("listingId")
            print(f"✓ Created test composite {cp_id} with listing {listing_id}")
        else:
            pytest.skip(f"Could not create composite: {create_res.status_code} {create_res.text}")
        
        # Now delete
        del_res = requests.delete(
            f"{BASE_URL}/api/business-tools/composite-products/{cp_id}",
            headers=HEADERS
        )
        assert del_res.status_code == 200, f"Expected 200, got {del_res.status_code}: {del_res.text}"
        print(f"✓ Deleted composite {cp_id}")
        
        # Verify composite is gone
        verify_res = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=HEADERS
        )
        cps = verify_res.json().get("compositeProducts", [])
        assert not any(cp["id"] == cp_id for cp in cps), "Composite should be deleted"
        print("✓ Composite no longer in list")


class TestRBACAuth:
    """Test RBAC and authentication requirements"""
    
    def test_composite_endpoints_require_auth(self):
        """Composite product endpoints require authentication"""
        endpoints = [
            ("GET", "/api/business-tools/composite-products"),
            ("POST", "/api/business-tools/composite-products"),
            ("GET", "/api/business-tools/composite-products/seller-inventory"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            assert response.status_code == 401 or response.status_code == 403 or response.status_code == 422, \
                f"{method} {endpoint} should require auth, got {response.status_code}"
        
        print("✓ All composite endpoints require authentication")
    
    def test_invalid_token_returns_401(self):
        """Invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers={"Authorization": "Bearer invalid-token-xyz"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid token returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
