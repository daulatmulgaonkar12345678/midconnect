"""
Seller Catalog System Backend Tests
====================================

Tests for:
1. Seller catalog API endpoints (GET /api/seller-catalog/{slug})
2. Enterprise products API with sellerSlug in response
3. Filter API with sellerSlug in response
4. Product detail page data with sellerSlug for clickable seller names
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test seller and product data (from main agent context)
TEST_SELLER_SLUG = "seller-de460c"
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"


class TestHealthCheck:
    """Basic health check to verify backend is running"""
    
    def test_health_check(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("Health check passed")


class TestSellerCatalogAPI:
    """Tests for GET /api/seller-catalog/{slug} endpoint"""
    
    def test_seller_catalog_returns_seller_info(self):
        """Verify seller catalog returns correct seller info with sellerSlug"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify seller info structure
        assert "seller" in data, "Missing 'seller' in response"
        seller = data["seller"]
        
        assert seller.get("slug") == TEST_SELLER_SLUG, f"Seller slug mismatch: {seller.get('slug')}"
        assert "companyName" in seller, "Missing companyName in seller"
        assert "id" in seller, "Missing id in seller"
        assert "location" in seller, "Missing location in seller"
        assert "rating" in seller, "Missing rating in seller"
        
        print(f"Seller catalog returned: {seller.get('companyName')} (slug: {seller.get('slug')})")
    
    def test_seller_catalog_returns_categories_with_products(self):
        """Verify seller catalog returns products grouped by category"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify categories structure
        assert "categories" in data, "Missing 'categories' in response"
        categories = data["categories"]
        
        assert isinstance(categories, list), "Categories should be a list"
        assert len(categories) > 0, "Expected at least one category"
        
        # Verify category structure
        first_cat = categories[0]
        assert "categoryName" in first_cat, "Missing categoryName in category"
        assert "categorySlug" in first_cat, "Missing categorySlug in category"
        assert "products" in first_cat, "Missing products in category"
        assert "totalProducts" in first_cat, "Missing totalProducts in category"
        
        # Verify product structure within category
        if first_cat["products"]:
            product = first_cat["products"][0]
            assert "listingId" in product, "Missing listingId in product"
            assert "productId" in product, "Missing productId in product"
            assert "productName" in product, "Missing productName in product"
            assert "productSlug" in product, "Missing productSlug in product - needed for navigation"
            
            print(f"Found product: {product.get('productName')} (slug: {product.get('productSlug')})")
    
    def test_seller_catalog_returns_totals(self):
        """Verify seller catalog returns totalCategories and totalProducts"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "totalCategories" in data, "Missing 'totalCategories' in response"
        assert "totalProducts" in data, "Missing 'totalProducts' in response"
        
        assert isinstance(data["totalCategories"], int), "totalCategories should be int"
        assert isinstance(data["totalProducts"], int), "totalProducts should be int"
        
        print(f"Totals: {data['totalCategories']} categories, {data['totalProducts']} products")
    
    def test_seller_catalog_404_for_nonexistent_slug(self):
        """Verify 404 returned for non-existent seller slug"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/nonexistent-seller-slug-xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("404 correctly returned for non-existent seller")


class TestEnterpriseProductAPISellerSlug:
    """Tests for sellerSlug in enterprise product API responses"""
    
    def test_enterprise_product_returns_seller_slug(self):
        """Verify enterprise product API returns sellerSlug for sellers"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/enterprise")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify sellers list
        assert "sellers" in data, "Missing 'sellers' in response"
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Expected at least one seller"
        
        # Verify sellerSlug is present
        seller = sellers[0]
        assert "sellerSlug" in seller, "Missing 'sellerSlug' in seller - needed for clickable seller name"
        assert seller["sellerSlug"] == TEST_SELLER_SLUG, f"SellerSlug mismatch: {seller.get('sellerSlug')}"
        
        # Verify other seller fields needed for StandardSellerCard
        assert "sellerId" in seller, "Missing sellerId"
        assert "companyName" in seller, "Missing companyName"
        assert "listingId" in seller, "Missing listingId"
        
        print(f"Enterprise product API returned sellerSlug: {seller.get('sellerSlug')}")
    
    def test_enterprise_product_seller_has_required_fields(self):
        """Verify seller in enterprise product has all required fields for UI"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/enterprise")
        assert response.status_code == 200
        
        data = response.json()
        seller = data["sellers"][0]
        
        required_fields = [
            "listingId", "sellerId", "companyName", "location",
            "badgeType", "searchableAttributes", "pricingTiers",
            "moq", "stock", "sellerSlug"
        ]
        
        for field in required_fields:
            assert field in seller, f"Missing required field '{field}' in seller"
        
        print("All required seller fields present for UI rendering")


class TestFilterAPISellerSlug:
    """Tests for sellerSlug in filter API responses"""
    
    def test_filter_api_returns_seller_slug(self):
        """Verify filter API returns sellerSlug in results"""
        response = requests.post(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/filter",
            json={"sortBy": "price", "order": "asc", "page": 1, "limit": 10}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify results
        assert "results" in data, "Missing 'results' in response"
        results = data["results"]
        
        assert len(results) > 0, "Expected at least one result"
        
        # Verify sellerSlug is present
        result = results[0]
        assert "sellerSlug" in result, "Missing 'sellerSlug' in filter result - needed for clickable seller name"
        assert result["sellerSlug"] == TEST_SELLER_SLUG, f"SellerSlug mismatch: {result.get('sellerSlug')}"
        
        print(f"Filter API returned sellerSlug: {result.get('sellerSlug')}")
    
    def test_filter_api_with_attributes(self):
        """Verify filter API works with attribute filtering and returns sellerSlug"""
        response = requests.post(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/filter",
            json={
                "attributes": {"power": "5 HP"},
                "sortBy": "price",
                "order": "asc",
                "page": 1,
                "limit": 10
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        # If filtering found results, verify sellerSlug
        if results:
            assert "sellerSlug" in results[0], "Missing sellerSlug in filtered result"
            print(f"Filter with attributes returned sellerSlug: {results[0].get('sellerSlug')}")
        else:
            # Fallback level should be set if no exact match
            assert "fallbackLevel" in data, "Missing fallbackLevel in response"
            print(f"Filter returned fallbackLevel: {data.get('fallbackLevel')}")


class TestSellerCatalogCategoryEndpoint:
    """Tests for GET /api/seller-catalog/{slug}/category/{category_slug}"""
    
    def test_seller_category_products_returns_product_slug(self):
        """Verify category products have productSlug for navigation"""
        # First get categories from seller catalog
        response = requests.get(f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}")
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", [])
        
        if categories and categories[0].get("categorySlug"):
            category_slug = categories[0]["categorySlug"]
            
            # Get category-specific products
            cat_response = requests.get(
                f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}/category/{category_slug}"
            )
            
            if cat_response.status_code == 200:
                cat_data = cat_response.json()
                products = cat_data.get("products", [])
                
                if products:
                    product = products[0]
                    assert "productSlug" in product, "Missing productSlug - needed for product detail navigation"
                    print(f"Category products have productSlug: {product.get('productSlug')}")
            else:
                print(f"Category endpoint returned {cat_response.status_code}")
        else:
            print("No categories with slug found for testing")


class TestLegacySellerLookup:
    """Tests for legacy seller lookup (sellers collection)"""
    
    def test_seller_catalog_finds_legacy_seller(self):
        """Verify seller catalog can find seller from legacy sellers collection"""
        # seller-de460c should be in the sellers collection (not users)
        response = requests.get(f"{BASE_URL}/api/seller-catalog/{TEST_SELLER_SLUG}")
        assert response.status_code == 200, f"Legacy seller lookup failed: {response.status_code}"
        
        data = response.json()
        seller = data.get("seller", {})
        
        assert seller.get("slug") == TEST_SELLER_SLUG, "Seller slug not returned correctly"
        print(f"Legacy seller found: {seller.get('companyName')}")


class TestProductToSellerNavigation:
    """Tests to verify product-to-seller navigation data is correct"""
    
    def test_product_page_data_has_seller_link_info(self):
        """Verify product page returns all data needed for seller link"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_SLUG}/enterprise")
        assert response.status_code == 200
        
        data = response.json()
        seller = data["sellers"][0]
        
        # All data needed for SellerNameLink component
        assert seller.get("sellerSlug"), "sellerSlug required for seller link"
        assert seller.get("companyName"), "companyName required for display"
        
        expected_link = f"/seller-catalog/{seller['sellerSlug']}"
        print(f"Product page seller should link to: {expected_link}")
        print(f"Seller name to display: {seller['companyName']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
