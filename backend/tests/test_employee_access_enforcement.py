"""
Employee Access Enforcement Tests
=================================
Tests for admin-controlled employee access enforcement via maxEmployees subscription override.

Features tested:
1. When maxEmployees=0, employees get 403 EMPLOYEE_ACCESS_BLOCKED on any API call
2. When maxEmployees>0, employees can access normally
3. Seller (boss) is NOT blocked even when maxEmployees=0
4. Link employee (POST /api/business-tools/employee-mgmt/link) blocked when limit reached
5. Admin users are not blocked by employee guard
"""

import pytest
import requests
import os
from bson import ObjectId
from pymongo import MongoClient

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com').rstrip('/')

# MongoDB connection for test setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'midconnect')

# Test data
SELLER_ID = "69a0ac1089b696c2337c5a6e"
EMPLOYEE_ID = "69d7e4bdeb57ec2620fb07f5"
EMPLOYEE_FIREBASE_UID = "test-employee-uid"
ADMIN_TOKEN = "dev-test-token"


@pytest.fixture(scope="module")
def db():
    """MongoDB connection fixture"""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def api_client():
    """Requests session fixture"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(autouse=True)
def reset_subscription(db):
    """Reset subscription to known state before each test"""
    # Set maxEmployees to 0 for testing blocked state
    db.subscriptions.update_one(
        {"userId": ObjectId(SELLER_ID)},
        {"$set": {"overrides.maxEmployees": 0}}
    )
    yield
    # Reset to 5 after tests
    db.subscriptions.update_one(
        {"userId": ObjectId(SELLER_ID)},
        {"$set": {"overrides.maxEmployees": 5}}
    )


class TestEmployeeAccessBlocked:
    """Tests for employee access being blocked when maxEmployees=0"""
    
    def test_employee_blocked_on_my_access_endpoint(self, api_client, db):
        """Employee should get 403 EMPLOYEE_ACCESS_BLOCKED when maxEmployees=0"""
        # Ensure maxEmployees=0
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "EMPLOYEE_ACCESS_BLOCKED"
        assert "employer's subscription" in data["detail"]["message"]
    
    def test_employee_blocked_on_inventory_endpoint(self, api_client, db):
        """Employee should be blocked on any business-tools endpoint"""
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "EMPLOYEE_ACCESS_BLOCKED"
    
    def test_employee_blocked_on_invoices_endpoint(self, api_client, db):
        """Employee should be blocked on invoices endpoint"""
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "EMPLOYEE_ACCESS_BLOCKED"


class TestEmployeeAccessAllowed:
    """Tests for employee access being allowed when maxEmployees>0"""
    
    def test_employee_allowed_when_max_employees_positive(self, api_client, db):
        """Employee should be able to access when maxEmployees>0"""
        # Set maxEmployees to 5
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 5}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "userId" in data
        assert data["userId"] == EMPLOYEE_ID
        assert data["status"] == "active"
    
    def test_employee_allowed_when_max_employees_unlimited(self, api_client, db):
        """Employee should be able to access when maxEmployees=-1 (unlimited)"""
        # Set maxEmployees to -1 (unlimited)
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": -1}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["userId"] == EMPLOYEE_ID


class TestSellerNotBlocked:
    """Tests for seller (boss) not being blocked even when maxEmployees=0"""
    
    def test_seller_not_blocked_when_max_employees_zero(self, api_client, db):
        """Seller should NOT be blocked even when maxEmployees=0"""
        # Ensure maxEmployees=0
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["userId"] == SELLER_ID
        assert data["isAdmin"] == True
    
    def test_seller_can_access_inventory_when_max_employees_zero(self, api_client, db):
        """Seller should be able to access inventory even when maxEmployees=0"""
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        
        # Should get 200 (or data response), not 403
        assert response.status_code != 403, "Seller should not be blocked"


class TestLinkEmployeeLimit:
    """Tests for link employee endpoint respecting maxEmployees limit"""
    
    def test_link_blocked_when_limit_reached(self, api_client, db):
        """Link employee should be blocked when maxEmployees limit is reached"""
        # Count current employees
        current_count = db.users.count_documents({
            "companyId": ObjectId(SELLER_ID),
            "employeeStatus": {"$in": ["active", "disabled"]}
        })
        
        # Set maxEmployees to current count (limit reached)
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": current_count}}
        )
        
        # Create a test buyer to link
        test_email = "test_link_limit@example.com"
        db.users.delete_one({"email": test_email})  # Clean up first
        db.users.insert_one({
            "email": test_email,
            "firebaseUid": "test-link-limit-uid",
            "accountType": "buyer"
        })
        
        try:
            response = api_client.post(
                f"{BASE_URL}/api/business-tools/employee-mgmt/link",
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
                json={
                    "email": test_email,
                    "role": "Sales Executive",
                    "permissions": {"modules": {}, "panels": {}}
                }
            )
            
            assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
            assert "limit reached" in response.json()["detail"].lower()
        finally:
            # Clean up test user
            db.users.delete_one({"email": test_email})
    
    def test_link_allowed_when_under_limit(self, api_client, db):
        """Link employee should succeed when under maxEmployees limit"""
        # Count current employees
        current_count = db.users.count_documents({
            "companyId": ObjectId(SELLER_ID),
            "employeeStatus": {"$in": ["active", "disabled"]}
        })
        
        # Set maxEmployees to current count + 1 (room for one more)
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": current_count + 1}}
        )
        
        # Create a test buyer to link
        test_email = "test_link_success@example.com"
        db.users.delete_one({"email": test_email})  # Clean up first
        db.users.insert_one({
            "email": test_email,
            "firebaseUid": "test-link-success-uid",
            "accountType": "buyer"
        })
        
        try:
            response = api_client.post(
                f"{BASE_URL}/api/business-tools/employee-mgmt/link",
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
                json={
                    "email": test_email,
                    "role": "Sales Executive",
                    "permissions": {"modules": {}, "panels": {}}
                }
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert "linked successfully" in data["message"]
            
            # Verify employee was linked
            linked_user = db.users.find_one({"email": test_email})
            assert linked_user["companyId"] == ObjectId(SELLER_ID)
            assert linked_user["employeeStatus"] == "active"
        finally:
            # Clean up - unlink and delete test user
            db.users.delete_one({"email": test_email})


class TestAdminNotBlocked:
    """Tests for admin users not being blocked by employee guard"""
    
    def test_admin_not_blocked_even_with_company_id(self, api_client, db):
        """Admin users should not be blocked even if they have companyId"""
        # The admin user (dev-test-token) is also a seller
        # They should not be blocked by the employee guard
        
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/list?tab=active",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        
        # Admin should be able to list employees
        assert response.status_code == 200, f"Admin should not be blocked: {response.text}"


class TestAccessRestoredAfterLimitIncrease:
    """Tests for employee access being restored after maxEmployees is increased"""
    
    def test_access_restored_after_limit_increase(self, api_client, db):
        """Employee access should be restored when maxEmployees is increased from 0"""
        # First, verify employee is blocked with maxEmployees=0
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 0}}
        )
        
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        assert response.status_code == 403
        
        # Now increase maxEmployees
        db.subscriptions.update_one(
            {"userId": ObjectId(SELLER_ID)},
            {"$set": {"overrides.maxEmployees": 5}}
        )
        
        # Employee should now have access
        response = api_client.get(
            f"{BASE_URL}/api/business-tools/employee-mgmt/my-access",
            headers={"Authorization": f"Bearer {EMPLOYEE_FIREBASE_UID}"}
        )
        
        assert response.status_code == 200, f"Expected 200 after limit increase, got {response.status_code}"
        data = response.json()
        assert data["userId"] == EMPLOYEE_ID


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
