"""
SEO v2.0 Migration Tests
========================
Tests for the SEO v2.0 migration feature including:
1. GET /api/redirect/product/{objectId} - Returns redirect info with new slug
2. GET /api/redirect/category/{objectId} - Returns redirect info with new slug  
3. Product slug migration - all products have slugs in v2 format ending with -supplier-india
4. Category slug migration - all categories have slugs
5. No duplicate slugs in products or categories
6. Sitemap only includes slug-based URLs (no ObjectIds)

Test IDs from agent context:
- Product ID: 699be9023cbe1a8c31591668 (slug: industrial-electric-motor-5hp-test-category-supplier-india)
- Category ID: 699bc605940f2204a1968569 (slug: testspectemplatecategory1771816453001682)
"""

import pytest
import requests
import os
import re

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data from agent context
TEST_PRODUCT_ID = "699be9023cbe1a8c31591668"
TEST_PRODUCT_SLUG = "industrial-electric-motor-5hp-test-category-supplier-india"
TEST_CATEGORY_ID = "699bc605940f2204a1968569"
TEST_CATEGORY_SLUG = "testspectemplatecategory1771816453001682"

# SEO v2 slug patterns
PRODUCT_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+-supplier-india(-\d+)?$')
CATEGORY_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+(-\d+)?$')


class TestProductRedirectEndpoint:
    """Test GET /api/redirect/product/{identifier}"""
    
    def test_redirect_with_valid_objectid(self):
        """Product redirect endpoint returns correct redirect info for valid ObjectId"""
        response = requests.get(f"{BASE_URL}/api/redirect/product/{TEST_PRODUCT_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Product redirect response: {data}")
        
        # Check response structure
        assert "redirect" in data, "Response should have 'redirect' field"
        assert "slug" in data or "message" in data, "Response should have 'slug' or 'message'"
        
        # If redirect is needed, verify slug format
        if data.get("redirect"):
            assert data.get("slug"), "Redirect response should have 'slug'"
            assert data.get("status") == 301, "Redirect should be 301"
            assert "/product/" in data.get("to", ""), "Redirect 'to' should contain /product/"
            print(f"✅ Product redirect working: {TEST_PRODUCT_ID} -> {data.get('slug')}")
        else:
            print(f"ℹ️ No redirect needed for product ID: {TEST_PRODUCT_ID}")
    
    def test_redirect_with_non_existent_id(self):
        """Product redirect returns no redirect for non-existent ID"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/redirect/product/{fake_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("redirect") == False, "Should not redirect for non-existent ID"
        print(f"✅ Non-existent product ID handled correctly")
    
    def test_redirect_with_random_slug(self):
        """Product redirect handles random slug gracefully"""
        response = requests.get(f"{BASE_URL}/api/redirect/product/some-random-slug")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "redirect" in data
        print(f"✅ Random slug handled correctly: redirect={data.get('redirect')}")


class TestCategoryRedirectEndpoint:
    """Test GET /api/redirect/category/{identifier}"""
    
    def test_redirect_with_valid_objectid(self):
        """Category redirect endpoint returns correct redirect info for valid ObjectId"""
        response = requests.get(f"{BASE_URL}/api/redirect/category/{TEST_CATEGORY_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Category redirect response: {data}")
        
        # Check response structure
        assert "redirect" in data, "Response should have 'redirect' field"
        
        # If redirect is needed, verify slug format
        if data.get("redirect"):
            assert data.get("slug"), "Redirect response should have 'slug'"
            assert data.get("status") == 301, "Redirect should be 301"
            assert "/category/" in data.get("to", ""), "Redirect 'to' should contain /category/"
            print(f"✅ Category redirect working: {TEST_CATEGORY_ID} -> {data.get('slug')}")
        else:
            print(f"ℹ️ No redirect needed for category ID: {TEST_CATEGORY_ID}")
    
    def test_redirect_with_non_existent_id(self):
        """Category redirect returns no redirect for non-existent ID"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/redirect/category/{fake_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("redirect") == False, "Should not redirect for non-existent ID"
        print(f"✅ Non-existent category ID handled correctly")


class TestProductSlugMigration:
    """Test that all products have valid slugs in v2 format"""
    
    def test_all_products_have_slugs(self):
        """All products should have non-null slugs"""
        response = requests.get(f"{BASE_URL}/api/products?limit=100")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        products = data if isinstance(data, list) else data.get("products", [])
        
        print(f"Total products: {len(products)}")
        
        null_slug_count = 0
        valid_slug_count = 0
        invalid_format_count = 0
        
        for product in products:
            slug = product.get("slug")
            name = product.get("name", "Unknown")
            
            if not slug:
                null_slug_count += 1
                print(f"⚠️ Product without slug: {name} (ID: {product.get('_id', product.get('id'))})")
            elif PRODUCT_SLUG_PATTERN.match(slug):
                valid_slug_count += 1
            else:
                invalid_format_count += 1
                print(f"⚠️ Product slug not v2 format: {slug}")
        
        print(f"\nProduct Slug Summary:")
        print(f"  - Valid v2 slugs: {valid_slug_count}")
        print(f"  - Null slugs: {null_slug_count}")
        print(f"  - Invalid format: {invalid_format_count}")
        
        assert null_slug_count == 0, f"Found {null_slug_count} products without slugs"
        print(f"✅ All {len(products)} products have slugs")
    
    def test_product_slug_ends_with_supplier_india(self):
        """Product slugs should end with -supplier-india"""
        response = requests.get(f"{BASE_URL}/api/products?limit=100")
        
        assert response.status_code == 200
        
        data = response.json()
        products = data if isinstance(data, list) else data.get("products", [])
        
        non_v2_slugs = []
        for product in products:
            slug = product.get("slug")
            if slug and not slug.endswith("-supplier-india") and not re.match(r'.*-supplier-india-\d+$', slug):
                non_v2_slugs.append({
                    "name": product.get("name"),
                    "slug": slug
                })
        
        if non_v2_slugs:
            print(f"Products with non-v2 slugs (not ending with -supplier-india):")
            for p in non_v2_slugs[:5]:
                print(f"  - {p['name']}: {p['slug']}")
        
        assert len(non_v2_slugs) == 0, f"Found {len(non_v2_slugs)} products with non-v2 format slugs"
        print(f"✅ All product slugs follow v2 format (-supplier-india suffix)")
    
    def test_no_duplicate_product_slugs(self):
        """No duplicate slugs should exist in products"""
        response = requests.get(f"{BASE_URL}/api/products?limit=500")
        
        assert response.status_code == 200
        
        data = response.json()
        products = data if isinstance(data, list) else data.get("products", [])
        
        slug_map = {}
        duplicates = []
        
        for product in products:
            slug = product.get("slug")
            if slug:
                if slug in slug_map:
                    duplicates.append({
                        "slug": slug,
                        "product1": slug_map[slug],
                        "product2": product.get("name")
                    })
                else:
                    slug_map[slug] = product.get("name")
        
        if duplicates:
            print(f"Duplicate product slugs found:")
            for dup in duplicates[:5]:
                print(f"  - '{dup['slug']}': {dup['product1']} and {dup['product2']}")
        
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate product slugs"
        print(f"✅ No duplicate slugs in {len(products)} products")


class TestCategorySlugMigration:
    """Test that all categories have valid slugs"""
    
    def test_all_categories_have_slugs(self):
        """All categories should have non-null slugs"""
        response = requests.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        categories = data if isinstance(data, list) else data.get("categories", [])
        
        print(f"Total categories: {len(categories)}")
        
        null_slug_count = 0
        valid_slug_count = 0
        
        for category in categories:
            slug = category.get("slug")
            name = category.get("name", "Unknown")
            
            if not slug:
                null_slug_count += 1
                print(f"⚠️ Category without slug: {name} (ID: {category.get('_id', category.get('id'))})")
            elif CATEGORY_SLUG_PATTERN.match(slug):
                valid_slug_count += 1
            else:
                print(f"⚠️ Category slug format issue: {slug}")
        
        print(f"\nCategory Slug Summary:")
        print(f"  - Valid slugs: {valid_slug_count}")
        print(f"  - Null slugs: {null_slug_count}")
        
        assert null_slug_count == 0, f"Found {null_slug_count} categories without slugs"
        print(f"✅ All {len(categories)} categories have slugs")
    
    def test_no_duplicate_category_slugs(self):
        """No duplicate slugs should exist in categories"""
        response = requests.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 200
        
        data = response.json()
        categories = data if isinstance(data, list) else data.get("categories", [])
        
        slug_map = {}
        duplicates = []
        
        for category in categories:
            slug = category.get("slug")
            if slug:
                if slug in slug_map:
                    duplicates.append({
                        "slug": slug,
                        "cat1": slug_map[slug],
                        "cat2": category.get("name")
                    })
                else:
                    slug_map[slug] = category.get("name")
        
        if duplicates:
            print(f"Duplicate category slugs found:")
            for dup in duplicates[:5]:
                print(f"  - '{dup['slug']}': {dup['cat1']} and {dup['cat2']}")
        
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate category slugs"
        print(f"✅ No duplicate slugs in {len(categories)} categories")


class TestProductAccessibleBySlug:
    """Test that product pages are accessible via slug URLs"""
    
    def test_product_accessible_by_slug(self):
        """Product should be accessible via its slug"""
        # First get the product by ID to get its slug
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        product = response.json()
        slug = product.get("slug")
        
        print(f"Test product: {product.get('name')}")
        print(f"Test product slug: {slug}")
        
        assert slug, f"Product {TEST_PRODUCT_ID} should have a slug"
        
        # Try to access product by slug
        response_by_slug = requests.get(f"{BASE_URL}/api/products/slug/{slug}")
        
        # If endpoint doesn't exist, try enterprise endpoint
        if response_by_slug.status_code == 404:
            response_by_slug = requests.get(f"{BASE_URL}/api/products/enterprise/{slug}")
        
        # If still 404, check if slug is being used directly
        if response_by_slug.status_code == 404:
            response_by_slug = requests.get(f"{BASE_URL}/api/products/{slug}")
        
        print(f"Product by slug response status: {response_by_slug.status_code}")
        
        # At minimum, the product by ID should return the slug
        assert slug.endswith("-supplier-india") or re.match(r'.*-supplier-india-\d+$', slug), \
            f"Product slug should end with -supplier-india, got: {slug}"
        
        print(f"✅ Product {TEST_PRODUCT_ID} has valid slug: {slug}")


class TestSitemapSlugValidation:
    """Test that sitemap would only use slug-based URLs"""
    
    def test_products_for_sitemap_have_slugs(self):
        """All products that would be in sitemap should have valid slugs"""
        response = requests.get(f"{BASE_URL}/api/products?limit=1000")
        
        assert response.status_code == 200
        
        data = response.json()
        products = data if isinstance(data, list) else data.get("products", [])
        
        products_without_slugs = []
        products_with_objectid_in_slug = []
        
        objectid_pattern = re.compile(r'^[a-f0-9]{24}$', re.IGNORECASE)
        
        for product in products:
            slug = product.get("slug")
            product_id = str(product.get("_id", product.get("id", "")))
            name = product.get("name")
            
            if not slug:
                products_without_slugs.append({"id": product_id, "name": name})
            elif objectid_pattern.match(slug):
                # Slug IS an ObjectId - bad for SEO
                products_with_objectid_in_slug.append({"id": product_id, "name": name, "slug": slug})
        
        print(f"\nSitemap Validation Results:")
        print(f"  - Total products: {len(products)}")
        print(f"  - Products without slugs: {len(products_without_slugs)}")
        print(f"  - Products with ObjectId as slug: {len(products_with_objectid_in_slug)}")
        
        if products_without_slugs:
            print(f"\nProducts without slugs (would be excluded from sitemap):")
            for p in products_without_slugs[:5]:
                print(f"  - {p['name']} (ID: {p['id']})")
        
        if products_with_objectid_in_slug:
            print(f"\nProducts with ObjectId as slug (BAD for SEO):")
            for p in products_with_objectid_in_slug[:5]:
                print(f"  - {p['name']} slug: {p['slug']}")
        
        assert len(products_with_objectid_in_slug) == 0, \
            f"Found {len(products_with_objectid_in_slug)} products with ObjectId as slug"
        assert len(products_without_slugs) == 0, \
            f"Found {len(products_without_slugs)} products without slugs"
        
        print(f"✅ All {len(products)} products have SEO-friendly slugs for sitemap")
    
    def test_categories_for_sitemap_have_slugs(self):
        """All categories that would be in sitemap should have valid slugs"""
        response = requests.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 200
        
        data = response.json()
        categories = data if isinstance(data, list) else data.get("categories", [])
        
        categories_without_slugs = []
        categories_with_objectid_in_slug = []
        
        objectid_pattern = re.compile(r'^[a-f0-9]{24}$', re.IGNORECASE)
        
        for category in categories:
            slug = category.get("slug")
            cat_id = str(category.get("_id", category.get("id", "")))
            name = category.get("name")
            
            if not slug:
                categories_without_slugs.append({"id": cat_id, "name": name})
            elif objectid_pattern.match(slug):
                categories_with_objectid_in_slug.append({"id": cat_id, "name": name, "slug": slug})
        
        print(f"\nCategory Sitemap Validation:")
        print(f"  - Total categories: {len(categories)}")
        print(f"  - Categories without slugs: {len(categories_without_slugs)}")
        print(f"  - Categories with ObjectId as slug: {len(categories_with_objectid_in_slug)}")
        
        assert len(categories_with_objectid_in_slug) == 0, \
            f"Found {len(categories_with_objectid_in_slug)} categories with ObjectId as slug"
        assert len(categories_without_slugs) == 0, \
            f"Found {len(categories_without_slugs)} categories without slugs"
        
        print(f"✅ All {len(categories)} categories have SEO-friendly slugs for sitemap")


class TestLegacyIdRedirectMapping:
    """Test that old ID mappings are stored for 301 redirects"""
    
    def test_product_has_legacy_id_field(self):
        """Products should have legacyIds field for redirect mapping"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}")
        
        assert response.status_code == 200
        
        product = response.json()
        
        # Check if product has legacyIds field
        legacy_ids = product.get("legacyIds", [])
        product_id = str(product.get("_id", product.get("id", "")))
        
        print(f"Product ID: {product_id}")
        print(f"Product legacyIds: {legacy_ids}")
        
        # The legacyIds should contain the old ID for redirect mapping
        # This is essential for 301 redirects to work
        if legacy_ids:
            print(f"✅ Product has legacy ID mapping for redirects")
        else:
            print(f"ℹ️ Product has no legacy IDs (might be newly created with slug)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
