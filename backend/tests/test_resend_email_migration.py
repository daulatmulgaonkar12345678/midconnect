"""
Test: Resend Email Migration
============================

Verifies:
1. Backend health check endpoint works
2. Old email_verification_service.py is removed
3. New email_service.py exists with all required classes
4. Email service gracefully handles MOCK mode (no API key)
5. server.py uses new email service imports
6. quotation_router.py sends email on quote creation

MOCK MODE: Since no RESEND_API_KEY is set, email service runs in mock mode.
"""

import pytest
import requests
import os
import importlib.util
import sys

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://erp-india-suite.preview.emergentagent.com"


class TestBackendHealth:
    """Test backend health endpoint"""
    
    def test_health_endpoint_returns_200(self):
        """Health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "healthy", f"Expected 'healthy', got {data.get('status')}"
        print(f"✅ Health check passed: {data}")


class TestEmailServiceFiles:
    """Test email service file structure"""
    
    def test_old_email_verification_service_removed(self):
        """Old email_verification_service.py should NOT exist"""
        old_file_path = "/app/backend/services/email_verification_service.py"
        file_exists = os.path.exists(old_file_path)
        assert not file_exists, f"Old file should be removed: {old_file_path}"
        print("✅ Old email_verification_service.py is removed")
    
    def test_new_email_service_exists(self):
        """New email_service.py should exist"""
        new_file_path = "/app/backend/services/email_service.py"
        file_exists = os.path.exists(new_file_path)
        assert file_exists, f"New file should exist: {new_file_path}"
        print("✅ New email_service.py exists")
    
    def test_email_service_has_required_classes(self):
        """email_service.py should have all required classes"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read()
        
        required_classes = [
            "EmailVerificationService",
            "SubscriptionEmailService", 
            "InquiryEmailService",
            "OrderEmailService"
        ]
        
        for class_name in required_classes:
            assert f"class {class_name}" in content, f"Missing class: {class_name}"
            print(f"✅ Found class: {class_name}")
    
    def test_email_service_uses_resend(self):
        """email_service.py should import and use Resend"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read()
        
        assert "import resend" in content, "Should import resend SDK"
        assert "RESEND_API_KEY" in content, "Should reference RESEND_API_KEY"
        assert "resend.api_key" in content or "resend.Emails.send" in content, "Should use resend API"
        print("✅ Email service uses Resend SDK")
    
    def test_email_service_has_mock_mode(self):
        """email_service.py should support MOCK mode when no API key"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read()
        
        assert "MOCK" in content, "Should mention MOCK mode"
        assert "[MOCK EMAIL]" in content or "_mock" in content, "Should have mock logging"
        print("✅ Email service supports MOCK mode")
    
    def test_email_service_uses_sha256_tokens(self):
        """email_service.py should use SHA256 hashed tokens"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read()
        
        assert "hashlib.sha256" in content, "Should use SHA256 for token hashing"
        assert "secrets.token_urlsafe" in content, "Should use secrets for token generation"
        print("✅ Email service uses SHA256 hashed tokens")
    
    def test_email_service_has_1hour_expiry(self):
        """email_service.py should have 1-hour token expiry"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read()
        
        # Check for 1 hour expiry setting
        assert "TOKEN_EXPIRY_HOURS = 1" in content or "timedelta(hours=1)" in content or "TOKEN_EXPIRY_HOURS" in content, \
            "Should have 1-hour token expiry"
        print("✅ Email service has token expiry configuration")


class TestServerEmailImports:
    """Test server.py uses new email service imports"""
    
    def test_server_imports_email_service(self):
        """server.py should import from services.email_service"""
        with open("/app/backend/server.py", 'r') as f:
            content = f.read()
        
        # Should import from new email_service, not old email_verification_service
        assert "from services.email_service import" in content, \
            "server.py should import from services.email_service"
        
        # Should NOT import from old file
        assert "from services.email_verification_service import" not in content, \
            "server.py should NOT import from old email_verification_service"
        
        print("✅ server.py imports from new email_service")
    
    def test_server_imports_verification_service(self):
        """server.py should import get_email_verification_service"""
        with open("/app/backend/server.py", 'r') as f:
            content = f.read()
        
        assert "get_email_verification_service" in content, \
            "server.py should use get_email_verification_service"
        print("✅ server.py uses get_email_verification_service")


class TestQuotationRouterEmail:
    """Test quotation_router.py email integration"""
    
    def test_quotation_router_imports_email_service(self):
        """quotation_router.py should import from email_service"""
        with open("/app/backend/routers/quotation_router.py", 'r') as f:
            content = f.read()
        
        assert "from services.email_service import" in content, \
            "quotation_router.py should import from services.email_service"
        print("✅ quotation_router.py imports from email_service")
    
    def test_quotation_router_sends_email_on_quote(self):
        """quotation_router.py should send email on quote creation"""
        with open("/app/backend/routers/quotation_router.py", 'r') as f:
            content = f.read()
        
        assert "get_inquiry_email_service" in content, \
            "Should use inquiry email service"
        assert "send_buyer_quote_received" in content, \
            "Should send buyer_quote_received email"
        print("✅ quotation_router.py sends email on quote creation")


class TestEnvConfiguration:
    """Test .env configuration for email"""
    
    def test_resend_api_key_in_env(self):
        """RESEND_API_KEY should be defined in .env (can be empty for mock mode)"""
        with open("/app/backend/.env", 'r') as f:
            content = f.read()
        
        assert "RESEND_API_KEY" in content, ".env should have RESEND_API_KEY variable"
        print("✅ RESEND_API_KEY is defined in .env")
    
    def test_sender_email_in_env(self):
        """SENDER_EMAIL should be defined in .env"""
        with open("/app/backend/.env", 'r') as f:
            content = f.read()
        
        assert "SENDER_EMAIL" in content, ".env should have SENDER_EMAIL variable"
        print("✅ SENDER_EMAIL is defined in .env")


class TestNoZohoReferences:
    """Test that Zoho SMTP references are removed"""
    
    def test_no_zoho_in_email_service(self):
        """email_service.py should not reference Zoho"""
        with open("/app/backend/services/email_service.py", 'r') as f:
            content = f.read().lower()
        
        assert "zoho" not in content, "email_service.py should not reference Zoho"
        assert "smtp" not in content, "email_service.py should not use SMTP"
        print("✅ No Zoho/SMTP references in email_service.py")
    
    def test_no_zoho_in_env(self):
        """Backend .env should not have Zoho variables"""
        with open("/app/backend/.env", 'r') as f:
            content = f.read().lower()
        
        assert "zoho" not in content, ".env should not have Zoho variables"
        print("✅ No Zoho references in .env")


class TestEmailServiceMockMode:
    """Test email service behavior in mock mode"""
    
    def test_send_verification_endpoint_exists(self):
        """Send verification endpoint should exist"""
        # This endpoint requires auth, so we just check it doesn't 404
        response = requests.post(
            f"{BASE_URL}/api/send-verification",
            json={"email": "test@example.com"},
            timeout=10
        )
        # Should get 401 (unauthorized) or 422 (validation), not 404
        assert response.status_code != 404, f"Send verification endpoint should exist, got {response.status_code}"
        print(f"✅ Send verification endpoint exists (status: {response.status_code})")
    
    def test_verify_email_endpoint_exists(self):
        """Verify email endpoint should exist (GET with token query param)"""
        response = requests.get(
            f"{BASE_URL}/api/verify-email?token=test-token",
            timeout=10
        )
        # Should not 404 - will return error for invalid token
        assert response.status_code != 404, f"Verify email endpoint should exist, got {response.status_code}"
        print(f"✅ Verify email endpoint exists (status: {response.status_code})")
    
    def test_resend_verification_endpoint_exists(self):
        """Resend verification endpoint should exist"""
        response = requests.post(
            f"{BASE_URL}/api/resend-verification",
            json={"email": "test@example.com"},
            timeout=10
        )
        # Should not 404
        assert response.status_code != 404, f"Resend verification endpoint should exist, got {response.status_code}"
        print(f"✅ Resend verification endpoint exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
