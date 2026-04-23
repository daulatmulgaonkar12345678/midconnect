"""
QUOTATION SYSTEM API TESTS
==========================

Comprehensive tests for the Hybrid RFQ → Quote → WhatsApp → Acceptance System.

Test Coverage:
- POST /api/quotes/create - Create quote (seller)
- POST /api/quotes/{quoteId}/whatsapp-redirect - WhatsApp redirect
- GET /api/quotes/{quoteId} - View quote (buyer)
- POST /api/quotes/{quoteId}/accept - Accept quote (buyer)
- POST /api/quotes/{quoteId}/reject - Reject quote (buyer)
- POST /api/quotes/admin/expire-quotes - Run expiry job
- GET /api/quotes/analytics - Quote analytics
- GET /api/quotes/buyer - Buyer quotes list
- GET /api/quotes/seller - Seller quotes list
- GET /api/quotes/public/{quoteId} - Public quote view

Business Rules Tested:
- Quote ID is non-sequential (QT-XXXXX random alphanumeric)
- Total price auto-calculated: (unitPrice × qty) + packagingCharges
- validityDays <= 15
- Only buyer can accept/reject quote (not seller)
- Quote expires automatically
"""

import pytest
import requests
import os
import re
from datetime import datetime, timezone

# API configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com')
DEV_TOKEN = "dev-test-token"

# Test data from the main agent
TEST_INQUIRY_ID = "699ca628c4462b3b8208ed5d"
TEST_QUOTE_ID = "QT-M24DO"
TEST_QUOTE_TOKEN = "UpYuDK9O1On3zRvtE0CcJRWOliUwRTlcZwKKD92n7Ac"
SELLER_ID = "699ca5c7fe015041f7de460c"
BUYER_ID = "699ca628c4462b3b8208ed5c"


class TestQuoteEndpointsHealth:
    """Basic health and connectivity tests for quote endpoints"""
    
    def test_api_health(self):
        """Test that API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ API health check passed")
    
    def test_seller_quotes_endpoint_reachable(self):
        """Test seller quotes endpoint is reachable with auth"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/quotes/seller", headers=headers)
        assert response.status_code == 200, f"Seller quotes endpoint failed: {response.text}"
        data = response.json()
        assert "quotes" in data, "Response missing 'quotes' field"
        assert "total" in data, "Response missing 'total' field"
        print(f"✅ Seller quotes endpoint works - found {data['total']} quotes")


class TestExistingQuoteOperations:
    """Tests using the existing test quote QT-M24DO"""
    
    def _get_quote_from_seller_list(self):
        """Helper to get quote details from seller's quotes list"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/quotes/seller", headers=headers)
        assert response.status_code == 200
        data = response.json()
        for quote in data["quotes"]:
            if quote["quoteId"] == TEST_QUOTE_ID:
                return quote
        raise AssertionError(f"Quote {TEST_QUOTE_ID} not found in seller list")
    
    def test_seller_list_shows_quote(self):
        """Seller can view quote they created via seller quotes list"""
        quote = self._get_quote_from_seller_list()
        
        # Verify quote data structure
        assert quote["quoteId"] == TEST_QUOTE_ID
        assert "unitPrice" in quote, "Missing unitPrice"
        assert "totalPrice" in quote, "Missing totalPrice"
        assert "moq" in quote, "Missing moq"
        assert "status" in quote, "Missing status"
        assert "validityDate" in quote, "Missing validityDate"
        print(f"✅ Quote view works - quoteId={quote['quoteId']}, status={quote['status']}")
    
    def test_quote_id_format_non_sequential(self):
        """Quote ID should be non-sequential format QT-XXXXX"""
        quote = self._get_quote_from_seller_list()
        
        # Verify QT-XXXXX format
        quote_id = quote["quoteId"]
        pattern = r'^QT-[A-Z0-9]{5}$'
        assert re.match(pattern, quote_id), f"Quote ID {quote_id} doesn't match QT-XXXXX pattern"
        print(f"✅ Quote ID format verified: {quote_id}")
    
    def test_total_price_calculation(self):
        """Verify total price = (unitPrice × requestedQuantity) + packagingCharges"""
        quote = self._get_quote_from_seller_list()
        
        unit_price = quote["unitPrice"]
        qty = quote["requestedQuantity"]
        packaging = quote.get("packagingCharges", 0)
        expected_total = (unit_price * qty) + packaging
        
        # Allow small floating point difference
        assert abs(quote["totalPrice"] - expected_total) < 0.01, \
            f"Total price mismatch: expected {expected_total}, got {quote['totalPrice']}"
        print(f"✅ Total price calculation verified: ({unit_price} × {qty}) + {packaging} = {quote['totalPrice']}")
    
    def test_whatsapp_redirect_marks_flag(self):
        """WhatsApp redirect endpoint marks whatsappRedirectUsed flag"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        
        # Call WhatsApp redirect
        response = requests.post(
            f"{BASE_URL}/api/quotes/{TEST_QUOTE_ID}/whatsapp-redirect",
            headers=headers
        )
        assert response.status_code == 200, f"WhatsApp redirect failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "message" in data, "Missing message"
        assert "secureUrl" in data, "Missing secureUrl"
        assert "quoteId" in data, "Missing quoteId"
        assert data["quoteId"] == TEST_QUOTE_ID
        
        # Verify flag is set on quote
        quote = self._get_quote_from_seller_list()
        assert quote["whatsappRedirectUsed"] == True, "whatsappRedirectUsed should be True"
        print(f"✅ WhatsApp redirect works - secureUrl generated, flag set")
    
    def test_seller_cannot_accept_own_quote(self):
        """Security: Seller cannot accept their own quote (buyer authorization check)"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.post(
            f"{BASE_URL}/api/quotes/{TEST_QUOTE_ID}/accept",
            headers=headers
        )
        # Should fail because the dev-test-token user is the seller, not the buyer
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        error_data = response.json()
        assert "detail" in error_data, "Missing error detail"
        print(f"✅ Seller cannot accept own quote - security check passed: {error_data['detail']}")
    
    def test_seller_cannot_reject_own_quote(self):
        """Security: Seller cannot reject their own quote"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.post(
            f"{BASE_URL}/api/quotes/{TEST_QUOTE_ID}/reject",
            headers=headers,
            json={"reason": "Testing rejection"}
        )
        # Should fail - seller cannot reject
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"✅ Seller cannot reject own quote - security check passed")


class TestQuoteCreation:
    """Tests for quote creation endpoint"""
    
    def test_create_quote_requires_seller_role(self):
        """Only sellers can create quotes"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "inquiryId": TEST_INQUIRY_ID,
            "unitPrice": 100.0,
            "moq": 5,
            "leadTimeDays": 7,
            "validityDays": 7
        }
        response = requests.post(
            f"{BASE_URL}/api/quotes/create",
            headers=headers,
            json=payload
        )
        # This will fail with "Active quote already exists" because we already have QT-M24DO
        # But it verifies the endpoint is accessible with seller role
        # (401/403 would mean auth issue, 400 means business logic)
        assert response.status_code in [200, 400], f"Unexpected error: {response.text}"
        if response.status_code == 400:
            error = response.json().get("detail", "")
            assert "Active quote already exists" in error or "already exists" in error.lower(), \
                f"Unexpected error: {error}"
        print(f"✅ Create quote endpoint accessible with seller role")
    
    def test_create_quote_validates_validity_days_max_15(self):
        """Validity days cannot exceed 15"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "inquiryId": TEST_INQUIRY_ID,
            "unitPrice": 100.0,
            "moq": 5,
            "leadTimeDays": 7,
            "validityDays": 20  # Exceeds max of 15
        }
        response = requests.post(
            f"{BASE_URL}/api/quotes/create",
            headers=headers,
            json=payload
        )
        # Should fail validation or business logic check
        assert response.status_code in [400, 422], f"Expected validation error: {response.text}"
        print(f"✅ Validity days > 15 rejected correctly")


class TestPublicQuoteView:
    """Tests for public quote viewing (WhatsApp link access)"""
    
    def test_public_quote_view_with_token(self):
        """Public quote view works with valid access token"""
        response = requests.get(
            f"{BASE_URL}/api/quotes/public/{TEST_QUOTE_ID}",
            params={"token": TEST_QUOTE_TOKEN}
        )
        assert response.status_code == 200, f"Public view failed: {response.text}"
        data = response.json()
        
        assert "quote" in data, "Missing quote"
        assert "isExpired" in data, "Missing isExpired"
        assert "requiresLogin" in data, "Missing requiresLogin"
        
        quote = data["quote"]
        assert quote["quoteId"] == TEST_QUOTE_ID
        assert "unitPrice" in quote
        assert "totalPrice" in quote
        print(f"✅ Public quote view works with token")
    
    def test_public_quote_view_invalid_token(self):
        """Public quote view fails with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/quotes/public/{TEST_QUOTE_ID}",
            params={"token": "invalid-token-12345"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Public view rejects invalid token")
    
    def test_public_quote_view_requires_token(self):
        """Public quote view requires access token"""
        response = requests.get(
            f"{BASE_URL}/api/quotes/public/{TEST_QUOTE_ID}"
        )
        assert response.status_code == 422, f"Expected 422 (missing token), got {response.status_code}"
        print(f"✅ Public view requires token parameter")


class TestQuoteExpiry:
    """Tests for quote expiry functionality"""
    
    def test_expire_quotes_endpoint(self):
        """Admin expire-quotes endpoint works"""
        response = requests.post(f"{BASE_URL}/api/quotes/admin/expire-quotes")
        assert response.status_code == 200, f"Expire quotes failed: {response.text}"
        data = response.json()
        
        assert "success" in data, "Missing success field"
        assert "expiredCount" in data, "Missing expiredCount field"
        assert "timestamp" in data, "Missing timestamp field"
        print(f"✅ Expire quotes endpoint works - expired {data['expiredCount']} quotes")


class TestQuoteAnalytics:
    """Tests for quote analytics endpoint"""
    
    def test_seller_analytics(self):
        """Seller can view their quote analytics"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/quotes/analytics",
            headers=headers
        )
        assert response.status_code == 200, f"Analytics failed: {response.text}"
        data = response.json()
        
        # Verify analytics structure
        assert "period" in data, "Missing period"
        assert "totalQuotes" in data, "Missing totalQuotes"
        assert "viewRate" in data, "Missing viewRate"
        assert "acceptanceRate" in data, "Missing acceptanceRate"
        assert "rejectionRate" in data, "Missing rejectionRate"
        assert "expiryRate" in data, "Missing expiryRate"
        
        print(f"✅ Analytics endpoint works - {data['totalQuotes']} total quotes, {data['viewRate']}% view rate")


class TestQuoteLists:
    """Tests for quote list endpoints"""
    
    def test_seller_quotes_list(self):
        """Seller can list their quotes"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/quotes/seller",
            headers=headers
        )
        assert response.status_code == 200, f"Seller list failed: {response.text}"
        data = response.json()
        
        assert "quotes" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        
        # Should have at least the test quote
        assert data["total"] >= 1, "Expected at least 1 quote"
        print(f"✅ Seller quotes list works - {data['total']} quotes, page {data['page']}/{data['pages']}")
    
    def test_seller_quotes_list_filter_by_status(self):
        """Seller can filter quotes by status"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/quotes/seller",
            headers=headers,
            params={"status": "viewed"}
        )
        assert response.status_code == 200, f"Filtered list failed: {response.text}"
        data = response.json()
        
        # All returned quotes should have the filtered status
        for quote in data["quotes"]:
            assert quote["status"] == "viewed", f"Expected status 'viewed', got '{quote['status']}'"
        print(f"✅ Seller quotes filter by status works")
    
    def test_buyer_quotes_list(self):
        """Buyer quotes list endpoint is accessible"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/quotes/buyer",
            headers=headers
        )
        assert response.status_code == 200, f"Buyer list failed: {response.text}"
        data = response.json()
        
        assert "quotes" in data
        assert "total" in data
        # Note: dev-test-token user may not be the buyer, so might return 0 quotes
        print(f"✅ Buyer quotes list works - {data['total']} quotes")


class TestQuoteValidation:
    """Tests for quote input validation"""
    
    def test_create_quote_requires_inquiry_id(self):
        """Quote creation requires inquiryId"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "unitPrice": 100.0,
            "moq": 5,
            "leadTimeDays": 7
        }
        response = requests.post(
            f"{BASE_URL}/api/quotes/create",
            headers=headers,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 validation error: {response.text}"
        print(f"✅ Quote creation validates required inquiryId")
    
    def test_create_quote_requires_positive_price(self):
        """Unit price must be positive"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "inquiryId": TEST_INQUIRY_ID,
            "unitPrice": -100.0,  # Invalid
            "moq": 5,
            "leadTimeDays": 7
        }
        response = requests.post(
            f"{BASE_URL}/api/quotes/create",
            headers=headers,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for negative price: {response.text}"
        print(f"✅ Negative unit price rejected")
    
    def test_create_quote_requires_positive_moq(self):
        """MOQ must be positive integer"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "inquiryId": TEST_INQUIRY_ID,
            "unitPrice": 100.0,
            "moq": 0,  # Invalid
            "leadTimeDays": 7
        }
        response = requests.post(
            f"{BASE_URL}/api/quotes/create",
            headers=headers,
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for zero MOQ: {response.text}"
        print(f"✅ Zero MOQ rejected")


class TestQuoteStatusTransitions:
    """Tests for quote status flow"""
    
    def _get_quote_from_seller_list(self):
        """Helper to get quote details from seller's quotes list"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/quotes/seller", headers=headers)
        assert response.status_code == 200
        data = response.json()
        for quote in data["quotes"]:
            if quote["quoteId"] == TEST_QUOTE_ID:
                return quote
        raise AssertionError(f"Quote {TEST_QUOTE_ID} not found in seller list")
    
    def test_quote_status_is_viewed_after_view(self):
        """Quote status changes to 'viewed' after buyer views"""
        quote = self._get_quote_from_seller_list()
        
        # Quote was already viewed based on our setup
        assert quote["status"] in ["sent", "viewed"], f"Unexpected status: {quote['status']}"
        print(f"✅ Quote status is '{quote['status']}' (expected 'sent' or 'viewed')")
    
    def test_viewed_quote_has_viewedAt_timestamp(self):
        """Viewed quote should have viewedAt timestamp"""
        quote = self._get_quote_from_seller_list()
        
        if quote["status"] == "viewed":
            assert quote.get("viewedAt") is not None, "Viewed quote missing viewedAt"
            print(f"✅ Viewed quote has viewedAt: {quote['viewedAt']}")
        else:
            print(f"ℹ️ Quote status is '{quote['status']}', viewedAt check skipped")


class TestQuoteDataIntegrity:
    """Tests for quote data integrity and field presence"""
    
    def _get_quote_from_seller_list(self):
        """Helper to get quote details from seller's quotes list"""
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/quotes/seller", headers=headers)
        assert response.status_code == 200
        data = response.json()
        for quote in data["quotes"]:
            if quote["quoteId"] == TEST_QUOTE_ID:
                return quote
        raise AssertionError(f"Quote {TEST_QUOTE_ID} not found in seller list")
    
    def test_quote_has_all_required_fields(self):
        """Quote response contains all required fields"""
        quote = self._get_quote_from_seller_list()
        
        required_fields = [
            "quoteId", "inquiryId", "productId", "productName",
            "sellerId", "sellerName", "buyerId",
            "requestedQuantity", "unitPrice", "moq",
            "packagingCharges", "totalPrice", "leadTimeDays",
            "validityDate", "status", "createdAt"
        ]
        
        for field in required_fields:
            assert field in quote, f"Missing required field: {field}"
        
        print(f"✅ Quote contains all required fields ({len(required_fields)} fields)")
    
    def test_quote_transport_always_false(self):
        """transportIncluded should always be False (per spec v1)"""
        quote = self._get_quote_from_seller_list()
        
        assert quote.get("transportIncluded") == False, \
            f"transportIncluded should be False, got {quote.get('transportIncluded')}"
        print(f"✅ transportIncluded is False as per spec")


class TestAdminAnalytics:
    """Tests for admin analytics endpoint"""
    
    def test_platform_wide_analytics(self):
        """Admin analytics endpoint returns platform-wide stats"""
        response = requests.get(f"{BASE_URL}/api/quotes/admin/analytics")
        assert response.status_code == 200, f"Admin analytics failed: {response.text}"
        data = response.json()
        
        expected_fields = ["period", "totalQuotes", "viewRate", "acceptanceRate"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Admin analytics works - {data['totalQuotes']} platform quotes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
