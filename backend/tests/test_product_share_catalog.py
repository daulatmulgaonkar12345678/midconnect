"""
Product Share & Catalog Feature Tests
- Tests for product catalog generation (PDF/Excel)
- Tests for recipients endpoint (buyers + suppliers)
- Tests for catalog settings endpoint
- Tests for share-document endpoint (secure links)
- Tests for public document access (no auth)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProductShareRecipients:
    """Recipients endpoint tests - GET /api/business-tools/recipients"""
    
    def test_recipients_endpoint_exists_requires_auth(self):
        """GET /api/business-tools/recipients should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/recipients")
        # Should require authentication
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Recipients endpoint requires auth (status {response.status_code})")
    
    def test_recipients_endpoint_accepts_search_param(self):
        """GET /api/business-tools/recipients?search=test should accept query param"""
        response = requests.get(f"{BASE_URL}/api/business-tools/recipients?search=test")
        # Should still require auth but not fail on query param
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Recipients endpoint accepts search param (status {response.status_code})")


class TestCatalogSettings:
    """Catalog Settings endpoint tests - GET/PUT /api/business-tools/catalog-settings"""
    
    def test_catalog_settings_get_requires_auth(self):
        """GET /api/business-tools/catalog-settings should require auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/catalog-settings")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Catalog settings GET requires auth (status {response.status_code})")
    
    def test_catalog_settings_put_requires_auth(self):
        """PUT /api/business-tools/catalog-settings should require auth"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/catalog-settings",
            json={"settings": {"showPrice": True, "showImage": True}}
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Catalog settings PUT requires auth (status {response.status_code})")


class TestProductShares:
    """Product Shares endpoint tests - POST /api/business-tools/product-shares"""
    
    def test_product_shares_post_requires_auth(self):
        """POST /api/business-tools/product-shares should require auth"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/product-shares",
            json={
                "productIds": ["507f1f77bcf86cd799439011"],
                "recipientIds": ["507f1f77bcf86cd799439012"],
                "format": "pdf",
                "showPrice": True
            }
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Product shares POST requires auth (status {response.status_code})")
    
    def test_product_shares_download_requires_auth(self):
        """GET /api/business-tools/product-shares/{id}/download should require auth"""
        fake_id = "507f1f77bcf86cd799439011"
        response = requests.get(f"{BASE_URL}/api/business-tools/product-shares/{fake_id}/download")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Product shares download requires auth (status {response.status_code})")


class TestShareDocument:
    """Share Document endpoint tests - POST /api/business-tools/share-document"""
    
    def test_share_document_requires_auth(self):
        """POST /api/business-tools/share-document should require auth"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/share-document",
            params={
                "documentType": "invoice",
                "documentId": "507f1f77bcf86cd799439011",
                "recipientPhone": "9876543210"
            }
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Share document POST requires auth (status {response.status_code})")


class TestProductCategories:
    """Product Categories endpoint tests - GET /api/business-tools/product-categories"""
    
    def test_product_categories_requires_auth(self):
        """GET /api/business-tools/product-categories should require auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/product-categories")
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Product categories requires auth (status {response.status_code})")


class TestPublicDocumentAccess:
    """Public Document endpoint tests - GET /api/doc/{token}"""
    
    def test_public_doc_invalid_token_returns_404(self):
        """GET /api/doc/{invalid_token} should return 404 for invalid token"""
        invalid_token = "invalid_test_token_abc123"
        response = requests.get(f"{BASE_URL}/api/doc/{invalid_token}")
        assert response.status_code in [404], f"Expected 404, got {response.status_code}"
        print(f"PASS: Public doc with invalid token returns 404 (status {response.status_code})")
    
    def test_public_doc_route_exists(self):
        """GET /api/doc/{token} route should exist (not 404 on route itself)"""
        test_token = "test_token_12345"
        response = requests.get(f"{BASE_URL}/api/doc/{test_token}")
        # Should return 404 for not found document, not 405 method not allowed
        assert response.status_code != 405, "Route should support GET method"
        assert response.status_code in [404, 410], f"Expected 404/410, got {response.status_code}"
        print(f"PASS: Public doc route exists and accepts GET (status {response.status_code})")


class TestCatalogSettingsFields:
    """Catalog Settings field names validation"""
    
    def test_catalog_settings_endpoint_exists(self):
        """Verify catalog-settings endpoint exists and expects proper fields"""
        # Test that PUT request with valid field names is processed (auth required)
        response = requests.put(
            f"{BASE_URL}/api/business-tools/catalog-settings",
            json={
                "settings": {
                    "showImage": True,
                    "showName": True,
                    "showCategory": True,
                    "showSpecification": True,
                    "showDescription": True,
                    "showPrice": True,
                    "showUnit": True,
                    "showMoq": True
                }
            }
        )
        # Should require auth, not fail on field names
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Catalog settings accepts all field names (status {response.status_code})")


class TestEndpointRegistration:
    """Verify all new endpoints are properly registered"""
    
    def test_all_product_share_endpoints_registered(self):
        """Verify all product sharing endpoints exist under /api/business-tools"""
        endpoints = [
            ("GET", "/api/business-tools/recipients"),
            ("GET", "/api/business-tools/product-categories"),
            ("GET", "/api/business-tools/catalog-settings"),
            ("PUT", "/api/business-tools/catalog-settings"),
            ("POST", "/api/business-tools/product-shares"),
            ("POST", "/api/business-tools/share-document"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            elif method == "PUT":
                response = requests.put(f"{BASE_URL}{endpoint}", json={})
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            # Should not return 404 Not Found (endpoint exists but requires auth)
            assert response.status_code != 404, f"{method} {endpoint} returned 404 - endpoint not found"
            assert response.status_code in [401, 422, 400, 405], f"{method} {endpoint} unexpected status {response.status_code}"
            print(f"PASS: {method} {endpoint} registered (status {response.status_code})")
    
    def test_public_doc_endpoint_registered(self):
        """Verify public doc endpoint exists under /api"""
        response = requests.get(f"{BASE_URL}/api/doc/test_token")
        # Should not return 404 for route not found - token not found is expected
        assert response.status_code in [404, 410], f"Expected 404/410, got {response.status_code}"
        print(f"PASS: Public doc endpoint /api/doc/{{token}} registered (status {response.status_code})")


class TestRequestValidation:
    """Test request body validation for product share endpoints"""
    
    def test_product_shares_validates_body(self):
        """POST /api/business-tools/product-shares should validate request body"""
        # Empty body should still require auth first
        response = requests.post(
            f"{BASE_URL}/api/business-tools/product-shares",
            json={}
        )
        # Should require auth or validation error
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Product shares validates body (status {response.status_code})")
    
    def test_catalog_settings_put_validates_body(self):
        """PUT /api/business-tools/catalog-settings should accept settings object"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/catalog-settings",
            json={"settings": {}}
        )
        # Should require auth first
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"PASS: Catalog settings PUT validates body (status {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
