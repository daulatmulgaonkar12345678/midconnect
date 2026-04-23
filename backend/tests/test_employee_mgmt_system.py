"""
Employee Management System Tests - Iteration 98
Tests for the new Employee Management features:
1. GET /api/business-tools/employee-mgmt/modules - 10 modules list
2. GET /api/business-tools/employee-mgmt/role-templates - 6 role templates
3. GET /api/business-tools/employee-mgmt/search?email=... - Search user by email
4. POST /api/business-tools/employee-mgmt/link - Link employee
5. GET /api/business-tools/employee-mgmt/list?tab=active/pending/unlinked - 3 tabs
6. PUT /api/business-tools/employee-mgmt/{id} - Update employee access
7. POST /api/business-tools/employee-mgmt/{id}/unlink - Unlink employee
8. POST /api/business-tools/employee-mgmt/{id}/relink - Relink employee
9. GET /api/business-tools/employee-mgmt/my-access - Current user access
10. GET /api/business-tools/employee-mgmt/logs - Audit logs
11. Self-protection: Admin can't modify own access
"""

import pytest
import requests
import os
import sys

# Add backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com').rstrip('/')

# Expected values from employee_mgmt_router.py
EXPECTED_MODULES = [
    "dashboard", "inventory", "invoices", "quotations",
    "purchase_orders", "reports", "buyers", "suppliers",
    "employees", "settings"
]

EXPECTED_ROLE_TEMPLATES = [
    "Admin", "Manager", "Sales Executive", 
    "Inventory Manager", "Accountant", "Viewer"
]


class TestEmployeeMgmtEndpointsExist:
    """Test that all employee management endpoints exist and require auth"""
    
    def test_modules_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/modules returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/modules")
        # Should return 401 (auth required) or 422 (validation error for missing header)
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /modules endpoint exists and requires auth")
    
    def test_role_templates_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/role-templates returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/role-templates")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /role-templates endpoint exists and requires auth")
    
    def test_search_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/search returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/search?email=test@example.com")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /search endpoint exists and requires auth")
    
    def test_link_endpoint_requires_auth(self):
        """POST /api/business-tools/employee-mgmt/link returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/employee-mgmt/link",
            json={"email": "test@example.com", "role": "Test", "permissions": {}}
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ POST /link endpoint exists and requires auth")
    
    def test_list_active_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/list?tab=active returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=active")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /list?tab=active endpoint exists and requires auth")
    
    def test_list_pending_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/list?tab=pending returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=pending")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /list?tab=pending endpoint exists and requires auth")
    
    def test_list_unlinked_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/list?tab=unlinked returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=unlinked")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /list?tab=unlinked endpoint exists and requires auth")
    
    def test_update_employee_endpoint_requires_auth(self):
        """PUT /api/business-tools/employee-mgmt/{id} returns 401 without auth"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/employee-mgmt/507f1f77bcf86cd799439011",
            json={"role": "Test"}
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ PUT /{id} endpoint exists and requires auth")
    
    def test_unlink_endpoint_requires_auth(self):
        """POST /api/business-tools/employee-mgmt/{id}/unlink returns 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/business-tools/employee-mgmt/507f1f77bcf86cd799439011/unlink")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ POST /{id}/unlink endpoint exists and requires auth")
    
    def test_relink_endpoint_requires_auth(self):
        """POST /api/business-tools/employee-mgmt/{id}/relink returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/employee-mgmt/507f1f77bcf86cd799439011/relink",
            json={"email": "test@example.com", "role": "Test", "permissions": {}}
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ POST /{id}/relink endpoint exists and requires auth")
    
    def test_my_access_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/my-access returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/my-access")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /my-access endpoint exists and requires auth")
    
    def test_logs_endpoint_requires_auth(self):
        """GET /api/business-tools/employee-mgmt/logs returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employee-mgmt/logs")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}: {response.text}"
        print("✓ GET /logs endpoint exists and requires auth")


class TestEmployeeMgmtRouterDirectImport:
    """Test router module directly via Python imports for schema validation"""
    
    def test_permission_modules_constant(self):
        """PERMISSION_MODULES has 10 modules"""
        from routers.employee_mgmt_router import PERMISSION_MODULES
        
        assert len(PERMISSION_MODULES) == 10, f"Expected 10 modules, got {len(PERMISSION_MODULES)}"
        assert PERMISSION_MODULES == EXPECTED_MODULES, f"Modules mismatch: {PERMISSION_MODULES}"
        print(f"✓ PERMISSION_MODULES has 10 correct modules: {PERMISSION_MODULES}")
    
    def test_default_role_templates_constant(self):
        """DEFAULT_ROLE_TEMPLATES has 6 role templates"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES
        
        assert len(DEFAULT_ROLE_TEMPLATES) == 6, f"Expected 6 templates, got {len(DEFAULT_ROLE_TEMPLATES)}"
        
        template_names = list(DEFAULT_ROLE_TEMPLATES.keys())
        assert sorted(template_names) == sorted(EXPECTED_ROLE_TEMPLATES), f"Templates mismatch: {template_names}"
        print(f"✓ DEFAULT_ROLE_TEMPLATES has 6 templates: {template_names}")
    
    def test_admin_template_has_all_permissions(self):
        """Admin role template has view=True, action=True for all modules"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES, PERMISSION_MODULES
        
        admin_template = DEFAULT_ROLE_TEMPLATES.get("Admin")
        assert admin_template is not None, "Admin template not found"
        
        for module in PERMISSION_MODULES:
            perms = admin_template.get(module, {})
            assert perms.get("view") == True, f"Admin missing view for {module}"
            assert perms.get("action") == True, f"Admin missing action for {module}"
        
        print("✓ Admin template has full permissions for all modules")
    
    def test_viewer_template_view_only(self):
        """Viewer role template has view=True, action=False for all modules"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES, PERMISSION_MODULES
        
        viewer_template = DEFAULT_ROLE_TEMPLATES.get("Viewer")
        assert viewer_template is not None, "Viewer template not found"
        
        for module in PERMISSION_MODULES:
            perms = viewer_template.get(module, {})
            assert perms.get("view") == True, f"Viewer missing view for {module}"
            assert perms.get("action") == False, f"Viewer has action for {module} (should be False)"
        
        print("✓ Viewer template has view-only permissions for all modules")
    
    def test_manager_template_restricted_employees_settings(self):
        """Manager template has restricted action for employees and settings"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES
        
        manager_template = DEFAULT_ROLE_TEMPLATES.get("Manager")
        assert manager_template is not None, "Manager template not found"
        
        # Manager should NOT have action on employees and settings
        assert manager_template["employees"]["action"] == False, "Manager should not have action on employees"
        assert manager_template["settings"]["action"] == False, "Manager should not have action on settings"
        
        # But should have view on everything
        assert manager_template["employees"]["view"] == True, "Manager should have view on employees"
        assert manager_template["settings"]["view"] == True, "Manager should have view on settings"
        
        print("✓ Manager template has restricted action on employees and settings")
    
    def test_sales_executive_template_modules(self):
        """Sales Executive has specific modules enabled"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES
        
        sales_template = DEFAULT_ROLE_TEMPLATES.get("Sales Executive")
        assert sales_template is not None, "Sales Executive template not found"
        
        # Sales can view: dashboard, invoices, quotations, buyers, reports
        expected_view = ["dashboard", "invoices", "quotations", "buyers", "reports"]
        for module in expected_view:
            assert sales_template[module]["view"] == True, f"Sales should view {module}"
        
        # Sales can action: invoices, quotations, buyers
        expected_action = ["invoices", "quotations", "buyers"]
        for module in expected_action:
            assert sales_template[module]["action"] == True, f"Sales should action {module}"
        
        print("✓ Sales Executive template has correct module access")
    
    def test_inventory_manager_template_modules(self):
        """Inventory Manager has specific modules enabled"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES
        
        inv_template = DEFAULT_ROLE_TEMPLATES.get("Inventory Manager")
        assert inv_template is not None, "Inventory Manager template not found"
        
        # Inventory Manager can view: dashboard, inventory, purchase_orders, suppliers, reports
        expected_view = ["dashboard", "inventory", "purchase_orders", "suppliers", "reports"]
        for module in expected_view:
            assert inv_template[module]["view"] == True, f"Inventory Manager should view {module}"
        
        # Inventory Manager can action: inventory, purchase_orders, suppliers
        expected_action = ["inventory", "purchase_orders", "suppliers"]
        for module in expected_action:
            assert inv_template[module]["action"] == True, f"Inventory Manager should action {module}"
        
        print("✓ Inventory Manager template has correct module access")
    
    def test_accountant_template_modules(self):
        """Accountant has specific modules enabled"""
        from routers.employee_mgmt_router import DEFAULT_ROLE_TEMPLATES
        
        acc_template = DEFAULT_ROLE_TEMPLATES.get("Accountant")
        assert acc_template is not None, "Accountant template not found"
        
        # Accountant can view: dashboard, invoices, reports, buyers
        expected_view = ["dashboard", "invoices", "reports", "buyers"]
        for module in expected_view:
            assert acc_template[module]["view"] == True, f"Accountant should view {module}"
        
        # Accountant can action: invoices only
        assert acc_template["invoices"]["action"] == True, "Accountant should action invoices"
        
        print("✓ Accountant template has correct module access")


class TestEmployeeMgmtModels:
    """Test Pydantic models for validation"""
    
    def test_link_employee_request_model(self):
        """LinkEmployeeRequest model validates correctly"""
        from routers.employee_mgmt_router import LinkEmployeeRequest
        
        # Valid request
        valid_req = LinkEmployeeRequest(
            email="test@example.com",
            role="Sales Executive",
            permissions={
                "dashboard": {"view": True, "action": False},
                "invoices": {"view": True, "action": True}
            }
        )
        assert valid_req.email == "test@example.com"
        assert valid_req.role == "Sales Executive"
        assert len(valid_req.permissions) == 2
        print("✓ LinkEmployeeRequest model validates correctly")
    
    def test_link_employee_request_min_length(self):
        """LinkEmployeeRequest validates min_length for email and role"""
        from routers.employee_mgmt_router import LinkEmployeeRequest
        from pydantic import ValidationError
        
        # Email too short
        try:
            LinkEmployeeRequest(email="ab", role="Sales", permissions={})
            assert False, "Should have raised ValidationError for short email"
        except ValidationError:
            pass
        
        # Role too short (empty)
        try:
            LinkEmployeeRequest(email="test@example.com", role="", permissions={})
            assert False, "Should have raised ValidationError for empty role"
        except ValidationError:
            pass
        
        print("✓ LinkEmployeeRequest validates min_length constraints")
    
    def test_update_employee_request_model(self):
        """UpdateEmployeeAccessRequest model validates correctly"""
        from routers.employee_mgmt_router import UpdateEmployeeAccessRequest
        
        # All fields optional
        req = UpdateEmployeeAccessRequest()
        assert req.role is None
        assert req.permissions is None
        assert req.status is None
        
        # With fields
        req2 = UpdateEmployeeAccessRequest(
            role="Manager",
            status="disabled"
        )
        assert req2.role == "Manager"
        assert req2.status == "disabled"
        
        print("✓ UpdateEmployeeAccessRequest model validates correctly")
    
    def test_module_permission_model(self):
        """ModulePermission model has view and action booleans"""
        from routers.employee_mgmt_router import ModulePermission
        
        perm = ModulePermission(view=True, action=False)
        assert perm.view == True
        assert perm.action == False
        
        # Default values
        perm_default = ModulePermission()
        assert perm_default.view == False
        assert perm_default.action == False
        
        print("✓ ModulePermission model has correct defaults")


class TestEmployeeMgmtRouterLogic:
    """Test router initialization and helper functions"""
    
    def test_serialize_doc_function(self):
        """serialize_doc handles ObjectId and datetime"""
        from routers.employee_mgmt_router import serialize_doc
        from bson import ObjectId
        from datetime import datetime, timezone
        
        test_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Test",
            "created": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            "nested": {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "value": 123
            }
        }
        
        result = serialize_doc(test_doc)
        
        assert result["id"] == "507f1f77bcf86cd799439011"
        assert "_id" not in result
        assert result["name"] == "Test"
        assert "2024-01-01" in result["created"]
        assert result["nested"]["id"] == "507f1f77bcf86cd799439012"
        
        print("✓ serialize_doc correctly handles ObjectId and datetime")
    
    def test_router_has_required_endpoints(self):
        """Router initialization creates all required endpoints"""
        from routers.employee_mgmt_router import init_employee_mgmt_router
        from unittest.mock import MagicMock, AsyncMock
        
        # Mock dependencies
        mock_db = MagicMock()
        mock_verify_token = AsyncMock(return_value={"uid": "test"})
        mock_resolve_seller = MagicMock(return_value="seller123")
        mock_sio = MagicMock()
        
        # Create router
        router = init_employee_mgmt_router(mock_db, mock_verify_token, mock_resolve_seller, mock_sio)
        
        # Check routes exist
        routes = {r.path for r in router.routes}
        
        expected_routes = {
            "/employee-mgmt/modules",
            "/employee-mgmt/role-templates",
            "/employee-mgmt/search",
            "/employee-mgmt/link",
            "/employee-mgmt/list",
            "/employee-mgmt/{employee_id}",
            "/employee-mgmt/{employee_id}/unlink",
            "/employee-mgmt/{employee_id}/relink",
            "/employee-mgmt/my-access",
            "/employee-mgmt/logs",
            "/employee-mgmt/unlink-all"
        }
        
        for route in expected_routes:
            assert route in routes, f"Missing route: {route}"
        
        print(f"✓ Router has all {len(expected_routes)} required endpoints")


class TestSocketIOIntegration:
    """Test Socket.IO setup for real-time access sync"""
    
    def test_socketio_mounted_in_server(self):
        """Socket.IO is mounted at /api/socket.io in server.py"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Verify Socket.IO setup in server code
        assert 'import socketio' in content, "Missing socketio import"
        assert 'AsyncServer' in content, "Missing AsyncServer creation"
        assert 'app.mount("/api/socket.io"' in content, "Socket.IO not mounted at /api/socket.io"
        assert 'ASGIApp' in content, "Missing ASGIApp wrapper"
        
        print("✓ Socket.IO correctly configured in server.py at /api/socket.io")


class TestFrontendDataTestIds:
    """Verify frontend has required data-testid attributes by checking source code"""
    
    def test_employee_page_has_data_testids(self):
        """Employee management page.tsx has required data-testid attributes"""
        page_path = "/app/frontend/src/app/seller/business-tools/employees/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Static data-testid attributes (exact match)
        static_testids = [
            "employee-mgmt-page",
            "employee-heading",
            "search-section",
            "search-email-input",
            "search-btn",
            "employee-tabs",
            "permission-grid",
            "link-modal",
            "edit-modal",
            "logs-modal",
            "view-logs-btn",
        ]
        
        # Dynamic data-testid attributes (template literal pattern)
        dynamic_patterns = [
            "tab-",  # tab-{key} where key is active, pending, unlinked
        ]
        
        missing = []
        for testid in static_testids:
            if f'data-testid="{testid}"' not in content:
                missing.append(testid)
        
        for pattern in dynamic_patterns:
            if f'data-testid={{`{pattern}' not in content:
                missing.append(f"dynamic:{pattern}")
        
        assert len(missing) == 0, f"Missing data-testid attributes: {missing}"
        print(f"✓ All {len(static_testids)} static and {len(dynamic_patterns)} dynamic data-testid patterns found")
    
    def test_permission_grid_has_module_testids(self):
        """Permission grid has data-testid for each module row"""
        page_path = "/app/frontend/src/app/seller/business-tools/employees/page.tsx"
        
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for dynamic test ID pattern
        assert "perm-row-" in content, "Missing perm-row-{module} pattern"
        assert "perm-view-" in content, "Missing perm-view-{module} pattern"
        assert "perm-action-" in content, "Missing perm-action-{module} pattern"
        
        print("✓ Permission grid has dynamic data-testid patterns for modules")


class TestEmployeeAccessContext:
    """Test EmployeeAccessContext provides correct functions"""
    
    def test_context_file_has_required_exports(self):
        """EmployeeAccessContext.tsx exports required items"""
        ctx_path = "/app/frontend/src/context/EmployeeAccessContext.tsx"
        
        with open(ctx_path, 'r') as f:
            content = f.read()
        
        required_exports = [
            "useEmployeeAccess",
            "EmployeeAccessProvider",
            "canView",
            "canAction",
            "isFullAdmin",
            "isDisabled",
            "isUnlinked"
        ]
        
        for item in required_exports:
            assert item in content, f"Missing export/function: {item}"
        
        print(f"✓ EmployeeAccessContext has all {len(required_exports)} required exports")
    
    def test_context_uses_socket_io(self):
        """EmployeeAccessContext uses Socket.IO for real-time sync"""
        ctx_path = "/app/frontend/src/context/EmployeeAccessContext.tsx"
        
        with open(ctx_path, 'r') as f:
            content = f.read()
        
        assert "socket.io-client" in content, "Missing socket.io-client import"
        assert "/api/socket.io" in content, "Missing Socket.IO path configuration"
        assert "access_updated" in content, "Missing access_updated event listener"
        
        print("✓ EmployeeAccessContext uses Socket.IO with correct path")


class TestLayoutIntegration:
    """Test layout wraps with EmployeeAccessProvider"""
    
    def test_layout_has_employee_access_provider(self):
        """Layout.tsx wraps children with EmployeeAccessProvider"""
        layout_path = "/app/frontend/src/app/seller/business-tools/layout.tsx"
        
        with open(layout_path, 'r') as f:
            content = f.read()
        
        assert "EmployeeAccessProvider" in content, "Missing EmployeeAccessProvider import/usage"
        assert "from '@/context/EmployeeAccessContext'" in content or \
               "from \"@/context/EmployeeAccessContext\"" in content, \
               "Missing EmployeeAccessContext import"
        
        print("✓ Layout.tsx imports and uses EmployeeAccessProvider")
    
    def test_nav_items_have_module_field(self):
        """navItems in layout have module field for permission-based filtering"""
        layout_path = "/app/frontend/src/app/seller/business-tools/layout.tsx"
        
        with open(layout_path, 'r') as f:
            content = f.read()
        
        # Check that navItems include module field
        assert "module:" in content, "Missing module field in navItems"
        
        # Check expected module values are present
        expected_modules = ["dashboard", "inventory", "invoices", "quotations", 
                          "reports", "buyers", "suppliers", "employees", "settings"]
        
        found_modules = []
        for module in expected_modules:
            if f"module: '{module}'" in content or f'module: "{module}"' in content:
                found_modules.append(module)
        
        assert len(found_modules) >= 5, f"Expected at least 5 module fields, found: {found_modules}"
        print(f"✓ navItems have module field for {len(found_modules)} modules: {found_modules}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
