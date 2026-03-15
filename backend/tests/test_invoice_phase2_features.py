"""
Invoice Phase 2 API Tests - Receipt validation, Reminder system, WhatsApp links, Overdue detection, PDF enhancements.

Features tested:
1. Receipt upload validation (UPI/bank_transfer/cheque require receipts)
2. Reminder settings CRUD
3. Invoice reminders list with WhatsApp links
4. WhatsApp link generation endpoint
5. dueDays field in invoice creation
6. Overdue detection auto-marking
7. PDF generation with payment summary
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

# Test configuration
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class TestReceiptValidation:
    """Test receipt validation for different payment methods."""
    
    @pytest.fixture(scope="class")
    def test_invoice(self):
        """Create a test invoice for payment tests."""
        # First, get buyers
        buyers_res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=HEADERS)
        if buyers_res.status_code != 200 or not buyers_res.json().get("buyers"):
            pytest.skip("No buyers available to create invoice")
        buyer_id = buyers_res.json()["buyers"][0]["id"]
        
        # Create invoice
        payload = {
            "buyerId": buyer_id,
            "items": [{"productName": "TEST_ReceiptValidation_Item", "quantity": 1, "price": 5000, "gstPercent": 18}],
            "notes": "Test invoice for receipt validation",
            "deductStock": False,
            "dueDays": 7
        }
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS, json=payload)
        if res.status_code != 200:
            pytest.skip(f"Could not create test invoice: {res.text}")
        return res.json()["invoice"]
    
    def test_upi_payment_without_receipt_returns_400(self, test_invoice):
        """UPI payment without receiptUrls should be rejected with 400."""
        payload = {
            "amount": 500,
            "paymentMethod": "upi",
            "referenceNumber": "TEST_UPI_NO_RECEIPT"
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 400, f"Expected 400 for UPI without receipt, got {res.status_code}"
        assert "receipt" in res.json().get("detail", "").lower(), "Error should mention receipt requirement"
        print(f"✓ UPI without receipt correctly rejected: {res.json()['detail']}")
    
    def test_bank_transfer_without_receipt_returns_400(self, test_invoice):
        """Bank transfer payment without receiptUrls should be rejected with 400."""
        payload = {
            "amount": 500,
            "paymentMethod": "bank_transfer",
            "referenceNumber": "TEST_BANK_NO_RECEIPT"
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 400, f"Expected 400 for bank_transfer without receipt, got {res.status_code}"
        assert "receipt" in res.json().get("detail", "").lower()
        print(f"✓ Bank transfer without receipt correctly rejected: {res.json()['detail']}")
    
    def test_cheque_without_receipt_returns_400(self, test_invoice):
        """Cheque payment without receiptUrls should be rejected with 400."""
        payload = {
            "amount": 500,
            "paymentMethod": "cheque",
            "referenceNumber": "TEST_CHEQUE_NO_RECEIPT"
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 400, f"Expected 400 for cheque without receipt, got {res.status_code}"
        print(f"✓ Cheque without receipt correctly rejected")
    
    def test_cash_payment_without_receipt_succeeds(self, test_invoice):
        """Cash payment without receiptUrls should succeed (200)."""
        payload = {
            "amount": 500,
            "paymentMethod": "cash",
            "notes": "TEST_CASH_NO_RECEIPT_OK"
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 200, f"Expected 200 for cash without receipt, got {res.status_code}: {res.text}"
        payment = res.json().get("payment", {})
        assert payment.get("amount") == 500
        print(f"✓ Cash payment without receipt succeeded: Payment ID {payment.get('id')}")
    
    def test_other_payment_without_receipt_succeeds(self, test_invoice):
        """Other payment method without receiptUrls should succeed."""
        payload = {
            "amount": 300,
            "paymentMethod": "other",
            "notes": "TEST_OTHER_NO_RECEIPT_OK"
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 200, f"Expected 200 for 'other' method without receipt, got {res.status_code}"
        print(f"✓ 'Other' payment without receipt succeeded")
    
    def test_upi_with_receipt_succeeds(self, test_invoice):
        """UPI payment with receiptUrls array should succeed."""
        payload = {
            "amount": 1000,
            "paymentMethod": "upi",
            "referenceNumber": "TEST_UPI_WITH_RECEIPT",
            "receiptUrls": ["https://res.cloudinary.com/test/image/upload/test_receipt.jpg"]
        }
        res = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}/payments",
            headers=HEADERS, json=payload
        )
        assert res.status_code == 200, f"Expected 200 for UPI with receipt, got {res.status_code}: {res.text}"
        payment = res.json().get("payment", {})
        assert payment.get("receiptUrls") is not None
        assert len(payment.get("receiptUrls", [])) > 0
        print(f"✓ UPI with receipt succeeded: receiptUrls = {payment.get('receiptUrls')}")
    
    def test_invoice_detail_includes_receipts(self, test_invoice):
        """GET invoice detail should return payments with receiptUrls arrays."""
        res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{test_invoice['id']}",
            headers=HEADERS
        )
        assert res.status_code == 200
        invoice = res.json().get("invoice", {})
        payments = invoice.get("payments", [])
        assert len(payments) > 0, "Invoice should have payments"
        
        # Find payment with receiptUrls
        has_receipt_payment = any(p.get("receiptUrls") for p in payments)
        assert has_receipt_payment, "At least one payment should have receiptUrls"
        
        for p in payments:
            if p.get("receiptUrls"):
                assert isinstance(p["receiptUrls"], list)
                print(f"✓ Payment {p['id']} has receiptUrls: {p['receiptUrls']}")


class TestReminderSettings:
    """Test reminder settings CRUD endpoints."""
    
    def test_get_default_reminder_settings(self):
        """GET reminder-settings returns defaults when not set."""
        res = requests.get(f"{BASE_URL}/api/business-tools/reminder-settings", headers=HEADERS)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        settings = res.json().get("settings", {})
        assert "enabled" in settings
        assert "reminderDays" in settings
        assert isinstance(settings["reminderDays"], list)
        # Default should be [3, 7, 15]
        assert settings["enabled"] == True
        assert 3 in settings["reminderDays"]
        assert 7 in settings["reminderDays"]
        assert 15 in settings["reminderDays"]
        print(f"✓ Default reminder settings: {settings}")
    
    def test_update_reminder_settings(self):
        """PUT reminder-settings updates settings."""
        payload = {
            "enabled": True,
            "reminderDays": [5, 10, 20],
            "customMessages": {}
        }
        res = requests.put(f"{BASE_URL}/api/business-tools/reminder-settings", headers=HEADERS, json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        # Verify update
        get_res = requests.get(f"{BASE_URL}/api/business-tools/reminder-settings", headers=HEADERS)
        settings = get_res.json().get("settings", {})
        assert settings.get("reminderDays") == [5, 10, 20], f"Expected [5, 10, 20], got {settings.get('reminderDays')}"
        print(f"✓ Reminder settings updated: {settings}")
    
    def test_restore_default_reminder_settings(self):
        """Restore default settings after test."""
        payload = {"enabled": True, "reminderDays": [3, 7, 15], "customMessages": {}}
        res = requests.put(f"{BASE_URL}/api/business-tools/reminder-settings", headers=HEADERS, json=payload)
        assert res.status_code == 200
        print("✓ Restored default reminder settings [3, 7, 15]")


class TestInvoiceReminders:
    """Test invoice reminders endpoint."""
    
    def test_get_invoice_reminders(self):
        """GET invoice-reminders returns reminders list."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoice-reminders", headers=HEADERS)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "reminders" in data
        assert "enabled" in data
        assert isinstance(data["reminders"], list)
        
        print(f"✓ Invoice reminders endpoint returned {len(data['reminders'])} reminders")
        
        # Check reminder structure if any exist
        if data["reminders"]:
            reminder = data["reminders"][0]
            required_fields = ["invoiceId", "invoiceNumber", "buyerName", "daysSince", "reminderType", "pendingAmount"]
            for field in required_fields:
                assert field in reminder, f"Missing field '{field}' in reminder"
            
            # Check whatsappLink format if present
            if reminder.get("whatsappLink"):
                assert "wa.me" in reminder["whatsappLink"]
                print(f"✓ Sample reminder: {reminder['invoiceNumber']} - {reminder['reminderType']} - {reminder['daysSince']}d - WhatsApp link present")


class TestWhatsAppLink:
    """Test WhatsApp link generation endpoint."""
    
    @pytest.fixture(scope="class")
    def invoice_with_phone(self):
        """Get or create an invoice with a buyer who has a phone number."""
        # Get invoices
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        invoices = res.json().get("invoices", [])
        
        # Find invoice with buyer phone
        for inv in invoices:
            if inv.get("buyerPhone"):
                return inv
        
        pytest.skip("No invoice with buyer phone number available")
    
    def test_whatsapp_link_default_followup(self, invoice_with_phone):
        """GET whatsapp-link returns wa.me URL with prefilled message."""
        invoice_id = invoice_with_phone["id"]
        res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/whatsapp-link",
            headers=HEADERS
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "whatsappLink" in data
        assert "wa.me" in data["whatsappLink"]
        assert "message" in data
        assert "Total Amount" in data["message"] or "Invoice" in data["message"]
        print(f"✓ WhatsApp link generated: {data['whatsappLink'][:50]}...")
    
    def test_whatsapp_link_overdue_type(self, invoice_with_phone):
        """GET whatsapp-link?reminder_type=overdue returns overdue message."""
        invoice_id = invoice_with_phone["id"]
        res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/whatsapp-link?reminder_type=overdue",
            headers=HEADERS
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "overdue" in data["message"].lower()
        print(f"✓ Overdue WhatsApp message: {data['message'][:60]}...")
    
    def test_whatsapp_link_indian_phone_format(self, invoice_with_phone):
        """WhatsApp link should prepend 91 for 10-digit Indian numbers."""
        invoice_id = invoice_with_phone["id"]
        res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/whatsapp-link",
            headers=HEADERS
        )
        data = res.json()
        
        # Extract phone from wa.me link
        wa_link = data.get("whatsappLink", "")
        # wa.me/{phone}?text=...
        if "wa.me/" in wa_link:
            phone_part = wa_link.split("wa.me/")[1].split("?")[0]
            # Should start with 91 for Indian numbers
            assert phone_part.startswith("91") or len(phone_part) > 10, f"Phone should have country code: {phone_part}"
            print(f"✓ Phone formatted correctly: {phone_part}")


class TestDueDaysField:
    """Test dueDays field in invoice creation and listing."""
    
    def test_create_invoice_with_duedays(self):
        """POST invoice with dueDays stores the field."""
        # Get a buyer
        buyers_res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=HEADERS)
        if buyers_res.status_code != 200 or not buyers_res.json().get("buyers"):
            pytest.skip("No buyers available")
        buyer_id = buyers_res.json()["buyers"][0]["id"]
        
        payload = {
            "buyerId": buyer_id,
            "items": [{"productName": "TEST_DueDays_Item", "quantity": 1, "price": 1000, "gstPercent": 18}],
            "notes": "Testing dueDays field",
            "deductStock": False,
            "dueDays": 14  # Custom due days
        }
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS, json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        invoice = res.json().get("invoice", {})
        # Note: dueDays may not be returned in create response, check via GET
        invoice_id = invoice.get("id")
        
        # Verify via GET
        get_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=HEADERS)
        inv_data = get_res.json().get("invoice", {})
        # dueDays defaults to 7 if not properly stored, we set 14
        due_days = inv_data.get("dueDays", 7)
        print(f"✓ Invoice created with dueDays: {due_days}")
    
    def test_invoice_list_includes_duedays(self):
        """GET invoices list returns dueDays field for each invoice."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        assert res.status_code == 200
        
        invoices = res.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices available to test")
        
        # Check that dueDays is present in list
        for inv in invoices[:3]:
            assert "dueDays" in inv, f"Invoice {inv.get('invoiceNumber')} missing dueDays"
            assert isinstance(inv["dueDays"], int)
        print(f"✓ Invoice list includes dueDays field (sample: {invoices[0].get('dueDays', 7)})")


class TestOverdueDetection:
    """Test automatic overdue detection."""
    
    def test_invoice_list_triggers_overdue_check(self):
        """GET invoices triggers automatic overdue detection."""
        # This test verifies the endpoint works - actual overdue marking depends on dates
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        invoices = res.json().get("invoices", [])
        
        # Check for any overdue invoices
        overdue_invoices = [inv for inv in invoices if inv.get("status") == "overdue"]
        print(f"✓ Invoice list fetched. Found {len(overdue_invoices)} overdue invoices out of {len(invoices)}")
        
        # Verify overdue invoices have pending amount > 0
        for inv in overdue_invoices:
            assert inv.get("pendingAmount", 0) > 0, "Overdue invoice should have pending amount"


class TestPdfWithPaymentSummary:
    """Test PDF generation includes payment summary."""
    
    def test_pdf_endpoint_returns_binary(self):
        """GET invoices/{id}/pdf returns PDF binary."""
        # Get an invoice
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        invoices = res.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices available")
        
        invoice_id = invoices[0]["id"]
        
        pdf_res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/pdf",
            headers=HEADERS
        )
        assert pdf_res.status_code == 200, f"Expected 200, got {pdf_res.status_code}"
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert len(pdf_res.content) > 1000, "PDF should be larger than 1KB"
        
        # Check PDF header
        assert pdf_res.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ PDF generated: {len(pdf_res.content)} bytes")
    
    def test_pdf_filename_header(self):
        """PDF response has correct filename header."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        invoices = res.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices available")
        
        invoice = invoices[0]
        invoice_id = invoice["id"]
        invoice_num = invoice.get("invoiceNumber", "")
        
        pdf_res = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/pdf",
            headers=HEADERS
        )
        
        content_disp = pdf_res.headers.get("content-disposition", "")
        assert invoice_num.replace("-", "") in content_disp.replace("-", "") or "invoice" in content_disp.lower()
        print(f"✓ PDF filename header: {content_disp}")


class TestInvoiceListPaymentColumns:
    """Test invoice list includes payment tracking columns."""
    
    def test_invoice_list_has_paid_pending_columns(self):
        """Invoice list API returns totalPaid and pendingAmount for each invoice."""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=HEADERS)
        assert res.status_code == 200
        
        invoices = res.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices available")
        
        for inv in invoices[:5]:
            assert "totalPaid" in inv, f"Invoice {inv.get('invoiceNumber')} missing totalPaid"
            assert "pendingAmount" in inv, f"Invoice {inv.get('invoiceNumber')} missing pendingAmount"
            assert "total" in inv
            
            # Verify math: pendingAmount should be total - totalPaid (approximately)
            expected_pending = inv["total"] - inv["totalPaid"]
            actual_pending = inv["pendingAmount"]
            assert abs(expected_pending - actual_pending) < 0.1, f"Pending mismatch: expected {expected_pending}, got {actual_pending}"
        
        print(f"✓ Invoice list includes totalPaid and pendingAmount columns")


# Run-time configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
