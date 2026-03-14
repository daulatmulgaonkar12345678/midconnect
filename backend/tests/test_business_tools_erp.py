"""
Business Tools ERP Backend Tests
- Composite Products CRUD + Sell with stock deduction
- Invoices CRUD + PDF generation + per-item GST calculation
- Reports: sales summary, product sales, inventory status, top buyers
- Activity Logs with module filter

Tests use dev-test-token for authentication (MOCKED Firebase Auth in dev mode)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}
BUYER_ID = "69b55383a39abdd1ea3cd68e"  # Test Buyer from context


class TestHealthAndSetup:
    """Basic health check before running ERP tests"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health check passed")


# ===========================================
# COMPOSITE PRODUCTS TESTS
# ===========================================

class TestCompositeProductsCRUD:
    """Test composite products CRUD operations"""
    
    def test_list_composite_products(self):
        """GET /api/business-tools/composite-products - list all composite products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/composite-products", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list composite products: {response.text}"
        data = response.json()
        assert "compositeProducts" in data
        print(f"✓ Listed {len(data['compositeProducts'])} composite products")
    
    def test_list_composite_products_requires_auth(self):
        """Composite products requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/composite-products")
        assert response.status_code == 422 or response.status_code == 401, "Should require auth"
        print("✓ Composite products requires auth")
    
    def test_create_composite_product_requires_valid_listings(self):
        """POST - creating composite product requires valid seller listings"""
        # Try to create with non-existent product IDs
        payload = {
            "name": "TEST_Invalid_Composite",
            "description": "Test composite with invalid products",
            "items": [
                {"productId": "000000000000000000000000", "quantity": 1}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/composite-products", json=payload, headers=AUTH_HEADER)
        # Should fail with 400 because listing doesn't exist
        assert response.status_code == 400, f"Expected 400 for invalid productId, got {response.status_code}: {response.text}"
        print("✓ Create composite product validates listings exist")
    
    def test_update_nonexistent_composite_product(self):
        """PUT - updating non-existent composite product returns 404"""
        payload = {"name": "Updated Name"}
        response = requests.put(f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent composite, got {response.status_code}"
        print("✓ Update non-existent composite returns 404")
    
    def test_delete_nonexistent_composite_product(self):
        """DELETE - deleting non-existent composite product returns 404"""
        response = requests.delete(f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000", headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent composite, got {response.status_code}"
        print("✓ Delete non-existent composite returns 404")
    
    def test_sell_nonexistent_composite_product(self):
        """POST /sell - selling non-existent composite product returns 404"""
        payload = {"quantity": 1}
        response = requests.post(f"{BASE_URL}/api/business-tools/composite-products/000000000000000000000000/sell", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent composite, got {response.status_code}"
        print("✓ Sell non-existent composite returns 404")


# ===========================================
# INVOICE TESTS
# ===========================================

class TestInvoiceCRUD:
    """Test invoice CRUD operations"""
    
    def test_list_invoices(self):
        """GET /api/business-tools/invoices - list all invoices"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list invoices: {response.text}"
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        print(f"✓ Listed invoices, total: {data['total']}")
        return data
    
    def test_list_invoices_with_status_filter(self):
        """GET /api/business-tools/invoices?status=draft - filter by status"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices?status=draft", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to filter invoices: {response.text}"
        data = response.json()
        for inv in data.get("invoices", []):
            assert inv.get("status") == "draft", f"Invoice {inv.get('invoiceNumber')} has status {inv.get('status')}, expected draft"
        print(f"✓ Filtered invoices by status=draft")
    
    def test_list_invoices_requires_auth(self):
        """Invoices requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices")
        assert response.status_code == 422 or response.status_code == 401, "Should require auth"
        print("✓ Invoices requires auth")
    
    def test_create_invoice_with_gst_calculation(self):
        """POST /api/business-tools/invoices - create invoice with per-item GST"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [
                {"productName": f"TEST_Product_{unique_id}_A", "quantity": 2, "price": 1000.0, "gstPercent": 18},
                {"productName": f"TEST_Product_{unique_id}_B", "quantity": 1, "price": 500.0, "gstPercent": 12}
            ],
            "notes": f"Test invoice {unique_id}",
            "deductStock": False  # Don't try to deduct stock since we may not have listings
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to create invoice: {response.text}"
        data = response.json()
        invoice = data.get("invoice", {})
        
        # Verify invoice number format: INV-{sellerId_suffix}-{sequence}
        inv_number = invoice.get("invoiceNumber", "")
        assert inv_number.startswith("INV-"), f"Invoice number should start with INV-, got {inv_number}"
        parts = inv_number.split("-")
        assert len(parts) == 3, f"Invoice number format should be INV-XXXXXX-YYYY, got {inv_number}"
        print(f"✓ Invoice number format correct: {inv_number}")
        
        # Verify per-item GST calculation
        items = invoice.get("items", [])
        assert len(items) == 2, f"Expected 2 items, got {len(items)}"
        
        # Item A: price 1000, qty 2, gst 18%
        # line_subtotal = 1000 * 2 = 2000
        # gst_amount = 2000 * 18 / 100 = 360
        # total = 2000 + 360 = 2360
        item_a = items[0]
        assert item_a.get("gstPercent") == 18, f"Item A gstPercent should be 18, got {item_a.get('gstPercent')}"
        assert item_a.get("gstAmount") == 360.0, f"Item A gstAmount should be 360, got {item_a.get('gstAmount')}"
        assert item_a.get("total") == 2360.0, f"Item A total should be 2360, got {item_a.get('total')}"
        print(f"✓ Item A GST calculation correct: gstAmount={item_a.get('gstAmount')}, total={item_a.get('total')}")
        
        # Item B: price 500, qty 1, gst 12%
        # line_subtotal = 500 * 1 = 500
        # gst_amount = 500 * 12 / 100 = 60
        # total = 500 + 60 = 560
        item_b = items[1]
        assert item_b.get("gstPercent") == 12, f"Item B gstPercent should be 12, got {item_b.get('gstPercent')}"
        assert item_b.get("gstAmount") == 60.0, f"Item B gstAmount should be 60, got {item_b.get('gstAmount')}"
        assert item_b.get("total") == 560.0, f"Item B total should be 560, got {item_b.get('total')}"
        print(f"✓ Item B GST calculation correct: gstAmount={item_b.get('gstAmount')}, total={item_b.get('total')}")
        
        # Verify invoice totals
        # subtotal = 2000 + 500 = 2500
        # gst = 360 + 60 = 420
        # grand_total = 2500 + 420 = 2920
        assert invoice.get("subtotal") == 2500.0, f"Subtotal should be 2500, got {invoice.get('subtotal')}"
        assert invoice.get("gst") == 420.0, f"GST should be 420, got {invoice.get('gst')}"
        assert invoice.get("total") == 2920.0, f"Total should be 2920, got {invoice.get('total')}"
        print(f"✓ Invoice totals correct: subtotal={invoice.get('subtotal')}, gst={invoice.get('gst')}, total={invoice.get('total')}")
        
        return invoice
    
    def test_create_invoice_with_invalid_buyer(self):
        """POST - creating invoice with invalid buyer returns 400"""
        payload = {
            "buyerId": "000000000000000000000000",
            "items": [{"productName": "Test", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for invalid buyer, got {response.status_code}: {response.text}"
        print("✓ Create invoice validates buyer exists")
    
    def test_get_single_invoice(self):
        """GET /api/business-tools/invoices/{id} - get single invoice"""
        # First get list and find an invoice
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test GET single")
        
        invoice_id = invoices[0].get("id")
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get invoice: {response.text}"
        data = response.json()
        assert "invoice" in data
        assert data["invoice"].get("id") == invoice_id
        print(f"✓ Got single invoice: {data['invoice'].get('invoiceNumber')}")
    
    def test_get_nonexistent_invoice(self):
        """GET - getting non-existent invoice returns 404"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices/000000000000000000000000", headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent invoice, got {response.status_code}"
        print("✓ Get non-existent invoice returns 404")


class TestInvoiceStatusUpdate:
    """Test invoice status transitions"""
    
    def test_update_invoice_status_to_sent(self):
        """PUT /api/business-tools/invoices/{id}/status - update to sent"""
        # Get a draft invoice
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices?status=draft", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No draft invoices to test status update")
        
        invoice_id = invoices[0].get("id")
        payload = {"status": "sent"}
        response = requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        print(f"✓ Updated invoice status to sent")
        
        # Revert back to draft for other tests
        revert_payload = {"status": "draft"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=revert_payload, headers=AUTH_HEADER)
    
    def test_update_invoice_status_to_paid(self):
        """PUT - update status to paid"""
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test status update")
        
        invoice_id = invoices[0].get("id")
        payload = {"status": "paid"}
        response = requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        print(f"✓ Updated invoice status to paid")
        
        # Revert back to draft
        revert_payload = {"status": "draft"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=revert_payload, headers=AUTH_HEADER)
    
    def test_update_invoice_status_to_cancelled(self):
        """PUT - update status to cancelled"""
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test status update")
        
        invoice_id = invoices[0].get("id")
        payload = {"status": "cancelled"}
        response = requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        print(f"✓ Updated invoice status to cancelled")
        
        # Revert back to draft
        revert_payload = {"status": "draft"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=revert_payload, headers=AUTH_HEADER)
    
    def test_update_invoice_status_invalid(self):
        """PUT - invalid status returns 400"""
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test status update")
        
        invoice_id = invoices[0].get("id")
        payload = {"status": "invalid_status"}
        response = requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for invalid status, got {response.status_code}"
        print("✓ Invalid status returns 400")
    
    def test_update_nonexistent_invoice_status(self):
        """PUT - updating non-existent invoice returns 404"""
        payload = {"status": "sent"}
        response = requests.put(f"{BASE_URL}/api/business-tools/invoices/000000000000000000000000/status", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent invoice, got {response.status_code}"
        print("✓ Update non-existent invoice status returns 404")


class TestInvoicePDF:
    """Test PDF generation"""
    
    def test_get_invoice_pdf(self):
        """GET /api/business-tools/invoices/{id}/pdf - download PDF"""
        # Get an invoice
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test PDF generation")
        
        invoice_id = invoices[0].get("id")
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/pdf", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get PDF: {response.text}"
        
        # Verify content-type is application/pdf
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        print("✓ PDF content-type is application/pdf")
        
        # Verify PDF bytes start with %PDF-
        content = response.content
        assert content.startswith(b"%PDF-"), f"PDF content should start with %PDF-, got {content[:10]}"
        print(f"✓ PDF generated successfully, size: {len(content)} bytes")
    
    def test_get_pdf_nonexistent_invoice(self):
        """GET PDF for non-existent invoice returns 404"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices/000000000000000000000000/pdf", headers=AUTH_HEADER)
        assert response.status_code == 404, f"Expected 404 for non-existent invoice PDF, got {response.status_code}"
        print("✓ Get PDF for non-existent invoice returns 404")


class TestInvoiceDelete:
    """Test invoice deletion rules - only draft/cancelled can be deleted"""
    
    def test_delete_draft_invoice(self):
        """DELETE /api/business-tools/invoices/{id} - delete draft invoice"""
        # Create a new draft invoice to delete
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Delete_{unique_id}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert create_response.status_code == 200
        invoice_id = create_response.json().get("invoice", {}).get("id")
        
        # Delete the draft invoice
        response = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to delete draft invoice: {response.text}"
        print("✓ Deleted draft invoice successfully")
        
        # Verify invoice is gone
        get_response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert get_response.status_code == 404, "Invoice should not exist after deletion"
        print("✓ Verified invoice deleted")
    
    def test_delete_cancelled_invoice(self):
        """DELETE - delete cancelled invoice succeeds"""
        # Create and cancel an invoice
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Cancel_{unique_id}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert create_response.status_code == 200
        invoice_id = create_response.json().get("invoice", {}).get("id")
        
        # Cancel the invoice
        status_payload = {"status": "cancelled"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=status_payload, headers=AUTH_HEADER)
        
        # Delete the cancelled invoice
        response = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to delete cancelled invoice: {response.text}"
        print("✓ Deleted cancelled invoice successfully")
    
    def test_delete_sent_invoice_fails(self):
        """DELETE - cannot delete sent invoice"""
        # Create an invoice and mark as sent
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Sent_{unique_id}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert create_response.status_code == 200
        invoice_id = create_response.json().get("invoice", {}).get("id")
        
        # Mark as sent
        status_payload = {"status": "sent"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=status_payload, headers=AUTH_HEADER)
        
        # Try to delete - should fail
        response = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for deleting sent invoice, got {response.status_code}"
        print("✓ Cannot delete sent invoice (returns 400)")
        
        # Cleanup: cancel and delete
        cancel_payload = {"status": "cancelled"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=cancel_payload, headers=AUTH_HEADER)
        requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
    
    def test_delete_paid_invoice_fails(self):
        """DELETE - cannot delete paid invoice"""
        # Create an invoice and mark as paid
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Paid_{unique_id}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert create_response.status_code == 200
        invoice_id = create_response.json().get("invoice", {}).get("id")
        
        # Mark as paid
        status_payload = {"status": "paid"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=status_payload, headers=AUTH_HEADER)
        
        # Try to delete - should fail
        response = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)
        assert response.status_code == 400, f"Expected 400 for deleting paid invoice, got {response.status_code}"
        print("✓ Cannot delete paid invoice (returns 400)")
        
        # Cleanup: cancel and delete
        cancel_payload = {"status": "cancelled"}
        requests.put(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/status", json=cancel_payload, headers=AUTH_HEADER)
        requests.delete(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=AUTH_HEADER)


class TestInvoiceNumberAutoIncrement:
    """Test invoice numbering auto-increments"""
    
    def test_invoice_number_increments(self):
        """Verify invoice numbers auto-increment"""
        # Create first invoice
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Inc1_{unique_id}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        response1 = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload, headers=AUTH_HEADER)
        assert response1.status_code == 200
        inv1 = response1.json().get("invoice", {})
        inv_num1 = inv1.get("invoiceNumber", "")
        
        # Create second invoice
        unique_id2 = str(uuid.uuid4())[:8]
        payload2 = {
            "buyerId": BUYER_ID,
            "items": [{"productName": f"TEST_Inc2_{unique_id2}", "quantity": 1, "price": 100, "gstPercent": 0}],
            "deductStock": False
        }
        response2 = requests.post(f"{BASE_URL}/api/business-tools/invoices", json=payload2, headers=AUTH_HEADER)
        assert response2.status_code == 200
        inv2 = response2.json().get("invoice", {})
        inv_num2 = inv2.get("invoiceNumber", "")
        
        # Extract sequence numbers
        seq1 = int(inv_num1.split("-")[-1])
        seq2 = int(inv_num2.split("-")[-1])
        
        assert seq2 == seq1 + 1, f"Invoice numbers should increment: {inv_num1} -> {inv_num2}"
        print(f"✓ Invoice numbers auto-increment: {inv_num1} -> {inv_num2}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/business-tools/invoices/{inv1.get('id')}", headers=AUTH_HEADER)
        requests.delete(f"{BASE_URL}/api/business-tools/invoices/{inv2.get('id')}", headers=AUTH_HEADER)


# ===========================================
# REPORTS TESTS
# ===========================================

class TestReportsSalesSummary:
    """Test sales summary report"""
    
    def test_sales_summary_monthly(self):
        """GET /api/business-tools/reports/sales-summary - monthly view"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/sales-summary?period=monthly", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get sales summary: {response.text}"
        data = response.json()
        
        assert "overall" in data, "Response should have 'overall' field"
        assert "periods" in data, "Response should have 'periods' field"
        
        overall = data.get("overall", {})
        assert "totalRevenue" in overall, "Overall should have totalRevenue"
        assert "totalGst" in overall, "Overall should have totalGst"
        assert "invoiceCount" in overall, "Overall should have invoiceCount"
        print(f"✓ Sales summary monthly: totalRevenue={overall.get('totalRevenue')}, invoiceCount={overall.get('invoiceCount')}")
    
    def test_sales_summary_quarterly(self):
        """GET /api/business-tools/reports/sales-summary?period=quarterly"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/sales-summary?period=quarterly", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get quarterly summary: {response.text}"
        data = response.json()
        
        for period in data.get("periods", []):
            assert "quarter" in period, "Quarterly periods should have 'quarter' field"
            assert "label" in period, "Period should have label"
            assert period["label"].startswith("Q"), f"Quarterly label should start with Q, got {period['label']}"
        print("✓ Sales summary quarterly format correct")
    
    def test_sales_summary_with_date_range(self):
        """GET - sales summary with date filters"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/sales-summary?startDate=2024-01-01T00:00:00Z&endDate=2026-12-31T23:59:59Z", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with date range: {response.text}"
        print("✓ Sales summary with date range works")
    
    def test_sales_summary_requires_auth(self):
        """Sales summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/sales-summary")
        assert response.status_code == 422 or response.status_code == 401, "Should require auth"
        print("✓ Sales summary requires auth")


class TestReportsProductSales:
    """Test product sales report"""
    
    def test_product_sales(self):
        """GET /api/business-tools/reports/product-sales - top selling products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/product-sales", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get product sales: {response.text}"
        data = response.json()
        
        assert "products" in data, "Response should have 'products' field"
        for product in data.get("products", []):
            assert "productName" in product, "Product should have productName"
            assert "totalQuantity" in product, "Product should have totalQuantity"
            assert "totalRevenue" in product, "Product should have totalRevenue"
        print(f"✓ Product sales report: {len(data.get('products', []))} products")
    
    def test_product_sales_with_limit(self):
        """GET - product sales with limit"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/product-sales?limit=5", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with limit: {response.text}"
        data = response.json()
        assert len(data.get("products", [])) <= 5, "Should respect limit"
        print("✓ Product sales with limit works")


class TestReportsInventoryStatus:
    """Test inventory status report"""
    
    def test_inventory_status(self):
        """GET /api/business-tools/reports/inventory-status"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/inventory-status", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get inventory status: {response.text}"
        data = response.json()
        
        assert "summary" in data, "Response should have 'summary' field"
        assert "items" in data, "Response should have 'items' field"
        
        summary = data.get("summary", {})
        assert "totalItems" in summary, "Summary should have totalItems"
        assert "lowStock" in summary, "Summary should have lowStock"
        assert "outOfStock" in summary, "Summary should have outOfStock"
        assert "totalStockUnits" in summary, "Summary should have totalStockUnits"
        print(f"✓ Inventory status: totalItems={summary.get('totalItems')}, lowStock={summary.get('lowStock')}, outOfStock={summary.get('outOfStock')}")


class TestReportsTopBuyers:
    """Test top buyers report"""
    
    def test_top_buyers(self):
        """GET /api/business-tools/reports/top-buyers"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/top-buyers", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to get top buyers: {response.text}"
        data = response.json()
        
        assert "buyers" in data, "Response should have 'buyers' field"
        for buyer in data.get("buyers", []):
            assert "buyerId" in buyer, "Buyer should have buyerId"
            assert "buyerName" in buyer, "Buyer should have buyerName"
            assert "totalSpent" in buyer, "Buyer should have totalSpent"
            assert "invoiceCount" in buyer, "Buyer should have invoiceCount"
        print(f"✓ Top buyers report: {len(data.get('buyers', []))} buyers")
    
    def test_top_buyers_with_limit(self):
        """GET - top buyers with limit"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports/top-buyers?limit=3", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with limit: {response.text}"
        data = response.json()
        assert len(data.get("buyers", [])) <= 3, "Should respect limit"
        print("✓ Top buyers with limit works")


# ===========================================
# ACTIVITY LOGS TESTS
# ===========================================

class TestActivityLogs:
    """Test activity logs endpoint"""
    
    def test_list_activity_logs(self):
        """GET /api/business-tools/activity-logs - list all logs"""
        response = requests.get(f"{BASE_URL}/api/business-tools/activity-logs", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed to list activity logs: {response.text}"
        data = response.json()
        
        assert "logs" in data, "Response should have 'logs' field"
        assert "total" in data, "Response should have 'total' field"
        
        for log in data.get("logs", []):
            assert "action" in log, "Log should have action"
            assert "module" in log, "Log should have module"
            assert "timestamp" in log, "Log should have timestamp"
        print(f"✓ Activity logs: {data.get('total')} total, showing {len(data.get('logs', []))}")
    
    def test_activity_logs_with_module_filter(self):
        """GET - activity logs filtered by module"""
        response = requests.get(f"{BASE_URL}/api/business-tools/activity-logs?module=invoices", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with module filter: {response.text}"
        data = response.json()
        
        for log in data.get("logs", []):
            assert log.get("module") == "invoices", f"Log module should be invoices, got {log.get('module')}"
        print("✓ Activity logs module filter works")
    
    def test_activity_logs_with_action_filter(self):
        """GET - activity logs filtered by action"""
        response = requests.get(f"{BASE_URL}/api/business-tools/activity-logs?action=invoice_created", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with action filter: {response.text}"
        data = response.json()
        
        for log in data.get("logs", []):
            assert log.get("action") == "invoice_created", f"Log action should be invoice_created, got {log.get('action')}"
        print("✓ Activity logs action filter works")
    
    def test_activity_logs_pagination(self):
        """GET - activity logs with pagination"""
        response = requests.get(f"{BASE_URL}/api/business-tools/activity-logs?limit=5&skip=0", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Failed with pagination: {response.text}"
        data = response.json()
        assert len(data.get("logs", [])) <= 5, "Should respect limit"
        print("✓ Activity logs pagination works")


# ===========================================
# CLEANUP TESTS
# ===========================================

class TestCleanup:
    """Cleanup TEST_ prefixed data created during testing"""
    
    def test_cleanup_test_invoices(self):
        """Delete TEST_ prefixed invoices"""
        list_response = requests.get(f"{BASE_URL}/api/business-tools/invoices?limit=100", headers=AUTH_HEADER)
        invoices = list_response.json().get("invoices", [])
        
        deleted = 0
        for inv in invoices:
            items = inv.get("items", [])
            for item in items:
                if item.get("productName", "").startswith("TEST_"):
                    # Cancel first if not draft/cancelled
                    if inv.get("status") not in ["draft", "cancelled"]:
                        requests.put(
                            f"{BASE_URL}/api/business-tools/invoices/{inv.get('id')}/status",
                            json={"status": "cancelled"},
                            headers=AUTH_HEADER
                        )
                    # Delete
                    del_response = requests.delete(f"{BASE_URL}/api/business-tools/invoices/{inv.get('id')}", headers=AUTH_HEADER)
                    if del_response.status_code == 200:
                        deleted += 1
                    break
        
        print(f"✓ Cleaned up {deleted} test invoices")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
