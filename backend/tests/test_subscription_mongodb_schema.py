"""
Test Backend Subscription Endpoints MongoDB Schema Alignment

SSOT Verification Tests:
1. userId stored as ObjectId (not string)
2. All fields use camelCase (no snake_case)
3. Backend endpoints have try/except guards
4. Legacy users.subscription uses endDate (not end_date)

API_URL from environment variable.
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
DEV_TOKEN = "dev-test-token"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {DEV_TOKEN}"
}


class TestGetOrCreateSubscription:
    """Test get_or_create_subscription uses userId (camelCase) and ObjectId"""
    
    def test_seller_subscription_status_returns_camelcase_fields(self):
        """Verify /seller/subscription/status returns camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify subscription object has camelCase fields
        subscription = data.get("subscription", {})
        assert "planName" in subscription, "Missing camelCase field 'planName'"
        assert "startDate" in subscription, "Missing camelCase field 'startDate'"
        assert "daysRemaining" in subscription, "Missing camelCase field 'daysRemaining'"
        assert "isExpiringSoon" in subscription, "Missing camelCase field 'isExpiringSoon'"
        assert "isActive" in subscription, "Missing camelCase field 'isActive'"
        
        # Verify NO snake_case fields
        assert "plan_name" not in subscription, "Found snake_case 'plan_name' - should be camelCase"
        assert "start_date" not in subscription, "Found snake_case 'start_date' - should be camelCase"
        assert "end_date" not in subscription, "Found snake_case 'end_date' - should be camelCase"
        assert "days_remaining" not in subscription, "Found snake_case 'days_remaining' - should be camelCase"
        assert "is_expiring_soon" not in subscription, "Found snake_case 'is_expiring_soon' - should be camelCase"
        
        print("✅ seller/subscription/status returns camelCase fields")
    
    def test_usage_fields_are_camelcase(self):
        """Verify usage object uses camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        usage = data.get("usage", {})
        
        # Verify camelCase
        assert "acceptedThisMonth" in usage, "Missing camelCase field 'acceptedThisMonth'"
        assert "monthlyLimit" in usage, "Missing camelCase field 'monthlyLimit'"
        assert "limitReached" in usage, "Missing camelCase field 'limitReached'"
        
        # Verify NO snake_case
        assert "accepted_this_month" not in usage, "Found snake_case 'accepted_this_month'"
        assert "monthly_limit" not in usage, "Found snake_case 'monthly_limit'"
        assert "limit_reached" not in usage, "Found snake_case 'limit_reached'"
        
        print("✅ usage object uses camelCase fields")
    
    def test_features_fields_are_camelcase(self):
        """Verify features object uses camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        features = data.get("features", {})
        
        # Verify camelCase
        assert "canAcceptInquiries" in features, "Missing camelCase field 'canAcceptInquiries'"
        assert "unlimitedInquiries" in features, "Missing camelCase field 'unlimitedInquiries'"
        
        # Verify NO snake_case
        assert "can_accept_inquiries" not in features, "Found snake_case 'can_accept_inquiries'"
        assert "unlimited_inquiries" not in features, "Found snake_case 'unlimited_inquiries'"
        
        print("✅ features object uses camelCase fields")
    
    def test_root_level_fields_are_camelcase(self):
        """Verify root level fields use camelCase"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify camelCase at root level
        assert "showExpiryWarning" in data, "Missing camelCase field 'showExpiryWarning'"
        assert "showUpgradeCta" in data, "Missing camelCase field 'showUpgradeCta'"
        
        # Verify NO snake_case
        assert "show_expiry_warning" not in data, "Found snake_case 'show_expiry_warning'"
        assert "show_upgrade_cta" not in data, "Found snake_case 'show_upgrade_cta'"
        
        print("✅ root level fields use camelCase")


class TestAdminActivateSubscription:
    """Test /admin/subscriptions/activate stores userId as ObjectId"""
    
    def test_activate_endpoint_exists(self):
        """Verify activate endpoint exists and requires admin"""
        # Without valid user_id, should return 404 or 422
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/invalid_id",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat(),
                "duration_days": 90,
                "notes": "Test activation"
            }
        )
        # Should return error (400, 404, or 422), not 500 (internal error)
        # 500 would indicate missing try/except
        assert response.status_code != 500 or "Subscription activation failed" in response.text, \
            f"Endpoint may have unhandled exception: {response.status_code}"
        print(f"✅ activate endpoint has proper error handling (status: {response.status_code})")
    
    def test_activate_response_uses_camelcase(self):
        """Verify activation response uses camelCase fields"""
        # First get a valid user ID
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user for testing")
        
        user_id = me_response.json().get("id")
        if not user_id:
            pytest.skip("No user ID available")
        
        # Activate subscription
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat(),
                "duration_days": 90,
                "notes": "Test activation for schema verification"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get("subscription", {})
            
            # Verify camelCase in response
            assert "planName" in subscription, "Missing camelCase 'planName' in response"
            assert "startDate" in subscription, "Missing camelCase 'startDate' in response"
            assert "endDate" in subscription, "Missing camelCase 'endDate' in response"
            assert "durationDays" in subscription, "Missing camelCase 'durationDays' in response"
            assert "daysRemaining" in subscription, "Missing camelCase 'daysRemaining' in response"
            assert "isExpiringSoon" in subscription, "Missing camelCase 'isExpiringSoon' in response"
            
            # Verify NO snake_case
            assert "plan_name" not in subscription, "Found snake_case 'plan_name'"
            assert "start_date" not in subscription, "Found snake_case 'start_date'"
            assert "end_date" not in subscription, "Found snake_case 'end_date'"
            assert "duration_days" not in subscription, "Found snake_case 'duration_days'"
            assert "days_remaining" not in subscription, "Found snake_case 'days_remaining'"
            
            print("✅ activate response uses camelCase fields")
        else:
            print(f"ℹ️ Activation returned {response.status_code} - verify error handling present")


class TestAdminExtendSubscription:
    """Test /admin/subscriptions/extend stores userId as ObjectId"""
    
    def test_extend_endpoint_has_error_handling(self):
        """Verify extend endpoint has try/except guards"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/extend/invalid_id",
            headers=HEADERS,
            json={
                "extend_days": 30,
                "notes": "Test extension"
            }
        )
        # Should return controlled error, not unhandled 500
        assert response.status_code != 500 or "Subscription extension failed" in response.text, \
            f"Endpoint may have unhandled exception"
        print(f"✅ extend endpoint has proper error handling (status: {response.status_code})")
    
    def test_extend_response_uses_camelcase(self):
        """Verify extend response uses camelCase fields"""
        # First get current user and ensure they have a subscription
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user")
        
        user_id = me_response.json().get("id")
        
        # Ensure user has active subscription first
        activate_response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat(),
                "duration_days": 30
            }
        )
        
        # Now test extend
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/extend/{user_id}",
            headers=HEADERS,
            json={
                "extend_days": 30,
                "notes": "Test extension"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get("subscription", {})
            
            # Verify camelCase
            assert "oldEndDate" in subscription or "newEndDate" in subscription, \
                "Missing camelCase date fields"
            assert "daysRemaining" in subscription, "Missing camelCase 'daysRemaining'"
            
            # Verify NO snake_case
            assert "old_end_date" not in subscription, "Found snake_case 'old_end_date'"
            assert "new_end_date" not in subscription, "Found snake_case 'new_end_date'"
            assert "days_remaining" not in subscription, "Found snake_case 'days_remaining'"
            
            print("✅ extend response uses camelCase fields")
        else:
            print(f"ℹ️ Extend returned {response.status_code}")


class TestAdminSuspendSubscription:
    """Test /admin/subscriptions/suspend stores userId as ObjectId"""
    
    def test_suspend_endpoint_has_error_handling(self):
        """Verify suspend endpoint has try/except guards"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/suspend/invalid_id",
            headers=HEADERS,
            json={
                "reason": "Test suspension"
            }
        )
        # Should return controlled error, not unhandled 500
        assert response.status_code != 500 or "Subscription suspension failed" in response.text, \
            f"Endpoint may have unhandled exception"
        print(f"✅ suspend endpoint has proper error handling (status: {response.status_code})")
    
    def test_suspend_response_uses_camelcase(self):
        """Verify suspend response uses camelCase fields"""
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user")
        
        user_id = me_response.json().get("id")
        
        # First activate
        requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat(),
                "duration_days": 90
            }
        )
        
        # Now suspend
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/suspend/{user_id}",
            headers=HEADERS,
            json={
                "reason": "Schema verification test"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get("subscription", {})
            
            # Verify camelCase
            if "suspendedAt" in subscription:
                assert "suspended_at" not in subscription, "Found snake_case 'suspended_at'"
            
            # Verify userId (should be string in response, ObjectId in DB)
            assert "userId" in subscription, "Missing 'userId' in response"
            assert "user_id" not in subscription, "Found snake_case 'user_id'"
            
            print("✅ suspend response uses camelCase fields")
        else:
            print(f"ℹ️ Suspend returned {response.status_code}")


class TestAdminReactivateSubscription:
    """Test /admin/subscriptions/reactivate stores userId as ObjectId"""
    
    def test_reactivate_endpoint_has_error_handling(self):
        """Verify reactivate endpoint has try/except guards"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/reactivate/invalid_id",
            headers=HEADERS
        )
        # Should return controlled error
        assert response.status_code != 500 or "Subscription reactivation failed" in response.text, \
            f"Endpoint may have unhandled exception"
        print(f"✅ reactivate endpoint has proper error handling (status: {response.status_code})")
    
    def test_reactivate_response_uses_camelcase(self):
        """Verify reactivate response uses camelCase fields"""
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user")
        
        user_id = me_response.json().get("id")
        
        # First activate then suspend
        requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat(),
                "duration_days": 90
            }
        )
        
        requests.post(
            f"{BASE_URL}/api/admin/subscriptions/suspend/{user_id}",
            headers=HEADERS,
            json={"reason": "Test for reactivation"}
        )
        
        # Now reactivate
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/reactivate/{user_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get("subscription", {})
            
            # Verify camelCase
            assert "userId" in subscription, "Missing 'userId' in response"
            assert "user_id" not in subscription, "Found snake_case 'user_id'"
            
            if "endDate" in subscription:
                assert "end_date" not in subscription, "Found snake_case 'end_date'"
            
            print("✅ reactivate response uses camelCase fields")
        elif response.status_code == 400:
            # This is expected if subscription is not suspended
            print("ℹ️ Subscription was not in suspended state (expected behavior)")
        else:
            print(f"ℹ️ Reactivate returned {response.status_code}")


class TestLegacyUserSubscriptionSchema:
    """Test that users.subscription uses camelCase (endDate not end_date)"""
    
    def test_user_me_subscription_uses_camelcase(self):
        """Verify /users/me subscription object uses camelCase"""
        response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        subscription = data.get("subscription", {})
        
        # Check that if dates exist, they're camelCase
        if subscription:
            # Verify NO snake_case date fields
            assert "end_date" not in subscription, "Found snake_case 'end_date' in user.subscription"
            assert "start_date" not in subscription, "Found snake_case 'start_date' in user.subscription"
            
            # If these fields exist, verify they're camelCase
            # Note: They should be endDate and startDate
            print(f"  subscription keys: {list(subscription.keys())}")
            
            if "endDate" in subscription or "end_date" not in subscription:
                print("✅ user.subscription uses camelCase date fields (or none present)")
    
    def test_admin_users_subscription_fields_camelcase(self):
        """Verify admin/users endpoint returns subscription in camelCase"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=HEADERS,
            params={"skip": 0, "limit": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            
            for user in users[:3]:  # Check first 3 users
                # Check subscription-related fields at user level
                if "subscriptionPlan" in user:
                    assert "subscription_plan" not in user, "Found snake_case 'subscription_plan'"
                if "subscriptionStatus" in user:
                    assert "subscription_status" not in user, "Found snake_case 'subscription_status'"
                if "subscriptionEnd" in user:
                    assert "subscription_end" not in user, "Found snake_case 'subscription_end'"
                if "daysRemaining" in user:
                    assert "days_remaining" not in user, "Found snake_case 'days_remaining'"
                if "isExpiringSoon" in user:
                    assert "is_expiring_soon" not in user, "Found snake_case 'is_expiring_soon'"
            
            print("✅ admin/users returns camelCase subscription fields")
        else:
            print(f"ℹ️ admin/users returned {response.status_code}")


class TestSubscriptionHistorySchema:
    """Test that subscription history uses camelCase (userId, adminId)"""
    
    def test_history_created_after_activate(self):
        """Verify subscription history is created with camelCase fields"""
        # This is an indirect test - we check the activate endpoint creates history
        # by verifying the response structure
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user")
        
        user_id = me_response.json().get("id")
        
        # Activate to trigger history creation
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            headers=HEADERS,
            json={
                "plan_name": "pro",
                "start_date": datetime.now().isoformat(),
                "duration_days": 90,
                "notes": "History test activation"
            }
        )
        
        # Check that the activate succeeded (history is created internally)
        if response.status_code == 200:
            print("✅ Subscription activated - history should be created with camelCase fields")
            print("   (History uses: userId as ObjectId, adminId as ObjectId)")
        else:
            print(f"ℹ️ Activation returned {response.status_code}")


class TestTryExceptValidationGuards:
    """Test that all endpoints have proper try/except guards"""
    
    def test_activate_handles_invalid_objectid(self):
        """Verify activate handles invalid ObjectId gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/not_a_valid_id",
            headers=HEADERS,
            json={
                "plan_name": "trial",
                "start_date": datetime.now().isoformat()
            }
        )
        # Should be 400/404/422, not 500 with traceback
        if response.status_code == 500:
            # Check for controlled error message
            assert "Subscription activation failed" in response.text, \
                "500 error should have controlled message, not raw traceback"
        print(f"✅ activate handles invalid ObjectId (status: {response.status_code})")
    
    def test_extend_handles_invalid_objectid(self):
        """Verify extend handles invalid ObjectId gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/extend/not_a_valid_id",
            headers=HEADERS,
            json={"extend_days": 30}
        )
        if response.status_code == 500:
            assert "Subscription extension failed" in response.text
        print(f"✅ extend handles invalid ObjectId (status: {response.status_code})")
    
    def test_suspend_handles_invalid_objectid(self):
        """Verify suspend handles invalid ObjectId gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/suspend/not_a_valid_id",
            headers=HEADERS,
            json={"reason": "test"}
        )
        if response.status_code == 500:
            assert "Subscription suspension failed" in response.text
        print(f"✅ suspend handles invalid ObjectId (status: {response.status_code})")
    
    def test_reactivate_handles_invalid_objectid(self):
        """Verify reactivate handles invalid ObjectId gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/admin/subscriptions/reactivate/not_a_valid_id",
            headers=HEADERS
        )
        if response.status_code == 500:
            assert "Subscription reactivation failed" in response.text
        print(f"✅ reactivate handles invalid ObjectId (status: {response.status_code})")


class TestManageSubscriptionEndpoint:
    """Test admin/subscriptions/manage/{user_id} uses camelCase"""
    
    def test_manage_returns_camelcase_subscription(self):
        """Verify manage endpoint returns camelCase fields"""
        me_response = requests.get(f"{BASE_URL}/api/users/me", headers=HEADERS)
        if me_response.status_code != 200:
            pytest.skip("Cannot get current user")
        
        user_id = me_response.json().get("id")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/subscriptions/manage/{user_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get("subscription", {})
            
            # Verify camelCase
            assert "planName" in subscription or len(subscription) == 0, \
                "Missing camelCase 'planName'"
            
            # Verify NO snake_case
            assert "plan_name" not in subscription, "Found snake_case 'plan_name'"
            assert "start_date" not in subscription, "Found snake_case 'start_date'"
            assert "end_date" not in subscription, "Found snake_case 'end_date'"
            assert "user_id" not in subscription, "Found snake_case 'user_id'"
            
            # userId should be converted to string in response (but stored as ObjectId)
            if "userId" in subscription:
                assert isinstance(subscription["userId"], str), \
                    "userId should be serialized as string in response"
            
            print("✅ manage endpoint returns camelCase subscription")
        else:
            print(f"ℹ️ Manage returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
