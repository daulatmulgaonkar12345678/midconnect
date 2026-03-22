"""
Test Suite for Hybrid Offline Mode + Draft Invoice System

Tests:
1. PWA manifest.json endpoint
2. Service worker sw.js endpoint
3. Backend sync-offline-draft endpoint validation
4. Invoice endpoints (smoke test)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com')


class TestPWAAssets:
    """Test PWA manifest and service worker availability"""

    def test_manifest_json_available(self):
        """manifest.json should be served at /manifest.json"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Validate required PWA fields
        assert "name" in data, "manifest.json must have 'name' field"
        assert "short_name" in data, "manifest.json must have 'short_name' field"
        assert "start_url" in data, "manifest.json must have 'start_url' field"
        assert "display" in data, "manifest.json must have 'display' field"
        assert "icons" in data, "manifest.json must have 'icons' field"
        
        # Check specific values
        assert data["name"] == "UdyogConnect - Business Tools"
        assert data["short_name"] == "UdyogConnect"
        assert data["display"] == "standalone"
        assert data["start_url"] == "/seller/business-tools"
        
        # Check icons have required sizes
        icon_sizes = [icon.get("sizes") for icon in data["icons"]]
        assert "192x192" in icon_sizes, "Must have 192x192 icon"
        assert "512x512" in icon_sizes, "Must have 512x512 icon"
        
        print("TEST PASS: manifest.json has all required PWA fields")

    def test_service_worker_available(self):
        """sw.js should be served at /sw.js"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content = response.text
        # Check SW contains expected code
        assert "addEventListener" in content, "SW must have event listeners"
        assert "install" in content, "SW must handle install event"
        assert "fetch" in content, "SW must handle fetch event"
        assert "CACHE_NAME" in content, "SW must define cache name"
        
        print("TEST PASS: sw.js is available and has correct structure")


class TestOfflineSyncEndpoint:
    """Test the sync-offline-draft backend endpoint"""

    def test_sync_endpoint_requires_auth(self):
        """POST /api/invoices/sync-offline-draft should require authorization"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={"buyerId": "test", "items": []},
            headers={"Content-Type": "application/json"}
        )
        # Should fail with 401 (no auth) or 422 (missing auth header validation)
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print("TEST PASS: sync-offline-draft requires authentication")

    def test_sync_endpoint_rejects_invalid_token(self):
        """POST /api/invoices/sync-offline-draft should reject invalid tokens"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={
                "buyerId": "507f1f77bcf86cd799439011",
                "items": [
                    {"productName": "Test Product", "quantity": 1, "price": 100, "gstPercent": 18}
                ]
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token_12345"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should have detail field"
        print("TEST PASS: sync-offline-draft rejects invalid tokens")


class TestBusinessToolsPages:
    """Test Business Tools page endpoints"""

    def test_business_tools_dashboard_page_loads(self):
        """Business Tools dashboard should return 200"""
        response = requests.get(f"{BASE_URL}/seller/business-tools")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check page contains expected HTML
        assert "UdyogConnect" in response.text or "Business" in response.text
        print("TEST PASS: Business Tools dashboard page loads (200)")

    def test_invoices_page_loads(self):
        """Invoices page should return 200"""
        response = requests.get(f"{BASE_URL}/seller/business-tools/invoices")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("TEST PASS: Invoices page loads (200)")


class TestInvoiceAPIEndpoints:
    """Smoke test for invoice API endpoints (auth required)"""

    def test_invoices_list_requires_auth(self):
        """GET /api/business-tools/invoices should require auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices")
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print("TEST PASS: Invoices list endpoint requires auth")

    def test_invoice_products_requires_auth(self):
        """GET /api/business-tools/invoice-products should require auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products")
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print("TEST PASS: Invoice products endpoint requires auth")

    def test_check_stock_requires_auth(self):
        """POST /api/business-tools/invoices/check-stock should require auth"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/check-stock",
            json={"buyerId": "test", "items": []},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print("TEST PASS: Check stock endpoint requires auth")


class TestNetworkContext:
    """Test network-related features presence in HTML"""

    def test_business_tools_layout_loads_correctly(self):
        """Business Tools layout should load (NetworkProvider is loaded via JS chunks)"""
        response = requests.get(f"{BASE_URL}/seller/business-tools")
        assert response.status_code == 200
        
        # Next.js loads components via JS chunks, check for business-tools layout script
        content = response.text
        # Check that the business-tools layout chunk is being loaded
        assert "business-tools" in content.lower() or "_layout" in content.lower()
        print("TEST PASS: Business Tools layout loads correctly (client components via JS chunks)")

    def test_manifest_link_in_html(self):
        """HTML should have manifest link"""
        response = requests.get(f"{BASE_URL}")
        assert response.status_code == 200
        
        # Check for manifest link
        assert 'rel="manifest"' in response.text
        assert '/manifest.json' in response.text
        print("TEST PASS: HTML has manifest link")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
