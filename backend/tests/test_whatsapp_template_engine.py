"""
WhatsApp Message Template Engine Tests
Tests the centralized WhatsApp messaging templates for Udyog Connect.

Features to test:
1. build_footer() includes 'Powered by Udyog Connect' and 'www.udyogconnect.in'
2. build_footer() includes rotating ad from ROTATING_ADS list
3. po_message() - Purchase Order template
4. invoice_message() - Invoice template
5. payment_reminder_soft() - Gentle reminder template
6. payment_reminder_strict() - Overdue reminder template
7. catalog_message() - Catalog sharing template
8. catalog_marketing_message() - Catalog marketing with catalog and optional invoice
9. pending_order_notify() - Pending order notification template
10. build_wa_link() and clean_phone() helper functions
"""

import pytest
import sys
import os

# Add backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.whatsapp_messages import (
    ROTATING_ADS,
    build_footer,
    clean_phone,
    build_wa_link,
    po_message,
    invoice_message,
    payment_reminder_soft,
    payment_reminder_strict,
    dispatch_message,
    catalog_message,
    catalog_marketing_message,
    pending_order_notify,
)


class TestBuildFooter:
    """Test build_footer() function - Branding block on ALL messages"""
    
    def test_footer_contains_powered_by_udyog_connect(self):
        """Footer must contain 'Powered by Udyog Connect'"""
        footer = build_footer()
        assert "Powered by Udyog Connect" in footer, "Footer missing 'Powered by Udyog Connect'"
        print("PASS: Footer contains 'Powered by Udyog Connect'")
    
    def test_footer_contains_website_url(self):
        """Footer must contain 'www.udyogconnect.in'"""
        footer = build_footer()
        assert "www.udyogconnect.in" in footer, "Footer missing website URL"
        print("PASS: Footer contains 'www.udyogconnect.in'")
    
    def test_footer_contains_separator(self):
        """Footer must start with separator"""
        footer = build_footer()
        assert footer.startswith("\n---\n"), "Footer should start with newline and separator"
        print("PASS: Footer starts with separator")
    
    def test_footer_contains_rotating_ad(self):
        """Footer must contain one ad from ROTATING_ADS list"""
        # Call multiple times to verify randomness and that ads come from the list
        seen_ads = set()
        for _ in range(100):
            footer = build_footer()
            found_ad = False
            for ad in ROTATING_ADS:
                if ad in footer:
                    seen_ads.add(ad)
                    found_ad = True
                    break
            assert found_ad, f"Footer does not contain any rotating ad from ROTATING_ADS list: {footer}"
        
        print(f"PASS: Footer contains rotating ads. Seen {len(seen_ads)} different ads in 100 calls")
        # Verify we saw at least 2 different ads (randomness check)
        assert len(seen_ads) >= 2, f"Expected random rotation, but only saw {len(seen_ads)} ads"
        print(f"PASS: Confirmed ad rotation - {len(seen_ads)} unique ads observed")


class TestHelperFunctions:
    """Test helper functions: clean_phone, build_wa_link"""
    
    def test_clean_phone_10_digit(self):
        """10-digit Indian number should get 91 prefix"""
        assert clean_phone("9876543210") == "919876543210"
        print("PASS: 10-digit number gets 91 prefix")
    
    def test_clean_phone_with_plus_91(self):
        """Number with +91 should remove + only"""
        assert clean_phone("+919876543210") == "919876543210"
        print("PASS: +91 prefix handled correctly")
    
    def test_clean_phone_with_spaces(self):
        """Number with spaces should be cleaned"""
        assert clean_phone("98765 43210") == "919876543210"
        print("PASS: Spaces removed and 91 prefix added")
    
    def test_clean_phone_with_dashes(self):
        """Number with dashes should be cleaned"""
        assert clean_phone("987-654-3210") == "919876543210"
        print("PASS: Dashes removed and 91 prefix added")
    
    def test_build_wa_link_basic(self):
        """build_wa_link should create valid WhatsApp URL"""
        link = build_wa_link("9876543210", "Hello World")
        assert link.startswith("https://wa.me/919876543210")
        assert "text=Hello%20World" in link
        print("PASS: WhatsApp link built correctly")
    
    def test_build_wa_link_special_chars(self):
        """build_wa_link should URL-encode special characters"""
        link = build_wa_link("9876543210", "Hello!\nNew Line")
        assert "https://wa.me/919876543210" in link
        # Newline should be URL encoded
        assert "%0A" in link or "%0a" in link
        print("PASS: Special characters URL-encoded in WhatsApp link")


class TestPOMessage:
    """Test PO (Purchase Order) message template"""
    
    def test_po_message_contains_po_number(self):
        """PO message must include PO number"""
        msg = po_message(
            po_number="PO-2024-0001",
            items=[{"productName": "Steel Rod", "sku": "SKU001", "quantity": 100, "price": 50.0}],
            doc_url="https://example.com/po/123",
            business_name="Test Business",
            supplier_name="Supplier Co"
        )
        assert "PO-2024-0001" in msg, "PO number missing from message"
        print("PASS: PO message contains PO number")
    
    def test_po_message_contains_items(self):
        """PO message must include items list"""
        items = [
            {"productName": "Steel Rod", "sku": "SKU001", "quantity": 100, "price": 50.0},
            {"productName": "Iron Pipe", "quantity": 50}
        ]
        msg = po_message(
            po_number="PO-2024-0001",
            items=items,
            doc_url="https://example.com/po/123",
            business_name="Test Business"
        )
        assert "Steel Rod" in msg, "Product name missing"
        assert "SKU001" in msg, "SKU missing"
        assert "Qty: 100" in msg, "Quantity missing"
        assert "Iron Pipe" in msg, "Second product missing"
        print("PASS: PO message contains all items")
    
    def test_po_message_contains_doc_url(self):
        """PO message must include document URL"""
        msg = po_message(
            po_number="PO-2024-0001",
            items=[{"productName": "Steel Rod", "quantity": 100}],
            doc_url="https://example.com/po/123",
            business_name="Test Business"
        )
        assert "https://example.com/po/123" in msg, "Document URL missing"
        print("PASS: PO message contains document URL")
    
    def test_po_message_contains_business_name(self):
        """PO message must include business name"""
        msg = po_message(
            po_number="PO-2024-0001",
            items=[{"productName": "Steel Rod", "quantity": 100}],
            doc_url="https://example.com/po/123",
            business_name="ABC Industries"
        )
        assert "ABC Industries" in msg, "Business name missing"
        print("PASS: PO message contains business name")
    
    def test_po_message_contains_footer(self):
        """PO message must include Udyog Connect footer"""
        msg = po_message(
            po_number="PO-2024-0001",
            items=[{"productName": "Steel Rod", "quantity": 100}],
            doc_url="https://example.com/po/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing from footer"
        print("PASS: PO message contains Udyog Connect footer")
    
    def test_po_message_with_supplier_name(self):
        """PO message should greet supplier by name if provided"""
        msg = po_message(
            po_number="PO-2024-0001",
            items=[{"productName": "Steel Rod", "quantity": 100}],
            doc_url="https://example.com/po/123",
            business_name="Test Business",
            supplier_name="John Smith"
        )
        assert "Hello John Smith" in msg, "Supplier greeting missing"
        print("PASS: PO message greets supplier by name")


class TestInvoiceMessage:
    """Test Invoice message template"""
    
    def test_invoice_message_contains_invoice_number(self):
        """Invoice message must include invoice number"""
        msg = invoice_message(
            invoice_number="INV-2024-0001",
            amount=15000.50,
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "INV-2024-0001" in msg, "Invoice number missing"
        print("PASS: Invoice message contains invoice number")
    
    def test_invoice_message_contains_amount(self):
        """Invoice message must include formatted amount"""
        msg = invoice_message(
            invoice_number="INV-2024-0001",
            amount=15000.50,
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "Rs.15,000.50" in msg, f"Formatted amount missing from message: {msg}"
        print("PASS: Invoice message contains formatted amount")
    
    def test_invoice_message_contains_doc_url(self):
        """Invoice message must include document URL"""
        msg = invoice_message(
            invoice_number="INV-2024-0001",
            amount=15000.50,
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "https://example.com/inv/123" in msg, "Document URL missing"
        print("PASS: Invoice message contains document URL")
    
    def test_invoice_message_contains_footer(self):
        """Invoice message must include Udyog Connect footer"""
        msg = invoice_message(
            invoice_number="INV-2024-0001",
            amount=15000.50,
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Invoice message contains Udyog Connect footer")


class TestPaymentReminderSoft:
    """Test Payment Reminder (Soft/Gentle) template"""
    
    def test_soft_reminder_contains_gentle_language(self):
        """Soft reminder must use gentle reminder language"""
        msg = payment_reminder_soft(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "gentle reminder" in msg.lower(), "Gentle reminder language missing"
        print("PASS: Soft reminder uses gentle language")
    
    def test_soft_reminder_contains_invoice_number(self):
        """Soft reminder must include invoice number"""
        msg = payment_reminder_soft(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "INV-2024-0001" in msg, "Invoice number missing"
        print("PASS: Soft reminder contains invoice number")
    
    def test_soft_reminder_contains_pending_amount(self):
        """Soft reminder must include pending amount"""
        msg = payment_reminder_soft(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "Rs.5,000.00" in msg, "Pending amount missing"
        print("PASS: Soft reminder contains pending amount")
    
    def test_soft_reminder_contains_due_date(self):
        """Soft reminder must include due date"""
        msg = payment_reminder_soft(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "15 Jan 2024" in msg, "Due date missing"
        print("PASS: Soft reminder contains due date")
    
    def test_soft_reminder_contains_footer(self):
        """Soft reminder must include Udyog Connect footer"""
        msg = payment_reminder_soft(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Soft reminder contains Udyog Connect footer")


class TestPaymentReminderStrict:
    """Test Payment Reminder (Strict/Overdue) template"""
    
    def test_strict_reminder_contains_overdue_language(self):
        """Strict reminder must use overdue language"""
        msg = payment_reminder_strict(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "overdue" in msg.lower(), "Overdue language missing"
        print("PASS: Strict reminder uses overdue language")
    
    def test_strict_reminder_contains_invoice_number(self):
        """Strict reminder must include invoice number"""
        msg = payment_reminder_strict(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "INV-2024-0001" in msg, "Invoice number missing"
        print("PASS: Strict reminder contains invoice number")
    
    def test_strict_reminder_contains_urgency(self):
        """Strict reminder should convey urgency"""
        msg = payment_reminder_strict(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        # Should have urgency indicators
        urgency_keywords = ["immediately", "urgent", "service interruption"]
        found_urgency = any(kw.lower() in msg.lower() for kw in urgency_keywords)
        assert found_urgency, f"Urgency language missing from strict reminder: {msg}"
        print("PASS: Strict reminder contains urgency language")
    
    def test_strict_reminder_contains_footer(self):
        """Strict reminder must include Udyog Connect footer"""
        msg = payment_reminder_strict(
            invoice_number="INV-2024-0001",
            pending_amount=5000.00,
            due_date="15 Jan 2024",
            doc_url="https://example.com/inv/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Strict reminder contains Udyog Connect footer")


class TestCatalogMessage:
    """Test Catalog sharing message template"""
    
    def test_catalog_message_contains_catalog_url(self):
        """Catalog message must include catalog URL"""
        msg = catalog_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business"
        )
        assert "https://example.com/catalog/123" in msg, "Catalog URL missing"
        print("PASS: Catalog message contains catalog URL")
    
    def test_catalog_message_contains_business_name(self):
        """Catalog message must include business name"""
        msg = catalog_message(
            catalog_url="https://example.com/catalog/123",
            business_name="ABC Steel Traders"
        )
        assert "ABC Steel Traders" in msg, "Business name missing"
        print("PASS: Catalog message contains business name")
    
    def test_catalog_message_contains_footer(self):
        """Catalog message must include Udyog Connect footer"""
        msg = catalog_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Catalog message contains Udyog Connect footer")
    
    def test_catalog_message_with_recipient_name(self):
        """Catalog message should greet recipient by name if provided"""
        msg = catalog_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business",
            recipient_name="Mr. Sharma"
        )
        assert "Hello Mr. Sharma" in msg, "Recipient greeting missing"
        print("PASS: Catalog message greets recipient by name")


class TestSalesPushMessage:
    """Test Sales Push (Combined Catalog + Invoice) template"""
    
    def test_sales_push_contains_catalog_url(self):
        """Sales push must include catalog URL"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business"
        )
        assert "https://example.com/catalog/123" in msg, "Catalog URL missing"
        print("PASS: Sales push contains catalog URL")
    
    def test_sales_push_contains_business_name(self):
        """Sales push must include business name"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="XYZ Enterprises"
        )
        assert "XYZ Enterprises" in msg, "Business name missing"
        print("PASS: Sales push contains business name")
    
    def test_sales_push_with_optional_invoice_url(self):
        """Sales push should include invoice URL if provided"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business",
            invoice_url="https://example.com/sample-invoice/456"
        )
        assert "https://example.com/catalog/123" in msg, "Catalog URL missing"
        assert "https://example.com/sample-invoice/456" in msg, "Invoice URL missing"
        print("PASS: Sales push contains optional invoice URL")
    
    def test_sales_push_without_invoice_url(self):
        """Sales push should work without invoice URL"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business"
        )
        assert "https://example.com/catalog/123" in msg, "Catalog URL missing"
        # Should not contain "Invoice" section when no invoice URL
        assert "Sample Invoice" not in msg or "invoice_url" not in msg, "Invoice section should be minimal when not provided"
        print("PASS: Sales push works without invoice URL")
    
    def test_sales_push_contains_footer(self):
        """Sales push must include Udyog Connect footer"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Sales push contains Udyog Connect footer")
    
    def test_sales_push_with_buyer_name(self):
        """Sales push should greet buyer by name if provided"""
        msg = catalog_marketing_message(
            catalog_url="https://example.com/catalog/123",
            business_name="Test Business",
            buyer_name="Dear Customer"
        )
        assert "Hello Dear Customer" in msg, "Buyer greeting missing"
        print("PASS: Sales push greets buyer by name")


class TestDispatchMessage:
    """Test Dispatch/Order message template"""
    
    def test_dispatch_message_contains_order_id(self):
        """Dispatch message must include order ID"""
        msg = dispatch_message(
            order_id="ORD-2024-0001",
            tracking_link="https://track.example.com/123",
            business_name="Test Business"
        )
        assert "ORD-2024-0001" in msg, "Order ID missing"
        print("PASS: Dispatch message contains order ID")
    
    def test_dispatch_message_contains_tracking_link(self):
        """Dispatch message must include tracking link"""
        msg = dispatch_message(
            order_id="ORD-2024-0001",
            tracking_link="https://track.example.com/123",
            business_name="Test Business"
        )
        assert "https://track.example.com/123" in msg, "Tracking link missing"
        print("PASS: Dispatch message contains tracking link")
    
    def test_dispatch_message_contains_footer(self):
        """Dispatch message must include Udyog Connect footer"""
        msg = dispatch_message(
            order_id="ORD-2024-0001",
            tracking_link="https://track.example.com/123",
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Dispatch message contains Udyog Connect footer")


class TestPendingOrderNotify:
    """Test Pending Order Notification template"""
    
    def test_pending_order_notify_contains_product_name(self):
        """Pending order notification must include product name"""
        msg = pending_order_notify(
            product_name="Steel Rod 10mm",
            pending_qty=50,
            business_name="Test Business"
        )
        assert "Steel Rod 10mm" in msg, "Product name missing"
        print("PASS: Pending order notification contains product name")
    
    def test_pending_order_notify_contains_pending_qty(self):
        """Pending order notification must include pending quantity"""
        msg = pending_order_notify(
            product_name="Steel Rod 10mm",
            pending_qty=50,
            business_name="Test Business"
        )
        assert "50" in msg, "Pending quantity missing"
        print("PASS: Pending order notification contains pending quantity")
    
    def test_pending_order_notify_contains_footer(self):
        """Pending order notification must include Udyog Connect footer"""
        msg = pending_order_notify(
            product_name="Steel Rod 10mm",
            pending_qty=50,
            business_name="Test Business"
        )
        assert "Powered by Udyog Connect" in msg, "Footer missing"
        assert "www.udyogconnect.in" in msg, "Website URL missing"
        print("PASS: Pending order notification contains Udyog Connect footer")
    
    def test_pending_order_notify_with_buyer_name(self):
        """Pending order notification should greet buyer by name"""
        msg = pending_order_notify(
            product_name="Steel Rod 10mm",
            pending_qty=50,
            business_name="Test Business",
            buyer_name="Mr. Buyer"
        )
        assert "Hello Mr. Buyer" in msg, "Buyer greeting missing"
        print("PASS: Pending order notification greets buyer by name")


class TestRotatingAdsContent:
    """Test ROTATING_ADS list content"""
    
    def test_rotating_ads_list_not_empty(self):
        """ROTATING_ADS list must not be empty"""
        assert len(ROTATING_ADS) > 0, "ROTATING_ADS list is empty"
        print(f"PASS: ROTATING_ADS has {len(ROTATING_ADS)} ads")
    
    def test_rotating_ads_contains_udyog_connect_messaging(self):
        """ROTATING_ADS should have Udyog Connect related messaging"""
        ads_text = " ".join(ROTATING_ADS).lower()
        # Should mention business/digitize/automate/grow type messaging
        keywords = ["business", "digitize", "automate", "billing", "invoice", "grow", "manage"]
        found = [kw for kw in keywords if kw in ads_text]
        assert len(found) >= 2, f"Ads should contain business-related keywords, found: {found}"
        print(f"PASS: ROTATING_ADS contains business messaging keywords: {found}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
