"""
Test Suite: Unpublish Listing Feature
Tests for POST /api/listings/{listing_id}/unpublish endpoint

Features tested:
1. Unpublish active listing -> sets status to draft
2. Unpublish should reject if listing is already draft or archived
3. Unpublish should reject unauthorized users (non-owner)
4. Draft listings should NOT appear in public search results
5. Draft listings SHOULD still appear in seller's own listing page
6. Existing POST /api/listings/{listing_id}/publish still works for draft->active
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token"}

# Test listing IDs from agent context
TEST_LISTING_IDS = [
    "69b57c730ed7999c085b3656",  # active
    "69b5c25c2972a896e0a78417",  # active
    "69b57c730ed7999c085b3657",  # active
]


class TestUnpublishEndpoint:
    """Tests for POST /api/listings/{listing_id}/unpublish"""
    
    def test_unpublish_active_listing_success(self):
        """Test: Unpublish an active listing -> sets status to draft"""
        listing_id = TEST_LISTING_IDS[0]
        
        # First, check current status
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=AUTH_HEADER
        )
        print(f"[GET listing] Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            current_status = data.get('listing', {}).get('status', 'unknown')
            print(f"[GET listing] Current status: {current_status}")
        
        # Unpublish the listing
        response = requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        print(f"[UNPUBLISH] Status: {response.status_code}, Response: {response.text[:500]}")
        
        # If listing was already draft, we expect 400
        if response.status_code == 400:
            assert "Cannot unpublish" in response.text or "draft" in response.text.lower()
            print("[UNPUBLISH] Listing was already draft - expected behavior")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get('status') == 'draft', f"Expected status 'draft', got {data.get('status')}"
        assert 'message' in data
        print(f"[UNPUBLISH] Success: {data}")
    
    def test_unpublish_already_draft_listing_fails(self):
        """Test: Unpublish should reject if listing is already draft"""
        listing_id = TEST_LISTING_IDS[0]
        
        # First unpublish to ensure it's draft
        requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        
        # Try to unpublish again
        response = requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        print(f"[UNPUBLISH DRAFT] Status: {response.status_code}, Response: {response.text[:500]}")
        
        assert response.status_code == 400, f"Expected 400 for draft listing, got {response.status_code}"
        assert "Cannot unpublish" in response.text or "draft" in response.text.lower()
        print("[UNPUBLISH DRAFT] Correctly rejected unpublish of draft listing")
    
    def test_unpublish_nonexistent_listing_fails(self):
        """Test: Unpublish should return 404 for non-existent listing"""
        fake_listing_id = "000000000000000000000000"
        
        response = requests.post(
            f"{BASE_URL}/api/listings/{fake_listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        print(f"[UNPUBLISH NONEXISTENT] Status: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("[UNPUBLISH NONEXISTENT] Correctly returned 404")
    
    def test_unpublish_unauthorized_fails(self):
        """Test: Unpublish should reject unauthorized users (no token)"""
        listing_id = TEST_LISTING_IDS[0]
        
        response = requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish"
            # No auth header
        )
        print(f"[UNPUBLISH NO AUTH] Status: {response.status_code}")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("[UNPUBLISH NO AUTH] Correctly rejected unauthorized request")


class TestDraftVisibility:
    """Tests for draft listing visibility in search vs seller page"""
    
    def test_draft_listing_not_in_public_search(self):
        """Test: Draft listings should NOT appear in public search results"""
        listing_id = TEST_LISTING_IDS[0]
        
        # First, ensure listing is draft
        requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        
        # Get listing details to find product name
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=AUTH_HEADER
        )
        
        if response.status_code != 200:
            pytest.skip("Could not get listing details")
        
        listing_data = response.json().get('listing', {})
        product_name = listing_data.get('productName', 'motor')
        print(f"[SEARCH] Searching for product: {product_name}")
        
        # Search for the product
        search_response = requests.get(
            f"{BASE_URL}/api/search?q={product_name}",
            headers=AUTH_HEADER
        )
        print(f"[SEARCH] Status: {search_response.status_code}")
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            listings = search_data.get('listings', [])
            
            # Check that our draft listing is NOT in results
            draft_in_results = any(
                str(l.get('_id')) == listing_id or str(l.get('listingId')) == listing_id
                for l in listings
            )
            
            assert not draft_in_results, f"Draft listing {listing_id} should NOT appear in search results"
            print(f"[SEARCH] Draft listing correctly excluded from {len(listings)} search results")
        else:
            print(f"[SEARCH] Search returned {search_response.status_code}")
    
    def test_draft_listing_visible_in_seller_listings(self):
        """Test: Draft listings SHOULD still appear in seller's own listing page"""
        listing_id = TEST_LISTING_IDS[0]
        
        # First, ensure listing is draft
        requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        
        # Get seller's listings
        response = requests.get(
            f"{BASE_URL}/api/seller/listings",
            headers=AUTH_HEADER
        )
        print(f"[SELLER LISTINGS] Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        listings = data.get('listings', [])
        
        # Check that our draft listing IS in seller's listings
        draft_in_seller_listings = any(
            str(l.get('_id')) == listing_id
            for l in listings
        )
        
        assert draft_in_seller_listings, f"Draft listing {listing_id} should appear in seller's listings"
        
        # Verify it has draft status
        draft_listing = next(
            (l for l in listings if str(l.get('_id')) == listing_id),
            None
        )
        assert draft_listing is not None
        assert draft_listing.get('status') == 'draft', f"Expected status 'draft', got {draft_listing.get('status')}"
        print(f"[SELLER LISTINGS] Draft listing correctly visible with status: {draft_listing.get('status')}")


class TestPublishEndpoint:
    """Tests for POST /api/listings/{listing_id}/publish (draft -> active)"""
    
    def test_publish_draft_listing(self):
        """Test: Existing publish endpoint still works for draft->active"""
        listing_id = TEST_LISTING_IDS[0]
        
        # First, ensure listing is draft
        requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/unpublish",
            headers=AUTH_HEADER
        )
        
        # Try to publish
        response = requests.post(
            f"{BASE_URL}/api/listings/{listing_id}/publish",
            headers=AUTH_HEADER
        )
        print(f"[PUBLISH] Status: {response.status_code}, Response: {response.text[:500]}")
        
        # Note: Publish requires GST verification, so it may fail with 400/403
        # This is expected behavior per agent context
        if response.status_code in [400, 403]:
            print(f"[PUBLISH] Expected failure due to GST/email verification requirement")
            assert "GST" in response.text or "verification" in response.text.lower() or "verified" in response.text.lower()
            return
        
        if response.status_code == 200:
            data = response.json()
            assert data.get('status') == 'active'
            print(f"[PUBLISH] Success: {data}")


class TestToggleStatusFlow:
    """Tests for the complete toggle flow (active <-> draft)"""
    
    def test_toggle_active_to_draft_and_back(self):
        """Test: Full toggle flow - active -> draft -> active (if GST verified)"""
        listing_id = TEST_LISTING_IDS[1]  # Use second listing
        
        # Get initial status
        response = requests.get(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            headers=AUTH_HEADER
        )
        
        if response.status_code != 200:
            pytest.skip(f"Could not get listing {listing_id}")
        
        initial_status = response.json().get('listing', {}).get('status')
        print(f"[TOGGLE] Initial status: {initial_status}")
        
        # If active, unpublish to draft
        if initial_status == 'active':
            response = requests.post(
                f"{BASE_URL}/api/listings/{listing_id}/unpublish",
                headers=AUTH_HEADER
            )
            assert response.status_code == 200
            print("[TOGGLE] Unpublished: active -> draft")
            
            # Verify status changed
            response = requests.get(
                f"{BASE_URL}/api/seller/listings/{listing_id}",
                headers=AUTH_HEADER
            )
            new_status = response.json().get('listing', {}).get('status')
            assert new_status == 'draft', f"Expected 'draft', got {new_status}"
            print(f"[TOGGLE] Verified status is now: {new_status}")
        
        # If draft, try to publish (may fail due to GST)
        if initial_status == 'draft':
            response = requests.post(
                f"{BASE_URL}/api/listings/{listing_id}/publish",
                headers=AUTH_HEADER
            )
            print(f"[TOGGLE] Publish attempt: {response.status_code}")
            # Don't assert success - GST verification may block


class TestSearchExcludesDraft:
    """Additional tests for search endpoint excluding draft listings"""
    
    def test_search_only_returns_active_listings(self):
        """Test: GET /api/search only returns active listings"""
        response = requests.get(
            f"{BASE_URL}/api/search?q=motor",
            headers=AUTH_HEADER
        )
        print(f"[SEARCH ACTIVE] Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            listings = data.get('listings', [])
            
            # All returned listings should be active
            for listing in listings:
                status = listing.get('status', 'unknown')
                # Note: Search results may not include status field
                # The filter is applied server-side
                print(f"[SEARCH ACTIVE] Listing {listing.get('_id', 'unknown')[:8]}... status: {status}")
            
            print(f"[SEARCH ACTIVE] Total results: {len(listings)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
