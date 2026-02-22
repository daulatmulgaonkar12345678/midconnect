#!/usr/bin/env python3
"""
MongoDB Field Migration Script - snake_case to camelCase
=========================================================

This script renames all snake_case fields to camelCase in the database.
Run ONCE after deploying the camelCase backend code.

IMPORTANT: Backup your database before running this script!

Usage:
    python scripts/migrate_to_camelcase.py

Author: MidConnect B2B Marketplace
Date: Feb 20, 2026
"""

import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "b2b_marketplace")


async def migrate_collection(db, collection_name: str, field_renames: dict):
    """
    Rename fields in a collection.
    
    Args:
        db: Database instance
        collection_name: Name of collection to update
        field_renames: Dict of old_name -> new_name
    """
    collection = db[collection_name]
    
    # Build $rename operation
    rename_ops = {old: new for old, new in field_renames.items()}
    
    if not rename_ops:
        print(f"  [SKIP] {collection_name}: No renames needed")
        return 0
    
    # Count documents that have any of the old field names
    or_conditions = [{old: {"$exists": True}} for old in rename_ops.keys()]
    count = await collection.count_documents({"$or": or_conditions})
    
    if count == 0:
        print(f"  [SKIP] {collection_name}: No documents to migrate")
        return 0
    
    # Perform rename
    result = await collection.update_many(
        {"$or": or_conditions},
        {"$rename": rename_ops}
    )
    
    print(f"  [OK] {collection_name}: Renamed {result.modified_count} documents")
    return result.modified_count


async def main():
    """Main migration function"""
    print("=" * 60)
    print("MongoDB camelCase Migration Script")
    print("=" * 60)
    print(f"Database: {DB_NAME}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Starting migration...")
    print()
    
    total_migrated = 0
    
    # 1. Categories collection
    print("[1/8] categories collection")
    total_migrated += await migrate_collection(db, "categories", {
        "display_order": "displayOrder",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "created_by": "createdBy",
        "spec_template_count": "specTemplateCount",
        "listing_count": "listingCount"
    })
    
    # 2. globalDropdowns collection
    print("[2/8] globalDropdowns collection")
    total_migrated += await migrate_collection(db, "globalDropdowns", {
        "is_system": "isSystem",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "created_by": "createdBy",
        "display_order": "displayOrder"
    })
    
    # 3. specTemplates collection
    print("[3/8] specTemplates collection")
    total_migrated += await migrate_collection(db, "specTemplates", {
        "category_id": "categoryId",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "created_by": "createdBy",
        "field_type": "fieldType",
        "is_mandatory": "isMandatory",
        "is_seller_editable": "isSellerEditable",
        "is_locked_after_create": "isLockedAfterCreate",
        "display_order": "displayOrder",
        "dropdown_key": "dropdownKey",
        "min_value": "minValue",
        "max_value": "maxValue",
        "help_text": "helpText"
    })
    
    # 4. products collection
    print("[4/8] products collection")
    total_migrated += await migrate_collection(db, "products", {
        "category_id": "categoryId",
        "spec_template_id": "specTemplateId",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "created_by": "createdBy",
        "manufacturer_id": "manufacturerId",
        "product_name": "name"
    })
    
    # 5. productVariants collection
    print("[5/8] productVariants collection")
    total_migrated += await migrate_collection(db, "productVariants", {
        "product_id": "productId",
        "spec_template_id": "specTemplateId",
        "normalized_spec_hash": "normalizedSpecHash",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    })
    
    # 6. sellerListings collection
    print("[6/8] sellerListings collection")
    total_migrated += await migrate_collection(db, "sellerListings", {
        "product_id": "productId",
        "seller_id": "sellerId",
        "category_id": "categoryId",
        "variant_id": "variantId",
        "is_active": "isActive",
        "seller_role": "sellerRole",
        "max_capacity": "maxCapacity",
        "capacity_time_basis": "capacityTimeBasis",
        "lead_time": "leadTime",
        "packaging_size": "packagingSize",
        "delivery_locations": "deliveryLocations",
        "seller_notes": "sellerNotes",
        "pricing_tiers": "pricingTiers",
        "pricing_slabs": "pricingTiers",
        "last_stock_update": "lastStockUpdate",
        "published_at": "publishedAt",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    })
    
    # 7. inquiries collection
    print("[7/8] inquiries collection")
    total_migrated += await migrate_collection(db, "inquiries", {
        "product_id": "productId",
        "seller_id": "sellerId",
        "buyer_id": "buyerId",
        "listing_id": "listingId",
        "buyer_type": "buyerType",
        "buyer_info": "buyerInfo",
        "requirement_note": "requirementNote",
        "location_city": "locationCity",
        "location_state": "locationState",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    })
    
    # 8. users collection
    print("[8/8] users collection")
    total_migrated += await migrate_collection(db, "users", {
        "firebase_uid": "firebaseUid",
        "business_name": "businessName",
        "gst_number": "gstNumber",
        "gst_document": "gstDocument",
        "gst_status": "gstStatus",
        "owner_name": "ownerName",
        "is_seller": "isSeller",
        "is_admin": "isAdmin",
        "is_manufacturer": "isManufacturer",
        "email_verified": "emailVerified",
        "phone_verified": "phoneVerified",
        "enquiries_this_month": "enquiriesThisMonth",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    })
    
    print()
    print("=" * 60)
    print(f"Migration complete! Total documents modified: {total_migrated}")
    print("=" * 60)
    
    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
