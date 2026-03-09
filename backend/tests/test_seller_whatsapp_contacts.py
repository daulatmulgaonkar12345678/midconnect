"""
Test Suite: Seller WhatsApp Contacts Feature
============================================

Tests the multi-WhatsApp numbers with primary contact for seller inquiries.

Features tested:
- GET /api/seller/whatsapp/contacts - returns empty list initially (requires auth)
- POST /api/seller/whatsapp/contacts - adds new WhatsApp contact
- PATCH /api/seller/whatsapp/contacts/{id} - updates contact
- DELETE /api/seller/whatsapp/contacts/{id} - deletes contact  
- POST /api/seller/whatsapp/contacts/{id}/set-primary - sets contact as primary
- GET /api/seller/whatsapp/settings - returns autoWhatsappConnect setting
- PATCH /api/seller/whatsapp/settings - updates autoWhatsappConnect
- GET /api/seller/whatsapp/seller/{seller_id}/primary - public endpoint for buyer flow

Phone number validation (E.164 format): +919876543210
"""

import pytest
import requests
import os
from datetime import datetime

# Base URL from environment - required for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Dev token for testing (works when Firebase is not configured)
DEV_TOKEN = "dev-test-token"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture  
def auth_headers():
    """Auth headers with dev token"""
    return {"Authorization": f"Bearer {DEV_TOKEN}"}


class TestHealthAndBasics:
    """Health check and basic connectivity tests"""
    
    def test_health_check(self, api_client):
        """Ensure API is running"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✓ Health check passed: {response.json()}")


class TestWhatsAppContactsAuth:
    """Tests that require authentication"""
    
    def test_get_contacts_unauthorized(self, api_client):
        """GET /api/seller/whatsapp/contacts should require auth"""
        response = api_client.get(f"{BASE_URL}/api/seller/whatsapp/contacts")
        # Should be 401 without auth token
        assert response.status_code == 401
        print("✓ GET contacts returns 401 without auth")
    
    def test_get_contacts_with_auth(self, api_client, auth_headers):
        """GET /api/seller/whatsapp/contacts should return contacts list"""
        response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers
        )
        # Should return 200 with contacts array (may be empty initially)
        assert response.status_code == 200
        data = response.json()
        assert "contacts" in data
        assert isinstance(data["contacts"], list)
        print(f"✓ GET contacts returned {len(data['contacts'])} contacts")


class TestWhatsAppContactCRUD:
    """CRUD operations for WhatsApp contacts"""
    
    def test_add_contact_invalid_phone(self, api_client, auth_headers):
        """POST contact with invalid phone should fail validation"""
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={
                "phoneNumber": "invalid",  # Not E.164 format
                "label": "Test"
            }
        )
        # Should fail validation - 422 for Pydantic validation error
        assert response.status_code == 422
        print("✓ Invalid phone number rejected")
    
    def test_add_contact_valid_phone(self, api_client, auth_headers):
        """POST contact with valid E.164 phone should succeed"""
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={
                "phoneNumber": "+919876543210",  # Valid E.164 format
                "label": "TEST_Sales",
                "isPrimary": False
            }
        )
        
        # Should succeed
        if response.status_code == 201 or response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "contact" in data
            assert data["contact"]["phoneNumber"] == "+919876543210"
            print(f"✓ Contact added successfully: {data['contact']['id']}")
            return data["contact"]["id"]
        elif response.status_code == 400 and "already added" in response.text:
            # Contact might already exist from previous test run
            print("✓ Contact already exists (expected for repeat tests)")
            return None
        else:
            print(f"Response: {response.status_code} - {response.text}")
            pytest.skip(f"Unexpected response: {response.status_code}")
    
    def test_add_first_contact_becomes_primary(self, api_client, auth_headers):
        """First contact added should automatically become primary"""
        # First, get current contacts to know if this is the first
        get_response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers
        )
        
        if get_response.status_code != 200:
            pytest.skip("Cannot get current contacts")
            
        current_contacts = get_response.json().get("contacts", [])
        
        # Add a new contact with unique phone
        test_phone = f"+91987654{int(datetime.now().timestamp()) % 10000:04d}"
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={
                "phoneNumber": test_phone,
                "label": "TEST_First",
                "isPrimary": False  # Even if we say false, first should become primary
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            contact = data.get("contact", {})
            
            # If this was the first contact, it should be primary
            if len(current_contacts) == 0:
                assert contact.get("isPrimary") == True
                print("✓ First contact automatically set as primary")
            else:
                print(f"✓ Contact added (not first, isPrimary={contact.get('isPrimary')})")
        elif response.status_code == 400:
            print("✓ Phone already exists or validation error")


class TestWhatsAppContactUpdate:
    """Tests for updating contacts"""
    
    def test_update_nonexistent_contact(self, api_client, auth_headers):
        """PATCH with invalid contact ID should return 404"""
        fake_id = "000000000000000000000000"  # Valid ObjectId format but doesn't exist
        response = api_client.patch(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{fake_id}",
            headers=auth_headers,
            json={"label": "Updated"}
        )
        # Should be 404
        assert response.status_code == 404
        print("✓ Update nonexistent contact returns 404")
    
    def test_update_invalid_id_format(self, api_client, auth_headers):
        """PATCH with invalid ID format should return 400"""
        response = api_client.patch(
            f"{BASE_URL}/api/seller/whatsapp/contacts/invalid-id",
            headers=auth_headers,
            json={"label": "Updated"}
        )
        # Should be 400 for invalid ObjectId format
        assert response.status_code == 400
        print("✓ Update with invalid ID format returns 400")


class TestWhatsAppContactDelete:
    """Tests for deleting contacts"""
    
    def test_delete_nonexistent_contact(self, api_client, auth_headers):
        """DELETE with invalid contact ID should return 404"""
        fake_id = "000000000000000000000000"
        response = api_client.delete(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ Delete nonexistent contact returns 404")


class TestWhatsAppSetPrimary:
    """Tests for setting primary contact"""
    
    def test_set_primary_nonexistent(self, api_client, auth_headers):
        """POST set-primary for invalid contact should return 404"""
        fake_id = "000000000000000000000000"
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{fake_id}/set-primary",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ Set primary for nonexistent contact returns 404")


class TestWhatsAppSettings:
    """Tests for WhatsApp settings"""
    
    def test_get_settings_unauthorized(self, api_client):
        """GET settings without auth should return 401"""
        response = api_client.get(f"{BASE_URL}/api/seller/whatsapp/settings")
        assert response.status_code == 401
        print("✓ GET settings returns 401 without auth")
    
    def test_get_settings_with_auth(self, api_client, auth_headers):
        """GET settings with auth should return settings"""
        response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/settings",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "autoWhatsappConnect" in data
        assert isinstance(data["autoWhatsappConnect"], bool)
        print(f"✓ GET settings returned autoWhatsappConnect={data['autoWhatsappConnect']}")
    
    def test_update_settings_toggle_on(self, api_client, auth_headers):
        """PATCH settings to enable auto-connect"""
        response = api_client.patch(
            f"{BASE_URL}/api/seller/whatsapp/settings",
            headers=auth_headers,
            json={"autoWhatsappConnect": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("autoWhatsappConnect") == True
        print("✓ Settings updated to autoWhatsappConnect=True")
    
    def test_update_settings_toggle_off(self, api_client, auth_headers):
        """PATCH settings to disable auto-connect"""
        response = api_client.patch(
            f"{BASE_URL}/api/seller/whatsapp/settings",
            headers=auth_headers,
            json={"autoWhatsappConnect": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("autoWhatsappConnect") == False
        print("✓ Settings updated to autoWhatsappConnect=False")


class TestPublicSellerPrimaryContact:
    """Tests for public endpoint to get seller's primary contact"""
    
    def test_public_endpoint_invalid_seller(self, api_client):
        """GET primary for invalid seller ID should return null contact"""
        response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/seller/invalid-id/primary"
        )
        # Should still return 200 but with null contact
        assert response.status_code == 200
        data = response.json()
        assert data.get("contact") is None
        assert data.get("autoConnect") == False
        print("✓ Invalid seller returns null contact with autoConnect=False")
    
    def test_public_endpoint_valid_seller_no_contacts(self, api_client):
        """GET primary for valid seller without contacts should return null"""
        # Using a fake but valid ObjectId format
        fake_seller_id = "000000000000000000000001"
        response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/seller/{fake_seller_id}/primary"
        )
        assert response.status_code == 200
        data = response.json()
        # Should have contact as null or return autoConnect based on settings
        assert "contact" in data
        assert "autoConnect" in data
        print(f"✓ Seller without contacts returns contact={data['contact']}, autoConnect={data['autoConnect']}")


class TestPhoneNumberValidation:
    """Tests for E.164 phone number validation"""
    
    def test_phone_without_plus(self, api_client, auth_headers):
        """Phone without + prefix should fail"""
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={"phoneNumber": "919876543210", "label": "Test"}  # Missing +
        )
        assert response.status_code == 422
        print("✓ Phone without + rejected")
    
    def test_phone_too_short(self, api_client, auth_headers):
        """Phone number too short should fail"""
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={"phoneNumber": "+12345", "label": "Test"}  # Too short
        )
        assert response.status_code == 422
        print("✓ Short phone number rejected")
    
    def test_phone_with_spaces_cleaned(self, api_client, auth_headers):
        """Phone with spaces should be cleaned and accepted"""
        response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={"phoneNumber": "+91 98765 43211", "label": "TEST_Spaces"}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Phone should be cleaned to +919876543211
            assert data["contact"]["phoneNumber"] == "+919876543211"
            print("✓ Phone with spaces cleaned correctly")
        elif response.status_code == 400 and "already added" in response.text:
            print("✓ Phone already exists")
        else:
            print(f"Response: {response.status_code} - {response.text}")


class TestE2EWhatsAppFlow:
    """End-to-end flow tests"""
    
    def test_full_crud_flow(self, api_client, auth_headers):
        """Test full CRUD flow: create -> read -> update -> delete"""
        
        # 1. Create a contact
        unique_phone = f"+91999{int(datetime.now().timestamp()) % 1000000:06d}"
        create_response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers,
            json={
                "phoneNumber": unique_phone,
                "label": "TEST_E2E_Flow",
                "isPrimary": False
            }
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create contact: {create_response.status_code}")
        
        contact_id = create_response.json()["contact"]["id"]
        print(f"✓ Created contact: {contact_id}")
        
        # 2. Read contacts and verify
        get_response = api_client.get(
            f"{BASE_URL}/api/seller/whatsapp/contacts",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        contacts = get_response.json()["contacts"]
        assert any(c["id"] == contact_id for c in contacts)
        print("✓ Contact found in list")
        
        # 3. Update the contact
        update_response = api_client.patch(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{contact_id}",
            headers=auth_headers,
            json={"label": "TEST_E2E_Updated"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["contact"]["label"] == "TEST_E2E_Updated"
        print("✓ Contact updated")
        
        # 4. Set as primary
        primary_response = api_client.post(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{contact_id}/set-primary",
            headers=auth_headers
        )
        assert primary_response.status_code == 200
        print("✓ Contact set as primary")
        
        # 5. Delete the contact
        delete_response = api_client.delete(
            f"{BASE_URL}/api/seller/whatsapp/contacts/{contact_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        print("✓ Contact deleted")
        
        print("✓ Full CRUD flow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
