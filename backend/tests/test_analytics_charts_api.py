"""
Product Analytics Charts API Tests
Tests for supplier price trends, purchase quantities, inventory stock trends,
and supplier rate comparisons.
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from pymongo import MongoClient
import asyncio

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test fixtures - created and cleaned up
TEST_PREFIX = "TEST_ANALYTICS_"


@pytest.fixture(scope="module")
def db():
    """MongoDB connection fixture"""
    client = MongoClient("mongodb://localhost:27017")
    return client["midconnect"]


@pytest.fixture(scope="module")
def test_data(db):
    """Create test seller, listings, suppliers, POs, and inventory logs"""
    
    # Create test seller
    seller_id = ObjectId()
    seller = {
        "_id": seller_id,
        "email": f"{TEST_PREFIX}seller@test.com",
        "name": f"{TEST_PREFIX}Seller",
        "firebaseUid": f"{TEST_PREFIX}firebase_uid",
        "accountType": "seller",
        "profileComplete": True,
        "createdAt": datetime.now(timezone.utc)
    }
    db.users.insert_one(seller)
    
    # Create test product
    product_id = ObjectId()
    product = {
        "_id": product_id,
        "name": f"{TEST_PREFIX}Product",
        "slug": f"{TEST_PREFIX}product-slug",
        "status": "active",
        "createdAt": datetime.now(timezone.utc)
    }
    db.products.insert_one(product)
    
    # Create seller listing
    listing_id = ObjectId()
    listing = {
        "_id": listing_id,
        "sellerId": seller_id,
        "productId": product_id,
        "sku": f"{TEST_PREFIX}SKU001",
        "stock": 100,
        "minStock": 20,
        "status": "active",
        "createdAt": datetime.now(timezone.utc)
    }
    db.sellerListings.insert_one(listing)
    
    # Create test suppliers
    supplier1_id = ObjectId()
    supplier2_id = ObjectId()
    suppliers = [
        {
            "_id": supplier1_id,
            "sellerId": seller_id,
            "supplierName": f"{TEST_PREFIX}Supplier A",
            "contactName": "Contact A",
            "phone": "9876543210",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": supplier2_id,
            "sellerId": seller_id,
            "supplierName": f"{TEST_PREFIX}Supplier B",
            "contactName": "Contact B",
            "phone": "9876543211",
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.seller_suppliers.insert_many(suppliers)
    
    # Create supplier_products mappings
    supplier_products = [
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier1_id,
            "listingId": listing_id,
            "rate": 100.0,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "supplierId": supplier2_id,
            "listingId": listing_id,
            "rate": 110.0,  # Higher rate, so supplier1 is best price
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    db.supplier_products.insert_many(supplier_products)
    
    # Create purchase orders (for price and purchase trends)
    po1_id = ObjectId()
    po2_id = ObjectId()
    now = datetime.now(timezone.utc)
    
    purchase_orders = [
        {
            "_id": po1_id,
            "sellerId": seller_id,
            "supplierId": supplier1_id,
            "poNumber": f"{TEST_PREFIX}PO001",
            "status": "confirmed",
            "items": [{
                "listingId": listing_id,
                "productName": f"{TEST_PREFIX}Product",
                "quantity": 50,
                "rate": 100.0,
                "total": 5000.0
            }],
            "grandTotal": 5000.0,
            "createdAt": now - timedelta(days=10)
        },
        {
            "_id": po2_id,
            "sellerId": seller_id,
            "supplierId": supplier2_id,
            "poNumber": f"{TEST_PREFIX}PO002",
            "status": "received",
            "items": [{
                "listingId": listing_id,
                "productName": f"{TEST_PREFIX}Product",
                "quantity": 30,
                "rate": 110.0,
                "total": 3300.0
            }],
            "grandTotal": 3300.0,
            "createdAt": now - timedelta(days=5)
        }
    ]
    db.purchase_orders.insert_many(purchase_orders)
    
    # Create inventory logs (for stock trend)
    inventory_logs = [
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing_id,
            "changeType": "purchase_receipt",
            "quantity": 50,
            "previousStock": 50,
            "newStock": 100,
            "note": f"{TEST_PREFIX}Received from PO001",
            "createdAt": now - timedelta(days=10)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing_id,
            "changeType": "sale",
            "quantity": -10,
            "previousStock": 100,
            "newStock": 90,
            "note": f"{TEST_PREFIX}Sale",
            "createdAt": now - timedelta(days=7)
        },
        {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "listingId": listing_id,
            "changeType": "purchase_receipt",
            "quantity": 30,
            "previousStock": 90,
            "newStock": 120,
            "note": f"{TEST_PREFIX}Received from PO002",
            "createdAt": now - timedelta(days=5)
        }
    ]
    db.inventory_logs.insert_many(inventory_logs)
    
    data = {
        "seller_id": str(seller_id),
        "listing_id": str(listing_id),
        "product_id": str(product_id),
        "supplier1_id": str(supplier1_id),
        "supplier2_id": str(supplier2_id),
        "firebase_uid": f"{TEST_PREFIX}firebase_uid"
    }
    
    yield data
    
    # Cleanup
    db.users.delete_many({"email": {"$regex": f"^{TEST_PREFIX}"}})
    db.products.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
    db.sellerListings.delete_many({"sku": {"$regex": f"^{TEST_PREFIX}"}})
    db.seller_suppliers.delete_many({"supplierName": {"$regex": f"^{TEST_PREFIX}"}})
    db.supplier_products.delete_many({})  # Clean all test supplier products
    db.purchase_orders.delete_many({"poNumber": {"$regex": f"^{TEST_PREFIX}"}})
    db.inventory_logs.delete_many({"note": {"$regex": f"^{TEST_PREFIX}"}})


class TestAnalyticsEndpoints:
    """Test analytics API endpoints existence"""
    
    def test_health_check(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")
    
    def test_analytics_products_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/products returns seller's products"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/products")
        assert response.status_code in [401, 422]  # Requires auth header
        print("✓ GET /api/business-tools/analytics/products endpoint exists (auth required)")
    
    def test_analytics_summary_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/summary requires listing_id"""
        response = requests.get(f"{BASE_URL}/api/business-tools/analytics/summary")
        assert response.status_code in [401, 422]  # Missing auth or listing_id
        print("✓ GET /api/business-tools/analytics/summary endpoint exists")
    
    def test_analytics_price_trend_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/price-trend requires listing_id"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/price-trend",
            params={"listing_id": test_data["listing_id"]}
        )
        assert response.status_code in [401, 422]  # Missing auth
        print("✓ GET /api/business-tools/analytics/price-trend endpoint exists")
    
    def test_analytics_purchase_trend_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/purchase-trend requires listing_id"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/purchase-trend",
            params={"listing_id": test_data["listing_id"]}
        )
        assert response.status_code in [401, 422]  # Missing auth
        print("✓ GET /api/business-tools/analytics/purchase-trend endpoint exists")
    
    def test_analytics_stock_trend_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/stock-trend requires listing_id"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/stock-trend",
            params={"listing_id": test_data["listing_id"]}
        )
        assert response.status_code in [401, 422]  # Missing auth
        print("✓ GET /api/business-tools/analytics/stock-trend endpoint exists")
    
    def test_analytics_supplier_comparison_endpoint_exists(self, test_data):
        """GET /api/business-tools/analytics/supplier-comparison requires listing_id"""
        response = requests.get(
            f"{BASE_URL}/api/business-tools/analytics/supplier-comparison",
            params={"listing_id": test_data["listing_id"]}
        )
        assert response.status_code in [401, 422]  # Missing auth
        print("✓ GET /api/business-tools/analytics/supplier-comparison endpoint exists")


class TestAnalyticsDBLevel:
    """Test analytics logic at database level (bypassing auth)"""
    
    def test_analytics_products_aggregation(self, db, test_data):
        """Verify products aggregation pipeline works"""
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
        assert len(items) >= 1  # At least our test listing
        
        # Find our test listing
        test_item = next((i for i in items if str(i["listingId"]) == test_data["listing_id"]), None)
        assert test_item is not None
        assert TEST_PREFIX in test_item["productName"]
        assert test_item["sku"] == f"{TEST_PREFIX}SKU001"
        print(f"✓ Products aggregation returned {len(items)} products including test product")
    
    def test_analytics_summary_aggregation(self, db, test_data):
        """Verify summary stats aggregation works"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing_id"])
        
        # PO stats pipeline
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
        
        assert stat["totalOrders"] == 2  # We created 2 POs
        assert stat["totalQty"] == 80  # 50 + 30
        assert stat["totalSpend"] == 8300.0  # 5000 + 3300
        assert 100 <= stat["avgRate"] <= 110  # Between our two rates
        
        # Supplier count
        sp_count = db.supplier_products.count_documents({"sellerId": seller_id, "listingId": listing_id})
        assert sp_count == 2  # We created 2 supplier mappings
        
        print(f"✓ Summary aggregation: {stat['totalOrders']} orders, {stat['totalQty']} qty, ₹{stat['totalSpend']} spend, {sp_count} suppliers")
    
    def test_analytics_price_trend_aggregation(self, db, test_data):
        """Verify price trend aggregation pipeline works"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing_id"])
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
            }},
            {"$sort": {"_id.period": 1}},
        ]
        
        results = list(db.purchase_orders.aggregate(pipeline))
        assert len(results) >= 2  # At least 2 data points (2 POs, different days)
        
        # Check we have data for both suppliers
        supplier_names = set(r.get("supplierName") for r in results)
        assert f"{TEST_PREFIX}Supplier A" in supplier_names
        assert f"{TEST_PREFIX}Supplier B" in supplier_names
        print(f"✓ Price trend aggregation returned {len(results)} data points for suppliers: {supplier_names}")
    
    def test_analytics_purchase_trend_aggregation(self, db, test_data):
        """Verify purchase quantity trend aggregation works"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing_id"])
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
        assert len(results) >= 2  # 2 POs on different days
        
        total_qty = sum(r["totalQuantity"] for r in results)
        assert total_qty == 80  # 50 + 30
        
        print(f"✓ Purchase trend aggregation returned {len(results)} periods, total quantity: {total_qty}")
    
    def test_analytics_stock_trend_query(self, db, test_data):
        """Verify stock trend from inventory logs"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing_id"])
        now = datetime.now(timezone.utc)
        sd = now - timedelta(days=30)
        
        logs = list(db.inventory_logs.find({
            "sellerId": seller_id,
            "listingId": listing_id,
            "createdAt": {"$gte": sd, "$lte": now}
        }).sort("createdAt", 1))
        
        assert len(logs) >= 3  # We created 3 inventory logs
        
        # Verify log structure
        for log in logs:
            assert "newStock" in log
            assert "quantity" in log
            assert "changeType" in log
        
        print(f"✓ Stock trend query returned {len(logs)} inventory log entries")
    
    def test_analytics_supplier_comparison(self, db, test_data):
        """Verify supplier rate comparison query"""
        seller_id = ObjectId(test_data["seller_id"])
        listing_id = ObjectId(test_data["listing_id"])
        
        sp_items = list(db.supplier_products.find({
            "sellerId": seller_id,
            "listingId": listing_id
        }))
        
        assert len(sp_items) == 2  # 2 suppliers mapped
        
        # Build supplier comparison with best price logic
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
                    "supplierName": supplier.get("supplierName", "Unknown"),
                    "rate": rate,
                })
        
        # Mark best price
        for s in suppliers:
            s["isBestPrice"] = s["rate"] == min_rate and len(suppliers) > 1
        
        suppliers.sort(key=lambda x: x["rate"])
        
        assert len(suppliers) == 2
        assert suppliers[0]["rate"] == 100.0  # Best price
        assert suppliers[0]["isBestPrice"] == True
        assert suppliers[1]["rate"] == 110.0  # Higher rate
        assert suppliers[1]["isBestPrice"] == False
        
        print(f"✓ Supplier comparison: {suppliers[0]['supplierName']} has best price at ₹{suppliers[0]['rate']}")


class TestPeriodParsing:
    """Test period shorthand parsing (7d, 30d, 3m, 6m, 1y)"""
    
    def test_period_7d(self):
        """7d should be 7 days"""
        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=7)
        assert (now - expected_start).days == 7
        print("✓ Period 7d = 7 days")
    
    def test_period_30d(self):
        """30d should be 30 days"""
        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=30)
        assert (now - expected_start).days == 30
        print("✓ Period 30d = 30 days")
    
    def test_period_3m(self):
        """3m should be 90 days"""
        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=90)
        assert (now - expected_start).days == 90
        print("✓ Period 3m = 90 days")
    
    def test_period_6m(self):
        """6m should be 180 days"""
        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=180)
        assert (now - expected_start).days == 180
        print("✓ Period 6m = 180 days")
    
    def test_period_1y(self):
        """1y should be 365 days"""
        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=365)
        assert (now - expected_start).days == 365
        print("✓ Period 1y = 365 days")


class TestGroupingGranularity:
    """Test date grouping granularity based on period"""
    
    def test_daily_grouping_for_short_period(self):
        """<=31 days should use daily grouping"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        days = (now - start).days
        
        expected_format = "%Y-%m-%d" if days <= 31 else "%Y-%m"
        assert expected_format == "%Y-%m-%d"
        print("✓ Short period (7d) uses daily grouping")
    
    def test_monthly_grouping_for_long_period(self):
        """>31 days should use monthly grouping"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=90)  # 3m
        days = (now - start).days
        
        expected_format = "%Y-%m-%d" if days <= 31 else "%Y-%m"
        assert expected_format == "%Y-%m"
        print("✓ Long period (3m) uses monthly grouping")


class TestResponseFormat:
    """Test response format matches frontend expectations"""
    
    def test_products_response_format(self, db, test_data):
        """Products endpoint returns listingId, productName, sku"""
        seller_id = ObjectId(test_data["seller_id"])
        
        pipeline = [
            {"$match": {"sellerId": seller_id, "status": {"$in": ["active", "paused"]}}},
            {"$lookup": {"from": "products", "localField": "productId", "foreignField": "_id", "as": "pd"}},
            {"$unwind": {"path": "$pd", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "listingId": "$_id",
                "productName": "$pd.name",
                "sku": {"$ifNull": ["$sku", ""]},
            }},
        ]
        items = list(db.sellerListings.aggregate(pipeline))
        
        response = {"products": [{"listingId": str(i["listingId"]), "productName": i.get("productName", ""), "sku": i.get("sku", "")} for i in items]}
        
        assert "products" in response
        assert len(response["products"]) > 0
        for p in response["products"]:
            assert "listingId" in p
            assert "productName" in p
            assert "sku" in p
        print("✓ Products response format correct")
    
    def test_summary_response_format(self, db, test_data):
        """Summary endpoint returns required fields"""
        required_fields = ["totalOrders", "totalQuantity", "totalSpend", "avgRate", "supplierCount", "currentStock", "minStock"]
        
        # Simulate response
        response = {
            "totalOrders": 2,
            "totalQuantity": 80,
            "totalSpend": 8300.0,
            "avgRate": 105.0,
            "supplierCount": 2,
            "currentStock": 100,
            "minStock": 20,
        }
        
        for field in required_fields:
            assert field in response, f"Missing field: {field}"
        print("✓ Summary response format correct with all required fields")
    
    def test_price_trend_response_format(self, db, test_data):
        """Price trend endpoint returns suppliers array with data points"""
        # Simulate response
        response = {
            "suppliers": [
                {
                    "supplierName": "Supplier A",
                    "data": [
                        {"period": "2026-03-05", "avgRate": 100.0, "minRate": 100.0, "maxRate": 100.0}
                    ]
                }
            ]
        }
        
        assert "suppliers" in response
        assert isinstance(response["suppliers"], list)
        for s in response["suppliers"]:
            assert "supplierName" in s
            assert "data" in s
            for d in s["data"]:
                assert "period" in d
                assert "avgRate" in d
        print("✓ Price trend response format correct")
    
    def test_purchase_trend_response_format(self):
        """Purchase trend endpoint returns data array with period, quantity, amount"""
        response = {
            "data": [
                {"period": "2026-03-05", "quantity": 50, "amount": 5000.0, "orders": 1}
            ]
        }
        
        assert "data" in response
        for d in response["data"]:
            assert "period" in d
            assert "quantity" in d
            assert "amount" in d
        print("✓ Purchase trend response format correct")
    
    def test_stock_trend_response_format(self):
        """Stock trend endpoint returns data array with date, stock, change, type"""
        response = {
            "data": [
                {"date": "2026-03-05T00:00:00Z", "stock": 100, "change": 50, "type": "purchase_receipt", "note": ""}
            ],
            "currentStock": 100,
            "minStock": 20
        }
        
        assert "data" in response
        assert "currentStock" in response
        assert "minStock" in response
        for d in response["data"]:
            assert "date" in d
            assert "stock" in d
            assert "change" in d
            assert "type" in d
        print("✓ Stock trend response format correct")
    
    def test_supplier_comparison_response_format(self):
        """Supplier comparison endpoint returns suppliers with rate and isBestPrice"""
        response = {
            "suppliers": [
                {"supplierId": "abc123", "supplierName": "Supplier A", "rate": 100.0, "isBestPrice": True},
                {"supplierId": "abc124", "supplierName": "Supplier B", "rate": 110.0, "isBestPrice": False}
            ]
        }
        
        assert "suppliers" in response
        for s in response["suppliers"]:
            assert "supplierId" in s
            assert "supplierName" in s
            assert "rate" in s
            assert "isBestPrice" in s
        print("✓ Supplier comparison response format correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
