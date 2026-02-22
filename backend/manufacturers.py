"""
B2B Marketplace - Manufacturer & Product Request System
========================================================
Admin-controlled Products and Manufacturers with seller request workflow.

Core Principle:
- Products and Manufacturers are centrally controlled by Admin
- Sellers can only select from approved data or request additions
- All seller listings require admin approval

This ensures:
- Clean data
- Zero duplication
- High buyer trust
- Long-term scalability
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger("b2b_manufacturers")

# ==================== PYDANTIC MODELS ====================

# --- Manufacturer Models ---

class ManufacturerCreate(BaseModel):
    """Create a new manufacturer (admin only)"""
    brandName: str = Field(..., min_length=2, max_length=200)
    legalName: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    logoUrl: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = Field(None, max_length=100)
    certifications: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list, description="Category IDs this manufacturer operates in")

class ManufacturerUpdate(BaseModel):
    """Update manufacturer (admin only)"""
    brandName: Optional[str] = Field(None, min_length=2, max_length=200)
    legalName: Optional[str] = None
    description: Optional[str] = None
    logoUrl: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    certifications: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    status: Optional[Literal["approved", "inactive"]] = None

# --- Request Models ---

class ManufacturerRequest(BaseModel):
    """Seller request for new manufacturer"""
    brandName: str = Field(..., min_length=2, max_length=200)
    legalName: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=500, description="Why this manufacturer is needed")
    supportingDocuments: List[str] = Field(default_factory=list, description="URLs to supporting docs")

class ProductRequest(BaseModel):
    """Seller request for new product"""
    productName: str = Field(..., min_length=2, max_length=200)
    suggestedCategoryId: str
    manufacturerId: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    reason: Optional[str] = Field(None, max_length=500)

class RequestReview(BaseModel):
    """Admin review of a request"""
    status: Literal["approved", "rejected"]
    adminNotes: Optional[str] = Field(None, max_length=500)

class CategoryRequest(BaseModel):
    """Seller request for new category"""
    categoryName: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    reason: Optional[str] = Field(None, max_length=500, description="Why this category is needed")

class SpecFieldRequest(BaseModel):
    """Seller request for new specification field"""
    categoryId: str = Field(..., description="Category this field should be added to")
    fieldName: str = Field(..., min_length=2, max_length=100)
    fieldType: Literal["text", "number", "dropdown", "boolean"] = "text"
    suggestedOptions: List[str] = Field(default_factory=list, description="For dropdown type")
    unit: Optional[str] = Field(None, max_length=20, description="e.g., V, HP, kW")
    reason: Optional[str] = Field(None, max_length=500)


# ==================== ROUTER SETUP ====================

def create_manufacturer_router(db, require_admin, require_auth, require_verified_seller, serialize_mongo_doc):
    """
    Create the manufacturer and request management router.
    """
    router = APIRouter(tags=["Manufacturers & Requests"])
    
    # ==================== ADMIN: MANUFACTURER CRUD ====================
    
    @router.get("/admin/manufacturers")
    async def list_manufacturers(
        admin: dict = Depends(require_admin),
        status: Optional[str] = Query(None, description="Filter by status"),
        categoryId: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100)
    ):
        """List all manufacturers (admin only)"""
        query = {}
        
        if status:
            query["status"] = status
        if categoryId:
            query["categories"] = categoryId
        if search:
            query["$or"] = [
                {"brandName": {"$regex": search, "$options": "i"}},
                {"legalName": {"$regex": search, "$options": "i"}}
            ]
        
        skip = (page - 1) * limit
        total = await db.manufacturers.count_documents(query)
        
        manufacturers = await db.manufacturers.find(query)\
            .sort("brandName", 1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        serialized = [serialize_mongo_doc(m) for m in manufacturers]
        
        # Add product count for each manufacturer - STRICT camelCase
        for m in serialized:
            m["productCount"] = await db.products.count_documents({"manufacturerId": m["_id"]})
            m["listingCount"] = await db.sellerListings.count_documents({"manufacturerId": m["_id"]})
        
        return {
            "manufacturers": serialized,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    @router.get("/admin/manufacturers/{manufacturerId}")
    async def get_manufacturer(
        manufacturerId: str,
        admin: dict = Depends(require_admin)
    ):
        """Get manufacturer details (admin only)"""
        try:
            mfr = await db.manufacturers.find_one({"_id": ObjectId(manufacturerId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid manufacturer ID")
        
        if not mfr:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        
        serialized = serialize_mongo_doc(mfr)
        
        # Get related products
        products = await db.products.find({"manufacturerId": manufacturerId}).limit(20).to_list(20)
        serialized["products"] = [serialize_mongo_doc(p) for p in products]
        
        return {"manufacturer": serialized}
    
    @router.post("/admin/manufacturers")
    async def create_manufacturer(
        data: ManufacturerCreate,
        admin: dict = Depends(require_admin)
    ):
        """Create a new manufacturer (admin only)"""
        # Check for duplicate brand name
        existing = await db.manufacturers.find_one({
            "brandName": {"$regex": f"^{data.brandName}$", "$options": "i"}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Manufacturer with this brand name already exists")
        
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "brandName": data.brandName,
            "legalName": data.legalName,
            "description": data.description,
            "logoUrl": data.logoUrl,
            "website": data.website,
            "country": data.country,
            "certifications": data.certifications,
            "categories": data.categories,
            "status": "approved",
            "createdAt": now,
            "createdBy": admin["_id"],  # Must be ObjectId, not str
            "updatedAt": now
        }
        
        await db.manufacturers.insert_one(doc)
        
        logger.info(f"Admin {admin['email']} created manufacturer: {data.brandName}")
        return {"message": "Manufacturer created successfully", "manufacturer": serialize_mongo_doc(doc)}
    
    @router.patch("/admin/manufacturers/{manufacturerId}")
    async def update_manufacturer(
        manufacturerId: str,
        data: ManufacturerUpdate,
        admin: dict = Depends(require_admin)
    ):
        """Update a manufacturer (admin only)"""
        try:
            mfr = await db.manufacturers.find_one({"_id": ObjectId(manufacturerId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid manufacturer ID")
        
        if not mfr:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        
        update_data = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.brandName is not None:
            # Check for duplicate
            dup = await db.manufacturers.find_one({
                "_id": {"$ne": ObjectId(manufacturerId)},
                "brandName": {"$regex": f"^{data.brandName}$", "$options": "i"}
            })
            if dup:
                raise HTTPException(status_code=400, detail="Another manufacturer with this name exists")
            update_data["brandName"] = data.brandName
        
        if data.legalName is not None:
            update_data["legalName"] = data.legalName
        if data.description is not None:
            update_data["description"] = data.description
        if data.logoUrl is not None:
            update_data["logoUrl"] = data.logoUrl
        if data.website is not None:
            update_data["website"] = data.website
        if data.country is not None:
            update_data["country"] = data.country
        if data.certifications is not None:
            update_data["certifications"] = data.certifications
        if data.categories is not None:
            update_data["categories"] = data.categories
        if data.status is not None:
            update_data["status"] = data.status
        
        await db.manufacturers.update_one({"_id": ObjectId(manufacturerId)}, {"$set": update_data})
        
        updated = await db.manufacturers.find_one({"_id": ObjectId(manufacturerId)})
        
        logger.info(f"Admin {admin['email']} updated manufacturer: {manufacturerId}")
        return {"message": "Manufacturer updated", "manufacturer": serialize_mongo_doc(updated)}
    
    @router.delete("/admin/manufacturers/{manufacturerId}")
    async def delete_manufacturer(
        manufacturerId: str,
        admin: dict = Depends(require_admin),
        force: bool = Query(False)
    ):
        """Delete or deactivate a manufacturer (admin only)"""
        try:
            mfr = await db.manufacturers.find_one({"_id": ObjectId(manufacturerId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid manufacturer ID")
        
        if not mfr:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        
        # Check if manufacturer is in use
        listing_count = await db.sellerListings.count_documents({"manufacturerId": manufacturerId})
        product_count = await db.products.count_documents({"manufacturerId": manufacturerId})
        
        if (listing_count > 0 or product_count > 0) and not force:
            raise HTTPException(
                status_code=400,
                detail=f"Manufacturer has {product_count} products and {listing_count} listings. Use force=true to deactivate."
            )
        
        if force:
            # Soft delete - deactivate
            await db.manufacturers.update_one(
                {"_id": ObjectId(manufacturerId)},
                {"$set": {"status": "inactive", "updatedAt": datetime.now(timezone.utc)}}
            )
            logger.info(f"Admin {admin['email']} deactivated manufacturer: {manufacturerId}")
            return {"message": "Manufacturer deactivated"}
        else:
            await db.manufacturers.delete_one({"_id": ObjectId(manufacturerId)})
            logger.info(f"Admin {admin['email']} deleted manufacturer: {manufacturerId}")
            return {"message": "Manufacturer deleted"}
    
    # ==================== PUBLIC: MANUFACTURER LIST ====================
    
    @router.get("/manufacturers")
    async def list_approved_manufacturers(
        categoryId: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=500)
    ):
        """List approved manufacturers (public - for seller dropdowns)"""
        query = {"status": "approved"}
        
        if categoryId:
            query["categories"] = categoryId
        if search:
            query["brandName"] = {"$regex": search, "$options": "i"}
        
        manufacturers = await db.manufacturers.find(query)\
            .sort("brandName", 1)\
            .limit(limit)\
            .to_list(limit)
        
        # Return only essential fields for dropdown
        return {
            "manufacturers": [
                {
                    "_id": str(m["_id"]),
                    "brandName": m["brandName"],
                    "logoUrl": m.get("logoUrl"),
                    "country": m.get("country")
                }
                for m in manufacturers
            ]
        }
    
    # ==================== SELLER: REQUEST NEW MANUFACTURER ====================
    
    @router.post("/seller/requests/manufacturer")
    async def request_manufacturer(
        data: ManufacturerRequest,
        seller: dict = Depends(require_verified_seller)
    ):
        """Submit a request for a new manufacturer"""
        seller_id = str(seller["_id"])
        
        # Check for duplicate pending request
        existing = await db.manufacturerRequests.find_one({
            "brandName": {"$regex": f"^{data.brandName}$", "$options": "i"},
            "status": "pending"
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A request for this manufacturer is already pending review"
            )
        
        # Check if manufacturer already exists
        exists = await db.manufacturers.find_one({
            "brandName": {"$regex": f"^{data.brandName}$", "$options": "i"}
        })
        if exists:
            raise HTTPException(
                status_code=400,
                detail="This manufacturer already exists in our database"
            )
        
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "brandName": data.brandName,
            "legalName": data.legalName,
            "website": data.website,
            "country": data.country,
            "reason": data.reason,
            "supportingDocuments": data.supportingDocuments,
            "requestedBy": seller_id,
            "requestedByEmail": seller.get("email"),
            "status": "pending",
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.manufacturerRequests.insert_one(doc)
        
        logger.info(f"Seller {seller['email']} requested manufacturer: {data.brandName}")
        return {
            "message": "Manufacturer request submitted for admin review",
            "request": serialize_mongo_doc(doc)
        }
    
    @router.get("/seller/requests/manufacturer")
    async def get_my_manufacturer_requests(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None)
    ):
        """Get seller's manufacturer requests"""
        query = {"requestedBy": str(seller["_id"])}
        if status:
            query["status"] = status
        
        requests = await db.manufacturerRequests.find(query).sort("createdAt", -1).to_list(50)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests]}
    
    # ==================== SELLER: REQUEST NEW PRODUCT ====================
    
    @router.post("/seller/requests/product")
    async def request_product(
        data: ProductRequest,
        seller: dict = Depends(require_verified_seller)
    ):
        """Submit a request for a new product"""
        seller_id = str(seller["_id"])
        
        # Validate category exists
        try:
            category = await db.categories.find_one({"_id": ObjectId(data.suggestedCategoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Validate manufacturer if provided
        if data.manufacturerId:
            try:
                mfr = await db.manufacturers.find_one({"_id": ObjectId(data.manufacturerId)})
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid manufacturer ID")
            if not mfr:
                raise HTTPException(status_code=404, detail="Manufacturer not found")
        
        # Check for duplicate pending request
        existing = await db.productRequests.find_one({
            "productName": {"$regex": f"^{data.productName}$", "$options": "i"},
            "status": "pending"
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A request for this product is already pending review"
            )
        
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "productName": data.productName,
            "suggestedCategoryId": data.suggestedCategoryId,
            "categoryName": category.get("name"),
            "manufacturerId": data.manufacturerId,
            "description": data.description,
            "reason": data.reason,
            "requestedBy": seller_id,
            "requestedByEmail": seller.get("email"),
            "status": "pending",
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.productRequests.insert_one(doc)
        
        logger.info(f"Seller {seller['email']} requested product: {data.productName}")
        return {
            "message": "Product request submitted for admin review",
            "request": serialize_mongo_doc(doc)
        }
    
    @router.get("/seller/requests/product")
    async def get_my_product_requests(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None)
    ):
        """Get seller's product requests"""
        query = {"requestedBy": str(seller["_id"])}
        if status:
            query["status"] = status
        
        requests = await db.productRequests.find(query).sort("createdAt", -1).to_list(50)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests]}
    
    # ==================== ADMIN: REVIEW REQUESTS ====================
    
    @router.get("/admin/requests/manufacturers")
    async def list_manufacturer_requests(
        admin: dict = Depends(require_admin),
        status: str = Query("pending")
    ):
        """List manufacturer requests (admin only)"""
        query = {"status": status} if status != "all" else {}
        
        requests = await db.manufacturerRequests.find(query)\
            .sort("createdAt", -1)\
            .to_list(100)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests], "total": len(requests)}
    
    @router.post("/admin/requests/manufacturers/{request_id}/review")
    async def review_manufacturer_request(
        request_id: str,
        review: RequestReview,
        admin: dict = Depends(require_admin)
    ):
        """Approve or reject a manufacturer request (admin only)"""
        try:
            request = await db.manufacturerRequests.find_one({"_id": ObjectId(request_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request ID")
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if request.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Request has already been reviewed")
        
        now = datetime.now(timezone.utc)
        
        if review.status == "approved":
            # Create the manufacturer
            mfr_doc = {
                "_id": ObjectId(),
                "brandName": request["brandName"],
                "legalName": request.get("legalName"),
                "website": request.get("website"),
                "country": request.get("country"),
                "certifications": [],
                "categories": [],
                "status": "approved",
                "createdAt": now,
                "createdBy": admin["_id"],  # Must be ObjectId, not str
                "updatedAt": now
            }
            await db.manufacturers.insert_one(mfr_doc)
            
            # Update request
            await db.manufacturerRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "approved",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes,
                    "createdManufacturerId": str(mfr_doc["_id"])
                }}
            )
            
            logger.info(f"Admin {admin['email']} approved manufacturer request: {request['brandName']}")
            return {
                "message": "Manufacturer request approved and manufacturer created",
                "manufacturer": serialize_mongo_doc(mfr_doc)
            }
        else:
            # Reject
            await db.manufacturerRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "rejected",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes
                }}
            )
            
            logger.info(f"Admin {admin['email']} rejected manufacturer request: {request['brandName']}")
            return {"message": "Manufacturer request rejected"}
    
    @router.get("/admin/requests/products")
    async def list_product_requests(
        admin: dict = Depends(require_admin),
        status: str = Query("pending")
    ):
        """List product requests (admin only)"""
        query = {"status": status} if status != "all" else {}
        
        requests = await db.productRequests.find(query)\
            .sort("createdAt", -1)\
            .to_list(100)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests], "total": len(requests)}
    
    @router.post("/admin/requests/products/{request_id}/review")
    async def review_product_request(
        request_id: str,
        review: RequestReview,
        admin: dict = Depends(require_admin)
    ):
        """Approve or reject a product request (admin only)"""
        try:
            request = await db.productRequests.find_one({"_id": ObjectId(request_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request ID")
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if request.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Request has already been reviewed")
        
        now = datetime.now(timezone.utc)
        
        if review.status == "approved":
            # Create the product - ONLY fields allowed by MongoDB schema
            product_doc = {
                "_id": ObjectId(),
                
                # Required by Mongo schema
                "name": request["productName"],
                "categoryId": ObjectId(request["suggestedCategoryId"]),
                "isActive": True,
                "createdAt": now,
                "updatedAt": now,
                
                # Optional (allowed by schema)
                "description": request.get("description"),
                "categoryName": None,
                "family": None,
                "variant": None,
                "coverImageUrl": None,
                "unit": None,
                
                # Required array fields
                "specTemplateIds": [],
                "specTemplateVersions": [],
                
                # Must be ObjectId
                "createdBy": admin["_id"]
            }
            await db.products.insert_one(product_doc)
            
            # Update request
            await db.productRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "approved",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes,
                    "createdProductId": str(product_doc["_id"])
                }}
            )
            
            logger.info(f"Admin {admin['email']} approved product request: {request['productName']}")
            return {
                "message": "Product request approved and product created",
                "product": serialize_mongo_doc(product_doc)
            }
        else:
            # Reject
            await db.productRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "rejected",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes
                }}
            )
            
            logger.info(f"Admin {admin['email']} rejected product request: {request['productName']}")
            return {"message": "Product request rejected"}
    
    # ==================== SELLER: REQUEST NEW CATEGORY ====================
    
    @router.post("/seller/requests/category")
    async def request_category(
        data: CategoryRequest,
        seller: dict = Depends(require_verified_seller)
    ):
        """Submit a request for a new category"""
        seller_id = str(seller["_id"])
        
        # Check for duplicate pending request
        existing = await db.categoryRequests.find_one({
            "categoryName": {"$regex": f"^{data.categoryName}$", "$options": "i"},
            "status": "pending"
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A request for this category is already pending review"
            )
        
        # Check if category already exists
        exists = await db.categories.find_one({
            "name": {"$regex": f"^{data.categoryName}$", "$options": "i"}
        })
        if exists:
            raise HTTPException(
                status_code=400,
                detail="This category already exists"
            )
        
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "categoryName": data.categoryName,
            "description": data.description,
            "reason": data.reason,
            "requestedBy": seller_id,
            "requestedByEmail": seller.get("email"),
            "status": "pending",
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.categoryRequests.insert_one(doc)
        
        logger.info(f"Seller {seller['email']} requested category: {data.categoryName}")
        return {
            "message": "Category request submitted for admin review",
            "request": serialize_mongo_doc(doc)
        }
    
    @router.get("/seller/requests/category")
    async def get_my_category_requests(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None)
    ):
        """Get seller's category requests"""
        query = {"requestedBy": str(seller["_id"])}
        if status:
            query["status"] = status
        
        requests = await db.categoryRequests.find(query).sort("createdAt", -1).to_list(50)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests]}
    
    # ==================== SELLER: REQUEST NEW SPEC FIELD ====================
    
    @router.post("/seller/requests/spec-field")
    async def request_spec_field(
        data: SpecFieldRequest,
        seller: dict = Depends(require_verified_seller)
    ):
        """Submit a request for a new specification field"""
        seller_id = str(seller["_id"])
        
        # Validate category exists
        try:
            category = await db.categories.find_one({"_id": ObjectId(data.categoryId)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Check for duplicate pending request
        existing = await db.specFieldRequests.find_one({
            "categoryId": data.categoryId,
            "fieldName": {"$regex": f"^{data.fieldName}$", "$options": "i"},
            "status": "pending"
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A request for this specification field is already pending review"
            )
        
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "categoryId": data.categoryId,
            "categoryName": category.get("name"),
            "fieldName": data.fieldName,
            "fieldType": data.fieldType,
            "suggestedOptions": data.suggestedOptions,
            "unit": data.unit,
            "reason": data.reason,
            "requestedBy": seller_id,
            "requestedByEmail": seller.get("email"),
            "status": "pending",
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.specFieldRequests.insert_one(doc)
        
        logger.info(f"Seller {seller['email']} requested spec field: {data.fieldName} for category {category.get('name')}")
        return {
            "message": "Specification field request submitted for admin review",
            "request": serialize_mongo_doc(doc)
        }
    
    @router.get("/seller/requests/spec-field")
    async def get_my_spec_field_requests(
        seller: dict = Depends(require_verified_seller),
        status: Optional[str] = Query(None)
    ):
        """Get seller's spec field requests"""
        query = {"requestedBy": str(seller["_id"])}
        if status:
            query["status"] = status
        
        requests = await db.specFieldRequests.find(query).sort("createdAt", -1).to_list(50)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests]}
    
    # ==================== ADMIN: REVIEW CATEGORY REQUESTS ====================
    
    @router.get("/admin/requests/categories")
    async def list_category_requests(
        admin: dict = Depends(require_admin),
        status: str = Query("pending")
    ):
        """List category requests (admin only)"""
        query = {"status": status} if status != "all" else {}
        
        requests = await db.categoryRequests.find(query)\
            .sort("createdAt", -1)\
            .to_list(100)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests], "total": len(requests)}
    
    @router.post("/admin/requests/categories/{request_id}/review")
    async def review_category_request(
        request_id: str,
        review: RequestReview,
        admin: dict = Depends(require_admin)
    ):
        """Approve or reject a category request (admin only)"""
        try:
            request = await db.categoryRequests.find_one({"_id": ObjectId(request_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request ID")
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if request.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Request has already been reviewed")
        
        now = datetime.now(timezone.utc)
        
        if review.status == "approved":
            # Create the category
            cat_doc = {
                "_id": ObjectId(),
                "name": request["categoryName"],
                "description": request.get("description"),
                "icon": None,
                "image": None,
                "displayOrder": 0,
                "settings": {
                    "allowedUnits": ["pcs"],
                    "defaultUnit": "pcs",
                    "allowedSellerTypes": ["manufacturer", "distributor", "dealer"],
                    "dimensionsEnabled": False,
                    "dimensionUnits": ["mm", "cm"],
                    "dimensionFormat": None,
                    "dropdownOverrides": {}
                },
                "isActive": True,
                "createdAt": now,
                "createdBy": admin["_id"],
                "createdFromRequestId": request_id,
                "updatedAt": now
            }
            await db.categories.insert_one(cat_doc)
            
            # Update request
            await db.categoryRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "approved",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes,
                    "createdCategoryId": str(cat_doc["_id"])
                }}
            )
            
            logger.info(f"Admin {admin['email']} approved category request: {request['categoryName']}")
            return {
                "message": "Category request approved and category created",
                "category": serialize_mongo_doc(cat_doc)
            }
        else:
            # Reject
            await db.categoryRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "rejected",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes
                }}
            )
            
            logger.info(f"Admin {admin['email']} rejected category request: {request['categoryName']}")
            return {"message": "Category request rejected"}
    
    # ==================== ADMIN: REVIEW SPEC FIELD REQUESTS ====================
    
    @router.get("/admin/requests/spec-fields")
    async def list_spec_field_requests(
        admin: dict = Depends(require_admin),
        status: str = Query("pending")
    ):
        """List spec field requests (admin only)"""
        query = {"status": status} if status != "all" else {}
        
        requests = await db.specFieldRequests.find(query)\
            .sort("createdAt", -1)\
            .to_list(100)
        
        return {"requests": [serialize_mongo_doc(r) for r in requests], "total": len(requests)}
    
    @router.post("/admin/requests/spec-fields/{request_id}/review")
    async def review_spec_field_request(
        request_id: str,
        review: RequestReview,
        admin: dict = Depends(require_admin)
    ):
        """Approve or reject a spec field request (admin only)"""
        try:
            request = await db.specFieldRequests.find_one({"_id": ObjectId(request_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request ID")
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if request.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Request has already been reviewed")
        
        now = datetime.now(timezone.utc)
        
        if review.status == "approved":
            # Find or create spec template for the category
            template = await db.specTemplates.find_one({
                "categoryId": ObjectId(request["categoryId"]),
                "isActive": {"$ne": False}
            })
            
            # Create the field key from name
            import re
            field_key = re.sub(r'[^a-z0-9_]', '_', request["fieldName"].lower())
            field_key = re.sub(r'_+', '_', field_key).strip('_')
            
            new_field = {
                "key": field_key,
                "label": request["fieldName"],
                "fieldType": request.get("fieldType", "text"),
                "unit": request.get("unit"),
                "isMandatory": False,
                "isSellerEditable": True,
                "isLockedAfterCreate": False,
                "displayOrder": 100,  # Add at end
                "options": request.get("suggestedOptions") if request.get("fieldType") == "dropdown" else None,
                "placeholder": f"Enter {request['fieldName']}",
                "helpText": None
            }
            
            if template:
                # Add field to existing template
                await db.specTemplates.update_one(
                    {"_id": template["_id"]},
                    {
                        "$push": {"fields": new_field},
                        "$inc": {"version": 1},
                        "$set": {"updatedAt": now}
                    }
                )
            else:
                # Create new template
                template_doc = {
                    "_id": ObjectId(),
                    "name": f"{request.get('categoryName', 'Custom')} Specifications",
                    "categoryId": ObjectId(request["categoryId"]),
                    "description": "Auto-created from spec field request",
                    "fields": [new_field],
                    "version": 1,
                    "isActive": True,
                    "createdAt": now,
                    "createdBy": admin["_id"],
                    "updatedAt": now
                }
                await db.specTemplates.insert_one(template_doc)
            
            # Update request
            await db.specFieldRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "approved",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes,
                    "createdFieldKey": field_key
                }}
            )
            
            logger.info(f"Admin {admin['email']} approved spec field request: {request['fieldName']}")
            return {
                "message": "Spec field request approved and field added to template",
                "field_key": field_key
            }
        else:
            # Reject
            await db.specFieldRequests.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {
                    "status": "rejected",
                    "reviewedBy": str(admin["_id"]),
                    "reviewedAt": now,
                    "adminNotes": review.adminNotes
                }}
            )
            
            logger.info(f"Admin {admin['email']} rejected spec field request: {request['fieldName']}")
            return {"message": "Spec field request rejected"}
    
    return router
