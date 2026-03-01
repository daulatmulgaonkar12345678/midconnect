"""
SMART SEARCH SERVICE
=====================

Implements intelligent search features for MongoDB Atlas M0:
- Typo tolerance (moter → motor)
- Phonetic matching (motar → motor)
- "Did you mean?" suggestions
- Smart autocomplete ranking
- Product name caching for performance

Optimized for free tier:
- Fuzzy logic runs only when results are empty
- Product names are cached in memory
- Limited suggestions for fast response
"""

import logging
import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple
from fuzzywuzzy import fuzz, process
from metaphone import doublemetaphone
import re

logger = logging.getLogger("smart_search")


class SmartSearchService:
    """
    Smart search service with typo tolerance and phonetic matching.
    
    Features:
    1. Fuzzy matching for typos (Levenshtein distance)
    2. Phonetic matching (Double Metaphone algorithm)
    3. "Did you mean?" suggestions
    4. Cached product names for performance
    """
    
    # Cache settings
    CACHE_REFRESH_INTERVAL = 300  # 5 minutes
    
    # Fuzzy matching thresholds
    FUZZY_THRESHOLD = 65  # Minimum similarity score (0-100)
    PHONETIC_THRESHOLD = 0.7  # Minimum phonetic match ratio
    
    # Common typo patterns for Indian English
    TYPO_PATTERNS = {
        'motor': ['moter', 'motar', 'motr', 'mottor', 'motter', 'mutor'],
        'cable': ['cabel', 'cabal', 'kable', 'cabl'],
        'switch': ['swich', 'swithc', 'swicth', 'swtich'],
        'transformer': ['transfarmer', 'transfomer', 'transformar', 'transormer'],
        'pump': ['pum', 'pummp', 'pupm'],
        'compressor': ['compresser', 'compressar', 'compresor'],
        'electric': ['electic', 'electrc', 'electrik', 'elecrtic'],
        'copper': ['coper', 'coppr', 'cupper', 'kopper'],
        'aluminum': ['aluminium', 'alumnum', 'aluminam'],
        'voltage': ['voltge', 'voltaj', 'volatge'],
        'ampere': ['amper', 'ampear', 'amphere', 'ampre'],
        'watt': ['wat', 'waat', 'vatt'],
        'industrial': ['industral', 'industreal', 'industriel'],
        'generator': ['generater', 'genrator', 'genertor'],
        'inverter': ['inveter', 'invertar', 'invrter'],
        'battery': ['batry', 'battry', 'batery'],
        'contactor': ['contacter', 'contactar', 'contctor'],
        'breaker': ['braker', 'breakar', 'breker'],
        'gloves': ['glows', 'glovs', 'glove', 'gluves', 'gluvs'],
        'bearing': ['bering', 'bearng', 'baering', 'berring'],
        'valve': ['valv', 'valev', 'vlave'],
        'wheel': ['weel', 'whel', 'wheeel'],
        'cutting': ['cuting', 'cutng', 'cuttin'],
        'safety': ['safty', 'saftey', 'safetty'],
    }
    
    # Build reverse lookup for common typos
    KNOWN_CORRECTIONS = {}
    for correct, typos in TYPO_PATTERNS.items():
        for typo in typos:
            KNOWN_CORRECTIONS[typo.lower()] = correct
    
    def __init__(self, db):
        self.db = db
        self._product_names_cache: List[str] = []
        self._category_names_cache: List[str] = []
        self._last_cache_refresh: float = 0
        self._phonetic_cache: Dict[str, Tuple[str, str]] = {}
        self._cache_initialized: bool = False
        self._cache_loading: bool = False
    
    async def _refresh_cache_if_needed(self):
        """Refresh product names cache if stale."""
        current_time = time.time()
        
        # Skip if already loading to prevent concurrent loads
        if self._cache_loading:
            return
        
        # Check if cache needs refresh (first load or expired)
        needs_refresh = (
            not self._cache_initialized or 
            (current_time - self._last_cache_refresh > self.CACHE_REFRESH_INTERVAL)
        )
        
        if needs_refresh:
            await self._load_names_cache()
            self._last_cache_refresh = current_time
    
    async def _load_names_cache(self):
        """Load product and category names into memory cache."""
        # Prevent concurrent cache loads
        if self._cache_loading:
            return
        
        self._cache_loading = True
        try:
            # Get distinct product names
            self._product_names_cache = await self.db.products.distinct("name")
            
            # Get distinct category names
            self._category_names_cache = await self.db.categories.distinct("name")
            
            # Build phonetic cache
            self._build_phonetic_cache()
            
            # Mark cache as initialized (only log on first load)
            if not self._cache_initialized:
                logger.info(f"SmartSearch cache initialized: {len(self._product_names_cache)} products, {len(self._category_names_cache)} categories")
                self._cache_initialized = True
            
        except Exception as e:
            logger.error(f"Error loading names cache: {e}")
        finally:
            self._cache_loading = False
    
    def _build_phonetic_cache(self):
        """Build phonetic representations of all product names."""
        self._phonetic_cache = {}
        all_names = self._product_names_cache + self._category_names_cache
        
        for name in all_names:
            for word in name.lower().split():
                if len(word) >= 3 and word not in self._phonetic_cache:
                    primary, secondary = doublemetaphone(word)
                    self._phonetic_cache[word] = (primary, secondary)
    
    def _get_phonetic_code(self, word: str) -> Tuple[str, str]:
        """Get phonetic code for a word."""
        word = word.lower().strip()
        if word in self._phonetic_cache:
            return self._phonetic_cache[word]
        return doublemetaphone(word)
    
    def correct_typo_from_known(self, word: str) -> Optional[str]:
        """Check if word is a known typo and return correction."""
        return self.KNOWN_CORRECTIONS.get(word.lower())
    
    def find_fuzzy_match(self, query: str, candidates: List[str], threshold: int = None) -> Optional[Tuple[str, int]]:
        """
        Find best fuzzy match for query in candidates.
        
        Returns:
            Tuple of (best_match, score) or None
        """
        if not candidates:
            return None
        
        threshold = threshold or self.FUZZY_THRESHOLD
        
        try:
            result = process.extractOne(
                query,
                candidates,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold
            )
            
            if result:
                # Handle both 2-tuple and 3-tuple formats from different fuzzywuzzy versions
                # Some versions return (match, score), others return (match, score, index)
                match = result[0]
                score = result[1]
                return (match, score)
                
        except Exception as e:
            logger.error(f"Fuzzy match error: {str(e)}")
        
        return None
    
    def find_phonetic_match(self, query_word: str, candidates: List[str]) -> Optional[str]:
        """
        Find phonetic match for a word.
        
        Uses Double Metaphone algorithm optimized for various accents.
        """
        query_phonetic = self._get_phonetic_code(query_word)
        
        for candidate in candidates:
            for word in candidate.lower().split():
                candidate_phonetic = self._get_phonetic_code(word)
                
                # Match if primary codes match
                if query_phonetic[0] and candidate_phonetic[0]:
                    if query_phonetic[0] == candidate_phonetic[0]:
                        return candidate
                
                # Match if secondary codes match
                if query_phonetic[1] and candidate_phonetic[1]:
                    if query_phonetic[1] == candidate_phonetic[1]:
                        return candidate
        
        return None
    
    async def get_spelling_suggestion(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get spelling suggestion for a query.
        
        Returns:
            {
                "original": "moter",
                "suggested": "motor",
                "type": "typo" | "phonetic" | "fuzzy",
                "confidence": 0.0-1.0
            }
        """
        await self._refresh_cache_if_needed()
        
        words = query.lower().split()
        corrections = []
        
        for word in words:
            if len(word) < 3:
                continue
            
            # 1. Check known typos first (fastest)
            known_correction = self.correct_typo_from_known(word)
            if known_correction and known_correction != word:
                corrections.append({
                    "original": word,
                    "suggested": known_correction,
                    "type": "typo",
                    "confidence": 0.95
                })
                continue
            
            # 2. Check phonetic match (India-friendly)
            all_names = self._product_names_cache + self._category_names_cache
            all_words = list(set(w.lower() for name in all_names for w in name.split() if len(w) >= 3))
            
            phonetic_match = self.find_phonetic_match(word, all_words)
            if phonetic_match and phonetic_match.lower() != word:
                corrections.append({
                    "original": word,
                    "suggested": phonetic_match,
                    "type": "phonetic",
                    "confidence": 0.80
                })
                continue
            
            # 3. Check fuzzy match (slower, but catches more)
            fuzzy_result = self.find_fuzzy_match(word, all_words, threshold=70)
            if fuzzy_result:
                match, score = fuzzy_result
                if match.lower() != word:
                    corrections.append({
                        "original": word,
                        "suggested": match,
                        "type": "fuzzy",
                        "confidence": score / 100
                    })
        
        if corrections:
            # Return the highest confidence correction
            best = max(corrections, key=lambda x: x["confidence"])
            
            # Build corrected query
            corrected_words = words.copy()
            for corr in corrections:
                for i, w in enumerate(corrected_words):
                    if w == corr["original"]:
                        corrected_words[i] = corr["suggested"]
            
            corrected_query = " ".join(corrected_words)
            
            return {
                "original": query,
                "corrected": corrected_query,
                "corrections": corrections,
                "type": best["type"],
                "confidence": best["confidence"]
            }
        
        return None
    
    async def get_smart_autocomplete(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get smart autocomplete suggestions with fuzzy matching.
        
        Returns suggestions even for misspelled queries.
        """
        await self._refresh_cache_if_needed()
        
        suggestions = []
        corrected_query = None
        
        # 1. Check for spelling corrections
        spelling = await self.get_spelling_suggestion(query)
        if spelling:
            corrected_query = spelling["corrected"]
        
        search_query = corrected_query or query
        
        # 2. Direct matches
        for name in self._product_names_cache:
            if search_query.lower() in name.lower():
                suggestions.append({
                    "type": "product",
                    "text": name,
                    "matchType": "direct"
                })
                if len(suggestions) >= limit:
                    break
        
        # 3. Fuzzy matches if not enough direct matches
        if len(suggestions) < limit:
            fuzzy_matches = process.extract(
                search_query,
                self._product_names_cache,
                scorer=fuzz.token_sort_ratio,
                limit=limit - len(suggestions)
            )
            
            for match_result in fuzzy_matches:
                # Handle both 2-tuple and 3-tuple formats from different fuzzywuzzy versions
                if len(match_result) >= 2:
                    match = match_result[0]
                    score = match_result[1]
                    if score >= self.FUZZY_THRESHOLD and match not in [s["text"] for s in suggestions]:
                        suggestions.append({
                            "type": "product",
                            "text": match,
                            "matchType": "fuzzy",
                            "score": score
                        })
        
        return {
            "query": query,
            "correctedQuery": corrected_query,
            "didYouMean": corrected_query if corrected_query and corrected_query != query else None,
            "suggestions": suggestions[:limit]
        }
    
    async def search_with_typo_tolerance(
        self,
        query: str,
        base_filter: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Search with typo tolerance and suggestions.
        
        If no direct results, automatically:
        1. Suggest spelling corrections
        2. Try fuzzy search
        3. Try phonetic search
        """
        await self._refresh_cache_if_needed()
        
        base_filter = base_filter or {"isActive": True, "status": "active"}
        
        # 1. Try direct search first
        search_pattern = "|".join(re.escape(t) for t in query.split())
        
        direct_results = await self.db.sellerListings.find({
            **base_filter,
            "$or": [
                {"searchableText": {"$regex": search_pattern, "$options": "i"}},
                {"normalizedSearchTokens": {"$in": [t.lower() for t in query.split()]}},
            ]
        }).limit(20).to_list(20)
        
        # 2. If results found, return them
        if direct_results:
            return {
                "results": direct_results,
                "query": query,
                "correctedQuery": None,
                "didYouMean": None,
                "searchType": "direct"
            }
        
        # 3. No results - try spelling correction
        spelling = await self.get_spelling_suggestion(query)
        
        if spelling:
            corrected = spelling["corrected"]
            corrected_pattern = "|".join(re.escape(t) for t in corrected.split())
            
            corrected_results = await self.db.sellerListings.find({
                **base_filter,
                "$or": [
                    {"searchableText": {"$regex": corrected_pattern, "$options": "i"}},
                    {"normalizedSearchTokens": {"$in": [t.lower() for t in corrected.split()]}},
                ]
            }).limit(20).to_list(20)
            
            if corrected_results:
                return {
                    "results": corrected_results,
                    "query": query,
                    "correctedQuery": corrected,
                    "didYouMean": corrected,
                    "searchType": "corrected",
                    "corrections": spelling["corrections"]
                }
        
        # 4. Still no results - return empty with suggestion
        return {
            "results": [],
            "query": query,
            "correctedQuery": spelling["corrected"] if spelling else None,
            "didYouMean": spelling["corrected"] if spelling else None,
            "searchType": "no_results",
            "suggestion": f"No results for '{query}'. Try a different search term."
        }
    
    def rank_results(
        self,
        results: List[Dict],
        query: str,
        user_location: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Rank search results intelligently.
        
        Ranking priority:
        1. Exact match (query in name)
        2. Similarity score
        3. Popularity (view count, inquiry count)
        4. Location relevance (if user location provided)
        5. Recency
        """
        def calculate_score(item: Dict) -> float:
            score = 0.0
            name = item.get("productName", "") or item.get("name", "")
            
            # 1. Exact match bonus (+50)
            if query.lower() in name.lower():
                score += 50
            
            # 2. Similarity score (+0-30)
            similarity = fuzz.token_sort_ratio(query.lower(), name.lower())
            score += similarity * 0.3
            
            # 3. Popularity bonus (+0-10)
            views = item.get("viewCount", 0)
            inquiries = item.get("inquiryCount", 0)
            score += min(views / 100, 5) + min(inquiries * 2, 5)
            
            # 4. Location bonus (+0-15)
            if user_location:
                if item.get("city") == user_location.get("city"):
                    score += 15
                elif item.get("state") == user_location.get("state"):
                    score += 10
            
            # 5. Recency bonus (+0-5)
            # Recent items get slight boost
            score += item.get("rankScore", 0) * 0.5
            
            # 6. Premium seller bonus (+5)
            if item.get("isPremiumSeller"):
                score += 5
            
            # 7. In stock bonus (+3)
            if item.get("inStock"):
                score += 3
            
            return score
        
        # Sort by calculated score
        return sorted(results, key=calculate_score, reverse=True)


# Singleton instance storage
_smart_search_instance: Optional[SmartSearchService] = None

# Factory function with singleton pattern
def create_smart_search_service(db):
    """
    Create and return a SmartSearchService instance (singleton).
    This ensures the cache is shared across all requests and only loaded once.
    """
    global _smart_search_instance
    
    if _smart_search_instance is None:
        _smart_search_instance = SmartSearchService(db)
        logger.info("SmartSearchService singleton created")
    
    return _smart_search_instance


async def initialize_smart_search_cache(db):
    """
    Initialize the smart search cache at startup.
    Call this from the server startup event to pre-warm the cache.
    """
    service = create_smart_search_service(db)
    await service._load_names_cache()
    logger.info("SmartSearch cache pre-warmed at startup")
