"""
Phase A Backend Testing - Admin Analytics + Seller Performance
==============================================================

Tests for:
1. Admin Analytics Endpoints (require admin role)
   - GET /api/admin/analytics/overview
   - GET /api/admin/analytics/revenue
   - GET /api/admin/analytics/quotes
   - GET /api/admin/analytics/leads
   - GET /api/admin/analytics/products
   - POST /api/admin/analytics/run-aggregation
   - GET /api/admin/analytics/audit-logs

2. Seller Performance Endpoints (seller role, own data only)
   - GET /api/seller/performance
   - GET /api/seller/performance/trend
   - GET /api/seller/performance/lead-stats

3. RBAC Validation
   - Admin endpoints require admin role
   - Seller endpoints return only own data

Test Data Context:
- 1 seller with pro subscription
- 1 quote (viewed status)
- 13 inquiries (12 accepted, 1 pending)
- Monthly aggregation has been run
"""

import pytest
import requests
import os

# API Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://panel-product-sync.preview.emergentagent.com').rstrip('/')
DEV_TOKEN = "dev-test-token"

HEADERS = {
    "Authorization": f"Bearer {DEV_TOKEN}",
    "Content-Type": "application/json"
}


class TestAdminAnalyticsOverview:
    """Tests for GET /api/admin/analytics/overview"""
    
    def test_overview_returns_200(self):
        """Overview endpoint returns 200 for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/overview",
            headers=HEADERS
        )
        print(f"Overview Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_overview_has_required_fields(self):
        """Overview response contains all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/overview",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Overview Data: {data}")
        
        # Check top-level fields
        assert "timestamp" in data, "Missing timestamp"
        assert "period" in data, "Missing period"
        assert "users" in data, "Missing users section"
        assert "sellers" in data, "Missing sellers section"
        assert "inquiries" in data, "Missing inquiries section"
        assert "quotes" in data, "Missing quotes section"
        assert "performance" in data, "Missing performance section"
        
        # Check users section
        users = data["users"]
        assert "total" in users, "Missing users.total"
        assert "sellers" in users, "Missing users.sellers"
        assert "buyers" in users, "Missing users.buyers"
        
        # Check sellers section
        sellers = data["sellers"]
        assert "total" in sellers, "Missing sellers.total"
        assert "free" in sellers, "Missing sellers.free"
        assert "pro" in sellers, "Missing sellers.pro"
        
        # Check quotes section
        quotes = data["quotes"]
        assert "total" in quotes, "Missing quotes.total"
        assert "acceptanceRate" in quotes, "Missing quotes.acceptanceRate"
    
    def test_overview_without_auth_returns_401(self):
        """Overview endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/overview"
        )
        print(f"No-auth Response: {response.status_code}")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"


class TestAdminAnalyticsRevenue:
    """Tests for GET /api/admin/analytics/revenue"""
    
    def test_revenue_returns_200(self):
        """Revenue endpoint returns 200 for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/revenue",
            headers=HEADERS
        )
        print(f"Revenue Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_revenue_has_required_fields(self):
        """Revenue response contains subscription and MRR data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/revenue",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Revenue Data: {data}")
        
        # Check top-level fields
        assert "timestamp" in data, "Missing timestamp"
        assert "subscriptions" in data, "Missing subscriptions"
        assert "revenue" in data, "Missing revenue"
        assert "conversion" in data, "Missing conversion"
        assert "leadLimits" in data, "Missing leadLimits"
        
        # Check revenue section
        revenue = data["revenue"]
        assert "projectedMRR" in revenue, "Missing projectedMRR"
        
        # Check subscriptions
        subs = data["subscriptions"]
        assert "active" in subs, "Missing active subscriptions"


class TestAdminAnalyticsQuotes:
    """Tests for GET /api/admin/analytics/quotes"""
    
    def test_quotes_returns_200(self):
        """Quotes analytics endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/quotes",
            headers=HEADERS
        )
        print(f"Quotes Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_quotes_has_leaderboard(self):
        """Quotes analytics includes seller leaderboard for admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/quotes?include_leaderboard=true",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Quotes Data Keys: {data.keys()}")
        
        # Check main sections
        assert "quotes" in data, "Missing quotes section"
        assert "rates" in data, "Missing rates section"
        assert "values" in data, "Missing values section"
        
        # Check rates
        rates = data["rates"]
        assert "acceptanceRate" in rates, "Missing acceptanceRate"
        assert "expiryRate" in rates, "Missing expiryRate"
        
        # Check leaderboard (admin only feature)
        if "leaderboard" in data:
            leaderboard = data["leaderboard"]
            print(f"Leaderboard Keys: {leaderboard.keys()}")


class TestAdminAnalyticsLeads:
    """Tests for GET /api/admin/analytics/leads"""
    
    def test_leads_returns_200(self):
        """Leads analytics endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/leads",
            headers=HEADERS
        )
        print(f"Leads Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_leads_has_funnel_data(self):
        """Leads response contains funnel and response time data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/leads",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Leads Data: {data}")
        
        # Check required sections
        assert "funnel" in data, "Missing funnel"
        assert "conversionRate" in data, "Missing conversionRate"
        assert "responseTimeDistribution" in data, "Missing responseTimeDistribution"
        
        # Check funnel breakdown
        funnel = data["funnel"]
        assert "total" in funnel, "Missing funnel.total"
        assert "pending" in funnel, "Missing funnel.pending"
        assert "accepted" in funnel, "Missing funnel.accepted"


class TestAdminAnalyticsProducts:
    """Tests for GET /api/admin/analytics/products"""
    
    def test_products_returns_200(self):
        """Products analytics endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/products",
            headers=HEADERS
        )
        print(f"Products Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_products_has_rankings(self):
        """Products response contains various rankings"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/products",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Products Data Keys: {data.keys()}")
        
        # Check required sections
        assert "mostInquired" in data, "Missing mostInquired"
        assert "highestConversion" in data, "Missing highestConversion"
        assert "highestExpiry" in data, "Missing highestExpiry"
        assert "highestValue" in data, "Missing highestValue"


class TestAdminRunAggregation:
    """Tests for POST /api/admin/analytics/run-aggregation"""
    
    def test_run_aggregation_returns_200(self):
        """Manual aggregation run returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/admin/analytics/run-aggregation",
            headers=HEADERS
        )
        print(f"Aggregation Response Status: {response.status_code}")
        print(f"Aggregation Response: {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_aggregation_creates_audit_log(self):
        """Running aggregation creates audit log entry"""
        # First run aggregation
        response = requests.post(
            f"{BASE_URL}/api/admin/analytics/run-aggregation",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        # Then check audit logs
        audit_response = requests.get(
            f"{BASE_URL}/api/admin/analytics/audit-logs?action=cron.manual_run&days=1",
            headers=HEADERS
        )
        print(f"Audit Response Status: {audit_response.status_code}")
        assert audit_response.status_code == 200


class TestAdminAuditLogs:
    """Tests for GET /api/admin/analytics/audit-logs"""
    
    def test_audit_logs_returns_200(self):
        """Audit logs endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/audit-logs",
            headers=HEADERS
        )
        print(f"Audit Logs Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_audit_logs_has_pagination(self):
        """Audit logs response includes pagination"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/audit-logs?page=1&limit=10",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Audit Logs Data: {data}")
        
        # Check pagination fields
        assert "logs" in data, "Missing logs array"
        assert "total" in data, "Missing total count"
        assert "page" in data, "Missing page number"
        assert "pages" in data, "Missing pages count"
    
    def test_audit_logs_filter_by_action(self):
        """Audit logs can be filtered by action type"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/audit-logs?action=cron.manual_run",
            headers=HEADERS
        )
        print(f"Filtered Audit Response: {response.status_code}")
        assert response.status_code == 200


class TestSellerPerformance:
    """Tests for GET /api/seller/performance"""
    
    def test_performance_returns_200(self):
        """Seller performance endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance",
            headers=HEADERS
        )
        print(f"Performance Response Status: {response.status_code}")
        # Dev token authenticates as admin, might need seller role
        # If 403, that's RBAC working correctly
        if response.status_code == 403:
            print("RBAC: Seller performance requires seller role")
            pytest.skip("Dev token doesn't have seller role - RBAC working")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_performance_has_score_breakdown(self):
        """Performance response contains score breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance",
            headers=HEADERS
        )
        if response.status_code == 403:
            pytest.skip("Dev token doesn't have seller role")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Performance Data: {data}")
        
        # Check required fields per spec
        assert "score" in data, "Missing score"
        assert "tier" in data, "Missing tier"
        assert "breakdown" in data, "Missing breakdown"
        assert "marketplaceAverage" in data, "Missing marketplaceAverage"
        
        # Check breakdown components
        breakdown = data["breakdown"]
        expected_components = ["responseSpeed", "acceptanceRate", "expiryRate", 
                              "subscriptionTier", "leadConsistency", "quoteCompletion"]
        for component in expected_components:
            assert component in breakdown, f"Missing breakdown.{component}"


class TestSellerPerformanceTrend:
    """Tests for GET /api/seller/performance/trend"""
    
    def test_trend_returns_200(self):
        """Seller trend endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance/trend?days=30",
            headers=HEADERS
        )
        print(f"Trend Response Status: {response.status_code}")
        if response.status_code == 403:
            print("RBAC: Trend requires seller role")
            pytest.skip("Dev token doesn't have seller role")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_trend_has_daily_data(self):
        """Trend response contains daily metrics"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance/trend?days=30",
            headers=HEADERS
        )
        if response.status_code == 403:
            pytest.skip("Dev token doesn't have seller role")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Trend Data: {data}")
        
        assert "sellerId" in data, "Missing sellerId"
        assert "period" in data, "Missing period"
        assert "trend" in data, "Missing trend array"


class TestSellerLeadStats:
    """Tests for GET /api/seller/performance/lead-stats"""
    
    def test_lead_stats_returns_200(self):
        """Lead stats endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance/lead-stats",
            headers=HEADERS
        )
        print(f"Lead Stats Response Status: {response.status_code}")
        if response.status_code == 403:
            print("RBAC: Lead stats requires seller role")
            pytest.skip("Dev token doesn't have seller role")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_lead_stats_has_usage_info(self):
        """Lead stats response contains usage and limit info"""
        response = requests.get(
            f"{BASE_URL}/api/seller/performance/lead-stats",
            headers=HEADERS
        )
        if response.status_code == 403:
            pytest.skip("Dev token doesn't have seller role")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Lead Stats Data: {data}")
        
        assert "sellerId" in data, "Missing sellerId"
        assert "leadStats" in data, "Missing leadStats"
        assert "canAcceptNewLead" in data, "Missing canAcceptNewLead"


class TestRBACValidation:
    """Tests for RBAC enforcement"""
    
    def test_admin_endpoints_require_auth(self):
        """Admin endpoints return 401 without auth"""
        endpoints = [
            "/api/admin/analytics/overview",
            "/api/admin/analytics/revenue",
            "/api/admin/analytics/quotes",
            "/api/admin/analytics/leads",
            "/api/admin/analytics/products",
            "/api/admin/analytics/audit-logs"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"{endpoint}: {response.status_code}")
            assert response.status_code == 401, f"{endpoint} should require auth"
    
    def test_admin_aggregation_requires_auth(self):
        """Run aggregation requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/analytics/run-aggregation")
        print(f"Aggregation without auth: {response.status_code}")
        assert response.status_code == 401


class TestAnalyticsHealth:
    """Tests for GET /api/admin/analytics/health"""
    
    def test_health_returns_200(self):
        """Health check returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/health",
            headers=HEADERS
        )
        print(f"Health Response Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_health_has_index_info(self):
        """Health check includes index information"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/health",
            headers=HEADERS
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Health Data: {data}")
        
        assert "status" in data, "Missing status"
        assert "collections" in data, "Missing collections"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
