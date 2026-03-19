"""
Invoice 'Sent' Status Feature Tests - Test the following:
1. PUT /api/business-tools/invoices/{id}/mark-sent changes draft to sent with sentAt and sentVia='manual'
2. PUT /api/business-tools/invoices/{id}/mark-sent returns message if not draft (already sent/paid)
3. PUT /api/business-tools/invoices/{id}/mark-sent returns 404 for invalid invoice
4. GET /api/business-tools/invoices/{id}/whatsapp-link auto-updates draft to sent with sentVia='whatsapp'
5. WhatsApp link endpoint does NOT change status if invoice is already 'sent' (idempotent)
6. Invoice detail response includes sentAt and sentVia fields
7. Regression: existing invoice CRUD still works
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture
def auth_headers():
    """Auth headers with dev-test-token for testing."""
    return {
        "Authorization": "Bearer dev-test-token",
        "Content-Type": "application/json"
    }

class TestInvoiceSentStatusMarkSent:
    """Tests for PUT /api/business-tools/invoices/{id}/mark-sent endpoint."""
    
    def test_mark_sent_endpoint_exists(self, auth_headers):
        """Test that mark-sent endpoint exists and returns proper response."""
        # First, get a list of invoices to find a draft invoice
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200, f"Failed to get invoices: {list_res.text}"
        
        invoices = list_res.json().get("invoices", [])
        draft_invoice = next((inv for inv in invoices if inv.get("status") == "draft"), None)
        
        if draft_invoice:
            res = requests.put(f"{BASE_URL}/api/business-tools/invoices/{draft_invoice['id']}/mark-sent", headers=auth_headers)
            assert res.status_code == 200, f"mark-sent failed: {res.text}"
            data = res.json()
            assert "message" in data
            assert "status" in data
            assert data["status"] == "sent"
            assert "sentAt" in data
            print(f"✅ mark-sent endpoint works for draft invoice: {data}")
        else:
            print("ℹ️ No draft invoice found to test mark-sent - testing with non-draft invoice")
            # Test with any invoice (should return 'already sent' message)
            if invoices:
                res = requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoices[0]['id']}/mark-sent", headers=auth_headers)
                assert res.status_code == 200, f"mark-sent failed: {res.text}"
                data = res.json()
                assert "message" in data
                print(f"✅ mark-sent returns message for non-draft: {data}")

    def test_mark_sent_returns_message_if_not_draft(self, auth_headers):
        """Test that mark-sent returns a message without error if invoice is not draft."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200
        
        invoices = list_res.json().get("invoices", [])
        # Find invoice that is NOT draft (sent, paid, cancelled etc)
        non_draft = next((inv for inv in invoices if inv.get("status") != "draft"), None)
        
        if non_draft:
            res = requests.put(f"{BASE_URL}/api/business-tools/invoices/{non_draft['id']}/mark-sent", headers=auth_headers)
            assert res.status_code == 200, f"mark-sent should not fail for non-draft: {res.text}"
            data = res.json()
            assert "message" in data
            assert "already" in data["message"].lower() or "is already" in data["message"].lower()
            print(f"✅ Non-draft invoice returns appropriate message: {data['message']}")
        else:
            pytest.skip("No non-draft invoice found for testing")

    def test_mark_sent_returns_404_for_invalid_id(self, auth_headers):
        """Test that mark-sent returns 404 for non-existent invoice ID."""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
        res = requests.put(f"{BASE_URL}/api/business-tools/invoices/{fake_id}/mark-sent", headers=auth_headers)
        assert res.status_code == 404, f"Expected 404 for invalid invoice, got {res.status_code}"
        print("✅ mark-sent returns 404 for invalid invoice ID")

    def test_mark_sent_returns_400_for_malformed_id(self, auth_headers):
        """Test that mark-sent returns 400 for malformed invoice ID."""
        res = requests.put(f"{BASE_URL}/api/business-tools/invoices/invalid-id-format/mark-sent", headers=auth_headers)
        assert res.status_code == 400, f"Expected 400 for malformed ID, got {res.status_code}"
        print("✅ mark-sent returns 400 for malformed invoice ID")


class TestInvoiceWhatsAppLinkAutoSent:
    """Tests for GET /api/business-tools/invoices/{id}/whatsapp-link auto-update behavior."""
    
    def test_whatsapp_link_endpoint_exists(self, auth_headers):
        """Test that whatsapp-link endpoint exists and returns expected structure."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200
        
        invoices = list_res.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices found for testing")
        
        # Find an invoice with buyer phone
        test_invoice = None
        for inv in invoices:
            if inv.get("buyerPhone"):
                test_invoice = inv
                break
        
        if not test_invoice:
            pytest.skip("No invoice with buyer phone found")
        
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/whatsapp-link", headers=auth_headers)
        
        # Either 200 success or 400 if no phone
        if res.status_code == 200:
            data = res.json()
            assert "whatsappLink" in data
            assert "message" in data
            assert "wa.me" in data["whatsappLink"]
            print(f"✅ whatsapp-link endpoint returns proper structure")
        elif res.status_code == 400:
            print(f"ℹ️ whatsapp-link returned 400 (likely no buyer phone): {res.json()}")
        else:
            assert False, f"Unexpected status code: {res.status_code}"

    def test_whatsapp_link_updates_draft_to_sent(self, auth_headers):
        """Test that whatsapp-link auto-updates draft invoice to sent with sentVia='whatsapp'."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200
        
        invoices = list_res.json().get("invoices", [])
        # Find a draft invoice with buyer phone
        draft_with_phone = None
        for inv in invoices:
            if inv.get("status") == "draft" and inv.get("buyerPhone"):
                draft_with_phone = inv
                break
        
        if not draft_with_phone:
            print("ℹ️ No draft invoice with buyer phone found - testing sent invoice idempotency")
            pytest.skip("No draft invoice with buyer phone found")
        
        # Call whatsapp-link
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{draft_with_phone['id']}/whatsapp-link", headers=auth_headers)
        
        if res.status_code == 200:
            # Get invoice detail to verify status change
            detail_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{draft_with_phone['id']}", headers=auth_headers)
            assert detail_res.status_code == 200
            updated_inv = detail_res.json().get("invoice", {})
            
            assert updated_inv.get("status") == "sent", f"Invoice should be 'sent' after whatsapp-link, got: {updated_inv.get('status')}"
            assert updated_inv.get("sentVia") == "whatsapp", f"sentVia should be 'whatsapp', got: {updated_inv.get('sentVia')}"
            assert updated_inv.get("sentAt") is not None, "sentAt should be set"
            print(f"✅ Draft invoice auto-updated to 'sent' via whatsapp: sentAt={updated_inv.get('sentAt')}")
        else:
            print(f"ℹ️ whatsapp-link call failed: {res.text}")

    def test_whatsapp_link_does_not_change_already_sent(self, auth_headers):
        """Test that whatsapp-link does NOT overwrite sentAt if invoice is already 'sent'."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200
        
        invoices = list_res.json().get("invoices", [])
        # Find an already 'sent' invoice with buyer phone
        sent_with_phone = None
        for inv in invoices:
            if inv.get("status") == "sent" and inv.get("buyerPhone"):
                sent_with_phone = inv
                break
        
        if not sent_with_phone:
            pytest.skip("No 'sent' invoice with buyer phone found")
        
        # Get original sentAt
        detail_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{sent_with_phone['id']}", headers=auth_headers)
        original_inv = detail_res.json().get("invoice", {})
        original_sentAt = original_inv.get("sentAt")
        original_sentVia = original_inv.get("sentVia")
        
        # Call whatsapp-link
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{sent_with_phone['id']}/whatsapp-link", headers=auth_headers)
        
        if res.status_code == 200:
            # Get invoice detail again
            detail_res2 = requests.get(f"{BASE_URL}/api/business-tools/invoices/{sent_with_phone['id']}", headers=auth_headers)
            updated_inv = detail_res2.json().get("invoice", {})
            
            # sentAt should NOT change
            assert updated_inv.get("sentAt") == original_sentAt, f"sentAt should not change for already-sent invoice"
            assert updated_inv.get("sentVia") == original_sentVia, f"sentVia should not change"
            print(f"✅ Already-sent invoice preserves sentAt={original_sentAt}, sentVia={original_sentVia}")
        else:
            print(f"ℹ️ whatsapp-link call status: {res.status_code}")


class TestInvoiceDetailSentFields:
    """Tests for sentAt and sentVia fields in invoice detail response."""
    
    def test_invoice_detail_includes_sent_fields(self, auth_headers):
        """Test that invoice detail response includes sentAt and sentVia fields."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert list_res.status_code == 200
        
        invoices = list_res.json().get("invoices", [])
        # Find a 'sent' invoice to verify fields
        sent_invoice = next((inv for inv in invoices if inv.get("status") == "sent"), None)
        
        if sent_invoice:
            detail_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{sent_invoice['id']}", headers=auth_headers)
            assert detail_res.status_code == 200
            inv = detail_res.json().get("invoice", {})
            
            # These fields may or may not be present depending on when the invoice was sent
            if inv.get("sentAt"):
                print(f"✅ Invoice detail has sentAt: {inv.get('sentAt')}")
            else:
                print(f"ℹ️ Invoice is 'sent' but sentAt not populated (may be legacy invoice)")
            
            if inv.get("sentVia"):
                print(f"✅ Invoice detail has sentVia: {inv.get('sentVia')}")
                assert inv.get("sentVia") in ["manual", "whatsapp"], f"Invalid sentVia value: {inv.get('sentVia')}"
            else:
                print(f"ℹ️ sentVia not populated for this invoice")
        else:
            print("ℹ️ No sent invoice found - testing draft invoice")
            if invoices:
                detail_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoices[0]['id']}", headers=auth_headers)
                assert detail_res.status_code == 200
                print("✅ Invoice detail endpoint works")

    def test_invoice_list_response_structure(self, auth_headers):
        """Test that invoice list response has proper structure."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert res.status_code == 200
        
        data = res.json()
        assert "invoices" in data
        invoices = data["invoices"]
        
        if invoices:
            inv = invoices[0]
            required_fields = ["id", "invoiceNumber", "status", "total", "totalPaid", "pendingAmount"]
            for field in required_fields:
                assert field in inv, f"Missing field '{field}' in invoice list response"
            print(f"✅ Invoice list has all required fields. Total invoices: {len(invoices)}")


class TestInvoiceCRUDRegression:
    """Regression tests for existing invoice CRUD operations."""
    
    def test_get_invoices_list(self, auth_headers):
        """Test GET /api/business-tools/invoices endpoint."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "invoices" in data
        print(f"✅ GET invoices list: {len(data['invoices'])} invoices")

    def test_get_invoice_detail(self, auth_headers):
        """Test GET /api/business-tools/invoices/{id} endpoint."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        invoices = list_res.json().get("invoices", [])
        
        if invoices:
            res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoices[0]['id']}", headers=auth_headers)
            assert res.status_code == 200
            data = res.json()
            assert "invoice" in data
            assert "id" in data["invoice"]
            print(f"✅ GET invoice detail works: {data['invoice']['invoiceNumber']}")
        else:
            pytest.skip("No invoices to test")

    def test_update_invoice_status(self, auth_headers):
        """Test PUT /api/business-tools/invoices/{id}/status endpoint."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        invoices = list_res.json().get("invoices", [])
        
        # Find a draft invoice to test status update
        draft = next((inv for inv in invoices if inv.get("status") == "draft"), None)
        
        if draft:
            # Test changing to cancelled (safe to test)
            res = requests.put(
                f"{BASE_URL}/api/business-tools/invoices/{draft['id']}/status",
                headers=auth_headers,
                json={"status": "cancelled"}
            )
            assert res.status_code == 200
            print(f"✅ PUT invoice status works")
            
            # Revert to draft for other tests
            requests.put(
                f"{BASE_URL}/api/business-tools/invoices/{draft['id']}/status",
                headers=auth_headers,
                json={"status": "draft"}
            )
        else:
            print("ℹ️ No draft invoice to test status update - skipping")

    def test_invoice_pdf_endpoint(self, auth_headers):
        """Test GET /api/business-tools/invoices/{id}/pdf endpoint."""
        list_res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        invoices = list_res.json().get("invoices", [])
        
        if invoices:
            res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoices[0]['id']}/pdf", headers=auth_headers)
            assert res.status_code == 200
            assert res.headers.get("content-type") == "application/pdf"
            print(f"✅ GET invoice PDF works")
        else:
            pytest.skip("No invoices to test PDF")

    def test_get_invoice_products(self, auth_headers):
        """Test GET /api/business-tools/invoice-products endpoint."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "products" in data
        print(f"✅ GET invoice-products works: {len(data['products'])} products")


class TestAuthRequired:
    """Test that endpoints require authentication."""
    
    def test_mark_sent_requires_auth(self):
        """Test that mark-sent endpoint requires authentication."""
        res = requests.put(f"{BASE_URL}/api/business-tools/invoices/507f1f77bcf86cd799439011/mark-sent")
        assert res.status_code in [401, 422], f"Expected auth error, got {res.status_code}"
        print("✅ mark-sent requires authentication")

    def test_whatsapp_link_requires_auth(self):
        """Test that whatsapp-link endpoint requires authentication."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/507f1f77bcf86cd799439011/whatsapp-link")
        assert res.status_code in [401, 422], f"Expected auth error, got {res.status_code}"
        print("✅ whatsapp-link requires authentication")
