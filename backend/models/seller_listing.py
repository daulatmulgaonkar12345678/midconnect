"""
Canonical Data Models for seller_listings

These Pydantic models are the SINGLE SOURCE OF TRUTH for the seller_listings schema.
All application code MUST use these models for:
1. Creating new listings
2. Validating input data
3. Serializing output data

STRICT RULES:
- All foreign keys are ObjectId (stored) but accept/output strings (serialized)
- NO legacy field names (seller_id, product_id, etc.)
- All timestamps use camelCase
- Models enforce business rules at the Python layer
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from bson import ObjectId
from bson.errors import InvalidId


# ==================== UTILITY TYPES ====================

class PyObjectId(str):
    """
    Custom type for MongoDB ObjectId that validates and serializes properly.
    
    - Accepts: ObjectId, string (24-char hex)
    - Rejects: Invalid strings, None, other types
    - Serializes to: string
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if v is None:
            raise ValueError("ObjectId cannot be None")
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            try:
                ObjectId(v)  # Validate it's a valid ObjectId string
                return v
            except InvalidId:
                raise ValueError(f"Invalid ObjectId format: {v}")
        raise ValueError(f"Cannot convert {type(v).__name__} to ObjectId")


def validate_objectid(v: Any, field_name: str) -> str:
    """Validate and convert to ObjectId string."""
    if v is None:
        raise ValueError(f"{field_name} cannot be None")
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        try:
            ObjectId(v)
            return v
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format for {field_name}: {v}")
    raise ValueError(f"Cannot convert {type(v).__name__} to ObjectId for {field_name}")


def to_objectid(v: Any) -> ObjectId:
    """Convert string or ObjectId to ObjectId for database storage."""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        try:
            return ObjectId(v)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {v}")
    raise ValueError(f"Cannot convert {type(v).__name__} to ObjectId")


# ==================== PRICING MODELS ====================

class PricingTier(BaseModel):
    """A single tier in quantity-based pricing."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    min_qty: int = Field(ge=1, alias="minQty", description="Minimum quantity for this tier")
    max_qty: Optional[int] = Field(None, ge=1, alias="maxQty", description="Maximum quantity (null = unlimited)")
    price_per_unit: float = Field(gt=0, alias="pricePerUnit", description="Price per unit in this tier")
    
    @model_validator(mode='after')
    def validate_qty_range(self):
        if self.max_qty is not None and self.max_qty < self.min_qty:
            raise ValueError(f"maxQty ({self.max_qty}) must be >= minQty ({self.min_qty})")
        return self
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format (camelCase)."""
        return {
            "minQty": self.min_qty,
            "maxQty": self.max_qty,
            "pricePerUnit": self.price_per_unit
        }


# ==================== LISTING MODELS ====================

class SellerListingBase(BaseModel):
    """Base fields for seller listings."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid"  # STRICT: Reject unknown fields
    )
    
    # Status
    status: Literal["active", "inactive", "draft", "paused", "archived"] = "draft"
    is_active: bool = Field(False, alias="is_active")
    
    # Commercial data
    stock: int = Field(0, ge=0, description="Available stock quantity")
    moq: int = Field(1, ge=1, description="Minimum Order Quantity")
    max_capacity: Optional[int] = Field(None, ge=1, alias="maxCapacity")
    lead_time: Optional[int] = Field(None, ge=0, alias="leadTime", description="Lead time in days")
    currency: str = Field("INR", max_length=3)
    
    # Pricing
    pricing_tiers: List[PricingTier] = Field(default_factory=list, alias="pricingTiers")
    
    # Seller metadata
    seller_role: Optional[str] = Field(None, alias="sellerRole")
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    specifications: Optional[Dict[str, Any]] = None
    
    @field_validator('pricing_tiers', mode='before')
    @classmethod
    def validate_pricing_tiers(cls, v):
        """Ensure pricing tiers don't overlap."""
        if not v:
            return v
        # Convert dicts to PricingTier if needed
        tiers = []
        for item in v:
            if isinstance(item, dict):
                tiers.append(PricingTier(**item))
            else:
                tiers.append(item)
        
        # Validate non-overlapping ranges
        sorted_tiers = sorted(tiers, key=lambda t: t.min_qty)
        for i in range(len(sorted_tiers) - 1):
            current = sorted_tiers[i]
            next_tier = sorted_tiers[i + 1]
            if current.max_qty is None:
                raise ValueError(f"Tier starting at {current.min_qty} has unlimited max but is not the last tier")
            if current.max_qty >= next_tier.min_qty:
                raise ValueError(f"Overlapping tiers: {current.min_qty}-{current.max_qty} and {next_tier.min_qty}")
        
        return tiers
    
    @model_validator(mode='after')
    def sync_is_active_with_status(self):
        """Ensure is_active flag matches status."""
        self.is_active = self.status == "active"
        return self


class SellerListingCreate(BaseModel):
    """
    Model for creating a new seller listing.
    
    All IDs are provided as strings and validated as ObjectId format.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"  # STRICT: Reject unknown fields
    )
    
    # Required ObjectId references (as strings)
    seller_id: str = Field(..., alias="sellerId", description="Reference to users collection")
    product_id: str = Field(..., alias="productId", description="Reference to products collection")
    category_id: str = Field(..., alias="categoryId", description="Reference to categories collection")
    
    # Status (defaults to draft)
    status: Literal["active", "inactive", "draft", "paused", "archived"] = "draft"
    
    # Commercial data
    stock: int = Field(0, ge=0)
    moq: int = Field(1, ge=1)
    max_capacity: Optional[int] = Field(None, ge=1, alias="maxCapacity")
    lead_time: Optional[int] = Field(None, ge=0, alias="leadTime")
    currency: str = Field("INR", max_length=3)
    
    # Pricing
    pricing_tiers: List[PricingTier] = Field(default_factory=list, alias="pricingTiers")
    
    # Seller metadata
    seller_role: Optional[str] = Field(None, alias="sellerRole")
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    specifications: Optional[Dict[str, Any]] = None
    
    @field_validator('seller_id', 'product_id', 'category_id', mode='before')
    @classmethod
    def validate_object_ids(cls, v, info):
        """Validate ObjectId format for all ID fields."""
        return validate_objectid(v, info.field_name)
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 images allowed")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert to database format with ObjectId types and camelCase keys.
        
        This is the CANONICAL format for insertion into MongoDB.
        """
        now = datetime.now(timezone.utc)
        
        return {
            "sellerId": to_objectid(self.seller_id),
            "productId": to_objectid(self.product_id),
            "categoryId": to_objectid(self.category_id),
            "status": self.status,
            "is_active": self.status == "active",
            "stock": self.stock,
            "moq": self.moq,
            "maxCapacity": self.max_capacity,
            "leadTime": self.lead_time,
            "currency": self.currency,
            "pricingTiers": [t.to_db_dict() for t in self.pricing_tiers],
            "sellerRole": self.seller_role,
            "description": self.description,
            "images": self.images[:10],  # Enforce max
            "specifications": self.specifications,
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": now if self.status == "active" else None
        }


class SellerListingUpdate(BaseModel):
    """
    Model for updating an existing seller listing.
    
    All fields are optional. Only provided fields will be updated.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"  # STRICT: Reject unknown fields
    )
    
    # Status
    status: Optional[Literal["active", "inactive", "draft", "paused", "archived"]] = None
    
    # Commercial data (all optional for updates)
    stock: Optional[int] = Field(None, ge=0)
    moq: Optional[int] = Field(None, ge=1)
    max_capacity: Optional[int] = Field(None, ge=1, alias="maxCapacity")
    lead_time: Optional[int] = Field(None, ge=0, alias="leadTime")
    currency: Optional[str] = Field(None, max_length=3)
    
    # Pricing
    pricing_tiers: Optional[List[PricingTier]] = Field(None, alias="pricingTiers")
    
    # Seller metadata
    seller_role: Optional[str] = Field(None, alias="sellerRole")
    description: Optional[str] = None
    images: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 images allowed")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert to database update format with camelCase keys.
        
        Only includes fields that were explicitly set.
        """
        updates = {}
        
        if self.status is not None:
            updates["status"] = self.status
            updates["is_active"] = self.status == "active"
            if self.status == "active":
                updates["publishedAt"] = datetime.now(timezone.utc)
        
        if self.stock is not None:
            updates["stock"] = self.stock
        
        if self.moq is not None:
            updates["moq"] = self.moq
        
        if self.max_capacity is not None:
            updates["maxCapacity"] = self.max_capacity
        
        if self.lead_time is not None:
            updates["leadTime"] = self.lead_time
        
        if self.currency is not None:
            updates["currency"] = self.currency
        
        if self.pricing_tiers is not None:
            updates["pricingTiers"] = [t.to_db_dict() for t in self.pricing_tiers]
        
        if self.seller_role is not None:
            updates["sellerRole"] = self.seller_role
        
        if self.description is not None:
            updates["description"] = self.description
        
        if self.images is not None:
            updates["images"] = self.images[:10]
        
        if self.specifications is not None:
            updates["specifications"] = self.specifications
        
        # Always update timestamp
        updates["updatedAt"] = datetime.now(timezone.utc)
        
        return updates


class SellerListingResponse(BaseModel):
    """
    Model for API responses containing a seller listing.
    
    All ObjectIds are serialized to strings.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: str = Field(..., alias="_id")
    seller_id: str = Field(..., alias="sellerId")
    product_id: str = Field(..., alias="productId")
    category_id: str = Field(..., alias="categoryId")
    status: str
    is_active: bool
    stock: int
    moq: int
    max_capacity: Optional[int] = Field(None, alias="maxCapacity")
    lead_time: Optional[int] = Field(None, alias="leadTime")
    currency: str
    pricing_tiers: List[Dict[str, Any]] = Field(default_factory=list, alias="pricingTiers")
    seller_role: Optional[str] = Field(None, alias="sellerRole")
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    specifications: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    published_at: Optional[datetime] = Field(None, alias="publishedAt")
    
    # Joined fields (from $lookup aggregations)
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    seller_name: Optional[str] = None
    seller_email: Optional[str] = None
    
    @classmethod
    def from_db(cls, doc: Dict[str, Any]) -> "SellerListingResponse":
        """Create response model from MongoDB document."""
        if not doc:
            return None
        
        # Serialize ObjectIds and datetimes
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value
            elif isinstance(value, dict):
                serialized[key] = {
                    k: str(v) if isinstance(v, ObjectId) else v
                    for k, v in value.items()
                }
            elif isinstance(value, list):
                serialized[key] = [
                    str(item) if isinstance(item, ObjectId) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return cls(**serialized)


# ==================== VALIDATION HELPERS ====================

class ListingValidationError(Exception):
    """Custom exception for listing validation failures."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation failed for {field}: {message}")


def validate_listing_for_publish(listing: Dict[str, Any]) -> List[str]:
    """
    Validate that a listing meets all requirements for publishing.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Required fields for publishing
    if not listing.get("pricingTiers"):
        errors.append("At least one pricing tier is required for publishing")
    
    if not listing.get("moq") or listing.get("moq", 0) < 1:
        errors.append("MOQ must be at least 1 for publishing")
    
    if not listing.get("sellerId"):
        errors.append("sellerId is required")
    
    if not listing.get("productId"):
        errors.append("productId is required")
    
    if not listing.get("categoryId"):
        errors.append("categoryId is required")
    
    return errors
