"""
MIDCONNECT FINAL MARKETPLACE ARCHITECTURE
==========================================
4-Layer Model with strict camelCase:

Category → SpecTemplate (SSOT) → Product → ProductVariant → SellerListing

COLLECTIONS (STRICT - NO LEGACY):
1. specTemplates - Structure SSOT (admin controlled)
2. products - Admin catalog (links to specTemplateId)
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
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import logging

logger = logging.getLogger("b2b_seller")

# ==================== PYDANTIC MODELS (FINAL ARCHITECTURE) ====================

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
    """
    Create a new seller listing - FINAL ARCHITECTURE
    
    Seller provides productId and attributes.
    Backend creates/reuses variant automatically.
    Listing stores variantId (NOT specifications).
    """
    productId: str = Field(..., description="Reference to products collection")
    attributes: Dict[str, Any] = Field(..., description="Attribute values matching specTemplate")
    
    # Commercial data (seller controls)
    sellerRole: str = Field(..., description="distributor, manufacturer, trader, dealer")
    description: Optional[str] = Field(None, max_length=2000)
    images: List[str] = Field(default_factory=list, max_length=5)
    
    # Availability - FLAT fields
    moq: int = Field(default=1, ge=1, description="Minimum Order Quantity")
    stock: int = Field(default=0, ge=0)
    maxCapacity: Optional[int] = Field(None, ge=1)
    leadTime: Optional[int] = Field(None, ge=0, description="Days to fulfill")
    
    # Pricing - tier based
    currency: str = Field(default="INR", max_length=3)
    pricingTiers: List[PricingTier] = Field(..., min_length=1, max_length=10)
    
    # Optional
    datasheetUrl: Optional[str] = None


class ListingUpdate(BaseModel):
    """Update an existing listing - commercial data and attributes"""
    description: Optional[str] = Field(None, max_length=2000)
    images: Optional[List[str]] = Field(None, max_length=5)
    datasheetUrl: Optional[str] = None
    status: Optional[Literal["draft", "active", "paused", "archived"]] = None
    
    # Availability - FLAT fields
    moq: Optional[int] = Field(None, ge=1)
    stock: Optional[int] = Field(None, ge=0)
    maxCapacity: Optional[int] = Field(None, ge=1)
    leadTime: Optional[int] = Field(None, ge=0)
    
    # Attributes - creates new variant if changed
    attributes: Optional[Dict[str, Any]] = Field(None, description="Attribute values - creates new variant if changed")


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


# ==================== INQUIRY MODELS ====================

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


# ==================== ROUTER SETUP ====================

def create_seller_router(db, require_auth, require_verified_seller, require_gst_verified_seller=None):
    """
    Create seller product management router.
    FINAL ARCHITECTURE: 4-layer model with variantId
    STRICT: No legacy collections, no snake_case
    
    PHASE 4 - SELLER PRODUCT PERMISSION CONTROL:
    - Not seller -> 403
    - Seller but GST pending -> Allow draft, block publish
    - Seller GST verified -> Allow all
    """
    router = APIRouter(prefix="/seller", tags=["Seller Products"])
    
    # Import variant service
    from services.product_variant_service import ProductVariantService
    variant_service = ProductVariantService(db)
    
    # ==================== PERMISSION HELPERS ====================
    
    def check_seller_role(user: dict) -> bool:
        """PHASE 3: Check if user has seller role"""
        roles = user.get("roles", [])
        return "seller" in roles
    
    def check_gst_verified(user: dict) -> bool:
        """PHASE 3: Check if seller GST is verified"""
        gst = user.get("gst", {})
        return gst.get("verified", False)
    
    def get_seller_status(user: dict) -> dict:
        """
        PHASE 3 - SELLER STATE DERIVED (NO sellerStatus FIELD):
        Returns computed seller state from roles and gst fields.
        """
        roles = user.get("roles", [])
        gst = user.get("gst", {})
        
        is_seller = "seller" in roles
        is_verified = gst.get("verified", False)
        is_pending = gst.get("status") == "pending"
        
        return {
            "isSeller": is_seller,
            "gstVerified": is_verified,
            "gstPending": is_pending,
            "canCreateDraft": is_seller,  # Sellers can create drafts
            "canPublish": is_seller and is_verified  # Only verified sellers can publish
        }
    
    def validate_listing_completeness(listing: dict) -> None:
        """
        ENTERPRISE GRADE: Server-side validation before publishing.
        
        Rules:
        - Listings may be saved as draft with incomplete data
        - Listings MUST NOT be published if mandatory fields are missing
        - Returns HTTP 400 with detailed missing fields if incomplete
        
        Required fields for publishing:
        - pricingTiers (must have at least one tier)
        - moq (minimum order quantity, must be > 0)
        - stock (must be > 0)
        - maxCapacity (must be > 0)
        - images (at least 1 image)
        - variantId (must have product variant linked)
        """
        required_fields = {
            "pricingTiers": {
                "check": lambda v: v and len(v) > 0,
                "message": "At least one pricing tier required"
            },
            "moq": {
                "check": lambda v: v and v > 0,
                "message": "MOQ (Minimum Order Quantity) must be greater than 0"
            },
            "stock": {
                "check": lambda v: v and v > 0,
                "message": "Stock quantity must be greater than 0"
            },
            "maxCapacity": {
                "check": lambda v: v and v > 0,
                "message": "Maximum capacity must be greater than 0"
            },
            "images": {
                "check": lambda v: v and len(v) > 0,
                "message": "At least one product image required"
            },
            "variantId": {
                "check": lambda v: v is not None,
                "message": "Product variant must be linked"
            }
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
                    "message": f"Please complete the following fields before publishing: {', '.join(missing_fields)}"
                }
            )
    
    # ==================== HELPER FUNCTIONS ====================
    
    def serialize_mongo_doc(data):
        """
        ENTERPRISE STANDARD: Full MongoDB serialization.
        Handles ALL BSON types safely:
        - ObjectId → string
        - datetime → ISO string  
        - dict → recursive serialize
        - list → recursive serialize
        - None → None
        - primitives → pass through
        
        RULE: Every API response MUST pass through this.
        """
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
        
        # Handle any other non-JSON-serializable types
        try:
            # Check if it's JSON serializable
            import json
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)
    
    def success_response(data: dict) -> dict:
        """
        ENTERPRISE STANDARD: Wrap all responses with serialization.
        Use this for EVERY endpoint return.
        """
        return serialize_mongo_doc(data)
    
    def serialize_listing(listing: dict) -> dict:
        """Serialize listing for API response - uses full serializer"""
        return serialize_mongo_doc(listing)
    
    def serialize_objectids(doc: dict) -> dict:
        """Convert all ObjectIds in a document to strings - uses full serializer"""
        return serialize_mongo_doc(doc)
    
    async def get_product_with_template(product_id: str):
        """Get product with its spec template - STRICT camelCase only"""
        try:
            product = await db.products.find_one({"_id": ObjectId(product_id)})
        except Exception:
            return None, None
        
        if not product:
            return None, None
        
        # Get spec template - STRICT: specTemplateId only
        template = None
        template_id = product.get("specTemplateId")
        
        if template_id:
            try:
                template = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
            except:
                pass
        
        return product, template
    
    # ==================== LISTING ENDPOINTS ====================
    
    @router.post("/listings")
    async def create_listing(
        data: ListingCreate,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Create a new seller listing.
        
        FINAL ARCHITECTURE FLOW:
        1. Seller selects product
        2. Seller fills attribute values
        3. Backend validates against specTemplate
        4. Backend creates/reuses productVariant
        5. Create sellerListing with variantId
        
        Listing NEVER stores specifications directly.
        """
        seller_oid = ObjectId(seller["_id"])
        
        # Validate product
        try:
            product_oid = ObjectId(data.productId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid productId format")
        
        product, template = await get_product_with_template(data.productId)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if not product.get("isActive", True):
            raise HTTPException(status_code=400, detail="Product is not active")
        
        # ENTERPRISE: Product must have specTemplateIds
        template_ids = product.get("specTemplateIds", [])
        if not template_ids:
            raise HTTPException(
                status_code=400, 
                detail="Product has no specTemplateIds. Cannot create listing without attribute structure."
            )
        
        # Create or reuse variant - ENTERPRISE: Uses product's specTemplateIds
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
        
        # Check for existing listing (seller + variant) - STRICT: sellerListings only
        existing = await db.sellerListings.find_one({
            "sellerId": seller_oid,
            "variantId": variant_oid
        })
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail="You already have a listing for this product variant. Edit your existing listing instead."
            )
        
        # Build listing document - FINAL ARCHITECTURE
        now = datetime.now(timezone.utc)
        
        pricing_tiers = []
        for tier in data.pricingTiers:
            pricing_tiers.append({
                "minQty": tier.minQty,
                "maxQty": tier.maxQty,
                "pricePerUnit": tier.pricePerUnit
            })
        
        listing_doc = {
            "_id": ObjectId(),
            # References - ALL ObjectId
            "sellerId": seller_oid,
            "productId": product_oid,
            "variantId": variant_oid,
            "categoryId": category_oid,
            
            # Status
            "status": "draft",
            "isActive": False,
            
            # Commercial data (seller controlled)
            "sellerRole": data.sellerRole,
            "description": data.description,
            "images": data.images[:5],
            
            # Availability - FLAT fields
            "moq": data.moq,
            "stock": data.stock,
            "maxCapacity": data.maxCapacity,
            "leadTime": data.leadTime,
            
            # Pricing
            "currency": data.currency.upper(),
            "pricingTiers": pricing_tiers,
            
            # Optional
            "datasheetUrl": data.datasheetUrl,
            
            # Timestamps
            "createdAt": now,
            "updatedAt": now,
            "publishedAt": None,
            
            # Audit
            "priceHistory": [],
        }
        
        # STRICT: sellerListings only
        await db.sellerListings.insert_one(listing_doc)
        
        logger.info(f"Seller {seller['email']} created listing for variant: {variant['_id']}")
        
        # ENTERPRISE STANDARD: Always serialize before return
        return success_response({
            "message": "Listing created successfully",
            "listing": listing_doc,
            "variant": variant,
            "nextStep": "Update pricing and publish when ready"
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
        seller_oid = ObjectId(seller["_id"])
        
        query = {"sellerId": seller_oid}
        if status:
            query["status"] = status
        if categoryId:
            try:
                query["categoryId"] = ObjectId(categoryId)
            except:
                pass
        
        skip = (page - 1) * limit
        
        # STRICT: sellerListings only
        total = await db.sellerListings.count_documents(query)
        
        listings = await db.sellerListings.find(query)\
            .sort("updatedAt", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        # Enrich with product and variant info
        enriched = []
        for listing in listings:
            item = dict(listing)
            
            # Get variant attributes
            if listing.get("variantId"):
                variant = await db.productVariants.find_one({"_id": listing["variantId"]})
                if variant:
                    item["attributes"] = variant.get("attributes", {})
            
            # Get product name - STRICT: products use 'name' field
            if listing.get("productId"):
                product = await db.products.find_one({"_id": listing["productId"]})
                if product:
                    item["productName"] = product.get("name")
            
            enriched.append(item)
        
        # ENTERPRISE STANDARD: Always serialize before return
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
        """
        Get a specific listing with full details including:
        - Variant attributes
        - Product info
        - Spec template schema (for dynamic form rendering)
        
        ENTERPRISE STANDARD:
        - All responses serialized via success_response()
        - Spec template fields included for dynamic UI
        """
        try:
            seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only, enforce seller ownership
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Build response - will be fully serialized at the end
        result = dict(listing)
        spec_template = None
        
        # Get variant with attributes AND extract template info
        if listing.get("variantId"):
            try:
                variant_id = listing["variantId"] if isinstance(listing["variantId"], ObjectId) else ObjectId(listing["variantId"])
                variant = await db.productVariants.find_one({"_id": variant_id})
                logger.info(f"[SPEC_TEMPLATE_DEBUG] Variant found: {variant is not None}, variantId: {variant_id}")
                
                if variant:
                    result["variant"] = variant
                    result["attributes"] = variant.get("attributes", {})
                    
                    # CRITICAL: Extract spec template from variant's templateVersions
                    template_versions = variant.get("templateVersions", [])
                    logger.info(f"[SPEC_TEMPLATE_DEBUG] templateVersions: {template_versions}")
                    
                    if template_versions:
                        template_info = template_versions[0]
                        template_id = template_info.get("templateId")
                        template_version = template_info.get("version", 1)
                        logger.info(f"[SPEC_TEMPLATE_DEBUG] Looking for template: {template_id} version {template_version}")
                        
                        if template_id:
                            # Fetch the full spec template with field definitions
                            template = await db.specTemplates.find_one({
                                "_id": template_id if isinstance(template_id, ObjectId) else ObjectId(template_id)
                            })
                            logger.info(f"[SPEC_TEMPLATE_DEBUG] Template found: {template is not None}")
                            
                            if template:
                                spec_template = {
                                    "templateId": template["_id"],
                                    "name": template.get("name", ""),
                                    "version": template.get("version", template_version),
                                    "fields": template.get("fields", []),
                                    "description": template.get("description", "")
                                }
                                logger.info(f"[SPEC_TEMPLATE_DEBUG] Template loaded: {template['_id']}, fields count: {len(template.get('fields', []))}")
            except Exception as e:
                logger.warning(f"Error fetching variant/template: {e}", exc_info=True)
        
        # Get product info - STRICT: products use 'name' field
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
                    
                    # If no template from variant, try to get from product
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
        
        # Build final response with spec template for dynamic form
        response = {
            "listing": result,
            "specTemplate": spec_template  # This enables dynamic field rendering in frontend
        }
        
        # ENTERPRISE STANDARD: Always serialize before return
        return success_response(response)
    
    @router.patch("/listings/{listing_id}")
    async def update_listing(
        listing_id: str,
        data: ListingUpdate,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Update a listing - commercial data AND attributes.
        
        FINAL ARCHITECTURE:
        - Seller CANNOT change productId
        - Seller CAN change attributes → creates NEW variant, updates variantId
        - Seller CAN update: description, images, availability, status
        
        When attributes change:
        1. Create new ProductVariant (or reuse existing with same attributes)
        2. Update listing's variantId to point to new variant
        3. The old variant remains (may be used by other listings)
        """
        seller_oid = ObjectId(seller["_id"])
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        update_data = {"updatedAt": now}
        variant_changed = False
        new_variant = None
        
        # Handle attributes change → create new variant
        if data.attributes is not None:
            # Get current variant to compare
            current_variant = None
            if listing.get("variantId"):
                current_variant = await db.productVariants.find_one({"_id": listing["variantId"]})
            
            current_attrs = current_variant.get("attributes", {}) if current_variant else {}
            
            # Normalize new attributes for comparison
            new_attrs = variant_service._normalize_attributes(data.attributes)
            
            # Check if attributes actually changed
            if new_attrs != current_attrs:
                # Get product and spec template for variant creation
                product_id = str(listing["productId"])
                product, template = await get_product_with_template(product_id)
                
                if not product:
                    raise HTTPException(status_code=400, detail="Product not found for listing")
                
                # ENTERPRISE: Product must have specTemplateIds
                template_ids = product.get("specTemplateIds", [])
                if not template_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot change attributes: product has no specTemplateIds"
                    )
                
                # Create or reuse variant with new attributes - ENTERPRISE architecture
                try:
                    new_variant = await variant_service.get_or_create_variant(
                        product_id=product_id,
                        attributes=data.attributes
                    )
                    
                    # Update variantId to point to new variant
                    new_variant_oid = ObjectId(new_variant["_id"])
                    update_data["variantId"] = new_variant_oid
                    variant_changed = True
                    
                    logger.info(f"Seller {seller['email']} changed attributes, new variant: {new_variant['_id']}")
                    
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
        
        # Build update - commercial fields
        if data.description is not None:
            update_data["description"] = data.description
        if data.images is not None:
            update_data["images"] = data.images[:5]
        if data.datasheetUrl is not None:
            update_data["datasheetUrl"] = data.datasheetUrl
        
        # FLAT availability fields
        if data.moq is not None:
            update_data["moq"] = data.moq
        if data.stock is not None:
            update_data["stock"] = data.stock
        if data.maxCapacity is not None:
            update_data["maxCapacity"] = data.maxCapacity
        if data.leadTime is not None:
            update_data["leadTime"] = data.leadTime
        
        # Status handling
        if data.status is not None:
            if data.status == "active":
                # PHASE 4/5: Check GST verification for publish/activate
                seller_status = get_seller_status(seller)
                if not seller_status["canPublish"]:
                    gst = seller.get("gst", {})
                    gst_status = gst.get("status", "pending")
                    raise HTTPException(
                        status_code=403,
                        detail=f"GST verification required before publishing products. Current status: {gst_status}"
                    )
                
                # Validate can activate
                pricing_tiers = listing.get("pricingTiers", [])
                moq = listing.get("moq") or data.moq
                if not pricing_tiers:
                    raise HTTPException(status_code=400, detail="Cannot activate without pricing tiers")
                if not moq:
                    raise HTTPException(status_code=400, detail="Cannot activate without MOQ")
                if not listing.get("publishedAt"):
                    update_data["publishedAt"] = now
            update_data["status"] = data.status
            update_data["isActive"] = data.status == "active"
        
        # STRICT: sellerListings only
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": update_data}
        )
        
        updated = await db.sellerListings.find_one({"_id": listing_oid})
        
        logger.info(f"Seller {seller['email']} updated listing: {listing_id}")
        
        response = {"message": "Listing updated", "listing": updated}
        if variant_changed and new_variant:
            response["variantChanged"] = True
            response["newVariant"] = new_variant
        
        # ENTERPRISE STANDARD: Always serialize before return
        return success_response(response)
    
    @router.patch("/listings/{listing_id}/pricing")
    async def update_pricing(
        listing_id: str,
        data: PricingUpdate,
        seller: dict = Depends(require_verified_seller)
    ):
        """Update pricing tiers only - fast path for daily price changes"""
        seller_oid = ObjectId(seller["_id"])
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        
        # Convert pricing tiers
        new_tiers = []
        for tier in data.pricingTiers:
            new_tiers.append({
                "minQty": tier.minQty,
                "maxQty": tier.maxQty,
                "pricePerUnit": tier.pricePerUnit
            })
        
        # Store in price history
        old_tiers = listing.get("pricingTiers", [])
        if old_tiers != new_tiers:
            await db.sellerListings.update_one(
                {"_id": listing_oid},
                {"$push": {
                    "priceHistory": {
                        "timestamp": now,
                        "oldTiers": old_tiers,
                        "action": "pricingUpdate"
                    }
                }}
            )
        
        # Update pricing
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {
                "pricingTiers": new_tiers,
                "updatedAt": now
            }}
        )
        
        logger.info(f"Seller {seller['email']} updated pricing: {listing_id}")
        return {
            "message": "Pricing updated",
            "pricingTiers": new_tiers,
            "lastUpdated": now.isoformat()
        }
    
    @router.post("/listings/{listing_id}/publish")
    async def publish_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Publish a draft listing.
        
        ENTERPRISE GRADE VALIDATION:
        1. Check GST verification (PHASE 4/5)
        2. Check seller account status (banned/suspended)
        3. Validate listing completeness (all mandatory fields)
        4. Only then allow publishing
        
        Returns HTTP 400 with missing fields if incomplete.
        """
        seller_oid = ObjectId(seller["_id"])
        
        # PHASE 4: Check GST verification for publish
        seller_status = get_seller_status(seller)
        if not seller_status["canPublish"]:
            gst = seller.get("gst", {})
            gst_status = gst.get("status", "pending")
            raise HTTPException(
                status_code=403,
                detail=f"GST verification required before publishing products. Current status: {gst_status}"
            )
        
        # Check seller account status
        account_status = seller.get("sellerStatus", "active")
        if account_status == "banned":
            raise HTTPException(status_code=403, detail="Seller account is banned")
        if account_status == "suspended":
            raise HTTPException(status_code=403, detail="Seller account is suspended")
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        if listing.get("status") == "active":
            return {"message": "Listing already published", "status": "active"}
        
        # ENTERPRISE GRADE: Validate listing completeness before publishing
        validate_listing_completeness(listing)
        
        now = datetime.now(timezone.utc)
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {
                "status": "active",
                "isActive": True,
                "publishedAt": now,
                "updatedAt": now
            }}
        )
        
        logger.info(f"Seller {seller['email']} published listing: {listing_id}")
        return {"message": "Listing published", "status": "active", "publishedAt": now}
    
    @router.get("/listings/{listing_id}/validate")
    async def validate_listing_for_publish(
        listing_id: str,
        seller: dict = Depends(require_auth)
    ):
        """
        ENTERPRISE GRADE: Pre-publish validation check.
        
        Allows frontend to check if a listing can be published
        WITHOUT actually publishing it.
        
        Returns:
        - isComplete: boolean
        - canPublish: boolean (includes GST check)
        - missingFields: list of fields that need to be filled
        - fieldErrors: detailed error messages per field
        """
        seller_oid = ObjectId(seller["_id"])
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Check listing completeness
        required_fields = {
            "pricingTiers": {
                "check": lambda v: v and len(v) > 0,
                "message": "At least one pricing tier required"
            },
            "moq": {
                "check": lambda v: v and v > 0,
                "message": "MOQ (Minimum Order Quantity) must be greater than 0"
            },
            "stock": {
                "check": lambda v: v and v > 0,
                "message": "Stock quantity must be greater than 0"
            },
            "maxCapacity": {
                "check": lambda v: v and v > 0,
                "message": "Maximum capacity must be greater than 0"
            },
            "images": {
                "check": lambda v: v and len(v) > 0,
                "message": "At least one product image required"
            },
            "variantId": {
                "check": lambda v: v is not None,
                "message": "Product variant must be linked"
            }
        }
        
        missing_fields = []
        field_errors = {}
        
        for field, config in required_fields.items():
            value = listing.get(field)
            if not config["check"](value):
                missing_fields.append(field)
                field_errors[field] = config["message"]
        
        is_complete = len(missing_fields) == 0
        
        # Check GST verification
        seller_status = get_seller_status(seller)
        gst = seller.get("gst", {})
        gst_verified = seller_status["gstVerified"]
        gst_status_str = gst.get("status", "none")
        
        # Check seller account status
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
            "gstStatus": gst_status_str,
            "accountStatus": account_status,
            "blockers": [
                f"Missing fields: {', '.join(missing_fields)}" if missing_fields else None,
                f"GST not verified (status: {gst_status_str})" if not gst_verified else None,
                f"Account {account_status}" if not account_active else None
            ]
        }
    
    @router.post("/listings/{listing_id}/pause")
    async def pause_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Pause a listing"""
        seller_oid = ObjectId(seller["_id"])
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        now = datetime.now(timezone.utc)
        await db.sellerListings.update_one(
            {"_id": listing_oid},
            {"$set": {
                "status": "paused",
                "isActive": False,
                "updatedAt": now
            }}
        )
        
        return {"message": "Listing paused", "status": "paused"}
    
    @router.delete("/listings/{listing_id}")
    async def delete_listing(
        listing_id: str,
        seller: dict = Depends(require_verified_seller),
        hardDelete: bool = Query(False)
    ):
        """Archive or permanently delete a listing"""
        seller_oid = ObjectId(seller["_id"])
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # STRICT: sellerListings only
        listing = await db.sellerListings.find_one({
            "_id": listing_oid,
            "sellerId": seller_oid
        })
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        if hardDelete:
            await db.sellerListings.delete_one({"_id": listing_oid})
            logger.info(f"Seller {seller['email']} deleted listing: {listing_id}")
            return {"message": "Listing permanently deleted"}
        else:
            now = datetime.now(timezone.utc)
            await db.sellerListings.update_one(
                {"_id": listing_oid},
                {"$set": {
                    "status": "archived",
                    "isActive": False,
                    "updatedAt": now
                }}
            )
            logger.info(f"Seller {seller['email']} archived listing: {listing_id}")
            return {"message": "Listing archived", "status": "archived"}
    
    # ==================== DASHBOARD & STATS ====================
    
    @router.get("/dashboard")
    async def get_seller_dashboard(
        seller: dict = Depends(require_verified_seller)
    ):
        """Get seller dashboard summary"""
        seller_oid = ObjectId(seller["_id"])
        
        # STRICT: sellerListings only
        pipeline = [
            {"$match": {"sellerId": seller_oid}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        status_counts = await db.sellerListings.aggregate(pipeline).to_list(10)
        
        stats = {"total": 0, "draft": 0, "active": 0, "paused": 0, "archived": 0}
        for item in status_counts:
            status = item["_id"]
            if status in stats:
                stats[status] = item["count"]
            stats["total"] += item["count"]
        
        # Recent listings
        recent = await db.sellerListings.find({"sellerId": seller_oid})\
            .sort("updatedAt", -1)\
            .limit(5)\
            .to_list(5)
        
        enriched_recent = []
        for listing in recent:
            item = serialize_listing(listing)
            if listing.get("productId"):
                product = await db.products.find_one({"_id": listing["productId"]})
                if product:
                    item["productName"] = product.get("name")
            enriched_recent.append(item)
        
        return {
            "stats": stats,
            "recentListings": enriched_recent
        }
    
    @router.get("/stats")
    async def get_seller_stats(
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Get seller statistics.
        
        USES: subscription_service for subscription data (SSOT)
        """
        from services.subscription_service import get_effective_subscription, check_and_update_monthly_usage
        
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        try:
            # Count listings - STRICT: sellerListings only
            total_listings = await db.sellerListings.count_documents({"sellerId": seller_oid})
            
            published_listings = await db.sellerListings.count_documents({
                "sellerId": seller_oid,
                "status": "active"
            })
            
            # Inquiry stats - STRICT: sellerId as ObjectId
            total_enquiries = await db.inquiries.count_documents({"sellerId": seller_oid})
            
            pending_enquiries = await db.inquiries.count_documents({
                "sellerId": seller_oid,
                "status": "pending"
            })
            
            # SSOT: Use subscription service
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
                "subscription": {
                    "plan": "free",
                    "isUnlimited": False,
                    "usageDisplay": "0 / 5",
                    "remaining": 5
                }
            }
    
    @router.get("/subscription")
    async def get_subscription_status(
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Get seller's subscription status.
        
        SSOT: Uses subscription_service which reads from subscriptions collection.
        """
        from services.subscription_service import get_subscription_status_for_seller
        
        seller_oid = ObjectId(seller["_id"]) if isinstance(seller["_id"], str) else seller["_id"]
        
        status_data = await get_subscription_status_for_seller(db, seller_oid)
        
        # Add upgrade info
        status_data["upgradeInfo"] = {
            "showUpgrade": status_data.get("showUpgradeCta", False),
            "upgradeUrl": "/seller/subscription",
            "priceQuarterly": 999
        }
        
        # Add benefits (for backwards compatibility)
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
        """
        PHASE 7 - FRONTEND SELLER DASHBOARD LOGIC
        
        Get seller's current status including:
        - GST verification status
        - Role status
        - Permissions (canCreateDraft, canPublish)
        
        Frontend uses this to:
        - Show "Register as seller" if not seller
        - Show "GST verification in progress" banner if pending
        - Enable/disable publish buttons
        """
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
    
    def _get_seller_status_message(status: dict, gst: dict) -> str:
        """Generate user-friendly status message"""
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
    
    # ==================== PRODUCT VARIANTS HELPER ====================
    
    @router.get("/products/{product_id}/variants")
    async def get_product_variants(
        product_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Get all available variants for a product.
        Useful for seller to see what attribute combinations exist.
        """
        variants = await variant_service.get_variants_for_product(product_id)
        
        return {
            "productId": product_id,
            "variants": variants,
            "total": len(variants)
        }
    
    @router.get("/categories/{category_id}/spec-template")
    async def get_category_spec_template(
        category_id: str,
        seller: dict = Depends(require_verified_seller)
    ):
        """Get the spec template for a category - STRICT camelCase"""
        try:
            category_oid = ObjectId(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        category = await db.categories.find_one({"_id": category_oid})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # STRICT: specTemplates only, camelCase fields only
        template = await db.specTemplates.find_one({
            "categoryId": category_oid,
            "isActive": {"$ne": False}
        })
        
        result = {
            "category": {
                "_id": str(category["_id"]),
                "name": category.get("name"),
                "settings": category.get("settings", {})
            }
        }
        
        if template:
            result["specTemplate"] = serialize_objectids(template)
        else:
            result["specTemplate"] = None
            result["note"] = "No spec template defined for this category."
        
        return result
    
    # ==================== INQUIRY MANAGEMENT ====================
    
    @router.get("/inquiries")
    async def get_seller_inquiries(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        """Get all inquiries for this seller - STRICT camelCase with safe error handling"""
        import traceback
        
        try:
            # CRITICAL: Query must use ObjectId, not string
            seller_oid = seller["_id"] if isinstance(seller["_id"], ObjectId) else ObjectId(seller["_id"])
            
            # Build query - sellerId as ObjectId
            query = {"sellerId": seller_oid}
            if status and status in ["pending", "accepted", "rejected", "reported", "new"]:
                query["status"] = status
            
            # Safe pagination
            page = max(1, page)
            limit = min(100, max(1, limit))
            skip = (page - 1) * limit
            
            # Count and fetch
            total = await db.inquiries.count_documents(query)
            logger.info(f"[SELLER INQUIRIES] sellerId={seller_oid}, status={status}, total={total}")
            
            inquiries = await db.inquiries.find(query)\
                .sort("createdAt", -1)\
                .skip(skip)\
                .limit(limit)\
                .to_list(limit)
            
            # Count unread (pending) inquiries
            unread_count = await db.inquiries.count_documents({
                "sellerId": seller_oid,
                "status": "pending"
            })
            
            result = []
            for inq in inquiries:
                try:
                    # Serialize ObjectIds safely
                    serialized = serialize_mongo_doc(inq)
                    
                    # Get listing info - SAFE handling
                    listing_id = inq.get("listingId")
                    listing_name = ""
                    if listing_id:
                        try:
                            lid = listing_id if isinstance(listing_id, ObjectId) else ObjectId(str(listing_id))
                            listing = await db.sellerListings.find_one({"_id": lid})
                            
                            if listing:
                                # Get product name
                                product_id = listing.get("productId")
                                if product_id:
                                    pid = product_id if isinstance(product_id, ObjectId) else ObjectId(str(product_id))
                                    product = await db.products.find_one({"_id": pid})
                                    if product:
                                        listing_name = product.get("name", "")
                                        serialized["listingName"] = listing_name
                                
                                # Get first image safely
                                images = listing.get("images") or []
                                serialized["listingImage"] = images[0] if images else None
                        except Exception as e:
                            logger.warning(f"Error fetching listing {listing_id}: {e}")
                    
                    # STRICT CONTACT UNLOCK: Fetch buyer from users collection
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
                                    # UNLOCKED: Full buyer contact visible
                                    buyer_info = {
                                        "name": buyer_profile.get("businessName") or buyer.get("email", "").split("@")[0],
                                        "phone": buyer_profile.get("phone"),
                                        "email": buyer.get("email"),
                                        "companyName": buyer_profile.get("businessName"),
                                        "city": buyer_profile.get("city"),
                                        "state": buyer_profile.get("state"),
                                    }
                                else:
                                    # LOCKED: Only masked info (NO phone, NO email)
                                    company_name = buyer_profile.get("businessName") or ""
                                    buyer_masked = {
                                        "companyInitial": company_name[0].upper() if company_name else "?",
                                        "city": buyer_profile.get("city"),
                                        "state": buyer_profile.get("state"),
                                    }
                        except Exception as e:
                            logger.warning(f"Error fetching buyer {buyer_id}: {e}")
                    
                    # Fallback to embedded buyerInfo if no buyerId (legacy inquiries)
                    if not buyer_info and not buyer_masked:
                        embedded_buyer = inq.get("buyerInfo") or {}
                        if serialized.get("status") == "accepted":
                            buyer_info = embedded_buyer
                        else:
                            company_name = embedded_buyer.get("companyName") or ""
                            buyer_masked = {
                                "companyInitial": company_name[0].upper() if company_name else "?",
                                "city": embedded_buyer.get("city"),
                                "state": embedded_buyer.get("state"),
                            }
                    
                    # Set buyer fields - NEVER leak phone/email before accept
                    serialized["buyerInfo"] = buyer_info
                    serialized["buyerMasked"] = buyer_masked
                    serialized["buyerType"] = inq.get("buyerType")
                    
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
            
        except Exception as e:
            logger.error(f"SELLER INQUIRY ERROR: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to fetch inquiries")
    
    @router.post("/inquiries/{inquiry_id}/accept")
    async def accept_inquiry(
        inquiry_id: str,
        data: InquiryAccept,
        seller: dict = Depends(require_verified_seller)
    ):
        """
        Accept an inquiry with a quote and generate WhatsApp redirect link.
        
        ENTERPRISE SUBSCRIPTION FLOW:
        1. can_accept_inquiry() → checks subscription limits from subscriptions collection (SSOT)
        2. If cannot accept → 403 with detailed error
        3. If can accept → update inquiry, increment counter (only for non-unlimited), return success
        
        Updates inquiry status to "accepted", stores seller response,
        reveals buyer contact details, and returns WhatsApp link for direct contact.
        """
        from services.subscription_service import can_accept_inquiry as check_can_accept, increment_enquiry_usage
        import urllib.parse
        
        # CRITICAL: Use ObjectId for all database operations
        seller_oid = seller["_id"] if isinstance(seller["_id"], ObjectId) else ObjectId(seller["_id"])
        
        # Step 1: Check subscription limits using SSOT (subscriptions collection)
        can_accept_result = await check_can_accept(db, seller_oid)
        
        # Step 2: If cannot accept → return 403 with detailed error
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
        
        # Step 3: Validate and fetch the inquiry
        try:
            inquiry = await db.inquiries.find_one({
                "_id": ObjectId(inquiry_id),
                "sellerId": seller_oid  # ObjectId, not string
            })
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid inquiry ID")
        
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        
        if inquiry.get("status") not in ["pending", "new"]:
            raise HTTPException(status_code=400, detail=f"Cannot accept inquiry with status: {inquiry.get('status')}")
        
        now = datetime.now(timezone.utc)
        validity_date = now + timedelta(days=data.validityDays)
        
        # Step 4: Update inquiry with sellerResponse
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {
                "status": "accepted",
                "sellerResponse": {
                    "quotedPrice": data.quotedPrice,
                    "validTill": validity_date,
                    "sellerNote": data.sellerNote
                },
                # Keep legacy quote field for backwards compatibility
                "quote": {
                    "price": data.quotedPrice,
                    "moq": data.moq,
                    "leadTimeDays": data.leadTimeDays,
                    "validTill": validity_date,
                    "sellerNote": data.sellerNote,
                    "quotedAt": now
                },
                "acceptedAt": now,
                "updatedAt": now
            }}
        )
        
        # Step 5: Increment usage counter ONLY for non-unlimited plans
        subscription = can_accept_result["subscription"]
        new_used_count = can_accept_result["usage"]["used"]
        
        if not subscription["isUnlimited"]:
            # Increment counter for free/trial/expired plans
            new_used_count = await increment_enquiry_usage(db, seller_oid)
        # For unlimited plans (pro/enterprise), we do NOT increment enquiriesUsed
        
        # Step 6: Get updated inquiry and buyer info
        updated_inquiry = await db.inquiries.find_one({"_id": ObjectId(inquiry_id)})
        buyer_info = updated_inquiry.get("buyerInfo", {})
        
        # Get product name from inquiry or listing
        product_name = updated_inquiry.get("productName", "")
        if not product_name:
            listing_id = updated_inquiry.get("listingId")
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
                                product_name = product.get("name", "your product")
                except Exception as e:
                    logger.warning(f"Error fetching product name: {e}")
        
        if not product_name:
            product_name = "your product"
        
        # Get seller business name from profile
        seller_name = seller.get("profile", {}).get("businessName") or seller.get("businessName") or "B2B Market Seller"
        
        # Get buyer details
        buyer_name = buyer_info.get("name") or buyer_info.get("companyName") or "Customer"
        buyer_phone = buyer_info.get("phone", "")
        quantity = updated_inquiry.get("quantity", 1)
        
        # Format validity date as "18 Feb 2026"
        formatted_date = validity_date.strftime("%d %b %Y")
        
        # Generate WhatsApp message
        whatsapp_message = f"""Hello {buyer_name},

This is {seller_name} from B2B Market.

We received your inquiry for {product_name}, Qty {quantity}.

Our quoted price is ₹{data.quotedPrice}, valid till {formatted_date}."""
        
        # Add seller note if provided
        if data.sellerNote:
            whatsapp_message += f"\n\n{data.sellerNote}"
        
        # Generate WhatsApp link if buyer phone exists
        whatsapp_link = None
        if buyer_phone:
            # Clean phone number - remove spaces, dashes, and ensure country code
            clean_phone = buyer_phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            # Add India country code if not present
            if not clean_phone.startswith("+"):
                if clean_phone.startswith("91"):
                    clean_phone = "+" + clean_phone
                else:
                    clean_phone = "+91" + clean_phone
            
            # URL encode the message
            encoded_message = urllib.parse.quote(whatsapp_message)
            whatsapp_link = f"https://wa.me/{clean_phone.replace('+', '')}?text={encoded_message}"
        
        # Calculate remaining
        limit = subscription["limit"]
        if subscription["isUnlimited"]:
            remaining = -1
        else:
            remaining = max(0, limit - new_used_count)
        
        return {
            "success": True,
            "message": "Inquiry accepted successfully",
            "inquiryId": inquiry_id,
            "whatsappLink": whatsapp_link,
            "buyerContact": {
                "name": buyer_info.get("name"),
                "phone": buyer_info.get("phone"),
                "email": buyer_info.get("email"),
                "company": buyer_info.get("companyName")
            },
            "quote": {
                "price": data.quotedPrice,
                "validTill": validity_date.isoformat()
            },
            "subscriptionUsage": {
                "used": new_used_count,
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
        # CRITICAL FIX: Use ObjectId for sellerId matching
        seller_oid = seller["_id"] if isinstance(seller["_id"], ObjectId) else ObjectId(seller["_id"])
        
        try:
            inquiry = await db.inquiries.find_one({
                "_id": ObjectId(inquiry_id),
                "sellerId": seller_oid  # ObjectId, not string
            })
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
                "rejection": {
                    "reason": data.reason,
                    "note": data.note,
                    "rejectedAt": now
                },
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
        # CRITICAL FIX: Use ObjectId for sellerId matching
        seller_oid = seller["_id"] if isinstance(seller["_id"], ObjectId) else ObjectId(seller["_id"])
        seller_id_str = str(seller_oid)
        
        try:
            inquiry = await db.inquiries.find_one({
                "_id": ObjectId(inquiry_id),
                "sellerId": seller_oid  # ObjectId, not string
            })
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid inquiry ID")
        
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        
        now = datetime.now(timezone.utc)
        
        await db.inquiries.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {
                "status": "reported",
                "report": {
                    "type": data.reportType,
                    "details": data.details,
                    "reportedAt": now,
                    "reportedBy": seller_id_str
                },
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
