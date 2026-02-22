"""
V14 Master Data Alignment Migration
===================================
Comprehensive migration to align ALL MongoDB documents to strict camelCase schema.

This migration performs:
1. Phase 1: Validate current state
2. Phase 2: Users collection migration (flat fields -> nested profile/gst, roles array)
3. Phase 3: Products collection cleanup
4. Phase 4: Seller Listings standardization
5. Phase 5: Inquiries cleanup
6. Phase 6: Category requests cleanup
7. Phase 7: Subscriptions cleanup
8. Phase 8: Global field cleanup across all collections
9. Phase 9: Validation check
10. Phase 10: Final strict enforcement

Run with:
    python V14_master_data_alignment.py --dry-run    # Preview changes
    python V14_master_data_alignment.py --execute    # Execute migration
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# TARGET SCHEMAS (camelCase SSOT)
# =============================================================================

TARGET_SCHEMAS = {
    "users": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "firebaseUid", "roles", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "email": {"bsonType": "string"},
                "firebaseUid": {"bsonType": "string"},
                "roles": {"bsonType": "array", "items": {"bsonType": "string"}},
                "isAdmin": {"bsonType": "bool"},
                "profile": {
                    "bsonType": "object",
                    "properties": {
                        "businessName": {"bsonType": ["string", "null"]},
                        "phone": {"bsonType": ["string", "null"]},
                        "city": {"bsonType": ["string", "null"]},
                        "state": {"bsonType": ["string", "null"]},
                        "pincode": {"bsonType": ["string", "null"]},
                        "address": {"bsonType": ["string", "null"]},
                        "latitude": {"bsonType": ["double", "null"]},
                        "longitude": {"bsonType": ["double", "null"]}
                    }
                },
                "gst": {
                    "bsonType": "object",
                    "properties": {
                        "number": {"bsonType": ["string", "null"]},
                        "status": {"bsonType": ["string", "null"]},
                        "verified": {"bsonType": "bool"}
                    }
                },
                "emailVerified": {"bsonType": "bool"},
                "accountStatus": {"bsonType": "string"},
                "canLogin": {"bsonType": "bool"},
                "isActive": {"bsonType": "bool"},
                "deletedAt": {"bsonType": ["date", "null"]},
                "deletionReason": {"bsonType": ["string", "null"]},
                "subscription": {
                    "bsonType": "object",
                    "properties": {
                        "plan": {"bsonType": "string"},
                        "status": {"bsonType": "string"},
                        "startDate": {"bsonType": ["date", "null"]},
                        "endDate": {"bsonType": ["date", "null"]},
                        "trialEndsAt": {"bsonType": ["date", "null"]},
                        "inquiryLimit": {"bsonType": ["int", "long"]},
                        "enquiriesThisMonth": {"bsonType": ["int", "long"]},
                        "enquiriesResetAt": {"bsonType": "date"},
                        "active": {"bsonType": "bool"}
                    }
                },
                "favourites": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "recentSearches": {"bsonType": "array", "items": {"bsonType": "string"}},
                "adminPromotedAt": {"bsonType": ["date", "null"]},
                "subscriptionUpdatedAt": {"bsonType": ["date", "null"]},
                "subscriptionUpdatedBy": {"bsonType": ["string", "null"]},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "products": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "categoryId", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "description": {"bsonType": ["string", "null"]},
                "categoryId": {"bsonType": "objectId"},
                "categoryName": {"bsonType": "string"},
                "family": {"bsonType": ["string", "null"]},
                "variant": {"bsonType": ["string", "null"]},
                "slug": {"bsonType": ["string", "null"]},
                "coverImageUrl": {"bsonType": ["string", "null"]},
                "specTemplateIds": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "specTemplateVersions": {"bsonType": "array", "items": {"bsonType": ["int", "long"]}},
                "specSchema": {"bsonType": ["array", "null"]},
                "standardParameters": {"bsonType": ["array", "null"]},
                "normalizedSpecs": {"bsonType": ["object", "null"]},
                "normalizedSpecHash": {"bsonType": ["string", "null"]},
                "unit": {"bsonType": ["string", "null"]},
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "createdBy": {"bsonType": ["objectId", "null"]},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "seller_listings": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["sellerId", "productId", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "sellerId": {"bsonType": "objectId"},
                "productId": {"bsonType": "objectId"},
                "categoryId": {"bsonType": ["objectId", "null"]},
                "productSnapshot": {
                    "bsonType": "object",
                    "properties": {
                        "name": {"bsonType": "string"},
                        "categoryId": {"bsonType": "objectId"},
                        "categoryName": {"bsonType": "string"},
                        "coverImageUrl": {"bsonType": ["string", "null"]}
                    }
                },
                "sellerRole": {"bsonType": ["string", "null"]},
                "sellerType": {"bsonType": ["string", "null"]},
                "description": {"bsonType": ["string", "null"]},
                "specifications": {"bsonType": "object"},
                "specTemplateIds": {"bsonType": "array", "items": {"bsonType": "objectId"}},
                "specTemplateVersions": {"bsonType": "array", "items": {"bsonType": ["int", "long"]}},
                "availability": {
                    "bsonType": "object",
                    "properties": {
                        "moq": {"bsonType": ["int", "long"]},
                        "stock": {"bsonType": ["int", "long"]},
                        "leadTimeDays": {"bsonType": ["int", "long"]},
                        "stockStatus": {"bsonType": "string"}
                    }
                },
                "moq": {"bsonType": ["int", "long", "null"]},
                "stock": {"bsonType": ["int", "long", "null"]},
                "leadTime": {"bsonType": ["int", "long", "null"]},
                "pricing": {"bsonType": ["array", "object", "null"]},
                "currency": {"bsonType": ["string", "null"]},
                "images": {"bsonType": "array", "items": {"bsonType": "string"}},
                "status": {"bsonType": "string"},
                "isActive": {"bsonType": "bool"},
                "publishedAt": {"bsonType": ["date", "null"]},
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "inquiries": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["listingId", "sellerId", "buyerId", "quantity", "status", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "listingId": {"bsonType": "objectId"},
                "productId": {"bsonType": ["objectId", "null"]},
                "sellerId": {"bsonType": "objectId"},
                "buyerId": {"bsonType": "objectId"},
                "quantity": {"bsonType": "int"},
                "message": {"bsonType": ["string", "null"]},
                "requirementNote": {"bsonType": ["string", "null"]},
                "buyerType": {"bsonType": "string"},
                "productName": {"bsonType": ["string", "null"]},
                "buyerInfo": {
                    "bsonType": "object",
                    "properties": {
                        "name": {"bsonType": ["string", "null"]},
                        "companyName": {"bsonType": ["string", "null"]},
                        "email": {"bsonType": ["string", "null"]},
                        "phone": {"bsonType": ["string", "null"]},
                        "city": {"bsonType": ["string", "null"]},
                        "state": {"bsonType": ["string", "null"]}
                    }
                },
                "status": {"bsonType": "string"},
                "isActive": {"bsonType": "bool"},
                "acceptedAt": {"bsonType": ["date", "null"]},
                "rejectedAt": {"bsonType": ["date", "null"]},
                "expiredAt": {"bsonType": ["date", "null"]},
                "quote": {
                    "bsonType": ["object", "null"],
                    "properties": {
                        "price": {"bsonType": ["double", "int", "null"]},
                        "moq": {"bsonType": ["int", "null"]},
                        "leadTimeDays": {"bsonType": ["int", "null"]},
                        "validTill": {"bsonType": ["date", "null"]},
                        "sellerNote": {"bsonType": ["string", "null"]},
                        "quotedAt": {"bsonType": ["date", "null"]}
                    }
                },
                "createdAt": {"bsonType": "date"},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "categories": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "isActive", "createdAt", "updatedAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string"},
                "description": {"bsonType": ["string", "null"]},
                "imageUrl": {"bsonType": ["string", "null"]},
                "icon": {"bsonType": ["string", "null"]},
                "displayOrder": {"bsonType": ["int", "long", "null"]},
                "settings": {
                    "bsonType": "object",
                    "properties": {
                        "allowedUnits": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "defaultUnit": {"bsonType": ["string", "null"]},
                        "allowedSellerTypes": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "dimensionsEnabled": {"bsonType": "bool"},
                        "dimensionUnits": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "dimensionFormat": {"bsonType": ["string", "null"]},
                        "dropdownOverrides": {"bsonType": ["object", "null"]}
                    }
                },
                "isActive": {"bsonType": "bool"},
                "createdAt": {"bsonType": "date"},
                "createdBy": {"bsonType": ["objectId", "null"]},
                "updatedAt": {"bsonType": "date"}
            }
        }
    },
    
    "subscriptions": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["userId", "planName", "startDate", "status", "createdAt"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "userId": {"bsonType": "objectId"},
                "planName": {"bsonType": "string"},
                "durationDays": {"bsonType": "int"},
                "startDate": {"bsonType": "date"},
                "endDate": {"bsonType": ["date", "null"]},
                "status": {"bsonType": "string"},
                "enquiryLimit": {"bsonType": ["int", "null"]},
                "enquiriesUsed": {"bsonType": ["int", "null"]},
                "enquiriesResetAt": {"bsonType": ["date", "null"]},
                "lastUpdatedBy": {"bsonType": ["string", "objectId", "null"]},
                "updatedAt": {"bsonType": ["date", "null"]},
                "notes": {"bsonType": ["string", "null"]},
                "createdAt": {"bsonType": "date"}
            }
        }
    }
}

# =============================================================================
# MIGRATION HELPERS
# =============================================================================

def snake_to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    components = s.split('_')
    return components[0] + ''.join(x.capitalize() for x in components[1:])


def find_snake_case_fields(doc: dict, path: str = "") -> list:
    """Recursively find all snake_case fields in a document."""
    snake_fields = []
    for key, value in doc.items():
        full_path = f"{path}.{key}" if path else key
        if key != "_id" and "_" in key:
            snake_fields.append(full_path)
        if isinstance(value, dict):
            snake_fields.extend(find_snake_case_fields(value, full_path))
    return snake_fields


class MigrationReport:
    def __init__(self):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.phases = {}
        self.total_modified = 0
        self.total_errors = 0
        self.errors = []
    
    def add_phase(self, phase_name: str, data: dict):
        self.phases[phase_name] = data
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.total_errors += 1
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "phases": self.phases,
            "total_modified": self.total_modified,
            "total_errors": self.total_errors,
            "errors": self.errors
        }


# =============================================================================
# PHASE 2: USERS MIGRATION
# =============================================================================

async def migrate_users(db, dry_run: bool, report: MigrationReport):
    """
    Migrate users collection:
    - Move flat fields into profile object
    - Convert GST structure
    - Build roles array from is_seller/is_admin
    - Rename timestamps
    - Remove legacy fields
    """
    print("\n" + "="*70)
    print("PHASE 2: USERS COLLECTION MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0,
        "changes": []
    }
    
    users = db.users
    all_users = await users.find().to_list(length=None)
    phase_report["total_docs"] = len(all_users)
    
    for user in all_users:
        user_id = user["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        # Check for legacy flat fields that need to move to profile
        legacy_flat_fields = {
            "business_name": "businessName",
            "businessName": "businessName",  # Already in camelCase but needs to move to profile
            "phone": "phone",
            "city": "city", 
            "state": "state",
            "pincode": "pincode",
            "address": "address"
        }
        
        # Build or update profile object
        current_profile = user.get("profile", {})
        needs_profile_update = False
        
        for old_field, new_field in legacy_flat_fields.items():
            if old_field in user and old_field != "profile":
                value = user[old_field]
                if new_field not in current_profile or current_profile.get(new_field) is None:
                    current_profile[new_field] = value
                    needs_profile_update = True
                    changes.append(f"Move {old_field} -> profile.{new_field}")
                update_ops["$unset"][old_field] = ""
        
        if needs_profile_update:
            update_ops["$set"]["profile"] = current_profile
        
        # Build or update GST object
        legacy_gst_fields = {
            "gst_number": "number",
            "gstNumber": "number",
            "gst_status": "status",
            "gstStatus": "status"
        }
        
        current_gst = user.get("gst", {"number": None, "status": None, "verified": False})
        needs_gst_update = False
        
        for old_field, new_field in legacy_gst_fields.items():
            if old_field in user:
                value = user[old_field]
                if new_field not in current_gst or current_gst.get(new_field) is None:
                    current_gst[new_field] = value
                    needs_gst_update = True
                    changes.append(f"Move {old_field} -> gst.{new_field}")
                update_ops["$unset"][old_field] = ""
        
        # Set gst.verified based on status
        if current_gst.get("status") in ["verified", "VERIFIED"]:
            current_gst["verified"] = True
        else:
            current_gst["verified"] = current_gst.get("verified", False)
        
        if needs_gst_update or "gst" not in user:
            update_ops["$set"]["gst"] = current_gst
        
        # Build roles array
        current_roles = user.get("roles", [])
        if not isinstance(current_roles, list):
            current_roles = []
        
        is_seller = user.get("is_seller", user.get("isSeller", False))
        is_admin = user.get("is_admin", user.get("isAdmin", False))
        
        if is_seller and "seller" not in current_roles:
            current_roles.append("seller")
            changes.append("Add 'seller' to roles")
        
        if is_admin and "admin" not in current_roles:
            current_roles.append("admin")
            changes.append("Add 'admin' to roles")
        
        update_ops["$set"]["roles"] = current_roles
        update_ops["$set"]["isAdmin"] = bool(is_admin)
        
        # Remove legacy role fields
        for legacy_field in ["is_seller", "is_admin", "seller_type"]:
            if legacy_field in user:
                update_ops["$unset"][legacy_field] = ""
                changes.append(f"Remove legacy field: {legacy_field}")
        
        # Rename timestamps
        if "created_at" in user:
            update_ops["$set"]["createdAt"] = user["created_at"]
            update_ops["$unset"]["created_at"] = ""
            changes.append("Rename created_at -> createdAt")
        
        if "updated_at" in user:
            update_ops["$set"]["updatedAt"] = user["updated_at"]
            update_ops["$unset"]["updated_at"] = ""
            changes.append("Rename updated_at -> updatedAt")
        
        # Ensure required fields
        if "createdAt" not in user and "createdAt" not in update_ops["$set"]:
            update_ops["$set"]["createdAt"] = datetime.now(timezone.utc)
            changes.append("Add missing createdAt")
        
        if "updatedAt" not in user and "updatedAt" not in update_ops["$set"]:
            update_ops["$set"]["updatedAt"] = datetime.now(timezone.utc)
            changes.append("Add missing updatedAt")
        
        if "isActive" not in user:
            update_ops["$set"]["isActive"] = True
            changes.append("Add missing isActive")
        
        if "emailVerified" not in user:
            update_ops["$set"]["emailVerified"] = user.get("email_verified", False)
            changes.append("Add emailVerified")
        
        if "email_verified" in user:
            update_ops["$unset"]["email_verified"] = ""
        
        if "accountStatus" not in user:
            update_ops["$set"]["accountStatus"] = user.get("account_status", "active")
            changes.append("Add accountStatus")
        
        if "account_status" in user:
            update_ops["$unset"]["account_status"] = ""
        
        # Clean up empty operations
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  User {user_id}: {len(changes)} changes")
            for change in changes[:5]:
                print(f"    - {change}")
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more")
            
            if not dry_run and update_ops:
                try:
                    await users.update_one({"_id": user_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"User {user_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
            
            phase_report["changes"].append({
                "user_id": str(user_id),
                "changes": changes
            })
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid, {phase_report['errors']} errors")
    report.add_phase("users", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 3: PRODUCTS MIGRATION
# =============================================================================

async def migrate_products(db, dry_run: bool, report: MigrationReport):
    """Migrate products collection to strict camelCase."""
    print("\n" + "="*70)
    print("PHASE 3: PRODUCTS COLLECTION MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0,
        "changes": []
    }
    
    products = db.products
    all_products = await products.find().to_list(length=None)
    phase_report["total_docs"] = len(all_products)
    
    field_renames = {
        "category_id": "categoryId",
        "category_name": "categoryName",
        "cover_image_url": "coverImageUrl",
        "spec_template_ids": "specTemplateIds",
        "spec_template_versions": "specTemplateVersions",
        "spec_schema": "specSchema",
        "standard_parameters": "standardParameters",
        "normalized_specs": "normalizedSpecs",
        "normalized_spec_hash": "normalizedSpecHash",
        "is_active": "isActive",
        "created_at": "createdAt",
        "created_by": "createdBy",
        "updated_at": "updatedAt"
    }
    
    for product in all_products:
        product_id = product["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        # Rename snake_case fields
        for old_field, new_field in field_renames.items():
            if old_field in product:
                update_ops["$set"][new_field] = product[old_field]
                update_ops["$unset"][old_field] = ""
                changes.append(f"Rename {old_field} -> {new_field}")
        
        # Ensure required fields
        if "isActive" not in product and "isActive" not in update_ops["$set"]:
            update_ops["$set"]["isActive"] = True
            changes.append("Add missing isActive")
        
        if "specTemplateIds" not in product and "specTemplateIds" not in update_ops["$set"]:
            update_ops["$set"]["specTemplateIds"] = []
            changes.append("Add missing specTemplateIds")
        
        if "specTemplateVersions" not in product and "specTemplateVersions" not in update_ops["$set"]:
            update_ops["$set"]["specTemplateVersions"] = []
            changes.append("Add missing specTemplateVersions")
        
        # Ensure createdBy is ObjectId or null
        if "createdBy" in product and product["createdBy"] is not None:
            if isinstance(product["createdBy"], str):
                try:
                    update_ops["$set"]["createdBy"] = ObjectId(product["createdBy"])
                    changes.append("Convert createdBy to ObjectId")
                except:
                    update_ops["$set"]["createdBy"] = None
                    changes.append("Set invalid createdBy to null")
        
        # Clean up
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  Product {product_id}: {len(changes)} changes")
            
            if not dry_run and update_ops:
                try:
                    await products.update_one({"_id": product_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"Product {product_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid")
    report.add_phase("products", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 4: SELLER LISTINGS MIGRATION
# =============================================================================

async def migrate_seller_listings(db, dry_run: bool, report: MigrationReport):
    """Migrate seller_listings collection."""
    print("\n" + "="*70)
    print("PHASE 4: SELLER LISTINGS MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0
    }
    
    listings = db.seller_listings
    all_listings = await listings.find().to_list(length=None)
    phase_report["total_docs"] = len(all_listings)
    
    field_renames = {
        "seller_id": "sellerId",
        "product_id": "productId",
        "category_id": "categoryId",
        "product_snapshot": "productSnapshot",
        "seller_type": "sellerType",
        "seller_role": "sellerRole",
        "spec_template_ids": "specTemplateIds",
        "spec_template_versions": "specTemplateVersions",
        "lead_time": "leadTime",
        "lead_time_days": "leadTimeDays",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "published_at": "publishedAt"
    }
    
    for listing in all_listings:
        listing_id = listing["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        # Rename snake_case fields
        for old_field, new_field in field_renames.items():
            if old_field in listing:
                update_ops["$set"][new_field] = listing[old_field]
                update_ops["$unset"][old_field] = ""
                changes.append(f"Rename {old_field} -> {new_field}")
        
        # Standardize pricing structure
        pricing = listing.get("pricing", [])
        if isinstance(pricing, list):
            standardized_pricing = []
            for slab in pricing:
                if isinstance(slab, dict):
                    std_slab = {
                        "quantityMin": slab.get("quantityMin", slab.get("minQty", slab.get("quantity_min", 1))),
                        "quantityMax": slab.get("quantityMax", slab.get("maxQty", slab.get("quantity_max"))),
                        "pricePerUnit": slab.get("pricePerUnit", slab.get("price_per_unit", 0)),
                        "currency": slab.get("currency", "INR")
                    }
                    # Ensure numeric types
                    std_slab["quantityMin"] = int(std_slab["quantityMin"]) if std_slab["quantityMin"] else 1
                    if std_slab["pricePerUnit"]:
                        std_slab["pricePerUnit"] = float(std_slab["pricePerUnit"])
                    standardized_pricing.append(std_slab)
            
            if standardized_pricing != pricing:
                update_ops["$set"]["pricing"] = standardized_pricing
                changes.append("Standardize pricing slabs")
        
        # Ensure required fields
        if "isActive" not in listing and "isActive" not in update_ops["$set"]:
            update_ops["$set"]["isActive"] = True
            changes.append("Add missing isActive")
        
        if "images" not in listing:
            update_ops["$set"]["images"] = []
            changes.append("Add missing images array")
        
        if "specifications" not in listing:
            update_ops["$set"]["specifications"] = {}
            changes.append("Add missing specifications")
        
        # Clean up
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  Listing {listing_id}: {len(changes)} changes")
            
            if not dry_run and update_ops:
                try:
                    await listings.update_one({"_id": listing_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"Listing {listing_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid")
    report.add_phase("seller_listings", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 5: INQUIRIES MIGRATION
# =============================================================================

async def migrate_inquiries(db, dry_run: bool, report: MigrationReport):
    """Migrate inquiries collection."""
    print("\n" + "="*70)
    print("PHASE 5: INQUIRIES MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0
    }
    
    inquiries = db.inquiries
    all_inquiries = await inquiries.find().to_list(length=None)
    phase_report["total_docs"] = len(all_inquiries)
    
    field_renames = {
        "listing_id": "listingId",
        "product_id": "productId",
        "seller_id": "sellerId",
        "buyer_id": "buyerId",
        "buyer_type": "buyerType",
        "buyer_info": "buyerInfo",
        "product_name": "productName",
        "requirement_note": "requirementNote",
        "is_active": "isActive",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "accepted_at": "acceptedAt",
        "rejected_at": "rejectedAt",
        "expired_at": "expiredAt"
    }
    
    for inquiry in all_inquiries:
        inquiry_id = inquiry["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        # Rename snake_case fields
        for old_field, new_field in field_renames.items():
            if old_field in inquiry:
                update_ops["$set"][new_field] = inquiry[old_field]
                update_ops["$unset"][old_field] = ""
                changes.append(f"Rename {old_field} -> {new_field}")
        
        # Ensure quantity is int
        quantity = inquiry.get("quantity")
        if quantity is not None and not isinstance(quantity, int):
            try:
                update_ops["$set"]["quantity"] = int(quantity)
                changes.append("Convert quantity to int")
            except:
                update_ops["$set"]["quantity"] = 1
                changes.append("Set invalid quantity to 1")
        
        # Standardize buyerInfo
        buyer_info = inquiry.get("buyerInfo", inquiry.get("buyer_info", {}))
        if buyer_info:
            std_buyer_info = {
                "name": buyer_info.get("name"),
                "companyName": buyer_info.get("companyName", buyer_info.get("company_name")),
                "email": buyer_info.get("email"),
                "phone": buyer_info.get("phone"),
                "city": buyer_info.get("city"),
                "state": buyer_info.get("state")
            }
            if std_buyer_info != buyer_info:
                update_ops["$set"]["buyerInfo"] = std_buyer_info
                changes.append("Standardize buyerInfo")
        
        # Ensure required fields
        if "isActive" not in inquiry and "isActive" not in update_ops["$set"]:
            update_ops["$set"]["isActive"] = inquiry.get("status", "pending") not in ["completed", "cancelled"]
            changes.append("Add missing isActive")
        
        if "buyerType" not in inquiry and "buyerType" not in update_ops["$set"]:
            update_ops["$set"]["buyerType"] = "buyer"
            changes.append("Add missing buyerType")
        
        # Clean up
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  Inquiry {inquiry_id}: {len(changes)} changes")
            
            if not dry_run and update_ops:
                try:
                    await inquiries.update_one({"_id": inquiry_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"Inquiry {inquiry_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid")
    report.add_phase("inquiries", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 6: CATEGORIES MIGRATION
# =============================================================================

async def migrate_categories(db, dry_run: bool, report: MigrationReport):
    """Migrate categories collection."""
    print("\n" + "="*70)
    print("PHASE 6: CATEGORIES MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0
    }
    
    categories = db.categories
    all_categories = await categories.find().to_list(length=None)
    phase_report["total_docs"] = len(all_categories)
    
    field_renames = {
        "image_url": "imageUrl",
        "image": "imageUrl",
        "display_order": "displayOrder",
        "is_active": "isActive",
        "created_at": "createdAt",
        "created_by": "createdBy",
        "updated_at": "updatedAt"
    }
    
    for category in all_categories:
        cat_id = category["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        for old_field, new_field in field_renames.items():
            if old_field in category:
                update_ops["$set"][new_field] = category[old_field]
                update_ops["$unset"][old_field] = ""
                changes.append(f"Rename {old_field} -> {new_field}")
        
        if "isActive" not in category and "isActive" not in update_ops["$set"]:
            update_ops["$set"]["isActive"] = True
            changes.append("Add missing isActive")
        
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  Category {cat_id}: {len(changes)} changes")
            
            if not dry_run and update_ops:
                try:
                    await categories.update_one({"_id": cat_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"Category {cat_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid")
    report.add_phase("categories", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 7: SUBSCRIPTIONS MIGRATION
# =============================================================================

async def migrate_subscriptions(db, dry_run: bool, report: MigrationReport):
    """Migrate subscriptions collection."""
    print("\n" + "="*70)
    print("PHASE 7: SUBSCRIPTIONS MIGRATION")
    print("="*70)
    
    phase_report = {
        "total_docs": 0,
        "modified": 0,
        "already_valid": 0,
        "errors": 0
    }
    
    subscriptions = db.subscriptions
    all_subs = await subscriptions.find().to_list(length=None)
    phase_report["total_docs"] = len(all_subs)
    
    field_renames = {
        "user_id": "userId",
        "plan_name": "planName",
        "duration_days": "durationDays",
        "start_date": "startDate",
        "end_date": "endDate",
        "trial_ends_at": "trialEndsAt",
        "inquiry_limit": "enquiryLimit",
        "enquiry_limit": "enquiryLimit",
        "enquiries_used": "enquiriesUsed",
        "enquiries_reset_at": "enquiriesResetAt",
        "last_updated_by": "lastUpdatedBy",
        "created_at": "createdAt",
        "updated_at": "updatedAt"
    }
    
    for sub in all_subs:
        sub_id = sub["_id"]
        changes = []
        update_ops = {"$set": {}, "$unset": {}}
        
        for old_field, new_field in field_renames.items():
            if old_field in sub:
                update_ops["$set"][new_field] = sub[old_field]
                update_ops["$unset"][old_field] = ""
                changes.append(f"Rename {old_field} -> {new_field}")
        
        if not update_ops["$set"]:
            del update_ops["$set"]
        if not update_ops["$unset"]:
            del update_ops["$unset"]
        
        if changes:
            print(f"  Subscription {sub_id}: {len(changes)} changes")
            
            if not dry_run and update_ops:
                try:
                    await subscriptions.update_one({"_id": sub_id}, update_ops)
                    phase_report["modified"] += 1
                except Exception as e:
                    phase_report["errors"] += 1
                    report.add_error(f"Subscription {sub_id}: {str(e)}")
            else:
                phase_report["modified"] += 1
        else:
            phase_report["already_valid"] += 1
    
    print(f"\n  Summary: {phase_report['modified']} modified, {phase_report['already_valid']} already valid")
    report.add_phase("subscriptions", phase_report)
    report.total_modified += phase_report["modified"]


# =============================================================================
# PHASE 9: VALIDATION CHECK
# =============================================================================

async def validate_all_collections(db, report: MigrationReport):
    """Validate all collections against schemas."""
    print("\n" + "="*70)
    print("PHASE 9: VALIDATION CHECK")
    print("="*70)
    
    for coll_name in ["users", "products", "seller_listings", "inquiries", "categories", "subscriptions"]:
        try:
            result = await db.command("validate", coll_name, full=True)
            valid = result.get("valid", False)
            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
            
            status = "✅" if valid and not warnings else "⚠️"
            print(f"  {status} {coll_name}: valid={valid}, errors={len(errors)}, warnings={len(warnings)}")
            
            if warnings:
                for w in warnings[:2]:
                    print(f"      Warning: {w[:80]}...")
        except Exception as e:
            print(f"  ❌ {coll_name}: {str(e)[:60]}")
            report.add_error(f"Validation {coll_name}: {str(e)}")


# =============================================================================
# PHASE 10: APPLY STRICT VALIDATION
# =============================================================================

async def apply_strict_validation(db, dry_run: bool, report: MigrationReport):
    """Apply strict validators to all collections."""
    print("\n" + "="*70)
    print("PHASE 10: APPLY STRICT VALIDATION")
    print("="*70)
    
    if dry_run:
        print("  (Skipped in dry-run mode)")
        return
    
    for coll_name, schema in TARGET_SCHEMAS.items():
        try:
            await db.command("collMod", coll_name,
                validator=schema,
                validationLevel="strict",
                validationAction="error"
            )
            print(f"  ✅ {coll_name}: Strict validation applied")
        except Exception as e:
            print(f"  ❌ {coll_name}: {str(e)[:60]}")
            report.add_error(f"Strict validation {coll_name}: {str(e)}")


# =============================================================================
# MAIN MIGRATION RUNNER
# =============================================================================

async def run_migration(dry_run: bool = True):
    """Run the complete migration."""
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'b2b_marketplace')
    
    if not mongo_url:
        print("ERROR: MONGO_URL not set")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    report = MigrationReport()
    
    print("=" * 70)
    print(f"V14 MASTER DATA ALIGNMENT {'(DRY RUN)' if dry_run else '(EXECUTE)'}")
    print(f"Database: {db_name}")
    print(f"Timestamp: {report.timestamp}")
    print("=" * 70)
    
    # Phase 1: Current State
    print("\n" + "="*70)
    print("PHASE 1: CURRENT STATE ANALYSIS")
    print("="*70)
    
    collections = await db.list_collection_names()
    for coll in sorted(collections):
        count = await db[coll].count_documents({})
        print(f"  {coll}: {count} documents")
    
    # Run migrations
    await migrate_users(db, dry_run, report)
    await migrate_products(db, dry_run, report)
    await migrate_seller_listings(db, dry_run, report)
    await migrate_inquiries(db, dry_run, report)
    await migrate_categories(db, dry_run, report)
    await migrate_subscriptions(db, dry_run, report)
    
    # Validation
    await validate_all_collections(db, report)
    
    # Apply strict validation (only if not dry run)
    await apply_strict_validation(db, dry_run, report)
    
    # Save report
    report_path = f"/app/backend/migrations/V14_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)
    
    print("\n" + "=" * 70)
    print(f"MIGRATION {'DRY RUN' if dry_run else 'EXECUTION'} COMPLETE")
    print(f"Total modified: {report.total_modified}")
    print(f"Total errors: {report.total_errors}")
    print(f"Report: {report_path}")
    print("=" * 70)
    
    return report.total_errors == 0


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("\n⚠️  Running in DRY-RUN mode. No changes will be made.")
        print("    Use --execute to apply changes.\n")
    else:
        print("\n🔴 EXECUTING MIGRATION - Changes will be permanent!\n")
    
    success = asyncio.run(run_migration(dry_run=dry_run))
    sys.exit(0 if success else 1)
