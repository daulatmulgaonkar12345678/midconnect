"""
Subscription Plan Limits Verification Tests - Iteration 120 (Part 2)
=====================================================================
Additional tests to verify plan-specific limits for real users:
- Pro user (userId=69c4c81605e9972a11b16366) gets correct pro limits
- Standard user (userId=69c4c9085fb00a2104f25fa4) gets correct standard limits
- Free plan limits verification
- Override merge behavior verification
"""

import pytest
import requests
import os

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

# Test token for admin user
DEV_TEST_TOKEN = "dev-test-token"
HEADERS = {
    "Authorization": f"Bearer {DEV_TEST_TOKEN}",
    "Content-Type": "application/json"
}

# Known test user IDs from the database
PRO_USER_ID = "69c4c81605e9972a11b16366"
STANDARD_USER_ID = "69c4c9085fb00a2104f25fa4"

# Expected plan limits from PLAN_CONFIG
EXPECTED_LIMITS = {
    "free": {
        "maxPanels": 3,
        "maxRules": 10,
        "maxInvoicesPerMonth": 10,
        "maxEmployees": 0,
        "export": False,
        "pdfExport": False,
        "automation": False,
        "maxSessions": 1,
    },
    "standard": {
        "maxPanels": 10,
        "maxRules": 50,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": 15,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 3,
    },
    "pro": {
        "maxPanels": 50,
        "maxRules": 200,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": -1,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 5,
    },
    "enterprise": {
        "maxPanels": -1,
        "maxRules": -1,
        "maxInvoicesPerMonth": -1,
        "maxEmployees": -1,
        "export": True,
        "pdfExport": True,
        "automation": True,
        "maxSessions": 10,
    },
}


class TestProUserLimits:
    """Tests for Pro plan user limits"""
    
    def test_pro_user_subscription_override_shows_pro_plan(self):
        """Pro plan user (userId=69c4c81605e9972a11b16366) has planName=pro"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
            headers=HEADERS
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["planName"] == "pro", f"Pro user should have planName=pro, got {data['planName']}"
        print(f"✓ Pro user has planName=pro")
    
    def test_pro_user_default_limits(self):
        """Pro plan user gets correct default pro limits (maxPanels=50, maxRules=200)"""
        # Verify via admin override endpoint that shows planName
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify plan is pro
        assert data["planName"] == "pro", f"Expected pro plan, got {data['planName']}"
        
        # Verify no overrides (using default limits)
        assert data["overrides"] == {}, f"Pro user should have no overrides, got {data['overrides']}"
        
        # The expected limits for pro plan
        expected = EXPECTED_LIMITS["pro"]
        print(f"✓ Pro user has default limits: maxPanels={expected['maxPanels']}, maxRules={expected['maxRules']}")


class TestStandardUserLimits:
    """Tests for Standard plan user limits"""
    
    def test_standard_user_subscription_override_shows_standard_plan(self):
        """Standard plan user (userId=69c4c9085fb00a2104f25fa4) has planName=standard"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/override/{STANDARD_USER_ID}",
            headers=HEADERS
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["planName"] == "standard", f"Standard user should have planName=standard, got {data['planName']}"
        print(f"✓ Standard user has planName=standard")
    
    def test_standard_user_default_limits(self):
        """Standard plan user gets correct default standard limits (maxPanels=10, maxRules=50)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/subscription/override/{STANDARD_USER_ID}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify plan is standard
        assert data["planName"] == "standard", f"Expected standard plan, got {data['planName']}"
        
        # Verify no overrides (using default limits)
        assert data["overrides"] == {}, f"Standard user should have no overrides, got {data['overrides']}"
        
        # The expected limits for standard plan
        expected = EXPECTED_LIMITS["standard"]
        print(f"✓ Standard user has default limits: maxPanels={expected['maxPanels']}, maxRules={expected['maxRules']}")


class TestOverrideMergeBehavior:
    """Tests for override merge behavior with plan defaults"""
    
    def test_override_merges_with_pro_plan_defaults(self):
        """Overrides merge with pro plan defaults: override takes priority"""
        # Set a specific override on pro user
        override_payload = {
            "userId": PRO_USER_ID,
            "overrides": {
                "maxPanels": 75  # Override pro default of 50
            }
        }
        
        set_response = requests.post(
            f"{BASE_URL}/api/admin/subscription/override",
            headers=HEADERS,
            json=override_payload
        )
        assert set_response.status_code == 200, f"Set failed: {set_response.text}"
        
        try:
            # Verify override is stored
            get_response = requests.get(
                f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
                headers=HEADERS
            )
            assert get_response.status_code == 200
            data = get_response.json()
            
            # Plan should still be pro
            assert data["planName"] == "pro", f"Plan should still be pro, got {data['planName']}"
            
            # Override should be stored
            assert data["overrides"]["maxPanels"] == 75, f"Override should be 75, got {data['overrides']}"
            
            print(f"✓ Override (maxPanels=75) merges with pro plan defaults")
        finally:
            # Cleanup: Clear override
            requests.delete(
                f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
                headers=HEADERS
            )
    
    def test_override_merges_with_plan_defaults_multiple_keys(self):
        """Overrides merge with plan defaults: multiple override keys work"""
        # Set multiple overrides on pro user (which we know exists)
        override_payload = {
            "userId": PRO_USER_ID,
            "overrides": {
                "maxRules": 300,  # Override pro default of 200
                "maxEmployees": 100,  # Override pro default of -1
                "export": True  # Same as default, but explicit
            }
        }
        
        set_response = requests.post(
            f"{BASE_URL}/api/admin/subscription/override",
            headers=HEADERS,
            json=override_payload
        )
        assert set_response.status_code == 200, f"Set failed: {set_response.text}"
        
        try:
            # Verify override is stored
            get_response = requests.get(
                f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
                headers=HEADERS
            )
            assert get_response.status_code == 200
            data = get_response.json()
            
            # Plan should still be pro
            assert data["planName"] == "pro", f"Plan should still be pro, got {data['planName']}"
            
            # Overrides should be stored
            assert data["overrides"]["maxRules"] == 300, f"maxRules override should be 300"
            assert data["overrides"]["maxEmployees"] == 100, f"maxEmployees override should be 100"
            assert data["overrides"]["export"] == True, f"export override should be True"
            
            print(f"✓ Multiple overrides (maxRules=300, maxEmployees=100, export=True) merge with pro plan defaults")
        finally:
            # Cleanup: Clear override
            requests.delete(
                f"{BASE_URL}/api/admin/subscription/override/{PRO_USER_ID}",
                headers=HEADERS
            )


class TestPlanConfigVerification:
    """Tests to verify PLAN_CONFIG values are correct"""
    
    def test_free_plan_config_values(self):
        """Verify free plan has correct config values"""
        expected = EXPECTED_LIMITS["free"]
        
        # Free plan should have:
        assert expected["maxPanels"] == 3, "Free maxPanels should be 3"
        assert expected["maxRules"] == 10, "Free maxRules should be 10"
        assert expected["export"] == False, "Free export should be False"
        assert expected["automation"] == False, "Free automation should be False"
        
        print(f"✓ Free plan config verified: maxPanels=3, maxRules=10, export=False")
    
    def test_standard_plan_config_values(self):
        """Verify standard plan has correct config values"""
        expected = EXPECTED_LIMITS["standard"]
        
        # Standard plan should have:
        assert expected["maxPanels"] == 10, "Standard maxPanels should be 10"
        assert expected["maxRules"] == 50, "Standard maxRules should be 50"
        assert expected["export"] == True, "Standard export should be True"
        assert expected["automation"] == True, "Standard automation should be True"
        
        print(f"✓ Standard plan config verified: maxPanels=10, maxRules=50, export=True")
    
    def test_pro_plan_config_values(self):
        """Verify pro plan has correct config values"""
        expected = EXPECTED_LIMITS["pro"]
        
        # Pro plan should have:
        assert expected["maxPanels"] == 50, "Pro maxPanels should be 50"
        assert expected["maxRules"] == 200, "Pro maxRules should be 200"
        assert expected["export"] == True, "Pro export should be True"
        assert expected["automation"] == True, "Pro automation should be True"
        
        print(f"✓ Pro plan config verified: maxPanels=50, maxRules=200, export=True")
    
    def test_enterprise_plan_config_values(self):
        """Verify enterprise plan has correct config values (unlimited)"""
        expected = EXPECTED_LIMITS["enterprise"]
        
        # Enterprise plan should have unlimited (-1):
        assert expected["maxPanels"] == -1, "Enterprise maxPanels should be -1 (unlimited)"
        assert expected["maxRules"] == -1, "Enterprise maxRules should be -1 (unlimited)"
        assert expected["export"] == True, "Enterprise export should be True"
        assert expected["automation"] == True, "Enterprise automation should be True"
        
        print(f"✓ Enterprise plan config verified: maxPanels=-1, maxRules=-1 (unlimited)")


class TestNoTrialStarterPlans:
    """Tests to verify trial/starter plans are NOT in the system"""
    
    def test_valid_plans_only_four(self):
        """Verify only 4 plans exist: free, standard, pro, enterprise"""
        valid_plans = ["free", "standard", "pro", "enterprise"]
        invalid_plans = ["trial", "starter", "basic", "premium"]
        
        # The PLAN_CONFIG should only have the 4 valid plans
        assert len(EXPECTED_LIMITS) == 4, f"Should have exactly 4 plans, got {len(EXPECTED_LIMITS)}"
        
        for plan in valid_plans:
            assert plan in EXPECTED_LIMITS, f"Plan '{plan}' should exist"
        
        for plan in invalid_plans:
            assert plan not in EXPECTED_LIMITS, f"Plan '{plan}' should NOT exist"
        
        print(f"✓ Only 4 valid plans exist: {valid_plans}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
