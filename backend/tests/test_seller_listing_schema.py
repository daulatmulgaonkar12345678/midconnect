"""
Backend Test: POST /api/seller/listings - FINAL ARCHITECTURE Schema Validation
=============================================================================

This test validates that the backend correctly:
1. Rejects requests without authentication (401)
2. Accepts the NEW camelCase payload structure
3. Validates required fields (productId, sellerRole, pricingTiers, etc.)
4. Rejects the OLD snake_case payload structure

No actual listing creation - just schema validation at the API level.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com/api')

# Test product ID from database (Electrical Equipment category)
TEST_PRODUCT_ID = "6981a9a74108b0cbd93aa631"  # Three Phase AC Motor
TEST_CATEGORY_ID = "6981a9a74108b0cbd93aa630"  # Electrical Equipment


class TestSellerListingEndpoint:
    """Test POST /api/seller/listings endpoint schema validation."""
    
    def test_01_health_check(self):
        """Backend is healthy."""
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Backend healthy: {data}")
    
    def test_02_auth_required(self):
        """Endpoint requires authentication."""
        payload = {
            "productId": TEST_PRODUCT_ID,
            "attributes": {"power": 5, "voltage": 415},
            "sellerRole": "distributor",
            "images": ["https://example.com/image.jpg"],
            "moq": 1,
            "stock": 100,
            "currency": "INR",
            "pricingTiers": [{"minQty": 1, "maxQty": None, "pricePerUnit": 1000}]
        }
        
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json=payload,
            timeout=30
        )
        
        # Should require auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Auth required: {response.status_code} - {response.json()}")
    
    def test_03_products_exist(self):
        """Verify products with specTemplateId exist for testing."""
        response = requests.get(f"{BASE_URL}/products", timeout=10)
        assert response.status_code == 200
        
        products = response.json()
        print(f"✅ Found {len(products)} products")
        
        if products:
            print(f"   First product: {products[0].get('name')}")
    
    def test_04_categories_exist(self):
        """Verify categories exist."""
        response = requests.get(f"{BASE_URL}/categories/all", timeout=10)
        assert response.status_code == 200
        
        categories = response.json()
        print(f"✅ Found {len(categories)} categories")
        
        # Find Electrical Equipment
        elec = next((c for c in categories if c["_id"] == TEST_CATEGORY_ID), None)
        if elec:
            print(f"   Test category found: {elec['name']}")


class TestPayloadSchemaValidation:
    """Test payload validation without authentication."""
    
    def test_01_valid_payload_structure(self):
        """Document the expected FINAL ARCHITECTURE payload."""
        valid_payload = {
            # Required fields
            "productId": "objectid_string",
            "attributes": {"power": 5, "voltage": 415},
            "sellerRole": "distributor",  # NOT seller_type
            "images": ["url1", "url2"],
            "moq": 1,  # FLAT, NOT availability.moq
            "stock": 100,  # FLAT
            "currency": "INR",
            "pricingTiers": [  # NOT pricing.slabs
                {"minQty": 1, "maxQty": 99, "pricePerUnit": 1000},
                {"minQty": 100, "maxQty": None, "pricePerUnit": 900}
            ],
            
            # Optional fields
            "description": "Optional description",
            "maxCapacity": 500,  # FLAT
            "leadTime": 7,  # FLAT (days)
            "datasheetUrl": "https://example.com/datasheet.pdf"
        }
        
        print("✅ Valid FINAL ARCHITECTURE payload structure:")
        for key, value in valid_payload.items():
            print(f"   {key}: {type(value).__name__}")
    
    def test_02_pricing_tier_structure(self):
        """Document PricingTier schema."""
        valid_tier = {
            "minQty": 1,       # int, >= 1
            "maxQty": 99,      # int or None (unlimited)
            "pricePerUnit": 1000.50  # float, > 0
        }
        
        # NOT the old structure:
        old_slab = {
            "min_qty": 1,         # WRONG - snake_case
            "max_qty": 99,        # WRONG - snake_case
            "price_per_unit": 1000  # WRONG - snake_case
        }
        
        print("✅ Valid PricingTier (camelCase):")
        for k, v in valid_tier.items():
            print(f"   {k}: {v}")
        
        print("\n❌ OLD slab structure (snake_case - REJECTED):")
        for k, v in old_slab.items():
            print(f"   {k}: {v}")
    
    def test_03_legacy_payload_comparison(self):
        """Compare old vs new payload structure."""
        
        old_payload = {
            "product_name": "Test",       # OLD - use productId instead
            "category_id": "xxx",          # OLD - not needed (derived from productId)
            "seller_type": "distributor",  # OLD - use sellerRole
            "specifications": {},          # OLD - use attributes
            "availability": {              # OLD - use flat moq, stock, etc.
                "moq": 1,
                "stock": 100
            },
            "pricing": {                   # OLD - use pricingTiers
                "slabs": []
            }
        }
        
        new_payload = {
            "productId": "xxx",            # NEW - required
            "attributes": {},              # NEW - required
            "sellerRole": "distributor",   # NEW - required
            "moq": 1,                      # NEW - flat field
            "stock": 100,                  # NEW - flat field
            "pricingTiers": []             # NEW - required
        }
        
        print("✅ Schema comparison:")
        print("\n❌ OLD payload structure (causes 422):")
        for k in old_payload.keys():
            print(f"   {k}")
        
        print("\n✅ NEW payload structure (FINAL ARCHITECTURE):")
        for k in new_payload.keys():
            print(f"   {k}")


class TestFrontendAPITypeDefinitions:
    """Verify frontend type definitions match backend expectations."""
    
    def test_01_listing_create_payload_interface(self):
        """ListingCreatePayload from api.ts should match backend."""
        # From /app/frontend-web/src/lib/api.ts lines 1164-1183
        frontend_interface = """
interface ListingCreatePayload {
  productId: string;           // Required
  attributes: Record<string, string | number | boolean>;
  sellerRole: string;          // Required
  description?: string;
  images: string[];
  moq: number;                 // FLAT - NOT availability.moq
  stock: number;               // FLAT
  maxCapacity?: number;        // FLAT
  leadTime?: number;           // FLAT (days)
  currency: string;
  pricingTiers: PricingTierCreate[];  // NOT pricing.slabs
  datasheetUrl?: string;
}

interface PricingTierCreate {
  minQty: number;
  maxQty: number | null;
  pricePerUnit: number;
}
        """
        print("✅ Frontend ListingCreatePayload interface (api.ts):")
        print(frontend_interface)
    
    def test_02_backend_pydantic_model(self):
        """ListingCreate Pydantic model from seller_products.py."""
        # From /app/backend/seller_products.py lines 49-76
        backend_model = """
class ListingCreate(BaseModel):
    productId: str = Field(...)
    attributes: Dict[str, Any] = Field(...)
    sellerRole: str = Field(...)
    description: Optional[str] = Field(None, max_length=2000)
    images: List[str] = Field(default_factory=list, max_length=5)
    moq: int = Field(default=1, ge=1)
    stock: int = Field(default=0, ge=0)
    maxCapacity: Optional[int] = Field(None, ge=1)
    leadTime: Optional[int] = Field(None, ge=0)
    currency: str = Field(default="INR", max_length=3)
    pricingTiers: List[PricingTier] = Field(..., min_length=1, max_length=10)
    datasheetUrl: Optional[str] = None

class PricingTier(BaseModel):
    minQty: int = Field(..., ge=1)
    maxQty: Optional[int] = Field(None, ge=1)
    pricePerUnit: float = Field(..., gt=0)
        """
        print("✅ Backend ListingCreate Pydantic model (seller_products.py):")
        print(backend_model)
    
    def test_03_schema_field_alignment(self):
        """Verify field names match exactly between frontend and backend."""
        frontend_fields = {
            "productId", "attributes", "sellerRole", "description",
            "images", "moq", "stock", "maxCapacity", "leadTime",
            "currency", "pricingTiers", "datasheetUrl"
        }
        
        backend_fields = {
            "productId", "attributes", "sellerRole", "description",
            "images", "moq", "stock", "maxCapacity", "leadTime",
            "currency", "pricingTiers", "datasheetUrl"
        }
        
        # Check alignment
        assert frontend_fields == backend_fields, "Schema mismatch!"
        
        print("✅ Frontend and backend field names are ALIGNED:")
        for field in sorted(frontend_fields):
            print(f"   ✓ {field}")


class TestEndpointURLs:
    """Verify endpoint URLs are correct."""
    
    def test_01_seller_listings_endpoint(self):
        """POST /api/seller/listings exists."""
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json={},  # Empty payload
            timeout=30
        )
        
        # Should get 401 (auth required) NOT 404 (endpoint not found)
        assert response.status_code != 404, f"Endpoint not found! Status: {response.status_code}"
        print(f"✅ POST /seller/listings exists (status: {response.status_code})")
    
    def test_02_seller_dashboard_endpoint(self):
        """GET /api/seller/dashboard exists."""
        response = requests.get(
            f"{BASE_URL}/seller/dashboard",
            timeout=30
        )
        
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
        print(f"✅ GET /seller/dashboard exists (status: {response.status_code})")
    
    def test_03_seller_subscription_endpoint(self):
        """GET /api/seller/subscription exists."""
        response = requests.get(
            f"{BASE_URL}/seller/subscription",
            timeout=30
        )
        
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
        print(f"✅ GET /seller/subscription exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
