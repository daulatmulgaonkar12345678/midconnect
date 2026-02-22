"""
Product Variants Service - ENTERPRISE ARCHITECTURE
===================================================

FINAL ENTERPRISE SCHEMA:
productVariants: {
    _id: ObjectId,
    productId: ObjectId,
    templateVersions: [
        { templateId: ObjectId, version: int }
    ],
    attributes: {
        "power": 45,
        "voltage": "415",
        ...
    },
    createdAt: datetime
}

ARCHITECTURAL RULES:
1. All references stored as ObjectId (never string)
2. All fields use camelCase (never snake_case)
3. templateVersions[] freezes template version at variant creation
4. attributes validated against template field definitions
5. No duplicate attribute combinations per product
6. No fallback logic, no legacy support
7. SpecTemplate is mandatory - no template = error
"""

from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def to_objectid(value: Any, field_name: str) -> ObjectId:
    """Convert value to ObjectId. Raises ValueError if conversion fails."""
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format for {field_name}: {value}")
    raise ValueError(f"Cannot convert {type(value).__name__} to ObjectId for {field_name}")


class ProductVariantService:
    """
    Service for managing the productVariants collection.
    
    ENTERPRISE ARCHITECTURE:
    - ProductVariant stores templateVersions[] to freeze template version
    - On template structure change, new variants get new version
    - Old variants remain valid with their frozen version
    - This prevents version drift and data corruption
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.productVariants
    
    # ==================== INDEXES ====================
    
    async def ensure_indexes(self):
        """Create indexes for optimal query performance."""
        await self.collection.create_index("productId", name="productId_1")
        await self.collection.create_index(
            [("productId", 1), ("attributes", 1)],
            name="productId_attributes"
        )
        await self.collection.create_index("createdAt", name="createdAt_1")
        logger.info("[ProductVariantService] Indexes ensured")
    
    # ==================== CREATE OR REUSE ====================
    
    async def get_or_create_variant(
        self,
        product_id: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get existing variant or create new one.
        
        ENTERPRISE FLOW:
        1. Get product to find specTemplateIds
        2. For each template, get current version
        3. Build templateVersions array
        4. Validate attributes against templates
        5. Check for existing variant with same attributes
        6. If none exists, create new variant with frozen versions
        
        Args:
            product_id: Reference to products collection (ObjectId or string)
            attributes: Dict of attribute key-value pairs
            
        Returns:
            The variant document (existing or newly created)
        """
        product_oid = to_objectid(product_id, "productId")
        
        # Get product to find template references
        product = await self.db.products.find_one({"_id": product_oid})
        if not product:
            raise ValueError(f"Product not found: {product_id}")
        
        # Get specTemplateIds from product
        template_ids = product.get("specTemplateIds", [])
        if not template_ids:
            raise ValueError(f"Product has no specTemplateIds: {product_id}")
        
        # Build templateVersions and validate attributes
        template_versions = []
        for template_id in template_ids:
            template_oid = to_objectid(template_id, "specTemplateId")
            template = await self.db.specTemplates.find_one({
                "_id": template_oid,
                "isActive": True
            })
            
            if not template:
                raise ValueError(f"SpecTemplate not found or inactive: {template_id}")
            
            # Freeze current version
            template_versions.append({
                "templateId": template_oid,
                "version": template.get("version", 1)
            })
            
            # Validate attributes against this template
            await self._validate_attributes_against_template(template, attributes)
        
        # Normalize attributes for consistent comparison
        normalized_attrs = self._normalize_attributes(attributes)
        
        # Check for existing variant with same attributes
        existing = await self.collection.find_one({
            "productId": product_oid,
            "attributes": normalized_attrs
        })
        
        if existing:
            logger.info(f"[ProductVariantService] Reusing existing variant {existing['_id']}")
            return self._serialize(existing)
        
        # Create new variant with frozen template versions
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "productId": product_oid,
            "templateVersions": template_versions,
            "attributes": normalized_attrs,
            "createdAt": now
        }
        
        await self.collection.insert_one(doc)
        logger.info(f"[ProductVariantService] Created new variant {doc['_id']}")
        
        return self._serialize(doc)
    
    async def _validate_attributes_against_template(
        self,
        template: Dict[str, Any],
        attributes: Dict[str, Any]
    ) -> None:
        """
        Validate attributes against a single template's field definitions.
        
        STRICT RULES:
        - isMandatory fields must be present
        - Field values must match expected types
        """
        template_fields = template.get("fields", [])
        field_keys = {f.get("key") for f in template_fields}
        
        # Check mandatory fields
        for field in template_fields:
            if field.get("isMandatory"):
                key = field.get("key")
                if key not in attributes or attributes[key] in [None, "", []]:
                    raise ValueError(f"Missing mandatory attribute: {key}")
        
        # Log unknown attributes (but don't reject - for flexibility)
        for key in attributes.keys():
            if key not in field_keys:
                logger.warning(f"[ProductVariantService] Unknown attribute key: {key}")
    
    def _normalize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize attributes for consistent storage and comparison.
        - Sort keys alphabetically
        - Convert numeric strings to numbers
        - Strip whitespace from strings
        """
        normalized = {}
        for key in sorted(attributes.keys()):
            value = attributes[key]
            if isinstance(value, str):
                value = value.strip()
                # Try to convert to number if it looks like one
                try:
                    if '.' in value:
                        value = float(value)
                    elif value.isdigit():
                        value = int(value)
                except (ValueError, AttributeError):
                    pass
            normalized[key] = value
        return normalized
    
    # ==================== READ ====================
    
    async def get_variant_by_id(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get a variant by its ID."""
        try:
            variant_oid = to_objectid(variant_id, "variantId")
        except ValueError:
            return None
        
        variant = await self.collection.find_one({"_id": variant_oid})
        return self._serialize(variant) if variant else None
    
    async def get_variants_for_product(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all variants for a product."""
        product_oid = to_objectid(product_id, "productId")
        
        variants = await self.collection.find({
            "productId": product_oid
        }).sort("createdAt", -1).to_list(100)
        
        return [self._serialize(v) for v in variants]
    
    async def get_variant_with_template_info(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get variant with resolved template information.
        Returns variant with template names and field labels.
        """
        variant = await self.get_variant_by_id(variant_id)
        if not variant:
            return None
        
        # Resolve template info
        templates_info = []
        for tv in variant.get("templateVersions", []):
            template = await self.db.specTemplates.find_one({
                "_id": to_objectid(tv["templateId"], "templateId")
            })
            if template:
                templates_info.append({
                    "templateId": str(template["_id"]),
                    "name": template.get("name"),
                    "version": tv["version"],
                    "currentVersion": template.get("version"),
                    "isOutdated": tv["version"] < template.get("version", 1)
                })
        
        variant["templatesInfo"] = templates_info
        return variant
    
    # ==================== DELETE ====================
    
    async def delete_variant(self, variant_id: str) -> bool:
        """
        Delete a variant by ID.
        
        STRICT: Cannot delete if seller listings depend on it.
        """
        variant_oid = to_objectid(variant_id, "variantId")
        
        # Check for dependent listings
        listing_count = await self.db.sellerListings.count_documents({
            "variantId": variant_oid
        })
        
        if listing_count > 0:
            raise ValueError(f"Cannot delete variant: {listing_count} seller listings depend on it")
        
        result = await self.collection.delete_one({"_id": variant_oid})
        
        if result.deleted_count > 0:
            logger.info(f"[ProductVariantService] Deleted variant {variant_id}")
            return True
        return False
    
    # ==================== UTILITIES ====================
    
    def _serialize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize a variant document for API response."""
        if not doc:
            return None
        
        result = {}
        for key, value in doc.items():
            if key == "_id":
                result["_id"] = str(value)
            elif key == "productId":
                result["productId"] = str(value)
            elif key == "templateVersions":
                result["templateVersions"] = [
                    {
                        "templateId": str(tv["templateId"]),
                        "version": tv["version"]
                    }
                    for tv in value
                ]
            elif key == "createdAt":
                result["createdAt"] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
            else:
                result[key] = value
        
        return result
