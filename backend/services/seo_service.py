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
SEO_VERSION = 7

# Supported programmatic SEO intents (single source of truth)
SUPPORTED_INTENTS = ["price", "buy", "suppliers", "wholesale", "cheap"]
INTENT_WORDS = {
    "price": "Price of",
    "buy": "Buy",
    "suppliers": "Top",
    "wholesale": "Wholesale",
    "cheap": "Cheap",
}
INTENT_CTAS = {
    "price": "Compare prices from verified sellers.",
    "buy": "Buy directly from verified manufacturers.",
    "suppliers": "Connect with top verified suppliers.",
    "wholesale": "Get wholesale rates on bulk orders.",
    "cheap": "Find the most affordable options.",
}

# Template types drive content variation (prevents duplicate content at scale)
TEMPLATE_TYPES = ["MARKET", "BUYER", "LOCAL", "EDUCATION"]

# Top 20 Indian cities for programmatic SEO (single source of truth, used by
# sitemap, internal linking, and content generation).
TOP_CITIES = [
    "mumbai", "delhi", "bangalore", "pune", "hyderabad",
    "chennai", "ahmedabad", "kolkata", "surat", "jaipur",
    "nagpur", "indore", "bhopal", "lucknow", "kanpur",
    "coimbatore", "vadodara", "rajkot", "visakhapatnam", "nashik",
]

# Local SEO signals per city: industrial zones + nearby cities.
# Curated (not AI-generated) to avoid factual errors. Used to enrich
# city pages with locality signals that Google rewards.
CITY_LOCAL_DATA: Dict[str, Dict[str, List[str]]] = {
    "mumbai":       {"zones": ["Andheri MIDC", "Bhandup Industrial Estate", "Taloja MIDC", "Navi Mumbai"], "nearby": ["Thane", "Navi Mumbai", "Kalyan", "Vasai"]},
    "delhi":        {"zones": ["Okhla Industrial Area", "Naraina", "Mayapuri", "Bawana"], "nearby": ["Gurgaon", "Noida", "Faridabad", "Ghaziabad"]},
    "bangalore":    {"zones": ["Peenya Industrial Area", "Bommasandra", "Jigani", "Electronics City"], "nearby": ["Hosur", "Tumkur", "Mysore", "Bidadi"]},
    "pune":         {"zones": ["Bhosari MIDC", "Chakan MIDC", "Pimpri Chinchwad", "Hinjewadi"], "nearby": ["Pimpri", "Chakan", "Talegaon", "Satara"]},
    "hyderabad":    {"zones": ["Balanagar", "Jeedimetla", "Nacharam", "Medchal"], "nearby": ["Secunderabad", "Medchal", "Sangareddy", "Rangareddy"]},
    "chennai":      {"zones": ["Ambattur Industrial Estate", "Guindy", "Sriperumbudur", "Oragadam"], "nearby": ["Kanchipuram", "Sriperumbudur", "Tiruvallur", "Chengalpattu"]},
    "ahmedabad":    {"zones": ["Naroda GIDC", "Vatva GIDC", "Odhav", "Sanand GIDC"], "nearby": ["Gandhinagar", "Sanand", "Kalol", "Mehsana"]},
    "kolkata":      {"zones": ["Howrah Industrial Area", "Dum Dum", "Kasba", "Salt Lake Sector V"], "nearby": ["Howrah", "Barrackpore", "Dankuni", "Hooghly"]},
    "surat":        {"zones": ["Sachin GIDC", "Pandesara GIDC", "Hazira", "Udhna"], "nearby": ["Navsari", "Bharuch", "Vapi", "Ankleshwar"]},
    "jaipur":       {"zones": ["Sitapura Industrial Area", "VKI Area", "Malviya Industrial Area", "Bagru"], "nearby": ["Kishangarh", "Ajmer", "Alwar", "Dausa"]},
    "nagpur":       {"zones": ["MIDC Hingna", "Butibori MIDC", "Kamptee", "Wadi"], "nearby": ["Wardha", "Kamptee", "Bhandara", "Amravati"]},
    "indore":       {"zones": ["Pithampur Industrial Area", "Sanwer Road", "Rau", "Palda"], "nearby": ["Pithampur", "Dewas", "Ujjain", "Mhow"]},
    "bhopal":       {"zones": ["Govindpura Industrial Area", "Mandideep", "Bagroda", "Piplani"], "nearby": ["Mandideep", "Sehore", "Vidisha", "Raisen"]},
    "lucknow":      {"zones": ["Amausi Industrial Area", "Chinhat", "Talkatora", "Scooter India"], "nearby": ["Kanpur", "Unnao", "Barabanki", "Sitapur"]},
    "kanpur":       {"zones": ["Dada Nagar", "Panki", "Jajmau", "Fazalganj"], "nearby": ["Unnao", "Lucknow", "Fatehpur", "Kanpur Dehat"]},
    "coimbatore":   {"zones": ["SIDCO Industrial Estate", "Peelamedu", "Kurichi", "Singanallur"], "nearby": ["Tirupur", "Pollachi", "Salem", "Erode"]},
    "vadodara":     {"zones": ["Makarpura GIDC", "Gorwa", "Savli", "Halol"], "nearby": ["Halol", "Padra", "Anand", "Bharuch"]},
    "rajkot":       {"zones": ["Aji GIDC", "Lodhika GIDC", "Metoda", "Shapar-Veraval"], "nearby": ["Morbi", "Jamnagar", "Gondal", "Jetpur"]},
    "visakhapatnam":{"zones": ["Visakhapatnam Special Economic Zone", "Auto Nagar", "Gajuwaka", "Duvvada"], "nearby": ["Vizianagaram", "Anakapalle", "Srikakulam", "Tuni"]},
    "nashik":       {"zones": ["Ambad MIDC", "Satpur MIDC", "Sinnar MIDC", "Ozar"], "nearby": ["Sinnar", "Igatpuri", "Niphad", "Dindori"]},
}


def get_city_local_data(city: str) -> Dict[str, List[str]]:
    """Return industrial zones + nearby cities for a city (empty lists if unknown)."""
    return CITY_LOCAL_DATA.get((city or "").strip().lower(), {"zones": [], "nearby": []})


def get_template_type(slug: str, city: Optional[str] = None, intent: Optional[str] = None) -> str:
    """
    Deterministically pick a content template based on slug+city+intent hash.
    Ensures the SAME (slug, city, intent) combination always renders with the
    SAME template, while spreading variations across pages.
    """
    seed = f"{slug or ''}|{(city or '').lower()}|{(intent or '').lower()}"
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return TEMPLATE_TYPES[h % len(TEMPLATE_TYPES)]


class SEOService:
    """Enterprise SEO content generator using marketplace-standard templates."""
    
    SITE_NAME = "UdyogConnect"
    SITE_URL = "https://www.udyogconnect.in"
    
    # SEO v2.1 - Max slug length
    MAX_SLUG_LENGTH = 90
    
    # Industry applications mapping for different product categories
    INDUSTRY_APPLICATIONS = {
        "motors": ["CNC lathes and milling machines", "textile spinning units", "HVAC blowers and cooling towers", "packaging machinery", "cement mill drives"],
        "electrical": ["distribution panel wiring", "VFD control panels", "solar plant string wiring", "industrial lighting circuits", "sub-station switchgear"],
        "steel": ["structural fabrication for warehouses", "automotive chassis components", "construction rebar and beams", "pressure vessel fabrication", "heavy equipment frames"],
        "chemicals": ["textile dyeing baths", "effluent treatment plants", "API pharmaceutical synthesis", "soap and detergent lines", "boiler water treatment"],
        "cables": ["LT/HT power distribution", "control panel wiring", "fiber-optic backbone networks", "solar DC harness runs", "lift and elevator controls"],
        "pipes": ["process plant piping headers", "potable water supply mains", "fire sprinkler risers", "agricultural drip irrigation", "compressed air lines"],
        "pumps": ["boiler feed water circulation", "chemical dosing on ETPs", "building cold-water boosters", "farm irrigation systems", "CIP lines in food plants"],
        "valves": ["steam header isolation in boilers", "oil and gas flow control", "chemical injection skid isolation", "chiller water modulation", "fire-suppression shutoff"],
        "bearings": ["conveyor belt idlers", "electric motor spindles", "CNC machine tool spindles", "automotive wheel hubs", "textile ring frames"],
        "fasteners": ["steel structural connections", "machine base mounting", "automotive chassis assembly", "PCB and electronics housing", "modular furniture joinery"],
        "tools": ["sheet-metal cutting and bending", "die-and-mould finishing", "automotive MRO workshops", "pipeline welding and fabrication", "panel wiring and crimping"],
        "safety": ["chemical plant lockout/tagout", "high-rise construction sites", "welding and cutting workshops", "oil refinery turnarounds", "warehouse forklift operations"],
        "default": ["panel wiring", "machine installation", "industrial automation", "factory maintenance", "OEM manufacturing"]
    }

    # Specific use-case one-liners (drop-in sentence fragments, not bullet lists)
    # Used to replace generic phrases like "used in many industries".
    INDUSTRY_USE_CASES_PROSE = {
        "motors":     "driving CNC machines, industrial fans, textile looms, water pumps, and material-handling conveyors",
        "electrical": "panel-board wiring, switchgear assembly, solar plant connections, and factory-floor distribution",
        "steel":      "structural fabrication, automotive components, construction reinforcement, and pressure-vessel manufacturing",
        "chemicals":  "dyeing and finishing, effluent treatment, pharmaceutical synthesis, and boiler-water treatment",
        "cables":     "LT/HT power distribution, control panels, solar installations, and elevator control wiring",
        "pipes":      "process plants, water supply, fire-safety networks, irrigation systems, and compressed-air lines",
        "pumps":      "boiler circulation, chemical dosing, building water supply, farm irrigation, and food-plant CIP",
        "valves":     "steam isolation, oil and gas flow control, chemical injection, chiller circuits, and fire shutoff",
        "bearings":   "conveyor idlers, motor spindles, CNC tool-holders, automotive hubs, and textile machinery",
        "fasteners":  "steel structural joints, machine bases, automotive chassis, electronics housings, and modular furniture",
        "tools":      "sheet-metal work, mould finishing, workshop MRO, pipeline welding, and panel wiring",
        "safety":     "chemical-plant lockout, high-rise construction, welding shops, oil-refinery turnarounds, and warehouses",
        "default":    "panel wiring, machine installation, industrial automation, factory maintenance, and OEM assembly",
    }

    # Who typically buys each category — used in the "Who should buy this?" section.
    BUYER_PROFILES = {
        "motors":     ["OEM machine builders", "factory maintenance engineers", "HVAC contractors", "pump integrators", "automation system integrators"],
        "electrical": ["electrical contractors", "panel builders", "MEP consultants", "solar EPC firms", "industrial plant engineers"],
        "steel":      ["fabricators and structural shops", "EPC contractors", "real-estate builders", "automotive tier-1/2 suppliers", "equipment manufacturers"],
        "chemicals":  ["process plant operators", "textile dye houses", "ETP/STP operators", "pharmaceutical manufacturers", "water-treatment contractors"],
        "cables":     ["electrical contractors", "panel-board assemblers", "solar EPC firms", "telecom operators", "industrial MRO teams"],
        "pipes":      ["plumbing contractors", "HVAC/MEP installers", "EPC contractors", "irrigation dealers", "process plant operators"],
        "pumps":      ["mechanical contractors", "building MEP teams", "irrigation retailers", "food-processing plants", "chemical plant engineers"],
        "valves":     ["process plant engineers", "EPC contractors", "boiler operators", "fire-safety contractors", "MEP system integrators"],
        "bearings":   ["machine OEMs", "maintenance and reliability teams", "CNC workshop owners", "automotive dealers", "conveyor installers"],
        "fasteners":  ["fabricators", "OEM assembly lines", "automotive suppliers", "electronics contract manufacturers", "furniture makers"],
        "tools":      ["fabrication workshops", "automotive MRO", "electrical contractors", "die-and-mould makers", "industrial maintenance teams"],
        "safety":     ["plant safety officers", "EHS consultants", "construction contractors", "refinery shutdown teams", "warehouse supervisors"],
        "default":    ["contractors", "manufacturers", "factory maintenance teams", "OEM buyers", "MRO supervisors"],
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
        seller_count: int = 0,
        intent: str = None
    ) -> str:
        """
        Generate CTR-optimized title tag (55-65 characters).

        Format with intent (programmatic SEO):
            "{IntentWord} {Product} in {City} ({Year}) | From ₹{Price} | UdyogConnect"
        Otherwise falls through to existing city/general logic.
        """
        clean_name = cls._clean_product_name(product_name)
        year = datetime.now(timezone.utc).year

        # ===== INTENT TITLE =====
        if intent and intent.lower() in SUPPORTED_INTENTS:
            intent_word = INTENT_WORDS.get(intent.lower(), "Top")
            price_str = f"From ₹{cls._format_price(min_price)}" if min_price else None

            if city:
                city_title = city.strip().title()
                if price_str:
                    full = f"{intent_word} {clean_name} in {city_title} ({year}) | {price_str} | {cls.SITE_NAME}"
                    if len(full) <= 65:
                        return full
                mid = f"{intent_word} {clean_name} in {city_title} ({year}) | {cls.SITE_NAME}"
                if len(mid) <= 65:
                    return mid
                short = f"{intent_word} {clean_name} in {city_title} | {cls.SITE_NAME}"
                if len(short) <= 65:
                    return short
            else:
                # Intent without city — still keep intent keyword
                if price_str:
                    full = f"{intent_word} {clean_name} in India ({year}) | {price_str} | {cls.SITE_NAME}"
                    if len(full) <= 65:
                        return full
                mid = f"{intent_word} {clean_name} in India ({year}) | {cls.SITE_NAME}"
                if len(mid) <= 65:
                    return mid
            # Fall through to existing logic if nothing fits

        # Pick an intent word deterministically based on product name (original logic)
        intent_words = ["Best", "Top", "Compare"]
        intent_pick = intent_words[sum(ord(c) for c in product_name.lower()) % len(intent_words)]
        
        price_str = f"From ₹{cls._format_price(min_price)}" if min_price else None
        
        # ===== CITY TITLE (city pages or seller-specific) =====
        if city:
            city_title = city.strip().title()
            
            # Try full: Best {Product} in {City} (2026) | From ₹X | UdyogConnect
            if price_str:
                full = f"{intent_pick} {clean_name} in {city_title} ({year}) | {price_str} | {cls.SITE_NAME}"
                if len(full) <= 65:
                    return full
            
            # Try: Best {Product} in {City} (2026) | UdyogConnect
            mid = f"{intent_pick} {clean_name} in {city_title} ({year}) | {cls.SITE_NAME}"
            if len(mid) <= 65:
                return mid
            
            # Try: Best {Product} in {City} | UdyogConnect
            short = f"{intent_pick} {clean_name} in {city_title} | {cls.SITE_NAME}"
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
            full = f"{intent_pick} {clean_name} Prices ({year}) | {price_str} | {cls.SITE_NAME}"
            if len(full) <= 65:
                return full

        # Try: {Intent} {Product} Prices in India ({year}) | UdyogConnect — keeps intent+year even without price
        intent_year = f"{intent_pick} {clean_name} Prices in India ({year}) | {cls.SITE_NAME}"
        if len(intent_year) <= 65:
            return intent_year

        # Try: {Intent} {Product} in India ({year}) | UdyogConnect — shorter form that still carries intent+year
        intent_short = f"{intent_pick} {clean_name} in India ({year}) | {cls.SITE_NAME}"
        if len(intent_short) <= 65:
            return intent_short

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
        city: str = None,
        intent: str = None
    ) -> str:
        """
        Generate CTR-optimized meta description (140-160 characters, v5 format).
        Supports programmatic intent modifier for scale SEO.
        """
        clean_name = cls._clean_product_name(product_name)
        region = city.strip().title() if city else "India"

        # Intent-specific CTA for programmatic pages (more targeted)
        if intent and intent.lower() in SUPPORTED_INTENTS:
            intent_cta = INTENT_CTAS.get(intent.lower(), "")
            intent_prefix = {
                "price": f"{clean_name} price in {region}",
                "buy": f"Buy {clean_name} in {region}",
                "suppliers": f"Top {clean_name} suppliers in {region}",
                "wholesale": f"Wholesale {clean_name} in {region}",
                "cheap": f"Cheap {clean_name} in {region}",
            }.get(intent.lower(), f"{clean_name} in {region}")

            if min_price:
                desc = (
                    f"{intent_prefix}. Starting from ₹{cls._format_price(min_price)}. "
                    f"{intent_cta} Get quotes on UdyogConnect."
                )
            elif seller_count > 0:
                desc = (
                    f"{intent_prefix}. {seller_count}+ verified sellers. "
                    f"{intent_cta} Get quotes on UdyogConnect."
                )
            else:
                desc = f"{intent_prefix}. {intent_cta} Request quotes on UdyogConnect today."
        else:
            cta = "Compare verified manufacturers, dealers & distributors on UdyogConnect."
            close = "Get best deals today."

            if min_price:
                desc = (
                    f"{clean_name} suppliers in {region}. "
                    f"Prices start from ₹{cls._format_price(min_price)}. "
                    f"{cta} {close}"
                )
            elif seller_count > 1:
                desc = (
                    f"{clean_name} suppliers in {region}. "
                    f"{seller_count}+ verified sellers with transparent pricing. "
                    f"{cta}"
                )
            else:
                desc = (
                    f"{clean_name} suppliers in {region}. "
                    f"{cta} {close}"
                )

        # Trim to 160 chars — try tightened variant first
        if len(desc) > 160:
            if min_price:
                desc = (
                    f"{clean_name} suppliers in {region}. From ₹{cls._format_price(min_price)}. "
                    f"Compare verified sellers on UdyogConnect."
                )
            else:
                desc = (
                    f"{clean_name} suppliers in {region}. "
                    f"Compare verified sellers on UdyogConnect."
                )
        if len(desc) > 160:
            desc = desc[:157].rstrip() + "..."

        # Pad if too short (< 140)
        if len(desc) < 140:
            pads = [" Bulk orders welcome.", " Free RFQ.", " Pan-India delivery."]
            for pad in pads:
                if len(desc) + len(pad) <= 160:
                    desc = desc.rstrip('.') + '.' + pad
                    if len(desc) >= 140:
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
        
        # ===== Introduction — human-style opener with real use-case prose =====
        seller_text = f"{seller_count}+ verified" if seller_count > 1 else "verified"
        use_case_prose = cls.INDUSTRY_USE_CASES_PROSE.get(category_key, cls.INDUSTRY_USE_CASES_PROSE["default"])
        price_mention = f" Prices start from ₹{cls._format_price(min_price)}." if min_price else ""
        # City availability signal — boosts "{product} in {city}" queries
        # Always mention 3-5 top cities (falls back to MAJOR_CITIES when no seller-city data yet)
        top_cities_for_intro = (available_cities or [])[:5]
        if len(top_cities_for_intro) < 3:
            fallback = [c for c in ["Pune", "Mumbai", "Delhi", "Ahmedabad", "Bangalore"] if c not in top_cities_for_intro]
            top_cities_for_intro = (top_cities_for_intro + fallback)[:5]
        city_names = ", ".join(c.title() for c in top_cities_for_intro)

        # Rotate between 3 intro openers (deterministic per product) to avoid AI-template patterns
        opener_variants = [
            f"Looking for {clean_name} suppliers across India?",
            f"Need {clean_name} for your next project?",
            f"Sourcing {clean_name} at competitive rates?",
        ]
        opener_idx = sum(ord(c) for c in product_name.lower()) % len(opener_variants)
        opener_line = opener_variants[opener_idx]

        intro = f"""{opener_line} {cls.SITE_NAME} connects you with {seller_text} suppliers, manufacturers, and dealers of {clean_name} across {city_names} and other major industrial hubs.{price_mention}

{clean_name} is typically used for {use_case_prose}. Procurement teams choose {cls.SITE_NAME} to compare multiple verified sellers in one place, lock in bulk pricing, and shortlist local suppliers for faster delivery and on-site support."""
        sections.append(intro.strip())

        # ===== Template-variant highlight block (MARKET / BUYER / LOCAL / TECH) =====
        # Picks one of 4 variants deterministically by product hash. Existing
        # sections below are kept — this is an ADDITIONAL section, not a replacement.
        product_slug_hash = cls.generate_seo_slug(product_name, category_name)
        template_type = get_template_type(product_slug_hash)
        price_display = f"₹{cls._format_price(min_price)}" if min_price else "competitive market rates"
        seller_phrase = f"{seller_count}+" if seller_count > 1 else "multiple"

        if template_type == "MARKET":
            variant_block = f"""## {clean_name} Price Trends & Market Snapshot

Current market price for {clean_name} starts from {price_display}. Prices vary based on grade, brand, specifications, and order quantity — bulk-procurement contracts typically unlock 10-20% savings versus spot rates.

### Supplier Availability

{seller_phrase} verified suppliers are currently active on {cls.SITE_NAME}, each with its own MOQ, delivery timeline, and payment terms. Multi-quote comparison is the fastest way to benchmark prices in real time.

### Demand Across Industrial Hubs

High demand is observed from manufacturing units, EPC contractors, and OEM procurement teams. Monthly price movement is driven by raw-material index trends, forex (for imported variants), and seasonal capex cycles."""
        elif template_type == "BUYER":
            buyer_profiles = cls.BUYER_PROFILES.get(category_key, cls.BUYER_PROFILES["default"])[:3]
            buyer_bullets = "\n".join(f"- {bp[0].upper()+bp[1:]} handling industrial-scale projects" for bp in buyer_profiles)
            variant_block = f"""## Who Typically Buys {clean_name}?

{buyer_bullets}
- Factory maintenance teams for recurring replacement needs
- Contract manufacturers sourcing for OEM programmes

### Where is {clean_name} Used?

{clean_name} is commonly specified for {use_case_prose} — the exact choice depends on load conditions, environmental exposure, and compliance requirements on the project.

### Buying Tips

Before ordering, compare suppliers on MOQ, lead time, GST-inclusive landed cost, and warranty. Ask for mill-test certificates or sample batches for first-time suppliers — this is the single biggest quality safeguard."""
        elif template_type == "LOCAL":
            variant_block = f"""## Why Source {clean_name} Locally

Buying {clean_name} from a local supplier cuts freight cost by 3-7%, shrinks lead time to 24-48 hours for in-stock items, and simplifies on-site quality inspection.

### Industrial Zones & Local Supply

Common supply zones include MIDC estates, GIDC estates, SIDCO areas, and neighbourhood industrial clusters — each hosts a different mix of manufacturers, stockists, and authorised dealers. Local sellers on {cls.SITE_NAME} display their GST, business type, and fulfilment area upfront.

### Nearby City Coverage

Sellers also serve nearby regions for quick dispatch — state capital buyers often get same-day delivery, while surrounding districts receive {clean_name} within 1-2 business days from {cls.SITE_NAME} verified suppliers."""
        else:  # TECH / EDUCATION
            variant_block = f"""## {clean_name} Specifications & Real-World Usage

{clean_name} is built for industrial-grade duty — selected on dimensions, material grade, certification (ISO/BIS/IS-equivalent), and warranty. {price_display.capitalize() if isinstance(price_display, str) else 'Pricing'} applies to standard-spec variants; custom/premium grades carry a 15-40% uplift.

### Technical Benefits

- Consistent performance under rated industrial loads
- Compatible with multiple end-use applications (see list below)
- Reliable service life when installed per manufacturer spec

### Common End-Use Applications

Used for {use_case_prose}. Selecting the right spec for each end-use — not just the lowest-priced SKU — directly affects uptime, safety, and total cost of ownership."""

        sections.append(variant_block.strip())
        
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
        
        # ===== H2: Real Use Cases (category-specific, not generic) =====
        real_apps = applications[:5]
        app_bullets = "\n".join(f"- {a[0].upper() + a[1:]}" for a in real_apps)
        app_section = f"""## Real-World Applications of {clean_name}

{clean_name} is most commonly specified for {use_case_prose}. On the ground, procurement teams source {clean_name} for:

{app_bullets}

Each of these end-uses carries different spec requirements (grade, tolerance, certification), MOQ expectations, and delivery urgency — which is why comparing multiple verified suppliers on {cls.SITE_NAME} helps you match the right seller to the exact application, not just the headline price."""
        sections.append(app_section.strip())

        # ===== H2: Who Should Buy This =====
        buyer_profiles = cls.BUYER_PROFILES.get(category_key, cls.BUYER_PROFILES["default"])
        buyer_bullets = "\n".join(f"- **{bp[0].upper() + bp[1:]}** — typically placing {'recurring' if i < 2 else 'project-based'} orders for {'in-stock' if i % 2 == 0 else 'made-to-order'} variants" for i, bp in enumerate(buyer_profiles[:5]))
        who_section = f"""## Who Should Buy {clean_name}?

{clean_name} on {cls.SITE_NAME} is most often sourced by:

{buyer_bullets}

Whether you order a single piece for a repair or a full truckload for a site, our verified sellers handle both — with transparent MOQ, unit pricing, and GST-compliant invoicing on every transaction."""
        sections.append(who_section.strip())
        
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
        # Always generate for top 3-5 cities (use seller cities first, fall back to MAJOR_CITIES).
        if available_cities and len(available_cities) >= 3:
            cities = available_cities[:15]
        else:
            seller_cities_lower = {c.lower() for c in (available_cities or [])}
            fallback_cities = [c for c in ["Pune", "Mumbai", "Delhi", "Ahmedabad", "Bangalore"] if c.lower() not in seller_cities_lower]
            cities = (available_cities or []) + fallback_cities
            cities = cities[:15]

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
                f"support for your industrial procurement. [View all {clean_name} "
                f"suppliers in {city} →]({city_link})"
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
    def generate_programmatic_content(
        cls,
        product_name: str,
        category_name: str = None,
        specifications: Dict[str, Any] = None,
        description: str = None,
        seller_count: int = 0,
        available_cities: List[str] = None,
        min_price: float = None,
        max_price: float = None,
        avg_delivery_days: int = None,
        city: str = None,
        intent: str = None,
        template_type: str = None,
    ) -> str:
        """
        Generate programmatic SEO content with city/intent/template variations.

        Reuses the full `generate_seo_content` output and prepends a unique,
        template-driven opening section (200-300 words) that varies by:
        - city (LOCAL emphasis)
        - intent (BUYER/MARKET/EDUCATION emphasis)
        - template_type (MARKET / BUYER / LOCAL / EDUCATION)

        This keeps Jaccard similarity below ~40% across combinations while
        reusing proven content infrastructure. No new architecture required.
        """
        clean_name = cls._clean_product_name(product_name)
        region = city.strip().title() if city else "India"
        year = datetime.now(timezone.utc).year

        # Resolve template type deterministically if not provided
        slug_for_hash = cls.generate_seo_slug(product_name, category_name)
        if not template_type or template_type not in TEMPLATE_TYPES:
            template_type = get_template_type(slug_for_hash, city, intent)

        price_line = (
            f"Current market prices start from ₹{cls._format_price(min_price)}."
            if min_price else "Pricing varies by specification, quantity, and supplier."
        )
        seller_line = (
            f"{seller_count}+ verified sellers" if seller_count > 1
            else ("one verified seller" if seller_count == 1 else "multiple verified sellers")
        )

        # ===== H1 — template-aware =====
        if city and intent:
            intent_verb = INTENT_WORDS.get((intent or "").lower(), "Top")
            h1 = f"# {intent_verb} {clean_name} in {region} ({year}) — Verified Suppliers & Best Prices"
        elif city:
            h1 = f"# {clean_name} Suppliers in {region} ({year}) — Prices, Sellers & Delivery"
        elif intent:
            intent_verb = INTENT_WORDS.get((intent or "").lower(), "Top")
            h1 = f"# {intent_verb} {clean_name} in India ({year}) — Verified Manufacturers & Dealers"
        else:
            h1 = f"# {clean_name} Suppliers in India — Verified Manufacturers & Dealers ({year})"

        # ===== Template-specific opening section (200-300 words, UNIQUE per combo) =====
        if template_type == "MARKET":
            opener = f"""## {clean_name} Price & Market Snapshot in {region}

The {clean_name} market in {region} is served by {seller_line} on {cls.SITE_NAME}. {price_line} Over the last 90 days, buyer interest in {clean_name} has grown steadily across {region}'s industrial corridors — driven by manufacturing expansion, construction projects, and MSME demand.

If you are a procurement manager comparing rates, our live listings let you benchmark quotes from multiple {region}-based suppliers at once. Lot-size discounts typically kick in above 50-100 units, and bulk procurement contracts can unlock an additional 10-20% savings vs. spot pricing.

Seasonal demand, raw-material index fluctuations, and forex exposure (for imported variants) affect {clean_name} pricing month-to-month. Tracking price movement on {cls.SITE_NAME} helps you time large orders optimally."""
        elif template_type == "BUYER":
            intent_context = INTENT_CTAS.get((intent or "").lower(), "Compare quotes from verified sellers.")
            opener = f"""## How to Choose the Right {clean_name} in {region}

Buying {clean_name} in {region} is a multi-step decision: matching specifications, validating supplier credentials, and negotiating delivery terms. This guide helps you move from a shortlist to a confirmed order efficiently.

**Step 1 — Define your specifications.** Clarify grade, size, material, and tolerance upfront. Ambiguous specs trigger multiple quote revisions.

**Step 2 — Compare {seller_line}.** Request quotes from 3-5 {region}-based sellers. Look at unit price, MOQ, GST-inclusive final cost, and payment terms — not just headline rates.

**Step 3 — Validate quality.** Ask for mill-test certificates, sample delivery, or a factory visit for large orders. Verified sellers on {cls.SITE_NAME} display GST, business registration, and badge status upfront.

**Step 4 — Lock delivery SLA.** {region} has excellent logistics to most of India; same-day delivery is common within city. {intent_context}"""
        elif template_type == "LOCAL":
            opener = f"""## Why Source {clean_name} from {region}

{region} is one of India's most active industrial hubs for {clean_name}. The city hosts manufacturers, stockists, and authorized dealers — meaning local procurement eliminates long freight transits, duty surprises, and unreliable last-mile handoffs.

**Proximity = lower cost.** A {region}-based supplier saves 2-7% on freight for medium-sized orders versus sourcing from a distant state. Round-trip quality inspections are affordable too.

**Local service network.** {seller_line.capitalize()} in {region} offer on-site support, after-sales servicing, and easy returns — critical for capital equipment and consumables alike.

**Faster lead times.** Typical {region} delivery within 24-48 hours for in-stock items. Custom/made-to-order variants: 5-14 days. {price_line}

**Regional expertise.** Sellers in {region} understand local substrate, climate, and compliance requirements — important for materials, coatings, and electrical components."""
        else:  # EDUCATION
            cat_key = cls._get_category_key(category_name)
            apps = cls.INDUSTRY_APPLICATIONS.get(cat_key, cls.INDUSTRY_APPLICATIONS["default"])
            app_text = ", ".join(apps[:4])
            opener = f"""## Understanding {clean_name} — What It Is and Where It's Used

{clean_name} is a core industrial input used across {app_text}. Engineers specify it based on performance parameters, environmental tolerance, and compliance needs — the right selection directly affects uptime, safety, and lifecycle cost.

**How {clean_name} works.** {clean_name} performs under specific mechanical, thermal, or electrical loads depending on the grade. Premium variants offer higher reliability at a price premium; standard grades cover 80% of general-purpose needs.

**Common industries and applications.** {clean_name} is sourced routinely by manufacturing plants, EPC contractors, fabricators, MRO teams, and OEMs across {region}. {seller_line.capitalize()} on {cls.SITE_NAME} supply both standard and custom variants.

**Specification basics.** Buyers typically evaluate {clean_name} on dimensions, material grade, certifications (ISO, BIS, IS-equivalent), and warranty. {price_line}"""

        # ===== INTENT-SPECIFIC SUBSECTION (200-300 words) =====
        # Injected when `intent` is set, forces uniqueness even when two pages share template.
        intent_block = ""
        if intent and intent.lower() in SUPPORTED_INTENTS:
            intent_key = intent.lower()
            intent_blocks = {
                "price": f"""## {clean_name} Price Trends in {region}

{clean_name} pricing in {region} moves with raw-material indices, import duty, and seasonal demand. {price_line} Short-term price volatility is typical (±3-8% month-over-month) — savvy procurement teams track multi-supplier quotes over 4-6 weeks before placing large contracts.

**Factors affecting {clean_name} prices in {region}:**
- **Grade and specification** — premium grades command 15-40% higher prices
- **Order quantity** — volume discounts of 8-18% above 500 units
- **Payment terms** — 2-5% price reduction for upfront payments vs. credit
- **Supplier type** — direct manufacturer pricing is 10-20% below dealer/stockist
- **Delivery urgency** — stock items are 5-10% cheaper than made-to-order

To lock the best rate, send parallel RFQs to {seller_line} on {cls.SITE_NAME} and compare bottom-line (GST-inclusive) pricing rather than headline rates.""",
                "buy": f"""## How to Buy {clean_name} in {region} — Step-by-Step

Ready to place an order? Here is the exact buying workflow verified buyers follow on {cls.SITE_NAME}:

1. **Shortlist sellers.** Filter by {region}-based suppliers with verified badge and positive response rate.
2. **Send a clear RFQ.** Specify grade, quantity, delivery address, target timeline, and payment preference. Clarity here cuts quote cycles by 50%.
3. **Compare 3-5 quotes.** Evaluate unit price, MOQ, GST-inclusive total, freight terms (ex-works vs. delivered), and lead time.
4. **Request a sample or test certificate.** For first-time suppliers, a sample batch or mill-test report protects against quality risk.
5. **Finalize terms and pay securely.** Standard practice: 30-50% advance on confirmation, balance on dispatch/delivery. UdyogConnect helps track delivery milestones.
6. **Inspect on delivery.** Physical inspection + QC on key parameters before unloading. Raise disputes through the UdyogConnect buyer protection flow if needed.

{price_line} Most experienced {region} buyers close purchase orders within 5-10 business days from initial RFQ.""",
                "suppliers": f"""## Top {clean_name} Suppliers in {region}

{region} hosts {seller_line} of {clean_name}, ranging from direct manufacturers to authorized dealers and specialized stockists. How do you pick the right one?

**Tier 1 — Manufacturers.** Best for large-volume, spec-heavy orders. Lowest per-unit cost, longer lead time, stricter MOQ. Ideal when you need consistent grade over multi-month contracts.

**Tier 2 — Authorized dealers and distributors.** Balance of price and flexibility. Faster lead times, smaller MOQ, warranty pass-through from the OEM. Best for mid-volume orders.

**Tier 3 — Stockists and traders.** Fastest delivery from existing inventory. Higher per-unit cost. Best for urgent, low-volume needs or trial orders.

All verified {clean_name} suppliers in {region} on {cls.SITE_NAME} display their business type, GST credentials, response time, and historical ratings — helping you pick the right supplier type for each specific purchase.""",
                "wholesale": f"""## Wholesale {clean_name} Sourcing in {region}

Wholesale {clean_name} procurement in {region} is about unit-economics, predictability, and supplier redundancy. Bulk buyers (typically 500+ units/month) unlock pricing 10-25% below spot rates.

**Wholesale negotiation playbook:**
- **Lock annual/quarterly volume commitments** for 8-15% additional discount
- **Request price-lock clauses** against raw-material volatility (common in metals, polymers)
- **Standardize SKUs** across sellers to simplify QC and reduce price dispersion
- **Qualify 2-3 approved suppliers** to maintain negotiating leverage and supply continuity
- **Align payment cycles** — 30-45 day credit terms are standard for verified buyers

{price_line} {seller_line.capitalize()} in {region} on {cls.SITE_NAME} quote wholesale rates on request — submit a single RFQ and receive side-by-side proposals within 24-48 hours.""",
                "cheap": f"""## Finding Affordable {clean_name} in {region}

Looking for the most cost-effective {clean_name} options in {region}? Here is how to optimize for price without sacrificing acceptable quality:

**Strategy 1 — Standard-grade SKUs.** Premium variants can cost 30-50% more for marginal performance gains. For general-purpose applications, standard grade covers most needs.

**Strategy 2 — Bulk + combined freight.** Pooling smaller orders into a single 500+ unit shipment unlocks volume tiers and shaves unit freight cost by 5-12%.

**Strategy 3 — Local sourcing.** {region}-based suppliers save freight cost and lead time versus out-of-state alternatives. Typical savings: 3-7% landed cost.

**Strategy 4 — Stock clearance deals.** Dealers occasionally list discounted inventory — follow {cls.SITE_NAME} listings and set up alerts for your SKU.

{price_line} Compare "cheapest" quotes carefully — always check certifications, warranty, and return policy. The lowest headline price is not always the lowest total cost of ownership.""",
            }
            intent_block = "\n\n" + intent_blocks.get(intent_key, "")

        # Pull the full base content, then strip its H1 (we have our template-specific one)
        base_content = cls.generate_seo_content(
            product_name=product_name,
            category_name=category_name,
            specifications=specifications,
            description=description,
            seller_count=seller_count,
            available_cities=available_cities,
            min_price=min_price,
            max_price=max_price,
            avg_delivery_days=avg_delivery_days,
        )
        # Remove the first line (original H1) — we inject our programmatic one
        base_without_h1 = re.sub(r'^#\s[^\n]*\n+', '', base_content, count=1)

        return f"{h1}\n\n{opener}{intent_block}\n\n{base_without_h1}"
    
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
        available_cities: List[str] = None,
        product_slug: str = None
    ) -> Dict[str, Any]:
        """
        Generate internal links for SEO.
        
        Includes:
        - Link to category page
        - Links to similar products
        - Links to city-specific listings (real /products/{slug}/in/{city} URLs)
        - Links to intent+city pages (programmatic SEO scale)
        - Link to top-rated products
        """
        links = {
            "category": None,
            "similarProducts": [],
            "cityPages": [],
            "intentCityPages": [],
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
        
        # City pages — use real /products/{slug}/in/{city} URLs (not query-param filters)
        if available_cities and product_slug:
            for city in available_cities[:6]:
                city_slug = re.sub(r'[^a-z0-9]+', '-', city.lower()).strip('-')
                links["cityPages"].append({
                    "name": f"{product_name} in {city}",
                    "url": f"{cls.SITE_URL}/products/{product_slug}/in/{city_slug}"
                })
        elif available_cities:
            # Fallback for callers that don't pass product_slug
            for city in available_cities[:6]:
                city_slug = re.sub(r'[^a-z0-9]+', '-', city.lower()).strip('-')
                links["cityPages"].append({
                    "name": f"{product_name} in {city}",
                    "url": f"{cls.SITE_URL}/products?city={city_slug}"
                })

        # Intent+City pages — programmatic internal linking for top 3 cities × 5 intents.
        # Surface up to 15 per product (enough for Googlebot crawl, not enough to spam).
        if available_cities and product_slug:
            for city in available_cities[:3]:
                city_slug = re.sub(r'[^a-z0-9]+', '-', city.lower()).strip('-')
                for intent in SUPPORTED_INTENTS:
                    links["intentCityPages"].append({
                        "name": f"{intent.title()} {product_name} in {city}",
                        "intent": intent,
                        "url": f"{cls.SITE_URL}/products/{product_slug}/{intent}/in/{city_slug}"
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
        Returns True if SEO is missing, weak, outdated version.
        Does NOT overwrite manually edited SEO (if marked).

        v5 thresholds:
          - seoVersion < SEO_VERSION
          - OR title length < 50
          - OR description missing / < 120
          - OR content word count < 600
          - OR missing FAQ block
          - OR slug missing
        """
        # Never overwrite manual edits
        if product.get("seoManuallyEdited"):
            return False

        # Version check — triggers regeneration when template/schema evolves
        current_version = product.get("seoVersion", 0) or 0
        if current_version < SEO_VERSION:
            return True

        seo_title = product.get("seoTitle") or ""
        seo_desc = product.get("seoDescription") or ""
        seo_content = product.get("seoContent") or ""
        slug = product.get("slug") or ""

        if not seo_title or len(seo_title) < 50:
            return True
        if not seo_desc or len(seo_desc) < 120:
            return True
        if not seo_content:
            return True
        if len(seo_content.split()) < 600:
            return True
        if "frequently asked" not in seo_content.lower() and "faq" not in seo_content.lower():
            return True
        if not slug:
            return True
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
