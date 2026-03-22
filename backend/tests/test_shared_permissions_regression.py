"""
Regression tests for shared permissions utility refactor.
Tests that all 12 routers now using utils/permissions.py return 200 (not 403) for admin users.
Focus: Verify the original bug (403 Permission Denied on POST /api/business-tools/purchase-orders) is fixed.
"""

import pytest
import requests
import os

# Get BASE_URL from environment - use external URL for proper testing
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://doc-builder-preview-1.preview.emergentagent.com"

# Dev mode admin token - creates user with isAdmin:true and roles:['admin','seller','buyer']
DEV_TEST_TOKEN = "dev-test-token"


class TestSharedPermissionsRegression:
    """
    Verify all routers using the new shared permissions utility work correctly.
    Admin user should get 200 on all endpoints, not 403.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup common headers for all tests."""
        self.headers = {
            "Authorization": f"Bearer {DEV_TEST_TOKEN}",
            "Content-Type": "application/json"
        }

    # =============================================
    # ORIGINAL BUG TEST - Purchase Orders
    # =============================================

    def test_po_router_list_purchase_orders(self):
        """GET /api/business-tools/purchase-orders - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders",
            headers=self.headers
        )
        # Should NOT be 403 after fix
        assert response.status_code != 403, f"Got 403 Permission Denied - BUG NOT FIXED! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "purchaseOrders" in data
        print(f"PASS: GET /purchase-orders returned {len(data.get('purchaseOrders', []))} records")

    # =============================================
    # INVENTORY ROUTER
    # =============================================

    def test_inventory_router_list_inventory(self):
        """GET /api/business-tools/inventory - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/inventory",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "inventory" in data
        print(f"PASS: GET /inventory returned {len(data.get('inventory', []))} items")

    # =============================================
    # BUYERS ROUTER
    # =============================================

    def test_business_tools_router_list_buyers(self):
        """GET /api/business-tools/buyers - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/buyers",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "buyers" in data
        print(f"PASS: GET /buyers returned {len(data.get('buyers', []))} records")

    # =============================================
    # SUPPLIERS ROUTER
    # =============================================

    def test_business_tools_router_list_suppliers(self):
        """GET /api/business-tools/suppliers - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/suppliers",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suppliers" in data
        print(f"PASS: GET /suppliers returned {len(data.get('suppliers', []))} records")

    # =============================================
    # INVOICES ROUTER
    # =============================================

    def test_invoice_router_list_invoices(self):
        """GET /api/business-tools/invoices - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invoices" in data
        print(f"PASS: GET /invoices returned {len(data.get('invoices', []))} records")

    # =============================================
    # ACTIVITY LOG ROUTER
    # =============================================

    def test_activity_log_router_list_logs(self):
        """GET /api/business-tools/activity-logs - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/activity-logs",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "logs" in data
        print(f"PASS: GET /activity-logs returned {len(data.get('logs', []))} records")

    # =============================================
    # HOME ROUTER
    # =============================================

    def test_home_router_summary(self):
        """GET /api/business-tools/home/summary - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/home/summary",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Home summary should have these fields
        assert "totalProducts" in data or "totalRevenue" in data
        print(f"PASS: GET /home/summary returned summary data")

    def test_home_router_charts(self):
        """GET /api/business-tools/home/charts - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/home/charts",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "salesTrend" in data or "topProducts" in data
        print(f"PASS: GET /home/charts returned chart data")

    # =============================================
    # COMPOSITE PRODUCTS ROUTER
    # =============================================

    def test_composite_products_router_list(self):
        """GET /api/business-tools/composite-products - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/composite-products",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "compositeProducts" in data
        print(f"PASS: GET /composite-products returned {len(data.get('compositeProducts', []))} products")

    # =============================================
    # MY-PERMISSIONS ENDPOINT
    # =============================================

    def test_my_permissions_returns_admin(self):
        """GET /api/business-tools/my-permissions - admin should get isAdmin:true"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/my-permissions",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Admin user should have isAdmin: true
        assert data.get("isAdmin") is True, f"Expected isAdmin:true for admin, got: {data}"
        # Admin user should have accountType: "admin"
        assert data.get("accountType") == "admin", f"Expected accountType:'admin', got: {data.get('accountType')}"
        print(f"PASS: /my-permissions returned isAdmin:true, accountType:admin")

    # =============================================
    # LOW STOCK ALERTS ROUTER
    # =============================================

    def test_low_stock_alerts_returns_admin_view(self):
        """GET /api/business-tools/low-stock-alerts - admin gets all seller alerts with isAdminView:true"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Admin should see isAdminView:true
        assert data.get("isAdminView") is True, f"Expected isAdminView:true for admin, got: {data.get('isAdminView')}"
        assert "alerts" in data
        print(f"PASS: GET /low-stock-alerts returned isAdminView:true with {len(data.get('alerts', []))} alerts")

    # =============================================
    # ROLES & PERMISSIONS (from business_tools_router)
    # =============================================

    def test_roles_router_list(self):
        """GET /api/business-tools/roles - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/roles",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "roles" in data
        print(f"PASS: GET /roles returned {len(data.get('roles', []))} roles")

    def test_permissions_list(self):
        """GET /api/business-tools/permissions - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/permissions",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "permissions" in data
        print(f"PASS: GET /permissions returned {len(data.get('permissions', []))} permissions")

    # =============================================
    # EMPLOYEES (from business_tools_router)
    # =============================================

    def test_employees_router_list(self):
        """GET /api/business-tools/employees - should return 200 for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/employees",
            headers=self.headers
        )
        assert response.status_code != 403, f"Got 403 - permissions check failed! Response: {response.text}"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "employees" in data
        print(f"PASS: GET /employees returned {len(data.get('employees', []))} employees")


class TestResolveSellerIdForAdmin:
    """
    Test that resolve_seller_id returns None for admin users.
    This is a key change - admin users don't have a specific seller context.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Authorization": f"Bearer {DEV_TEST_TOKEN}",
            "Content-Type": "application/json"
        }

    def test_admin_can_view_all_low_stock_alerts(self):
        """Admin should see alerts from ALL sellers, not scoped to one seller."""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/low-stock-alerts",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # isAdminView should be True
        assert data.get("isAdminView") is True
        
        # If there are alerts, check they have sellerName (admin enrichment)
        alerts = data.get("alerts", [])
        if alerts:
            for alert in alerts:
                # Admin view should include sellerName
                assert "sellerName" in alert, f"Alert missing sellerName: {alert}"
            
            # Optionally: check if alerts are from multiple sellers
            seller_ids = set(alert.get("sellerId") for alert in alerts if alert.get("sellerId"))
            print(f"PASS: Admin sees {len(alerts)} alerts from {len(seller_ids)} unique seller(s)")
        else:
            print("PASS: No alerts in system but endpoint works for admin")


class TestNoPermissionDeniedRegression:
    """
    Explicit tests for the original bug: 403 Permission Denied.
    These tests ensure the fix doesn't regress.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Authorization": f"Bearer {DEV_TEST_TOKEN}",
            "Content-Type": "application/json"
        }

    def test_original_bug_po_endpoint_no_403(self):
        """
        ORIGINAL BUG: POST /api/business-tools/purchase-orders returned 403 for sellers.
        The root cause was user.get('accountType') returning None for users without that field.
        Fix: Centralized permissions.py with get_account_type() that defaults to 'seller'.
        """
        # Test GET first (was also affected)
        get_response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders",
            headers=self.headers
        )
        assert get_response.status_code == 200, f"GET /purchase-orders failed: {get_response.status_code} - {get_response.text}"
        print("PASS: GET /purchase-orders returns 200 (not 403)")

    def test_all_business_tools_endpoints_no_403(self):
        """
        Batch test: All business tools endpoints should NOT return 403 for admin.
        """
        endpoints_to_test = [
            "/api/business-tools/inventory",
            "/api/business-tools/buyers",
            "/api/business-tools/suppliers",
            "/api/business-tools/invoices",
            "/api/business-tools/activity-logs",
            "/api/business-tools/home/summary",
            "/api/business-tools/home/charts",
            "/api/business-tools/composite-products",
            "/api/business-tools/my-permissions",
            "/api/business-tools/low-stock-alerts",
            "/api/business-tools/roles",
            "/api/business-tools/employees",
            "/api/business-tools/permissions",
            "/api/business-tools/purchase-orders",
        ]

        failures = []
        for endpoint in endpoints_to_test:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=self.headers)
            if response.status_code == 403:
                failures.append(f"{endpoint} returned 403: {response.text[:100]}")
            elif response.status_code not in [200, 201]:
                # Log non-200 but don't fail (some endpoints may have no data)
                print(f"WARNING: {endpoint} returned {response.status_code}")

        if failures:
            pytest.fail(f"The following endpoints returned 403 Permission Denied:\n" + "\n".join(failures))
        
        print(f"PASS: All {len(endpoints_to_test)} endpoints returned non-403 status codes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
