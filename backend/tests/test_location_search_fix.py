"""
TEST: Location Search Fix - P0/P1 Bug Fixes
============================================

P0 Fix: Location API returns cities with active sellers
P1 Fix: /search page no longer has duplicate search bar (verified via Playwright UI test)

Tests the GET /api/search/locations endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pricing-portal-21.preview.emergentagent.com')


class TestLocationSearchFix:
    """Tests for P0 Location API Fix - Cities with active sellers"""
    
    def test_location_search_del_returns_delhi(self):
        """
        P0 FIX: GET /api/search/locations?q=del should return Delhi with sellerCount
        
        Original bug: Typing 'Pune' didn't show cities with sellers
        Fix: activeSellerCities collection was populated via rebuild
        """
        response = requests.get(f"{BASE_URL}/api/search/locations?q=del")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        data = response.json()
        assert "query" in data
        assert data["query"] == "del"
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        
        # Find Delhi city in suggestions
        delhi_suggestions = [s for s in data["suggestions"] if s.get("city") == "Delhi"]
        assert len(delhi_suggestions) >= 1, "Delhi should appear in suggestions"
        
        # Verify sellerCount is present and > 0
        delhi_city = next((s for s in delhi_suggestions if s.get("type") == "city"), None)
        assert delhi_city is not None, "Delhi city type suggestion should exist"
        assert "sellerCount" in delhi_city, "Delhi should have sellerCount"
        assert delhi_city["sellerCount"] >= 1, f"Delhi sellerCount should be >= 1, got {delhi_city.get('sellerCount')}"
        
        print(f"✅ Delhi found with sellerCount: {delhi_city['sellerCount']}")
    
    def test_location_search_returns_structured_data(self):
        """Verify location suggestions have proper structure"""
        response = requests.get(f"{BASE_URL}/api/search/locations?q=delhi")
        
        assert response.status_code == 200
        data = response.json()
        
        for suggestion in data["suggestions"]:
            assert "label" in suggestion, "Suggestion should have label"
            assert "type" in suggestion, "Suggestion should have type"
            assert suggestion["type"] in ["city", "state", "pincode", "pan_india"], f"Invalid type: {suggestion['type']}"
            
            # If it's a city type, verify city/state fields
            if suggestion["type"] == "city":
                assert "city" in suggestion
                assert "state" in suggestion
        
        print(f"✅ All {len(data['suggestions'])} suggestions have proper structure")
    
    def test_location_search_with_empty_query_returns_error_or_empty(self):
        """Empty query should not break the API"""
        response = requests.get(f"{BASE_URL}/api/search/locations?q=")
        
        # API requires min_length=1, so this should fail validation
        # But endpoint still returns valid JSON
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
    
    def test_location_search_pan_india_option(self):
        """Typing 'pan' or 'india' should return Pan India option"""
        response = requests.get(f"{BASE_URL}/api/search/locations?q=pan")
        
        assert response.status_code == 200
        data = response.json()
        
        pan_india = [s for s in data["suggestions"] if s.get("type") == "pan_india"]
        assert len(pan_india) >= 1, "Pan India option should appear for 'pan' query"
        print("✅ Pan India option available")
    
    def test_location_check_endpoint(self):
        """Test /api/search/locations/check for seller availability"""
        response = requests.get(f"{BASE_URL}/api/search/locations/check?city=Delhi")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hasSellers" in data
        # Delhi should have sellers based on rebuild
        assert data["hasSellers"] == True, "Delhi should have sellers"
        assert "sellerCount" in data
        assert data["sellerCount"] >= 1
        
        print(f"✅ Delhi has {data['sellerCount']} sellers")
    
    def test_location_check_no_sellers_provides_alternatives(self):
        """When no sellers in location, API should provide alternatives"""
        # Test with a city unlikely to have sellers
        response = requests.get(f"{BASE_URL}/api/search/locations/check?city=Nashik")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("hasSellers"):
            # Should have nearbyAlternatives
            assert "nearbyAlternatives" in data, "Should provide nearby alternatives"
            print(f"✅ No sellers in Nashik, {len(data.get('nearbyAlternatives', []))} alternatives provided")
        else:
            print(f"✅ Nashik has {data.get('sellerCount')} sellers")


class TestSearchEndpoint:
    """Tests for the main search endpoint"""
    
    def test_search_endpoint_returns_results(self):
        """Basic search should return valid response"""
        response = requests.get(f"{BASE_URL}/api/search?q=motor")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "listings" in data or "total" in data, "Response should have listings or total"
        print(f"✅ Search endpoint working, total: {data.get('total', len(data.get('listings', [])))}")
    
    def test_search_with_city_filter(self):
        """Search with city filter should work"""
        response = requests.get(f"{BASE_URL}/api/search?q=motor&city=Delhi&location_type=city")
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"✅ Search with city filter working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
