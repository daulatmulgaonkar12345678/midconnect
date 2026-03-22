"""
Enterprise Product Page P0 Fix Tests
=====================================

Tests for the P0 fix addressing:
1. Product images fallback (images -> coverImageUrl -> imageUrl)
2. Seller images fallback (images -> imageUrl -> image)
3. searchableAttributes fallback (searchableAttributes -> technicalSpecs)
4. POST /filter endpoint with sortBy=ranking

Test product ID: 699be9023cbe1a8c31591668
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com')

class TestEnterpriseProductEndpoint:
    """Tests for GET /api/products/{id}/enterprise endpoint"""
    
    def test_enterprise_endpoint_returns_200(self):
        """Test that enterprise endpoint returns 200 for valid product"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        assert "product" in data
        assert "sellers" in data
        assert "summary" in data
        print(f"✅ Enterprise endpoint returns 200")
    
    def test_product_images_array_populated(self):
        """Test that product.images array is populated with fallbacks"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        product = data["product"]
        
        # Check images array exists and is not empty
        assert "images" in product, "product.images field missing"
        assert isinstance(product["images"], list), "product.images should be a list"
        assert len(product["images"]) > 0, "product.images should not be empty"
        
        # Verify first image is a valid URL
        first_image = product["images"][0]
        assert first_image.startswith("http"), f"Image should be URL, got: {first_image}"
        print(f"✅ Product images: {product['images'][:2]}")
    
    def test_seller_images_array_populated(self):
        """Test that seller.images array is populated with fallbacks"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Should have at least one seller"
        
        for seller in sellers:
            assert "images" in seller, f"Seller {seller['listingId']} missing images field"
            assert isinstance(seller["images"], list), "seller.images should be a list"
            # Images can be empty but should be a list
            if len(seller["images"]) > 0:
                assert seller["images"][0].startswith("http"), "Seller image should be URL"
                print(f"✅ Seller images for {seller['listingId']}: {seller['images'][:1]}")
    
    def test_seller_searchable_attributes_populated(self):
        """Test that seller.searchableAttributes is populated with fallbacks"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Should have at least one seller"
        
        for seller in sellers:
            assert "searchableAttributes" in seller, f"Seller {seller['listingId']} missing searchableAttributes"
            attrs = seller["searchableAttributes"]
            assert isinstance(attrs, dict), "searchableAttributes should be a dict"
            
            # Check for expected attributes (power, voltage, phase, rpm, efficiency)
            expected_attrs = ["power", "voltage", "phase", "rpm", "efficiency"]
            for attr in expected_attrs:
                assert attr in attrs, f"Missing attribute: {attr}"
            
            print(f"✅ Seller searchableAttributes: {list(attrs.keys())}")
    
    def test_seller_attribute_labels_populated(self):
        """Test that seller.attributeLabels is populated"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Should have at least one seller"
        
        for seller in sellers:
            assert "attributeLabels" in seller, f"Seller missing attributeLabels"
            labels = seller["attributeLabels"]
            assert isinstance(labels, dict), "attributeLabels should be a dict"
            print(f"✅ Seller attributeLabels: {labels}")
    
    def test_seller_pricing_data(self):
        """Test that seller pricing tiers are populated"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Should have at least one seller"
        
        for seller in sellers:
            assert "pricingTiers" in seller, "Seller missing pricingTiers"
            assert "lowestPrice" in seller, "Seller missing lowestPrice"
            
            pricing = seller["pricingTiers"]
            assert isinstance(pricing, list), "pricingTiers should be a list"
            assert len(pricing) > 0, "Should have at least one pricing tier"
            
            for tier in pricing:
                assert "minQty" in tier, "Tier missing minQty"
                assert "pricePerUnit" in tier, "Tier missing pricePerUnit"
            
            print(f"✅ Seller pricing tiers: {len(pricing)} tiers, lowest: {seller['lowestPrice']}")
    
    def test_seller_role_badge(self):
        """Test that seller role (manufacturer/dealer) is populated"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        sellers = data["sellers"]
        
        assert len(sellers) > 0, "Should have at least one seller"
        
        for seller in sellers:
            assert "sellerRole" in seller, "Seller missing sellerRole"
            valid_roles = ["manufacturer", "dealer", "distributor", "wholesaler", "retailer"]
            assert seller["sellerRole"] in valid_roles, f"Invalid seller role: {seller['sellerRole']}"
            print(f"✅ Seller role: {seller['sellerRole']}")
    
    def test_summary_stats(self):
        """Test that summary stats are populated"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        
        assert "sellerCount" in summary
        assert "variantCount" in summary
        assert "minPrice" in summary
        assert "totalPages" in summary
        
        assert isinstance(summary["sellerCount"], int)
        assert summary["sellerCount"] >= 0
        
        print(f"✅ Summary: {summary['sellerCount']} sellers, {summary['variantCount']} variants, min price: {summary['minPrice']}")
    
    def test_available_facets(self):
        """Test that availableFacets are populated for filtering"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/enterprise")
        
        assert response.status_code == 200
        data = response.json()
        facets = data["availableFacets"]
        
        assert isinstance(facets, dict), "availableFacets should be a dict"
        
        # Check for expected facet keys
        expected_facets = ["power", "voltage", "phase", "rpm", "efficiency"]
        for facet in expected_facets:
            assert facet in facets, f"Missing facet: {facet}"
            assert isinstance(facets[facet], list), f"Facet {facet} values should be list"
        
        print(f"✅ Available facets: {list(facets.keys())}")


class TestFacetsEndpoint:
    """Tests for GET /api/products/{id}/facets endpoint"""
    
    def test_facets_endpoint_returns_200(self):
        """Test that facets endpoint returns 200"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/facets")
        
        assert response.status_code == 200
        data = response.json()
        assert "productId" in data
        assert "facets" in data
        assert "totalListings" in data
        print(f"✅ Facets endpoint returns 200")
    
    def test_facets_include_metadata(self):
        """Test that facets include metadata (label, fieldType)"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.get(f"{BASE_URL}/api/products/{product_id}/facets")
        
        assert response.status_code == 200
        data = response.json()
        facets = data["facets"]
        
        for key, facet_data in facets.items():
            assert "values" in facet_data, f"Facet {key} missing values"
            assert "count" in facet_data, f"Facet {key} missing count"
            assert "metadata" in facet_data, f"Facet {key} missing metadata"
            
            metadata = facet_data["metadata"]
            assert "label" in metadata, f"Facet {key} metadata missing label"
            assert "fieldType" in metadata, f"Facet {key} metadata missing fieldType"
            
            print(f"✅ Facet {key}: {len(facet_data['values'])} values, label: {metadata['label']}")


class TestFilterEndpoint:
    """Tests for POST /api/products/{id}/filter endpoint"""
    
    def test_filter_default_returns_200(self):
        """Test that filter endpoint with defaults returns 200"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={"page": 1, "limit": 20}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        print(f"✅ Filter endpoint returns 200, {data['total']} results")
    
    def test_filter_with_sort_by_ranking(self):
        """Test filter endpoint with sortBy=ranking"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={
                "sortBy": "ranking",
                "order": "desc",
                "page": 1,
                "limit": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "results" in data
        assert "sortedBy" in data
        assert data["sortedBy"] == "ranking"
        
        # Check that results have ranking score
        if len(data["results"]) > 0:
            first_result = data["results"][0]
            assert "rankingScore" in first_result, "Results should include rankingScore when sorted by ranking"
            assert isinstance(first_result["rankingScore"], (int, float)), "rankingScore should be numeric"
            print(f"✅ Ranking sort works, first result score: {first_result['rankingScore']}")
        else:
            print("✅ Ranking sort works (no results to check score)")
    
    def test_filter_with_sort_by_price(self):
        """Test filter endpoint with sortBy=price"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={
                "sortBy": "price",
                "order": "asc",
                "page": 1,
                "limit": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sortedBy"] == "price"
        print(f"✅ Price sort works")
    
    def test_filter_with_attributes(self):
        """Test filter endpoint with attribute filters"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={
                "attributes": {"voltage": "415V"},
                "page": 1,
                "limit": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "appliedFilters" in data
        assert data["appliedFilters"].get("voltage") == "415V"
        print(f"✅ Attribute filter works, applied: {data['appliedFilters']}")
    
    def test_filter_results_have_images_and_attributes(self):
        """Test that filter results include images and searchableAttributes"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={"page": 1, "limit": 20}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for result in data["results"]:
            assert "images" in result, "Result missing images"
            assert isinstance(result["images"], list), "images should be a list"
            
            assert "searchableAttributes" in result, "Result missing searchableAttributes"
            assert isinstance(result["searchableAttributes"], dict), "searchableAttributes should be a dict"
            
            assert "attributeLabels" in result, "Result missing attributeLabels"
            
            print(f"✅ Filter result {result['listingId']}: images={len(result['images'])}, attrs={len(result['searchableAttributes'])}")
    
    def test_filter_fallback_level(self):
        """Test that filter returns fallback level info"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={"page": 1, "limit": 20}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fallbackLevel" in data
        assert isinstance(data["fallbackLevel"], int)
        assert data["fallbackLevel"] >= 0
        
        if data["fallbackLevel"] > 0:
            assert "fallbackMessage" in data
        
        print(f"✅ Fallback level: {data['fallbackLevel']}")
    
    def test_filter_results_have_stock_status(self):
        """Test that filter results include stockStatus computed from stock value"""
        product_id = "699be9023cbe1a8c31591668"
        response = requests.post(
            f"{BASE_URL}/api/products/{product_id}/filter",
            json={"page": 1, "limit": 20}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for result in data["results"]:
            # Check stockStatus exists
            assert "stockStatus" in result, "Result missing stockStatus"
            
            # stockStatus should be string (in_stock, out_of_stock, limited)
            assert isinstance(result["stockStatus"], str), "stockStatus should be a string"
            assert result["stockStatus"] in ["in_stock", "out_of_stock", "limited"], \
                f"Invalid stockStatus: {result['stockStatus']}"
            
            # Verify stockStatus is computed correctly from stock value
            stock = result.get("stock", 0)
            if stock > 0:
                assert result["stockStatus"] == "in_stock", \
                    f"stockStatus should be in_stock when stock={stock}"
            else:
                assert result["stockStatus"] == "out_of_stock", \
                    f"stockStatus should be out_of_stock when stock={stock}"
            
            print(f"✅ Filter result stockStatus: {result['stockStatus']} (stock: {stock})")


class TestInvalidInputs:
    """Tests for error handling"""
    
    def test_invalid_product_id_enterprise(self):
        """Test enterprise endpoint with invalid product ID"""
        response = requests.get(f"{BASE_URL}/api/products/invalid-id/enterprise")
        assert response.status_code == 400
        print(f"✅ Invalid ID returns 400")
    
    def test_nonexistent_product_enterprise(self):
        """Test enterprise endpoint with non-existent product"""
        response = requests.get(f"{BASE_URL}/api/products/000000000000000000000000/enterprise")
        assert response.status_code == 404
        print(f"✅ Non-existent product returns 404")
    
    def test_invalid_product_id_filter(self):
        """Test filter endpoint with invalid product ID"""
        response = requests.post(
            f"{BASE_URL}/api/products/invalid-id/filter",
            json={"page": 1, "limit": 20}
        )
        assert response.status_code == 400
        print(f"✅ Invalid ID on filter returns 400")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
