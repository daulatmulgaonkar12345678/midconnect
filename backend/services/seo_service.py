"""
ENTERPRISE SEO SERVICE v2.0
============================
Marketplace-standard SEO content generation for UdyogConnect.

Features:
- Keyword-rich, SEO-friendly slugs (IndiaMART/Alibaba level)
- Optimized title tags (55-65 chars, CTR-focused)
- Dynamic meta descriptions (seller count, price range, MOQ)
- Structured on-page content (300-500 words, H1/H2 hierarchy)
- Enhanced JSON-LD (Product, AggregateOffer, BreadcrumbList, Organization, FAQ)
- Internal linking system
- Category-based keyword injection

NO AI dependency - deterministic templates that Google loves.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("seo_service")


class SEOService:
    """Enterprise SEO content generator using marketplace-standard templates."""
    
    SITE_NAME = "UdyogConnect"
    SITE_URL = "https://www.udyogconnect.in"
    
    # SEO v2.1 - Max slug length
    MAX_SLUG_LENGTH = 90
    
    # Industry applications mapping for different product categories
    INDUSTRY_APPLICATIONS = {
        "motors": ["manufacturing plants", "industrial automation", "pumps and compressors", "conveyors", "HVAC systems"],
        "electrical": ["power distribution", "industrial wiring", "construction projects", "renewable energy", "building automation"],
        "steel": ["construction", "fabrication", "manufacturing", "infrastructure projects", "automotive industry"],
        "chemicals": ["textile processing", "water treatment", "pharmaceuticals", "food processing", "paper manufacturing"],
        "cables": ["power transmission", "telecommunications", "industrial wiring", "construction", "renewable energy"],
        "pipes": ["plumbing", "industrial piping", "construction", "irrigation", "HVAC systems"],
        "pumps": ["water supply", "industrial processing", "irrigation", "HVAC", "chemical handling"],
        "valves": ["oil and gas", "water treatment", "chemical processing", "HVAC systems", "fire protection"],
        "bearings": ["automotive", "industrial machinery", "conveyor systems", "pumps", "compressors"],
        "fasteners": ["construction", "automotive", "machinery assembly", "furniture", "electronics"],
        "tools": ["manufacturing", "construction", "maintenance", "automotive repair", "fabrication"],
        "safety": ["manufacturing plants", "construction sites", "chemical plants", "oil and gas", "mining"],
        "default": ["manufacturing", "construction", "industrial applications", "engineering projects", "commercial use"]
    }
    
    # Major industrial cities for internal linking
    MAJOR_CITIES = [
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", 
        "Pune", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Kanpur",
        "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Vadodara",
        "Coimbatore", "Ludhiana", "Rajkot", "Faridabad", "Ghaziabad"
    ]

    # ==================== SLUG OPTIMIZATION ====================
    
    @classmethod
    def generate_seo_slug(
        cls, 
        product_name: str, 
        category_name: str = None,
        existing_slugs: List[str] = None
    ) -> str:
        """
        Generate keyword-rich, SEO-friendly, unique slug.
        
        Format: {product-name}-{category}-supplier-india
        
        Requirements:
        - Convert to lowercase
        - Replace spaces with "-"
        - Remove special characters
        - Append category keyword
        - Append "supplier-india"
        - Ensure uniqueness
        
        Example:
        Input: "Water Pump", Category: "Industrial Pumps"
        Output: "water-pump-industrial-pumps-supplier-india"
        """
        if not product_name:
            return "industrial-product-supplier-india"
        
        # Clean and normalize product name
        clean_name = product_name.lower().strip()
        
        # Remove special characters, keep only alphanumeric and spaces
        clean_name = re.sub(r'[^a-z0-9\s]+', '', clean_name)
        
        # Replace multiple spaces with single hyphen
        clean_name = re.sub(r'\s+', '-', clean_name)
        
        # Remove leading/trailing hyphens
        clean_name = clean_name.strip('-')
        
        # Build slug parts
        slug_parts = [clean_name]
        
        # Add category keyword if available
        if category_name:
            category_slug = re.sub(r'[^a-z0-9\s]+', '', category_name.lower())
            category_slug = re.sub(r'\s+', '-', category_slug).strip('-')
            # Only add if different from product name
            if category_slug and category_slug not in clean_name:
                slug_parts.append(category_slug)
        
        # Always append supplier-india suffix
        slug_parts.append("supplier-india")
        
        base_slug = '-'.join(slug_parts)
        
        # SEO v2.1: Enforce max 90 character limit
        if len(base_slug) > cls.MAX_SLUG_LENGTH:
            # Truncate product name part to fit
            suffix_len = len("-supplier-india")
            cat_len = len(category_slug) + 1 if category_name else 0
            max_name_len = cls.MAX_SLUG_LENGTH - suffix_len - cat_len
            clean_name = clean_name[:max_name_len].rstrip('-')
            slug_parts = [clean_name]
            if category_name and category_slug:
                slug_parts.append(category_slug)
            slug_parts.append("supplier-india")
            base_slug = '-'.join(slug_parts)
        
        # Ensure uniqueness
        if existing_slugs:
            final_slug = base_slug
            counter = 1
            while final_slug in existing_slugs:
                final_slug = f"{base_slug}-{counter}"
                counter += 1
            return final_slug
        
        return base_slug
    
    # ==================== TITLE TAG OPTIMIZATION ====================
    
    @classmethod
    def generate_seo_title(cls, product_name: str, category_name: str = None) -> str:
        """
        Generate SEO-optimized title tag (55-65 characters).
        
        Format: Buy {Product Name} Online | {Category Keyword} Suppliers in India | UdyogConnect
        
        Constraints:
        - 55-65 characters ideal
        - Must include primary keyword
        - Must include "India"
        
        Example:
        "Buy Industrial Water Pump Online | Pump Suppliers India | UdyogConnect"
        """
        clean_name = cls._clean_product_name(product_name)
        
        # Build primary title with full format
        if category_name:
            category_keyword = cls._extract_category_keyword(category_name)
            full_title = f"Buy {clean_name} Online | {category_keyword} Suppliers India | {cls.SITE_NAME}"
        else:
            full_title = f"Buy {clean_name} Online | Verified Suppliers India | {cls.SITE_NAME}"
        
        # If within limit, return full title
        if len(full_title) <= 65:
            return full_title
        
        # Try shorter version without "Online"
        if category_name:
            category_keyword = cls._extract_category_keyword(category_name)
            short_title = f"Buy {clean_name} | {category_keyword} Suppliers India | {cls.SITE_NAME}"
        else:
            short_title = f"Buy {clean_name} | Suppliers India | {cls.SITE_NAME}"
        
        if len(short_title) <= 65:
            return short_title
        
        # Minimal version
        minimal_title = f"{clean_name} Suppliers India | {cls.SITE_NAME}"
        if len(minimal_title) <= 65:
            return minimal_title
        
        # Last resort - truncate product name
        max_product_len = 65 - len(f" Suppliers India | {cls.SITE_NAME}") - 3
        truncated_name = clean_name[:max_product_len] + "..."
        return f"{truncated_name} Suppliers India | {cls.SITE_NAME}"
    
    # ==================== META DESCRIPTION ENHANCEMENT ====================
    
    @classmethod
    def generate_seo_description(
        cls, 
        product_name: str, 
        category_name: str = None, 
        seller_count: int = 0,
        min_price: float = None,
        max_price: float = None,
        min_moq: int = None
    ) -> str:
        """
        Generate dynamic meta description (150-160 characters).
        
        Template:
        "Explore {sellerCount}+ verified suppliers of {productName} in India. 
        Compare prices, specifications & MOQ. Get best deals instantly on UdyogConnect."
        
        Includes:
        - Product name
        - Seller count
        - Price range (if available)
        - MOQ (if available)
        - Call-to-action
        
        Constraints:
        - 150-160 characters
        - Readable, not keyword-stuffed
        """
        clean_name = cls._clean_product_name(product_name)
        
        # Build description parts
        parts = []
        
        # Start with seller count if available
        if seller_count > 1:
            parts.append(f"Explore {seller_count}+ verified suppliers of {clean_name} in India.")
        else:
            parts.append(f"Find verified suppliers of {clean_name} in India.")
        
        # Add price range if available
        if min_price and max_price and min_price != max_price:
            parts.append(f"Prices from ₹{cls._format_price(min_price)} to ₹{cls._format_price(max_price)}.")
        elif min_price:
            parts.append(f"Starting from ₹{cls._format_price(min_price)}.")
        
        # Add MOQ if available
        if min_moq and min_moq > 1:
            parts.append(f"MOQ: {min_moq} units.")
        
        # Always add CTA
        parts.append(f"Compare prices & get best deals on {cls.SITE_NAME}.")
        
        # Join and truncate
        description = " ".join(parts)
        
        # Ensure within limit
        if len(description) > 160:
            # Build shorter version
            if seller_count > 1:
                description = f"Explore {seller_count}+ verified {clean_name} suppliers in India. Compare prices, specs & MOQ. Get best deals on {cls.SITE_NAME}."
            else:
                description = f"Find verified {clean_name} suppliers in India. Compare prices, specs & MOQ. Get best deals on {cls.SITE_NAME}."
        
        if len(description) > 160:
            description = description[:157] + "..."
        
        return description
    
    # ==================== STRUCTURED ON-PAGE CONTENT ====================
    
    @classmethod
    def generate_seo_content(
        cls,
        product_name: str,
        category_name: str = None,
        specifications: Dict[str, Any] = None,
        description: str = None,
        seller_count: int = 0,
        available_cities: List[str] = None
    ) -> str:
        """
        Generate 300-500 word structured SEO content block.
        
        Required Structure:
        H1: {Product Name} Suppliers in India
        
        Paragraph 1: Overview of product and industry relevance
        
        H2: Specifications of {Product Name}
        
        H2: Applications of {Product Name}
        
        H2: Available Cities
        
        H2: Why Choose UdyogConnect
        
        Content must:
        - Be structured with proper headings
        - Avoid duplication
        - Add marketplace context
        """
        clean_name = cls._clean_product_name(product_name)
        category_key = cls._get_category_key(category_name)
        applications = cls.INDUSTRY_APPLICATIONS.get(category_key, cls.INDUSTRY_APPLICATIONS["default"])
        
        sections = []
        
        # ===== H1: Main Heading =====
        sections.append(f"# {clean_name} Suppliers in India")
        
        # ===== Paragraph 1: Overview =====
        seller_text = f"{seller_count}+ verified" if seller_count > 1 else "verified"
        overview = f"""
{cls.SITE_NAME} connects you with {seller_text} suppliers, manufacturers, and dealers of {clean_name} across India. Whether you need bulk quantities for industrial projects or are looking for competitive pricing, our platform offers direct access to trusted sellers with transparent pricing and specifications.
"""
        sections.append(overview.strip())
        
        # ===== H2: Specifications =====
        if specifications and len(specifications) > 0:
            spec_lines = []
            for key, value in list(specifications.items())[:8]:
                label = cls._format_spec_label(key)
                if value:
                    spec_lines.append(f"- **{label}**: {value}")
            
            if spec_lines:
                spec_section = f"""
## Specifications of {clean_name}

Our suppliers offer {clean_name} with various specifications to meet your requirements:

{chr(10).join(spec_lines)}

Contact sellers directly to discuss custom specifications for your specific needs.
"""
                sections.append(spec_section.strip())
        
        # ===== H2: Applications =====
        app_list = ", ".join(applications[:4])
        
        app_section = f"""
## Applications of {clean_name}

{clean_name} is widely used across multiple industries including {app_list}. Key application areas include:

- **Manufacturing**: Factory automation, production lines, and industrial machinery
- **Construction**: Building projects, infrastructure development, and civil engineering
- **Engineering**: Fabrication shops, maintenance operations, and equipment assembly
- **Commercial**: Office buildings, retail establishments, and hospitality industry
"""
        sections.append(app_section.strip())
        
        # ===== H2: Available Cities =====
        if available_cities and len(available_cities) > 0:
            cities = available_cities[:12]
        else:
            cities = cls.MAJOR_CITIES[:12]
        
        cities_text = ", ".join(cities)
        city_section = f"""
## {clean_name} Suppliers by City

Find {clean_name} suppliers in major industrial cities across India:

{cities_text}

Our network spans all major industrial hubs, ensuring quick delivery and local support for your procurement needs.
"""
        sections.append(city_section.strip())
        
        # ===== H2: Why Choose UdyogConnect =====
        why_section = f"""
## Why Choose {cls.SITE_NAME} for {clean_name}?

{cls.SITE_NAME} is India's trusted B2B marketplace for industrial products. When sourcing {clean_name} through our platform, you benefit from:

1. **Verified Suppliers**: All sellers undergo strict verification before listing
2. **Price Transparency**: Compare quotes from multiple suppliers instantly
3. **Direct Communication**: Connect directly with manufacturers and distributors
4. **Pan-India Network**: Access suppliers across all major industrial cities
5. **Quality Assurance**: Trusted brands and certified products

Start sourcing {clean_name} today and get competitive quotes from verified suppliers.
"""
        sections.append(why_section.strip())
        
        return "\n\n".join(sections)
    
    # ==================== INTERNAL LINKING SYSTEM ====================
    
    @classmethod
    def generate_internal_links(
        cls,
        product_id: str,
        product_name: str,
        category_id: str = None,
        category_name: str = None,
        category_slug: str = None,
        similar_products: List[Dict] = None,
        available_cities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate internal links for SEO.
        
        Includes:
        - Link to category page
        - Links to similar products
        - Links to city-specific listings
        - Link to top-rated products
        """
        links = {
            "category": None,
            "similarProducts": [],
            "cityPages": [],
            "topRated": f"{cls.SITE_URL}/products?sort=rating"
        }
        
        # Category link
        if category_id and category_slug:
            links["category"] = {
                "name": category_name or "Category",
                "url": f"{cls.SITE_URL}/category/{category_slug}"
            }
        elif category_id:
            links["category"] = {
                "name": category_name or "Category",
                "url": f"{cls.SITE_URL}/category/{category_id}"
            }
        
        # Similar products (up to 5)
        if similar_products:
            for product in similar_products[:5]:
                slug = product.get("slug") or product.get("_id")
                links["similarProducts"].append({
                    "name": product.get("name", "Product"),
                    "url": f"{cls.SITE_URL}/product/{slug}"
                })
        
        # City pages (if sellers are grouped by city)
        if available_cities:
            for city in available_cities[:6]:
                city_slug = re.sub(r'[^a-z0-9]+', '-', city.lower())
                links["cityPages"].append({
                    "name": f"{product_name} in {city}",
                    "url": f"{cls.SITE_URL}/products?city={city_slug}"
                })
        
        return links
    
    # ==================== ENHANCED JSON-LD ====================
    
    @classmethod
    def generate_json_ld(
        cls,
        product: Dict[str, Any],
        sellers: List[Dict[str, Any]],
        category_name: str = None
    ) -> Dict[str, Any]:
        """
        Generate enhanced JSON-LD structured data for Google rich snippets.
        
        Uses Product schema with:
        - Proper brand
        - AggregateOffer for multiple sellers
        - offerCount
        - priceCurrency: INR
        """
        product_name = product.get("name", "Industrial Product")
        product_slug = product.get("slug", "")
        description = product.get("description") or product.get("seoDescription") or f"Buy {product_name} from verified suppliers on {cls.SITE_NAME}"
        
        # Get price range from sellers
        prices = []
        for seller in sellers:
            pricing_tiers = seller.get("pricingTiers", [])
            if pricing_tiers:
                for tier in pricing_tiers:
                    price = tier.get("pricePerUnit") or tier.get("price")
                    if price and price > 0:
                        prices.append(float(price))
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
        
        # Get brand from first seller or default
        brand_name = "Various Manufacturers"
        if sellers and len(sellers) == 1:
            brand_name = sellers[0].get("companyName", "Verified Supplier")
        
        # Build Product schema
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product_name,
            "description": description[:500],
            "url": f"{cls.SITE_URL}/product/{product_slug}",
            "brand": {
                "@type": "Brand",
                "name": brand_name
            },
            "category": category_name or "Industrial Products",
            "manufacturer": {
                "@type": "Organization",
                "name": brand_name
            }
        }
        
        # Add images
        if images:
            json_ld["image"] = images[:5]
        
        # Add offers (AggregateOffer for marketplace)
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
        else:
            # No price available - Request for Quote
            json_ld["offers"] = {
                "@type": "Offer",
                "priceCurrency": "INR",
                "availability": "https://schema.org/InStock",
                "priceSpecification": {
                    "@type": "PriceSpecification",
                    "price": "Request Quote",
                    "priceCurrency": "INR"
                }
            }
        
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
            "sameAs": [
                "https://www.linkedin.com/company/udyogconnect",
                "https://twitter.com/udyogconnect"
            ]
        }
    
    @classmethod
    def generate_faq_json_ld(
        cls,
        product_name: str,
        category_name: str = None,
        seller_count: int = 0,
        min_price: float = None
    ) -> Dict[str, Any]:
        """Generate FAQ JSON-LD for product pages."""
        clean_name = cls._clean_product_name(product_name)
        
        faqs = [
            {
                "question": f"Where can I buy {clean_name} in India?",
                "answer": f"You can buy {clean_name} from {seller_count if seller_count > 0 else 'multiple'} verified suppliers on {cls.SITE_NAME}. Our platform connects you directly with manufacturers, dealers, and distributors across India."
            },
            {
                "question": f"What is the price of {clean_name}?",
                "answer": f"The price of {clean_name} varies based on specifications, quantity, and seller. {f'Prices start from ₹{cls._format_price(min_price)}.' if min_price else 'Contact suppliers directly for competitive quotes.'} Compare prices from multiple sellers on {cls.SITE_NAME}."
            },
            {
                "question": f"How do I get a quote for {clean_name}?",
                "answer": f"Getting a quote is simple: 1) Browse {clean_name} listings on {cls.SITE_NAME}, 2) Select your preferred supplier, 3) Click 'Request Quote' and specify your requirements, 4) Receive quotes directly from verified sellers."
            },
            {
                "question": f"Are the {clean_name} suppliers on {cls.SITE_NAME} verified?",
                "answer": f"Yes, all suppliers on {cls.SITE_NAME} undergo verification before listing. We verify business registration, GST details, and business history to ensure you're dealing with legitimate suppliers."
            }
        ]
        
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"]
                    }
                }
                for faq in faqs
            ]
        }
    
    # ==================== COMPLETE SEO DATA GENERATION ====================
    
    @classmethod
    def generate_complete_seo_data(
        cls,
        product: Dict[str, Any],
        category: Dict[str, Any] = None,
        sellers: List[Dict[str, Any]] = None,
        similar_products: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate all SEO data for a product at creation/update time.
        
        This is meant to be called when:
        - A new product is created
        - A product is updated
        - A new listing is added to a product
        
        Returns complete SEO data to store in the database.
        """
        sellers = sellers or []
        
        # Extract data
        product_name = product.get("name", "Industrial Product")
        category_name = category.get("name") if category else None
        category_slug = category.get("slug") if category else None
        category_id = str(category.get("_id")) if category else None
        
        # Calculate seller stats
        seller_count = len(sellers)
        prices = []
        moqs = []
        cities = set()
        
        for seller in sellers:
            # Collect prices
            pricing_tiers = seller.get("pricingTiers", [])
            for tier in pricing_tiers:
                price = tier.get("pricePerUnit") or tier.get("price")
                if price and price > 0:
                    prices.append(float(price))
            if seller.get("lowestPrice"):
                prices.append(float(seller["lowestPrice"]))
            
            # Collect MOQs
            moq = seller.get("moq")
            if moq:
                moqs.append(int(moq))
            
            # Collect cities
            city = seller.get("city")
            if city:
                cities.add(city)
        
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        min_moq = min(moqs) if moqs else None
        available_cities = list(cities)
        
        # Get specifications from product or first seller
        specifications = product.get("specifications", {})
        if not specifications and sellers:
            specifications = sellers[0].get("specifications", {}) or sellers[0].get("searchableAttributes", {})
        
        # Generate all SEO components
        existing_slugs = []  # In production, query DB for existing slugs
        
        seo_data = {
            # Core SEO fields
            "seoSlug": cls.generate_seo_slug(product_name, category_name, existing_slugs),
            "seoTitle": cls.generate_seo_title(product_name, category_name),
            "seoDescription": cls.generate_seo_description(
                product_name, category_name, seller_count, min_price, max_price, min_moq
            ),
            "seoContent": cls.generate_seo_content(
                product_name, category_name, specifications, 
                product.get("description"), seller_count, available_cities
            ),
            
            # Structured data
            "jsonLd": cls.generate_json_ld(product, sellers, category_name),
            "breadcrumbJsonLd": cls.generate_breadcrumb_json_ld(
                product_name, 
                product.get("slug", ""),
                category_name,
                category_slug
            ),
            "faqJsonLd": cls.generate_faq_json_ld(product_name, category_name, seller_count, min_price),
            
            # Internal links
            "internalLinks": cls.generate_internal_links(
                str(product.get("_id", "")),
                product_name,
                category_id,
                category_name,
                category_slug,
                similar_products,
                available_cities
            ),
            
            # Meta info for frontend
            "sellerCount": seller_count,
            "minPrice": min_price,
            "maxPrice": max_price,
            "minMoq": min_moq,
            "availableCities": available_cities,
            
            # Canonical URL
            "canonicalUrl": f"{cls.SITE_URL}/product/{product.get('slug', '')}",
            
            # Generation timestamp
            "seoGeneratedAt": datetime.now(timezone.utc).isoformat()
        }
        
        return seo_data
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _clean_product_name(name: str) -> str:
        """Clean and normalize product name."""
        if not name:
            return "Industrial Product"
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', name).strip()
        # Capitalize properly (title case for display)
        return clean.title() if clean.islower() else clean
    
    @staticmethod
    def _extract_category_keyword(category_name: str) -> str:
        """Extract primary keyword from category name."""
        if not category_name:
            return "Industrial"
        # Take first significant word
        words = category_name.split()
        if len(words) > 0:
            # Remove common suffixes
            keyword = words[0]
            if keyword.lower() in ["all", "other", "misc", "miscellaneous"]:
                keyword = words[1] if len(words) > 1 else "Industrial"
            return keyword
        return "Industrial"
    
    @staticmethod
    def _get_category_key(category_name: str) -> str:
        """Map category name to industry key for applications."""
        if not category_name:
            return "default"
        
        name_lower = category_name.lower()
        
        # Motor-related
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
        elif "pump" in name_lower:
            return "pumps"
        elif "valve" in name_lower:
            return "valves"
        elif "bearing" in name_lower:
            return "bearings"
        elif "fastener" in name_lower or "bolt" in name_lower or "screw" in name_lower:
            return "fasteners"
        elif "tool" in name_lower:
            return "tools"
        elif "safety" in name_lower or "ppe" in name_lower:
            return "safety"
        
        return "default"
    
    @staticmethod
    def _format_spec_label(key: str) -> str:
        """Format specification key as human-readable label."""
        formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
        formatted = formatted.replace('_', ' ')
        return formatted.title()
    
    @staticmethod
    def _format_price(price: float) -> str:
        """Format price for display (Indian number format)."""
        if price >= 10000000:  # 1 Crore+
            return f"{price/10000000:.2f} Cr"
        elif price >= 100000:  # 1 Lakh+
            return f"{price/100000:.2f} L"
        elif price >= 1000:
            return f"{price:,.0f}"
        else:
            return f"{price:.2f}"


# Singleton instance
seo_service = SEOService()
