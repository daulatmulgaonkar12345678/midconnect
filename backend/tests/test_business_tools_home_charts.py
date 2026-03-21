"""
Business Tools Home Dashboard & Charts API Tests
Tests the new endpoints - simple endpoint existence verification
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-perms-modal.preview.emergentagent.com').rstrip('/')


# =============================================================================
# NEW HOME ENDPOINTS TESTS
# =============================================================================

class TestHomeEndpoints:
    """Tests for GET /api/business-tools/home/* endpoints"""
    
    def test_home_summary_endpoint_exists(self):
        """Verify home/summary endpoint exists (returns 422 without auth header)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/home/summary")
        # 422 = endpoint exists but requires Authorization header
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/home/summary endpoint exists (requires auth)")
    
    def test_home_charts_endpoint_exists(self):
        """Verify home/charts endpoint exists (returns 422 without auth header)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/home/charts")
        # 422 = endpoint exists but requires Authorization header
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/home/charts endpoint exists (requires auth)")


# =============================================================================
# NEW ANALYTICS ENDPOINTS TESTS
# =============================================================================

class TestNewAnalyticsEndpoints:
    """Tests for new analytics endpoints"""
    
    def test_analytics_categories_endpoint_exists(self):
        """Verify analytics/categories endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/categories")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/categories endpoint exists (requires auth)")
    
    def test_analytics_category_sales_endpoint_exists(self):
        """Verify analytics/category-sales endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/category-sales")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/category-sales endpoint exists (requires auth)")
    
    def test_analytics_top_products_endpoint_exists(self):
        """Verify analytics/top-products endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/top-products")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/top-products endpoint exists (requires auth)")


# =============================================================================
# EXISTING ANALYTICS ENDPOINTS REGRESSION TESTS
# =============================================================================

class TestExistingAnalyticsEndpoints:
    """Regression tests for existing analytics endpoints"""
    
    def test_analytics_products_endpoint(self):
        """Verify analytics/products endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/products")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/products endpoint exists")
    
    def test_analytics_suppliers_endpoint(self):
        """Verify analytics/suppliers endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/suppliers")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/suppliers endpoint exists")
    
    def test_analytics_price_trend_endpoint(self):
        """Verify analytics/price-trend endpoint still works (requires listing_id param)"""
        # Without listing_id, should return 422 (validation error)
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/price-trend")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/price-trend endpoint exists")
    
    def test_analytics_purchase_trend_endpoint(self):
        """Verify analytics/purchase-trend endpoint still works (requires listing_id param)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/purchase-trend")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/purchase-trend endpoint exists")
    
    def test_analytics_stock_trend_endpoint(self):
        """Verify analytics/stock-trend endpoint still works (requires listing_id param)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/stock-trend")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/stock-trend endpoint exists")
    
    def test_analytics_supplier_comparison_endpoint(self):
        """Verify analytics/supplier-comparison endpoint still works (requires listing_id param)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/supplier-comparison")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/supplier-comparison endpoint exists")
    
    def test_analytics_summary_endpoint(self):
        """Verify analytics/summary endpoint still works (requires listing_id param)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/summary")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: /api/business-tools/analytics/summary endpoint exists")


# =============================================================================
# API HEALTH CHECK
# =============================================================================

class TestAPIHealth:
    """Basic API health verification"""
    
    def test_api_is_responsive(self):
        """Verify API is responsive"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: API health check successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
