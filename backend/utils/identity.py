"""
Identity Guard Utilities

This module provides STRICT validation and conversion functions for ObjectIds.
It is the gatekeeper that ensures all foreign keys are valid ObjectId types.

STRICT RULES:
- NO fallback values
- NO silent failures
- FAIL LOUDLY on invalid input
- All validation happens at system boundaries (API layer)

Usage:
    from utils.identity import require_objectid, to_objectid_safe
    
    # In API endpoint:
    seller_oid = require_objectid(seller_id, "sellerId")
    product_oid = require_objectid(product_id, "productId")
"""

from typing import Any, Optional, Union
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class IdentityError(Exception):
    """Raised when an identity validation fails."""
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Identity validation failed for {field}: {message}")


def require_objectid(value: Any, field_name: str) -> ObjectId:
    """
    STRICT: Convert value to ObjectId or raise HTTPException.
    
    Use this at API boundaries to validate incoming IDs.
    This function NEVER returns None or fallback values.
    
    Args:
        value: The value to convert (string, ObjectId)
        field_name: Name of the field (for error messages)
        
    Returns:
        ObjectId: The validated ObjectId
        
    Raises:
        HTTPException 400: If value cannot be converted to ObjectId
    """
    if value is None:
        logger.warning(f"Identity validation failed: {field_name} is None")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_OBJECT_ID",
                "field": field_name,
                "message": f"{field_name} is required and cannot be null"
            }
        )
    
    if isinstance(value, ObjectId):
        return value
    
    if isinstance(value, str):
        # Validate string format (24-character hex)
        if len(value) != 24:
            logger.warning(f"Identity validation failed: {field_name}='{value}' has invalid length")
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_OBJECT_ID",
                    "field": field_name,
                    "message": f"Invalid {field_name} format. Expected 24-character hex string, got {len(value)} characters"
                }
            )
        
        try:
            return ObjectId(value)
        except InvalidId:
            logger.warning(f"Identity validation failed: {field_name}='{value}' is not valid hex")
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_OBJECT_ID",
                    "field": field_name,
                    "message": f"Invalid {field_name} format. Must be 24-character hexadecimal string"
                }
            )
    
    logger.warning(f"Identity validation failed: {field_name} has wrong type {type(value).__name__}")
    raise HTTPException(
        status_code=400,
        detail={
            "error_code": "INVALID_OBJECT_ID",
            "field": field_name,
            "message": f"Invalid {field_name} type. Expected string or ObjectId, got {type(value).__name__}"
        }
    )


def to_objectid_safe(value: Any, field_name: str) -> Optional[ObjectId]:
    """
    Convert value to ObjectId, returning None for None inputs.
    Still STRICT - raises exception for invalid non-None values.
    
    Use this for optional ObjectId fields.
    
    Args:
        value: The value to convert (string, ObjectId, or None)
        field_name: Name of the field (for error messages)
        
    Returns:
        ObjectId or None
        
    Raises:
        HTTPException 400: If value is non-None and cannot be converted
    """
    if value is None:
        return None
    return require_objectid(value, field_name)


def validate_objectid_str(value: Any, field_name: str) -> str:
    """
    Validate that a value is a valid ObjectId and return as string.
    
    Use this when you need the string representation but want to validate format.
    
    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        
    Returns:
        str: The validated ObjectId as string
        
    Raises:
        HTTPException 400: If value is not a valid ObjectId
    """
    oid = require_objectid(value, field_name)
    return str(oid)


def is_valid_objectid(value: Any) -> bool:
    """
    Check if a value is a valid ObjectId (without raising exception).
    
    Use this for conditional logic, NOT for validation.
    For validation, always use require_objectid.
    
    Args:
        value: The value to check
        
    Returns:
        bool: True if valid ObjectId, False otherwise
    """
    if value is None:
        return False
    if isinstance(value, ObjectId):
        return True
    if isinstance(value, str) and len(value) == 24:
        try:
            ObjectId(value)
            return True
        except InvalidId:
            return False
    return False


def serialize_objectid(value: Any) -> Optional[str]:
    """
    Serialize an ObjectId to string for JSON response.
    
    Args:
        value: ObjectId or string
        
    Returns:
        str or None: String representation
    """
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


# ==================== BATCH VALIDATION ====================

def validate_objectid_batch(values: dict) -> dict:
    """
    Validate multiple ObjectId fields at once.
    
    Args:
        values: Dict of {field_name: value}
        
    Returns:
        Dict of {field_name: ObjectId}
        
    Raises:
        HTTPException 400: If any value is invalid (includes all failures)
    """
    results = {}
    errors = []
    
    for field_name, value in values.items():
        try:
            results[field_name] = require_objectid(value, field_name)
        except HTTPException as e:
            errors.append(e.detail)
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_OBJECT_IDS",
                "message": "Multiple ObjectId validation failures",
                "errors": errors
            }
        )
    
    return results


# ==================== LEGACY FIELD DETECTION ====================

def detect_legacy_fields(doc: dict) -> list:
    """
    Detect any legacy field names in a document.
    
    This is used for debugging and migration verification.
    
    Legacy fields that should NOT exist:
    - seller_id (should be sellerId with ObjectId)
    - product_id (should be productId with ObjectId)
    - category_id (should be categoryId with ObjectId)
    - product_name (should not exist, resolve via $lookup)
    - category_name (should not exist, resolve via $lookup)
    
    Args:
        doc: MongoDB document
        
    Returns:
        List of legacy field names found
    """
    LEGACY_FIELDS = [
        "seller_id",
        "product_id", 
        "category_id",
        "product_name",
        "category_name",
        "created_at",
        "updated_at",
        "published_at"
    ]
    
    found = []
    for field in LEGACY_FIELDS:
        if field in doc:
            found.append(field)
    
    return found


def assert_no_legacy_fields(doc: dict, context: str = "document"):
    """
    Assert that a document has no legacy fields.
    
    Use this as a guard before database operations.
    
    Args:
        doc: MongoDB document
        context: Description for error message
        
    Raises:
        ValueError: If legacy fields are found
    """
    legacy = detect_legacy_fields(doc)
    if legacy:
        raise ValueError(
            f"SCHEMA VIOLATION in {context}: Found legacy fields: {legacy}. "
            f"Use canonical fields (sellerId, productId, categoryId) with ObjectId types."
        )


# ==================== TYPE ASSERTIONS ====================

def assert_objectid_type(value: Any, field_name: str):
    """
    Assert that a value is an ObjectId type (not string).
    
    Use this before database operations to ensure correct types.
    
    Args:
        value: The value to check
        field_name: Name of the field
        
    Raises:
        TypeError: If value is not ObjectId
    """
    if not isinstance(value, ObjectId):
        raise TypeError(
            f"SCHEMA VIOLATION: {field_name} must be ObjectId type for database storage, "
            f"got {type(value).__name__}. Use require_objectid() to convert."
        )
