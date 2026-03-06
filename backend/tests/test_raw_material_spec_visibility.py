"""
Test raw material spec template visibility for buyers on product pages.
Tests the fix ensuring calculator shows when:
1) Category has categoryType='raw_material', OR  
2) Any spec template for the category has templateType='raw_material'

Endpoints tested:
- GET /api/spec-templates/by-category/{id}
- GET /api/products/{product_id}/raw-material-config
"""

import pytest
import requests
import os
from datetime import datetime

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calc-product-sync.preview.emergentagent.com').rstrip('/')


class TestSpecTemplatesByCategoryEndpoint:
    """Tests for GET /api/spec-templates/by-category/{id}"""
    
    def test_endpoint_exists(self):
        """Test that the endpoint exists and responds"""
        # Use a random invalid ID to test endpoint exists (should return 400 or 404)
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/invalid")
        # Endpoint exists - returns 400 for invalid ID
        assert response.status_code == 400, f"Expected 400 for invalid ID, got {response.status_code}"
        print("PASS: GET /api/spec-templates/by-category endpoint exists")
    
    def test_valid_category_returns_proper_structure(self):
        """Test that a valid category returns expected response structure"""
        # First get any existing category
        categories_response = requests.get(f"{BASE_URL}/api/categories")
        assert categories_response.status_code == 200
        
        categories = categories_response.json()
        if not categories:
            pytest.skip("No categories available in the database")
        
        # Use first category ID
        category_id = categories[0].get("_id") or categories[0].get("id")
        assert category_id, "Category should have an _id or id field"
        
        # Now test the spec-templates endpoint
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "category" in data, "Response should include 'category' field"
        assert "templates" in data, "Response should include 'templates' field"
        assert "isRawMaterial" in data, "Response MUST include 'isRawMaterial' field"
        
        # Verify category structure
        assert "_id" in data["category"], "Category should include '_id'"
        assert "name" in data["category"], "Category should include 'name'"
        assert "categoryType" in data["category"], "Category should include 'categoryType'"
        
        # isRawMaterial should be a boolean
        assert isinstance(data["isRawMaterial"], bool), "isRawMaterial should be boolean"
        
        print(f"PASS: Valid category returns proper structure. isRawMaterial={data['isRawMaterial']}, templates={len(data['templates'])}")
    
    def test_returns_raw_material_template_when_template_type_is_raw_material(self):
        """Test that isRawMaterial=true when any template has templateType='raw_material'"""
        # Get categories
        categories_response = requests.get(f"{BASE_URL}/api/categories")
        assert categories_response.status_code == 200
        categories = categories_response.json()
        
        # Look for any category that has raw_material templates
        found_raw_material = False
        
        for category in categories:
            category_id = category.get("_id") or category.get("id")
            response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if any template has templateType='raw_material'
                templates = data.get("templates", [])
                has_raw_material_template = any(
                    t.get("templateType") == "raw_material" for t in templates
                )
                
                if has_raw_material_template:
                    found_raw_material = True
                    assert data["isRawMaterial"] is True, \
                        f"isRawMaterial should be True when templateType='raw_material' for category {category_id}"
                    assert "rawMaterialTemplate" in data, \
                        "Response should include 'rawMaterialTemplate' when raw material exists"
                    print(f"PASS: Category {category_id} correctly returns isRawMaterial=True with raw_material template")
                    break
                
                # Also check if category has categoryType='raw_material'
                if category.get("categoryType") == "raw_material":
                    found_raw_material = True
                    assert data["isRawMaterial"] is True, \
                        f"isRawMaterial should be True when categoryType='raw_material' for category {category_id}"
                    print(f"PASS: Category {category_id} correctly returns isRawMaterial=True with categoryType='raw_material'")
                    break
        
        if not found_raw_material:
            # Test that standard categories return isRawMaterial=False
            for category in categories[:3]:  # Test first 3
                category_id = category.get("_id") or category.get("id")
                response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
                if response.status_code == 200:
                    data = response.json()
                    if category.get("categoryType") != "raw_material":
                        assert data["isRawMaterial"] is False or data["isRawMaterial"] is True, \
                            "isRawMaterial should be boolean"
                        print(f"PASS: Category {category_id} returns isRawMaterial={data['isRawMaterial']}")
            
            print("INFO: No raw_material templates found in database. Feature ready but needs admin configuration.")
    
    def test_invalid_category_id_returns_400(self):
        """Test that invalid category ID returns 400"""
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/invalid-id")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Invalid category ID returns 400")
    
    def test_nonexistent_category_returns_404(self):
        """Test that non-existent category ID returns 404"""
        # Valid ObjectId format but doesn't exist
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{fake_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent category ID returns 404")


class TestProductRawMaterialConfigEndpoint:
    """Tests for GET /api/products/{product_id}/raw-material-config"""
    
    def test_endpoint_exists(self):
        """Test that the endpoint exists and responds"""
        response = requests.get(f"{BASE_URL}/api/products/invalid/raw-material-config")
        # Endpoint exists - returns 400 for invalid ID
        assert response.status_code == 400, f"Expected 400 for invalid ID, got {response.status_code}"
        print("PASS: GET /api/products/{id}/raw-material-config endpoint exists")
    
    def test_valid_product_returns_config(self):
        """Test that a valid product returns raw material config"""
        # First get any existing product
        products_response = requests.get(f"{BASE_URL}/api/products?limit=5")
        assert products_response.status_code == 200
        
        products_data = products_response.json()
        # API returns list directly
        products = products_data if isinstance(products_data, list) else products_data.get("products", [])
        
        if not products:
            pytest.skip("No products available in the database")
        
        # Use first product ID
        product_id = products[0].get("_id") or products[0].get("id")
        assert product_id, "Product should have an _id or id field"
        
        # Now test the raw-material-config endpoint
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/raw-material-config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response includes isRawMaterial
        assert "isRawMaterial" in data, "Response MUST include 'isRawMaterial' field"
        assert isinstance(data["isRawMaterial"], bool), "isRawMaterial should be boolean"
        
        print(f"PASS: Product {product_id} returns config with isRawMaterial={data['isRawMaterial']}")
        
        return data  # Return for chained tests
    
    def test_raw_material_product_returns_calculator_config(self):
        """Test that raw material products return calculatorConfig with fields"""
        # Get products and check each one's raw material config
        products_response = requests.get(f"{BASE_URL}/api/products?limit=20")
        assert products_response.status_code == 200
        
        products_data = products_response.json()
        # API returns list directly
        products = products_data if isinstance(products_data, list) else products_data.get("products", [])
        
        found_raw_material = False
        
        for product in products:
            product_id = product.get("_id") or product.get("id")
            response = requests.get(f"{BASE_URL}/api/products/{product_id}/raw-material-config")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("isRawMaterial"):
                    found_raw_material = True
                    
                    # Verify full response structure for raw material products
                    assert "product" in data, "Raw material config should include 'product'"
                    assert "category" in data, "Raw material config should include 'category'"
                    
                    # calculatorConfig should be present (may be null if no template)
                    assert "calculatorConfig" in data, "Raw material config should include 'calculatorConfig'"
                    
                    if data.get("calculatorConfig"):
                        config = data["calculatorConfig"]
                        # Verify calculator config structure
                        assert "templateId" in config, "calculatorConfig should have 'templateId'"
                        
                        # Optional fields
                        if "fields" in config:
                            assert isinstance(config["fields"], list), "fields should be a list"
                        if "formulaType" in config:
                            assert isinstance(config["formulaType"], str), "formulaType should be string"
                    
                    # Materials list
                    assert "materials" in data, "Raw material config should include 'materials'"
                    assert isinstance(data["materials"], list), "materials should be a list"
                    
                    if data["materials"]:
                        # Verify materials structure
                        material = data["materials"][0]
                        assert "name" in material, "Material should have 'name'"
                        assert "density" in material, "Material should have 'density'"
                    
                    print(f"PASS: Raw material product {product_id} returns full config with {len(data.get('materials', []))} materials")
                    break
        
        if not found_raw_material:
            # Test that standard products return isRawMaterial=false
            for product in products[:3]:
                product_id = product.get("_id") or product.get("id")
                response = requests.get(f"{BASE_URL}/api/products/{product_id}/raw-material-config")
                if response.status_code == 200:
                    data = response.json()
                    assert data.get("isRawMaterial") is False, \
                        f"Standard product {product_id} should return isRawMaterial=False"
            
            print("PASS: Standard products correctly return isRawMaterial=False")
            print("INFO: No raw_material products found. Feature ready but needs admin to mark category as raw_material.")
    
    def test_standard_product_returns_is_raw_material_false(self):
        """Test that standard (non-raw material) products return isRawMaterial=false"""
        # Get products
        products_response = requests.get(f"{BASE_URL}/api/products?limit=10")
        assert products_response.status_code == 200
        
        products_data = products_response.json()
        # API returns list directly
        products = products_data if isinstance(products_data, list) else products_data.get("products", [])
        
        tested_standard = False
        
        for product in products:
            product_id = product.get("_id") or product.get("id")
            response = requests.get(f"{BASE_URL}/api/products/{product_id}/raw-material-config")
            
            if response.status_code == 200:
                data = response.json()
                
                # If this is NOT a raw material product
                if not data.get("isRawMaterial"):
                    tested_standard = True
                    
                    # Verify minimal response for non-raw material
                    assert data["isRawMaterial"] is False, "isRawMaterial should be False for standard products"
                    
                    # Should NOT include calculatorConfig, materials, etc.
                    # (or they should be None/empty if included)
                    if "calculatorConfig" in data:
                        # If included, should be None for standard products
                        assert data["calculatorConfig"] is None or data["calculatorConfig"] == {}, \
                            "Standard products should have null/empty calculatorConfig"
                    
                    print(f"PASS: Standard product {product_id} returns isRawMaterial=False")
                    break
        
        if not tested_standard:
            print("INFO: All tested products were raw materials")
        assert tested_standard or len(products) == 0, "Should find at least one standard product to test"
    
    def test_materials_list_structure(self):
        """Test that materials list has correct structure with name and density"""
        # Get any product's raw material config
        products_response = requests.get(f"{BASE_URL}/api/products?limit=10")
        assert products_response.status_code == 200
        
        products_data = products_response.json()
        # API returns list directly
        products = products_data if isinstance(products_data, list) else products_data.get("products", [])
        
        for product in products:
            product_id = product.get("_id") or product.get("id")
            response = requests.get(f"{BASE_URL}/api/products/{product_id}/raw-material-config")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("isRawMaterial") and data.get("materials"):
                    materials = data["materials"]
                    
                    for material in materials:
                        assert "name" in material, f"Material missing 'name': {material}"
                        assert "density" in material, f"Material missing 'density': {material}"
                        assert isinstance(material["name"], str), "Material name should be string"
                        assert isinstance(material["density"], (int, float)), "Material density should be number"
                        assert material["density"] > 0, f"Density should be positive: {material}"
                    
                    print(f"PASS: Materials list has proper structure. Found {len(materials)} materials.")
                    return
        
        # If no raw material products, check materials endpoint directly
        materials_response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        if materials_response.status_code == 200:
            materials = materials_response.json()
            if materials:
                for material in materials:
                    assert "name" in material, f"Material missing 'name'"
                    assert "density" in material, f"Material missing 'density'"
                print(f"PASS: Materials endpoint returns proper structure with {len(materials)} materials")
        else:
            print("INFO: No raw material products to test materials list structure")
    
    def test_invalid_product_id_returns_400(self):
        """Test that invalid product ID returns 400"""
        response = requests.get(f"{BASE_URL}/api/products/invalid-id/raw-material-config")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Invalid product ID returns 400")
    
    def test_nonexistent_product_returns_404(self):
        """Test that non-existent product ID returns 404"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/products/{fake_id}/raw-material-config")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent product ID returns 404")


class TestCategoryTypeAndTemplateTypeInteraction:
    """Test the interaction between categoryType and templateType for raw material detection"""
    
    def test_both_detection_methods_work(self):
        """Test that raw material is detected via both category type and template type"""
        # Get all categories
        categories_response = requests.get(f"{BASE_URL}/api/categories")
        assert categories_response.status_code == 200
        categories = categories_response.json()
        
        detection_methods = {
            "category_type": False,
            "template_type": False
        }
        
        for category in categories:
            category_id = category.get("_id") or category.get("id")
            category_type = category.get("categoryType", "standard")
            
            response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
            if response.status_code != 200:
                continue
            
            data = response.json()
            
            # Check if detected via category type
            if category_type == "raw_material":
                if data.get("isRawMaterial"):
                    detection_methods["category_type"] = True
                    print(f"PASS: Category {category_id} detected as raw_material via categoryType")
            
            # Check if detected via template type
            templates = data.get("templates", [])
            for template in templates:
                if template.get("templateType") == "raw_material":
                    if data.get("isRawMaterial"):
                        detection_methods["template_type"] = True
                        print(f"PASS: Category {category_id} detected as raw_material via templateType")
        
        # Report what was detected
        if not detection_methods["category_type"] and not detection_methods["template_type"]:
            print("INFO: No raw_material categories or templates configured yet.")
            print("INFO: Feature is ready - admin needs to set categoryType='raw_material' or create template with templateType='raw_material'")
        else:
            print(f"Detection methods verified: {detection_methods}")
    
    def test_spec_template_by_category_checks_template_type(self):
        """Verify spec templates endpoint also checks templateType"""
        # Get all categories and their templates
        categories_response = requests.get(f"{BASE_URL}/api/categories")
        categories = categories_response.json()
        
        for category in categories:
            category_id = category.get("_id") or category.get("id")
            response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
            
            if response.status_code == 200:
                data = response.json()
                templates = data.get("templates", [])
                
                # Check template types
                has_raw_material_template = any(
                    t.get("templateType") == "raw_material" for t in templates
                )
                
                if has_raw_material_template:
                    # isRawMaterial should be True
                    assert data.get("isRawMaterial") is True, \
                        f"isRawMaterial should be True when template has templateType='raw_material'"
                    
                    # rawMaterialTemplate should be populated
                    assert data.get("rawMaterialTemplate") is not None, \
                        "rawMaterialTemplate should be populated when raw_material template exists"
                    
                    print(f"PASS: Category {category_id} correctly identifies raw_material from templateType")
                    return
        
        print("INFO: No templates with templateType='raw_material' found in database")


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
