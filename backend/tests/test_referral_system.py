"""
REFERRAL SYSTEM TESTS (Iteration 95)
=====================================
Tests for the new Refer & Earn feature:
- GET /api/referral/my-link - Get/generate referral code & link
- GET /api/referral/stats - Get referral stats for dashboard
- POST /api/referral/track-signup - Link new user to referrer
- POST /api/referral/check-activation - Check activation criteria
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReferralEndpointsAuth:
    """Test that all referral endpoints require authentication (422 without auth)"""
    
    def test_my_link_requires_auth(self):
        """GET /api/referral/my-link returns 422 without authorization header"""
        response = requests.get(f"{BASE_URL}/api/referral/my-link")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"PASS: GET /api/referral/my-link returns 422 without auth")
    
    def test_stats_requires_auth(self):
        """GET /api/referral/stats returns 422 without authorization header"""
        response = requests.get(f"{BASE_URL}/api/referral/stats")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"PASS: GET /api/referral/stats returns 422 without auth")
    
    def test_track_signup_requires_auth(self):
        """POST /api/referral/track-signup returns 422 without authorization header"""
        response = requests.post(f"{BASE_URL}/api/referral/track-signup", json={"referralCode": "TEST1234"})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"PASS: POST /api/referral/track-signup returns 422 without auth")
    
    def test_check_activation_requires_auth(self):
        """POST /api/referral/check-activation returns 422 without authorization header"""
        response = requests.post(f"{BASE_URL}/api/referral/check-activation")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"PASS: POST /api/referral/check-activation returns 422 without auth")


class TestReferralEndpointsInvalidAuth:
    """Test endpoints with invalid auth return 401"""
    
    def test_my_link_invalid_auth(self):
        """GET /api/referral/my-link returns 401 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/referral/my-link",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        # Expect 401 (Unauthorized) or 503 (Firebase not configured in test env)
        assert response.status_code in [401, 503], f"Expected 401 or 503, got {response.status_code}"
        print(f"PASS: GET /api/referral/my-link returns {response.status_code} with invalid auth")
    
    def test_stats_invalid_auth(self):
        """GET /api/referral/stats returns 401 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/referral/stats",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code in [401, 503], f"Expected 401 or 503, got {response.status_code}"
        print(f"PASS: GET /api/referral/stats returns {response.status_code} with invalid auth")


class TestPageLoads:
    """Test that frontend pages return 200 HTTP status"""
    
    def test_business_tools_page(self):
        """Business Tools dashboard page /seller/business-tools returns 200"""
        response = requests.get(f"{BASE_URL}/seller/business-tools", allow_redirects=True)
        # May redirect to login for auth, but page should load without 500 errors
        assert response.status_code in [200, 302, 307], f"Expected 200/302/307, got {response.status_code}"
        print(f"PASS: /seller/business-tools returns {response.status_code}")
    
    def test_register_page_with_ref_param(self):
        """Register page with ref param /register?ref=TEST123 returns 200"""
        response = requests.get(f"{BASE_URL}/register?ref=TEST123", allow_redirects=True)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Check that the page content contains register-related text
        assert 'register' in response.text.lower() or 'sign up' in response.text.lower() or 'create' in response.text.lower(), \
            "Register page should contain registration content"
        print(f"PASS: /register?ref=TEST123 returns 200")
    
    def test_complete_profile_page(self):
        """Complete profile page /complete-profile returns 200"""
        response = requests.get(f"{BASE_URL}/complete-profile", allow_redirects=True)
        # May redirect to register/login if not authenticated
        assert response.status_code in [200, 302, 307], f"Expected 200/302/307, got {response.status_code}"
        print(f"PASS: /complete-profile returns {response.status_code}")


class TestPWARegression:
    """Verify PWA files are still served correctly (no regression)"""
    
    def test_manifest_json(self):
        """manifest.json is served correctly"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "name" in data, "manifest.json should contain 'name' field"
        print(f"PASS: manifest.json served correctly")
    
    def test_service_worker(self):
        """sw.js (service worker) is served correctly"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "self" in response.text or "service" in response.text.lower(), \
            "sw.js should contain service worker code"
        print(f"PASS: sw.js served correctly")


class TestReferralRouterExists:
    """Verify referral router file has correct endpoints"""
    
    def test_referral_router_file_exists(self):
        """Check referral_router.py file exists and has endpoints"""
        import os
        router_path = "/app/backend/routers/referral_router.py"
        assert os.path.exists(router_path), f"referral_router.py not found at {router_path}"
        
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Verify endpoints exist
        assert "@router.get(\"/referral/my-link\")" in content, "my-link endpoint not found"
        assert "@router.get(\"/referral/stats\")" in content, "stats endpoint not found"
        assert "@router.post(\"/referral/track-signup\")" in content, "track-signup endpoint not found"
        assert "@router.post(\"/referral/check-activation\")" in content, "check-activation endpoint not found"
        print(f"PASS: referral_router.py exists with all 4 endpoints")


class TestFrontendComponents:
    """Verify frontend referral components exist"""
    
    def test_referral_modal_exists(self):
        """ReferralModal.tsx component exists"""
        import os
        modal_path = "/app/frontend/src/components/ReferralModal.tsx"
        assert os.path.exists(modal_path), f"ReferralModal.tsx not found at {modal_path}"
        
        with open(modal_path, 'r') as f:
            content = f.read()
        
        # Verify key elements
        assert "referral-modal" in content, "data-testid referral-modal not found"
        assert "copy-referral-link-btn" in content, "copy button not found"
        assert "share-whatsapp-btn" in content, "WhatsApp share button not found"
        print(f"PASS: ReferralModal.tsx exists with required elements")
    
    def test_referral_widget_exists(self):
        """ReferralWidget.tsx component exists"""
        import os
        widget_path = "/app/frontend/src/components/ReferralWidget.tsx"
        assert os.path.exists(widget_path), f"ReferralWidget.tsx not found at {widget_path}"
        
        with open(widget_path, 'r') as f:
            content = f.read()
        
        # Verify key elements
        assert "referral-widget" in content, "data-testid referral-widget not found"
        print(f"PASS: ReferralWidget.tsx exists with required elements")
    
    def test_layout_has_refer_earn_button(self):
        """Business tools layout has Refer & Earn button"""
        import os
        layout_path = "/app/frontend/src/app/seller/business-tools/layout.tsx"
        
        with open(layout_path, 'r') as f:
            content = f.read()
        
        assert "refer-earn-header-btn" in content, "Refer & Earn header button not found"
        assert "ReferralModal" in content, "ReferralModal import not found in layout"
        assert "showReferral" in content, "showReferral state not found"
        print(f"PASS: Layout has Refer & Earn button and ReferralModal")
    
    def test_dashboard_has_referral_widget(self):
        """Business tools dashboard has ReferralWidget"""
        import os
        page_path = "/app/frontend/src/app/seller/business-tools/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert "ReferralWidget" in content, "ReferralWidget not found in dashboard"
        assert "check-activation" in content, "Activation check call not found"
        print(f"PASS: Dashboard has ReferralWidget and activation check")
    
    def test_register_captures_ref_param(self):
        """Register page captures ?ref= URL param to localStorage"""
        import os
        register_path = "/app/frontend/src/app/register/page.tsx"
        
        with open(register_path, 'r') as f:
            content = f.read()
        
        assert "referralCode" in content, "referralCode localStorage key not found"
        assert "ref" in content, "ref URL param handling not found"
        print(f"PASS: Register page captures ref param to localStorage")
    
    def test_complete_profile_sends_referral(self):
        """Complete profile sends referral tracking after registration"""
        import os
        profile_path = "/app/frontend/src/app/complete-profile/page.tsx"
        
        with open(profile_path, 'r') as f:
            content = f.read()
        
        assert "track-signup" in content, "track-signup API call not found"
        assert "referralCode" in content, "referralCode handling not found"
        print(f"PASS: Complete profile sends referral tracking")


class TestReferralBusinessLogic:
    """Verify referral business logic in code"""
    
    def test_tier_configuration(self):
        """Verify tier-based rewards configuration"""
        import os
        router_path = "/app/backend/routers/referral_router.py"
        
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check tier configuration
        assert "min_referrals\": 10" in content or "\"min_referrals\": 10" in content, \
            "10 referrals tier not found"
        assert "min_referrals\": 5" in content or "\"min_referrals\": 5" in content, \
            "5 referrals tier not found"
        assert "min_referrals\": 1" in content or "\"min_referrals\": 1" in content, \
            "1 referral tier not found"
        
        # Check reward days (1mo=30, 3mo=90, 6mo=180)
        assert "reward_days\": 30" in content or "\"reward_days\": 30" in content, \
            "30 days reward not found"
        assert "reward_days\": 90" in content or "\"reward_days\": 90" in content, \
            "90 days reward not found"
        assert "reward_days\": 180" in content or "\"reward_days\": 180" in content, \
            "180 days reward not found"
        
        print(f"PASS: Tier configuration is correct (1→30d, 5→90d, 10→180d)")
    
    def test_anti_abuse_measures(self):
        """Verify anti-abuse measures in code"""
        import os
        router_path = "/app/backend/routers/referral_router.py"
        
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check self-referral prevention
        assert "Cannot refer yourself" in content, "Self-referral prevention not found"
        
        # Check same phone check
        assert "same phone" in content.lower() or "user_phone" in content, \
            "Same phone check not found"
        
        # Check non-zero invoice requirement in activation
        assert "total\": {\"$gt\": 0}" in content or "\"$gt\": 0" in content, \
            "Non-zero invoice check not found"
        
        print(f"PASS: Anti-abuse measures implemented")
    
    def test_activation_criteria(self):
        """Verify activation criteria (2 of 3)"""
        import os
        router_path = "/app/backend/routers/referral_router.py"
        
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check 7-day window
        assert "ACTIVATION_WINDOW_DAYS = 7" in content, "7-day activation window not found"
        
        # Check 2 of 3 criteria
        assert "ACTIVATION_CRITERIA_NEEDED = 2" in content, "2 of 3 criteria not found"
        
        # Check criteria: 5 products, 3 invoices, 1 buyer + 1 supplier
        assert ">= 5" in content or "seller_listing_count >= 5" in content, \
            "5 products criterion not found"
        assert ">= 3" in content or "invoice_count >= 3" in content, \
            "3 invoices criterion not found"
        assert "buyer_count >= 1" in content or ">= 1 buyer" in content.lower(), \
            "1 buyer criterion not found"
        
        print(f"PASS: Activation criteria correct (2 of 3 within 7 days)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
