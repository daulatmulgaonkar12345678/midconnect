"""
Test Suite: Product Slug & Identity Resolution
----------------------------------------------
Tests the P0 CRITICAL bug fixes for product identity consistency:
1. GET /api/products - Returns products with slug field
2. GET /api/products/detail/{slug} - Lookup by slug works
3. GET /api/products/detail/{ObjectId} - Lookup by ObjectId works
4. GET /api/products/detail/{product_name} - Legacy product_name lookup returns 404 (removed)
5. GET /api/categories/public - Returns categories with correct product_count
6. Verify slug is unique for each product
7. Verify ObjectId and slug resolve to same product (identity consistency)

Related to: Migration V4_add_product_slugs.py
"""

import pytest
import requests
import os
from urllib.parse import quote

# Get BASE_URL from environment - support multiple env var names
BASE_URL = os.environ.get('NEXT_PUBLIC_API_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Fallback for Expo frontend env variable name
    BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'http://localhost:8001/api'

print(f"BASE_URL: {BASE_URL}")


class TestProductSlugIdentity:
    """Test product slug implementation and identity resolution"""
    
    def test_products_endpoint_returns_slug_field(self):
        """GET /api/products should return products with slug field"""
        response = requests.get(f"{BASE_URL}/products")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        products = response.json()
        print(f"\n[Test] GET /api/products returned {len(products)} products")
        
        if len(products) > 0:
            # Check that slug field exists in response
            first_product = products[0]
            print(f"  Product: {first_product.get('name')}")
            print(f"  Product ID: {first_product.get('_id')}")
            print(f"  Slug: {first_product.get('slug')}")
            print(f"  Seller count: {first_product.get('seller_count')}")
            
            # Slug should exist in products with active listings
            assert 'slug' in first_product, "Products should have 'slug' field"
            assert first_product.get('slug') is not None or len(products) == 0, "Slug should not be None for active products"
            
            # Verify other essential fields
            assert first_product.get('_id'), "Product should have _id"
            assert first_product.get('name'), "Product should have name"
            
    def test_categories_public_returns_product_count(self):
        """GET /api/categories/public should return categories with correct product_count"""
        response = requests.get(f"{BASE_URL}/categories/public")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        categories = response.json()
        print(f"\n[Test] GET /api/categories/public returned {len(categories)} categories")
        
        if len(categories) > 0:
            for cat in categories:
                print(f"  Category: {cat.get('name')}")
                print(f"    ID: {cat.get('_id')}")
                print(f"    Product count: {cat.get('product_count')}")
                print(f"    Listing count: {cat.get('listing_count')}")
                
                # Product count should be a positive integer
                assert cat.get('product_count', 0) >= 0, "product_count should be non-negative"
                assert isinstance(cat.get('product_count'), int), "product_count should be an integer"
    
    def test_product_detail_by_objectid(self):
        """GET /api/products/detail/{ObjectId} should work for valid ObjectId"""
        # First get a product ID from /api/products
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200, f"Failed to get products: {products_response.text}"
        
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for testing")
        
        product_id = products[0].get('_id')
        product_name = products[0].get('name')
        product_slug = products[0].get('slug')
        
        print(f"\n[Test] Testing ObjectId lookup for: {product_name}")
        print(f"  ObjectId: {product_id}")
        
        # Now get product detail by ObjectId
        detail_response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        
        assert detail_response.status_code == 200, f"Expected 200, got {detail_response.status_code}: {detail_response.text}"
        
        detail = detail_response.json()
        print(f"  Found product: {detail.get('product_name')}")
        print(f"  Slug: {detail.get('slug')}")
        print(f"  Seller count: {detail.get('seller_count')}")
        
        # Verify identity consistency
        assert detail.get('product_id') == product_id, "product_id should match requested ObjectId"
        assert detail.get('product_name') == product_name, "product_name should match"
        if product_slug:
            assert detail.get('slug') == product_slug, "slug should match"
    
    def test_product_detail_by_slug(self):
        """GET /api/products/detail/{slug} should work for valid slug"""
        # First get a product with slug from /api/products
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for testing")
        
        # Find a product with a slug
        product_with_slug = None
        for p in products:
            if p.get('slug'):
                product_with_slug = p
                break
        
        if not product_with_slug:
            pytest.skip("No products with slug available for testing")
        
        product_id = product_with_slug.get('_id')
        product_name = product_with_slug.get('name')
        product_slug = product_with_slug.get('slug')
        
        print(f"\n[Test] Testing slug lookup for: {product_name}")
        print(f"  Slug: {product_slug}")
        
        # Now get product detail by slug
        detail_response = requests.get(f"{BASE_URL}/products/detail/{product_slug}")
        
        assert detail_response.status_code == 200, f"Expected 200 for slug lookup, got {detail_response.status_code}: {detail_response.text}"
        
        detail = detail_response.json()
        print(f"  Found product: {detail.get('product_name')}")
        print(f"  Product ID: {detail.get('product_id')}")
        
        # Verify identity consistency
        assert detail.get('product_id') == product_id, f"product_id should match: expected {product_id}, got {detail.get('product_id')}"
        assert detail.get('product_name') == product_name, "product_name should match"
        assert detail.get('slug') == product_slug, "slug should match"
    
    def test_product_detail_by_product_name_returns_404(self):
        """GET /api/products/detail/{product_name} should return 404 (legacy fallback removed)"""
        # This tests that product_name lookup is NO LONGER supported
        # The system should only resolve by ObjectId or slug
        
        # Test with a known product name that would have worked before
        # Using a realistic product name that's NOT a valid ObjectId or slug
        test_names = [
            "Three Phase AC Motor",  # spaces and capitals - not a slug
            "Three%20Phase%20AC%20Motor",  # URL encoded with spaces
            "mot",  # Legacy short name
            "some-random-product-name-that-does-not-exist"
        ]
        
        print(f"\n[Test] Testing that product_name lookups return 404")
        
        for name in test_names:
            response = requests.get(f"{BASE_URL}/products/detail/{quote(name, safe='')}")
            print(f"  {name}: status={response.status_code}")
            
            # These should all return 404 (not found)
            # Since they are not valid ObjectIds or slugs
            assert response.status_code == 404, f"Expected 404 for '{name}', got {response.status_code}"
    
    def test_objectid_and_slug_resolve_to_same_product(self):
        """ObjectId and slug should resolve to the same product (identity consistency)"""
        # First get a product with both ID and slug
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for testing")
        
        # Find a product with a slug
        product_with_slug = None
        for p in products:
            if p.get('slug') and p.get('_id'):
                product_with_slug = p
                break
        
        if not product_with_slug:
            pytest.skip("No products with both ID and slug available")
        
        product_id = product_with_slug.get('_id')
        product_slug = product_with_slug.get('slug')
        
        print(f"\n[Test] Testing identity consistency")
        print(f"  ObjectId: {product_id}")
        print(f"  Slug: {product_slug}")
        
        # Get product by ObjectId
        response_by_id = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        assert response_by_id.status_code == 200, f"Failed to get by ObjectId: {response_by_id.text}"
        
        # Get product by slug
        response_by_slug = requests.get(f"{BASE_URL}/products/detail/{product_slug}")
        assert response_by_slug.status_code == 200, f"Failed to get by slug: {response_by_slug.text}"
        
        detail_by_id = response_by_id.json()
        detail_by_slug = response_by_slug.json()
        
        print(f"  By ObjectId: {detail_by_id.get('product_name')} (id: {detail_by_id.get('product_id')})")
        print(f"  By Slug: {detail_by_slug.get('product_name')} (id: {detail_by_slug.get('product_id')})")
        
        # Both should return the same product
        assert detail_by_id.get('product_id') == detail_by_slug.get('product_id'), "Both lookups should return same product_id"
        assert detail_by_id.get('product_name') == detail_by_slug.get('product_name'), "Both lookups should return same product_name"
        assert detail_by_id.get('slug') == detail_by_slug.get('slug'), "Both lookups should return same slug"
        assert detail_by_id.get('seller_count') == detail_by_slug.get('seller_count'), "Both lookups should return same seller_count"
    
    def test_slug_uniqueness_across_products(self):
        """Verify slugs are unique for each product"""
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        
        if len(products) < 2:
            pytest.skip("Need at least 2 products to test uniqueness")
        
        slugs = [p.get('slug') for p in products if p.get('slug')]
        unique_slugs = set(slugs)
        
        print(f"\n[Test] Testing slug uniqueness")
        print(f"  Total products: {len(products)}")
        print(f"  Products with slugs: {len(slugs)}")
        print(f"  Unique slugs: {len(unique_slugs)}")
        
        # All slugs should be unique
        assert len(slugs) == len(unique_slugs), f"Slugs should be unique. Found duplicates in: {slugs}"
        
        # Show all slugs
        for i, p in enumerate(products[:5]):
            print(f"  Product {i+1}: {p.get('name')} -> slug: {p.get('slug')}")


class TestSellerCountConsistency:
    """Test seller count consistency between endpoints"""
    
    def test_product_list_seller_count_matches_detail(self):
        """Seller count in /api/products should match count in /api/products/detail"""
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for testing")
        
        print(f"\n[Test] Testing seller count consistency")
        
        for p in products[:3]:  # Test first 3 products
            product_id = p.get('_id')
            list_seller_count = p.get('seller_count', 0)
            
            # Get detail
            detail_response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
            
            if detail_response.status_code == 200:
                detail = detail_response.json()
                detail_seller_count = detail.get('seller_count', 0)
                
                print(f"  {p.get('name')}:")
                print(f"    List seller_count: {list_seller_count}")
                print(f"    Detail seller_count: {detail_seller_count}")
                
                # P0 Bug: These should match!
                assert list_seller_count == detail_seller_count, (
                    f"Seller count mismatch for {p.get('name')}: "
                    f"list={list_seller_count}, detail={detail_seller_count}"
                )
            else:
                print(f"  {p.get('name')}: detail endpoint returned {detail_response.status_code}")
    
    def test_category_product_count_matches_products_list(self):
        """Product count in /api/categories/public should match filtered /api/products"""
        categories_response = requests.get(f"{BASE_URL}/categories/public")
        assert categories_response.status_code == 200
        
        categories = categories_response.json()
        if len(categories) == 0:
            pytest.skip("No categories available for testing")
        
        print(f"\n[Test] Testing category product count consistency")
        
        for cat in categories[:3]:  # Test first 3 categories
            category_id = cat.get('_id')
            category_product_count = cat.get('product_count', 0)
            
            # Get products filtered by this category
            products_response = requests.get(f"{BASE_URL}/products?category_id={category_id}")
            
            if products_response.status_code == 200:
                products = products_response.json()
                actual_product_count = len(products)
                
                print(f"  {cat.get('name')}:")
                print(f"    Category product_count: {category_product_count}")
                print(f"    Actual products in category: {actual_product_count}")
                
                # These should match
                assert category_product_count == actual_product_count, (
                    f"Product count mismatch for category {cat.get('name')}: "
                    f"category={category_product_count}, actual={actual_product_count}"
                )


class TestProductImageDisplay:
    """Test that product images are returned correctly"""
    
    def test_product_detail_has_images_array(self):
        """Product detail should include images array"""
        products_response = requests.get(f"{BASE_URL}/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        if len(products) == 0:
            pytest.skip("No products available for testing")
        
        product_id = products[0].get('_id')
        
        detail_response = requests.get(f"{BASE_URL}/products/detail/{product_id}")
        assert detail_response.status_code == 200
        
        detail = detail_response.json()
        
        print(f"\n[Test] Testing product images")
        print(f"  Product: {detail.get('product_name')}")
        print(f"  Images field exists: {'images' in detail}")
        print(f"  Images count: {len(detail.get('images', []))}")
        
        # Images should be an array (even if empty)
        assert 'images' in detail, "Product detail should have 'images' field"
        assert isinstance(detail.get('images'), list), "images should be a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
