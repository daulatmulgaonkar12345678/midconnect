"""
ENTERPRISE SEARCH NORMALIZATION SERVICE
========================================

Handles:
1. Unit normalization (1/2hp = 0.5hp = half hp = 500w)
2. Synonym expansion (ampere = amp = amps)
3. Token generation for searchable text
4. Query parsing to extract attributes

This is the core intelligence behind enterprise search.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class ParsedQuery:
    """Result of parsing a search query"""
    original: str
    normalized_text: str
    extracted_attributes: Dict[str, Any]
    search_tokens: List[str]
    category_hint: Optional[str]
    location_hint: Optional[str]


class SearchNormalizationService:
    """
    Enterprise-grade search normalization service.
    
    Converts user inputs like "half hp motor ampr" into structured searchable data.
    """
    
    # ==================== UNIT CONVERSION TABLES ====================
    
    # Power conversions (base unit: HP)
    POWER_TO_HP = {
        # Watts to HP (1 HP ≈ 746 watts)
        'w': 1/746,
        'watt': 1/746,
        'watts': 1/746,
        'kw': 1000/746,
        'kilowatt': 1000/746,
        'kilowatts': 1000/746,
        # HP variations
        'hp': 1,
        'horsepower': 1,
        'bhp': 1,
    }
    
    # Fraction mappings
    FRACTION_TO_DECIMAL = {
        '1/4': 0.25,
        '1/2': 0.5,
        '3/4': 0.75,
        '1/3': 0.33,
        '2/3': 0.67,
        '1/8': 0.125,
        '3/8': 0.375,
        '5/8': 0.625,
        '7/8': 0.875,
    }
    
    # Word fractions
    WORD_FRACTION_TO_DECIMAL = {
        'quarter': 0.25,
        'half': 0.5,
        'three quarter': 0.75,
        'three-quarter': 0.75,
        'one quarter': 0.25,
        'one-quarter': 0.25,
        'one half': 0.5,
        'one-half': 0.5,
    }
    
    # ==================== SYNONYM MAPPINGS ====================
    
    SYNONYMS = {
        # Electrical units
        'ampere': ['amp', 'amps', 'ampr', 'amperes', 'a'],
        'volt': ['voltage', 'v', 'volts'],
        'watt': ['w', 'watts'],
        'horsepower': ['hp', 'bhp', 'horse power'],
        
        # Phase types
        'single phase': ['1 phase', '1phase', 'single-phase', '1-phase', '1ph', 'single ph'],
        'three phase': ['3 phase', '3phase', 'three-phase', '3-phase', '3ph', 'three ph'],
        
        # Motor types
        'motor': ['moter', 'motors', 'moters'],
        'pump': ['pumps'],
        'compressor': ['compressors', 'compresser'],
        
        # Materials
        'copper': ['cu', 'cupper'],
        'aluminum': ['aluminium', 'al'],
        'steel': ['stainless steel', 'ss'],
        
        # Common typos
        'electric': ['electrc', 'electic', 'electrical'],
        'industrial': ['industral', 'industriel'],
    }
    
    # Reverse synonym map for quick lookup
    SYNONYM_TO_CANONICAL = {}
    for canonical, synonyms in SYNONYMS.items():
        for syn in synonyms:
            SYNONYM_TO_CANONICAL[syn.lower()] = canonical
        SYNONYM_TO_CANONICAL[canonical.lower()] = canonical
    
    # ==================== CATEGORY KEYWORDS ====================
    
    CATEGORY_KEYWORDS = {
        'motor': ['motor', 'moter', 'motors', 'engine'],
        'pump': ['pump', 'pumps', 'submersible'],
        'compressor': ['compressor', 'compressors'],
        'transformer': ['transformer', 'transformers'],
        'cable': ['cable', 'cables', 'wire', 'wires'],
        'switch': ['switch', 'switches', 'mcb', 'mccb'],
        'panel': ['panel', 'panels', 'board', 'boards'],
    }
    
    # ==================== ATTRIBUTE PATTERNS ====================
    
    # Patterns to extract attributes from text
    ATTRIBUTE_PATTERNS = [
        # Power patterns
        (r'(\d+(?:\.\d+)?)\s*(?:hp|horsepower|bhp)', 'power_hp', float),
        (r'(\d+(?:\.\d+)?)\s*(?:kw|kilowatt)', 'power_kw', float),
        (r'(\d+(?:\.\d+)?)\s*(?:w|watt)(?:s)?', 'power_watts', float),
        
        # Voltage patterns
        (r'(\d+(?:\.\d+)?)\s*(?:v|volt|voltage)(?:s)?', 'voltage', float),
        
        # Current patterns
        (r'(\d+(?:\.\d+)?)\s*(?:a|amp|amps|ampere)(?:s)?', 'current', float),
        
        # RPM patterns
        (r'(\d+)\s*(?:rpm|r\.p\.m)', 'rpm', int),
        
        # Phase patterns
        (r'(single|1|one)\s*(?:phase|ph)', 'phase', lambda x: 'single'),
        (r'(three|3)\s*(?:phase|ph)', 'phase', lambda x: 'three'),
    ]
    
    # ==================== MAIN METHODS ====================
    
    def normalize_power_value(self, value: float, from_unit: str) -> Tuple[float, List[str]]:
        """
        Normalize power value to HP and generate search variations.
        
        Args:
            value: Numeric value
            from_unit: Original unit (hp, kw, w, etc.)
        
        Returns:
            Tuple of (normalized HP value, list of search tokens)
        """
        from_unit = from_unit.lower().strip()
        
        # Convert to HP
        multiplier = self.POWER_TO_HP.get(from_unit, 1)
        hp_value = value * multiplier
        
        # Generate search variations
        tokens = []
        
        # HP variations
        tokens.append(f"{hp_value}hp")
        tokens.append(f"{hp_value} hp")
        if hp_value == int(hp_value):
            tokens.append(f"{int(hp_value)}hp")
            tokens.append(f"{int(hp_value)} hp")
        
        # Watts equivalent (1 HP ≈ 746 watts)
        watts = hp_value * 746
        if watts >= 1000:
            kw = watts / 1000
            tokens.append(f"{kw}kw")
            tokens.append(f"{kw} kw")
        else:
            tokens.append(f"{int(watts)}w")
            tokens.append(f"{int(watts)} watt")
        
        # Fraction variations for common values
        fraction_map = {
            0.25: ['1/4hp', '1/4 hp', 'quarter hp'],
            0.5: ['1/2hp', '1/2 hp', 'half hp'],
            0.75: ['3/4hp', '3/4 hp', 'three quarter hp'],
            0.33: ['1/3hp', '1/3 hp'],
            0.67: ['2/3hp', '2/3 hp'],
        }
        
        if hp_value in fraction_map:
            tokens.extend(fraction_map[hp_value])
        
        return hp_value, tokens
    
    def parse_power_from_text(self, text: str) -> Optional[Tuple[float, str]]:
        """
        Extract power value from text like "1/2 hp" or "500w".
        
        Returns:
            Tuple of (value, unit) or None
        """
        text = text.lower().strip()
        
        # Check for word fractions first (e.g., "half hp")
        for word, decimal in self.WORD_FRACTION_TO_DECIMAL.items():
            if word in text:
                for unit in ['hp', 'horsepower']:
                    if unit in text:
                        return decimal, 'hp'
        
        # Check for numeric fractions (e.g., "1/2 hp")
        for fraction, decimal in self.FRACTION_TO_DECIMAL.items():
            pattern = rf'{re.escape(fraction)}\s*(?:hp|horsepower|bhp)'
            if re.search(pattern, text):
                return decimal, 'hp'
        
        # Check for decimal values
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*(hp|horsepower|bhp)', 'hp'),
            (r'(\d+(?:\.\d+)?)\s*(kw|kilowatt)', 'kw'),
            (r'(\d+(?:\.\d+)?)\s*(w|watt)', 'w'),
        ]
        
        for pattern, unit in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                return value, unit
        
        return None
    
    def expand_synonyms(self, text: str) -> str:
        """
        Replace synonyms with canonical terms.
        
        "ampr" → "ampere"
        "moter" → "motor"
        """
        words = text.lower().split()
        result = []
        
        for word in words:
            canonical = self.SYNONYM_TO_CANONICAL.get(word, word)
            result.append(canonical)
        
        return ' '.join(result)
    
    def extract_attributes(self, text: str) -> Dict[str, Any]:
        """
        Extract structured attributes from search text.
        
        "230v motor 0.5hp" → {voltage: 230, power_hp: 0.5}
        """
        attributes = {}
        text_lower = text.lower()
        
        for pattern, attr_name, converter in self.ATTRIBUTE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = converter(match.group(1))
                    attributes[attr_name] = value
                except (ValueError, IndexError):
                    pass
        
        # Handle power unit conversions
        if 'power_kw' in attributes and 'power_hp' not in attributes:
            attributes['power_hp'] = attributes['power_kw'] * (1000/746)
        elif 'power_watts' in attributes and 'power_hp' not in attributes:
            attributes['power_hp'] = attributes['power_watts'] / 746
        
        return attributes
    
    def detect_category(self, text: str) -> Optional[str]:
        """
        Detect product category from search text.
        """
        text_lower = text.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return None
    
    def detect_location_hint(self, text: str) -> Optional[str]:
        """
        Detect location hints from search text.
        
        "near me" → user's location
        "in pune" → Pune
        """
        text_lower = text.lower()
        
        if 'near me' in text_lower or 'nearby' in text_lower:
            return 'near_me'
        
        # Check for "in <city>" pattern
        match = re.search(r'in\s+(\w+)', text_lower)
        if match:
            return match.group(1).title()
        
        return None
    
    def generate_search_tokens(self, listing_data: Dict) -> List[str]:
        """
        Generate normalized search tokens for a listing.
        
        This is called when saving a listing to pre-compute searchable tokens.
        """
        tokens = set()
        
        # Product name tokens
        product_name = listing_data.get('productName', '')
        if product_name:
            tokens.update(product_name.lower().split())
            # Add synonym expansions
            expanded = self.expand_synonyms(product_name)
            tokens.update(expanded.split())
        
        # Category tokens
        category_name = listing_data.get('categoryName', '')
        if category_name:
            tokens.update(category_name.lower().split())
        
        # Description tokens
        description = listing_data.get('description', '')
        if description:
            # Only add significant words (skip common words)
            words = description.lower().split()
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'for', 'of', 'to', 'in', 'on', 'at', 'by'}
            tokens.update(w for w in words if w not in stop_words and len(w) > 2)
        
        # Attribute tokens with unit variations
        attributes = listing_data.get('searchableAttributes', {})
        attribute_labels = listing_data.get('attributeLabels', {})
        
        for key, value in attributes.items():
            label = attribute_labels.get(key, key)
            
            # Add label
            tokens.add(label.lower())
            
            # Add value with variations
            if isinstance(value, (int, float)):
                tokens.add(str(value))
                
                # Power variations
                if 'power' in key.lower() or 'hp' in key.lower() or 'watt' in key.lower():
                    _, power_tokens = self.normalize_power_value(value, 'hp')
                    tokens.update(t.lower() for t in power_tokens)
                
                # Voltage variations
                elif 'volt' in key.lower() or 'voltage' in key.lower():
                    tokens.add(f"{value}v")
                    tokens.add(f"{value} volt")
                    tokens.add(f"{value} voltage")
                
                # Current variations
                elif 'current' in key.lower() or 'amp' in key.lower():
                    tokens.add(f"{value}a")
                    tokens.add(f"{value} amp")
                    tokens.add(f"{value} ampere")
            
            elif isinstance(value, str):
                tokens.update(value.lower().split())
        
        # Location tokens
        seller_city = listing_data.get('sellerCity', '')
        seller_state = listing_data.get('sellerState', '')
        if seller_city:
            tokens.add(seller_city.lower())
        if seller_state:
            tokens.add(seller_state.lower())
        
        return list(tokens)
    
    def parse_search_query(self, query: str) -> ParsedQuery:
        """
        Parse a user search query into structured components.
        
        "half hp motor ampr near me" →
        {
            original: "half hp motor ampr near me",
            normalized_text: "0.5 hp motor ampere",
            extracted_attributes: {power_hp: 0.5},
            search_tokens: ["0.5hp", "motor", "ampere"],
            category_hint: "motor",
            location_hint: "near_me"
        }
        """
        # Expand synonyms
        normalized = self.expand_synonyms(query)
        
        # Extract power from text and normalize
        power_result = self.parse_power_from_text(query)
        if power_result:
            value, unit = power_result
            hp_value, _ = self.normalize_power_value(value, unit)
            # Replace the original power mention with normalized
            normalized = re.sub(
                r'(half|quarter|one|two|three|\d+(?:\.\d+)?(?:/\d+)?)\s*(?:hp|horsepower|bhp|kw|kilowatt|w|watt)(?:s)?',
                f'{hp_value} hp',
                normalized,
                flags=re.IGNORECASE
            )
        
        # Extract structured attributes
        attributes = self.extract_attributes(query)
        
        # Detect category
        category = self.detect_category(query)
        
        # Detect location
        location = self.detect_location_hint(query)
        
        # Remove location hints from search text
        search_text = re.sub(r'\b(near me|nearby|in \w+)\b', '', normalized, flags=re.IGNORECASE).strip()
        
        # Generate search tokens
        tokens = list(set(search_text.lower().split()))
        
        return ParsedQuery(
            original=query,
            normalized_text=search_text,
            extracted_attributes=attributes,
            search_tokens=tokens,
            category_hint=category,
            location_hint=location
        )


# Singleton instance
search_normalizer = SearchNormalizationService()
