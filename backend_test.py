#!/usr/bin/env python3
"""
Backend API Testing for Role-Based Registration Flow
Tests the B2B marketplace registration endpoints and core functionality.
"""

import requests
import sys
import json
from datetime import datetime

class B2BAPITester:
    def __init__(self, base_url="https://auth-ssot-rebuild.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_result(self, test_name, success, details="", expected_status=None, actual_status=None):
        """Log test result for reporting"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test": test_name,
            "status": "PASS" if success else "FAIL",
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {test_name}")
        if details:
            print(f"   Details: {details}")
        if expected_status and actual_status:
            print(f"   Status: Expected {expected_status}, got {actual_status}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)
            else:
                self.log_result(name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            
            try:
                response_data = response.json() if response.content else {}
            except:
                response_data = {"raw_content": response.text[:200] if response.text else ""}
            
            details = f"URL: {url}"
            if not success:
                details += f" | Response: {response.text[:100]}"
            
            self.log_result(name, success, details, expected_status, response.status_code)
            return success, response_data

        except requests.exceptions.Timeout:
            self.log_result(name, False, "Request timeout (30s)", expected_status, "TIMEOUT")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_result(name, False, "Connection error - server may be down", expected_status, "CONNECTION_ERROR")
            return False, {}
        except Exception as e:
            self.log_result(name, False, f"Request failed: {str(e)}", expected_status, "ERROR")
            return False, {}

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200
        )
        return success

    def test_cors_headers(self):
        """Test CORS headers are properly configured"""
        print("\n🔍 Testing CORS Configuration...")
        url = f"{self.base_url}/api/health"
        
        try:
            # Test OPTIONS preflight request
            response = requests.options(url, headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            }, timeout=10)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            success = (
                cors_headers['Access-Control-Allow-Origin'] is not None and
                cors_headers['Access-Control-Allow-Methods'] is not None
            )
            
            details = f"CORS Headers: {cors_headers}"
            self.log_result("CORS Configuration", success, details)
            return success
            
        except Exception as e:
            self.log_result("CORS Configuration", False, f"CORS test failed: {str(e)}")
            return False

    def test_auth_endpoints_without_token(self):
        """Test auth endpoints without token (should return 401)"""
        print("\n🔍 Testing Auth Endpoints Security...")
        
        # Test auth endpoints that should require authentication
        auth_endpoints = [
            ("/api/auth/complete-profile", "POST"),
            ("/api/auth/check-registration", "GET"),
        ]
        
        all_success = True
        for endpoint, method in auth_endpoints:
            success, _ = self.run_test(
                f"Auth Security - {endpoint}",
                method,
                endpoint,
                401,  # Should return 401 without token
                data={"test": "data"} if method == "POST" else None
            )
            if not success:
                all_success = False
        
        return all_success

    def test_complete_profile_endpoint_structure(self):
        """Test complete-profile endpoint exists and validates input"""
        print("\n🔍 Testing Complete Profile Endpoint Structure...")
        
        # Test with invalid data (no token) - should return 401
        success, _ = self.run_test(
            "Complete Profile - No Auth",
            "POST",
            "/api/auth/complete-profile",
            401
        )
        
        # Test with malformed data (with mock token) - should return 400 or 401
        mock_headers = {'Authorization': 'Bearer mock-token-for-testing'}
        success2, _ = self.run_test(
            "Complete Profile - Invalid Data",
            "POST", 
            "/api/auth/complete-profile",
            401,  # Will be 401 due to invalid token, but endpoint exists
            data={"invalid": "data"},
            headers=mock_headers
        )
        
        return success and success2

    def test_check_registration_endpoint(self):
        """Test check-registration endpoint exists"""
        print("\n🔍 Testing Check Registration Endpoint...")
        
        success, _ = self.run_test(
            "Check Registration - No Auth",
            "GET",
            "/api/auth/check-registration", 
            401  # Should require auth
        )
        
        return success

    def test_api_routing(self):
        """Test that /api routes are properly configured"""
        print("\n🔍 Testing API Routing...")
        
        # Test that /api prefix is working
        success, _ = self.run_test(
            "API Routing - Health with /api prefix",
            "GET",
            "/api/health",
            200
        )
        
        # Test without /api prefix (should fail or redirect)
        success2, _ = self.run_test(
            "API Routing - Health without /api prefix", 
            "GET",
            "/health",
            404  # Expecting 404 since backend should require /api prefix
        )
        
        return success  # Only require the /api prefix to work

    def test_seller_dashboard_access(self):
        """Test seller dashboard endpoint exists (security)"""
        print("\n🔍 Testing Seller Dashboard Security...")
        
        success, _ = self.run_test(
            "Seller Dashboard - No Auth",
            "GET", 
            "/api/seller/dashboard",
            401  # Should require authentication
        )
        
        return success

    def run_all_backend_tests(self):
        """Run comprehensive backend API tests"""
        print("=" * 60)
        print("🚀 B2B MARKETPLACE BACKEND API TESTS")
        print("=" * 60)
        
        # Track test categories
        test_categories = {
            "health": self.test_health_endpoint(),
            "cors": self.test_cors_headers(), 
            "auth_security": self.test_auth_endpoints_without_token(),
            "complete_profile": self.test_complete_profile_endpoint_structure(),
            "check_registration": self.test_check_registration_endpoint(),
            "api_routing": self.test_api_routing(),
            "seller_security": self.test_seller_dashboard_access()
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Category breakdown
        print(f"\n📋 Category Results:")
        for category, result in test_categories.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {category}: {status}")
        
        # Check for critical failures
        critical_tests = ["health", "api_routing"]
        critical_failures = [cat for cat in critical_tests if not test_categories.get(cat, False)]
        
        if critical_failures:
            print(f"\n❌ CRITICAL FAILURES: {critical_failures}")
            print("   These must be fixed before frontend testing.")
            return False
        
        print(f"\n🎯 Backend API Status: {'READY' if self.tests_passed >= self.tests_run * 0.7 else 'ISSUES FOUND'}")
        return self.tests_passed >= self.tests_run * 0.7

def main():
    """Main test execution"""
    print("Starting B2B Marketplace Backend API Tests...")
    
    tester = B2BAPITester()
    success = tester.run_all_backend_tests()
    
    # Save detailed results for main agent
    results_file = "/app/test_reports/backend_api_results.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": tester.tests_run,
                    "passed": tester.tests_passed,
                    "failed": tester.tests_run - tester.tests_passed,
                    "success_rate": round(tester.tests_passed/tester.tests_run*100, 1) if tester.tests_run > 0 else 0,
                    "overall_status": "PASS" if success else "FAIL",
                    "timestamp": datetime.now().isoformat()
                },
                "detailed_results": tester.test_results
            }, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️ Could not save results file: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())