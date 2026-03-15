"""
Phase 3: Seller Onboarding + Business Branding Tests
=====================================================
Tests for:
1. GET /api/business-tools/seller-profile - returns profile, invoiceIdentity, profileComplete
2. PUT /api/business-tools/seller-profile - updates profile fields (businessName, phone, gstNumber, etc.)
3. Abbreviation generation and stability (should not change after initial setup)
4. Invoice number format validation (INV{ABBR}-{CODE}-{SEQ})
5. Invoice PDF with seller branding
6. Reports endpoints return data
7. Status consistency validation
8. Sequential invoice creation with unique numbers
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Known test data from previous iterations
BUYER_ID = "69b55383a39abdd1ea3cd68e"
SELLER_CODE = "7C5A6E"
EXPECTED_ABBREVIATION = "AE"  # For "Akash Enterprises"


class TestSellerProfileGet:
    """Test GET /api/business-tools/seller-profile endpoint"""

    def test_get_profile_returns_200(self):
        """GET seller-profile should return 200"""
        response = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET seller-profile returns 200")

    def test_profile_contains_required_fields(self):
        """Profile should contain businessName, phone, email, address, city, state, gstNumber, sellerLogoUrl"""
        response = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        profile = data.get("profile", {})
        required_fields = ["businessName", "phone", "email", "address", "city", "state", "gstNumber", "sellerLogoUrl"]
        
        for field in required_fields:
            assert field in profile, f"Missing field: {field}"
        
        print(f"PASS: Profile contains all required fields: {required_fields}")

    def test_invoice_identity_contains_abbreviation_and_code(self):
        """invoiceIdentity should contain sellerAbbreviation and sellerCode"""
        response = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        invoice_identity = data.get("invoiceIdentity", {})
        assert "sellerAbbreviation" in invoice_identity, "Missing sellerAbbreviation"
        assert "sellerCode" in invoice_identity, "Missing sellerCode"
        
        print(f"PASS: invoiceIdentity has sellerAbbreviation='{invoice_identity['sellerAbbreviation']}', sellerCode='{invoice_identity['sellerCode']}'")

    def test_profile_complete_boolean(self):
        """profileComplete should be true if businessName exists"""
        response = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        profile = data.get("profile", {})
        profile_complete = data.get("profileComplete")
        
        assert isinstance(profile_complete, bool), "profileComplete should be boolean"
        
        if profile.get("businessName"):
            assert profile_complete is True, "profileComplete should be True when businessName exists"
            print(f"PASS: profileComplete=True with businessName='{profile['businessName']}'")
        else:
            assert profile_complete is False, "profileComplete should be False when businessName is empty"
            print("PASS: profileComplete=False when businessName is empty")

    def test_abbreviation_matches_business_name(self):
        """Abbreviation should match first letters of business name words (AE for Akash Enterprises)"""
        response = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        
        invoice_identity = data.get("invoiceIdentity", {})
        abbr = invoice_identity.get("sellerAbbreviation", "")
        
        assert abbr == EXPECTED_ABBREVIATION, f"Expected abbreviation '{EXPECTED_ABBREVIATION}', got '{abbr}'"
        print(f"PASS: Abbreviation is '{abbr}' as expected for 'Akash Enterprises'")


class TestSellerProfilePut:
    """Test PUT /api/business-tools/seller-profile endpoint"""

    def test_update_profile_without_businessname_returns_400(self):
        """PUT without businessName should return 400"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={"phone": "1234567890"}  # No businessName
        )
        assert response.status_code == 400, f"Expected 400 for missing businessName, got {response.status_code}"
        print("PASS: PUT without businessName returns 400")

    def test_update_profile_with_businessname_succeeds(self):
        """PUT with businessName saves to user.profile"""
        # First get current profile to restore later
        get_resp = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        original_profile = get_resp.json().get("profile", {})
        
        # Update profile
        update_data = {
            "businessName": "Akash Enterprises",  # Keep same to not change abbreviation
            "phone": "9876543210",
            "address": "123 Industrial Area",
            "city": "Mumbai",
            "state": "Maharashtra"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        profile = data.get("profile", {})
        
        assert profile.get("businessName") == update_data["businessName"]
        assert profile.get("phone") == update_data["phone"]
        print(f"PASS: Profile updated successfully - businessName='{profile['businessName']}'")

    def test_update_gst_number_saves_correctly(self):
        """PUT with gstNumber should save to user.gst.number"""
        test_gst = "27AABCA1234E1Z5"
        response = requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={
                "businessName": "Akash Enterprises",
                "gstNumber": test_gst
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify by re-fetching
        get_resp = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        profile = get_resp.json().get("profile", {})
        
        assert profile.get("gstNumber") == test_gst, f"Expected gstNumber '{test_gst}', got '{profile.get('gstNumber')}'"
        print(f"PASS: GST number saved correctly: {test_gst}")

    def test_update_logo_url_saves_correctly(self):
        """PUT with sellerLogoUrl should update logo URL"""
        test_logo_url = "https://example.com/test-logo.png"
        response = requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={
                "businessName": "Akash Enterprises",
                "sellerLogoUrl": test_logo_url
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify by re-fetching
        get_resp = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        profile = get_resp.json().get("profile", {})
        
        assert profile.get("sellerLogoUrl") == test_logo_url, f"Expected logo URL '{test_logo_url}', got '{profile.get('sellerLogoUrl')}'"
        print(f"PASS: Logo URL saved correctly: {test_logo_url}")
        
        # Clean up - remove test logo URL
        requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={"businessName": "Akash Enterprises", "sellerLogoUrl": ""}
        )


class TestAbbreviationStability:
    """Test that abbreviation does not change after initial setup"""

    def test_abbreviation_does_not_change_on_business_name_edit(self):
        """After first save, changing business name should NOT change abbreviation"""
        # Get current abbreviation
        get_resp = requests.get(f"{BASE_URL}/api/business-tools/seller-profile", headers=AUTH_HEADER)
        original_data = get_resp.json()
        original_abbr = original_data.get("invoiceIdentity", {}).get("sellerAbbreviation")
        original_name = original_data.get("profile", {}).get("businessName")
        
        print(f"Original: businessName='{original_name}', abbreviation='{original_abbr}'")
        
        # Update to different business name
        new_name = "Power Control Systems"  # Would be "PCS" if abbreviation was regenerated
        response = requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={"businessName": new_name}
        )
        assert response.status_code == 200
        
        # Check abbreviation after update
        updated_data = response.json()
        new_abbr = updated_data.get("invoiceIdentity", {}).get("sellerAbbreviation")
        
        print(f"After update: businessName='{new_name}', abbreviation='{new_abbr}'")
        
        # Abbreviation should stay the same (AE, not PCS)
        assert new_abbr == original_abbr, f"Abbreviation changed from '{original_abbr}' to '{new_abbr}' - should be stable!"
        print(f"PASS: Abbreviation remained '{new_abbr}' despite name change to '{new_name}'")
        
        # Restore original business name
        requests.put(
            f"{BASE_URL}/api/business-tools/seller-profile",
            headers=AUTH_HEADER,
            json={"businessName": original_name}
        )
        print(f"Restored original business name: '{original_name}'")


class TestInvoiceNumberFormat:
    """Test invoice number format: INV{ABBR}-{CODE}-{SEQ}"""

    def test_new_invoices_use_correct_format(self):
        """New invoices should use format INVAE-7C5A6E-XXXX with correct abbreviation"""
        # Create a new invoice
        invoice_data = {
            "buyerId": BUYER_ID,
            "items": [
                {
                    "productName": "Phase 3 Test Product",
                    "quantity": 1,
                    "price": 1000,
                    "gstPercent": 18
                }
            ],
            "dueDays": 7,
            "deductStock": False,
            "notes": "Phase 3 invoice format test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices",
            headers=AUTH_HEADER,
            json=invoice_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        invoice = response.json().get("invoice", {})
        invoice_number = invoice.get("invoiceNumber", "")
        
        # Expected format: INVAE-7C5A6E-XXXX
        expected_prefix = f"INV{EXPECTED_ABBREVIATION}-{SELLER_CODE}-"
        assert invoice_number.startswith(expected_prefix), f"Invoice number '{invoice_number}' should start with '{expected_prefix}'"
        
        # Verify sequence is 4 digits
        seq_part = invoice_number.split("-")[-1]
        assert seq_part.isdigit() and len(seq_part) == 4, f"Sequence part should be 4 digits, got '{seq_part}'"
        
        print(f"PASS: New invoice created with number '{invoice_number}' matching format INV{{ABBR}}-{{CODE}}-{{SEQ}}")
        
        return invoice.get("id")


class TestSequentialInvoiceCreation:
    """Test rapid sequential invoice creation gets unique sequential numbers"""

    def test_rapid_invoice_creation_sequential_unique(self):
        """3 rapid invoices should get sequential unique numbers"""
        created_invoices = []
        
        for i in range(3):
            invoice_data = {
                "buyerId": BUYER_ID,
                "items": [
                    {
                        "productName": f"Rapid Test Item {i+1}",
                        "quantity": 1,
                        "price": 500 + (i * 100),
                        "gstPercent": 18
                    }
                ],
                "dueDays": 7,
                "deductStock": False,
                "notes": f"Sequential test #{i+1}"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/business-tools/invoices",
                headers=AUTH_HEADER,
                json=invoice_data
            )
            
            assert response.status_code == 200, f"Invoice {i+1} creation failed: {response.text}"
            invoice = response.json().get("invoice", {})
            created_invoices.append(invoice.get("invoiceNumber"))
        
        print(f"Created 3 invoices: {created_invoices}")
        
        # Verify all are unique
        assert len(set(created_invoices)) == 3, f"Expected 3 unique invoice numbers, got duplicates: {created_invoices}"
        
        # Extract sequence numbers and verify sequential
        sequences = []
        for inv_num in created_invoices:
            seq_str = inv_num.split("-")[-1]
            sequences.append(int(seq_str))
        
        sequences_sorted = sorted(sequences)
        for i in range(len(sequences_sorted) - 1):
            diff = sequences_sorted[i+1] - sequences_sorted[i]
            assert diff == 1, f"Sequence gap detected: {sequences_sorted[i]} -> {sequences_sorted[i+1]}"
        
        print(f"PASS: 3 rapid invoices got sequential unique numbers: sequences={sequences_sorted}")


class TestInvoicePDF:
    """Test Invoice PDF generation with seller branding"""

    def test_invoice_pdf_returns_valid_pdf(self):
        """GET /invoices/{id}/pdf should return 200 and valid PDF bytes"""
        # First get an invoice ID
        list_resp = requests.get(f"{BASE_URL}/api/business-tools/invoices?limit=1", headers=AUTH_HEADER)
        assert list_resp.status_code == 200
        invoices = list_resp.json().get("invoices", [])
        
        if not invoices:
            pytest.skip("No invoices available for PDF test")
        
        invoice_id = invoices[0]["id"]
        
        # Get PDF
        pdf_resp = requests.get(
            f"{BASE_URL}/api/business-tools/invoices/{invoice_id}/pdf",
            headers=AUTH_HEADER
        )
        
        assert pdf_resp.status_code == 200, f"Expected 200, got {pdf_resp.status_code}: {pdf_resp.text}"
        
        # Verify PDF content type
        content_type = pdf_resp.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Verify PDF bytes (should start with %PDF)
        pdf_bytes = pdf_resp.content
        assert len(pdf_bytes) > 0, "PDF content is empty"
        assert pdf_bytes[:4] == b'%PDF', f"Content does not start with PDF signature: {pdf_bytes[:20]}"
        
        print(f"PASS: PDF generated successfully ({len(pdf_bytes)} bytes) with valid PDF signature")


class TestReportsEndpoints:
    """Test reports endpoints return data (not empty)"""

    def test_sales_summary_returns_data(self):
        """GET /reports/sales-summary should return data (not empty)"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/reports/sales-summary",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        overall = data.get("overall", {})
        
        assert "totalRevenue" in overall, "Missing totalRevenue in sales summary"
        assert "invoiceCount" in overall, "Missing invoiceCount in sales summary"
        
        # Verify not empty (we have invoices)
        invoice_count = overall.get("invoiceCount", 0)
        assert invoice_count > 0, "Sales summary has 0 invoices - should have data"
        
        print(f"PASS: Sales summary returned: invoiceCount={invoice_count}, totalRevenue={overall.get('totalRevenue')}")


class TestStatusConsistency:
    """Test invoice status consistency"""

    def test_no_invoice_with_zero_paid_has_paid_status(self):
        """No invoice with paid=0 should have status=paid"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/invoices?limit=100",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        invoices = response.json().get("invoices", [])
        
        violations = []
        for inv in invoices:
            total_paid = inv.get("totalPaid", 0)
            status = inv.get("status", "")
            
            if total_paid == 0 and status == "paid":
                violations.append({
                    "invoiceNumber": inv.get("invoiceNumber"),
                    "totalPaid": total_paid,
                    "status": status
                })
        
        assert len(violations) == 0, f"Found {len(violations)} invoices with totalPaid=0 but status='paid': {violations}"
        print(f"PASS: Checked {len(invoices)} invoices - no status consistency violations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
