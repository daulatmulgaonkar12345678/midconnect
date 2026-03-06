"""
Configurable Calculator System - Database Models and API

This module provides a fully admin-configurable calculator system where:
- Admins define calculator templates with custom fields
- Admins write formula expressions (evaluated safely)
- Materials have per-unit weights (permanent values)
- Calculators are linked to categories
- No hardcoding required for new calculators
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
import math
import re

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UnitDefinition(BaseModel):
    """Single unit within a unit group"""
    key: str = Field(..., description="Unique key like 'mm', 'kg', 'liter'")
    label: str = Field(..., description="Display label like 'Millimeter'")
    conversion_to_base: float = Field(..., description="Multiply by this to get base unit")

class UnitGroupCreate(BaseModel):
    """Create a unit group (length, weight, volume, etc.)"""
    name: str = Field(..., description="Group name like 'length', 'weight'")
    display_name: str = Field(..., description="Display name like 'Length'")
    units: List[UnitDefinition]
    base_unit: str = Field(..., description="Base unit key for conversions")

class UnitGroupUpdate(BaseModel):
    """Update a unit group"""
    display_name: Optional[str] = None
    units: Optional[List[UnitDefinition]] = None
    base_unit: Optional[str] = None

class CalculatorFieldDefinition(BaseModel):
    """Single field in a calculator template"""
    key: str = Field(..., description="Field key used in formula, e.g., 'diameter'")
    label: str = Field(..., description="Display label, e.g., 'Diameter'")
    unit_group: str = Field(..., description="Unit group name, e.g., 'length'")
    default_unit: str = Field(..., description="Default unit, e.g., 'mm'")
    required: bool = Field(default=True)
    order: int = Field(default=0, description="Display order")
    placeholder: Optional[str] = None
    help_text: Optional[str] = None

class MaterialFormulaOverride(BaseModel):
    """Formula override for specific materials"""
    material_ids: List[str] = Field(..., description="List of material IDs this formula applies to")
    formula_expression: str = Field(..., description="Formula for these materials")
    fields: Optional[List[CalculatorFieldDefinition]] = Field(None, description="Custom fields for this formula (optional)")
    description: Optional[str] = Field(None, description="Description of this formula variant, e.g., 'Hollow Pipe', 'Solid Bar'")

class CalculatorTemplateCreate(BaseModel):
    """Create a calculator template"""
    name: str = Field(..., description="Calculator name, e.g., 'Round Bar Calculator'")
    slug: str = Field(..., description="URL slug, e.g., 'round-bar'")
    category_id: Optional[str] = Field(None, description="Linked category ObjectId")
    description: Optional[str] = None
    fields: List[CalculatorFieldDefinition]
    formula_expression: str = Field(..., description="Default math formula")
    material_formulas: Optional[List[MaterialFormulaOverride]] = Field(
        default=None, 
        description="Material-specific formula overrides"
    )
    output_unit: str = Field(default="kg", description="Output unit, e.g., 'kg', 'liter'")
    output_label: str = Field(default="Weight", description="Output label, e.g., 'Weight', 'Volume'")
    material_family: Optional[str] = Field(None, description="Material family for filtering, e.g., 'Steel', 'Stainless Steel'")
    use_material_density: bool = Field(default=True, description="Whether formula uses material_density variable")
    icon: Optional[str] = None

class CalculatorTemplateUpdate(BaseModel):
    """Update a calculator template"""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    fields: Optional[List[CalculatorFieldDefinition]] = None
    formula_expression: Optional[str] = None
    material_formulas: Optional[List[MaterialFormulaOverride]] = None
    output_unit: Optional[str] = None
    output_label: Optional[str] = None
    material_family: Optional[str] = None
    use_material_density: Optional[bool] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None

class MaterialCreate(BaseModel):
    """Create a material with density and per-unit weights"""
    name: str = Field(..., description="Material name, e.g., 'SS304 Circular bar'")
    material_family: str = Field(..., description="Family/group, e.g., 'Stainless Steel', 'Steel', 'Aluminum'")
    shape_type: Optional[str] = Field(None, description="Shape type: circular_bar, hollow_pipe, square_bar, etc.")
    linked_product_slug: Optional[str] = Field(None, description="Linked product slug for auto-matching")
    calculator_id: Optional[str] = Field(None, description="Linked calculator ID for this material")
    density: Optional[float] = Field(None, description="Density in kg/m³")
    weight_per_unit: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Pre-calculated weights, e.g., {'10mm_round_per_meter': 0.617}"
    )
    description: Optional[str] = None

class MaterialUpdate(BaseModel):
    """Update a material"""
    name: Optional[str] = None
    material_family: Optional[str] = None
    shape_type: Optional[str] = None
    linked_product_slug: Optional[str] = None
    calculator_id: Optional[str] = None
    density: Optional[float] = None
    weight_per_unit: Optional[Dict[str, float]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class CalculationRequest(BaseModel):
    """Request to calculate using a calculator template"""
    calculator_id: str = Field(..., description="Calculator template ID")
    material_id: Optional[str] = Field(None, description="Selected material ID")
    field_values: Dict[str, float] = Field(..., description="Field values, e.g., {'diameter': 20, 'length': 6}")
    field_units: Dict[str, str] = Field(..., description="Field units, e.g., {'diameter': 'mm', 'length': 'm'}")
    quantity: int = Field(default=1, ge=1)

class CalculationResult(BaseModel):
    """Calculation result"""
    calculator_name: str
    material_name: Optional[str]
    calculated_value: float
    output_unit: str
    output_label: str
    value_per_piece: float
    total_value: float
    quantity: int
    field_summary: Dict[str, str]
    formula_used: str
    formula_description: Optional[str] = None


# ============================================================================
# SAFE FORMULA EVALUATOR
# ============================================================================

class SafeFormulaEvaluator:
    """
    Safely evaluates mathematical expressions without using eval().
    Only allows basic math operations and predefined functions.
    """
    
    # Allowed functions and constants
    ALLOWED_NAMES = {
        'pi': math.pi,
        'e': math.e,
        'sqrt': math.sqrt,
        'pow': pow,
        'abs': abs,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'floor': math.floor,
        'ceil': math.ceil,
        'round': round,
        'min': min,
        'max': max,
    }
    
    @classmethod
    def evaluate(cls, expression: str, variables: Dict[str, float]) -> float:
        """
        Safely evaluate a mathematical expression.
        
        Args:
            expression: Math expression like "pi * pow(d/2, 2) * L"
            variables: Variable values like {"d": 0.02, "L": 6}
            
        Returns:
            Calculated result
            
        Raises:
            ValueError: If expression is invalid or contains disallowed operations
        """
        # Validate expression - only allow safe characters
        if not re.match(r'^[\w\s\+\-\*\/\(\)\.\,\^]+$', expression):
            raise ValueError(f"Expression contains invalid characters: {expression}")
        
        # Replace ^ with ** for power operations
        expression = expression.replace('^', '**')
        
        # Build safe namespace
        safe_namespace = cls.ALLOWED_NAMES.copy()
        safe_namespace.update(variables)
        
        # Additional safety: ensure no builtins
        safe_namespace['__builtins__'] = {}
        
        try:
            # Compile and evaluate
            code = compile(expression, '<string>', 'eval')
            
            # Check that all names in code are allowed
            for name in code.co_names:
                if name not in safe_namespace:
                    raise ValueError(f"Unknown variable or function: {name}")
            
            result = eval(code, safe_namespace)
            
            if not isinstance(result, (int, float)):
                raise ValueError(f"Expression did not return a number: {result}")
                
            return float(result)
            
        except SyntaxError as e:
            raise ValueError(f"Invalid formula syntax: {e}")
        except ZeroDivisionError:
            raise ValueError("Division by zero in formula")
        except Exception as e:
            raise ValueError(f"Formula evaluation error: {e}")


# ============================================================================
# UNIT CONVERSION SERVICE
# ============================================================================

class UnitConversionService:
    """Handles unit conversions using database-stored unit groups"""
    
    def __init__(self, db):
        self.db = db
        self._cache = {}
    
    async def get_unit_groups(self) -> Dict[str, Dict]:
        """Get all unit groups as a dictionary"""
        if not self._cache:
            cursor = self.db.unit_groups.find({"is_active": {"$ne": False}})
            async for group in cursor:
                self._cache[group["name"]] = {
                    "display_name": group.get("display_name", group["name"]),
                    "base_unit": group["base_unit"],
                    "units": {u["key"]: u for u in group["units"]}
                }
        return self._cache
    
    async def convert_to_base(self, value: float, unit: str, unit_group: str) -> float:
        """Convert a value to the base unit of its group"""
        groups = await self.get_unit_groups()
        
        if unit_group not in groups:
            raise ValueError(f"Unknown unit group: {unit_group}")
        
        group = groups[unit_group]
        if unit not in group["units"]:
            raise ValueError(f"Unknown unit '{unit}' in group '{unit_group}'")
        
        conversion_factor = group["units"][unit]["conversion_to_base"]
        return value * conversion_factor
    
    async def convert(self, value: float, from_unit: str, to_unit: str, unit_group: str) -> float:
        """Convert between units in the same group"""
        groups = await self.get_unit_groups()
        
        if unit_group not in groups:
            raise ValueError(f"Unknown unit group: {unit_group}")
        
        group = groups[unit_group]
        if from_unit not in group["units"]:
            raise ValueError(f"Unknown unit '{from_unit}' in group '{unit_group}'")
        if to_unit not in group["units"]:
            raise ValueError(f"Unknown unit '{to_unit}' in group '{unit_group}'")
        
        # Convert to base, then to target
        base_value = value * group["units"][from_unit]["conversion_to_base"]
        return base_value / group["units"][to_unit]["conversion_to_base"]
    
    def clear_cache(self):
        """Clear the unit groups cache"""
        self._cache = {}


# ============================================================================
# CALCULATOR SERVICE
# ============================================================================

class ConfigurableCalculatorService:
    """
    Main service for the configurable calculator system.
    Handles template management, calculations, and pricing.
    """
    
    def __init__(self, db):
        self.db = db
        self.unit_service = UnitConversionService(db)
    
    async def calculate(self, request: CalculationRequest) -> CalculationResult:
        """
        Perform a calculation using a calculator template.
        
        1. Load calculator template
        2. Load material (if needed)
        3. Check for material-specific formula override
        4. Convert all field values to base units
        5. Evaluate formula expression
        6. Return result with summary
        """
        # Load calculator template
        try:
            calc_id = ObjectId(request.calculator_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid calculator ID")
        
        calculator = await self.db.calculator_templates.find_one({"_id": calc_id})
        if not calculator:
            raise HTTPException(status_code=404, detail="Calculator not found")
        
        # Load material if specified
        material = None
        material_density = 1.0  # Default if no material
        
        if request.material_id:
            try:
                mat_id = ObjectId(request.material_id)
                material = await self.db.materials.find_one({"_id": mat_id})
                if material and material.get("density"):
                    material_density = material["density"]
            except:
                pass
        
        # Check for material-specific formula override
        formula = calculator["formula_expression"]
        fields_to_use = calculator["fields"]
        formula_description = None
        
        if request.material_id and calculator.get("material_formulas"):
            for override in calculator["material_formulas"]:
                if request.material_id in override.get("material_ids", []):
                    # Found a material-specific formula
                    formula = override["formula_expression"]
                    formula_description = override.get("description")
                    # Use custom fields if provided, otherwise use default
                    if override.get("fields"):
                        fields_to_use = override["fields"]
                    break
        
        # Build field lookup
        field_configs = {f["key"]: f for f in fields_to_use}
        
        # Convert all field values to base units
        converted_values = {}
        field_summary = {}
        
        for field_key, value in request.field_values.items():
            if field_key not in field_configs:
                continue
            
            field_config = field_configs[field_key]
            unit = request.field_units.get(field_key, field_config["default_unit"])
            unit_group = field_config["unit_group"]
            
            # Convert to base unit
            base_value = await self.unit_service.convert_to_base(value, unit, unit_group)
            converted_values[field_key] = base_value
            
            # Store summary
            field_summary[field_key] = f"{value} {unit}"
        
        # Add material density to variables
        converted_values["material_density"] = material_density
        converted_values["density"] = material_density  # Alias
        
        # Evaluate formula
        try:
            calculated_value = SafeFormulaEvaluator.evaluate(formula, converted_values)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Apply quantity
        value_per_piece = calculated_value
        total_value = calculated_value * request.quantity
        
        return CalculationResult(
            calculator_name=calculator["name"],
            material_name=material["name"] if material else None,
            calculated_value=round(calculated_value, 4),
            output_unit=calculator.get("output_unit", "kg"),
            output_label=calculator.get("output_label", "Weight"),
            value_per_piece=round(value_per_piece, 4),
            total_value=round(total_value, 4),
            quantity=request.quantity,
            field_summary=field_summary,
            formula_used=formula,
            formula_description=formula_description
        )
    
    async def get_calculator_for_category(self, category_id: str) -> Optional[Dict]:
        """Get the calculator template linked to a category"""
        try:
            cat_id = ObjectId(category_id)
        except:
            return None
        
        calculator = await self.db.calculator_templates.find_one({
            "category_id": cat_id,
            "is_active": {"$ne": False}
        })
        
        if calculator:
            calculator["_id"] = str(calculator["_id"])
            calculator["category_id"] = str(calculator["category_id"]) if calculator.get("category_id") else None
        
        return calculator
    
    async def calculate_seller_price(
        self,
        calculated_quantity: float,
        seller_rate: float,
        seller_unit: str,
        output_unit: str
    ) -> float:
        """
        Calculate final price for a seller.
        
        Converts units if needed and multiplies by rate.
        """
        # If units match, simple multiplication
        if seller_unit == output_unit:
            return calculated_quantity * seller_rate
        
        # Try to convert (e.g., kg to ton)
        try:
            converted_quantity = await self.unit_service.convert(
                calculated_quantity, output_unit, seller_unit, "weight"
            )
            return converted_quantity * seller_rate
        except:
            # If conversion fails, assume same unit
            return calculated_quantity * seller_rate


# ============================================================================
# API ROUTER
# ============================================================================

def create_configurable_calculator_router(db):
    """Create the API router for configurable calculators"""
    
    router = APIRouter(tags=["Configurable Calculator"])
    service = ConfigurableCalculatorService(db)
    
    # ========================
    # UNIT GROUPS
    # ========================
    
    @router.get("/unit-groups")
    async def get_unit_groups():
        """Get all unit groups"""
        groups = []
        cursor = db.unit_groups.find({"is_active": {"$ne": False}})
        async for group in cursor:
            group["_id"] = str(group["_id"])
            groups.append(group)
        return groups
    
    @router.post("/unit-groups")
    async def create_unit_group(data: UnitGroupCreate):
        """Create a new unit group"""
        now = datetime.now(timezone.utc)
        doc = {
            **data.model_dump(),
            "is_active": True,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.unit_groups.insert_one(doc)
        service.unit_service.clear_cache()
        return {"id": str(result.inserted_id), "message": "Unit group created"}
    
    @router.put("/unit-groups/{group_id}")
    async def update_unit_group(group_id: str, data: UnitGroupUpdate):
        """Update a unit group"""
        try:
            oid = ObjectId(group_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        update_data["updatedAt"] = datetime.now(timezone.utc)
        
        result = await db.unit_groups.update_one({"_id": oid}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Unit group not found")
        
        service.unit_service.clear_cache()
        return {"message": "Unit group updated"}
    
    # ========================
    # CALCULATOR TEMPLATES
    # ========================
    
    @router.get("/calculators")
    async def get_calculators():
        """Get all calculator templates"""
        calculators = []
        cursor = db.calculator_templates.find({}).sort("name", 1)
        async for calc in cursor:
            calc["_id"] = str(calc["_id"])
            if calc.get("category_id"):
                calc["category_id"] = str(calc["category_id"])
            calculators.append(calc)
        return calculators
    
    @router.get("/calculators/{calc_id}")
    async def get_calculator(calc_id: str):
        """Get a single calculator template"""
        try:
            oid = ObjectId(calc_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        calc = await db.calculator_templates.find_one({"_id": oid})
        if not calc:
            raise HTTPException(status_code=404, detail="Calculator not found")
        
        calc["_id"] = str(calc["_id"])
        if calc.get("category_id"):
            calc["category_id"] = str(calc["category_id"])
        
        return calc
    
    @router.get("/calculators/by-category/{category_id}")
    async def get_calculator_by_category(category_id: str):
        """Get calculator template for a specific category"""
        calc = await service.get_calculator_for_category(category_id)
        if not calc:
            raise HTTPException(status_code=404, detail="No calculator found for this category")
        return calc
    
    @router.post("/calculators")
    async def create_calculator(data: CalculatorTemplateCreate):
        """Create a new calculator template"""
        now = datetime.now(timezone.utc)
        
        doc = data.model_dump()
        
        # Convert category_id to ObjectId if provided
        if doc.get("category_id"):
            try:
                doc["category_id"] = ObjectId(doc["category_id"])
            except:
                raise HTTPException(status_code=400, detail="Invalid category ID")
        
        doc["is_active"] = True
        doc["createdAt"] = now
        doc["updatedAt"] = now
        
        # Validate formula syntax
        try:
            test_vars = {f.key: 1.0 for f in data.fields}
            test_vars["material_density"] = 7850
            test_vars["density"] = 7850
            SafeFormulaEvaluator.evaluate(data.formula_expression, test_vars)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid formula: {e}")
        
        result = await db.calculator_templates.insert_one(doc)
        return {"id": str(result.inserted_id), "message": "Calculator created"}
    
    @router.put("/calculators/{calc_id}")
    async def update_calculator(calc_id: str, data: CalculatorTemplateUpdate):
        """Update a calculator template"""
        try:
            oid = ObjectId(calc_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        # Convert category_id if provided
        if "category_id" in update_data and update_data["category_id"]:
            try:
                update_data["category_id"] = ObjectId(update_data["category_id"])
            except:
                raise HTTPException(status_code=400, detail="Invalid category ID")
        
        # Validate formula if provided
        if "formula_expression" in update_data:
            calc = await db.calculator_templates.find_one({"_id": oid})
            fields = update_data.get("fields", calc.get("fields", []))
            try:
                # Handle both dict and Pydantic model
                test_vars = {}
                for f in fields:
                    if hasattr(f, 'key'):
                        test_vars[f.key] = 1.0
                    elif isinstance(f, dict):
                        test_vars[f["key"]] = 1.0
                test_vars["material_density"] = 7850
                test_vars["density"] = 7850
                SafeFormulaEvaluator.evaluate(update_data["formula_expression"], test_vars)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid formula: {e}")
        
        update_data["updatedAt"] = datetime.now(timezone.utc)
        
        result = await db.calculator_templates.update_one({"_id": oid}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Calculator not found")
        
        return {"message": "Calculator updated"}
    
    @router.delete("/calculators/{calc_id}")
    async def delete_calculator(calc_id: str):
        """Delete a calculator template"""
        try:
            oid = ObjectId(calc_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        result = await db.calculator_templates.delete_one({"_id": oid})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Calculator not found")
        
        return {"message": "Calculator deleted"}
    
    # ========================
    # MATERIALS
    # ========================
    
    @router.get("/materials")
    async def get_materials(
        family: Optional[str] = None,
        material_type: Optional[str] = None  # Backwards compatibility
    ):
        """Get all materials, optionally filtered by family"""
        query = {"is_active": {"$ne": False}, "isActive": {"$ne": False}}
        
        # Filter by material_family
        if family:
            query["$or"] = [
                {"material_family": family},
                {"material_family": {"$regex": family, "$options": "i"}},
                {"material_family": {"$exists": False}}  # Include old materials

           ]
        elif material_type:
            # Backwards compatibility
            query["$or"] = [
                {"material_type": material_type},
                {"material_family": material_type},
                {"material_family": {"$exists": False}}

            ]
        
        materials = []
        cursor = db.materials.find(query).sort("name", 1)
        async for mat in cursor:
            mat["_id"] = str(mat["_id"])
            materials.append(mat)
        return materials
    
    @router.get("/materials/families")
    async def get_material_families():
        """Get distinct material families"""
        families = await db.materials.distinct("material_family", {"is_active": {"$ne": False}})
        # Filter out None values
        return [f for f in families if f]
    
    @router.get("/materials/by-product/{product_name}")
    async def get_material_by_product_name(product_name: str):
        """Find material that matches product name (case-insensitive, fuzzy match)"""
        # Try exact match first (case-insensitive)
        material = await db.materials.find_one({
            "name": {"$regex": f"^{product_name}$", "$options": "i"},
            "is_active": {"$ne": False}
        })
        
        if material:
            material["_id"] = str(material["_id"])
            return material
        
        # Try partial match - product name contains material name or vice versa
        # e.g., "SS304 Round Bar 10mm" should match "SS304 Round Bar"
        materials = []
        cursor = db.materials.find({"is_active": {"$ne": False}})
        async for mat in cursor:
            mat_name = mat.get("name", "").lower()
            prod_name = product_name.lower()
            
            # Check if material name is contained in product name
            if mat_name in prod_name or prod_name in mat_name:
                mat["_id"] = str(mat["_id"])
                mat["match_score"] = len(mat_name) if mat_name in prod_name else len(prod_name)
                materials.append(mat)
        
        # Return best match (longest match)
        if materials:
            materials.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return materials[0]
        
        return None
    
    @router.get("/materials/search")
    async def search_materials(q: str, limit: int = 10):
        """Search materials by name (for autocomplete)"""
        query = {
            "name": {"$regex": q, "$options": "i"},
            "is_active": {"$ne": False}
        }
        
        materials = []
        cursor = db.materials.find(query).sort("name", 1).limit(limit)
        async for mat in cursor:
            mat["_id"] = str(mat["_id"])
            materials.append(mat)
        return materials
    
    @router.get("/materials/types")
    async def get_material_types():
        """Get distinct material types"""
        types = await db.materials.distinct("material_type", {"is_active": {"$ne": False}})
        return types
    
    @router.post("/materials")
    async def create_material(data: MaterialCreate):
        """Create a new material"""
        now = datetime.now(timezone.utc)
        doc = {
            **data.model_dump(),
            "is_active": True,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.materials.insert_one(doc)
        return {"id": str(result.inserted_id), "message": "Material created"}
    
    @router.put("/materials/{material_id}")
    async def update_material(material_id: str, data: MaterialUpdate):
        """Update a material"""
        try:
            oid = ObjectId(material_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        update_data["updatedAt"] = datetime.now(timezone.utc)
        
        result = await db.materials.update_one({"_id": oid}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Material not found")
        
        return {"message": "Material updated"}
    
    @router.delete("/materials/{material_id}")
    async def delete_material(material_id: str):
        """Delete a material (soft delete)"""
        try:
            oid = ObjectId(material_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid ID")
        
        result = await db.materials.update_one(
            {"_id": oid},
            {"$set": {"is_active": False, "updatedAt": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Material not found")
        
        return {"message": "Material deleted"}
    
    # ========================
    # CALCULATION
    # ========================
    
    @router.post("/calculate")
    async def perform_calculation(request: CalculationRequest):
        """Perform a calculation using a calculator template"""
        return await service.calculate(request)
    
    @router.post("/calculate-with-prices")
    async def calculate_with_seller_prices(
        request: CalculationRequest,
        product_id: Optional[str] = None
    ):
        """
        Perform calculation and return prices for all sellers.
        
        1. Calculate quantity/weight
        2. Get sellers for product
        3. Calculate price for each seller
        4. Return sorted by price
        """
        # First calculate
        result = await service.calculate(request)
        
        if not product_id:
            return {
                "calculation": result.model_dump(),
                "seller_prices": []
            }
        
        # Get sellers with rates
        try:
            prod_id = ObjectId(product_id)
        except:
            return {
                "calculation": result.model_dump(),
                "seller_prices": []
            }
        
        seller_prices = []
        cursor = db.sellerListings.find({
            "productId": prod_id,
            "status": "active",
            "rate_per_unit": {"$exists": True, "$gt": 0}
        })
        
        async for listing in cursor:
            seller_rate = listing.get("rate_per_unit", 0)
            seller_unit = listing.get("rate_unit", result.output_unit)
            
            # Calculate price
            final_price = await service.calculate_seller_price(
                result.total_value,
                seller_rate,
                seller_unit,
                result.output_unit
            )
            
            # Get seller info
            seller = await db.users.find_one(
                {"_id": listing.get("sellerId")},
                {"companyName": 1, "city": 1, "badgeType": 1}
            )
            
            seller_prices.append({
                "listing_id": str(listing["_id"]),
                "seller_id": str(listing.get("sellerId")),
                "seller_name": seller.get("companyName", "Seller") if seller else "Seller",
                "seller_city": seller.get("city") if seller else None,
                "badge_type": seller.get("badgeType") if seller else None,
                "rate_per_unit": seller_rate,
                "rate_unit": seller_unit,
                "calculated_quantity": result.total_value,
                "final_price": round(final_price, 2),
                "price_display": f"₹{final_price:,.2f}"
            })
        
        # Sort by price
        seller_prices.sort(key=lambda x: x["final_price"])
        
        return {
            "calculation": result.model_dump(),
            "seller_prices": seller_prices
        }
    
    @router.get("/sellers-by-product/{product_id}")
    async def get_sellers_with_rates(product_id: str):
        """
        Get all sellers for a product with their rate_per_unit.
        Used by the frontend calculator to show seller price comparisons.
        """
        try:
            prod_id = ObjectId(product_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        sellers = []
        
        # Get seller listings with rates
        pipeline = [
            {
                "$match": {
                    "productId": prod_id,
                    "status": "active"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sellerId",
                    "foreignField": "_id",
                    "as": "sellerData"
                }
            },
            {
                "$unwind": {
                    "path": "$sellerData",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "sellerId": 1,
                    "rate_per_unit": 1,
                    "rate_unit": 1,
                    "moq": 1,
                    "stock": 1,
                    "leadTime": 1,
                    "pricingTiers": 1,
                    "searchableAttributes": 1,
                    "seller": {
                        "companyName": {"$ifNull": ["$sellerData.profile.businessName", "$sellerData.companyName"]},
                        "city": "$sellerData.profile.city",
                        "state": "$sellerData.profile.state",
                        "badgeType": "$sellerData.badgeType",
                        "rating": "$sellerData.rating",
                        "reviewCount": "$sellerData.reviewCount"
                    }
                }
            }
        ]
        
        async for listing in db.sellerListings.aggregate(pipeline):
            seller_info = listing.get("seller", {})
            
            # Get rate from rate_per_unit or from pricingTiers
            rate = listing.get("rate_per_unit", 0)
            rate_unit = listing.get("rate_unit", "kg")
            
            if not rate and listing.get("pricingTiers"):
                tiers = listing["pricingTiers"]
                if tiers and len(tiers) > 0:
                    rate = tiers[0].get("pricePerUnit", 0)
                    rate_unit = tiers[0].get("unit", "pc")
            
            # Get material type from searchableAttributes
            attrs = listing.get("searchableAttributes", {})
            material_type = attrs.get("material") or attrs.get("materialType") or attrs.get("Material")
            
            sellers.append({
                "_id": str(listing["_id"]),
                "sellerId": str(listing["sellerId"]),
                "sellerName": seller_info.get("companyName") or "Verified Seller",
                "companyName": seller_info.get("companyName"),
                "city": seller_info.get("city"),
                "state": seller_info.get("state"),
                "badgeType": seller_info.get("badgeType"),
                "rating": seller_info.get("rating"),
                "reviewCount": seller_info.get("reviewCount"),
                "rate_per_unit": rate,
                "rate_unit": rate_unit,
                "minOrderQty": listing.get("moq", 1),
                "leadTime": listing.get("leadTime"),
                "stock": listing.get("stock"),
                "materialType": material_type
            })
        
        # Sort by rate (lowest first), putting sellers without rates at the end
        sellers.sort(key=lambda x: (x["rate_per_unit"] == 0, x["rate_per_unit"]))
        
        return sellers
    
    return router
