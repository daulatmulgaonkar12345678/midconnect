"""
Test suite for 21 raw material shapes and 14+ material types
Tests shape configurations, material densities, and weight calculations
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://doc-builder-preview-1.preview.emergentagent.com"


class TestRawMaterialShapes:
    """Tests for GET /api/raw-materials/shapes - verify all 21 shapes"""
    
    def test_shapes_endpoint_returns_200(self):
        """Shapes endpoint should return 200 status"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        assert response.status_code == 200
        print("PASS: Shapes endpoint returns 200")
    
    def test_shapes_returns_21_shapes(self):
        """Should return exactly 21 shapes"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        assert len(shapes) == 21, f"Expected 21 shapes, got {len(shapes)}"
        print(f"PASS: Returns 21 shapes")
    
    def test_all_21_shape_keys_present(self):
        """All 21 shape keys should be present"""
        expected_keys = [
            "round_bar", "square_bar", "hex_bar", "flat_bar", "rectangular_bar",
            "pipe", "square_hollow", "rectangular_hollow",
            "angle", "channel", "i_beam", "h_beam", "t_section", "z_section",
            "plate", "sheet", "chequered_plate", "perforated_sheet",
            "wire_rod", "strip", "coil"
        ]
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        actual_keys = [s['key'] for s in shapes]
        
        for key in expected_keys:
            assert key in actual_keys, f"Missing shape: {key}"
        print(f"PASS: All 21 shape keys present: {expected_keys}")
    
    def test_shape_structure_has_required_fields(self):
        """Each shape should have key, name, fields, formula"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        
        for shape in shapes:
            assert 'key' in shape, f"Shape missing 'key': {shape}"
            assert 'name' in shape, f"Shape missing 'name': {shape}"
            assert 'fields' in shape, f"Shape missing 'fields': {shape}"
            assert 'formula' in shape, f"Shape missing 'formula': {shape}"
            assert len(shape['fields']) > 0, f"Shape has no fields: {shape['name']}"
        print("PASS: All shapes have required fields")
    
    def test_hex_bar_has_across_flats_field(self):
        """Hex bar should have 'across_flats' field"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        hex_bar = next((s for s in shapes if s['key'] == 'hex_bar'), None)
        
        assert hex_bar is not None, "Hex bar shape not found"
        field_keys = [f['key'] for f in hex_bar['fields']]
        assert 'across_flats' in field_keys, f"Hex bar missing 'across_flats', has: {field_keys}"
        print(f"PASS: Hex bar has 'across_flats' field")
    
    def test_angle_has_leg_a_leg_b_thickness_fields(self):
        """Angle should have leg_a, leg_b, thickness fields"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        angle = next((s for s in shapes if s['key'] == 'angle'), None)
        
        assert angle is not None, "Angle shape not found"
        field_keys = [f['key'] for f in angle['fields']]
        assert 'leg_a' in field_keys, f"Angle missing 'leg_a'"
        assert 'leg_b' in field_keys, f"Angle missing 'leg_b'"
        assert 'thickness' in field_keys, f"Angle missing 'thickness'"
        print(f"PASS: Angle has leg_a, leg_b, thickness fields")
    
    def test_channel_has_web_flange_fields(self):
        """Channel should have web_height, flange_width, web_thickness, flange_thickness"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        channel = next((s for s in shapes if s['key'] == 'channel'), None)
        
        assert channel is not None, "Channel shape not found"
        field_keys = [f['key'] for f in channel['fields']]
        assert 'web_height' in field_keys, f"Channel missing 'web_height'"
        assert 'flange_width' in field_keys, f"Channel missing 'flange_width'"
        assert 'web_thickness' in field_keys, f"Channel missing 'web_thickness'"
        assert 'flange_thickness' in field_keys, f"Channel missing 'flange_thickness'"
        print(f"PASS: Channel has all required fields")
    
    def test_i_beam_has_height_flange_web_fields(self):
        """I-Beam should have height, flange_width, web_thickness, flange_thickness"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        shapes = response.json()
        i_beam = next((s for s in shapes if s['key'] == 'i_beam'), None)
        
        assert i_beam is not None, "I-Beam shape not found"
        field_keys = [f['key'] for f in i_beam['fields']]
        assert 'height' in field_keys, f"I-Beam missing 'height'"
        assert 'flange_width' in field_keys, f"I-Beam missing 'flange_width'"
        assert 'web_thickness' in field_keys, f"I-Beam missing 'web_thickness'"
        assert 'flange_thickness' in field_keys, f"I-Beam missing 'flange_thickness'"
        print(f"PASS: I-Beam has all required fields")


class TestRawMaterialMaterials:
    """Tests for GET /api/raw-materials/materials - verify 14+ materials"""
    
    def test_materials_endpoint_returns_200(self):
        """Materials endpoint should return 200 status"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        assert response.status_code == 200
        print("PASS: Materials endpoint returns 200")
    
    def test_materials_returns_at_least_14(self):
        """Should return at least 14 materials"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        materials = response.json()
        assert len(materials) >= 14, f"Expected at least 14 materials, got {len(materials)}"
        print(f"PASS: Returns {len(materials)} materials (>= 14)")
    
    def test_required_materials_present(self):
        """All required materials should be present"""
        expected_materials = [
            "MS Steel", "EN8 Steel", "EN19 Steel",
            "SS202", "SS304", "SS304L", "SS316", "SS316L",
            "Aluminum 6061", "Aluminum 6063",
            "Copper", "Brass", "Cast Iron", "Titanium"
        ]
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        materials = response.json()
        actual_names = [m['name'] for m in materials]
        
        for mat in expected_materials:
            assert mat in actual_names, f"Missing material: {mat}"
        print(f"PASS: All 14 required materials present")
    
    def test_materials_have_correct_densities(self):
        """Materials should have correct densities"""
        expected_densities = {
            "MS Steel": 7850,
            "EN8 Steel": 7850,
            "EN19 Steel": 7850,
            "SS202": 7900,
            "SS304": 7930,
            "SS304L": 7930,
            "SS316": 8000,
            "SS316L": 8000,
            "Aluminum 6061": 2700,
            "Aluminum 6063": 2700,
            "Copper": 8960,
            "Brass": 8500,
            "Cast Iron": 7200,
            "Titanium": 4500
        }
        
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        materials = response.json()
        mat_dict = {m['name']: m['density'] for m in materials}
        
        for name, expected_density in expected_densities.items():
            if name in mat_dict:
                assert mat_dict[name] == expected_density, f"{name}: expected {expected_density}, got {mat_dict[name]}"
        print("PASS: All materials have correct densities")
    
    def test_material_structure(self):
        """Each material should have name, density"""
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        materials = response.json()
        
        for mat in materials:
            assert 'name' in mat, f"Material missing 'name'"
            assert 'density' in mat, f"Material missing 'density': {mat}"
            assert isinstance(mat['density'], (int, float)), f"Density should be number: {mat}"
        print("PASS: All materials have correct structure")


class TestWeightCalculations:
    """Tests for POST /api/raw-materials/calculate"""
    
    def test_hex_bar_25mm_3m_equals_12_75kg(self):
        """Hex Bar 25mm AF x 3m should equal ~12.75 kg"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "hex_bar",
                "material": "MS Steel",
                "dimensions": {
                    "across_flats": 25,
                    "across_flats_unit": "mm",
                    "length": 3,
                    "length_unit": "meter"
                },
                "quantity": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        weight = data['weight_per_piece']
        
        # Allow 1% tolerance
        assert 12.6 < weight < 12.9, f"Hex bar weight {weight:.2f} kg not ~12.75 kg"
        print(f"PASS: Hex Bar 25mm x 3m = {weight:.2f} kg (~12.75 kg)")
    
    def test_angle_65x65x6_6m_equals_35kg(self):
        """Angle 65x65x6 x 6m should equal ~35.04 kg"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "angle",
                "material": "MS Steel",
                "dimensions": {
                    "leg_a": 65,
                    "leg_a_unit": "mm",
                    "leg_b": 65,
                    "leg_b_unit": "mm",
                    "thickness": 6,
                    "thickness_unit": "mm",
                    "length": 6,
                    "length_unit": "meter"
                },
                "quantity": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        weight = data['weight_per_piece']
        
        # Allow 1% tolerance
        assert 34.5 < weight < 35.5, f"Angle weight {weight:.2f} kg not ~35.04 kg"
        print(f"PASS: Angle 65x65x6 x 6m = {weight:.2f} kg (~35.04 kg)")
    
    def test_i_beam_ismb200_6m_equals_150kg(self):
        """I-Beam ISMB 200 x 6m should equal ~149.63 kg"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "i_beam",
                "material": "MS Steel",
                "dimensions": {
                    "height": 200,
                    "height_unit": "mm",
                    "flange_width": 100,
                    "flange_width_unit": "mm",
                    "web_thickness": 5.7,
                    "web_thickness_unit": "mm",
                    "flange_thickness": 10.8,
                    "flange_thickness_unit": "mm",
                    "length": 6,
                    "length_unit": "meter"
                },
                "quantity": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        weight = data['weight_per_piece']
        
        # Allow 1% tolerance
        assert 148 < weight < 151, f"I-Beam weight {weight:.2f} kg not ~149.63 kg"
        print(f"PASS: I-Beam ISMB 200 x 6m = {weight:.2f} kg (~149.63 kg)")
    
    def test_channel_ismc150_6m_equals_97kg(self):
        """Channel ISMC 150 x 6m should equal ~97.16 kg"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "channel",
                "material": "MS Steel",
                "dimensions": {
                    "web_height": 150,
                    "web_height_unit": "mm",
                    "flange_width": 75,
                    "flange_width_unit": "mm",
                    "web_thickness": 5.4,
                    "web_thickness_unit": "mm",
                    "flange_thickness": 9,
                    "flange_thickness_unit": "mm",
                    "length": 6,
                    "length_unit": "meter"
                },
                "quantity": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        weight = data['weight_per_piece']
        
        # Allow 1% tolerance
        assert 96 < weight < 98.5, f"Channel weight {weight:.2f} kg not ~97.16 kg"
        print(f"PASS: Channel ISMC 150 x 6m = {weight:.2f} kg (~97.16 kg)")
    
    def test_calculate_returns_required_fields(self):
        """Calculate endpoint should return required result fields"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "round_bar",
                "material": "MS Steel",
                "dimensions": {
                    "diameter": 25,
                    "diameter_unit": "mm",
                    "length": 1,
                    "length_unit": "meter"
                },
                "quantity": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            'shape', 'material', 'density',
            'volume_per_piece', 'weight_per_piece', 'total_weight',
            'dimensions', 'quantity',
            'weight_per_piece_display', 'total_weight_display'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print("PASS: Calculate returns all required fields")
    
    def test_quantity_multiplies_total_weight(self):
        """Quantity should multiply total weight correctly"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "round_bar",
                "material": "MS Steel",
                "dimensions": {
                    "diameter": 25,
                    "diameter_unit": "mm",
                    "length": 1,
                    "length_unit": "meter"
                },
                "quantity": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        expected_total = data['weight_per_piece'] * 5
        assert abs(data['total_weight'] - expected_total) < 0.01, "Total weight not multiplied correctly"
        print(f"PASS: Quantity 5 gives total {data['total_weight']:.2f} kg = 5 x {data['weight_per_piece']:.2f}")


class TestAdditionalShapeCalculations:
    """Test additional shapes to ensure all 21 work"""
    
    def test_round_bar_calculation(self):
        """Round bar calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "round_bar",
                "material": "MS Steel",
                "dimensions": {"diameter": 50, "length": 1}
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: Round bar calculation works")
    
    def test_square_bar_calculation(self):
        """Square bar calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "square_bar",
                "material": "MS Steel",
                "dimensions": {"side": 50, "length": 1}
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: Square bar calculation works")
    
    def test_pipe_calculation(self):
        """Pipe calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "pipe",
                "material": "MS Steel",
                "dimensions": {"outer_diameter": 60, "thickness": 5, "length": 1}
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: Pipe calculation works")
    
    def test_plate_calculation(self):
        """Plate calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "plate",
                "material": "MS Steel",
                "dimensions": {"thickness": 10, "width": 1000, "length": 2}
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: Plate calculation works")
    
    def test_t_section_calculation(self):
        """T-section calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "t_section",
                "material": "MS Steel",
                "dimensions": {
                    "flange_width": 100,
                    "stem_height": 100,
                    "flange_thickness": 10,
                    "stem_thickness": 10,
                    "length": 1
                }
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: T-section calculation works")
    
    def test_h_beam_calculation(self):
        """H-beam calculation should work"""
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json={
                "shape": "h_beam",
                "material": "MS Steel",
                "dimensions": {
                    "height": 200,
                    "flange_width": 200,
                    "web_thickness": 8,
                    "flange_thickness": 12,
                    "length": 1
                }
            }
        )
        assert response.status_code == 200
        assert response.json()['weight_per_piece'] > 0
        print("PASS: H-beam calculation works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
