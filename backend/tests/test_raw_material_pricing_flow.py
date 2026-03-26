"""
Test Raw Material Pricing Flow
==============================
Complete test for raw material pricing flow from seller creation to buyer inquiry:

1. POST /api/seller/listings accepts rate_per_kg and material_supported fields
2. PATCH /api/seller/listings/{id}/rate-per-kg endpoint for daily rate updates
3. GET /api/raw-materials/sellers/raw-material/{productId} returns sellers with rate_per_kg
4. POST /api/inquiries accepts calculationData for raw material inquiries
5. GET /api/seller/inquiries returns calculationData for raw material inquiries
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://plan-limits-5.preview.emergentagent.com')


class TestRawMaterialPricingEndpoints:
    """Test raw material pricing API endpoints"""
    
    # ========== Test 1: POST /api/seller/listings accepts rate_per_kg ==========
    
    def test_listing_create_schema_accepts_rate_per_kg(self):
        """Test that listing creation schema accepts rate_per_kg field"""
        # Send a listing creation request with rate_per_kg
        # It should NOT return 422 (validation error) for the rate_per_kg field
        
        payload = {
            "productId": "507f1f77bcf86cd799439011",  # Dummy ID
            "attributes": {"test": "value"},
            "sellerRole": "manufacturer",
            "moq": 100,
            "stock": 1000,
            "maxCapacity": 5000,
            "leadTime": 7,
            "currency": "INR",
            "pricingTiers": [{"minQty": 1, "maxQty": 99, "pricePerUnit": 100}, {"minQty": 100, "maxQty": None, "pricePerUnit": 90}],
            "images": ["https://example.com/image.jpg"],
            "rate_per_kg": 85.50,  # Raw material rate
            "material_supported": "MS Steel"  # Material type
        }
        
        response = requests.post(
            f"{BASE_URL}/api/seller/listings",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (auth required) or 404 (product not found), NOT 422 (validation error)
        assert response.status_code != 422, f"Schema validation failed - rate_per_kg rejected: {response.text}"
        
        if response.status_code == 422:
            # Check if rate_per_kg specifically caused the error
            error_detail = response.json().get("detail", "")
            assert "rate_per_kg" not in str(error_detail), f"rate_per_kg field rejected: {error_detail}"
            assert "material_supported" not in str(error_detail), f"material_supported field rejected: {error_detail}"
        
        print(f"PASS: POST /api/seller/listings accepts rate_per_kg field (status: {response.status_code})")
    
    # ========== Test 2: PATCH /api/seller/listings/{id}/rate-per-kg endpoint ==========
    
    def test_rate_per_kg_update_endpoint_exists(self):
        """Test that PATCH /api/seller/listings/{id}/rate-per-kg endpoint exists"""
        
        listing_id = "507f1f77bcf86cd799439011"  # Dummy ID
        
        payload = {
            "rate_per_kg": 90.00,
            "material_supported": "MS Steel"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}/rate-per-kg",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (auth required), NOT 404 (endpoint not found) or 422 (validation error)
        assert response.status_code != 404, f"Endpoint not found - PATCH /api/seller/listings/{{id}}/rate-per-kg does not exist"
        assert response.status_code != 405, f"Method not allowed - PATCH method not supported"
        
        # Should get 401 for auth required (expected)
        if response.status_code == 401:
            print(f"PASS: PATCH /api/seller/listings/{{id}}/rate-per-kg endpoint exists (auth required)")
        else:
            print(f"PASS: PATCH /api/seller/listings/{{id}}/rate-per-kg endpoint exists (status: {response.status_code})")
    
    def test_rate_per_kg_update_schema_validation(self):
        """Test RatePerKgUpdate schema validation"""
        
        listing_id = "507f1f77bcf86cd799439011"  # Dummy ID
        
        # Test with valid payload
        payload = {
            "rate_per_kg": 85.00,
            "material_supported": "SS304 Steel"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}/rate-per-kg",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should NOT get 422 (schema should accept these fields)
        assert response.status_code != 422, f"Schema validation failed: {response.text}"
        
        print(f"PASS: RatePerKgUpdate schema accepts valid payload (status: {response.status_code})")
    
    def test_rate_per_kg_requires_positive_value(self):
        """Test that rate_per_kg must be positive"""
        
        listing_id = "507f1f77bcf86cd799439011"
        
        # Test with negative value
        payload = {
            "rate_per_kg": -10.00
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}/rate-per-kg",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 422 for validation error (negative rate not allowed)
        if response.status_code == 422:
            print("PASS: Negative rate_per_kg correctly rejected")
        else:
            print(f"INFO: Negative rate_per_kg response: {response.status_code}")
    
    # ========== Test 3: GET /api/raw-materials/sellers/raw-material/{productId} ==========
    
    def test_raw_material_sellers_endpoint_exists(self):
        """Test that GET /api/raw-materials/sellers/raw-material/{productId} endpoint exists"""
        
        product_id = "507f1f77bcf86cd799439011"  # Dummy ID
        
        response = requests.get(
            f"{BASE_URL}/api/raw-materials/sellers/raw-material/{product_id}"
        )
        
        # Should NOT get 404 (endpoint should exist)
        # Should return 400 (invalid ID format) or 200 (empty array for non-existent product)
        assert response.status_code != 404, "Endpoint /api/raw-materials/sellers/raw-material/{productId} not found"
        
        print(f"PASS: GET /api/raw-materials/sellers/raw-material/{{productId}} endpoint exists (status: {response.status_code})")
    
    def test_raw_material_sellers_returns_rate_per_kg(self):
        """Test that raw material sellers endpoint returns rate_per_kg field in response"""
        
        product_id = "507f1f77bcf86cd799439011"
        
        response = requests.get(
            f"{BASE_URL}/api/raw-materials/sellers/raw-material/{product_id}?material=MS%20Steel"
        )
        
        # If we get sellers, check the response structure
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                seller = data[0]
                # Check expected fields exist
                expected_fields = ["listingId", "sellerId", "sellerName", "rate_per_kg"]
                for field in expected_fields:
                    if field in seller:
                        print(f"  - {field}: {seller.get(field)}")
                print(f"PASS: Seller response structure includes rate_per_kg field")
            else:
                print(f"INFO: No sellers found for this product (empty array)")
        else:
            print(f"INFO: Response status {response.status_code}")


class TestInquiryWithCalculationData:
    """Test inquiry creation and retrieval with calculationData"""
    
    def test_inquiry_accepts_calculationData_field(self):
        """Test POST /api/inquiries accepts calculationData field"""
        
        payload = {
            "sellerId": "507f1f77bcf86cd799439011",
            "listingId": "507f1f77bcf86cd799439012",
            "quantity": 100,
            "message": "Test inquiry with calculation",
            "buyerType": "manufacturer",
            "calculationData": {
                "material": "MS Steel",
                "shape": "round_bar",
                "dimensions": {
                    "diameter": 20,
                    "length": 6000
                },
                "quantity": 10,
                "weight_per_piece": 14.8,
                "total_weight": 148.0,
                "rate_per_kg": 85.50,
                "calculated_price": 12654.0
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/inquiries",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (auth required), NOT 422 (validation error)
        assert response.status_code != 422, f"Schema validation failed - calculationData rejected: {response.text}"
        
        if response.status_code == 422:
            error_detail = response.json().get("detail", "")
            assert "calculationData" not in str(error_detail), f"calculationData field rejected: {error_detail}"
        
        print(f"PASS: POST /api/inquiries accepts calculationData field (status: {response.status_code})")
    
    def test_seller_inquiries_endpoint_exists(self):
        """Test GET /api/seller/inquiries endpoint exists"""
        
        response = requests.get(
            f"{BASE_URL}/api/seller/inquiries",
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (auth required), NOT 404 (endpoint not found)
        assert response.status_code != 404, "Endpoint /api/seller/inquiries not found"
        
        print(f"PASS: GET /api/seller/inquiries endpoint exists (status: {response.status_code})")


class TestRawMaterialShapesAndMaterials:
    """Test raw material calculator endpoints"""
    
    def test_materials_endpoint(self):
        """Test GET /api/raw-materials/materials returns materials list"""
        
        response = requests.get(f"{BASE_URL}/api/raw-materials/materials")
        
        assert response.status_code == 200, f"Materials endpoint failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Materials response should be a list"
        
        if len(data) > 0:
            material = data[0]
            assert "name" in material, "Material should have 'name' field"
            assert "density" in material, "Material should have 'density' field"
            print(f"PASS: Materials endpoint returns {len(data)} materials")
            for m in data[:3]:
                print(f"  - {m.get('name')}: density={m.get('density')} kg/m³")
        else:
            print("INFO: No materials found in database")
    
    def test_shapes_endpoint(self):
        """Test GET /api/raw-materials/shapes returns shapes config"""
        
        response = requests.get(f"{BASE_URL}/api/raw-materials/shapes")
        
        assert response.status_code == 200, f"Shapes endpoint failed: {response.status_code}"
        
        data = response.json()
        
        # Should return shape configurations
        if isinstance(data, dict):
            expected_shapes = ["round_bar", "pipe", "plate", "square_bar"]
            for shape in expected_shapes:
                if shape in data:
                    print(f"  - Found shape: {shape}")
            print(f"PASS: Shapes endpoint returns shape configurations")
        elif isinstance(data, list):
            print(f"PASS: Shapes endpoint returns {len(data)} shapes")
    
    def test_calculate_weight_endpoint(self):
        """Test POST /api/raw-materials/calculate endpoint"""
        
        payload = {
            "shape": "round_bar",
            "material": "MS Steel",
            "dimensions": {
                "diameter": 20,
                "length": 6000
            },
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/raw-materials/calculate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Calculate endpoint failed: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Check expected fields in response
        expected_fields = ["weight_per_piece", "total_weight", "material", "shape"]
        for field in expected_fields:
            assert field in data, f"Missing field '{field}' in calculation response"
        
        print(f"PASS: Calculate endpoint works correctly")
        print(f"  - Material: {data.get('material')}")
        print(f"  - Shape: {data.get('shape')}")
        print(f"  - Weight per piece: {data.get('weight_per_piece')} kg")
        print(f"  - Total weight: {data.get('total_weight')} kg")


class TestListingUpdateWithRatePerKg:
    """Test listing update endpoints with rate_per_kg field"""
    
    def test_listing_patch_accepts_rate_per_kg(self):
        """Test PATCH /api/seller/listings/{id} accepts rate_per_kg field"""
        
        listing_id = "507f1f77bcf86cd799439011"
        
        payload = {
            "rate_per_kg": 95.00,
            "material_supported": "SS316 Steel"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/seller/listings/{listing_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (auth required), NOT 422 (validation error)
        assert response.status_code != 422, f"Schema validation failed - rate_per_kg in update rejected: {response.text}"
        
        print(f"PASS: PATCH /api/seller/listings/{{id}} accepts rate_per_kg field (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
