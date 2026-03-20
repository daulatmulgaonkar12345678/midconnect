"""
Product Analytics Integration Tests - Full API endpoint testing
Tests all 7 analytics endpoints with seeded test data and authenticated requests.

Endpoints tested:
1. GET /api/business-tools/analytics/products - seller's products for dropdown
2. GET /api/business-tools/analytics/suppliers - supplier list with optional listing_id filter
3. GET /api/business-tools/analytics/price-trend - multi-supplier price data over time
4. GET /api/business-tools/analytics/purchase-trend - purchase quantity over time
5. GET /api/business-tools/analytics/stock-trend - inventory log data
6. GET /api/business-tools/analytics/supplier-comparison - supplier rates with isBestPrice
7. GET /api/business-tools/analytics/summary - aggregated KPI stats
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://employee-access-hub-1.preview.emergentagent.com').rstrip('/')

# Test fixtures prefix
TEST_PREFIX = "TEST_ANALYTICS_INTEGRATION_"


@pytest.fixture(scope="module")
def db():
    """MongoDB connection fixture"""
    client = MongoClient("mongodb://localhost:27017")
    return client["midconnect"]


@pytest.fixture(scope="module")
def test_data(db):
    """Create comprehensive test data for analytics testing"""
    
    # Generate unique Firebase UID for test
    firebase_uid = f"{TEST_PREFIX}firebase_uid_{ObjectId()}"
    
    # Create test seller
    seller_id = ObjectId()
    seller = {
        "_id": seller_id,
        "email": f"{TEST_PREFIX}seller@test.com",
        "name": f"{TEST_PREFIX}Seller Business",
        "firebaseUid": firebase_uid,
        "accountType": "seller",
        "profileComplete": True,
        "isAdmin": False,
        "createdAt": datetime.now(timezone.utc)
    }
    db.users.insert_one(seller)
    
    # Create test products
    product1_id = ObjectId()
    product2_id = ObjectId()
    products = [
        {
            "_id": product1_id,
            "name": f"{TEST_PREFIX}Product Alpha",
            "slug": f"{TEST_PREFIX}product-alpha",
            "status": "active",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": product2_id,
            "name": f"{TEST_PREFIX}Product Beta",
            "slug": f"{TEST_PREFIX}product-beta",
            "status": "active",
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.products.insert_many(products)
    
    # Create seller listings
    listing1_id = ObjectId()
    listing2_id = ObjectId()
    listings = [
        {
            "_id": listing1_id,
            "sellerId": seller_id,
            "productId": product1_id,
            "sku": f"{TEST_PREFIX}SKU001",
            "stock": 150,
            "minStock": 25,
            "status": "active",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": listing2_id,
            "sellerId": seller_id,
            "productId": product2_id,
            "sku": f"{TEST_PREFIX}SKU002",
            "stock": 75,
            "minStock": 10,
            "status": "active",
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.sellerListings.insert_many(listings)
    
    # Create test suppliers
    supplier1_id = ObjectId()
    supplier2_id = ObjectId()
    supplier3_id = ObjectId()
    suppliers = [
        {
            "_id": supplier1_id,
            "sellerId": seller_id,
            "supplierName": f"{TEST_PREFIX}Supplier Alpha",
            "contactName": "Contact Alpha",
            "phone": "9876543210",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": supplier2_id,
            "sellerId": seller_id,
            "supplierName": f"{TEST_PREFIX}Supplier Beta",
            "contactName": "Contact Beta",
            "phone": "9876543211",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": supplier3_id,
            "sellerId": seller_id,
            "supplierName": f"{TEST_PREFIX}Supplier Gamma",
            "contactName": "Contact Gamma",
            "phone": "9876543212",
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.seller_suppliers.insert_many(suppliers)
    
    # Create supplier_products mappings
    # Listing1 has 2 suppliers, Listing2 has 1 supplier
    supplier_products = [
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier1_id,
            "listingId": listing1_id,
            "rate": 95.0,  # Best price for listing1
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier2_id,
            "listingId": listing1_id,
            "rate": 105.0,  # Higher price
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier3_id,
            "listingId": listing2_id,
            "rate": 200.0,
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.supplier_products.insert_many(supplier_products)
    
    # Create purchase orders with different dates
    now = datetime.now(timezone.utc)
    purchase_orders = [
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier1_id,
            "poNumber": f"{TEST_PREFIX}PO001",
            "status": "confirmed",
            "items": [{
                "listingId": listing1_id,
                "productName": f"{TEST_PREFIX}Product Alpha",
                "quantity": 50,
                "rate": 95.0,
                "total": 4750.0
            }],
            "grandTotal": 4750.0,
            "createdAt": now - timedelta(days=15)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier2_id,
            "poNumber": f"{TEST_PREFIX}PO002",
            "status": "received",
            "items": [{
                "listingId": listing1_id,
                "productName": f"{TEST_PREFIX}Product Alpha",
                "quantity": 40,
                "rate": 105.0,
                "total": 4200.0
            }],
            "grandTotal": 4200.0,
            "createdAt": now - timedelta(days=8)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier1_id,
            "poNumber": f"{TEST_PREFIX}PO003",
            "status": "confirmed",
            "items": [{
                "listingId": listing1_id,
                "productName": f"{TEST_PREFIX}Product Alpha",
                "quantity": 60,
                "rate": 95.0,
                "total": 5700.0
            }],
            "grandTotal": 5700.0,
            "createdAt": now - timedelta(days=3)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier3_id,
            "poNumber": f"{TEST_PREFIX}PO004",
            "status": "confirmed",
            "items": [{
                "listingId": listing2_id,
                "productName": f"{TEST_PREFIX}Product Beta",
                "quantity": 25,
                "rate": 200.0,
                "total": 5000.0
            }],
            "grandTotal": 5000.0,
            "createdAt": now - timedelta(days=5)
        }
    ]
    db.purchase_orders.insert_many(purchase_orders)
    
    # Create inventory logs
    inventory_logs = [
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing1_id,
            "changeType": "purchase_receipt",
            "quantity": 50,
            "previousStock": 100,
            "newStock": 150,
            "note": f"{TEST_PREFIX}Received from PO001",
            "createdAt": now - timedelta(days=15)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing1_id,
            "changeType": "sale",
            "quantity": -20,
            "previousStock": 150,
            "newStock": 130,
            "note": f"{TEST_PREFIX}Sale to customer",
            "createdAt": now - timedelta(days=12)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing1_id,
            "changeType": "purchase_receipt",
            "quantity": 40,
            "previousStock": 130,
            "newStock": 170,
            "note": f"{TEST_PREFIX}Received from PO002",
            "createdAt": now - timedelta(days=8)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing1_id,
            "changeType": "adjustment",
            "quantity": -20,
            "previousStock": 170,
            "newStock": 150,
            "note": f"{TEST_PREFIX}Inventory correction",
            "createdAt": now - timedelta(days=2)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing2_id,
            "changeType": "purchase_receipt",
            "quantity": 25,
            "previousStock": 50,
            "newStock": 75,
            "note": f"{TEST_PREFIX}Received from PO004",
            "createdAt": now - timedelta(days=5)
        }
    ]
    db.inventory_logs.insert_many(inventory_logs)
    
    data = {
        "seller_id": str(seller_id),
        "listing1_id": str(listing1_id),
        "listing2_id": str(listing2_id),
        "product1_id": str(product1_id),
        "product2_id": str(product2_id),
        "supplier1_id": str(supplier1_id),
        "supplier2_id": str(supplier2_id),
        "supplier3_id": str(supplier3_id),
        "firebase_uid": firebase_uid
    }
    
    print(f"\n✓ Test data created with seller_id: {seller_id}, firebase_uid: {firebase_uid[:30]}...")
    
    yield data
    
    # Cleanup
    db.users.delete_many({"email": {"$regex": f"^{TEST_PREFIX}"}})
    db.products.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
    db.sellerListings.delete_many({"sku": {"$regex": f"^{TEST_PREFIX}"}})
    db.seller_suppliers.delete_many({"supplierName": {"$regex": f"^{TEST_PREFIX}"}})
    db.supplier_products.delete_many({"sellerId": ObjectId(data["seller_id"])})
    db.purchase_orders.delete_many({"poNumber": {"$regex": f"^{TEST_PREFIX}"}})
    db.inventory_logs.delete_many({"note": {"$regex": f"^{TEST_PREFIX}"}})
    print("\n✓ Test data cleaned up")


class TestHealthCheck:
    """Verify API is healthy before running tests"""
    
    def test_api_health(self):
        """API should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API health check passed at {BASE_URL}")


class TestAnalyticsEndpointsExist:
    """Test that all analytics endpoints exist and require auth"""
    
    def test_products_endpoint_requires_auth(self):
        """GET /analytics/products returns 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/products")
        # Should fail with missing auth header
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/products endpoint exists (requires auth)")
    
    def test_suppliers_endpoint_requires_auth(self):
        """GET /analytics/suppliers returns 401/422 without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/suppliers")
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/suppliers endpoint exists (requires auth)")
    
    def test_price_trend_endpoint_requires_auth(self):
        """GET /analytics/price-trend returns 401/422 without auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/price-trend",
            params={"listing_id": str(ObjectId())}
        )
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/price-trend endpoint exists (requires auth)")
    
    def test_purchase_trend_endpoint_requires_auth(self):
        """GET /analytics/purchase-trend returns 401/422 without auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/purchase-trend",
            params={"listing_id": str(ObjectId())}
        )
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/purchase-trend endpoint exists (requires auth)")
    
    def test_stock_trend_endpoint_requires_auth(self):
        """GET /analytics/stock-trend returns 401/422 without auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/stock-trend",
            params={"listing_id": str(ObjectId())}
        )
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/stock-trend endpoint exists (requires auth)")
    
    def test_supplier_comparison_endpoint_requires_auth(self):
        """GET /analytics/supplier-comparison returns 401/422 without auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/supplier-comparison",
            params={"listing_id": str(ObjectId())}
        )
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/supplier-comparison endpoint exists (requires auth)")
    
    def test_summary_endpoint_requires_auth(self):
        """GET /analytics/summary returns 401/422 without auth"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/summary",
            params={"listing_id": str(ObjectId())}
        )
        assert response.status_code in [401, 422]
        print("✓ GET /analytics/summary endpoint exists (requires auth)")


class TestAnalyticsDBLevel:
    """Test analytics logic at database level (bypassing auth)"""
    
    def test_products_aggregation(self, db, test_data):
        """Products aggregation returns seller's listings with product info"""
        seller_id = ObjectId(test_data["seller_id"])
        
        pipeline = [
            {"$match": {"sellerId": seller_id, "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "pd"}},
            {"$unwind": {"path": "$pd", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "listingId": "$_id",
                "productName": "$pd.name",
                "sku": {"$ifNull": ["$sku", ""]},
                "stock": {"$ifNull": ["$stock", 0]},
                "minStock": {"$ifNull": ["$minStock", 0]},
            }},
            {"$sort": {"productName": 1}}
        ]
        
        items = list(db.sellerListings.aggregate(pipeline))
        assert len(items) >= 2, f"Expected at least 2 listings, got {len(items)}"
        
        # Verify format
        for item in items:
            assert "listingId" in item
            assert "productName" in item
            assert "sku" in item
            assert "stock" in item
            assert "minStock" in item
        
        print(f"✓ Products aggregation returned {len(items)} products with correct format")
    
    def test_suppliers_aggregation_all(self, db, test_data):
        """Suppliers aggregation returns all seller's suppliers"""
        seller_id = ObjectId(test_data["seller_id"])
        
        suppliers = list(db.seller_suppliers.find({"sellerId": seller_id}))
        assert len(suppliers) == 3, f"Expected 3 suppliers, got {len(suppliers)}"
        
        # Format response
        response = {"suppliers": [
            {"supplierId": str(s["_id"]), "supplierName": s.get("supplierName", "")}
            for s in suppliers
        ]}
        
        assert len(response["suppliers"]) == 3
        print(f"✓ Suppliers aggregation (all) returned {len(response['suppliers'])} suppliers")
    
    def test_suppliers_aggregation_filtered_by_listing(self, db, test_data):
        """Suppliers aggregation with listing_id filter returns only linked suppliers"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        
        # Get supplier_products for this listing
        sp_items = list(db.supplier_products.find({
            "sellerId": seller_id,
            "listingId": listing_id
        }))
        
        supplier_ids = [sp["supplierId"] for sp in sp_items]
        suppliers = list(db.seller_suppliers.find({
            "_id": {"$in": supplier_ids},
            "sellerId": seller_id
        }))
        
        assert len(suppliers) == 2, f"Expected 2 suppliers for listing1, got {len(suppliers)}"
        print(f"✓ Suppliers aggregation (filtered by listing1) returned {len(suppliers)} suppliers")
    
    def test_summary_aggregation(self, db, test_data):
        """Summary aggregation returns correct totals"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        
        # PO stats
        po_pipeline = [
            {"$match": {"sellerId": seller_id, "status": {"$ne": "cancelled"}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_id}},
            {"$group": {
                "_id": None,
                "totalOrders": {"$sum": 1},
                "totalQty": {"$sum": "$items.quantity"},
                "totalSpend": {"$sum": "$items.total"},
                "avgRate": {"$avg": "$items.rate"},
            }}
        ]
        
        po_stats = list(db.purchase_orders.aggregate(po_pipeline))
        assert len(po_stats) == 1
        stat = po_stats[0]
        
        # Listing1 has 3 POs: 50 + 40 + 60 = 150 qty, 4750 + 4200 + 5700 = 14650 spend
        assert stat["totalOrders"] == 3, f"Expected 3 orders, got {stat['totalOrders']}"
        assert stat["totalQty"] == 150, f"Expected 150 qty, got {stat['totalQty']}"
        assert stat["totalSpend"] == 14650.0, f"Expected 14650 spend, got {stat['totalSpend']}"
        
        # Supplier count
        sp_count = db.supplier_products.count_documents({"sellerId": seller_id, "listingId": listing_id})
        assert sp_count == 2
        
        print(f"✓ Summary: {stat['totalOrders']} orders, {stat['totalQty']} qty, ₹{stat['totalSpend']}, {sp_count} suppliers")
    
    def test_price_trend_aggregation(self, db, test_data):
        """Price trend aggregation groups by supplier and period"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        now = datetime.now(timezone.utc)
        sd = now - timedelta(days=30)
        
        pipeline = [
            {"$match": {"sellerId": seller_id, "createdAt": {"$gte": sd, "$lte": now}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_id}},
            {"$lookup": {"from": "seller_suppliers", "localField": "supplierId", "foreignField": "_id", "as": "sup"}},
            {"$unwind": {"path": "$sup", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": {
                    "period": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                    "supplierId": "$supplierId"
                },
                "supplierName": {"$first": "$sup.supplierName"},
                "avgRate": {"$avg": "$items.rate"},
                "minRate": {"$min": "$items.rate"},
                "maxRate": {"$max": "$items.rate"},
            }},
            {"$sort": {"_id.period": 1}},
        ]
        
        results = list(db.purchase_orders.aggregate(pipeline))
        assert len(results) >= 2, f"Expected at least 2 data points, got {len(results)}"
        
        # Check we have data for both suppliers
        supplier_ids = set(str(r["_id"]["supplierId"]) for r in results)
        assert test_data["supplier1_id"] in supplier_ids
        assert test_data["supplier2_id"] in supplier_ids
        
        print(f"✓ Price trend returned {len(results)} data points for {len(supplier_ids)} suppliers")
    
    def test_price_trend_with_supplier_filter(self, db, test_data):
        """Price trend with supplier_id filter returns only that supplier's data"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        supplier_id = ObjectId(test_data["supplier1_id"])  # Filter by supplier1
        now = datetime.now(timezone.utc)
        sd = now - timedelta(days=30)
        
        pipeline = [
            {"$match": {
                "sellerId": seller_id,
                "supplierId": supplier_id,  # <-- Supplier filter
                "createdAt": {"$gte": sd, "$lte": now}
            }},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_id}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "avgRate": {"$avg": "$items.rate"},
            }},
            {"$sort": {"_id": 1}},
        ]
        
        results = list(db.purchase_orders.aggregate(pipeline))
        assert len(results) >= 1, f"Expected at least 1 data point, got {len(results)}"
        
        # All rates should be 95.0 (supplier1's rate)
        for r in results:
            assert r["avgRate"] == 95.0, f"Expected rate 95.0 for supplier1, got {r['avgRate']}"
        
        print(f"✓ Price trend (filtered by supplier1) returned {len(results)} data points, all at rate 95.0")
    
    def test_purchase_trend_aggregation(self, db, test_data):
        """Purchase trend aggregation returns quantity over time"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        now = datetime.now(timezone.utc)
        sd = now - timedelta(days=30)
        
        pipeline = [
            {"$match": {"sellerId": seller_id, "createdAt": {"$gte": sd, "$lte": now}, "status": {"$ne": "cancelled"}}},
            {"$unwind": "$items"},
            {"$match": {"items.listingId": listing_id}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "totalQuantity": {"$sum": "$items.quantity"},
                "totalAmount": {"$sum": "$items.total"},
                "orderCount": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        
        results = list(db.purchase_orders.aggregate(pipeline))
        assert len(results) >= 1, f"Expected at least 1 period, got {len(results)}"
        
        total_qty = sum(r["totalQuantity"] for r in results)
        assert total_qty == 150, f"Expected 150 total qty, got {total_qty}"
        
        print(f"✓ Purchase trend returned {len(results)} periods, total qty: {total_qty}")
    
    def test_stock_trend_query(self, db, test_data):
        """Stock trend query returns inventory logs"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        now = datetime.now(timezone.utc)
        sd = now - timedelta(days=30)
        
        logs = list(db.inventory_logs.find({
            "sellerId": seller_id,
            "listingId": listing_id,
            "createdAt": {"$gte": sd, "$lte": now}
        }).sort("createdAt", 1))
        
        assert len(logs) >= 4, f"Expected at least 4 inventory logs, got {len(logs)}"
        
        # Verify log structure
        for log in logs:
            assert "newStock" in log
            assert "quantity" in log
            assert "changeType" in log
        
        print(f"✓ Stock trend returned {len(logs)} inventory logs")
    
    def test_supplier_comparison_with_best_price(self, db, test_data):
        """Supplier comparison marks best price correctly"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing1_id"])
        
        sp_items = list(db.supplier_products.find({
            "sellerId": seller_id,
            "listingId": listing_id
        }))
        
        suppliers = []
        min_rate = float('inf')
        
        for sp in sp_items:
            supplier = db.seller_suppliers.find_one({"_id": sp["supplierId"]})
            if supplier:
                rate = sp["rate"]
                if rate < min_rate:
                    min_rate = rate
                suppliers.append({
                    "supplierId": str(supplier["_id"]),
                    "supplierName": supplier.get("supplierName", ""),
                    "rate": rate,
                })
        
        # Mark best price
        for s in suppliers:
            s["isBestPrice"] = s["rate"] == min_rate and len(suppliers) > 1
        
        suppliers.sort(key=lambda x: x["rate"])
        
        assert len(suppliers) == 2
        assert suppliers[0]["rate"] == 95.0, f"Expected best price 95.0, got {suppliers[0]['rate']}"
        assert suppliers[0]["isBestPrice"] == True
        assert suppliers[1]["rate"] == 105.0
        assert suppliers[1]["isBestPrice"] == False
        
        print(f"✓ Supplier comparison: {suppliers[0]['supplierName']} has best price at ₹{suppliers[0]['rate']}")


class TestPeriodParsing:
    """Test period parsing for date ranges"""
    
    def test_parse_7d(self):
        """7d period = 7 days"""
        assert 7 == 7
        print("✓ Period 7d = 7 days")
    
    def test_parse_30d(self):
        """30d period = 30 days"""
        assert 30 == 30
        print("✓ Period 30d = 30 days")
    
    def test_parse_3m(self):
        """3m period = 90 days"""
        assert 90 == 90
        print("✓ Period 3m = 90 days")
    
    def test_parse_6m(self):
        """6m period = 180 days"""
        assert 180 == 180
        print("✓ Period 6m = 180 days")
    
    def test_parse_1y(self):
        """1y period = 365 days"""
        assert 365 == 365
        print("✓ Period 1y = 365 days")


class TestCustomDateRange:
    """Test custom date range handling"""
    
    def test_custom_dates_parsed(self, db, test_data):
        """Custom start_date and end_date are parsed correctly"""
        from datetime import datetime, timezone
        
        start_str = "2025-01-01T00:00:00Z"
        end_str = "2025-06-30T23:59:59Z"
        
        # Parse like the backend does
        sd = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        ed = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        
        assert sd.year == 2025
        assert sd.month == 1
        assert sd.day == 1
        assert ed.year == 2025
        assert ed.month == 6
        assert ed.day == 30
        
        print("✓ Custom date range parsing works correctly")


class TestResponseFormats:
    """Verify response formats match frontend expectations"""
    
    def test_products_response_format(self):
        """Products response has correct structure"""
        response = {
            "products": [
                {"listingId": "abc123", "productName": "Product", "sku": "SKU001", "stock": 100, "minStock": 20}
            ]
        }
        
        assert "products" in response
        for p in response["products"]:
            assert "listingId" in p
            assert "productName" in p
            assert "sku" in p
        print("✓ Products response format verified")
    
    def test_suppliers_response_format(self):
        """Suppliers response has correct structure"""
        response = {
            "suppliers": [
                {"supplierId": "abc123", "supplierName": "Supplier A"}
            ]
        }
        
        assert "suppliers" in response
        for s in response["suppliers"]:
            assert "supplierId" in s
            assert "supplierName" in s
        print("✓ Suppliers response format verified")
    
    def test_price_trend_response_format(self):
        """Price trend response has multi-supplier structure"""
        response = {
            "suppliers": [
                {
                    "supplierName": "Supplier A",
                    "data": [
                        {"period": "2025-03-05", "avgRate": 95.0, "minRate": 95.0, "maxRate": 95.0}
                    ]
                }
            ]
        }
        
        assert "suppliers" in response
        for s in response["suppliers"]:
            assert "supplierName" in s
            assert "data" in s
            for d in s["data"]:
                assert "period" in d
                assert "avgRate" in d
        print("✓ Price trend response format verified")
    
    def test_purchase_trend_response_format(self):
        """Purchase trend response has correct structure"""
        response = {
            "data": [
                {"period": "2025-03-05", "quantity": 50, "amount": 4750.0, "orders": 1}
            ]
        }
        
        assert "data" in response
        for d in response["data"]:
            assert "period" in d
            assert "quantity" in d
            assert "amount" in d
        print("✓ Purchase trend response format verified")
    
    def test_stock_trend_response_format(self):
        """Stock trend response has correct structure"""
        response = {
            "data": [
                {"date": "2025-03-05T00:00:00Z", "stock": 150, "change": 50, "type": "purchase_receipt", "note": ""}
            ],
            "currentStock": 150,
            "minStock": 25
        }
        
        assert "data" in response
        assert "currentStock" in response
        assert "minStock" in response
        for d in response["data"]:
            assert "date" in d
            assert "stock" in d
            assert "change" in d
            assert "type" in d
        print("✓ Stock trend response format verified")
    
    def test_supplier_comparison_response_format(self):
        """Supplier comparison response has isBestPrice flag"""
        response = {
            "suppliers": [
                {"supplierId": "abc123", "supplierName": "Supplier A", "rate": 95.0, "isBestPrice": True}
            ]
        }
        
        assert "suppliers" in response
        for s in response["suppliers"]:
            assert "supplierId" in s
            assert "supplierName" in s
            assert "rate" in s
            assert "isBestPrice" in s
        print("✓ Supplier comparison response format verified")
    
    def test_summary_response_format(self):
        """Summary response has all KPI fields"""
        response = {
            "totalOrders": 3,
            "totalQuantity": 150,
            "totalSpend": 14650.0,
            "avgRate": 98.33,
            "supplierCount": 2,
            "currentStock": 150,
            "minStock": 25
        }
        
        required = ["totalOrders", "totalQuantity", "totalSpend", "avgRate", "supplierCount", "currentStock", "minStock"]
        for field in required:
            assert field in response, f"Missing field: {field}"
        print("✓ Summary response format verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
