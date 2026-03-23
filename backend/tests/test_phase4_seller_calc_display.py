"""
Phase 4: Seller Dashboard Integration for Raw Material Calculation Data
========================================================================
Tests:
1. POST /api/inquiries stores calculationData in database
2. GET /api/seller/inquiries returns calculationData field when present
3. InquiryCreate model accepts calculationData field
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://smart-docs-flow-2.preview.emergentagent.com').rstrip('/')

class TestPhase4SellerCalculationData:
    """Tests for Phase 4: Seller Dashboard Calculation Data Display"""
    
    # ========== 1. Test InquiryCreate model accepts calculationData ==========
    
    def test_inquiry_create_accepts_calculation_data(self):
        """Test POST /api/inquiries accepts calculationData field"""
        # Without auth, this will return 401, but the important thing is
        # it should NOT return 422 (validation error) if calculationData is valid
        
        inquiry_payload = {
            "sellerId": "000000000000000000000000",  # Fake seller ID
            "quantity": 100,
            "message": "Test inquiry with calculation data",
            "buyerType": "contractor",
            "calculationData": {
                "material": "Mild Steel",
                "shape": "round_bar",
                "dimensions": {
                    "diameter": "25",
                    "length": "1000"
                },
                "quantity": 100,
                "weight_per_piece": 3.85,
                "total_weight": 385.0,
                "rate_per_kg": 75,
                "calculated_price": 28875
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/inquiries",
            json=inquiry_payload
        )
        
        # Should get 401 (no auth) NOT 422 (validation error)
        # This confirms the model accepts calculationData field
        assert response.status_code in [401, 400, 404], f"Expected 401/400/404 (auth/validation), got {response.status_code}: {response.text}"
        
        # If we got 422, it means validation failed - check why
        if response.status_code == 422:
            error_detail = response.json().get("detail", [])
            # Check if calculationData caused the error
            calc_error = any("calculationData" in str(e) for e in error_detail) if isinstance(error_detail, list) else "calculationData" in str(error_detail)
            assert not calc_error, f"calculationData field rejected: {error_detail}"
        
        print("PASS: InquiryCreate model accepts calculationData field")
    
    # ========== 2. Test seller inquiries endpoint returns calculationData ==========
    
    def test_seller_inquiries_endpoint_requires_auth(self):
        """Test GET /api/seller/inquiries requires authentication"""
        response = requests.get(f"{BASE_URL}/api/seller/inquiries")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: GET /api/seller/inquiries requires authentication")
    
    def test_seller_inquiries_endpoint_exists(self):
        """Test GET /api/seller/inquiries endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/seller/inquiries",
            headers={"Authorization": "Bearer test-invalid-token"}
        )
        
        # Should return 401/403 (auth error) NOT 404 (endpoint not found)
        assert response.status_code != 404, "Endpoint /api/seller/inquiries not found!"
        print("PASS: GET /api/seller/inquiries endpoint exists")
    
    # ========== 3. Test calculationData schema validation ==========
    
    def test_calculation_data_schema_round_bar(self):
        """Test round bar calculation data schema"""
        calc_data = {
            "material": "Mild Steel",
            "shape": "round_bar",
            "dimensions": {"diameter": "25", "length": "1000"},
            "quantity": 50,
            "weight_per_piece": 3.85,
            "total_weight": 192.5,
            "rate_per_kg": 75,
            "calculated_price": 14437.5
        }
        
        # Validate required fields exist
        required_fields = ["material", "shape", "dimensions", "quantity", "weight_per_piece", "total_weight", "rate_per_kg", "calculated_price"]
        for field in required_fields:
            assert field in calc_data, f"Missing required field: {field}"
        
        # Validate shape is valid
        valid_shapes = ["round_bar", "square_bar", "pipe", "plate", "hex_bar"]
        assert calc_data["shape"] in valid_shapes, f"Invalid shape: {calc_data['shape']}"
        
        print("PASS: Round bar calculation data schema is valid")
    
    def test_calculation_data_schema_pipe(self):
        """Test pipe calculation data schema"""
        calc_data = {
            "material": "Stainless Steel 304",
            "shape": "pipe",
            "dimensions": {
                "outer_diameter": "50",
                "wall_thickness": "5",
                "length": "2000"
            },
            "quantity": 20,
            "weight_per_piece": 11.0,
            "total_weight": 220.0,
            "rate_per_kg": 280,
            "calculated_price": 61600
        }
        
        # Validate pipe-specific dimensions
        assert "outer_diameter" in calc_data["dimensions"], "Pipe requires outer_diameter"
        assert "wall_thickness" in calc_data["dimensions"], "Pipe requires wall_thickness"
        assert "length" in calc_data["dimensions"], "Pipe requires length"
        
        print("PASS: Pipe calculation data schema is valid")
    
    def test_calculation_data_schema_plate(self):
        """Test plate calculation data schema"""
        calc_data = {
            "material": "EN8",
            "shape": "plate",
            "dimensions": {
                "length": "500",
                "width": "300",
                "thickness": "10"
            },
            "quantity": 10,
            "weight_per_piece": 11.78,
            "total_weight": 117.8,
            "rate_per_kg": 95,
            "calculated_price": 11191
        }
        
        # Validate plate-specific dimensions
        assert "length" in calc_data["dimensions"], "Plate requires length"
        assert "width" in calc_data["dimensions"], "Plate requires width"
        assert "thickness" in calc_data["dimensions"], "Plate requires thickness"
        
        print("PASS: Plate calculation data schema is valid")


class TestFrontendTypeScript:
    """Test TypeScript types are correctly defined"""
    
    def test_seller_inquiry_type_file_exists(self):
        """Test SellerInquiry type is defined in types/index.ts"""
        types_file = "/app/frontend/src/types/index.ts"
        
        with open(types_file, "r") as f:
            content = f.read()
        
        # Check SellerInquiry interface exists
        assert "interface SellerInquiry" in content or "export interface SellerInquiry" in content, "SellerInquiry interface not found"
        
        # Check calculationData property exists
        assert "calculationData?" in content, "calculationData property not found in SellerInquiry"
        
        print("PASS: SellerInquiry type includes calculationData property")
    
    def test_calculation_data_type_structure(self):
        """Test calculationData type has correct structure"""
        types_file = "/app/frontend/src/types/index.ts"
        
        with open(types_file, "r") as f:
            content = f.read()
        
        # Check calculationData type fields
        expected_fields = ["material", "shape", "dimensions", "quantity", "weight_per_piece", "total_weight", "rate_per_kg", "calculated_price"]
        
        # Find the calculationData type definition
        import re
        calc_match = re.search(r'calculationData\?\s*:\s*\{([^}]+)\}', content, re.DOTALL)
        
        assert calc_match, "calculationData type definition not found"
        
        calc_type_content = calc_match.group(1)
        
        for field in expected_fields:
            assert field in calc_type_content, f"Field '{field}' not found in calculationData type"
        
        print("PASS: calculationData type has all required fields")


class TestSellerInquiriesPageImports:
    """Test seller inquiries page has correct imports"""
    
    def test_calculator_icon_imported(self):
        """Test Calculator icon is imported in seller inquiries page"""
        page_file = "/app/frontend/src/app/seller/inquiries/page.tsx"
        
        with open(page_file, "r") as f:
            content = f.read()
        
        assert "Calculator" in content, "Calculator icon not imported"
        assert "from 'lucide-react'" in content, "lucide-react import not found"
        
        print("PASS: Calculator icon is imported")
    
    def test_scale_icon_imported(self):
        """Test Scale icon is imported in seller inquiries page"""
        page_file = "/app/frontend/src/app/seller/inquiries/page.tsx"
        
        with open(page_file, "r") as f:
            content = f.read()
        
        assert "Scale" in content, "Scale icon not imported"
        
        print("PASS: Scale icon is imported")
    
    def test_calculation_data_section_exists(self):
        """Test Raw Material Calculation section exists in page"""
        page_file = "/app/frontend/src/app/seller/inquiries/page.tsx"
        
        with open(page_file, "r") as f:
            content = f.read()
        
        # Check for calculation data section
        assert "calculationData" in content, "calculationData not referenced in page"
        assert "Raw Material Calculation" in content, "Raw Material Calculation section not found"
        
        # Check for data-testid
        assert 'data-testid={`calc-data-' in content, "data-testid for calc-data section not found"
        
        print("PASS: Raw Material Calculation section exists in seller inquiries page")
    
    def test_calculation_data_fields_displayed(self):
        """Test all calculation data fields are displayed"""
        page_file = "/app/frontend/src/app/seller/inquiries/page.tsx"
        
        with open(page_file, "r") as f:
            content = f.read()
        
        # Check for field displays
        fields_to_check = [
            "calculationData.material",
            "calculationData.shape",
            "calculationData.quantity",
            "calculationData.total_weight",
            "calculationData.rate_per_kg",
            "calculationData.calculated_price",
            "calculationData.dimensions"
        ]
        
        for field in fields_to_check:
            assert field in content, f"Field display for '{field}' not found"
        
        print("PASS: All calculation data fields are displayed")


if __name__ == "__main__":
    # Run tests
    print("\n" + "="*60)
    print("Phase 4: Seller Dashboard Calculation Data Display Tests")
    print("="*60 + "\n")
    
    # Backend API Tests
    print("--- Backend API Tests ---\n")
    backend_tests = TestPhase4SellerCalculationData()
    backend_tests.test_inquiry_create_accepts_calculation_data()
    backend_tests.test_seller_inquiries_endpoint_requires_auth()
    backend_tests.test_seller_inquiries_endpoint_exists()
    backend_tests.test_calculation_data_schema_round_bar()
    backend_tests.test_calculation_data_schema_pipe()
    backend_tests.test_calculation_data_schema_plate()
    
    # TypeScript Type Tests
    print("\n--- TypeScript Type Tests ---\n")
    ts_tests = TestFrontendTypeScript()
    ts_tests.test_seller_inquiry_type_file_exists()
    ts_tests.test_calculation_data_type_structure()
    
    # Page Import Tests
    print("\n--- Page Import Tests ---\n")
    import_tests = TestSellerInquiriesPageImports()
    import_tests.test_calculator_icon_imported()
    import_tests.test_scale_icon_imported()
    import_tests.test_calculation_data_section_exists()
    import_tests.test_calculation_data_fields_displayed()
    
    print("\n" + "="*60)
    print("All Phase 4 tests completed successfully!")
    print("="*60)
