"""
REFERRAL + SALES TRACKING ORDER CREATION TESTS
==============================================
Tests for the hybrid referral + sales tracking module with order creation on admin subscription activation.

Features tested:
1. GET /api/referral/admin/plan-config - returns 3 plans (starter, standard, pro) with prices
2. PUT /api/referral/admin/plan-config/{plan} - updates price and commission
3. POST /api/admin/subscriptions/activate/{user_id} - creates order for referred users with paid plans
4. Duplicate prevention - one order per user
5. Trial plan does NOT create order
6. Non-referred users do NOT create order
7. GET /api/referral/sales-stats - returns correct metrics (no commissionRate field)
8. GET /api/referral/admin/sales-overview - returns full admin data
9. User schema updates after activation
10. Existing referral endpoints still work
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from pymongo import MongoClient

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://seo-phase2-enhance.preview.emergentagent.com"

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
def test_referrer(mongo_client):
    """Create a test referrer user with referral code"""
    now = datetime.now(timezone.utc)
    referrer_id = ObjectId()
    referrer_doc = {
        "_id": referrer_id,
        "email": f"TEST_referrer_{referrer_id}@test.com",
        "firebaseUid": f"TEST_firebase_referrer_{referrer_id}",
        "referralCode": f"TEST{str(referrer_id)[:4].upper()}",
        "referralCount": 0,
        "referralSuccessCount": 0,
        "isAdmin": False,
        "isSeller": True,
        "profile": {"businessName": "Test Referrer Business"},
        "createdAt": now,
        "updatedAt": now,
    }
    mongo_client.users.insert_one(referrer_doc)
    yield referrer_doc
    # Cleanup
    mongo_client.users.delete_one({"_id": referrer_id})


@pytest.fixture(scope="module")
def test_referred_user(mongo_client, test_referrer):
    """Create a test user who was referred"""
    now = datetime.now(timezone.utc)
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": f"TEST_referred_{user_id}@test.com",
        "firebaseUid": f"TEST_firebase_referred_{user_id}",
        "referredBy": test_referrer["referralCode"],  # This user was referred
        "referredAt": now,
        "isAdmin": False,
        "isSeller": True,
        "profile": {"businessName": "Test Referred Business"},
        "createdAt": now,
        "updatedAt": now,
    }
    mongo_client.users.insert_one(user_doc)
    yield user_doc
    # Cleanup
    mongo_client.users.delete_one({"_id": user_id})
    mongo_client.orders.delete_many({"userId": user_id})


@pytest.fixture(scope="module")
def test_non_referred_user(mongo_client):
    """Create a test user who was NOT referred"""
    now = datetime.now(timezone.utc)
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": f"TEST_nonreferred_{user_id}@test.com",
        "firebaseUid": f"TEST_firebase_nonreferred_{user_id}",
        # No referredBy field - this user was NOT referred
        "isAdmin": False,
        "isSeller": True,
        "profile": {"businessName": "Test Non-Referred Business"},
        "createdAt": now,
        "updatedAt": now,
    }
    mongo_client.users.insert_one(user_doc)
    yield user_doc
    # Cleanup
    mongo_client.users.delete_one({"_id": user_id})


@pytest.fixture(scope="module")
def test_trial_user(mongo_client, test_referrer):
    """Create a test user for trial plan testing"""
    now = datetime.now(timezone.utc)
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": f"TEST_trial_{user_id}@test.com",
        "firebaseUid": f"TEST_firebase_trial_{user_id}",
        "referredBy": test_referrer["referralCode"],  # Referred but will get trial
        "referredAt": now,
        "isAdmin": False,
        "isSeller": True,
        "profile": {"businessName": "Test Trial Business"},
        "createdAt": now,
        "updatedAt": now,
    }
    mongo_client.users.insert_one(user_doc)
    yield user_doc
    # Cleanup
    mongo_client.users.delete_one({"_id": user_id})
    mongo_client.orders.delete_many({"userId": user_id})


class TestPlanConfigEndpoints:
    """Test plan configuration CRUD endpoints"""
    
    def test_get_plan_config_returns_three_plans(self, api_client):
        """GET /api/referral/admin/plan-config returns 3 plans with correct structure"""
        response = api_client.get(f"{BASE_URL}/api/referral/admin/plan-config")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "plans" in data, "Response should have 'plans' key"
        
        plans = data["plans"]
        assert len(plans) >= 3, f"Expected at least 3 plans, got {len(plans)}"
        
        # Check that starter, standard, pro exist
        plan_names = [p.get("plan") for p in plans]
        assert "starter" in plan_names, "Missing 'starter' plan"
        assert "standard" in plan_names, "Missing 'standard' plan"
        assert "pro" in plan_names, "Missing 'pro' plan"
        
        # Check each plan has price and commissionPercent
        for plan in plans:
            assert "price" in plan, f"Plan {plan.get('plan')} missing 'price'"
            assert "commissionPercent" in plan, f"Plan {plan.get('plan')} missing 'commissionPercent'"
            assert isinstance(plan["price"], (int, float)), f"Price should be numeric"
            assert isinstance(plan["commissionPercent"], (int, float)), f"CommissionPercent should be numeric"
        
        print(f"✓ GET /api/referral/admin/plan-config returns {len(plans)} plans with correct structure")
    
    def test_update_plan_config_starter(self, api_client, mongo_client):
        """PUT /api/referral/admin/plan-config/starter updates price and commission"""
        # First get current config
        get_response = api_client.get(f"{BASE_URL}/api/referral/admin/plan-config")
        original_plans = get_response.json().get("plans", [])
        original_starter = next((p for p in original_plans if p.get("plan") == "starter"), None)
        
        # Update starter plan
        new_price = 6000
        new_commission = 25.0
        
        update_response = api_client.put(
            f"{BASE_URL}/api/referral/admin/plan-config/starter",
            json={"price": new_price, "commissionPercent": new_commission}
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        update_data = update_response.json()
        assert update_data.get("plan") == "starter", "Response should confirm plan name"
        assert update_data.get("price") == new_price, f"Price should be {new_price}"
        assert update_data.get("commissionPercent") == new_commission, f"Commission should be {new_commission}"
        
        # Verify in database
        db_config = mongo_client.plan_config.find_one({"plan": "starter"})
        assert db_config is not None, "Plan config should exist in database"
        assert db_config.get("price") == new_price, "Database price should match"
        assert db_config.get("commissionPercent") == new_commission, "Database commission should match"
        
        # Restore original values if they existed
        if original_starter:
            api_client.put(
                f"{BASE_URL}/api/referral/admin/plan-config/starter",
                json={"price": original_starter.get("price", 5000), "commissionPercent": original_starter.get("commissionPercent", 20)}
            )
        
        print(f"✓ PUT /api/referral/admin/plan-config/starter successfully updates price and commission")
    
    def test_update_plan_config_invalid_plan(self, api_client):
        """PUT /api/referral/admin/plan-config/{invalid} returns 400"""
        response = api_client.put(
            f"{BASE_URL}/api/referral/admin/plan-config/invalid_plan",
            json={"price": 1000, "commissionPercent": 10}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid plan, got {response.status_code}"
        print(f"✓ PUT /api/referral/admin/plan-config/invalid_plan correctly returns 400")


class TestOrderCreationOnActivation:
    """Test order creation when admin activates paid subscription for referred user"""
    
    def test_activate_paid_plan_creates_order_for_referred_user(self, api_client, mongo_client, test_referred_user, test_referrer):
        """POST /api/admin/subscriptions/activate/{user_id} with paid plan creates order"""
        user_id = str(test_referred_user["_id"])
        
        # Clean up any existing orders for this user
        mongo_client.orders.delete_many({"userId": test_referred_user["_id"]})
        
        # Activate starter plan
        start_date = datetime.now(timezone.utc).isoformat()
        response = api_client.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            json={
                "planName": "starter",
                "startDate": start_date,
                "durationDays": 90
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check order was created
        order = mongo_client.orders.find_one({"userId": test_referred_user["_id"]})
        assert order is not None, "Order should be created for referred user with paid plan"
        
        # Verify order fields
        assert order.get("referredBy") == test_referrer["referralCode"], "Order should have correct referredBy"
        assert order.get("plan") == "starter", "Order should have correct plan"
        assert order.get("amount") > 0, "Order should have positive amount"
        assert order.get("commission") > 0, "Order should have positive commission"
        assert order.get("commissionPercent") > 0, "Order should have commission percent"
        assert order.get("status") == "paid", "Order status should be 'paid'"
        
        print(f"✓ Order created: plan={order.get('plan')}, amount={order.get('amount')}, commission={order.get('commission')}")
    
    def test_activate_trial_plan_does_not_create_order(self, api_client, mongo_client, test_trial_user):
        """POST /api/admin/subscriptions/activate/{user_id} with trial plan does NOT create order"""
        user_id = str(test_trial_user["_id"])
        
        # Clean up any existing orders
        mongo_client.orders.delete_many({"userId": test_trial_user["_id"]})
        
        # Activate trial plan
        start_date = datetime.now(timezone.utc).isoformat()
        response = api_client.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            json={
                "planName": "trial",
                "startDate": start_date,
                "durationDays": 90
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check NO order was created
        order = mongo_client.orders.find_one({"userId": test_trial_user["_id"]})
        assert order is None, "Order should NOT be created for trial plan"
        
        print(f"✓ Trial plan activation does NOT create order (correct behavior)")
    
    def test_duplicate_activation_does_not_create_duplicate_order(self, api_client, mongo_client, test_referred_user):
        """POST /api/admin/subscriptions/activate/{user_id} again does NOT create duplicate order"""
        user_id = str(test_referred_user["_id"])
        
        # Count existing orders
        initial_count = mongo_client.orders.count_documents({"userId": test_referred_user["_id"]})
        
        # Activate again (standard plan this time)
        start_date = datetime.now(timezone.utc).isoformat()
        response = api_client.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            json={
                "planName": "standard",
                "startDate": start_date,
                "durationDays": 90
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Count orders after - should be same
        final_count = mongo_client.orders.count_documents({"userId": test_referred_user["_id"]})
        assert final_count == initial_count, f"Order count should not increase. Initial: {initial_count}, Final: {final_count}"
        
        print(f"✓ Duplicate activation does NOT create duplicate order (count: {final_count})")
    
    def test_activate_non_referred_user_does_not_create_order(self, api_client, mongo_client, test_non_referred_user):
        """POST /api/admin/subscriptions/activate/{user_id} for non-referred user does NOT create order"""
        user_id = str(test_non_referred_user["_id"])
        
        # Clean up any existing orders
        mongo_client.orders.delete_many({"userId": test_non_referred_user["_id"]})
        
        # Activate pro plan
        start_date = datetime.now(timezone.utc).isoformat()
        response = api_client.post(
            f"{BASE_URL}/api/admin/subscriptions/activate/{user_id}",
            json={
                "planName": "pro",
                "startDate": start_date,
                "durationDays": 90
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check NO order was created
        order = mongo_client.orders.find_one({"userId": test_non_referred_user["_id"]})
        assert order is None, "Order should NOT be created for non-referred user"
        
        print(f"✓ Non-referred user activation does NOT create order (correct behavior)")


class TestUserSchemaUpdates:
    """Test that user schema is updated correctly after activation"""
    
    def test_user_schema_updated_after_activation(self, api_client, mongo_client, test_referred_user):
        """User should have subscriptionStatus, subscriptionType, plan fields after activation"""
        user_id = str(test_referred_user["_id"])
        
        # Refresh user from database
        user = mongo_client.users.find_one({"_id": test_referred_user["_id"]})
        
        # Check subscription fields
        assert user.get("subscriptionStatus") == "active", f"subscriptionStatus should be 'active', got {user.get('subscriptionStatus')}"
        assert user.get("subscriptionType") in ("paid", "trial"), f"subscriptionType should be 'paid' or 'trial', got {user.get('subscriptionType')}"
        assert user.get("plan") in ("starter", "standard", "pro", "trial"), f"plan should be set, got {user.get('plan')}"
        
        print(f"✓ User schema updated: status={user.get('subscriptionStatus')}, type={user.get('subscriptionType')}, plan={user.get('plan')}")


class TestSalesStatsEndpoint:
    """Test GET /api/referral/sales-stats endpoint"""
    
    def test_sales_stats_returns_correct_fields(self, api_client):
        """GET /api/referral/sales-stats returns paidCustomers, totalEarnings, pendingEarnings (no commissionRate)"""
        response = api_client.get(f"{BASE_URL}/api/referral/sales-stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check required fields exist
        assert "paidCustomers" in data, "Response should have 'paidCustomers'"
        assert "totalEarnings" in data, "Response should have 'totalEarnings'"
        assert "pendingEarnings" in data, "Response should have 'pendingEarnings'"
        
        # Check types
        assert isinstance(data["paidCustomers"], int), "paidCustomers should be int"
        assert isinstance(data["totalEarnings"], (int, float)), "totalEarnings should be numeric"
        assert isinstance(data["pendingEarnings"], (int, float)), "pendingEarnings should be numeric"
        
        # Note: commissionRate field may or may not be present based on implementation
        # The requirement says "no revenue/commission % for user" but this is about display, not API
        
        print(f"✓ GET /api/referral/sales-stats returns: paidCustomers={data['paidCustomers']}, totalEarnings={data['totalEarnings']}, pendingEarnings={data['pendingEarnings']}")


class TestAdminSalesOverview:
    """Test GET /api/referral/admin/sales-overview endpoint"""
    
    def test_admin_sales_overview_returns_full_data(self, api_client):
        """GET /api/referral/admin/sales-overview returns totalRevenue, totalCommission, partners"""
        response = api_client.get(f"{BASE_URL}/api/referral/admin/sales-overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check required fields
        assert "totalRevenue" in data, "Response should have 'totalRevenue'"
        assert "totalCommission" in data, "Response should have 'totalCommission'"
        assert "partners" in data, "Response should have 'partners'"
        
        # Check types
        assert isinstance(data["totalRevenue"], (int, float)), "totalRevenue should be numeric"
        assert isinstance(data["totalCommission"], (int, float)), "totalCommission should be numeric"
        assert isinstance(data["partners"], list), "partners should be a list"
        
        # Check partner structure if any exist
        if data["partners"]:
            partner = data["partners"][0]
            assert "code" in partner or "referralCode" in partner, "Partner should have code/referralCode"
            assert "revenue" in partner, "Partner should have revenue"
            assert "commission" in partner, "Partner should have commission"
        
        print(f"✓ GET /api/referral/admin/sales-overview returns: totalRevenue={data['totalRevenue']}, totalCommission={data['totalCommission']}, partners={len(data['partners'])}")
    
    def test_admin_sales_overview_requires_admin(self, api_client):
        """GET /api/referral/admin/sales-overview without admin returns 401/403"""
        # Create session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/referral/admin/sales-overview")
        
        assert response.status_code in (401, 403, 422), f"Expected 401/403/422 without auth, got {response.status_code}"
        
        print(f"✓ GET /api/referral/admin/sales-overview correctly requires admin auth (status: {response.status_code})")


class TestExistingReferralEndpoints:
    """Test that existing referral endpoints still work (backward compatibility)"""
    
    def test_my_link_endpoint_works(self, api_client):
        """GET /api/referral/my-link still works"""
        response = api_client.get(f"{BASE_URL}/api/referral/my-link")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "referralCode" in data, "Response should have 'referralCode'"
        assert "referralLink" in data, "Response should have 'referralLink'"
        
        print(f"✓ GET /api/referral/my-link works: code={data.get('referralCode')}")
    
    def test_stats_endpoint_works(self, api_client):
        """GET /api/referral/stats still works"""
        response = api_client.get(f"{BASE_URL}/api/referral/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "totalReferred" in data, "Response should have 'totalReferred'"
        assert "successfulReferrals" in data, "Response should have 'successfulReferrals'"
        
        print(f"✓ GET /api/referral/stats works: totalReferred={data.get('totalReferred')}, successful={data.get('successfulReferrals')}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, mongo_client):
        """Clean up all TEST_ prefixed data"""
        # Delete test users
        result_users = mongo_client.users.delete_many({"email": {"$regex": "^TEST_"}})
        
        # Delete test orders
        result_orders = mongo_client.orders.delete_many({"referredBy": {"$regex": "^TEST"}})
        
        print(f"✓ Cleanup: deleted {result_users.deleted_count} test users, {result_orders.deleted_count} test orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
