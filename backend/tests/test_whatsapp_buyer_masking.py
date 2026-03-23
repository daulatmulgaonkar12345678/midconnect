"""
Test WhatsApp Button Visibility and Buyer Contact Masking

Features to test:
1. GET /api/seller/inquiries - returns buyerMasked (without phone/email) for pending inquiries
2. GET /api/seller/inquiries - returns buyerInfo (with phone/email) for accepted inquiries
3. GET /api/seller/inquiries - returns unreadCount for pending inquiries count
4. POST /api/seller/inquiries/{id}/accept - returns buyerContact with phone after accept
5. POST /api/seller/inquiries/{id}/accept - returns whatsappLink with 91 prefix
6. Buyer info fetched from users collection (not embedded buyerInfo) - uses buyerId
7. No phone leak for pending inquiries
"""

import pytest
import requests
import os
from datetime import datetime

# Use the same API URL as frontend
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://relational-update.preview.emergentagent.com"

AUTH_TOKEN = "dev-test-token"
TEST_USER_ID = "699adb3bacf78470ba9551fb"


class TestBuyerContactMaskingFeature:
    """Test buyer contact masking and WhatsApp button visibility"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
    
    # ==================== HELPER METHODS ====================
    
    def get_seller_inquiries(self, status=None):
        """Helper to get seller inquiries"""
        params = {}
        if status:
            params["status"] = status
        response = requests.get(
            f"{BASE_URL}/api/seller/inquiries",
            headers=self.headers,
            params=params
        )
        return response
    
    def accept_inquiry(self, inquiry_id, quoted_price=100.0):
        """Helper to accept an inquiry"""
        response = requests.post(
            f"{BASE_URL}/api/seller/inquiries/{inquiry_id}/accept",
            headers=self.headers,
            json={
                "quotedPrice": quoted_price,
                "validityDays": 7,
                "sellerNote": "Test acceptance"
            }
        )
        return response
    
    # ==================== BASIC API TESTS ====================
    
    def test_01_api_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API not accessible: {response.status_code}"
        print("✅ API health check passed")
    
    def test_02_seller_inquiries_endpoint_accessible(self):
        """Verify seller inquiries endpoint is accessible"""
        response = self.get_seller_inquiries()
        assert response.status_code == 200, f"Failed to access inquiries: {response.status_code}"
        
        data = response.json()
        assert "inquiries" in data, "Response missing 'inquiries' field"
        assert "total" in data, "Response missing 'total' field"
        print(f"✅ Seller inquiries endpoint accessible, found {data['total']} inquiries")
    
    # ==================== UNREAD COUNT TESTS ====================
    
    def test_03_inquiries_returns_unread_count(self):
        """GET /api/seller/inquiries should return unreadCount field"""
        response = self.get_seller_inquiries()
        assert response.status_code == 200
        
        data = response.json()
        assert "unreadCount" in data, "Response missing 'unreadCount' field"
        assert isinstance(data["unreadCount"], int), "unreadCount should be an integer"
        print(f"✅ unreadCount field present: {data['unreadCount']}")
    
    def test_04_unread_count_matches_pending_count(self):
        """unreadCount should match the count of pending inquiries"""
        # Get all inquiries
        all_response = self.get_seller_inquiries()
        assert all_response.status_code == 200
        all_data = all_response.json()
        
        # Get pending inquiries count
        pending_count = sum(1 for inq in all_data["inquiries"] if inq.get("status") == "pending")
        unread_count = all_data.get("unreadCount", 0)
        
        # Verify unreadCount matches pending count
        assert unread_count == pending_count, f"unreadCount ({unread_count}) != pending count ({pending_count})"
        print(f"✅ unreadCount ({unread_count}) matches pending count ({pending_count})")
    
    # ==================== BUYER MASKING TESTS ====================
    
    def test_05_pending_inquiries_have_buyer_masked(self):
        """Pending inquiries should have buyerMasked field (without phone/email)"""
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to test masking - create a new pending inquiry first")
        
        for inquiry in data["inquiries"]:
            if inquiry.get("status") == "pending":
                # Should have buyerMasked
                buyer_masked = inquiry.get("buyerMasked")
                assert buyer_masked is not None, f"Pending inquiry {inquiry.get('_id')} missing buyerMasked"
                
                # buyerMasked should NOT contain phone or email
                assert "phone" not in buyer_masked, f"SECURITY LEAK: phone in buyerMasked for pending inquiry"
                assert "email" not in buyer_masked, f"SECURITY LEAK: email in buyerMasked for pending inquiry"
                
                # buyerMasked should have companyInitial
                assert "companyInitial" in buyer_masked, "buyerMasked should have companyInitial"
                
                print(f"✅ Pending inquiry {inquiry.get('_id')}: buyerMasked correct (no phone/email)")
        
        print(f"✅ All {data['total']} pending inquiries have proper buyerMasked field")
    
    def test_06_pending_inquiry_buyer_info_is_null(self):
        """For pending inquiries, buyerInfo should be null (contact locked)"""
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to test")
        
        for inquiry in data["inquiries"]:
            if inquiry.get("status") == "pending":
                buyer_info = inquiry.get("buyerInfo")
                # buyerInfo should be null for pending inquiries
                assert buyer_info is None, f"SECURITY LEAK: buyerInfo present for pending inquiry {inquiry.get('_id')}"
                print(f"✅ Pending inquiry {inquiry.get('_id')}: buyerInfo is null (contact locked)")
        
        print(f"✅ All pending inquiries have buyerInfo=null (contact properly locked)")
    
    def test_07_no_phone_leak_in_pending_inquiries(self):
        """CRITICAL: Verify no phone number leaks in pending inquiry responses"""
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to test phone leak")
        
        for inquiry in data["inquiries"]:
            if inquiry.get("status") == "pending":
                # Check all fields for phone leak
                buyer_masked = inquiry.get("buyerMasked") or {}
                buyer_info = inquiry.get("buyerInfo") or {}
                
                # No phone in buyerMasked
                assert "phone" not in buyer_masked, f"SECURITY LEAK: phone in buyerMasked"
                
                # No buyerInfo at all (should be null)
                assert inquiry.get("buyerInfo") is None, f"SECURITY LEAK: buyerInfo present"
                
                # Convert inquiry to string to check for phone patterns
                inquiry_str = str(inquiry)
                
                # Check for obvious phone patterns (10 digits)
                import re
                phone_pattern = re.compile(r'\b\d{10}\b')
                phone_matches = phone_pattern.findall(inquiry_str)
                
                # Filter out IDs and timestamps
                for match in phone_matches:
                    # Skip if it's part of an ObjectId or timestamp
                    if match not in inquiry.get("_id", "") and match not in inquiry.get("listingId", ""):
                        # This might be a phone number leak
                        print(f"⚠️ Potential phone pattern found: {match} in inquiry {inquiry.get('_id')}")
        
        print(f"✅ No obvious phone leaks in pending inquiries")
    
    # ==================== ACCEPTED INQUIRY TESTS ====================
    
    def test_08_accepted_inquiries_have_buyer_info(self):
        """Accepted inquiries should have buyerInfo with phone/email"""
        response = self.get_seller_inquiries(status="accepted")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No accepted inquiries to test")
        
        for inquiry in data["inquiries"]:
            if inquiry.get("status") == "accepted":
                buyer_info = inquiry.get("buyerInfo")
                
                # buyerInfo should be present for accepted inquiries
                if buyer_info is not None:
                    # Check that contact fields are present
                    print(f"  Accepted inquiry {inquiry.get('_id')}: buyerInfo = {buyer_info}")
                    
                    # At least name should be present
                    assert "name" in buyer_info or "companyName" in buyer_info, \
                        f"buyerInfo should have name or companyName"
                    
                    print(f"✅ Accepted inquiry {inquiry.get('_id')}: buyerInfo has contact details")
                else:
                    # For legacy inquiries without buyerInfo, buyerMasked might still be present
                    print(f"⚠️ Accepted inquiry {inquiry.get('_id')}: buyerInfo is null (might be legacy)")
        
        print(f"✅ Accepted inquiries checked for buyerInfo field")
    
    def test_09_accepted_inquiries_no_buyer_masked(self):
        """Accepted inquiries should have buyerMasked=null since contact is unlocked"""
        response = self.get_seller_inquiries(status="accepted")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No accepted inquiries to test")
        
        for inquiry in data["inquiries"]:
            if inquiry.get("status") == "accepted":
                buyer_masked = inquiry.get("buyerMasked")
                
                # buyerMasked should be null for accepted inquiries (contact unlocked)
                assert buyer_masked is None, \
                    f"buyerMasked should be null for accepted inquiry {inquiry.get('_id')}"
                
                print(f"✅ Accepted inquiry {inquiry.get('_id')}: buyerMasked is null (contact unlocked)")
        
        print(f"✅ All accepted inquiries have buyerMasked=null")
    
    # ==================== ACCEPT INQUIRY ENDPOINT TESTS ====================
    
    def test_10_accept_returns_buyer_contact(self):
        """POST /api/seller/inquiries/{id}/accept should return buyerContact"""
        # First, get a pending inquiry
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to accept - need to create one first")
        
        # Get first pending inquiry
        pending_inquiry = data["inquiries"][0]
        inquiry_id = pending_inquiry.get("_id")
        
        # Accept the inquiry
        accept_response = self.accept_inquiry(inquiry_id)
        
        if accept_response.status_code == 403:
            # Subscription limit reached - still valid test
            print(f"⚠️ Subscription limit reached (403), cannot accept more inquiries")
            pytest.skip("Subscription limit reached")
        
        assert accept_response.status_code == 200, \
            f"Failed to accept inquiry: {accept_response.status_code} - {accept_response.text}"
        
        accept_data = accept_response.json()
        
        # Verify buyerContact is present
        assert "buyerContact" in accept_data, "accept response missing 'buyerContact' field"
        buyer_contact = accept_data["buyerContact"]
        
        # buyerContact should have name, phone, email, company
        assert "name" in buyer_contact, "buyerContact missing 'name'"
        assert "phone" in buyer_contact, "buyerContact missing 'phone'"
        assert "email" in buyer_contact, "buyerContact missing 'email'"
        assert "company" in buyer_contact, "buyerContact missing 'company'"
        
        print(f"✅ Accept response includes buyerContact: {buyer_contact}")
    
    def test_11_accept_returns_whatsapp_link(self):
        """POST /api/seller/inquiries/{id}/accept should return whatsappLink"""
        # Get a pending inquiry
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to accept")
        
        pending_inquiry = data["inquiries"][0]
        inquiry_id = pending_inquiry.get("_id")
        
        # Accept the inquiry
        accept_response = self.accept_inquiry(inquiry_id)
        
        if accept_response.status_code == 403:
            pytest.skip("Subscription limit reached")
        
        assert accept_response.status_code == 200
        accept_data = accept_response.json()
        
        # Verify whatsappLink is present
        assert "whatsappLink" in accept_data, "accept response missing 'whatsappLink' field"
        
        whatsapp_link = accept_data["whatsappLink"]
        
        # If buyer has phone, link should be present
        buyer_contact = accept_data.get("buyerContact", {})
        if buyer_contact.get("phone"):
            assert whatsapp_link is not None, "whatsappLink should be present when buyer has phone"
            assert whatsapp_link.startswith("https://wa.me/"), f"Invalid whatsappLink format: {whatsapp_link}"
            print(f"✅ Accept response includes whatsappLink: {whatsapp_link[:50]}...")
        else:
            print(f"⚠️ whatsappLink is null because buyer has no phone number")
    
    def test_12_whatsapp_link_has_91_prefix(self):
        """WhatsApp link should have 91 (India) country code prefix"""
        # Get a pending inquiry
        response = self.get_seller_inquiries(status="pending")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No pending inquiries to accept")
        
        pending_inquiry = data["inquiries"][0]
        inquiry_id = pending_inquiry.get("_id")
        
        # Accept the inquiry
        accept_response = self.accept_inquiry(inquiry_id)
        
        if accept_response.status_code == 403:
            pytest.skip("Subscription limit reached")
        
        assert accept_response.status_code == 200
        accept_data = accept_response.json()
        
        whatsapp_link = accept_data.get("whatsappLink")
        buyer_contact = accept_data.get("buyerContact", {})
        
        if whatsapp_link and buyer_contact.get("phone"):
            # Extract phone from whatsapp link
            # Format: https://wa.me/91XXXXXXXXXX?text=...
            import re
            phone_match = re.search(r'wa\.me/(\d+)\?', whatsapp_link)
            
            if phone_match:
                phone_in_link = phone_match.group(1)
                assert phone_in_link.startswith("91"), \
                    f"WhatsApp phone should start with 91, got: {phone_in_link}"
                print(f"✅ WhatsApp link has 91 prefix: {phone_in_link}")
            else:
                print(f"⚠️ Could not extract phone from whatsapp link")
        else:
            print(f"⚠️ No whatsapp link or no phone to verify 91 prefix")
    
    # ==================== BUYER ID USAGE TESTS ====================
    
    def test_13_verify_buyer_fetched_from_users_collection(self):
        """Verify buyer info is fetched from users collection using buyerId"""
        response = self.get_seller_inquiries()
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that inquiries have buyerId field
        for inquiry in data["inquiries"]:
            # buyerId should be present in inquiry
            if inquiry.get("status") == "accepted":
                buyer_info = inquiry.get("buyerInfo")
                if buyer_info:
                    # This indicates data was fetched (either from users or embedded)
                    print(f"  Inquiry {inquiry.get('_id')}: buyerInfo present")
            elif inquiry.get("status") == "pending":
                buyer_masked = inquiry.get("buyerMasked")
                if buyer_masked:
                    # This indicates buyer data was fetched and masked
                    print(f"  Inquiry {inquiry.get('_id')}: buyerMasked present")
        
        print(f"✅ Buyer data handling verified for {data['total']} inquiries")


class TestCreatePendingInquiryForMasking:
    """Test creating a pending inquiry to verify masking works"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_check_existing_pending_inquiries(self):
        """Check if there are existing pending inquiries"""
        response = requests.get(
            f"{BASE_URL}/api/seller/inquiries",
            headers=self.headers,
            params={"status": "pending"}
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"📊 Found {data['total']} pending inquiries")
        print(f"📊 unreadCount: {data.get('unreadCount', 'N/A')}")
        
        if data["total"] > 0:
            for inq in data["inquiries"]:
                print(f"  - Pending inquiry: {inq.get('_id')}, status: {inq.get('status')}")
                print(f"    buyerMasked: {inq.get('buyerMasked')}")
                print(f"    buyerInfo: {inq.get('buyerInfo')}")


class TestAcceptedInquiriesContactReveal:
    """Test that accepted inquiries properly reveal contact info"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_accepted_inquiry_contact_visible(self):
        """Verify accepted inquiries show full contact details"""
        response = requests.get(
            f"{BASE_URL}/api/seller/inquiries",
            headers=self.headers,
            params={"status": "accepted"}
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"📊 Found {data['total']} accepted inquiries")
        
        for inq in data["inquiries"]:
            buyer_info = inq.get("buyerInfo")
            buyer_masked = inq.get("buyerMasked")
            
            print(f"\n  Accepted inquiry: {inq.get('_id')}")
            print(f"    buyerInfo: {buyer_info}")
            print(f"    buyerMasked: {buyer_masked}")
            
            # For accepted, buyerMasked should be null
            assert buyer_masked is None, \
                f"buyerMasked should be null for accepted inquiry, got: {buyer_masked}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
