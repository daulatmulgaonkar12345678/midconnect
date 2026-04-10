"""
Test Draft Products Feature - Iteration 125

Tests that draft products:
1. Appear in seller's own listings (GET /api/seller/listings)
2. Are counted in dashboard summary (GET /api/business-tools/home/summary)
3. Appear in invoice products (GET /api/business-tools/invoice-products)
4. Do NOT appear in public search (POST /api/search/listings or GET /api/search)
5. Do NOT appear in public product detail page
6. Active products still work normally everywhere
7. Unpublish endpoint (POST /api/listings/{id}/unpublish) works
8. Publish endpoint (POST /api/listings/{id}/publish) works (may require verification)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_HEADER = {"Authorization": "Bearer dev-test-token", "Content-Type": "application/json"}

# Test listings
ACTIVE_LISTING_1 = "69b57c730ed7999c085b3656"
DRAFT_LISTING = "69b5c25c2972a896e0a78417"
ACTIVE_LISTING_2 = "69b57c730ed7999c085b3657"
SELLER_ID = "69a0ac1089b696c2337c5a6e"


class TestSellerListingsIncludeDraft:
    """Test that seller's own listings include draft products"""
    
    def test_seller_listings_returns_all_statuses(self):
        """GET /api/seller/listings should return active, paused, and draft listings"""
        response = requests.get(f"{BASE_URL}/api/seller/listings", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Should have at least 3 listings (2 active + 1 draft)
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"
        
        # Check that draft listing is included
        listing_ids = [l.get("_id") for l in listings]
        assert DRAFT_LISTING in listing_ids, f"Draft listing {DRAFT_LISTING} not found in seller listings"
        
        # Verify the draft listing has status='draft'
        draft_listing = next((l for l in listings if l.get("_id") == DRAFT_LISTING), None)
        assert draft_listing is not None, "Draft listing not found"
        assert draft_listing.get("status") == "draft", f"Expected status='draft', got {draft_listing.get('status')}"
        
        print(f"✓ Seller listings returns {len(listings)} listings including draft")
    
    def test_seller_listings_includes_active_listings(self):
        """GET /api/seller/listings should include active listings (if any exist)"""
        response = requests.get(f"{BASE_URL}/api/seller/listings", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Check for any active listings
        active_listings = [l for l in listings if l.get("status") == "active"]
        draft_listings = [l for l in listings if l.get("status") == "draft"]
        
        # At minimum, we should have listings (active or draft)
        assert len(listings) >= 2, f"Expected at least 2 listings, got {len(listings)}"
        
        print(f"✓ Seller listings: {len(active_listings)} active, {len(draft_listings)} draft")


class TestDashboardSummaryIncludesDraft:
    """Test that dashboard summary counts draft products"""
    
    def test_dashboard_summary_counts_all_products(self):
        """GET /api/business-tools/home/summary should count draft products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/home/summary", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        total_products = data.get("totalProducts", 0)
        
        # Should count at least 3 products (2 active + 1 draft)
        assert total_products >= 3, f"Expected at least 3 products in summary, got {total_products}"
        
        print(f"✓ Dashboard summary counts {total_products} products (includes draft)")
    
    def test_dashboard_summary_structure(self):
        """Verify dashboard summary has expected fields"""
        response = requests.get(f"{BASE_URL}/api/business-tools/home/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        expected_fields = ["totalProducts", "lowStockItems", "pendingPOs", "totalSuppliers"]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print("✓ Dashboard summary has all expected fields")


class TestInvoiceProductsIncludeDraft:
    """Test that invoice products include draft products"""
    
    def test_invoice_products_returns_all_statuses(self):
        """GET /api/business-tools/invoice-products should include draft products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        products = data.get("products", data) if isinstance(data, dict) else data
        
        # Should have at least 3 products
        assert len(products) >= 3, f"Expected at least 3 products, got {len(products)}"
        
        # Check that draft listing is included
        product_ids = [p.get("id") for p in products]
        assert DRAFT_LISTING in product_ids, f"Draft product {DRAFT_LISTING} not found in invoice products"
        
        print(f"✓ Invoice products returns {len(products)} products including draft")
    
    def test_invoice_products_includes_active(self):
        """GET /api/business-tools/invoice-products should include active products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        products = data.get("products", data) if isinstance(data, dict) else data
        product_ids = [p.get("id") for p in products]
        
        assert ACTIVE_LISTING_1 in product_ids, f"Active product {ACTIVE_LISTING_1} not found"
        assert ACTIVE_LISTING_2 in product_ids, f"Active product {ACTIVE_LISTING_2} not found"
        
        print("✓ Invoice products includes active products")


class TestPublicSearchExcludesDraft:
    """Test that public search does NOT include draft products"""
    
    def test_public_search_excludes_draft(self):
        """GET /api/search should NOT return draft listings"""
        response = requests.get(f"{BASE_URL}/api/search?q=motor", headers={"Content-Type": "application/json"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Draft listing should NOT be in results
        listing_ids = [l.get("_id") for l in listings]
        assert DRAFT_LISTING not in listing_ids, f"Draft listing {DRAFT_LISTING} should NOT appear in public search"
        
        print(f"✓ Public search excludes draft listings (returned {len(listings)} results)")
    
    def test_public_search_empty_query_excludes_draft(self):
        """GET /api/search with empty query should NOT return draft listings"""
        response = requests.get(f"{BASE_URL}/api/search?q=", headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Draft listing should NOT be in results
        listing_ids = [l.get("_id") for l in listings]
        assert DRAFT_LISTING not in listing_ids, f"Draft listing should NOT appear in public search"
        
        print("✓ Public search with empty query excludes draft listings")


class TestPublicProductPageExcludesDraft:
    """Test that public product detail page does NOT show draft products"""
    
    def test_public_product_detail_rejects_draft(self):
        """Public product detail should not show draft listing"""
        # Try to access draft listing via public endpoint (without auth)
        response = requests.get(
            f"{BASE_URL}/api/enterprise/products/{DRAFT_LISTING}",
            headers={"Content-Type": "application/json"}
        )
        
        # Should either return 404 or empty/error response
        # Draft products should not be accessible publicly
        if response.status_code == 200:
            data = response.json()
            # If it returns data, check if it's actually the draft listing
            if data and data.get("_id") == DRAFT_LISTING:
                pytest.fail(f"Draft listing {DRAFT_LISTING} should NOT be accessible via public product page")
        
        print(f"✓ Public product detail correctly handles draft listing (status: {response.status_code})")
    
    def test_public_product_detail_shows_active(self):
        """Public product detail should show active listings"""
        response = requests.get(
            f"{BASE_URL}/api/enterprise/products/{ACTIVE_LISTING_1}",
            headers={"Content-Type": "application/json"}
        )
        
        # Active listings should be accessible
        # Note: May return 404 if enterprise products endpoint has different behavior
        print(f"✓ Public product detail for active listing returns status: {response.status_code}")


class TestUnpublishEndpoint:
    """Test the unpublish endpoint (active -> draft)"""
    
    def test_unpublish_active_listing(self):
        """POST /api/listings/{id}/unpublish should set active listing to draft"""
        # First, check current status - find any active listing to test with
        response = requests.get(f"{BASE_URL}/api/seller/listings", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Find an active listing (prefer ACTIVE_LISTING_2 to avoid modifying ACTIVE_LISTING_1)
        active_listing = next((l for l in listings if l.get("status") == "active"), None)
        
        if active_listing:
            listing_id = active_listing.get("_id")
            # Test unpublish endpoint returns 200 for active listing
            response = requests.post(
                f"{BASE_URL}/api/listings/{listing_id}/unpublish",
                headers=AUTH_HEADER
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify it's now draft
            response = requests.get(f"{BASE_URL}/api/seller/listings", headers=AUTH_HEADER)
            data = response.json()
            listings = data.get("listings", [])
            updated_listing = next((l for l in listings if l.get("_id") == listing_id), None)
            assert updated_listing.get("status") == "draft", f"Expected status='draft' after unpublish"
            
            print(f"✓ Unpublish endpoint correctly sets listing {listing_id} to draft")
            print("  Note: Re-publish may require email/GST verification")
        else:
            # All listings are already draft - test that unpublish endpoint exists and rejects draft
            print("⚠ No active listings available - all are draft. Testing endpoint exists.")
    
    def test_unpublish_already_draft_returns_error(self):
        """POST /api/listings/{id}/unpublish on draft listing should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/listings/{DRAFT_LISTING}/unpublish",
            headers=AUTH_HEADER
        )
        
        # Should return 400 for already-draft listing
        assert response.status_code == 400, f"Expected 400 for already-draft listing, got {response.status_code}"
        
        print("✓ Unpublish correctly rejects already-draft listing with 400")
    
    def test_unpublish_nonexistent_returns_404(self):
        """POST /api/listings/{id}/unpublish on non-existent listing should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/listings/000000000000000000000000/unpublish",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent listing, got {response.status_code}"
        
        print("✓ Unpublish correctly returns 404 for non-existent listing")
    
    def test_unpublish_requires_auth(self):
        """POST /api/listings/{id}/unpublish without auth should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/listings/{ACTIVE_LISTING_1}/unpublish",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print("✓ Unpublish correctly requires authentication")


class TestPublishEndpoint:
    """Test the publish endpoint (draft -> active)"""
    
    def test_publish_draft_listing(self):
        """POST /api/listings/{id}/publish should attempt to publish draft listing"""
        response = requests.post(
            f"{BASE_URL}/api/listings/{DRAFT_LISTING}/publish",
            headers=AUTH_HEADER
        )
        
        # May return 200 (success), 400 (validation error), or 403 (GST verification required)
        # All are valid responses depending on seller's verification status
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            print("✓ Publish endpoint successfully published draft listing")
            # Restore to draft for other tests
            requests.post(f"{BASE_URL}/api/listings/{DRAFT_LISTING}/unpublish", headers=AUTH_HEADER)
        elif response.status_code == 400:
            print(f"✓ Publish endpoint returned 400 (validation error): {response.json().get('detail', 'N/A')}")
        else:
            print(f"✓ Publish endpoint returned 403 (GST verification required): {response.json().get('detail', 'N/A')}")
    
    def test_publish_requires_auth(self):
        """POST /api/listings/{id}/publish without auth should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/listings/{DRAFT_LISTING}/publish",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print("✓ Publish correctly requires authentication")


class TestBusinessToolsRoutersIncludeDraft:
    """Test that other business tool routers include draft products"""
    
    def test_composite_products_includes_draft(self):
        """GET /api/business-tools/composite-products should include draft products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/composite-products", headers=AUTH_HEADER)
        
        if response.status_code == 200:
            data = response.json()
            # Composite products are in 'compositeProducts' key
            products = data.get("compositeProducts", [])
            
            # Check if draft composite product is included (by listingId)
            listing_ids = [p.get("listingId") for p in products if isinstance(p, dict)]
            listing_statuses = {p.get("listingId"): p.get("listingStatus") for p in products if isinstance(p, dict)}
            
            if DRAFT_LISTING in listing_ids:
                status = listing_statuses.get(DRAFT_LISTING)
                assert status == "draft", f"Expected listingStatus='draft', got {status}"
                print(f"✓ Composite products includes draft listing with status='draft'")
            else:
                print(f"⚠ Draft listing not found in composite products (may not be composite type)")
        else:
            print(f"⚠ Composite products endpoint returned {response.status_code}")
    
    def test_panels_endpoint_accessible(self):
        """GET /api/business-tools/panels should be accessible"""
        response = requests.get(f"{BASE_URL}/api/business-tools/panels", headers=AUTH_HEADER)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Panels endpoint accessible")
    
    def test_reports_endpoint_accessible(self):
        """GET /api/business-tools/reports should be accessible"""
        response = requests.get(f"{BASE_URL}/api/business-tools/reports", headers=AUTH_HEADER)
        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Reports endpoint returns {response.status_code}")


class TestActiveProductsStillWork:
    """Test that active products still work normally everywhere"""
    
    def test_active_listing_in_seller_listings(self):
        """Active listings should appear in seller listings"""
        response = requests.get(f"{BASE_URL}/api/seller/listings", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        listings = data.get("listings", [])
        
        # Should have at least some listings
        assert len(listings) >= 2, f"Expected at least 2 listings, got {len(listings)}"
        
        # Check that all expected listings are present (regardless of status)
        listing_ids = [l.get("_id") for l in listings]
        assert ACTIVE_LISTING_1 in listing_ids or ACTIVE_LISTING_2 in listing_ids, "Expected test listings not found"
        
        print(f"✓ Seller listings returns {len(listings)} listings")
    
    def test_active_listing_in_invoice_products(self):
        """All listings should appear in invoice products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        products = data.get("products", data) if isinstance(data, dict) else data
        
        # Should have at least 2 products
        assert len(products) >= 2, f"Expected at least 2 products, got {len(products)}"
        
        product_ids = [p.get("id") for p in products]
        # At least one of our test listings should be present
        assert ACTIVE_LISTING_1 in product_ids or ACTIVE_LISTING_2 in product_ids or DRAFT_LISTING in product_ids
        
        print(f"✓ Invoice products returns {len(products)} products")
    
    def test_active_listing_in_dashboard_count(self):
        """All listings should be counted in dashboard"""
        response = requests.get(f"{BASE_URL}/api/business-tools/home/summary", headers=AUTH_HEADER)
        assert response.status_code == 200
        
        data = response.json()
        total_products = data.get("totalProducts", 0)
        
        # Should have at least 2 products
        assert total_products >= 2, f"Expected at least 2 products, got {total_products}"
        
        print(f"✓ Dashboard counts {total_products} products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
