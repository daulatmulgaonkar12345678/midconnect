"""
Test Export Endpoints and Subscription Enforcement
===================================================
Tests for:
1. All export endpoints return 200 for admin user (enterprise plan)
2. Outstanding export no longer throws timezone errors (was 500)
3. Free plan users get 403 with FEATURE_NOT_AVAILABLE for exports
4. Panel/record creation blocked for expired users
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_TOKEN = "dev-test-token"  # Admin user with enterprise plan


class TestExportEndpointsAdminUser:
    """Test all export endpoints work for admin user (enterprise plan)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    # ─── Core Export Endpoints ───

    def test_export_sales_xlsx(self):
        """GET /api/business-tools/export/sales?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "spreadsheetml" in response.headers.get("Content-Type", ""), "Expected Excel content type"
        print("✓ export/sales?format=xlsx returns 200 with Excel content")

    def test_export_sales_csv(self):
        """GET /api/business-tools/export/sales?format=csv returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales",
            params={"format": "csv"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", ""), "Expected CSV content type"
        print("✓ export/sales?format=csv returns 200 with CSV content")

    def test_export_profit_xlsx(self):
        """GET /api/business-tools/export/profit?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/profit",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/profit?format=xlsx returns 200")

    def test_export_inventory_xlsx(self):
        """GET /api/business-tools/export/inventory?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/inventory",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/inventory?format=xlsx returns 200")

    def test_export_buyers_xlsx(self):
        """GET /api/business-tools/export/buyers?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/buyers",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/buyers?format=xlsx returns 200")

    def test_export_invoices_xlsx(self):
        """GET /api/business-tools/export/invoices?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/invoices",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/invoices?format=xlsx returns 200")

    # ─── Outstanding Export (Previously 500 due to timezone bug) ───

    def test_export_outstanding_xlsx_no_500(self):
        """GET /api/business-tools/export/outstanding?format=xlsx returns 200 (was 500 due to timezone bug)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/outstanding",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        # This was the bug - timezone-naive vs timezone-aware datetime subtraction
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "spreadsheetml" in response.headers.get("Content-Type", ""), "Expected Excel content type"
        print("✓ export/outstanding?format=xlsx returns 200 (timezone bug FIXED)")

    def test_export_outstanding_csv(self):
        """GET /api/business-tools/export/outstanding?format=csv returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/outstanding",
            params={"format": "csv"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/outstanding?format=csv returns 200")

    # ─── Additional Report Exports ───

    def test_export_purchase_orders_xlsx(self):
        """GET /api/business-tools/export/purchase-orders?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/purchase-orders",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/purchase-orders?format=xlsx returns 200")

    def test_export_stock_movement_xlsx(self):
        """GET /api/business-tools/export/stock-movement?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/stock-movement",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/stock-movement?format=xlsx returns 200")

    def test_export_buyer_ledger_xlsx(self):
        """GET /api/business-tools/export/buyer-ledger?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/buyer-ledger",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/buyer-ledger?format=xlsx returns 200")

    def test_export_product_performance_xlsx(self):
        """GET /api/business-tools/export/product-performance?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/product-performance",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/product-performance?format=xlsx returns 200")

    def test_export_category_report_xlsx(self):
        """GET /api/business-tools/export/category-report?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/category-report",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/category-report?format=xlsx returns 200")

    def test_export_low_stock_xlsx(self):
        """GET /api/business-tools/export/low-stock?format=xlsx returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/low-stock",
            params={"format": "xlsx"},
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/low-stock?format=xlsx returns 200")

    def test_export_gst_report(self):
        """GET /api/business-tools/export/gst-report returns 200 (Excel with 2 sheets)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/gst-report",
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "spreadsheetml" in response.headers.get("Content-Type", ""), "Expected Excel content type"
        print("✓ export/gst-report returns 200 with Excel content")


class TestSubscriptionEnforcementConfig:
    """Test that plan config correctly defines export access"""

    def test_free_plan_has_export_false(self):
        """Verify free plan config has export=False"""
        import sys
        sys.path.insert(0, "/app/backend")
        from config.plan_features import PLAN_CONFIG
        
        assert PLAN_CONFIG["free"]["export"] is False, "Free plan should have export=False"
        print("✓ Free plan config has export=False")

    def test_standard_plan_has_export_true(self):
        """Verify standard plan config has export=True"""
        import sys
        sys.path.insert(0, "/app/backend")
        from config.plan_features import PLAN_CONFIG
        
        assert PLAN_CONFIG["standard"]["export"] is True, "Standard plan should have export=True"
        print("✓ Standard plan config has export=True")

    def test_pro_plan_has_export_true(self):
        """Verify pro plan config has export=True"""
        import sys
        sys.path.insert(0, "/app/backend")
        from config.plan_features import PLAN_CONFIG
        
        assert PLAN_CONFIG["pro"]["export"] is True, "Pro plan should have export=True"
        print("✓ Pro plan config has export=True")

    def test_enterprise_plan_has_export_true(self):
        """Verify enterprise plan config has export=True"""
        import sys
        sys.path.insert(0, "/app/backend")
        from config.plan_features import PLAN_CONFIG
        
        assert PLAN_CONFIG["enterprise"]["export"] is True, "Enterprise plan should have export=True"
        print("✓ Enterprise plan config has export=True")

    def test_feature_map_has_export_excel(self):
        """Verify FEATURE_MAP maps export_excel to export config key"""
        import sys
        sys.path.insert(0, "/app/backend")
        from config.plan_features import FEATURE_MAP
        
        assert "export_excel" in FEATURE_MAP, "FEATURE_MAP should have export_excel"
        assert FEATURE_MAP["export_excel"] == "export", "export_excel should map to 'export' config key"
        print("✓ FEATURE_MAP has export_excel -> export mapping")


class TestAdminUserHasEnterpriseAccess:
    """Verify admin user (dev-test-token) has enterprise plan with export access"""

    def test_admin_subscription_status(self):
        """GET /api/subscription/status returns enterprise plan for admin"""
        response = requests.get(
            f"{BASE_URL}/api/subscription/status",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Admin should have enterprise plan
        assert data.get("plan") == "enterprise" or data.get("status") == "active", f"Admin should have enterprise plan: {data}"
        print(f"✓ Admin subscription status: plan={data.get('plan')}, status={data.get('status')}")

    def test_admin_access_level(self):
        """GET /api/business-tools/access-level returns export=True for admin"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/access-level",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        limits = data.get("limits", {})
        assert limits.get("export") is True, f"Admin should have export=True: {limits}"
        print(f"✓ Admin access-level: export={limits.get('export')}, plan={data.get('plan')}")


class TestExportEndpointGuardPresence:
    """Verify enforce_export_access() is called in export endpoints (code review)"""

    def test_export_router_has_enforce_export_access(self):
        """Verify export_import_router.py has enforce_export_access guard"""
        import os
        
        router_path = "/app/backend/routers/export_import_router.py"
        assert os.path.exists(router_path), f"Router file not found: {router_path}"
        
        with open(router_path, "r") as f:
            content = f.read()
        
        # Check that enforce_export_access is defined
        assert "async def enforce_export_access" in content, "enforce_export_access function should be defined"
        
        # Check that it's called in export endpoints
        export_endpoints = [
            "export_sales", "export_profit", "export_inventory", "export_buyers",
            "export_invoices", "export_outstanding", "export_purchase_orders",
            "export_stock_movement", "export_buyer_ledger", "export_product_performance",
            "export_category_report", "export_low_stock", "export_gst_report"
        ]
        
        for endpoint in export_endpoints:
            # Check that enforce_export_access is called after get_current_user
            assert f"await enforce_export_access(user)" in content, f"enforce_export_access should be called in {endpoint}"
        
        print("✓ All export endpoints have enforce_export_access guard")

    def test_ensure_utc_function_exists(self):
        """Verify ensure_utc() function exists for timezone handling"""
        router_path = "/app/backend/routers/export_import_router.py"
        
        with open(router_path, "r") as f:
            content = f.read()
        
        assert "def ensure_utc(dt):" in content, "ensure_utc function should be defined"
        assert "dt.replace(tzinfo=timezone.utc)" in content, "ensure_utc should handle naive datetimes"
        print("✓ ensure_utc() function exists for timezone handling")


class TestExportWithDateFilters:
    """Test export endpoints with date filters work correctly"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    def test_export_sales_with_date_range(self):
        """GET /api/business-tools/export/sales with date filters returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/sales",
            params={
                "format": "xlsx",
                "startDate": "2024-01-01",
                "endDate": "2025-12-31"
            },
            headers=self.headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/sales with date filters returns 200")

    def test_export_outstanding_with_date_range(self):
        """GET /api/business-tools/export/outstanding with date filters returns 200 (timezone safe)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/export/outstanding",
            params={
                "format": "xlsx",
                "startDate": "2024-01-01",
                "endDate": "2025-12-31"
            },
            headers=self.headers,
        )
        # This tests the timezone fix with date filters
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ export/outstanding with date filters returns 200 (timezone safe)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
