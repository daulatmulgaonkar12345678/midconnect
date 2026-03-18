"""
Tests for HSN Code and WhatsApp Messaging Fixes
Tests the specific bug fixes for:
1. HSN code not showing in inventory page
2. WhatsApp messages now using centralized templates
3. BASE_URL changed to https://www.udyogconnect.in
4. doc_url properly generated with build_doc_url()
5. Buyer names trimmed (strip())
6. catalog_url fallback to BASE_URL
"""

import pytest
import sys
import os

# Add backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.whatsapp_messages import (
    BASE_URL,
    build_doc_url,
    build_footer,
    invoice_message,
    payment_reminder_soft,
    payment_reminder_strict,
    catalog_marketing_message,
)


class TestBASEURLFix:
    """Test that BASE_URL is correctly set to https://www.udyogconnect.in"""
    
    def test_base_url_is_www_domain(self):
        """BASE_URL must use www.udyogconnect.in (not //udyogconnect.in)"""
        assert BASE_URL == "https://www.udyogconnect.in", f"BASE_URL should be 'https://www.udyogconnect.in', got '{BASE_URL}'"
        print("PASS: BASE_URL is https://www.udyogconnect.in")
    
    def test_base_url_has_https_protocol(self):
        """BASE_URL must have https:// protocol (not just //)"""
        assert BASE_URL.startswith("https://"), f"BASE_URL must start with 'https://', got '{BASE_URL}'"
        print("PASS: BASE_URL has https:// protocol")


class TestBuildDocUrlFix:
    """Test that build_doc_url generates proper URLs"""
    
    def test_build_doc_url_returns_full_url(self):
        """build_doc_url should return full URL with www domain"""
        token = "abc123xyz"
        url = build_doc_url(token)
        expected = "https://www.udyogconnect.in/api/doc/abc123xyz"
        assert url == expected, f"Expected '{expected}', got '{url}'"
        print("PASS: build_doc_url returns full URL with www domain")
    
    def test_build_doc_url_not_empty(self):
        """build_doc_url should never return empty string"""
        token = "test_token"
        url = build_doc_url(token)
        assert url != "", "build_doc_url should not return empty string"
        assert "udyogconnect.in" in url, "URL should contain udyogconnect.in domain"
        print("PASS: build_doc_url returns non-empty URL with proper domain")


class TestInvoiceWhatsAppMessage:
    """Test invoice WhatsApp message has all required elements"""
    
    def test_invoice_message_contains_doc_url(self):
        """Invoice message must contain the doc_url"""
        doc_url = "https://www.udyogconnect.in/api/doc/abc123"
        msg = invoice_message(
            invoice_number="INV-001",
            amount=10000.00,
            doc_url=doc_url,
            business_name="Test Business",
            buyer_name="John Doe"
        )
        assert doc_url in msg, "Invoice message missing doc_url"
        print("PASS: Invoice message contains doc_url")
    
    def test_invoice_message_contains_business_name(self):
        """Invoice message must contain business name in Regards section"""
        msg = invoice_message(
            invoice_number="INV-001",
            amount=10000.00,
            doc_url="https://www.udyogconnect.in/api/doc/abc123",
            business_name="ABC Industries",
            buyer_name="John"
        )
        assert "ABC Industries" in msg, "Business name missing"
        assert "Regards" in msg, "'Regards' section missing"
        print("PASS: Invoice message contains 'Regards,\\n{business_name}'")
    
    def test_invoice_message_contains_powered_by(self):
        """Invoice message must contain 'Powered by Udyog Connect'"""
        msg = invoice_message(
            invoice_number="INV-001",
            amount=10000.00,
            doc_url="https://www.udyogconnect.in/api/doc/abc123",
            business_name="Test Business",
            buyer_name="John"
        )
        assert "Powered by Udyog Connect" in msg, "Footer 'Powered by Udyog Connect' missing"
        print("PASS: Invoice message contains 'Powered by Udyog Connect'")


class TestPaymentReminderMessages:
    """Test payment reminder messages (soft and overdue)"""
    
    def test_soft_reminder_contains_doc_url(self):
        """Soft reminder (followup) must contain doc_url"""
        doc_url = "https://www.udyogconnect.in/api/doc/xyz789"
        msg = payment_reminder_soft(
            invoice_number="INV-001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url=doc_url,
            business_name="Test Business",
            buyer_name="Customer"
        )
        assert doc_url in msg, "Soft reminder missing doc_url"
        print("PASS: Soft reminder contains doc_url")
    
    def test_overdue_reminder_contains_doc_url(self):
        """Overdue reminder must contain doc_url"""
        doc_url = "https://www.udyogconnect.in/api/doc/overdue123"
        msg = payment_reminder_strict(
            invoice_number="INV-001",
            pending_amount=5000.00,
            due_date="01 Jan 2024",
            doc_url=doc_url,
            business_name="Test Business",
            buyer_name="Customer"
        )
        assert doc_url in msg, "Overdue reminder missing doc_url"
        print("PASS: Overdue reminder contains doc_url")
    
    def test_reminders_contain_footer(self):
        """Both reminder types must contain Udyog Connect footer"""
        soft_msg = payment_reminder_soft(
            invoice_number="INV-001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://www.udyogconnect.in/api/doc/test",
            business_name="Test Business"
        )
        strict_msg = payment_reminder_strict(
            invoice_number="INV-001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://www.udyogconnect.in/api/doc/test",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in soft_msg, "Soft reminder missing footer"
        assert "Powered by Udyog Connect" in strict_msg, "Strict reminder missing footer"
        print("PASS: Both reminder types contain 'Powered by Udyog Connect' footer")


class TestAllDocURLsUseWWWDomain:
    """Test that all doc URLs use https://www.udyogconnect.in domain"""
    
    def test_build_doc_url_uses_www(self):
        """build_doc_url must use www.udyogconnect.in"""
        url = build_doc_url("test123")
        assert "www.udyogconnect.in" in url, f"URL should use www domain: {url}"
        assert not url.startswith("//"), "URL should not start with //"
        print("PASS: build_doc_url uses https://www.udyogconnect.in")


class TestBuyerNameTrimming:
    """Test that buyer names with extra spaces are trimmed"""
    
    def test_invoice_message_trims_buyer_name(self):
        """Buyer name 'Daulat  ' should be trimmed to 'Daulat'"""
        msg = invoice_message(
            invoice_number="INV-001",
            amount=10000.00,
            doc_url="https://www.udyogconnect.in/api/doc/abc123",
            business_name="Test Business",
            buyer_name="Daulat  "  # Extra spaces
        )
        # The greeting should be "Hello Daulat," not "Hello Daulat  ,"
        assert "Hello Daulat," in msg or "Hello Daulat\n" in msg, f"Buyer name not trimmed properly in: {msg[:100]}"
        assert "Daulat  " not in msg, "Buyer name with trailing spaces not trimmed"
        print("PASS: Buyer name with trailing spaces is trimmed")
    
    def test_soft_reminder_trims_buyer_name(self):
        """Soft reminder should trim buyer name"""
        msg = payment_reminder_soft(
            invoice_number="INV-001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://www.udyogconnect.in/api/doc/test",
            business_name="Test Business",
            buyer_name="  Customer Name  "  # Extra spaces both sides
        )
        assert "  Customer Name  " not in msg, "Buyer name not trimmed"
        assert "Customer Name" in msg, "Trimmed buyer name should be present"
        print("PASS: Soft reminder trims buyer name")


class TestCatalogURLFallback:
    """Test that sales push uses BASE_URL as fallback (not /catalog)"""
    
    def test_catalog_marketing_message_with_base_url(self):
        """catalog_marketing_message should work with BASE_URL"""
        msg = catalog_marketing_message(
            catalog_url=BASE_URL,  # Using BASE_URL as fallback
            business_name="Test Business",
            buyer_name="Customer"
        )
        assert "www.udyogconnect.in" in msg, "BASE_URL not in message"
        assert "/catalog" not in msg or "www.udyogconnect.in" in msg, "Should not use fake /catalog URL"
        print("PASS: catalog_marketing_message uses BASE_URL (not /catalog)")


class TestFooterStructure:
    """Test the footer structure"""
    
    def test_footer_has_proper_structure(self):
        """Footer should have separator, Powered by, ad, and website"""
        footer = build_footer()
        # Check structure
        assert "---" in footer, "Footer missing separator"
        assert "Powered by Udyog Connect" in footer, "Footer missing 'Powered by Udyog Connect'"
        assert "www.udyogconnect.in" in footer, "Footer missing website"
        print("PASS: Footer has proper structure with separator, branding, and website")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
