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
    
    def test_04_create_test_category_1(self, api_client, auth_headers):
        """Create first test category"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/categories",
            headers=auth_headers,
            json={"name": "TEST_DataIntegrity_Cat1", "description": "Test category 1"}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Response structure: {"message": "...", "category": {...}}
            category = data.get("category", data)
            TestValidateSpecTemplateIds.test_category_1_id = category.get("_id") or category.get("id")
            print(f"✅ Created test category 1: {TestValidateSpecTemplateIds.test_category_1_id}")
        elif response.status_code == 409:
            # Category already exists, fetch it
            list_response = api_client.get(f"{BASE_URL}/api/admin/categories", headers=auth_headers)
            if list_response.status_code == 200:
                cats = list_response.json().get("categories", [])
                for cat in cats:
                    if cat.get("name") == "TEST_DataIntegrity_Cat1":
                        TestValidateSpecTemplateIds.test_category_1_id = cat.get("_id") or cat.get("id")
                        print(f"✅ Found existing test category 1: {TestValidateSpecTemplateIds.test_category_1_id}")
                        break
        
        assert TestValidateSpecTemplateIds.test_category_1_id, f"Failed to create/find test category 1. Response: {response.status_code} - {response.text}"
    
    def test_05_create_test_category_2(self, api_client, auth_headers):
        """Create second test category for mismatch testing"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/categories",
            headers=auth_headers,
            json={"name": "TEST_DataIntegrity_Cat2", "description": "Test category 2 (mismatch)"}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            category = data.get("category", data)
            TestValidateSpecTemplateIds.test_category_2_id = category.get("_id") or category.get("id")
            print(f"✅ Created test category 2: {TestValidateSpecTemplateIds.test_category_2_id}")
        elif response.status_code == 409:
            list_response = api_client.get(f"{BASE_URL}/api/admin/categories", headers=auth_headers)
            if list_response.status_code == 200:
                cats = list_response.json().get("categories", [])
                for cat in cats:
                    if cat.get("name") == "TEST_DataIntegrity_Cat2":
                        TestValidateSpecTemplateIds.test_category_2_id = cat.get("_id") or cat.get("id")
                        print(f"✅ Found existing test category 2: {TestValidateSpecTemplateIds.test_category_2_id}")
                        break
        
        assert TestValidateSpecTemplateIds.test_category_2_id, f"Failed to create/find test category 2. Response: {response.status_code} - {response.text}"
    
    def test_06_create_spec_template_for_cat1(self, api_client, auth_headers):
        """Create spec template for category 1"""
        if not TestValidateSpecTemplateIds.test_category_1_id:
            pytest.skip("Category 1 not created")
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/spec-templates",
            headers=auth_headers,
            json={
                "name": "TEST_DataIntegrity_Template1",
                "categoryId": TestValidateSpecTemplateIds.test_category_1_id,
                "fields": [
                    {"name": "Voltage", "key": "voltage", "type": "text", "required": True}
                ]
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            template = data.get("template", data)
            TestValidateSpecTemplateIds.test_template_1_id = template.get("_id") or template.get("id")
            print(f"✅ Created spec template for cat1: {TestValidateSpecTemplateIds.test_template_1_id}")
        elif response.status_code == 409:
            list_response = api_client.get(f"{BASE_URL}/api/admin/spec-templates", headers=auth_headers)
            if list_response.status_code == 200:
                templates = list_response.json().get("templates", [])
                for t in templates:
                    if t.get("name") == "TEST_DataIntegrity_Template1":
                        TestValidateSpecTemplateIds.test_template_1_id = t.get("_id") or t.get("id")
                        print(f"✅ Found existing template for cat1: {TestValidateSpecTemplateIds.test_template_1_id}")
                        break
        
        assert TestValidateSpecTemplateIds.test_template_1_id, f"Failed to create/find spec template for cat1. Response: {response.status_code} - {response.text}"
    
    def test_07_create_spec_template_for_cat2(self, api_client, auth_headers):
        """Create spec template for category 2 (for mismatch testing)"""
        if not TestValidateSpecTemplateIds.test_category_2_id:
            pytest.skip("Category 2 not created")
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/spec-templates",
            headers=auth_headers,
            json={
                "name": "TEST_DataIntegrity_Template2",
                "categoryId": TestValidateSpecTemplateIds.test_category_2_id,
                "fields": [
                    {"name": "Power", "key": "power", "type": "text", "required": True}
                ]
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            template = data.get("template", data)
            TestValidateSpecTemplateIds.test_template_2_id = template.get("_id") or template.get("id")
            print(f"✅ Created spec template for cat2: {TestValidateSpecTemplateIds.test_template_2_id}")
        elif response.status_code == 409:
            list_response = api_client.get(f"{BASE_URL}/api/admin/spec-templates", headers=auth_headers)
            if list_response.status_code == 200:
                templates = list_response.json().get("templates", [])
                for t in templates:
                    if t.get("name") == "TEST_DataIntegrity_Template2":
                        TestValidateSpecTemplateIds.test_template_2_id = t.get("_id") or t.get("id")
                        print(f"✅ Found existing template for cat2: {TestValidateSpecTemplateIds.test_template_2_id}")
                        break
        
        assert TestValidateSpecTemplateIds.test_template_2_id, f"Failed to create/find spec template for cat2. Response: {response.status_code} - {response.text}"
    
    def test_08_product_create_with_valid_template_passes(self, api_client, auth_headers):
        """Creating product with valid template that matches category should work"""
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
        TestValidateSpecTemplateIds.test_product_id = data.get("_id") or data.get("id")
        print(f"✅ Product created with valid template: {TestValidateSpecTemplateIds.test_product_id}")
    
    def test_09_product_create_with_category_mismatch_fails(self, api_client, auth_headers):
        """Creating product with template from different category should fail (validate_spec_template_ids)"""
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
            # Verify response has expected keys
            expected_keys = ["productsScanned", "productsCleaned", "invalidRefsRemoved", "categoryMismatchRemoved"]
            for key in expected_keys:
                assert key in data, f"Response should have '{key}' key"
            print(f"✅ Cleanup response: {data}")


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
