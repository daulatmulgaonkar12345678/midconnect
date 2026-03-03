"""
TOKEN-BASED SLUG RESOLVER SERVICE
==================================
Enterprise-grade, order-independent URL slug resolution.

This service solves the problem of:
- Partial slugs: "abc" should match "abc-power-tools-supplier-india"
- Word order variations: "hand-tools-abc" should match "abc-hand-tools-supplier-india"
- City/state additions: "abc-tools-mumbai" should still match the base product
- Typo tolerance: Uses token matching instead of exact matching

ALGORITHM:
1. Tokenize input slug into words (split by hyphen/space)
2. Remove common suffixes (supplier, india, buy, online)
3. Query products where ALL tokens exist in product name/slug
4. Rank by match quality (exact > partial)
5. Return best match with redirect info
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId

logger = logging.getLogger("slug_resolver_service")


class SlugResolverService:
    """
    Token-based, order-independent slug resolver.
    
    Features:
    - Order-independent matching ("abc-xyz" matches "xyz-abc")
    - Partial slug support ("abc" matches "abc-tools-supplier")
    - City/state tolerance (ignores location tokens)
    - Weighted scoring for best match
    """
    
    # Common suffixes to strip from search (not meaningful for matching)
    STOP_WORDS = {
        'supplier', 'suppliers', 'india', 'indian',
        'buy', 'online', 'best', 'top', 'cheap', 'price', 'prices',
        'manufacturer', 'manufacturers', 'dealer', 'dealers',
        'distributor', 'distributors', 'trader', 'traders',
        'wholesale', 'wholesaler', 'retailer',
        'in', 'at', 'for', 'the', 'a', 'an', 'of', 'and', 'or',
        'near', 'me', 'with'
    }
    
    # Major Indian cities to ignore in slug matching
    INDIAN_CITIES = {
        'mumbai', 'delhi', 'bangalore', 'bengaluru', 'chennai', 'kolkata',
        'hyderabad', 'pune', 'ahmedabad', 'surat', 'jaipur', 'lucknow',
        'kanpur', 'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam',
        'vadodara', 'coimbatore', 'ludhiana', 'rajkot', 'faridabad',
        'ghaziabad', 'patna', 'agra', 'nashik', 'meerut', 'varanasi',
        'allahabad', 'amritsar', 'ranchi', 'howrah', 'gwalior', 'jodhpur',
        'raipur', 'kota', 'chandigarh', 'gurgaon', 'noida', 'greater',
        # States
        'maharashtra', 'karnataka', 'tamil', 'nadu', 'andhra', 'pradesh',
        'telangana', 'gujarat', 'rajasthan', 'uttar', 'west', 'bengal',
        'madhya', 'bihar', 'punjab', 'haryana', 'kerala', 'odisha',
        'jharkhand', 'chhattisgarh', 'uttarakhand', 'himachal', 'goa'
    }
    
    def __init__(self, db):
        self.db = db
    
    def tokenize_slug(self, slug: str) -> List[str]:
        """
        Tokenize a slug into meaningful words.
        
        Process:
        1. Convert to lowercase
        2. Split by hyphens and spaces
        3. Remove stop words
        4. Remove city/state names
        5. Remove empty tokens
        
        Returns list of meaningful tokens.
        """
        if not slug:
            return []
        
        # Lowercase and split by non-alphanumeric
        tokens = re.split(r'[-\s_]+', slug.lower().strip())
        
        # Filter tokens
        meaningful_tokens = []
        for token in tokens:
            # Skip empty
            if not token:
                continue
            # Skip stop words
            if token in self.STOP_WORDS:
                continue
            # Skip cities/states
            if token in self.INDIAN_CITIES:
                continue
            # Skip very short tokens (likely noise)
            if len(token) < 2:
                continue
            # Skip pure numbers
            if token.isdigit():
                continue
            
            meaningful_tokens.append(token)
        
        return meaningful_tokens
    
    def calculate_match_score(
        self, 
        search_tokens: List[str], 
        product_tokens: List[str],
        product_name: str = ""
    ) -> float:
        """
        Calculate match score between search tokens and product.
        
        Scoring:
        - +10 points for each matching token
        - +20 bonus if ALL search tokens match
        - +15 bonus if name starts with first search token
        - +5 bonus if exact token order match
        
        Returns score (0-100+, higher is better)
        """
        if not search_tokens or not product_tokens:
            return 0.0
        
        score = 0.0
        matched_tokens = 0
        
        # Count matching tokens
        for token in search_tokens:
            # Check exact match
            if token in product_tokens:
                score += 10
                matched_tokens += 1
            else:
                # Check partial match (prefix)
                for pt in product_tokens:
                    if pt.startswith(token) or token.startswith(pt):
                        score += 5
                        matched_tokens += 1
                        break
        
        # Bonus: All tokens matched
        if matched_tokens >= len(search_tokens):
            score += 20
        
        # Bonus: Product name starts with first token
        if search_tokens and product_name:
            name_lower = product_name.lower()
            if name_lower.startswith(search_tokens[0]):
                score += 15
        
        # Bonus: Token order matches (partial)
        if len(search_tokens) >= 2:
            joined_search = '-'.join(search_tokens)
            joined_product = '-'.join(product_tokens)
            if joined_search in joined_product:
                score += 5
        
        # Penalty: Too many unmatched search tokens
        unmatched = len(search_tokens) - matched_tokens
        score -= unmatched * 5
        
        return max(0, score)
    
    async def resolve_slug(
        self, 
        identifier: str,
        return_all_matches: bool = False
    ) -> Tuple[Optional[Dict], bool, Optional[str], List[Dict]]:
        """
        Resolve a URL slug to a product using token-based matching.
        
        Args:
            identifier: The URL slug (e.g., "abc-power-tools-hand-tools")
            return_all_matches: If True, return all matching products
        
        Returns:
            (best_match, needs_redirect, canonical_slug, all_matches)
            
        Matching Priority:
        1. Exact slug match (no redirect needed)
        2. ObjectId match (redirect to canonical)
        3. Token-based match (redirect to canonical)
        """
        if not identifier:
            return None, False, None, []
        
        decoded = identifier.strip()
        
        # === Priority 1: Exact slug match ===
        exact_match = await self.db.products.find_one(
            {"slug": decoded},
            {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
        )
        if exact_match:
            return exact_match, False, exact_match.get("slug"), [exact_match]
        
        # === Priority 2: ObjectId match ===
        if len(decoded) == 24:
            try:
                oid = ObjectId(decoded)
                oid_match = await self.db.products.find_one(
                    {"_id": oid},
                    {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
                )
                if oid_match:
                    canonical = oid_match.get("slug")
                    return oid_match, True, canonical, [oid_match]
            except Exception:
                pass
        
        # === Priority 3: Legacy slug/ID lookup ===
        legacy_match = await self.db.products.find_one(
            {"$or": [
                {"legacySlugs": decoded},
                {"legacyIds": decoded}
            ]},
            {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
        )
        if legacy_match:
            canonical = legacy_match.get("slug")
            return legacy_match, True, canonical, [legacy_match]
        
        # === Priority 4: Token-based fuzzy matching ===
        search_tokens = self.tokenize_slug(decoded)
        
        if not search_tokens:
            # No meaningful tokens - can't match
            return None, False, None, []
        
        # Build regex patterns for token matching
        # Each token should appear somewhere in name or slug
        regex_conditions = []
        for token in search_tokens:
            # Match token as whole word or part of hyphenated word
            pattern = f"(^|[-\\s]){re.escape(token)}"
            regex_conditions.append({
                "$or": [
                    {"slug": {"$regex": pattern, "$options": "i"}},
                    {"name": {"$regex": pattern, "$options": "i"}},
                    {"searchAliases": {"$regex": pattern, "$options": "i"}}
                ]
            })
        
        # Query: Product must match ALL tokens (AND logic)
        if len(regex_conditions) == 1:
            query = regex_conditions[0]
        else:
            query = {"$and": regex_conditions}
        
        # Fetch potential matches
        cursor = self.db.products.find(
            query,
            {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
        ).limit(20)
        
        candidates = await cursor.to_list(20)
        
        if not candidates:
            # Try fallback: Match ANY token (more lenient)
            if len(regex_conditions) > 1:
                fallback_query = {"$or": regex_conditions}
                cursor = self.db.products.find(
                    fallback_query,
                    {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
                ).limit(10)
                candidates = await cursor.to_list(10)
        
        if not candidates:
            return None, False, None, []
        
        # Score and rank candidates
        scored_candidates = []
        for candidate in candidates:
            product_slug = candidate.get("slug", "")
            product_name = candidate.get("name", "")
            product_tokens = self.tokenize_slug(product_slug) + self.tokenize_slug(product_name)
            
            score = self.calculate_match_score(
                search_tokens, 
                list(set(product_tokens)),
                product_name
            )
            
            scored_candidates.append({
                "product": candidate,
                "score": score
            })
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Best match
        best = scored_candidates[0]
        best_product = best["product"]
        canonical_slug = best_product.get("slug")
        
        # Redirect needed if slug doesn't match exactly
        needs_redirect = decoded != canonical_slug
        
        if return_all_matches:
            all_matches = [sc["product"] for sc in scored_candidates]
            return best_product, needs_redirect, canonical_slug, all_matches
        
        return best_product, needs_redirect, canonical_slug, [best_product]
    
    async def resolve_category_slug(
        self, 
        identifier: str
    ) -> Tuple[Optional[Dict], bool, Optional[str]]:
        """
        Resolve category slug with token matching.
        """
        if not identifier:
            return None, False, None
        
        decoded = identifier.strip()
        
        # Exact match
        exact = await self.db.categories.find_one(
            {"slug": decoded},
            {"_id": 1, "name": 1, "slug": 1}
        )
        if exact:
            return exact, False, exact.get("slug")
        
        # ObjectId match
        if len(decoded) == 24:
            try:
                oid = ObjectId(decoded)
                oid_match = await self.db.categories.find_one(
                    {"_id": oid},
                    {"_id": 1, "name": 1, "slug": 1}
                )
                if oid_match:
                    return oid_match, True, oid_match.get("slug")
            except Exception:
                pass
        
        # Token-based matching for categories
        search_tokens = self.tokenize_slug(decoded)
        
        if not search_tokens:
            return None, False, None
        
        # Match any token
        regex_conditions = []
        for token in search_tokens:
            pattern = f"(^|[-\\s]){re.escape(token)}"
            regex_conditions.append({
                "$or": [
                    {"slug": {"$regex": pattern, "$options": "i"}},
                    {"name": {"$regex": pattern, "$options": "i"}}
                ]
            })
        
        query = {"$or": regex_conditions} if regex_conditions else {}
        
        cursor = self.db.categories.find(
            query,
            {"_id": 1, "name": 1, "slug": 1}
        ).limit(10)
        
        candidates = await cursor.to_list(10)
        
        if not candidates:
            return None, False, None
        
        # Simple scoring - first match is usually best for categories
        best = candidates[0]
        return best, True, best.get("slug")


# Factory function
def create_slug_resolver(db):
    """Create slug resolver instance."""
    return SlugResolverService(db)
