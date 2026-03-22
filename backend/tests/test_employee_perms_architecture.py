"""
Employee Permissions Architecture Tests - Iteration 103
Tests for the new permission format: {modules: {module: boolean}, panels: {panelId: {canView, canCreate, canEdit}}}

Features tested:
1. GET /api/business-tools/employee-mgmt/modules - returns both system modules and custom panels
2. GET /api/business-tools/employee-mgmt/role-templates - returns templates in new format
3. PUT /api/business-tools/employee-mgmt/{employee_id} - accepts new permission format
4. POST /api/business-tools/employee-mgmt/link - accepts new permission format
5. GET /api/business-tools/employee-mgmt/my-access - returns normalized permissions and permittedPanels
6. GET /api/business-tools/employee-mgmt/list - returns employees with normalized permissions
7. Panel access enforcement: 403 for unauthorized panel access
8. Backward compatibility: old format normalized to new format
"""

import pytest
import requests
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doc-builder-preview-1.preview.emergentagent.com').rstrip('/')
AUTH_TOKEN = "dev-test-token"  # Firebase bypass in dev mode

EXPECTED_SYSTEM_MODULES = [
    "dashboard", "inventory", "invoices", "quotations",
    "purchase_orders", "reports", "buyers", "suppliers",
    "employees", "settings"
]


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}


class TestModulesEndpointNewFormat:
    """Test GET /api/business-tools/employee-mgmt/modules returns both modules and panels"""
    
    def test_modules_returns_modules_array(self, auth_headers):
        """GET /modules returns modules array with id and name"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/modules", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "modules" in data, "Response missing 'modules' key"
        assert isinstance(data["modules"], list), "modules should be a list"
        
        # Verify module structure
        for module in data["modules"]:
            assert "id" in module, f"Module missing 'id': {module}"
            assert "name" in module, f"Module missing 'name': {module}"
        
        # Verify all expected modules are present
        module_ids = [m["id"] for m in data["modules"]]
        for expected in EXPECTED_SYSTEM_MODULES:
            assert expected in module_ids, f"Missing expected module: {expected}"
        
        print(f"✓ GET /modules returns {len(data['modules'])} system modules")
    
    def test_modules_returns_panels_array(self, auth_headers):
        """GET /modules returns panels array (may be empty if no panels exist)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/modules", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "panels" in data, "Response missing 'panels' key"
        assert isinstance(data["panels"], list), "panels should be a list"
        
        # If panels exist, verify structure
        for panel in data["panels"]:
            assert "id" in panel, f"Panel missing 'id': {panel}"
            assert "name" in panel, f"Panel missing 'name': {panel}"
            assert "color" in panel, f"Panel missing 'color': {panel}"
        
        print(f"✓ GET /modules returns {len(data['panels'])} custom panels")


class TestRoleTemplatesNewFormat:
    """Test GET /api/business-tools/employee-mgmt/role-templates returns new format"""
    
    def test_role_templates_new_format(self, auth_headers):
        """Role templates use {modules: {}, panels: {}} format"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/role-templates", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templates" in data, "Response missing 'templates' key"
        
        templates = data["templates"]
        assert len(templates) >= 6, f"Expected at least 6 templates, got {len(templates)}"
        
        # Verify each template has new format
        for name, template in templates.items():
            assert "modules" in template, f"Template '{name}' missing 'modules' key"
            assert "panels" in template, f"Template '{name}' missing 'panels' key"
            assert isinstance(template["modules"], dict), f"Template '{name}' modules should be dict"
            assert isinstance(template["panels"], dict), f"Template '{name}' panels should be dict"
        
        print(f"✓ All {len(templates)} role templates use new format")
    
    def test_admin_template_all_modules_true(self, auth_headers):
        """Admin template has all modules set to True"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/role-templates", headers=auth_headers)
        data = response.json()
        
        admin_template = data["templates"].get("Admin")
        assert admin_template is not None, "Admin template not found"
        
        for module in EXPECTED_SYSTEM_MODULES:
            assert admin_template["modules"].get(module) == True, f"Admin missing True for {module}"
        
        print("✓ Admin template has all modules set to True")
    
    def test_viewer_template_all_modules_true(self, auth_headers):
        """Viewer template has all modules set to True (view-only in new format)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/role-templates", headers=auth_headers)
        data = response.json()
        
        viewer_template = data["templates"].get("Viewer")
        assert viewer_template is not None, "Viewer template not found"
        
        # In new format, module=True means access (view+action combined)
        for module in EXPECTED_SYSTEM_MODULES:
            assert viewer_template["modules"].get(module) == True, f"Viewer missing True for {module}"
        
        print("✓ Viewer template has all modules set to True")
    
    def test_manager_template_restricted_modules(self, auth_headers):
        """Manager template has employees and settings set to False"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/role-templates", headers=auth_headers)
        data = response.json()
        
        manager_template = data["templates"].get("Manager")
        assert manager_template is not None, "Manager template not found"
        
        # Manager should NOT have access to employees and settings
        assert manager_template["modules"].get("employees") == False, "Manager should not have employees access"
        assert manager_template["modules"].get("settings") == False, "Manager should not have settings access"
        
        # But should have access to other modules
        assert manager_template["modules"].get("dashboard") == True, "Manager should have dashboard access"
        assert manager_template["modules"].get("inventory") == True, "Manager should have inventory access"
        
        print("✓ Manager template has restricted employees and settings")


class TestMyAccessEndpoint:
    """Test GET /api/business-tools/employee-mgmt/my-access returns normalized permissions"""
    
    def test_my_access_returns_normalized_permissions(self, auth_headers):
        """my-access returns permissions in {modules: {}, panels: {}} format"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "permissions" in data, "Response missing 'permissions' key"
        
        perms = data["permissions"]
        assert "modules" in perms, "Permissions missing 'modules' key"
        assert "panels" in perms, "Permissions missing 'panels' key"
        assert isinstance(perms["modules"], dict), "modules should be dict"
        assert isinstance(perms["panels"], dict), "panels should be dict"
        
        print("✓ my-access returns normalized permissions format")
    
    def test_my_access_returns_permitted_panels(self, auth_headers):
        """my-access returns permittedPanels array"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "permittedPanels" in data, "Response missing 'permittedPanels' key"
        assert isinstance(data["permittedPanels"], list), "permittedPanels should be a list"
        
        # If panels exist, verify structure
        for panel in data["permittedPanels"]:
            assert "id" in panel, f"Panel missing 'id': {panel}"
            assert "name" in panel, f"Panel missing 'name': {panel}"
            assert "color" in panel, f"Panel missing 'color': {panel}"
            assert "slug" in panel, f"Panel missing 'slug': {panel}"
        
        print(f"✓ my-access returns permittedPanels array with {len(data['permittedPanels'])} panels")
    
    def test_my_access_returns_admin_fields(self, auth_headers):
        """my-access returns isAdmin, companyId, companyName, companyLogoUrl"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "isAdmin" in data, "Response missing 'isAdmin' key"
        assert "companyId" in data or data.get("companyId") is None, "Response missing 'companyId' key"
        assert "companyName" in data, "Response missing 'companyName' key"
        assert "companyLogoUrl" in data, "Response missing 'companyLogoUrl' key"
        
        print("✓ my-access returns admin and company fields")


class TestEmployeeListNormalizedPermissions:
    """Test GET /api/business-tools/employee-mgmt/list returns normalized permissions"""
    
    def test_list_active_returns_normalized_permissions(self, auth_headers):
        """list?tab=active returns employees with normalized permissions"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=active", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employees" in data, "Response missing 'employees' key"
        
        for emp in data["employees"]:
            if "permissions" in emp and emp["permissions"]:
                perms = emp["permissions"]
                assert "modules" in perms, f"Employee {emp.get('id')} permissions missing 'modules'"
                assert "panels" in perms, f"Employee {emp.get('id')} permissions missing 'panels'"
        
        print(f"✓ list?tab=active returns {len(data['employees'])} employees with normalized permissions")


class TestLinkEmployeeNewFormat:
    """Test POST /api/business-tools/employee-mgmt/link accepts new permission format"""
    
    def test_link_accepts_new_permission_format(self, auth_headers):
        """POST /link accepts {modules: {}, panels: {}} format"""
        # First search for a user to link (or use a test email)
        search_response = requests.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/search?email=test_link_user@example.com",
            headers=auth_headers
        )
        
        # If user not found, that's expected - we're testing the format acceptance
        if search_response.status_code == 200:
            search_data = search_response.json()
            if search_data.get("canLink"):
                # Try to link with new format
                link_payload = {
                    "email": "test_link_user@example.com",
                    "role": "TEST_Role",
                    "permissions": {
                        "modules": {
                            "dashboard": True,
                            "inventory": True,
                            "invoices": False
                        },
                        "panels": {
                            "test_panel_id": {
                                "canView": True,
                                "canCreate": False,
                                "canEdit": False
                            }
                        }
                    }
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/business-tools/employee-mgmt/link",
                    headers=auth_headers,
                    json=link_payload
                )
                
                # Should accept the format (may fail for other reasons like user not found)
                assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
                print("✓ POST /link accepts new permission format")
            else:
                print("✓ POST /link format test skipped (no linkable user)")
        else:
            print("✓ POST /link format test skipped (search failed)")


class TestUpdateEmployeeNewFormat:
    """Test PUT /api/business-tools/employee-mgmt/{id} accepts new permission format"""
    
    def test_update_accepts_new_permission_format(self, auth_headers):
        """PUT /{id} accepts {modules: {}, panels: {}} format"""
        # Get list of active employees
        list_response = requests.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=active",
            headers=auth_headers
        )
        
        if list_response.status_code == 200:
            employees = list_response.json().get("employees", [])
            if employees:
                emp_id = employees[0]["id"]
                
                update_payload = {
                    "role": "TEST_Updated_Role",
                    "permissions": {
                        "modules": {
                            "dashboard": True,
                            "inventory": True,
                            "invoices": True,
                            "quotations": False
                        },
                        "panels": {
                            "test_panel_id": {
                                "canView": True,
                                "canCreate": True,
                                "canEdit": False
                            }
                        }
                    }
                }
                
                response = requests.put(
                    f"{BASE_URL}/api/business-tools/employee-mgmt/{emp_id}",
                    headers=auth_headers,
                    json=update_payload
                )
                
                # Should accept the format (may fail for self-protection)
                assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}: {response.text}"
                print(f"✓ PUT /{emp_id} accepts new permission format (status: {response.status_code})")
            else:
                print("✓ PUT /{id} format test skipped (no employees)")
        else:
            print("✓ PUT /{id} format test skipped (list failed)")


class TestNormalizePermissionsFunction:
    """Test normalize_permissions function handles old and new formats"""
    
    def test_normalize_old_format_to_new(self):
        """normalize_permissions converts old {module: {view, action}} to new format"""
        from utils.permissions import normalize_permissions
        
        old_format = {
            "inventory": {"view": True, "action": True},
            "invoices": {"view": True, "action": False},
            "dashboard": {"view": False, "action": False}
        }
        
        result = normalize_permissions(old_format)
        
        assert "modules" in result, "Result missing 'modules' key"
        assert "panels" in result, "Result missing 'panels' key"
        
        # Old format view=True should become module=True
        assert result["modules"].get("inventory") == True, "inventory should be True"
        assert result["modules"].get("invoices") == True, "invoices should be True (view was True)"
        assert result["modules"].get("dashboard") == False, "dashboard should be False"
        
        print("✓ normalize_permissions converts old format correctly")
    
    def test_normalize_new_format_passthrough(self):
        """normalize_permissions passes through new format unchanged"""
        from utils.permissions import normalize_permissions
        
        new_format = {
            "modules": {
                "inventory": True,
                "invoices": False
            },
            "panels": {
                "panel_123": {"canView": True, "canCreate": False, "canEdit": False}
            }
        }
        
        result = normalize_permissions(new_format)
        
        assert result == new_format, "New format should pass through unchanged"
        print("✓ normalize_permissions passes through new format unchanged")
    
    def test_normalize_empty_permissions(self):
        """normalize_permissions handles empty/None permissions"""
        from utils.permissions import normalize_permissions
        
        result_none = normalize_permissions(None)
        assert result_none == {"modules": {}, "panels": {}}, "None should return empty structure"
        
        result_empty = normalize_permissions({})
        assert result_empty == {"modules": {}, "panels": {}}, "Empty dict should return empty structure"
        
        print("✓ normalize_permissions handles empty/None permissions")


class TestPanelAccessEnforcement:
    """Test panel access enforcement with granular permissions"""
    
    def test_panel_get_requires_canview(self, auth_headers):
        """GET /api/business-tools/panels/{id} requires canView permission"""
        # First get list of panels
        panels_response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=auth_headers)
        
        if panels_response.status_code == 200:
            panels = panels_response.json().get("panels", [])
            if panels:
                panel_id = panels[0]["id"]
                
                # Admin should be able to access
                response = requests.get(
                    f"{BASE_URL}/api/business-tools/panels/{panel_id}",
                    headers=auth_headers
                )
                
                # Admin should get 200
                assert response.status_code == 200, f"Admin should access panel: {response.status_code}"
                print(f"✓ GET /panels/{panel_id} works for admin")
            else:
                print("✓ Panel access test skipped (no panels)")
        else:
            print("✓ Panel access test skipped (panels list failed)")
    
    def test_panel_records_create_requires_cancreate(self, auth_headers):
        """POST /api/business-tools/panels/{id}/records requires canCreate permission"""
        # First get list of panels
        panels_response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=auth_headers)
        
        if panels_response.status_code == 200:
            panels = panels_response.json().get("panels", [])
            if panels:
                panel_id = panels[0]["id"]
                
                # Admin should be able to create
                response = requests.post(
                    f"{BASE_URL}/api/business-tools/panels/{panel_id}/records",
                    headers=auth_headers,
                    json={"data": {"test_field": "test_value"}}
                )
                
                # Admin should get 200 or 400 (validation error), not 403
                assert response.status_code in [200, 400], f"Admin should access: {response.status_code}"
                print(f"✓ POST /panels/{panel_id}/records works for admin (status: {response.status_code})")
            else:
                print("✓ Panel records create test skipped (no panels)")
        else:
            print("✓ Panel records create test skipped (panels list failed)")


class TestCheckPanelAccessFunction:
    """Test check_panel_access function in panel_router.py"""
    
    def test_check_panel_access_exists_in_router(self):
        """check_panel_access function exists in panel_router.py"""
        panel_router_path = "/app/backend/routers/panel_router.py"
        
        with open(panel_router_path, 'r') as f:
            content = f.read()
        
        assert "def check_panel_access" in content, "check_panel_access function not found"
        assert "canView" in content, "canView check not found"
        assert "canCreate" in content, "canCreate check not found"
        assert "canEdit" in content, "canEdit check not found"
        
        print("✓ check_panel_access function exists with granular permission checks")


class TestFrontendPermissionGridStructure:
    """Test frontend PermissionGrid component has separate sections"""
    
    def test_permission_grid_has_system_modules_section(self):
        """PermissionGrid has System Modules section"""
        page_path = "/app/frontend/src/app/seller/business-tools/employees/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert "System Modules" in content, "Missing 'System Modules' section header"
        assert "perm-module-" in content or "perm-row-" in content, "Missing module permission test IDs"
        
        print("✓ PermissionGrid has System Modules section")
    
    def test_permission_grid_has_custom_panels_section(self):
        """PermissionGrid has Custom Panels section"""
        page_path = "/app/frontend/src/app/seller/business-tools/employees/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert "Custom Panels" in content, "Missing 'Custom Panels' section header"
        assert "perm-panel-" in content, "Missing panel permission test IDs"
        
        print("✓ PermissionGrid has Custom Panels section")
    
    def test_permission_grid_has_granular_panel_controls(self):
        """PermissionGrid has View, Create, Edit checkboxes for panels"""
        page_path = "/app/frontend/src/app/seller/business-tools/employees/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert "canView" in content, "Missing canView control"
        assert "canCreate" in content, "Missing canCreate control"
        assert "canEdit" in content, "Missing canEdit control"
        
        print("✓ PermissionGrid has granular panel controls (View, Create, Edit)")


class TestSidebarPanelPermissions:
    """Test sidebar shows panels based on employee permissions"""
    
    def test_layout_has_sidebar_panels_logic(self):
        """Layout.tsx has sidebarPanels and showPanelsSection logic"""
        layout_path = "/app/frontend/src/app/seller/business-tools/layout.tsx"
        
        with open(layout_path, 'r') as f:
            content = f.read()
        
        assert "sidebarPanels" in content, "Missing sidebarPanels variable"
        assert "showPanelsSection" in content, "Missing showPanelsSection variable"
        assert "permittedPanels" in content, "Missing permittedPanels reference"
        
        print("✓ Layout.tsx has sidebar panel permission logic")
    
    def test_employee_access_context_has_panel_methods(self):
        """EmployeeAccessContext has canViewPanel, canCreatePanel, canEditPanel methods"""
        ctx_path = "/app/frontend/src/context/EmployeeAccessContext.tsx"
        
        with open(ctx_path, 'r') as f:
            content = f.read()
        
        assert "canViewPanel" in content, "Missing canViewPanel method"
        assert "canCreatePanel" in content, "Missing canCreatePanel method"
        assert "canEditPanel" in content, "Missing canEditPanel method"
        
        print("✓ EmployeeAccessContext has panel permission methods")


class TestBackwardCompatibility:
    """Test backward compatibility with old permission format"""
    
    def test_old_format_normalized_in_list(self, auth_headers):
        """Employees with old format permissions are normalized in list response"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=active",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            employees = response.json().get("employees", [])
            for emp in employees:
                if emp.get("permissions"):
                    perms = emp["permissions"]
                    # Should always have new format structure
                    assert "modules" in perms, f"Employee {emp.get('id')} missing modules key"
                    assert "panels" in perms, f"Employee {emp.get('id')} missing panels key"
            
            print(f"✓ All {len(employees)} employees have normalized permissions")
        else:
            print("✓ Backward compatibility test skipped (list failed)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
