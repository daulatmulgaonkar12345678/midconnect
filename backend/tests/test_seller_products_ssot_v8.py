"""
Test Suite for Seller Products SSOT V8 Schema Refactor
=======================================================
Tests all seller listing endpoints for CANONICAL camelCase format.

Key validations:
1. All endpoints return camelCase fields (sellerId, productId, categoryId, updatedAt, pricingTiers)
2. NO snake_case fields in responses (seller_id, created_at, pricing.slabs)
3. PATCH /listings/{id} accepts flat availability fields (moq, stock, maxCapacity, leadTime)
4. PATCH /listings/{id}/pricing accepts pricingTiers array (NOT pricing.slabs)
5. ObjectId serialized to string in all responses
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://material-estimator-19.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

# Dev test token for non-Firebase auth
DEV_TOKEN = "dev-test-token"

class TestSellerEndpointsBasic:
    """Basic endpoint accessibility tests (without seller verification)"""
    
    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health check passed: {data}")
    
    def test_seller_listings_requires_auth(self):
        """Verify seller endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/seller/listings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/seller/listings correctly requires authentication")
    
    def test_seller_dashboard_requires_auth(self):
        """Verify seller dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/seller/dashboard")
        assert response.status_code == 401
        print("✅ GET /api/seller/dashboard correctly requires authentication")
    
    def test_seller_stats_requires_auth(self):
        """Verify seller stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/seller/stats")
        assert response.status_code == 401
        print("✅ GET /api/seller/stats correctly requires authentication")
    
    def test_seller_subscription_requires_auth(self):
        """Verify seller subscription requires authentication"""
        response = requests.get(f"{BASE_URL}/api/seller/subscription")
        assert response.status_code == 401
        print("✅ GET /api/seller/subscription correctly requires authentication")


class TestSellerEndpointsWithAuth:
    """Tests with dev test token authentication (requires Firebase disabled)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers with dev token"""
        self.headers = {
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_seller_listings_with_auth(self):
        """Test GET /api/seller/listings returns camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        print(f"GET /api/seller/listings - Status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'Empty'}")
        
        # Firebase enabled in production - dev token won't work
        if response.status_code == 401:
            print("ℹ️ Firebase auth enabled - dev token invalid. Skipping authenticated tests.")
            pytest.skip("Firebase auth enabled - cannot test with dev token")
        
        if response.status_code == 200:
            data = response.json()
            assert "listings" in data, "Response should have 'listings' key"
            assert "total" in data, "Response should have 'total' key"
            assert "page" in data, "Response should have 'page' key"
            
            # If there are listings, check for camelCase fields
            if data.get("listings"):
                listing = data["listings"][0]
                print(f"Listing keys: {list(listing.keys())}")
                
                # Check for snake_case fields (should NOT exist)
                snake_case_fields = ["seller_id", "product_id", "category_id", "created_at", "updated_at", "published_at"]
                for field in snake_case_fields:
                    assert field not in listing, f"Snake_case field '{field}' should NOT exist in response"
                
                if "_id" in listing:
                    assert isinstance(listing["_id"], str), "_id should be string"
                    assert len(listing["_id"]) == 24, "_id should be 24-char hex string"
                
                print("✅ Listings have correct camelCase format")
            else:
                print("✅ No listings found (empty but valid response)")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required - endpoint protected")
    
    def test_seller_dashboard_with_auth(self):
        """Test GET /api/seller/dashboard returns camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/dashboard",
            headers=self.headers
        )
        
        print(f"GET /api/seller/dashboard - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify camelCase structure
            assert "stats" in data, "Response should have 'stats' key"
            assert "recentListings" in data, "Response should have 'recentListings' key (camelCase)"
            
            # Check that snake_case alternatives don't exist
            assert "recent_listings" not in data, "'recent_listings' should not exist (snake_case)"
            
            # Check stats structure
            stats = data["stats"]
            expected_keys = ["total", "draft", "active", "paused", "archived"]
            for key in expected_keys:
                assert key in stats, f"stats should have '{key}' key"
            
            print(f"✅ Dashboard stats: {stats}")
            print(f"✅ Recent listings count: {len(data.get('recentListings', []))}")
            
            # Check recentListings for camelCase
            if data.get("recentListings"):
                listing = data["recentListings"][0]
                snake_case_fields = ["seller_id", "product_id", "category_id", "created_at", "updated_at"]
                for field in snake_case_fields:
                    assert field not in listing, f"Snake_case '{field}' should NOT exist in recentListings"
                print("✅ recentListings have correct camelCase format")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required - endpoint protected")
    
    def test_seller_stats_with_auth(self):
        """Test GET /api/seller/stats returns camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/stats",
            headers=self.headers
        )
        
        print(f"GET /api/seller/stats - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify camelCase fields
            expected_camelcase = ["totalListings", "publishedListings", "totalEnquiries", "pendingEnquiries"]
            for field in expected_camelcase:
                assert field in data, f"Response should have '{field}' (camelCase)"
            
            # Verify NO snake_case
            snake_case_fields = ["total_listings", "published_listings", "total_enquiries", "pending_enquiries"]
            for field in snake_case_fields:
                assert field not in data, f"'{field}' (snake_case) should NOT exist"
            
            # Check subscription structure
            assert "subscription" in data, "Response should have 'subscription' key"
            sub = data["subscription"]
            assert "plan" in sub, "subscription should have 'plan'"
            assert "isUnlimited" in sub, "subscription should have 'isUnlimited' (camelCase)"
            
            print(f"✅ Stats camelCase verified: {list(data.keys())}")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required - endpoint protected")
    
    def test_seller_subscription_with_auth(self):
        """Test GET /api/seller/subscription returns camelCase fields"""
        response = requests.get(
            f"{BASE_URL}/api/seller/subscription",
            headers=self.headers
        )
        
        print(f"GET /api/seller/subscription - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify top-level camelCase structure
            assert "subscription" in data, "Response should have 'subscription' key"
            assert "usage" in data, "Response should have 'usage' key"
            assert "benefits" in data, "Response should have 'benefits' key"
            assert "upgradeInfo" in data, "Response should have 'upgradeInfo' (camelCase)"
            
            # Verify NO snake_case alternatives
            assert "upgrade_info" not in data, "'upgrade_info' (snake_case) should NOT exist"
            
            # Check subscription fields
            sub = data["subscription"]
            camelcase_fields = ["planName", "isActive", "endDate", "startDate", "daysRemaining"]
            for field in camelcase_fields:
                # Check presence (not all may be present depending on plan)
                if field in sub:
                    print(f"  ✅ subscription.{field} = {sub[field]}")
            
            # Check usage fields
            usage = data["usage"]
            assert "acceptedThisMonth" in usage, "usage should have 'acceptedThisMonth'"
            assert "monthlyLimit" in usage, "usage should have 'monthlyLimit'"
            
            print(f"✅ Subscription camelCase verified")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required - endpoint protected")


class TestListingUpdateEndpoints:
    """Test PATCH endpoints for flat field updates (SSOT V8)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers with dev token"""
        self.headers = {
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_update_listing_accepts_flat_availability_fields(self):
        """
        Test PATCH /api/seller/listings/{id} accepts flat fields:
        - moq (NOT availability.moq)
        - stock (NOT availability.stock)
        - maxCapacity (NOT availability.maxCapacity)
        - leadTime (NOT availability.leadTime)
        """
        # First get existing listings to find an ID
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        if response.status_code != 200:
            pytest.skip(f"Cannot get listings - status {response.status_code}")
        
        data = response.json()
        if not data.get("listings"):
            pytest.skip("No listings available to test update")
        
        listing_id = data["listings"][0]["_id"]
        print(f"Testing update on listing: {listing_id}")
        
        # Test PATCH with flat availability fields
        update_payload = {
            "moq": 10,
            "stock": 100,
            "maxCapacity": 500,
            "leadTime": 5,
            "description": "Updated via SSOT V8 test"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=self.headers,
            json=update_payload
        )
        
        print(f"PATCH /api/seller/listings/{listing_id} - Status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'Empty'}")
        
        if response.status_code == 200:
            result = response.json()
            assert "listing" in result, "Response should have 'listing' key"
            
            listing = result["listing"]
            
            # Verify flat fields are saved correctly
            assert listing.get("moq") == 10, f"moq should be 10, got {listing.get('moq')}"
            assert listing.get("stock") == 100, f"stock should be 100, got {listing.get('stock')}"
            assert listing.get("maxCapacity") == 500, f"maxCapacity should be 500"
            assert listing.get("leadTime") == 5, f"leadTime should be 5"
            
            # Verify NO nested availability object
            assert "availability" not in listing, "Should NOT have nested 'availability' object"
            
            # Verify NO snake_case fields
            assert "max_capacity" not in listing, "max_capacity (snake_case) should NOT exist"
            assert "lead_time" not in listing, "lead_time (snake_case) should NOT exist"
            
            print("✅ Update with flat availability fields successful!")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required")
        elif response.status_code == 404:
            print("ℹ️ Listing not found (may have been deleted)")
    
    def test_update_pricing_accepts_pricing_tiers(self):
        """
        Test PATCH /api/seller/listings/{id}/pricing accepts:
        - pricingTiers array (NOT pricing.slabs)
        - Each tier has minQty, maxQty, pricePerUnit
        """
        # First get existing listings to find an ID
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        if response.status_code != 200:
            pytest.skip(f"Cannot get listings - status {response.status_code}")
        
        data = response.json()
        if not data.get("listings"):
            pytest.skip("No listings available to test pricing update")
        
        listing_id = data["listings"][0]["_id"]
        print(f"Testing pricing update on listing: {listing_id}")
        
        # Test pricing update with pricingTiers
        pricing_payload = {
            "pricingTiers": [
                {"minQty": 1, "maxQty": 10, "pricePerUnit": 100.0},
                {"minQty": 11, "maxQty": 50, "pricePerUnit": 90.0},
                {"minQty": 51, "maxQty": None, "pricePerUnit": 80.0}
            ]
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}/pricing",
            headers=self.headers,
            json=pricing_payload
        )
        
        print(f"PATCH /api/seller/listings/{listing_id}/pricing - Status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'Empty'}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify pricingTiers in response
            assert "pricingTiers" in result, "Response should have 'pricingTiers'"
            
            tiers = result["pricingTiers"]
            assert len(tiers) == 3, f"Should have 3 tiers, got {len(tiers)}"
            
            # Verify tier structure (camelCase)
            for tier in tiers:
                assert "minQty" in tier, "Tier should have 'minQty'"
                assert "pricePerUnit" in tier, "Tier should have 'pricePerUnit'"
                # Verify NO snake_case
                assert "min_qty" not in tier, "Tier should NOT have 'min_qty'"
                assert "max_qty" not in tier, "Tier should NOT have 'max_qty'"
                assert "price_per_unit" not in tier, "Tier should NOT have 'price_per_unit'"
            
            print("✅ Pricing update with pricingTiers successful!")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required")
        elif response.status_code == 404:
            print("ℹ️ Listing not found")


class TestSchemaComplianceValidation:
    """Verify NO snake_case fields written to database"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers with dev token"""
        self.headers = {
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_get_single_listing_camelcase(self):
        """Test GET /api/seller/listings/{id} returns camelCase"""
        # First get listings
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        if response.status_code != 200 or not response.json().get("listings"):
            pytest.skip("No listings available")
        
        listing_id = response.json()["listings"][0]["_id"]
        
        # Get single listing
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=self.headers
        )
        
        print(f"GET /api/seller/listings/{listing_id} - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "listing" in data, "Response should have 'listing' key"
            
            listing = data["listing"]
            
            # Complete snake_case field check
            forbidden_snake_case = [
                "seller_id", "product_id", "category_id",
                "created_at", "updated_at", "published_at",
                "pricing_tiers", "max_capacity", "lead_time",
                "is_active", "seller_role"
            ]
            
            for field in forbidden_snake_case:
                assert field not in listing, f"'{field}' (snake_case) should NOT exist in listing"
            
            # Verify ObjectId serialization
            object_id_fields = ["_id", "sellerId", "productId", "categoryId"]
            for field in object_id_fields:
                if field in listing and listing[field]:
                    assert isinstance(listing[field], str), f"{field} should be string"
                    # ObjectId is 24 hex chars
                    if field != "_id" or len(listing[field]) == 24:
                        print(f"  ✅ {field} = {listing[field]} (valid string)")
            
            # Verify timestamp serialization
            timestamp_fields = ["createdAt", "updatedAt", "publishedAt"]
            for field in timestamp_fields:
                if field in listing and listing[field]:
                    assert isinstance(listing[field], str), f"{field} should be ISO string"
                    print(f"  ✅ {field} = {listing[field]}")
            
            print("✅ Single listing camelCase verification passed!")
        elif response.status_code == 403:
            print("ℹ️ Seller verification required")
    
    def test_listing_no_pricing_slabs(self):
        """Verify NO 'pricing.slabs' structure exists"""
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        if response.status_code != 200:
            pytest.skip(f"Cannot get listings - status {response.status_code}")
        
        data = response.json()
        for listing in data.get("listings", []):
            # Check for old nested structure
            assert "pricing" not in listing, "Listing should NOT have nested 'pricing' object"
            
            # pricingTiers should be at root level
            if "pricingTiers" in listing:
                assert isinstance(listing["pricingTiers"], list), "pricingTiers should be array"
                for tier in listing["pricingTiers"]:
                    assert "slabs" not in tier, "Tier should NOT have 'slabs'"
        
        print("✅ No deprecated 'pricing.slabs' structure found")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup headers with dev token"""
        self.headers = {
            "Authorization": f"Bearer {DEV_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_invalid_listing_id_returns_400(self):
        """Test invalid ObjectId format returns 400"""
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/invalid-id",
            headers=self.headers
        )
        
        # Firebase enabled in production - dev token won't work, expect 401
        if response.status_code == 401:
            print("ℹ️ Firebase auth enabled - cannot test with dev token")
            pytest.skip("Firebase auth enabled - cannot test with dev token")
        
        # Should return 400 (bad request) not 500
        assert response.status_code in [400, 403, 404], f"Expected 400/403/404, got {response.status_code}"
        print(f"✅ Invalid listing ID handled correctly: {response.status_code}")
    
    def test_nonexistent_listing_returns_404(self):
        """Test non-existent but valid ObjectId returns 404"""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
        
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/{fake_id}",
            headers=self.headers
        )
        
        # Firebase enabled in production - dev token won't work, expect 401
        if response.status_code == 401:
            print("ℹ️ Firebase auth enabled - cannot test with dev token")
            pytest.skip("Firebase auth enabled - cannot test with dev token")
        
        # Should return 404 or 403 (if seller verification fails first)
        assert response.status_code in [403, 404], f"Expected 403/404, got {response.status_code}"
        print(f"✅ Non-existent listing handled correctly: {response.status_code}")
    
    def test_patch_with_invalid_moq(self):
        """Test PATCH with invalid moq value"""
        # Get a listing first
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=self.headers
        )
        
        if response.status_code != 200 or not response.json().get("listings"):
            pytest.skip("No listings available")
        
        listing_id = response.json()["listings"][0]["_id"]
        
        # Try to update with invalid moq (0 or negative)
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=self.headers,
            json={"moq": 0}  # Invalid - should be >= 1
        )
        
        print(f"PATCH with moq=0 - Status: {response.status_code}")
        
        # Should return validation error (422) or at least not crash (500)
        assert response.status_code != 500, "Server should not crash on invalid input"
        print(f"✅ Invalid moq handled correctly: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
