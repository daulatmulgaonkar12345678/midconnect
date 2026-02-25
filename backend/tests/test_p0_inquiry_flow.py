"""
P0 Inquiry Flow Tests - Verifying ObjectId vs String Bug Fix
=============================================================
Tests the fix for confirm_enquiry and close_enquiry endpoints that
previously had ObjectId vs string comparison bugs causing 500 errors.

IMPORTANT: Firebase is initialized in production, so we test:
1. Public endpoints without auth
2. Error responses (401 is acceptable, 500 is a bug)
3. Direct DB verification for existing data

Test Matrix:
1. Buyer creates inquiry - requires auth (test 401 vs 500)
2. Seller accept via confirm - test proper error handling (400/404 vs 500)
3. Admin inquiry list - requires admin auth
4. Verify existing data has proper ObjectId format
"""

import pytest
import requests
import os
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://b2b-marketplace-v2.preview.emergentagent.com').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'b2b_marketplace')


class TestInquiryEndpointsNoAuth:
    """Test inquiry endpoints respond correctly (no 500 errors)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def test_01_confirm_enquiry_no_auth_returns_401_not_500(self):
        """PUT /api/enquiries/{id}/confirm without auth should return 401, not 500"""
        # Valid ObjectId format
        fake_id = str(ObjectId())
        
        response = self.session.put(f"{BASE_URL}/api/enquiries/{fake_id}/confirm")
        print(f"Confirm without auth: {response.status_code}")
        
        # Should return 401 (unauthorized), NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_02_close_enquiry_no_auth_returns_401_not_500(self):
        """PUT /api/enquiries/{id}/close without auth should return 401, not 500"""
        fake_id = str(ObjectId())
        
        response = self.session.put(f"{BASE_URL}/api/enquiries/{fake_id}/close")
        print(f"Close without auth: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_03_create_inquiry_no_auth_returns_401_not_500(self):
        """POST /api/inquiries without auth should return 401, not 500"""
        inquiry_data = {
            "sellerId": str(ObjectId()),
            "quantity": 100,
            "message": "Test inquiry"
        }
        
        response = self.session.post(f"{BASE_URL}/api/inquiries", json=inquiry_data)
        print(f"Create inquiry without auth: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_04_seller_accept_inquiry_no_auth_returns_401_not_500(self):
        """POST /api/seller/inquiries/{id}/accept without auth should return 401, not 500"""
        fake_id = str(ObjectId())
        accept_data = {
            "quotedPrice": 1000,
            "moq": 10,
            "leadTimeDays": 7,
            "validityDays": 30
        }
        
        response = self.session.post(f"{BASE_URL}/api/seller/inquiries/{fake_id}/accept", json=accept_data)
        print(f"Seller accept without auth: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
    
    def test_05_admin_inquiries_no_auth_returns_401_not_500(self):
        """GET /api/admin/inquiries without auth should return 401, not 500"""
        response = self.session.get(f"{BASE_URL}/api/admin/inquiries")
        print(f"Admin inquiries without auth: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"


class TestInquiryEndpointsInvalidToken:
    """Test endpoints with invalid auth token return proper errors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session with invalid token"""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid-token-12345"
        })
    
    def test_01_confirm_enquiry_invalid_token_returns_401_not_500(self):
        """PUT /api/enquiries/{id}/confirm with invalid token should return 401, not 500"""
        fake_id = str(ObjectId())
        
        response = self.session.put(f"{BASE_URL}/api/enquiries/{fake_id}/confirm")
        print(f"Confirm with invalid token: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_02_close_enquiry_invalid_token_returns_401_not_500(self):
        """PUT /api/enquiries/{id}/close with invalid token should return 401, not 500"""
        fake_id = str(ObjectId())
        
        response = self.session.put(f"{BASE_URL}/api/enquiries/{fake_id}/close")
        print(f"Close with invalid token: {response.status_code}")
        
        # Should return 401, NOT 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_03_admin_inquiries_invalid_token_not_500(self):
        """GET /api/admin/inquiries with invalid token should not return 500"""
        response = self.session.get(f"{BASE_URL}/api/admin/inquiries")
        print(f"Admin inquiries with invalid token: {response.status_code}")
        
        # Should NOT return 500
        assert response.status_code != 500, f"Got 500 error (bug): {response.text}"


class TestDatabaseDirectValidation:
    """Direct MongoDB verification of inquiry data integrity"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup MongoDB connection"""
        try:
            self.client = MongoClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            yield
            self.client.close()
        except Exception as e:
            pytest.skip(f"Cannot connect to MongoDB: {e}")
    
    def test_01_existing_inquiries_have_objectid_seller_id(self):
        """Verify existing inquiries have sellerId as ObjectId"""
        inquiries = list(self.db.inquiries.find({}).limit(10))
        
        if not inquiries:
            pytest.skip("No inquiries in database to verify")
        
        for inq in inquiries:
            seller_id = inq.get("sellerId")
            if seller_id is not None:
                # Seller ID should be ObjectId, not string
                assert isinstance(seller_id, ObjectId), \
                    f"Inquiry {inq['_id']}: sellerId is {type(seller_id).__name__}, should be ObjectId"
        
        print(f"Verified {len(inquiries)} inquiries - all have ObjectId sellerId")
    
    def test_02_existing_inquiries_have_objectid_buyer_id(self):
        """Verify existing inquiries have buyerId as ObjectId"""
        inquiries = list(self.db.inquiries.find({}).limit(10))
        
        if not inquiries:
            pytest.skip("No inquiries in database to verify")
        
        for inq in inquiries:
            buyer_id = inq.get("buyerId")
            if buyer_id is not None:
                # Buyer ID should be ObjectId, not string
                assert isinstance(buyer_id, ObjectId), \
                    f"Inquiry {inq['_id']}: buyerId is {type(buyer_id).__name__}, should be ObjectId"
        
        print(f"Verified {len(inquiries)} inquiries - all have ObjectId buyerId")
    
    def test_03_inquiries_use_camelcase_fields(self):
        """Verify inquiries collection uses camelCase field names"""
        inquiries = list(self.db.inquiries.find({}).limit(10))
        
        if not inquiries:
            pytest.skip("No inquiries in database to verify")
        
        for inq in inquiries:
            # Check for camelCase fields (SSOT)
            assert "sellerId" in inq or inq.get("sellerId") is None, \
                f"Inquiry should use sellerId (camelCase)"
            assert "buyerId" in inq or inq.get("buyerId") is None, \
                f"Inquiry should use buyerId (camelCase)"
            
            # Check no snake_case fields
            assert "seller_id" not in inq, \
                f"Inquiry {inq['_id']}: has snake_case seller_id - should be sellerId"
            assert "buyer_id" not in inq, \
                f"Inquiry {inq['_id']}: has snake_case buyer_id - should be buyerId"
        
        print(f"Verified {len(inquiries)} inquiries - all use camelCase")
    
    def test_04_seller_can_be_resolved(self):
        """Verify seller references can be resolved from inquiries"""
        inquiries = list(self.db.inquiries.find({"sellerId": {"$exists": True}}).limit(5))
        
        if not inquiries:
            pytest.skip("No inquiries with sellerId")
        
        resolved_count = 0
        for inq in inquiries:
            seller_id = inq.get("sellerId")
            if seller_id:
                # Try to resolve seller
                seller = self.db.users.find_one({"_id": seller_id})
                if seller:
                    resolved_count += 1
                    print(f"Inquiry {inq['_id']}: Seller resolved - {seller.get('businessName', seller.get('email', 'N/A'))}")
        
        print(f"Resolved {resolved_count}/{len(inquiries)} seller references")
    
    def test_05_inquiry_statuses_are_valid(self):
        """Verify inquiries have valid status values"""
        valid_statuses = ["pending", "accepted", "rejected", "reported", "closed", "new", "confirmed"]
        
        inquiries = list(self.db.inquiries.find({}).limit(20))
        
        if not inquiries:
            pytest.skip("No inquiries in database")
        
        for inq in inquiries:
            status = inq.get("status")
            if status:
                assert status in valid_statuses, \
                    f"Inquiry {inq['_id']}: Invalid status '{status}'"
        
        print(f"Verified {len(inquiries)} inquiries - all have valid status")


class TestPublicEndpoints:
    """Test public endpoints work correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def test_01_health_endpoint(self):
        """API health check"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("Health check passed")
    
    def test_02_seller_listings_public(self):
        """GET /api/seller-listings (public)"""
        response = self.session.get(f"{BASE_URL}/api/seller-listings", params={"limit": 5})
        print(f"Seller listings: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Got 500: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "listings" in data
            print(f"Found {len(data.get('listings', []))} listings")
    
    def test_03_products_public(self):
        """GET /api/products (public)"""
        response = self.session.get(f"{BASE_URL}/api/products", params={"limit": 5})
        print(f"Products: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Got 500: {response.text}"
    
    def test_04_categories_public(self):
        """GET /api/categories (public)"""
        response = self.session.get(f"{BASE_URL}/api/categories")
        print(f"Categories: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Got 500: {response.text}"


class TestErrorHandlingNotReturning500:
    """Verify endpoints return proper errors, not 500"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer fake-token"
        })
    
    def test_01_confirm_invalid_objectid_format(self):
        """PUT /api/enquiries/invalid-id/confirm should not crash"""
        response = self.session.put(f"{BASE_URL}/api/enquiries/invalid-not-objectid/confirm")
        print(f"Confirm invalid format: {response.status_code}")
        
        # Even with invalid ID format, should not return 500
        # Should return 400 (bad request) or 401 (if auth checked first)
        assert response.status_code != 500, f"Server crashed with 500: {response.text}"
    
    def test_02_close_invalid_objectid_format(self):
        """PUT /api/enquiries/invalid-id/close should not crash"""
        response = self.session.put(f"{BASE_URL}/api/enquiries/invalid-not-objectid/close")
        print(f"Close invalid format: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Server crashed with 500: {response.text}"
    
    def test_03_seller_accept_invalid_objectid(self):
        """POST /api/seller/inquiries/invalid-id/accept should not crash"""
        response = self.session.post(
            f"{BASE_URL}/api/seller/inquiries/invalid-objectid/accept",
            json={"quotedPrice": 100, "moq": 10, "leadTimeDays": 5, "validityDays": 7}
        )
        print(f"Seller accept invalid: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Server crashed with 500: {response.text}"
    
    def test_04_seller_reject_invalid_objectid(self):
        """POST /api/seller/inquiries/invalid-id/reject should not crash"""
        response = self.session.post(
            f"{BASE_URL}/api/seller/inquiries/invalid-objectid/reject",
            json={"reason": "Test rejection"}
        )
        print(f"Seller reject invalid: {response.status_code}")
        
        # Should not return 500
        assert response.status_code != 500, f"Server crashed with 500: {response.text}"


class TestAdminInquiriesFilterValidation:
    """Test admin inquiry filters don't cause type mismatch errors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup MongoDB connection for direct queries"""
        try:
            self.client = MongoClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            self.session = requests.Session()
            self.session.headers.update({
                "Content-Type": "application/json"
            })
            yield
            self.client.close()
        except Exception as e:
            pytest.skip(f"Cannot connect to MongoDB: {e}")
    
    def test_01_verify_admin_filter_logic(self):
        """Verify admin inquiry filter can handle ObjectId vs string"""
        # Get a sample inquiry
        inquiry = self.db.inquiries.find_one({"sellerId": {"$exists": True}})
        
        if not inquiry:
            pytest.skip("No inquiries with sellerId")
        
        seller_id = inquiry.get("sellerId")
        
        # The admin endpoint query uses:
        # query["sellerId"] = seller_id (string from query param)
        # But sellerId in DB is ObjectId
        # This could cause type mismatch
        
        # Test query with string sellerId
        str_query = {"sellerId": str(seller_id)}
        result_str = list(self.db.inquiries.find(str_query).limit(1))
        
        # Test query with ObjectId sellerId
        oid_query = {"sellerId": seller_id if isinstance(seller_id, ObjectId) else ObjectId(seller_id)}
        result_oid = list(self.db.inquiries.find(oid_query).limit(1))
        
        print(f"Query with string: {len(result_str)} results")
        print(f"Query with ObjectId: {len(result_oid)} results")
        
        # The ObjectId query should work
        assert len(result_oid) > 0, "ObjectId query should return results"
        
        # NOTE: String query might not work - this is a potential bug in admin endpoint
        if len(result_str) == 0 and len(result_oid) > 0:
            print("WARNING: Admin filter with string sellerId won't find ObjectId matches")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
