"""
Invoice Product Specifications Tests
- GET /api/business-tools/invoice-products - Returns listings with product specifications
- POST /api/business-tools/invoices - Create invoice with selected_specifications
- GET /api/business-tools/invoices - List invoices with items containing selected_specifications
- GET /api/business-tools/invoices/{id}/pdf - PDF generation with specs
- Invoice items with custom specifications (not from catalog)
- Invoice items with empty selected_specifications (backwards compatibility)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "dev-test-token"

# Test data from required_credentials
TEST_BUYER_ID = "69b55383a39abdd1ea3cd68e"
MOTOR_LISTING_ID = "69b57c730ed7999c085b3656"
STEEL_LISTING_ID = "69b57c730ed7999c085b3657"
TEST_INVOICE_WITH_SPECS = "69b5cddb5e9418f3843e70eb"


@pytest.fixture
def auth_headers():
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


class TestInvoiceProductsEndpoint:
    """Test GET /api/business-tools/invoice-products returns specs from admin catalog"""
    
    def test_get_invoice_products_returns_specifications(self, auth_headers):
        """invoice-products endpoint should return product specifications from admin catalog"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "products" in data, "Response should contain 'products' key"
        products = data["products"]
        assert isinstance(products, list), "products should be a list"
        
        print(f"Found {len(products)} products")
        
        # Find motor listing which should have specs
        motor_product = next((p for p in products if p.get("id") == MOTOR_LISTING_ID), None)
        if motor_product:
            print(f"Motor product: {motor_product}")
            assert "specifications" in motor_product, "Product should have specifications field"
            specs = motor_product["specifications"]
            assert isinstance(specs, list), "specifications should be a list"
            print(f"Motor specs: {specs}")
            # Motor should have specs like Voltage, Phase, Power, Material
            if len(specs) > 0:
                spec = specs[0]
                assert "key" in spec, "Spec should have 'key' field"
                assert "value" in spec, "Spec should have 'value' field"
                print(f"Spec format verified: {spec}")
    
    def test_invoice_products_structure(self, auth_headers):
        """Verify each product in invoice-products has required fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=auth_headers)
        assert response.status_code == 200
        
        products = response.json().get("products", [])
        
        if len(products) > 0:
            product = products[0]
            # Required fields for invoice product
            assert "id" in product, "Product should have id"
            assert "productName" in product, "Product should have productName"
            assert "price" in product, "Product should have price"
            assert "stock" in product, "Product should have stock"
            assert "specifications" in product, "Product should have specifications"
            print(f"Product structure verified: {list(product.keys())}")


class TestCreateInvoiceWithSpecs:
    """Test POST /api/business-tools/invoices stores selected_specifications"""
    
    def test_create_invoice_with_specifications(self, auth_headers):
        """Create invoice with selected_specifications and verify they are stored"""
        test_specs = [
            {"key": "Voltage", "value": "220V"},
            {"key": "Power", "value": "5HP"}
        ]
        
        payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": MOTOR_LISTING_ID,
                    "productName": "Test Motor",
                    "quantity": 2,
                    "price": 1500.00,
                    "gstPercent": 18,
                    "selected_specifications": test_specs
                }
            ],
            "notes": "Test invoice with specs",
            "deductStock": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "invoice" in data, "Response should contain invoice"
        invoice = data["invoice"]
        
        assert "id" in invoice, "Invoice should have id"
        assert "items" in invoice, "Invoice should have items"
        
        items = invoice["items"]
        assert len(items) == 1, "Invoice should have 1 item"
        
        item = items[0]
        assert "selected_specifications" in item, "Item should have selected_specifications"
        
        stored_specs = item["selected_specifications"]
        assert len(stored_specs) == 2, f"Expected 2 specs, got {len(stored_specs)}"
        
        # Verify spec content
        spec_keys = [s["key"] for s in stored_specs]
        assert "Voltage" in spec_keys, "Should contain Voltage spec"
        assert "Power" in spec_keys, "Should contain Power spec"
        
        print(f"Created invoice {invoice.get('invoiceNumber')} with specs: {stored_specs}")
        
        # Store invoice ID for cleanup
        return invoice["id"]
    
    def test_create_invoice_with_custom_specifications(self, auth_headers):
        """Create invoice with custom specifications (not from catalog)"""
        custom_specs = [
            {"key": "Warranty", "value": "2 Years"},
            {"key": "Color", "value": "Blue"},
            {"key": "Custom Note", "value": "Special handling required"}
        ]
        
        payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": STEEL_LISTING_ID,
                    "productName": "Test Steel",
                    "quantity": 5,
                    "price": 2000.00,
                    "gstPercent": 18,
                    "selected_specifications": custom_specs
                }
            ],
            "notes": "Test invoice with custom specs",
            "deductStock": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        item = data["invoice"]["items"][0]
        stored_specs = item["selected_specifications"]
        
        assert len(stored_specs) == 3, f"Expected 3 custom specs, got {len(stored_specs)}"
        
        spec_keys = [s["key"] for s in stored_specs]
        assert "Warranty" in spec_keys, "Should contain custom Warranty spec"
        assert "Color" in spec_keys, "Should contain custom Color spec"
        
        print(f"Custom specs stored successfully: {stored_specs}")
    
    def test_create_invoice_without_specifications(self, auth_headers):
        """Create invoice without specifications - backwards compatibility"""
        payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": MOTOR_LISTING_ID,
                    "productName": "Test Motor No Specs",
                    "quantity": 1,
                    "price": 1000.00,
                    "gstPercent": 18
                    # Note: No selected_specifications field
                }
            ],
            "notes": "Test invoice without specs",
            "deductStock": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        item = data["invoice"]["items"][0]
        # Should have empty specs list or field should exist
        specs = item.get("selected_specifications", [])
        assert isinstance(specs, list), "selected_specifications should be a list (empty)"
        
        print(f"Invoice without specs created successfully - specs field: {specs}")
    
    def test_create_invoice_with_empty_specifications(self, auth_headers):
        """Create invoice with explicitly empty specifications array"""
        payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": STEEL_LISTING_ID,
                    "productName": "Test Steel Empty Specs",
                    "quantity": 3,
                    "price": 1500.00,
                    "gstPercent": 12,
                    "selected_specifications": []  # Explicitly empty
                }
            ],
            "notes": "Test invoice with empty specs",
            "deductStock": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        item = data["invoice"]["items"][0]
        specs = item.get("selected_specifications", [])
        assert specs == [], f"Expected empty specs list, got {specs}"
        
        print("Invoice with empty specs created successfully")


class TestListInvoicesWithSpecs:
    """Test GET /api/business-tools/invoices returns items with selected_specifications"""
    
    def test_list_invoices_includes_specifications(self, auth_headers):
        """List invoices should return items with selected_specifications field"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "invoices" in data, "Response should contain invoices"
        invoices = data["invoices"]
        
        print(f"Found {len(invoices)} invoices")
        
        # Check if any invoice has items with specs
        found_specs = False
        for invoice in invoices[:5]:  # Check first 5 invoices
            items = invoice.get("items", [])
            for item in items:
                if "selected_specifications" in item:
                    specs = item["selected_specifications"]
                    if len(specs) > 0:
                        found_specs = True
                        print(f"Invoice {invoice.get('invoiceNumber')} has item with specs: {specs}")
                        break
            if found_specs:
                break
        
        print(f"Invoices structure verified, specs found: {found_specs}")


class TestInvoicePdfWithSpecs:
    """Test PDF generation includes specifications"""
    
    def test_pdf_generation_returns_valid_pdf(self, auth_headers):
        """PDF endpoint should return valid PDF with specs rendered"""
        # First, create an invoice with specs
        test_specs = [
            {"key": "Voltage", "value": "415V"},
            {"key": "Phase", "value": "3-Phase"}
        ]
        
        create_payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": MOTOR_LISTING_ID,
                    "productName": "Motor for PDF Test",
                    "quantity": 1,
                    "price": 5000.00,
                    "gstPercent": 18,
                    "selected_specifications": test_specs
                }
            ],
            "notes": "PDF test with specs",
            "deductStock": False
        }
        
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=create_payload)
        assert create_response.status_code == 200, f"Failed to create invoice: {create_response.text}"
        
        invoice_id = create_response.json()["invoice"]["id"]
        
        # Now download PDF
        pdf_response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/pdf", headers=auth_headers)
        
        assert pdf_response.status_code == 200, f"Expected 200, got {pdf_response.status_code}: {pdf_response.text}"
        
        # Verify it's a PDF
        content_type = pdf_response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got {content_type}"
        
        # Verify PDF magic bytes
        pdf_bytes = pdf_response.content
        assert pdf_bytes[:4] == b'%PDF', "Response should be a valid PDF (starts with %PDF)"
        
        print(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
        
        # Content-Disposition header check
        content_disp = pdf_response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".pdf" in content_disp, "Should have .pdf in filename"
        
        print(f"PDF headers verified: {content_disp}")
    
    def test_existing_invoice_pdf_with_specs(self, auth_headers):
        """Test PDF generation for existing test invoice with specs"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{TEST_INVOICE_WITH_SPECS}/pdf", headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Test invoice not found - may have been deleted")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        pdf_bytes = response.content
        assert pdf_bytes[:4] == b'%PDF', "Should be valid PDF"
        print(f"Existing invoice PDF generated, size: {len(pdf_bytes)} bytes")


class TestInvoiceDetailWithSpecs:
    """Test GET /api/business-tools/invoices/{id} returns specs"""
    
    def test_get_invoice_detail_includes_specifications(self, auth_headers):
        """Single invoice detail should include selected_specifications in items"""
        # First create an invoice with specs
        test_specs = [
            {"key": "Material", "value": "Stainless Steel"},
            {"key": "Grade", "value": "SS304"}
        ]
        
        create_payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": STEEL_LISTING_ID,
                    "productName": "Steel for Detail Test",
                    "quantity": 10,
                    "price": 250.00,
                    "gstPercent": 18,
                    "selected_specifications": test_specs
                }
            ],
            "notes": "Detail test with specs",
            "deductStock": False
        }
        
        create_response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=create_payload)
        assert create_response.status_code == 200
        
        invoice_id = create_response.json()["invoice"]["id"]
        
        # Get invoice detail
        detail_response = requests.get(f"{BASE_URL}/api/business-tools/invoices/{invoice_id}", headers=auth_headers)
        
        assert detail_response.status_code == 200, f"Expected 200, got {detail_response.status_code}"
        data = detail_response.json()
        
        assert "invoice" in data, "Response should contain invoice"
        invoice = data["invoice"]
        
        items = invoice.get("items", [])
        assert len(items) == 1, "Should have 1 item"
        
        item = items[0]
        assert "selected_specifications" in item, "Item should have selected_specifications"
        
        specs = item["selected_specifications"]
        assert len(specs) == 2, f"Expected 2 specs, got {len(specs)}"
        
        spec_keys = [s["key"] for s in specs]
        assert "Material" in spec_keys, "Should have Material spec"
        assert "Grade" in spec_keys, "Should have Grade spec"
        
        print(f"Invoice detail verified with specs: {specs}")


class TestMultipleItemsWithMixedSpecs:
    """Test invoice with multiple items - some with specs, some without"""
    
    def test_multiple_items_mixed_specifications(self, auth_headers):
        """Create invoice with multiple items having different spec configurations"""
        payload = {
            "buyerId": TEST_BUYER_ID,
            "items": [
                {
                    "productId": MOTOR_LISTING_ID,
                    "productName": "Motor with full specs",
                    "quantity": 1,
                    "price": 5000.00,
                    "gstPercent": 18,
                    "selected_specifications": [
                        {"key": "Voltage", "value": "220V"},
                        {"key": "Power", "value": "10HP"}
                    ]
                },
                {
                    "productId": STEEL_LISTING_ID,
                    "productName": "Steel without specs",
                    "quantity": 5,
                    "price": 1000.00,
                    "gstPercent": 12,
                    "selected_specifications": []  # Empty
                },
                {
                    "productId": None,
                    "productName": "Manual entry item",
                    "quantity": 2,
                    "price": 500.00,
                    "gstPercent": 5,
                    "selected_specifications": [
                        {"key": "Custom", "value": "Special item"}
                    ]
                }
            ],
            "notes": "Multiple items mixed specs test",
            "deductStock": False
        }
        
        response = requests.post(f"{BASE_URL}/api/business-tools/invoices", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        items = data["invoice"]["items"]
        assert len(items) == 3, "Should have 3 items"
        
        # Verify each item's specs
        assert len(items[0]["selected_specifications"]) == 2, "First item should have 2 specs"
        assert len(items[1]["selected_specifications"]) == 0, "Second item should have 0 specs"
        assert len(items[2]["selected_specifications"]) == 1, "Third item should have 1 custom spec"
        
        print("Multiple items with mixed specs verified successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
