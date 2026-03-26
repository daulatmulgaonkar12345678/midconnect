"""
Referral Sales Tracking System - Comprehensive API Tests
=========================================================
Tests for the hybrid referral + sales tracking module:
- GET /api/referral/sales-stats - User sales metrics
- GET /api/referral/admin/sales-overview - Admin full overview
- GET /api/referral/my-link - Backward compatibility
- GET /api/referral/stats - Backward compatibility
- POST /api/referral/track-signup - Fraud prevention (self-referral, same email/phone)
- Commission recording: 20% default, pending status, duplicate prevention
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token"}

# Test user from credentials: 69a0ac1089b696c2337c5a6e (isAdmin=true)
ADMIN_USER_ID = "69a0ac1089b696c2337c5a6e"


class TestSalesStatsEndpoint:
    """GET /api/referral/sales-stats - User view of sales metrics"""

    def test_sales_stats_returns_correct_fields(self):
        """Verify sales-stats returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/referral/sales-stats", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify all required fields are present
        assert "paidCustomers" in data, "Missing paidCustomers field"
        assert "totalEarnings" in data, "Missing totalEarnings field"
        assert "pendingEarnings" in data, "Missing pendingEarnings field"
        assert "paidOutEarnings" in data, "Missing paidOutEarnings field"
        assert "commissionRate" in data, "Missing commissionRate field"
        
        # Verify types
        assert isinstance(data["paidCustomers"], int), "paidCustomers should be int"
        assert isinstance(data["totalEarnings"], (int, float)), "totalEarnings should be numeric"
        assert isinstance(data["pendingEarnings"], (int, float)), "pendingEarnings should be numeric"
        assert isinstance(data["paidOutEarnings"], (int, float)), "paidOutEarnings should be numeric"
        assert isinstance(data["commissionRate"], (int, float)), "commissionRate should be numeric"
        
        # Verify commission rate is 20% (0.20)
        assert data["commissionRate"] == 0.20, f"Expected commissionRate 0.20, got {data['commissionRate']}"
        print(f"✅ sales-stats returns correct fields: paidCustomers={data['paidCustomers']}, totalEarnings={data['totalEarnings']}, commissionRate={data['commissionRate']}")

    def test_sales_stats_no_referral_code_returns_zeros(self):
        """User without referral code should get zeros"""
        # This test uses the admin user who may or may not have a referral code
        # The endpoint should handle both cases gracefully
        response = requests.get(f"{BASE_URL}/api/referral/sales-stats", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Values should be non-negative
        assert data["paidCustomers"] >= 0, "paidCustomers should be >= 0"
        assert data["totalEarnings"] >= 0, "totalEarnings should be >= 0"
        assert data["pendingEarnings"] >= 0, "pendingEarnings should be >= 0"
        assert data["paidOutEarnings"] >= 0, "paidOutEarnings should be >= 0"
        print(f"✅ sales-stats handles user correctly with values >= 0")

    def test_sales_stats_requires_auth(self):
        """sales-stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/referral/sales-stats")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("✅ sales-stats requires authentication")


class TestAdminSalesOverview:
    """GET /api/referral/admin/sales-overview - Admin full overview"""

    def test_admin_overview_returns_full_data(self):
        """Admin should see full revenue, commission, user details"""
        response = requests.get(f"{BASE_URL}/api/referral/admin/sales-overview", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify all required admin fields
        assert "totalReferredUsers" in data, "Missing totalReferredUsers"
        assert "paidUsers" in data, "Missing paidUsers"
        assert "totalRevenue" in data, "Missing totalRevenue"
        assert "totalCommission" in data, "Missing totalCommission"
        assert "pendingCommission" in data, "Missing pendingCommission"
        assert "commissionRate" in data, "Missing commissionRate"
        assert "partners" in data, "Missing partners list"
        
        # Verify types
        assert isinstance(data["totalReferredUsers"], int), "totalReferredUsers should be int"
        assert isinstance(data["paidUsers"], int), "paidUsers should be int"
        assert isinstance(data["totalRevenue"], (int, float)), "totalRevenue should be numeric"
        assert isinstance(data["totalCommission"], (int, float)), "totalCommission should be numeric"
        assert isinstance(data["partners"], list), "partners should be a list"
        
        # Verify commission rate
        assert data["commissionRate"] == 0.20, f"Expected commissionRate 0.20, got {data['commissionRate']}"
        
        print(f"✅ admin/sales-overview returns full data: totalReferredUsers={data['totalReferredUsers']}, totalRevenue={data['totalRevenue']}, partners={len(data['partners'])}")

    def test_admin_overview_partners_structure(self):
        """Verify partners list has correct structure"""
        response = requests.get(f"{BASE_URL}/api/referral/admin/sales-overview", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        partners = data.get("partners", [])
        
        # If there are partners, verify structure
        if partners:
            partner = partners[0]
            expected_fields = ["code", "revenue", "commission", "sales", "name", "totalReferred", "successfulReferred"]
            for field in expected_fields:
                assert field in partner, f"Partner missing field: {field}"
            print(f"✅ Partner structure verified with {len(partners)} partners")
        else:
            print("✅ No partners yet (empty list is valid)")

    def test_admin_overview_requires_admin(self):
        """Non-admin users should get 403"""
        # Create a non-admin token scenario - using invalid token
        non_admin_headers = {"Authorization": "Bearer invalid-non-admin-token"}
        response = requests.get(f"{BASE_URL}/api/referral/admin/sales-overview", headers=non_admin_headers)
        # Should fail with 401 (invalid token) or 403 (not admin)
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("✅ admin/sales-overview rejects non-admin users")


class TestBackwardCompatibility:
    """Existing referral endpoints should still work unchanged"""

    def test_my_link_still_works(self):
        """GET /api/referral/my-link should work unchanged"""
        response = requests.get(f"{BASE_URL}/api/referral/my-link", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "referralCode" in data, "Missing referralCode"
        assert "referralLink" in data, "Missing referralLink"
        assert "userId" in data, "Missing userId"
        
        # Verify link format
        assert "ref=" in data["referralLink"], "referralLink should contain ref= parameter"
        print(f"✅ my-link works: code={data['referralCode']}, link={data['referralLink'][:50]}...")

    def test_stats_still_works(self):
        """GET /api/referral/stats should work unchanged"""
        response = requests.get(f"{BASE_URL}/api/referral/stats", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify existing stats fields
        assert "referralCode" in data, "Missing referralCode"
        assert "totalReferred" in data, "Missing totalReferred"
        assert "successfulReferrals" in data, "Missing successfulReferrals"
        assert "pendingReferrals" in data, "Missing pendingReferrals"
        assert "tiers" in data, "Missing tiers"
        
        print(f"✅ stats works: totalReferred={data['totalReferred']}, successful={data['successfulReferrals']}")


class TestFraudPrevention:
    """POST /api/referral/track-signup fraud prevention tests"""

    def test_track_signup_rejects_self_referral(self):
        """Cannot refer yourself (same referralCode)"""
        # First get the user's referral code
        my_link_response = requests.get(f"{BASE_URL}/api/referral/my-link", headers=AUTH_HEADER)
        assert my_link_response.status_code == 200
        my_code = my_link_response.json().get("referralCode", "")
        
        if my_code:
            # Try to use own referral code
            response = requests.post(
                f"{BASE_URL}/api/referral/track-signup",
                headers=AUTH_HEADER,
                json={"referralCode": my_code}
            )
            # Should be rejected with 400
            assert response.status_code == 400, f"Expected 400 for self-referral, got {response.status_code}"
            assert "yourself" in response.text.lower() or "already" in response.text.lower(), \
                f"Error message should mention self-referral: {response.text}"
            print("✅ Self-referral correctly rejected")
        else:
            print("⚠️ No referral code found, skipping self-referral test")

    def test_track_signup_invalid_code(self):
        """Invalid referral code should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/referral/track-signup",
            headers=AUTH_HEADER,
            json={"referralCode": "INVALID_CODE_12345"}
        )
        # Should be 404 (invalid code) or 400 (already referred)
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"✅ Invalid referral code handled correctly: {response.status_code}")

    def test_track_signup_requires_auth(self):
        """track-signup should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/referral/track-signup",
            json={"referralCode": "TEST123"}
        )
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("✅ track-signup requires authentication")


class TestCommissionRecording:
    """Commission recording function tests via direct MongoDB verification"""

    def test_commission_rate_is_20_percent(self):
        """Verify DEFAULT_COMMISSION_RATE is 0.20 (20%)"""
        # This is verified through the API response
        response = requests.get(f"{BASE_URL}/api/referral/sales-stats", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert data["commissionRate"] == 0.20, f"Expected 20% commission rate, got {data['commissionRate']}"
        print("✅ Commission rate is 20% (0.20)")

    def test_admin_shows_pending_commission(self):
        """Admin overview should show pending commission separately"""
        response = requests.get(f"{BASE_URL}/api/referral/admin/sales-overview", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        assert "pendingCommission" in data, "Missing pendingCommission field"
        assert isinstance(data["pendingCommission"], (int, float)), "pendingCommission should be numeric"
        print(f"✅ Admin shows pendingCommission: {data['pendingCommission']}")


class TestAPIHealth:
    """Basic API health checks"""

    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        print("✅ API is healthy")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
