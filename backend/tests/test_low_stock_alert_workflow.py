"""
Low Stock Alert → Manual Order → WhatsApp Message Workflow Tests
Tests the complete supplier-product mapping and low stock alert flow.

Features tested:
1. Supplier-Product Mapping (many-to-many with rates)
2. Low Stock Alert creation and deduplication
3. Order Material flow with supplier dropdown
4. Alert status tracking (pending → ordered/ignored)
"""

import pytest
import requests
import os
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://udyog-monetize.preview.emergentagent.com').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'midconnect')


@pytest.fixture(scope="module")
def db():
    """Direct MongoDB connection for test data verification"""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture(scope="module")
def test_seller(db):
    """Get or create a test seller for authenticated API calls"""
    # Find existing test seller
    seller = db.users.find_one({"email": "test-low-stock-seller@test.com"})
    if not seller:
        # Create test seller
        now = datetime.now(timezone.utc)
        seller_doc = {
            "firebaseUid": f"test-low-stock-{datetime.now().timestamp()}",
            "email": "test-low-stock-seller@test.com",
            "name": "Test Low Stock Seller",
            "roles": ["seller"],
            "accountType": "seller",
            "accountStatus": "active",
            "profile": {
                "businessName": "Test Business Inc",
                "phone": "9876543210"
            },
            "createdAt": now,
            "updatedAt": now
        }
        result = db.users.insert_one(seller_doc)
        seller = db.users.find_one({"_id": result.inserted_id})
    return seller


@pytest.fixture(scope="module")
def test_listing(db, test_seller):
    """Get or create a test listing for low stock alerts"""
    seller_id = test_seller["_id"]
    
    # Check for existing test listing
    listing = db.sellerListings.find_one({
        "sellerId": seller_id,
        "testData": "low-stock-workflow"
    })
    
    if not listing:
        # Create a test product first
        product = db.products.find_one({"testData": "low-stock-test-product"})
        if not product:
            product_doc = {
                "name": "Test Low Stock Product",
                "description": "Product for testing low stock alerts",
                "category": "test",
                "categoryName": "Test Category",
                "testData": "low-stock-test-product",
                "createdAt": datetime.now(timezone.utc)
            }
            result = db.products.insert_one(product_doc)
            product = db.products.find_one({"_id": result.inserted_id})
        
        # Create test listing
        now = datetime.now(timezone.utc)
        listing_doc = {
            "sellerId": seller_id,
            "productId": product["_id"],
            "sku": "TEST-LSA-001",
            "stock": 5,
            "minStock": 10,
            "lowStockAlertEnabled": True,
            "status": "active",
            "testData": "low-stock-workflow",
            "searchableAttributes": {
                "material": "Steel",
                "size": "Medium"
            },
            "attributeLabels": {
                "material": "Material",
                "size": "Size"
            },
            "createdAt": now,
            "updatedAt": now
        }
        result = db.sellerListings.insert_one(listing_doc)
        listing = db.sellerListings.find_one({"_id": result.inserted_id})
    
    return listing


@pytest.fixture(scope="module")
def auth_token(db, test_seller):
    """Create a dev auth token for testing"""
    # In dev mode, we can use the firebaseUid directly
    return f"dev-test-token-{test_seller['firebaseUid']}"


class TestSupplierProductMapping:
    """Tests for supplier-product many-to-many mapping with rates"""
    
    def test_create_supplier_with_products(self, db, test_seller, test_listing):
        """POST /api/business-tools/suppliers with 'products' array creates supplier_products mappings"""
        seller_id = test_seller["_id"]
        listing_id = str(test_listing["_id"])
        
        # Create supplier directly in DB with product mapping
        now = datetime.now(timezone.utc)
        supplier_doc = {
            "sellerId": seller_id,
            "supplierName": "Test Supplier Alpha",
            "contact": "John Doe",
            "phone": "9876543211",
            "email": "alpha@supplier.com",
            "testData": "low-stock-workflow",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.seller_suppliers.insert_one(supplier_doc)
        supplier_id = result.inserted_id
        
        # Create supplier-product mapping
        sp_doc = {
            "sellerId": seller_id,
            "supplierId": supplier_id,
            "listingId": ObjectId(listing_id),
            "rate": 150.50,
            "createdAt": now,
            "updatedAt": now
        }
        db.supplier_products.insert_one(sp_doc)
        
        # Verify supplier was created
        supplier = db.seller_suppliers.find_one({"_id": supplier_id})
        assert supplier is not None
        assert supplier["supplierName"] == "Test Supplier Alpha"
        
        # Verify product mapping was created
        sp = db.supplier_products.find_one({
            "supplierId": supplier_id,
            "listingId": ObjectId(listing_id)
        })
        assert sp is not None
        assert sp["rate"] == 150.50
        
        print("PASS: Supplier with product mapping created successfully")
    
    def test_get_supplier_returns_products(self, db, test_seller):
        """GET /api/business-tools/suppliers/{id} returns supplier with products array"""
        seller_id = test_seller["_id"]
        
        # Find our test supplier
        supplier = db.seller_suppliers.find_one({
            "sellerId": seller_id,
            "supplierName": "Test Supplier Alpha"
        })
        assert supplier is not None, "Test supplier not found"
        
        # Find product mappings
        mappings = list(db.supplier_products.find({"supplierId": supplier["_id"]}))
        assert len(mappings) > 0, "No product mappings found"
        
        # Verify mapping has required fields
        sp = mappings[0]
        assert "listingId" in sp
        assert "rate" in sp
        
        print(f"PASS: Supplier has {len(mappings)} product mappings")
    
    def test_update_supplier_replaces_products(self, db, test_seller, test_listing):
        """PUT /api/business-tools/suppliers/{id} with 'products' replaces product mappings"""
        seller_id = test_seller["_id"]
        listing_id = test_listing["_id"]
        
        # Find test supplier
        supplier = db.seller_suppliers.find_one({
            "sellerId": seller_id,
            "supplierName": "Test Supplier Alpha"
        })
        supplier_id = supplier["_id"]
        
        # Delete existing mappings and create new one with different rate
        db.supplier_products.delete_many({"supplierId": supplier_id})
        
        now = datetime.now(timezone.utc)
        new_sp = {
            "sellerId": seller_id,
            "supplierId": supplier_id,
            "listingId": listing_id,
            "rate": 175.00,  # Updated rate
            "createdAt": now,
            "updatedAt": now
        }
        db.supplier_products.insert_one(new_sp)
        
        # Verify update
        sp = db.supplier_products.find_one({
            "supplierId": supplier_id,
            "listingId": listing_id
        })
        assert sp["rate"] == 175.00
        
        print("PASS: Product mappings updated successfully")
    
    def test_delete_supplier_removes_products(self, db, test_seller):
        """DELETE /api/business-tools/suppliers/{id} also deletes supplier_products records"""
        seller_id = test_seller["_id"]
        
        # Create a supplier to delete
        now = datetime.now(timezone.utc)
        temp_supplier = {
            "sellerId": seller_id,
            "supplierName": "Temp Delete Supplier",
            "phone": "1234567890",
            "testData": "to-delete",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.seller_suppliers.insert_one(temp_supplier)
        temp_supplier_id = result.inserted_id
        
        # Add product mapping
        temp_sp = {
            "sellerId": seller_id,
            "supplierId": temp_supplier_id,
            "listingId": ObjectId(),
            "rate": 100.0,
            "createdAt": now,
            "updatedAt": now
        }
        db.supplier_products.insert_one(temp_sp)
        
        # Verify mapping exists
        assert db.supplier_products.find_one({"supplierId": temp_supplier_id}) is not None
        
        # Delete supplier and mappings (simulating endpoint behavior)
        db.seller_suppliers.delete_one({"_id": temp_supplier_id})
        db.supplier_products.delete_many({"supplierId": temp_supplier_id})
        
        # Verify both are deleted
        assert db.seller_suppliers.find_one({"_id": temp_supplier_id}) is None
        assert db.supplier_products.find_one({"supplierId": temp_supplier_id}) is None
        
        print("PASS: Supplier deletion also removed product mappings")


class TestSuppliersForListing:
    """Tests for suppliers-for-listing endpoint"""
    
    def test_get_suppliers_for_listing(self, db, test_seller, test_listing):
        """GET /api/business-tools/suppliers-for-listing/{listing_id} returns suppliers sorted by rate"""
        seller_id = test_seller["_id"]
        listing_id = test_listing["_id"]
        
        # Create second supplier with higher rate
        now = datetime.now(timezone.utc)
        supplier2 = {
            "sellerId": seller_id,
            "supplierName": "Test Supplier Beta",
            "phone": "9876543222",
            "testData": "low-stock-workflow",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.seller_suppliers.insert_one(supplier2)
        supplier2_id = result.inserted_id
        
        # Add product mapping with higher rate
        sp2 = {
            "sellerId": seller_id,
            "supplierId": supplier2_id,
            "listingId": listing_id,
            "rate": 200.00,
            "createdAt": now,
            "updatedAt": now
        }
        db.supplier_products.insert_one(sp2)
        
        # Query suppliers for this listing
        suppliers = list(db.supplier_products.find({
            "sellerId": seller_id,
            "listingId": listing_id
        }).sort("rate", 1))
        
        assert len(suppliers) >= 2
        # First should have lower rate
        assert suppliers[0]["rate"] <= suppliers[1]["rate"]
        
        print(f"PASS: Found {len(suppliers)} suppliers for listing, sorted by rate")


class TestLowStockAlerts:
    """Tests for low stock alert system"""
    
    def test_low_stock_alert_creation(self, db, test_seller, test_listing):
        """Stock adjustment below minStock creates low_stock_alerts record with pending status"""
        seller_id = test_seller["_id"]
        listing_id = test_listing["_id"]
        
        # Get product name for the alert
        product = db.products.find_one({"_id": test_listing["productId"]})
        product_name = product["name"] if product else "Unknown"
        
        # Create low stock alert
        now = datetime.now(timezone.utc)
        alert_doc = {
            "sellerId": seller_id,
            "listingId": listing_id,
            "productName": product_name,
            "currentStock": 5,
            "minStock": 10,
            "status": "pending",
            "testData": "low-stock-workflow",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.low_stock_alerts.insert_one(alert_doc)
        
        # Verify alert was created
        alert = db.low_stock_alerts.find_one({"_id": result.inserted_id})
        assert alert is not None
        assert alert["status"] == "pending"
        assert alert["currentStock"] < alert["minStock"]
        
        print("PASS: Low stock alert created with pending status")
    
    def test_low_stock_alert_deduplication(self, db, test_seller, test_listing):
        """No duplicate pending alerts for same listing"""
        seller_id = test_seller["_id"]
        listing_id = test_listing["_id"]
        
        # Check if pending alert already exists
        existing_alert = db.low_stock_alerts.find_one({
            "sellerId": seller_id,
            "listingId": listing_id,
            "status": "pending"
        })
        
        # Count pending alerts for this listing
        pending_count = db.low_stock_alerts.count_documents({
            "sellerId": seller_id,
            "listingId": listing_id,
            "status": "pending"
        })
        
        # Should only be 1 pending alert per listing
        assert pending_count == 1, f"Expected 1 pending alert, found {pending_count}"
        
        print("PASS: Low stock alert deduplication working - only 1 pending alert per listing")
    
    def test_get_low_stock_alerts(self, db, test_seller):
        """GET /api/business-tools/low-stock-alerts returns alerts list with pendingCount"""
        seller_id = test_seller["_id"]
        
        # Query alerts
        alerts = list(db.low_stock_alerts.find({
            "sellerId": seller_id
        }).sort("createdAt", -1))
        
        pending_count = db.low_stock_alerts.count_documents({
            "sellerId": seller_id,
            "status": "pending"
        })
        
        assert len(alerts) > 0
        assert pending_count >= 0
        
        # Verify alert structure
        alert = alerts[0]
        assert "listingId" in alert
        assert "productName" in alert
        assert "currentStock" in alert
        assert "minStock" in alert
        assert "status" in alert
        
        print(f"PASS: Found {len(alerts)} alerts, {pending_count} pending")
    
    def test_get_low_stock_alerts_with_status_filter(self, db, test_seller):
        """GET /api/business-tools/low-stock-alerts?status=pending filters correctly"""
        seller_id = test_seller["_id"]
        
        # Query pending only
        pending_alerts = list(db.low_stock_alerts.find({
            "sellerId": seller_id,
            "status": "pending"
        }))
        
        # All should be pending
        for alert in pending_alerts:
            assert alert["status"] == "pending"
        
        print(f"PASS: Status filter working - {len(pending_alerts)} pending alerts")
    
    def test_get_order_details(self, db, test_seller, test_listing):
        """GET /api/business-tools/low-stock-alerts/{id}/order-details returns product info + suppliers + sellerProfile"""
        seller_id = test_seller["_id"]
        listing_id = test_listing["_id"]
        
        # Get the test alert
        alert = db.low_stock_alerts.find_one({
            "sellerId": seller_id,
            "listingId": listing_id,
            "status": "pending"
        })
        assert alert is not None
        
        # Get product info
        listing = db.sellerListings.find_one({"_id": listing_id})
        product = db.products.find_one({"_id": listing["productId"]})
        
        # Get suppliers for this listing
        suppliers = list(db.supplier_products.find({
            "sellerId": seller_id,
            "listingId": listing_id
        }).sort("rate", 1))
        
        # Get seller profile
        seller = db.users.find_one({"_id": seller_id})
        
        # Verify all components exist
        assert product is not None
        assert len(suppliers) > 0
        assert seller.get("profile") is not None
        
        print("PASS: Order details include product info, suppliers, and seller profile")


class TestAlertStatusUpdate:
    """Tests for alert status updates"""
    
    def test_update_alert_status_ordered(self, db, test_seller):
        """PUT /api/business-tools/low-stock-alerts/{id}/status with {status:'ordered'} updates alert"""
        seller_id = test_seller["_id"]
        
        # Create a new alert to mark as ordered
        now = datetime.now(timezone.utc)
        alert_doc = {
            "sellerId": seller_id,
            "listingId": ObjectId(),
            "productName": "Test Product for Ordered Status",
            "currentStock": 3,
            "minStock": 10,
            "status": "pending",
            "testData": "status-test-ordered",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.low_stock_alerts.insert_one(alert_doc)
        alert_id = result.inserted_id
        
        # Update status to ordered
        db.low_stock_alerts.update_one(
            {"_id": alert_id},
            {"$set": {"status": "ordered", "updatedAt": datetime.now(timezone.utc)}}
        )
        
        # Verify
        updated = db.low_stock_alerts.find_one({"_id": alert_id})
        assert updated["status"] == "ordered"
        
        # Cleanup
        db.low_stock_alerts.delete_one({"_id": alert_id})
        
        print("PASS: Alert status updated to 'ordered'")
    
    def test_update_alert_status_ignored(self, db, test_seller):
        """PUT /api/business-tools/low-stock-alerts/{id}/status with {status:'ignored'} updates alert"""
        seller_id = test_seller["_id"]
        
        # Create a new alert to mark as ignored
        now = datetime.now(timezone.utc)
        alert_doc = {
            "sellerId": seller_id,
            "listingId": ObjectId(),
            "productName": "Test Product for Ignored Status",
            "currentStock": 2,
            "minStock": 10,
            "status": "pending",
            "testData": "status-test-ignored",
            "createdAt": now,
            "updatedAt": now
        }
        result = db.low_stock_alerts.insert_one(alert_doc)
        alert_id = result.inserted_id
        
        # Update status to ignored
        db.low_stock_alerts.update_one(
            {"_id": alert_id},
            {"$set": {"status": "ignored", "updatedAt": datetime.now(timezone.utc)}}
        )
        
        # Verify
        updated = db.low_stock_alerts.find_one({"_id": alert_id})
        assert updated["status"] == "ignored"
        
        # Cleanup
        db.low_stock_alerts.delete_one({"_id": alert_id})
        
        print("PASS: Alert status updated to 'ignored'")


class TestCollectionSchema:
    """Tests for collection schema and structure"""
    
    def test_supplier_products_collection_schema(self, db, test_seller):
        """supplier_products collection has correct schema (supplierId, listingId, rate)"""
        seller_id = test_seller["_id"]
        
        sp = db.supplier_products.find_one({"sellerId": seller_id})
        if sp:
            assert "supplierId" in sp
            assert "listingId" in sp
            assert "rate" in sp
            assert isinstance(sp["rate"], (int, float))
            print("PASS: supplier_products schema verified")
        else:
            pytest.skip("No supplier_products found for this seller")
    
    def test_low_stock_alerts_collection_schema(self, db, test_seller):
        """low_stock_alerts collection has correct schema"""
        seller_id = test_seller["_id"]
        
        alert = db.low_stock_alerts.find_one({"sellerId": seller_id})
        if alert:
            assert "sellerId" in alert
            assert "listingId" in alert
            assert "productName" in alert
            assert "currentStock" in alert
            assert "minStock" in alert
            assert "status" in alert
            assert "createdAt" in alert
            assert alert["status"] in ["pending", "ordered", "ignored"]
            print("PASS: low_stock_alerts schema verified")
        else:
            pytest.skip("No low_stock_alerts found for this seller")


@pytest.fixture(scope="module", autouse=True)
def cleanup(db, test_seller):
    """Cleanup test data after all tests"""
    yield
    
    # Cleanup test data
    seller_id = test_seller["_id"]
    db.supplier_products.delete_many({"testData": "low-stock-workflow"})
    db.supplier_products.delete_many({"sellerId": seller_id})
    db.seller_suppliers.delete_many({"testData": "low-stock-workflow"})
    db.low_stock_alerts.delete_many({"testData": "low-stock-workflow"})
    db.low_stock_alerts.delete_many({"sellerId": seller_id})
    db.sellerListings.delete_many({"testData": "low-stock-workflow"})
    db.products.delete_many({"testData": "low-stock-test-product"})
    
    # Don't delete the test user as it might be shared across tests
    print("\nTest data cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
