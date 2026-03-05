"""
Raw Material Calculator API Tests
Tests for:
- GET /api/raw-materials/materials - Get all materials with densities
- GET /api/raw-materials/shapes - Get all shape configurations
- POST /api/raw-materials/calculate - Calculate weight for various shapes
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMaterialsAPI:
    """Test materials endpoint - returns 6 default materials with densities"""
    
    def test_get_materials_success(self):
        """GET /api/raw-materials/materials returns materials list"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 6, f"Expected at least 6 materials, got {len(data)}"
    
    def test_materials_have_required_fields(self):
        """Verify materials have _id, name, density"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        data = response.json()
        
        for material in data:
            assert "_id" in material, "Material should have _id"
            assert "name" in material, "Material should have name"
            assert "density" in material, "Material should have density"
            assert isinstance(material["density"], (int, float)), "Density should be numeric"
            assert material["density"] > 0, "Density should be positive"
    
    def test_materials_includes_expected_types(self):
        """Verify expected materials are present (MS Steel, SS304, SS316, Aluminum, Copper, Brass)"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        data = response.json()
        
        material_names = [m["name"] for m in data]
        expected = ["MS Steel", "SS304", "SS316", "Aluminum", "Copper", "Brass"]
        
        for name in expected:
            assert name in material_names, f"Material {name} should be present"


class TestShapesAPI:
    """Test shapes endpoint - returns 5 shape configurations"""
    
    def test_get_shapes_success(self):
        """GET /api/raw-materials/shapes returns shapes list"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 5, f"Expected 5 shapes, got {len(data)}"
    
    def test_shapes_have_required_fields(self):
        """Verify shapes have key, name, fields, formula"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        data = response.json()
        
        for shape in data:
            assert "key" in shape, "Shape should have key"
            assert "name" in shape, "Shape should have name"
            assert "fields" in shape, "Shape should have fields array"
            assert "formula" in shape, "Shape should have formula"
            assert isinstance(shape["fields"], list), "Fields should be a list"
    
    def test_shapes_includes_expected_types(self):
        """Verify expected shapes are present (round_bar, square_bar, pipe, plate, sheet)"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        data = response.json()
        
        shape_keys = [s["key"] for s in data]
        expected = ["round_bar", "square_bar", "pipe", "plate", "sheet"]
        
        for key in expected:
            assert key in shape_keys, f"Shape {key} should be present"


class TestCalculateRoundBar:
    """Test calculation for round bar shape"""
    
    def test_calculate_round_bar_basic(self):
        """POST /api/raw-materials/calculate - round_bar basic calculation"""
        payload = {
            "shape": "round_bar",
            "material": "MS Steel",
            "dimensions": {
                "diameter": 10,
                "diameter_unit": "mm",
                "length": 6,
                "length_unit": "meter"
            },
            "quantity": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["shape"] == "round_bar"
        assert data["material"] == "MS Steel"
        assert data["density"] == 7850  # MS Steel density
        assert data["quantity"] == 1
        
        # Verify weight calculation: V = π × (d/2)² × L
        # d=10mm=0.01m, L=6m
        expected_volume = math.pi * (0.01/2)**2 * 6  # ~0.0004712
        expected_weight = expected_volume * 7850  # ~3.699 kg
        assert abs(data["weight_per_piece"] - expected_weight) < 0.01, "Weight calculation should match"
    
    def test_calculate_round_bar_quantity(self):
        """Test round_bar with multiple quantity"""
        payload = {
            "shape": "round_bar",
            "material": "MS Steel",
            "dimensions": {
                "diameter": 10,
                "diameter_unit": "mm",
                "length": 6,
                "length_unit": "meter"
            },
            "quantity": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        data = response.json()
        
        assert data["quantity"] == 5
        assert abs(data["total_weight"] - data["weight_per_piece"] * 5) < 0.001


class TestCalculatePipe:
    """Test calculation for pipe/tube shape"""
    
    def test_calculate_pipe_basic(self):
        """POST /api/raw-materials/calculate - pipe basic calculation"""
        payload = {
            "shape": "pipe",
            "material": "SS304",
            "dimensions": {
                "outer_diameter": 50,
                "outer_diameter_unit": "mm",
                "thickness": 3,
                "thickness_unit": "mm",
                "length": 2,
                "length_unit": "meter"
            },
            "quantity": 2
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["shape"] == "pipe"
        assert data["material"] == "SS304"
        assert data["density"] == 7930  # SS304 density
        assert data["quantity"] == 2
        
        # Verify weight calculation: V = π × ((OD/2)² - ((OD-2t)/2)²) × L
        # OD=50mm=0.05m, t=3mm=0.003m, L=2m
        od = 0.05
        t = 0.003
        id = od - 2*t  # 0.044m
        expected_volume = math.pi * ((od/2)**2 - (id/2)**2) * 2
        expected_weight = expected_volume * 7930
        assert abs(data["weight_per_piece"] - expected_weight) < 0.01, "Pipe weight calculation should match"


class TestCalculatePlate:
    """Test calculation for plate shape with pricing"""
    
    def test_calculate_plate_with_price(self):
        """POST /api/raw-materials/calculate - plate with rate_per_kg"""
        payload = {
            "shape": "plate",
            "material": "Aluminum",
            "dimensions": {
                "thickness": 5,
                "thickness_unit": "mm",
                "width": 500,
                "width_unit": "mm",
                "length": 1,
                "length_unit": "meter"
            },
            "quantity": 3,
            "rate_per_kg": 250
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["shape"] == "plate"
        assert data["material"] == "Aluminum"
        assert data["density"] == 2700  # Aluminum density
        assert data["quantity"] == 3
        assert data["rate_per_kg"] == 250
        
        # Verify: V = thickness × width × length
        # t=5mm=0.005m, w=500mm=0.5m, L=1m
        expected_volume = 0.005 * 0.5 * 1  # 0.0025 m³
        expected_weight = expected_volume * 2700  # 6.75 kg/piece
        expected_total = expected_weight * 3  # 20.25 kg
        expected_price = expected_total * 250  # 5062.50
        
        assert abs(data["weight_per_piece"] - expected_weight) < 0.01
        assert abs(data["total_weight"] - expected_total) < 0.01
        assert data["total_price"] == 5062.5
        assert data["total_price_display"] is not None


class TestCalculateSquareBar:
    """Test calculation for square bar shape"""
    
    def test_calculate_square_bar(self):
        """POST /api/raw-materials/calculate - square_bar"""
        payload = {
            "shape": "square_bar",
            "material": "Copper",
            "dimensions": {
                "side": 20,
                "side_unit": "mm",
                "length": 3,
                "length_unit": "meter"
            },
            "quantity": 2
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "square_bar"
        assert data["material"] == "Copper"
        assert data["density"] == 8960  # Copper density
        
        # V = side² × L = 0.02² × 3 = 0.0012 m³
        expected_volume = 0.02**2 * 3
        expected_weight = expected_volume * 8960
        assert abs(data["weight_per_piece"] - expected_weight) < 0.01


class TestCalculateSheet:
    """Test calculation for sheet shape"""
    
    def test_calculate_sheet(self):
        """POST /api/raw-materials/calculate - sheet"""
        payload = {
            "shape": "sheet",
            "material": "Brass",
            "dimensions": {
                "thickness": 2,
                "thickness_unit": "mm",
                "width": 1000,
                "width_unit": "mm",
                "length": 2,
                "length_unit": "meter"
            },
            "quantity": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["shape"] == "sheet"
        assert data["material"] == "Brass"
        assert data["density"] == 8500  # Brass density


class TestCalculateEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_shape_returns_error(self):
        """Invalid shape should return 400/500"""
        payload = {
            "shape": "invalid_shape",
            "material": "MS Steel",
            "dimensions": {"diameter": 10, "length": 1},
            "quantity": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code in [400, 500], f"Invalid shape should return error, got {response.status_code}"
    
    def test_unit_conversion_inch(self):
        """Test inch unit conversion"""
        payload = {
            "shape": "round_bar",
            "material": "MS Steel",
            "dimensions": {
                "diameter": 1,
                "diameter_unit": "inch",  # 1 inch = 25.4 mm = 0.0254 m
                "length": 3,
                "length_unit": "feet"  # 3 feet = 0.9144 m
            },
            "quantity": 1
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # V = π × (0.0254/2)² × 0.9144 = ~0.000463 m³
        # Weight = 0.000463 × 7850 = ~3.64 kg
        assert 3 < data["weight_per_piece"] < 4, "1 inch × 3 feet round bar should weigh ~3.6 kg"


class TestResponseFormat:
    """Test response format and display fields"""
    
    def test_response_has_display_fields(self):
        """Response should include formatted display strings"""
        payload = {
            "shape": "round_bar",
            "material": "MS Steel",
            "dimensions": {"diameter": 50, "length": 6, "diameter_unit": "mm", "length_unit": "meter"},
            "quantity": 10,
            "rate_per_kg": 75
        }
        
        response = requests.post(f"{BASE_URL}/api/raw-materials/calculate", json=payload)
        data = response.json()
        
        assert "weight_per_piece_display" in data, "Should have weight_per_piece_display"
        assert "total_weight_display" in data, "Should have total_weight_display"
        assert "total_price_display" in data, "Should have total_price_display"
        assert "dimensions" in data, "Should have dimensions summary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
