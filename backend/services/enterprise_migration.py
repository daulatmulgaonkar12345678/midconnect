"""
ENTERPRISE PRODUCT ARCHITECTURE MIGRATION SERVICE
==================================================

Migrates existing sellerListings to use:
1. productVariants (activated)
2. searchableAttributes (denormalized)
3. searchableText (full-text search ready)

DOES NOT break existing flows.
DOES NOT remove old fields.
ADDS new enterprise fields.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
import logging

logger = logging.getLogger("enterprise_migration")


class EnterpriseMigrationService:
    """
    Service to migrate sellerListings to enterprise architecture.
    
    Flow:
    1. For each listing, get product and category
    2. Get specTemplate for category
    3. Extract/generate attributes
    4. Create or reuse productVariant
    5. Update listing with variantId, searchableAttributes, searchableText
    """
    
    def __init__(self, db):
        self.db = db
    
    def _generate_attribute_hash(self, attributes: Dict[str, Any]) -> str:
        """Generate deterministic hash from attributes for deduplication."""
        if not attributes:
            return "empty"
        
        # Sort keys and create canonical string
        sorted_items = sorted(attributes.items(), key=lambda x: x[0])
        canonical = json.dumps(sorted_items, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    
    def _normalize_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize attribute values for consistency."""
        if not attrs:
            return {}
        
        normalized = {}
        for key, value in attrs.items():
            # Convert key to camelCase
            clean_key = key.strip().lower().replace(" ", "_").replace("-", "_")
            
            # Normalize value
            if isinstance(value, str):
                normalized[clean_key] = value.strip()
            elif isinstance(value, (int, float)):
                normalized[clean_key] = value
            elif value is None:
                continue
            else:
                normalized[clean_key] = str(value)
        
        return normalized
    
    async def _build_searchable_text(
        self,
        product: Dict,
        category: Optional[Dict],
        attributes: Dict[str, Any],
        seller: Optional[Dict],
        listing: Dict
    ) -> str:
        """
        Build searchable text from all relevant fields.
        
        Includes:
        - Product name
        - Category name
        - Attribute keys and values
        - Seller location
        - Description
        - Common synonyms
        """
        parts = []
        
        # Product name
        if product.get("name"):
            parts.append(product["name"])
            # Add common variations
            name_parts = product["name"].split()
            parts.extend(name_parts)
        
        # Category name
        if category and category.get("name"):
            parts.append(category["name"])
        
        # Attributes with units
        for key, value in attributes.items():
            parts.append(f"{key}")
            parts.append(f"{value}")
            parts.append(f"{key}:{value}")
            
            # Add common industrial synonyms
            if key in ["power", "wattage", "kw"]:
                parts.extend(["power", "kw", "kilowatt", "watt"])
            if key in ["voltage", "volt", "v"]:
                parts.extend(["voltage", "volt", "v", "volts"])
            if key in ["mounting", "mount_type", "mounting_type"]:
                parts.extend(["mounting", "mount", "flange", "foot", "b3", "b5", "b14"])
        
        # Seller location
        if seller:
            if seller.get("profile", {}).get("city"):
                parts.append(seller["profile"]["city"])
            if seller.get("profile", {}).get("state"):
                parts.append(seller["profile"]["state"])
        
        # Description
        if listing.get("description"):
            parts.append(listing["description"])
        
        # Join and lowercase
        searchable = " ".join(filter(None, parts))
        return searchable.lower()
    
    async def _get_or_create_variant(
        self,
        product_id: ObjectId,
        attributes: Dict[str, Any],
        template_id: Optional[ObjectId]
    ) -> Dict:
        """Get existing variant or create new one."""
        attribute_hash = self._generate_attribute_hash(attributes)
        
        # Check for existing variant
        existing = await self.db.productVariants.find_one({
            "productId": product_id,
            "attributeHash": attribute_hash
        })
        
        if existing:
            return existing
        
        # Create new variant
        now = datetime.now(timezone.utc)
        variant = {
            "_id": ObjectId(),
            "productId": product_id,
            "attributes": attributes,
            "attributeHash": attribute_hash,
            "templateVersions": [],
            "isActive": True,
            "createdAt": now,
            "updatedAt": now
        }
        
        if template_id:
            template = await self.db.specTemplates.find_one({"_id": template_id})
            if template:
                variant["templateVersions"].append({
                    "templateId": template_id,
                    "version": template.get("version", 1),
                    "snapshotAt": now
                })
        
        await self.db.productVariants.insert_one(variant)
        logger.info(f"Created variant {variant['_id']} for product {product_id}")
        return variant
    
    async def migrate_listing(self, listing: Dict) -> Dict:
        """Migrate a single listing to enterprise architecture."""
        listing_id = listing["_id"]
        product_id = listing.get("productId")
        seller_id = listing.get("sellerId")
        
        if not product_id:
            logger.warning(f"Listing {listing_id} has no productId, skipping")
            return {"status": "skipped", "reason": "no_productId"}
        
        # Get product
        product = await self.db.products.find_one({"_id": product_id})
        if not product:
            logger.warning(f"Product {product_id} not found for listing {listing_id}")
            return {"status": "skipped", "reason": "product_not_found"}
        
        # Get category
        category = None
        category_id = product.get("categoryId")
        if category_id:
            category = await self.db.categories.find_one({"_id": category_id})
        
        # Get spec template
        template = None
        template_id = None
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            template_id = template_ids[0] if isinstance(template_ids[0], ObjectId) else ObjectId(template_ids[0])
            template = await self.db.specTemplates.find_one({"_id": template_id})
        
        # Get seller
        seller = None
        if seller_id:
            seller = await self.db.users.find_one({"_id": seller_id})
        
        # Extract attributes from listing.specifications or generate defaults
        raw_specs = listing.get("specifications", {})
        normalized_specs = listing.get("normalizedSpecs", {})
        
        # Use existing specs or empty dict
        attributes = self._normalize_attributes(raw_specs or normalized_specs or {})
        
        # If no attributes and we have template, use template defaults
        if not attributes and template and template.get("fields"):
            for field in template["fields"]:
                key = field.get("key")
                default = field.get("defaultValue")
                if key and default:
                    attributes[key] = default
        
        # Get or create variant
        variant = await self._get_or_create_variant(product_id, attributes, template_id)
        
        # Build searchable text
        searchable_text = await self._build_searchable_text(
            product, category, attributes, seller, listing
        )
        
        # Build attribute labels from template
        attribute_labels = {}
        if template and template.get("fields"):
            for field in template["fields"]:
                key = field.get("key")
                label = field.get("label")
                unit = field.get("unit")
                if key and label:
                    attribute_labels[key] = f"{label}" + (f" ({unit})" if unit else "")
        
        # Update listing with enterprise fields
        now = datetime.now(timezone.utc)
        update_data = {
            "variantId": variant["_id"],
            "searchableAttributes": attributes,
            "searchableText": searchable_text,
            "attributeLabels": attribute_labels,
            "enterpriseMigratedAt": now,
            "updatedAt": now
        }
        
        await self.db.sellerListings.update_one(
            {"_id": listing_id},
            {"$set": update_data}
        )
        
        logger.info(f"Migrated listing {listing_id} with variant {variant['_id']}")
        
        return {
            "status": "migrated",
            "listingId": str(listing_id),
            "variantId": str(variant["_id"]),
            "attributeCount": len(attributes),
            "searchableTextLength": len(searchable_text)
        }
    
    async def run_full_migration(self) -> Dict:
        """Run migration on all listings without variantId."""
        results = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        # Find all listings needing migration
        cursor = self.db.sellerListings.find({
            "$or": [
                {"variantId": {"$exists": False}},
                {"searchableAttributes": {"$exists": False}},
                {"searchableText": {"$exists": False}}
            ]
        })
        
        async for listing in cursor:
            results["total"] += 1
            try:
                result = await self.migrate_listing(listing)
                if result["status"] == "migrated":
                    results["migrated"] += 1
                else:
                    results["skipped"] += 1
                results["details"].append(result)
            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "status": "error",
                    "listingId": str(listing["_id"]),
                    "error": str(e)
                })
                logger.error(f"Migration error for listing {listing['_id']}: {e}")
        
        return results
    
    async def create_indexes(self) -> Dict:
        """Create enterprise indexes for search and filtering."""
        created = []
        
        try:
            # Text search index with weights
            await self.db.sellerListings.create_index(
                [("searchableText", "text"), ("description", "text")],
                weights={"searchableText": 5, "description": 1},
                name="enterprise_text_search"
            )
            created.append("enterprise_text_search")
        except Exception as e:
            logger.warning(f"Text index may already exist: {e}")
        
        try:
            # Product + status + variant compound index
            await self.db.sellerListings.create_index(
                [("productId", 1), ("status", 1), ("variantId", 1)],
                name="product_variant_idx"
            )
            created.append("product_variant_idx")
        except Exception as e:
            logger.warning(f"Compound index may already exist: {e}")
        
        try:
            # Searchable attributes index (sparse for optional fields)
            await self.db.sellerListings.create_index(
                [("productId", 1), ("status", 1), ("searchableAttributes", 1)],
                name="product_attrs_idx",
                sparse=True
            )
            created.append("product_attrs_idx")
        except Exception as e:
            logger.warning(f"Attributes index may already exist: {e}")
        
        try:
            # Variant deduplication index
            await self.db.productVariants.create_index(
                [("productId", 1), ("attributeHash", 1)],
                name="variant_dedup_idx",
                unique=True
            )
            created.append("variant_dedup_idx")
        except Exception as e:
            logger.warning(f"Variant index may already exist: {e}")
        
        return {"created": created, "total": len(created)}
    
    async def get_migration_status(self) -> Dict:
        """Get current migration status."""
        total_listings = await self.db.sellerListings.count_documents({})
        migrated = await self.db.sellerListings.count_documents({"variantId": {"$exists": True}})
        with_search_text = await self.db.sellerListings.count_documents({"searchableText": {"$exists": True}})
        total_variants = await self.db.productVariants.count_documents({})
        
        return {
            "totalListings": total_listings,
            "migratedListings": migrated,
            "withSearchText": with_search_text,
            "totalVariants": total_variants,
            "migrationComplete": migrated == total_listings if total_listings > 0 else True,
            "percentComplete": round(migrated / total_listings * 100, 1) if total_listings > 0 else 100
        }
