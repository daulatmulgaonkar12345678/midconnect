"""
Test Configurable Calculator API endpoints

Tests:
- Calculator template CRUD operations
- Material family filtering
- Calculation with formula execution
- Seller rates by product
- Unit groups
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test IDs from the main agent context
PIPE_CALCULATOR_ID = "69a9c3f643371dcb4a004e60"
TEST_CATEGORY_ID = "699be9023cbe1a8c31591667"
TEST_PRODUCT_ID = "699be9023cbe1a8c31591668"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCalculatorEndpoints:
    """Test calculator template API endpoints"""

    def test_get_all_calculators(self, api_client):
        """GET /api/calculator/calculators returns list of calculators"""
        response = api_client.get(f"{BASE_URL}/api/calculator/calculators")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure
        calc = data[0]
        assert "_id" in calc
        assert "name" in calc
        assert "fields" in calc
        assert "formula_expression" in calc
        print(f"✓ Found {len(data)} calculators")

    def test_get_calculator_by_id(self, api_client):
        """GET /api/calculator/calculators/{id} returns specific calculator"""
        response = api_client.get(f"{BASE_URL}/api/calculator/calculators/{PIPE_CALCULATOR_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["_id"] == PIPE_CALCULATOR_ID
        assert data["name"] == "Pipe Calculator"
        assert data["material_family"] == "Steel"
        assert len(data["fields"]) >= 3  # outer_diameter, thickness, length
        print(f"✓ Pipe Calculator: {data['name']}, family={data['material_family']}")

    def test_get_calculator_by_category(self, api_client):
        """GET /api/calculator/calculators/by-category/{id} returns linked calculator"""
        response = api_client.get(f"{BASE_URL}/api/calculator/calculators/by-category/{TEST_CATEGORY_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["category_id"] == TEST_CATEGORY_ID
        assert data["name"] == "Pipe Calculator"
        print(f"✓ Category {TEST_CATEGORY_ID} linked to {data['name']}")

    def test_calculator_fields_structure(self, api_client):
        """Verify calculator fields have required structure"""
        response = api_client.get(f"{BASE_URL}/api/calculator/calculators/{PIPE_CALCULATOR_ID}")
        assert response.status_code == 200
        
        data = response.json()
        fields = data["fields"]
        
        # Check field structure
        for field in fields:
            assert "key" in field, "Field missing 'key'"
            assert "label" in field, "Field missing 'label'"
            assert "unit_group" in field, "Field missing 'unit_group'"
            assert "default_unit" in field, "Field missing 'default_unit'"
            assert "required" in field, "Field missing 'required'"
            assert "order" in field, "Field missing 'order'"
        
        # Verify expected fields
        field_keys = [f["key"] for f in fields]
        assert "outer_diameter" in field_keys
        assert "thickness" in field_keys
        assert "length" in field_keys
        print(f"✓ Calculator fields verified: {field_keys}")


class TestMaterialEndpoints:
    """Test materials API endpoints"""

    def test_get_all_materials(self, api_client):
        """GET /api/calculator/materials returns all materials"""
        response = api_client.get(f"{BASE_URL}/api/calculator/materials")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10  # Should have 14+ materials
        print(f"✓ Found {len(data)} materials")

    def test_material_family_filter_steel(self, api_client):
        """GET /api/calculator/materials?family=Steel returns only Steel materials"""
        response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Steel")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 2  # MS Steel, EN8 Steel, EN19 Steel
        
        # Verify all returned materials are Steel family
        for mat in data:
            assert mat.get("material_family") == "Steel", f"Material {mat['name']} has wrong family"
        
        material_names = [m["name"] for m in data]
        assert "MS Steel" in material_names
        print(f"✓ Steel materials: {material_names}")

    def test_material_family_filter_stainless(self, api_client):
        """GET /api/calculator/materials?family=Stainless Steel returns only SS materials"""
        response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Stainless%20Steel")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all returned materials are Stainless Steel family
        for mat in data:
            assert mat.get("material_family") == "Stainless Steel"
        
        print(f"✓ Stainless Steel materials count: {len(data)}")

    def test_material_structure(self, api_client):
        """Verify material has required fields"""
        response = api_client.get(f"{BASE_URL}/api/calculator/materials")
        assert response.status_code == 200
        
        data = response.json()
        mat = data[0]
        
        assert "_id" in mat
        assert "name" in mat
        assert "density" in mat or "density" in mat
        print(f"✓ Material structure verified")

    def test_materials_have_density(self, api_client):
        """Verify materials have correct densities"""
        response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Steel")
        assert response.status_code == 200
        
        data = response.json()
        for mat in data:
            assert mat.get("density", 0) > 0, f"Material {mat['name']} missing density"
            # Steel density should be ~7850 kg/m³
            assert 7000 <= mat["density"] <= 8500, f"Material {mat['name']} has unusual density"
        
        print(f"✓ All Steel materials have valid density")


class TestCalculationEndpoint:
    """Test the calculation API"""

    def test_pipe_weight_calculation(self, api_client):
        """POST /api/calculator/calculate computes weight correctly"""
        # First get MS Steel material ID
        mat_response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Steel")
        materials = mat_response.json()
        ms_steel = next((m for m in materials if m["name"] == "MS Steel"), None)
        assert ms_steel is not None, "MS Steel material not found"
        
        # Calculate: OD=50mm, thickness=5mm, length=6m
        payload = {
            "calculator_id": PIPE_CALCULATOR_ID,
            "material_id": ms_steel["_id"],
            "field_values": {
                "outer_diameter": 50,
                "thickness": 5,
                "length": 6
            },
            "field_units": {
                "outer_diameter": "mm",
                "thickness": "mm",
                "length": "m"
            },
            "quantity": 1
        }
        
        response = api_client.post(f"{BASE_URL}/api/calculator/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["calculator_name"] == "Pipe Calculator"
        assert data["material_name"] == "MS Steel"
        assert data["output_unit"] == "kg"
        assert data["quantity"] == 1
        
        # Verify calculation: π × [(OD/2)² - (ID/2)²] × L × density
        # OD=0.05m, ID=0.04m, L=6m, density=7850
        expected_weight = math.pi * (0.025**2 - 0.02**2) * 6 * 7850
        actual_weight = data["total_value"]
        
        # Allow 1% tolerance
        assert abs(actual_weight - expected_weight) / expected_weight < 0.01
        print(f"✓ Pipe calculation: {actual_weight:.2f} kg (expected ~{expected_weight:.2f} kg)")

    def test_calculation_with_quantity(self, api_client):
        """Verify quantity multiplies total correctly"""
        mat_response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Steel")
        materials = mat_response.json()
        ms_steel = next((m for m in materials if m["name"] == "MS Steel"), None)
        
        payload = {
            "calculator_id": PIPE_CALCULATOR_ID,
            "material_id": ms_steel["_id"],
            "field_values": {
                "outer_diameter": 50,
                "thickness": 5,
                "length": 6
            },
            "field_units": {
                "outer_diameter": "mm",
                "thickness": "mm",
                "length": "m"
            },
            "quantity": 3
        }
        
        response = api_client.post(f"{BASE_URL}/api/calculator/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["quantity"] == 3
        assert abs(data["total_value"] - 3 * data["value_per_piece"]) < 0.01
        print(f"✓ Quantity multiplier works: {data['value_per_piece']:.2f} × 3 = {data['total_value']:.2f} kg")

    def test_calculation_returns_field_summary(self, api_client):
        """Verify calculation returns field summary for display"""
        mat_response = api_client.get(f"{BASE_URL}/api/calculator/materials?family=Steel")
        materials = mat_response.json()
        ms_steel = next((m for m in materials if m["name"] == "MS Steel"), None)
        
        payload = {
            "calculator_id": PIPE_CALCULATOR_ID,
            "material_id": ms_steel["_id"],
            "field_values": {
                "outer_diameter": 50,
                "thickness": 5,
                "length": 6
            },
            "field_units": {
                "outer_diameter": "mm",
                "thickness": "mm",
                "length": "m"
            },
            "quantity": 1
        }
        
        response = api_client.post(f"{BASE_URL}/api/calculator/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "field_summary" in data
        assert "outer_diameter" in data["field_summary"]
        assert "thickness" in data["field_summary"]
        assert "length" in data["field_summary"]
        print(f"✓ Field summary: {data['field_summary']}")

    def test_calculation_without_material(self, api_client):
        """Verify calculation works without material (uses default density=1)"""
        payload = {
            "calculator_id": PIPE_CALCULATOR_ID,
            "material_id": None,
            "field_values": {
                "outer_diameter": 50,
                "thickness": 5,
                "length": 6
            },
            "field_units": {
                "outer_diameter": "mm",
                "thickness": "mm",
                "length": "m"
            },
            "quantity": 1
        }
        
        response = api_client.post(f"{BASE_URL}/api/calculator/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["material_name"] is None
        # With density=1, the result should be the volume in m³
        print(f"✓ Calculation without material: {data['total_value']:.4f} (volume in m³)")


class TestSellersByProduct:
    """Test sellers-by-product endpoint for calculator integration"""

    def test_get_sellers_for_product(self, api_client):
        """GET /api/calculator/sellers-by-product/{id} returns seller rates"""
        response = api_client.get(f"{BASE_URL}/api/calculator/sellers-by-product/{TEST_PRODUCT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} sellers for product")
        
        if len(data) > 0:
            seller = data[0]
            assert "_id" in seller
            assert "sellerId" in seller
            assert "rate_per_unit" in seller
            assert "rate_unit" in seller
            print(f"  First seller: rate={seller['rate_per_unit']}/{seller['rate_unit']}")

    def test_invalid_product_id(self, api_client):
        """GET with invalid product ID returns 400"""
        response = api_client.get(f"{BASE_URL}/api/calculator/sellers-by-product/invalid")
        assert response.status_code == 400


class TestUnitGroups:
    """Test unit groups endpoint"""

    def test_get_unit_groups(self, api_client):
        """GET /api/calculator/unit-groups returns unit groups"""
        response = api_client.get(f"{BASE_URL}/api/calculator/unit-groups")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure
        group = data[0]
        assert "name" in group
        assert "units" in group
        assert "base_unit" in group
        
        print(f"✓ Found {len(data)} unit groups")


class TestCalculatorIntegration:
    """Integration tests for calculator flow"""

    def test_full_calculator_flow(self, api_client):
        """Test complete flow: get calculator, get materials, calculate"""
        # 1. Get calculator by category
        calc_response = api_client.get(f"{BASE_URL}/api/calculator/calculators/by-category/{TEST_CATEGORY_ID}")
        assert calc_response.status_code == 200
        calculator = calc_response.json()
        calc_id = calculator["_id"]
        material_family = calculator.get("material_family")
        
        print(f"1. Calculator: {calculator['name']}, family={material_family}")
        
        # 2. Get materials (filtered by family if specified)
        mat_url = f"{BASE_URL}/api/calculator/materials"
        if material_family:
            mat_url += f"?family={material_family}"
        mat_response = api_client.get(mat_url)
        assert mat_response.status_code == 200
        materials = mat_response.json()
        
        print(f"2. Materials loaded: {len(materials)} ({material_family or 'all'})")
        
        # 3. Perform calculation with first material
        if materials:
            material_id = materials[0]["_id"]
            material_name = materials[0]["name"]
            
            calc_payload = {
                "calculator_id": calc_id,
                "material_id": material_id,
                "field_values": {
                    "outer_diameter": 75,
                    "thickness": 6,
                    "length": 4
                },
                "field_units": {
                    "outer_diameter": "mm",
                    "thickness": "mm",
                    "length": "m"
                },
                "quantity": 2
            }
            
            result_response = api_client.post(f"{BASE_URL}/api/calculator/calculate", json=calc_payload)
            assert result_response.status_code == 200
            result = result_response.json()
            
            print(f"3. Calculation: {result['total_value']:.2f} kg ({result['quantity']} pcs of {material_name})")
        
        # 4. Get sellers with rates
        sellers_response = api_client.get(f"{BASE_URL}/api/calculator/sellers-by-product/{TEST_PRODUCT_ID}")
        assert sellers_response.status_code == 200
        sellers = sellers_response.json()
        
        print(f"4. Sellers: {len(sellers)} with rates")
        
        print("✓ Full calculator integration flow passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
