"""
Raw Material Weight Calculator Service

A reusable calculation engine for computing weight and price of raw materials
based on dimensions, material density, and shape.

Supported shapes:
- round_bar: Solid circular cross-section
- square_bar: Solid square cross-section  
- pipe: Hollow circular cross-section
- plate: Rectangular flat stock (thickness x width x length)
- sheet: Thin flat stock (similar to plate but typically thinner)

All calculations use metric units internally (meters, kg).
Input can be in various units which are converted before calculation.
"""

import math
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

class ShapeType(str, Enum):
    ROUND_BAR = "round_bar"
    SQUARE_BAR = "square_bar"
    PIPE = "pipe"
    PLATE = "plate"
    SHEET = "sheet"


class UnitType(str, Enum):
    # Length units
    MM = "mm"
    CM = "cm"
    METER = "meter"
    INCH = "inch"
    FEET = "feet"
    FT = "ft"  # Alias for feet


# Unit conversion factors to meters
UNIT_TO_METERS: Dict[str, float] = {
    "mm": 0.001,
    "cm": 0.01,
    "meter": 1.0,
    "m": 1.0,
    "inch": 0.0254,
    "in": 0.0254,
    "feet": 0.3048,
    "ft": 0.3048,
}


# Default material densities (kg/m³)
DEFAULT_MATERIALS: Dict[str, float] = {
    "MS Steel": 7850,
    "SS304": 7930,
    "SS316": 8000,
    "Aluminum": 2700,
    "Copper": 8960,
    "Brass": 8500,
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DimensionInput(BaseModel):
    """Input dimensions for weight calculation"""
    # Common fields
    length: float = Field(..., gt=0, description="Length of the material")
    length_unit: str = Field(default="meter", description="Unit of length")
    quantity: int = Field(default=1, ge=1, description="Number of pieces")
    
    # Shape-specific fields (optional based on shape)
    diameter: Optional[float] = Field(default=None, gt=0, description="Diameter for round shapes")
    diameter_unit: Optional[str] = Field(default="mm")
    
    outer_diameter: Optional[float] = Field(default=None, gt=0, description="Outer diameter for pipes")
    outer_diameter_unit: Optional[str] = Field(default="mm")
    
    inner_diameter: Optional[float] = Field(default=None, gt=0, description="Inner diameter for pipes")
    inner_diameter_unit: Optional[str] = Field(default="mm")
    
    thickness: Optional[float] = Field(default=None, gt=0, description="Wall thickness for pipes, or plate thickness")
    thickness_unit: Optional[str] = Field(default="mm")
    
    width: Optional[float] = Field(default=None, gt=0, description="Width for plates/sheets")
    width_unit: Optional[str] = Field(default="mm")
    
    side: Optional[float] = Field(default=None, gt=0, description="Side length for square bars")
    side_unit: Optional[str] = Field(default="mm")


class CalculationResult(BaseModel):
    """Result of weight calculation"""
    shape: str
    material: str
    density: float  # kg/m³
    
    # Calculated values
    volume_per_piece: float  # m³
    weight_per_piece: float  # kg
    total_weight: float  # kg
    
    # Price (if rate provided)
    rate_per_kg: Optional[float] = None
    total_price: Optional[float] = None
    
    # Input summary
    dimensions: Dict[str, Any]
    quantity: int
    
    # Formatted strings for display
    weight_per_piece_display: str
    total_weight_display: str
    total_price_display: Optional[str] = None


# ============================================================================
# UNIT CONVERSION
# ============================================================================

def convert_to_meters(value: float, unit: str) -> float:
    """Convert a length value to meters"""
    unit_lower = unit.lower().strip()
    factor = UNIT_TO_METERS.get(unit_lower, 1.0)
    return value * factor


def format_weight(weight_kg: float) -> str:
    """Format weight for display"""
    if weight_kg >= 1000:
        return f"{weight_kg / 1000:.2f} tonnes"
    elif weight_kg >= 1:
        return f"{weight_kg:.2f} kg"
    else:
        return f"{weight_kg * 1000:.2f} g"


def format_price(price: float, currency: str = "₹") -> str:
    """Format price for display"""
    if price >= 100000:
        return f"{currency}{price / 100000:.2f} L"
    elif price >= 1000:
        return f"{currency}{price:,.0f}"
    else:
        return f"{currency}{price:.2f}"


# ============================================================================
# SHAPE CALCULATORS
# ============================================================================

def calculate_round_bar_volume(diameter_m: float, length_m: float) -> float:
    """
    Calculate volume of a solid round bar.
    
    Formula: V = π × (d/2)² × L
    
    Args:
        diameter_m: Diameter in meters
        length_m: Length in meters
        
    Returns:
        Volume in cubic meters
    """
    radius = diameter_m / 2
    return math.pi * (radius ** 2) * length_m


def calculate_square_bar_volume(side_m: float, length_m: float) -> float:
    """
    Calculate volume of a solid square bar.
    
    Formula: V = side² × L
    
    Args:
        side_m: Side length in meters
        length_m: Length in meters
        
    Returns:
        Volume in cubic meters
    """
    return (side_m ** 2) * length_m


def calculate_pipe_volume(outer_diameter_m: float, inner_diameter_m: float, length_m: float) -> float:
    """
    Calculate volume of a hollow pipe.
    
    Formula: V = π × ((OD/2)² - (ID/2)²) × L
    
    Args:
        outer_diameter_m: Outer diameter in meters
        inner_diameter_m: Inner diameter in meters
        length_m: Length in meters
        
    Returns:
        Volume in cubic meters
    """
    outer_radius = outer_diameter_m / 2
    inner_radius = inner_diameter_m / 2
    return math.pi * ((outer_radius ** 2) - (inner_radius ** 2)) * length_m


def calculate_pipe_volume_from_thickness(outer_diameter_m: float, thickness_m: float, length_m: float) -> float:
    """
    Calculate volume of a hollow pipe using wall thickness.
    
    Formula: V = π × ((OD/2)² - ((OD-2t)/2)²) × L
    
    Args:
        outer_diameter_m: Outer diameter in meters
        thickness_m: Wall thickness in meters
        length_m: Length in meters
        
    Returns:
        Volume in cubic meters
    """
    inner_diameter_m = outer_diameter_m - (2 * thickness_m)
    if inner_diameter_m <= 0:
        raise ValueError("Thickness cannot be greater than half the outer diameter")
    return calculate_pipe_volume(outer_diameter_m, inner_diameter_m, length_m)


def calculate_plate_volume(thickness_m: float, width_m: float, length_m: float) -> float:
    """
    Calculate volume of a rectangular plate/sheet.
    
    Formula: V = thickness × width × length
    
    Args:
        thickness_m: Thickness in meters
        width_m: Width in meters
        length_m: Length in meters
        
    Returns:
        Volume in cubic meters
    """
    return thickness_m * width_m * length_m


# ============================================================================
# MAIN CALCULATOR SERVICE
# ============================================================================

class WeightCalculatorService:
    """
    Main service for calculating weight and price of raw materials.
    
    Usage:
        service = WeightCalculatorService()
        result = service.calculate(
            shape="round_bar",
            material="MS Steel",
            dimensions={"diameter": 10, "diameter_unit": "mm", "length": 6, "length_unit": "meter"},
            quantity=5,
            rate_per_kg=70
        )
    """
    
    def __init__(self, db=None):
        """
        Initialize the calculator service.
        
        Args:
            db: Optional MongoDB database connection for loading materials
        """
        self.db = db
        self._materials_cache: Dict[str, float] = {}
    
    async def get_material_density(self, material_name: str) -> float:
        """
        Get density for a material. First checks database, then defaults.
        
        Args:
            material_name: Name of the material
            
        Returns:
            Density in kg/m³
        """
        # Check cache first
        if material_name in self._materials_cache:
            return self._materials_cache[material_name]
        
        # Try database
        if self.db is not None:
            material = await self.db.materials.find_one({"name": material_name})
            if material:
                density = material.get("density", DEFAULT_MATERIALS.get(material_name, 7850))
                self._materials_cache[material_name] = density
                return density
        
        # Fall back to defaults
        density = DEFAULT_MATERIALS.get(material_name, 7850)
        self._materials_cache[material_name] = density
        return density
    
    async def get_all_materials(self) -> List[Dict[str, Any]]:
        """Get all materials from database or defaults"""
        if self.db is not None:
            materials = await self.db.materials.find({"isActive": {"$ne": False}}).to_list(100)
            if materials:
                return [{"name": m["name"], "density": m["density"], "_id": str(m["_id"])} for m in materials]
        
        # Return defaults
        return [{"name": name, "density": density} for name, density in DEFAULT_MATERIALS.items()]
    
    def calculate_sync(
        self,
        shape: str,
        material: str,
        density: float,
        dimensions: Dict[str, Any],
        quantity: int = 1,
        rate_per_kg: Optional[float] = None
    ) -> CalculationResult:
        """
        Synchronous calculation method (for client-side or when density is known).
        
        Args:
            shape: Shape type (round_bar, square_bar, pipe, plate, sheet)
            material: Material name
            density: Material density in kg/m³
            dimensions: Dictionary of dimensions with units
            quantity: Number of pieces
            rate_per_kg: Optional price per kg
            
        Returns:
            CalculationResult with all calculated values
        """
        shape_lower = shape.lower().strip()
        
        # Calculate volume based on shape
        if shape_lower == "round_bar":
            diameter_m = convert_to_meters(
                dimensions.get("diameter", 0),
                dimensions.get("diameter_unit", "mm")
            )
            length_m = convert_to_meters(
                dimensions.get("length", 0),
                dimensions.get("length_unit", "meter")
            )
            volume = calculate_round_bar_volume(diameter_m, length_m)
            dim_summary = {
                "diameter": f"{dimensions.get('diameter')} {dimensions.get('diameter_unit', 'mm')}",
                "length": f"{dimensions.get('length')} {dimensions.get('length_unit', 'meter')}"
            }
            
        elif shape_lower == "square_bar":
            side_m = convert_to_meters(
                dimensions.get("side", 0),
                dimensions.get("side_unit", "mm")
            )
            length_m = convert_to_meters(
                dimensions.get("length", 0),
                dimensions.get("length_unit", "meter")
            )
            volume = calculate_square_bar_volume(side_m, length_m)
            dim_summary = {
                "side": f"{dimensions.get('side')} {dimensions.get('side_unit', 'mm')}",
                "length": f"{dimensions.get('length')} {dimensions.get('length_unit', 'meter')}"
            }
            
        elif shape_lower == "pipe":
            length_m = convert_to_meters(
                dimensions.get("length", 0),
                dimensions.get("length_unit", "meter")
            )
            
            # Can use either OD/ID or OD/thickness
            if dimensions.get("inner_diameter"):
                outer_d_m = convert_to_meters(
                    dimensions.get("outer_diameter", 0),
                    dimensions.get("outer_diameter_unit", "mm")
                )
                inner_d_m = convert_to_meters(
                    dimensions.get("inner_diameter", 0),
                    dimensions.get("inner_diameter_unit", "mm")
                )
                volume = calculate_pipe_volume(outer_d_m, inner_d_m, length_m)
                dim_summary = {
                    "outer_diameter": f"{dimensions.get('outer_diameter')} {dimensions.get('outer_diameter_unit', 'mm')}",
                    "inner_diameter": f"{dimensions.get('inner_diameter')} {dimensions.get('inner_diameter_unit', 'mm')}",
                    "length": f"{dimensions.get('length')} {dimensions.get('length_unit', 'meter')}"
                }
            else:
                outer_d_m = convert_to_meters(
                    dimensions.get("outer_diameter", 0),
                    dimensions.get("outer_diameter_unit", "mm")
                )
                thickness_m = convert_to_meters(
                    dimensions.get("thickness", 0),
                    dimensions.get("thickness_unit", "mm")
                )
                volume = calculate_pipe_volume_from_thickness(outer_d_m, thickness_m, length_m)
                dim_summary = {
                    "outer_diameter": f"{dimensions.get('outer_diameter')} {dimensions.get('outer_diameter_unit', 'mm')}",
                    "thickness": f"{dimensions.get('thickness')} {dimensions.get('thickness_unit', 'mm')}",
                    "length": f"{dimensions.get('length')} {dimensions.get('length_unit', 'meter')}"
                }
                
        elif shape_lower in ("plate", "sheet"):
            thickness_m = convert_to_meters(
                dimensions.get("thickness", 0),
                dimensions.get("thickness_unit", "mm")
            )
            width_m = convert_to_meters(
                dimensions.get("width", 0),
                dimensions.get("width_unit", "mm")
            )
            length_m = convert_to_meters(
                dimensions.get("length", 0),
                dimensions.get("length_unit", "meter")
            )
            volume = calculate_plate_volume(thickness_m, width_m, length_m)
            dim_summary = {
                "thickness": f"{dimensions.get('thickness')} {dimensions.get('thickness_unit', 'mm')}",
                "width": f"{dimensions.get('width')} {dimensions.get('width_unit', 'mm')}",
                "length": f"{dimensions.get('length')} {dimensions.get('length_unit', 'meter')}"
            }
            
        else:
            raise ValueError(f"Unsupported shape: {shape}")
        
        # Calculate weight
        weight_per_piece = volume * density
        total_weight = weight_per_piece * quantity
        
        # Calculate price if rate provided
        total_price = None
        total_price_display = None
        if rate_per_kg is not None:
            total_price = total_weight * rate_per_kg
            total_price_display = format_price(total_price)
        
        return CalculationResult(
            shape=shape_lower,
            material=material,
            density=density,
            volume_per_piece=round(volume, 8),
            weight_per_piece=round(weight_per_piece, 4),
            total_weight=round(total_weight, 4),
            rate_per_kg=rate_per_kg,
            total_price=round(total_price, 2) if total_price else None,
            dimensions=dim_summary,
            quantity=quantity,
            weight_per_piece_display=format_weight(weight_per_piece),
            total_weight_display=format_weight(total_weight),
            total_price_display=total_price_display
        )
    
    async def calculate(
        self,
        shape: str,
        material: str,
        dimensions: Dict[str, Any],
        quantity: int = 1,
        rate_per_kg: Optional[float] = None,
        density: Optional[float] = None
    ) -> CalculationResult:
        """
        Async calculation method that looks up density from database.
        
        Args:
            shape: Shape type
            material: Material name (used to lookup density)
            dimensions: Dictionary of dimensions with units
            quantity: Number of pieces
            rate_per_kg: Optional price per kg
            density: Optional density override (skips lookup)
            
        Returns:
            CalculationResult
        """
        if density is None:
            density = await self.get_material_density(material)
        
        return self.calculate_sync(
            shape=shape,
            material=material,
            density=density,
            dimensions=dimensions,
            quantity=quantity,
            rate_per_kg=rate_per_kg
        )


# ============================================================================
# SHAPE CONFIGURATIONS (for UI generation)
# ============================================================================

SHAPE_CONFIGS = {
    "round_bar": {
        "name": "Round Bar",
        "description": "Solid circular cross-section bar",
        "fields": [
            {"key": "diameter", "label": "Diameter", "unit_options": ["mm", "cm", "inch"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": ["meter", "feet", "cm"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = π × (d/2)² × L",
        "icon": "circle"
    },
    "square_bar": {
        "name": "Square Bar",
        "description": "Solid square cross-section bar",
        "fields": [
            {"key": "side", "label": "Side", "unit_options": ["mm", "cm", "inch"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": ["meter", "feet", "cm"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = side² × L",
        "icon": "square"
    },
    "pipe": {
        "name": "Pipe / Tube",
        "description": "Hollow circular cross-section",
        "fields": [
            {"key": "outer_diameter", "label": "Outer Diameter (OD)", "unit_options": ["mm", "cm", "inch"], "default_unit": "mm", "required": True},
            {"key": "thickness", "label": "Wall Thickness", "unit_options": ["mm", "cm", "inch"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": ["meter", "feet", "cm"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = π × ((OD/2)² - ((OD-2t)/2)²) × L",
        "icon": "circle-dot"
    },
    "plate": {
        "name": "Plate",
        "description": "Flat rectangular stock",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": ["mm", "cm", "inch"], "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": ["meter", "feet", "cm"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = thickness × width × length",
        "icon": "rectangle-horizontal"
    },
    "sheet": {
        "name": "Sheet",
        "description": "Thin flat stock",
        "fields": [
            {"key": "thickness", "label": "Thickness", "unit_options": ["mm", "cm"], "default_unit": "mm", "required": True},
            {"key": "width", "label": "Width", "unit_options": ["mm", "cm", "meter", "feet"], "default_unit": "mm", "required": True},
            {"key": "length", "label": "Length", "unit_options": ["meter", "feet", "cm"], "default_unit": "meter", "required": True},
        ],
        "formula": "V = thickness × width × length",
        "icon": "layers"
    }
}


def get_shape_config(shape: str) -> Dict[str, Any]:
    """Get configuration for a shape type"""
    return SHAPE_CONFIGS.get(shape.lower(), None)


def get_all_shapes() -> List[Dict[str, Any]]:
    """Get all available shapes with their configurations"""
    return [{"key": key, **config} for key, config in SHAPE_CONFIGS.items()]
