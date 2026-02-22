"""
Test Admin Listings Dropdown Endpoints and Filter Parameters

Features tested:
1. GET /api/admin/listings/dropdown/products - Searchable dropdown for products
2. GET /api/admin/listings/dropdown/sellers - Searchable dropdown for sellers
3. GET /api/admin/listings?product_id=X - Filter listings by product
4. GET /api/admin/listings?seller_id=X - Filter listings by seller
5. GET /api/admin/listings?product_id=X&seller_id=Y - Combined filter
6. Verify API response includes product_name and seller_name from $lookup joins

Test data:
- productId: 6981a9a74108b0cbd93aa631 (Three Phase AC Motor)
- sellerId: 6981ea51d0f7789d258ef2ba (Test Business)
"""

import pytest
import requests
import os

# Use local URL for testing since code is running locally
BASE_URL = "http://localhost:8001/api"

# Test token for DEV MODE (no Firebase)
DEV_TOKEN = "dev-test-token"

# Known test data from previous iteration
KNOWN_PRODUCT_ID = "6981a9a74108b0cbd93aa631"  # Three Phase AC Motor
KNOWN_SELLER_ID = "6981ea51d0f7789d258ef2ba"  # Test Business


@pytest.fixture
def auth_headers():
    """Headers with admin authentication token"""
    return {
        "Authorization": f"Bearer {DEV_TOKEN}",
        "Content-Type": "application/json"
    }


class TestDropdownProducts:
    """Tests for GET /api/admin/listings/dropdown/products"""
    
    def test_products_dropdown_returns_200(self, auth_headers):
        """Verify products dropdown endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Products dropdown returned 200")
    
    def test_products_dropdown_returns_products_array(self, auth_headers):
        """Verify response contains products array"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products",
            headers=auth_headers
        )
        data = response.json()
        
        assert "products" in data, f"Missing 'products' key in response: {data}"
        assert isinstance(data["products"], list), "products should be a list"
        print(f"✓ Products dropdown contains 'products' array with {len(data['products'])} items")
    
    def test_products_dropdown_item_structure(self, auth_headers):
        """Verify each product has _id and name fields"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products",
            headers=auth_headers
        )
        data = response.json()
        
        assert len(data["products"]) > 0, "No products in dropdown"
        
        for product in data["products"]:
            assert "_id" in product, f"Product missing _id: {product}"
            assert "name" in product, f"Product missing name: {product}"
            assert isinstance(product["_id"], str), "_id should be string"
            assert isinstance(product["name"], str), "name should be string"
        
        print(f"✓ All {len(data['products'])} products have valid _id and name")
    
    def test_products_dropdown_with_search(self, auth_headers):
        """Test search functionality filters products"""
        # Search for "Motor" - should find products with Motor in name
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products?search=Motor",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert "products" in data
        
        # If products returned, they should contain "Motor" in name (case insensitive)
        for product in data["products"]:
            assert "motor" in product["name"].lower(), f"Search filter not working: {product['name']}"
        
        print(f"✓ Search 'Motor' returned {len(data['products'])} products")
    
    def test_products_dropdown_with_limit(self, auth_headers):
        """Test limit parameter"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products?limit=5",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert len(data["products"]) <= 5, f"Limit not respected: got {len(data['products'])} items"
        print(f"✓ Limit=5 respected, returned {len(data['products'])} products")
    
    def test_products_dropdown_includes_known_product(self, auth_headers):
        """Verify known product appears in dropdown"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/products?search=Three%20Phase",
            headers=auth_headers
        )
        data = response.json()
        
        product_ids = [p["_id"] for p in data["products"]]
        
        # The known product should be in results
        assert any("Three Phase" in p["name"] for p in data["products"]), \
            f"Expected 'Three Phase AC Motor' in results: {data['products']}"
        
        print(f"✓ Known product 'Three Phase AC Motor' found in dropdown")


class TestDropdownSellers:
    """Tests for GET /api/admin/listings/dropdown/sellers"""
    
    def test_sellers_dropdown_returns_200(self, auth_headers):
        """Verify sellers dropdown endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/sellers",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Sellers dropdown returned 200")
    
    def test_sellers_dropdown_returns_sellers_array(self, auth_headers):
        """Verify response contains sellers array"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/sellers",
            headers=auth_headers
        )
        data = response.json()
        
        assert "sellers" in data, f"Missing 'sellers' key in response: {data}"
        assert isinstance(data["sellers"], list), "sellers should be a list"
        print(f"✓ Sellers dropdown contains 'sellers' array with {len(data['sellers'])} items")
    
    def test_sellers_dropdown_item_structure(self, auth_headers):
        """Verify each seller has _id, business_name, and email fields"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/sellers",
            headers=auth_headers
        )
        data = response.json()
        
        assert len(data["sellers"]) > 0, "No sellers in dropdown"
        
        for seller in data["sellers"]:
            assert "_id" in seller, f"Seller missing _id: {seller}"
            assert "business_name" in seller, f"Seller missing business_name: {seller}"
            assert "email" in seller, f"Seller missing email: {seller}"
        
        print(f"✓ All {len(data['sellers'])} sellers have valid _id, business_name, email")
    
    def test_sellers_dropdown_with_search(self, auth_headers):
        """Test search functionality filters sellers"""
        # Search for "Test" - should find Test Business
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/sellers?search=Test",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert "sellers" in data
        
        # If sellers returned, they should match search term
        if data["sellers"]:
            for seller in data["sellers"]:
                name_match = "test" in seller.get("business_name", "").lower()
                email_match = "test" in seller.get("email", "").lower()
                assert name_match or email_match, f"Search filter not working: {seller}"
        
        print(f"✓ Search 'Test' returned {len(data['sellers'])} sellers")
    
    def test_sellers_dropdown_with_limit(self, auth_headers):
        """Test limit parameter"""
        response = requests.get(
            f"{BASE_URL}/admin/listings/dropdown/sellers?limit=5",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert len(data["sellers"]) <= 5, f"Limit not respected: got {len(data['sellers'])} items"
        print(f"✓ Limit=5 respected, returned {len(data['sellers'])} sellers")


class TestListingsFilterByProduct:
    """Tests for GET /api/admin/listings?product_id=X"""
    
    def test_filter_by_product_returns_200(self, auth_headers):
        """Test filtering by product_id"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Filter by product_id returned 200")
    
    def test_filter_by_product_returns_matching_listings(self, auth_headers):
        """Verify filtered listings match the product_id"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "listings" in data, f"Missing 'listings' key: {data}"
        
        # All returned listings should have the matching productId
        for listing in data["listings"]:
            assert listing["productId"] == KNOWN_PRODUCT_ID, \
                f"Listing productId mismatch: expected {KNOWN_PRODUCT_ID}, got {listing['productId']}"
        
        print(f"✓ All {len(data['listings'])} listings match product_id filter")
    
    def test_filter_by_product_includes_joined_fields(self, auth_headers):
        """Verify $lookup joins populate product_name and seller_name"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        if data["listings"]:
            listing = data["listings"][0]
            
            # Check joined fields exist
            assert "product_name" in listing, f"Missing product_name in listing: {listing.keys()}"
            assert "seller_name" in listing, f"Missing seller_name in listing: {listing.keys()}"
            
            # Verify product_name matches expected value
            assert listing["product_name"] == "Three Phase AC Motor", \
                f"Expected product_name='Three Phase AC Motor', got '{listing['product_name']}'"
            
            print(f"✓ Joined fields present: product_name='{listing['product_name']}', seller_name='{listing['seller_name']}'")
        else:
            print(f"⚠ No listings found for product {KNOWN_PRODUCT_ID}")


class TestListingsFilterBySeller:
    """Tests for GET /api/admin/listings?seller_id=X"""
    
    def test_filter_by_seller_returns_200(self, auth_headers):
        """Test filtering by seller_id"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Filter by seller_id returned 200")
    
    def test_filter_by_seller_returns_matching_listings(self, auth_headers):
        """Verify filtered listings match the seller_id"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "listings" in data, f"Missing 'listings' key: {data}"
        
        # All returned listings should have the matching sellerId
        for listing in data["listings"]:
            assert listing["sellerId"] == KNOWN_SELLER_ID, \
                f"Listing sellerId mismatch: expected {KNOWN_SELLER_ID}, got {listing['sellerId']}"
        
        print(f"✓ All {len(data['listings'])} listings match seller_id filter")
    
    def test_filter_by_seller_includes_seller_name(self, auth_headers):
        """Verify seller_name is populated from $lookup join"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        if data["listings"]:
            listing = data["listings"][0]
            
            assert "seller_name" in listing, f"Missing seller_name in listing"
            assert listing["seller_name"] is not None, "seller_name should not be null"
            
            # Verify seller_name contains expected value (business_name might include email)
            assert "Test Business" in listing["seller_name"], \
                f"Expected seller_name to contain 'Test Business', got '{listing['seller_name']}'"
            
            print(f"✓ seller_name from $lookup: '{listing['seller_name']}'")
        else:
            print(f"⚠ No listings found for seller {KNOWN_SELLER_ID}")


class TestListingsCombinedFilter:
    """Tests for GET /api/admin/listings?product_id=X&seller_id=Y"""
    
    def test_combined_filter_returns_200(self, auth_headers):
        """Test combined product_id + seller_id filter"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}&seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Combined filter returned 200")
    
    def test_combined_filter_returns_specific_listing(self, auth_headers):
        """Verify combined filter returns the specific listing"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}&seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "listings" in data
        
        # With unique compound index, should get exactly 1 or 0 listings
        assert len(data["listings"]) <= 1, \
            f"Combined filter should return at most 1 listing (unique constraint), got {len(data['listings'])}"
        
        if data["listings"]:
            listing = data["listings"][0]
            assert listing["productId"] == KNOWN_PRODUCT_ID
            assert listing["sellerId"] == KNOWN_SELLER_ID
            print(f"✓ Combined filter returned exactly 1 matching listing")
        else:
            print(f"⚠ No listing found for product+seller combination")
    
    def test_combined_filter_includes_all_joined_fields(self, auth_headers):
        """Verify all joined fields are present in response"""
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={KNOWN_PRODUCT_ID}&seller_id={KNOWN_SELLER_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        if data["listings"]:
            listing = data["listings"][0]
            
            # Core listing fields
            assert "_id" in listing
            assert "productId" in listing
            assert "sellerId" in listing
            assert "status" in listing
            assert "stock" in listing
            assert "leadTime" in listing
            assert "pricingTiers" in listing
            
            # Joined fields from $lookup
            assert "product_name" in listing
            assert "seller_name" in listing
            
            # Verify joined values are correct
            assert listing["product_name"] == "Three Phase AC Motor"
            assert "Test Business" in listing["seller_name"]
            
            print(f"✓ All core and joined fields present with correct values")
            print(f"  product_name: {listing['product_name']}")
            print(f"  seller_name: {listing['seller_name']}")
        else:
            pytest.skip("No listing found for combined filter test")


class TestListingsFilterNonExistent:
    """Tests for filtering with non-existent IDs"""
    
    def test_filter_by_nonexistent_product_returns_empty(self, auth_headers):
        """Filter by non-existent product returns empty list"""
        fake_id = "000000000000000000000000"
        response = requests.get(
            f"{BASE_URL}/admin/listings?product_id={fake_id}",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert data["listings"] == [], f"Expected empty list for non-existent product"
        assert data["total"] == 0
        
        print(f"✓ Non-existent product filter returns empty list")
    
    def test_filter_by_nonexistent_seller_returns_empty(self, auth_headers):
        """Filter by non-existent seller returns empty list"""
        fake_id = "000000000000000000000000"
        response = requests.get(
            f"{BASE_URL}/admin/listings?seller_id={fake_id}",
            headers=auth_headers
        )
        data = response.json()
        
        assert response.status_code == 200
        assert data["listings"] == [], f"Expected empty list for non-existent seller"
        assert data["total"] == 0
        
        print(f"✓ Non-existent seller filter returns empty list")


class TestAdminAuth:
    """Verify endpoints require admin authentication"""
    
    def test_products_dropdown_requires_auth(self):
        """Products dropdown should require auth"""
        response = requests.get(f"{BASE_URL}/admin/listings/dropdown/products")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Products dropdown requires authentication")
    
    def test_sellers_dropdown_requires_auth(self):
        """Sellers dropdown should require auth"""
        response = requests.get(f"{BASE_URL}/admin/listings/dropdown/sellers")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Sellers dropdown requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
