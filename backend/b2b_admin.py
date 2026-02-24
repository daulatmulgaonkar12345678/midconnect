"""
B2B Admin Foundation - Phase 1
================================
Admin-controlled structure for B2B marketplace:
- Global Dropdowns (unit systems, seller types, etc.)
- Category Settings (allowed units, seller types, dimensions)
- Spec Templates (dynamic product specifications)

Principle: Admin defines structure. Sellers define business logic.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Literal
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger("b2b_admin")

# ==================== PYDANTIC MODELS ====================

# --- Dropdown Models ---

class DropdownValue(BaseModel):
    """SSOT: All fields use camelCase - Single value in a dropdown"""
    value: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    displayOrder: int = Field(default=0, ge=0)
    isActive: bool = True
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        # Only allow alphanumeric, underscore, hyphen
        import re
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError('Value must be lowercase alphanumeric with underscores/hyphens only')
        return v

class GlobalDropdownCreate(BaseModel):
    """SSOT: All fields use camelCase - Create a new global dropdown"""
    key: str = Field(..., min_length=2, max_length=50, description="Unique identifier")
    name: str = Field(..., min_length=2, max_length=100, description="Display name")
    description: Optional[str] = Field(None, max_length=500)
    values: List[DropdownValue] = Field(..., min_length=1, max_length=100)
    
    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Key must start with letter, contain only lowercase letters, numbers, underscores')
        return v

class GlobalDropdownUpdate(BaseModel):
    """SSOT: All fields use camelCase - Update a global dropdown"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    values: Optional[List[DropdownValue]] = None
    isActive: Optional[bool] = None

# --- Category Settings Models ---

class CategoryDropdownOverride(BaseModel):
    """SSOT: All fields use camelCase - Override global dropdown for a category"""
    enabled: bool = True
    values: Optional[List[DropdownValue]] = None  # If set, overrides global values
    isMandatory: bool = False
    restrictToValues: Optional[List[str]] = None  # Restrict to subset of global values

class CategorySettings(BaseModel):
    """SSOT: All fields use camelCase - Admin-controlled settings for a category"""
    # Unit system
    allowedUnits: List[str] = Field(default=["pcs"], min_length=1)
    defaultUnit: str = "pcs"
    
    # Seller types allowed
    allowedSellerTypes: List[str] = Field(
        default=["manufacturer", "distributor", "dealer"],
        min_length=1
    )
    
    # Dimension system
    dimensionsEnabled: bool = False
    dimensionUnits: List[str] = Field(default=["mm", "cm"])
    dimensionFormat: Optional[Literal["LxW", "LxWxH"]] = None
    
    # Dropdown overrides (key -> override config)
    dropdownOverrides: Dict[str, CategoryDropdownOverride] = Field(default_factory=dict)

class CategoryCreate(BaseModel):
    """SSOT: All fields use camelCase - Create a new category with settings"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = None
    icon: Optional[str] = None
    displayOrder: int = Field(default=0, ge=0)
    settings: Optional[CategorySettings] = None

class CategoryUpdate(BaseModel):
    """SSOT: All fields use camelCase - Update category"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = None
    icon: Optional[str] = None
    displayOrder: Optional[int] = Field(None, ge=0)
    settings: Optional[CategorySettings] = None
    isActive: Optional[bool] = None

# --- Spec Template Models ---

class SpecFieldDefinition(BaseModel):
    """SSOT: All fields use camelCase - Definition of a specification field"""
    key: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    fieldType: Literal["text", "number", "dropdown", "boolean", "range"] = "text"
    
    # Unit for numeric fields
    unit: Optional[str] = Field(None, max_length=20)
    
    # Constraints
    isMandatory: bool = False
    isSellerEditable: bool = True
    isLockedAfterCreate: bool = False
    displayOrder: int = Field(default=0, ge=0)
    
    # For dropdown type - either reference global or inline options
    dropdownKey: Optional[str] = None  # Reference to globalDropdowns.key
    options: Optional[List[str]] = None  # Inline options (if dropdownKey not set)
    
    # For number/range type
    minValue: Optional[float] = None
    maxValue: Optional[float] = None
    
    # Validation hint
    placeholder: Optional[str] = None
    helpText: Optional[str] = None
    
    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Key must start with letter, contain only lowercase letters, numbers, underscores')
        return v

class SpecTemplateCreate(BaseModel):
    """SSOT: All fields use camelCase - Create a new spec template"""
    name: str = Field(..., min_length=2, max_length=100)
    categoryId: str = Field(..., description="Category this template belongs to")
    fields: List[SpecFieldDefinition] = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

class SpecTemplateUpdate(BaseModel):
    """SSOT: All fields use camelCase - Update spec template"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    fields: Optional[List[SpecFieldDefinition]] = None
    description: Optional[str] = Field(None, max_length=500)
    isActive: Optional[bool] = None


# ==================== ROUTER SETUP ====================

def create_b2b_admin_router(db, require_admin):
    """
    Create the B2B admin router with database and auth dependencies.
    
    Args:
        db: MongoDB database instance
        require_admin: Dependency that validates admin access
    """
    router = APIRouter(prefix="/admin/b2b", tags=["B2B Admin"])
    
    # ==================== GLOBAL DROPDOWNS ====================
    
    @router.get("/dropdowns")
    async def list_global_dropdowns(
        admin: dict = Depends(require_admin),
        include_inactive: bool = Query(False),
        include_system: bool = Query(True)
    ):
        """List all global dropdowns"""
        query = {}
        if not include_inactive:
            query["isActive"] = {"$ne": False}
        if not include_system:
            query["isSystem"] = {"$ne": True}
        
        dropdowns = await db.globalDropdowns.find(query).sort("name", 1).to_list(100)
        
        for d in dropdowns:
            d["_id"] = str(d["_id"])
        
        return {"dropdowns": dropdowns, "total": len(dropdowns)}
    
    @router.get("/dropdowns/{key}")
    async def get_global_dropdown(
        key: str,
        admin: dict = Depends(require_admin)
    ):
        """Get a specific global dropdown by key"""
        dropdown = await db.globalDropdowns.find_one({"key": key})
        if not dropdown:
            raise HTTPException(status_code=404, detail="Dropdown not found")
        
        dropdown["_id"] = str(dropdown["_id"])
        return {"dropdown": dropdown}
    
    @router.post("/dropdowns")
    async def create_global_dropdown(
        data: GlobalDropdownCreate,
        admin: dict = Depends(require_admin)
    ):
        """Create a new global dropdown"""
        # Check for duplicate key
        existing = await db.globalDropdowns.find_one({"key": data.key})
        if existing:
            raise HTTPException(status_code=400, detail=f"Dropdown with key '{data.key}' already exists")
        
        # Ensure unique values
        values = [v.model_dump() for v in data.values]
        value_keys = [v["value"] for v in values]
        if len(value_keys) != len(set(value_keys)):
            raise HTTPException(status_code=400, detail="Dropdown values must be unique")
        
        doc = {
            "_id": ObjectId(),
            "key": data.key,
            "name": data.name,
            "description": data.description,
            "values": values,
            "isSystem": False,
            "isActive": True,
            "createdAt": datetime.now(timezone.utc),
            "createdBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }
        
        await db.globalDropdowns.insert_one(doc)
        doc["_id"] = str(doc["_id"])
        
        logger.info(f"Admin {admin['email']} created dropdown: {data.key}")
        return {"message": "Dropdown created successfully", "dropdown": doc}
    
    @router.patch("/dropdowns/{key}")
    async def update_global_dropdown(
        key: str,
        data: GlobalDropdownUpdate,
        admin: dict = Depends(require_admin)
    ):
        """Update a global dropdown"""
        dropdown = await db.globalDropdowns.find_one({"key": key})
        if not dropdown:
            raise HTTPException(status_code=404, detail="Dropdown not found")
        
        if dropdown.get("isSystem") and data.isActive is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate system dropdowns")
        
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.values is not None:
            values = [v.model_dump() for v in data.values]
            value_keys = [v["value"] for v in values]
            if len(value_keys) != len(set(value_keys)):
                raise HTTPException(status_code=400, detail="Dropdown values must be unique")
            update_data["values"] = values
        if data.isActive is not None:
            update_data["isActive"] = data.isActive
        
        await db.globalDropdowns.update_one({"key": key}, {"$set": update_data})
        
        updated = await db.globalDropdowns.find_one({"key": key})
        updated["_id"] = str(updated["_id"])
        
        logger.info(f"Admin {admin['email']} updated dropdown: {key}")
        return {"message": "Dropdown updated successfully", "dropdown": updated}
    
    @router.delete("/dropdowns/{key}")
    async def delete_global_dropdown(
        key: str,
        admin: dict = Depends(require_admin),
        force: bool = Query(False)
    ):
        """Delete a global dropdown (soft delete by default)"""
        dropdown = await db.globalDropdowns.find_one({"key": key})
        if not dropdown:
            raise HTTPException(status_code=404, detail="Dropdown not found")
        
        if dropdown.get("isSystem"):
            raise HTTPException(status_code=400, detail="Cannot delete system dropdowns")
        
        # Check if dropdown is in use by any spec template
        in_use = await db.specTemplates.count_documents({
            "fields.dropdownKey": key,
            "isActive": {"$ne": False}
        })
        
        if in_use > 0 and not force:
            raise HTTPException(
                status_code=400,
                detail=f"Dropdown is used by {in_use} spec templates. Use force=true to delete anyway."
            )
        
        if force:
            await db.globalDropdowns.delete_one({"key": key})
            logger.info(f"Admin {admin['email']} hard-deleted dropdown: {key}")
            return {"message": "Dropdown deleted permanently"}
        else:
            await db.globalDropdowns.update_one(
                {"key": key},
                {"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc)}}
            )
            logger.info(f"Admin {admin['email']} soft-deleted dropdown: {key}")
            return {"message": "Dropdown deactivated"}
    
    # ==================== CATEGORIES WITH SETTINGS ====================
    
    @router.get("/categories")
    async def list_categories_with_settings(
        admin: dict = Depends(require_admin),
        include_inactive: bool = Query(False)
    ):
        """List all categories with their settings"""
        query = {} if include_inactive else {"isActive": {"$ne": False}}
        categories = await db.categories.find(query).sort("displayOrder", 1).to_list(100)
        
        for cat in categories:
            cat_oid = cat["_id"]
            cat["_id"] = str(cat["_id"])
            # Add counts - STRICT camelCase
            cat["productCount"] = await db.products.count_documents({
                "categoryId": cat_oid
            })
            cat["specTemplateCount"] = await db.specTemplates.count_documents({
                "categoryId": cat_oid,
                "isActive": {"$ne": False}
            })
        
        return {"categories": categories, "total": len(categories)}
    
    @router.get("/categories/{categoryId}")
    async def get_category_with_settings(
        categoryId: str,
        admin: dict = Depends(require_admin)
    ):
        """Get a category with its full settings"""
        try:
            cat = await db.categories.find_one({"_id": ObjectId(categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        
        cat["_id"] = str(cat["_id"])
        
        # Get associated spec templates
        templates = await db.specTemplates.find({
            "categoryId": categoryId,
            "isActive": {"$ne": False}
        }).to_list(50)
        
        for t in templates:
            t["_id"] = str(t["_id"])
        
        return {"category": cat, "spec_templates": templates}
    
    @router.post("/categories")
    async def create_category_with_settings(
        data: CategoryCreate,
        admin: dict = Depends(require_admin)
    ):
        """Create a new category with settings"""
        # Check for duplicate name
        existing = await db.categories.find_one({
            "name": {"$regex": f"^{data.name}$", "$options": "i"}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        
        # Validate settings against global dropdowns
        settings = data.settings.model_dump() if data.settings else CategorySettings().model_dump()
        
        # Validate allowed_units exist in global dropdown
        unit_dropdown = await db.globalDropdowns.find_one({"key": "unit_system"})
        if unit_dropdown:
            valid_units = [v["value"] for v in unit_dropdown.get("values", [])]
            invalid_units = [u for u in settings["allowed_units"] if u not in valid_units]
            if invalid_units:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid units: {invalid_units}. Valid: {valid_units}"
                )
        
        # Validate seller types
        seller_dropdown = await db.globalDropdowns.find_one({"key": "seller_type"})
        if seller_dropdown:
            valid_types = [v["value"] for v in seller_dropdown.get("values", [])]
            invalid_types = [t for t in settings["allowed_seller_types"] if t not in valid_types]
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid seller types: {invalid_types}. Valid: {valid_types}"
                )
        
        doc = {
            "_id": ObjectId(),
            "name": data.name,
            "description": data.description,
            "image": data.image,
            "icon": data.icon,
            "displayOrder": data.displayOrder,
            "settings": settings,
            "isActive": True,
            "createdAt": datetime.now(timezone.utc),
            "createdBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }
        
        await db.categories.insert_one(doc)
        doc["_id"] = str(doc["_id"])
        
        logger.info(f"Admin {admin['email']} created category: {data.name}")
        return {"message": "Category created successfully", "category": doc}
    
    @router.patch("/categories/{categoryId}")
    async def update_category_with_settings(
        categoryId: str,
        data: CategoryUpdate,
        admin: dict = Depends(require_admin)
    ):
        """Update a category and its settings"""
        try:
            cat = await db.categories.find_one({"_id": ObjectId(categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.name is not None:
            # Check for duplicate name
            dup = await db.categories.find_one({
                "_id": {"$ne": ObjectId(categoryId)},
                "name": {"$regex": f"^{data.name}$", "$options": "i"}
            })
            if dup:
                raise HTTPException(status_code=400, detail="Category with this name already exists")
            update_data["name"] = data.name
        
        if data.description is not None:
            update_data["description"] = data.description
        if data.image is not None:
            update_data["image"] = data.image
        if data.icon is not None:
            update_data["icon"] = data.icon
        if data.displayOrder is not None:
            update_data["displayOrder"] = data.displayOrder
        if data.isActive is not None:
            update_data["isActive"] = data.isActive
        
        if data.settings is not None:
            settings = data.settings.model_dump()
            
            # Validate settings (same as create)
            unit_dropdown = await db.globalDropdowns.find_one({"key": "unit_system"})
            if unit_dropdown:
                valid_units = [v["value"] for v in unit_dropdown.get("values", [])]
                invalid_units = [u for u in settings["allowed_units"] if u not in valid_units]
                if invalid_units:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid units: {invalid_units}. Valid: {valid_units}"
                    )
            
            seller_dropdown = await db.globalDropdowns.find_one({"key": "seller_type"})
            if seller_dropdown:
                valid_types = [v["value"] for v in seller_dropdown.get("values", [])]
                invalid_types = [t for t in settings["allowed_seller_types"] if t not in valid_types]
                if invalid_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid seller types: {invalid_types}. Valid: {valid_types}"
                    )
            
            update_data["settings"] = settings
        
        await db.categories.update_one({"_id": ObjectId(categoryId)}, {"$set": update_data})
        
        updated = await db.categories.find_one({"_id": ObjectId(categoryId)})
        updated["_id"] = str(updated["_id"])
        
        logger.info(f"Admin {admin['email']} updated category: {categoryId}")
        return {"message": "Category updated successfully", "category": updated}
    
    @router.patch("/categories/{categoryId}/settings")
    async def update_category_settings_only(
        categoryId: str,
        settings: CategorySettings,
        admin: dict = Depends(require_admin)
    ):
        """Update only the settings of a category (convenience endpoint)"""
        try:
            cat = await db.categories.find_one({"_id": ObjectId(categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        
        settings_dict = settings.model_dump()
        
        await db.categories.update_one(
            {"_id": ObjectId(categoryId)},
            {"$set": {"settings": settings_dict, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        updated = await db.categories.find_one({"_id": ObjectId(categoryId)})
        updated["_id"] = str(updated["_id"])
        
        logger.info(f"Admin {admin['email']} updated settings for category: {categoryId}")
        return {"message": "Category settings updated", "category": updated}
    
    # ==================== SPEC TEMPLATES ====================
    
    @router.get("/spec-templates")
    async def list_spec_templates(
        admin: dict = Depends(require_admin),
        categoryId: Optional[str] = Query(None),
        include_inactive: bool = Query(False)
    ):
        """List all spec templates, optionally filtered by category"""
        query = {}
        if categoryId:
            query["categoryId"] = categoryId
        if not include_inactive:
            query["isActive"] = {"$ne": False}
        
        templates = await db.specTemplates.find(query).sort("name", 1).to_list(200)
        
        # Enrich with category name
        category_cache = {}
        for t in templates:
            t["_id"] = str(t["_id"])
            cat_id = t.get("categoryId")
            if cat_id and cat_id not in category_cache:
                cat = await db.categories.find_one({"_id": ObjectId(cat_id)})
                category_cache[cat_id] = cat["name"] if cat else "Unknown"
            t["categoryName"] = category_cache.get(cat_id, "Unknown")
            
            # Count products using this template (check both array and legacy singular)
            products_array = await db.products.count_documents({
                "specTemplateIds": t["_id"]
            })
            products_singular = await db.products.count_documents({
                "specTemplateId": t["_id"]
            })
            t["productCount"] = products_array + products_singular
        
        return {"templates": templates, "total": len(templates)}
    
    @router.get("/spec-templates/{template_id}")
    async def get_spec_template(
        template_id: str,
        admin: dict = Depends(require_admin)
    ):
        """Get a specific spec template with resolved dropdowns"""
        try:
            template = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid template ID")
        
        if not template:
            raise HTTPException(status_code=404, detail="Spec template not found")
        
        template["_id"] = str(template["_id"])
        
        # Resolve dropdown references
        for field in template.get("fields", []):
            if field.get("dropdownKey"):
                dropdown = await db.globalDropdowns.find_one({"key": field["dropdownKey"]})
                if dropdown:
                    field["resolved_options"] = [v["label"] for v in dropdown.get("values", [])]
                    field["resolved_values"] = [v["value"] for v in dropdown.get("values", [])]
        
        # Get category info
        cat = await db.categories.find_one({"_id": ObjectId(template.get("categoryId"))})
        template["category_name"] = cat["name"] if cat else "Unknown"
        
        return {"template": template}
    
    @router.post("/spec-templates")
    async def create_spec_template(
        data: SpecTemplateCreate,
        admin: dict = Depends(require_admin)
    ):
        """Create a new spec template"""
        # Validate category exists
        try:
            cat = await db.categories.find_one({"_id": ObjectId(data.categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Validate field keys are unique
        field_keys = [f.key for f in data.fields]
        if len(field_keys) != len(set(field_keys)):
            raise HTTPException(status_code=400, detail="Field keys must be unique")
        
        # Validate dropdown references
        for field in data.fields:
            if field.dropdownKey:
                dropdown = await db.globalDropdowns.find_one({"key": field.dropdownKey})
                if not dropdown:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Global dropdown '{field.dropdownKey}' not found"
                    )
                if not dropdown.get("isActive", True):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Global dropdown '{field.dropdownKey}' is inactive"
                    )
        
        fields = [f.model_dump() for f in data.fields]
        
        doc = {
            "_id": ObjectId(),
            "name": data.name,
            "categoryId": ObjectId(data.categoryId),  # FIXED: Store as ObjectId
            "description": data.description,
            "fields": fields,
            "version": 1,
            "isActive": True,
            "createdAt": datetime.now(timezone.utc),
            "createdBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }
        
        await db.specTemplates.insert_one(doc)
        doc["_id"] = str(doc["_id"])
        
        logger.info(f"Admin {admin['email']} created spec template: {data.name}")
        return {"message": "Spec template created successfully", "template": doc}
    
    @router.patch("/spec-templates/{template_id}")
    async def update_spec_template(
        template_id: str,
        data: SpecTemplateUpdate,
        admin: dict = Depends(require_admin)
    ):
        """Update a spec template"""
        try:
            template = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid template ID")
        
        if not template:
            raise HTTPException(status_code=404, detail="Spec template not found")
        
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.isActive is not None:
            update_data["isActive"] = data.isActive
        
        if data.fields is not None:
            # Validate field keys are unique
            field_keys = [f.key for f in data.fields]
            if len(field_keys) != len(set(field_keys)):
                raise HTTPException(status_code=400, detail="Field keys must be unique")
            
            # Validate dropdown references
            for field in data.fields:
                if field.dropdownKey:
                    dropdown = await db.globalDropdowns.find_one({"key": field.dropdownKey})
                    if not dropdown:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Global dropdown '{field.dropdownKey}' not found"
                        )
            
            update_data["fields"] = [f.model_dump() for f in data.fields]
            update_data["version"] = template.get("version", 1) + 1
        
        await db.specTemplates.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": update_data}
        )
        
        updated = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
        updated["_id"] = str(updated["_id"])
        
        logger.info(f"Admin {admin['email']} updated spec template: {template_id}")
        return {"message": "Spec template updated successfully", "template": updated}
    
    @router.delete("/spec-templates/{template_id}")
    async def delete_spec_template(
        template_id: str,
        admin: dict = Depends(require_admin),
        force: bool = Query(False)
    ):
        """Delete a spec template (soft delete by default)"""
        try:
            template = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid template ID")
        
        if not template:
            raise HTTPException(status_code=404, detail="Spec template not found")
        
        # Check if template is in use (check both array and legacy singular)
        try:
            template_oid = ObjectId(template_id)
        except:
            template_oid = template_id
        
        in_use_array = await db.products.count_documents({"specTemplateIds": template_oid})
        in_use_singular = await db.products.count_documents({"specTemplateId": template_oid})
        in_use = in_use_array + in_use_singular
        
        if in_use > 0 and not force:
            raise HTTPException(
                status_code=400,
                detail=f"Template is used by {in_use} products. Use force=true to delete anyway."
            )
        
        if force:
            await db.specTemplates.delete_one({"_id": ObjectId(template_id)})
            logger.info(f"Admin {admin['email']} hard-deleted spec template: {template_id}")
            return {"message": "Spec template deleted permanently"}
        else:
            await db.specTemplates.update_one(
                {"_id": ObjectId(template_id)},
                {"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc)}}
            )
            logger.info(f"Admin {admin['email']} soft-deleted spec template: {template_id}")
            return {"message": "Spec template deactivated"}
    
    # ==================== SEED DATA ====================
    
    @router.post("/seed-system-dropdowns")
    async def seed_system_dropdowns(
        admin: dict = Depends(require_admin)
    ):
        """Seed the system with default global dropdowns"""
        
        system_dropdowns = [
            {
                "key": "unit_system",
                "name": "Unit System",
                "description": "Standard measurement units for products",
                "values": [
                    {"value": "pcs", "label": "Pieces", "displayOrder": 1, "isActive": True},
                    {"value": "kg", "label": "Kilograms", "displayOrder": 2, "isActive": True},
                    {"value": "ton", "label": "Metric Tons", "displayOrder": 3, "isActive": True},
                    {"value": "meter", "label": "Meters", "displayOrder": 4, "isActive": True},
                    {"value": "sq_meter", "label": "Square Meters", "displayOrder": 5, "isActive": True},
                    {"value": "cubic_meter", "label": "Cubic Meters", "displayOrder": 6, "isActive": True},
                    {"value": "liter", "label": "Liters", "displayOrder": 7, "isActive": True},
                    {"value": "feet", "label": "Feet", "displayOrder": 8, "isActive": True},
                    {"value": "sq_feet", "label": "Square Feet", "displayOrder": 9, "isActive": True},
                ],
                "isSystem": True
            },
            {
                "key": "dimension_unit",
                "name": "Dimension Unit",
                "description": "Units for product dimensions (L×W×H)",
                "values": [
                    {"value": "mm", "label": "Millimeters", "displayOrder": 1, "isActive": True},
                    {"value": "cm", "label": "Centimeters", "displayOrder": 2, "isActive": True},
                    {"value": "inch", "label": "Inches", "displayOrder": 3, "isActive": True},
                    {"value": "feet", "label": "Feet", "displayOrder": 4, "isActive": True},
                    {"value": "meter", "label": "Meters", "displayOrder": 5, "isActive": True},
                ],
                "isSystem": True
            },
            {
                "key": "seller_type",
                "name": "Seller Type",
                "description": "Types of sellers in the marketplace",
                "values": [
                    {"value": "manufacturer", "label": "Manufacturer", "displayOrder": 1, "isActive": True},
                    {"value": "distributor", "label": "Distributor", "displayOrder": 2, "isActive": True},
                    {"value": "wholesaler", "label": "Wholesaler", "displayOrder": 3, "isActive": True},
                    {"value": "dealer", "label": "Dealer", "displayOrder": 4, "isActive": True},
                    {"value": "retailer", "label": "Retailer", "displayOrder": 5, "isActive": True},
                ],
                "isSystem": True
            },
            {
                "key": "material_type",
                "name": "Material Type",
                "description": "Common material types",
                "values": [
                    {"value": "steel", "label": "Steel", "displayOrder": 1, "isActive": True},
                    {"value": "stainless_steel", "label": "Stainless Steel", "displayOrder": 2, "isActive": True},
                    {"value": "aluminum", "label": "Aluminum", "displayOrder": 3, "isActive": True},
                    {"value": "copper", "label": "Copper", "displayOrder": 4, "isActive": True},
                    {"value": "brass", "label": "Brass", "displayOrder": 5, "isActive": True},
                    {"value": "iron", "label": "Iron", "displayOrder": 6, "isActive": True},
                    {"value": "plastic", "label": "Plastic", "displayOrder": 7, "isActive": True},
                    {"value": "rubber", "label": "Rubber", "displayOrder": 8, "isActive": True},
                    {"value": "wood", "label": "Wood", "displayOrder": 9, "isActive": True},
                    {"value": "glass", "label": "Glass", "displayOrder": 10, "isActive": True},
                    {"value": "ceramic", "label": "Ceramic", "displayOrder": 11, "isActive": True},
                    {"value": "composite", "label": "Composite", "displayOrder": 12, "isActive": True},
                ],
                "isSystem": False  # Not system, can be modified
            },
            {
                "key": "packaging_type",
                "name": "Packaging Type",
                "description": "How products are packaged",
                "values": [
                    {"value": "box", "label": "Box", "displayOrder": 1, "isActive": True},
                    {"value": "carton", "label": "Carton", "displayOrder": 2, "isActive": True},
                    {"value": "pallet", "label": "Pallet", "displayOrder": 3, "isActive": True},
                    {"value": "bundle", "label": "Bundle", "displayOrder": 4, "isActive": True},
                    {"value": "drum", "label": "Drum", "displayOrder": 5, "isActive": True},
                    {"value": "bag", "label": "Bag", "displayOrder": 6, "isActive": True},
                    {"value": "bulk", "label": "Bulk", "displayOrder": 7, "isActive": True},
                    {"value": "roll", "label": "Roll", "displayOrder": 8, "isActive": True},
                ],
                "isSystem": False
            },
            {
                "key": "grade",
                "name": "Grade/Quality",
                "description": "Product grade or quality level",
                "values": [
                    {"value": "premium", "label": "Premium", "displayOrder": 1, "isActive": True},
                    {"value": "standard", "label": "Standard", "displayOrder": 2, "isActive": True},
                    {"value": "economy", "label": "Economy", "displayOrder": 3, "isActive": True},
                    {"value": "industrial", "label": "Industrial Grade", "displayOrder": 4, "isActive": True},
                    {"value": "commercial", "label": "Commercial Grade", "displayOrder": 5, "isActive": True},
                    {"value": "food_grade", "label": "Food Grade", "displayOrder": 6, "isActive": True},
                ],
                "isSystem": False
            }
        ]
        
        created = 0
        skipped = 0
        
        for dropdown_data in system_dropdowns:
            existing = await db.globalDropdowns.find_one({"key": dropdown_data["key"]})
            if existing:
                skipped += 1
                continue
            
            doc = {
                "_id": ObjectId(),
                **dropdown_data,
                "isActive": True,
                "createdAt": datetime.now(timezone.utc),
                "createdBy": str(admin["_id"]),
                "updatedAt": datetime.now(timezone.utc)
            }
            await db.globalDropdowns.insert_one(doc)
            created += 1
        
        logger.info(f"Admin {admin['email']} seeded system dropdowns: {created} created, {skipped} skipped")
        return {
            "message": f"System dropdowns seeded: {created} created, {skipped} already exist",
            "created": created,
            "skipped": skipped
        }
    
    return router
