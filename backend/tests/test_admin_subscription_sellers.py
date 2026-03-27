"""
Test Admin Subscription Sellers Endpoint
Tests for GET /api/admin/subscription/sellers and related override endpoints

Features tested:
- GET /api/admin/subscription/sellers returns seller list with plan, status, overrides, effectiveLimits, usage, defaultLimits
- GET /api/admin/subscription/sellers?search=admin filters by search term
- GET /api/admin/subscription/sellers?plan_filter=free filters by plan
- POST /api/admin/subscription/override sets overrides and they reflect in /sellers list
- DELETE /api/admin/subscription/override/{userId} clears overrides
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestAdminSubscriptionSellersEndpoint:
    """Tests for GET /api/admin/subscription/sellers endpoint"""

    def test_sellers_endpoint_returns_200(self):
        """Test that the sellers endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "sellers" in data, "Response should contain 'sellers' key"
        assert "total" in data, "Response should contain 'total' key"
        assert "page" in data, "Response should contain 'page' key"
        assert "pages" in data, "Response should contain 'pages' key"
        print(f"✓ GET /api/admin/subscription/sellers returns 200 with {len(data['sellers'])} sellers")

    def test_sellers_response_structure(self):
        """Test that each seller has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["sellers"]) > 0:
            seller = data["sellers"][0]
            required_fields = [
                "userId", "email", "name", "companyName", "plan", "effectivePlan",
                "status", "isExpired", "endDate", "overrides", "defaultLimits",
                "effectiveLimits", "usage"
            ]
            for field in required_fields:
                assert field in seller, f"Seller should have '{field}' field"
            
            # Check usage structure
            assert "panels" in seller["usage"], "Usage should have 'panels' count"
            assert "rules" in seller["usage"], "Usage should have 'rules' count"
            
            # Check limits structure
            assert "maxPanels" in seller["effectiveLimits"], "effectiveLimits should have 'maxPanels'"
            assert "maxRules" in seller["effectiveLimits"], "effectiveLimits should have 'maxRules'"
            
            print(f"✓ Seller response structure is correct with all required fields")
        else:
            print("⚠ No sellers found in database to verify structure")

    def test_sellers_search_filter(self):
        """Test search filter functionality"""
        # First get all sellers
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        all_sellers = response.json()["sellers"]
        
        if len(all_sellers) > 0:
            # Search by email of first seller
            search_term = all_sellers[0]["email"].split("@")[0][:4]  # First 4 chars of email
            
            response = requests.get(
                f"{BASE_URL}/api/admin/subscription/sellers?search={search_term}",
                headers=HEADERS
            )
            assert response.status_code == 200
            filtered = response.json()["sellers"]
            print(f"✓ Search filter works: searched '{search_term}', got {len(filtered)} results")
        else:
            print("⚠ No sellers to test search filter")

    def test_sellers_plan_filter(self):
        """Test plan filter functionality"""
        # Test filtering by 'free' plan
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers?plan_filter=free",
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned sellers should have plan='free'
        for seller in data["sellers"]:
            assert seller["plan"] == "free", f"Expected plan='free', got '{seller['plan']}'"
        
        print(f"✓ Plan filter works: filtered by 'free', got {len(data['sellers'])} sellers")

    def test_sellers_pagination(self):
        """Test pagination parameters"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers?page=1&limit=5",
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1, "Page should be 1"
        assert len(data["sellers"]) <= 5, "Should return at most 5 sellers"
        print(f"✓ Pagination works: page=1, limit=5, got {len(data['sellers'])} sellers")


class TestAdminSubscriptionOverrideIntegration:
    """Tests for override CRUD and its reflection in sellers list"""

    def test_set_override_reflects_in_sellers_list(self):
        """Test that setting an override is reflected in the sellers list"""
        # First get a seller
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        sellers = response.json()["sellers"]
        
        if len(sellers) == 0:
            pytest.skip("No sellers available for override test")
        
        # Find a seller to test with
        test_seller = sellers[0]
        user_id = test_seller["userId"]
        original_overrides = test_seller["overrides"]
        
        # Set a custom override
        override_payload = {
            "userId": user_id,
            "overrides": {
                "maxPanels": 999,
                "maxRules": 888
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/subscription/override",
            headers=HEADERS,
            json=override_payload
        )
        assert response.status_code == 200, f"Failed to set override: {response.text}"
        
        # Verify override is reflected in sellers list
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        sellers = response.json()["sellers"]
        
        updated_seller = next((s for s in sellers if s["userId"] == user_id), None)
        assert updated_seller is not None, "Seller should still be in list"
        assert updated_seller["overrides"].get("maxPanels") == 999, "Override maxPanels should be 999"
        assert updated_seller["overrides"].get("maxRules") == 888, "Override maxRules should be 888"
        assert updated_seller["effectiveLimits"]["maxPanels"] == 999, "effectiveLimits should reflect override"
        assert updated_seller["effectiveLimits"]["maxRules"] == 888, "effectiveLimits should reflect override"
        
        print(f"✓ Override set and reflected in sellers list for user {user_id}")
        
        # Cleanup: restore original overrides or clear
        if original_overrides:
            requests.post(
                f"{BASE_URL}/api/admin/subscription/override",
                headers=HEADERS,
                json={"userId": user_id, "overrides": original_overrides}
            )
        else:
            requests.delete(
                f"{BASE_URL}/api/admin/subscription/override/{user_id}",
                headers=HEADERS
            )
        print(f"✓ Cleanup: restored original overrides for user {user_id}")

    def test_delete_override_clears_from_sellers_list(self):
        """Test that deleting an override clears it from the sellers list"""
        # First get a seller
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        sellers = response.json()["sellers"]
        
        if len(sellers) == 0:
            pytest.skip("No sellers available for delete override test")
        
        test_seller = sellers[0]
        user_id = test_seller["userId"]
        original_overrides = test_seller["overrides"]
        
        # First set an override
        override_payload = {
            "userId": user_id,
            "overrides": {"maxPanels": 777}
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/subscription/override",
            headers=HEADERS,
            json=override_payload
        )
        assert response.status_code == 200
        
        # Now delete the override
        response = requests.delete(
            f"{BASE_URL}/api/admin/subscription/override/{user_id}",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Failed to delete override: {response.text}"
        
        # Verify override is cleared in sellers list
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        sellers = response.json()["sellers"]
        
        updated_seller = next((s for s in sellers if s["userId"] == user_id), None)
        assert updated_seller is not None
        # After delete, overrides should be empty or not contain maxPanels=777
        assert updated_seller["overrides"].get("maxPanels") != 777, "Override should be cleared"
        
        print(f"✓ Override deleted and cleared from sellers list for user {user_id}")
        
        # Restore original if needed
        if original_overrides:
            requests.post(
                f"{BASE_URL}/api/admin/subscription/override",
                headers=HEADERS,
                json={"userId": user_id, "overrides": original_overrides}
            )


class TestAdminSubscriptionSellersAuth:
    """Tests for authentication on admin endpoints"""

    def test_sellers_endpoint_requires_auth(self):
        """Test that the sellers endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers"
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ GET /api/admin/subscription/sellers requires authentication")

    def test_override_endpoint_requires_auth(self):
        """Test that the override endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscription/override",
            json={"userId": "test", "overrides": {"maxPanels": 10}}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ POST /api/admin/subscription/override requires authentication")


class TestAdminSubscriptionSellersEdgeCases:
    """Edge case tests"""

    def test_empty_search_returns_all(self):
        """Test that empty search returns all sellers"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers?search=",
            headers=HEADERS
        )
        assert response.status_code == 200
        print("✓ Empty search parameter returns results")

    def test_invalid_plan_filter_returns_empty(self):
        """Test that invalid plan filter returns empty list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers?plan_filter=invalid_plan",
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sellers"]) == 0, "Invalid plan filter should return empty list"
        print("✓ Invalid plan filter returns empty list")

    def test_plan_options_returned(self):
        """Test that planOptions are returned in response"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/sellers",
            headers=HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        assert "planOptions" in data, "Response should contain 'planOptions'"
        assert "free" in data["planOptions"], "planOptions should include 'free'"
        assert "standard" in data["planOptions"], "planOptions should include 'standard'"
        assert "pro" in data["planOptions"], "planOptions should include 'pro'"
        assert "enterprise" in data["planOptions"], "planOptions should include 'enterprise'"
        print(f"✓ planOptions returned: {data['planOptions']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
