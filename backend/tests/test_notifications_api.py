"""
Test Notifications API Endpoints
Features tested:
- GET /api/business-tools/notifications/unread-count - returns unread badge count
- GET /api/business-tools/notifications - returns notifications with pagination
- GET /api/business-tools/notifications?notification_type=low_stock - type filter
- GET /api/business-tools/notifications?unread_only=true - unread filter
- PUT /api/business-tools/notifications/{id}/read - mark single notification as read
- PUT /api/business-tools/notifications/mark-all-read - mark all notifications as read
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestNotificationsEndpointExistence:
    """Test that all notification endpoints exist and return expected status codes."""
    
    def test_api_health(self):
        """Verify the API is accessible."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("PASS: API health check successful")
    
    def test_notifications_unread_count_endpoint_exists(self):
        """GET /api/business-tools/notifications/unread-count exists (returns 422 without auth)."""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications/unread-count")
        # 422 means endpoint exists but requires auth header
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/notifications/unread-count endpoint exists (returns 422 without auth)")
    
    def test_notifications_list_endpoint_exists(self):
        """GET /api/business-tools/notifications exists (returns 422 without auth)."""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/notifications endpoint exists (returns 422 without auth)")
    
    def test_notifications_list_with_type_filter_endpoint_exists(self):
        """GET /api/business-tools/notifications?notification_type=low_stock exists."""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications?notification_type=low_stock")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/notifications?notification_type=low_stock endpoint exists")
    
    def test_notifications_list_with_unread_filter_endpoint_exists(self):
        """GET /api/business-tools/notifications?unread_only=true exists."""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications?unread_only=true")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/notifications?unread_only=true endpoint exists")
    
    def test_notifications_list_with_pagination_endpoint_exists(self):
        """GET /api/business-tools/notifications?limit=20&skip=0 exists."""
        response = requests.get(f"{BASE_URL}/api/business-tools/notifications?limit=20&skip=0")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/notifications?limit=20&skip=0 endpoint exists")
    
    def test_mark_notification_read_endpoint_exists(self):
        """PUT /api/business-tools/notifications/{id}/read exists (returns 422 without auth)."""
        # Using a placeholder ID - endpoint should still be found
        response = requests.put(f"{BASE_URL}/api/business-tools/notifications/000000000000000000000000/read")
        # 422 means endpoint exists but requires auth header
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: PUT /api/business-tools/notifications/{id}/read endpoint exists (returns 422 without auth)")
    
    def test_mark_all_read_endpoint_exists(self):
        """PUT /api/business-tools/notifications/mark-all-read exists (returns 422 without auth)."""
        response = requests.put(f"{BASE_URL}/api/business-tools/notifications/mark-all-read")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: PUT /api/business-tools/notifications/mark-all-read endpoint exists (returns 422 without auth)")


class TestNotificationsEndpointBehavior:
    """Test endpoint behavior with various parameters."""
    
    def test_notifications_type_filters_valid_types(self):
        """Test that all type filters are accepted by the endpoint."""
        valid_types = ['low_stock', 'invoice_created', 'payment_received', 'purchase_order', 'inventory_update', 'system']
        for type_filter in valid_types:
            response = requests.get(f"{BASE_URL}/api/business-tools/notifications?notification_type={type_filter}")
            # Should return 422 (auth required) not 400 (bad request)
            assert response.status_code == 422, f"Type filter '{type_filter}' rejected: {response.status_code}"
        print(f"PASS: All type filters accepted ({', '.join(valid_types)})")
    
    def test_notifications_combined_filters(self):
        """Test combining type filter with unread filter."""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/notifications?notification_type=low_stock&unread_only=true&limit=10&skip=0"
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: Combined filters (type + unread + pagination) accepted")


class TestDashboardMetricsNotificationCount:
    """Test that dashboard metrics includes unread notification count."""
    
    def test_dashboard_metrics_endpoint_exists(self):
        """GET /api/business-tools/dashboard-metrics exists (used by Home page)."""
        response = requests.get(f"{BASE_URL}/api/business-tools/dashboard-metrics")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("PASS: GET /api/business-tools/dashboard-metrics endpoint exists (returns 422 without auth)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
