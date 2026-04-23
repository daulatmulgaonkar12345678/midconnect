"""
Seller Catalog Router
=====================

Public-facing seller catalog pages for buyers to browse seller products.

Endpoints:
- GET /api/seller-catalog/{slug} - Get seller catalog with products by category
- GET /api/seller-catalog/{slug}/category/{category_slug} - Get products for specific category
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller-catalog", tags=["Seller Catalog"])


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_doc(value)
            elif isinstance(value, list):
                result[key] = serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug (matches frontend slugify behavior)."""
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


async def get_seller_by_slug(db, slug: str) -> Optional[Dict]:
    """
    Get seller by slug.
    Falls back to legacy sellers collection, then ObjectId lookup if slug not found.
    """
    # First try by slug in users collection
    seller = await db.users.find_one({
        "sellerSlug": slug,
        "roles": "seller",
        "accountStatus": "active"
    })
    
    if seller:
        return seller
    
    # Fallback: try legacy sellers collection
    seller = await db.sellers.find_one({
        "sellerSlug": slug
    })
    
    if seller:
        # Add accountStatus for compatibility
        seller["accountStatus"] = seller.get("accountStatus", "active")
        return seller
    
    # Fallback: try by ObjectId in users
    try:
        seller = await db.users.find_one({
            "_id": ObjectId(slug),
            "roles": "seller",
            "accountStatus": "active"
        })
        if seller:
            return seller
    except Exception:
        pass
    
    # Fallback: try by ObjectId in legacy sellers
    try:
        seller = await db.sellers.find_one({
            "_id": ObjectId(slug)
        })
        if seller:
            seller["accountStatus"] = seller.get("accountStatus", "active")
            return seller
    except Exception:
        pass

    # Fallback: match slugified companyName / sellerName / displayName for sellers with null sellerSlug
    # Iterate through active sellers that have no sellerSlug and compare slugified names
    name_fields = ["companyName", "sellerName", "displayName", "name", "fullName"]
    cursor = db.users.find(
        {
            "roles": "seller",
            "accountStatus": "active",
            "$or": [{"sellerSlug": None}, {"sellerSlug": {"$exists": False}}, {"sellerSlug": ""}],
        },
        {f: 1 for f in name_fields}
    )
    async for candidate in cursor:
        for field in name_fields:
            value = candidate.get(field)
            if value and _slugify(value) == slug:
                # Backfill the slug for future fast lookups
                try:
                    await db.users.update_one(
                        {"_id": candidate["_id"]},
                        {"$set": {"sellerSlug": slug}}
                    )
                except Exception:
                    pass
                full = await db.users.find_one({"_id": candidate["_id"]})
                if full:
                    return full
    return None


async def calculate_seller_rating(db, seller_id: ObjectId) -> Dict:
    """
    Calculate overall seller rating from all product reviews.
    
    Returns:
        {
            "avgRating": float,
            "totalReviews": int,
            "ratingDistribution": {1: int, 2: int, 3: int, 4: int, 5: int}
        }
    """
    # Get all listings for this seller
    listings = await db.sellerListings.find(
        {"sellerId": seller_id, "status": "active"},
        {"_id": 1}
    ).to_list(1000)
    
    listing_ids = [listing["_id"] for listing in listings]
    
    if not listing_ids:
        return {
            "avgRating": 0,
            "totalReviews": 0,
            "ratingDistribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }
    
    # Get all reviews for these listings
    pipeline = [
        {"$match": {"listingId": {"$in": listing_ids}}},
        {"$group": {
            "_id": None,
            "avgRating": {"$avg": "$rating"},
            "totalReviews": {"$sum": 1},
            "ratings": {"$push": "$rating"}
        }}
    ]
    
    result = await db.reviews.aggregate(pipeline).to_list(1)
    
    if not result:
        return {
            "avgRating": 0,
            "totalReviews": 0,
            "ratingDistribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }
    
    data = result[0]
    
    # Calculate rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in data.get("ratings", []):
        if rating in distribution:
            distribution[rating] += 1
    
    return {
        "avgRating": round(data.get("avgRating", 0), 1),
        "totalReviews": data.get("totalReviews", 0),
        "ratingDistribution": distribution
    }


async def get_seller_products_by_category(
    db,
    seller_id: ObjectId,
    products_per_category: int = 4,
    random_order: bool = True
) -> List[Dict]:
    """
    Get seller's products grouped by category with rotation.
    
    Returns list of categories with their products.
    Each category has max `products_per_category` products.
    Products are fetched in random order for fair visibility.
    """
    # Aggregation pipeline to get products grouped by category
    pipeline = [
        # Match active listings for this seller
        {"$match": {
            "sellerId": seller_id,
            "status": "active"
        }},
        # Lookup product info
        {"$lookup": {
            "from": "products",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": "$product"},
        # Lookup category info
        {"$lookup": {
            "from": "categories",
            "localField": "product.categoryId",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        # Add random sort for rotation
        {"$addFields": {"randomSort": {"$rand": {}}}},
        {"$sort": {"randomSort": 1}} if random_order else {"$sort": {"createdAt": -1}},
        # Group by category
        {"$group": {
            "_id": "$category._id",
            "categoryName": {"$first": "$category.name"},
            "categorySlug": {"$first": "$category.slug"},
            "categoryIcon": {"$first": "$category.icon"},
            "products": {"$push": {
                "listingId": "$_id",
                "productId": "$productId",
                "productName": "$product.name",
                "productSlug": "$product.slug",
                "description": "$description",
                "images": "$images",
                "pricingSlabs": "$pricingSlabs",
                "moq": "$moq",
                "avgRating": {"$ifNull": ["$avgRating", 0]},
                "totalReviews": {"$ifNull": ["$totalReviews", 0]},
                "stockStatus": "$stockStatus"
            }}
        }},
        # Limit products per category
        {"$project": {
            "categoryId": "$_id",
            "categoryName": 1,
            "categorySlug": 1,
            "categoryIcon": 1,
            "products": {"$slice": ["$products", products_per_category]},
            "totalProducts": {"$size": "$products"}
        }},
        # Sort categories by total products (show most active categories first)
        {"$sort": {"totalProducts": -1}}
    ]
    
    categories = await db.sellerListings.aggregate(pipeline).to_list(100)
    
    return categories


async def calculate_category_rating(db, seller_id: ObjectId, category_id: ObjectId) -> Dict:
    """Calculate rating for a specific category for this seller."""
    # Get listings in this category
    pipeline = [
        {"$match": {"sellerId": seller_id, "status": "active"}},
        {"$lookup": {
            "from": "products",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": "$product"},
        {"$match": {"product.categoryId": category_id}},
        {"$project": {"_id": 1}}
    ]
    
    listings = await db.sellerListings.aggregate(pipeline).to_list(1000)
    listing_ids = [listing["_id"] for listing in listings]
    
    if not listing_ids:
        return {"avgRating": 0, "totalReviews": 0}
    
    # Get reviews
    review_pipeline = [
        {"$match": {"listingId": {"$in": listing_ids}}},
        {"$group": {
            "_id": None,
            "avgRating": {"$avg": "$rating"},
            "totalReviews": {"$sum": 1}
        }}
    ]
    
    result = await db.reviews.aggregate(review_pipeline).to_list(1)
    
    if not result:
        return {"avgRating": 0, "totalReviews": 0}
    
    return {
        "avgRating": round(result[0].get("avgRating", 0), 1),
        "totalReviews": result[0].get("totalReviews", 0)
    }


def init_seller_catalog_routes(app_db):
    """Initialize routes with database reference."""
    db = app_db
    
    @router.get("/{slug}")
    async def get_seller_catalog(
        slug: str,
        products_per_category: int = Query(4, ge=1, le=500)
    ):
        """
        Get seller catalog page data.
        
        Returns:
        - Seller profile (company name, logo, location, badges, ratings)
        - Products grouped by category
        - Category-wise ratings
        
        Products are rotated randomly for fair visibility.
        """
        # Get seller
        seller = await get_seller_by_slug(db, slug)
        
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        seller_id = seller["_id"]
        
        # Get seller rating
        rating_data = await calculate_seller_rating(db, seller_id)
        
        # Get products by category
        categories = await get_seller_products_by_category(
            db, seller_id, products_per_category
        )
        
        # Add category ratings
        for cat in categories:
            if cat.get("categoryId"):
                cat_rating = await calculate_category_rating(
                    db, seller_id, cat["categoryId"]
                )
                cat["avgRating"] = cat_rating["avgRating"]
                cat["totalReviews"] = cat_rating["totalReviews"]
        
        # Build response
        # Handle both users collection (profile nested) and legacy sellers (flat structure)
        profile = seller.get("profile", {})
        
        # For legacy sellers, use flat structure
        company_name = profile.get("businessName") or seller.get("businessName")
        city = profile.get("city") or seller.get("city")
        state = profile.get("state") or seller.get("state")
        address = profile.get("address") or seller.get("address")
        phone = profile.get("phone") or seller.get("phone")
        
        response = {
            "seller": {
                "id": str(seller_id),
                "slug": seller.get("sellerSlug"),
                "companyName": company_name,
                "logo": seller.get("logo"),
                "bannerImage": seller.get("sellerBannerImage"),
                "location": {
                    "city": city,
                    "state": state,
                    "address": address
                },
                "phone": phone,
                "email": seller.get("email"),
                "enterpriseEstablishmentYear": seller.get("enterpriseEstablishmentYear"),
                "platformRegistrationYear": seller.get("platformRegistrationYear"),
                "gstVerified": seller.get("gst", {}).get("verified", False),
                "badgeType": seller.get("badgeType"),
                "rating": rating_data
            },
            "categories": serialize_doc(categories),
            "totalCategories": len(categories),
            "totalProducts": sum(cat.get("totalProducts", 0) for cat in categories)
        }
        
        return serialize_doc(response)
    
    
    @router.get("/{slug}/category/{category_slug}")
    async def get_seller_category_products(
        slug: str,
        category_slug: str,
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100)
    ):
        """
        Get all products for a specific category from a seller.
        
        Used when user clicks "View All" in a category section.
        Supports pagination.
        """
        # Get seller
        seller = await get_seller_by_slug(db, slug)
        
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        seller_id = seller["_id"]
        
        # Get category
        category = await db.categories.find_one({"slug": category_slug})
        
        if not category:
            # Try by ObjectId
            try:
                category = await db.categories.find_one({"_id": ObjectId(category_slug)})
            except Exception:
                pass
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        category_id = category["_id"]
        
        # Get products
        pipeline = [
            {"$match": {"sellerId": seller_id, "status": "active"}},
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "product"
            }},
            {"$unwind": "$product"},
            {"$match": {"product.categoryId": category_id}},
            {"$addFields": {"randomSort": {"$rand": {}}}},
            {"$sort": {"randomSort": 1}},
            {"$skip": skip},
            {"$limit": limit},
            {"$project": {
                "listingId": "$_id",
                "productId": "$productId",
                "productName": "$product.name",
                "productSlug": "$product.slug",
                "description": "$description",
                "images": "$images",
                "pricingSlabs": "$pricingSlabs",
                "moq": "$moq",
                "avgRating": {"$ifNull": ["$avgRating", 0]},
                "totalReviews": {"$ifNull": ["$totalReviews", 0]},
                "stockStatus": "$stockStatus"
            }}
        ]
        
        products = await db.sellerListings.aggregate(pipeline).to_list(limit)
        
        # Get total count
        count_pipeline = [
            {"$match": {"sellerId": seller_id, "status": "active"}},
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "product"
            }},
            {"$unwind": "$product"},
            {"$match": {"product.categoryId": category_id}},
            {"$count": "total"}
        ]
        
        count_result = await db.sellerListings.aggregate(count_pipeline).to_list(1)
        total = count_result[0]["total"] if count_result else 0
        
        # Get category rating
        cat_rating = await calculate_category_rating(db, seller_id, category_id)
        
        return serialize_doc({
            "category": {
                "id": str(category_id),
                "name": category.get("name"),
                "slug": category.get("slug"),
                "icon": category.get("icon"),
                "avgRating": cat_rating["avgRating"],
                "totalReviews": cat_rating["totalReviews"]
            },
            "products": products,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "hasMore": skip + limit < total
            }
        })
    
    
    @router.get("/by-id/{seller_id}")
    async def get_seller_catalog_by_id(
        seller_id: str,
        products_per_category: int = Query(4, ge=1, le=500)
    ):
        """
        Get seller catalog by seller ID (ObjectId).
        Redirects to slug-based URL for SEO.
        """
        try:
            seller = await db.users.find_one({
                "_id": ObjectId(seller_id),
                "roles": "seller",
                "accountStatus": "active"
            })
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid seller ID")
        
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        seller_slug = seller.get("sellerSlug")
        
        if seller_slug:
            # Return redirect info
            return {
                "redirect": True,
                "slug": seller_slug,
                "redirectUrl": f"/seller/{seller_slug}"
            }
        
        # If no slug, generate one
        profile = seller.get("profile", {})
        business_name = profile.get("businessName", "")
        
        if business_name:
            from server import generate_seller_slug
            new_slug = generate_seller_slug(business_name)
            
            # Check uniqueness
            existing = await db.users.find_one({"sellerSlug": new_slug})
            if existing:
                counter = 2
                while True:
                    test_slug = f"{new_slug}-{counter}"
                    exists = await db.users.find_one({"sellerSlug": test_slug})
                    if not exists:
                        new_slug = test_slug
                        break
                    counter += 1
            
            # Update seller with new slug
            await db.users.update_one(
                {"_id": seller["_id"]},
                {"$set": {"sellerSlug": new_slug}}
            )
            
            return {
                "redirect": True,
                "slug": new_slug,
                "redirectUrl": f"/seller/{new_slug}"
            }
        
        raise HTTPException(status_code=500, detail="Unable to generate seller URL")
    
    
    return router
