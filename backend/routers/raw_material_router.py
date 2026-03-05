"""
Raw Material Calculator API Router

Provides endpoints for:
1. Materials CRUD (admin)
2. Weight calculation API
3. Shape configurations
4. Raw material product/category queries
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    density: float = Field(..., gt=0, le=50000, description="Density in kg/m³")
    description: Optional[str] = Field(default=None, max_length=500)


class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    density: Optional[float] = Field(default=None, gt=0, le=50000)
    description: Optional[str] = Field(default=None, max_length=500)
    isActive: Optional[bool] = None


class CalculateWeightRequest(BaseModel):
    shape: str = Field(..., description="Shape type: round_bar, square_bar, pipe, plate, sheet")
    material: str = Field(..., description="Material name")
    density: Optional[float] = Field(default=None, description="Optional density override")
    dimensions: Dict[str, Any] = Field(..., description="Dimension values with units")
    quantity: int = Field(default=1, ge=1, le=100000)
    rate_per_kg: Optional[float] = Field(default=None, ge=0)


class CategoryTypeUpdate(BaseModel):
    category_type: str = Field(..., pattern="^(standard|raw_material)$")


class ProductTypeUpdate(BaseModel):
    product_type: str = Field(..., pattern="^(standard_product|raw_material|machine|service)$")


class ShapeFieldConfig(BaseModel):
    """Configuration for a dimension field in a shape"""
    key: str = Field(..., min_length=1, max_length=50, description="Field key e.g., 'diameter'")
    label: str = Field(..., min_length=1, max_length=100, description="Display label e.g., 'Diameter'")
    unit_options: List[str] = Field(..., min_length=1, description="Available units e.g., ['mm', 'cm', 'inch']")
    default_unit: str = Field(..., description="Default unit")
    required: bool = Field(default=True)


class ShapeCreate(BaseModel):
    """Create a new shape configuration"""
    key: str = Field(..., min_length=1, max_length=50, pattern="^[a-z_]+$", description="Unique key e.g., 'round_bar'")
    name: str = Field(..., min_length=1, max_length=100, description="Display name e.g., 'Round Bar'")
    description: Optional[str] = Field(default=None, max_length=500)
    icon: Optional[str] = Field(default=None, max_length=50, description="Icon name e.g., 'circle'")
    fields: List[ShapeFieldConfig] = Field(..., min_length=1, description="Dimension fields for this shape")
    formula: str = Field(..., min_length=1, max_length=500, description="Formula e.g., 'V = π × (d/2)² × L'")
    formula_type: str = Field(..., description="Calculation type: volume_cylinder, volume_hollow_cylinder, volume_box, etc.")


class ShapeUpdate(BaseModel):
    """Update an existing shape"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    icon: Optional[str] = Field(default=None, max_length=50)
    fields: Optional[List[ShapeFieldConfig]] = None
    formula: Optional[str] = Field(default=None, max_length=500)
    formula_type: Optional[str] = None
    isActive: Optional[bool] = None


# ============================================================================
# ROUTER FACTORY
# ============================================================================

def create_raw_material_router(db, require_admin, require_verified_seller=None):
    """
    Factory function to create the raw material router with dependencies.
    
    Args:
        db: MongoDB database instance
        require_admin: Admin authentication dependency
        require_verified_seller: Optional seller authentication dependency
    """
    router = APIRouter(tags=["Raw Materials"])
    
    # Import the calculator service
    from services.weight_calculator_service import (
        WeightCalculatorService,
        get_shape_config,
        get_all_shapes,
        SHAPE_CONFIGS,
        DEFAULT_MATERIALS
    )
    
    # ========================================================================
    # PUBLIC ENDPOINTS
    # ========================================================================
    
    @router.get("/materials")
    async def get_materials():
        """Get all active materials with densities"""
        materials = await db.materials.find({"isActive": {"$ne": False}}).to_list(100)
        return [
            {
                "_id": str(m["_id"]),
                "name": m["name"],
                "density": m["density"],
                "description": m.get("description")
            }
            for m in materials
        ]
    
    @router.get("/materials/{material_id}")
    async def get_material(material_id: str):
        """Get a specific material by ID"""
        try:
            material = await db.materials.find_one({"_id": ObjectId(material_id)})
        except:
            raise HTTPException(status_code=400, detail="Invalid material ID")
        
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        
        return {
            "_id": str(material["_id"]),
            "name": material["name"],
            "density": material["density"],
            "description": material.get("description"),
            "isActive": material.get("isActive", True),
            "createdAt": material.get("createdAt"),
            "updatedAt": material.get("updatedAt")
        }
    
    @router.get("/shapes")
    async def get_shapes():
        """Get all supported shapes with their field configurations.
        Loads from database if available, falls back to hardcoded defaults."""
        
        # Try to load from database first
        db_shapes = await db.shapes.find({"isActive": {"$ne": False}}).to_list(100)
        
        if db_shapes and len(db_shapes) > 0:
            return [
                {
                    "_id": str(s["_id"]),
                    "key": s["key"],
                    "name": s["name"],
                    "description": s.get("description"),
                    "icon": s.get("icon"),
                    "fields": s.get("fields", []),
                    "formula": s.get("formula"),
                    "formula_type": s.get("formula_type")
                }
                for s in db_shapes
            ]
        
        # Fallback to hardcoded shapes
        return get_all_shapes()
    
    @router.get("/shapes/{shape}")
    async def get_shape(shape: str):
        """Get configuration for a specific shape"""
        config = get_shape_config(shape)
        if not config:
            raise HTTPException(status_code=404, detail=f"Shape '{shape}' not found")
        return {"key": shape, **config}
    
    @router.post("/calculate")
    async def calculate_weight(data: CalculateWeightRequest):
        """
        Calculate weight and optionally price for raw material.
        
        This is the main calculation endpoint used by:
        - Product pages
        - SEO calculator pages
        - Inquiry generation
        """
        service = WeightCalculatorService(db)
        
        try:
            result = await service.calculate(
                shape=data.shape,
                material=data.material,
                dimensions=data.dimensions,
                quantity=data.quantity,
                rate_per_kg=data.rate_per_kg,
                density=data.density
            )
            return result.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            raise HTTPException(status_code=500, detail="Calculation failed")
    
    @router.get("/raw-material-categories")
    async def get_raw_material_categories():
        """Get all categories marked as raw_material type"""
        categories = await db.categories.find({
            "category_type": "raw_material",
            "isActive": {"$ne": False}
        }).to_list(100)
        
        return [
            {
                "_id": str(c["_id"]),
                "name": c["name"],
                "slug": c.get("slug"),
                "description": c.get("description")
            }
            for c in categories
        ]
    
    @router.get("/raw-material-products")
    async def get_raw_material_products(
        category_id: Optional[str] = None,
        limit: int = Query(default=50, le=100)
    ):
        """Get all products marked as raw_material type"""
        query = {"product_type": "raw_material", "isActive": {"$ne": False}}
        
        if category_id:
            try:
                query["categoryId"] = ObjectId(category_id)
            except:
                pass
        
        products = await db.products.find(query).limit(limit).to_list(limit)
        
        return [
            {
                "_id": str(p["_id"]),
                "name": p.get("name"),
                "slug": p.get("slug"),
                "categoryId": str(p.get("categoryId")) if p.get("categoryId") else None,
                "description": p.get("description"),
                "product_type": p.get("product_type")
            }
            for p in products
        ]
    
    @router.get("/sellers/raw-material/{product_id}")
    async def get_raw_material_sellers(
        product_id: str,
        material: Optional[str] = None
    ):
        """
        Get sellers for a raw material product with their rates.
        
        Returns sellers with rate_per_kg for price calculation.
        """
        try:
            product_oid = ObjectId(product_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # Build query
        query = {
            "productId": product_oid,
            "status": "active",
            "isActive": True,
            "rate_per_kg": {"$exists": True, "$gt": 0}
        }
        
        if material:
            query["$or"] = [
                {"material_supported": material},
                {"material_supported": {"$exists": False}}  # Support all materials
            ]
        
        # Get listings with seller info
        pipeline = [
            {"$match": query},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "_id": 1,
                "sellerId": 1,
                "rate_per_kg": 1,
                "material_supported": 1,
                "moq": 1,
                "stock": 1,
                "leadTime": 1,
                "images": {"$slice": ["$images", 2]},
                "city": 1,
                "state": 1,
                "sellerName": {"$ifNull": [
                    "$seller.profile.businessName",
                    "$seller.businessName",
                    "Verified Seller"
                ]},
                "sellerBadge": "$seller.badgeType"
            }}
        ]
        
        listings = await db.sellerListings.aggregate(pipeline).to_list(50)
        
        return [
            {
                "listingId": str(l["_id"]),
                "sellerId": str(l["sellerId"]),
                "sellerName": l.get("sellerName", "Verified Seller"),
                "sellerBadge": l.get("sellerBadge"),
                "rate_per_kg": l.get("rate_per_kg"),
                "material_supported": l.get("material_supported"),
                "moq": l.get("moq", 1),
                "stock": l.get("stock"),
                "leadTime": l.get("leadTime"),
                "location": f"{l.get('city', '')}, {l.get('state', '')}".strip(", ") or None,
                "images": l.get("images", [])
            }
            for l in listings
        ]
    
    # ========================================================================
    # ADMIN ENDPOINTS
    # ========================================================================
    
    @router.post("/admin/materials", dependencies=[Depends(require_admin)])
    async def create_material(data: MaterialCreate):
        """Create a new material (admin only)"""
        # Check if material already exists
        existing = await db.materials.find_one({"name": data.name})
        if existing:
            raise HTTPException(status_code=409, detail="Material with this name already exists")
        
        now = datetime.now(timezone.utc)
        material = {
            "name": data.name,
            "density": data.density,
            "description": data.description,
            "isActive": True,
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.materials.insert_one(material)
        logger.info(f"Material created: {data.name}")
        
        return {
            "_id": str(result.inserted_id),
            "name": data.name,
            "density": data.density,
            "message": "Material created successfully"
        }
    
    @router.put("/admin/materials/{material_id}", dependencies=[Depends(require_admin)])
    async def update_material(material_id: str, data: MaterialUpdate):
        """Update a material (admin only)"""
        try:
            material_oid = ObjectId(material_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid material ID")
        
        # Check if material exists
        existing = await db.materials.find_one({"_id": material_oid})
        if not existing:
            raise HTTPException(status_code=404, detail="Material not found")
        
        # Check name uniqueness if changing name
        if data.name and data.name != existing["name"]:
            duplicate = await db.materials.find_one({"name": data.name, "_id": {"$ne": material_oid}})
            if duplicate:
                raise HTTPException(status_code=409, detail="Material with this name already exists")
        
        # Build update
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            update_data["name"] = data.name
        if data.density is not None:
            update_data["density"] = data.density
        if data.description is not None:
            update_data["description"] = data.description
        if data.isActive is not None:
            update_data["isActive"] = data.isActive
        
        await db.materials.update_one({"_id": material_oid}, {"$set": update_data})
        logger.info(f"Material updated: {material_id}")
        
        return {"message": "Material updated successfully", "_id": material_id}
    
    @router.delete("/admin/materials/{material_id}", dependencies=[Depends(require_admin)])
    async def delete_material(material_id: str):
        """Soft delete a material (admin only)"""
        try:
            material_oid = ObjectId(material_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid material ID")
        
        result = await db.materials.update_one(
            {"_id": material_oid},
            {"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Material not found")
        
        logger.info(f"Material deleted: {material_id}")
        return {"message": "Material deleted successfully"}
    
    @router.put("/admin/categories/{category_id}/type", dependencies=[Depends(require_admin)])
    async def update_category_type(category_id: str, data: CategoryTypeUpdate):
        """Update category type to standard or raw_material (admin only)"""
        try:
            category_oid = ObjectId(category_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        result = await db.categories.update_one(
            {"_id": category_oid},
            {"$set": {
                "category_type": data.category_type,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.info(f"Category {category_id} type updated to: {data.category_type}")
        return {"message": f"Category type updated to {data.category_type}"}
    
    @router.put("/admin/products/{product_id}/type", dependencies=[Depends(require_admin)])
    async def update_product_type(product_id: str, data: ProductTypeUpdate):
        """Update product type (admin only)"""
        try:
            product_oid = ObjectId(product_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        result = await db.products.update_one(
            {"_id": product_oid},
            {"$set": {
                "product_type": data.product_type,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"Product {product_id} type updated to: {data.product_type}")
        return {"message": f"Product type updated to {data.product_type}"}
    
    @router.get("/admin/materials", dependencies=[Depends(require_admin)])
    async def admin_get_all_materials():
        """Get all materials including inactive (admin only)"""
        materials = await db.materials.find({}).to_list(200)
        return [
            {
                "_id": str(m["_id"]),
                "name": m["name"],
                "density": m["density"],
                "description": m.get("description"),
                "isActive": m.get("isActive", True),
                "createdAt": m.get("createdAt"),
                "updatedAt": m.get("updatedAt")
            }
            for m in materials
        ]
    
    # ========================================================================
    # SHAPES ADMIN CRUD
    # ========================================================================
    
    @router.get("/admin/shapes", dependencies=[Depends(require_admin)])
    async def admin_get_all_shapes():
        """Get all shapes including inactive (admin only)"""
        shapes = await db.shapes.find({}).to_list(100)
        
        # If no shapes in DB, seed with defaults
        if not shapes:
            default_shapes = get_all_shapes()
            for shape in default_shapes:
                shape_doc = {
                    "_id": ObjectId(),
                    "key": shape["key"],
                    "name": shape["name"],
                    "description": shape.get("description"),
                    "icon": shape.get("icon"),
                    "fields": shape.get("fields", []),
                    "formula": shape.get("formula"),
                    "formula_type": shape["key"],  # Use key as formula type
                    "isActive": True,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
                await db.shapes.insert_one(shape_doc)
            shapes = await db.shapes.find({}).to_list(100)
        
        return [
            {
                "_id": str(s["_id"]),
                "key": s["key"],
                "name": s["name"],
                "description": s.get("description"),
                "icon": s.get("icon"),
                "fields": s.get("fields", []),
                "formula": s.get("formula"),
                "formula_type": s.get("formula_type"),
                "isActive": s.get("isActive", True),
                "createdAt": s.get("createdAt"),
                "updatedAt": s.get("updatedAt")
            }
            for s in shapes
        ]
    
    @router.post("/admin/shapes", dependencies=[Depends(require_admin)])
    async def create_shape(data: ShapeCreate):
        """Create a new shape configuration (admin only)"""
        # Check for duplicate key
        existing = await db.shapes.find_one({"key": data.key})
        if existing:
            raise HTTPException(status_code=409, detail=f"Shape with key '{data.key}' already exists")
        
        now = datetime.now(timezone.utc)
        shape_doc = {
            "_id": ObjectId(),
            "key": data.key,
            "name": data.name,
            "description": data.description,
            "icon": data.icon,
            "fields": [f.model_dump() for f in data.fields],
            "formula": data.formula,
            "formula_type": data.formula_type,
            "isActive": True,
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.shapes.insert_one(shape_doc)
        logger.info(f"Shape created: {data.key} - {data.name}")
        
        return {"message": "Shape created successfully", "_id": str(shape_doc["_id"]), "key": data.key}
    
    @router.put("/admin/shapes/{shape_id}", dependencies=[Depends(require_admin)])
    async def update_shape(shape_id: str, data: ShapeUpdate):
        """Update an existing shape (admin only)"""
        try:
            shape_oid = ObjectId(shape_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid shape ID")
        
        existing = await db.shapes.find_one({"_id": shape_oid})
        if not existing:
            raise HTTPException(status_code=404, detail="Shape not found")
        
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.icon is not None:
            update_data["icon"] = data.icon
        if data.fields is not None:
            update_data["fields"] = [f.model_dump() for f in data.fields]
        if data.formula is not None:
            update_data["formula"] = data.formula
        if data.formula_type is not None:
            update_data["formula_type"] = data.formula_type
        if data.isActive is not None:
            update_data["isActive"] = data.isActive
        
        await db.shapes.update_one({"_id": shape_oid}, {"$set": update_data})
        logger.info(f"Shape updated: {shape_id}")
        
        return {"message": "Shape updated successfully", "_id": shape_id}
    
    @router.delete("/admin/shapes/{shape_id}", dependencies=[Depends(require_admin)])
    async def delete_shape(shape_id: str):
        """Soft delete a shape (admin only)"""
        try:
            shape_oid = ObjectId(shape_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid shape ID")
        
        result = await db.shapes.update_one(
            {"_id": shape_oid},
            {"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Shape not found")
        
        logger.info(f"Shape deleted: {shape_id}")
        return {"message": "Shape deleted successfully"}
    
    return router
