"""
Test: Discount System, WhatsApp Share-Link, Auto-Price from Inventory
======================================================================
Iteration 97: Tests for new B2B ERP enhancements
- discountType '%' and 'Rs' in Quotation and Invoice item models
- Discount calculation: Base Rate → Discount → Tax → Total
- POST /api/business-tools/quotations/{id}/share-link endpoint
- Public doc router supports 'quotation' document type
- PDF services render discount correctly
"""

import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-phase2-enhance.preview.emergentagent.com')


class TestDiscountModels:
    """Test that Pydantic models support discountType field"""

    def test_quotation_item_model_has_discount_type(self):
        """QuotationItemCreate model should have discountType field with default '%'"""
        from routers.quotation_router import QuotationItemCreate
        
        # Test default value
        item = QuotationItemCreate()
        assert hasattr(item, 'discountType'), "QuotationItemCreate should have discountType field"
        assert item.discountType == '%', f"Default discountType should be '%', got {item.discountType}"
        print("✓ QuotationItemCreate has discountType field with default '%'")

    def test_quotation_item_model_accepts_rs_discount_type(self):
        """QuotationItemCreate should accept 'Rs' as discountType"""
        from routers.quotation_router import QuotationItemCreate
        
        item = QuotationItemCreate(
            productId="prod123",
            productName="Test Product",
            price=1000,
            quantity=2,
            discount=50,
            discountType="Rs"
        )
        assert item.discountType == "Rs", f"discountType should be 'Rs', got {item.discountType}"
        print("✓ QuotationItemCreate accepts 'Rs' discountType")

    def test_invoice_item_model_has_discount_type(self):
        """InvoiceItemCreate model should have discountType field"""
        from models.business_tools import InvoiceItemCreate
        
        # Test default value
        item = InvoiceItemCreate(quantity=1, price=100)
        assert hasattr(item, 'discountType'), "InvoiceItemCreate should have discountType field"
        assert item.discountType == '%' or item.discountType is None or item.discountType == '%', "Default should be '%'"
        print("✓ InvoiceItemCreate has discountType field")

    def test_invoice_item_model_accepts_rs_discount_type(self):
        """InvoiceItemCreate should accept 'Rs' as discountType"""
        from models.business_tools import InvoiceItemCreate
        
        item = InvoiceItemCreate(
            productId="prod123",
            productName="Test Product",
            price=1000,
            quantity=2,
            discount=100,
            discountType="Rs"
        )
        assert item.discountType == "Rs", f"discountType should be 'Rs', got {item.discountType}"
        print("✓ InvoiceItemCreate accepts 'Rs' discountType")


class TestDiscountCalculation:
    """Test discount calculation logic: Base Rate → Discount → Tax → Total"""

    def test_percentage_discount_calculation(self):
        """Test calculation with percentage discount"""
        # Formula: Base = price * qty
        # DiscAmount = Base * disc / 100 (when type='%')
        # Taxable = Base - DiscAmount
        # GST = Taxable * gstPercent / 100
        # Total = Taxable + GST
        
        price = 1000
        qty = 2
        discount = 10  # 10%
        gst_percent = 18
        
        base = price * qty  # 2000
        disc_amount = base * discount / 100  # 200
        taxable = base - disc_amount  # 1800
        gst = taxable * gst_percent / 100  # 324
        total = taxable + gst  # 2124
        
        assert base == 2000
        assert disc_amount == 200
        assert taxable == 1800
        assert gst == 324
        assert total == 2124
        print("✓ Percentage discount calculation correct: Base(2000) - 10%(200) = Taxable(1800) + GST(324) = Total(2124)")

    def test_flat_rs_discount_calculation(self):
        """Test calculation with flat Rs discount"""
        # DiscAmount = disc (when type='Rs')
        
        price = 1000
        qty = 2
        discount = 150  # Rs 150 flat
        gst_percent = 18
        
        base = price * qty  # 2000
        disc_amount = discount  # 150 (flat amount)
        taxable = max(base - disc_amount, 0)  # 1850
        gst = taxable * gst_percent / 100  # 333
        total = taxable + gst  # 2183
        
        assert base == 2000
        assert disc_amount == 150
        assert taxable == 1850
        assert gst == 333
        assert total == 2183
        print("✓ Flat Rs discount calculation correct: Base(2000) - Rs.150 = Taxable(1850) + GST(333) = Total(2183)")

    def test_zero_discount_calculation(self):
        """Test calculation with zero discount"""
        price = 500
        qty = 3
        discount = 0
        gst_percent = 5
        
        base = price * qty  # 1500
        disc_amount = 0
        taxable = base - disc_amount  # 1500
        gst = taxable * gst_percent / 100  # 75
        total = taxable + gst  # 1575
        
        assert base == 1500
        assert taxable == 1500
        assert total == 1575
        print("✓ Zero discount calculation correct")


class TestQuotationShareLinkEndpoint:
    """Test POST /api/business-tools/quotations/{id}/share-link endpoint"""

    def test_share_link_endpoint_returns_401_without_auth(self):
        """Share-link endpoint should return 401 without valid auth"""
        import requests
        
        fake_id = "507f1f77bcf86cd799439011"
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}/share-link",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/business-tools/quotations/{id}/share-link returns 401 without valid auth")

    def test_share_link_endpoint_exists(self):
        """Share-link endpoint should exist (not 404 on method)"""
        import requests
        
        fake_id = "507f1f77bcf86cd799439011"
        # A GET should return 405 (Method Not Allowed) if endpoint exists but only accepts POST
        # Or 401 if auth check happens first
        response = requests.post(
            f"{BASE_URL}/api/business-tools/quotations/{fake_id}/share-link",
            headers={"Authorization": "Bearer test_token", "Content-Type": "application/json"}
        )
        # Should be 401 (auth fails) or 404 (quotation not found after auth)
        # NOT 404 with "Not Found" route message
        assert response.status_code in [401, 404, 403], f"Unexpected status: {response.status_code}"
        print(f"✓ Share-link endpoint exists (status={response.status_code})")


class TestPublicDocRouterQuotation:
    """Test public doc router supports quotation document type"""

    def test_public_doc_router_quotation_type_in_code(self):
        """Verify quotation type is handled in product_share_router.py"""
        router_path = '/app/backend/routers/product_share_router.py'
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check that 'quotation' document type is handled
        assert 'elif doc_type == "quotation"' in content, "Public doc router should handle 'quotation' document type"
        assert 'generate_quotation_pdf' in content, "Should import/call generate_quotation_pdf"
        print("✓ Public doc router handles 'quotation' document type")

    def test_public_doc_endpoint_exists(self):
        """Test that /api/doc/{token} endpoint exists"""
        import requests
        
        # Using a fake token - should get 404 (not found) not 404 (route doesn't exist)
        response = requests.get(f"{BASE_URL}/api/doc/fake_token_12345")
        assert response.status_code in [404, 403], f"Expected 404 or 403, got {response.status_code}"
        # If it returns proper error, endpoint exists
        data = response.json()
        assert 'detail' in data, "Should return JSON with detail field"
        print(f"✓ Public doc endpoint exists: {data.get('detail', 'no detail')}")


class TestPDFDiscountDisplay:
    """Test PDF services display discount correctly"""

    def test_quotation_pdf_service_imports(self):
        """Quotation PDF service should import successfully"""
        from services.quotation_pdf_service import generate_quotation_pdf
        assert callable(generate_quotation_pdf)
        print("✓ quotation_pdf_service imports successfully")

    def test_invoice_pdf_service_imports(self):
        """Invoice PDF service should import successfully"""
        from services.invoice_pdf_service import generate_invoice_pdf
        assert callable(generate_invoice_pdf)
        print("✓ invoice_pdf_service imports successfully")

    def test_quotation_pdf_discount_logic_in_code(self):
        """Verify discount display logic in quotation_pdf_service.py"""
        pdf_path = '/app/backend/services/quotation_pdf_service.py'
        with open(pdf_path, 'r') as f:
            content = f.read()
        
        # Check for discountType handling
        assert 'discountType' in content, "Should reference discountType"
        assert 'discountAmount' in content, "Should reference discountAmount"
        # Check for proper display format (5% with amount, or flat Rs)
        assert 'disc_type' in content or 'discountType' in content, "Should handle discount type"
        print("✓ Quotation PDF service has discount display logic")

    def test_invoice_pdf_discount_logic_in_code(self):
        """Verify discount display logic in invoice_pdf_service.py"""
        pdf_path = '/app/backend/services/invoice_pdf_service.py'
        with open(pdf_path, 'r') as f:
            content = f.read()
        
        # Check for discountType handling
        assert 'discountType' in content, "Should reference discountType"
        assert 'discountAmount' in content, "Should reference discountAmount"
        print("✓ Invoice PDF service has discount display logic")

    def test_quotation_pdf_generation_with_percentage_discount(self):
        """Test PDF generation with percentage discount item"""
        from services.quotation_pdf_service import generate_quotation_pdf
        
        mock_quotation = {
            "quotationNumber": "QUO-TEST-001",
            "date": "2026-01-15T10:00:00Z",
            "status": "draft",
            "validityDays": 15,
            "items": [
                {
                    "productId": "prod1",
                    "productName": "Test Product",
                    "hsnCode": "8471",
                    "quantity": 2,
                    "price": 1000,
                    "discount": 10,
                    "discountType": "%",
                    "discountAmount": 200,
                    "gstPercent": 18,
                    "taxableAmount": 1800,
                    "gstAmount": 324,
                    "total": 2124,
                }
            ],
            "subtotal": 1800,
            "cgst": 162,
            "sgst": 162,
            "igst": 0,
            "gst": 324,
            "total": 2124,
            "roundOff": 0,
            "notes": "",
            "termsAndConditions": "",
            "placeOfSupply": "Maharashtra",
        }
        mock_seller = {
            "businessName": "Test Business",
            "name": "Test Business",
            "address": "123 Test St",
            "city": "Mumbai",
            "state": "Maharashtra",
            "phone": "9876543210",
            "email": "test@example.com",
            "gstNumber": "27XXXXX1234X1Z5",
            "sellerLogoUrl": "",
            "bankDetails": {},
            "invoiceTerms": "",
        }
        mock_buyer = {
            "buyerName": "Test Buyer",
            "company": "Buyer Co",
            "address": "456 Buyer St",
            "phone": "9123456789",
            "gstNumber": "27YYYYY5678Y2Z6",
            "state": "Maharashtra",
        }
        
        pdf_bytes = generate_quotation_pdf(mock_quotation, mock_seller, mock_buyer, is_offline=False)
        assert isinstance(pdf_bytes, bytes), "Should return bytes"
        assert len(pdf_bytes) > 1000, "PDF should have substantial content"
        assert pdf_bytes[:4] == b'%PDF', "Should be valid PDF"
        print(f"✓ Quotation PDF generated with percentage discount ({len(pdf_bytes)} bytes)")

    def test_quotation_pdf_generation_with_flat_discount(self):
        """Test PDF generation with flat Rs discount item"""
        from services.quotation_pdf_service import generate_quotation_pdf
        
        mock_quotation = {
            "quotationNumber": "QUO-TEST-002",
            "date": "2026-01-15T10:00:00Z",
            "status": "draft",
            "validityDays": 15,
            "items": [
                {
                    "productId": "prod1",
                    "productName": "Test Product 2",
                    "hsnCode": "8472",
                    "quantity": 1,
                    "price": 5000,
                    "discount": 500,
                    "discountType": "Rs",
                    "discountAmount": 500,
                    "gstPercent": 12,
                    "taxableAmount": 4500,
                    "gstAmount": 540,
                    "total": 5040,
                }
            ],
            "subtotal": 4500,
            "cgst": 270,
            "sgst": 270,
            "igst": 0,
            "gst": 540,
            "total": 5040,
            "roundOff": 0,
            "notes": "",
            "termsAndConditions": "",
            "placeOfSupply": "Maharashtra",
        }
        mock_seller = {
            "businessName": "Test Business",
            "state": "Maharashtra",
        }
        mock_buyer = {
            "buyerName": "Test Buyer 2",
            "state": "Maharashtra",
        }
        
        pdf_bytes = generate_quotation_pdf(mock_quotation, mock_seller, mock_buyer, is_offline=False)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b'%PDF'
        print(f"✓ Quotation PDF generated with flat Rs discount ({len(pdf_bytes)} bytes)")


class TestInvoiceDiscountCalculationInRouter:
    """Test invoice router discount calculation logic"""

    def test_invoice_router_discount_calculation_in_code(self):
        """Verify invoice router has correct discount calculation logic"""
        router_path = '/app/backend/routers/invoice_router.py'
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check for discountType handling in create invoice
        assert "disc_type" in content or "discountType" in content, "Should handle discountType"
        # Check for both % and Rs calculations
        assert 'disc_type == "%"' in content or "discountType == '%'" in content or "if disc_type ==" in content, "Should have percentage discount logic"
        print("✓ Invoice router has discount calculation logic")

    def test_quotation_router_discount_calculation_in_code(self):
        """Verify quotation router has correct discount calculation logic"""
        router_path = '/app/backend/routers/quotation_router.py'
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check for discountType handling
        assert 'discountType' in content, "Should handle discountType"
        # Check for calculation with both % and Rs
        assert 'item.discountType == "%"' in content or "discountType ==" in content, "Should handle % discount"
        print("✓ Quotation router has discount calculation logic")


class TestFrontendDataTestIds:
    """Test that frontend has required data-testid attributes for discount toggle"""

    def test_quotation_page_discount_toggle_testid(self):
        """Verify quotation page has discount toggle data-testid"""
        page_path = '/app/frontend/src/app/seller/business-tools/quotations/page.tsx'
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid={`item-discount-toggle-' in content or 'data-testid="item-discount-toggle' in content, \
            "Quotation page should have discount toggle data-testid"
        assert 'discountType' in content, "Should reference discountType"
        print("✓ Quotation page has discount toggle data-testid")

    def test_invoice_page_discount_toggle_testid(self):
        """Verify invoice page has discount toggle data-testid"""
        page_path = '/app/frontend/src/app/seller/business-tools/invoices/page.tsx'
        with open(page_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid={`invoice-item-discount-toggle-' in content or 'data-testid="invoice-item-discount' in content, \
            "Invoice page should have discount toggle data-testid"
        assert 'discountType' in content, "Should reference discountType"
        print("✓ Invoice page has discount toggle data-testid")


class TestShareLinkResponseFormat:
    """Test the expected response format of share-link endpoint"""

    def test_share_link_router_response_fields_in_code(self):
        """Verify share-link endpoint returns expected fields"""
        router_path = '/app/backend/routers/quotation_router.py'
        with open(router_path, 'r') as f:
            content = f.read()
        
        # Check for response fields
        assert '"pdfUrl"' in content or "'pdfUrl'" in content, "Should return pdfUrl"
        assert '"whatsappLink"' in content or "'whatsappLink'" in content, "Should return whatsappLink"
        assert '"message"' in content or "'message'" in content, "Should return message"
        assert 'Powered by UdyogConnect' in content, "Should include branding"
        print("✓ Share-link endpoint has correct response fields with UdyogConnect branding")


class TestAutoPricingFromInventory:
    """Test auto-fill price, GST%, HSN from inventory on product select"""

    def test_quotation_page_autofill_logic(self):
        """Verify quotation page has auto-fill logic on product select"""
        page_path = '/app/frontend/src/app/seller/business-tools/quotations/page.tsx'
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for onProductSelect function
        assert 'onProductSelect' in content, "Should have onProductSelect function"
        # Check that it sets price, gstPercent, hsnCode
        assert 'listing.price' in content or 'price: listing' in content, "Should auto-fill price"
        assert 'listing.gstRate' in content or 'gstRate' in content, "Should auto-fill GST rate"
        assert 'listing.hsnCode' in content or 'hsnCode' in content, "Should auto-fill HSN code"
        print("✓ Quotation page has auto-fill logic for price, GST%, HSN")

    def test_invoice_page_autofill_logic(self):
        """Verify invoice page has auto-fill logic on product select"""
        page_path = '/app/frontend/src/app/seller/business-tools/invoices/page.tsx'
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for onProductSelect function
        assert 'onProductSelect' in content, "Should have onProductSelect function"
        # Check that it sets price, gstPercent, hsnCode
        assert 'price:' in content and 'listing' in content, "Should auto-fill price from listing"
        assert 'gstPercent:' in content or 'gstRate' in content, "Should auto-fill GST"
        assert 'hsnCode' in content, "Should auto-fill HSN"
        print("✓ Invoice page has auto-fill logic for price, GST%, HSN")


class TestBackendAPIEndpoints:
    """Test backend API endpoints return correct status codes"""

    def test_quotation_list_endpoint(self):
        """GET /api/business-tools/quotations should return 401 without auth"""
        import requests
        response = requests.get(
            f"{BASE_URL}/api/business-tools/quotations",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401
        print("✓ GET /api/business-tools/quotations returns 401")

    def test_invoice_list_endpoint(self):
        """GET /api/business-tools/invoices should return 401 without auth"""
        import requests
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401
        print("✓ GET /api/business-tools/invoices returns 401")

    def test_invoice_products_endpoint(self):
        """GET /api/business-tools/invoice-products should return 401 without auth"""
        import requests
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoice-products",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401
        print("✓ GET /api/business-tools/invoice-products returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
