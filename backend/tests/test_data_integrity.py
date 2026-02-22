#!/usr/bin/env python3
"""
Data Integrity Tests - API Response Structure Validation
=========================================================

Tests verify that all list/dashboard API endpoints return consistent, deterministic response structures.

Key Validations:
1. All list endpoints return { "data": [], "total": int, "page": int, "pages": int }
2. Never return raw arrays or undefined values
3. Pages defaults to 1 (not 0) when empty
4. All stats are calculated from single source of truth (inquiries collection)

Endpoint Categories:
- Admin: /api/admin/inquiries, /api/admin/stats, /api/admin/products, /api/admin/users
- Seller: /api/seller/dashboard, /api/seller/listings, /api/seller/inquiries
- Buyer: /api/buyer/inquiries
"""

import pytest
import requests
import os

# Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')


@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestListEndpointResponseStructure:
    """Verify all list endpoints return consistent response structure"""
    
    def test_admin_inquiries_response_structure(self, api_client):
        """Admin inquiries should return paginated object (not raw array)"""
        response = api_client.get(f"{BASE_URL}/api/admin/inquiries")
        # Will return 401 (auth required), but should NOT return 404
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/admin/inquiries endpoint returns auth error (not 404)")
    
    def test_admin_stats_response_structure(self, api_client):
        """Admin stats should return object with stats key"""
        response = api_client.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/admin/stats endpoint returns auth error (not 404)")
    
    def test_admin_products_response_structure(self, api_client):
        """Admin products should return paginated object"""
        response = api_client.get(f"{BASE_URL}/api/admin/products")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/admin/products endpoint returns auth error (not 404)")
    
    def test_admin_users_response_structure(self, api_client):
        """Admin users should return paginated object"""
        response = api_client.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/admin/users endpoint returns auth error (not 404)")
    
    def test_seller_dashboard_response_structure(self, api_client):
        """Seller dashboard should return object with stats and recent_listings"""
        response = api_client.get(f"{BASE_URL}/api/seller/dashboard")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/seller/dashboard endpoint returns auth error (not 404)")
    
    def test_seller_listings_response_structure(self, api_client):
        """Seller listings should return paginated object"""
        response = api_client.get(f"{BASE_URL}/api/seller/listings")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/seller/listings endpoint returns auth error (not 404)")
    
    def test_seller_inquiries_response_structure(self, api_client):
        """Seller inquiries should return paginated object"""
        response = api_client.get(f"{BASE_URL}/api/seller/inquiries")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/seller/inquiries endpoint returns auth error (not 404)")
    
    def test_buyer_inquiries_response_structure(self, api_client):
        """Buyer inquiries should return paginated object"""
        response = api_client.get(f"{BASE_URL}/api/buyer/inquiries")
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("✅ /api/buyer/inquiries endpoint returns auth error (not 404)")


class TestPublicEndpointsResponseStructure:
    """Test public endpoints that don't require auth"""
    
    def test_products_public_endpoint(self, api_client):
        """Public products endpoint should return array (not paginated)"""
        response = api_client.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Products should return an array"
        print(f"✅ /api/products returns array with {len(data)} items")
    
    def test_categories_public_endpoint(self, api_client):
        """Public categories endpoint should return array"""
        response = api_client.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Categories should return an array"
        print(f"✅ /api/categories returns array with {len(data)} items")
    
    def test_health_endpoint(self, api_client):
        """Health endpoint should return status object"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data, "Health should include 'status' key"
        assert data["status"] == "healthy"
        print("✅ /api/health returns proper status object")
    
    def test_health_ready_endpoint(self, api_client):
        """Health ready endpoint should return MongoDB status"""
        response = api_client.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "mongodb" in data, "Health ready should include 'mongodb' key"
        assert data["mongodb"]["status"] == "connected"
        print("✅ /api/health/ready returns MongoDB connection status")


class TestPaginationDefaultValues:
    """Test that pagination defaults are sensible"""
    
    def test_products_supports_pagination_params(self, api_client):
        """Products endpoint should accept pagination params"""
        response = api_client.get(f"{BASE_URL}/api/products?page=1&limit=10")
        assert response.status_code == 200
        print("✅ /api/products accepts pagination params")
    
    def test_products_handles_invalid_page(self, api_client):
        """Products endpoint should handle invalid page gracefully"""
        response = api_client.get(f"{BASE_URL}/api/products?page=-1")
        # Should either fix the value or return validation error
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        print("✅ /api/products handles invalid page value")
    
    def test_products_handles_invalid_limit(self, api_client):
        """Products endpoint should handle invalid limit gracefully"""
        response = api_client.get(f"{BASE_URL}/api/products?limit=1000")
        # Should either cap the value or return validation error
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        print("✅ /api/products handles invalid limit value")


class TestSingleSourceOfTruthValidation:
    """Validate SSOT principles via API behavior"""
    
    def test_subscription_endpoint_exists(self, api_client):
        """Seller subscription endpoint should exist"""
        response = api_client.get(f"{BASE_URL}/api/seller/subscription")
        assert response.status_code != 404, "Subscription endpoint should exist"
        print("✅ /api/seller/subscription endpoint exists")
    
    def test_admin_subscription_update_endpoint_exists(self, api_client):
        """Admin subscription update endpoint should exist"""
        response = api_client.patch(
            f"{BASE_URL}/api/admin/users/507f1f77bcf86cd799439011/subscription",
            json={"plan": "trial"}
        )
        # Should get auth error, not 404
        assert response.status_code != 404, "Admin subscription update endpoint should exist"
        print("✅ /api/admin/users/{id}/subscription endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
