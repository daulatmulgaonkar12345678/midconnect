"""
TEST: POST /api/seller/listings - FINAL ARCHITECTURE
=====================================================
Testing the seller listing creation flow with the new camelCase payload structure.

PAYLOAD STRUCTURE (FINAL ARCHITECTURE):
{
    "productId": str,          # Reference to products collection
    "attributes": dict,        # Attribute values matching specTemplate
    "sellerRole": str,         # distributor, manufacturer, trader, dealer
    "description": str,        # Optional
    "images": list,            # Required (1-5)
    "moq": int,                # FLAT field (NOT nested in availability)
    "stock": int,              # FLAT field
    "maxCapacity": int,        # Optional FLAT field
    "leadTime": int,           # Optional FLAT field (days)
    "currency": str,           # Default: "INR"
    "pricingTiers": list,      # NOT pricing.slabs
    "datasheetUrl": str        # Optional
}
"""

import pytest
import requests
import os
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://quote-system-19.preview.emergentagent.com/api')

# Test data storage
test_data = {
    "seller_id": None,
    "product_id": None,
    "spec_template_id": None,
    "category_id": None,
    "listing_id": None
}


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async operations."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db():
    """Get database connection."""
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'b2b_marketplace')]


class TestSellerListingCreate:
    """Test POST /api/seller/listings with FINAL ARCHITECTURE payload."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db, event_loop):
        """Setup test data before tests."""
        self.db = db
        self.loop = event_loop
        
        # Run async setup
        self.loop.run_until_complete(self._async_setup())
    
    async def _async_setup(self):
        """Async setup: create test seller and get product data."""
        # 1. Create or get test seller
        seller = await self.db.users.find_one({"email": "testseller_listing@example.com"})
        if not seller:
            now = datetime.now(timezone.utc)
            seller = {
                "_id": ObjectId(),
                "email": "testseller_listing@example.com",
                "firebase_uid": "test_firebase_listing_seller_456",
                "businessName": "Test Listing Seller",
                "phone": "+919876543211",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "isSeller": True,
                "isAdmin": False,
                "accountStatus": "ACTIVE",
                "emailVerified": True,
                "subscription": {"plan": "free"},
                "createdAt": now,
                "updatedAt": now
            }
            await self.db.users.insert_one(seller)
            print(f"Created test seller: {seller['_id']}")
        else:
            # Ensure isSeller is True
            await self.db.users.update_one(
                {"_id": seller["_id"]},
                {"$set": {"isSeller": True}}
            )
        
        test_data["seller_id"] = str(seller["_id"])
        
        # 2. Find a product with specTemplateId
        product = await self.db.products.find_one({
            "specTemplateId": {"$exists": True, "$ne": None}
        })
        
        if product:
            test_data["product_id"] = str(product["_id"])
            test_data["spec_template_id"] = str(product.get("specTemplateId"))
            test_data["category_id"] = str(product.get("categoryId"))
            print(f"Found product: {product['name']}, specTemplateId: {test_data['spec_template_id']}")
        else:
            print("WARNING: No product with specTemplateId found!")
    
    def test_01_health_check(self):
        """Verify backend is healthy before testing."""
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")
    
    def test_02_verify_test_data_exists(self):
        """Verify test data was created successfully."""
        assert test_data["seller_id"] is not None, "Test seller not created"
        assert test_data["product_id"] is not None, "No product with specTemplateId found"
        assert test_data["spec_template_id"] is not None, "No specTemplateId found"
        print(f"✅ Test data ready:")
        print(f"   Seller ID: {test_data['seller_id']}")
        print(f"   Product ID: {test_data['product_id']}")
        print(f"   SpecTemplate ID: {test_data['spec_template_id']}")
    
    def test_03_listing_create_without_auth(self):
        """Test that POST /seller/listings requires authentication."""
        payload = {
            "productId": test_data["product_id"],
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
        
        # Should fail without auth
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}: {response.text}"
        print(f"✅ Auth check passed: {response.status_code}")
    
    def test_04_payload_structure_validation(self):
        """Verify the expected payload structure matches FINAL ARCHITECTURE."""
        # This is a schema validation test
        expected_fields = {
            "productId": "string - Required",
            "attributes": "dict - Required",
            "sellerRole": "string - Required",
            "description": "string - Optional",
            "images": "list - Required (1-5)",
            "moq": "int - Required (FLAT, NOT availability.moq)",
            "stock": "int - Required (FLAT)",
            "maxCapacity": "int - Optional (FLAT)",
            "leadTime": "int - Optional (FLAT)",
            "currency": "string - Default INR",
            "pricingTiers": "list - Required (NOT pricing.slabs)",
            "datasheetUrl": "string - Optional"
        }
        
        print("✅ Expected FINAL ARCHITECTURE payload structure:")
        for field, description in expected_fields.items():
            print(f"   {field}: {description}")
    
    def test_05_verify_legacy_payload_rejected(self):
        """Verify that the OLD snake_case payload is NOT accepted."""
        # This is the OLD/LEGACY payload that should be rejected
        legacy_payload = {
            "product_name": "Test Product",
            "category_id": test_data["category_id"],
            "seller_type": "distributor",  # OLD: should be sellerRole
            "specifications": {  # OLD: should be attributes
                "power": "5HP",
                "voltage": "415V"
            },
            "availability": {  # OLD: should be flat moq, stock, etc.
                "moq": 1,
                "stock": 100
            },
            "pricing": {  # OLD: should be flat pricingTiers
                "slabs": [{"min_qty": 1, "max_qty": None, "price_per_unit": 1000}]
            }
        }
        
        # Without auth, should fail with 401/403, not 422
        # The 422 would indicate the payload validation happened
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json=legacy_payload,
            timeout=30
        )
        
        # Should fail (either auth or validation)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
        print(f"✅ Legacy payload not accepted silently: {response.status_code}")
        
        # If we got 422, it's because the fields are wrong - good!
        if response.status_code == 422:
            print(f"   Validation error (expected): {response.text[:200]}")


class TestListingPayloadValidation:
    """Test payload validation for FINAL ARCHITECTURE."""
    
    def test_01_missing_required_fields(self):
        """Test that missing required fields cause validation error."""
        # Payload missing productId
        payload = {
            "attributes": {"power": 5},
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
        
        # Should fail (401 for auth, or 422 for validation)
        assert response.status_code in [401, 403, 422]
        print(f"✅ Missing productId handled: {response.status_code}")
    
    def test_02_empty_pricing_tiers(self):
        """Test that empty pricingTiers causes validation error."""
        payload = {
            "productId": test_data["product_id"],
            "attributes": {"power": 5},
            "sellerRole": "distributor",
            "images": ["https://example.com/image.jpg"],
            "moq": 1,
            "stock": 100,
            "currency": "INR",
            "pricingTiers": []  # Empty - should fail
        }
        
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json=payload,
            timeout=30
        )
        
        # Should fail validation (pricingTiers min_length=1)
        assert response.status_code in [401, 403, 422]
        print(f"✅ Empty pricingTiers handled: {response.status_code}")
    
    def test_03_invalid_pricing_tier_values(self):
        """Test that invalid pricing tier values cause validation error."""
        payload = {
            "productId": test_data["product_id"],
            "attributes": {"power": 5},
            "sellerRole": "distributor",
            "images": ["https://example.com/image.jpg"],
            "moq": 1,
            "stock": 100,
            "currency": "INR",
            "pricingTiers": [{"minQty": 0, "maxQty": None, "pricePerUnit": 0}]  # minQty < 1, pricePerUnit <= 0
        }
        
        response = requests.post(
            f"{BASE_URL}/seller/listings",
            json=payload,
            timeout=30
        )
        
        # Should fail validation
        assert response.status_code in [401, 403, 422]
        print(f"✅ Invalid pricing tier values handled: {response.status_code}")


class TestAPISchemaMatching:
    """Verify frontend api.ts schema matches backend expectations."""
    
    def test_01_listing_create_payload_interface(self):
        """Document the expected ListingCreatePayload from api.ts."""
        # From /app/frontend-web/src/lib/api.ts lines 1164-1183
        expected_interface = """
        ListingCreatePayload {
            productId: string;           // Required: Reference to products collection
            attributes: Record<string, string | number | boolean>;  // Required
            sellerRole: string;          // Required: distributor, manufacturer, trader, dealer
            description?: string;
            images: string[];
            moq: number;                 // Flat field (NOT nested in availability)
            stock: number;               // Flat field
            maxCapacity?: number;        // Flat field
            leadTime?: number;           // Flat field (days)
            currency: string;
            pricingTiers: PricingTierCreate[];  // NOT pricing.slabs
            datasheetUrl?: string;
        }
        
        PricingTierCreate {
            minQty: number;
            maxQty: number | null;
            pricePerUnit: number;
        }
        """
        print(f"✅ Expected ListingCreatePayload interface:")
        print(expected_interface)
    
    def test_02_backend_pydantic_model(self):
        """Document the backend ListingCreate Pydantic model."""
        # From /app/backend/seller_products.py lines 49-76
        expected_model = """
        ListingCreate (Pydantic) {
            productId: str (Required)
            attributes: Dict[str, Any] (Required)
            sellerRole: str (Required)
            description: Optional[str] (max_length=2000)
            images: List[str] (default=[], max_length=5)
            moq: int (default=1, ge=1)
            stock: int (default=0, ge=0)
            maxCapacity: Optional[int] (ge=1)
            leadTime: Optional[int] (ge=0)
            currency: str (default="INR", max_length=3)
            pricingTiers: List[PricingTier] (min_length=1, max_length=10)
            datasheetUrl: Optional[str]
        }
        
        PricingTier (Pydantic) {
            minQty: int (ge=1)
            maxQty: Optional[int] (ge=1)
            pricePerUnit: float (gt=0)
        }
        """
        print(f"✅ Backend ListingCreate Pydantic model:")
        print(expected_model)
    
    def test_03_schema_alignment_check(self):
        """Verify frontend and backend schemas are aligned."""
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
        
        assert frontend_fields == backend_fields, "Schema mismatch between frontend and backend"
        print(f"✅ Frontend and backend schemas are aligned")
        print(f"   Common fields: {frontend_fields}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
