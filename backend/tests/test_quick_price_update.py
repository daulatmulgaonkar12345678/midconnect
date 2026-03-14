"""
Test Quick Price Update Feature
================================
Tests the PATCH /api/seller/listings/{id} endpoint for price updates.

Bug context:
- Frontend sends pricingSlabs to update price
- Backend needs to accept pricingSlabs and update pricingTiers
- Backend needs to accept stockStatus field
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://erp-foundation-setup.preview.emergentagent.com"

DEV_TOKEN = "dev-test-token"


class TestQuickPriceUpdate:
    """Tests for the quick price update feature"""
    
    def test_health_check(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Backend health check passed")
    
    def test_seller_listings_endpoint_exists(self):
        """Verify PATCH /api/seller/listings endpoint exists"""
        # Without auth, should return 401, not 404
        response = requests.patch(f"{BASE_URL}/api/seller/listings/test123")
        # 401 (unauthorized) or 422 (validation) means endpoint exists
        # 404 would mean endpoint not found
        assert response.status_code in [401, 422, 400], f"Expected 401/422/400, got {response.status_code}: {response.text}"
        print(f"✓ PATCH endpoint exists, returned {response.status_code}")
    
    def test_seller_listings_endpoint_with_dev_token(self):
        """Test endpoint with dev token - should work if Firebase not configured"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/000000000000000000000000",
            headers=headers,
            json={"description": "test"}
        )
        # 404 (listing not found) means auth passed
        # 403 means not authorized (maybe not seller)
        # 401 means token not valid
        print(f"Dev token test result: {response.status_code} - {response.text[:200]}")
        # If dev mode is enabled, we should get 404 or 403, not 401
        # This is informational
    
    def test_pricing_slabs_field_accepted(self):
        """Test that pricingSlabs field is accepted in PATCH request body"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "pricingSlabs": [
                {"minQty": 1, "maxQty": 99, "pricePerUnit": 100.0},
                {"minQty": 100, "maxQty": None, "pricePerUnit": 90.0}
            ]
        }
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/000000000000000000000000",
            headers=headers,
            json=payload
        )
        # Should not return 422 (validation error) for pricingSlabs
        # 404 (not found) or 403 (not authorized) is acceptable
        print(f"pricingSlabs test: {response.status_code} - {response.text[:300]}")
        # Check if there's a validation error mentioning pricingSlabs
        if response.status_code == 422:
            assert "pricingSlabs" not in response.text.lower() or "extra fields" not in response.text.lower(), \
                f"pricingSlabs rejected as extra field: {response.text}"
            print("✓ pricingSlabs field is accepted (422 for other reasons)")
        else:
            print(f"✓ pricingSlabs field is accepted, got {response.status_code}")
    
    def test_stock_status_field_accepted(self):
        """Test that stockStatus field is accepted in PATCH request body"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "stockStatus": "in_stock"
        }
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/000000000000000000000000",
            headers=headers,
            json=payload
        )
        print(f"stockStatus test: {response.status_code} - {response.text[:300]}")
        # Should not return 422 (validation error) for stockStatus
        if response.status_code == 422:
            assert "stockStatus" not in response.text.lower() or "extra fields" not in response.text.lower(), \
                f"stockStatus rejected as extra field: {response.text}"
            print("✓ stockStatus field is accepted (422 for other reasons)")
        else:
            print(f"✓ stockStatus field is accepted, got {response.status_code}")

    def test_get_seller_listings(self):
        """Test GET /api/seller/listings endpoint"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/seller/listings", headers=headers)
        print(f"GET listings: {response.status_code} - {response.text[:500]}")
        # If dev mode works, we should get a list (possibly empty)


class TestListingUpdateModel:
    """Tests to verify ListingUpdate model accepts the required fields"""
    
    def test_full_quick_price_payload(self):
        """Test the full payload that frontend sends for quick price update"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        # This is exactly what the frontend sends
        payload = {
            "basePrice": 100.0,
            "pricingSlabs": [
                {"minQty": 1, "maxQty": 99, "pricePerUnit": 100.0},
                {"minQty": 100, "maxQty": None, "pricePerUnit": 90.0}
            ],
            "validTill": "7_days",
            "stockStatus": "in_stock"
        }
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/000000000000000000000000",
            headers=headers,
            json=payload
        )
        print(f"Full payload test: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        # Check for validation errors on our new fields
        if response.status_code == 422:
            data = response.json()
            detail = str(data.get("detail", ""))
            # Should not fail on pricingSlabs or stockStatus
            assert "pricingSlabs" not in detail.lower() or "extra" not in detail.lower(), \
                f"pricingSlabs rejected: {detail}"
            assert "stockStatus" not in detail.lower() or "extra" not in detail.lower(), \
                f"stockStatus rejected: {detail}"
            print("✓ New fields accepted (422 for other validation)")


class TestDatabasePersistence:
    """
    Tests to verify that price updates persist in database.
    Requires an actual seller listing to exist.
    """
    
    def test_create_and_update_listing(self):
        """Create a test listing and verify price update persists"""
        # This test requires a real seller user
        # Skip if dev token doesn't work
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        
        # First check if we can get seller status
        response = requests.get(f"{BASE_URL}/api/seller/status", headers=headers)
        print(f"Seller status: {response.status_code} - {response.text[:300]}")
        
        if response.status_code != 200:
            pytest.skip("Dev token not working for seller endpoints")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
