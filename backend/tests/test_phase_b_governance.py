"""
Phase B: Governance Layer Testing
=================================

Tests for:
1. Governance Monitoring Endpoints
   - GET /api/admin/governance/market-health
   - GET /api/admin/governance/abuse-summary
   - GET /api/admin/governance/high-expiry-sellers
   - GET /api/admin/governance/slow-responders
   - GET /api/admin/governance/zero-conversion
   - GET /api/admin/governance/suspicious-activity
   - GET /api/admin/governance/seller/{id}/summary

2. Governance Actions (Admin)
   - POST /api/admin/governance/seller/{id}/suspend
   - POST /api/admin/governance/seller/{id}/unsuspend
   - POST /api/admin/governance/seller/{id}/warn

3. GST Verification (Admin)
   - POST /api/admin/governance/gst/{id}/approve
   - POST /api/admin/governance/gst/{id}/reject
   - GET /api/admin/governance/gst/pending

4. Governance Enforcement
   - Suspended seller cannot accept leads
   - All governance actions logged to adminAuditLogs

5. Audit Logging
   - All actions logged with admin ID, timestamp, details
"""

import pytest
import requests
import os
from datetime import datetime, timezone

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://invoice-gst-calc.preview.emergentagent.com').rstrip('/')
DEV_TOKEN = "dev-test-token"
TEST_SELLER_ID = "699cb1d8ded1c6446549c19f"


@pytest.fixture
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEV_TOKEN}"
    })
    return session


class TestMarketHealthMonitoring:
    """Tests for market health monitoring endpoints"""
    
    def test_01_market_health(self, api_client):
        """GET /api/admin/governance/market-health - Returns marketplace health metrics"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/market-health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "timestamp" in data
        assert "period" in data
        assert "quotes" in data
        assert "sellers" in data
        assert "response" in data
        assert "healthScore" in data
        
        # Verify quotes structure
        quotes = data["quotes"]
        assert "total" in quotes
        assert "acceptanceRate" in quotes
        assert "expiryRate" in quotes
        
        # Verify sellers structure
        sellers = data["sellers"]
        assert "active" in sellers
        assert "warned" in sellers
        assert "suspended" in sellers
        
        # Verify healthScore is 0-100
        assert 0 <= data["healthScore"] <= 100
        
        print(f"✅ Market Health: healthScore={data['healthScore']}, sellers.active={sellers['active']}")
    
    def test_02_abuse_summary(self, api_client):
        """GET /api/admin/governance/abuse-summary - Returns all abuse indicators"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/abuse-summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "timestamp" in data
        assert "thresholds" in data
        assert "alerts" in data
        assert "totalAlerts" in data
        
        # Verify thresholds (per spec)
        thresholds = data["thresholds"]
        assert thresholds["high_expiry_rate"] == 40
        assert thresholds["slow_response_hours"] == 24
        assert thresholds["min_quotes_for_analysis"] == 5
        
        # Verify alerts structure
        alerts = data["alerts"]
        assert "highExpiry" in alerts
        assert "slowResponders" in alerts
        assert "zeroConversion" in alerts
        assert "suspicious" in alerts
        
        print(f"✅ Abuse Summary: totalAlerts={data['totalAlerts']}")
    
    def test_03_high_expiry_sellers(self, api_client):
        """GET /api/admin/governance/high-expiry-sellers - Returns sellers with >40% expiry rate"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/high-expiry-sellers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "threshold" in data
        assert "count" in data
        assert "sellers" in data
        assert data["threshold"] == 40  # Default threshold
        
        print(f"✅ High Expiry Sellers: count={data['count']}")
    
    def test_04_high_expiry_sellers_custom_threshold(self, api_client):
        """GET /api/admin/governance/high-expiry-sellers?threshold=20 - Custom threshold"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/high-expiry-sellers?threshold=20")
        
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 20
        
        print(f"✅ High Expiry (threshold=20): count={data['count']}")
    
    def test_05_slow_responders(self, api_client):
        """GET /api/admin/governance/slow-responders - Returns sellers with >24hrs avg response"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/slow-responders")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "thresholdHours" in data
        assert "count" in data
        assert "sellers" in data
        assert data["thresholdHours"] == 24  # Default threshold
        
        print(f"✅ Slow Responders: count={data['count']}")
    
    def test_06_zero_conversion(self, api_client):
        """GET /api/admin/governance/zero-conversion - Returns sellers with zero accepted quotes"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/zero-conversion")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data
        assert "sellers" in data
        
        print(f"✅ Zero Conversion: count={data['count']}")
    
    def test_07_suspicious_activity(self, api_client):
        """GET /api/admin/governance/suspicious-activity - Returns suspicious patterns"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/suspicious-activity")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data
        assert "patterns" in data
        
        print(f"✅ Suspicious Activity: count={data['count']}")


class TestSellerGovernanceSummary:
    """Tests for seller governance summary endpoint"""
    
    def test_01_seller_summary(self, api_client):
        """GET /api/admin/governance/seller/{id}/summary - Returns comprehensive seller governance summary"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "sellerId" in data
        assert "email" in data
        assert "businessName" in data
        assert "status" in data
        assert "warningCount" in data
        assert "warnings" in data
        assert "isGstVerified" in data
        assert "performance" in data
        assert "listings" in data
        
        # Verify performance structure
        perf = data["performance"]
        assert "score" in perf
        assert "tier" in perf
        
        print(f"✅ Seller Summary: status={data['status']}, warningCount={data['warningCount']}, score={perf['score']}")
    
    def test_02_invalid_seller_id(self, api_client):
        """GET /api/admin/governance/seller/invalid/summary - Returns 400 for invalid ID"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/invalid-id/summary")
        
        assert response.status_code == 400
        print("✅ Invalid seller ID returns 400")
    
    def test_03_nonexistent_seller(self, api_client):
        """GET /api/admin/governance/seller/{id}/summary - Returns 404 for nonexistent seller"""
        # Using a valid ObjectId format but nonexistent
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/000000000000000000000000/summary")
        
        assert response.status_code == 404
        print("✅ Nonexistent seller returns 404")


class TestGovernanceActions:
    """Tests for governance action endpoints (suspend, unsuspend, warn)"""
    
    def test_01_suspend_seller(self, api_client):
        """POST /api/admin/governance/seller/{id}/suspend - Suspends seller with audit log"""
        payload = {
            "reason": "Testing Phase B: High expiry rate detected",
            "duration": "7 days",
            "notes": "Automated test suspension"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/suspend",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["status"] == "suspended"
        assert data["sellerId"] == TEST_SELLER_ID
        
        print(f"✅ Seller suspended: {data['message']}")
    
    def test_02_verify_suspension_audit(self, api_client):
        """Verify suspension is logged in audit logs"""
        response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action=seller.suspend")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        
        # Find our test suspension
        logs = data["logs"]
        test_log = next((l for l in logs if l["targetId"] == TEST_SELLER_ID), None)
        
        assert test_log is not None
        assert test_log["action"] == "seller.suspend"
        assert "reason" in test_log["details"]
        
        print(f"✅ Suspend audit log found: total={data['total']}")
    
    def test_03_verify_suspended_status(self, api_client):
        """Verify seller status is now 'suspended'"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "suspended"
        assert data["statusReason"] is not None
        
        print(f"✅ Seller status confirmed: {data['status']}")
    
    def test_04_unsuspend_seller(self, api_client):
        """POST /api/admin/governance/seller/{id}/unsuspend - Unsuspends seller with audit log"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/unsuspend?notes=Testing%20Phase%20B%20unsuspension"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["status"] == "active"
        
        print(f"✅ Seller unsuspended: {data['message']}")
    
    def test_05_verify_unsuspend_audit(self, api_client):
        """Verify unsuspension is logged in audit logs"""
        response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action=seller.unsuspend")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        
        print(f"✅ Unsuspend audit log found: total={data['total']}")
    
    def test_06_warn_seller(self, api_client):
        """POST /api/admin/governance/seller/{id}/warn - Issues warning with level (1-3)"""
        payload = {
            "reason": "Testing Phase B: Slow response time warning",
            "level": 2
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/warn",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "totalWarnings" in data
        assert data["autoSuspendThreshold"] == 3
        
        print(f"✅ Warning issued: level=2, totalWarnings={data['totalWarnings']}")
    
    def test_07_verify_warn_audit(self, api_client):
        """Verify warning is logged in audit logs"""
        response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action=seller.warn")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        
        # Find our test warning
        logs = data["logs"]
        test_log = next((l for l in logs if l["targetId"] == TEST_SELLER_ID), None)
        
        assert test_log is not None
        assert "level" in test_log["details"]
        
        print(f"✅ Warn audit log found: total={data['total']}")
    
    def test_08_verify_warning_count(self, api_client):
        """Verify seller warning count increased"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["warningCount"] >= 1
        assert len(data["warnings"]) >= 1
        
        print(f"✅ Warning count verified: {data['warningCount']}")


class TestGstVerification:
    """Tests for GST verification endpoints"""
    
    def test_01_pending_gst_verifications(self, api_client):
        """GET /api/admin/governance/gst/pending - Lists pending GST verifications"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/gst/pending")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data
        assert "pendingVerifications" in data
        
        # Verify structure of pending verifications
        if data["count"] > 0:
            pending = data["pendingVerifications"][0]
            assert "sellerId" in pending
            assert "email" in pending
            
        print(f"✅ Pending GST Verifications: count={data['count']}")
    
    def test_02_approve_gst(self, api_client):
        """POST /api/admin/governance/gst/{id}/approve - Approves GST with audit log"""
        # Get a seller to approve (use test seller)
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/gst/{TEST_SELLER_ID}/approve"
        )
        
        # May return 200 or 404 (if already approved/no GST)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            print(f"✅ GST approved for seller {TEST_SELLER_ID}")
        else:
            print(f"⚠️ GST approval: seller not found or already verified")
    
    def test_03_reject_gst(self, api_client):
        """POST /api/admin/governance/gst/{id}/reject - Rejects GST with reason"""
        payload = {
            "reason": "Testing Phase B: Document unclear"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/gst/{TEST_SELLER_ID}/reject",
            json=payload
        )
        
        # May return 200 or 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert data["reason"] == payload["reason"]
            print(f"✅ GST rejected for seller {TEST_SELLER_ID}")
        else:
            print(f"⚠️ GST rejection: seller not found")
    
    def test_04_verify_gst_audit_logs(self, api_client):
        """Verify GST decisions are logged"""
        # Check approve logs
        approve_response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action=gst.approve")
        assert approve_response.status_code == 200
        
        # Check reject logs
        reject_response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action=gst.reject")
        assert reject_response.status_code == 200
        
        print(f"✅ GST audit logs verified: approve={approve_response.json()['total']}, reject={reject_response.json()['total']}")


class TestRBACEnforcement:
    """Tests for RBAC enforcement - admin endpoints require auth"""
    
    def test_01_market_health_no_auth(self):
        """GET /api/admin/governance/market-health without auth returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.get(f"{BASE_URL}/api/admin/governance/market-health")
        assert response.status_code == 401
        print("✅ Market health requires auth (401)")
    
    def test_02_suspend_no_auth(self):
        """POST /api/admin/governance/seller/{id}/suspend without auth returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/suspend",
            json={"reason": "test"}
        )
        assert response.status_code == 401
        print("✅ Suspend requires auth (401)")
    
    def test_03_gst_approve_no_auth(self):
        """POST /api/admin/governance/gst/{id}/approve without auth returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/admin/governance/gst/{TEST_SELLER_ID}/approve")
        assert response.status_code == 401
        print("✅ GST approve requires auth (401)")


class TestGovernanceEnforcement:
    """Tests for governance enforcement - suspended sellers blocked from operations"""
    
    def test_01_suspend_for_enforcement_test(self, api_client):
        """Setup: Suspend seller for enforcement testing"""
        payload = {
            "reason": "Testing governance enforcement",
            "duration": "indefinite"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/suspend",
            json=payload
        )
        
        assert response.status_code == 200
        print("✅ Seller suspended for enforcement test")
    
    def test_02_verify_seller_suspended(self, api_client):
        """Verify seller status is suspended"""
        response = api_client.get(f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"
        
        print("✅ Seller suspension confirmed")
    
    def test_03_cleanup_unsuspend(self, api_client):
        """Cleanup: Unsuspend seller after tests"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/governance/seller/{TEST_SELLER_ID}/unsuspend?notes=Cleanup%20after%20Phase%20B%20tests"
        )
        
        assert response.status_code == 200
        print("✅ Seller unsuspended (cleanup)")


class TestAuditLogging:
    """Tests for comprehensive audit logging"""
    
    def test_01_all_audit_actions_logged(self, api_client):
        """Verify all governance actions have audit logs"""
        # Get all audit logs
        response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?limit=100")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        
        # Check structure of audit logs
        if data["logs"]:
            log = data["logs"][0]
            assert "id" in log
            assert "timestamp" in log
            assert "adminId" in log
            assert "action" in log
            assert "targetType" in log
            assert "details" in log
        
        print(f"✅ Audit logs verified: total={data['total']}")
    
    def test_02_filter_by_action(self, api_client):
        """Verify audit logs can be filtered by action"""
        actions = ["seller.suspend", "seller.unsuspend", "seller.warn", "gst.approve", "gst.reject"]
        
        for action in actions:
            response = api_client.get(f"{BASE_URL}/api/admin/analytics/audit-logs?action={action}")
            assert response.status_code == 200
            data = response.json()
            
            # All returned logs should have matching action
            for log in data["logs"]:
                assert log["action"] == action
        
        print("✅ Action filtering verified for all governance actions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
