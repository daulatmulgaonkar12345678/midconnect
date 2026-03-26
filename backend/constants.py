"""
Centralized Constants for B2B Marketplace
==========================================
Single Source of Truth for all enums, status values, and allowed values.

STRICT RULES (camelCase SSOT - APPROVED):
1. Database field names use camelCase: sellerId, productId, categoryId, createdAt, updatedAt
2. All relational IDs are ObjectId type (not strings) in DB, serialized to strings in API responses
3. All datetimes use UTC with timezone.utc
4. All status fields use these enums - NO free-form strings
5. isActive is the canonical boolean field for soft-delete filtering
"""

from enum import Enum
from typing import List, Set

# ================== STATUS ENUMS ==================

class InquiryStatus(str, Enum):
    """Valid statuses for buyer inquiries"""
    PENDING = "pending"
    VIEWED = "viewed"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ListingStatus(str, Enum):
    """Valid statuses for seller listings"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ReportStatus(str, Enum):
    """Valid statuses for fraud/spam reports"""
    PENDING_REVIEW = "pending_review"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class ReportType(str, Enum):
    """Valid types for fraud/spam reports"""
    SPAM = "spam"
    FRAUD = "fraud"
    INAPPROPRIATE = "inappropriate"
    FAKE_LISTING = "fake_listing"
    OTHER = "other"

class SubscriptionStatus(str, Enum):
    """Valid subscription statuses"""
    FREE = "free"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SubscriptionPlan(str, Enum):
    """Valid subscription plans"""
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class AccountStatus(str, Enum):
    """Valid account statuses"""
    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"

class ListingStatus(str, Enum):
    """
    STRICT LISTING STATUS MODEL (FINAL)
    
    Lifecycle: draft -> active -> paused/archived
    
    VISIBILITY RULES:
    - DRAFT: Only seller can see (editing)
    - ACTIVE: Publicly visible to buyers
    - PAUSED: Temporarily hidden (seller can reactivate)
    - ARCHIVED: Permanently hidden
    
    NOTE: "published" and "approved" are NEVER valid for listings.
    Use "active" for publicly visible listings.
    """
    DRAFT = "draft"
    ACTIVE = "active"      # ONLY this status is publicly visible
    PAUSED = "paused"
    ARCHIVED = "archived"

class ProductStatus(str, Enum):
    """
    MASTER PRODUCT STATUS MODEL (CATALOG)
    
    - ACTIVE: Product eligible for listings
    - INACTIVE: Product hidden from new listings
    """
    ACTIVE = "active"
    INACTIVE = "inactive"

class ProductRequestStatus(str, Enum):
    """Valid statuses for product requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class GSTStatus(str, Enum):
    """Valid GST verification statuses"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"

class SellerStatus(str, Enum):
    """Valid seller application statuses"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

# ================== SELLER TYPES ==================

class SellerType(str, Enum):
    """Valid seller types"""
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    DEALER = "dealer"
    WHOLESALER = "wholesaler"
    RETAILER = "retailer"
    IMPORTER = "importer"
    EXPORTER = "exporter"

# Also support capitalized versions for backward compatibility
class SellerRole(str, Enum):
    """Valid seller roles (capitalized for UI)"""
    MANUFACTURER = "Manufacturer"
    DEALER = "Dealer"
    DISTRIBUTOR = "Distributor"
    TRADER = "Trader"
    WHOLESALER = "Wholesaler"
    RETAILER = "Retailer"

ALLOWED_SELLER_TYPES: List[str] = [st.value for st in SellerType]
ALLOWED_SELLER_ROLES: List[str] = [sr.value for sr in SellerRole]

# ================== UNITS ==================

class StandardUnit(str, Enum):
    """Standardized unit values"""
    PCS = "pcs"           # pieces
    METER = "meter"
    KG = "kg"
    GRAM = "gram"
    LITER = "liter"
    ML = "ml"
    SET = "set"
    PAIR = "pair"
    BOX = "box"
    PACK = "pack"
    ROLL = "roll"
    SHEET = "sheet"
    TON = "ton"
    QUINTAL = "quintal"
    BAG = "bag"
    BUNDLE = "bundle"
    CARTON = "carton"
    DRUM = "drum"
    SQ_METER = "sq_meter"
    SQ_FEET = "sq_feet"
    CUBIC_METER = "cubic_meter"
    FEET = "feet"
    INCH = "inch"

ALLOWED_UNITS: List[str] = [u.value for u in StandardUnit]

# Unit normalization mapping (legacy → standard)
UNIT_NORMALIZATION_MAP = {
    # Pieces variants
    "pieces": "pcs",
    "piece": "pcs",
    "pc": "pcs",
    "pcs": "pcs",
    # Meter variants
    "meters": "meter",
    "m": "meter",
    "meter": "meter",
    # Kilogram variants
    "kilogram": "kg",
    "kilograms": "kg",
    "kgs": "kg",
    "kg": "kg",
    # Gram variants
    "grams": "gram",
    "gm": "gram",
    "gram": "gram",
    # Liter variants
    "liters": "liter",
    "l": "liter",
    "litres": "liter",
    "liter": "liter",
    # Milliliter variants
    "milliliter": "ml",
    "milliliters": "ml",
    "ml": "ml",
    # Other plurals
    "sets": "set",
    "pairs": "pair",
    "boxes": "box",
    "packs": "pack",
    "rolls": "roll",
    "sheets": "sheet",
    "tons": "ton",
    "tonnes": "ton",
    "quintals": "quintal",
    "bags": "bag",
    "bundles": "bundle",
    "cartons": "carton",
    "drums": "drum",
    # Area/Volume
    "sqm": "sq_meter",
    "sqft": "sq_feet",
    "cbm": "cubic_meter",
    "ft": "feet",
    "in": "inch",
    "inches": "inch",
}

def normalize_unit(unit: str) -> str:
    """Normalize a unit value to standard format"""
    if not unit:
        return "pcs"  # Default
    unit_lower = unit.lower().strip()
    return UNIT_NORMALIZATION_MAP.get(unit_lower, unit_lower)

def is_valid_unit(unit: str) -> bool:
    """Check if a unit is valid (either standard or normalizable)"""
    if not unit:
        return False
    normalized = normalize_unit(unit)
    return normalized in ALLOWED_UNITS

# ================== PRICING ==================

class PricingType(str, Enum):
    """Valid pricing types"""
    FIXED = "fixed"
    NEGOTIABLE = "negotiable"
    RFQ_ONLY = "rfq_only"

class StockStatus(str, Enum):
    """Valid stock statuses"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    MADE_TO_ORDER = "made_to_order"

# ================== BUYER TYPES ==================

class BuyerType(str, Enum):
    """Valid buyer types for inquiries"""
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    DEALER = "dealer"
    WHOLESALER = "wholesaler"
    RETAILER = "retailer"
    END_USER = "end_user"
    OTHER = "other"

# ================== DIMENSION UNITS ==================

ALLOWED_DIMENSION_UNITS: List[str] = ["mm", "cm", "m", "inch", "feet"]

# ================== CANONICAL FIELD NAMES (camelCase SSOT) ==================
# These are the ONLY valid field names for database storage
# API responses serialize ObjectId to strings

CANONICAL_FIELD_NAMES = {
    # ID Fields (all must be ObjectId type in DB)
    "id_fields": {
        "sellerId",      # Reference to users collection
        "buyerId",       # Reference to users collection  
        "productId",     # Reference to products collection
        "categoryId",    # Reference to categories collection
        "listingId",     # Reference to seller_listings collection
        "inquiryId",     # Reference to inquiries collection
        "createdBy",     # User who created the record
        "reviewedBy",    # Admin who reviewed
    },
    # Timestamp Fields (all must be datetime with UTC)
    "timestamp_fields": {
        "createdAt",
        "updatedAt",
        "deletedAt",
        "publishedAt",
        "acceptedAt",
        "rejectedAt",
        "reviewedAt",
        "quotedAt",
        "expiresAt",
        "validTill",
        "trialEndsAt",
    },
    # Boolean Fields
    "boolean_fields": {
        "isActive",      # Canonical soft-delete flag
        "is_active",     # Allowed alias (backward compat)
        "is_admin",
        "is_seller",
        "email_verified",
        "can_login",
    },
}

# Legacy fields that should be REMOVED from documents
# These are snake_case variants that conflict with camelCase SSOT
LEGACY_FIELDS_TO_REMOVE = {
    "active",           # Use isActive or status instead
    "seller_id",        # Use sellerId
    "buyer_id",         # Use buyerId
    "product_id",       # Use productId
    "category_id",      # Use categoryId
    "listing_id",       # Use listingId
    "created_at",       # Use createdAt
    "updated_at",       # Use updatedAt
    "deleted_at",       # Use deletedAt
    "published_at",     # Use publishedAt
    "product_name",     # Denormalized - use $lookup
    "category_name",    # Denormalized - use $lookup
    "seller_name",      # Denormalized - use $lookup
    "seller_type",      # Use sellerRole
}

# ================== HELPER FUNCTIONS ==================

def get_status_values(status_enum) -> List[str]:
    """Get list of valid values for a status enum"""
    return [s.value for s in status_enum]

def is_valid_status(value: str, status_enum) -> bool:
    """Check if a value is valid for a status enum"""
    return value in get_status_values(status_enum)

def validate_listing_status(status: str) -> bool:
    """Validate listing status against enum"""
    return is_valid_status(status, ListingStatus)

def validate_inquiry_status(status: str) -> bool:
    """Validate inquiry status against enum"""
    return is_valid_status(status, InquiryStatus)

def validate_subscription_status(status: str) -> bool:
    """Validate subscription status against enum"""
    return is_valid_status(status, SubscriptionStatus)

# Export all enums for easy import
__all__ = [
    # Enums
    "InquiryStatus",
    "ListingStatus",
    "ReportStatus",
    "ReportType",
    "SubscriptionStatus",
    "SubscriptionPlan",
    "AccountStatus",
    "ProductRequestStatus",
    "GSTStatus",
    "SellerStatus",
    "SellerType",
    "SellerRole",
    "StandardUnit",
    "PricingType",
    "StockStatus",
    "BuyerType",
    # Lists
    "ALLOWED_SELLER_TYPES",
    "ALLOWED_SELLER_ROLES",
    "ALLOWED_UNITS",
    "ALLOWED_DIMENSION_UNITS",
    "CANONICAL_FIELD_NAMES",
    "LEGACY_FIELDS_TO_REMOVE",
    # Functions
    "normalize_unit",
    "is_valid_unit",
    "get_status_values",
    "is_valid_status",
    "validate_listing_status",
    "validate_inquiry_status",
    "validate_subscription_status",
    "UNIT_NORMALIZATION_MAP",
]
