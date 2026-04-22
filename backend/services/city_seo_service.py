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
        
        # Count active sellers in this city via user profile
        pipeline = [
            {"$match": {"productId": product_id, "status": "active"}},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            {"$match": {
                "$or": [
                    {"city": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                    {"sellerCity": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                    {"seller.profile.city": {"$regex": f"^{normalized_city}$", "$options": "i"}}
                ]
            }},
            {"$count": "total"}
        ]
        result = await self.db.sellerListings.aggregate(pipeline).to_list(1)
        seller_count = result[0]["total"] if result else 0
        
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
                "status": "active"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            {"$match": {
                "$or": [
                    {"city": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                    {"sellerCity": {"$regex": f"^{normalized_city}$", "$options": "i"}},
                    {"seller.profile.city": {"$regex": f"^{normalized_city}$", "$options": "i"}}
                ]
            }},
            {"$project": {
                "_id": 1,
                "sellerId": 1,
                "pricingTiers": 1,
                "moq": 1,
                "leadTime": 1,
                "stock": 1,
                "images": {"$slice": ["$images", 2]},
                "companyName": {"$ifNull": ["$seller.profile.businessName", "Verified Seller"]},
                "city": {"$ifNull": ["$city", {"$ifNull": ["$sellerCity", "$seller.profile.city"]}]},
                "badgeType": {"$ifNull": ["$seller.badgeType", "none"]},
                "listingId": {"$toString": "$_id"}
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
        
        # Title: {Product Name} in {City} | Industrial Supplier | UdyogConnect
        seo_title = f"{product_name} in {city_title} | Industrial Supplier | UdyogConnect"
        if len(seo_title) > 65:
            seo_title = f"{product_name} in {city_title} | UdyogConnect"
        if len(seo_title) > 65:
            max_pn = 65 - len(f" in {city_title} | UdyogConnect") - 3
            seo_title = f"{product_name[:max_pn]}... in {city_title} | UdyogConnect"
        
        # Description: 140-160 chars with city keyword
        from services.seo_service import seo_service
        seo_description = seo_service.generate_seo_description(
            product_name, product.get("categoryName"),
            seller_count, min_price, max_price, city=city_title
        )
        
        # Canonical URL - always the main product page
        canonical_url = f"{self.SITE_URL}/products/{product_slug}"
        
        # City page URL (for this specific page)
        city_page_url = f"{self.SITE_URL}/products/{product_slug}/{city_slug}"
        
        # Generate city-specific SEO content (400+ words unique)
        seo_content = self.generate_city_seo_content(
            product_name, city, seller_count, min_price, product.get("categoryName")
        )

        # Build JSON-LD schemas for city page
        city_json_ld = self._build_city_json_ld(
            product_name=product_name,
            product_slug=product_slug,
            city_title=city_title,
            city_slug=city_slug,
            seller_count=seller_count,
            min_price=min_price,
            max_price=max_price,
            category_name=product.get("categoryName"),
            sellers=sellers,
            city_page_url=city_page_url,
        )

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
                "seoContent": seo_content,
                "canonicalUrl": canonical_url,
                "cityPageUrl": city_page_url,
                "jsonLd": city_json_ld["product"],
                "breadcrumbJsonLd": city_json_ld["breadcrumb"],
                "faqJsonLd": city_json_ld["faq"],
            },
            "internalLinks": {
                "mainProductPage": f"{self.SITE_URL}/products/{product_slug}",
                "categoryPage": f"{self.SITE_URL}/categories/{product.get('categoryName', '').lower().replace(' ', '-')}" if product.get("categoryName") else None
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
        Generate 400-800 word structured SEO content for city page.
        Unique per city — NOT duplicate of main product page.
        """
        city_title = city.title()
        
        content = f"""# {product_name} Suppliers in {city_title}

Looking for reliable {product_name} suppliers in {city_title}? UdyogConnect connects you with {seller_count} verified manufacturers, dealers, and distributors offering {product_name} in {city_title} and surrounding areas. Get competitive pricing, fast local delivery, and trusted quality from pre-verified sellers.

## {product_name} Price in {city_title}

"""
        if min_price:
            content += f"""Prices for {product_name} in {city_title} start from ₹{min_price:,.0f}. Pricing varies based on specifications, quantity ordered, and the supplier. Compare quotes from {seller_count} suppliers on UdyogConnect to find the most competitive rates. Bulk orders and long-term contracts often qualify for additional discounts.

"""
        else:
            content += f"""Contact {city_title}-based suppliers directly on UdyogConnect to get the latest pricing for {product_name}. Request quotations from multiple sellers to compare and negotiate the best deal for your requirements.

"""
        
        content += f"""## Why Buy {product_name} from {city_title} Suppliers?

Sourcing {product_name} from local suppliers in {city_title} offers several advantages for businesses:

1. **Faster Delivery**: Local warehouses and manufacturing units mean reduced transit time — often same-day or next-day delivery within {city_title}
2. **Lower Logistics Cost**: Proximity reduces freight charges, especially for bulk industrial orders
3. **After-Sales Support**: On-site service, maintenance support, and easy returns from nearby suppliers
4. **Competitive Pricing**: {seller_count} verified suppliers competing for your business ensures the best rates
5. **Quality Inspection**: Visit supplier premises for physical quality checks before placing large orders

## {product_name} Applications in {city_title}

{city_title}'s industrial sector uses {product_name} across multiple applications:

- **Manufacturing Units**: Factory production lines, assembly operations, and process automation
- **Construction Projects**: Infrastructure development, commercial buildings, and residential complexes
- **Engineering Workshops**: Fabrication, maintenance, and repair operations
- **OEM & Export**: Original equipment manufacturing and export-oriented production facilities

{city_title} is one of India's key industrial hubs, making it an ideal location to source quality {product_name} at competitive prices.

## How to Source {product_name} in {city_title}

Follow these steps to find the right {product_name} supplier in {city_title} through UdyogConnect:

1. **Browse Sellers**: View {seller_count} verified {product_name} suppliers listed above
2. **Compare Offers**: Check prices, minimum order quantity (MOQ), lead times, and certifications
3. **Request Quotations**: Send RFQ to multiple suppliers for competitive bidding
4. **Verify & Order**: Check ratings, reviews, and GST verification status before placing your order
5. **Get Delivery**: Enjoy fast local delivery from {city_title}-based suppliers

## About UdyogConnect B2B Marketplace

UdyogConnect is India's trusted B2B platform for industrial procurement. All suppliers undergo strict verification including GST registration, business legitimacy, and quality checks. Whether you need {product_name} in {city_title} or any other industrial city, our network of verified sellers ensures reliable sourcing with price transparency.

Start sourcing {product_name} from {city_title} suppliers today — compare quotes and place your order on UdyogConnect!
"""
        
        return content

    def _build_city_json_ld(
        self,
        product_name: str,
        product_slug: str,
        city_title: str,
        city_slug: str,
        seller_count: int,
        min_price: Optional[float],
        max_price: Optional[float],
        category_name: Optional[str],
        sellers: List[Dict[str, Any]],
        city_page_url: str,
    ) -> Dict[str, Any]:
        """Build Product + Breadcrumb + FAQ JSON-LD for a city page."""
        from services.seo_service import seo_service as _seo

        # --- Product schema with AggregateOffer scoped to the city ---
        product_schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": f"{product_name} in {city_title}",
            "description": (
                f"Buy {product_name} from {seller_count} verified suppliers in {city_title}. "
                f"Compare prices and get quotes on UdyogConnect."
            )[:500],
            "url": city_page_url,
            "category": category_name or "Industrial Products",
            "brand": {"@type": "Brand", "name": "Various Manufacturers"},
            "areaServed": {
                "@type": "City",
                "name": city_title,
                "containedInPlace": {"@type": "Country", "name": "India"},
            },
        }

        if min_price and max_price and max_price > min_price and seller_count > 1:
            product_schema["offers"] = {
                "@type": "AggregateOffer",
                "priceCurrency": "INR",
                "lowPrice": round(float(min_price), 2),
                "highPrice": round(float(max_price), 2),
                "offerCount": seller_count,
                "availability": "https://schema.org/InStock",
                "eligibleRegion": {"@type": "City", "name": city_title},
                "seller": {
                    "@type": "Organization",
                    "name": f"Verified Suppliers on UdyogConnect ({city_title})"
                },
            }
        elif min_price:
            product_schema["offers"] = {
                "@type": "Offer",
                "priceCurrency": "INR",
                "price": round(float(min_price), 2),
                "availability": "https://schema.org/InStock",
                "eligibleRegion": {"@type": "City", "name": city_title},
                "seller": {
                    "@type": "Organization",
                    "name": (sellers[0].get("companyName") if sellers else "Verified Supplier"),
                },
            }
        else:
            product_schema["offers"] = {
                "@type": "Offer",
                "priceCurrency": "INR",
                "availability": "https://schema.org/InStock",
                "priceSpecification": {
                    "@type": "PriceSpecification",
                    "price": "Request Quote",
                    "priceCurrency": "INR",
                },
            }

        # --- Breadcrumb ---
        breadcrumb_schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": self.SITE_URL},
                {"@type": "ListItem", "position": 2, "name": "Products", "item": f"{self.SITE_URL}/products"},
                {
                    "@type": "ListItem", "position": 3, "name": product_name,
                    "item": f"{self.SITE_URL}/products/{product_slug}"
                },
                {"@type": "ListItem", "position": 4, "name": city_title, "item": city_page_url},
            ],
        }

        # --- FAQ schema scoped to the city ---
        price_text = f"₹{_seo._format_price(min_price)}" if min_price else "varies by seller"
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"Where can I buy {product_name} in {city_title}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            f"You can buy {product_name} from {seller_count} verified suppliers in "
                            f"{city_title} listed on UdyogConnect. Compare prices, check ratings, "
                            f"and request quotes directly."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": f"What is the price of {product_name} in {city_title}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            f"The price of {product_name} in {city_title} starts from {price_text}. "
                            f"Pricing depends on specifications, order quantity, and supplier. "
                            f"Request quotations from multiple sellers to compare."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": f"How fast is {product_name} delivery in {city_title}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            f"Local suppliers in {city_title} typically offer same-day or next-day "
                            f"delivery within city limits. Contact the supplier to confirm exact "
                            f"lead time for your order size."
                        ),
                    },
                },
            ],
        }

        return {"product": product_schema, "breadcrumb": breadcrumb_schema, "faq": faq_schema}


# Factory function
def create_city_seo_service(db):
    """Create city SEO service instance."""
    return CitySEOService(db)
