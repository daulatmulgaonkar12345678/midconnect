"""
REVIEWS ROUTER
==============
Handles all review-related endpoints for the seller listing reviews system.

Features:
- Review submission with eligibility check (inquiry must be accepted)
- Review retrieval by seller listing
- Average rating computation (backend-side)
- Eligibility check endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from bson import ObjectId
from datetime import datetime, timezone
import logging

logger = logging.getLogger("reviews")


class ReviewCreate(BaseModel):
    """Create a new review"""
    sellerListingId: str = Field(..., description="Seller listing being reviewed")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5 stars")
    reviewText: Optional[str] = Field(None, max_length=1000, description="Review text")


class ReviewResponse(BaseModel):
    """Review response model"""
    _id: str
    sellerListingId: str
    productId: str
    sellerId: str
    buyerId: str
    buyerName: str
    rating: int
    reviewText: Optional[str]
    createdAt: str


def create_reviews_router(db, get_current_user):
    """Factory function to create reviews router with database dependency."""
    
    router = APIRouter(prefix="/reviews", tags=["reviews"])
    
    # ==================== COLLECTION SETUP ====================
    
    async def ensure_reviews_collection():
        """Create reviews collection with proper indexes if not exists."""
        collections = await db.list_collection_names()
        
        if "reviews" not in collections:
            await db.create_collection("reviews")
            logger.info("Created reviews collection")
        
        # Create unique index to prevent duplicate reviews
        try:
            await db.reviews.create_index(
                [("buyerId", 1), ("sellerListingId", 1)],
                unique=True,
                name="unique_buyer_listing_review"
            )
            logger.info("Created unique index on reviews (buyerId, sellerListingId)")
        except Exception as e:
            # Index might already exist
            logger.debug(f"Index creation skipped: {e}")
        
        # Create index for fast lookup by listing
        try:
            await db.reviews.create_index(
                [("sellerListingId", 1)],
                name="idx_reviews_listing"
            )
        except Exception:
            pass
    
    # ==================== ELIGIBILITY CHECK ====================
    
    @router.get("/eligible")
    async def check_review_eligibility(
        sellerListingId: str,
        current_user = Depends(get_current_user)
    ):
        """
        Check if buyer is eligible to write a review.
        
        Eligibility requires:
        1. User has an accepted inquiry for this seller+product
        2. User hasn't already reviewed this listing
        """
        await ensure_reviews_collection()
        
        buyer_id = current_user.get("_id") or current_user.get("id")
        if not buyer_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        try:
            buyer_oid = ObjectId(buyer_id)
            listing_oid = ObjectId(sellerListingId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get the listing to find sellerId and productId
        listing = await db.sellerListings.find_one({"_id": listing_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        seller_id = listing.get("sellerId")
        product_id = listing.get("productId")
        
        # Check 1: Has accepted inquiry
        accepted_inquiry = await db.inquiries.find_one({
            "buyerId": buyer_oid,
            "sellerId": seller_id,
            "productId": product_id,
            "status": "accepted"
        })
        
        if not accepted_inquiry:
            return {
                "eligible": False,
                "reason": "no_accepted_inquiry",
                "message": "You need an accepted inquiry to review this seller"
            }
        
        # Check 2: Not already reviewed
        existing_review = await db.reviews.find_one({
            "buyerId": buyer_oid,
            "sellerListingId": listing_oid
        })
        
        if existing_review:
            return {
                "eligible": False,
                "reason": "already_reviewed",
                "message": "You have already reviewed this listing"
            }
        
        return {
            "eligible": True,
            "reason": None,
            "message": "You can write a review for this listing"
        }
    
    # ==================== CREATE REVIEW ====================
    
    @router.post("")
    async def create_review(
        data: ReviewCreate,
        current_user = Depends(get_current_user)
    ):
        """
        Create a new review for a seller listing.
        
        Requirements:
        - User must have an accepted inquiry
        - User hasn't already reviewed this listing
        - Rating must be 1-5
        """
        await ensure_reviews_collection()
        
        buyer_id = current_user.get("_id") or current_user.get("id")
        buyer_name = current_user.get("displayName") or current_user.get("name") or "Anonymous Buyer"
        
        if not buyer_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        try:
            buyer_oid = ObjectId(buyer_id)
            listing_oid = ObjectId(data.sellerListingId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Get listing details
        listing = await db.sellerListings.find_one({"_id": listing_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        seller_id = listing.get("sellerId")
        product_id = listing.get("productId")
        
        # Validate eligibility
        accepted_inquiry = await db.inquiries.find_one({
            "buyerId": buyer_oid,
            "sellerId": seller_id,
            "productId": product_id,
            "status": "accepted"
        })
        
        if not accepted_inquiry:
            raise HTTPException(
                status_code=403,
                detail="You must have an accepted inquiry to review this seller"
            )
        
        # Create review document
        review_doc = {
            "sellerListingId": listing_oid,
            "productId": product_id if isinstance(product_id, ObjectId) else ObjectId(product_id),
            "sellerId": seller_id if isinstance(seller_id, ObjectId) else ObjectId(seller_id),
            "buyerId": buyer_oid,
            "buyerName": buyer_name,
            "rating": data.rating,
            "reviewText": data.reviewText.strip() if data.reviewText else None,
            "createdAt": datetime.now(timezone.utc)
        }
        
        try:
            result = await db.reviews.insert_one(review_doc)
            logger.info(f"Review created: {result.inserted_id} by buyer {buyer_id}")
            
            # Update aggregated rating in sellerListing for performance
            await update_listing_rating_stats(listing_oid)
            
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise HTTPException(
                    status_code=409,
                    detail="You have already reviewed this listing"
                )
            logger.error(f"Failed to create review: {e}")
            raise HTTPException(status_code=500, detail="Failed to create review")
        
        return {
            "success": True,
            "reviewId": str(result.inserted_id),
            "message": "Review submitted successfully"
        }
    
    # ==================== RATING AGGREGATION ====================
    
    async def update_listing_rating_stats(listing_id: ObjectId):
        """
        Update aggregated rating stats in sellerListing document.
        
        This stores avgRating and totalReviews directly in the listing
        for efficient querying without aggregation on every request.
        
        Called when:
        - New review is created
        - Review is updated or deleted (future feature)
        """
        try:
            # Calculate current stats from reviews
            cursor = db.reviews.find({"sellerListingId": listing_id})
            reviews = await cursor.to_list(1000)
            
            total_reviews = len(reviews)
            avg_rating = 0
            
            if total_reviews > 0:
                total_rating = sum(r.get("rating", 0) for r in reviews)
                avg_rating = round(total_rating / total_reviews, 1)
            
            # Update listing with aggregated stats
            await db.sellerListings.update_one(
                {"_id": listing_id},
                {"$set": {
                    "avgRating": avg_rating,
                    "totalReviews": total_reviews,
                    "lastReviewAt": datetime.now(timezone.utc) if total_reviews > 0 else None
                }}
            )
            
            logger.info(f"Updated rating stats for listing {listing_id}: avg={avg_rating}, count={total_reviews}")
            
        except Exception as e:
            logger.error(f"Failed to update rating stats for listing {listing_id}: {e}")
    
    # ==================== GET REVIEWS FOR LISTING ====================
    
    @router.get("/listing/{sellerListingId}")
    async def get_listing_reviews(sellerListingId: str):
        """
        Get all reviews for a seller listing.
        
        Returns:
        - Reviews list
        - Average rating (computed server-side)
        - Total review count
        """
        await ensure_reviews_collection()
        
        try:
            listing_oid = ObjectId(sellerListingId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # Fetch reviews
        cursor = db.reviews.find(
            {"sellerListingId": listing_oid}
        ).sort("createdAt", -1)
        
        reviews = await cursor.to_list(100)
        
        # Compute average rating server-side
        total_rating = sum(r.get("rating", 0) for r in reviews)
        total_reviews = len(reviews)
        avg_rating = round(total_rating / total_reviews, 1) if total_reviews > 0 else 0
        
        # Format response
        formatted_reviews = []
        for review in reviews:
            formatted_reviews.append({
                "_id": str(review["_id"]),
                "sellerListingId": str(review["sellerListingId"]),
                "productId": str(review["productId"]),
                "sellerId": str(review["sellerId"]),
                "buyerId": str(review["buyerId"]),
                "buyerName": review.get("buyerName", "Anonymous"),
                "rating": review["rating"],
                "reviewText": review.get("reviewText"),
                "createdAt": review["createdAt"].isoformat() if review.get("createdAt") else None
            })
        
        return {
            "reviews": formatted_reviews,
            "avgRating": avg_rating,
            "totalReviews": total_reviews
        }
    
    # ==================== GET SELLER LISTING DETAILS ====================
    
    @router.get("/seller-listing/{sellerListingId}/details")
    async def get_seller_listing_details(sellerListingId: str):
        """
        Get full details for a specific seller listing.
        
        Returns:
        - Product (master data)
        - Seller Listing (media + commercial)
        - Seller Profile
        - Reviews
        - Average Rating
        """
        await ensure_reviews_collection()
        
        try:
            listing_oid = ObjectId(sellerListingId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        # Get seller listing
        listing = await db.sellerListings.find_one({"_id": listing_oid})
        if not listing:
            raise HTTPException(status_code=404, detail="Seller listing not found")
        
        # Get product
        product_id = listing.get("productId")
        product = None
        if product_id:
            try:
                product_oid = ObjectId(product_id) if isinstance(product_id, str) else product_id
                product = await db.products.find_one({"_id": product_oid})
            except Exception:
                pass
        
        # Get seller profile from users collection (where profile data is stored)
        seller_id = listing.get("sellerId")
        seller = None
        seller_profile = {}
        if seller_id:
            try:
                seller_oid = ObjectId(seller_id) if isinstance(seller_id, str) else seller_id
                # First try users collection (main profile storage)
                seller = await db.users.find_one({"_id": seller_oid})
                if seller:
                    # Profile data is nested under 'profile' in users collection
                    profile = seller.get("profile", {})
                    seller_profile = {
                        "_id": str(seller["_id"]),
                        "businessName": profile.get("businessName") or seller.get("businessName") or "Verified Seller",
                        "city": profile.get("city") or seller.get("city"),
                        "state": profile.get("state") or seller.get("state"),
                        "badgeType": seller.get("badgeType", "none"),
                        "gstNumber": profile.get("gstNumber") or seller.get("gst", {}).get("number"),
                        "establishedYear": profile.get("establishedYear") or seller.get("enterpriseEstablishmentYear"),
                        "sellerSlug": seller.get("sellerSlug")  # For clickable seller name
                    }
                else:
                    # Fallback to sellers collection (legacy)
                    seller = await db.sellers.find_one({"_id": seller_oid})
                    if seller:
                        seller_profile = {
                            "_id": str(seller["_id"]),
                            "businessName": seller.get("businessName") or "Verified Seller",
                            "city": seller.get("city"),
                            "state": seller.get("state"),
                            "badgeType": seller.get("badgeType", "none"),
                            "gstNumber": seller.get("gst", {}).get("number") if seller.get("gst") else None,
                            "establishedYear": seller.get("establishedYear"),
                            "sellerSlug": seller.get("sellerSlug")
                        }
            except Exception as e:
                logger.error(f"Error fetching seller profile: {e}")
        
        # Default seller profile if nothing found
        if not seller_profile:
            seller_profile = {
                "_id": str(seller_id) if seller_id else None,
                "businessName": "Verified Seller",
                "city": None,
                "state": None,
                "badgeType": "none",
                "gstNumber": None,
                "establishedYear": None,
                "sellerSlug": None
            }
        
        # Get category
        category = None
        if product and product.get("categoryId"):
            try:
                cat_oid = ObjectId(product["categoryId"]) if isinstance(product["categoryId"], str) else product["categoryId"]
                category = await db.categories.find_one({"_id": cat_oid})
            except Exception:
                pass
        
        # Get reviews
        cursor = db.reviews.find({"sellerListingId": listing_oid}).sort("createdAt", -1)
        reviews = await cursor.to_list(50)
        
        # Compute rating
        total_rating = sum(r.get("rating", 0) for r in reviews)
        total_reviews = len(reviews)
        avg_rating = round(total_rating / total_reviews, 1) if total_reviews > 0 else 0
        
        # Format response
        def serialize_oid(doc):
            if not doc:
                return None
            result = {}
            for k, v in doc.items():
                if isinstance(v, ObjectId):
                    result[k] = str(v)
                elif isinstance(v, datetime):
                    result[k] = v.isoformat()
                elif isinstance(v, dict):
                    result[k] = serialize_oid(v)
                elif isinstance(v, list):
                    result[k] = [serialize_oid(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v]
                else:
                    result[k] = v
            return result
        
        return {
            "product": serialize_oid(product),
            "sellerListing": serialize_oid(listing),
            "seller": seller_profile,
            "category": {
                "_id": str(category["_id"]) if category else None,
                "name": category.get("name") if category else None,
                "slug": category.get("slug") if category else None
            } if category else None,
            "reviews": [
                {
                    "_id": str(r["_id"]),
                    "buyerName": r.get("buyerName", "Anonymous"),
                    "rating": r["rating"],
                    "reviewText": r.get("reviewText"),
                    "createdAt": r["createdAt"].isoformat() if r.get("createdAt") else None
                }
                for r in reviews
            ],
            "avgRating": avg_rating,
            "totalReviews": total_reviews
        }
    
    return router
