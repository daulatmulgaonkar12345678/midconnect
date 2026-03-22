"""
Test: Seller Listing Creation - Step 2 Validation Fix
Tests the 400 Bad Request error fix for seller listing creation.

The fix implemented:
1. Frontend validation on 'Continue to Commercial Terms' button
2. Button disabled when no spec template exists
3. Red error block shown when no spec template found
4. Backend rejects listings with empty technical specifications

Test Scenarios:
1. API rejects product with no specTemplateIds
2. API rejects listing with empty attributes
3. API accepts listing with valid attributes
"""

import pytest
import requests
import os

# Use the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doc-builder-preview-1.preview.emergentagent.com')
AUTH_TOKEN = "dev-test-token"

# Test product IDs
PRODUCT_WITHOUT_SPEC_TEMPLATE = "699d629108ac3c22bb591667"  # TEST_NoSpecTemplate_Product
PRODUCT_WITH_SPEC_TEMPLATE = "699be9023cbe1a8c31591668"  # Industrial Electric Motor 5HP


class TestListingCreationValidation:
    """Test that listing creation validates technical specifications correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers for all tests"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }

    def test_reject_product_without_spec_template(self):
        """
        Test 1: Backend rejects listing creation for product without spec template
        Expected: 400 Bad Request with message "Product has no specTemplateIds"
        """
        payload = {
            "productId": PRODUCT_WITHOUT_SPEC_TEMPLATE,
            "attributes": {"test": "value"},
            "sellerRole": "distributor",
            "images": ["https://example.com/image.jpg"],
            "moq": 10,
            "stock": 100,
            "currency": "INR",
            "pricingTiers": [{"minQty": 1, "maxQty": None, "pricePerUnit": 500}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers,
            json=payload
        )
        
        # Assert status code is 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Assert correct error message
        data = response.json()
        assert "specTemplateIds" in data.get("detail", "").lower() or "spec" in data.get("detail", "").lower(), \
            f"Expected error about specTemplateIds, got: {data}"
        
        print(f"✅ Test 1 PASSED: Product without spec template correctly rejected")
        print(f"   Response: {data}")

    def test_reject_empty_attributes(self):
        """
        Test 2: Backend rejects listing with empty technical specifications
        Expected: 400 Bad Request with message about missing attributes
        """
        payload = {
            "productId": PRODUCT_WITH_SPEC_TEMPLATE,
            "attributes": {},  # EMPTY - should be rejected
            "sellerRole": "distributor",
            "images": ["https://example.com/image.jpg"],
            "moq": 10,
            "stock": 100,
            "currency": "INR",
            "pricingTiers": [{"minQty": 1, "maxQty": None, "pricePerUnit": 500}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers,
            json=payload
        )
        
        # Assert status code is 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Assert correct error message about specifications
        data = response.json()
        assert "specifications" in data.get("detail", "").lower() or "attribute" in data.get("detail", "").lower(), \
            f"Expected error about specifications/attributes, got: {data}"
        
        print(f"✅ Test 2 PASSED: Empty attributes correctly rejected")
        print(f"   Response: {data}")

    def test_accept_valid_listing(self):
        """
        Test 3: Backend accepts listing with valid technical specifications
        Expected: 200/201 with listing created successfully
        
        Note: This test may fail if a listing already exists for this variant,
        in which case we expect a 409 Conflict
        """
        payload = {
            "productId": PRODUCT_WITH_SPEC_TEMPLATE,
            "attributes": {
                "power": "5 HP",
                "voltage": "415V",
                "phase": "3 Phase",
                "rpm": 1440,
                "efficiency": "IE3"
            },
            "sellerRole": "manufacturer",
            "images": ["https://images.unsplash.com/photo-1581092921461-eab62e97a780?w=400"],
            "moq": 5,
            "stock": 50,
            "currency": "INR",
            "pricingTiers": [
                {"minQty": 1, "maxQty": 10, "pricePerUnit": 12500},
                {"minQty": 11, "maxQty": 50, "pricePerUnit": 11000},
                {"minQty": 51, "maxQty": None, "pricePerUnit": 9500}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers,
            json=payload
        )
        
        # Accept either success (200/201) or conflict (409 if listing already exists)
        assert response.status_code in [200, 201, 409], \
            f"Expected 200/201/409, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        if response.status_code == 409:
            print(f"✅ Test 3 PASSED: Valid listing correctly processed (already exists)")
            print(f"   Response: Conflict - Listing already exists for this variant")
        else:
            assert "listing" in data or "message" in data, f"Expected listing in response, got: {data}"
            print(f"✅ Test 3 PASSED: Valid listing created successfully")
            print(f"   Response: {data.get('message', 'Listing created')}")

    def test_spec_template_api_returns_null_for_category_without_template(self):
        """
        Test 4: API returns null specTemplate for category without template
        This verifies the frontend can correctly detect when no template exists
        """
        # Category ID for TEST_DI_Cat1 which has no spec template
        category_id = "699bce748dd2e92e3fbc4336"
        
        response = requests.get(
            f"{BASE_URL}/api/seller/categories/{category_id}/spec-template",
            headers=self.headers
        )
        
        # Assert success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Assert specTemplate is null
        assert data.get("specTemplate") is None, f"Expected null specTemplate, got: {data.get('specTemplate')}"
        assert data.get("note") is not None, f"Expected a note explaining why, got: {data}"
        
        print(f"✅ Test 4 PASSED: API correctly returns null specTemplate")
        print(f"   Category: {data.get('category', {}).get('name')}")
        print(f"   Note: {data.get('note')}")

    def test_spec_template_api_returns_template_for_category_with_template(self):
        """
        Test 5: API returns specTemplate for category with template
        """
        # Category ID for Test Category which has Electric Motor Specifications template
        category_id = "699be9023cbe1a8c31591667"
        
        response = requests.get(
            f"{BASE_URL}/api/seller/categories/{category_id}/spec-template",
            headers=self.headers
        )
        
        # Assert success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Assert specTemplate exists with fields
        spec_template = data.get("specTemplate")
        assert spec_template is not None, f"Expected specTemplate, got: {data}"
        assert "fields" in spec_template, f"Expected fields in specTemplate, got: {spec_template}"
        assert len(spec_template.get("fields", [])) > 0, f"Expected at least one field"
        
        print(f"✅ Test 5 PASSED: API correctly returns specTemplate")
        print(f"   Template: {spec_template.get('name')}")
        print(f"   Fields: {len(spec_template.get('fields', []))}")


class TestSellerStatusValidation:
    """Test seller authentication and status endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers for all tests"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }

    def test_seller_status_returns_verified(self):
        """
        Test 6: Seller status endpoint returns verified seller
        """
        response = requests.get(
            f"{BASE_URL}/api/seller/status",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("isSeller") == True, f"Expected isSeller=True, got: {data}"
        assert data.get("gst", {}).get("verified") == True, f"Expected verified GST, got: {data}"
        
        print(f"✅ Test 6 PASSED: Seller status correctly returned")
        print(f"   Permissions: {data.get('permissions')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
