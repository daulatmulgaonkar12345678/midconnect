"""
Product Type Architecture Tests
================================
Tests for the product_type field that differentiates between:
- 'raw_material' products (calculator + RawMaterialSellerCard with ₹/kg pricing)
- 'standard_product' products (filters + StandardSellerCard with ₹/piece pricing)

Test Products:
- Standard: industrial-electric-motor-5hp-test-category-supplier-india
- Raw Material: ss304-round-bar-steel-raw-materials-supplier-india
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com')


class TestProductTypeAPI:
    """Tests for product_type field in enterprise product API responses"""
    
    def test_standard_product_returns_standard_product_type(self):
        """Standard product should return product_type='standard_product'"""
        response = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "product" in data
        assert data["product"].get("product_type") == "standard_product"
        print(f"Standard product type: {data['product'].get('product_type')}")
    
    def test_raw_material_returns_raw_material_type(self):
        """Raw material product should return product_type='raw_material'"""
        response = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "product" in data
        assert data["product"].get("product_type") == "raw_material"
        print(f"Raw material product type: {data['product'].get('product_type')}")
    
    def test_standard_product_has_sellers(self):
        """Standard product should have seller data"""
        response = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "sellers" in data
        assert len(data["sellers"]) >= 1
        
        # Check seller structure for standard product
        seller = data["sellers"][0]
        assert "pricingTiers" in seller
        assert "lowestPrice" in seller
        print(f"Standard product seller count: {len(data['sellers'])}")
    
    def test_raw_material_has_sellers(self):
        """Raw material product should have seller data"""
        response = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "sellers" in data
        assert len(data["sellers"]) >= 1
        print(f"Raw material seller count: {len(data['sellers'])}")
    
    def test_standard_product_has_facets(self):
        """Standard product should have filterable facets"""
        response = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/facets"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "facets" in data
        # Standard product should have spec-based facets
        print(f"Standard product facets: {list(data.get('facets', {}).keys())}")
    
    def test_raw_material_has_linked_calculator(self):
        """Raw material product's category should have a linked calculator"""
        # First get the product to find its category
        response = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        category_id = data["product"].get("categoryId")
        assert category_id is not None
        
        # Check if calculator exists for this category
        calc_response = requests.get(
            f"{BASE_URL}/api/calculator/calculators/by-category/{category_id}"
        )
        # Calculator should exist for raw material category
        assert calc_response.status_code == 200
        
        calc_data = calc_response.json()
        assert "name" in calc_data
        print(f"Calculator for raw material: {calc_data.get('name')}")
    
    def test_product_type_field_always_present(self):
        """product_type field should always be present in API response"""
        # Test standard product
        response1 = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/enterprise"
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert "product_type" in data1["product"], "product_type missing from standard product"
        
        # Test raw material
        response2 = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert "product_type" in data2["product"], "product_type missing from raw material"


class TestProductTypeNoOverlap:
    """Tests to ensure no overlap between product types"""
    
    def test_standard_product_is_not_raw_material(self):
        """Standard product should NOT be raw_material type"""
        response = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        product_type = data["product"].get("product_type")
        assert product_type != "raw_material"
        assert product_type == "standard_product"
    
    def test_raw_material_is_not_standard(self):
        """Raw material should NOT be standard_product type"""
        response = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        product_type = data["product"].get("product_type")
        assert product_type != "standard_product"
        assert product_type == "raw_material"


class TestPricingUnits:
    """Tests for pricing unit expectations"""
    
    def test_standard_product_pricing_per_piece(self):
        """Standard product sellers should have per-piece pricing in pricingTiers"""
        response = requests.get(
            f"{BASE_URL}/api/products/industrial-electric-motor-5hp-test-category-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        sellers = data.get("sellers", [])
        assert len(sellers) > 0
        
        seller = sellers[0]
        assert "pricingTiers" in seller
        assert len(seller["pricingTiers"]) > 0
        # Standard products have pricePerUnit in INR
        tier = seller["pricingTiers"][0]
        assert "pricePerUnit" in tier
        assert tier["pricePerUnit"] > 0
        print(f"Standard product price per piece: ₹{tier['pricePerUnit']}")
    
    def test_raw_material_sellers_have_rates(self):
        """Raw material product should have sellers with rate_per_unit for calculator"""
        # Get product ID first
        response = requests.get(
            f"{BASE_URL}/api/products/ss304-round-bar-steel-raw-materials-supplier-india/enterprise"
        )
        assert response.status_code == 200
        
        data = response.json()
        product_id = data["product"].get("_id")
        assert product_id is not None
        
        # Get sellers with rates
        sellers_response = requests.get(
            f"{BASE_URL}/api/calculator/sellers-by-product/{product_id}"
        )
        assert sellers_response.status_code == 200
        
        sellers = sellers_response.json()
        assert isinstance(sellers, list)
        if len(sellers) > 0:
            seller = sellers[0]
            # Raw material sellers should have rate_per_unit (₹/kg) and rate_unit
            assert "rate_per_unit" in seller
            assert "rate_unit" in seller
            assert seller["rate_unit"] == "kg"
            print(f"Raw material seller rate: ₹{seller.get('rate_per_unit')}/{seller.get('rate_unit')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
