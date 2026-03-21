"""
Test Business Tool Access System (3-tier: none/standard/advanced)
Tests:
- GET /api/admin/users/{id}/detail includes businessToolAccess field
- PUT /api/admin/users/{id}/business-tool-access sets access level
- PUT /api/admin/users/{id}/business-tool-access rejects invalid values
- GET /api/business-tools/my-permissions includes businessToolAccess field
- GET /api/business-tools/access-level returns correct level
- Panel CRUD returns 403 for standard access users (note: platform admin bypasses this)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
AUTH_TOKEN = "dev-test-token"
DEV_TEST_USER_ID = "69a0ac1089b696c2337c5a6e"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestAdminUserDetailBusinessToolAccess:
    """Test GET /api/admin/users/{id}/detail includes businessToolAccess"""
    
    def test_user_detail_includes_business_tool_access_field(self):
        """Verify businessToolAccess field is present in user detail response"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/detail",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "businessToolAccess" in data, "businessToolAccess field missing from user detail"
        assert data["businessToolAccess"] in ("none", "standard", "advanced"), \
            f"Invalid businessToolAccess value: {data['businessToolAccess']}"
        print(f"✓ User detail includes businessToolAccess: {data['businessToolAccess']}")
    
    def test_user_detail_returns_correct_user_info(self):
        """Verify user detail returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/detail",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "id" in data or "_id" in data
        assert "email" in data
        assert "isAdmin" in data
        assert "accountStatus" in data
        print(f"✓ User detail returns all expected fields")


class TestAdminSetBusinessToolAccess:
    """Test PUT /api/admin/users/{id}/business-tool-access"""
    
    def test_set_access_level_to_standard(self):
        """Set businessToolAccess to 'standard'"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "standard"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("businessToolAccess") == "standard"
        print("✓ Set businessToolAccess to 'standard' successfully")
    
    def test_set_access_level_to_advanced(self):
        """Set businessToolAccess to 'advanced'"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "advanced"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("businessToolAccess") == "advanced"
        print("✓ Set businessToolAccess to 'advanced' successfully")
    
    def test_set_access_level_to_none(self):
        """Set businessToolAccess to 'none'"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "none"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("businessToolAccess") == "none"
        print("✓ Set businessToolAccess to 'none' successfully")
    
    def test_reject_invalid_access_level(self):
        """Reject invalid businessToolAccess values"""
        invalid_values = ["invalid", "premium", "basic", "", "ADVANCED", "Standard"]
        
        for invalid_value in invalid_values:
            response = requests.put(
                f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
                headers=HEADERS,
                json={"businessToolAccess": invalid_value}
            )
            assert response.status_code == 400, \
                f"Expected 400 for '{invalid_value}', got {response.status_code}: {response.text}"
        
        print(f"✓ Correctly rejected {len(invalid_values)} invalid access level values")
    
    def test_reject_missing_access_level(self):
        """Reject request without businessToolAccess field"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly rejected request without businessToolAccess field")
    
    def test_invalid_user_id_returns_error(self):
        """Invalid user ID returns 400 or 404"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/invalid-id/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "standard"}
        )
        assert response.status_code in (400, 404), \
            f"Expected 400 or 404, got {response.status_code}: {response.text}"
        print("✓ Invalid user ID correctly returns error")
    
    def test_nonexistent_user_returns_404(self):
        """Non-existent user ID returns 404"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/000000000000000000000000/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "standard"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Non-existent user correctly returns 404")


class TestMyPermissionsBusinessToolAccess:
    """Test GET /api/business-tools/my-permissions includes businessToolAccess"""
    
    def test_my_permissions_includes_business_tool_access(self):
        """Verify businessToolAccess field is present in my-permissions response"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "businessToolAccess" in data, "businessToolAccess field missing from my-permissions"
        assert data["businessToolAccess"] in ("none", "standard", "advanced"), \
            f"Invalid businessToolAccess value: {data['businessToolAccess']}"
        print(f"✓ my-permissions includes businessToolAccess: {data['businessToolAccess']}")
    
    def test_platform_admin_gets_advanced_access(self):
        """Platform admin should always get 'advanced' access level"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        # Dev-test-token user is platform admin, should get advanced
        assert data.get("businessToolAccess") == "advanced", \
            f"Platform admin should have 'advanced' access, got: {data.get('businessToolAccess')}"
        assert data.get("isAdmin") == True, "Platform admin should have isAdmin=True"
        print("✓ Platform admin correctly gets 'advanced' businessToolAccess")


class TestAccessLevelEndpoint:
    """Test GET /api/business-tools/access-level"""
    
    def test_access_level_returns_correct_level(self):
        """Verify access-level endpoint returns correct level"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/access-level",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "level" in data, "level field missing from access-level response"
        assert data["level"] in ("none", "standard", "advanced"), \
            f"Invalid level value: {data['level']}"
        print(f"✓ access-level returns level: {data['level']}")
    
    def test_access_level_returns_limits(self):
        """Verify access-level endpoint returns limits"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/access-level",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "limits" in data, "limits field missing from access-level response"
        limits = data["limits"]
        assert "maxPanels" in limits, "maxPanels missing from limits"
        assert "maxFieldsPerPanel" in limits, "maxFieldsPerPanel missing from limits"
        assert limits["maxPanels"] == 10, f"Expected maxPanels=10, got {limits['maxPanels']}"
        assert limits["maxFieldsPerPanel"] == 20, f"Expected maxFieldsPerPanel=20, got {limits['maxFieldsPerPanel']}"
        print(f"✓ access-level returns correct limits: {limits}")
    
    def test_platform_admin_gets_advanced_level(self):
        """Platform admin should get 'advanced' level"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/access-level",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        # Dev-test-token user is platform admin
        assert data["level"] == "advanced", \
            f"Platform admin should have 'advanced' level, got: {data['level']}"
        print("✓ Platform admin correctly gets 'advanced' level")


class TestPanelAccessControl:
    """Test panel CRUD access control based on businessToolAccess level
    
    Note: The dev-test-token user is a platform admin, so require_advanced_access()
    will always pass for them (is_platform_admin check bypasses access level).
    This is correct behavior - platform admins always have advanced access.
    """
    
    def test_platform_admin_can_list_panels(self):
        """Platform admin can list panels (bypasses access check)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "panels" in data
        assert "count" in data
        assert "limit" in data
        print(f"✓ Platform admin can list panels (count: {data['count']})")
    
    def test_platform_admin_can_create_panel(self):
        """Platform admin can create panel (bypasses access check)"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/panels",
            headers=HEADERS,
            json={
                "name": "TEST_AccessControl_Panel",
                "description": "Test panel for access control testing",
                "icon": "test-icon",
                "color": "blue",
                "fields": [
                    {"key": "test_field", "label": "Test Field", "type": "text"}
                ]
            }
        )
        
        # Platform admin should be able to create
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        panel_id = data.get("id")
        assert panel_id, "Panel ID missing from response"
        print(f"✓ Platform admin can create panel (id: {panel_id})")
        
        # Cleanup: delete the test panel
        if panel_id:
            cleanup_response = requests.delete(
                f"{BASE_URL}/api/business-tools/panels/{panel_id}",
                headers=HEADERS
            )
            assert cleanup_response.status_code == 200, f"Cleanup failed: {cleanup_response.text}"
            print("✓ Test panel cleaned up")
    
    def test_linkable_targets_accessible(self):
        """Platform admin can access linkable targets"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels/linkable-targets",
            headers=HEADERS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "targets" in data
        # Should include system modules
        target_ids = [t["id"] for t in data["targets"]]
        assert "inventory" in target_ids, "inventory should be in linkable targets"
        assert "invoices" in target_ids, "invoices should be in linkable targets"
        print(f"✓ Linkable targets accessible (count: {len(data['targets'])})")


class TestAccessLevelPersistence:
    """Test that access level changes persist correctly"""
    
    def test_access_level_change_persists(self):
        """Verify access level change is persisted in user detail"""
        # Set to 'none'
        set_response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "none"}
        )
        assert set_response.status_code == 200
        
        # Verify in user detail
        detail_response = requests.get(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/detail",
            headers=HEADERS
        )
        assert detail_response.status_code == 200
        assert detail_response.json().get("businessToolAccess") == "none"
        
        # Set back to 'advanced'
        restore_response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            headers=HEADERS,
            json={"businessToolAccess": "advanced"}
        )
        assert restore_response.status_code == 200
        
        # Verify restored
        final_response = requests.get(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/detail",
            headers=HEADERS
        )
        assert final_response.status_code == 200
        assert final_response.json().get("businessToolAccess") == "advanced"
        
        print("✓ Access level changes persist correctly")


class TestEndpointAuthentication:
    """Test that endpoints require authentication"""
    
    def test_admin_user_detail_requires_auth(self):
        """Admin user detail requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/detail"
        )
        assert response.status_code in (401, 403), \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Admin user detail requires authentication")
    
    def test_set_access_level_requires_auth(self):
        """Set access level requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
            json={"businessToolAccess": "standard"}
        )
        assert response.status_code in (401, 403), \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Set access level requires authentication")
    
    def test_my_permissions_requires_auth(self):
        """My permissions requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions"
        )
        # 422 is returned by FastAPI when required header is missing
        assert response.status_code in (401, 403, 422), \
            f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ My permissions requires authentication (returns {response.status_code})")
    
    def test_access_level_requires_auth(self):
        """Access level requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/access-level"
        )
        # 422 is returned by FastAPI when required header is missing
        assert response.status_code in (401, 403, 422), \
            f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ Access level requires authentication (returns {response.status_code})")
    
    def test_panels_requires_auth(self):
        """Panels endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/panels"
        )
        # 422 is returned by FastAPI when required header is missing
        assert response.status_code in (401, 403, 422), \
            f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ Panels endpoint requires authentication (returns {response.status_code})")


# Cleanup fixture to restore access level after tests
@pytest.fixture(scope="module", autouse=True)
def restore_access_level():
    """Restore access level to 'advanced' after all tests"""
    yield
    # Restore to advanced after tests
    requests.put(
        f"{BASE_URL}/api/admin/users/{DEV_TEST_USER_ID}/business-tool-access",
        headers=HEADERS,
        json={"businessToolAccess": "advanced"}
    )
    print("\n✓ Restored businessToolAccess to 'advanced' after tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
