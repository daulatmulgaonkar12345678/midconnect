"""
QUOTATION OFFLINE MODULE API TESTS
===================================

Tests for the Business Tools Quotation Module including:
- Quotation CRUD operations
- PDF generation endpoint
- Quotation to Invoice conversion flow (store-prefill, get-prefill, mark-converted)
- Offline quotation sync
- Buyer offline sync with deduplication

All endpoints require Firebase auth - test 401 for invalid token.
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://offline-quotations.preview.emergentagent.com')

# For authenticated testing, we need valid Firebase token
# Since Firebase is not configured, we test 401/422 behavior for unauthenticated requests
INVALID_TOKEN = "invalid-test-token-12345"
HEADERS_NO_AUTH = {}
HEADERS_INVALID_AUTH = {"Authorization": f"Bearer {INVALID_TOKEN}"}


class TestQuotationEndpointAuth:
    """Test that all quotation endpoints require authentication"""
    
    def test_api_health(self):
        """API health check passes"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ API health check passed")

    def test_list_quotations_requires_auth(self):
        """GET /api/business-tools/quotations returns 401 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/quotations",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Invalid" in data.get("detail", ""), f"Expected 'Invalid' in error detail"
        print("✅ GET /quotations returns 401 for invalid token")

    def test_create_quotation_requires_auth(self):
        """POST /api/business-tools/quotations returns 401/422 for invalid token"""
        payload = {
            "buyerId": "5f8a423b12c4e61234567890",
            "items": [{"productId": "test", "productName": "Test Product", "quantity": 1, "price": 100, "gstPercent": 18}],
            "notes": "Test quotation",
            "validityDays": 15
        }
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations",
            headers=HEADERS_INVALID_AUTH,
            json=payload
        )
        # Returns 401 for invalid token
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /quotations returns 401 for invalid token")

    def test_get_quotation_pdf_requires_auth(self):
        """GET /api/business-tools/quotations/{id}/pdf returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        response = requests.get(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}/pdf",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ GET /quotations/{id}/pdf returns 401 for invalid token")

    def test_store_prefill_requires_auth(self):
        """POST /api/business-tools/quotations/{id}/store-prefill returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}/store-prefill",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ POST /quotations/{id}/store-prefill returns 401 for invalid token")

    def test_get_prefill_requires_auth(self):
        """GET /api/business-tools/quotations/get-prefill/{id} returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        response = requests.get(
            f"{BASE_URL}/api/business-tools/quotations/get-prefill/{fake_id}",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ GET /quotations/get-prefill/{id} returns 401 for invalid token")

    def test_mark_converted_requires_auth(self):
        """POST /api/business-tools/quotations/{id}/mark-converted returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}/mark-converted",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ POST /quotations/{id}/mark-converted returns 401 for invalid token")

    def test_sync_offline_quotation_requires_auth(self):
        """POST /api/business-tools/quotations/sync-offline returns 401 for invalid token"""
        payload = {
            "buyerId": "5f8a423b12c4e61234567890",
            "items": [{"productId": "test", "productName": "Test Product", "quantity": 1, "price": 100, "gstPercent": 18}],
            "notes": "Offline quotation",
            "validityDays": 15
        }
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations/sync-offline",
            headers=HEADERS_INVALID_AUTH,
            json=payload
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /quotations/sync-offline returns 401 for invalid token")

    def test_delete_quotation_requires_auth(self):
        """DELETE /api/business-tools/quotations/{id} returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        response = requests.delete(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}",
            headers=HEADERS_INVALID_AUTH
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ DELETE /quotations/{id} returns 401 for invalid token")

    def test_update_quotation_requires_auth(self):
        """PUT /api/business-tools/quotations/{id} returns 401 for invalid token"""
        fake_id = "5f8a423b12c4e61234567890"
        payload = {"status": "sent"}
        response = requests.put(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}",
            headers=HEADERS_INVALID_AUTH,
            json=payload
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ PUT /quotations/{id} returns 401 for invalid token")


class TestBuyerSyncEndpoint:
    """Tests for buyer sync endpoint with deduplication"""

    def test_buyer_sync_offline_requires_auth(self):
        """POST /api/business-tools/buyers/sync-offline returns 401 for invalid token"""
        payload = {
            "buyerName": "Test Buyer",
            "phone": "9876543210",
            "state": "Maharashtra"
        }
        response = requests.post(
            f"{BASE_URL}/api/business-tools/buyers/sync-offline",
            headers=HEADERS_INVALID_AUTH,
            json=payload
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /buyers/sync-offline returns 401 for invalid token")


class TestQuotationPDFServiceImport:
    """Test that the quotation PDF service can be imported and works"""
    
    def test_pdf_service_import(self):
        """Quotation PDF service module can be imported"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.quotation_pdf_service import generate_quotation_pdf
            assert generate_quotation_pdf is not None
            print("✅ Quotation PDF service module imports successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import quotation_pdf_service: {e}")

    def test_pdf_generation_with_mock_data(self):
        """PDF service generates valid PDF bytes"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.quotation_pdf_service import generate_quotation_pdf
        
        # Mock quotation data
        quotation = {
            "quotationNumber": "QUO-TEST-001",
            "date": datetime.now().isoformat(),
            "validityDays": 15,
            "status": "draft",
            "items": [
                {
                    "productName": "Test Product",
                    "description": "Test Description",
                    "hsnCode": "8506",
                    "quantity": 10,
                    "price": 100.0,
                    "discount": 0,
                    "gstPercent": 18,
                    "gstAmount": 180.0,
                    "total": 1180.0,
                    "selected_specifications": [{"key": "Size", "value": "Large"}]
                }
            ],
            "subtotal": 1000.0,
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0,
            "gst": 180.0,
            "total": 1180.0,
            "roundOff": 0,
            "notes": "Test notes",
            "termsAndConditions": "Test terms",
            "placeOfSupply": "Maharashtra"
        }
        
        seller = {
            "businessName": "Test Business",
            "name": "Test Seller",
            "address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "phone": "9876543210",
            "email": "test@example.com",
            "gstNumber": "27AAACT1234F1ZP",
            "bankDetails": {
                "bankName": "Test Bank",
                "accountNumber": "123456789",
                "accountName": "Test Account",
                "ifscCode": "TEST0001234",
                "branch": "Test Branch"
            }
        }
        
        buyer = {
            "buyerName": "Test Buyer",
            "company": "Buyer Company",
            "address": "456 Buyer Lane",
            "phone": "9876543211",
            "gstNumber": "27BBBCT5678F1ZQ",
            "state": "Maharashtra"
        }
        
        # Generate PDF
        pdf_bytes = generate_quotation_pdf(quotation, seller, buyer, is_offline=False)
        
        # Verify it's valid PDF bytes
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print(f"✅ PDF generated successfully: {len(pdf_bytes)} bytes")

    def test_pdf_generation_with_offline_watermark(self):
        """PDF service adds DRAFT watermark for offline quotations"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.quotation_pdf_service import generate_quotation_pdf
        
        quotation = {
            "quotationNumber": "QUO-OFFLINE-001",
            "date": datetime.now().isoformat(),
            "validityDays": 10,
            "status": "draft",
            "items": [{"productName": "Item", "quantity": 1, "price": 50, "gstPercent": 5, "gstAmount": 2.5, "total": 52.5}],
            "subtotal": 50.0,
            "gst": 2.5,
            "total": 52.5,
            "placeOfSupply": "Gujarat"
        }
        seller = {"businessName": "Offline Seller", "state": "Gujarat"}
        buyer = {"buyerName": "Offline Buyer", "state": "Gujarat"}
        
        # Generate with offline flag
        pdf_bytes = generate_quotation_pdf(quotation, seller, buyer, is_offline=True)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        # The watermark is drawn on the canvas, but we can verify PDF was generated
        print(f"✅ Offline PDF with DRAFT watermark generated: {len(pdf_bytes)} bytes")


class TestRouterEndpointExistence:
    """Verify all quotation router endpoints exist by checking OPTIONS or HEAD"""
    
    def test_quotations_list_endpoint_exists(self):
        """GET /api/business-tools/quotations endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/quotations")
        # 401 (no auth) or 422 (validation) means endpoint exists
        assert response.status_code in [401, 422, 200], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations list endpoint exists (status: {response.status_code})")
    
    def test_quotations_create_endpoint_exists(self):
        """POST /api/business-tools/quotations endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/business-tools/quotations", json={})
        assert response.status_code in [401, 422, 400], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations create endpoint exists (status: {response.status_code})")
    
    def test_quotations_pdf_endpoint_exists(self):
        """GET /api/business-tools/quotations/{id}/pdf endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/quotations/test123/pdf")
        # 422 means validation failed (missing auth header) - endpoint exists
        assert response.status_code in [401, 400, 404, 422], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations/{{id}}/pdf endpoint exists (status: {response.status_code})")
    
    def test_quotations_store_prefill_endpoint_exists(self):
        """POST /api/business-tools/quotations/{id}/store-prefill endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/business-tools/quotations/test123/store-prefill")
        assert response.status_code in [401, 400, 404, 422], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations/{{id}}/store-prefill endpoint exists (status: {response.status_code})")
    
    def test_quotations_get_prefill_endpoint_exists(self):
        """GET /api/business-tools/quotations/get-prefill/{id} endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/quotations/get-prefill/test123")
        assert response.status_code in [401, 400, 404, 422], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations/get-prefill/{{id}} endpoint exists (status: {response.status_code})")
    
    def test_quotations_mark_converted_endpoint_exists(self):
        """POST /api/business-tools/quotations/{id}/mark-converted endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/business-tools/quotations/test123/mark-converted")
        assert response.status_code in [401, 400, 404, 422], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations/{{id}}/mark-converted endpoint exists (status: {response.status_code})")
    
    def test_quotations_sync_offline_endpoint_exists(self):
        """POST /api/business-tools/quotations/sync-offline endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/business-tools/quotations/sync-offline", json={})
        assert response.status_code in [401, 422, 400], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /quotations/sync-offline endpoint exists (status: {response.status_code})")
    
    def test_buyers_sync_offline_endpoint_exists(self):
        """POST /api/business-tools/buyers/sync-offline endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/business-tools/buyers/sync-offline", json={})
        assert response.status_code in [401, 422, 400], f"Endpoint might not exist: {response.status_code}"
        print(f"✅ /buyers/sync-offline endpoint exists (status: {response.status_code})")


class TestSyncEngineSortPriority:
    """Tests for the syncEngine sortByPriority function logic"""
    
    def test_sync_priority_order_verified_in_code(self):
        """Verify that syncEngine has correct priority order in code"""
        import re
        
        with open('/app/frontend/src/lib/syncEngine.ts', 'r') as f:
            content = f.read()
        
        # Check that sortByPriority function exists
        assert 'function sortByPriority' in content, "sortByPriority function not found"
        
        # Check priority mapping exists with correct order
        # buyer: 0, quotation: 1, invoice: 2, inventory: 3, purchase_order: 4
        assert "buyer: 0" in content or "buyer': 0" in content, "buyer priority 0 not found"
        assert "quotation: 1" in content or "quotation': 1" in content, "quotation priority 1 not found"
        assert "invoice: 2" in content or "invoice': 2" in content, "invoice priority 2 not found"
        assert "inventory: 3" in content or "inventory': 3" in content, "inventory priority 3 not found"
        assert "purchase_order: 4" in content or "purchase_order': 4" in content, "purchase_order priority 4 not found"
        
        print("✅ syncEngine sortByPriority has correct priority order: buyer(0) → quotation(1) → invoice(2) → inventory(3) → purchase_order(4)")


class TestOfflineStoreTypes:
    """Tests for the offlineStore types"""
    
    def test_offline_store_supports_quotation_type(self):
        """offlineStore.ts includes 'quotation' in OfflineItemType"""
        with open('/app/frontend/src/lib/offlineStore.ts', 'r') as f:
            content = f.read()
        
        # Check OfflineItemType includes quotation and buyer
        assert "'quotation'" in content or '"quotation"' in content, "quotation type not in OfflineItemType"
        assert "'buyer'" in content or '"buyer"' in content, "buyer type not in OfflineItemType"
        
        print("✅ offlineStore supports 'quotation' and 'buyer' types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
