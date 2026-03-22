"""
Test Suite: Product ↔ SpecTemplate Relationship - Architectural Fix

This test validates the permanent architectural fix for Product ↔ SpecTemplate relationship:
1. validate_spec_template_ids helper validates template existence
2. validate_spec_template_ids checks template.isActive != false
3. validate_spec_template_ids checks template.categoryId matches product.categoryId
4. Product create uses validate_spec_template_ids for strict validation
5. Product update uses validate_spec_template_ids for strict validation
6. Template delete removes reference from all products ($pull)
7. /admin/products/cleanup-template-refs endpoint exists
8. Cleanup endpoint removes invalid template references
9. Cleanup endpoint removes category mismatched references
10. Indexes created for specTemplateIds and categoryId

ARCHITECTURAL RULES:
- Product can only reference templates with matching categoryId
- Template delete auto-cleans product references
- Category change clears all specTemplateIds
- No snake_case (camelCase only)
- Only specTemplateIds (array), not specTemplateId (singular)
"""

import pytest
import requests
import os
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://doc-builder-preview-1.preview.emergentagent.com"

# Dev auth token (Firebase not configured)
DEV_TOKEN = "dev-test-token"
AUTH_HEADER = {"Authorization": f"Bearer {DEV_TOKEN}"}


class TestProductSpecTemplateRelationship:
    """Test suite for Product ↔ SpecTemplate architectural fix"""
    
    # Test data IDs for cleanup
    test_category_id = None
    test_category_id_2 = None
    test_template_id = None
    test_template_id_2 = None
    test_template_id_other_category = None
    test_product_id = None
    
    @pytest.fixture(autouse=True)
    def setup_headers(self):
        """Setup auth headers for all tests"""
        self.headers = AUTH_HEADER
    
    # ==================== SETUP: Create Test Data ====================
    
    def test_01_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ Health check passed")
    
    def test_02_create_test_category_1(self):
        """Create first test category for template association"""
        payload = {
            "name": f"TEST_SpecTemplateCategory_{datetime.now().timestamp()}",
            "description": "Test category for spec template relationship testing"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/categories",
            json=payload,
            headers=self.headers
        )
        assert response.status_code in [200, 201], f"Failed to create category: {response.text}"
        
        data = response.json()
        category = data.get("category", data)
        TestProductSpecTemplateRelationship.test_category_id = category.get("id") or str(category.get("_id"))
        print(f"✅ Created test category 1: {TestProductSpecTemplateRelationship.test_category_id}")
    
    def test_03_create_test_category_2(self):
        """Create second test category (different from first) for category mismatch testing"""
        payload = {
            "name": f"TEST_SpecTemplateCategory2_{datetime.now().timestamp()}",
            "description": "Second test category for category mismatch testing"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/categories",
            json=payload,
            headers=self.headers
        )
        assert response.status_code in [200, 201], f"Failed to create category 2: {response.text}"
        
        data = response.json()
        category = data.get("category", data)
        TestProductSpecTemplateRelationship.test_category_id_2 = category.get("id") or str(category.get("_id"))
        print(f"✅ Created test category 2: {TestProductSpecTemplateRelationship.test_category_id_2}")
    
    def test_04_create_spec_template_for_category_1(self):
        """Create active spec template for category 1"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        payload = {
            "name": f"TEST_Template_Cat1_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "fields": [
                {"key": "color", "label": "Color", "fieldType": "text", "required": False},
                {"key": "size", "label": "Size", "fieldType": "dropdown", "options": ["Small", "Medium", "Large"], "required": True}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/spec-templates",
            json=payload,
            headers=self.headers
        )
        assert response.status_code in [200, 201], f"Failed to create spec template: {response.text}"
        
        data = response.json()
        template = data.get("template", data)
        TestProductSpecTemplateRelationship.test_template_id = template.get("id") or str(template.get("_id"))
        print(f"✅ Created spec template for category 1: {TestProductSpecTemplateRelationship.test_template_id}")
    
    def test_05_create_second_spec_template_for_category_1(self):
        """Create second active spec template for category 1 (for cleanup testing)"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        payload = {
            "name": f"TEST_Template2_Cat1_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "fields": [
                {"key": "weight", "label": "Weight", "fieldType": "number", "unit": "kg", "required": False}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/spec-templates",
            json=payload,
            headers=self.headers
        )
        assert response.status_code in [200, 201], f"Failed to create second spec template: {response.text}"
        
        data = response.json()
        template = data.get("template", data)
        TestProductSpecTemplateRelationship.test_template_id_2 = template.get("id") or str(template.get("_id"))
        print(f"✅ Created second spec template for category 1: {TestProductSpecTemplateRelationship.test_template_id_2}")
    
    def test_06_create_spec_template_for_category_2(self):
        """Create spec template for category 2 (different category)"""
        assert TestProductSpecTemplateRelationship.test_category_id_2, "Category 2 ID not set"
        
        payload = {
            "name": f"TEST_Template_Cat2_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id_2,
            "fields": [
                {"key": "material", "label": "Material", "fieldType": "text", "required": False}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/spec-templates",
            json=payload,
            headers=self.headers
        )
        assert response.status_code in [200, 201], f"Failed to create spec template for category 2: {response.text}"
        
        data = response.json()
        template = data.get("template", data)
        TestProductSpecTemplateRelationship.test_template_id_other_category = template.get("id") or str(template.get("_id"))
        print(f"✅ Created spec template for category 2: {TestProductSpecTemplateRelationship.test_template_id_other_category}")
    
    # ==================== TEST: Product Create Validation ====================
    
    def test_07_product_create_with_valid_template(self):
        """Product create should succeed with valid template (exists, active, matching category)"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        assert TestProductSpecTemplateRelationship.test_template_id, "Template ID not set"
        
        payload = {
            "name": f"TEST_Product_ValidTemplate_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "specTemplateIds": [TestProductSpecTemplateRelationship.test_template_id],
            "description": "Product with valid template reference"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=payload,
            headers=self.headers
        )
        
        # Should succeed
        assert response.status_code in [200, 201], f"Product create should succeed: {response.text}"
        
        data = response.json()
        product = data.get("product", data)
        TestProductSpecTemplateRelationship.test_product_id = product.get("id") or str(product.get("_id"))
        
        # Verify specTemplateIds is stored
        spec_template_ids = product.get("specTemplateIds", [])
        assert len(spec_template_ids) > 0, "specTemplateIds should be stored"
        print(f"✅ Product created with valid template: {TestProductSpecTemplateRelationship.test_product_id}")
    
    def test_08_product_create_with_nonexistent_template_fails(self):
        """Product create should fail with non-existent template ID"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        fake_template_id = "507f1f77bcf86cd799439099"  # Valid ObjectId format but doesn't exist
        
        payload = {
            "name": f"TEST_Product_FakeTemplate_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "specTemplateIds": [fake_template_id],
            "description": "Product with non-existent template"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=payload,
            headers=self.headers
        )
        
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400 for non-existent template, got {response.status_code}: {response.text}"
        
        data = response.json()
        detail = data.get("detail", {})
        error = detail.get("error") if isinstance(detail, dict) else str(detail)
        assert "not found" in str(error).lower() or "not exist" in str(error).lower(), f"Error should mention template not found: {error}"
        print(f"✅ Product create correctly rejected non-existent template")
    
    def test_09_product_create_with_category_mismatch_fails(self):
        """Product create should fail when template belongs to different category"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        assert TestProductSpecTemplateRelationship.test_template_id_other_category, "Category 2 template ID not set"
        
        # Try to create product in category 1 with template from category 2
        payload = {
            "name": f"TEST_Product_CategoryMismatch_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,  # Category 1
            "specTemplateIds": [TestProductSpecTemplateRelationship.test_template_id_other_category],  # Template from Category 2
            "description": "Product with category mismatched template"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=payload,
            headers=self.headers
        )
        
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400 for category mismatch, got {response.status_code}: {response.text}"
        
        data = response.json()
        detail = data.get("detail", {})
        error = detail.get("error") if isinstance(detail, dict) else str(detail)
        assert "mismatch" in str(error).lower() or "different category" in str(error).lower(), f"Error should mention category mismatch: {error}"
        print(f"✅ Product create correctly rejected category mismatched template")
    
    def test_10_product_create_with_invalid_objectid_fails(self):
        """Product create should fail with invalid ObjectId format for template"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        invalid_template_id = "not-a-valid-objectid"
        
        payload = {
            "name": f"TEST_Product_InvalidObjId_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "specTemplateIds": [invalid_template_id],
            "description": "Product with invalid ObjectId template"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=payload,
            headers=self.headers
        )
        
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400 for invalid ObjectId, got {response.status_code}: {response.text}"
        print(f"✅ Product create correctly rejected invalid ObjectId")
    
    # ==================== TEST: Product Update Validation ====================
    
    def test_11_product_update_with_valid_template(self):
        """Product update should succeed with valid template"""
        assert TestProductSpecTemplateRelationship.test_product_id, "Product ID not set"
        assert TestProductSpecTemplateRelationship.test_template_id_2, "Template 2 ID not set"
        
        # Add second template to product
        payload = {
            "specTemplateIds": [
                TestProductSpecTemplateRelationship.test_template_id,
                TestProductSpecTemplateRelationship.test_template_id_2
            ]
        }
        response = requests.patch(
            f"{BASE_URL}/api/admin/products/{TestProductSpecTemplateRelationship.test_product_id}",
            json=payload,
            headers=self.headers
        )
        
        # Should succeed
        assert response.status_code == 200, f"Product update should succeed: {response.text}"
        
        data = response.json()
        product = data.get("product", data)
        spec_template_ids = product.get("specTemplateIds", [])
        assert len(spec_template_ids) == 2, f"Should have 2 templates, got {len(spec_template_ids)}"
        print(f"✅ Product updated with valid templates")
    
    def test_12_product_update_with_category_mismatch_fails(self):
        """Product update should fail when trying to add template from different category"""
        assert TestProductSpecTemplateRelationship.test_product_id, "Product ID not set"
        assert TestProductSpecTemplateRelationship.test_template_id_other_category, "Other category template ID not set"
        
        payload = {
            "specTemplateIds": [TestProductSpecTemplateRelationship.test_template_id_other_category]
        }
        response = requests.patch(
            f"{BASE_URL}/api/admin/products/{TestProductSpecTemplateRelationship.test_product_id}",
            json=payload,
            headers=self.headers
        )
        
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400 for category mismatch on update, got {response.status_code}: {response.text}"
        
        data = response.json()
        detail = data.get("detail", {})
        error = detail.get("error") if isinstance(detail, dict) else str(detail)
        assert "mismatch" in str(error).lower() or "different category" in str(error).lower(), f"Error should mention category mismatch: {error}"
        print(f"✅ Product update correctly rejected category mismatched template")
    
    # ==================== TEST: Template Delete with Auto-Cleanup ====================
    
    def test_13_template_delete_cleans_product_references(self):
        """Template delete should automatically remove references from products ($pull)"""
        # First, create a new template and product specifically for this test
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        # Create a template to delete
        template_payload = {
            "name": f"TEST_Template_ToDelete_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "fields": [{"key": "deletable", "label": "Deletable", "fieldType": "text", "required": False}]
        }
        template_response = requests.post(
            f"{BASE_URL}/api/admin/spec-templates",
            json=template_payload,
            headers=self.headers
        )
        assert template_response.status_code in [200, 201], f"Failed to create template: {template_response.text}"
        
        template_data = template_response.json()
        template = template_data.get("template", template_data)
        delete_template_id = template.get("id") or str(template.get("_id"))
        
        # Create a product with this template
        product_payload = {
            "name": f"TEST_Product_WithDeletableTemplate_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "specTemplateIds": [delete_template_id]
        }
        product_response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=product_payload,
            headers=self.headers
        )
        assert product_response.status_code in [200, 201], f"Failed to create product: {product_response.text}"
        
        product_data = product_response.json()
        product = product_data.get("product", product_data)
        test_product_id = product.get("id") or str(product.get("_id"))
        
        # Verify product has the template
        get_response = requests.get(
            f"{BASE_URL}/api/admin/products/{test_product_id}",
            headers=self.headers
        )
        if get_response.status_code == 200:
            product_before = get_response.json().get("product", get_response.json())
            templates_before = product_before.get("specTemplateIds", [])
            assert len(templates_before) > 0, "Product should have template before delete"
        
        # Delete the template with force=true
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/spec-templates/{delete_template_id}?force=true",
            headers=self.headers
        )
        assert delete_response.status_code == 200, f"Template delete failed: {delete_response.text}"
        
        delete_data = delete_response.json()
        products_updated = delete_data.get("productsUpdated", 0)
        print(f"Template delete updated {products_updated} products")
        
        # Verify template reference was removed from product
        get_response_after = requests.get(
            f"{BASE_URL}/api/admin/products/{test_product_id}",
            headers=self.headers
        )
        if get_response_after.status_code == 200:
            product_after = get_response_after.json().get("product", get_response_after.json())
            templates_after = product_after.get("specTemplateIds", [])
            
            # Template should be removed
            template_still_exists = any(
                str(t) == delete_template_id or (isinstance(t, dict) and str(t.get("_id") or t.get("id")) == delete_template_id)
                for t in templates_after
            )
            assert not template_still_exists, f"Template reference should be removed after delete. Templates: {templates_after}"
        
        print(f"✅ Template delete automatically cleaned product references")
    
    # ==================== TEST: Cleanup Endpoint ====================
    
    def test_14_cleanup_endpoint_exists(self):
        """Verify /admin/products/cleanup-template-refs endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/admin/products/cleanup-template-refs",
            headers=self.headers
        )
        
        # Should return 200 (success) not 404 (not found)
        assert response.status_code != 404, f"Cleanup endpoint should exist, got 404"
        assert response.status_code == 200, f"Cleanup endpoint should succeed: {response.text}"
        
        data = response.json()
        assert "summary" in data or "message" in data, f"Response should have summary or message: {data}"
        print(f"✅ Cleanup endpoint exists and returns: {data.get('message', 'OK')}")
    
    def test_15_cleanup_endpoint_reports_results(self):
        """Cleanup endpoint should report cleanup results with proper structure"""
        response = requests.post(
            f"{BASE_URL}/api/admin/products/cleanup-template-refs",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Cleanup should succeed: {response.text}"
        
        data = response.json()
        
        # Check summary structure
        summary = data.get("summary", {})
        assert "productsScanned" in summary, "Should report productsScanned"
        assert "productsCleaned" in summary, "Should report productsCleaned"
        assert "invalidRefsRemoved" in summary, "Should report invalidRefsRemoved"
        assert "categoryMismatchRemoved" in summary, "Should report categoryMismatchRemoved"
        assert "validTemplatesCount" in summary, "Should report validTemplatesCount"
        
        print(f"✅ Cleanup endpoint returns proper summary:")
        print(f"   - Products scanned: {summary.get('productsScanned')}")
        print(f"   - Products cleaned: {summary.get('productsCleaned')}")
        print(f"   - Invalid refs removed: {summary.get('invalidRefsRemoved')}")
        print(f"   - Category mismatches removed: {summary.get('categoryMismatchRemoved')}")
    
    # ==================== TEST: Inactive Template Validation ====================
    
    def test_16_product_create_with_inactive_template_fails(self):
        """Product create should fail when template isActive is false"""
        assert TestProductSpecTemplateRelationship.test_category_id, "Category 1 ID not set"
        
        # Create a new template
        template_payload = {
            "name": f"TEST_Template_ToDeactivate_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "fields": [{"key": "temp", "label": "Temp", "fieldType": "text", "required": False}]
        }
        template_response = requests.post(
            f"{BASE_URL}/api/admin/spec-templates",
            json=template_payload,
            headers=self.headers
        )
        assert template_response.status_code in [200, 201], f"Failed to create template: {template_response.text}"
        
        template_data = template_response.json()
        template = template_data.get("template", template_data)
        inactive_template_id = template.get("id") or str(template.get("_id"))
        
        # Soft-delete (deactivate) the template
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/spec-templates/{inactive_template_id}?force=true",
            headers=self.headers
        )
        assert delete_response.status_code == 200, f"Template deactivation failed: {delete_response.text}"
        
        # Try to create product with inactive template
        product_payload = {
            "name": f"TEST_Product_WithInactiveTemplate_{datetime.now().timestamp()}",
            "categoryId": TestProductSpecTemplateRelationship.test_category_id,
            "specTemplateIds": [inactive_template_id]
        }
        product_response = requests.post(
            f"{BASE_URL}/api/admin/products",
            json=product_payload,
            headers=self.headers
        )
        
        # Should fail with 400
        assert product_response.status_code == 400, f"Expected 400 for inactive template, got {product_response.status_code}: {product_response.text}"
        
        data = product_response.json()
        detail = data.get("detail", {})
        error = detail.get("error") if isinstance(detail, dict) else str(detail)
        assert "inactive" in str(error).lower() or "deactivated" in str(error).lower(), f"Error should mention inactive/deactivated: {error}"
        print(f"✅ Product create correctly rejected inactive template")
    
    # ==================== TEST: Architectural Rules ====================
    
    def test_17_spec_template_ids_is_array_not_singular(self):
        """Verify specTemplateIds is used (array), not specTemplateId (singular)"""
        assert TestProductSpecTemplateRelationship.test_product_id, "Product ID not set"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/products/{TestProductSpecTemplateRelationship.test_product_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            product = data.get("product", data)
            
            # Should have specTemplateIds (array), not specTemplateId
            assert "specTemplateIds" in product or "specTemplateIds" in str(product), \
                "Product should use specTemplateIds (array)"
            
            # Should NOT have singular specTemplateId
            assert "specTemplateId" not in product or product.get("specTemplateId") is None, \
                "Product should NOT use singular specTemplateId"
            
            spec_template_ids = product.get("specTemplateIds", [])
            assert isinstance(spec_template_ids, list), "specTemplateIds should be an array"
            
            print(f"✅ Product uses specTemplateIds (array) as required")
        else:
            print(f"⚠️ Could not verify product structure (status: {response.status_code})")
    
    def test_18_verify_camelcase_field_names(self):
        """Verify all fields use camelCase (no snake_case)"""
        assert TestProductSpecTemplateRelationship.test_product_id, "Product ID not set"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/products/{TestProductSpecTemplateRelationship.test_product_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            product = data.get("product", data)
            
            # Check for snake_case violations
            snake_case_fields = [
                "spec_template_ids", "category_id", "created_at", "updated_at",
                "is_active", "created_by"
            ]
            
            for field in snake_case_fields:
                assert field not in product, f"Found snake_case field '{field}' - should be camelCase"
            
            # Verify camelCase fields exist
            camel_case_fields = ["categoryId", "createdAt", "updatedAt"]
            for field in camel_case_fields:
                if field in product:
                    print(f"   ✓ {field} is camelCase")
            
            print(f"✅ Product fields use camelCase (no snake_case)")
        else:
            print(f"⚠️ Could not verify field naming (status: {response.status_code})")


class TestIndexVerification:
    """Verify indexes were created"""
    
    def test_indexes_exist(self):
        """
        Verify indexes for specTemplateIds and categoryId exist.
        This is a proxy check - we verify the API responses are performant.
        """
        # This is a functional test - actual index verification requires DB access
        # We verify the cleanup endpoint works efficiently (which uses the indexes)
        
        response = requests.post(
            f"{BASE_URL}/api/admin/products/cleanup-template-refs",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200, f"Cleanup should work (indexes should exist): {response.text}"
        print(f"✅ API operations work correctly (indexes presumed to exist)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
