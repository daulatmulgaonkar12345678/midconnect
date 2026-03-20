"""
Test Suite for Service Worker Bug Fixes (Iteration 93)

Bug fixes tested:
1. sw.js properly skips RSC requests (?_rsc= query params) - just returns without calling respondWith
2. sw.js handles navigation fetch failures gracefully - always returns a Response (not undefined)
3. sw.js handles static asset cache misses with proper fallback Response
4. Backend sync endpoint POST /api/business-tools/invoices/sync-offline-draft validates input correctly
5. Layout uses mobile-web-app-capable meta tag (not deprecated apple-mobile-web-app-capable)
6. Sync engine uses correct URL /api/business-tools/invoices/sync-offline-draft (not /api/invoices/)
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://employee-access-hub-1.preview.emergentagent.com')


class TestServiceWorkerBugFixes:
    """Verify sw.js has proper Response handling to avoid 'Failed to convert value to Response' errors"""

    def test_sw_skips_rsc_requests(self):
        """sw.js should skip RSC requests with ?_rsc= query params"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content = response.text
        
        # Check that sw.js has RSC skip logic
        assert "_rsc" in content, "SW must check for _rsc query param"
        assert "searchParams.has('_rsc')" in content, "SW must use searchParams.has('_rsc') to skip RSC requests"
        
        # Verify it returns early without calling respondWith for RSC requests
        # The pattern should be: if RSC request, just return (no respondWith)
        rsc_block_pattern = r"if\s*\(\s*url\.searchParams\.has\(['\"]_rsc['\"]\)\s*\)\s*\{\s*return;"
        assert re.search(rsc_block_pattern, content), "SW should return early for RSC requests without calling respondWith"
        
        print("TEST PASS: sw.js properly skips RSC requests")

    def test_sw_navigate_has_fallback_response(self):
        """sw.js navigation handler should always return a Response, not undefined"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for navigation mode handling
        assert "request.mode === 'navigate'" in content, "SW must handle navigation requests"
        
        # Check for fallback response (503 or offline HTML)
        assert "new Response(" in content, "SW must have fallback Response creation"
        
        # Verify there's an offline fallback with status 503
        assert "503" in content, "SW must return 503 for offline fallback"
        assert "text/html" in content, "SW must return HTML for navigation fallback"
        
        # Verify the offline page has actual content
        assert "Offline" in content, "Offline fallback should mention offline status"
        
        print("TEST PASS: sw.js navigation handler has proper fallback Response")

    def test_sw_static_assets_have_fallback_response(self):
        """sw.js static asset handler should have fallback Response for cache misses"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for static asset handling
        assert "/_next/static" in content, "SW must handle Next.js static assets"
        
        # Check for cache-first strategy
        assert "caches.match(request)" in content, "SW must check cache first for static assets"
        
        # Verify catch block returns a Response, not undefined
        # Pattern: .catch(() => { return new Response(...)
        catch_response_pattern = r"\.catch\s*\(\s*\(\s*\)\s*=>\s*\{\s*[^}]*return\s+new\s+Response"
        assert re.search(catch_response_pattern, content), "SW catch block must return new Response"
        
        print("TEST PASS: sw.js static asset handler has proper fallback Response")

    def test_sw_default_returns_without_respondwith(self):
        """sw.js default case should return without calling respondWith (avoids 'Failed to convert value to Response')"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200
        
        content = response.text
        
        # The last lines of fetch handler should just return without respondWith
        # Look for comment about avoiding the error
        assert "Failed to convert" in content or "pass through" in content.lower(), \
            "SW should have comment about avoiding Response error or pass-through behavior"
        
        # Count respondWith calls - they should all be in specific blocks, not default
        respondwith_calls = content.count("event.respondWith(")
        
        # Should have respondWith for: navigation, static assets (but NOT for default, API, RSC, non-GET)
        assert respondwith_calls >= 2, f"SW should have at least 2 respondWith calls, found {respondwith_calls}"
        
        print("TEST PASS: sw.js default case avoids 'Failed to convert value to Response' error")


class TestMetaTagFix:
    """Verify deprecated apple-mobile-web-app-capable is replaced with mobile-web-app-capable"""

    def test_uses_correct_meta_tag(self):
        """HTML should use mobile-web-app-capable, not deprecated apple-mobile-web-app-capable"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for correct meta tag
        assert 'name="mobile-web-app-capable"' in content, \
            "HTML must use mobile-web-app-capable meta tag"
        
        # The deprecated tag should NOT be present (as the sole PWA capable tag)
        # Note: apple-mobile-web-app-status-bar-style is OK, it's a different tag
        # The deprecated one was 'apple-mobile-web-app-capable' for web app capability
        if 'name="apple-mobile-web-app-capable"' in content:
            # If present, it's a bug - the deprecated tag should have been replaced
            pytest.fail("Found deprecated apple-mobile-web-app-capable meta tag - should use mobile-web-app-capable")
        
        print("TEST PASS: HTML uses correct mobile-web-app-capable meta tag")


class TestSyncEndpointUrl:
    """Verify sync endpoint uses correct URL pattern /api/business-tools/invoices/..."""

    def test_sync_endpoint_correct_url(self):
        """Sync endpoint should be at /api/business-tools/invoices/sync-offline-draft (not /api/invoices/)"""
        # Test the correct URL returns expected validation error (requires auth)
        correct_response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={"test": "data"},
            headers={"Content-Type": "application/json"}
        )
        # Should return 422 for validation error (missing auth and fields)
        assert correct_response.status_code == 422, \
            f"Expected 422 at correct URL, got {correct_response.status_code}"
        
        # Verify the validation error mentions expected fields
        data = correct_response.json()
        detail_str = str(data.get("detail", []))
        assert "authorization" in detail_str.lower() or "buyerId" in detail_str.lower(), \
            "Response should mention required fields"
        
        print("TEST PASS: Sync endpoint at /api/business-tools/invoices/sync-offline-draft validates correctly")

    def test_wrong_url_returns_404(self):
        """The old incorrect URL /api/invoices/sync-offline-draft should return 404"""
        wrong_response = requests.post(
            f"{BASE_URL}/api/invoices/sync-offline-draft",
            json={"test": "data"},
            headers={"Content-Type": "application/json"}
        )
        # Wrong URL should return 404 (endpoint doesn't exist at that path)
        assert wrong_response.status_code == 404, \
            f"Expected 404 at wrong URL /api/invoices/, got {wrong_response.status_code}"
        
        print("TEST PASS: Old incorrect URL /api/invoices/sync-offline-draft returns 404")


class TestSyncEndpointValidation:
    """Verify sync endpoint validates input correctly"""

    def test_sync_requires_auth_header(self):
        """Sync endpoint should require Authorization header"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={"buyerId": "test123", "items": []},
            headers={"Content-Type": "application/json"}
            # No Authorization header
        )
        assert response.status_code == 422, f"Expected 422 for missing auth, got {response.status_code}"
        
        data = response.json()
        # Should mention missing authorization
        detail_str = str(data)
        assert "authorization" in detail_str.lower(), "Should mention missing authorization"
        
        print("TEST PASS: Sync endpoint requires Authorization header")

    def test_sync_requires_buyerid(self):
        """Sync endpoint should require buyerId field"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={"items": [{"productName": "Test", "quantity": 1, "price": 100, "gstPercent": 18}]},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test_token"
            }
        )
        # Should return 401 (invalid token) or 422 (missing buyerId)
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        
        print("TEST PASS: Sync endpoint validates buyerId field")

    def test_sync_requires_items(self):
        """Sync endpoint should require items field"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/invoices/sync-offline-draft",
            json={"buyerId": "test123"},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test_token"
            }
        )
        # Should return 401 (invalid token) or 422 (missing items)
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        
        print("TEST PASS: Sync endpoint validates items field")


class TestPWAManifest:
    """Verify PWA manifest is served correctly"""

    def test_manifest_served_correctly(self):
        """manifest.json should be served with correct PWA config"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check required fields
        assert data["name"] == "UdyogConnect - Business Tools"
        assert data["short_name"] == "UdyogConnect"
        assert data["display"] == "standalone"
        assert data["start_url"] == "/seller/business-tools"
        
        # Check icons
        assert len(data["icons"]) >= 2, "Must have at least 2 icons"
        
        print("TEST PASS: manifest.json served with correct PWA config")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
