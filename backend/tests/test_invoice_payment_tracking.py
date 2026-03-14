"""
Invoice Payment Tracking System - Backend API Tests
Tests: Add payment, auto-recalculation, status transitions, list payments, delete payments, validation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}


class TestPaymentTrackingSetup:
    """Setup: Get or create a test invoice for payment tests"""
    
    @pytest.fixture(scope="class")
    def test_invoice(self, request):
        """Get an existing draft/sent invoice or create a new one for testing"""
        # First list existing invoices
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        assert res.status_code == 200, f"Failed to list invoices: {res.text}"
        invoices = res.json().get("invoices", [])
        
        # Find a draft or sent invoice that's NOT already paid (skip INV-7C5A6E-0019)
        test_invoice = None
        for inv in invoices:
            if inv.get("status") in ["draft", "sent", "partially_paid"] and inv.get("pendingAmount", 0) > 0:
                if "0019" not in inv.get("invoiceNumber", ""):  # Skip already-paid one
                    test_invoice = inv
                    break
        
        if not test_invoice:
            # Create a new invoice for testing
            buyers_res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=AUTH_HEADER)
            assert buyers_res.status_code == 200
            buyers = buyers_res.json().get("buyers", [])
            assert len(buyers) > 0, "No buyers found - cannot create test invoice"
            
            buyer_id = buyers[0]["id"]
            create_payload = {
                "buyerId": buyer_id,
                "items": [
                    {"productName": "Payment Test Item", "quantity": 2, "price": 500, "gstPercent": 18}
                ],
                "notes": "Test invoice for payment tracking tests",
                "deductStock": False
            }
            create_res = requests.post(f"{BASE_URL}/api/business-tools/invoices", 
                                       headers=AUTH_HEADER, json=create_payload)
            assert create_res.status_code == 200, f"Failed to create test invoice: {create_res.text}"
            test_invoice = create_res.json().get("invoice")
        
        # Store the invoice ID in class for cleanup
        request.cls.test_invoice_id = test_invoice["id"]
        print(f"Using invoice: {test_invoice.get('invoiceNumber')} (ID: {test_invoice['id']}), Total: {test_invoice.get('total')}, Pending: {test_invoice.get('pendingAmount', test_invoice.get('total'))}")
        return test_invoice


class TestAddPaymentEndpoint(TestPaymentTrackingSetup):
    """Tests for POST /api/business-tools/invoices/{id}/payments"""
    
    def test_add_payment_with_all_fields(self, test_invoice):
        """Add payment with all fields: amount, paymentDate, paymentMethod, accountName, referenceNumber, notes"""
        invoice_id = test_invoice["id"]
        pending = test_invoice.get("pendingAmount", test_invoice.get("total"))
        payment_amount = min(100, pending * 0.3)  # Pay 30% or 100, whichever is smaller
        
        payload = {
            "amount": payment_amount,
            "paymentDate": "2024-01-15",
            "paymentMethod": "upi",
            "accountName": "John Doe - HDFC",
            "referenceNumber": "UPI123456789",
            "notes": "First partial payment via UPI"
        }
        
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                           headers=AUTH_HEADER, json=payload)
        assert res.status_code == 200, f"Failed to add payment: {res.text}"
        
        data = res.json()
        assert "payment" in data, "Response should contain 'payment'"
        payment = data["payment"]
        
        # Verify all fields are stored
        assert payment["amount"] == payment_amount
        assert payment["paymentMethod"] == "upi"
        assert payment["accountName"] == "John Doe - HDFC"
        assert payment["referenceNumber"] == "UPI123456789"
        assert payment["notes"] == "First partial payment via UPI"
        assert "id" in payment
        assert "createdAt" in payment
        
        # Store payment ID for later tests
        self.__class__.first_payment_id = payment["id"]
        self.__class__.first_payment_amount = payment_amount
        print(f"Payment created: ID={payment['id']}, Amount={payment_amount}")
    
    def test_add_payment_minimal_fields(self, test_invoice):
        """Add payment with only required field (amount)"""
        invoice_id = test_invoice["id"]
        
        payload = {
            "amount": 50
        }
        
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                           headers=AUTH_HEADER, json=payload)
        assert res.status_code == 200, f"Failed to add minimal payment: {res.text}"
        
        payment = res.json()["payment"]
        assert payment["amount"] == 50
        assert payment["paymentMethod"] == "cash"  # Default
        
        self.__class__.second_payment_id = payment["id"]
        print(f"Minimal payment created: ID={payment['id']}")
    
    def test_add_payment_bank_transfer(self, test_invoice):
        """Add payment with bank_transfer method"""
        invoice_id = test_invoice["id"]
        
        payload = {
            "amount": 25,
            "paymentMethod": "bank_transfer",
            "accountName": "ABC Corp - ICICI",
            "referenceNumber": "NEFT12345"
        }
        
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                           headers=AUTH_HEADER, json=payload)
        assert res.status_code == 200, f"Failed to add bank payment: {res.text}"
        
        payment = res.json()["payment"]
        assert payment["paymentMethod"] == "bank_transfer"
        
        self.__class__.third_payment_id = payment["id"]
        print(f"Bank transfer payment created: ID={payment['id']}")


class TestAutoRecalculation(TestPaymentTrackingSetup):
    """Tests for auto-recalculation of totalPaid, pendingAmount after payments"""
    
    def test_invoice_totals_updated_after_payment(self, test_invoice):
        """After adding payment, invoice totalPaid and pendingAmount should update"""
        invoice_id = test_invoice["id"]
        
        # Get updated invoice
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert res.status_code == 200
        
        invoice = res.json()["invoice"]
        grand_total = invoice.get("total", 0)
        total_paid = invoice.get("totalPaid", 0)
        pending = invoice.get("pendingAmount", 0)
        
        print(f"After payments - Grand Total: {grand_total}, Total Paid: {total_paid}, Pending: {pending}")
        
        # Verify recalculation
        assert total_paid > 0, "totalPaid should be > 0 after payments"
        assert pending == round(grand_total - total_paid, 2), f"pending ({pending}) should equal grand_total ({grand_total}) - total_paid ({total_paid})"


class TestStatusTransitions(TestPaymentTrackingSetup):
    """Tests for automatic status transitions based on payments"""
    
    def test_status_changes_to_partially_paid(self, test_invoice):
        """Status should be 'partially_paid' when partial payment added"""
        invoice_id = test_invoice["id"]
        
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert res.status_code == 200
        
        invoice = res.json()["invoice"]
        pending = invoice.get("pendingAmount", 0)
        total_paid = invoice.get("totalPaid", 0)
        
        # If there's pending amount and some payment made, should be partially_paid
        if pending > 0 and total_paid > 0:
            assert invoice["status"] == "partially_paid", f"Status should be 'partially_paid', got: {invoice['status']}"
            print(f"Status correctly set to 'partially_paid'")
        elif pending == 0 and total_paid > 0:
            assert invoice["status"] == "paid", f"Status should be 'paid' when fully paid"
            print(f"Invoice is fully paid")


class TestPaymentExceedingPending:
    """Test validation: Payment amount cannot exceed pending amount"""
    
    def test_payment_exceeding_pending_rejected(self):
        """Payment amount exceeding pending amount should be rejected"""
        # First get an invoice with known pending amount
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        assert res.status_code == 200
        
        invoices = res.json().get("invoices", [])
        test_inv = None
        for inv in invoices:
            if inv.get("status") not in ["cancelled", "paid"] and inv.get("pendingAmount", 0) > 0:
                test_inv = inv
                break
        
        if not test_inv:
            pytest.skip("No invoice with pending amount found")
        
        invoice_id = test_inv["id"]
        pending = test_inv.get("pendingAmount", test_inv.get("total", 0))
        
        # Try to pay more than pending
        payload = {
            "amount": pending + 1000,  # Way more than pending
            "paymentMethod": "cash"
        }
        
        res = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                           headers=AUTH_HEADER, json=payload)
        
        assert res.status_code == 400, f"Should reject payment exceeding pending. Got: {res.status_code}, {res.text}"
        assert "exceeds" in res.text.lower() or "pending" in res.text.lower(), f"Error should mention exceeds/pending: {res.text}"
        print(f"Payment exceeding pending correctly rejected: {res.json().get('detail')}")


class TestListPayments:
    """Tests for GET /api/business-tools/invoices/{id}/payments"""
    
    def test_list_payments_returns_summary(self):
        """GET payments should return list and summary"""
        # Get an invoice with payments
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = res.json().get("invoices", [])
        
        test_inv = None
        for inv in invoices:
            if inv.get("totalPaid", 0) > 0:
                test_inv = inv
                break
        
        if not test_inv:
            pytest.skip("No invoice with payments found")
        
        invoice_id = test_inv["id"]
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", headers=AUTH_HEADER)
        assert res.status_code == 200, f"Failed to list payments: {res.text}"
        
        data = res.json()
        assert "payments" in data, "Response should have 'payments' array"
        assert "summary" in data, "Response should have 'summary' object"
        
        summary = data["summary"]
        assert "grandTotal" in summary, "Summary should have grandTotal"
        assert "totalPaid" in summary, "Summary should have totalPaid"
        assert "pendingAmount" in summary, "Summary should have pendingAmount"
        assert "paymentCount" in summary, "Summary should have paymentCount"
        assert "status" in summary, "Summary should have status"
        
        print(f"Payments list: {len(data['payments'])} payments")
        print(f"Summary: {summary}")
    
    def test_invoice_detail_includes_payments(self):
        """GET /invoices/{id} should include payments array"""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = res.json().get("invoices", [])
        
        test_inv = None
        for inv in invoices:
            if inv.get("totalPaid", 0) > 0:
                test_inv = inv
                break
        
        if not test_inv:
            pytest.skip("No invoice with payments found")
        
        invoice_id = test_inv["id"]
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert res.status_code == 200
        
        invoice = res.json()["invoice"]
        assert "payments" in invoice, "Invoice detail should include 'payments' array"
        assert "totalPaid" in invoice, "Invoice should have 'totalPaid'"
        assert "pendingAmount" in invoice, "Invoice should have 'pendingAmount'"
        
        print(f"Invoice {invoice.get('invoiceNumber')} has {len(invoice['payments'])} payments")


class TestDeletePayment:
    """Tests for DELETE /api/business-tools/invoices/{id}/payments/{payment_id}"""
    
    def test_delete_payment_and_recalculate(self):
        """Delete a payment should recalculate invoice totals"""
        # First, find or create an invoice with a payment we can delete
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = res.json().get("invoices", [])
        
        test_inv = None
        for inv in invoices:
            if inv.get("totalPaid", 0) > 0 and inv.get("status") not in ["cancelled"]:
                test_inv = inv
                break
        
        if not test_inv:
            pytest.skip("No invoice with payments to delete")
        
        invoice_id = test_inv["id"]
        
        # Get payments list
        pay_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", headers=AUTH_HEADER)
        payments = pay_res.json().get("payments", [])
        
        if not payments:
            pytest.skip("No payments to delete")
        
        payment_to_delete = payments[-1]  # Delete the last one
        payment_id = payment_to_delete["id"]
        payment_amount = payment_to_delete["amount"]
        
        initial_total_paid = pay_res.json()["summary"]["totalPaid"]
        
        # Delete the payment
        del_res = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments/{payment_id}", 
                                  headers=AUTH_HEADER)
        assert del_res.status_code == 200, f"Failed to delete payment: {del_res.text}"
        print(f"Deleted payment {payment_id} (amount: {payment_amount})")
        
        # Verify recalculation
        verify_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        invoice = verify_res.json()["invoice"]
        
        new_total_paid = invoice.get("totalPaid", 0)
        expected_total = round(initial_total_paid - payment_amount, 2)
        
        assert abs(new_total_paid - expected_total) < 0.01, f"After delete: totalPaid should be {expected_total}, got {new_total_paid}"
        print(f"After deletion - Total Paid: {new_total_paid} (was {initial_total_paid})")


class TestMultiplePartialPayments:
    """Test scenario: Multiple partial payments of different amounts/methods"""
    
    def test_three_payments_different_methods(self):
        """Add 3 payments with different amounts and methods"""
        # Create a fresh invoice
        buyers_res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=AUTH_HEADER)
        buyers = buyers_res.json().get("buyers", [])
        if not buyers:
            pytest.skip("No buyers found")
        
        buyer_id = buyers[0]["id"]
        create_payload = {
            "buyerId": buyer_id,
            "items": [
                {"productName": "Multi-payment Test", "quantity": 1, "price": 10000, "gstPercent": 18}
            ],
            "notes": "Test for multiple partial payments",
            "deductStock": False
        }
        
        create_res = requests.post(f"{BASE_URL}/api/business-tools/invoices", 
                                   headers=AUTH_HEADER, json=create_payload)
        assert create_res.status_code == 200
        invoice = create_res.json()["invoice"]
        invoice_id = invoice["id"]
        grand_total = invoice["total"]  # Should be 11800 (10000 + 18% GST)
        print(f"Created invoice {invoice['invoiceNumber']} with total {grand_total}")
        
        # Payment 1: UPI - 3000
        p1 = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                          headers=AUTH_HEADER, json={
                              "amount": 3000,
                              "paymentMethod": "upi",
                              "accountName": "Customer UPI",
                              "referenceNumber": "UPI001"
                          })
        assert p1.status_code == 200
        print("Payment 1: UPI 3000")
        
        # Payment 2: Bank Transfer - 5000
        p2 = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                          headers=AUTH_HEADER, json={
                              "amount": 5000,
                              "paymentMethod": "bank_transfer",
                              "accountName": "HDFC Current",
                              "referenceNumber": "NEFT002"
                          })
        assert p2.status_code == 200
        print("Payment 2: Bank Transfer 5000")
        
        # Payment 3: Cash - 2800
        p3 = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                          headers=AUTH_HEADER, json={
                              "amount": 2800,
                              "paymentMethod": "cash",
                              "notes": "Cash received in office"
                          })
        assert p3.status_code == 200
        print("Payment 3: Cash 2800")
        
        # Verify totals
        verify_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        invoice = verify_res.json()["invoice"]
        
        expected_paid = 3000 + 5000 + 2800  # 10800
        expected_pending = grand_total - expected_paid
        
        assert invoice["totalPaid"] == expected_paid, f"totalPaid should be {expected_paid}, got {invoice['totalPaid']}"
        assert abs(invoice["pendingAmount"] - expected_pending) < 0.01, f"pendingAmount should be ~{expected_pending}, got {invoice['pendingAmount']}"
        assert invoice["status"] == "partially_paid", f"Status should be 'partially_paid', got {invoice['status']}"
        
        # Verify payments list
        payments = invoice.get("payments", [])
        assert len(payments) == 3, f"Should have 3 payments, got {len(payments)}"
        
        print(f"Final state: Total Paid={invoice['totalPaid']}, Pending={invoice['pendingAmount']}, Status={invoice['status']}")


class TestFullPaymentToStatus:
    """Test status changes to 'paid' when fully paid"""
    
    def test_full_payment_sets_status_paid(self):
        """When total paid equals grand total, status should be 'paid'"""
        # Create a small invoice
        buyers_res = requests.get(f"{BASE_URL}/api/business-tools/buyers", headers=AUTH_HEADER)
        buyers = buyers_res.json().get("buyers", [])
        if not buyers:
            pytest.skip("No buyers found")
        
        buyer_id = buyers[0]["id"]
        create_payload = {
            "buyerId": buyer_id,
            "items": [
                {"productName": "Full Payment Test", "quantity": 1, "price": 100, "gstPercent": 0}
            ],
            "notes": "Test for full payment status",
            "deductStock": False
        }
        
        create_res = requests.post(f"{BASE_URL}/api/business-tools/invoices", 
                                   headers=AUTH_HEADER, json=create_payload)
        assert create_res.status_code == 200
        invoice = create_res.json()["invoice"]
        invoice_id = invoice["id"]
        grand_total = invoice["total"]  # 100
        print(f"Created invoice {invoice['invoiceNumber']} with total {grand_total}")
        
        # Pay the full amount
        p = requests.post(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments", 
                         headers=AUTH_HEADER, json={
                             "amount": grand_total,
                             "paymentMethod": "cash"
                         })
        assert p.status_code == 200
        print(f"Added full payment of {grand_total}")
        
        # Verify status is 'paid'
        verify_res = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        invoice = verify_res.json()["invoice"]
        
        assert invoice["status"] == "paid", f"Status should be 'paid', got {invoice['status']}"
        assert invoice["pendingAmount"] == 0, f"pendingAmount should be 0, got {invoice['pendingAmount']}"
        assert invoice["totalPaid"] == grand_total, f"totalPaid should be {grand_total}, got {invoice['totalPaid']}"
        
        print(f"Status correctly changed to 'paid'")


class TestInvoiceListShowsPaidPending:
    """Test that invoice list includes Paid and Pending columns"""
    
    def test_list_invoices_has_paid_pending_fields(self):
        """GET /invoices should return totalPaid and pendingAmount for each invoice"""
        res = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        assert res.status_code == 200
        
        invoices = res.json().get("invoices", [])
        assert len(invoices) > 0, "Should have at least one invoice"
        
        for inv in invoices[:5]:  # Check first 5
            assert "totalPaid" in inv, f"Invoice {inv.get('invoiceNumber')} missing 'totalPaid'"
            assert "pendingAmount" in inv, f"Invoice {inv.get('invoiceNumber')} missing 'pendingAmount'"
            print(f"{inv.get('invoiceNumber')}: Total={inv.get('total')}, Paid={inv.get('totalPaid')}, Pending={inv.get('pendingAmount')}, Status={inv.get('status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
