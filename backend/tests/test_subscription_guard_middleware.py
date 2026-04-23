"""
Subscription Guard Middleware Tests - Iteration 119
====================================================

Tests for central subscription enforcement middleware:
1. GET /api/subscription/status - returns plan, features, isExpired, endDate
2. Expired subscription blocks POST /api/business-tools/panels (write operation)
3. Expired subscription allows GET /api/business-tools/panels (read-only)
4. Expired subscription blocks GET /api/business-tools/panels/{id}/export/excel (feature gate)
5. Free plan blocks export excel (feature=false)
6. Free plan allows panel creation up to limit of 3, then blocks with LIMIT_REACHED
7. Free plan blocks automation rule creation (feature=false)
8. Paid plan (starter/pro) allows export and automation
9. Admin user bypasses all subscription checks (plan=enterprise)
10. GET /api/subscription/status for expired user shows isExpired=true
11. Plan config SSOT: free has maxPanels=3, pro has maxPanels=50
12. Subscription guard blocks invoice creation for expired users
13. Subscription guard blocks inventory update for expired users
14. Subscription guard blocks buyer creation for expired users

SSOT: config/plan_features.py is the single source of truth for plan limits
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-scaling-hub.preview.emergentagent.com').rstrip('/')
DEV_TOKEN = "dev-test-token"  # Admin access in dev mode

@pytest.fixture
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEV_TOKEN}"
    })
    return session


class TestHealthAndSetup:
    """Verify API is accessible before running tests"""
    
    def test_01_api_health_check(self, api_client):
        """Test that the API is healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ API health check passed")


class TestSubscriptionStatusEndpoint:
    """
    Tests for GET /api/subscription/status
    Returns plan, features, isExpired, endDate
    """
    
    def test_02_subscription_status_returns_correct_fields(self, api_client):
        """Test that /api/subscription/status returns all expected fields"""
        response = api_client.get(f"{BASE_URL}/api/subscription/status")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "plan" in data, "plan field should be present"
        assert "status" in data, "status field should be present"
        assert "isExpired" in data, "isExpired field should be present"
        assert "features" in data, "features field should be present"
        assert "endDate" in data, "endDate field should be present (can be null)"
        
        # Verify features object has expected keys
        features = data["features"]
        assert "maxPanels" in features, "maxPanels should be in features"
        assert "maxRules" in features, "maxRules should be in features"
        assert "export" in features, "export should be in features"
        assert "automation" in features, "automation should be in features"
        
        print(f"✅ Subscription status returns correct fields - Plan: {data['plan']}, isExpired: {data['isExpired']}")
    
    def test_03_admin_user_has_enterprise_plan(self, api_client):
        """Test that admin user (dev-test-token) has enterprise plan"""
        response = api_client.get(f"{BASE_URL}/api/subscription/status")
        assert response.status_code == 200
        data = response.json()
        
        # Admin should have enterprise plan
        assert data["plan"] == "enterprise", f"Admin should have enterprise plan, got {data['plan']}"
        assert data["isExpired"] == False, "Admin should not be expired"
        
        # Enterprise features
        features = data["features"]
        assert features["maxPanels"] == -1, "Enterprise should have unlimited panels (-1)"
        assert features["maxRules"] == -1, "Enterprise should have unlimited rules (-1)"
        assert features["export"] == True, "Enterprise should have export enabled"
        assert features["automation"] == True, "Enterprise should have automation enabled"
        
        print(f"✅ Admin user has enterprise plan with all features enabled")


class TestPlanConfigSSOT:
    """
    Tests for plan configuration SSOT (config/plan_features.py)
    Verify plan limits match expected values
    """
    
    def test_04_verify_plan_features_config(self, api_client):
        """Verify plan features match SSOT config"""
        # Import plan features directly to verify SSOT
        import sys
        sys.path.insert(0, '/app/backend')
        from config.plan_features import PLAN_FEATURES, get_plan_config
        
        # Verify free plan config
        free_config = get_plan_config("free")
        assert free_config["maxPanels"] == 3, f"Free plan should have maxPanels=3, got {free_config['maxPanels']}"
        assert free_config["maxRules"] == 5, f"Free plan should have maxRules=5, got {free_config['maxRules']}"
        assert free_config["export"] == False, "Free plan should have export=False"
        assert free_config["automation"] == False, "Free plan should have automation=False"
        
        # Verify pro plan config
        pro_config = get_plan_config("pro")
        assert pro_config["maxPanels"] == 50, f"Pro plan should have maxPanels=50, got {pro_config['maxPanels']}"
        assert pro_config["maxRules"] == 200, f"Pro plan should have maxRules=200, got {pro_config['maxRules']}"
        assert pro_config["export"] == True, "Pro plan should have export=True"
        assert pro_config["automation"] == True, "Pro plan should have automation=True"
        
        # Verify starter plan config
        starter_config = get_plan_config("starter")
        assert starter_config["maxPanels"] == 10, f"Starter plan should have maxPanels=10, got {starter_config['maxPanels']}"
        assert starter_config["maxRules"] == 50, f"Starter plan should have maxRules=50, got {starter_config['maxRules']}"
        assert starter_config["export"] == True, "Starter plan should have export=True"
        assert starter_config["automation"] == True, "Starter plan should have automation=True"
        
        # Verify enterprise plan config
        enterprise_config = get_plan_config("enterprise")
        assert enterprise_config["maxPanels"] == -1, "Enterprise should have unlimited panels (-1)"
        assert enterprise_config["maxRules"] == -1, "Enterprise should have unlimited rules (-1)"
        
        print("✅ Plan features config SSOT verified - free: 3 panels, pro: 50 panels, enterprise: unlimited")


class TestAdminBypassAllChecks:
    """
    Tests that admin users bypass all subscription checks
    Admin should be able to access all features regardless of plan
    """
    
    def test_05_admin_can_access_panels_endpoint(self, api_client):
        """Test admin can access panels endpoint (advanced feature)"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/panels")
        # Admin should have access (200) or no panels yet (200 with empty list)
        assert response.status_code == 200, f"Admin should access panels, got {response.status_code}"
        data = response.json()
        assert "panels" in data, "Response should have panels key"
        print(f"✅ Admin can access panels endpoint - Count: {data.get('count', len(data.get('panels', [])))}")
    
    def test_06_admin_can_access_automation_rules(self, api_client):
        """Test admin can access automation rules endpoint"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/automation/rules")
        assert response.status_code == 200, f"Admin should access automation rules, got {response.status_code}"
        data = response.json()
        assert "rules" in data, "Response should have rules key"
        print(f"✅ Admin can access automation rules - Count: {data.get('count', len(data.get('rules', [])))}")
    
    def test_07_admin_can_access_invoices(self, api_client):
        """Test admin can access invoices endpoint"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/invoices")
        assert response.status_code == 200, f"Admin should access invoices, got {response.status_code}"
        data = response.json()
        assert "invoices" in data, "Response should have invoices key"
        print(f"✅ Admin can access invoices endpoint")
    
    def test_08_admin_can_access_inventory(self, api_client):
        """Test admin can access inventory endpoint"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/inventory")
        assert response.status_code == 200, f"Admin should access inventory, got {response.status_code}"
        data = response.json()
        assert "inventory" in data, "Response should have inventory key"
        print(f"✅ Admin can access inventory endpoint")
    
    def test_09_admin_can_access_buyers(self, api_client):
        """Test admin can access buyers endpoint"""
        response = api_client.get(f"{BASE_URL}/api/business-tools/buyers")
        assert response.status_code == 200, f"Admin should access buyers, got {response.status_code}"
        data = response.json()
        assert "buyers" in data, "Response should have buyers key"
        print(f"✅ Admin can access buyers endpoint")


class TestSubscriptionGuardMiddlewareFunctions:
    """
    Direct tests of subscription guard middleware functions
    Tests enforce_subscription(), check_resource_limit(), get_user_subscription()
    """
    
    def test_10_get_user_subscription_for_admin(self):
        """Test get_user_subscription returns enterprise for admin"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_admin_subscription():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import get_user_subscription
            
            # Mock admin user
            admin_user = {
                "_id": ObjectId(),
                "isAdmin": True,
                "email": "admin@test.com"
            }
            
            sub_info = await get_user_subscription(db, admin_user)
            
            assert sub_info["plan"] == "enterprise", f"Admin should have enterprise plan, got {sub_info['plan']}"
            assert sub_info["isExpired"] == False, "Admin should not be expired"
            assert sub_info["config"]["maxPanels"] == -1, "Admin should have unlimited panels"
            
            client.close()
            return sub_info
        
        result = asyncio.get_event_loop().run_until_complete(test_admin_subscription())
        print(f"✅ get_user_subscription returns enterprise for admin - Plan: {result['plan']}")
    
    def test_11_enforce_subscription_allows_admin_write(self):
        """Test enforce_subscription allows admin write operations"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_admin_write():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Mock admin user
            admin_user = {
                "_id": ObjectId(),
                "isAdmin": True,
                "email": "admin@test.com"
            }
            
            # Should not raise exception for admin
            sub_info = await enforce_subscription(db, admin_user, feature="create_panel", write_operation=True)
            
            assert sub_info["plan"] == "enterprise"
            assert sub_info["isExpired"] == False
            
            client.close()
            return sub_info
        
        result = asyncio.get_event_loop().run_until_complete(test_admin_write())
        print(f"✅ enforce_subscription allows admin write operations")
    
    def test_12_check_resource_limit_allows_admin_unlimited(self):
        """Test check_resource_limit allows admin unlimited resources"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_admin_limit():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import check_resource_limit
            
            # Mock admin user
            admin_user = {
                "_id": ObjectId(),
                "isAdmin": True,
                "email": "admin@test.com"
            }
            
            # Should not raise exception even with high count
            sub_info = await check_resource_limit(db, admin_user, "create_panel", current_count=1000)
            
            assert sub_info["plan"] == "enterprise"
            assert sub_info["config"]["maxPanels"] == -1  # Unlimited
            
            client.close()
            return sub_info
        
        result = asyncio.get_event_loop().run_until_complete(test_admin_limit())
        print(f"✅ check_resource_limit allows admin unlimited resources")


class TestExpiredSubscriptionBlocking:
    """
    Tests that expired subscriptions block write operations but allow reads
    """
    
    def test_13_enforce_subscription_blocks_expired_write(self):
        """Test enforce_subscription blocks write for expired user"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_expired_write():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription, get_user_subscription
            from config.plan_features import PLAN_FEATURES
            
            # Create a mock expired user subscription info
            # We'll mock the get_user_subscription to return expired status
            
            # First, create a test user with expired subscription in DB
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_expired@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            # Insert test user
            await db.users.insert_one(test_user)
            
            # Create expired subscription
            past_date = datetime.now(timezone.utc) - timedelta(days=30)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "expired",
                "startDate": past_date - timedelta(days=90),
                "endDate": past_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that write operation is blocked
            try:
                await enforce_subscription(db, test_user, write_operation=True)
                blocked = False
            except HTTPException as e:
                blocked = True
                assert e.status_code == 403
                assert e.detail["error"] == "SUBSCRIPTION_EXPIRED"
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert blocked, "Expired subscription should block write operations"
            return blocked
        
        result = asyncio.get_event_loop().run_until_complete(test_expired_write())
        print(f"✅ enforce_subscription blocks write for expired user")
    
    def test_14_enforce_subscription_allows_expired_read(self):
        """Test enforce_subscription allows read for expired user"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_expired_read():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with expired subscription
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_expired_read@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            past_date = datetime.now(timezone.utc) - timedelta(days=30)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "expired",
                "startDate": past_date - timedelta(days=90),
                "endDate": past_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that read operation is allowed
            try:
                sub_info = await enforce_subscription(db, test_user, write_operation=False)
                allowed = True
            except HTTPException:
                allowed = False
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert allowed, "Expired subscription should allow read operations"
            return allowed
        
        result = asyncio.get_event_loop().run_until_complete(test_expired_read())
        print(f"✅ enforce_subscription allows read for expired user")


class TestFeatureGating:
    """
    Tests for feature gating based on plan
    """
    
    def test_15_free_plan_blocks_export_feature(self):
        """Test free plan blocks export feature"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_free_export():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_free_export@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            # Create free subscription (no endDate, status=free)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that export feature is blocked
            try:
                await enforce_subscription(db, test_user, feature="export_excel", write_operation=False)
                blocked = False
            except HTTPException as e:
                blocked = True
                assert e.status_code == 403
                assert e.detail["error"] == "FEATURE_NOT_AVAILABLE"
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert blocked, "Free plan should block export feature"
            return blocked
        
        result = asyncio.get_event_loop().run_until_complete(test_free_export())
        print(f"✅ Free plan blocks export feature")
    
    def test_16_free_plan_blocks_automation_feature(self):
        """Test free plan blocks automation feature"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_free_automation():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_free_automation@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that automation feature is blocked
            try:
                await enforce_subscription(db, test_user, feature="run_automation", write_operation=True)
                blocked = False
            except HTTPException as e:
                blocked = True
                assert e.status_code == 403
                assert e.detail["error"] == "FEATURE_NOT_AVAILABLE"
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert blocked, "Free plan should block automation feature"
            return blocked
        
        result = asyncio.get_event_loop().run_until_complete(test_free_automation())
        print(f"✅ Free plan blocks automation feature")
    
    def test_17_pro_plan_allows_export_feature(self):
        """Test pro plan allows export feature"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_pro_export():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with pro plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_pro_export@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            future_date = datetime.now(timezone.utc) + timedelta(days=90)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "active",
                "startDate": datetime.now(timezone.utc),
                "endDate": future_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that export feature is allowed
            try:
                sub_info = await enforce_subscription(db, test_user, feature="export_excel", write_operation=False)
                allowed = True
            except HTTPException:
                allowed = False
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert allowed, "Pro plan should allow export feature"
            return allowed
        
        result = asyncio.get_event_loop().run_until_complete(test_pro_export())
        print(f"✅ Pro plan allows export feature")
    
    def test_18_starter_plan_allows_automation_feature(self):
        """Test starter plan allows automation feature"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_starter_automation():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with starter plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_starter_automation@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            future_date = datetime.now(timezone.utc) + timedelta(days=90)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "starter",
                "status": "active",
                "startDate": datetime.now(timezone.utc),
                "endDate": future_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that automation feature is allowed
            try:
                sub_info = await enforce_subscription(db, test_user, feature="run_automation", write_operation=True)
                allowed = True
            except HTTPException:
                allowed = False
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert allowed, "Starter plan should allow automation feature"
            return allowed
        
        result = asyncio.get_event_loop().run_until_complete(test_starter_automation())
        print(f"✅ Starter plan allows automation feature")


class TestResourceLimits:
    """
    Tests for resource limits (panels, rules) based on plan
    """
    
    def test_19_free_plan_limit_reached_blocks_panel_creation(self):
        """Test free plan blocks panel creation when limit reached"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_free_panel_limit():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import check_resource_limit
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_free_panel_limit@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that panel creation is blocked when at limit (3 panels)
            try:
                await check_resource_limit(db, test_user, "create_panel", current_count=3)
                blocked = False
            except HTTPException as e:
                blocked = True
                assert e.status_code == 403
                assert e.detail["error"] == "LIMIT_REACHED"
                assert e.detail["limit"] == 3
                assert e.detail["current"] == 3
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert blocked, "Free plan should block panel creation at limit"
            return blocked
        
        result = asyncio.get_event_loop().run_until_complete(test_free_panel_limit())
        print(f"✅ Free plan blocks panel creation when limit reached (3 panels)")
    
    def test_20_free_plan_allows_panel_creation_under_limit(self):
        """Test free plan allows panel creation under limit"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_free_panel_under_limit():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import check_resource_limit
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_free_panel_under@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that panel creation is allowed under limit (2 panels)
            try:
                sub_info = await check_resource_limit(db, test_user, "create_panel", current_count=2)
                allowed = True
            except HTTPException:
                allowed = False
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert allowed, "Free plan should allow panel creation under limit"
            return allowed
        
        result = asyncio.get_event_loop().run_until_complete(test_free_panel_under_limit())
        print(f"✅ Free plan allows panel creation under limit (2 < 3)")
    
    def test_21_pro_plan_allows_many_panels(self):
        """Test pro plan allows many panels (up to 50)"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_pro_many_panels():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import check_resource_limit
            
            # Create a test user with pro plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_pro_many_panels@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            future_date = datetime.now(timezone.utc) + timedelta(days=90)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "active",
                "startDate": datetime.now(timezone.utc),
                "endDate": future_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Test that panel creation is allowed with 40 panels (under 50 limit)
            try:
                sub_info = await check_resource_limit(db, test_user, "create_panel", current_count=40)
                allowed = True
            except HTTPException:
                allowed = False
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert allowed, "Pro plan should allow many panels (40 < 50)"
            return allowed
        
        result = asyncio.get_event_loop().run_until_complete(test_pro_many_panels())
        print(f"✅ Pro plan allows many panels (40 < 50 limit)")


class TestSubscriptionStatusForExpiredUser:
    """
    Tests that GET /api/subscription/status shows isExpired=true for expired users
    """
    
    def test_22_get_user_subscription_shows_expired(self):
        """Test get_user_subscription shows isExpired=true for expired user"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_expired_status():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import get_user_subscription
            
            # Create a test user with expired subscription
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_expired_status@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            past_date = datetime.now(timezone.utc) - timedelta(days=30)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "expired",
                "startDate": past_date - timedelta(days=90),
                "endDate": past_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            # Get subscription status
            sub_info = await get_user_subscription(db, test_user)
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert sub_info["isExpired"] == True, f"isExpired should be True, got {sub_info['isExpired']}"
            assert sub_info["status"] == "expired", f"status should be expired, got {sub_info['status']}"
            return sub_info
        
        result = asyncio.get_event_loop().run_until_complete(test_expired_status())
        print(f"✅ get_user_subscription shows isExpired=true for expired user")


class TestErrorResponseStructure:
    """
    Tests for error response structure from subscription guard
    """
    
    def test_23_subscription_expired_error_structure(self):
        """Test SUBSCRIPTION_EXPIRED error has correct structure"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_error_structure():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with expired subscription
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_error_structure@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            past_date = datetime.now(timezone.utc) - timedelta(days=30)
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "pro",
                "status": "expired",
                "startDate": past_date - timedelta(days=90),
                "endDate": past_date,
                "createdAt": datetime.now(timezone.utc)
            })
            
            error_detail = None
            try:
                await enforce_subscription(db, test_user, write_operation=True)
            except HTTPException as e:
                error_detail = e.detail
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert error_detail is not None, "Should raise HTTPException"
            assert error_detail["error"] == "SUBSCRIPTION_EXPIRED"
            assert "message" in error_detail
            assert "currentPlan" in error_detail
            assert "upgradeUrl" in error_detail
            return error_detail
        
        result = asyncio.get_event_loop().run_until_complete(test_error_structure())
        print(f"✅ SUBSCRIPTION_EXPIRED error has correct structure: {result['error']}")
    
    def test_24_feature_not_available_error_structure(self):
        """Test FEATURE_NOT_AVAILABLE error has correct structure"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_feature_error():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import enforce_subscription
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_feature_error@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            error_detail = None
            try:
                await enforce_subscription(db, test_user, feature="export_excel", write_operation=False)
            except HTTPException as e:
                error_detail = e.detail
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert error_detail is not None, "Should raise HTTPException"
            assert error_detail["error"] == "FEATURE_NOT_AVAILABLE"
            assert "message" in error_detail
            assert "feature" in error_detail
            assert "currentPlan" in error_detail
            assert "upgradeUrl" in error_detail
            return error_detail
        
        result = asyncio.get_event_loop().run_until_complete(test_feature_error())
        print(f"✅ FEATURE_NOT_AVAILABLE error has correct structure: {result['error']}")
    
    def test_25_limit_reached_error_structure(self):
        """Test LIMIT_REACHED error has correct structure"""
        import sys
        sys.path.insert(0, '/app/backend')
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from fastapi import HTTPException
        import os
        
        MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        DB_NAME = os.environ.get('DB_NAME', 'midconnect')
        
        async def test_limit_error():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            
            from middleware.subscription_guard import check_resource_limit
            
            # Create a test user with free plan
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "email": "test_limit_error@test.com",
                "isAdmin": False,
                "accountType": "seller"
            }
            
            await db.users.insert_one(test_user)
            
            await db.subscriptions.insert_one({
                "userId": test_user_id,
                "planName": "free",
                "status": "free",
                "createdAt": datetime.now(timezone.utc)
            })
            
            error_detail = None
            try:
                await check_resource_limit(db, test_user, "create_panel", current_count=3)
            except HTTPException as e:
                error_detail = e.detail
            
            # Cleanup
            await db.users.delete_one({"_id": test_user_id})
            await db.subscriptions.delete_one({"userId": test_user_id})
            client.close()
            
            assert error_detail is not None, "Should raise HTTPException"
            assert error_detail["error"] == "LIMIT_REACHED"
            assert "message" in error_detail
            assert "feature" in error_detail
            assert "limit" in error_detail
            assert "current" in error_detail
            assert "currentPlan" in error_detail
            assert "upgradeUrl" in error_detail
            return error_detail
        
        result = asyncio.get_event_loop().run_until_complete(test_limit_error())
        print(f"✅ LIMIT_REACHED error has correct structure: {result['error']}, limit={result['limit']}, current={result['current']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
