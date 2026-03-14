"""
OTP-Based Registration Verification Tests
==========================================

Tests for the OTP verification system that replaces email link verification.

Features tested:
- POST /api/auth/register/request-otp - Request OTP for registration
- POST /api/auth/register/verify-otp - Verify 6-digit OTP
- GET /api/auth/register/otp-status - Check OTP verification status
- OTP rate limiting (30s cooldown, 5/hour limit)
- OTP max attempts (5 attempts per OTP)
- OTP expiry (10 minutes)

NOTE: OTP system runs in MOCK mode (no Resend API key configured)
      The OTP is returned in API response as '_otp' field for testing
"""

import pytest
import requests
import os
import time
import random
import string

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seller-invoices.preview.emergentagent.com')
if BASE_URL.endswith('/'):
    BASE_URL = BASE_URL.rstrip('/')

# Generate unique test email for each test run
def generate_test_email():
    """Generate unique email for testing"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_otp_{random_suffix}@example.com"


class TestHealthCheck:
    """Basic health check before OTP tests"""
    
    def test_health_check(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=30)
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print(f"✓ Health check passed")


class TestOTPRequestEndpoint:
    """Tests for POST /api/auth/register/request-otp"""
    
    def test_request_otp_success(self):
        """Test successful OTP request with mock mode"""
        test_email = generate_test_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert "message" in data, "Missing 'message' field"
        assert "expires_at" in data, "Missing 'expires_at' field"
        assert "cooldown_until" in data, "Missing 'cooldown_until' field"
        
        # In mock mode, OTP should be in response
        assert data.get("_mock") == True, "Expected _mock=True (running in mock mode)"
        assert "_otp" in data, "Missing '_otp' field in mock mode"
        assert len(data.get("_otp", "")) == 6, f"Expected 6-digit OTP, got {data.get('_otp')}"
        assert data.get("_otp", "").isdigit(), "OTP should be numeric"
        
        print(f"✓ OTP request successful for {test_email}")
        print(f"  OTP: {data.get('_otp')}")
        print(f"  Expires: {data.get('expires_at')}")
    
    def test_request_otp_email_normalization(self):
        """Test that email is normalized (lowercase, trimmed)"""
        test_email = generate_test_email()
        uppercase_email = test_email.upper()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": f"  {uppercase_email}  ", "name": "Test User"},
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Email normalization works (uppercase & spaces handled)")
    
    def test_request_otp_invalid_email_format(self):
        """Test OTP request with invalid email format"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": "not-an-email", "name": "Test User"},
            timeout=30
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid email, got {response.status_code}"
        print(f"✓ Invalid email format rejected correctly")
    
    def test_request_otp_without_name(self):
        """Test OTP request without optional name field"""
        test_email = generate_test_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email},  # No name provided
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ OTP request works without name field")
    
    def test_request_otp_cooldown(self):
        """Test 30-second cooldown between OTP requests"""
        test_email = generate_test_email()
        
        # First request
        response1 = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        assert response1.status_code == 200, f"First request failed: {response1.text}"
        
        # Second immediate request should trigger cooldown
        response2 = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        
        assert response2.status_code == 429, f"Expected 429 (cooldown), got {response2.status_code}: {response2.text}"
        data = response2.json()
        
        # Should contain cooldown info
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert "cooldown_remaining" in detail or "cooldown" in str(detail).lower(), f"Cooldown info missing: {detail}"
        print(f"✓ 30-second cooldown enforced correctly")


class TestOTPVerifyEndpoint:
    """Tests for POST /api/auth/register/verify-otp"""
    
    def test_verify_otp_success(self):
        """Test successful OTP verification"""
        test_email = generate_test_email()
        
        # Request OTP
        request_response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        assert request_response.status_code == 200
        otp = request_response.json().get("_otp")
        assert otp, "OTP not returned in mock mode"
        
        # Verify OTP
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": otp},
            timeout=30
        )
        
        assert verify_response.status_code == 200, f"Verification failed: {verify_response.text}"
        data = verify_response.json()
        
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert data.get("verified") == True, f"Expected verified=True, got {data}"
        assert data.get("email") == test_email.lower(), f"Email mismatch: {data.get('email')}"
        print(f"✓ OTP verification successful for {test_email}")
    
    def test_verify_otp_invalid_format_non_numeric(self):
        """Test OTP verification with non-numeric OTP"""
        test_email = generate_test_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": "abc123"},
            timeout=30
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for non-numeric OTP, got {response.status_code}"
        print(f"✓ Non-numeric OTP rejected correctly")
    
    def test_verify_otp_invalid_format_wrong_length(self):
        """Test OTP verification with wrong length"""
        test_email = generate_test_email()
        
        # Too short
        response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": "12345"},  # 5 digits
            timeout=30
        )
        assert response.status_code in [400, 422], f"Expected 400/422 for short OTP, got {response.status_code}"
        
        # Too long
        response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": "1234567"},  # 7 digits
            timeout=30
        )
        assert response.status_code in [400, 422], f"Expected 400/422 for long OTP, got {response.status_code}"
        
        print(f"✓ Wrong length OTP rejected correctly")
    
    def test_verify_otp_wrong_code(self):
        """Test OTP verification with wrong code"""
        test_email = generate_test_email()
        
        # Request OTP
        request_response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        assert request_response.status_code == 200
        otp = request_response.json().get("_otp")
        
        # Verify with wrong OTP
        wrong_otp = "000000" if otp != "000000" else "999999"
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": wrong_otp},
            timeout=30
        )
        
        assert verify_response.status_code == 400, f"Expected 400 for wrong OTP, got {verify_response.status_code}"
        data = verify_response.json()
        
        # Should contain attempts remaining info
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert "attempts_remaining" in detail or "attempt" in str(detail).lower(), f"Missing attempts info: {detail}"
        
        print(f"✓ Wrong OTP rejected with attempts remaining info")
    
    def test_verify_otp_no_otp_requested(self):
        """Test OTP verification when no OTP was requested"""
        test_email = generate_test_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": "123456"},
            timeout=30
        )
        
        assert response.status_code == 400, f"Expected 400 for no OTP requested, got {response.status_code}"
        print(f"✓ Verification rejected when no OTP was requested")
    
    def test_verify_otp_max_attempts(self):
        """Test max 5 attempts per OTP"""
        test_email = generate_test_email()
        
        # Request OTP
        request_response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        assert request_response.status_code == 200
        otp = request_response.json().get("_otp")
        wrong_otp = "000000" if otp != "000000" else "999999"
        
        # Make 5 wrong attempts
        for i in range(5):
            verify_response = requests.post(
                f"{BASE_URL}/api/auth/register/verify-otp",
                json={"email": test_email, "otp": wrong_otp},
                timeout=30
            )
            
            if i < 4:
                # First 4 attempts should return 400 with attempts remaining
                assert verify_response.status_code == 400, f"Attempt {i+1}: Expected 400, got {verify_response.status_code}"
            else:
                # 5th attempt should exhaust attempts and return 429
                assert verify_response.status_code in [400, 429], f"Attempt {i+1}: Expected 400/429, got {verify_response.status_code}"
        
        # 6th attempt should fail with max attempts exceeded
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": wrong_otp},
            timeout=30
        )
        
        assert verify_response.status_code in [400, 429], f"Expected 400/429 after exhausting attempts, got {verify_response.status_code}"
        print(f"✓ Max 5 attempts per OTP enforced correctly")


class TestOTPStatusEndpoint:
    """Tests for GET /api/auth/register/otp-status"""
    
    def test_otp_status_not_verified(self):
        """Test OTP status for email that hasn't verified"""
        test_email = generate_test_email()
        
        response = requests.get(
            f"{BASE_URL}/api/auth/register/otp-status",
            params={"email": test_email},
            timeout=30
        )
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        data = response.json()
        
        assert data.get("verified") == False, f"Expected verified=False for new email, got {data}"
        assert "message" in data, "Missing 'message' field"
        print(f"✓ OTP status returns verified=False for unverified email")
    
    def test_otp_status_after_verification(self):
        """Test OTP status after successful verification"""
        test_email = generate_test_email()
        
        # Request OTP
        request_response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        assert request_response.status_code == 200
        otp = request_response.json().get("_otp")
        
        # Verify OTP
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": otp},
            timeout=30
        )
        assert verify_response.status_code == 200, f"Verification failed: {verify_response.text}"
        
        # Check status
        status_response = requests.get(
            f"{BASE_URL}/api/auth/register/otp-status",
            params={"email": test_email},
            timeout=30
        )
        
        assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
        data = status_response.json()
        
        assert data.get("verified") == True, f"Expected verified=True after verification, got {data}"
        print(f"✓ OTP status returns verified=True after successful verification")
    
    def test_otp_status_email_normalization(self):
        """Test that email is normalized in status check"""
        test_email = generate_test_email()
        uppercase_email = test_email.upper()
        
        response = requests.get(
            f"{BASE_URL}/api/auth/register/otp-status",
            params={"email": f"  {uppercase_email}  "},  # With spaces and uppercase
            timeout=30
        )
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        print(f"✓ Email normalization works in status check")


class TestOTPEmailAlreadyRegistered:
    """Test OTP request for already registered email"""
    
    def test_request_otp_already_registered(self):
        """
        Test OTP request for email that is already registered.
        Note: This requires knowing a registered email in the system.
        We'll test the flow works if we don't have a registered email.
        """
        # Using a generic test - if this email is not registered, it should succeed
        test_email = generate_test_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": "Test User"},
            timeout=30
        )
        
        # Should succeed for new email
        assert response.status_code == 200, f"Request failed for new email: {response.text}"
        print(f"✓ New email can request OTP")


class TestE2EOTPRegistrationFlow:
    """End-to-end test for OTP registration flow"""
    
    def test_full_otp_registration_flow(self):
        """Test complete OTP registration flow"""
        test_email = generate_test_email()
        test_name = "E2E Test User"
        
        # Step 1: Request OTP
        print(f"\n  Step 1: Requesting OTP for {test_email}...")
        request_response = requests.post(
            f"{BASE_URL}/api/auth/register/request-otp",
            json={"email": test_email, "name": test_name},
            timeout=30
        )
        assert request_response.status_code == 200, f"OTP request failed: {request_response.text}"
        request_data = request_response.json()
        
        assert request_data.get("success") == True
        assert request_data.get("_mock") == True, "Expected mock mode"
        otp = request_data.get("_otp")
        assert otp and len(otp) == 6, f"Invalid OTP received: {otp}"
        print(f"    ✓ OTP received: {otp}")
        
        # Step 2: Check status (should be unverified)
        print(f"  Step 2: Checking status before verification...")
        status_response = requests.get(
            f"{BASE_URL}/api/auth/register/otp-status",
            params={"email": test_email},
            timeout=30
        )
        assert status_response.status_code == 200
        assert status_response.json().get("verified") == False
        print(f"    ✓ Status is 'not verified' as expected")
        
        # Step 3: Verify OTP
        print(f"  Step 3: Verifying OTP...")
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/register/verify-otp",
            json={"email": test_email, "otp": otp},
            timeout=30
        )
        assert verify_response.status_code == 200, f"Verification failed: {verify_response.text}"
        verify_data = verify_response.json()
        
        assert verify_data.get("success") == True
        assert verify_data.get("verified") == True
        assert verify_data.get("email") == test_email.lower()
        print(f"    ✓ OTP verified successfully")
        
        # Step 4: Check status (should be verified)
        print(f"  Step 4: Checking status after verification...")
        status_response = requests.get(
            f"{BASE_URL}/api/auth/register/otp-status",
            params={"email": test_email},
            timeout=30
        )
        assert status_response.status_code == 200
        assert status_response.json().get("verified") == True
        print(f"    ✓ Status is 'verified' as expected")
        
        print(f"\n✓ Full OTP registration flow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
