"""
ENTERPRISE SEO SERVICE v3.0
============================
Marketplace-standard SEO content generation for UdyogConnect.

Features:
- CTR-optimized titles with intent words, pricing, and year
- Dynamic meta descriptions (140-160 chars, CTA-driven)
- 500-900 word on-page content with FAQ + Market Insights
- Enhanced JSON-LD (Product, AggregateOffer, BreadcrumbList, Organization, FAQ)
- Internal linking with city page URLs
- Category-based keyword injection
- seoVersion tracking for bulk updates

NO AI dependency - deterministic templates that Google loves.
"""

import re
import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("seo_service")

# Current SEO version — bump when content templates change
SEO_VERSION = 4


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
    def generate_seo_title(
        cls, 
        product_name: str, 
        category_name: str = None,
        city: str = None,
        min_price: float = None,
        seller_count: int = 0
    ) -> str:
        """
        Generate CTR-optimized title tag (55-65 characters).
        
        Format (with city+price): Best {Product} in {City} (2026) | From ₹{price} | UdyogConnect
        Format (with city):       Best {Product} in {City} | Industrial Supplier | UdyogConnect
        Format (no city+price):   Compare {Product} Prices (2026) | From ₹{price} | UdyogConnect
        Format (no city):         Buy {Product} Online | {Category} Suppliers India | UdyogConnect
        
        Uses dynamic intent words: Best, Top, Compare based on product hash.
        """
        clean_name = cls._clean_product_name(product_name)
        year = datetime.now(timezone.utc).year
        
        # Pick an intent word deterministically based on product name
        intent_words = ["Best", "Top", "Compare"]
        intent = intent_words[sum(ord(c) for c in product_name.lower()) % len(intent_words)]
        
        price_str = f"From ₹{cls._format_price(min_price)}" if min_price else None
        
        # ===== CITY TITLE (city pages or seller-specific) =====
        if city:
            city_title = city.strip().title()
            
            # Try full: Best {Product} in {City} (2026) | From ₹X | UdyogConnect
            if price_str:
                full = f"{intent} {clean_name} in {city_title} ({year}) | {price_str} | {cls.SITE_NAME}"
                if len(full) <= 65:
                    return full
            
            # Try: Best {Product} in {City} (2026) | UdyogConnect
            mid = f"{intent} {clean_name} in {city_title} ({year}) | {cls.SITE_NAME}"
            if len(mid) <= 65:
                return mid
            
            # Try: Best {Product} in {City} | UdyogConnect
            short = f"{intent} {clean_name} in {city_title} | {cls.SITE_NAME}"
            if len(short) <= 65:
                return short
            
            # Truncate: {Product} in {City} | UdyogConnect
            minimal = f"{clean_name} in {city_title} | {cls.SITE_NAME}"
            if len(minimal) <= 65:
                return minimal
            max_len = 65 - len(f" in {city_title} | {cls.SITE_NAME}") - 3
            return f"{clean_name[:max(max_len,10)]}... in {city_title} | {cls.SITE_NAME}"
        
        # ===== GENERAL TITLE (no city) =====
        category_keyword = cls._extract_category_keyword(category_name) if category_name else None
        
        # Try full: Compare {Product} Prices (2026) | From ₹X | UdyogConnect
        if price_str:
            full = f"{intent} {clean_name} Prices ({year}) | {price_str} | {cls.SITE_NAME}"
            if len(full) <= 65:
                return full
        
        # Try: Buy {Product} Online | {Category} Suppliers India | UdyogConnect
        if category_keyword:
            cat_title = f"Buy {clean_name} Online | {category_keyword} Suppliers India | {cls.SITE_NAME}"
        else:
            cat_title = f"Buy {clean_name} Online | Verified Suppliers India | {cls.SITE_NAME}"
        if len(cat_title) <= 65:
            return cat_title
        
        # Shorter: {Product} | {Category} Suppliers India | UdyogConnect
        if category_keyword:
            short = f"{clean_name} | {category_keyword} Suppliers India | {cls.SITE_NAME}"
        else:
            short = f"{clean_name} | Suppliers India | {cls.SITE_NAME}"
        if len(short) <= 65:
            return short
        
        # Minimal
        minimal = f"{clean_name} Suppliers India | {cls.SITE_NAME}"
        if len(minimal) <= 65:
            return minimal
        
        max_len = 65 - len(f" Suppliers India | {cls.SITE_NAME}") - 3
        return f"{clean_name[:max(max_len,10)]}... Suppliers India | {cls.SITE_NAME}"
    
    # ==================== META DESCRIPTION ENHANCEMENT ====================
    
    @classmethod
    def generate_seo_description(
        cls, 
        product_name: str, 
        category_name: str = None, 
        seller_count: int = 0,
        min_price: float = None,
        max_price: float = None,
        min_moq: int = None,
        city: str = None
    ) -> str:
        """
        Generate CTR-optimized meta description (140-160 characters).
        Includes: product name, city, starting price, CTA (Compare/Get Quote/Buy Now).
        """
        clean_name = cls._clean_product_name(product_name)
        city_text = f" in {city.strip().title()}" if city else ""
        
        # Pick CTA based on product hash for variation
        ctas = [
            f"Compare prices & get quotes on {cls.SITE_NAME}.",
            f"Get quotes from verified suppliers on {cls.SITE_NAME}.",
            f"Request quotes instantly on {cls.SITE_NAME}.",
        ]
        cta = ctas[sum(ord(c) for c in product_name.lower()) % len(ctas)]
        
        # Build with price if available
        if min_price and seller_count > 1:
            desc = f"Compare prices of {clean_name}{city_text} starting from ₹{cls._format_price(min_price)}. {seller_count}+ verified industrial suppliers. {cta}"
        elif min_price:
            desc = f"Buy {clean_name}{city_text} starting from ₹{cls._format_price(min_price)}. Verified industrial suppliers. {cta}"
        elif seller_count > 1:
            desc = f"Find {seller_count}+ verified {clean_name} suppliers{city_text or ' in India'}. {cta}"
        else:
            desc = f"Find verified industrial suppliers of {clean_name}{city_text or ' in India'}. {cta}"
        
        # Trim to 160 chars
        if len(desc) > 160:
            # Shorter version without count
            if min_price:
                desc = f"Compare {clean_name}{city_text} from ₹{cls._format_price(min_price)}. Verified suppliers. {cta}"
            else:
                desc = f"Find verified {clean_name} suppliers{city_text or ' in India'}. {cta}"
        
        if len(desc) > 160:
            desc = desc[:157] + "..."
        
        # Pad if too short
        if len(desc) < 140:
            pads = [" Bulk orders welcome.", " Free quotes.", " Best deals guaranteed."]
            for pad in pads:
                if len(desc) + len(pad) <= 160:
                    desc = desc.rstrip('.') + '.' + pad
                    break
        
        return desc
    
    # ==================== STRUCTURED ON-PAGE CONTENT ====================
    
    @classmethod
    def generate_seo_content(
        cls,
        product_name: str,
        category_name: str = None,
        specifications: Dict[str, Any] = None,
        description: str = None,
        seller_count: int = 0,
        available_cities: List[str] = None,
        min_price: float = None,
        max_price: float = None,
        avg_delivery_days: int = None
    ) -> str:
        """
        Generate 500-900 word structured SEO content block.
        
        Structure:
        H1: {Product Name} Suppliers in India
        Introduction: product + industrial use
        H2: Types (if applicable)
        H2: Specifications
        H2: Market Insights (real data: sellers, prices, delivery)
        H2: Applications (industry-based)
        H2: Buying Guide
        H2: Available Cities
        H2: Why Choose UdyogConnect
        H2: FAQ (min 3 questions with answers)
        """
        clean_name = cls._clean_product_name(product_name)
        category_key = cls._get_category_key(category_name)
        applications = cls.INDUSTRY_APPLICATIONS.get(category_key, cls.INDUSTRY_APPLICATIONS["default"])
        year = datetime.now(timezone.utc).year
        
        sections = []
        
        # ===== H1 =====
        sections.append(f"# {clean_name} Suppliers in India — Verified Manufacturers & Dealers ({year})")
        
        # ===== Introduction (80-120 words) =====
        seller_text = f"{seller_count}+ verified" if seller_count > 1 else "verified"
        app_list_short = ", ".join(applications[:3])
        price_mention = f" Prices start from ₹{cls._format_price(min_price)}." if min_price else ""
        # City availability signal — boosts "{product} in {city}" queries
        top_cities_for_intro = (available_cities or [])[:5]
        city_avail_line = ""
        if top_cities_for_intro:
            city_names = ", ".join(c.title() for c in top_cities_for_intro)
            city_avail_line = f" Available from verified suppliers in {city_names} and other major Indian cities."
        intro = f"""{cls.SITE_NAME} connects you with {seller_text} suppliers, manufacturers, and dealers of {clean_name} across India.{price_mention}{city_avail_line} Whether you need bulk quantities for industrial projects or are looking for competitive pricing, our platform offers direct access to trusted sellers with transparent pricing and specifications.

{clean_name} is a critical component used in {app_list_short} and many other industrial applications. Sourcing from reliable suppliers ensures consistent quality, timely delivery, and compliance with industry standards. With our B2B marketplace, procurement teams can compare offers from multiple sellers and negotiate directly to get the best value."""
        sections.append(intro.strip())
        
        # ===== H2: Types & Variants =====
        type_variants = cls._generate_type_variants(clean_name, category_key)
        if type_variants:
            types_section = f"""## Types of {clean_name}

Industrial {clean_name} is available in several variants to meet diverse requirements:

{type_variants}

Each variant serves specific industrial needs. Contact our verified suppliers to find the right type of {clean_name} for your application."""
            sections.append(types_section.strip())
        
        # ===== H2: Specifications =====
        if specifications and len(specifications) > 0:
            spec_lines = []
            for key, value in list(specifications.items())[:10]:
                label = cls._format_spec_label(key)
                if value:
                    spec_lines.append(f"- **{label}**: {value}")
            
            if spec_lines:
                spec_section = f"""## Specifications of {clean_name}

Our suppliers offer {clean_name} with various specifications to meet your requirements:

{chr(10).join(spec_lines)}

Specifications vary by manufacturer and model. Contact sellers directly to discuss custom specifications for your specific project needs. Bulk orders may qualify for customized products tailored to your exact requirements."""
                sections.append(spec_section.strip())
        
        # ===== H2: Market Insights (NEW — real data injection) =====
        insights_parts = []
        if seller_count > 0:
            insights_parts.append(f"Currently, {seller_count} verified sellers offer {clean_name} on {cls.SITE_NAME}")
        if min_price and max_price and min_price != max_price:
            insights_parts.append(f"Market price ranges from ₹{cls._format_price(min_price)} to ₹{cls._format_price(max_price)} depending on specifications, brand, and order quantity")
        elif min_price:
            insights_parts.append(f"Prices start from ₹{cls._format_price(min_price)} for standard variants")
        if avg_delivery_days:
            insights_parts.append(f"Average delivery time is {avg_delivery_days}-{avg_delivery_days + 2} business days across India")
        if available_cities and len(available_cities) > 0:
            top_cities = ", ".join(available_cities[:5])
            insights_parts.append(f"Top supply hubs include {top_cities}")
        
        if insights_parts:
            bullet_lines = "\n".join(f"- {p}." for p in insights_parts)
            market_section = f"""## {clean_name} Market Insights ({year})

Here is a real-time snapshot of the {clean_name} market on {cls.SITE_NAME}:

{bullet_lines}

These figures are updated as new suppliers join and pricing changes. Check the product page for the latest data."""
            sections.append(market_section.strip())
        
        # ===== H2: Applications =====
        app_list = ", ".join(applications[:4])
        app_section = f"""## Applications of {clean_name}

{clean_name} is widely used across multiple industries including {app_list}. Key application areas include:

- **Manufacturing**: Factory automation, production lines, industrial machinery, and assembly operations
- **Construction**: Building projects, infrastructure development, civil engineering, and structural works
- **Engineering**: Fabrication shops, maintenance operations, equipment assembly, and testing facilities
- **Energy & Utilities**: Power generation, distribution systems, renewable energy installations, and grid maintenance
- **Commercial & OEM**: Office buildings, retail establishments, and original equipment manufacturing

The versatility of {clean_name} makes it indispensable across India's growing industrial sector. Whether for new installations or replacement parts, quality sourcing is essential for operational efficiency."""
        sections.append(app_section.strip())
        
        # ===== H2: Buying Guide =====
        buying_section = f"""## How to Buy {clean_name} at Best Price

Follow these steps to source {clean_name} efficiently through {cls.SITE_NAME}:

1. **Define Requirements**: Specify exact specifications, quantity, and delivery timeline
2. **Compare Suppliers**: Browse multiple verified sellers and compare prices, MOQ, and lead times
3. **Request Quotations**: Send RFQ to shortlisted suppliers for competitive quotes
4. **Verify Quality**: Check seller ratings, certifications, and sample availability
5. **Negotiate & Order**: Negotiate pricing for bulk orders and confirm delivery terms

Buying directly from manufacturers on {cls.SITE_NAME} can save 10-30% compared to traditional distribution channels. Our platform ensures price transparency and eliminates middlemen."""
        sections.append(buying_section.strip())
        
        # ===== H2: Available Cities =====
        # Per-city H3 sections boost "{product} in {city}" query rankings.
        if available_cities and len(available_cities) > 0:
            cities = available_cities[:15]
        else:
            cities = cls.MAJOR_CITIES[:15]

        product_slug = cls.generate_seo_slug(product_name, category_name)
        top_cities_detail = cities[:5]
        detail_blocks = []
        for city in top_cities_detail:
            city_slug = city.lower().replace(' ', '-')
            city_link = f"/products/{product_slug}/in/{city_slug}"
            price_note = (
                f" starting from ₹{cls._format_price(min_price)}"
                if min_price else ""
            )
            detail_blocks.append(
                f"### {clean_name} Suppliers in {city}\n\n"
                f"Looking for {clean_name} suppliers in {city}? Connect with verified "
                f"local manufacturers, dealers, and distributors{price_note}. Local "
                f"suppliers in {city} offer faster delivery, easier returns, and on-site "
                f"support. [View all {clean_name} suppliers in {city} →]({city_link})"
            )

        remaining = cities[5:10]
        remaining_links = ", ".join(
            f"[{c}](/products/{product_slug}/in/{c.lower().replace(' ', '-')})"
            for c in remaining
        ) if remaining else ""

        other_cities_line = (
            f"Also available in {remaining_links}." if remaining_links else ""
        )

        city_section = f"""## {clean_name} Suppliers by City

Find {clean_name} suppliers in major industrial cities across India. Sourcing locally
gives you faster delivery, easier returns, and on-site technical support.

{chr(10) + chr(10).join(detail_blocks)}

{other_cities_line}

Our network spans all major industrial hubs, ensuring quick delivery and local support for your procurement needs."""
        sections.append(city_section.strip())
        
        # ===== H2: Why Choose UdyogConnect =====
        why_section = f"""## Why Choose {cls.SITE_NAME} for {clean_name}?

{cls.SITE_NAME} is India's trusted B2B marketplace for industrial products. When sourcing {clean_name} through our platform, you benefit from:

1. **Verified Suppliers**: All sellers undergo strict verification including GST and business registration checks
2. **Price Transparency**: Compare quotes from multiple suppliers instantly with no hidden charges
3. **Direct Communication**: Connect directly with manufacturers and distributors — no brokers involved
4. **Pan-India Network**: Access suppliers across all major industrial cities with nationwide delivery
5. **Quality Assurance**: Trusted brands, certified products, and seller ratings for informed decisions
6. **Bulk Pricing**: Special rates for industrial quantities and long-term procurement contracts

Start sourcing {clean_name} today and get competitive quotes from verified suppliers across India."""
        sections.append(why_section.strip())
        
        # ===== H2: FAQ Section (min 3 questions) =====
        faq_section = cls._generate_faq_content(clean_name, category_name, seller_count, min_price)
        sections.append(faq_section)
        
        return "\n\n".join(sections)
    
    @classmethod
    def _generate_faq_content(
        cls, clean_name: str, category_name: str = None, 
        seller_count: int = 0, min_price: float = None
    ) -> str:
        """Generate FAQ section embedded in content (not just JSON-LD)."""
        seller_text = str(seller_count) if seller_count > 0 else "multiple"
        price_text = f"₹{cls._format_price(min_price)}" if min_price else "varies based on specifications"
        
        faqs = [
            (
                f"What is {clean_name} used for?",
                f"{clean_name} is used in manufacturing, construction, engineering, and industrial maintenance. Common applications include factory automation, production lines, infrastructure projects, and equipment assembly. It plays a vital role in India's industrial supply chain."
            ),
            (
                f"What is the price of {clean_name} in India?",
                f"The price of {clean_name} starts from {price_text} on {cls.SITE_NAME}. Final pricing depends on specifications, quantity, brand, and the supplier. Request quotes from multiple sellers to compare and find the best deal."
            ),
            (
                f"Which is the best {clean_name} for industrial use?",
                f"The best {clean_name} depends on your specific application, required specifications, and budget. {cls.SITE_NAME} lists {seller_text} verified suppliers offering various brands and grades. Compare seller ratings and product specifications to make an informed choice."
            ),
            (
                f"How do I get a quote for {clean_name}?",
                f"Visit the {clean_name} product page on {cls.SITE_NAME}, select a supplier, and click 'Request Quote'. Specify your requirements including quantity, delivery location, and timeline. You will receive competitive quotes directly from verified sellers."
            ),
        ]
        
        qa_lines = []
        for q, a in faqs:
            qa_lines.append(f"**Q: {q}**\n\n{a}")
        
        return f"""## Frequently Asked Questions about {clean_name}

{chr(10) + chr(10).join(qa_lines)}"""

    @classmethod
    def _generate_type_variants(cls, product_name: str, category_key: str) -> str:
        """Generate product type/variant list based on category."""
        variants_map = {
            "motors": [
                "**AC Motors**: Induction motors, synchronous motors for industrial drives",
                "**DC Motors**: Brushed and brushless DC motors for precision control",
                "**Servo Motors**: High-precision motors for CNC machines and robotics",
                "**Gear Motors**: Speed reduction motors for conveyors and material handling",
            ],
            "electrical": [
                "**Switch Gear**: MCBs, MCCBs, contactors, and relay panels",
                "**Distribution Boards**: LT panels, PCC panels, and MCC panels",
                "**Wiring Accessories**: Switches, sockets, junction boxes, and conduits",
                "**Transformers**: Step-up, step-down, and isolation transformers",
            ],
            "steel": [
                "**Flat Products**: Sheets, plates, coils, and strips in various grades",
                "**Long Products**: Bars, rods, angles, channels, and beams",
                "**Tubular Products**: Pipes, tubes, and hollow sections",
                "**Stainless Steel**: SS304, SS316, and other corrosion-resistant grades",
            ],
            "pipes": [
                "**GI Pipes**: Galvanized iron pipes for water supply and plumbing",
                "**CPVC Pipes**: Chemical-resistant pipes for industrial applications",
                "**HDPE Pipes**: High-density polyethylene pipes for drainage and irrigation",
                "**SS Pipes**: Stainless steel pipes for food, pharma, and chemical industries",
            ],
            "tools": [
                "**Hand Tools**: Wrenches, pliers, screwdrivers, and hammers",
                "**Power Tools**: Drills, grinders, saws, and sanders",
                "**Measuring Tools**: Calipers, micrometers, gauges, and levels",
                "**Cutting Tools**: Blades, bits, end mills, and reamers",
            ],
            "safety": [
                "**Head Protection**: Safety helmets, hard hats, and bump caps",
                "**Eye Protection**: Safety goggles, face shields, and welding shields",
                "**Respiratory Protection**: Dust masks, gas masks, and air-purifying respirators",
                "**Hand Protection**: Industrial gloves — leather, rubber, and cut-resistant",
            ],
        }
        
        variants = variants_map.get(category_key)
        if not variants:
            return ""
        
        return "\n".join(f"- {v}" for v in variants)
    
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
    
    # ==================== SEO QUALITY CHECK ====================
    
    @classmethod
    def should_regenerate_seo(cls, product: Dict[str, Any]) -> bool:
        """
        Check if a product's SEO data needs regeneration.
        Returns True if SEO is missing, weak, outdated version, or auto-generated and outdated.
        Does NOT overwrite manually edited SEO (if marked).
        """
        # Never overwrite manual edits
        if product.get("seoManuallyEdited"):
            return False

        # Version check — triggers regeneration when template/schema evolves
        current_version = product.get("seoVersion", 0) or 0
        if current_version < SEO_VERSION:
            return True

        # Check if core SEO fields exist
        seo_title = product.get("seoTitle") or ""
        seo_desc = product.get("seoDescription") or ""
        seo_content = product.get("seoContent") or ""
        slug = product.get("slug") or ""

        # Missing any core field
        if not seo_title or not seo_desc or not seo_content or not slug:
            return True

        # Weak title (too short or generic)
        if len(seo_title) < 30:
            return True

        # Weak description (too short)
        if len(seo_desc) < 120:
            return True

        # Weak content (< 400 words) or missing FAQ block
        word_count = len(seo_content.split())
        if word_count < 400:
            return True
        if "frequently asked" not in seo_content.lower() and "faq" not in seo_content.lower():
            return True

        # Slug doesn't follow v2.1 format
        if not slug.endswith("-supplier-india") and not re.match(r'^[a-z0-9-]+$', slug):
            return True

        return False
    
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
            "seoGeneratedAt": datetime.now(timezone.utc).isoformat(),
            # Version marker for bulk upgrade tracking
            "seoVersion": SEO_VERSION
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
