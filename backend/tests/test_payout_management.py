"""
ADMIN PAYOUT MANAGEMENT TESTS
=============================
Tests for the Admin Payout Management module for UdyogConnect ERP.

Features tested:
1. Orders created with payoutStatus='pending' by default
2. POST /api/referral/admin/mark-payout marks order as paid with payoutDate, payoutReference, payoutMethod, paidByAdmin
3. POST /api/referral/admin/mark-payout rejects already-paid orders (400)
4. POST /api/referral/admin/mark-payout rejects invalid orderId (400)
5. POST /api/referral/admin/mark-payout rejects non-existent orderId (404)
6. POST /api/referral/admin/bulk-payout marks multiple orders as paid with batchId
7. POST /api/referral/admin/bulk-payout skips already-paid orders and reports them
8. GET /api/referral/admin/partner-orders/{code} returns orders with payout details
9. GET /api/referral/admin/partner-orders/{code} shows correct paid/pending amounts
10. GET /api/referral/admin/sales-overview includes pendingPayout and paidOutAmount
11. GET /api/referral/admin/sales-overview partners have paidAmount and pendingAmount
12. GET /api/referral/admin/export-payouts returns CSV with all payout fields
13. GET /api/referral/sales-stats uses payoutStatus for earnings breakdown
14. Existing referral endpoints unchanged: /api/referral/my-link, /api/referral/stats
15. Admin auth required for all payout endpoints (non-admin gets 403)
"""

import pytest
import requests
import os
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://plan-limits-5.preview.emergentagent.com"

# MongoDB connection for direct data manipulation
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "midconnect"

# Test token for admin access
ADMIN_TOKEN = "dev-test-token"


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client for test data setup/cleanup"""
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def api_client():
    """Requests session with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def no_auth_client():
    """Requests session without auth"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_partner(mongo_client):
    """Create a test referral partner user"""
    now = datetime.now(timezone.utc)
    partner_id = ObjectId()
    partner_doc = {
        "_id": partner_id,
        "email": f"TEST_payout_partner_{partner_id}@test.com",
        "firebaseUid": f"TEST_firebase_partner_{partner_id}",
        "referralCode": f"PAYTEST{str(partner_id)[:4].upper()}",
        "referralCount": 0,
        "referralSuccessCount": 0,
        "isAdmin": False,
        "isSeller": True,
        "profile": {"businessName": "Test Payout Partner Business"},
        "createdAt": now,
        "updatedAt": now,
    }
    mongo_client.users.insert_one(partner_doc)
    yield partner_doc
    # Cleanup
    mongo_client.users.delete_one({"_id": partner_id})


@pytest.fixture(scope="module")
def test_orders(mongo_client, test_partner):
    """Create test orders for payout testing"""
    now = datetime.now(timezone.utc)
    orders = []
    
    # Create 5 test orders with payoutStatus='pending'
    for i in range(5):
        user_id = ObjectId()
        # Create user for this order
        user_doc = {
            "_id": user_id,
            "email": f"TEST_payout_user_{i}_{user_id}@test.com",
            "firebaseUid": f"TEST_firebase_payout_user_{i}_{user_id}",
            "referredBy": test_partner["referralCode"],
            "isAdmin": False,
            "isSeller": True,
            "profile": {"businessName": f"Test Payout User {i}"},
            "createdAt": now,
            "updatedAt": now,
        }
        mongo_client.users.insert_one(user_doc)
        
        order_doc = {
            "_id": ObjectId(),
            "userId": user_id,
            "referredBy": test_partner["referralCode"],
            "plan": ["starter", "standard", "pro"][i % 3],
            "amount": [5000, 10000, 15000][i % 3],
            "commission": [1000, 2000, 3000][i % 3],
            "commissionPercent": 20,
            "status": "paid",
            "payoutStatus": "pending",  # Default pending
            "createdAt": now,
        }
        mongo_client.orders.insert_one(order_doc)
        orders.append({"order": order_doc, "user": user_doc})
    
    yield orders
    
    # Cleanup
    for item in orders:
        mongo_client.orders.delete_one({"_id": item["order"]["_id"]})
        mongo_client.users.delete_one({"_id": item["user"]["_id"]})


class TestOrderPayoutStatusDefault:
    """Test that orders are created with payoutStatus='pending' by default"""
    
    def test_orders_have_pending_payout_status(self, mongo_client, test_orders):
        """Verify test orders have payoutStatus='pending'"""
        for item in test_orders:
            order = mongo_client.orders.find_one({"_id": item["order"]["_id"]})
            assert order is not None, "Order should exist"
            assert order.get("payoutStatus") == "pending", f"Order should have payoutStatus='pending', got {order.get('payoutStatus')}"
        
        print(f"✓ All {len(test_orders)} test orders have payoutStatus='pending'")


class TestMarkPayoutEndpoint:
    """Test POST /api/referral/admin/mark-payout endpoint"""
    
    def test_mark_payout_success(self, api_client, mongo_client, test_orders):
        """POST /api/referral/admin/mark-payout marks order as paid with all fields"""
        order_id = str(test_orders[0]["order"]["_id"])
        
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/mark-payout",
            json={
                "orderId": order_id,
                "payoutReference": "REF-TEST-001",
                "payoutMethod": "bank_transfer"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("payoutStatus") == "paid", "Response should confirm payoutStatus='paid'"
        assert "payoutDate" in data, "Response should have payoutDate"
        
        # Verify in database
        order = mongo_client.orders.find_one({"_id": test_orders[0]["order"]["_id"]})
        assert order.get("payoutStatus") == "paid", "DB order should have payoutStatus='paid'"
        assert order.get("payoutDate") is not None, "DB order should have payoutDate"
        assert order.get("payoutReference") == "REF-TEST-001", "DB order should have payoutReference"
        assert order.get("payoutMethod") == "bank_transfer", "DB order should have payoutMethod"
        assert order.get("paidByAdmin") is not None, "DB order should have paidByAdmin"
        
        print(f"✓ POST /api/referral/admin/mark-payout successfully marks order as paid with all fields")
    
    def test_mark_payout_rejects_already_paid(self, api_client, test_orders):
        """POST /api/referral/admin/mark-payout rejects already-paid orders (400)"""
        # Use the order we just marked as paid
        order_id = str(test_orders[0]["order"]["_id"])
        
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/mark-payout",
            json={
                "orderId": order_id,
                "payoutReference": "REF-TEST-DUPLICATE",
                "payoutMethod": "manual"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for already-paid order, got {response.status_code}: {response.text}"
        
        print(f"✓ POST /api/referral/admin/mark-payout correctly rejects already-paid order (400)")
    
    def test_mark_payout_rejects_invalid_order_id(self, api_client):
        """POST /api/referral/admin/mark-payout rejects invalid orderId (400)"""
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/mark-payout",
            json={
                "orderId": "invalid-not-objectid",
                "payoutReference": "REF-TEST",
                "payoutMethod": "manual"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid orderId, got {response.status_code}: {response.text}"
        
        print(f"✓ POST /api/referral/admin/mark-payout correctly rejects invalid orderId (400)")
    
    def test_mark_payout_rejects_nonexistent_order(self, api_client):
        """POST /api/referral/admin/mark-payout rejects non-existent orderId (404)"""
        fake_order_id = str(ObjectId())  # Valid ObjectId format but doesn't exist
        
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/mark-payout",
            json={
                "orderId": fake_order_id,
                "payoutReference": "REF-TEST",
                "payoutMethod": "manual"
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}: {response.text}"
        
        print(f"✓ POST /api/referral/admin/mark-payout correctly rejects non-existent orderId (404)")


class TestBulkPayoutEndpoint:
    """Test POST /api/referral/admin/bulk-payout endpoint"""
    
    def test_bulk_payout_marks_multiple_orders(self, api_client, mongo_client, test_orders):
        """POST /api/referral/admin/bulk-payout marks multiple orders as paid with batchId"""
        # Use orders 1 and 2 (index 0 is already paid from previous test)
        order_ids = [str(test_orders[1]["order"]["_id"]), str(test_orders[2]["order"]["_id"])]
        
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/bulk-payout",
            json={
                "orderIds": order_ids,
                "payoutReference": "BULK-REF-001",
                "payoutMethod": "bulk_transfer"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "batchId" in data, "Response should have batchId"
        assert data.get("paidCount") == 2, f"Expected paidCount=2, got {data.get('paidCount')}"
        assert len(data.get("paidOrderIds", [])) == 2, "Should have 2 paid order IDs"
        
        # Verify in database
        for oid_str in order_ids:
            order = mongo_client.orders.find_one({"_id": ObjectId(oid_str)})
            assert order.get("payoutStatus") == "paid", f"Order {oid_str} should be paid"
            assert order.get("payoutBatchId") == data["batchId"], "Order should have batchId"
            assert order.get("payoutReference") == "BULK-REF-001", "Order should have payoutReference"
        
        print(f"✓ POST /api/referral/admin/bulk-payout marks {data.get('paidCount')} orders with batchId={data.get('batchId')}")
    
    def test_bulk_payout_skips_already_paid(self, api_client, test_orders):
        """POST /api/referral/admin/bulk-payout skips already-paid orders and reports them"""
        # Include already-paid orders (0, 1, 2) and pending orders (3, 4)
        order_ids = [
            str(test_orders[0]["order"]["_id"]),  # Already paid
            str(test_orders[1]["order"]["_id"]),  # Already paid
            str(test_orders[3]["order"]["_id"]),  # Pending
            str(test_orders[4]["order"]["_id"]),  # Pending
        ]
        
        response = api_client.post(
            f"{BASE_URL}/api/referral/admin/bulk-payout",
            json={
                "orderIds": order_ids,
                "payoutReference": "BULK-REF-002",
                "payoutMethod": "manual"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("paidCount") == 2, f"Expected paidCount=2 (only pending orders), got {data.get('paidCount')}"
        assert data.get("skippedCount") == 2, f"Expected skippedCount=2 (already paid), got {data.get('skippedCount')}"
        
        # Check skipped reasons
        skipped = data.get("skipped", [])
        assert len(skipped) == 2, "Should have 2 skipped entries"
        for skip in skipped:
            assert skip.get("reason") == "already paid", f"Skip reason should be 'already paid', got {skip.get('reason')}"
        
        print(f"✓ POST /api/referral/admin/bulk-payout: paid={data.get('paidCount')}, skipped={data.get('skippedCount')}")


class TestPartnerOrdersEndpoint:
    """Test GET /api/referral/admin/partner-orders/{code} endpoint"""
    
    def test_partner_orders_returns_orders_with_payout_details(self, api_client, test_partner, test_orders):
        """GET /api/referral/admin/partner-orders/{code} returns orders with payout details"""
        referral_code = test_partner["referralCode"]
        
        response = api_client.get(f"{BASE_URL}/api/referral/admin/partner-orders/{referral_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "orders" in data, "Response should have 'orders'"
        assert "referralCode" in data, "Response should have 'referralCode'"
        assert data["referralCode"] == referral_code, "Response should have correct referralCode"
        
        orders = data["orders"]
        assert len(orders) >= 5, f"Expected at least 5 orders, got {len(orders)}"
        
        # Check order structure includes payout fields
        for order in orders:
            assert "orderId" in order, "Order should have orderId"
            assert "payoutStatus" in order, "Order should have payoutStatus"
            assert "payoutDate" in order or order.get("payoutStatus") == "pending", "Paid orders should have payoutDate"
            assert "payoutReference" in order, "Order should have payoutReference"
            assert "payoutMethod" in order, "Order should have payoutMethod"
            assert "payoutBatchId" in order, "Order should have payoutBatchId"
        
        print(f"✓ GET /api/referral/admin/partner-orders/{referral_code} returns {len(orders)} orders with payout details")
    
    def test_partner_orders_shows_correct_amounts(self, api_client, test_partner):
        """GET /api/referral/admin/partner-orders/{code} shows correct paid/pending amounts"""
        referral_code = test_partner["referralCode"]
        
        response = api_client.get(f"{BASE_URL}/api/referral/admin/partner-orders/{referral_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "paidAmount" in data, "Response should have 'paidAmount'"
        assert "pendingAmount" in data, "Response should have 'pendingAmount'"
        assert "totalCommission" in data, "Response should have 'totalCommission'"
        
        # Verify amounts are numeric
        assert isinstance(data["paidAmount"], (int, float)), "paidAmount should be numeric"
        assert isinstance(data["pendingAmount"], (int, float)), "pendingAmount should be numeric"
        assert isinstance(data["totalCommission"], (int, float)), "totalCommission should be numeric"
        
        # Verify paidAmount + pendingAmount = totalCommission
        total = round(data["paidAmount"] + data["pendingAmount"], 2)
        expected_total = round(data["totalCommission"], 2)
        assert total == expected_total, f"paidAmount + pendingAmount ({total}) should equal totalCommission ({expected_total})"
        
        print(f"✓ Partner orders: paidAmount={data['paidAmount']}, pendingAmount={data['pendingAmount']}, total={data['totalCommission']}")


class TestSalesOverviewPayoutFields:
    """Test GET /api/referral/admin/sales-overview includes payout fields"""
    
    def test_sales_overview_includes_payout_totals(self, api_client):
        """GET /api/referral/admin/sales-overview includes pendingPayout and paidOutAmount"""
        response = api_client.get(f"{BASE_URL}/api/referral/admin/sales-overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pendingPayout" in data, "Response should have 'pendingPayout'"
        assert "paidOutAmount" in data, "Response should have 'paidOutAmount'"
        
        # Verify types
        assert isinstance(data["pendingPayout"], (int, float)), "pendingPayout should be numeric"
        assert isinstance(data["paidOutAmount"], (int, float)), "paidOutAmount should be numeric"
        
        print(f"✓ Sales overview: pendingPayout={data['pendingPayout']}, paidOutAmount={data['paidOutAmount']}")
    
    def test_sales_overview_partners_have_payout_amounts(self, api_client):
        """GET /api/referral/admin/sales-overview partners have paidAmount and pendingAmount"""
        response = api_client.get(f"{BASE_URL}/api/referral/admin/sales-overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        partners = data.get("partners", [])
        
        if partners:
            for partner in partners:
                assert "paidAmount" in partner, f"Partner {partner.get('code')} should have 'paidAmount'"
                assert "pendingAmount" in partner, f"Partner {partner.get('code')} should have 'pendingAmount'"
                assert isinstance(partner["paidAmount"], (int, float)), "paidAmount should be numeric"
                assert isinstance(partner["pendingAmount"], (int, float)), "pendingAmount should be numeric"
            
            print(f"✓ All {len(partners)} partners have paidAmount and pendingAmount fields")
        else:
            print("✓ No partners found (test data may have been cleaned up)")


class TestExportPayoutsCSV:
    """Test GET /api/referral/admin/export-payouts endpoint"""
    
    def test_export_payouts_returns_csv(self, api_client):
        """GET /api/referral/admin/export-payouts returns CSV with all payout fields"""
        response = api_client.get(f"{BASE_URL}/api/referral/admin/export-payouts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv content type, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert "payouts_export" in content_disp, "Filename should contain 'payouts_export'"
        
        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) >= 1, "CSV should have at least header row"
        
        # Check header contains payout fields
        header = lines[0].lower()
        assert "payout status" in header, "CSV header should have 'Payout Status'"
        assert "payout date" in header, "CSV header should have 'Payout Date'"
        assert "payout reference" in header, "CSV header should have 'Payout Reference'"
        assert "payout method" in header, "CSV header should have 'Payout Method'"
        assert "batch id" in header, "CSV header should have 'Batch ID'"
        
        print(f"✓ GET /api/referral/admin/export-payouts returns CSV with {len(lines)} rows including payout fields")


class TestSalesStatsPayoutStatus:
    """Test GET /api/referral/sales-stats uses payoutStatus for earnings breakdown"""
    
    def test_sales_stats_uses_payout_status(self, api_client):
        """GET /api/referral/sales-stats returns pendingEarnings and paidOutEarnings based on payoutStatus"""
        response = api_client.get(f"{BASE_URL}/api/referral/sales-stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pendingEarnings" in data, "Response should have 'pendingEarnings'"
        assert "paidOutEarnings" in data, "Response should have 'paidOutEarnings'"
        assert "totalEarnings" in data, "Response should have 'totalEarnings'"
        
        # Verify types
        assert isinstance(data["pendingEarnings"], (int, float)), "pendingEarnings should be numeric"
        assert isinstance(data["paidOutEarnings"], (int, float)), "paidOutEarnings should be numeric"
        
        print(f"✓ Sales stats: pendingEarnings={data['pendingEarnings']}, paidOutEarnings={data['paidOutEarnings']}")


class TestExistingEndpointsUnchanged:
    """Test that existing referral endpoints still work unchanged"""
    
    def test_my_link_endpoint_unchanged(self, api_client):
        """GET /api/referral/my-link still works"""
        response = api_client.get(f"{BASE_URL}/api/referral/my-link")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "referralCode" in data, "Response should have 'referralCode'"
        assert "referralLink" in data, "Response should have 'referralLink'"
        
        print(f"✓ GET /api/referral/my-link unchanged: code={data.get('referralCode')}")
    
    def test_stats_endpoint_unchanged(self, api_client):
        """GET /api/referral/stats still works"""
        response = api_client.get(f"{BASE_URL}/api/referral/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "totalReferred" in data, "Response should have 'totalReferred'"
        assert "successfulReferrals" in data, "Response should have 'successfulReferrals'"
        
        print(f"✓ GET /api/referral/stats unchanged: totalReferred={data.get('totalReferred')}")


class TestAdminAuthRequired:
    """Test that admin auth is required for all payout endpoints"""
    
    def test_mark_payout_requires_admin(self, no_auth_client):
        """POST /api/referral/admin/mark-payout requires admin auth"""
        response = no_auth_client.post(
            f"{BASE_URL}/api/referral/admin/mark-payout",
            json={"orderId": str(ObjectId()), "payoutReference": "test"}
        )
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ POST /api/referral/admin/mark-payout requires admin auth (status: {response.status_code})")
    
    def test_bulk_payout_requires_admin(self, no_auth_client):
        """POST /api/referral/admin/bulk-payout requires admin auth"""
        response = no_auth_client.post(
            f"{BASE_URL}/api/referral/admin/bulk-payout",
            json={"orderIds": [str(ObjectId())], "payoutReference": "test"}
        )
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ POST /api/referral/admin/bulk-payout requires admin auth (status: {response.status_code})")
    
    def test_partner_orders_requires_admin(self, no_auth_client):
        """GET /api/referral/admin/partner-orders/{code} requires admin auth"""
        response = no_auth_client.get(f"{BASE_URL}/api/referral/admin/partner-orders/TESTCODE")
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ GET /api/referral/admin/partner-orders requires admin auth (status: {response.status_code})")
    
    def test_export_payouts_requires_admin(self, no_auth_client):
        """GET /api/referral/admin/export-payouts requires admin auth"""
        response = no_auth_client.get(f"{BASE_URL}/api/referral/admin/export-payouts")
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ GET /api/referral/admin/export-payouts requires admin auth (status: {response.status_code})")
    
    def test_sales_overview_requires_admin(self, no_auth_client):
        """GET /api/referral/admin/sales-overview requires admin auth"""
        response = no_auth_client.get(f"{BASE_URL}/api/referral/admin/sales-overview")
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ GET /api/referral/admin/sales-overview requires admin auth (status: {response.status_code})")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, mongo_client):
        """Clean up all TEST_payout_ prefixed data"""
        # Delete test users
        result_users = mongo_client.users.delete_many({"email": {"$regex": "^TEST_payout_"}})
        
        # Delete test orders by referral code pattern
        result_orders = mongo_client.orders.delete_many({"referredBy": {"$regex": "^PAYTEST"}})
        
        print(f"✓ Cleanup: deleted {result_users.deleted_count} test users, {result_orders.deleted_count} test orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
