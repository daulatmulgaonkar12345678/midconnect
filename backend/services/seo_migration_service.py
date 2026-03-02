"""
SEO v2.0 Migration Service
===========================
Complete migration of products and categories to SEO v2.0 standards.

Features:
- Regenerate slugs for products: {product-name}-{category}-supplier-india
- Regenerate slugs for categories: {category-name}
- Store old ID mappings for 301 redirects
- Ensure uniqueness with -1, -2, -3 suffixes
- Idempotent - safe to run multiple times

This migration preserves SEO authority by:
1. Storing old ID → new slug mappings
2. Enabling 301 redirects from old URLs
3. Updating all references consistently
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from bson import ObjectId

logger = logging.getLogger("seo_migration")


class SEOMigrationService:
    """Handles SEO v2.0 migration for products and categories."""
    
    # Pattern to check if slug matches v2 format
    V2_PRODUCT_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+-supplier-india(-\d+)?$')
    V2_CATEGORY_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+(-\d+)?$')
    
    def __init__(self, db):
        self.db = db
    
    # ==================== SLUG GENERATION ====================
    
    @staticmethod
    def generate_product_slug(
        product_name: str, 
        category_name: str = None,
        existing_slugs: List[str] = None
    ) -> str:
        """
        Generate SEO v2.0 product slug.
        
        Format: {product-name}-{category}-supplier-india
        
        - Lowercase
        - Replace spaces with "-"
        - Remove special characters
        - Ensure uniqueness with -1, -2 suffix
        """
        if not product_name:
            product_name = "industrial-product"
        
        # Clean product name
        clean_name = product_name.lower().strip()
        clean_name = re.sub(r'[^a-z0-9\s]+', '', clean_name)
        clean_name = re.sub(r'\s+', '-', clean_name).strip('-')
        
        # Build slug parts
        slug_parts = [clean_name]
        
        # Add category if available and different from product name
        if category_name:
            category_slug = re.sub(r'[^a-z0-9\s]+', '', category_name.lower())
            category_slug = re.sub(r'\s+', '-', category_slug).strip('-')
            if category_slug and category_slug not in clean_name:
                slug_parts.append(category_slug)
        
        # Always append supplier-india suffix
        slug_parts.append("supplier-india")
        
        base_slug = '-'.join(slug_parts)
        
        # Ensure uniqueness
        if existing_slugs:
            final_slug = base_slug
            counter = 1
            while final_slug in existing_slugs:
                final_slug = f"{base_slug}-{counter}"
                counter += 1
            return final_slug
        
        return base_slug
    
    @staticmethod
    def generate_category_slug(
        category_name: str,
        existing_slugs: List[str] = None
    ) -> str:
        """
        Generate SEO v2.0 category slug.
        
        Format: {category-name}
        
        - Lowercase
        - Replace spaces with "-"
        - Remove special characters
        - Ensure uniqueness
        """
        if not category_name:
            category_name = "general-category"
        
        # Clean category name
        clean_name = category_name.lower().strip()
        clean_name = re.sub(r'[^a-z0-9\s]+', '', clean_name)
        clean_name = re.sub(r'\s+', '-', clean_name).strip('-')
        
        if not clean_name:
            clean_name = "category"
        
        base_slug = clean_name
        
        # Ensure uniqueness
        if existing_slugs:
            final_slug = base_slug
            counter = 1
            while final_slug in existing_slugs:
                final_slug = f"{base_slug}-{counter}"
                counter += 1
            return final_slug
        
        return base_slug
    
    # ==================== MIGRATION METHODS ====================
    
    async def migrate_all_products(self, force_regenerate: bool = False) -> Dict:
        """
        Migrate all products to SEO v2.0 slugs.
        
        Args:
            force_regenerate: If True, regenerate ALL slugs. If False, only regenerate
                            null/empty or non-v2 format slugs.
        
        Returns:
            Migration statistics and any errors
        """
        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "redirects_created": 0
        }
        
        # Get all existing slugs for uniqueness check
        existing_slugs = await self.db.products.distinct("slug")
        existing_slugs = [s for s in existing_slugs if s]
        
        # Get categories for name lookup
        categories = await self.db.categories.find({}).to_list(500)
        category_map = {str(c["_id"]): c for c in categories}
        
        # Get all products
        products = await self.db.products.find({}).to_list(10000)
        stats["total"] = len(products)
        
        for product in products:
            try:
                product_id = product["_id"]
                old_slug = product.get("slug")
                product_name = product.get("name", "")
                
                # Determine if migration is needed
                needs_migration = False
                
                if not old_slug or old_slug == "":
                    needs_migration = True
                elif force_regenerate:
                    needs_migration = True
                elif not self.V2_PRODUCT_SLUG_PATTERN.match(old_slug):
                    needs_migration = True
                
                if not needs_migration:
                    stats["skipped"] += 1
                    continue
                
                # Get category name
                cat_id = product.get("categoryId")
                category_name = None
                if cat_id:
                    cat_str = str(cat_id)
                    if cat_str in category_map:
                        category_name = category_map[cat_str].get("name")
                
                # Remove old slug from existing list if present
                if old_slug and old_slug in existing_slugs:
                    existing_slugs.remove(old_slug)
                
                # Generate new slug
                new_slug = self.generate_product_slug(product_name, category_name, existing_slugs)
                
                # Prepare update
                update_data = {
                    "slug": new_slug,
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                # Store old ID/slug for redirect mapping (if not already stored)
                if not product.get("legacyIds"):
                    update_data["legacyIds"] = [str(product_id)]
                elif str(product_id) not in product.get("legacyIds", []):
                    update_data["legacyIds"] = product.get("legacyIds", []) + [str(product_id)]
                
                # Store old slug for redirect
                if old_slug and old_slug != new_slug:
                    old_slugs = product.get("legacySlugs", [])
                    if old_slug not in old_slugs:
                        update_data["legacySlugs"] = old_slugs + [old_slug]
                    stats["redirects_created"] += 1
                
                # Update product
                await self.db.products.update_one(
                    {"_id": product_id},
                    {"$set": update_data}
                )
                
                # Add to existing slugs
                existing_slugs.append(new_slug)
                stats["migrated"] += 1
                
                logger.info(f"Migrated product: {product_name[:40]} -> {new_slug}")
                
            except Exception as e:
                stats["errors"].append({
                    "productId": str(product.get("_id")),
                    "name": product.get("name"),
                    "error": str(e)
                })
        
        return stats
    
    async def migrate_all_categories(self, force_regenerate: bool = False) -> Dict:
        """
        Migrate all categories to SEO v2.0 slugs.
        
        Args:
            force_regenerate: If True, regenerate ALL slugs.
        
        Returns:
            Migration statistics and any errors
        """
        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "redirects_created": 0
        }
        
        # Get all existing slugs for uniqueness check
        existing_slugs = await self.db.categories.distinct("slug")
        existing_slugs = [s for s in existing_slugs if s]
        
        # Get all categories
        categories = await self.db.categories.find({}).to_list(1000)
        stats["total"] = len(categories)
        
        for category in categories:
            try:
                category_id = category["_id"]
                old_slug = category.get("slug")
                category_name = category.get("name", "")
                
                # Determine if migration is needed
                needs_migration = False
                
                if not old_slug or old_slug == "":
                    needs_migration = True
                elif force_regenerate:
                    needs_migration = True
                elif not self.V2_CATEGORY_SLUG_PATTERN.match(old_slug):
                    needs_migration = True
                
                if not needs_migration:
                    stats["skipped"] += 1
                    continue
                
                # Remove old slug from existing list if present
                if old_slug and old_slug in existing_slugs:
                    existing_slugs.remove(old_slug)
                
                # Generate new slug
                new_slug = self.generate_category_slug(category_name, existing_slugs)
                
                # Prepare update
                update_data = {
                    "slug": new_slug,
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                # Store old ID for redirect mapping
                if not category.get("legacyIds"):
                    update_data["legacyIds"] = [str(category_id)]
                
                # Store old slug for redirect
                if old_slug and old_slug != new_slug:
                    old_slugs = category.get("legacySlugs", [])
                    if old_slug not in old_slugs:
                        update_data["legacySlugs"] = old_slugs + [old_slug]
                    stats["redirects_created"] += 1
                
                # Update category
                await self.db.categories.update_one(
                    {"_id": category_id},
                    {"$set": update_data}
                )
                
                # Add to existing slugs
                existing_slugs.append(new_slug)
                stats["migrated"] += 1
                
                logger.info(f"Migrated category: {category_name[:40]} -> {new_slug}")
                
            except Exception as e:
                stats["errors"].append({
                    "categoryId": str(category.get("_id")),
                    "name": category.get("name"),
                    "error": str(e)
                })
        
        return stats
    
    async def get_redirect_mapping(self, entity_type: str, identifier: str) -> Optional[str]:
        """
        Get new slug for an old ID or legacy slug.
        
        Used for 301 redirect resolution.
        
        Args:
            entity_type: "product" or "category"
            identifier: Old ObjectId or legacy slug
        
        Returns:
            New slug if found, None otherwise
        """
        collection = self.db.products if entity_type == "product" else self.db.categories
        
        # Try to find by legacy ID
        doc = await collection.find_one(
            {"legacyIds": identifier},
            {"slug": 1}
        )
        
        if doc:
            return doc.get("slug")
        
        # Try to find by legacy slug
        doc = await collection.find_one(
            {"legacySlugs": identifier},
            {"slug": 1}
        )
        
        if doc:
            return doc.get("slug")
        
        # Try to find by ObjectId directly
        if len(identifier) == 24:
            try:
                doc = await collection.find_one(
                    {"_id": ObjectId(identifier)},
                    {"slug": 1}
                )
                if doc:
                    return doc.get("slug")
            except:
                pass
        
        return None
    
    async def validate_migration(self) -> Dict:
        """
        Validate migration completeness.
        
        Checks:
        - No null slugs
        - No duplicate slugs
        - All slugs match v2 pattern
        """
        validation = {
            "products": {
                "total": 0,
                "null_slugs": 0,
                "invalid_format": 0,
                "duplicates": []
            },
            "categories": {
                "total": 0,
                "null_slugs": 0,
                "invalid_format": 0,
                "duplicates": []
            },
            "is_valid": True
        }
        
        # Validate products
        products = await self.db.products.find({}, {"slug": 1, "name": 1}).to_list(10000)
        validation["products"]["total"] = len(products)
        
        seen_slugs = {}
        for p in products:
            slug = p.get("slug")
            
            if not slug:
                validation["products"]["null_slugs"] += 1
                validation["is_valid"] = False
            elif not self.V2_PRODUCT_SLUG_PATTERN.match(slug):
                validation["products"]["invalid_format"] += 1
            
            if slug:
                if slug in seen_slugs:
                    validation["products"]["duplicates"].append({
                        "slug": slug,
                        "ids": [seen_slugs[slug], str(p["_id"])]
                    })
                    validation["is_valid"] = False
                else:
                    seen_slugs[slug] = str(p["_id"])
        
        # Validate categories
        categories = await self.db.categories.find({}, {"slug": 1, "name": 1}).to_list(1000)
        validation["categories"]["total"] = len(categories)
        
        seen_slugs = {}
        for c in categories:
            slug = c.get("slug")
            
            if not slug:
                validation["categories"]["null_slugs"] += 1
                validation["is_valid"] = False
            elif not self.V2_CATEGORY_SLUG_PATTERN.match(slug):
                validation["categories"]["invalid_format"] += 1
            
            if slug:
                if slug in seen_slugs:
                    validation["categories"]["duplicates"].append({
                        "slug": slug,
                        "ids": [seen_slugs[slug], str(c["_id"])]
                    })
                    validation["is_valid"] = False
                else:
                    seen_slugs[slug] = str(c["_id"])
        
        return validation
    
    async def run_full_migration(self, force_regenerate: bool = False) -> Dict:
        """
        Run complete SEO v2.0 migration.
        
        Steps:
        1. Migrate all categories (needed for product slug generation)
        2. Migrate all products
        3. Validate migration
        
        Returns:
            Complete migration report
        """
        report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "categories": None,
            "products": None,
            "validation": None,
            "completed_at": None,
            "success": False
        }
        
        try:
            # Step 1: Migrate categories first (needed for product slugs)
            logger.info("Starting category migration...")
            report["categories"] = await self.migrate_all_categories(force_regenerate)
            
            # Step 2: Migrate products
            logger.info("Starting product migration...")
            report["products"] = await self.migrate_all_products(force_regenerate)
            
            # Step 3: Validate
            logger.info("Validating migration...")
            report["validation"] = await self.validate_migration()
            
            report["completed_at"] = datetime.now(timezone.utc).isoformat()
            report["success"] = report["validation"]["is_valid"]
            
        except Exception as e:
            report["error"] = str(e)
            report["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        return report
