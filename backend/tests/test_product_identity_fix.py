"""
Test Product Identity and Slug URL Resolution Fix
Tests the P0 critical bug fixes for:
1. Product slug-based URL lookup
2. Seller count consistency
3. Pricing format normalization
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:8001/api').rstrip('/')


class TestProductSlugAndIdentity:
    """Test product slug-based lookup and identity resolution"""
    
    def test_health_check(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print("✓ API health check passed")
    
    def test_products_list_returns_slug(self):
        """GET /api/products should return products with slug field"""
        response = requests.get(f"{BASE_URL}/products")
        assert response.status_code == 200
        
        products = response.json()
        assert len(products) > 0, "No products returned"
        
        first_product = products[0]
        assert "slug" in first_product, "Product missing 'slug' field"
        assert first_product["slug"], "Slug should not be empty"
        assert "-" in first_product["slug"], "Slug should contain hyphens"
        assert first_product["slug"] == "three-phase-ac-motor", f"Expected slug 'three-phase-ac-motor', got '{first_product['slug']}'"
        
        print(f"✓ Products list returns slug: {first_product['slug']}")
    
    def test_products_list_returns_seller_count(self):
        """GET /api/products should return seller_count > 0"""
        response = requests.get(f"{BASE_URL}/products")
        assert response.status_code == 200
        
        products = response.json()
        assert len(products) > 0
        
        first_product = products[0]
        assert "seller_count" in first_product, "Product missing 'seller_count' field"
        assert first_product["seller_count"] > 0, "seller_count should be > 0 for visible products"
        
        print(f"✓ Products list returns seller_count: {first_product['seller_count']}")
    
    def test_product_detail_by_slug(self):
        """GET /api/products/detail/{slug} should work"""
        response = requests.get(f"{BASE_URL}/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_name"] == "Three Phase AC Motor"
        assert data["slug"] == "three-phase-ac-motor"
        assert data["seller_count"] > 0
        
        print(f"✓ Product detail by slug works: {data['product_name']}")
    
    def test_product_detail_by_objectid(self):
        """GET /api/products/detail/{ObjectId} should work"""
        # First get the ObjectId from products list
        products_response = requests.get(f"{BASE_URL}/products")
        products = products_response.json()
        product_id = products[0]["_id"]
        
        response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_id"] == product_id
        assert data["slug"] == "three-phase-ac-motor"
        
        print(f"✓ Product detail by ObjectId works: {product_id}")
    
    def test_product_detail_product_name_returns_404(self):
        """GET /api/products/detail/{product_name} should return 404 (legacy lookup removed)"""
        # Try with URL-encoded product name
        response = requests.get(f"{BASE_URL}/products/detail/Three%20Phase%20AC%20Motor")
        assert response.status_code == 404, "Product name lookup should return 404"
        
        # Also try with 'mot' (partial name)
        response2 = requests.get(f"{BASE_URL}/products/detail/mot")
        assert response2.status_code == 404
        
        print("✓ Product name lookup correctly returns 404")
    
    def test_seller_count_consistency(self):
        """Seller count should be consistent between list and detail views"""
        # Get from products list
        products_response = requests.get(f"{BASE_URL}/products")
        products = products_response.json()
        list_seller_count = products[0]["seller_count"]
        
        # Get from product detail
        detail_response = requests.get(f"{BASE_URL}/products/detail/three-phase-ac-motor")
        detail_data = detail_response.json()
        detail_seller_count = detail_data["seller_count"]
        
        assert list_seller_count == detail_seller_count, f"Seller count mismatch: list={list_seller_count}, detail={detail_seller_count}"
        
        # Also verify seller array length matches
        assert len(detail_data["sellers"]) == detail_seller_count
        
        print(f"✓ Seller count consistent: {list_seller_count} (list) == {detail_seller_count} (detail)")


class TestPricingFormat:
    """Test pricing format normalization (camelCase to snake_case)"""
    
    def test_pricing_slabs_format(self):
        """Pricing slabs should use snake_case format"""
        response = requests.get(f"{BASE_URL}/products/detail/three-phase-ac-motor")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["sellers"]) > 0
        
        seller = data["sellers"][0]
        assert "pricing_slabs" in seller
        assert len(seller["pricing_slabs"]) > 0
        
        slab = seller["pricing_slabs"][0]
        # Check snake_case fields
        assert "quantity_min" in slab, "pricing_slabs should have 'quantity_min'"
        assert "price_per_unit" in slab, "pricing_slabs should have 'price_per_unit'"
        
        # Verify values are not NaN or None for price
        assert isinstance(slab["price_per_unit"], (int, float)), "price_per_unit should be numeric"
        assert slab["price_per_unit"] > 0, "price_per_unit should be > 0"
        
        print(f"✓ Pricing format correct: quantity_min={slab['quantity_min']}, price={slab['price_per_unit']}")


class TestCategoriesPublic:
    """Test public categories endpoint"""
    
    def test_categories_public_returns_product_count(self):
        """GET /api/categories/public should return categories with correct product_count"""
        response = requests.get(f"{BASE_URL}/categories/public")
        assert response.status_code == 200
        
        categories = response.json()
        assert len(categories) > 0, "No public categories returned"
        
        # Find Electrical Equipment category
        electrical = next((c for c in categories if c["name"] == "Electrical Equipment"), None)
        assert electrical is not None, "Electrical Equipment category not found"
        assert electrical["product_count"] >= 1, f"Expected product_count >= 1, got {electrical['product_count']}"
        
        print(f"✓ Categories public: {electrical['name']} has {electrical['product_count']} products")


class TestIdentityConsistency:
    """Test that ObjectId and slug resolve to the same product"""
    
    def test_objectid_and_slug_return_same_data(self):
        """ObjectId and slug should resolve to identical product data"""
        # Get products to get ObjectId
        products_response = requests.get(f"{BASE_URL}/products")
        products = products_response.json()
        product_id = products[0]["_id"]
        product_slug = products[0]["slug"]
        
        # Get by ObjectId
        by_id_response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        by_id_data = by_id_response.json()
        
        # Get by slug
        by_slug_response = requests.get(f"{BASE_URL}/products/detail/{product_slug}")
        by_slug_data = by_slug_response.json()
        
        # Compare key fields
        assert by_id_data["product_id"] == by_slug_data["product_id"]
        assert by_id_data["product_name"] == by_slug_data["product_name"]
        assert by_id_data["slug"] == by_slug_data["slug"]
        assert by_id_data["seller_count"] == by_slug_data["seller_count"]
        
        print(f"✓ Identity consistency: ObjectId and slug return same product")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
