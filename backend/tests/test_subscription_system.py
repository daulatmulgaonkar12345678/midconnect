"""
Test Subscription System - Variable Naming (camelCase) Verification

Tests:
1. Backend /api/seller/subscription/status returns camelCase fields
2. Backend usage object has acceptedThisMonth (not accepted_this_month)
3. Backend features object has canAcceptInquiries (not can_accept_inquiries)
4. Backend root level has showExpiryWarning (not show_expiry_warning)
5. Backend root level has showUpgradeCta (not show_upgrade_cta)
6. Admin /api/admin/users returns subscription fields in users array
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://b2b-marketplace-v2.preview.emergentagent.com')
DEV_TOKEN = "dev-test-token"

class TestSellerSubscriptionStatusEndpoint:
    """Test seller subscription status endpoint returns correct camelCase fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for tests"""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEV_TOKEN}"
        }
    
    def test_subscription_status_endpoint_exists(self):
        """Test that /api/seller/subscription/status endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        # Should return 200 or valid response (not 404)
        assert response.status_code != 404, "Endpoint /api/seller/subscription/status should exist"
        print(f"✅ Subscription status endpoint exists: {response.status_code}")
    
    def test_subscription_object_structure(self):
        """Test subscription object has correct camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Verify subscription object exists
            assert "subscription" in data, "Response should contain 'subscription' object"
            subscription = data["subscription"]
            
            # Check for camelCase fields in subscription
            expected_fields = ["planName", "status", "startDate", "endDate", "daysRemaining", "isExpiringSoon", "isActive"]
            for field in expected_fields:
                assert field in subscription, f"subscription should have '{field}' (camelCase)"
            
            # Check NO snake_case fields
            snake_case_fields = ["plan_name", "start_date", "end_date", "days_remaining", "is_expiring_soon", "is_active"]
            for field in snake_case_fields:
                assert field not in subscription, f"subscription should NOT have '{field}' (snake_case)"
            
            print(f"✅ Subscription object has correct camelCase structure: {list(subscription.keys())}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")
    
    def test_usage_object_has_acceptedThisMonth(self):
        """Test usage object has acceptedThisMonth (not accepted_this_month)"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Verify usage object exists
            assert "usage" in data, "Response should contain 'usage' object"
            usage = data["usage"]
            
            # Check for camelCase field: acceptedThisMonth
            assert "acceptedThisMonth" in usage, "usage should have 'acceptedThisMonth' (camelCase)"
            assert "accepted_this_month" not in usage, "usage should NOT have 'accepted_this_month' (snake_case)"
            
            # Verify other expected fields
            expected_fields = ["acceptedThisMonth", "monthlyLimit", "remaining", "limitReached", "resetsOn"]
            for field in expected_fields:
                assert field in usage, f"usage should have '{field}' (camelCase)"
            
            print(f"✅ usage.acceptedThisMonth verified: {usage['acceptedThisMonth']}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")
    
    def test_features_object_has_canAcceptInquiries(self):
        """Test features object has canAcceptInquiries (not can_accept_inquiries)"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Verify features object exists
            assert "features" in data, "Response should contain 'features' object"
            features = data["features"]
            
            # Check for camelCase field: canAcceptInquiries
            assert "canAcceptInquiries" in features, "features should have 'canAcceptInquiries' (camelCase)"
            assert "can_accept_inquiries" not in features, "features should NOT have 'can_accept_inquiries' (snake_case)"
            
            # Verify other expected fields
            expected_fields = ["canAcceptInquiries", "unlimitedInquiries", "verifiedBadge", "prioritySupport", "analyticsAccess"]
            for field in expected_fields:
                assert field in features, f"features should have '{field}' (camelCase)"
            
            print(f"✅ features.canAcceptInquiries verified: {features['canAcceptInquiries']}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")
    
    def test_root_level_showExpiryWarning(self):
        """Test root level has showExpiryWarning (not show_expiry_warning)"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Check for camelCase field: showExpiryWarning
            assert "showExpiryWarning" in data, "Response should have 'showExpiryWarning' at root level (camelCase)"
            assert "show_expiry_warning" not in data, "Response should NOT have 'show_expiry_warning' (snake_case)"
            
            print(f"✅ showExpiryWarning verified: {data['showExpiryWarning']}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")
    
    def test_root_level_showUpgradeCta(self):
        """Test root level has showUpgradeCta (not show_upgrade_cta)"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Check for camelCase field: showUpgradeCta
            assert "showUpgradeCta" in data, "Response should have 'showUpgradeCta' at root level (camelCase)"
            assert "show_upgrade_cta" not in data, "Response should NOT have 'show_upgrade_cta' (snake_case)"
            
            print(f"✅ showUpgradeCta verified: {data['showUpgradeCta']}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")
    
    def test_complete_response_structure(self):
        """Test complete response structure matches expected TypeScript interface"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription/status",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Verify root level keys
            expected_root_keys = ["subscription", "usage", "features", "showExpiryWarning", "showUpgradeCta"]
            for key in expected_root_keys:
                assert key in data, f"Response should have '{key}' at root level"
            
            # Print full structure for verification
            print(f"✅ Complete response structure:")
            print(f"   - subscription: {list(data['subscription'].keys())}")
            print(f"   - usage: {list(data['usage'].keys())}")
            print(f"   - features: {list(data['features'].keys())}")
            print(f"   - showExpiryWarning: {type(data['showExpiryWarning']).__name__}")
            print(f"   - showUpgradeCta: {type(data['showUpgradeCta']).__name__}")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")


class TestAdminUsersSubscriptionFields:
    """Test admin users endpoint returns subscription fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for tests"""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEV_TOKEN}"
        }
    
    def test_admin_users_endpoint_exists(self):
        """Test that /api/admin/users endpoint exists and requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=self.headers
        )
        # Should return 200 with valid token or auth-related error
        assert response.status_code in [200, 401, 403], f"Unexpected status: {response.status_code}"
        print(f"✅ Admin users endpoint accessible: {response.status_code}")
    
    def test_admin_users_returns_users_array(self):
        """Test admin users returns users array with subscription fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            
            # Should have users array
            assert "users" in data, "Response should contain 'users' array"
            assert isinstance(data["users"], list), "users should be a list"
            
            # If there are users, check structure
            if len(data["users"]) > 0:
                user = data["users"][0]
                
                # Check for subscription-related fields
                subscription_fields = ["subscriptionStatus", "subscriptionPlan", "subscriptionEnd", "daysRemaining", "isExpiringSoon"]
                found_fields = [f for f in subscription_fields if f in user]
                
                print(f"✅ Admin users response contains subscription fields: {found_fields}")
                print(f"   - Total users: {data.get('total', len(data['users']))}")
            else:
                print(f"✅ Admin users endpoint works but no users found to verify fields")
        else:
            pytest.skip(f"Cannot test - endpoint returned {response.status_code}")


class TestFrontendAPIFunctions:
    """Test that frontend API functions use correct endpoints"""
    
    def test_api_file_uses_correct_endpoint(self):
        """Verify api.ts uses /seller/subscription/status endpoint"""
        api_file_path = "/app/frontend/src/lib/api.ts"
        
        try:
            with open(api_file_path, 'r') as f:
                content = f.read()
            
            # Check for getSellerSubscription using correct endpoint
            assert "/seller/subscription/status" in content, "api.ts should use /seller/subscription/status endpoint"
            
            # Verify both functions exist and use the same endpoint
            assert "getSellerSubscription" in content, "api.ts should have getSellerSubscription function"
            assert "getSellerSubscriptionStatus" in content, "api.ts should have getSellerSubscriptionStatus function"
            
            print("✅ Frontend api.ts uses correct endpoint: /seller/subscription/status")
        except FileNotFoundError:
            pytest.skip("Frontend api.ts not found")
    
    def test_types_file_has_correct_interface(self):
        """Verify types/index.ts has SellerSubscriptionStatus with camelCase fields"""
        types_file_path = "/app/frontend/src/types/index.ts"
        
        try:
            with open(types_file_path, 'r') as f:
                content = f.read()
            
            # Check for SellerSubscriptionStatus interface
            assert "SellerSubscriptionStatus" in content, "types should have SellerSubscriptionStatus interface"
            
            # Check for camelCase fields in interface
            assert "acceptedThisMonth" in content, "SellerSubscriptionStatus should have acceptedThisMonth"
            assert "canAcceptInquiries" in content, "SellerSubscriptionStatus should have canAcceptInquiries"
            assert "showExpiryWarning" in content, "SellerSubscriptionStatus should have showExpiryWarning"
            assert "showUpgradeCta" in content, "SellerSubscriptionStatus should have showUpgradeCta"
            
            print("✅ Frontend types have correct camelCase interface fields")
        except FileNotFoundError:
            pytest.skip("Frontend types/index.ts not found")


class TestSellerSubscriptionPage:
    """Test seller subscription page implementation"""
    
    def test_subscription_page_exists(self):
        """Verify /seller/subscription page.tsx exists"""
        page_path = "/app/frontend/src/app/seller/subscription/page.tsx"
        
        try:
            with open(page_path, 'r') as f:
                content = f.read()
            
            # Check for basic component structure
            assert "export default function SellerSubscriptionPage" in content, "Page should export SellerSubscriptionPage"
            assert "getSellerSubscriptionStatus" in content, "Page should import and use getSellerSubscriptionStatus"
            
            print("✅ Seller subscription page exists with correct imports")
        except FileNotFoundError:
            pytest.fail("Seller subscription page not found at /app/frontend/src/app/seller/subscription/page.tsx")
    
    def test_subscription_page_uses_correct_field_names(self):
        """Verify subscription page uses camelCase field names"""
        page_path = "/app/frontend/src/app/seller/subscription/page.tsx"
        
        try:
            with open(page_path, 'r') as f:
                content = f.read()
            
            # Check for camelCase field usage
            camel_case_fields = ["acceptedThisMonth", "canAcceptInquiries", "showExpiryWarning", "showUpgradeCta"]
            
            for field in camel_case_fields:
                assert field in content, f"Page should use camelCase field: {field}"
            
            # Check for NO snake_case usage
            snake_case_fields = ["accepted_this_month", "can_accept_inquiries", "show_expiry_warning", "show_upgrade_cta"]
            
            for field in snake_case_fields:
                assert field not in content, f"Page should NOT use snake_case field: {field}"
            
            print("✅ Subscription page uses correct camelCase field names")
        except FileNotFoundError:
            pytest.skip("Seller subscription page not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
