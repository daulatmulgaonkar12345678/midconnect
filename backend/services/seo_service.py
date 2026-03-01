"""
ENTERPRISE SEO SERVICE
=======================
Template-based SEO content generation for products.

NO AI required - deterministic templates that Google loves.
Structure > AI Content for ranking.

Generates:
- seoTitle (55-60 chars)
- seoDescription (150-160 chars)  
- seoContent (300-500 words structured content)
- JSON-LD structured data
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger("seo_service")


class SEOService:
    """Enterprise SEO content generator using templates."""
    
    SITE_NAME = "UdyogConnect"
    SITE_URL = "https://www.udyogconnect.in"
    
    # Industry applications mapping for different product categories
    INDUSTRY_APPLICATIONS = {
        "motors": ["manufacturing plants", "industrial automation", "pumps and compressors", "conveyors", "HVAC systems"],
        "electrical": ["power distribution", "industrial wiring", "construction projects", "renewable energy", "building automation"],
        "steel": ["construction", "fabrication", "manufacturing", "infrastructure projects", "automotive industry"],
        "chemicals": ["textile processing", "water treatment", "pharmaceuticals", "food processing", "paper manufacturing"],
        "cables": ["power transmission", "telecommunications", "industrial wiring", "construction", "renewable energy"],
        "pipes": ["plumbing", "industrial piping", "construction", "irrigation", "HVAC systems"],
        "default": ["manufacturing", "construction", "industrial applications", "engineering projects", "commercial use"]
    }
    
    @classmethod
    def generate_seo_title(cls, product_name: str, category_name: str = None) -> str:
        """
        Generate SEO-optimized title (55-60 characters).
        
        Format: Buy {Product} at Best Price | Verified Suppliers | UdyogConnect
        """
        # Clean product name
        clean_name = cls._clean_product_name(product_name)
        
        # Build title with fallbacks for length
        full_title = f"Buy {clean_name} at Best Price | Verified Suppliers | {cls.SITE_NAME}"
        
        if len(full_title) <= 60:
            return full_title
        
        # Shorter version
        short_title = f"Buy {clean_name} | Best Price | {cls.SITE_NAME}"
        if len(short_title) <= 60:
            return short_title
        
        # Minimal version
        return f"{clean_name} | {cls.SITE_NAME}"[:60]
    
    @classmethod
    def generate_seo_description(cls, product_name: str, category_name: str = None, seller_count: int = 0) -> str:
        """
        Generate SEO meta description (150-160 characters).
        
        Focus on action-oriented, benefit-rich copy.
        """
        clean_name = cls._clean_product_name(product_name)
        
        if seller_count > 1:
            desc = f"Find {seller_count}+ verified suppliers of {clean_name}. Compare prices, MOQ and contact manufacturers directly on {cls.SITE_NAME}. Get best deals today!"
        else:
            desc = f"Find verified suppliers of {clean_name}. Compare prices, MOQ and contact manufacturers directly on {cls.SITE_NAME}. Get best deals today!"
        
        # Truncate if needed
        if len(desc) > 160:
            desc = desc[:157] + "..."
        
        return desc
    
    @classmethod
    def generate_seo_content(
        cls,
        product_name: str,
        category_name: str = None,
        specifications: Dict[str, Any] = None,
        description: str = None
    ) -> str:
        """
        Generate 300-500 word SEO content using templates.
        
        Structure:
        1. What is the product (Introduction)
        2. Key Specifications
        3. Applications & Industries
        4. Benefits
        5. Why buy from UdyogConnect
        """
        clean_name = cls._clean_product_name(product_name)
        category_key = cls._get_category_key(category_name)
        applications = cls.INDUSTRY_APPLICATIONS.get(category_key, cls.INDUSTRY_APPLICATIONS["default"])
        
        # Build structured content
        sections = []
        
        # Section 1: Introduction
        sections.append(f"""## About {clean_name}

{clean_name} is a high-quality industrial product widely used across manufacturing, construction, and engineering sectors in India. Known for its durability, reliability, and performance, this product meets the demanding requirements of modern industrial applications.""")
        
        # Section 2: Specifications (if available)
        if specifications and len(specifications) > 0:
            spec_lines = []
            for key, value in list(specifications.items())[:6]:
                label = cls._format_spec_label(key)
                spec_lines.append(f"- **{label}**: {value}")
            
            if spec_lines:
                sections.append(f"""## Technical Specifications

{chr(10).join(spec_lines)}

These specifications ensure optimal performance for your industrial requirements.""")
        
        # Section 3: Applications
        app_list = ", ".join(applications[:4])
        sections.append(f"""## Applications & Industries

{clean_name} finds extensive use in {app_list}, and many other industrial applications. Whether you're setting up a new facility or maintaining existing equipment, this product delivers consistent performance.

Industries that commonly use this product include:
- Manufacturing plants and factories
- Construction and infrastructure projects
- Engineering and fabrication workshops
- Industrial automation systems""")
        
        # Section 4: Benefits
        sections.append(f"""## Key Benefits

Choosing quality {clean_name} offers several advantages:

1. **Durability**: Built to withstand demanding industrial conditions
2. **Reliability**: Consistent performance over extended periods
3. **Cost-Effective**: Competitive pricing from verified suppliers
4. **Quality Assured**: Products from trusted manufacturers and dealers""")
        
        # Section 5: Why UdyogConnect
        sections.append(f"""## Why Buy from {cls.SITE_NAME}?

{cls.SITE_NAME} is India's trusted B2B marketplace connecting buyers with verified manufacturers, dealers, and distributors. When you source {clean_name} through our platform, you benefit from:

- **Verified Suppliers**: All sellers undergo verification before listing
- **Price Comparison**: Compare quotes from multiple suppliers
- **Direct Communication**: Connect directly with manufacturers
- **Pan-India Network**: Suppliers across all major industrial cities
- **Secure Transactions**: Safe and transparent business dealings

Find the best {clean_name} suppliers near you and get competitive quotes today.""")
        
        return "\n\n".join(sections)
    
    @classmethod
    def generate_json_ld(
        cls,
        product: Dict[str, Any],
        sellers: List[Dict[str, Any]],
        category_name: str = None
    ) -> Dict[str, Any]:
        """
        Generate JSON-LD structured data for Google rich snippets.
        
        Uses Product schema with AggregateOffer for multiple sellers.
        """
        product_name = product.get("name", "Industrial Product")
        product_slug = product.get("slug", "")
        description = product.get("description") or product.get("seoDescription") or f"Buy {product_name} from verified suppliers on UdyogConnect"
        
        # Get price range from sellers
        prices = []
        for seller in sellers:
            pricing_tiers = seller.get("pricingTiers", [])
            if pricing_tiers:
                for tier in pricing_tiers:
                    price = tier.get("pricePerUnit") or tier.get("price")
                    if price and price > 0:
                        prices.append(float(price))
            # Also check lowestPrice
            lowest = seller.get("lowestPrice")
            if lowest and lowest > 0:
                prices.append(float(lowest))
        
        # Get images
        images = product.get("images", [])
        if not images and sellers:
            for seller in sellers:
                seller_images = seller.get("images", [])
                if seller_images:
                    images = seller_images[:3]
                    break
        
        # Build base product schema
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product_name,
            "description": description[:500],  # Google limit
            "url": f"{cls.SITE_URL}/product/{product_slug}",
            "brand": {
                "@type": "Brand",
                "name": "Various Manufacturers"
            },
            "category": category_name or "Industrial Products"
        }
        
        # Add images
        if images:
            json_ld["image"] = images[:5]
        
        # Add offers (AggregateOffer for multiple sellers)
        if prices:
            low_price = min(prices)
            high_price = max(prices)
            offer_count = len(sellers)
            
            if offer_count > 1:
                json_ld["offers"] = {
                    "@type": "AggregateOffer",
                    "priceCurrency": "INR",
                    "lowPrice": round(low_price, 2),
                    "highPrice": round(high_price, 2),
                    "offerCount": offer_count,
                    "availability": "https://schema.org/InStock",
                    "seller": {
                        "@type": "Organization",
                        "name": f"Verified Suppliers on {cls.SITE_NAME}"
                    }
                }
            else:
                json_ld["offers"] = {
                    "@type": "Offer",
                    "priceCurrency": "INR",
                    "price": round(low_price, 2),
                    "availability": "https://schema.org/InStock",
                    "seller": {
                        "@type": "Organization",
                        "name": sellers[0].get("companyName", "Verified Supplier") if sellers else "Verified Supplier"
                    }
                }
        
        # Add aggregate rating placeholder (for future reviews)
        # json_ld["aggregateRating"] = {...}
        
        return json_ld
    
    @classmethod
    def generate_breadcrumb_json_ld(
        cls,
        product_name: str,
        product_slug: str,
        category_name: str = None,
        category_slug: str = None
    ) -> Dict[str, Any]:
        """Generate BreadcrumbList JSON-LD for navigation."""
        items = [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": cls.SITE_URL
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Products",
                "item": f"{cls.SITE_URL}/products"
            }
        ]
        
        if category_name and category_slug:
            items.append({
                "@type": "ListItem",
                "position": 3,
                "name": category_name,
                "item": f"{cls.SITE_URL}/category/{category_slug}"
            })
            items.append({
                "@type": "ListItem",
                "position": 4,
                "name": product_name,
                "item": f"{cls.SITE_URL}/product/{product_slug}"
            })
        else:
            items.append({
                "@type": "ListItem",
                "position": 3,
                "name": product_name,
                "item": f"{cls.SITE_URL}/product/{product_slug}"
            })
        
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items
        }
    
    @classmethod
    def generate_organization_json_ld(cls) -> Dict[str, Any]:
        """Generate Organization JSON-LD for site identity."""
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": cls.SITE_NAME,
            "url": cls.SITE_URL,
            "logo": f"{cls.SITE_URL}/logo.png",
            "description": "India's trusted B2B marketplace for industrial products. Connect with verified manufacturers, dealers, and distributors.",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "D2, Kedareshwar Park, Gujarwadi, Katraj",
                "addressLocality": "Pune",
                "addressRegion": "Maharashtra",
                "postalCode": "411046",
                "addressCountry": "IN"
            },
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+91-7387821042",
                "contactType": "customer service",
                "availableLanguage": ["English", "Hindi"]
            },
            "sameAs": []
        }
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _clean_product_name(name: str) -> str:
        """Clean and normalize product name."""
        if not name:
            return "Industrial Product"
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', name).strip()
        # Capitalize properly
        return clean.title() if clean.islower() else clean
    
    @staticmethod
    def _get_category_key(category_name: str) -> str:
        """Map category name to industry key."""
        if not category_name:
            return "default"
        
        name_lower = category_name.lower()
        
        if "motor" in name_lower or "pump" in name_lower:
            return "motors"
        elif "electric" in name_lower or "switch" in name_lower or "mcb" in name_lower:
            return "electrical"
        elif "steel" in name_lower or "metal" in name_lower or "iron" in name_lower:
            return "steel"
        elif "chemical" in name_lower or "caustic" in name_lower:
            return "chemicals"
        elif "cable" in name_lower or "wire" in name_lower:
            return "cables"
        elif "pipe" in name_lower or "tube" in name_lower:
            return "pipes"
        
        return "default"
    
    @staticmethod
    def _format_spec_label(key: str) -> str:
        """Format specification key as human-readable label."""
        # Convert camelCase or snake_case to Title Case
        formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
        formatted = formatted.replace('_', ' ')
        return formatted.title()


# Singleton instance
seo_service = SEOService()
