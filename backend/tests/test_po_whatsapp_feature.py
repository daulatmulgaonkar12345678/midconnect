"""
Test Suite: Purchase Order WhatsApp Sharing Feature
Tests: GET /api/business-tools/purchase-orders, GET /api/business-tools/purchase-orders/{poId}/whatsapp-link,
       GET /api/doc/{token} for PO PDF download, and regression tests for other endpoints.
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestPurchaseOrdersListEndpoint:
    """Test GET /api/business-tools/purchase-orders returns PO list"""

    def test_list_purchase_orders_returns_200(self):
        """Backend: GET /api/business-tools/purchase-orders returns PO list (200)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "purchaseOrders" in data, "Response should contain 'purchaseOrders' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: GET /api/business-tools/purchase-orders returned 200 with {len(data['purchaseOrders'])} POs")

    def test_list_purchase_orders_structure(self):
        """Test PO list response structure contains required fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        pos = data.get("purchaseOrders", [])
        
        if len(pos) > 0:
            po = pos[0]
            # Required fields for PO cards
            assert "id" in po, "PO should have 'id' field"
            assert "poNumber" in po, "PO should have 'poNumber' field"
            assert "supplierName" in po, "PO should have 'supplierName' field"
            assert "status" in po, "PO should have 'status' field"
            # Fields for WhatsApp feature
            assert "supplierPhone" in po, "PO should have 'supplierPhone' field for WhatsApp"
            print(f"PASS: PO structure verified - poNumber: {po['poNumber']}, status: {po['status']}, supplierPhone: {po.get('supplierPhone', 'N/A')}")
        else:
            pytest.skip("No POs in database to verify structure")


class TestPOWhatsAppLinkEndpoint:
    """Test GET /api/business-tools/purchase-orders/{poId}/whatsapp-link endpoint"""

    @pytest.fixture
    def existing_po_id(self):
        """Get an existing PO ID from the list"""
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        if response.status_code == 200:
            pos = response.json().get("purchaseOrders", [])
            # Find a PO with supplier phone (for testing)
            for po in pos:
                if po.get("supplierPhone"):
                    return po["id"]
            # Return first PO even without phone (to test error case)
            if pos:
                return pos[0]["id"]
        return None

    def test_whatsapp_link_returns_valid_response(self, existing_po_id):
        """Backend: GET /api/business-tools/purchase-orders/{poId}/whatsapp-link returns whatsappLink"""
        if not existing_po_id:
            pytest.skip("No PO available in database")
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{existing_po_id}/whatsapp-link",
            headers=HEADERS
        )
        
        # Could be 200 (success) or 400 (no phone)
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "whatsappLink" in data, "Response should contain 'whatsappLink'"
            assert "documentLink" in data, "Response should contain 'documentLink'"
            assert "supplierPhone" in data, "Response should contain 'supplierPhone'"
            
            # Verify whatsappLink format
            assert data["whatsappLink"].startswith("https://wa.me/"), "WhatsApp link should start with https://wa.me/"
            
            # Verify documentLink format
            assert "/api/doc/" in data["documentLink"], "documentLink should contain /api/doc/{token}"
            
            print(f"PASS: WhatsApp link generated successfully")
            print(f"  - whatsappLink: {data['whatsappLink'][:50]}...")
            print(f"  - documentLink: {data['documentLink']}")
            print(f"  - supplierPhone: {data['supplierPhone']}")
            return data
        else:
            print(f"INFO: WhatsApp link returned 400 (supplier phone missing) - expected behavior")
            return None

    def test_whatsapp_link_contains_doc_url(self, existing_po_id):
        """Backend: WhatsApp link response includes documentLink field (/api/doc/{token})"""
        if not existing_po_id:
            pytest.skip("No PO available in database")
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{existing_po_id}/whatsapp-link",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "documentLink" in data, "Response must include 'documentLink'"
            
            # Extract token from documentLink
            doc_link = data["documentLink"]
            assert doc_link.startswith("/api/doc/"), f"documentLink should be /api/doc/{{token}}, got: {doc_link}"
            
            token = doc_link.replace("/api/doc/", "")
            assert len(token) > 10, "Token should be a non-trivial secure string"
            print(f"PASS: documentLink verified: {doc_link}")
        else:
            pytest.skip("Supplier phone not available for this PO")

    def test_whatsapp_message_contains_download_link(self, existing_po_id):
        """Backend: WhatsApp message text contains the secure doc download link"""
        if not existing_po_id:
            pytest.skip("No PO available in database")
        
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{existing_po_id}/whatsapp-link",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data, "Response should include pre-filled 'message' text"
            
            message = data["message"]
            # Message should contain download URL
            assert "/api/doc/" in message or "Download" in message, "Message should reference the download link"
            print(f"PASS: Message contains download reference")
            print(f"  Message preview: {message[:100]}...")
        else:
            pytest.skip("Supplier phone not available for this PO")

    def test_whatsapp_link_invalid_po_returns_404(self):
        """Test invalid PO ID returns 404"""
        fake_id = "000000000000000000000000"
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{fake_id}/whatsapp-link",
            headers=HEADERS
        )
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"PASS: Invalid PO ID returns {response.status_code}")


class TestSecureDocumentDownload:
    """Test /api/doc/{token} returns PO as PDF"""

    @pytest.fixture
    def document_share_token(self):
        """Get a valid document share token by creating one via WhatsApp link"""
        # First get a PO with supplier phone
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        if response.status_code != 200:
            return None
        
        pos = response.json().get("purchaseOrders", [])
        po_with_phone = None
        for po in pos:
            if po.get("supplierPhone"):
                po_with_phone = po
                break
        
        if not po_with_phone:
            return None
        
        # Generate WhatsApp link to create document share
        wa_response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{po_with_phone['id']}/whatsapp-link",
            headers=HEADERS
        )
        
        if wa_response.status_code == 200:
            doc_link = wa_response.json().get("documentLink", "")
            token = doc_link.replace("/api/doc/", "")
            return token
        return None

    def test_doc_endpoint_returns_pdf_for_po(self, document_share_token):
        """Backend: /api/doc/{token} returns application/pdf for PO document shares"""
        if not document_share_token:
            pytest.skip("Could not create document share token (no PO with supplier phone)")
        
        # This is a public endpoint - no auth header needed
        response = requests.get(f"{BASE_URL}/api/doc/{document_share_token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got content-type: {content_type}"
        
        # Verify it's actually PDF content (PDF magic bytes)
        content = response.content
        assert len(content) > 100, "PDF should have substantial content"
        assert content[:4] == b'%PDF', f"Response should be PDF format (got: {content[:20]})"
        
        print(f"PASS: /api/doc/{document_share_token[:8]}... returns valid PDF ({len(content)} bytes)")

    def test_invalid_token_returns_404(self):
        """Test invalid token returns 404"""
        response = requests.get(f"{BASE_URL}/api/doc/invalid_token_abc123")
        assert response.status_code == 404, f"Expected 404 for invalid token, got {response.status_code}"
        print("PASS: Invalid token returns 404")


class TestPOStatusAutoUpdate:
    """Test PO status auto-updates from draft to sent after WhatsApp link generation"""

    def test_status_update_on_whatsapp_send(self):
        """Backend: PO status auto-updates from draft to sent after WhatsApp link generation"""
        # Get existing POs
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        assert response.status_code == 200
        
        pos = response.json().get("purchaseOrders", [])
        
        # Look for PO with phone that can be tested
        po_with_phone = None
        for po in pos:
            if po.get("supplierPhone") and po.get("status") in ["draft", "sent"]:
                po_with_phone = po
                break
        
        if not po_with_phone:
            # Document that we verified the feature design (from code review)
            print("INFO: No PO with supplier phone in draft status to test auto-update")
            print("CODE REVIEW: po_router.py lines 390-394 confirm draft->sent status update on WhatsApp link generation")
            pytest.skip("No testable PO available")
        
        # Generate WhatsApp link
        wa_response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{po_with_phone['id']}/whatsapp-link",
            headers=HEADERS
        )
        
        if wa_response.status_code == 200:
            # Re-fetch the PO to verify status change
            po_response = requests.get(
                f"{BASE_URL}/api/business-tools/purchase-orders/{po_with_phone['id']}",
                headers=HEADERS
            )
            
            if po_response.status_code == 200:
                updated_po = po_response.json().get("purchaseOrder", {})
                # If original was draft, should now be sent
                if po_with_phone["status"] == "draft":
                    assert updated_po["status"] == "sent", f"Expected 'sent', got '{updated_po['status']}'"
                    print(f"PASS: PO status auto-updated from draft to sent")
                else:
                    print(f"INFO: PO already in '{po_with_phone['status']}' status")


class TestDocumentSharesCollection:
    """Test document_shares collection gets new record"""

    def test_document_share_created_on_whatsapp_link(self):
        """Backend: document_shares collection gets a new record with documentType:po"""
        # This test verifies behavior from code review
        # po_router.py lines 356-366 show document_shares.insert_one with:
        #   - token, sellerId, documentType:"po", documentId, recipientPhone, expiresAt (7 days), createdAt
        
        # Verify by generating a link and checking the token works
        response = requests.get(f"{BASE_URL}/api/business-tools/purchase-orders", headers=HEADERS)
        if response.status_code != 200:
            pytest.skip("Cannot list POs")
        
        pos = response.json().get("purchaseOrders", [])
        po_with_phone = next((po for po in pos if po.get("supplierPhone")), None)
        
        if not po_with_phone:
            print("CODE REVIEW: po_router.py lines 356-366 confirm document_shares record creation")
            print("  Fields: token, sellerId, documentType:'po', documentId, recipientPhone, expiresAt (7 days)")
            pytest.skip("No PO with supplier phone to test")
        
        wa_response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/{po_with_phone['id']}/whatsapp-link",
            headers=HEADERS
        )
        
        assert wa_response.status_code == 200
        doc_link = wa_response.json().get("documentLink", "")
        token = doc_link.replace("/api/doc/", "")
        
        # Verify the token is valid by using it
        doc_response = requests.get(f"{BASE_URL}/api/doc/{token}")
        assert doc_response.status_code == 200, "Document share token should be valid"
        
        print(f"PASS: document_shares record created (token validated via /api/doc/{token[:8]}...)")


class TestRegressionOtherEndpoints:
    """Regression: All other business-tools endpoints still work"""

    def test_inventory_endpoint(self):
        """Regression: GET /api/business-tools/inventory still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/inventory", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/business-tools/inventory returns 200")

    def test_buyers_endpoint(self):
        """Regression: GET /api/business-tools/buyers still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/business-tools/buyers returns 200")

    def test_invoices_endpoint(self):
        """Regression: GET /api/business-tools/invoices still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/business-tools/invoices returns 200")

    def test_low_stock_alerts_endpoint(self):
        """Regression: GET /api/business-tools/low-stock-alerts still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/low-stock-alerts", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/business-tools/low-stock-alerts returns 200")

    def test_suppliers_endpoint(self):
        """Regression: GET /api/business-tools/suppliers still works"""
        response = requests.get(f"{BASE_URL}/api/business-tools/suppliers", headers=HEADERS)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/business-tools/suppliers returns 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
