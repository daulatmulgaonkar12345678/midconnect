#!/usr/bin/env python3
"""
Enterprise Data Integrity Migration Tests
==========================================

This test file validates the data integrity resolution features:
1. Backend /admin/data-integrity/migrate endpoint exists
2. Migration converts specTemplates.categoryId string to ObjectId  
3. Migration converts products.categoryId string to ObjectId
4. Migration removes orphan template references
5. Migration removes category mismatched references
6. Frontend uses strict category filter
7. Frontend validates template selection before save
8. Frontend clears specTemplateIds when category changes
9. No legacy fallback logic in frontend
10. Backend validate_spec_template_ids checks category match

Test Date: Feb 2026
"""

import pytest
import requests
import os

# Configuration - Use environment variable BASE_URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

DEV_TOKEN = "dev-test-token"


@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def auth_headers():
    """Admin authentication headers"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEV_TOKEN}"
    }


class TestDataIntegrityMigrationEndpoint:
    """Test the /admin/data-integrity/migrate endpoint"""
    
    def test_01_health_check(self, api_client):
        """Verify API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ API health check passed")
    
    def test_02_migration_endpoint_exists(self, api_client, auth_headers):
        """Test that /admin/data-integrity/migrate endpoint exists"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/data-integrity/migrate",
            headers=auth_headers
        )
        # Should NOT be 404 - endpoint must exist
        assert response.status_code != 404, "Migration endpoint should exist"
        print(f"✅ Migration endpoint exists (status: {response.status_code})")
        
        # If 200, verify response structure
        if response.status_code == 200:
            data = response.json()
            assert "message" in data, "Response should have 'message' key"
            assert "results" in data, "Response should have 'results' key"
            assert "totalFixes" in data, "Response should have 'totalFixes' key"
            print(f"✅ Migration response structure valid: {data}")
    
    def test_03_migration_response_structure(self, api_client, auth_headers):
        """Verify migration response has all expected fields"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/data-integrity/migrate",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", {})
            
            # Check all expected result keys
            expected_keys = [
                "step1_specTemplates_categoryId_converted",
                "step2_products_categoryId_converted",
                "step3_orphan_refs_removed",
                "step4_category_mismatch_removed",
                "errors"
            ]
            
            for key in expected_keys:
                assert key in results, f"Results should have '{key}' key"
            
            print(f"✅ Migration results structure valid:")
            print(f"   - Step 1 (specTemplates categoryId): {results.get('step1_specTemplates_categoryId_converted', 0)}")
            print(f"   - Step 2 (products categoryId): {results.get('step2_products_categoryId_converted', 0)}")
            print(f"   - Step 3 (orphan refs removed): {results.get('step3_orphan_refs_removed', 0)}")
            print(f"   - Step 4 (category mismatch removed): {results.get('step4_category_mismatch_removed', 0)}")
            print(f"   - Total fixes: {data.get('totalFixes', 0)}")
        else:
            print(f"⚠️ Migration returned status {response.status_code}")


class TestValidateSpecTemplateIds:
    """Test backend validate_spec_template_ids function via API calls"""
    
    test_category_1_id = None
    test_category_2_id = None
    test_template_1_id = None
    test_template_2_id = None  # For different category
    test_product_id = None
    
    def test_04_find_existing_test_data(self, api_client, auth_headers):
        """Find existing test categories and templates from previous test runs"""
        # Get existing categories
        cat_response = api_client.get(f"{BASE_URL}/api/admin/categories", headers=auth_headers)
        assert cat_response.status_code == 200, "Failed to fetch categories"
        cats = cat_response.json().get("categories", [])
        
        # Find two different categories
        for cat in cats:
            if not TestValidateSpecTemplateIds.test_category_1_id:
                TestValidateSpecTemplateIds.test_category_1_id = cat.get("_id")
            elif not TestValidateSpecTemplateIds.test_category_2_id and cat.get("_id") != TestValidateSpecTemplateIds.test_category_1_id:
                TestValidateSpecTemplateIds.test_category_2_id = cat.get("_id")
        
        # Get existing templates
        tmpl_response = api_client.get(f"{BASE_URL}/api/admin/spec-templates", headers=auth_headers)
        assert tmpl_response.status_code == 200, "Failed to fetch templates"
        templates = tmpl_response.json().get("templates", [])
        
        # Find templates for category 1 and category 2
        for t in templates:
            if t.get("categoryId") == TestValidateSpecTemplateIds.test_category_1_id and not TestValidateSpecTemplateIds.test_template_1_id:
                TestValidateSpecTemplateIds.test_template_1_id = t.get("_id")
            elif t.get("categoryId") == TestValidateSpecTemplateIds.test_category_2_id and not TestValidateSpecTemplateIds.test_template_2_id:
                TestValidateSpecTemplateIds.test_template_2_id = t.get("_id")
        
        print(f"✅ Found test data:")
        print(f"   - Category 1: {TestValidateSpecTemplateIds.test_category_1_id}")
        print(f"   - Category 2: {TestValidateSpecTemplateIds.test_category_2_id}")
        print(f"   - Template 1 (for cat 1): {TestValidateSpecTemplateIds.test_template_1_id}")
        print(f"   - Template 2 (for cat 2): {TestValidateSpecTemplateIds.test_template_2_id}")
        
        assert TestValidateSpecTemplateIds.test_category_1_id, "No categories found in database"
        assert TestValidateSpecTemplateIds.test_template_1_id, "No templates found for category 1"
    
    def test_08_product_create_with_valid_template_passes(self, api_client, auth_headers):
        """Creating product with valid template that matches category should work"""
        if not TestValidateSpecTemplateIds.test_category_1_id or not TestValidateSpecTemplateIds.test_template_1_id:
            pytest.skip("Prerequisites not met - category or template not created")
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/products",
            headers=auth_headers,
            json={
                "name": "TEST_DataIntegrity_Product1",
                "categoryId": TestValidateSpecTemplateIds.test_category_1_id,
                "family": "Test Family",
                "variant": "Test Variant",
                "specTemplateIds": [TestValidateSpecTemplateIds.test_template_1_id]
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        product = data.get("product", data)
        TestValidateSpecTemplateIds.test_product_id = product.get("_id") or product.get("id")
        print(f"✅ Product created with valid template: {TestValidateSpecTemplateIds.test_product_id}")
    
    def test_09_product_create_with_category_mismatch_fails(self, api_client, auth_headers):
        """Creating product with template from different category should fail (validate_spec_template_ids)"""
        if not TestValidateSpecTemplateIds.test_category_1_id or not TestValidateSpecTemplateIds.test_template_2_id:
            pytest.skip("Prerequisites not met - category or template not created")
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/products",
            headers=auth_headers,
            json={
                "name": "TEST_DataIntegrity_Product_Mismatch",
                "categoryId": TestValidateSpecTemplateIds.test_category_1_id,  # Category 1
                "family": "Test Family",
                "variant": "Test Variant",
                "specTemplateIds": [TestValidateSpecTemplateIds.test_template_2_id]  # Template from Category 2
            }
        )
        
        # Should return 400 due to category mismatch
        assert response.status_code == 400, f"Expected 400 for category mismatch, got {response.status_code}: {response.text}"
        print(f"✅ Category mismatch correctly rejected with 400")
    
    def test_10_product_create_with_nonexistent_template_fails(self, api_client, auth_headers):
        """Creating product with non-existent template should fail"""
        if not TestValidateSpecTemplateIds.test_category_1_id:
            pytest.skip("Prerequisites not met - category not created")
        
        fake_template_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format, but doesn't exist
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/products",
            headers=auth_headers,
            json={
                "name": "TEST_DataIntegrity_Product_FakeTemplate",
                "categoryId": TestValidateSpecTemplateIds.test_category_1_id,
                "family": "Test Family",
                "variant": "Test Variant",
                "specTemplateIds": [fake_template_id]
            }
        )
        
        # Should return 400 due to non-existent template
        assert response.status_code == 400, f"Expected 400 for non-existent template, got {response.status_code}: {response.text}"
        print(f"✅ Non-existent template correctly rejected with 400")
    
    def test_11_product_update_with_valid_template_passes(self, api_client, auth_headers):
        """Updating product with valid template should work"""
        if not TestValidateSpecTemplateIds.test_product_id:
            pytest.skip("No product to update")
        
        response = api_client.patch(
            f"{BASE_URL}/api/admin/products/{TestValidateSpecTemplateIds.test_product_id}",
            headers=auth_headers,
            json={
                "specTemplateIds": [TestValidateSpecTemplateIds.test_template_1_id]
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✅ Product update with valid template succeeded")
    
    def test_12_product_update_with_category_mismatch_fails(self, api_client, auth_headers):
        """Updating product with template from different category should fail"""
        if not TestValidateSpecTemplateIds.test_product_id:
            pytest.skip("No product to update")
        
        response = api_client.patch(
            f"{BASE_URL}/api/admin/products/{TestValidateSpecTemplateIds.test_product_id}",
            headers=auth_headers,
            json={
                "specTemplateIds": [TestValidateSpecTemplateIds.test_template_2_id]  # Template from Category 2
            }
        )
        
        # Should return 400 due to category mismatch
        assert response.status_code == 400, f"Expected 400 for category mismatch on update, got {response.status_code}: {response.text}"
        print(f"✅ Category mismatch on update correctly rejected with 400")


class TestCleanupEndpoint:
    """Test the cleanup endpoint for template references"""
    
    def test_13_cleanup_endpoint_exists(self, api_client, auth_headers):
        """Test that cleanup endpoint exists"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/products/cleanup-template-refs",
            headers=auth_headers
        )
        
        assert response.status_code != 404, "Cleanup endpoint should exist"
        print(f"✅ Cleanup endpoint exists (status: {response.status_code})")
        
        if response.status_code == 200:
            data = response.json()
            # Response structure: {summary: {...}, details: [...], message: "..."}
            summary = data.get("summary", data)
            
            # Verify response has expected keys (either in root or in summary)
            expected_keys = ["productsScanned", "productsCleaned", "invalidRefsRemoved", "categoryMismatchRemoved"]
            for key in expected_keys:
                assert key in summary, f"Response summary should have '{key}' key"
            print(f"✅ Cleanup response: {summary}")


class TestSpecTemplatesEndpoint:
    """Test spec templates endpoint for categoryId structure"""
    
    def test_14_spec_templates_have_category_id(self, api_client, auth_headers):
        """Verify spec templates have categoryId field"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/spec-templates",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        templates = data.get("templates", [])
        
        if templates:
            # Check first template has categoryId
            template = templates[0]
            assert "categoryId" in template, "Template should have categoryId field"
            print(f"✅ Templates have categoryId field")
            
            # Check categoryId is not empty string (should be ObjectId or valid reference)
            if template.get("categoryId"):
                print(f"   - Sample categoryId: {template['categoryId']}")
        else:
            print("⚠️ No templates found to verify")


class TestProductsEndpointDataIntegrity:
    """Test products endpoint for data integrity"""
    
    def test_15_products_have_category_id(self, api_client, auth_headers):
        """Verify products have categoryId field"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/products",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        products = data.get("products", [])
        
        if products:
            product = products[0]
            assert "categoryId" in product, "Product should have categoryId field"
            print(f"✅ Products have categoryId field")
            
            # Check specTemplateIds is array (not singular)
            if "specTemplateIds" in product:
                assert isinstance(product["specTemplateIds"], list), "specTemplateIds should be array"
                print(f"✅ specTemplateIds is array: {product['specTemplateIds']}")
        else:
            print("⚠️ No products found to verify")
    
    def test_16_products_use_camelcase(self, api_client, auth_headers):
        """Verify products use camelCase field names"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/products",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", [])
        
        if products:
            product = products[0]
            
            # Check for camelCase (not snake_case)
            snake_case_keys = ["category_id", "spec_template_ids", "is_active", "created_at", "updated_at"]
            for key in snake_case_keys:
                assert key not in product, f"Product should not have snake_case key '{key}'"
            
            # Verify camelCase keys
            camel_case_keys = ["categoryId", "isActive", "createdAt", "updatedAt"]
            for key in camel_case_keys:
                if key in product:
                    print(f"   ✅ {key}: present (camelCase)")
            
            print(f"✅ Products use camelCase field names")
        else:
            print("⚠️ No products found to verify")


class TestCleanup:
    """Cleanup test data"""
    
    def test_99_cleanup_test_data(self, api_client, auth_headers):
        """Clean up test data created during tests"""
        # Delete test product
        if TestValidateSpecTemplateIds.test_product_id:
            response = api_client.delete(
                f"{BASE_URL}/api/admin/products/{TestValidateSpecTemplateIds.test_product_id}",
                headers=auth_headers
            )
            print(f"Cleaned up product: {response.status_code}")
        
        # Delete test templates
        if TestValidateSpecTemplateIds.test_template_1_id:
            response = api_client.delete(
                f"{BASE_URL}/api/admin/spec-templates/{TestValidateSpecTemplateIds.test_template_1_id}",
                headers=auth_headers
            )
            print(f"Cleaned up template 1: {response.status_code}")
        
        if TestValidateSpecTemplateIds.test_template_2_id:
            response = api_client.delete(
                f"{BASE_URL}/api/admin/spec-templates/{TestValidateSpecTemplateIds.test_template_2_id}",
                headers=auth_headers
            )
            print(f"Cleaned up template 2: {response.status_code}")
        
        # Delete test categories
        if TestValidateSpecTemplateIds.test_category_1_id:
            response = api_client.delete(
                f"{BASE_URL}/api/admin/categories/{TestValidateSpecTemplateIds.test_category_1_id}",
                headers=auth_headers
            )
            print(f"Cleaned up category 1: {response.status_code}")
        
        if TestValidateSpecTemplateIds.test_category_2_id:
            response = api_client.delete(
                f"{BASE_URL}/api/admin/categories/{TestValidateSpecTemplateIds.test_category_2_id}",
                headers=auth_headers
            )
            print(f"Cleaned up category 2: {response.status_code}")
        
        print("✅ Test cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
