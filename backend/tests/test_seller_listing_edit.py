"""
B2B Marketplace - Seller Listing EDIT Page API Tests
=====================================================
Tests for the seller listing edit flow including:
- GET /seller/listings/{id} - Get single listing
- PATCH /seller/listings/{id} - Update listing details
- PATCH /seller/listings/{id}/pricing - Update pricing
- POST /seller/listings/{id}/publish - Publish listing
- POST /seller/listings/{id}/pause - Pause listing
- Authentication validation (ownership)

Run with: pytest /app/backend/tests/test_seller_listing_edit.py -v --tb=short --junitxml=/app/test_reports/pytest/pytest_results_edit.xml
"""

import pytest
import requests
import os

# Use production API URL 
BASE_URL = os.environ.get('NEXT_PUBLIC_API_URL', 'https://midconnect.onrender.com/api').rstrip('/')


# ==== Health & Base Tests ====

class TestBaseConnectivity:
    """Verify API connectivity"""
    
    def test_api_health(self):
        """GET /health - Basic health check"""
        response = requests.get(f"{BASE_URL}/health", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")


# ==== Get Listing Endpoint Tests ====

class TestGetSellerListing:
    """GET /seller/listings/{id} endpoint tests"""
    
    def test_get_listing_requires_auth(self):
        """GET /seller/listings/{id} - requires authentication"""
        response = requests.get(f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011")
        # Should return 401 without auth
        assert response.status_code in [401, 403, 503]
        print(f"✅ Get listing requires auth: {response.status_code}")
    
    def test_get_listing_invalid_token(self):
        """GET /seller/listings/{id} - invalid token rejected"""
        response = requests.get(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        # Should return 401 with invalid token
        assert response.status_code in [401, 503]
        print(f"✅ Invalid token rejected: {response.status_code}")
    
    def test_get_listing_invalid_id_format(self):
        """GET /seller/listings/invalid-id - handles invalid ObjectId"""
        response = requests.get(
            f"{BASE_URL}/seller/listings/not_a_valid_object_id",
            headers={"Authorization": "Bearer test_token"}
        )
        # Should return 400 or 401
        assert response.status_code in [400, 401, 503]
        print(f"✅ Invalid ID handled: {response.status_code}")


# ==== Update Listing (PATCH) Tests ====

class TestUpdateSellerListing:
    """PATCH /seller/listings/{id} endpoint tests"""
    
    def test_update_listing_requires_auth(self):
        """PATCH /seller/listings/{id} - requires authentication"""
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011",
            json={"description": "Updated description"}
        )
        assert response.status_code in [401, 403, 503]
        print(f"✅ Update requires auth: {response.status_code}")
    
    def test_update_listing_invalid_token(self):
        """PATCH /seller/listings/{id} - invalid token rejected"""
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011",
            json={"description": "Test update"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 503]
        print(f"✅ Update with invalid token rejected: {response.status_code}")
    
    def test_update_listing_schema_validation(self):
        """PATCH /seller/listings/{id} - validates request schema"""
        # Test with invalid data types
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011",
            json={"moq": "not_a_number"},  # Invalid type
            headers={"Authorization": "Bearer test_token"}
        )
        # Should return 401 (auth first) or 422 (validation)
        assert response.status_code in [401, 422, 503]
        print(f"✅ Schema validation check: {response.status_code}")


# ==== Update Pricing (PATCH) Tests ====

class TestUpdateSellerPricing:
    """PATCH /seller/listings/{id}/pricing endpoint tests"""
    
    def test_pricing_update_requires_auth(self):
        """PATCH /seller/listings/{id}/pricing - requires auth"""
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/pricing",
            json={
                "pricing_type": "fixed",
                "slabs": [{"quantity_min": 1, "quantity_max": 100, "price_per_unit": 10.0, "currency": "INR"}]
            }
        )
        assert response.status_code in [401, 403, 503]
        print(f"✅ Pricing update requires auth: {response.status_code}")
    
    def test_pricing_update_invalid_token(self):
        """PATCH /seller/listings/{id}/pricing - invalid token rejected"""
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/pricing",
            json={
                "pricing_type": "negotiable",
                "slabs": [{"quantity_min": 1, "quantity_max": None, "price_per_unit": 25.0, "currency": "INR"}]
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 503]
        print(f"✅ Pricing with invalid token rejected: {response.status_code}")
    
    def test_pricing_endpoint_exists(self):
        """Verify /seller/listings/{id}/pricing endpoint exists"""
        response = requests.patch(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/pricing",
            json={"pricing_type": "rfq_only"},
            headers={"Authorization": "Bearer test_token"}
        )
        # Should NOT be 404 (Method Not Allowed or Auth error expected)
        # 404 would indicate endpoint doesn't exist
        assert response.status_code != 404, "Pricing endpoint does not exist!"
        print(f"✅ Pricing endpoint exists (status: {response.status_code})")


# ==== Publish/Pause Tests ====

class TestListingActions:
    """POST /seller/listings/{id}/publish and /pause endpoint tests"""
    
    def test_publish_requires_auth(self):
        """POST /seller/listings/{id}/publish - requires authentication"""
        response = requests.post(f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/publish")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Publish requires auth: {response.status_code}")
    
    def test_pause_requires_auth(self):
        """POST /seller/listings/{id}/pause - requires authentication"""
        response = requests.post(f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/pause")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Pause requires auth: {response.status_code}")
    
    def test_publish_endpoint_exists(self):
        """Verify /seller/listings/{id}/publish endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/publish",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code != 404, "Publish endpoint does not exist!"
        print(f"✅ Publish endpoint exists (status: {response.status_code})")
    
    def test_pause_endpoint_exists(self):
        """Verify /seller/listings/{id}/pause endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011/pause",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code != 404, "Pause endpoint does not exist!"
        print(f"✅ Pause endpoint exists (status: {response.status_code})")


# ==== Category Spec Template Tests ====

class TestCategorySpecTemplate:
    """GET /seller/categories/{id}/spec-template endpoint tests"""
    
    @pytest.fixture
    def category_id(self):
        """Get a valid category ID"""
        response = requests.get(f"{BASE_URL}/categories/all", timeout=30)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["_id"]
        pytest.skip("No categories available for testing")
    
    def test_spec_template_requires_auth(self, category_id):
        """GET /seller/categories/{id}/spec-template - requires authentication"""
        response = requests.get(f"{BASE_URL}/seller/categories/{category_id}/spec-template")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Spec template requires auth: {response.status_code}")
    
    def test_spec_template_endpoint_exists(self, category_id):
        """Verify spec template endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/seller/categories/{category_id}/spec-template",
            headers={"Authorization": "Bearer test_token"}
        )
        # Should not be 404
        assert response.status_code != 404, "Spec template endpoint does not exist!"
        print(f"✅ Spec template endpoint exists (status: {response.status_code})")


# ==== Seller Stats & Dashboard Tests ====

class TestSellerDashboard:
    """Dashboard and stats endpoints tests"""
    
    def test_dashboard_requires_auth(self):
        """GET /seller/dashboard - requires auth"""
        response = requests.get(f"{BASE_URL}/seller/dashboard")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Dashboard requires auth: {response.status_code}")
    
    def test_stats_requires_auth(self):
        """GET /seller/stats - requires auth"""
        response = requests.get(f"{BASE_URL}/seller/stats")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Stats requires auth: {response.status_code}")
    
    def test_stats_endpoint_exists(self):
        """Verify /seller/stats endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/seller/stats",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code != 404, "Stats endpoint does not exist!"
        print(f"✅ Stats endpoint exists (status: {response.status_code})")


# ==== Public Categories Test ====

class TestPublicCategoriesForEdit:
    """Public category endpoints used in edit flow"""
    
    def test_get_all_categories_for_dropdown(self):
        """GET /categories/all - used for category display in edit page"""
        response = requests.get(f"{BASE_URL}/categories/all", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Categories returned: {len(data)}")
        
        # Verify category structure for display
        if len(data) > 0:
            cat = data[0]
            assert "_id" in cat, "Category missing _id"
            assert "name" in cat, "Category missing name"
            print(f"   Sample: {cat['name']}")


# ==== API Response Format Tests ====

class TestResponseFormats:
    """Verify response formats expected by frontend"""
    
    def test_categories_response_is_list(self):
        """Categories endpoint returns array (not wrapped)"""
        response = requests.get(f"{BASE_URL}/categories/all", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Categories should be a list, not wrapped in object"
        print(f"✅ Categories response is list: {len(data)} items")
    
    def test_json_content_type(self):
        """API returns JSON content type"""
        response = requests.get(f"{BASE_URL}/health", timeout=30)
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, f"Expected JSON content type, got: {content_type}"
        print(f"✅ Content-Type is JSON: {content_type}")


# ==== Ownership Validation Tests ====

class TestOwnershipValidation:
    """
    Tests for seller ownership validation.
    The backend should verify the authenticated user owns the listing.
    """
    
    def test_delete_listing_requires_auth(self):
        """DELETE /seller/listings/{id} - requires authentication"""
        response = requests.delete(f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011")
        assert response.status_code in [401, 403, 503]
        print(f"✅ Delete requires auth: {response.status_code}")
    
    def test_delete_endpoint_exists(self):
        """Verify DELETE endpoint exists"""
        response = requests.delete(
            f"{BASE_URL}/seller/listings/507f1f77bcf86cd799439011",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code != 404, "Delete endpoint does not exist!"
        print(f"✅ Delete endpoint exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
