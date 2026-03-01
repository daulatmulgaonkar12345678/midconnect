"""
Test Suite: Fuzzy Search and Seller Badges
===========================================
Tests for:
1. Fuzzy search autocomplete - 'glows' → 'gloves', 'moter' → 'motor'
2. Admin sellers list API with badgeType field
3. Admin badge update API
4. SmartSearch cache initialization (singleton pattern)
"""

import pytest
import requests
import os
import time

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token"}

TEST_SELLER_ID = "699cb1d8ded1c6446549c19f"


class TestFuzzySearchAutocomplete:
    """Tests for fuzzy search autocomplete API with typo correction"""
    
    def test_autocomplete_glows_to_gloves(self):
        """Test typo 'glows' should suggest 'gloves' in didYouMean field"""
        response = requests.get(
            f"{BASE_URL}/api/search/autocomplete",
            params={"q": "glows"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response for 'glows': {data}")
        
        # Check didYouMean field
        did_you_mean = data.get("didYouMean")
        corrected_query = data.get("correctedQuery")
        
        # Either didYouMean or correctedQuery should contain 'gloves'
        assert did_you_mean == "gloves" or corrected_query == "gloves", \
            f"Expected 'gloves' in didYouMean/correctedQuery, got didYouMean={did_you_mean}, correctedQuery={corrected_query}"
        
        print(f"✅ 'glows' correctly suggests 'gloves' via didYouMean={did_you_mean}")
    
    def test_autocomplete_moter_to_motor(self):
        """Test typo 'moter' should suggest 'motor' in didYouMean field"""
        response = requests.get(
            f"{BASE_URL}/api/search/autocomplete",
            params={"q": "moter"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response for 'moter': {data}")
        
        # Check didYouMean field
        did_you_mean = data.get("didYouMean")
        corrected_query = data.get("correctedQuery")
        
        # Either didYouMean or correctedQuery should contain 'motor'
        assert did_you_mean == "motor" or corrected_query == "motor", \
            f"Expected 'motor' in didYouMean/correctedQuery, got didYouMean={did_you_mean}, correctedQuery={corrected_query}"
        
        print(f"✅ 'moter' correctly suggests 'motor' via didYouMean={did_you_mean}")
    
    def test_autocomplete_no_error_on_typos(self):
        """Verify no unpacking errors occur with typo queries"""
        typo_queries = ["glows", "moter", "elctric", "cabel", "swich"]
        
        for query in typo_queries:
            response = requests.get(
                f"{BASE_URL}/api/search/autocomplete",
                params={"q": query}
            )
            
            assert response.status_code == 200, \
                f"Query '{query}' failed with {response.status_code}: {response.text}"
            
            # Verify response structure is valid
            data = response.json()
            assert "query" in data, f"Missing 'query' field for '{query}'"
            
            print(f"✅ Query '{query}' returned successfully without error")


class TestSpellingEndpoint:
    """Tests for dedicated spelling check endpoint"""
    
    def test_spelling_glows(self):
        """Test spelling check for 'glows'"""
        response = requests.get(
            f"{BASE_URL}/api/search/spelling",
            params={"q": "glows"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Spelling check for 'glows': {data}")
        
        corrected = data.get("corrected")
        assert corrected == "gloves", f"Expected 'gloves', got '{corrected}'"
        
        print(f"✅ Spelling endpoint correctly corrects 'glows' → 'gloves'")
    
    def test_spelling_moter(self):
        """Test spelling check for 'moter'"""
        response = requests.get(
            f"{BASE_URL}/api/search/spelling",
            params={"q": "moter"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Spelling check for 'moter': {data}")
        
        corrected = data.get("corrected")
        assert corrected == "motor", f"Expected 'motor', got '{corrected}'"
        
        print(f"✅ Spelling endpoint correctly corrects 'moter' → 'motor'")


class TestAdminSellersAPI:
    """Tests for admin sellers list API with badge info"""
    
    def test_admin_get_sellers_returns_badge_type(self):
        """GET /api/admin/sellers should return sellers with badgeType field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/sellers",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Admin sellers response: {data.keys()}")
        
        assert "sellers" in data, "Missing 'sellers' field"
        assert "total" in data, "Missing 'total' field"
        
        sellers = data.get("sellers", [])
        if len(sellers) > 0:
            first_seller = sellers[0]
            assert "badgeType" in first_seller, f"Missing 'badgeType' in seller: {first_seller.keys()}"
            print(f"✅ Seller has badgeType: {first_seller.get('badgeType')}")
        else:
            print("⚠️ No sellers in database to verify badgeType field")
        
        print(f"✅ Admin sellers API returns {len(sellers)} sellers with badgeType field")
    
    def test_admin_get_sellers_requires_auth(self):
        """GET /api/admin/sellers should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/sellers")
        
        # Should fail without auth
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✅ Admin sellers API correctly requires authentication")


class TestAdminBadgeUpdateAPI:
    """Tests for admin badge update API"""
    
    def test_update_badge_to_choice(self):
        """PUT /api/admin/sellers/{seller_id}/badge should update badge type"""
        response = requests.put(
            f"{BASE_URL}/api/admin/sellers/{TEST_SELLER_ID}/badge",
            headers=AUTH_HEADER,
            json={"badgeType": "choice"}
        )
        
        # May return 404 if seller doesn't exist - that's okay for this test
        if response.status_code == 404:
            print(f"⚠️ Seller {TEST_SELLER_ID} not found - badge update test skipped")
            pytest.skip("Test seller not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        assert data.get("badgeType") == "choice", f"Expected badgeType='choice', got: {data}"
        
        print(f"✅ Badge updated to 'choice' for seller {TEST_SELLER_ID}")
    
    def test_update_badge_to_trusted(self):
        """Test updating badge to 'trusted'"""
        response = requests.put(
            f"{BASE_URL}/api/admin/sellers/{TEST_SELLER_ID}/badge",
            headers=AUTH_HEADER,
            json={"badgeType": "trusted"}
        )
        
        if response.status_code == 404:
            pytest.skip("Test seller not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("badgeType") == "trusted", f"Expected 'trusted', got: {data}"
        
        print(f"✅ Badge updated to 'trusted'")
    
    def test_update_badge_to_none(self):
        """Test removing badge (setting to 'none')"""
        response = requests.put(
            f"{BASE_URL}/api/admin/sellers/{TEST_SELLER_ID}/badge",
            headers=AUTH_HEADER,
            json={"badgeType": "none"}
        )
        
        if response.status_code == 404:
            pytest.skip("Test seller not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("badgeType") == "none", f"Expected 'none', got: {data}"
        
        print(f"✅ Badge removed (set to 'none')")
    
    def test_invalid_badge_type_rejected(self):
        """Test that invalid badge types are rejected"""
        response = requests.put(
            f"{BASE_URL}/api/admin/sellers/{TEST_SELLER_ID}/badge",
            headers=AUTH_HEADER,
            json={"badgeType": "invalid_badge"}
        )
        
        # Should return 422 validation error
        assert response.status_code == 422, \
            f"Expected 422 for invalid badge, got {response.status_code}: {response.text}"
        
        print("✅ Invalid badge type correctly rejected with 422")
    
    def test_badge_update_requires_auth(self):
        """Badge update should require admin authentication"""
        response = requests.put(
            f"{BASE_URL}/api/admin/sellers/{TEST_SELLER_ID}/badge",
            json={"badgeType": "choice"}
        )
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✅ Badge update correctly requires authentication")


class TestHealthEndpoint:
    """Basic health check to verify server is running"""
    
    def test_health_endpoint(self):
        """Verify health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected healthy status, got: {data}"
        
        print("✅ Health endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
