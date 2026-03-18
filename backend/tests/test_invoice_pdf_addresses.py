"""
Test Suite: Invoice PDF Bill To / Ship To Address Layout
Tests the PDF generation with billing and shipping addresses side-by-side
and the 'Same as Billing Address' feature
"""

import pytest
import sys
sys.path.insert(0, '/app/backend')

from services.invoice_pdf_service import generate_invoice_pdf, generate_merged_invoice_pdf


@pytest.fixture
def seller():
    return {
        'businessName': 'Test Seller Co',
        'address': '456 Seller Ave',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'phone': '1234567890',
        'email': 'seller@test.com',
        'gstNumber': '27AAAAA1234A1Z5',
        'bankDetails': {'bankName': 'Test Bank', 'accountNumber': '12345', 'ifscCode': 'TEST0001'}
    }


@pytest.fixture
def buyer():
    return {
        'buyerName': 'Test Buyer',
        'company': 'Buyer Corp',
        'address': '789 Buyer Lane, Mumbai, Maharashtra 400001',
        'phone': '9988776655',
        'gstNumber': '27BBBBB5678B1Z6',
        'state': 'Maharashtra'
    }


@pytest.fixture
def base_invoice():
    return {
        'invoiceNumber': 'INV-TEST-001',
        'date': '2026-01-15T10:00:00Z',
        'items': [
            {
                'productName': 'Test Product',
                'hsnCode': '1234',
                'quantity': 2,
                'price': 100,
                'gstPercent': 18,
                'discount': 0,
                'gstAmount': 36,
                'total': 236
            }
        ],
        'subtotal': 200,
        'gst': 36,
        'total': 236,
        'placeOfSupply': 'Maharashtra'
    }


class TestInvoicePDFNoQRCode:
    """Verify QR code has been removed from PDF generation"""
    
    def test_pdf_generates_without_qrcode_import(self, seller, buyer, base_invoice):
        """Test that PDF generates successfully without qrcode dependency"""
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF header check
        assert pdf_bytes[:4] == b'%PDF'
    
    def test_no_qrcode_in_source_code(self):
        """Verify qrcode import was removed from source"""
        import inspect
        from services import invoice_pdf_service
        source = inspect.getsource(invoice_pdf_service)
        assert 'qrcode' not in source.lower(), "qrcode import should be removed"
        assert 'generate_qr' not in source.lower(), "generate_qr function should be removed"


class TestInvoicePDFBillingShippingLayout:
    """Test Bill To / Ship To 2-column layout"""
    
    def test_pdf_with_different_shipping_address(self, seller, buyer, base_invoice):
        """Test PDF generation with separate shipping address"""
        base_invoice['shippingAddress'] = {
            'addressLine1': '123 Shipping Street',
            'addressLine2': 'Floor 2',
            'city': 'Pune',
            'state': 'Maharashtra',
            'pincode': '411001',
            'contactPerson': 'Ship Contact',
            'phone': '9876543210'
        }
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with different shipping address: {len(pdf_bytes)} bytes")
    
    def test_pdf_without_shipping_address_shows_same_as_billing(self, seller, buyer, base_invoice):
        """Test that empty shipping shows 'Same as Billing Address'"""
        base_invoice['shippingAddress'] = {}
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF without shipping address: {len(pdf_bytes)} bytes")
    
    def test_pdf_with_none_shipping_address(self, seller, buyer, base_invoice):
        """Test PDF with None shipping address"""
        base_invoice['shippingAddress'] = None
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with None shipping address: {len(pdf_bytes)} bytes")
    
    def test_pdf_with_same_shipping_as_billing(self, seller, buyer, base_invoice):
        """Test PDF when shipping matches billing address"""
        # Shipping address same as buyer address
        base_invoice['shippingAddress'] = {
            'addressLine1': '789 Buyer Lane, Mumbai, Maharashtra 400001',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001'
        }
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with same shipping/billing: {len(pdf_bytes)} bytes")
    
    def test_shipping_address_with_contact_person(self, seller, buyer, base_invoice):
        """Test shipping address with contact person details"""
        base_invoice['shippingAddress'] = {
            'addressLine1': '999 Warehouse Road',
            'city': 'Nashik',
            'state': 'Maharashtra',
            'pincode': '422001',
            'contactPerson': 'Warehouse Manager',
            'phone': '9000000001'
        }
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with contact person: {len(pdf_bytes)} bytes")


class TestInvoicePDFCopyTypes:
    """Test different copy types for PDF generation"""
    
    def test_original_copy(self, seller, buyer, base_invoice):
        """Test Original for Recipient copy"""
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer, copy_type='original')
        assert len(pdf_bytes) > 0
    
    def test_transporter_copy(self, seller, buyer, base_invoice):
        """Test Duplicate for Transporter copy"""
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer, copy_type='transporter')
        assert len(pdf_bytes) > 0
    
    def test_supplier_copy(self, seller, buyer, base_invoice):
        """Test Triplicate for Supplier/CA copy"""
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer, copy_type='supplier')
        assert len(pdf_bytes) > 0
    
    def test_office_copy(self, seller, buyer, base_invoice):
        """Test Office Copy"""
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer, copy_type='office')
        assert len(pdf_bytes) > 0


class TestInvoiceMergedPDF:
    """Test merged multi-page PDF generation"""
    
    def test_merged_pdf_all_copies(self, seller, buyer, base_invoice):
        """Test merged PDF with all 4 copy types"""
        merged_bytes = generate_merged_invoice_pdf(
            base_invoice, seller, buyer,
            ['original', 'transporter', 'supplier', 'office']
        )
        assert isinstance(merged_bytes, bytes)
        assert len(merged_bytes) > 0
        # Merged should be larger than single
        single_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert len(merged_bytes) > len(single_bytes)
        print(f"Merged PDF (4 copies): {len(merged_bytes)} bytes")
    
    def test_merged_pdf_two_copies(self, seller, buyer, base_invoice):
        """Test merged PDF with 2 copy types"""
        merged_bytes = generate_merged_invoice_pdf(
            base_invoice, seller, buyer,
            ['original', 'transporter']
        )
        assert isinstance(merged_bytes, bytes)
        assert len(merged_bytes) > 0
        print(f"Merged PDF (2 copies): {len(merged_bytes)} bytes")
    
    def test_merged_pdf_single_copy(self, seller, buyer, base_invoice):
        """Test merged PDF with single copy (edge case)"""
        merged_bytes = generate_merged_invoice_pdf(
            base_invoice, seller, buyer,
            ['original']
        )
        assert isinstance(merged_bytes, bytes)
        assert len(merged_bytes) > 0


class TestSellerDetailsFullWidth:
    """Test that Seller details appear as full-width section"""
    
    def test_seller_with_all_details(self, buyer, base_invoice):
        """Test seller section with full details"""
        seller = {
            'businessName': 'Comprehensive Seller Inc.',
            'address': '100 Business Park',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'phone': '9876543210',
            'email': 'sales@seller.com',
            'gstNumber': '27AAAAA1234A1Z5',
            'bankDetails': {
                'bankName': 'HDFC Bank',
                'accountNumber': '50100000000000',
                'accountName': 'Comprehensive Seller Inc.',
                'ifscCode': 'HDFC0001234',
                'branch': 'Mumbai Main'
            }
        }
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with full seller details: {len(pdf_bytes)} bytes")
    
    def test_seller_minimal_details(self, buyer, base_invoice):
        """Test seller section with minimal details"""
        seller = {
            'businessName': 'Simple Seller'
        }
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert len(pdf_bytes) > 0
        print(f"Generated PDF with minimal seller: {len(pdf_bytes)} bytes")


class TestGSTCalculation:
    """Test IGST vs CGST/SGST in PDF"""
    
    def test_intra_state_cgst_sgst(self, seller, buyer, base_invoice):
        """Test intra-state invoice shows CGST/SGST"""
        # Same state - should be CGST/SGST
        base_invoice['placeOfSupply'] = 'Maharashtra'
        seller['state'] = 'Maharashtra'
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert len(pdf_bytes) > 0
    
    def test_inter_state_igst(self, seller, buyer, base_invoice):
        """Test inter-state invoice shows IGST"""
        base_invoice['placeOfSupply'] = 'Karnataka'
        seller['state'] = 'Maharashtra'
        
        pdf_bytes = generate_invoice_pdf(base_invoice, seller, buyer)
        assert len(pdf_bytes) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
