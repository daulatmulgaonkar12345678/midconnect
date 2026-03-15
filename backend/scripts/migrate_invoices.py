"""
Invoice Migration Script
Fixes:
1. Generate sellerAbbreviation and sellerCode for all sellers
2. Create seller_invoice_counters collection with atomic counters
3. Renumber all invoices with new format: INV{ABBR}-{CODE}-{SEQUENCE}
4. Recalculate pendingAmount and fix status for all invoices
5. Create unique index on invoices.invoiceNumber
"""

import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "midconnect")


def generate_abbreviation(name: str) -> str:
    """Take first letter of each word."""
    words = name.split()
    abbr = ''.join(w[0].upper() for w in words if w and w[0].isalpha())
    return abbr if abbr else 'XX'


def generate_seller_code(seller_id: str) -> str:
    """Use last 6 chars of seller_id as unique code."""
    return seller_id[-6:].upper()


async def run_migration():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("=" * 60)
    print("INVOICE MIGRATION SCRIPT")
    print("=" * 60)

    # Step 1: Get all unique seller IDs from invoices
    seller_ids = await db.invoices.distinct("sellerId")
    print(f"\nFound {len(seller_ids)} unique sellers with invoices")

    for seller_oid in seller_ids:
        seller_id_str = str(seller_oid)
        print(f"\n--- Processing seller: {seller_id_str} ---")

        # Get business name from user profile or sellers collection
        business_name = None
        user = await db.users.find_one({"_id": seller_oid})
        if user:
            profile = user.get("profile")
            if isinstance(profile, dict):
                business_name = profile.get("businessName")
            if not business_name:
                seller = await db.sellers.find_one({"email": user.get("email")})
                if seller:
                    business_name = seller.get("businessName")
        if not business_name:
            business_name = f"Seller-{seller_id_str[-6:]}"

        abbreviation = generate_abbreviation(business_name)
        seller_code = generate_seller_code(seller_id_str)
        print(f"  Business Name: {business_name}")
        print(f"  Abbreviation: {abbreviation}")
        print(f"  Seller Code: {seller_code}")

        # Step 2: Get all invoices for this seller, sorted by creation date
        invoices = await db.invoices.find(
            {"sellerId": seller_oid}
        ).sort("createdAt", 1).to_list(10000)
        print(f"  Invoices: {len(invoices)}")

        # Step 3: Renumber invoices sequentially
        for seq, inv in enumerate(invoices, 1):
            old_number = inv.get("invoiceNumber", "N/A")
            new_number = f"INV{abbreviation}-{seller_code}-{seq:04d}"

            # Fix pendingAmount and status
            total = inv.get("total", 0)
            payments = await db.invoice_payments.find({"invoiceId": inv["_id"]}).to_list(500)
            total_paid = round(sum(p.get("amount", 0) for p in payments), 2)
            pending = round(max(0, total - total_paid), 2)

            # Derive correct status
            current_status = inv.get("status", "draft")
            if current_status == "cancelled":
                new_status = "cancelled"
            elif total_paid >= total and total > 0:
                new_status = "paid"
            elif total_paid > 0:
                new_status = "partially_paid"
            elif current_status in ("paid", "partially_paid"):
                new_status = "sent"
            else:
                new_status = current_status

            update = {
                "invoiceNumber": new_number,
                "totalPaid": total_paid,
                "pendingAmount": pending,
                "status": new_status,
            }

            await db.invoices.update_one({"_id": inv["_id"]}, {"$set": update})
            status_changed = f" (STATUS FIX: {current_status} -> {new_status})" if current_status != new_status else ""
            pending_changed = f" (PENDING FIX: {inv.get('pendingAmount', 'N/A')} -> {pending})" if inv.get('pendingAmount') != pending else ""
            print(f"    {old_number} -> {new_number}{status_changed}{pending_changed}")

        # Step 4: Create/update seller_invoice_counters
        await db.seller_invoice_counters.update_one(
            {"sellerId": seller_oid},
            {"$set": {
                "sellerId": seller_oid,
                "sellerAbbreviation": abbreviation,
                "sellerCode": seller_code,
                "businessName": business_name,
                "lastSequence": len(invoices),
                "updatedAt": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        print(f"  Counter set to: {len(invoices)}")

    # Step 5: Create unique index on invoiceNumber
    print("\n--- Creating unique index on invoices.invoiceNumber ---")
    try:
        await db.invoices.create_index("invoiceNumber", unique=True)
        print("  Unique index created successfully")
    except Exception as e:
        print(f"  Index creation warning: {e}")

    # Step 6: Create index on seller_invoice_counters
    await db.seller_invoice_counters.create_index("sellerId", unique=True)
    print("  seller_invoice_counters index created")

    # Summary
    total_invoices = await db.invoices.count_documents({})
    print(f"\n{'=' * 60}")
    print(f"MIGRATION COMPLETE")
    print(f"  Total invoices migrated: {total_invoices}")
    print(f"  Seller counters created: {len(seller_ids)}")
    print(f"{'=' * 60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
