"""
V15 User Schema Standardization Migration
=========================================

Problem:
- MongoDB has duplicate/inconsistent fields:
  - is_seller vs isSeller
  - business_name vs business.name
  - gst_number vs gst.number
  
Solution:
- Standardize to camelCase structure:
  - isSeller: boolean
  - business: { name, location, gst, gst_verified }
  - profile: { businessName, phone, city, state }
  
Run this migration to fix data inconsistency between
Seller Dashboard and Admin Panel.
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['b2b_marketplace']
    
    print("=" * 60)
    print("V15 USER SCHEMA STANDARDIZATION MIGRATION")
    print("=" * 60)
    
    # Get current stats
    total_users = await db.users.count_documents({})
    print(f"\nTotal users in database: {total_users}")
    
    # Check for inconsistent fields
    with_is_seller = await db.users.count_documents({"is_seller": {"$exists": True}})
    with_business_name = await db.users.count_documents({"business_name": {"$exists": True}})
    with_gst_number = await db.users.count_documents({"gst_number": {"$exists": True}})
    with_city = await db.users.count_documents({"city": {"$exists": True}})
    with_state = await db.users.count_documents({"state": {"$exists": True}})
    with_business_obj = await db.users.count_documents({"business": {"$exists": True}})
    with_profile_obj = await db.users.count_documents({"profile": {"$exists": True}})
    with_isSeller = await db.users.count_documents({"isSeller": True})
    
    print(f"\nDocuments with legacy fields:")
    print(f"  - is_seller (snake_case): {with_is_seller}")
    print(f"  - business_name: {with_business_name}")
    print(f"  - gst_number: {with_gst_number}")
    print(f"  - city: {with_city}")
    print(f"  - state: {with_state}")
    print(f"\nDocuments with new structure:")
    print(f"  - business object: {with_business_obj}")
    print(f"  - profile object: {with_profile_obj}")
    print(f"  - isSeller=True: {with_isSeller}")
    
    # STEP 1: Ensure camelCase isSeller flag
    print("\n--- STEP 1: Standardize seller flag to isSeller ---")
    result1 = await db.users.update_many(
        {"is_seller": True, "isSeller": {"$ne": True}},
        {"$set": {"isSeller": True}}
    )
    print(f"  Updated {result1.modified_count} users with isSeller=True from is_seller")
    
    # STEP 2: Migrate business_name to profile.businessName
    print("\n--- STEP 2: Migrate business_name to profile.businessName ---")
    
    # Find all users with business_name but no profile.businessName
    users_with_business_name = await db.users.find({
        "business_name": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"profile.businessName": {"$exists": False}},
            {"profile.businessName": None},
            {"profile.businessName": ""}
        ]
    }).to_list(None)
    
    migrated_count = 0
    for user in users_with_business_name:
        business_name = user.get("business_name", "")
        city = user.get("city", "")
        state = user.get("state", "")
        phone = user.get("phone", "")
        gst_number = user.get("gst_number", "")
        
        # Build profile object
        profile = user.get("profile", {}) or {}
        if business_name and not profile.get("businessName"):
            profile["businessName"] = business_name
        if phone and not profile.get("phone"):
            profile["phone"] = phone
        if city and not profile.get("city"):
            profile["city"] = city
        if state and not profile.get("state"):
            profile["state"] = state
            
        # Build business object (for sellers)
        business = user.get("business", {}) or {}
        if business_name and not business.get("name"):
            business["name"] = business_name
        if city or state:
            location = f"{city}, {state}" if city and state else city or state
            if not business.get("location"):
                business["location"] = location
        if gst_number and not business.get("gst"):
            business["gst"] = gst_number
            
        # Build gst object
        gst = user.get("gst", {}) or {}
        if gst_number and not gst.get("number"):
            gst["number"] = gst_number
        
        # Update the user
        update_fields = {
            "profile": profile,
            "updatedAt": datetime.now(timezone.utc)
        }
        
        # Only set business if user is a seller
        if user.get("isSeller") or user.get("is_seller") or gst_number:
            update_fields["business"] = business
            if gst_number:
                update_fields["gst"] = gst
        
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_fields}
        )
        migrated_count += 1
    
    print(f"  Migrated {migrated_count} users with business_name to profile.businessName")
    
    # STEP 3: Also copy from business.name to profile.businessName where missing
    print("\n--- STEP 3: Sync business.name to profile.businessName ---")
    
    users_with_business_obj = await db.users.find({
        "business.name": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"profile.businessName": {"$exists": False}},
            {"profile.businessName": None},
            {"profile.businessName": ""}
        ]
    }).to_list(None)
    
    synced_count = 0
    for user in users_with_business_obj:
        business_name = user.get("business", {}).get("name", "")
        if business_name:
            profile = user.get("profile", {}) or {}
            profile["businessName"] = business_name
            
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"profile": profile, "updatedAt": datetime.now(timezone.utc)}}
            )
            synced_count += 1
    
    print(f"  Synced {synced_count} users from business.name to profile.businessName")
    
    # STEP 4: Remove deprecated fields
    print("\n--- STEP 4: Remove deprecated snake_case fields ---")
    result4 = await db.users.update_many(
        {},
        {
            "$unset": {
                "is_seller": "",
                # Keep business_name for now as backup
                # "business_name": "",
                # "gst_number": "",
                # "city": "",
                # "state": "",
                "emailVerified": "",  # Should use profile.emailVerified
            }
        }
    )
    print(f"  Removed deprecated fields from {result4.modified_count} documents")
    
    # STEP 5: Verify the migration
    print("\n--- STEP 5: Verify migration results ---")
    
    # Check sellers now have profile.businessName
    sellers = await db.users.find({"isSeller": True}).to_list(None)
    sellers_with_name = 0
    sellers_without_name = []
    
    for seller in sellers:
        profile = seller.get("profile", {}) or {}
        business_name = profile.get("businessName") or seller.get("business", {}).get("name")
        if business_name:
            sellers_with_name += 1
        else:
            sellers_without_name.append({
                "id": str(seller["_id"]),
                "email": seller.get("email")
            })
    
    print(f"\n  Sellers with businessName: {sellers_with_name}/{len(sellers)}")
    if sellers_without_name:
        print(f"  Sellers still missing businessName: {len(sellers_without_name)}")
        for s in sellers_without_name[:5]:
            print(f"    - {s['email']} ({s['id']})")
    
    # Final stats
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    
    final_with_profile = await db.users.count_documents({"profile.businessName": {"$exists": True, "$ne": None, "$ne": ""}})
    print(f"\nUsers with profile.businessName: {final_with_profile}")
    
    client.close()
    print("\nMigration finished successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
