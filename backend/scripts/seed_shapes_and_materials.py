"""
Seed script for shapes and materials in the raw material calculator.

This script populates the database with all standard industrial shapes and materials.
Run this once to initialize the database, or to reset to defaults.

Usage:
    python -m scripts.seed_shapes_and_materials
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# MATERIALS DATA
# ============================================================================

MATERIALS = [
    # Steel variants
    {"name": "MS Steel", "density": 7850, "description": "Mild Steel / Carbon Steel"},
    {"name": "EN8 Steel", "density": 7850, "description": "Medium Carbon Steel EN8"},
    {"name": "EN19 Steel", "density": 7850, "description": "High Tensile Steel EN19"},
    
    # Stainless Steel variants
    {"name": "SS202", "density": 7900, "description": "Stainless Steel 202"},
    {"name": "SS304", "density": 7930, "description": "Stainless Steel 304"},
    {"name": "SS304L", "density": 7930, "description": "Stainless Steel 304L (Low Carbon)"},
    {"name": "SS316", "density": 8000, "description": "Stainless Steel 316"},
    {"name": "SS316L", "density": 8000, "description": "Stainless Steel 316L (Low Carbon)"},
    
    # Aluminum
    {"name": "Aluminum 6061", "density": 2700, "description": "Aluminum Alloy 6061"},
    {"name": "Aluminum 6063", "density": 2700, "description": "Aluminum Alloy 6063"},
    
    # Other metals
    {"name": "Copper", "density": 8960, "description": "Pure Copper"},
    {"name": "Brass", "density": 8500, "description": "Brass Alloy (Cu-Zn)"},
    {"name": "Cast Iron", "density": 7200, "description": "Grey Cast Iron"},
    {"name": "Titanium", "density": 4500, "description": "Commercial Pure Titanium"},
]

# ============================================================================
# SHAPES DATA
# ============================================================================

# Common unit options
DIMENSION_UNITS = ["mm", "cm", "inch"]
LENGTH_UNITS = ["mm", "cm", "meter", "inch", "feet"]

SHAPES = [
    # ======================
    # SOLID BARS
    # ======================
    {
        "key": "round_bar",
        "name": "Round Bar",
        "description": "Solid circular cross-section bar",
        "icon": "circle",
        "fields": [
            {"key": "diameter", "label": "Diameter", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = π × (d/2)² × L",
        "formula_type": "round_bar"
    },
    {
        "key": "square_bar",
        "name": "Square Bar",
        "description": "Solid square cross-section bar",
        "icon": "square",
        "fields": [
            {"key": "side", "label": "Side", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = side² × L",
        "formula_type": "square_bar"
    },
    {
        "key": "hex_bar",
        "name": "Hex Bar",
        "description": "Hexagonal cross-section bar",
        "icon": "hexagon",
        "fields": [
            {"key": "across_flats", "label": "Across Flats (AF)", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (3√3/2) × (AF/2)² × L = 0.866 × AF² × L",
        "formula_type": "hex_bar"
    },
    {
        "key": "flat_bar",
        "name": "Flat Bar",
        "description": "Rectangular solid bar",
        "icon": "rectangle-horizontal",
        "fields": [
            {"key": "width", "label": "Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = width × thickness × L",
        "formula_type": "flat_bar"
    },
    {
        "key": "rectangular_bar",
        "name": "Rectangular Bar",
        "description": "Rectangular solid bar",
        "icon": "rectangle-horizontal",
        "fields": [
            {"key": "width", "label": "Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "height", "label": "Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = width × height × L",
        "formula_type": "rectangular_bar"
    },
    
    # ======================
    # HOLLOW SECTIONS
    # ======================
    {
        "key": "pipe",
        "name": "Pipe / Tube",
        "description": "Hollow circular cross-section",
        "icon": "circle-dot",
        "fields": [
            {"key": "outer_diameter", "label": "Outer Diameter (OD)", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Wall Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = π × ((OD/2)² - (ID/2)²) × L",
        "formula_type": "pipe"
    },
    {
        "key": "square_hollow",
        "name": "Square Hollow Section (SHS)",
        "description": "Square hollow tube",
        "icon": "square",
        "fields": [
            {"key": "side", "label": "Outer Side", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Wall Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (side² - (side - 2t)²) × L",
        "formula_type": "square_hollow"
    },
    {
        "key": "rectangular_hollow",
        "name": "Rectangular Hollow Section (RHS)",
        "description": "Rectangular hollow tube",
        "icon": "rectangle-horizontal",
        "fields": [
            {"key": "width", "label": "Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "height", "label": "Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Wall Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (W×H - (W-2t)×(H-2t)) × L",
        "formula_type": "rectangular_hollow"
    },
    
    # ======================
    # STRUCTURAL SECTIONS
    # ======================
    {
        "key": "angle",
        "name": "Angle (L Angle)",
        "description": "L-shaped structural section",
        "icon": "corner-up-right",
        "fields": [
            {"key": "leg_a", "label": "Leg A", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "leg_b", "label": "Leg B", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = t × (A + B - t) × L",
        "formula_type": "angle"
    },
    {
        "key": "channel",
        "name": "Channel (C Channel)",
        "description": "C-shaped structural channel",
        "icon": "square-bracket",
        "fields": [
            {"key": "web_height", "label": "Web Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_width", "label": "Flange Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "web_thickness", "label": "Web Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_thickness", "label": "Flange Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (H×tw + 2×W×tf - 2×tw×tf) × L",
        "formula_type": "channel"
    },
    {
        "key": "i_beam",
        "name": "I Beam",
        "description": "I-shaped structural beam (ISMB/IPE)",
        "icon": "pilcrow",
        "fields": [
            {"key": "height", "label": "Total Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_width", "label": "Flange Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "web_thickness", "label": "Web Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_thickness", "label": "Flange Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (2×W×tf + (H-2tf)×tw) × L",
        "formula_type": "i_beam"
    },
    {
        "key": "h_beam",
        "name": "H Beam",
        "description": "H-shaped structural beam (HE/UC)",
        "icon": "pilcrow",
        "fields": [
            {"key": "height", "label": "Total Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_width", "label": "Flange Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "web_thickness", "label": "Web Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_thickness", "label": "Flange Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (2×W×tf + (H-2tf)×tw) × L",
        "formula_type": "h_beam"
    },
    {
        "key": "t_section",
        "name": "T Section",
        "description": "T-shaped structural section",
        "icon": "type",
        "fields": [
            {"key": "flange_width", "label": "Flange Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "stem_height", "label": "Stem Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_thickness", "label": "Flange Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "stem_thickness", "label": "Stem Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (W×tf + H×ts) × L",
        "formula_type": "t_section"
    },
    {
        "key": "z_section",
        "name": "Z Section",
        "description": "Z-shaped structural section",
        "icon": "type",
        "fields": [
            {"key": "height", "label": "Total Height", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "flange_width", "label": "Flange Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = t × (H + 2W - 2t) × L",
        "formula_type": "z_section"
    },
    
    # ======================
    # FLAT PRODUCTS
    # ======================
    {
        "key": "plate",
        "name": "Plate",
        "description": "Flat thick plate (> 5mm)",
        "icon": "rectangle-horizontal",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "inch", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = thickness × width × length",
        "formula_type": "plate"
    },
    {
        "key": "sheet",
        "name": "Sheet",
        "description": "Thin flat sheet (< 5mm)",
        "icon": "layers",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "inch", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = thickness × width × length",
        "formula_type": "sheet"
    },
    {
        "key": "chequered_plate",
        "name": "Chequered Plate",
        "description": "Anti-slip patterned plate",
        "icon": "grid-3x3",
        "fields": [
            {"key": "thickness", "label": "Base Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "inch", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = (thickness × 1.05) × width × length",
        "formula_type": "chequered_plate"
    },
    {
        "key": "perforated_sheet",
        "name": "Perforated Sheet",
        "description": "Sheet with hole pattern",
        "icon": "grip-horizontal",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "inch", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
            {"key": "open_area", "label": "Open Area (%)", "unit_options": ["%"], "default_unit": "%", "required": True},
        ],
        "formula": "V = thickness × width × length × (1 - open_area/100)",
        "formula_type": "perforated_sheet"
    },
    
    # ======================
    # WIRE & COIL PRODUCTS
    # ======================
    {
        "key": "wire_rod",
        "name": "Wire Rod",
        "description": "Round wire rod",
        "icon": "minus",
        "fields": [
            {"key": "diameter", "label": "Diameter", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = π × (d/2)² × L",
        "formula_type": "round_bar"
    },
    {
        "key": "strip",
        "name": "Strip",
        "description": "Narrow flat strip",
        "icon": "minus",
        "fields": [
            {"key": "width", "label": "Width", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": LENGTH_UNITS, "default_unit": "meter", "required": True},
        ],
        "formula": "V = width × thickness × length",
        "formula_type": "flat_bar"
    },
    {
        "key": "coil",
        "name": "Coil",
        "description": "Rolled coil (specify sheet dimensions)",
        "icon": "disc",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": DIMENSION_UNITS, "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Total Length", "unit_options": ["meter"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = thickness × width × length",
        "formula_type": "plate"
    },
]


async def seed_database():
    """Seed the database with materials and shapes"""
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "midconnect")
    
    print(f"Connecting to MongoDB: {DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    now = datetime.now(timezone.utc)
    
    # ========================================
    # SEED MATERIALS
    # ========================================
    print("\n=== Seeding Materials ===")
    
    for material in MATERIALS:
        existing = await db.materials.find_one({"name": material["name"]})
        if existing:
            print(f"  [EXISTS] {material['name']}")
        else:
            doc = {
                "_id": ObjectId(),
                "name": material["name"],
                "density": material["density"],
                "description": material.get("description"),
                "isActive": True,
                "createdAt": now,
                "updatedAt": now
            }
            await db.materials.insert_one(doc)
            print(f"  [CREATED] {material['name']} ({material['density']} kg/m³)")
    
    # ========================================
    # SEED SHAPES
    # ========================================
    print("\n=== Seeding Shapes ===")
    
    for shape in SHAPES:
        existing = await db.shapes.find_one({"key": shape["key"]})
        if existing:
            # Update existing shape with new fields
            await db.shapes.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "name": shape["name"],
                    "description": shape.get("description"),
                    "icon": shape.get("icon"),
                    "fields": shape["fields"],
                    "formula": shape["formula"],
                    "formula_type": shape["formula_type"],
                    "updatedAt": now
                }}
            )
            print(f"  [UPDATED] {shape['name']} ({shape['key']})")
        else:
            doc = {
                "_id": ObjectId(),
                "key": shape["key"],
                "name": shape["name"],
                "description": shape.get("description"),
                "icon": shape.get("icon"),
                "fields": shape["fields"],
                "formula": shape["formula"],
                "formula_type": shape["formula_type"],
                "isActive": True,
                "createdAt": now,
                "updatedAt": now
            }
            await db.shapes.insert_one(doc)
            print(f"  [CREATED] {shape['name']} ({shape['key']})")
    
    # ========================================
    # SUMMARY
    # ========================================
    material_count = await db.materials.count_documents({})
    shape_count = await db.shapes.count_documents({})
    
    print(f"\n=== Summary ===")
    print(f"Total Materials: {material_count}")
    print(f"Total Shapes: {shape_count}")
    print("Seeding complete!")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
