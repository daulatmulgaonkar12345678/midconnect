"""
DETERMINISTIC SLUG RESOLVER SERVICE
===================================
Resolves a URL identifier to a product using explicit mappings only
(Batch 5, 2026-11-19 — SEO integrity fix).

Resolution order (each step is a deterministic mapping; no similarity or
keyword matching anywhere):
1. Exact slug match — no redirect needed
2. Case-normalized slug match (slugs are stored lowercase) — redirect to canonical
3. ObjectId match (24-hex legacy /product/{id} URLs) — redirect to canonical
4. Explicit legacy mappings: legacySlugs / legacyIds fields — redirect to canonical

Anything else is NOT a product address and resolves to None, so callers
return HTTP 404. The previous token-based fuzzy matching (partial slugs,
word-order tolerance, ANY-token fallback) was removed: it let invalid URLs
resolve to unrelated products (e.g. a random slug surfacing "Notebooks"
via a single shared token), which is an SEO integrity defect. City, state,
stop-word tolerance and prefix matching are gone with it; legitimate
legacy addresses are covered by the explicit legacySlugs/legacyIds
mappings and ObjectId redirects instead.

Note: resolve_category_slug below retains its own legacy token matching;
it serves only the enterprise category resolver endpoint and is intentionally
untouched by the Batch 5 product-slug fix.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId

logger = logging.getLogger("slug_resolver_service")


class SlugResolverService:
    """
    Deterministic product slug resolver (exact, case-normalized, ObjectId,
    or explicit legacy mapping — never fuzzy).

    - Invalid or unrelated slugs resolve to None (callers return HTTP 404)
    - Legacy ObjectId URLs and legacySlugs/legacyIds redirect to canonical
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
    

    async def resolve_slug(
        self, 
        identifier: str,
        return_all_matches: bool = False
    ) -> Tuple[Optional[Dict], bool, Optional[str], List[Dict]]:
        """
        Resolve a URL identifier to a product using deterministic matching only.
        
        Args:
            identifier: The URL slug (e.g., "abc-power-tools-hand-tools")
            return_all_matches: If True, return all matching products
        
        Returns:
            (best_match, needs_redirect, canonical_slug, all_matches)
            
        Matching Priority:
        1. Exact slug match (no redirect needed)
        2. ObjectId match (redirect to canonical)
        3. Explicit legacy mapping (legacySlugs / legacyIds) - redirect to canonical
        4. Case-normalized slug match (redirect to canonical)

        No token, prefix, or ANY-token fallback matching exists; identifiers
        that map to no product return None so callers raise HTTP 404.
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

        # === Priority 1b: Case-normalized exact match ===
        # Slugs are stored lowercase; accept e.g. "MOTOR-SUPPLIER-INDIA" and
        # point it at the canonical slug (deterministic: slugs are unique).
        if decoded != decoded.lower():
            normalized_match = await self.db.products.find_one(
                {"slug": {"$regex": "^" + re.escape(decoded) + "$", "$options": "i"}},
                {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}
            )
            if normalized_match:
                canonical = normalized_match.get("slug")
                return normalized_match, True, canonical, [normalized_match]
        
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
        
        # === Batch 5 (2026-11-19): no fallback matching ===
        # Token/prefix/ANY-token fuzzy matching was removed: it let invalid
        # URLs resolve to unrelated products via a single shared token or a
        # prefix hit. A valid product address is exactly one of: canonical
        # slug (case-insensitive), ObjectId, or an explicit legacySlugs /
        # legacyIds mapping. Everything else is not a product address.
        return None, False, None, []
    
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
