"""
Update existing materials to have material_family field.

This script updates the materials collection to use the new material_family concept.

Run: python -m scripts.update_material_families
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# Material family mapping
MATERIAL_FAMILIES = {
    # Steel family
    "MS Steel": "Steel",
    "EN8 Steel": "Steel",
    "EN19 Steel": "Steel",
    "Carbon Steel": "Steel",
    
    # Stainless Steel family
    "SS202": "Stainless Steel",
    "SS304": "Stainless Steel",
    "SS304L": "Stainless Steel",
    "SS316": "Stainless Steel",
    "SS316L": "Stainless Steel",
    "Stainless Steel": "Stainless Steel",
    
    # Aluminum family
    "Aluminum": "Aluminum",
    "Aluminum 6061": "Aluminum",
    "Aluminum 6063": "Aluminum",
    
    # Other metals
    "Copper": "Copper",
    "Brass": "Brass",
    "Cast Iron": "Cast Iron",
    "Titanium": "Titanium",
}

async def update_material_families():
    """Update all materials to have material_family"""
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "midconnect")
    
    print(f"Connecting to MongoDB: {DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    now = datetime.now(timezone.utc)
    
    print("\n=== Updating Material Families ===")
    
    cursor = db.materials.find({})
    updated_count = 0
    
    async for material in cursor:
        name = material.get("name", "")
        current_family = material.get("material_family")
        
        # Determine family from name
        new_family = MATERIAL_FAMILIES.get(name)
        
        # Try partial matching
        if not new_family:
            name_lower = name.lower()
            if "ss" in name_lower or "stainless" in name_lower:
                new_family = "Stainless Steel"
            elif "steel" in name_lower or "ms " in name_lower or "en8" in name_lower or "en19" in name_lower:
                new_family = "Steel"
            elif "aluminum" in name_lower or "aluminium" in name_lower:
                new_family = "Aluminum"
            elif "copper" in name_lower:
                new_family = "Copper"
            elif "brass" in name_lower:
                new_family = "Brass"
            elif "iron" in name_lower:
                new_family = "Cast Iron"
            elif "titanium" in name_lower:
                new_family = "Titanium"
            else:
                new_family = "Other"
        
        if current_family != new_family:
            await db.materials.update_one(
                {"_id": material["_id"]},
                {"$set": {
                    "material_family": new_family,
                    "updatedAt": now
                }}
            )
            print(f"  [UPDATED] {name} → {new_family}")
            updated_count += 1
        else:
            print(f"  [OK] {name} → {current_family or new_family}")
    
    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count} materials")
    
    # Show families
    families = await db.materials.distinct("material_family")
    print(f"\nMaterial Families: {families}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(update_material_families())
