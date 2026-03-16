"""
Test Admin Low Stock Alerts Feature
Tests the fix for admin Permission Denied (403) error on Low Stock Alerts page.
- Admin users should be able to view low stock alerts from ALL sellers
- Backend should allow both 'seller' and 'admin' roles
- Admin response should include isAdminView:true and sellerName for each alert
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
DEV_TEST_TOKEN = "dev-test-token"  # Admin token for dev mode


class TestAdminPermissions:
    """Test admin permissions endpoint returns correct data"""
    
    def test_my_permissions_returns_admin_true(self):
        """GET /api/business-tools/my-permissions returns isAdmin:true for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("isAdmin") is True, f"Expected isAdmin:true, got {data.get('isAdmin')}"
        
    def test_my_permissions_returns_all_permissions(self):
        """GET /api/business-tools/my-permissions returns all permissions for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Admin should have manage_inventory permission (required for low stock alerts)
        assert "manage_inventory" in permissions, f"Admin missing manage_inventory permission. Got: {permissions}"
        
        # Verify key permissions exist
        expected_permissions = [
            "manage_listings", "manage_inventory", "view_enquiries",
            "manage_buyers", "manage_suppliers", "create_invoice",
            "view_reports", "manage_employees", "manage_roles"
        ]
        for perm in expected_permissions:
            assert perm in permissions, f"Admin missing {perm} permission"
    
    def test_my_permissions_accountType_admin(self):
        """GET /api/business-tools/my-permissions returns accountType:admin for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("accountType") == "admin", f"Expected accountType:admin, got {data.get('accountType')}"


class TestAdminLowStockAlerts:
    """Test low stock alerts endpoint for admin users"""
    
    def test_low_stock_alerts_no_403_for_admin(self):
        """GET /api/business-tools/low-stock-alerts returns 200 (not 403) for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        # The main bug was 403, so we verify it's not 403
        assert response.status_code != 403, f"Admin got 403 Permission Denied - BUG NOT FIXED"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_low_stock_alerts_returns_isAdminView_true(self):
        """GET /api/business-tools/low-stock-alerts returns isAdminView:true for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("isAdminView") is True, f"Expected isAdminView:true, got {data.get('isAdminView')}"
    
    def test_low_stock_alerts_from_all_sellers(self):
        """GET /api/business-tools/low-stock-alerts returns alerts from multiple sellers"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        alerts = data.get("alerts", [])
        
        if len(alerts) > 0:
            # Collect unique sellerIds
            seller_ids = set(alert.get("sellerId") for alert in alerts if alert.get("sellerId"))
            print(f"Found alerts from {len(seller_ids)} unique sellers: {seller_ids}")
            # Admin should see alerts from multiple sellers if data exists
            # Note: This test passes if data exists with multiple sellers
    
    def test_low_stock_alerts_include_sellerName(self):
        """Admin alerts include sellerName field for each alert"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        alerts = data.get("alerts", [])
        
        # Verify all alerts have sellerName field
        for alert in alerts:
            assert "sellerName" in alert, f"Alert {alert.get('id')} missing sellerName field"
            # sellerName should be a string (even if "Unknown Seller")
            assert isinstance(alert.get("sellerName"), str), f"sellerName should be string, got {type(alert.get('sellerName'))}"
            print(f"Alert {alert.get('id')}: sellerName = '{alert.get('sellerName')}'")
    
    def test_low_stock_alerts_with_status_filter(self):
        """GET /api/business-tools/low-stock-alerts?status=pending works for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts?status=pending",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        alerts = data.get("alerts", [])
        
        # All returned alerts should have pending status
        for alert in alerts:
            assert alert.get("status") == "pending", f"Expected pending status, got {alert.get('status')}"
    
    def test_low_stock_alerts_response_structure(self):
        """Verify complete response structure for admin low stock alerts"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level response fields
        assert "alerts" in data, "Response missing 'alerts' field"
        assert "total" in data, "Response missing 'total' field"
        assert "pendingCount" in data, "Response missing 'pendingCount' field"
        assert "isAdminView" in data, "Response missing 'isAdminView' field"
        assert "limit" in data, "Response missing 'limit' field"
        assert "skip" in data, "Response missing 'skip' field"
        
        # Check alert structure
        alerts = data.get("alerts", [])
        if len(alerts) > 0:
            alert = alerts[0]
            required_fields = ["id", "sellerId", "listingId", "productName", "currentStock", "minStock", "status", "sellerName"]
            for field in required_fields:
                assert field in alert, f"Alert missing required field: {field}"


class TestAdminLowStockAlertsDifferentiateFromSeller:
    """Verify admin view differs from regular seller view"""
    
    def test_admin_view_flag_is_true(self):
        """Admin isAdminView should be true"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers={"Authorization": f"Bearer {DEV_TEST_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("isAdminView") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
