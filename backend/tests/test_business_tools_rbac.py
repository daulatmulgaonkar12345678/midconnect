"""
Business Tools RBAC & Employee Management API Tests
Tests for:
- Permissions API
- Role CRUD operations
- Employee CRUD operations
- Role deletion constraints (employees assigned)
"""

import pytest
import requests
import os
import uuid

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

# Test auth header (dev mode)
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Store created resources for cleanup
created_roles = []
created_employees = []


class TestHealthCheck:
    """Basic health check to verify API is running"""
    
    def test_health_endpoint(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health check passed")


class TestPermissionsEndpoint:
    """Test GET /api/business-tools/permissions - list all available permissions"""
    
    def test_get_permissions_returns_all_9_permissions(self):
        """Verify all 9 permissions are returned"""
        response = requests.get(f"{BASE_URL}/api/business-tools/permissions", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        data = response.json()
        assert "permissions" in data, "Response missing 'permissions' key"
        
        permissions = data["permissions"]
        assert len(permissions) == 9, f"Expected 9 permissions, got {len(permissions)}"
        
        # Verify each permission has required fields
        expected_permissions = [
            "manage_listings",
            "manage_inventory", 
            "view_enquiries",
            "manage_buyers",
            "manage_suppliers",
            "create_invoice",
            "view_reports",
            "manage_employees",
            "manage_roles"
        ]
        
        permission_keys = [p["key"] for p in permissions]
        for expected in expected_permissions:
            assert expected in permission_keys, f"Missing permission: {expected}"
        
        # Verify structure of each permission
        for perm in permissions:
            assert "key" in perm, f"Permission missing 'key': {perm}"
            assert "label" in perm, f"Permission missing 'label': {perm}"
            assert "description" in perm, f"Permission missing 'description': {perm}"
        
        print(f"✓ All 9 permissions returned: {permission_keys}")
    
    def test_get_permissions_requires_auth(self):
        """Verify permissions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/permissions")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("✓ Permissions endpoint requires authentication")


class TestMyPermissionsEndpoint:
    """Test GET /api/business-tools/my-permissions - get current user's permissions"""
    
    def test_seller_admin_has_all_permissions(self):
        """Verify seller admin has isAdmin=true and all permissions"""
        response = requests.get(f"{BASE_URL}/api/business-tools/my-permissions", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get my-permissions: {response.text}"
        
        data = response.json()
        
        # Seller admin should have all permissions
        assert data.get("accountType") == "seller", f"Expected accountType 'seller', got {data.get('accountType')}"
        assert data.get("isAdmin") == True, f"Expected isAdmin=True for seller admin, got {data.get('isAdmin')}"
        
        # Verify all 9 permissions are present
        permissions = data.get("permissions", [])
        assert len(permissions) == 9, f"Expected 9 permissions for seller admin, got {len(permissions)}"
        
        expected_permissions = [
            "manage_listings", "manage_inventory", "view_enquiries",
            "manage_buyers", "manage_suppliers", "create_invoice",
            "view_reports", "manage_employees", "manage_roles"
        ]
        
        for expected in expected_permissions:
            assert expected in permissions, f"Seller admin missing permission: {expected}"
        
        print(f"✓ Seller admin has isAdmin=True and all 9 permissions")
    
    def test_my_permissions_requires_auth(self):
        """Verify my-permissions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/my-permissions")
        assert response.status_code in [401, 422], f"Expected 401/422 without auth, got {response.status_code}"
        print("✓ My-permissions endpoint requires authentication")


class TestRoleCRUD:
    """Test Role CRUD operations"""
    
    def test_create_role_success(self):
        """Test POST /api/business-tools/roles - create a new role"""
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_Role_{unique_id}",
            "description": "Test role for automated testing",
            "permissions": ["view_enquiries", "manage_inventory"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create role: {response.text}"
        
        data = response.json()
        assert "role" in data, "Response missing 'role' key"
        
        role = data["role"]
        assert role.get("name") == role_data["name"], f"Role name mismatch"
        assert role.get("description") == role_data["description"], f"Role description mismatch"
        assert set(role.get("permissions", [])) == set(role_data["permissions"]), f"Role permissions mismatch"
        assert "id" in role, "Role missing 'id'"
        assert role.get("isActive") == True, "New role should be active"
        
        # Store for cleanup
        created_roles.append(role["id"])
        
        print(f"✓ Created role: {role['name']} (id: {role['id']})")
        return role
    
    def test_create_role_with_invalid_permission(self):
        """Test role creation fails with invalid permissions"""
        role_data = {
            "name": f"TEST_InvalidRole_{uuid.uuid4().hex[:8]}",
            "description": "Should fail",
            "permissions": ["view_enquiries", "invalid_permission"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for invalid permission, got {response.status_code}"
        print("✓ Role creation correctly fails with invalid permission")
    
    def test_create_role_duplicate_name(self):
        """Test role creation fails with duplicate name"""
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_DuplicateRole_{unique_id}",
            "description": "First role",
            "permissions": ["view_enquiries"]
        }
        
        # Create first role
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create first role: {response.text}"
        role_id = response.json()["role"]["id"]
        created_roles.append(role_id)
        
        # Try to create duplicate
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for duplicate role name, got {response.status_code}"
        print("✓ Role creation correctly fails with duplicate name")
    
    def test_list_roles(self):
        """Test GET /api/business-tools/roles - list all roles for seller"""
        response = requests.get(f"{BASE_URL}/api/business-tools/roles", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list roles: {response.text}"
        
        data = response.json()
        assert "roles" in data, "Response missing 'roles' key"
        assert isinstance(data["roles"], list), "Roles should be a list"
        
        print(f"✓ Listed {len(data['roles'])} roles")
        return data["roles"]
    
    def test_update_role(self):
        """Test PUT /api/business-tools/roles/{role_id} - update a role"""
        # First create a role
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_UpdateRole_{unique_id}",
            "description": "Original description",
            "permissions": ["view_enquiries"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create role for update test: {response.text}"
        
        role_id = response.json()["role"]["id"]
        created_roles.append(role_id)
        
        # Update the role
        update_data = {
            "name": f"TEST_UpdatedRole_{unique_id}",
            "description": "Updated description",
            "permissions": ["view_enquiries", "manage_buyers"]
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/roles/{role_id}", json=update_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update role: {response.text}"
        
        data = response.json()
        role = data["role"]
        assert role["name"] == update_data["name"], "Name not updated"
        assert role["description"] == update_data["description"], "Description not updated"
        assert set(role["permissions"]) == set(update_data["permissions"]), "Permissions not updated"
        
        print(f"✓ Role updated successfully: {role['name']}")
    
    def test_delete_role_without_employees(self):
        """Test DELETE /api/business-tools/roles/{role_id} - delete a role without employees"""
        # Create a role
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_DeleteRole_{unique_id}",
            "description": "To be deleted",
            "permissions": ["view_reports"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create role for delete test: {response.text}"
        
        role_id = response.json()["role"]["id"]
        
        # Delete the role
        response = requests.delete(f"{BASE_URL}/api/business-tools/roles/{role_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to delete role: {response.text}"
        
        print(f"✓ Role deleted successfully")
    
    def test_delete_nonexistent_role(self):
        """Test deleting a role that doesn't exist returns 404"""
        fake_id = "000000000000000000000000"
        response = requests.delete(f"{BASE_URL}/api/business-tools/roles/{fake_id}", headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent role, got {response.status_code}"
        print("✓ Delete non-existent role returns 404")


class TestEmployeeCRUD:
    """Test Employee CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup_role_for_employees(self):
        """Create a role for employee tests"""
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_EmployeeRole_{unique_id}",
            "description": "Role for employee tests",
            "permissions": ["view_enquiries", "manage_inventory"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        if response.status_code == 200:
            self.role_id = response.json()["role"]["id"]
            created_roles.append(self.role_id)
        else:
            # Use existing role if available
            roles_response = requests.get(f"{BASE_URL}/api/business-tools/roles", headers=AUTH_HEADER)
            if roles_response.status_code == 200:
                roles = roles_response.json().get("roles", [])
                if roles:
                    self.role_id = roles[0]["id"]
                else:
                    pytest.skip("No role available for employee tests")
            else:
                pytest.skip("Cannot get roles for employee tests")
    
    def test_create_employee_success(self):
        """Test POST /api/business-tools/employees - create a new employee"""
        unique_id = uuid.uuid4().hex[:8]
        employee_data = {
            "name": f"TEST_Employee_{unique_id}",
            "email": f"test.employee.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": self.role_id,
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create employee: {response.text}"
        
        data = response.json()
        assert "employee" in data, "Response missing 'employee' key"
        
        employee = data["employee"]
        assert employee.get("name") == employee_data["name"], "Employee name mismatch"
        assert employee.get("email") == employee_data["email"].lower(), "Employee email mismatch"
        assert employee.get("accountType") == "employee", "accountType should be 'employee'"
        assert employee.get("status") == "active", "New employee should be active"
        assert "id" in employee, "Employee missing 'id'"
        assert "sellerId" in employee, "Employee should have sellerId"
        assert "roleId" in employee, "Employee should have roleId"
        
        created_employees.append(employee["id"])
        
        print(f"✓ Created employee: {employee['name']} (id: {employee['id']})")
        return employee
    
    def test_create_employee_with_invalid_role(self):
        """Test employee creation fails with invalid role ID"""
        unique_id = uuid.uuid4().hex[:8]
        employee_data = {
            "name": f"TEST_InvalidEmployee_{unique_id}",
            "email": f"invalid.employee.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": "000000000000000000000000",  # Non-existent role
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for invalid role, got {response.status_code}"
        print("✓ Employee creation correctly fails with invalid role ID")
    
    def test_create_employee_duplicate_email(self):
        """Test employee creation fails with duplicate email"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"duplicate.employee.{unique_id}@example.com"
        
        employee_data = {
            "name": f"TEST_DuplicateEmployee1_{unique_id}",
            "email": email,
            "password": "TestPassword123!",
            "roleId": self.role_id,
            "phone": "9876543210"
        }
        
        # Create first employee
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create first employee: {response.text}"
        emp_id = response.json()["employee"]["id"]
        created_employees.append(emp_id)
        
        # Try to create duplicate
        employee_data["name"] = f"TEST_DuplicateEmployee2_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        print("✓ Employee creation correctly fails with duplicate email")
    
    def test_list_employees(self):
        """Test GET /api/business-tools/employees - list all employees"""
        response = requests.get(f"{BASE_URL}/api/business-tools/employees", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list employees: {response.text}"
        
        data = response.json()
        assert "employees" in data, "Response missing 'employees' key"
        assert isinstance(data["employees"], list), "Employees should be a list"
        
        # Verify employee structure if any exist
        for emp in data["employees"]:
            assert "id" in emp, "Employee missing 'id'"
            assert "email" in emp, "Employee missing 'email'"
            assert "name" in emp, "Employee missing 'name'"
            assert "roleName" in emp, "Employee missing 'roleName'"
        
        print(f"✓ Listed {len(data['employees'])} employees")
        return data["employees"]
    
    def test_update_employee(self):
        """Test PUT /api/business-tools/employees/{employee_id} - update an employee"""
        # First create an employee
        unique_id = uuid.uuid4().hex[:8]
        employee_data = {
            "name": f"TEST_UpdateEmployee_{unique_id}",
            "email": f"update.employee.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": self.role_id,
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create employee for update test: {response.text}"
        
        emp_id = response.json()["employee"]["id"]
        created_employees.append(emp_id)
        
        # Update the employee
        update_data = {
            "name": f"TEST_UpdatedEmployee_{unique_id}",
            "phone": "1234567890",
            "status": "active"
        }
        
        response = requests.put(f"{BASE_URL}/api/business-tools/employees/{emp_id}", json=update_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update employee: {response.text}"
        
        data = response.json()
        employee = data["employee"]
        assert employee["name"] == update_data["name"], "Name not updated"
        assert employee["phone"] == update_data["phone"], "Phone not updated"
        
        print(f"✓ Employee updated successfully: {employee['name']}")
    
    def test_deactivate_employee(self):
        """Test DELETE /api/business-tools/employees/{employee_id} - deactivate (soft delete) an employee"""
        # First create an employee
        unique_id = uuid.uuid4().hex[:8]
        employee_data = {
            "name": f"TEST_DeactivateEmployee_{unique_id}",
            "email": f"deactivate.employee.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": self.role_id,
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create employee for deactivate test: {response.text}"
        
        emp_id = response.json()["employee"]["id"]
        
        # Deactivate the employee
        response = requests.delete(f"{BASE_URL}/api/business-tools/employees/{emp_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to deactivate employee: {response.text}"
        
        # Verify employee is deactivated (status=inactive) via list
        response = requests.get(f"{BASE_URL}/api/business-tools/employees", headers=AUTH_HEADER)
        assert response.status_code == 200
        employees = response.json().get("employees", [])
        emp = next((e for e in employees if e["id"] == emp_id), None)
        if emp:
            assert emp.get("status") == "inactive", "Employee should be inactive after soft delete"
        
        print(f"✓ Employee deactivated successfully (soft delete)")
    
    def test_update_nonexistent_employee(self):
        """Test updating a non-existent employee returns 404"""
        fake_id = "000000000000000000000000"
        update_data = {"name": "Should Fail"}
        
        response = requests.put(f"{BASE_URL}/api/business-tools/employees/{fake_id}", json=update_data, headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent employee, got {response.status_code}"
        print("✓ Update non-existent employee returns 404")


class TestRoleDeletionWithEmployees:
    """Test that role deletion fails when employees are assigned"""
    
    def test_cannot_delete_role_with_assigned_employees(self):
        """Verify role deletion fails if employees are assigned to it"""
        unique_id = uuid.uuid4().hex[:8]
        
        # Create a role
        role_data = {
            "name": f"TEST_RoleWithEmployee_{unique_id}",
            "description": "Role with employees attached",
            "permissions": ["view_enquiries"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create role: {response.text}"
        role_id = response.json()["role"]["id"]
        created_roles.append(role_id)
        
        # Create an employee with this role
        employee_data = {
            "name": f"TEST_EmployeeForRoleDelete_{unique_id}",
            "email": f"employee.role.delete.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": role_id,
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create employee: {response.text}"
        emp_id = response.json()["employee"]["id"]
        created_employees.append(emp_id)
        
        # Try to delete the role - should fail
        response = requests.delete(f"{BASE_URL}/api/business-tools/roles/{role_id}", headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 when deleting role with employees, got {response.status_code}"
        
        data = response.json()
        assert "employees are assigned" in data.get("detail", "").lower() or "cannot delete" in data.get("detail", "").lower(), \
            f"Expected error message about employees being assigned, got: {data}"
        
        print("✓ Role deletion correctly fails when employees are assigned")


class TestEmployeeDocumentStructure:
    """Verify employee document has correct fields in users collection"""
    
    def test_employee_document_has_required_fields(self):
        """Verify employee doc has: accountType=employee, sellerId, roleId, status=active"""
        # Create a role first
        unique_id = uuid.uuid4().hex[:8]
        role_data = {
            "name": f"TEST_DocStructureRole_{unique_id}",
            "description": "Role for document structure test",
            "permissions": ["view_enquiries"]
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/roles", json=role_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create role: {response.text}"
        role_id = response.json()["role"]["id"]
        created_roles.append(role_id)
        
        # Create employee
        employee_data = {
            "name": f"TEST_DocStructureEmployee_{unique_id}",
            "email": f"doc.structure.{unique_id}@example.com",
            "password": "TestPassword123!",
            "roleId": role_id,
            "phone": "9876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/employees", json=employee_data, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create employee: {response.text}"
        
        employee = response.json()["employee"]
        created_employees.append(employee["id"])
        
        # Verify required fields
        assert employee.get("accountType") == "employee", f"accountType should be 'employee', got {employee.get('accountType')}"
        assert employee.get("sellerId") is not None, "Employee should have sellerId"
        assert employee.get("roleId") is not None, "Employee should have roleId"
        assert employee.get("status") == "active", f"status should be 'active', got {employee.get('status')}"
        
        print(f"✓ Employee document has correct structure:")
        print(f"  - accountType: {employee.get('accountType')}")
        print(f"  - sellerId: {employee.get('sellerId')}")
        print(f"  - roleId: {employee.get('roleId')}")
        print(f"  - status: {employee.get('status')}")


class TestCleanup:
    """Cleanup test data - run last"""
    
    def test_cleanup_test_employees(self):
        """Deactivate test employees"""
        cleaned = 0
        for emp_id in created_employees:
            try:
                response = requests.delete(f"{BASE_URL}/api/business-tools/employees/{emp_id}", headers=AUTH_HEADER)
                if response.status_code == 200:
                    cleaned += 1
            except Exception:
                pass
        print(f"✓ Cleaned up {cleaned} test employees")
    
    def test_cleanup_test_roles(self):
        """Delete test roles (after employees are deactivated)"""
        cleaned = 0
        for role_id in created_roles:
            try:
                response = requests.delete(f"{BASE_URL}/api/business-tools/roles/{role_id}", headers=AUTH_HEADER)
                if response.status_code == 200:
                    cleaned += 1
            except Exception:
                pass
        print(f"✓ Cleaned up {cleaned} test roles")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
