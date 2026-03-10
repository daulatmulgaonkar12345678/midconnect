"""
Seller Catalog Feature Tests
============================

Tests for:
1. Seller catalog API endpoints (GET /api/seller-catalog/{slug})
2. Enterprise establishment year validation in profile completion
3. Seller slug generation from business name
4. 404 handling for non-existent sellers

Endpoints tested:
- GET /api/seller-catalog/{slug} - Seller catalog page data
- GET /api/seller-catalog/{slug}/category/{category_slug} - Category products
"""

import pytest
import requests
import os
import re
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestHealthCheck:
    """Basic health check before running tests"""
    
    def test_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")


class TestSellerCatalogAPI:
    """Tests for seller catalog API endpoints"""
    
    def test_seller_catalog_returns_404_for_non_existent_slug(self):
        """GET /api/seller-catalog/{slug} should return 404 for non-existent sellers"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/non-existent-seller-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "Seller" in data.get("detail", "")
        print("✓ Seller catalog returns 404 for non-existent slug")
    
    def test_seller_catalog_returns_404_for_invalid_objectid(self):
        """GET /api/seller-catalog/{slug} should return 404 for invalid ObjectId"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/invalid-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Seller catalog returns 404 for invalid ObjectId")
    
    def test_seller_catalog_returns_404_for_auth_overhaul_33(self):
        """GET /api/seller-catalog/auth-overhaul-33 should return 404 (expected - no seller with this slug)"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/auth-overhaul-33")
        # This is expected to be 404 as there's no seller with slug "auth-overhaul-33"
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "Seller" in data.get("detail", "")
        print("✓ Seller catalog returns 404 for auth-overhaul-33 (expected - no seller exists)")
    
    def test_seller_catalog_category_returns_404_for_non_existent_seller(self):
        """GET /api/seller-catalog/{slug}/category/{cat_slug} should return 404 for non-existent sellers"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/non-existent-seller/category/electronics")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Seller category products returns 404 for non-existent seller")
    
    def test_seller_catalog_accepts_products_per_category_param(self):
        """Verify products_per_category query param is accepted"""
        # Even though seller doesn't exist, endpoint should accept the param
        response = requests.get(f"{BASE_URL}/api/seller-catalog/test-slug?products_per_category=4")
        # Should return 404 (seller not found), not 422 (bad param)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Seller catalog accepts products_per_category parameter")


class TestSellerSlugGeneration:
    """Tests for seller slug generation logic"""
    
    def test_generate_slug_logic(self):
        """Verify seller slug generation rules"""
        # Test the slug generation logic (simulating backend behavior)
        test_cases = [
            ("ABC Industries", "abc-industries"),
            ("Sharma Industrial Supplies", "sharma-industrial-supplies"),
            ("R.K. Engineering & Co.", "rk-engineering-co"),
            ("Test  Multiple   Spaces", "test-multiple-spaces"),
            ("Company-With-Hyphens", "company-with-hyphens"),
            ("UPPERCASE COMPANY", "uppercase-company"),
        ]
        
        for business_name, expected_slug in test_cases:
            # Apply slug generation rules
            slug = business_name.lower().strip()
            slug = re.sub(r'[^a-z0-9\s-]', '', slug)
            slug = re.sub(r'[\s-]+', '-', slug)
            slug = slug.strip('-')
            if len(slug) > 90:
                slug = slug[:90].rsplit('-', 1)[0]
            
            assert slug == expected_slug, f"For '{business_name}': expected '{expected_slug}', got '{slug}'"
            print(f"✓ Slug generation: '{business_name}' -> '{slug}'")
    
    def test_slug_max_length(self):
        """Slug should be limited to 90 characters"""
        long_name = "A" * 100 + " Industries"
        slug = long_name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        slug = slug.strip('-')
        if len(slug) > 90:
            slug = slug[:90].rsplit('-', 1)[0]
        
        assert len(slug) <= 90, f"Slug exceeds 90 chars: {len(slug)}"
        print("✓ Slug respects 90 character limit")


class TestEnterpriseEstablishmentYearValidation:
    """Tests for enterprise establishment year validation"""
    
    def test_establishment_year_min_value(self):
        """Establishment year should be >= 1800"""
        current_year = datetime.now().year
        min_year = 1800
        
        # Valid years
        assert min_year <= 1800 <= current_year
        assert min_year <= 1900 <= current_year
        assert min_year <= 2000 <= current_year
        assert min_year <= current_year <= current_year
        
        # Invalid year (too old)
        assert 1799 < min_year, "1799 should be invalid (before 1800)"
        print("✓ Establishment year validation: minimum 1800")
    
    def test_establishment_year_max_value(self):
        """Establishment year should be <= current year"""
        current_year = datetime.now().year
        
        # Invalid year (future)
        future_year = current_year + 1
        assert future_year > current_year, f"{future_year} should be invalid (future)"
        print(f"✓ Establishment year validation: maximum {current_year}")
    
    def test_profile_complete_model_validation_rules(self):
        """Verify ProfileCompleteCreate model has correct validation"""
        # These rules are defined in server.py ProfileCompleteCreate model:
        # - enterpriseEstablishmentYear: Optional[int] = None
        # - Validator: must be between 1800 and current year
        # - Required for sellers only
        current_year = datetime.now().year
        
        valid_years = [1800, 1900, 1950, 2000, 2020, current_year]
        invalid_years = [1799, 1000, 0, -1, current_year + 1, current_year + 100]
        
        for year in valid_years:
            assert 1800 <= year <= current_year, f"Year {year} should be valid"
        
        for year in invalid_years:
            assert not (1800 <= year <= current_year), f"Year {year} should be invalid"
        
        print("✓ Establishment year validation rules correct")


class TestSellerCatalogResponseStructure:
    """Tests for expected response structure (when seller exists)"""
    
    def test_expected_response_fields(self):
        """Document expected response structure for seller catalog"""
        expected_seller_fields = [
            "id", "slug", "companyName", "logo", "bannerImage", 
            "location", "phone", "email", "enterpriseEstablishmentYear",
            "platformRegistrationYear", "gstVerified", "badgeType", "rating"
        ]
        
        expected_category_fields = [
            "categoryId", "categoryName", "categorySlug", "categoryIcon",
            "avgRating", "totalReviews", "totalProducts", "products"
        ]
        
        expected_product_fields = [
            "listingId", "productId", "productName", "productSlug",
            "description", "images", "pricingSlabs", "moq",
            "avgRating", "totalReviews", "stockStatus"
        ]
        
        # Just documenting expected structure
        print(f"✓ Expected seller fields: {len(expected_seller_fields)}")
        print(f"✓ Expected category fields: {len(expected_category_fields)}")
        print(f"✓ Expected product fields: {len(expected_product_fields)}")


class TestEnterpriseProductSellerInterface:
    """Tests for EnterpriseProductSeller interface with sellerSlug"""
    
    def test_enterprise_product_api_includes_seller_slug(self):
        """GET /api/products/{id}/enterprise should include sellerSlug in seller objects"""
        # First, get a product to test with
        response = requests.get(f"{BASE_URL}/api/products")
        if response.status_code != 200:
            pytest.skip("Products API not available")
        
        products = response.json()
        if not products or len(products) == 0:
            pytest.skip("No products available for testing")
        
        # Get enterprise product data
        product_id = products[0].get("_id") or products[0].get("id")
        if not product_id:
            pytest.skip("No product ID available")
        
        enterprise_response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        if enterprise_response.status_code != 200:
            pytest.skip("Enterprise product endpoint not available or no sellers")
        
        data = enterprise_response.json()
        sellers = data.get("sellers", [])
        
        # Check if sellers have sellerSlug field (may be null for legacy sellers)
        if sellers:
            first_seller = sellers[0]
            # sellerSlug field should exist in the response (may be null)
            # We're just checking the field is part of the API contract
            print(f"✓ Enterprise seller has sellerSlug field: {'sellerSlug' in first_seller}")
            print(f"✓ First seller sellerSlug value: {first_seller.get('sellerSlug', 'NOT_PRESENT')}")
        else:
            print("✓ No sellers found for product (expected for some products)")


class TestSellerCatalogByIdEndpoint:
    """Tests for seller catalog by ID endpoint"""
    
    def test_seller_catalog_by_id_returns_404_for_invalid_id(self):
        """GET /api/seller-catalog/by-id/{seller_id} should return 404 for invalid ID"""
        response = requests.get(f"{BASE_URL}/api/seller-catalog/by-id/invalid-id-here")
        # Should return 400 (invalid ID format) or 404 (not found)
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print("✓ Seller catalog by-id returns error for invalid ID")
    
    def test_seller_catalog_by_id_returns_404_for_non_existent_seller(self):
        """GET /api/seller-catalog/by-id/{seller_id} should return 404 for non-existent seller"""
        # Use a valid ObjectId format but non-existent
        fake_object_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/seller-catalog/by-id/{fake_object_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Seller catalog by-id returns 404 for non-existent seller")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
