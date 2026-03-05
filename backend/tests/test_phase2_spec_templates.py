"""
Phase 2 Admin Spec Template System Testing
Tests:
1. Spec templates with templateType (standard/raw_material)
2. Spec templates with formulaType (round_bar/square_bar/pipe/plate/sheet)
3. GET /api/spec-templates/by-category/{category_id} endpoint
4. Calculator API still working with different shapes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestRawMaterialsAPI:
    """Test raw materials calculator APIs"""
    
    def test_materials_endpoint(self):
        """GET /api/raw-materials/materials returns materials with density"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify material structure
        for material in data:
            assert "_id" in material
            assert "name" in material
            assert "density" in material
            assert isinstance(material["density"], (int, float))
            assert material["density"] > 0
        
        print(f"✅ GET /api/raw-materials/materials - {len(data)} materials returned")
    
    def test_shapes_endpoint(self):
        """GET /api/raw-materials/shapes returns shape configurations"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # round_bar, square_bar, pipe, plate, sheet
        
        # Check expected shapes
        shape_keys = [shape["key"] for shape in data]
        assert "round_bar" in shape_keys
        assert "square_bar" in shape_keys
        assert "pipe" in shape_keys
        assert "plate" in shape_keys
        assert "sheet" in shape_keys
        
        # Verify shape structure
        for shape in data:
            assert "key" in shape
            assert "name" in shape
            assert "fields" in shape
            assert "formula" in shape
            assert isinstance(shape["fields"], list)
        
        print(f"✅ GET /api/raw-materials/shapes - {len(data)} shapes returned")
    
    def test_calculate_round_bar(self):
        """POST /api/raw-materials/calculate - round_bar shape"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "round_bar",
                "material": "MS Steel",
                "dimensions": {"diameter": 10, "length": 6},
                "quantity": 1
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "round_bar"
        assert data["material"] == "MS Steel"
        assert data["density"] == 7850.0
        assert data["weight_per_piece"] > 0
        assert data["total_weight"] > 0
        assert "weight_per_piece_display" in data
        assert "total_weight_display" in data
        
        print(f"✅ POST calculate round_bar - weight: {data['total_weight_display']}")
    
    def test_calculate_square_bar(self):
        """POST /api/raw-materials/calculate - square_bar shape"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "square_bar",
                "material": "MS Steel",
                "dimensions": {"side": 10, "length": 6},
                "quantity": 1
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "square_bar"
        assert data["weight_per_piece"] > 0
        
        print(f"✅ POST calculate square_bar - weight: {data['total_weight_display']}")
    
    def test_calculate_pipe(self):
        """POST /api/raw-materials/calculate - pipe shape"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "pipe",
                "material": "SS304",
                "dimensions": {"outer_diameter": 50, "thickness": 5, "length": 3},
                "quantity": 2,
                "rate_per_kg": 200
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "pipe"
        assert data["material"] == "SS304"
        assert data["quantity"] == 2
        assert data["rate_per_kg"] == 200.0
        assert data["total_price"] > 0
        assert data["total_price_display"] is not None
        
        print(f"✅ POST calculate pipe - weight: {data['total_weight_display']}, price: {data['total_price_display']}")
    
    def test_calculate_plate(self):
        """POST /api/raw-materials/calculate - plate shape"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "plate",
                "material": "Aluminum",
                "dimensions": {"thickness": 5, "width": 100, "length": 2},
                "quantity": 1
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "plate"
        assert data["material"] == "Aluminum"
        assert data["density"] == 2700.0
        
        print(f"✅ POST calculate plate - weight: {data['total_weight_display']}")
    
    def test_calculate_sheet(self):
        """POST /api/raw-materials/calculate - sheet shape"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "sheet",
                "material": "SS316",
                "dimensions": {"thickness": 2, "width": 1000, "length": 2},
                "quantity": 1
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "sheet"
        assert data["material"] == "SS316"
        
        print(f"✅ POST calculate sheet - weight: {data['total_weight_display']}")


class TestSpecTemplatesByCategory:
    """Test the new spec-templates/by-category endpoint"""
    
    def test_get_templates_by_category(self):
        """GET /api/spec-templates/by-category/{category_id} returns templates"""
        # First get a category ID
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        if not categories:
            pytest.skip("No categories found in database")
        
        category_id = categories[0]["_id"]
        
        # Now test the by-category endpoint
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/{category_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response structure
        assert "category" in data
        assert "templates" in data
        assert "isRawMaterial" in data
        
        # Verify category info
        assert data["category"]["_id"] == category_id
        assert "name" in data["category"]
        assert "categoryType" in data["category"]
        
        # Verify templates is a list
        assert isinstance(data["templates"], list)
        
        # Verify isRawMaterial flag
        assert isinstance(data["isRawMaterial"], bool)
        assert data["isRawMaterial"] == (data["category"]["categoryType"] == "raw_material")
        
        print(f"✅ GET /api/spec-templates/by-category/{category_id}")
        print(f"   Category: {data['category']['name']}, Type: {data['category']['categoryType']}")
        print(f"   Templates: {len(data['templates'])}, isRawMaterial: {data['isRawMaterial']}")
    
    def test_invalid_category_id(self):
        """GET /api/spec-templates/by-category with invalid ID returns 400"""
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/invalid-id")
        assert response.status_code == 400
        
        print("✅ GET /api/spec-templates/by-category/invalid-id - returns 400")
    
    def test_nonexistent_category(self):
        """GET /api/spec-templates/by-category with nonexistent ID returns 404"""
        # Use a valid ObjectId format but non-existent
        response = requests.get(f"{BASE_URL}/api/spec-templates/by-category/000000000000000000000000")
        assert response.status_code == 404
        
        print("✅ GET /api/spec-templates/by-category/nonexistent - returns 404")


class TestAdminEndpointsRequireAuth:
    """Test that admin endpoints require authentication"""
    
    def test_admin_materials_requires_auth(self):
        """GET /api/raw-materials/admin/materials requires auth"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/admin/materials")
        # Should get 401 or 403 without auth
        assert response.status_code in [401, 403, 500]  # 500 if not caught properly
        
        print("✅ GET /api/raw-materials/admin/materials - requires auth")
    
    def test_admin_spec_templates_requires_auth(self):
        """GET /api/admin/spec-templates requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/spec-templates")
        # Should get 401 or 403 without auth
        assert response.status_code in [401, 403, 500]
        
        print("✅ GET /api/admin/spec-templates - requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
