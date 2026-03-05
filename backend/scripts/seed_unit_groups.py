"""
Seed script for default unit groups in the configurable calculator system.

This creates the standard unit groups:
- Length (mm, cm, m, inch, feet)
- Weight (g, kg, ton)
- Volume (ml, liter, m³)
- Area (mm², cm², m², ft²)
- Quantity (pcs, bags, boxes)

Run: python -m scripts.seed_unit_groups
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# UNIT GROUPS DATA
# ============================================================================

UNIT_GROUPS = [
    {
        "name": "length",
        "display_name": "Length",
        "base_unit": "m",
        "units": [
            {"key": "mm", "label": "Millimeter (mm)", "conversion_to_base": 0.001},
            {"key": "cm", "label": "Centimeter (cm)", "conversion_to_base": 0.01},
            {"key": "m", "label": "Meter (m)", "conversion_to_base": 1.0},
            {"key": "inch", "label": "Inch (in)", "conversion_to_base": 0.0254},
            {"key": "feet", "label": "Feet (ft)", "conversion_to_base": 0.3048},
        ]
    },
    {
        "name": "weight",
        "display_name": "Weight",
        "base_unit": "kg",
        "units": [
            {"key": "g", "label": "Gram (g)", "conversion_to_base": 0.001},
            {"key": "kg", "label": "Kilogram (kg)", "conversion_to_base": 1.0},
            {"key": "ton", "label": "Metric Ton", "conversion_to_base": 1000.0},
            {"key": "lb", "label": "Pound (lb)", "conversion_to_base": 0.453592},
        ]
    },
    {
        "name": "volume",
        "display_name": "Volume",
        "base_unit": "liter",
        "units": [
            {"key": "ml", "label": "Milliliter (ml)", "conversion_to_base": 0.001},
            {"key": "liter", "label": "Liter (L)", "conversion_to_base": 1.0},
            {"key": "m3", "label": "Cubic Meter (m³)", "conversion_to_base": 1000.0},
            {"key": "gallon", "label": "Gallon (US)", "conversion_to_base": 3.78541},
        ]
    },
    {
        "name": "area",
        "display_name": "Area",
        "base_unit": "m2",
        "units": [
            {"key": "mm2", "label": "Square mm (mm²)", "conversion_to_base": 0.000001},
            {"key": "cm2", "label": "Square cm (cm²)", "conversion_to_base": 0.0001},
            {"key": "m2", "label": "Square Meter (m²)", "conversion_to_base": 1.0},
            {"key": "ft2", "label": "Square Feet (ft²)", "conversion_to_base": 0.092903},
        ]
    },
    {
        "name": "quantity",
        "display_name": "Quantity",
        "base_unit": "pcs",
        "units": [
            {"key": "pcs", "label": "Pieces", "conversion_to_base": 1.0},
            {"key": "dozen", "label": "Dozen", "conversion_to_base": 12.0},
            {"key": "bag", "label": "Bags", "conversion_to_base": 1.0},
            {"key": "box", "label": "Boxes", "conversion_to_base": 1.0},
            {"key": "bundle", "label": "Bundles", "conversion_to_base": 1.0},
            {"key": "roll", "label": "Rolls", "conversion_to_base": 1.0},
        ]
    },
    {
        "name": "percentage",
        "display_name": "Percentage",
        "base_unit": "percent",
        "units": [
            {"key": "percent", "label": "Percent (%)", "conversion_to_base": 1.0},
        ]
    }
]


async def seed_unit_groups():
    """Seed the database with default unit groups"""
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "midconnect")
    
    print(f"Connecting to MongoDB: {DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    now = datetime.now(timezone.utc)
    
    print("\n=== Seeding Unit Groups ===")
    
    for group in UNIT_GROUPS:
        existing = await db.unit_groups.find_one({"name": group["name"]})
        if existing:
            # Update existing group
            await db.unit_groups.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "display_name": group["display_name"],
                    "base_unit": group["base_unit"],
                    "units": group["units"],
                    "updatedAt": now
                }}
            )
            print(f"  [UPDATED] {group['display_name']} ({len(group['units'])} units)")
        else:
            # Create new group
            doc = {
                "_id": ObjectId(),
                "name": group["name"],
                "display_name": group["display_name"],
                "base_unit": group["base_unit"],
                "units": group["units"],
                "is_active": True,
                "createdAt": now,
                "updatedAt": now
            }
            await db.unit_groups.insert_one(doc)
            print(f"  [CREATED] {group['display_name']} ({len(group['units'])} units)")
    
    # Summary
    count = await db.unit_groups.count_documents({})
    print(f"\n=== Summary ===")
    print(f"Total Unit Groups: {count}")
    print("Seeding complete!")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_unit_groups())
