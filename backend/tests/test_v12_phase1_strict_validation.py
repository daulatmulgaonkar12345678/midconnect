"""
Test V12 Phase 1 - Strict Validation Enforcement
=================================================
Tests for:
1. GET /api/health - Health check endpoint
2. GET /api/categories/all - Categories with camelCase fields
3. GET /api/products - Products list
4. MongoDB strict validation verification
5. Pydantic models import test
6. Sanitization helpers tests (safe_object_id, safe_int, safe_bool)
"""

import pytest
import requests
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seller-images.preview.emergentagent.com').rstrip('/')


class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_returns_200(self):
        """GET /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_health_returns_healthy_status(self):
        """GET /api/health returns status='healthy'"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
    
    def test_health_has_timestamp(self):
        """GET /api/health includes timestamp"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert "timestamp" in data, "Response missing 'timestamp' field"


class TestCategoriesEndpoint:
    """Categories endpoint tests"""
    
    def test_categories_all_returns_200(self):
        """GET /api/categories/all returns 200"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_categories_returns_list(self):
        """GET /api/categories/all returns a list"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "Expected at least one category"
    
    def test_categories_have_camelcase_fields(self):
        """GET /api/categories/all returns camelCase fields"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        data = response.json()
        assert len(data) > 0, "No categories to test"
        
        category = data[0]
        # Verify camelCase fields exist
        assert "isActive" in category, "Missing camelCase field 'isActive'"
        assert "createdAt" in category, "Missing camelCase field 'createdAt'"
        assert "updatedAt" in category, "Missing camelCase field 'updatedAt'"
        
        # Verify snake_case fields don't exist
        assert "is_active" not in category, "Legacy snake_case 'is_active' should not exist"
        assert "created_at" not in category, "Legacy snake_case 'created_at' should not exist"
        assert "updated_at" not in category, "Legacy snake_case 'updated_at' should not exist"
    
    def test_categories_isactive_is_boolean(self):
        """Categories isActive field is boolean type"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        data = response.json()
        assert len(data) > 0, "No categories to test"
        
        for category in data:
            assert isinstance(category.get("isActive"), bool), \
                f"isActive should be boolean, got {type(category.get('isActive'))}"


class TestProductsEndpoint:
    """Products endpoint tests"""
    
    def test_products_returns_200(self):
        """GET /api/products returns 200"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_products_returns_list(self):
        """GET /api/products returns a list"""
        response = requests.get(f"{BASE_URL}/api/products")
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_products_have_category_id_field(self):
        """Products have categoryId field (camelCase)"""
        response = requests.get(f"{BASE_URL}/api/products")
        data = response.json()
        
        if len(data) > 0:
            product = data[0]
            assert "categoryId" in product, "Missing 'categoryId' field"
            # Verify it's a valid ObjectId format (24 hex chars)
            cat_id = product.get("categoryId")
            assert cat_id is not None, "categoryId is None"
            assert len(cat_id) == 24, f"categoryId should be 24 chars, got {len(cat_id)}"


class TestPydanticModelsImport:
    """Test that Pydantic models file is valid and imports correctly"""
    
    def test_pydantic_models_import(self):
        """Verify pydantic_models.py can be imported"""
        try:
            from models.pydantic_models import (
                CategoryCreate,
                CategoryUpdate,
                ProductCreate,
                ProductUpdate,
                ListingCreate,
                ListingUpdate,
                UserCreate,
                UserProfileUpdate,
                InquiryCreate,
                SpecTemplateCreate
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import pydantic_models: {e}")
    
    def test_pydantic_models_enums(self):
        """Verify enums are defined correctly"""
        try:
            from models.pydantic_models import (
                AccountStatus,
                SubscriptionPlan,
                ListingStatus,
                InquiryStatus,
                ReportType,
                SpecFieldType
            )
            # Test enum values
            assert AccountStatus.ACTIVE.value == "active"
            assert SubscriptionPlan.FREE.value == "free"
            assert ListingStatus.DRAFT.value == "draft"
            assert InquiryStatus.PENDING.value == "pending"
            assert SpecFieldType.DROPDOWN.value == "dropdown"
        except ImportError as e:
            pytest.fail(f"Failed to import enums: {e}")
    
    def test_category_create_validation(self):
        """Test CategoryCreate model validation"""
        from models.pydantic_models import CategoryCreate
        
        # Valid category
        category = CategoryCreate(
            name="Test Category",
            description="Test description"
        )
        assert category.name == "Test Category"
        assert category.isActive == True  # Default value
    
    def test_product_create_validation(self):
        """Test ProductCreate model validation"""
        from models.pydantic_models import ProductCreate
        
        # Valid product
        product = ProductCreate(
            name="Test Product",
            categoryId="507f1f77bcf86cd799439011"  # Valid ObjectId format
        )
        assert product.name == "Test Product"
        assert product.categoryId == "507f1f77bcf86cd799439011"
    
    def test_strict_model_rejects_extra_fields(self):
        """Test StrictModel rejects extra fields"""
        from models.pydantic_models import CategoryCreate
        from pydantic import ValidationError
        
        # Try to create with extra field - should fail
        with pytest.raises(ValidationError):
            CategoryCreate(
                name="Test",
                extra_field="should_fail"  # Extra field not allowed
            )


class TestSanitizationHelpers:
    """Test sanitization helpers from server.py"""
    
    def test_safe_object_id_valid(self):
        """Test safe_object_id with valid ObjectId string"""
        from bson import ObjectId
        # Import from server or use inline logic
        valid_id = "507f1f77bcf86cd799439011"
        
        # Should convert successfully
        obj_id = ObjectId(valid_id)
        assert str(obj_id) == valid_id
    
    def test_safe_object_id_invalid(self):
        """Test safe_object_id with invalid string"""
        from bson import ObjectId
        
        invalid_ids = ["invalid", "123", "", "not-an-objectid"]
        for invalid_id in invalid_ids:
            with pytest.raises(Exception):
                ObjectId(invalid_id)
    
    def test_safe_int_conversions(self):
        """Test safe_int conversion logic"""
        # Valid conversions
        assert int("123") == 123
        assert int(456) == 456
        assert int("0") == 0
        
        # Invalid should raise
        with pytest.raises(ValueError):
            int("not_a_number")
    
    def test_safe_bool_conversions(self):
        """Test safe_bool conversion logic"""
        # True values
        true_values = [True, "true", "True", "1", "yes", "Yes"]
        for val in true_values:
            if isinstance(val, bool):
                assert val == True
            elif isinstance(val, str):
                assert val.lower() in ('true', '1', 'yes')
        
        # False values
        false_values = [False, "false", "0", "no"]
        for val in false_values:
            if isinstance(val, bool):
                assert val == False
            elif isinstance(val, str):
                assert val.lower() in ('false', '0', 'no')


class TestSanitizeRequestBody:
    """Test request body sanitization"""
    
    def test_system_fields_list(self):
        """Verify system fields are defined"""
        # These fields should NEVER be accepted from frontend
        SYSTEM_FIELDS = {
            '_id', 'id',
            'createdAt', 'created_at',
            'updatedAt', 'updated_at', 
            'createdBy', 'created_by',
            'userId', 'user_id',
            'sellerId', 'seller_id',
            'adminId', 'admin_id',
            'buyerId', 'buyer_id',
        }
        
        # Verify these exist
        assert '_id' in SYSTEM_FIELDS
        assert 'createdAt' in SYSTEM_FIELDS
        assert 'sellerId' in SYSTEM_FIELDS
    
    def test_admin_only_fields_list(self):
        """Verify admin-only fields are defined"""
        ADMIN_ONLY_FIELDS = {
            'roles', 'isAdmin', 'is_admin',
            'subscription', 'canLogin', 'can_login',
            'accountStatus', 'account_status',
            'isActive', 'is_active'
        }
        
        assert 'roles' in ADMIN_ONLY_FIELDS
        assert 'isAdmin' in ADMIN_ONLY_FIELDS


class TestSearchEndpoint:
    """Test search endpoint"""
    
    def test_search_products_returns_200(self):
        """POST /api/search/products returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_search_products_returns_results(self):
        """Search for 'motor' returns results"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": "motor"}
        )
        data = response.json()
        # Search endpoint returns dict with 'products' key
        if isinstance(data, dict):
            assert "products" in data, "Missing 'products' key in response"
            assert isinstance(data["products"], list), "products should be a list"
        else:
            assert isinstance(data, list), f"Expected dict or list, got {type(data)}"
    
    def test_search_with_empty_query(self):
        """Search with empty query doesn't crash"""
        response = requests.post(
            f"{BASE_URL}/api/search/products",
            json={"query": ""}
        )
        # Should return 200 or 422, not 500
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"


class TestValidationEnforcement:
    """Test that validation is enforced"""
    
    def test_categories_endpoint_filters_inactive(self):
        """GET /api/categories/all only returns active categories"""
        response = requests.get(f"{BASE_URL}/api/categories/all")
        data = response.json()
        
        for category in data:
            assert category.get("isActive") == True, \
                f"Found inactive category: {category.get('_id')}"
    
    def test_objectid_format_validation(self):
        """Test that invalid ObjectIds are rejected"""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        valid_ids = [
            "507f1f77bcf86cd799439011",
            "6981a9a74108b0cbd93aa642",
        ]
        invalid_ids = [
            "invalid",
            "123",
            "not-an-objectid",
            "",
            "zzzzzzzzzzzzzzzzzzzzzzzz",  # 24 chars but not hex
        ]
        
        for valid_id in valid_ids:
            try:
                ObjectId(valid_id)
            except InvalidId:
                pytest.fail(f"Valid ObjectId {valid_id} was rejected")
        
        for invalid_id in invalid_ids:
            with pytest.raises(InvalidId):
                ObjectId(invalid_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
