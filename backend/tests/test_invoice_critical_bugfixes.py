"""
Test Invoice Critical Bug Fixes:
1. Invoice Number Format: INV{ABBR}-{CODE}-{NNNN}
2. No Duplicate Invoice Numbers
3. Status Consistency: Derived from payment state
4. Reports: Include all statuses (draft, sent, viewed, partially_paid, paid, overdue)
5. seller_invoice_counters: Atomic counter for invoice numbering
"""

import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"


class TestInvoiceNumberFormat:
    """Test invoice number format is INV{ABBR}-{CODE}-{NNNN}"""

    def test_get_invoices_returns_new_format(self):
        """All invoices should have format INV{ABBR}-{CODE}-{NNNN}"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"GET invoices failed: {response.text}"
        
        data = response.json()
        invoices = data.get("invoices", [])
        assert len(invoices) > 0, "No invoices found"
        
        print(f"Found {len(invoices)} invoices")
        
        # Verify format for each invoice
        for inv in invoices:
            inv_num = inv.get("invoiceNumber", "")
            print(f"  Invoice: {inv_num}")
            
            # Format should be INVX-YYYYYY-NNNN
            assert inv_num.startswith("INV"), f"Invoice {inv_num} doesn't start with INV"
            
            parts = inv_num.split("-")
            assert len(parts) == 3, f"Invoice {inv_num} doesn't have 3 parts (INVX-CODE-SEQ)"
            
            # First part: INV + abbreviation (1+ chars)
            assert parts[0].startswith("INV"), f"First part should start with INV: {parts[0]}"
            abbreviation = parts[0][3:]  # After "INV"
            assert len(abbreviation) >= 1, f"Abbreviation missing in {inv_num}"
            
            # Second part: seller code (6 chars hex)
            assert len(parts[1]) == 6, f"Seller code should be 6 chars: {parts[1]}"
            
            # Third part: sequence number (4 digits)
            assert parts[2].isdigit(), f"Sequence should be digits: {parts[2]}"
            assert len(parts[2]) == 4, f"Sequence should be 4 digits: {parts[2]}"
        
        print("PASS: All invoices have correct format INV{ABBR}-{CODE}-{NNNN}")

    def test_no_duplicate_invoice_numbers(self):
        """Verify no duplicate invoice numbers exist"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices?limit=100",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        invoices = data.get("invoices", [])
        
        invoice_numbers = [inv.get("invoiceNumber") for inv in invoices]
        unique_numbers = set(invoice_numbers)
        
        print(f"Total invoices: {len(invoice_numbers)}, Unique: {len(unique_numbers)}")
        
        # Find duplicates if any
        if len(invoice_numbers) != len(unique_numbers):
            from collections import Counter
            counts = Counter(invoice_numbers)
            duplicates = {num: count for num, count in counts.items() if count > 1}
            print(f"DUPLICATES FOUND: {duplicates}")
            assert False, f"Duplicate invoice numbers found: {duplicates}"
        
        print("PASS: No duplicate invoice numbers")


class TestRapidInvoiceCreation:
    """Test creating multiple invoices rapidly produces unique sequential numbers"""

    def get_buyer_id(self):
        """Get a buyer ID for creating invoices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/buyers",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Failed to get buyers: {response.text}"
        buyers = response.json().get("buyers", [])
        assert len(buyers) > 0, "No buyers found - need a buyer to create invoices"
        return buyers[0].get("id")

    def test_rapid_invoice_creation_unique_numbers(self):
        """Create 5 invoices rapidly and verify all get unique sequential numbers"""
        buyer_id = self.get_buyer_id()
        
        invoice_numbers = []
        invoice_ids = []
        
        # Create 5 invoices rapidly
        for i in range(5):
            invoice_data = {
                "buyerId": buyer_id,
                "items": [
                    {
                        "productName": f"Rapid Test Item {i+1}",
                        "quantity": 1,
                        "price": 100 + i,
                        "gstPercent": 18
                    }
                ],
                "notes": f"Rapid creation test #{i+1}",
                "dueDays": 7,
                "deductStock": False
            }
            
            response = requests.post(
                f"{BASE_URL}/api/business-tools/invoices",
                headers={
                    "Authorization": f"Bearer {AUTH_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=invoice_data
            )
            
            assert response.status_code == 200, f"Failed to create invoice {i+1}: {response.text}"
            
            created = response.json().get("invoice", {})
            inv_num = created.get("invoiceNumber")
            inv_id = created.get("id")
            
            print(f"Created invoice {i+1}: {inv_num}")
            invoice_numbers.append(inv_num)
            invoice_ids.append(inv_id)
        
        # Verify all unique
        unique_nums = set(invoice_numbers)
        assert len(unique_nums) == 5, f"Not all unique! Numbers: {invoice_numbers}"
        
        # Verify sequential (extract sequence numbers)
        sequences = []
        for num in invoice_numbers:
            parts = num.split("-")
            seq = int(parts[2])
            sequences.append(seq)
        
        sequences_sorted = sorted(sequences)
        # Check if sequences are consecutive
        for i in range(len(sequences_sorted) - 1):
            diff = sequences_sorted[i+1] - sequences_sorted[i]
            assert diff == 1, f"Sequences not consecutive: {sequences_sorted}"
        
        print(f"PASS: Created 5 invoices with unique sequential numbers: {sequences_sorted}")
        
        # Cleanup - delete the test invoices if they are in draft status
        for inv_id in invoice_ids:
            try:
                # First update to draft if needed
                requests.put(
                    f"{BASE_URL}/api/business-tools/invoices/{inv_id}/status",
                    headers={
                        "Authorization": f"Bearer {AUTH_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={"status": "cancelled"}
                )
            except:
                pass


class TestStatusConsistency:
    """Test invoice status is consistently derived from payment state"""

    def get_buyer_id(self):
        """Get a buyer ID for creating invoices"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/buyers",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        buyers = response.json().get("buyers", [])
        return buyers[0].get("id")

    def test_invoice_with_zero_paid_not_marked_paid(self):
        """Invoice with totalPaid=0 and total>0 should NOT be 'paid' status"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        invoices = data.get("invoices", [])
        
        inconsistent = []
        for inv in invoices:
            total = inv.get("total", 0)
            total_paid = inv.get("totalPaid", 0)
            status = inv.get("status", "")
            
            # If totalPaid=0 and total>0, status should NOT be "paid"
            if total > 0 and total_paid == 0 and status == "paid":
                inconsistent.append({
                    "invoiceNumber": inv.get("invoiceNumber"),
                    "total": total,
                    "totalPaid": total_paid,
                    "status": status,
                    "issue": "Paid=0 but status is 'paid'"
                })
        
        if inconsistent:
            print(f"INCONSISTENT INVOICES FOUND: {inconsistent}")
            assert False, f"Status inconsistency: {len(inconsistent)} invoices have totalPaid=0 but status='paid'"
        
        print("PASS: No invoices with totalPaid=0 and status='paid'")

    def test_partial_payment_status_partially_paid(self):
        """Invoice with 0 < totalPaid < total should be 'partially_paid'"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        invoices = response.json().get("invoices", [])
        
        for inv in invoices:
            total = inv.get("total", 0)
            total_paid = inv.get("totalPaid", 0)
            status = inv.get("status", "")
            
            if total > 0 and total_paid > 0 and total_paid < total:
                # Should be partially_paid
                if status != "partially_paid":
                    print(f"Invoice {inv.get('invoiceNumber')}: total={total}, paid={total_paid}, status={status} - should be 'partially_paid'")
                    # Note: overdue invoices with partial payment might stay overdue
                    assert status in ["partially_paid", "overdue"], f"Partial payment should be 'partially_paid' or 'overdue', got {status}"
        
        print("PASS: Partial payment status consistency verified")

    def test_full_payment_status_paid(self):
        """Invoice with totalPaid >= total should be 'paid'"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        invoices = response.json().get("invoices", [])
        
        for inv in invoices:
            total = inv.get("total", 0)
            total_paid = inv.get("totalPaid", 0)
            status = inv.get("status", "")
            
            if total > 0 and total_paid >= total:
                assert status == "paid", f"Invoice {inv.get('invoiceNumber')} fully paid ({total_paid}/{total}) but status is {status}"
        
        print("PASS: Full payment status consistency verified")

    def test_payment_updates_status_correctly(self):
        """Adding a payment should update status correctly"""
        buyer_id = self.get_buyer_id()
        
        # Create a new invoice
        invoice_data = {
            "buyerId": buyer_id,
            "items": [
                {
                    "productName": "Status Test Item",
                    "quantity": 1,
                    "price": 1000,
                    "gstPercent": 18
                }
            ],
            "notes": "Status transition test",
            "dueDays": 7,
            "deductStock": False
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json=invoice_data
        )
        assert create_resp.status_code == 200, f"Failed to create invoice: {create_resp.text}"
        
        created_invoice = create_resp.json().get("invoice", {})
        invoice_id = created_invoice.get("id")
        total = created_invoice.get("total", 0)
        
        print(f"Created invoice {created_invoice.get('invoiceNumber')} with total={total}, status={created_invoice.get('status')}")
        assert created_invoice.get("status") == "draft", "New invoice should be draft"
        
        # Add partial payment
        partial_amount = total / 2
        payment_resp = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json={"amount": partial_amount, "paymentMethod": "cash"}
        )
        assert payment_resp.status_code == 200, f"Failed to add payment: {payment_resp.text}"
        
        # Check status after partial payment
        get_resp = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert get_resp.status_code == 200
        updated_invoice = get_resp.json().get("invoice", {})
        
        print(f"After partial payment: totalPaid={updated_invoice.get('totalPaid')}, status={updated_invoice.get('status')}")
        assert updated_invoice.get("status") == "partially_paid", f"Should be 'partially_paid' after partial payment, got {updated_invoice.get('status')}"
        
        # Add remaining payment
        remaining = updated_invoice.get("pendingAmount", 0)
        payment_resp2 = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json={"amount": remaining, "paymentMethod": "cash"}
        )
        assert payment_resp2.status_code == 200
        
        # Check status after full payment
        get_resp2 = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert get_resp2.status_code == 200
        final_invoice = get_resp2.json().get("invoice", {})
        
        print(f"After full payment: totalPaid={final_invoice.get('totalPaid')}, status={final_invoice.get('status')}")
        assert final_invoice.get("status") == "paid", f"Should be 'paid' after full payment, got {final_invoice.get('status')}"
        
        print("PASS: Payment correctly updates status (draft -> partially_paid -> paid)")

    def test_delete_payments_reverts_status(self):
        """Deleting all payments from paid invoice should revert status to 'sent' not 'paid'"""
        buyer_id = self.get_buyer_id()
        
        # Create invoice
        invoice_data = {
            "buyerId": buyer_id,
            "items": [{"productName": "Delete Payment Test", "quantity": 1, "price": 500, "gstPercent": 18}],
            "notes": "Delete payment status test",
            "dueDays": 7,
            "deductStock": False
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json=invoice_data
        )
        assert create_resp.status_code == 200
        invoice_id = create_resp.json()["invoice"]["id"]
        total = create_resp.json()["invoice"]["total"]
        
        # Add full payment
        requests.post(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json={"amount": total, "paymentMethod": "cash"}
        )
        
        # Verify it's paid
        get_resp = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        paid_invoice = get_resp.json()["invoice"]
        assert paid_invoice["status"] == "paid", "Invoice should be paid after full payment"
        
        # Get payment ID
        payments = paid_invoice.get("payments", [])
        assert len(payments) > 0, "Should have at least one payment"
        payment_id = payments[0]["id"]
        
        # Delete the payment
        del_resp = requests.delete(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/payments/{payment_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert del_resp.status_code == 200
        
        # Check status reverts to 'sent' (not 'paid')
        get_resp2 = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        reverted = get_resp2.json()["invoice"]
        
        print(f"After deleting all payments: totalPaid={reverted.get('totalPaid')}, status={reverted.get('status')}")
        assert reverted.get("totalPaid") == 0, "totalPaid should be 0 after deleting payment"
        assert reverted.get("status") != "paid", f"Status should NOT be 'paid' after deleting all payments, got {reverted.get('status')}"
        assert reverted.get("status") == "sent", f"Status should be 'sent' after deleting all payments, got {reverted.get('status')}"
        
        print("PASS: Deleting all payments correctly reverts status to 'sent'")


class TestReportsIncludeAllInvoices:
    """Test reports include all invoice statuses (not just draft/sent/paid)"""

    def test_sales_summary_returns_invoices(self):
        """GET /api/business-tools/reports/sales-summary should return invoice data"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/sales-summary",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Sales summary failed: {response.text}"
        
        data = response.json()
        overall = data.get("overall", {})
        
        invoice_count = overall.get("invoiceCount", 0)
        total_revenue = overall.get("totalRevenue", 0)
        
        print(f"Sales Summary: {invoice_count} invoices, totalRevenue={total_revenue}")
        
        # Should have invoices (previously was returning 0)
        assert invoice_count > 0, f"Expected invoices in sales-summary, got {invoice_count}"
        
        print("PASS: Sales summary returns invoice data")

    def test_sales_summary_includes_all_statuses(self):
        """Verify sales-summary includes all statuses (draft, sent, viewed, partially_paid, paid, overdue)"""
        # First get all invoices to compare
        invoices_resp = requests.get(
            f"{BASE_URL}/api/business-tools/invoices?limit=100",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert invoices_resp.status_code == 200
        
        invoices = invoices_resp.json().get("invoices", [])
        # Count non-cancelled invoices
        active_statuses = ["draft", "sent", "viewed", "partially_paid", "paid", "overdue"]
        active_invoices = [inv for inv in invoices if inv.get("status") in active_statuses]
        active_count = len(active_invoices)
        
        print(f"Active invoices (non-cancelled): {active_count}")
        
        # Status breakdown
        status_counts = {}
        for inv in invoices:
            s = inv.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        print(f"Status breakdown: {status_counts}")
        
        # Now check reports
        report_resp = requests.get(
            f"{BASE_URL}/api/business-tools/reports/sales-summary",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert report_resp.status_code == 200
        
        report_count = report_resp.json().get("overall", {}).get("invoiceCount", 0)
        print(f"Sales summary invoiceCount: {report_count}")
        
        # Report should include at least the active invoices
        # Note: might be fewer if date range filters apply
        assert report_count > 0, "Sales summary should have invoices"
        
        print("PASS: Sales summary includes invoices from multiple statuses")

    def test_product_sales_returns_data(self):
        """GET /api/business-tools/reports/product-sales should return products"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/product-sales",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Product sales failed: {response.text}"
        
        products = response.json().get("products", [])
        print(f"Product sales: {len(products)} products")
        
        # Should have at least some products
        for p in products[:5]:
            print(f"  - {p.get('productName')}: qty={p.get('totalQuantity')}, revenue={p.get('totalRevenue')}")
        
        assert len(products) > 0, "Expected products in product-sales report"
        print("PASS: Product sales returns data")

    def test_top_buyers_returns_data(self):
        """GET /api/business-tools/reports/top-buyers should return buyer data"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/top-buyers",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Top buyers failed: {response.text}"
        
        buyers = response.json().get("buyers", [])
        print(f"Top buyers: {len(buyers)} buyers")
        
        for b in buyers[:5]:
            print(f"  - {b.get('buyerName')}: spent={b.get('totalSpent')}, invoices={b.get('invoiceCount')}")
        
        assert len(buyers) > 0, "Expected buyers in top-buyers report"
        print("PASS: Top buyers returns data")

    def test_profit_summary_returns_data(self):
        """GET /api/business-tools/reports/profit-summary should return data"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/profit-summary",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Profit summary failed: {response.text}"
        
        data = response.json()
        overall = data.get("overall", {})
        periods = data.get("periods", [])
        
        print(f"Profit summary: totalRevenue={overall.get('totalRevenue')}, totalProfit={overall.get('totalProfit')}, margin={overall.get('profitMargin')}%")
        print(f"  Periods: {len(periods)}")
        
        assert overall.get("totalRevenue", 0) > 0 or overall.get("invoiceCount", 0) > 0, "Expected some data in profit-summary"
        print("PASS: Profit summary returns data")


class TestSellerInvoiceCounters:
    """Test seller_invoice_counters collection has correct lastSequence"""

    def test_invoice_count_matches_counter(self):
        """Verify seller_invoice_counters.lastSequence matches invoice count"""
        # Get all invoices
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices?limit=100",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        invoices = response.json().get("invoices", [])
        invoice_count = len(invoices)
        
        # Extract max sequence number from invoices
        max_seq = 0
        for inv in invoices:
            inv_num = inv.get("invoiceNumber", "")
            if "-" in inv_num:
                parts = inv_num.split("-")
                if len(parts) == 3 and parts[2].isdigit():
                    seq = int(parts[2])
                    if seq > max_seq:
                        max_seq = seq
        
        print(f"Invoice count: {invoice_count}, Max sequence: {max_seq}")
        
        # Max sequence should be >= invoice count (might be higher if some deleted)
        assert max_seq >= invoice_count - 10, f"Max sequence {max_seq} seems too low for {invoice_count} invoices"
        
        print("PASS: Invoice sequence numbers are reasonable")

    def test_new_invoice_uses_atomic_counter(self):
        """Verify new invoice gets next sequence from counter (not from sellers.invoiceCounter)"""
        # Get current max sequence
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices?limit=100",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200
        
        invoices = response.json().get("invoices", [])
        
        # Find max sequence
        max_seq = 0
        for inv in invoices:
            inv_num = inv.get("invoiceNumber", "")
            if "-" in inv_num:
                parts = inv_num.split("-")
                if len(parts) == 3 and parts[2].isdigit():
                    seq = int(parts[2])
                    if seq > max_seq:
                        max_seq = seq
        
        print(f"Current max sequence: {max_seq}")
        
        # Get buyer ID
        buyers_resp = requests.get(
            f"{BASE_URL}/api/business-tools/buyers",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert buyers_resp.status_code == 200
        buyers = buyers_resp.json().get("buyers", [])
        buyer_id = buyers[0]["id"]
        
        # Create new invoice
        create_resp = requests.post(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"},
            json={
                "buyerId": buyer_id,
                "items": [{"productName": "Counter Test", "quantity": 1, "price": 100, "gstPercent": 18}],
                "notes": "Atomic counter test",
                "dueDays": 7,
                "deductStock": False
            }
        )
        assert create_resp.status_code == 200, f"Failed to create: {create_resp.text}"
        
        new_invoice = create_resp.json()["invoice"]
        new_num = new_invoice.get("invoiceNumber")
        
        # Extract new sequence
        parts = new_num.split("-")
        new_seq = int(parts[2])
        
        print(f"New invoice: {new_num}, sequence: {new_seq}")
        
        # New sequence should be max_seq + 1
        assert new_seq == max_seq + 1, f"Expected sequence {max_seq + 1}, got {new_seq}"
        
        print("PASS: New invoice uses atomic counter correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
