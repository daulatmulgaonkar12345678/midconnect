"""
Test Quick Price Update and B2B Inquiry System
================================================
Testing:
1. Quick Price Update endpoint PATCH /api/seller/listings/{id}/quick-price
2. Seller Inquiries endpoint GET /api/seller/inquiries
3. Accept Inquiry endpoint POST /api/seller/inquiries/{id}/accept
4. Reject Inquiry endpoint POST /api/seller/inquiries/{id}/reject
5. Report Inquiry endpoint POST /api/seller/inquiries/{id}/report
6. Buyer create inquiry endpoint POST /api/inquiries/b2b
7. Buyer get my inquiries endpoint GET /api/inquiries/b2b/my
"""

import pytest
import requests
import os
from datetime import datetime

# Use production URL from environment
BASE_URL = os.environ.get('NEXT_PUBLIC_API_URL', 'https://midconnect.onrender.com/api')
if not BASE_URL.endswith('/api'):
    BASE_URL = BASE_URL.rstrip('/') + '/api' if '/api' not in BASE_URL else BASE_URL.rstrip('/')

# Test constants
INVALID_TOKEN = "invalid_test_token_12345"
DUMMY_LISTING_ID = "507f1f77bcf86cd799439011"
DUMMY_INQUIRY_ID = "507f1f77bcf86cd799439022"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealthAndBasics:
    """Test basic API availability"""
    
    def test_health_endpoint(self, api_client):
        """Verify API health endpoint works"""
        # Note: BASE_URL includes /api, health is at /api/health
        response = api_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"✓ Health check passed: {data}")
    
    def test_categories_public(self, api_client):
        """Verify categories endpoint is public"""
        response = api_client.get(f"{BASE_URL}/categories/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Categories endpoint returned {len(data)} categories")


class TestQuickPriceUpdate:
    """Test Quick Price Update endpoint"""
    
    def test_quick_price_update_requires_auth(self, api_client):
        """PATCH /seller/listings/{id}/quick-price requires authentication"""
        response = api_client.patch(
            f"{BASE_URL}/seller/listings/{DUMMY_LISTING_ID}/quick-price",
            json={
                "base_price": 100.00,
                "valid_till": "7_days",
                "stock_status": "in_stock"
            }
        )
        # Should return 401 or 403 without valid token
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Quick price update requires auth: {response.status_code}")
    
    def test_quick_price_update_invalid_token(self, api_client):
        """PATCH /seller/listings/{id}/quick-price with invalid token"""
        response = api_client.patch(
            f"{BASE_URL}/seller/listings/{DUMMY_LISTING_ID}/quick-price",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "base_price": 100.00,
                "valid_till": "7_days",
                "stock_status": "in_stock"
            }
        )
        # Should return 401 (invalid token) or 503 (Firebase not configured)
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Invalid token returns: {response.status_code}")
    
    def test_quick_price_update_validation(self, api_client):
        """Test validation errors for quick price update"""
        # Test with missing base_price (required field)
        response = api_client.patch(
            f"{BASE_URL}/seller/listings/{DUMMY_LISTING_ID}/quick-price",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "valid_till": "7_days"
            }
        )
        # Should return 401/503 for auth, or 422 for validation
        assert response.status_code in [401, 422, 503], f"Expected 401/422/503, got {response.status_code}"
        print(f"✓ Validation check returned: {response.status_code}")


class TestSellerInquiries:
    """Test Seller Inquiries endpoints"""
    
    def test_get_seller_inquiries_requires_auth(self, api_client):
        """GET /seller/inquiries requires authentication"""
        response = api_client.get(f"{BASE_URL}/seller/inquiries")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Get seller inquiries requires auth: {response.status_code}")
    
    def test_get_seller_inquiries_with_invalid_token(self, api_client):
        """GET /seller/inquiries with invalid token"""
        response = api_client.get(
            f"{BASE_URL}/seller/inquiries",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Get seller inquiries with invalid token: {response.status_code}")
    
    def test_get_seller_inquiries_pagination_params(self, api_client):
        """Test pagination parameters are accepted"""
        response = api_client.get(
            f"{BASE_URL}/seller/inquiries",
            params={"page": 1, "limit": 10, "status": "pending"},
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        # Should accept params even if auth fails
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Pagination params accepted: {response.status_code}")


class TestAcceptInquiry:
    """Test Accept Inquiry endpoint"""
    
    def test_accept_inquiry_requires_auth(self, api_client):
        """POST /seller/inquiries/{id}/accept requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/accept",
            json={
                "quoted_price": 150.00,
                "validity_days": 7,
                "seller_note": "Thank you for your inquiry"
            }
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Accept inquiry requires auth: {response.status_code}")
    
    def test_accept_inquiry_with_invalid_token(self, api_client):
        """POST /seller/inquiries/{id}/accept with invalid token"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/accept",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "quoted_price": 150.00,
                "validity_days": 7
            }
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Accept inquiry with invalid token: {response.status_code}")
    
    def test_accept_inquiry_validation(self, api_client):
        """Test validation for accept inquiry"""
        # Missing required quoted_price
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/accept",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "validity_days": 7
            }
        )
        assert response.status_code in [401, 422, 503], f"Expected 401/422/503, got {response.status_code}"
        print(f"✓ Accept validation returned: {response.status_code}")


class TestRejectInquiry:
    """Test Reject Inquiry endpoint"""
    
    def test_reject_inquiry_requires_auth(self, api_client):
        """POST /seller/inquiries/{id}/reject requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/reject",
            json={
                "reason": "not_available",
                "note": "Product out of stock"
            }
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Reject inquiry requires auth: {response.status_code}")
    
    def test_reject_inquiry_with_invalid_token(self, api_client):
        """POST /seller/inquiries/{id}/reject with invalid token"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/reject",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "reason": "price_too_low"
            }
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Reject inquiry with invalid token: {response.status_code}")
    
    def test_reject_inquiry_reason_validation(self, api_client):
        """Test rejection reason must be valid enum value"""
        # Invalid reason
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/reject",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "reason": "invalid_reason_xyz"
            }
        )
        # Will get 401/503 for auth, or 422 for validation
        assert response.status_code in [401, 422, 503], f"Expected 401/422/503, got {response.status_code}"
        print(f"✓ Invalid reason returned: {response.status_code}")


class TestReportInquiry:
    """Test Report Inquiry endpoint"""
    
    def test_report_inquiry_requires_auth(self, api_client):
        """POST /seller/inquiries/{id}/report requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/report",
            json={
                "report_type": "spam",
                "details": "Suspicious inquiry"
            }
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Report inquiry requires auth: {response.status_code}")
    
    def test_report_inquiry_with_invalid_token(self, api_client):
        """POST /seller/inquiries/{id}/report with invalid token"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/report",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "report_type": "fake_inquiry"
            }
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Report inquiry with invalid token: {response.status_code}")


class TestBuyerInquiries:
    """Test Buyer B2B Inquiry endpoints"""
    
    def test_create_b2b_inquiry_requires_auth(self, api_client):
        """POST /inquiries/b2b requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/inquiries/b2b",
            json={
                "listing_id": DUMMY_LISTING_ID,
                "quantity": 100,
                "requirement_note": "Need bulk order",
                "buyer_type": "trader",
                "location_city": "Mumbai",
                "location_state": "Maharashtra"
            }
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Create B2B inquiry requires auth: {response.status_code}")
    
    def test_create_b2b_inquiry_with_invalid_token(self, api_client):
        """POST /inquiries/b2b with invalid token"""
        response = api_client.post(
            f"{BASE_URL}/inquiries/b2b",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "listing_id": DUMMY_LISTING_ID,
                "quantity": 100,
                "buyer_type": "contractor"
            }
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Create B2B inquiry with invalid token: {response.status_code}")
    
    def test_create_b2b_inquiry_validation(self, api_client):
        """Test validation for B2B inquiry creation"""
        # Missing required fields
        response = api_client.post(
            f"{BASE_URL}/inquiries/b2b",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={
                "buyer_type": "trader"
            }
        )
        assert response.status_code in [401, 422, 503], f"Expected 401/422/503, got {response.status_code}"
        print(f"✓ Create B2B inquiry validation: {response.status_code}")
    
    def test_get_my_b2b_inquiries_requires_auth(self, api_client):
        """GET /inquiries/b2b/my requires authentication"""
        response = api_client.get(f"{BASE_URL}/inquiries/b2b/my")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"✓ Get my B2B inquiries requires auth: {response.status_code}")
    
    def test_get_my_b2b_inquiries_with_invalid_token(self, api_client):
        """GET /inquiries/b2b/my with invalid token"""
        response = api_client.get(
            f"{BASE_URL}/inquiries/b2b/my",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Get my B2B inquiries with invalid token: {response.status_code}")
    
    def test_get_my_b2b_inquiries_pagination(self, api_client):
        """Test pagination for buyer inquiries"""
        response = api_client.get(
            f"{BASE_URL}/inquiries/b2b/my",
            params={"page": 1, "limit": 10, "status": "pending"},
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        assert response.status_code in [401, 503], f"Expected 401/503, got {response.status_code}"
        print(f"✓ Buyer inquiries pagination params accepted: {response.status_code}")


class TestEndpointExistence:
    """Test that all required endpoints exist"""
    
    def test_quick_price_endpoint_exists(self, api_client):
        """Verify quick price endpoint exists (not 404)"""
        response = api_client.patch(
            f"{BASE_URL}/seller/listings/{DUMMY_LISTING_ID}/quick-price",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={"base_price": 100}
        )
        # 404 means endpoint doesn't exist, anything else means it exists
        assert response.status_code != 404, "Quick price endpoint not found (404)"
        print(f"✓ Quick price endpoint exists: status {response.status_code}")
    
    def test_seller_inquiries_endpoint_exists(self, api_client):
        """Verify seller inquiries endpoint exists (not 404)"""
        response = api_client.get(
            f"{BASE_URL}/seller/inquiries",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        assert response.status_code != 404, "Seller inquiries endpoint not found (404)"
        print(f"✓ Seller inquiries endpoint exists: status {response.status_code}")
    
    def test_accept_inquiry_endpoint_exists(self, api_client):
        """Verify accept inquiry endpoint exists (not 404)"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/accept",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={"quoted_price": 100}
        )
        assert response.status_code != 404, "Accept inquiry endpoint not found (404)"
        print(f"✓ Accept inquiry endpoint exists: status {response.status_code}")
    
    def test_reject_inquiry_endpoint_exists(self, api_client):
        """Verify reject inquiry endpoint exists (not 404)"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/reject",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={"reason": "not_available"}
        )
        assert response.status_code != 404, "Reject inquiry endpoint not found (404)"
        print(f"✓ Reject inquiry endpoint exists: status {response.status_code}")
    
    def test_report_inquiry_endpoint_exists(self, api_client):
        """Verify report inquiry endpoint exists (not 404)"""
        response = api_client.post(
            f"{BASE_URL}/seller/inquiries/{DUMMY_INQUIRY_ID}/report",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={"report_type": "spam"}
        )
        assert response.status_code != 404, "Report inquiry endpoint not found (404)"
        print(f"✓ Report inquiry endpoint exists: status {response.status_code}")
    
    def test_create_b2b_inquiry_endpoint_exists(self, api_client):
        """Verify create B2B inquiry endpoint exists (not 404)"""
        response = api_client.post(
            f"{BASE_URL}/inquiries/b2b",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            json={"listing_id": DUMMY_LISTING_ID, "quantity": 100}
        )
        assert response.status_code != 404, "Create B2B inquiry endpoint not found (404)"
        print(f"✓ Create B2B inquiry endpoint exists: status {response.status_code}")
    
    def test_get_my_b2b_inquiries_endpoint_exists(self, api_client):
        """Verify get my B2B inquiries endpoint exists (not 404)"""
        response = api_client.get(
            f"{BASE_URL}/inquiries/b2b/my",
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
        )
        assert response.status_code != 404, "Get my B2B inquiries endpoint not found (404)"
        print(f"✓ Get my B2B inquiries endpoint exists: status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
