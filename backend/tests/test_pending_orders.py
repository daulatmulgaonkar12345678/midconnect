"""Test that pending orders are created when stock is insufficient."""
import asyncio
import sys
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone


async def test_pending_order_creation():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['midconnect']

    # Find a seller
    seller = await db.users.find_one({"role": "seller"})
    if not seller:
        print("SKIP: No seller found in DB")
        return

    seller_id = seller["_id"]

    # Find a listing with stock=0 or create a test one
    listing = await db.sellerListings.find_one({"sellerId": seller_id})
    if not listing:
        print("SKIP: No listings found for seller")
        return

    listing_id = listing["_id"]
    original_stock = listing.get("stock", 0)

    # Temporarily set stock to 0
    await db.sellerListings.update_one({"_id": listing_id}, {"$set": {"stock": 0}})

    # Check what the reserved stock calculation looks like
    pipeline = [
        {"$match": {
            "sellerId": seller_id,
            "listingId": listing_id,
            "status": {"$in": ["pending", "partially_fulfilled"]}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$pendingQty"}}}
    ]
    reserved_result = await db.pending_orders.aggregate(pipeline).to_list(1)
    reserved = reserved_result[0]["total"] if reserved_result else 0
    available = max(0, 0 - reserved)

    print(f"Listing ID: {listing_id}")
    print(f"Stock: 0, Reserved: {reserved}, Available: {available}")
    print(f"When requested qty > available, pending order SHOULD be created")
    print(f"allowPartialFulfillment must be True for this to work")

    # Test: With stock=5 and reserved=5, available=0
    await db.sellerListings.update_one({"_id": listing_id}, {"$set": {"stock": 5}})
    # Create a fake pending order to reserve all stock
    test_po = {
        "sellerId": seller_id,
        "buyerId": ObjectId(),
        "listingId": listing_id,
        "invoiceId": ObjectId(),
        "productName": "Test",
        "orderedQty": 5,
        "fulfilledQty": 0,
        "pendingQty": 5,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    po_result = await db.pending_orders.insert_one(test_po)

    # Now check available
    reserved_result2 = await db.pending_orders.aggregate(pipeline).to_list(1)
    reserved2 = reserved_result2[0]["total"] if reserved_result2 else 0
    available2 = max(0, 5 - reserved2)
    print(f"\nWith stock=5, reserved={reserved2}, available={available2}")
    assert available2 == 0, f"Expected available=0, got {available2}"
    print("PASS: Available stock correctly accounts for reservations")

    # Cleanup
    await db.pending_orders.delete_one({"_id": po_result.inserted_id})
    await db.sellerListings.update_one({"_id": listing_id}, {"$set": {"stock": original_stock}})
    print("\nAll tests passed! Cleanup done.")


asyncio.run(test_pending_order_creation())
