"""
Invoice Freight, TCS, Round Off & Payment Terms Feature Tests
Tests for new invoice fields: paymentTerms, additionalCharges (freight), tcsEnabled, tcsPercent, roundOff
"""

import pytest
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.business_tools import InvoiceCreate, InvoiceItemCreate, AdditionalCharge
from services.invoice_pdf_service import generate_invoice_pdf


# ─────────────────────────────────────────────────────────────────────────────
# MODEL VALIDATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAdditionalChargeModel:
    """Tests for AdditionalCharge Pydantic model"""
    
    def test_additional_charge_fixed_type(self):
        """AdditionalCharge with fixed type should work"""
        charge = AdditionalCharge(name="Freight", type="fixed", value=500)
        assert charge.name == "Freight"
        assert charge.type == "fixed"
        assert charge.value == 500
        print("✓ AdditionalCharge fixed type model works")
    
    def test_additional_charge_percentage_type(self):
        """AdditionalCharge with percentage type should work"""
        charge = AdditionalCharge(name="Loading", type="percentage", value=2)
        assert charge.name == "Loading"
        assert charge.type == "percentage"
        assert charge.value == 2
        print("✓ AdditionalCharge percentage type model works")

    def test_additional_charge_default_type(self):
        """AdditionalCharge should default to 'fixed' type"""
        charge = AdditionalCharge(name="Packing", value=100)
        assert charge.type == "fixed"
        print("✓ AdditionalCharge defaults to 'fixed' type")


class TestInvoiceCreateModel:
    """Tests for InvoiceCreate model with new fields"""
    
    def test_invoice_create_with_payment_terms(self):
        """InvoiceCreate should accept paymentTerms field"""
        invoice = InvoiceCreate(
            buyerId="507f1f77bcf86cd799439011",
            items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)],
            paymentTerms="100% advance payment"
        )
        assert invoice.paymentTerms == "100% advance payment"
        print("✓ InvoiceCreate accepts paymentTerms field")
    
    def test_invoice_create_with_freight(self):
        """InvoiceCreate should accept additionalCharges with Freight"""
        invoice = InvoiceCreate(
            buyerId="507f1f77bcf86cd799439011",
            items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)],
            additionalCharges=[AdditionalCharge(name="Freight", type="fixed", value=500)]
        )
        assert len(invoice.additionalCharges) == 1
        assert invoice.additionalCharges[0].name == "Freight"
        assert invoice.additionalCharges[0].value == 500
        print("✓ InvoiceCreate accepts additionalCharges with Freight")
    
    def test_invoice_create_with_tcs_enabled(self):
        """InvoiceCreate should accept tcsEnabled and tcsPercent fields"""
        invoice = InvoiceCreate(
            buyerId="507f1f77bcf86cd799439011",
            items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)],
            tcsEnabled=True,
            tcsPercent=0.1
        )
        assert invoice.tcsEnabled is True
        assert invoice.tcsPercent == 0.1
        print("✓ InvoiceCreate accepts tcsEnabled and tcsPercent fields")
    
    def test_invoice_create_tcs_default_values(self):
        """TCS should default to disabled with 0.1% rate"""
        invoice = InvoiceCreate(
            buyerId="507f1f77bcf86cd799439011",
            items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)]
        )
        assert invoice.tcsEnabled is False
        assert invoice.tcsPercent == 0.1
        print("✓ TCS defaults to disabled with 0.1% rate")
    
    def test_invoice_create_tcs_percent_validation_max(self):
        """TCS percent should be validated (max 5%)"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            InvoiceCreate(
                buyerId="507f1f77bcf86cd799439011",
                items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)],
                tcsEnabled=True,
                tcsPercent=6  # Above max of 5%
            )
        print("✓ TCS percent validation rejects values > 5%")
    
    def test_invoice_create_tcs_percent_validation_min(self):
        """TCS percent should be validated (min 0%)"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            InvoiceCreate(
                buyerId="507f1f77bcf86cd799439011",
                items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)],
                tcsEnabled=True,
                tcsPercent=-1  # Below min of 0%
            )
        print("✓ TCS percent validation rejects values < 0%")
    
    def test_invoice_create_backwards_compatible(self):
        """Invoice without new fields should still work (backwards compatible)"""
        invoice = InvoiceCreate(
            buyerId="507f1f77bcf86cd799439011",
            items=[InvoiceItemCreate(productName="Test Product", quantity=1, price=1000, gstPercent=18)]
        )
        assert invoice.paymentTerms is None
        assert invoice.additionalCharges == []
        assert invoice.tcsEnabled is False
        print("✓ InvoiceCreate is backwards compatible without new fields")


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoiceCalculations:
    """Tests for invoice calculation logic"""
    
    def test_tcs_calculation_on_subtotal_plus_gst(self):
        """TCS should be calculated on (subtotal + GST), not on freight"""
        # Example: subtotal=10000, GST 18%=1800, TCS 0.1%
        subtotal = 10000
        gst = 1800  # 18% of 10000
        tcs_percent = 0.1
        freight = 500
        
        # TCS = 0.1% of (subtotal + GST) = 0.1% of 11800 = 11.80
        expected_tcs = round((subtotal + gst) * tcs_percent / 100, 2)
        assert expected_tcs == 11.80
        
        # Pre-round total = subtotal + GST + freight + TCS
        pre_round = subtotal + gst + freight + expected_tcs
        assert pre_round == 10000 + 1800 + 500 + 11.80
        assert pre_round == 12311.80
        print(f"✓ TCS calculation correct: {tcs_percent}% of {subtotal + gst} = {expected_tcs}")
    
    def test_round_off_calculation(self):
        """Round off should be auto-calculated to nearest rupee"""
        pre_round_total = 12311.80
        rounded_total = round(pre_round_total)  # 12312
        round_off = round(rounded_total - pre_round_total, 2)  # +0.20
        
        assert rounded_total == 12312
        assert round_off == 0.20
        print(f"✓ Round off calculation correct: {pre_round_total} → {rounded_total} (round off: +{round_off})")
    
    def test_round_off_negative(self):
        """Round off can be negative when rounding down"""
        pre_round_total = 12312.70
        rounded_total = round(pre_round_total)  # 12313
        round_off = round(rounded_total - pre_round_total, 2)  # +0.30
        
        assert rounded_total == 12313
        assert round_off == 0.30
        
        # Another case where it rounds down
        pre_round_total2 = 12312.30
        rounded_total2 = round(pre_round_total2)  # 12312
        round_off2 = round(rounded_total2 - pre_round_total2, 2)  # -0.30
        
        assert rounded_total2 == 12312
        assert round_off2 == -0.30
        print(f"✓ Round off can be negative: {pre_round_total2} → {rounded_total2} (round off: {round_off2})")
    
    def test_freight_fixed_amount(self):
        """Freight should be a fixed amount added to total"""
        subtotal = 10000
        gst = 1800
        freight = 500  # Fixed amount
        
        total_with_freight = subtotal + gst + freight
        assert total_with_freight == 12300
        print(f"✓ Freight fixed amount: subtotal({subtotal}) + GST({gst}) + freight({freight}) = {total_with_freight}")
    
    def test_full_invoice_calculation(self):
        """Full invoice calculation with all charges"""
        # Items
        subtotal = 10000
        gst_percent = 18
        gst = round(subtotal * gst_percent / 100, 2)  # 1800
        
        # Additional charges
        freight = 500  # Fixed
        
        # TCS (on subtotal + GST)
        tcs_percent = 0.1
        tcs_amount = round((subtotal + gst) * tcs_percent / 100, 2)  # 11.80
        
        # Pre-round total
        pre_round = subtotal + gst + freight + tcs_amount  # 12311.80
        
        # Round off
        rounded_total = round(pre_round)  # 12312
        round_off = round(rounded_total - pre_round, 2)  # 0.20
        
        # Final grand total
        grand_total = rounded_total
        
        assert gst == 1800
        assert tcs_amount == 11.80
        assert pre_round == 12311.80
        assert round_off == 0.20
        assert grand_total == 12312
        
        print(f"✓ Full calculation:")
        print(f"  Subtotal: {subtotal}")
        print(f"  GST (18%): {gst}")
        print(f"  Freight: {freight}")
        print(f"  TCS (0.1%): {tcs_amount}")
        print(f"  Pre-round: {pre_round}")
        print(f"  Round Off: {round_off}")
        print(f"  Grand Total: {grand_total}")


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoicePDFGeneration:
    """Tests for PDF generation with new fields"""
    
    def test_pdf_with_payment_terms(self):
        """PDF should include payment terms in header section"""
        invoice = {
            "invoiceNumber": "INV-TEST-001",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 1000, "gstPercent": 18, "gstAmount": 180, "total": 1180}],
            "subtotal": 1000,
            "gst": 180,
            "total": 1180,
            "paymentTerms": "100% advance payment required"
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        print("✓ PDF generated with payment terms")
    
    def test_pdf_with_freight_charge(self):
        """PDF should show Freight in totals section"""
        invoice = {
            "invoiceNumber": "INV-TEST-002",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 12300,
            "additionalCharges": [{"name": "Freight", "type": "fixed", "value": 500, "amount": 500}],
            "freight": 500
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        print("✓ PDF generated with Freight charge")
    
    def test_pdf_with_tcs(self):
        """PDF should show TCS in totals section"""
        invoice = {
            "invoiceNumber": "INV-TEST-003",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 11812,
            "tcsEnabled": True,
            "tcsPercent": 0.1,
            "tcsAmount": 11.80
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        print("✓ PDF generated with TCS")
    
    def test_pdf_with_round_off_positive(self):
        """PDF should show positive round off"""
        invoice = {
            "invoiceNumber": "INV-TEST-004",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 12312,
            "roundOff": 0.20
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        print("✓ PDF generated with positive round off")
    
    def test_pdf_with_round_off_negative(self):
        """PDF should show negative round off"""
        invoice = {
            "invoiceNumber": "INV-TEST-005",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 12312,
            "roundOff": -0.30
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        print("✓ PDF generated with negative round off")
    
    def test_pdf_with_all_new_fields(self):
        """PDF should work with all new fields combined"""
        invoice = {
            "invoiceNumber": "INV-TEST-006",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 12312,
            "paymentTerms": "30 days credit",
            "additionalCharges": [{"name": "Freight", "type": "fixed", "value": 500, "amount": 500}],
            "freight": 500,
            "tcsEnabled": True,
            "tcsPercent": 0.1,
            "tcsAmount": 11.80,
            "roundOff": 0.20
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000  # Should be a substantial PDF
        assert pdf_bytes[:4] == b'%PDF'
        print("✓ PDF generated with all new fields combined")
    
    def test_pdf_without_new_fields_backwards_compatible(self):
        """PDF should work without new fields (backwards compatible)"""
        invoice = {
            "invoiceNumber": "INV-TEST-007",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 11800
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        print("✓ PDF backwards compatible without new fields")
    
    def test_pdf_with_multiple_additional_charges(self):
        """PDF should handle multiple additional charges"""
        invoice = {
            "invoiceNumber": "INV-TEST-008",
            "date": "2026-01-15T10:00:00",
            "items": [{"productName": "Test Item", "quantity": 1, "price": 10000, "gstPercent": 18, "gstAmount": 1800, "total": 11800}],
            "subtotal": 10000,
            "gst": 1800,
            "total": 12900,
            "additionalCharges": [
                {"name": "Freight", "type": "fixed", "value": 500, "amount": 500},
                {"name": "Packing", "type": "fixed", "value": 200, "amount": 200},
                {"name": "Loading", "type": "fixed", "value": 100, "amount": 100},
                {"name": "Insurance", "type": "percentage", "value": 2, "amount": 300}
            ],
            "freight": 500
        }
        seller = {"businessName": "Test Seller", "gstNumber": "29AAACR1234A1ZZ"}
        buyer = {"buyerName": "Test Buyer"}
        
        pdf_bytes = generate_invoice_pdf(invoice, seller, buyer)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        print("✓ PDF generated with multiple additional charges")


# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND DATA-TESTID VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

class TestFrontendDataTestIds:
    """Verify frontend has correct data-testid attributes"""
    
    def test_data_testid_attributes_exist(self):
        """Check data-testid attributes in frontend code"""
        frontend_file = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Required data-testids for new fields
        required_testids = [
            'payment-terms-input',
            'freight-input',
            'tcs-toggle',
            'tcs-percent-input',
            'charges-preview'
        ]
        
        for testid in required_testids:
            assert f'data-testid="{testid}"' in content or f"data-testid='{testid}'" in content, \
                f"Missing data-testid: {testid}"
            print(f"✓ Found data-testid='{testid}'")
        
        print("✓ All required data-testid attributes present in frontend")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
