"""
ENTERPRISE LISTING GUARD
=========================
Strict write-time validation for seller listings.

Ensures:
- No empty searchableAttributes
- No empty images
- No incomplete listings
- Only valid searchable listings stored

This is production-level data governance.
"""

from fastapi import HTTPException
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("enterprise_guard")


class EnterpriseListingGuard:
    """
    Enterprise-grade validation guard for seller listings.
    
    Ensures data integrity at write time:
    - searchableAttributes must have at least 1 attribute
    - images must have at least 1 image
    - All required fields must be present
    """
    
    @staticmethod
    def validate_searchable_attributes(
        attributes: Optional[Dict[str, Any]],
        allow_empty: bool = False
    ) -> Dict[str, Any]:
        """
        Validate searchableAttributes for listing.
        
        Args:
            attributes: Dict of technical specifications
            allow_empty: If False, raises error for empty attributes
            
        Returns:
            Validated attributes dict
            
        Raises:
            HTTPException: If validation fails
        """
        if attributes is None:
            attributes = {}
        
        if not isinstance(attributes, dict):
            raise HTTPException(
                status_code=400,
                detail="searchableAttributes must be a dictionary"
            )
        
        if not allow_empty and len(attributes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Technical specifications required. Cannot create listing without at least one specification attribute."
            )
        
        # Validate each attribute value is not None/empty
        valid_attrs = {}
        for key, value in attributes.items():
            if value is not None and value != "":
                valid_attrs[key] = value
        
        if not allow_empty and len(valid_attrs) == 0:
            raise HTTPException(
                status_code=400,
                detail="Technical specifications required. All provided attributes are empty."
            )
        
        return valid_attrs
    
    @staticmethod
    def validate_images(
        images: Optional[List[str]],
        min_required: int = 1,
        max_allowed: int = 10
    ) -> List[str]:
        """
        Validate images array for listing.
        
        Args:
            images: List of image URLs
            min_required: Minimum number of images required
            max_allowed: Maximum number of images allowed
            
        Returns:
            Validated images list
            
        Raises:
            HTTPException: If validation fails
        """
        if images is None:
            images = []
        
        if not isinstance(images, list):
            raise HTTPException(
                status_code=400,
                detail="images must be a list of URLs"
            )
        
        # Filter out empty/invalid URLs
        valid_images = [img for img in images if img and isinstance(img, str) and img.strip()]
        
        if len(valid_images) < min_required:
            raise HTTPException(
                status_code=400,
                detail=f"At least {min_required} product image is required. Listings without images cannot be created."
            )
        
        if len(valid_images) > max_allowed:
            valid_images = valid_images[:max_allowed]
            logger.warning(f"Images truncated to {max_allowed}")
        
        return valid_images
    
    @staticmethod
    def validate_pricing_tiers(
        pricing_tiers: Optional[List[Dict[str, Any]]],
        min_required: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Validate pricing tiers for listing.
        
        Args:
            pricing_tiers: List of pricing tier dicts
            min_required: Minimum number of tiers required
            
        Returns:
            Validated pricing tiers
            
        Raises:
            HTTPException: If validation fails
        """
        if pricing_tiers is None:
            pricing_tiers = []
        
        if not isinstance(pricing_tiers, list):
            raise HTTPException(
                status_code=400,
                detail="pricingTiers must be a list"
            )
        
        if len(pricing_tiers) < min_required:
            raise HTTPException(
                status_code=400,
                detail=f"At least {min_required} pricing tier is required"
            )
        
        # Validate each tier has required fields
        valid_tiers = []
        for i, tier in enumerate(pricing_tiers):
            if not isinstance(tier, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"Pricing tier {i+1} must be a dictionary"
                )
            
            min_qty = tier.get("minQty")
            price = tier.get("pricePerUnit")
            
            if min_qty is None or price is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pricing tier {i+1} must have minQty and pricePerUnit"
                )
            
            if not isinstance(min_qty, (int, float)) or min_qty < 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pricing tier {i+1}: minQty must be >= 1"
                )
            
            if not isinstance(price, (int, float)) or price <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pricing tier {i+1}: pricePerUnit must be > 0"
                )
            
            valid_tiers.append({
                "minQty": int(min_qty),
                "maxQty": tier.get("maxQty"),
                "pricePerUnit": float(price)
            })
        
        return valid_tiers
    
    @staticmethod
    def validate_listing_for_create(
        images: List[str],
        searchable_attributes: Dict[str, Any],
        pricing_tiers: List[Dict[str, Any]],
        moq: Optional[int] = None,
        stock: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Full validation for listing creation.
        
        Returns validated data dict with all fields.
        
        Raises:
            HTTPException: If any validation fails
        """
        guard = EnterpriseListingGuard
        
        validated = {
            "images": guard.validate_images(images, min_required=1),
            "searchableAttributes": guard.validate_searchable_attributes(searchable_attributes),
            "pricingTiers": guard.validate_pricing_tiers(pricing_tiers, min_required=1),
        }
        
        # MOQ validation
        if moq is not None:
            if not isinstance(moq, (int, float)) or moq < 1:
                raise HTTPException(
                    status_code=400,
                    detail="MOQ must be at least 1"
                )
            validated["moq"] = int(moq)
        else:
            validated["moq"] = 1
        
        # Stock validation
        if stock is not None:
            if not isinstance(stock, (int, float)) or stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Stock cannot be negative"
                )
            validated["stock"] = int(stock)
        else:
            validated["stock"] = 0
        
        return validated
    
    @staticmethod
    def validate_listing_for_update(
        images: Optional[List[str]] = None,
        searchable_attributes: Optional[Dict[str, Any]] = None,
        pricing_tiers: Optional[List[Dict[str, Any]]] = None,
        moq: Optional[int] = None,
        stock: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Partial validation for listing update.
        
        Only validates fields that are being updated.
        
        Returns validated update dict.
        
        Raises:
            HTTPException: If any validation fails
        """
        guard = EnterpriseListingGuard
        validated = {}
        
        if images is not None:
            validated["images"] = guard.validate_images(images, min_required=1)
        
        if searchable_attributes is not None:
            validated["searchableAttributes"] = guard.validate_searchable_attributes(searchable_attributes)
        
        if pricing_tiers is not None:
            validated["pricingTiers"] = guard.validate_pricing_tiers(pricing_tiers, min_required=1)
        
        if moq is not None:
            if not isinstance(moq, (int, float)) or moq < 1:
                raise HTTPException(
                    status_code=400,
                    detail="MOQ must be at least 1"
                )
            validated["moq"] = int(moq)
        
        if stock is not None:
            if not isinstance(stock, (int, float)) or stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Stock cannot be negative"
                )
            validated["stock"] = int(stock)
        
        return validated


# Singleton instance for easy import
enterprise_guard = EnterpriseListingGuard()
