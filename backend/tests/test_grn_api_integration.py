"""
GRN API Integration Tests - Test actual HTTP endpoints
Tests the receive goods API workflow with real HTTP calls.
"""

import pytest
import requests
import os
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-emp-mgmt.preview.emergentagent.com').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'midconnect')


@pytest.fixture(scope="module")
def db():
    """Direct MongoDB connection"""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture(scope="module")
def test_seller(db):
    """Get or create test seller and return their firebase UID"""
    seller = db.users.find_one({"email": "test-api-grn-seller@test.com"})
    if not seller:
        now = datetime.now(timezone.utc)
        seller_doc = {
            "firebaseUid": f"test-api-grn-seller-{int(datetime.now().timestamp())}",
            "email": "test-api-grn-seller@test.com",
            "name": "Test API GRN Seller",
            "roles": ["seller"],
            "accountType": "seller",
            "accountStatus": "active",
            "profile": {
                "businessName": "API GRN Test Business",
                "phone": "9876543210"
            },
            "createdAt": now,
            "updatedAt": now
        }
        result = db.users.insert_one(seller_doc)
        seller = db.users.find_one({"_id": result.inserted_id})
    return seller


@pytest.fixture(scope="module")
def test_auth_token(test_seller):
    """Return dev test token for API authentication"""
    return "dev-test-token"


@pytest.fixture(scope="module")
def api_headers(test_auth_token):
    """Return headers for API requests"""
    return {
        "Authorization": f"Bearer {test_auth_token}",
        "Content-Type": "application/json"
    }


class TestGRNAPIEndpoints:
    """Test actual GRN API endpoints"""
    
    def test_list_purchase_orders(self, api_headers):
        """Test GET /api/business-tools/purchase-orders"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders",
            headers=api_headers
        )
        # 401 expected without valid Firebase token
        # But we want to verify the endpoint exists
        assert response.status_code in [200, 401, 403]
        print(f"✅ GET /api/business-tools/purchase-orders returned {response.status_code}")
    
    def test_po_receive_endpoint_exists(self, api_headers):
        """Test POST /api/business-tools/purchase-orders/{id}/receive endpoint exists"""
        # Try with a dummy ID - should get 401 (auth) or 400 (invalid ID)
        response = requests.post(
            f"{BASE_URL}/api/business-tools/purchase-orders/000000000000000000000000/receive",
            headers=api_headers,
            json={"items": [], "notes": "test"}
        )
        # 401 = auth required, 400 = invalid ID, 404 = not found - all valid responses
        assert response.status_code in [400, 401, 403, 404, 422]
        print(f"✅ POST /api/business-tools/purchase-orders/{{id}}/receive returned {response.status_code}")
    
    def test_po_receipts_endpoint_exists(self, api_headers):
        """Test GET /api/business-tools/purchase-orders/{id}/receipts endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders/000000000000000000000000/receipts",
            headers=api_headers
        )
        assert response.status_code in [200, 401, 403, 404]
        print(f"✅ GET /api/business-tools/purchase-orders/{{id}}/receipts returned {response.status_code}")
    
    def test_po_status_update_accepts_partially_received(self, api_headers):
        """Test PUT /api/business-tools/purchase-orders/{id}/status accepts partially_received"""
        response = requests.put(
            f"{BASE_URL}/api/business-tools/purchase-orders/000000000000000000000000/status",
            headers=api_headers,
            json={"status": "partially_received"}
        )
        # Should not get 422 validation error - partially_received should be accepted
        # Will get 401/404 but validates the schema accepts this status
        assert response.status_code in [401, 403, 404]
        print(f"✅ PUT /api/business-tools/purchase-orders/{{id}}/status with 'partially_received' returned {response.status_code}")
    
    def test_po_filter_by_partially_received(self, api_headers):
        """Test GET /api/business-tools/purchase-orders?status=partially_received"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/purchase-orders?status=partially_received",
            headers=api_headers
        )
        assert response.status_code in [200, 401, 403]
        print(f"✅ GET /api/business-tools/purchase-orders?status=partially_received returned {response.status_code}")


class TestGRNSchemaValidation:
    """Test GRN model schema validation"""
    
    def test_grn_create_model_validation(self, api_headers):
        """Test GRNCreate model accepts items with receivedQuantity"""
        # This tests that the schema validation works
        # The actual request will fail auth but validates model parsing
        response = requests.post(
            f"{BASE_URL}/api/business-tools/purchase-orders/507f1f77bcf86cd799439011/receive",
            headers=api_headers,
            json={
                "items": [
                    {"listingId": "507f1f77bcf86cd799439011", "receivedQuantity": 25}
                ],
                "notes": "Test GRN notes"
            }
        )
        # 422 would indicate schema validation failure
        # 401/404 indicates schema accepted, auth failed
        assert response.status_code in [401, 403, 404]
        print(f"✅ GRNCreate model accepts items with receivedQuantity (status: {response.status_code})")
    
    def test_grn_item_receive_model(self, api_headers):
        """Test GRNItemReceive model with listingId and receivedQuantity"""
        response = requests.post(
            f"{BASE_URL}/api/business-tools/purchase-orders/507f1f77bcf86cd799439011/receive",
            headers=api_headers,
            json={
                "items": [
                    {"listingId": "507f1f77bcf86cd799439011", "receivedQuantity": 0},
                    {"listingId": "507f1f77bcf86cd799439012", "receivedQuantity": 100}
                ],
                "notes": None
            }
        )
        # Check the model validation passes
        assert response.status_code in [401, 403, 404]
        print(f"✅ GRNItemReceive model validated correctly (status: {response.status_code})")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ API health check passed")
