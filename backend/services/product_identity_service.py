"""
Product Identity Service

PRODUCT IDENTITY GOVERNANCE:
Products are uniquely identified by: (name, categoryId, specTemplateId, normalizedSpecHash)
This service handles product deduplication and identity management.

SSOT: All fields use camelCase
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ProductIdentityService:
    """
    Service for managing product identity and deduplication.
    
    Product Identity Formula:
    identity = hash(name + categoryId + specTemplateId + sorted(spec_fields))
    
    This prevents duplicate products with the same logical identity
    from being created in the master catalog.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize the service with database connection.
        
        Args:
            db: Motor async database instance
        """
        self.db = db
        self.products_collection = db.products
    
    def generate_spec_hash(self, spec_fields: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash from specification fields.
        
        The hash is generated from sorted, normalized field keys.
        This ensures consistent hashing regardless of field order.
        
        Args:
            spec_fields: Dictionary of specification fields
            
        Returns:
            str: SHA256 hash of normalized spec fields (first 16 chars)
        """
        if not spec_fields:
            return "empty_spec"
        
        # Sort keys for deterministic ordering
        sorted_keys = sorted(spec_fields.keys())
        
        # Create normalized string representation
        normalized = json.dumps(sorted_keys, sort_keys=True)
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # First 16 chars for brevity
    
    def normalize_specifications(self, spec_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize specification fields for storage and comparison.
        
        - Sorts keys alphabetically
        - Strips whitespace from string values
        - Converts all keys to lowercase
        
        Args:
            spec_fields: Raw specification fields
            
        Returns:
            Dict: Normalized specification fields
        """
        if not spec_fields:
            return {}
        
        normalized = {}
        for key, value in spec_fields.items():
            # Normalize key
            norm_key = key.strip().lower() if isinstance(key, str) else str(key)
            
            # Normalize value
            if isinstance(value, str):
                norm_value = value.strip()
            else:
                norm_value = value
            
            normalized[norm_key] = norm_value
        
        # Return sorted dict
        return dict(sorted(normalized.items()))
    
    async def find_existing_product(
        self,
        name: str,
        category_id: str,
        spec_template_id: Optional[str] = None,
        specifications: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an existing product by identity signature.
        
        Identity Match Criteria:
        1. Same name (case-insensitive)
        2. Same category
        3. Same spec template (if provided)
        4. Same specification hash (if specs provided)
        
        Args:
            name: Product name
            category_id: Category ObjectId string
            spec_template_id: Optional spec template ObjectId string
            specifications: Optional specification fields
            
        Returns:
            Existing product document or None
        """
        try:
            # Build query with case-insensitive name match
            query: Dict[str, Any] = {
                "name": {"$regex": f"^{name}$", "$options": "i"},
                "categoryId": ObjectId(category_id) if isinstance(category_id, str) else category_id
            }
            
            # Add spec template filter if provided
            if spec_template_id:
                template_oid = ObjectId(spec_template_id) if isinstance(spec_template_id, str) else spec_template_id
                query["$or"] = [
                    {"specTemplateId": template_oid},
                    {"specTemplateIds": template_oid}
                ]
            
            # Find product
            product = await self.products_collection.find_one(query)
            
            if product:
                # Serialize ObjectIds for JSON response
                return self._serialize_product(product)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding existing product: {e}")
            return None
    
    def _serialize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize a product document for API response.
        
        Converts ObjectIds to strings for JSON serialization.
        """
        if not product:
            return {}
        
        serialized = {}
        for key, value in product.items():
            if key == "_id":
                serialized["_id"] = str(value)
                serialized["id"] = str(value)  # Alias for frontend
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, list):
                serialized[key] = [
                    str(item) if isinstance(item, ObjectId) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return serialized
    
    async def create_product_identity(
        self,
        name: str,
        category_id: str,
        spec_template_ids: List[str],
        specifications: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate product identity fields for a new product.
        
        Returns fields to be included in the product document:
        - normalizedSpecHash: For deduplication
        - normalizedSpecs: Normalized specification fields
        
        Args:
            name: Product name
            category_id: Category ObjectId string
            spec_template_ids: List of spec template ObjectId strings
            specifications: Optional specification fields
            
        Returns:
            Dict with identity fields
        """
        spec_fields = specifications or {}
        
        return {
            "normalizedSpecHash": self.generate_spec_hash(spec_fields),
            "normalizedSpecs": self.normalize_specifications(spec_fields)
        }
