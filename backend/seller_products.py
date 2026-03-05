"""
MIDCONNECT FINAL MARKETPLACE ARCHITECTURE
==========================================
4-Layer Model with strict camelCase:

Category → SpecTemplate (SSOT) → Product → ProductVariant → SellerListing

COLLECTIONS (STRICT - NO LEGACY):
1. specTemplates - Structure SSOT (admin controlled)
2. products - Admin catalog (links to specTemplateIds ARRAY)
3. productVariants - Attribute combinations (system managed)
4. sellerListings - Commercial offers (seller controlled)
5. categories - Product categories
6. inquiries - Buyer inquiries

RULES:
- All fields camelCase
- All IDs stored as ObjectId
- Seller links to variantId, NOT productId directly
- Seller CANNOT store specifications in listing
- Tier pricing via pricingTiers array
- No legacy/hybrid mode
- No snake_case fields
- No fallback collections

ENTERPRISE SCHEMA:
- products.specTemplateIds: ObjectId[] (ARRAY, not singular)
- sellerListings.searchableAttributes: denormalized from productVariants.attributes
- sellerListings.images: REQUIRED array with at least 1 image
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import logging

from guards.enterprise_listing_guard import enterprise_guard
from services.seller_location_service import create_seller_location_service

logger = logging.getLogger("b2b_seller")


# ==================== PYDANTIC MODELS ====================

class PricingTier(BaseModel):
    """A single tier in quantity-based pricing"""
    minQty: int = Field(..., ge=1, description="Minimum quantity for this tier")
    maxQty: Optional[int] = Field(None, ge=1, description="Maximum quantity (null = unlimited)")
    pricePerUnit: float = Field(..., gt=0, description="Price per unit in this tier")
    
    @field_validator('maxQty')
    @classmethod
    def validate_max_greater_than_min(cls, v, info):
        if v is not None and 'minQty' in info.data:
            if v < info.data['minQty']:
                raise ValueError('maxQty must be >= minQty')
        return v


class ListingCreate(BaseModel):
    """Create a new seller listing"""
    productId: str = Field(..., description="Reference to products collection")
    manufacturerId: Optional[str] = Field(None, description="Reference to manufacturers collection (dropdown)")
    attributes: Dict[str, Any] = Field(..., description="Attribute values matching specTemplate")
    sellerRole: str = Field(..., description="distributor, manufacturer, trader, dealer")
    description: Optional[str] = Field(None, max_length=2000)
    images: List[str] = Field(default_factory=list, max_length=5)
    videos: List[str] = Field(default_factory=list, max_length=2, description="Product demo videos (max 2, 30s each)")
    moq: int = Field(default=1, ge=1, description="Minimum Order Quantity")
    stock: int = Field(default=0, ge=0)
    maxCapacity: Optional[int] = Field(None, ge=1)
    leadTime: Optional[int] = Field(None, ge=0, description="Days to fulfill")
    currency: str = Field(default="INR", max_length=3)
    pricingTiers: List[PricingTier] = Field(..., min_length=1, max_length=10)
    datasheetUrl: Optional[str] = None


class ListingUpdate(BaseModel):
    """Update an existing listing"""
    description: Optional[str] = Field(None, max_length=2000)
    images: Optional[List[str]] = Field(None, max_length=5)
    videos: Optional[List[str]] = Field(None, max_length=2, description="Product demo videos (max 2)")
    datasheetUrl: Optional[str] = None
    status: Optional[Literal["draft", "active", "paused", "archived"]] = None
    moq: Optional[int] = Field(None, ge=1)
    stock: Optional[int] = Field(None, ge=0)
    maxCapacity: Optional[int] = Field(None, ge=1)
    leadTime: Optional[int] = Field(None, ge=0)
    attributes: Optional[Dict[str, Any]] = Field(None)


class PricingUpdate(BaseModel):
    """Update pricing tiers only"""
    pricingTiers: List[PricingTier] = Field(..., min_length=1, max_length=10)


class QuickPriceUpdate(BaseModel):
    """Quick price update for daily changes"""
    basePrice: float = Field(..., gt=0)
    pricingTiers: Optional[List[PricingTier]] = Field(None, max_length=10)
    validTill: Literal["today", "7_days", "15_days", "30_days", "custom"] = Field(default="7_days")
    validTillDate: Optional[datetime] = None
    stockStatus: Optional[Literal["in_stock", "limited", "made_to_order", "out_of_stock"]] = None
    note: Optional[str] = Field(None, max_length=200)


class InquiryAccept(BaseModel):
    """Seller accepts an inquiry with a quote"""
    quotedPrice: float = Field(..., gt=0)
    moq: Optional[int] = Field(None, ge=1)
    leadTimeDays: Optional[int] = Field(None, ge=0)
    validityDays: int = Field(default=7, ge=1, le=90)
    sellerNote: Optional[str] = Field(None, max_length=500)


class InquiryReject(BaseModel):
    """Seller rejects an inquiry"""
    reason: Literal[
        "price_too_low", "not_available", "moq_issue",
        "location_not_serviceable", "capacity_full", "other"
    ]
    note: Optional[str] = Field(None, max_length=300)


class InquiryReport(BaseModel):
    """Report a problematic inquiry"""
    reportType: Literal["spam", "unrealistic_quantity", "fake_inquiry", "abusive", "other"]
    details: Optional[str] = Field(None, max_length=500)


# ==================== ROUTER FACTORY ====================

def create_seller_router(db, require_auth, require_verified_seller, require_gst_verified_seller=None):
    """
    Create seller product management router.
    FINAL ARCHITECTURE: 4-layer model with variantId
    """
    router = APIRouter(prefix="/seller", tags=["Seller Products"])
    
    from services.product_variant_service import ProductVariantService
    variant_service = ProductVariantService(db)
    
    # ==================== HELPER FUNCTIONS ====================
    
    def check_seller_role(user: dict) -> bool:
        return "seller" in user.get("roles", [])
    
    def check_gst_verified(user: dict) -> bool:
        return user.get("gst", {}).get("verified", False)
    
    def get_seller_status(user: dict) -> dict:
        roles = user.get("roles", [])
        gst = user.get("gst", {})
        is_seller = "seller" in roles
        is_verified = gst.get("verified", False)
        is_pending = gst.get("status") == "pending"
        return {
            "isSeller": is_seller,
            "gstVerified": is_verified,
            "gstPending": is_pending,
            "canCreateDraft": is_seller,
            "canPublish": is_seller and is_verified
        }
    
    def validate_listing_completeness(listing: dict) -> None:
        """
        ENTERPRISE VALIDATION: Ensures listing has all required fields before publish.
        
        Strict checks:
        - pricingTiers: at least 1 tier
        - moq: greater than 0
        - stock: greater than 0
        - maxCapacity: greater than 0
        - images: at least 1 image
        - variantId: must be linked
        - searchableAttributes: must have at least 1 attribute
        """
        required_fields = {
            "pricingTiers": {"check": lambda v: v and len(v) > 0, "message": "At least one pricing tier required"},
            "moq": {"check": lambda v: v and v > 0, "message": "MOQ must be greater than 0"},
            "stock": {"check": lambda v: v and v > 0, "message": "Stock quantity must be greater than 0"},
            "maxCapacity": {"check": lambda v: v and v > 0, "message": "Maximum capacity must be greater than 0"},
            "images": {"check": lambda v: v and len(v) > 0, "message": "At least one product image required"},
            "variantId": {"check": lambda v: v is not None, "message": "Product variant must be linked"},
            # ENTERPRISE: Technical specifications required for searchability
            "searchableAttributes": {"check": lambda v: v and len(v) > 0, "message": "Technical specifications required"}
        }
        missing_fields = []
        field_errors = {}
        for field, config in required_fields.items():
            value = listing.get(field)
            if not config["check"](value):
                missing_fields.append(field)
                field_errors[field] = config["message"]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Listing is incomplete and cannot be published",
                    "missingFields": missing_fields,
                    "fieldErrors": field_errors,
                    "message": f"Please complete: {', '.join(missing_fields)}"
                }
            )
    
    def serialize_mongo_doc(data):
        if data is None:
            return None
        if isinstance(data, ObjectId):
            return str(data)
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, list):
            return [serialize_mongo_doc(item) for item in data]
        if isinstance(data, dict):
            return {key: serialize_mongo_doc(value) for key, value in data.items()}
        try:
            import json
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)
    
    def success_response(data: dict) -> dict:
        return serialize_mongo_doc(data)
    
    def serialize_listing(listing: dict) -> dict:
        return serialize_mongo_doc(listing)
    
    def serialize_objectids(doc: dict) -> dict:
        return serialize_mongo_doc(doc)
    
    async def _build_searchable_text(db, product, category_id, variant, seller, description):
        """Build searchable text from all relevant fields."""
        parts = []
        
        # Product name
        if product.get("name"):
            parts.append(product["name"])
        
        # Category name
        category_name = None
        if category_id:
            category = await db.categories.find_one({"_id": category_id})
            if category and category.get("name"):
                parts.append(category["name"])
                category_name = category["name"]
        
        # Variant attributes
        attrs = variant.get("attributes", {})
        for key, value in attrs.items():
            parts.append(f"{key}")
            parts.append(f"{value}")
        
        # Seller location
        seller_city = None
        seller_state = None
        if seller:
            profile = seller.get("profile", {})
            if profile.get("city"):
                parts.append(profile["city"])
                seller_city = profile["city"]
            if profile.get("state"):
                parts.append(profile["state"])
                seller_state = profile["state"]
        
        # Description
        if description:
            parts.append(description)
        
        return " ".join(filter(None, parts)).lower()
    
    async def _build_normalized_search_tokens(db, product, category_id, variant, seller, description):
        """
        Build normalized search tokens for enterprise search.
        Includes unit variations, synonyms, and attribute values.
        """
        from services.search_normalization_service import search_normalizer
        
        # Gather all listing data
        listing_data = {
            "productName": product.get("name", ""),
            "description": description or "",
            "searchableAttributes": variant.get("attributes", {}),
            "attributeLabels": {},
        }
        
        # Get attribute labels
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            try:
                template_id = template_ids[0] if isinstance(template_ids[0], ObjectId) else ObjectId(str(template_ids[0]))
                template = await db.specTemplates.find_one({"_id": template_id})
                if template and template.get("fields"):
                    for field in template["fields"]:
                        key = field.get("key")
                        label = field.get("label")
                        if key and label:
                            listing_data["attributeLabels"][key] = label
            except Exception:
                pass
        
        # Add category name
        if category_id:
            category = await db.categories.find_one({"_id": category_id})
            if category:
                listing_data["categoryName"] = category.get("name", "")
        
        # Add seller location
        if seller:
            profile = seller.get("profile", {})
            listing_data["sellerCity"] = profile.get("city", "")
            listing_data["sellerState"] = profile.get("state", "")
        
        # Generate normalized tokens
        tokens = search_normalizer.generate_search_tokens(listing_data)
        
        return tokens
    
    async def _get_attribute_labels(db, product):
        """Get attribute labels from spec template."""
        labels = {}
        template_ids = product.get("specTemplateIds", [])
        if template_ids:
            template_id = template_ids[0] if isinstance(template_ids[0], ObjectId) else ObjectId(str(template_ids[0]))
            template = await db.specTemplates.find_one({"_id": template_id})
            if template and template.get("fields"):
                for field in template["fields"]:
                    key = field.get("key")
                    label = field.get("label")
                    unit = field.get("unit")
                    if key and label:
                        labels[key] = f"{label}" + (f" ({unit})" if unit else "")
        return labels
    
    async def get_product_with_template(product_id: str):
        """
        Get product with its specTemplate.
        
        ENTERPRISE RULE: Uses specTemplateIds (array) - NOT singular specTemplateId.
        Falls back to specTemplateId only for legacy data compatibility.
        """
        try:
            product = await db.products.find_one({"_id": ObjectId(product_id)})
        except Exception:
            return None, None
        
        if not product:
            return None, None
        
        template = None
        
        # ENTERPRISE: Use specTemplateIds (array) as primary source
        template_ids = product.get("specTemplateIds", [])
        
        if template_ids and len(template_ids) > 0:
            template_id = template_ids[0]
            
            # Handle string or ObjectId
            if isinstance(template_id, str):
                template_id = ObjectId(template_id)
            
            try:
                template = await db.specTemplates.find_one({"_id": template_id})
            except Exception:
                pass
        
        # LEGACY FALLBACK: Check singular specTemplateId if array is empty
        # TODO: Remove this fallback after full migration
        if not template:
            legacy_id = product.get("specTemplateId")
            if legacy_id:
                try:
                    if isinstance(legacy_id, str):
                        legacy_id = ObjectId(legacy_id)
                    template = await db.specTemplates.find_one({"_id": legacy_id})
                    logger.warning(f"Product {product_id} using legacy specTemplateId - should migrate to specTemplateIds")
                except Exception:
                    pass
        
        return product, template
    
    def _get_seller_status_message(status: dict, gst: dict) -> str:
        if not status["isSeller"]:
            return "Register as a seller to access this section."
        if not gst.get("verified", False):
            gst_status = gst.get("status", "pending")
            if gst_status == "pending":
                return "GST verification in progress. You can create drafts but cannot publish."
            elif gst_status == "rejected":
                return "GST verification rejected. Please re-submit valid GST documents."
            else:
                return "GST verification required to publish products."
        return "You are a verified seller."
    
    # ==================== LISTING ENDPOINTS ====================
    
    @router.post("/listings")
    async def create_listing(
        data: ListingCreate,
        seller: dict = Depends(require_verified_seller)
    ):
        """Create a new seller listing"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            product_oid = ObjectId(data.productId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid productId format")
        
        product, template = await get_product_with_template(data.productId)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if not product.get("isActive", True):
            raise HTTPException(status_code=400, detail="Product is not active")
        
        template_ids = product.get("specTemplateIds", [])
        if not template_ids:
            raise HTTPException(status_code=400, detail="Product has no specTemplateIds")
        
        try:
            variant = await variant_service.get_or_create_variant(
                product_id=data.productId,
                attributes=data.attributes
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        variant_oid = ObjectId(variant["_id"])
        category_oid = product.get("categoryId")
        if isinstance(category_oid, str):
            category_oid = ObjectId(category_oid)
        
        existing = await db.sellerListings.find_one({
            "sellerId": seller_oid,
            "variantId": variant_oid
        })
        
        if existing:
            raise HTTPException(status_code=409, detail="Listing already exists for this variant")
        
        # ============================================================
        # ENTERPRISE GUARD: Strict Write-Time Validation
        # ============================================================
        # Get searchableAttributes ONLY from variant - NO FALLBACK to raw data.attributes
        # This ensures attributes flow through the proper variant creation flow
        searchable_attributes = variant.get("attributes", {})
        
        # STRICT: If variant has no attributes, reject the listing
        if not searchable_attributes or len(searchable_attributes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Variant has no technical specifications. Please provide attributes when creating the variant."
            )
        
        # ENTERPRISE GUARD: Validate listing data before insert
        try:
            validated = enterprise_guard.validate_listing_for_create(
                images=data.images,
                searchable_attributes=searchable_attributes,
                pricing_tiers=[{"minQty": t.minQty, "maxQty": t.maxQty, "pricePerUnit": t.pricePerUnit} for t in data.pricingTiers],
                moq=data.moq,
                stock=data.stock,
                videos=data.videos  # Optional product demo videos
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Enterprise guard validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")
        
        # ============================================================
        # MANUFACTURER VALIDATION (Phase 2 - Dropdown Strategy)
        # ============================================================
        manufacturer_id = None
        manufacturer_name = None
        
        if data.manufacturerId:
            try:
                manufacturer = await db.manufacturers.find_one({
                    "_id": ObjectId(data.manufacturerId),
                    "status": "approved",
                    "isActive": {"$ne": False}
                })
                if not manufacturer:
                    raise HTTPException(
                        status_code=400, 
                        detail="Invalid manufacturer. Please select from the dropdown."
                    )
                manufacturer_id = ObjectId(data.manufacturerId)
                manufacturer_name = manufacturer.get("brandName")  # Store for display (no join needed)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid manufacturerId format")
        
        # ============================================================
        # GET SELLER LOCATION + GEO COORDINATES (for geo search)
        # ============================================================
        seller_profile = seller.get("profile", {})
        seller_city = seller_profile.get("city")
        seller_state = seller_profile.get("state")
        seller_pincode = seller_profile.get("pincode")
        seller_rating = seller.get("rating", 0)
        
        # Get coordinates from seller profile or geocode from city
        seller_coordinates = None
        if seller_profile.get("coordinates"):
            # Use pre-stored coordinates from seller profile
            seller_coordinates = seller_profile["coordinates"]
        elif seller_city:
            # Geocode from city name
            from services.pincode_geocode_service import geocode_service
            location = geocode_service.get_coordinates_by_city(seller_city)
            if location:
                seller_coordinates = {
                    "type": "Point",
                    "coordinates": [location.longitude, location.latitude]  # GeoJSON: [lng, lat]
                }
        
        # Compute minPrice from MINIMUM of all pricing tiers (NOT first tier)
        min_price = min(t.pricePerUnit for t in data.pricingTiers) if data.pricingTiers else 0
        
        # Compute inStock
        in_stock = validated["stock"] > 0
        
        now = datetime.now(timezone.utc)
        
        listing_doc = {
            "_id": ObjectId(),
            "sellerId": seller_oid,
            "productId": product_oid,
            "variantId": variant_oid,
            "categoryId": category_oid,
            "status": "draft",
            "isActive": False,
            "sellerRole": data.sellerRole,
            "description": data.description,
            "images": validated["images"],  # ENTERPRISE: Validated images
            "videos": validated.get("videos", []),  # Product demo videos (max 2, 30s each)
            "moq": validated["moq"],  # ENTERPRISE: Validated MOQ
            "stock": validated["stock"],  # ENTERPRISE: Validated stock
            "maxCapacity": data.maxCapacity,
            "leadTime": data.leadTime,
            "currency": data.currency.upper(),
            "pricingTiers": validated["pricingTiers"],  # ENTERPRISE: Validated pricing
            "datasheetUrl": data.datasheetUrl,
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": None,
            "priceHistory": [],
            # ENTERPRISE: Denormalized search fields (VALIDATED)
            "searchableAttributes": validated["searchableAttributes"],
            "searchableText": await _build_searchable_text(db, product, category_oid, variant, seller, data.description),
            "attributeLabels": await _get_attribute_labels(db, product),
            # ENTERPRISE SEARCH: Normalized tokens for intelligent search
            "normalizedSearchTokens": await _build_normalized_search_tokens(db, product, category_oid, variant, seller, data.description),
            # ============================================================
            # PHASE 2 SEARCH OPTIMIZATION FIELDS
            # ============================================================
            # Manufacturer (from dropdown - no free text)
            "manufacturerId": manufacturer_id,
            "manufacturerName": manufacturer_name,
            # Seller location (denormalized for search)
            "city": seller_city,
            "state": seller_state,
            "pincode": seller_pincode,
            "sellerRating": seller_rating,
            # GEO SEARCH: GeoJSON Point for 2dsphere queries
            "coordinates": seller_coordinates,
            # Search-optimized computed fields
            "minPrice": min_price,
            "inStock": in_stock,
            # Monetization-ready fields
            "sellerTier": "free",  # free | silver | gold
            "boostScore": 0,  # Dynamic boost for ranking
            "isPremiumSeller": False,
        }
        
        await db.sellerListings.insert_one(listing_doc)
        logger.info(f"Seller {seller['email']} created listing for variant: {variant['_id']} [ENTERPRISE VALIDATED]")
        
        return success_response({
            "message": "Listing created successfully",
            "listing": listing_doc,
            "variant": variant
        })
    
    @router.get("/listings")
    async def get_my_listings(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None),
        categoryId: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        """Get all listings for the current seller"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        query = {"sellerId": seller_oid}
        if status:
            query["status"] = status
        if categoryId:
            try:
                query["categoryId"] = ObjectId(categoryId)
            except Exception:
                pass
        
        skip = (page - 1) * limit
        total = await db.sellerListings.count_documents(query)
        listings = await db.sellerListings.find(query).sort("updatedAt", -1).skip(skip).limit(limit).to_list(limit)
        
        enriched = []
        for listing in listings:
            item = dict(listing)
            if listing.get("variantId"):
                variant = await db.productVariants.find_one({"_id": listing["variantId"]})
                if variant:
                    item["attributes"] = variant.get("attributes", {})
            if listing.get("productId"):
                product = await db.products.find_one({"_id": listing["productId"]})
                if product:
                    item["productName"] = product.get("name")
            # Add category name lookup
            if listing.get("categoryId"):
                category = await db.categories.find_one({"_id": listing["categoryId"]})
                if category:
                    item["categoryName"] = category.get("name")
            enriched.append(item)
        
        return success_response({
            "listings": enriched,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1
        })
    
    @router.get("/listings/{listing_id}")
    async def get_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Get a specific listing with full details"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        result = dict(listing)
        spec_template = None
        
        if listing.get("variantId"):
            try:
                variant_id = listing["variantId"] if isinstance(listing["variantId"], ObjectId) else ObjectId(listing["variantId"])
                variant = await db.productVariants.find_one({"_id": variant_id})
                if variant:
                    result["variant"] = variant
                    result["attributes"] = variant.get("attributes", {})
                    template_versions = variant.get("templateVersions", [])
                    if template_versions:
                        template_info = template_versions[0]
                        template_id = template_info.get("templateId")
                        if template_id:
                            template = await db.specTemplates.find_one({
                                "_id": template_id if isinstance(template_id, ObjectId) else ObjectId(template_id)
                            })
                            if template:
                                spec_template = {
                                    "templateId": template["_id"],
                                    "name": template.get("name", ""),
                                    "version": template.get("version", 1),
                                    "fields": template.get("fields", []),
                                    "description": template.get("description", "")
                                }
            except Exception as e:
                logger.warning(f"Error fetching variant/template: {e}")
        
        if listing.get("productId"):
            try:
                product_id = listing["productId"] if isinstance(listing["productId"], ObjectId) else ObjectId(listing["productId"])
                product = await db.products.find_one({"_id": product_id})
                if product:
                    result["product"] = {
                        "_id": product["_id"],
                        "productName": product.get("name"),
                        "categoryId": product.get("categoryId"),
                        "specTemplateIds": product.get("specTemplateIds", [])
                    }
                    if not spec_template and product.get("specTemplateIds"):
                        template_id = product["specTemplateIds"][0]
                        template = await db.specTemplates.find_one({
                            "_id": template_id if isinstance(template_id, ObjectId) else ObjectId(template_id)
                        })
                        if template:
                            spec_template = {
                                "templateId": template["_id"],
                                "name": template.get("name", ""),
                                "version": template.get("version", 1),
                                "fields": template.get("fields", []),
                                "description": template.get("description", "")
                            }
            except Exception as e:
                logger.warning(f"Error fetching product: {e}")
        
        return success_response({"listing": result, "specTemplate": spec_template})
    
    @router.patch("/listings/{listing_id}")
    async def update_listing(
        listing_id: str,
        data: ListingUpdate,
        seller: dict = Depends(require_verified_seller)
    ):
        """Update a listing"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        update_data = {"updatedAt": now}
        variant_changed = False
        new_variant = None
        new_searchable_attrs = None
        
        if data.attributes is not None:
            current_variant = None
            if listing.get("variantId"):
                current_variant = await db.productVariants.find_one({"_id": listing["variantId"]})
            current_attrs = current_variant.get("attributes", {}) if current_variant else {}
            new_attrs = variant_service._normalize_attributes(data.attributes)
            
            if new_attrs != current_attrs:
                product_id = str(listing["productId"])
                product, template = await get_product_with_template(product_id)
                if not product:
                    raise HTTPException(status_code=400, detail="Product not found")
                template_ids = product.get("specTemplateIds", [])
                if not template_ids:
                    raise HTTPException(status_code=400, detail="Cannot change attributes: no specTemplateIds")
                try:
                    new_variant = await variant_service.get_or_create_variant(
                        product_id=product_id,
                        attributes=data.attributes
                    )
                    new_variant_oid = ObjectId(new_variant["_id"])
                    update_data["variantId"] = new_variant_oid
                    variant_changed = True
                    # ENTERPRISE: Update searchableAttributes when variant changes
                    new_searchable_attrs = new_variant.get("attributes", {})
                    
                    # STRICT: Reject empty attributes in updated variant
                    if not new_searchable_attrs or len(new_searchable_attrs) == 0:
                        raise HTTPException(
                            status_code=400,
                            detail="Updated variant has no technical specifications"
                        )
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
        
        if data.description is not None:
            update_data["description"] = data.description
        if data.images is not None:
            update_data["images"] = data.images[:5]
        if data.datasheetUrl is not None:
            update_data["datasheetUrl"] = data.datasheetUrl
        if data.moq is not None:
            update_data["moq"] = data.moq
        if data.stock is not None:
            update_data["stock"] = data.stock
        if data.maxCapacity is not None:
            update_data["maxCapacity"] = data.maxCapacity
        if data.leadTime is not None:
            update_data["leadTime"] = data.leadTime
        
        # ============================================================
        # ENTERPRISE GUARD: Validate update data
        # ============================================================
        try:
            validated = enterprise_guard.validate_listing_for_update(
                images=data.images,
                searchable_attributes=new_searchable_attrs,
                pricing_tiers=None,  # Pricing is handled separately
                moq=data.moq,
                stock=data.stock,
                videos=data.videos  # Optional product demo videos
            )
            # Apply validated values
            for key, value in validated.items():
                if key == "searchableAttributes" and value:
                    update_data["searchableAttributes"] = value
                elif key in ["images", "videos", "moq", "stock"]:
                    update_data[key] = value
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Enterprise guard update validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")
        
        if data.status is not None:
            if data.status == "active":
                seller_status = get_seller_status(seller)
                if not seller_status["canPublish"]:
                    gst = seller.get("gst", {})
                    raise HTTPException(status_code=403, detail=f"GST verification required. Status: {gst.get('status', 'pending')}")
                pricing_tiers = listing.get("pricingTiers", [])
                moq = listing.get("moq") or data.moq
                if not pricing_tiers:
                    raise HTTPException(status_code=400, detail="Cannot activate without pricing tiers")
                if not moq:
                    raise HTTPException(status_code=400, detail="Cannot activate without MOQ")
                
                # ENTERPRISE GUARD: Additional checks for activation
                current_images = update_data.get("images") or listing.get("images", [])
                current_attrs = update_data.get("searchableAttributes") or listing.get("searchableAttributes", {})
                
                if not current_images:
                    raise HTTPException(status_code=400, detail="Cannot activate listing without images")
                if not current_attrs:
                    raise HTTPException(status_code=400, detail="Cannot activate listing without technical specifications")
                
                if not listing.get("publishedAt"):
                    update_data["publishedAt"] = now
            update_data["status"] = data.status
            update_data["isActive"] = data.status == "active"
        
        await db.sellerListings.update_one({"_id": listing_oid}, {"$set": update_data})
        updated = await db.sellerListings.find_one({"_id": listing_oid})
        
        response = {"message": "Listing updated", "listing": updated}
        if variant_changed and new_variant:
            response["variantChanged"] = True
            response["newVariant"] = new_variant
        
        return success_response(response)
    
    @router.patch("/listings/{listing_id}/pricing")
    async def update_pricing(
        listing_id: str,
        data: PricingUpdate,
        seller: dict = Depends(require_verified_seller)
    ):
        """Update pricing tiers only"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        new_tiers = [{"minQty": t.minQty, "maxQty": t.maxQty, "pricePerUnit": t.pricePerUnit} for t in data.pricingTiers]
        old_tiers = listing.get("pricingTiers", [])
        
        if old_tiers != new_tiers:
            await db.sellerListings.update_one(
                {"_id": listing_oid},
                {"$push": {"priceHistory": {"timestamp": now, "oldTiers": old_tiers, "action": "pricingUpdate"}}}
            )
        
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {"pricingTiers": new_tiers, "updatedAt": now}}
        )
        
        return {"message": "Pricing updated", "pricingTiers": new_tiers, "lastUpdated": now.isoformat()}
    
    @router.post("/listings/{listing_id}/publish")
    async def publish_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Publish a draft listing"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        seller_status = get_seller_status(seller)
        if not seller_status["canPublish"]:
            gst = seller.get("gst", {})
            raise HTTPException(status_code=403, detail=f"GST verification required. Status: {gst.get('status', 'pending')}")
        
        account_status = seller.get("sellerStatus", "active")
        if account_status == "banned":
            raise HTTPException(status_code=403, detail="Seller account is banned")
        if account_status == "suspended":
            raise HTTPException(status_code=403, detail="Seller account is suspended")
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        if listing.get("status") == "active":
            return {"message": "Listing already published", "status": "active"}
        
        validate_listing_completeness(listing)
        
        now = datetime.now(timezone.utc)
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {"status": "active", "isActive": True, "publishedAt": now, "updatedAt": now}}
        )
        
        # Update activeSellerCities count
        try:
            location_service = create_seller_location_service(db)
            profile = seller.get("profile", {})
            city = profile.get("city")
            state = profile.get("state")
            if city and state:
                await location_service.update_seller_city(city, state, increment=1)
        except Exception as e:
            logger.warning(f"Failed to update seller city count: {e}")
        
        return {"message": "Listing published", "status": "active", "publishedAt": now}
    
    @router.get("/listings/{listing_id}/validate")
    async def validate_listing_for_publish(
        listing_id: str,
        seller: dict = Depends(require_auth)
    ):
        """Pre-publish validation check"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        required_fields = {
            "pricingTiers": {"check": lambda v: v and len(v) > 0, "message": "At least one pricing tier required"},
            "moq": {"check": lambda v: v and v > 0, "message": "MOQ must be greater than 0"},
            "stock": {"check": lambda v: v and v > 0, "message": "Stock must be greater than 0"},
            "maxCapacity": {"check": lambda v: v and v > 0, "message": "Max capacity must be greater than 0"},
            "images": {"check": lambda v: v and len(v) > 0, "message": "At least one image required"},
            "variantId": {"check": lambda v: v is not None, "message": "Product variant must be linked"}
        }
        
        missing_fields = []
        field_errors = {}
        for field, config in required_fields.items():
            value = listing.get(field)
            if not config["check"](value):
                missing_fields.append(field)
                field_errors[field] = config["message"]
        
        is_complete = len(missing_fields) == 0
        seller_status = get_seller_status(seller)
        gst = seller.get("gst", {})
        gst_verified = seller_status["gstVerified"]
        account_status = seller.get("sellerStatus", "active")
        account_active = account_status not in ["banned", "suspended"]
        can_publish = is_complete and gst_verified and account_active
        
        return {
            "listingId": listing_id,
            "isComplete": is_complete,
            "canPublish": can_publish,
            "currentStatus": listing.get("status", "draft"),
            "missingFields": missing_fields,
            "fieldErrors": field_errors,
            "gstVerified": gst_verified,
            "gstStatus": gst.get("status", "none"),
            "accountStatus": account_status
        }
    
    @router.post("/listings/{listing_id}/pause")
    async def pause_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Pause a listing"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {"status": "paused", "isActive": False, "updatedAt": now}}
        )
        
        return {"message": "Listing paused", "status": "paused"}
    
    @router.delete("/listings/{listing_id}")
    async def delete_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller),
        hardDelete: bool = Query(False)
    ):
        """Archive or permanently delete a listing"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({"_id": listing_oid, "sellerId": seller_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        if hardDelete:
            await db.sellerListings.delete_one({"_id": listing_oid})
            return {"message": "Listing permanently deleted"}
        else:
            now = datetime.now(timezone.utc)
            await db.sellerListings.update_one(
                {"_id": listing_oid},
                {"$set": {"status": "archived", "isActive": False, "updatedAt": now}}
            )
            return {"message": "Listing archived", "status": "archived"}
    
    # ==================== DASHBOARD & STATS ====================
    
    @router.get("/dashboard")
    async def get_seller_dashboard(
        seller: dict = Depends(require_verified_seller)
    ):
        """Get seller dashboard summary"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = await db.sellerListings.aggregate(pipeline).to_list(10)
        
        stats = {"total": 0, "draft": 0, "active": 0, "paused": 0, "archived": 0}
        for item in status_counts:
            status = item["_id"]
            if status in stats:
                stats[status] = item["count"]
            stats["total"] += item["count"]
        
        recent = await db.sellerListings.find({"sellerId": seller_oid}).sort("updatedAt", -1).limit(5).to_list(5)
        enriched_recent = []
        for listing in recent:
            item = serialize_listing(listing)
            if listing.get("productId"):
                product = await db.products.find_one({"_id": listing["productId"]})
                if product:
                    item["productName"] = product.get("name")
            enriched_recent.append(item)
        
        return {"stats": stats, "recentListings": enriched_recent}
    
    @router.get("/stats")
    async def get_seller_stats(
        seller: dict = Depends(require_verified_seller)
    ):
        """Get seller statistics"""
        from services.subscription_service import get_effective_subscription, check_and_update_monthly_usage
        
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            total_listings = await db.sellerListings.count_documents({"sellerId": seller_oid})
            published_listings = await db.sellerListings.count_documents({"sellerId": seller_oid, "status": "active"})
            total_enquiries = await db.inquiries.count_documents({"sellerId": seller_oid})
            pending_enquiries = await db.inquiries.count_documents({"sellerId": seller_oid, "status": "pending"})
            
            subscription = await get_effective_subscription(db, seller_oid)
            this_month_enquiries = await check_and_update_monthly_usage(db, seller_oid)
            
            plan = subscription["plan"]
            is_unlimited = subscription["isUnlimited"]
            inquiry_limit = subscription["limit"]
            
            return {
                "totalListings": total_listings,
                "publishedListings": published_listings,
                "totalEnquiries": total_enquiries,
                "pendingEnquiries": pending_enquiries,
                "thisMonthEnquiries": this_month_enquiries,
                "subscription": {
                    "plan": plan,
                    "isUnlimited": is_unlimited,
                    "usageDisplay": f"{this_month_enquiries} / {'Unlimited' if is_unlimited else inquiry_limit}",
                    "remaining": -1 if is_unlimited else max(0, inquiry_limit - this_month_enquiries)
                }
            }
        except Exception as e:
            logger.warning(f"Error fetching seller stats: {e}")
            return {
                "totalListings": 0,
                "publishedListings": 0,
                "totalEnquiries": 0,
                "pendingEnquiries": 0,
                "thisMonthEnquiries": 0,
                "subscription": {"plan": "free", "isUnlimited": False, "usageDisplay": "0 / 5", "remaining": 5}
            }
    
    @router.get("/subscription")
    async def get_subscription_status(
        seller: dict = Depends(require_verified_seller)
    ):
        """Get seller's subscription status"""
        from services.subscription_service import get_subscription_status_for_seller
        
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        status_data = await get_subscription_status_for_seller(db, seller_oid)
        
        status_data["upgradeInfo"] = {
            "showUpgrade": status_data.get("showUpgradeCta", False),
            "upgradeUrl": "/seller/subscription",
            "priceQuarterly": 999
        }
        
        plan = status_data["subscription"]["planName"]
        is_unlimited = status_data["subscription"]["isUnlimited"]
        status_data["benefits"] = {
            "unlimitedInquiries": is_unlimited,
            "instantApproval": is_unlimited,
            "prioritySupport": plan == "pro",
            "verifiedBadge": plan in ["trial", "pro"],
            "analyticsAccess": plan == "pro",
            "autoWhatsappUnlock": plan == "pro"
        }
        
        return status_data
    
    @router.get("/status")
    async def get_seller_status_endpoint(
        seller: dict = Depends(require_verified_seller)
    ):
        """Get seller's current status"""
        status = get_seller_status(seller)
        gst = seller.get("gst", {})
        
        return success_response({
            "isSeller": status["isSeller"],
            "gst": {
                "number": gst.get("number"),
                "status": gst.get("status"),
                "verified": gst.get("verified", False)
            },
            "permissions": {
                "canCreateDraft": status["canCreateDraft"],
                "canPublish": status["canPublish"]
            },
            "message": _get_seller_status_message(status, gst)
        })
    
    # ==================== PRODUCT VARIANTS HELPER ====================
    
    @router.get("/products/{product_id}/variants")
    async def get_product_variants(
        product_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Get all available variants for a product"""
        variants = await variant_service.get_variants_for_product(product_id)
        return {"productId": product_id, "variants": variants, "total": len(variants)}
    
    @router.get("/categories/{category_id}/spec-template")
    async def get_category_spec_template(
        category_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Get the spec template for a category"""
        try:
            category_oid = ObjectId(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        category = await db.categories.find_one({"_id": category_oid})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Try to find template - handle both ObjectId and string categoryId formats
        template = await db.specTemplates.find_one({
            "categoryId": category_oid, 
            "isActive": {"$ne": False}
        })
        
        # Fallback: try string format if ObjectId lookup failed
        if not template:
            template = await db.specTemplates.find_one({
                "categoryId": category_id,  # Try as string
                "isActive": {"$ne": False}
            })
        
        result = {"category": {"_id": str(category["_id"]), "name": category.get("name"), "settings": category.get("settings", {})}}
        
        if template:
            result["specTemplate"] = serialize_objectids(template)
        else:
            result["specTemplate"] = None
            result["note"] = "No spec template defined for this category."
        
        return result
    
    @router.get("/products/{product_id}/spec-template")
    async def get_product_spec_template(
        product_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Get ALL spec templates for a product.
        
        Products can have multiple spec templates (e.g., different valve types).
        Returns all templates so sellers can choose the appropriate one.
        """
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        product = await db.products.find_one({"_id": product_oid})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get ALL spec templates from product's specTemplateIds
        spec_template_ids = product.get("specTemplateIds", [])
        templates = []
        
        for tid in spec_template_ids:
            template_oid = ObjectId(str(tid)) if not isinstance(tid, ObjectId) else tid
            template = await db.specTemplates.find_one({
                "_id": template_oid,
                "isActive": {"$ne": False}
            })
            if template:
                templates.append(serialize_objectids(template))
        
        # Fallback to category-based lookup if no templates found from specTemplateIds
        if not templates:
            category_id = product.get("categoryId")
            if category_id:
                category_oid = ObjectId(str(category_id)) if not isinstance(category_id, ObjectId) else category_id
                # Try ObjectId format first
                template = await db.specTemplates.find_one({
                    "categoryId": category_oid,
                    "isActive": {"$ne": False}
                })
                # Fallback to string format
                if not template:
                    template = await db.specTemplates.find_one({
                        "categoryId": str(category_id),
                        "isActive": {"$ne": False}
                    })
                if template:
                    templates.append(serialize_objectids(template))
        
        result = {
            "product": {
                "_id": str(product["_id"]),
                "name": product.get("name"),
                "categoryId": str(product.get("categoryId")) if product.get("categoryId") else None,
                "specTemplateIds": [str(t) for t in spec_template_ids]
            },
            # Return ALL templates for multi-template products
            "specTemplates": templates,
            # Keep backward compatibility - first template for legacy clients
            "specTemplate": templates[0] if templates else None
        }
        
        if not templates:
            result["note"] = "No spec template found for this product."
        
        return result
    
    # ==================== INQUIRY MANAGEMENT ====================
    
    @router.get("/inquiries")
    async def get_seller_inquiries(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        """Get seller inquiries with buyer masking"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        query = {"sellerId": seller_oid}
        if status and status in ["pending", "accepted", "rejected", "reported", "new"]:
            query["status"] = status
        
        skip = (page - 1) * limit
        total = await db.inquiries.count_documents(query)
        inquiries = await db.inquiries.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        unread_count = await db.inquiries.count_documents({"sellerId": seller_oid, "status": "pending"})
        
        result = []
        for inq in inquiries:
            try:
                serialized = serialize_mongo_doc(inq)
                
                listing_id = inq.get("listingId")
                if listing_id:
                    try:
                        lid = listing_id if isinstance(listing_id, ObjectId) else ObjectId(str(listing_id))
                        listing = await db.sellerListings.find_one({"_id": lid})
                        if listing:
                            product_id = listing.get("productId")
                            if product_id:
                                pid = product_id if isinstance(product_id, ObjectId) else ObjectId(str(product_id))
                                product = await db.products.find_one({"_id": pid})
                                if product:
                                    serialized["listingName"] = product.get("name", "")
                            images = listing.get("images") or []
                            serialized["listingImage"] = images[0] if images else None
                    except Exception as e:
                        logger.warning(f"Error fetching listing {listing_id}: {e}")
                
                buyer_id = inq.get("buyerId")
                buyer_info = None
                buyer_masked = None
                
                if buyer_id:
                    try:
                        bid = buyer_id if isinstance(buyer_id, ObjectId) else ObjectId(str(buyer_id))
                        buyer = await db.users.find_one({"_id": bid})
                        if buyer:
                            buyer_profile = buyer.get("profile") or {}
                            if serialized.get("status") == "accepted":
                                buyer_info = {
                                    "name": buyer_profile.get("businessName") or buyer.get("email", "").split("@")[0],
                                    "phone": buyer_profile.get("phone"),
                                    "email": buyer.get("email"),
                                    "companyName": buyer_profile.get("businessName"),
                                    "city": buyer_profile.get("city"),
                                    "state": buyer_profile.get("state")
                                }
                            else:
                                company_name = buyer_profile.get("businessName") or ""
                                buyer_masked = {
                                    "companyInitial": company_name[0].upper() if company_name else "?",
                                    "city": buyer_profile.get("city"),
                                    "state": buyer_profile.get("state")
                                }
                    except Exception as e:
                        logger.warning(f"Error fetching buyer {buyer_id}: {e}")
                
                if not buyer_info and not buyer_masked:
                    embedded_buyer = inq.get("buyerInfo") or {}
                    if serialized.get("status") == "accepted":
                        buyer_info = embedded_buyer
                    else:
                        company_name = embedded_buyer.get("companyName") or ""
                        buyer_masked = {
                            "companyInitial": company_name[0].upper() if company_name else "?",
                            "city": embedded_buyer.get("city"),
                            "state": embedded_buyer.get("state")
                        }
                
                serialized["buyerInfo"] = buyer_info
                serialized["buyerMasked"] = buyer_masked
                serialized["buyerType"] = inq.get("buyerType")
                # Include raw material calculation data if present
                if inq.get("calculationData"):
                    serialized["calculationData"] = serialize_mongo_doc(inq.get("calculationData"))
                result.append(serialized)
            except Exception as e:
                logger.warning(f"Error processing inquiry {inq.get('_id')}: {e}")
                continue
        
        return {
            "inquiries": result,
            "total": total,
            "unreadCount": unread_count,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit)
        }
    
    @router.post("/inquiries/{inquiry_id}/accept")
    async def accept_inquiry(
        inquiry_id: str,
        data: InquiryAccept,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Accept an inquiry with a quote.
        
        SSOT ARCHITECTURE (True Single Source of Truth):
        1. QuotationService creates quote in 'quotes' collection (ONLY source)
        2. QuotationService generates WhatsApp message (ONLY source)
        3. Inquiry only stores status + reference to quote
        4. Backend returns whatsappLink
        5. Frontend only opens returned link (no message building)
        6. No hardcoded fallbacks for seller/business names
        """
        from services.subscription_service import can_accept_inquiry as check_can_accept, increment_enquiry_usage
        from services.seller_governance_service import SellerGovernanceService
        from services.quotation_service import get_quotation_service, QuoteCreateRequest
        import urllib.parse
        
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        # ============================================================
        # STEP 1: PRICE VALIDATION - Prevent ₹0 quotes
        # ============================================================
        if data.quotedPrice <= 0:
            raise HTTPException(
                status_code=400,
                detail="Quoted price must be greater than ₹0. Please enter a valid price."
            )
        
        # ============================================================
        # STEP 2: GOVERNANCE CHECK - Verify seller not suspended/banned
        # ============================================================
        governance_service = SellerGovernanceService(db)
        governance_result = await governance_service.can_accept_lead(seller_oid)
        if not governance_result["canAccept"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": governance_result["reason"],
                    "message": governance_result.get("message", "Cannot accept leads"),
                    "status": governance_result.get("status", "blocked")
                }
            )
        
        # ============================================================
        # STEP 3: SUBSCRIPTION CHECK - Verify lead limit not exceeded
        # ============================================================
        can_accept_result = await check_can_accept(db, seller_oid)
        if not can_accept_result["canAccept"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": can_accept_result["reason"],
                    "currentCount": can_accept_result["usage"]["used"],
                    "limit": can_accept_result["usage"]["limit"],
                    "resetsInDays": can_accept_result.get("resetsInDays", 0),
                    "notification": can_accept_result.get("notification"),
                    "upgradeUrl": can_accept_result.get("upgradeUrl", "/seller/subscription")
                }
            )
        
        # ============================================================
        # STEP 4: FETCH INQUIRY
        # ============================================================
        try:
            inquiry = await db.inquiries.find_one({"_id": ObjectId(inquiry_id), "sellerId": seller_oid})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid inquiry ID")
        
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        
        if inquiry.get("status") not in ["pending", "new"]:
            raise HTTPException(status_code=400, detail=f"Cannot accept inquiry with status: {inquiry.get('status')}")
        
        now = datetime.now(timezone.utc)
        
        # ============================================================
        # STEP 5: UPDATE INQUIRY STATUS ONLY (No quote data here - SSOT)
        # ============================================================
        # Quote will be stored ONLY in quotes collection via QuotationService
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {
                "status": "accepted",
                "acceptedAt": now,
                "updatedAt": now
            }}
        )
        
        # Update subscription usage
        subscription = can_accept_result["subscription"]
        used_count = can_accept_result["usage"]["used"]
        
        if not subscription["isUnlimited"]:
            used_count = await increment_enquiry_usage(db, seller_oid)
        
        # ============================================================
        # STEP 6: CREATE QUOTE VIA QUOTATION SERVICE (SSOT)
        # ============================================================
        quotation_service = await get_quotation_service(db)
        
        try:
            quote_result = await quotation_service.create_quote(
                seller_id=seller_oid,
                request=QuoteCreateRequest(
                    inquiryId=inquiry_id,
                    unitPrice=data.quotedPrice,
                    moq=data.moq or 1,
                    leadTimeDays=data.leadTimeDays or 1,
                    validityDays=data.validityDays
                )
            )
        except ValueError as e:
            # Rollback inquiry status if quote creation fails
            await db.inquiries.update_one(
                {"_id": ObjectId(inquiry_id)},
                {"$set": {"status": "pending", "acceptedAt": None, "updatedAt": now}}
            )
            raise HTTPException(status_code=400, detail=str(e))
        
        # Update inquiry with quote reference
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {"quoteId": quote_result["quote"].get("quoteId")}}
        )
        
        # ============================================================
        # STEP 7: GENERATE WHATSAPP PREVIEW (SSOT - QuotationService only)
        # ============================================================
        preview = quotation_service.generate_whatsapp_preview(
            quote=quote_result["quote"],
            base_url="https://udyogconnect.in"
        )
        
        # ============================================================
        # STEP 8: BUILD WHATSAPP LINK
        # ============================================================
        # Get buyer phone from quote_result (already fetched by QuotationService)
        buyer_phone = quote_result["quote"].get("buyerPhone", "")
        buyer_name = quote_result["quote"].get("buyerName", "")
        buyer_company = quote_result["quote"].get("buyerCompany", "")
        seller_business = quote_result["quote"].get("sellerName", "")
        
        # Fallback: fetch buyer info directly if not in quote
        if not buyer_phone:
            buyer_id = inquiry.get("buyerId")
            if buyer_id:
                try:
                    bid = buyer_id if isinstance(buyer_id, ObjectId) else ObjectId(str(buyer_id))
                    buyer = await db.users.find_one({"_id": bid})
                    if buyer:
                        buyer_profile = buyer.get("profile") or {}
                        buyer_name = buyer_name or buyer_profile.get("name") or buyer_profile.get("businessName") or ""
                        buyer_phone = buyer_profile.get("phone") or ""
                        buyer_company = buyer_company or buyer_profile.get("businessName") or ""
                except Exception as e:
                    logger.warning(f"Error fetching buyer phone: {e}")
            
            # Final fallback to embedded buyer info
            if not buyer_phone:
                embedded_buyer = inquiry.get("buyerInfo") or {}
                buyer_phone = embedded_buyer.get("phone") or ""
                buyer_name = buyer_name or embedded_buyer.get("name") or embedded_buyer.get("companyName") or ""
                buyer_company = buyer_company or embedded_buyer.get("companyName") or ""
        
        # Get buyer email
        buyer_email = ""
        buyer_id = inquiry.get("buyerId")
        if buyer_id:
            try:
                bid = buyer_id if isinstance(buyer_id, ObjectId) else ObjectId(str(buyer_id))
                buyer = await db.users.find_one({"_id": bid})
                if buyer:
                    buyer_email = buyer.get("email") or ""
            except Exception:
                pass
        if not buyer_email:
            embedded_buyer = inquiry.get("buyerInfo") or {}
            buyer_email = embedded_buyer.get("email") or ""
        
        # Build WhatsApp link with message from preview
        whatsapp_link = None
        if buyer_phone:
            clean_phone = "".join(filter(str.isdigit, buyer_phone))
            if clean_phone and len(clean_phone) >= 10:
                if not clean_phone.startswith("91"):
                    clean_phone = "91" + clean_phone
                encoded_message = urllib.parse.quote(preview["message"])
                whatsapp_link = f"https://wa.me/{clean_phone}?text={encoded_message}"
        
        # ============================================================
        # STEP 9: RETURN RESPONSE
        # ============================================================
        limit = subscription["limit"]
        remaining = -1 if subscription["isUnlimited"] else max(0, limit - used_count)
        
        return {
            "success": True,
            "message": "Inquiry accepted successfully",
            "inquiryId": inquiry_id,
            "whatsappLink": whatsapp_link,  # SSOT: Frontend uses this link directly
            "buyerContact": {
                "name": buyer_name or "Customer",
                "phone": buyer_phone,
                "email": buyer_email,
                "company": buyer_company
            },
            "sellerContact": {
                "businessName": seller_business  # From QuotationService (DB lookup)
            },
            "quote": quote_result["quote"],  # SSOT: Return quote from QuotationService
            "subscriptionUsage": {
                "used": used_count,
                "limit": limit,
                "remaining": remaining,
                "isUnlimited": subscription["isUnlimited"]
            }
        }
    
    @router.post("/inquiries/{inquiry_id}/reject")
    async def reject_inquiry(
        inquiry_id: str,
        data: InquiryReject,
        seller: dict = Depends(require_verified_seller)
    ):
        """Reject an inquiry"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            inquiry = await db.inquiries.find_one({"_id": ObjectId(inquiry_id), "sellerId": seller_oid})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid inquiry ID")
        
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        
        if inquiry.get("status") not in ["pending", "new"]:
            raise HTTPException(status_code=400, detail=f"Cannot reject inquiry with status: {inquiry.get('status')}")
        
        now = datetime.now(timezone.utc)
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {
                "status": "rejected",
                "rejection": {"reason": data.reason, "note": data.note, "rejectedAt": now},
                "updatedAt": now
            }}
        )
        
        return {"message": "Inquiry rejected", "inquiryId": inquiry_id, "reason": data.reason}
    
    @router.post("/inquiries/{inquiry_id}/report")
    async def report_inquiry(
        inquiry_id: str,
        data: InquiryReport,
        seller: dict = Depends(require_verified_seller)
    ):
        """Report a problematic inquiry"""
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        seller_id_str = str(seller_oid)
        
        try:
            inquiry = await db.inquiries.find_one({"_id": ObjectId(inquiry_id), "sellerId": seller_oid})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid inquiry ID")
        
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        
        now = datetime.now(timezone.utc)
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {
                "status": "reported",
                "report": {"type": data.reportType, "details": data.details, "reportedAt": now, "reportedBy": seller_id_str},
                "updatedAt": now
            }}
        )
        
        await db.inquiryReports.insert_one({
            "inquiryId": inquiry_id,
            "sellerId": seller_id_str,
            "buyerId": inquiry.get("buyerId"),
            "reportType": data.reportType,
            "details": data.details,
            "status": "pendingReview",
            "createdAt": now
        })
        
        return {"message": "Inquiry reported", "inquiryId": inquiry_id, "reportType": data.reportType}
    
    return router
