"""
Test Business Tools Layout Fix - Iteration 99

Tests the fix for useEmployeeAccess() hook being called outside EmployeeAccessProvider.
The fix moves all UI logic into BusinessToolsInner component that renders INSIDE the provider.

Key tests:
1. Backend health check
2. /api/business-tools/my-permissions endpoint (requires auth)
3. /api/business-tools/employee-mgmt/my-access endpoint (requires auth)
4. Verify layout.tsx structure has BusinessToolsInner inside EmployeeAccessProvider
"""

import pytest
import requests
import os
import re

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-phase2-enhance.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestBackendHealth:
    """Backend health check tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy", f"Unexpected health status: {data}"
        print(f"✓ Health check passed: {data}")


class TestMyPermissionsEndpoint:
    """Tests for /api/business-tools/my-permissions endpoint"""
    
    def test_my_permissions_requires_auth(self):
        """GET /api/business-tools/my-permissions should return 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/my-permissions")
        # Should fail without auth token
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print(f"✓ my-permissions correctly requires auth (status: {response.status_code})")
    
    def test_my_permissions_endpoint_exists(self):
        """Verify the endpoint exists (not 404)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/my-permissions")
        # Should NOT be 404 - endpoint should exist
        assert response.status_code != 404, "my-permissions endpoint not found (404)"
        print(f"✓ my-permissions endpoint exists (status: {response.status_code})")


class TestEmployeeAccessEndpoint:
    """Tests for /api/business-tools/employee-mgmt/my-access endpoint"""
    
    def test_my_access_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/my-access should return 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access")
        # Should fail without auth token
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print(f"✓ my-access correctly requires auth (status: {response.status_code})")
    
    def test_my_access_endpoint_exists(self):
        """Verify the endpoint exists (not 404)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access")
        # Should NOT be 404 - endpoint should exist
        assert response.status_code != 404, "my-access endpoint not found (404)"
        print(f"✓ my-access endpoint exists (status: {response.status_code})")


class TestLayoutTsxStructure:
    """Tests to verify the layout.tsx fix structure"""
    
    @pytest.fixture
    def layout_content(self):
        """Read the layout.tsx file content"""
        layout_path = "/app/frontend/src/app/seller/business-tools/layout.tsx"
        with open(layout_path, 'r') as f:
            return f.read()
    
    def test_business_tools_inner_component_exists(self, layout_content):
        """Verify BusinessToolsInner component is defined"""
        assert "function BusinessToolsInner" in layout_content or "const BusinessToolsInner" in layout_content, \
            "BusinessToolsInner component not found in layout.tsx"
        print("✓ BusinessToolsInner component exists")
    
    def test_use_employee_access_inside_inner(self, layout_content):
        """Verify useEmployeeAccess is called inside components that are INSIDE EmployeeAccessProvider, not in outer layout"""
        # Find the outer BusinessToolsLayout function
        outer_match = re.search(r'export default function BusinessToolsLayout\s*\([^)]*\)\s*\{', layout_content)
        assert outer_match, "BusinessToolsLayout function not found"
        
        outer_start = outer_match.end()
        
        # Get the content of the outer function
        outer_content = layout_content[outer_start:]
        
        # Find useEmployeeAccess calls in the outer function
        # These should NOT exist - all useEmployeeAccess calls should be in inner components
        use_employee_in_outer = re.search(r'useEmployeeAccess\s*\(\s*\)', outer_content)
        assert not use_employee_in_outer, \
            "useEmployeeAccess is incorrectly called in outer BusinessToolsLayout function"
        
        # Verify useEmployeeAccess IS called somewhere in the file (in inner components)
        use_employee_access_calls = list(re.finditer(r'useEmployeeAccess\s*\(\s*\)', layout_content))
        assert len(use_employee_access_calls) > 0, "useEmployeeAccess should be called somewhere in the file"
        
        # All calls should be BEFORE the outer BusinessToolsLayout function
        outer_func_start = outer_match.start()
        for call in use_employee_access_calls:
            call_pos = call.start()
            assert call_pos < outer_func_start, \
                f"useEmployeeAccess called in outer BusinessToolsLayout at position {call_pos}"
        
        print(f"✓ useEmployeeAccess is called in inner components ({len(use_employee_access_calls)} calls), not in outer layout")
    
    def test_employee_access_provider_wraps_inner(self, layout_content):
        """Verify EmployeeAccessProvider wraps BusinessToolsInner in the return"""
        # Look for the pattern: <EmployeeAccessProvider>...<BusinessToolsInner
        pattern = r'<EmployeeAccessProvider>[\s\S]*?<BusinessToolsInner'
        match = re.search(pattern, layout_content)
        assert match, "BusinessToolsInner is not wrapped by EmployeeAccessProvider"
        print("✓ EmployeeAccessProvider wraps BusinessToolsInner")
    
    def test_no_use_employee_access_in_outer_layout(self, layout_content):
        """Verify useEmployeeAccess is NOT called in the outer BusinessToolsLayout function"""
        # Find the outer BusinessToolsLayout function
        outer_match = re.search(r'export default function BusinessToolsLayout\s*\([^)]*\)\s*\{', layout_content)
        assert outer_match, "BusinessToolsLayout function not found"
        
        outer_start = outer_match.end()
        
        # Get the content of the outer function (until the end of file or next export)
        outer_content = layout_content[outer_start:]
        
        # Check if useEmployeeAccess is called in the outer function
        # It should NOT be called there
        use_employee_in_outer = re.search(r'useEmployeeAccess\s*\(\s*\)', outer_content)
        assert not use_employee_in_outer, \
            "useEmployeeAccess is incorrectly called in outer BusinessToolsLayout function"
        print("✓ useEmployeeAccess is NOT called in outer BusinessToolsLayout")
    
    def test_permission_context_provider_in_inner(self, layout_content):
        """Verify PermissionContext.Provider is inside BusinessToolsInner"""
        # Find BusinessToolsInner
        inner_match = re.search(r'function BusinessToolsInner\s*\([^)]*\)\s*\{', layout_content)
        assert inner_match, "BusinessToolsInner function not found"
        
        inner_start = inner_match.start()
        
        # Find PermissionContext.Provider
        provider_match = re.search(r'<PermissionContext\.Provider', layout_content)
        assert provider_match, "PermissionContext.Provider not found"
        
        provider_pos = provider_match.start()
        
        # Provider should be after BusinessToolsInner starts
        assert provider_pos > inner_start, \
            "PermissionContext.Provider is not inside BusinessToolsInner"
        print("✓ PermissionContext.Provider is inside BusinessToolsInner")


class TestEmployeeAccessContext:
    """Tests for EmployeeAccessContext structure"""
    
    @pytest.fixture
    def context_content(self):
        """Read the EmployeeAccessContext.tsx file content"""
        context_path = "/app/frontend/src/context/EmployeeAccessContext.tsx"
        with open(context_path, 'r') as f:
            return f.read()
    
    def test_can_view_returns_true_while_loading(self, context_content):
        """Verify canView returns true while loading (optimistic)"""
        # Look for the canView function that returns true while loading
        pattern = r'canView.*?if\s*\(\s*loading\s*\)\s*return\s*true'
        match = re.search(pattern, context_content, re.DOTALL)
        assert match, "canView should return true while loading"
        print("✓ canView returns true while loading (optimistic)")
    
    def test_can_view_returns_true_when_no_access(self, context_content):
        """Verify canView returns true when no access data (for regular sellers)"""
        # Look for the pattern that returns true when !access
        pattern = r'if\s*\(\s*!access\s*\)\s*return\s*true'
        match = re.search(pattern, context_content)
        assert match, "canView should return true when no access data"
        print("✓ canView returns true when no access data (for regular sellers)")
    
    def test_exports_required_functions(self, context_content):
        """Verify context exports canView, canAction, isFullAdmin, isDisabled, isUnlinked"""
        required_exports = ['canView', 'canAction', 'isFullAdmin', 'isDisabled', 'isUnlinked']
        for export in required_exports:
            assert export in context_content, f"Missing export: {export}"
        print(f"✓ All required exports present: {required_exports}")


class TestNoAccessComponent:
    """Tests for NoAccess component"""
    
    @pytest.fixture
    def noaccess_content(self):
        """Read the NoAccess.tsx file content"""
        noaccess_path = "/app/frontend/src/components/NoAccess.tsx"
        with open(noaccess_path, 'r') as f:
            return f.read()
    
    def test_has_access_restricted_text(self, noaccess_content):
        """Verify NoAccess shows 'Access Restricted' message"""
        assert "Access Restricted" in noaccess_content, "NoAccess should show 'Access Restricted'"
        print("✓ NoAccess shows 'Access Restricted' message")
    
    def test_has_data_testid(self, noaccess_content):
        """Verify NoAccess has data-testid attribute"""
        assert 'data-testid="no-access' in noaccess_content, "NoAccess should have data-testid"
        print("✓ NoAccess has data-testid attribute")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
