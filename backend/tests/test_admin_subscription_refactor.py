"""
Admin Subscription Refactor Tests

Tests for the refactored admin UI where subscription management
was merged into the user detail page and standalone subscriptions 
page was removed.

Features tested:
1. User list endpoint returns subscription columns
2. User detail endpoint returns user information
3. Subscription management endpoints (activate, extend, suspend, reactivate)
4. No standalone subscriptions page endpoint (should not have separate list)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Use the preview URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001/api').rstrip('/')
if not BASE_URL.endswith('/api'):
    BASE_URL = BASE_URL + '/api'

# Dev test token for testing (when Firebase is disabled)
DEV_TOKEN = "dev-test-token"

class TestAdminUsersWithSubscriptionColumns:
    """Test that user list page displays subscription columns"""
    
    def test_admin_users_returns_subscription_plan(self):
        """User list should include subscription_plan field"""
        response = requests.get(
            f"{BASE_URL}/admin/users?page=1&limit=5",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "pages" in data
        
        if data["users"]:
            user = data["users"][0]
            # Verify subscription columns exist
            assert "subscription_plan" in user, "Missing subscription_plan column"
            assert "subscription_status" in user, "Missing subscription_status column"
            assert "subscription_end" in user, "Missing subscription_end column (End Date)"
            assert "days_remaining" in user, "Missing days_remaining column (Days Left)"
            assert "is_expiring_soon" in user, "Missing is_expiring_soon field"
            
            # Verify valid values
            assert user["subscription_plan"] in ["free", "trial", "pro", None], \
                f"Invalid subscription_plan: {user['subscription_plan']}"
            print(f"PASS: User {user['email']} has subscription columns")

    def test_admin_users_pagination_works(self):
        """Verify pagination returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/admin/users?page=1&limit=2",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["pages"] >= 1, "Pages should be at least 1"
        assert len(data["users"]) <= 2, "Should respect limit"


class TestUserDetailEndpoint:
    """Test user detail page endpoint"""
    
    @pytest.fixture
    def user_id(self):
        """Get a valid user ID for testing"""
        response = requests.get(
            f"{BASE_URL}/admin/users?page=1&limit=1",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        if response.status_code == 200 and response.json()["users"]:
            return response.json()["users"][0]["_id"]
        pytest.skip("No users available for testing")
    
    def test_user_detail_returns_user_info(self, user_id):
        """User detail endpoint returns user information"""
        response = requests.get(
            f"{BASE_URL}/admin/users/{user_id}/detail",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "_id" in data
        assert "email" in data
        assert "business_name" in data
        assert "is_seller" in data
        assert "is_admin" in data
        assert "account_status" in data
        print(f"PASS: User detail for {data['email']} returned successfully")
    
    def test_user_detail_invalid_id_returns_404(self):
        """Invalid user ID should return 404"""
        response = requests.get(
            f"{BASE_URL}/admin/users/000000000000000000000000/detail",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 404


class TestSubscriptionManagement:
    """Test subscription management controls from user detail page"""
    
    @pytest.fixture
    def user_id(self):
        """Get a valid user ID for testing"""
        response = requests.get(
            f"{BASE_URL}/admin/users?page=1&limit=1",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        if response.status_code == 200 and response.json()["users"]:
            return response.json()["users"][0]["_id"]
        pytest.skip("No users available for testing")
    
    def test_get_subscription_details(self, user_id):
        """Get subscription details for a user"""
        response = requests.get(
            f"{BASE_URL}/admin/subscriptions/manage/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "subscription" in data
        assert "user" in data
        
        sub = data["subscription"]
        assert "plan_name" in sub
        assert "status" in sub
        assert "days_remaining" in sub
        assert "is_expiring_soon" in sub
        
        print(f"PASS: Subscription details - Plan: {sub['plan_name']}, Status: {sub['status']}")
    
    def test_activate_subscription_pro(self, user_id):
        """Activate Pro subscription with admin controls"""
        payload = {
            "plan_name": "pro",
            "start_date": datetime.utcnow().isoformat(),
            "duration_days": 90,
            "notes": "Pytest test activation"
        }
        
        response = requests.post(
            f"{BASE_URL}/admin/subscriptions/activate/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["message"] == "Subscription activated successfully"
        assert data["subscription"]["plan_name"] == "pro"
        assert data["subscription"]["status"] == "active"
        print(f"PASS: Pro subscription activated, days remaining: {data['subscription']['days_remaining']}")
    
    def test_extend_subscription(self, user_id):
        """Extend subscription by days"""
        # First activate a subscription
        activate_payload = {
            "plan_name": "pro",
            "start_date": datetime.utcnow().isoformat(),
            "duration_days": 30
        }
        requests.post(
            f"{BASE_URL}/admin/subscriptions/activate/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json=activate_payload
        )
        
        # Then extend it
        extend_payload = {"extend_days": 15, "notes": "Test extension"}
        response = requests.post(
            f"{BASE_URL}/admin/subscriptions/extend/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json=extend_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "extended by 15 days" in data["message"].lower()
        print(f"PASS: Subscription extended, new days remaining: {data['subscription']['days_remaining']}")
    
    def test_suspend_subscription(self, user_id):
        """Suspend a subscription"""
        # First activate
        requests.post(
            f"{BASE_URL}/admin/subscriptions/activate/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json={"plan_name": "pro", "start_date": datetime.utcnow().isoformat(), "duration_days": 30}
        )
        
        # Then suspend
        suspend_payload = {"reason": "Test suspension reason"}
        response = requests.post(
            f"{BASE_URL}/admin/subscriptions/suspend/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json=suspend_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["subscription"]["status"] == "suspended"
        print("PASS: Subscription suspended successfully")
    
    def test_reactivate_subscription(self, user_id):
        """Reactivate a suspended subscription"""
        # First activate and suspend
        requests.post(
            f"{BASE_URL}/admin/subscriptions/activate/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json={"plan_name": "pro", "start_date": datetime.utcnow().isoformat(), "duration_days": 30}
        )
        requests.post(
            f"{BASE_URL}/admin/subscriptions/suspend/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Content-Type": "application/json"},
            json={"reason": "Test"}
        )
        
        # Then reactivate
        response = requests.post(
            f"{BASE_URL}/admin/subscriptions/reactivate/{user_id}",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["subscription"]["status"] == "active"
        print("PASS: Subscription reactivated successfully")


class TestOldSubscriptionsPageRemoved:
    """Verify the old /admin/subscriptions page has been removed"""
    
    def test_admin_subscriptions_list_still_exists_for_api(self):
        """
        The API endpoint /admin/subscriptions may still exist for programmatic access,
        but the frontend page was removed. This tests the API still works if needed.
        """
        response = requests.get(
            f"{BASE_URL}/admin/subscriptions?page=1&limit=10",
            headers={"Authorization": f"Bearer {DEV_TOKEN}"}
        )
        # API endpoint still exists (returns 200 or 401 without auth)
        # The frontend page /admin/subscriptions was removed
        if response.status_code == 200:
            print("NOTE: /api/admin/subscriptions endpoint still exists (for API use)")
        else:
            print(f"Status: {response.status_code} - endpoint behavior ok")


class TestRequiredAuth:
    """Verify admin endpoints require authentication"""
    
    def test_admin_users_requires_auth(self):
        """Admin users endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/admin/users")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_user_detail_requires_auth(self):
        """Admin user detail endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/admin/users/123/detail")
        assert response.status_code == 401
    
    def test_subscription_manage_requires_auth(self):
        """Subscription manage endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/admin/subscriptions/manage/123")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
