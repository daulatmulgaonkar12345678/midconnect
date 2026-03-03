"""
CITY SEO SERVICE
================
City-based SEO page generation and management.

Enterprise Rule:
City page only exists if sellers exist in that city.

This service:
1. Validates city page eligibility
2. Generates city-specific SEO content
3. Provides city page data
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

logger = logging.getLogger("city_seo_service")


class CitySEOService:
    """
    City-based SEO page service.
    
    Creates city pages only when:
    1. Product has active sellers in that city
    2. Sufficient search demand (optional)
    
    URL Pattern:
    /products/{product-slug}/{city-slug}
    
    Example:
    /products/industrial-motor-supplier-india/mumbai
    """
    
    SITE_URL = "https://www.udyogconnect.in"
    
    # Major cities for SEO
    MAJOR_CITIES = [
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad",
        "Pune", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Kanpur",
        "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Vadodara",
        "Coimbatore", "Ludhiana", "Rajkot", "Faridabad", "Ghaziabad"
    ]
    
    def __init__(self, db):
        self.db = db
    
    @staticmethod
    def normalize_city(city: str) -> str:
        """Normalize city name for matching."""
        if not city:
            return ""
        return city.lower().strip()
    
    @staticmethod
    def generate_city_slug(city: str) -> str:
        """Generate SEO-friendly city slug."""
        if not city:
            return ""
        slug = city.lower().strip()
        slug = re.sub(r'[^a-z0-9\s]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        return slug.strip('-')
    
    async def check_city_page_eligibility(
        self,
        product_id: ObjectId,
        city: str
    ) -> Tuple[bool, int]:
        """
        Check if city page should exist for this product.
        
        Returns:
            (is_eligible, seller_count)
        """
        normalized_city = self.normalize_city(city)
        
        if not normalized_city:
            return False, 0
        
        # Count active sellers in this city
        seller_count = await self.db.sellerListings.count_documents({
            "productId": product_id,
            "status": "active",
            "$or": [
                {"city": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                {"sellerCity": {"$regex": f"^{normalized_city}$", "$options": "i"}}
            ]
        })
        
        # City page eligible if at least 1 seller
        return seller_count > 0, seller_count
    
    async def get_city_page_data(
        self,
        product_slug: str,
        city: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get data for city-specific product page.
        
        Returns None if city page should not exist.
        """
        normalized_city = self.normalize_city(city)
        city_slug = self.generate_city_slug(city)
        
        # Get product
        product = await self.db.products.find_one(
            {"slug": product_slug},
            {
                "_id": 1,
                "name": 1,
                "slug": 1,
                "categoryId": 1,
                "categoryName": 1,
                "seoTitle": 1,
                "seoDescription": 1
            }
        )
        
        if not product:
            return None
        
        # Check eligibility
        is_eligible, seller_count = await self.check_city_page_eligibility(
            product["_id"], city
        )
        
        if not is_eligible:
            return None
        
        # Get city-specific sellers
        sellers = await self.db.sellerListings.aggregate([
            {"$match": {
                "productId": product["_id"],
                "status": "active",
                "$or": [
                    {"city": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                    {"sellerCity": {"$regex": f"^{normalized_city}$", "$options": "i"}}
                ]
            }},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "_id": 1,
                "sellerId": 1,
                "pricingTiers": 1,
                "moq": 1,
                "leadTime": 1,
                "stock": 1,
                "images": {"$slice": ["$images", 2]},
                "companyName": {"$ifNull": ["$seller.profile.businessName", "Verified Seller"]},
                "badgeType": {"$ifNull": ["$seller.badgeType", "none"]}
            }},
            {"$limit": 50}
        ]).to_list(50)
        
        # Convert ObjectIds to strings in sellers
        for s in sellers:
            if "_id" in s:
                s["_id"] = str(s["_id"])
            if "sellerId" in s:
                s["sellerId"] = str(s["sellerId"])
        
        # Calculate price stats
        prices = []
        for s in sellers:
            for tier in s.get("pricingTiers", []):
                price = tier.get("pricePerUnit") or tier.get("price")
                if price:
                    prices.append(float(price))
        
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        
        # Generate city-specific SEO
        product_name = product.get("name", "Product")
        city_title = city.title()
        
        seo_title = f"Buy {product_name} in {city_title} | {seller_count} Suppliers | UdyogConnect"
        if len(seo_title) > 65:
            seo_title = f"{product_name} Suppliers in {city_title} | UdyogConnect"
        
        seo_description = f"Find {seller_count} verified {product_name} suppliers in {city_title}. "
        if min_price:
            seo_description += f"Prices from ₹{min_price:,.0f}. "
        seo_description += f"Compare quotes and get best deals on UdyogConnect."
        seo_description = seo_description[:160]
        
        # Canonical URL - always the main product page
        canonical_url = f"{self.SITE_URL}/products/{product_slug}"
        
        # City page URL (for this specific page)
        city_page_url = f"{self.SITE_URL}/products/{product_slug}/{city_slug}"
        
        return {
            "product": {
                "_id": str(product["_id"]),
                "name": product_name,
                "slug": product_slug,
                "categoryName": product.get("categoryName")
            },
            "city": {
                "name": city_title,
                "slug": city_slug,
                "normalized": normalized_city
            },
            "sellers": sellers,
            "stats": {
                "sellerCount": seller_count,
                "minPrice": min_price,
                "maxPrice": max_price
            },
            "seo": {
                "title": seo_title,
                "description": seo_description,
                "canonicalUrl": canonical_url,  # Points to main product page
                "cityPageUrl": city_page_url
            }
        }
    
    async def get_available_cities_for_product(
        self,
        product_id: ObjectId
    ) -> List[Dict[str, Any]]:
        """
        Get all cities with active sellers for a product.
        
        Used for:
        1. Internal linking
        2. City navigation on product page
        3. Sitemap generation
        """
        pipeline = [
            {"$match": {
                "productId": product_id,
                "status": "active"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": "$seller"},
            {"$group": {
                "_id": {"$toLower": {"$ifNull": ["$seller.profile.city", "other"]}},
                "sellerCount": {"$sum": 1},
                "minPrice": {"$min": {"$arrayElemAt": ["$pricingTiers.pricePerUnit", 0]}}
            }},
            {"$match": {"_id": {"$ne": "other"}}},
            {"$sort": {"sellerCount": -1}},
            {"$limit": 20}
        ]
        
        results = await self.db.sellerListings.aggregate(pipeline).to_list(20)
        
        cities = []
        for r in results:
            city_name = r["_id"]
            cities.append({
                "name": city_name.title(),
                "slug": self.generate_city_slug(city_name),
                "sellerCount": r["sellerCount"],
                "minPrice": r.get("minPrice")
            })
        
        return cities
    
    def generate_city_seo_content(
        self,
        product_name: str,
        city: str,
        seller_count: int,
        min_price: float = None,
        category_name: str = None
    ) -> str:
        """
        Generate structured SEO content for city page.
        
        Content includes:
        - City-specific H1
        - Local market context
        - Why buy from this city
        """
        city_title = city.title()
        
        content = f"""# {product_name} Suppliers in {city_title}

Find {seller_count} verified {product_name} suppliers and manufacturers in {city_title}. UdyogConnect connects you with local dealers offering competitive pricing and fast delivery.

## {product_name} Price in {city_title}

"""
        if min_price:
            content += f"Prices for {product_name} in {city_title} start from ₹{min_price:,.0f}. Compare quotes from multiple suppliers to get the best deal.\n\n"
        else:
            content += f"Contact suppliers directly to get the latest prices for {product_name} in {city_title}.\n\n"
        
        content += f"""## Why Buy {product_name} from {city_title} Suppliers?

1. **Local Support**: Get after-sales service and support from nearby suppliers
2. **Faster Delivery**: Reduced shipping time from local warehouses
3. **Competitive Pricing**: Compare {seller_count} local suppliers for best rates
4. **Verified Sellers**: All suppliers on UdyogConnect are verified

## How to Buy {product_name} in {city_title}

1. Browse {seller_count} verified suppliers above
2. Compare prices, MOQ, and specifications
3. Request quotes from multiple sellers
4. Choose the best offer and place your order

Start sourcing {product_name} from {city_title} suppliers today!
"""
        
        return content


# Factory function
def create_city_seo_service(db):
    """Create city SEO service instance."""
    return CitySEOService(db)
