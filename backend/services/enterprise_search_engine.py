"""
ENTERPRISE SEARCH ENGINE v2.0
==============================
Self-learning, token-based, weighted search system.

Features:
1. Token-based search (order independent)
2. Weighted ranking (name > aliases > category > attributes > content)
3. Self-learning keyword promotion
4. Spam filtering
5. searchAliases auto-population

This is enterprise-grade search that improves daily.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

logger = logging.getLogger("enterprise_search")


class EnterpriseSearchEngine:
    """
    Token-based search engine with weighted ranking.
    
    Search works in ANY word order:
    - "power tools abc" matches "abc power tools"
    - "abc tools" matches "abc power tools hand tools"
    
    Weights:
    - Exact name match: 5
    - searchAliases: 4
    - Category match: 3
    - Attributes match: 2
    - SEO content: 1
    """
    
    # Ranking weights
    WEIGHT_NAME_EXACT = 10
    WEIGHT_NAME_PARTIAL = 5
    WEIGHT_ALIASES = 4
    WEIGHT_CATEGORY = 3
    WEIGHT_ATTRIBUTES = 2
    WEIGHT_CONTENT = 1
    
    # Spam words to filter
    SPAM_WORDS = {
        "free", "job", "pdf", "download", "sex", "xxx", "porn",
        "casino", "betting", "loan", "credit", "forex", "crypto",
        "bitcoin", "earn", "money", "rich", "quick", "fast",
        "hack", "crack", "keygen", "serial", "torrent"
    }
    
    # Minimum keyword requirements
    MIN_KEYWORD_LENGTH = 3
    MAX_KEYWORD_LENGTH = 60
    MIN_SEARCH_COUNT_FOR_PROMOTION = 10
    MIN_QUALITY_SCORE_FOR_PROMOTION = 0.6
    
    def __init__(self, db):
        self.db = db
    
    # ==================== TOKENIZATION ====================
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize search query."""
        if not query:
            return ""
        
        # Lowercase and strip
        normalized = query.lower().strip()
        
        # Remove special characters except spaces and hyphens
        normalized = re.sub(r'[^a-z0-9\s\-]', '', normalized)
        
        # Replace multiple spaces/hyphens with single space
        normalized = re.sub(r'[\s\-]+', ' ', normalized)
        
        return normalized.strip()
    
    @staticmethod
    def tokenize(query: str) -> List[str]:
        """
        Split query into tokens.
        
        "power tools abc" -> ["power", "tools", "abc"]
        """
        normalized = EnterpriseSearchEngine.normalize_query(query)
        if not normalized:
            return []
        
        tokens = normalized.split()
        
        # Filter out very short tokens (1-2 chars)
        tokens = [t for t in tokens if len(t) >= 2]
        
        return tokens
    
    # ==================== SPAM DETECTION ====================
    
    @classmethod
    def is_spam_keyword(cls, keyword: str) -> bool:
        """Check if keyword is spam."""
        normalized = cls.normalize_query(keyword)
        
        # Too short or too long
        if len(normalized) < cls.MIN_KEYWORD_LENGTH:
            return True
        if len(normalized) > cls.MAX_KEYWORD_LENGTH:
            return True
        
        # Contains spam words
        tokens = normalized.split()
        for token in tokens:
            if token in cls.SPAM_WORDS:
                return True
        
        # All numbers
        if normalized.replace(' ', '').isdigit():
            return True
        
        return False
    
    # ==================== TOKEN-BASED SEARCH ====================
    
    async def search_products(
        self,
        query: str,
        category_id: str = None,
        city: str = None,
        limit: int = 50,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Token-based search with weighted ranking.
        
        Works in ANY word order:
        - "power tools abc" matches "abc power tools"
        - Each token must match at least one field
        
        Returns products sorted by relevance score.
        """
        tokens = self.tokenize(query)
        
        if not tokens:
            # No valid tokens - return all active products
            return await self._get_all_products(category_id, city, limit, page)
        
        # Build AND-based token query
        # Each token must match at least one searchable field
        token_conditions = []
        
        for token in tokens:
            token_regex = {"$regex": token, "$options": "i"}
            token_conditions.append({
                "$or": [
                    {"name": token_regex},
                    {"searchAliases": token_regex},
                    {"categoryName": token_regex},
                    {"description": token_regex},
                    {"seoContent": token_regex}
                ]
            })
        
        # All tokens must match
        base_query = {
            "$and": token_conditions,
            "isActive": {"$ne": False}
        }
        
        if category_id:
            try:
                base_query["categoryId"] = ObjectId(category_id)
            except:
                base_query["categoryId"] = category_id
        
        # Get matching products
        skip = (page - 1) * limit
        
        products = await self.db.products.find(
            base_query,
            {
                "_id": 1,
                "name": 1,
                "slug": 1,
                "categoryId": 1,
                "categoryName": 1,
                "description": 1,
                "searchAliases": 1,
                "seoTitle": 1,
                "seoDescription": 1,
                "coverImageUrl": 1,
                "images": 1
            }
        ).to_list(500)  # Get more for ranking
        
        # Calculate relevance scores
        scored_products = []
        for product in products:
            score = self._calculate_relevance_score(product, tokens)
            scored_products.append({
                **product,
                "_relevanceScore": score
            })
        
        # Sort by relevance score (descending)
        scored_products.sort(key=lambda x: x["_relevanceScore"], reverse=True)
        
        # Paginate
        paginated = scored_products[skip:skip + limit]
        
        # Get seller counts for top results
        results = []
        for product in paginated:
            seller_count = await self.db.sellerListings.count_documents({
                "productId": product["_id"],
                "status": "active"
            })
            
            # Get min price
            min_price = None
            listing = await self.db.sellerListings.find_one(
                {"productId": product["_id"], "status": "active"},
                {"pricingTiers": 1}
            )
            if listing and listing.get("pricingTiers"):
                prices = [t.get("pricePerUnit") or t.get("price") for t in listing["pricingTiers"]]
                prices = [p for p in prices if p]
                if prices:
                    min_price = min(prices)
            
            results.append({
                "_id": str(product["_id"]),
                "name": product.get("name"),
                "slug": product.get("slug"),
                "categoryName": product.get("categoryName"),
                "description": product.get("description", "")[:200],
                "seoTitle": product.get("seoTitle"),
                "coverImageUrl": product.get("coverImageUrl"),
                "images": product.get("images", [])[:2],
                "sellerCount": seller_count,
                "minPrice": min_price,
                "relevanceScore": product["_relevanceScore"]
            })
        
        return {
            "products": results,
            "total": len(scored_products),
            "page": page,
            "limit": limit,
            "query": query,
            "tokens": tokens
        }
    
    def _calculate_relevance_score(
        self, 
        product: Dict, 
        tokens: List[str]
    ) -> float:
        """
        Calculate weighted relevance score.
        
        Weights:
        - Exact name match: 10
        - Name partial: 5
        - searchAliases: 4
        - Category: 3
        - Attributes: 2
        - Content: 1
        """
        score = 0.0
        name = (product.get("name") or "").lower()
        aliases = product.get("searchAliases") or []
        category = (product.get("categoryName") or "").lower()
        description = (product.get("description") or "").lower()
        content = (product.get("seoContent") or "").lower()
        
        for token in tokens:
            token_lower = token.lower()
            
            # Exact name match (highest)
            if token_lower == name or name.startswith(token_lower):
                score += self.WEIGHT_NAME_EXACT
            elif token_lower in name:
                score += self.WEIGHT_NAME_PARTIAL
            
            # Alias match
            for alias in aliases:
                if token_lower in alias.lower():
                    score += self.WEIGHT_ALIASES
                    break
            
            # Category match
            if token_lower in category:
                score += self.WEIGHT_CATEGORY
            
            # Description/content match
            if token_lower in description:
                score += self.WEIGHT_ATTRIBUTES
            
            if token_lower in content:
                score += self.WEIGHT_CONTENT
        
        return score
    
    async def _get_all_products(
        self,
        category_id: str,
        city: str,
        limit: int,
        page: int
    ) -> Dict[str, Any]:
        """Get all products when no search query."""
        query = {"isActive": {"$ne": False}}
        
        if category_id:
            try:
                query["categoryId"] = ObjectId(category_id)
            except:
                pass
        
        skip = (page - 1) * limit
        
        products = await self.db.products.find(
            query,
            {"_id": 1, "name": 1, "slug": 1, "categoryName": 1, "coverImageUrl": 1}
        ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        total = await self.db.products.count_documents(query)
        
        results = []
        for p in products:
            seller_count = await self.db.sellerListings.count_documents({
                "productId": p["_id"],
                "status": "active"
            })
            results.append({
                "_id": str(p["_id"]),
                "name": p.get("name"),
                "slug": p.get("slug"),
                "categoryName": p.get("categoryName"),
                "coverImageUrl": p.get("coverImageUrl"),
                "sellerCount": seller_count
            })
        
        return {
            "products": results,
            "total": total,
            "page": page,
            "limit": limit,
            "query": "",
            "tokens": []
        }
    
    # ==================== SELF-LEARNING SYSTEM ====================
    
    async def track_and_learn(
        self,
        keyword: str,
        matched_product_id: ObjectId = None,
        results_count: int = 0
    ) -> Dict[str, Any]:
        """
        Track search and learn from it.
        
        Steps:
        1. Validate keyword (not spam)
        2. Track in searchAnalytics
        3. Calculate quality score
        4. Auto-promote if high quality
        """
        normalized = self.normalize_query(keyword)
        
        if not normalized or self.is_spam_keyword(normalized):
            return {"tracked": False, "reason": "spam_or_invalid"}
        
        now = datetime.now(timezone.utc)
        
        # Calculate quality score
        quality_score = self._calculate_keyword_quality(
            normalized, matched_product_id, results_count
        )
        
        # Track in searchAnalytics
        update_doc = {
            "$inc": {"count": 1},
            "$set": {
                "lastSearchedAt": now,
                "updatedAt": now,
                "qualityScore": quality_score
            },
            "$setOnInsert": {
                "normalizedKeyword": normalized,
                "keyword": keyword.strip(),
                "createdAt": now,
                "promoted": False,
                "rejected": False
            }
        }
        
        if matched_product_id:
            update_doc["$set"]["lastProductMatched"] = matched_product_id
            update_doc["$inc"]["matchedCount"] = 1
        else:
            update_doc["$inc"]["noMatchCount"] = 1
        
        result = await self.db.searchAnalytics.find_one_and_update(
            {"normalizedKeyword": normalized},
            update_doc,
            upsert=True,
            return_document=True
        )
        
        # Check for auto-promotion
        promoted = False
        if result and not result.get("promoted") and not result.get("rejected"):
            count = result.get("count", 0)
            score = result.get("qualityScore", 0)
            product_id = result.get("lastProductMatched")
            
            if (count >= self.MIN_SEARCH_COUNT_FOR_PROMOTION and 
                score >= self.MIN_QUALITY_SCORE_FOR_PROMOTION and
                product_id):
                
                promoted = await self._auto_promote_keyword(normalized, product_id)
                
                if promoted:
                    await self.db.searchAnalytics.update_one(
                        {"normalizedKeyword": normalized},
                        {"$set": {"promoted": True, "promotedAt": now}}
                    )
        
        return {
            "tracked": True,
            "normalized": normalized,
            "count": result.get("count", 1) if result else 1,
            "qualityScore": quality_score,
            "promoted": promoted
        }
    
    def _calculate_keyword_quality(
        self,
        keyword: str,
        matched_product_id: ObjectId,
        results_count: int
    ) -> float:
        """
        Calculate quality score for a keyword.
        
        Factors:
        - Has matched product: +0.3
        - Results count > 0: +0.2
        - Keyword length reasonable: +0.2
        - Contains product-like words: +0.3
        """
        score = 0.0
        
        # Has match
        if matched_product_id:
            score += 0.3
        
        # Has results
        if results_count > 0:
            score += 0.2
        
        # Reasonable length (5-40 chars is ideal)
        keyword_len = len(keyword)
        if 5 <= keyword_len <= 40:
            score += 0.2
        elif 3 <= keyword_len < 5 or 40 < keyword_len <= 60:
            score += 0.1
        
        # Contains product-like words
        product_words = {
            "motor", "pump", "tool", "machine", "equipment", "industrial",
            "steel", "pipe", "valve", "bearing", "cable", "wire", "electric",
            "power", "gear", "belt", "chain", "fastener", "bolt", "screw"
        }
        tokens = keyword.lower().split()
        for token in tokens:
            if token in product_words:
                score += 0.1
                break
        
        # Contains location (good for local SEO)
        cities = {"mumbai", "delhi", "bangalore", "chennai", "pune", "hyderabad"}
        for token in tokens:
            if token in cities:
                score += 0.1
                break
        
        return min(score, 1.0)
    
    async def _auto_promote_keyword(
        self,
        keyword: str,
        product_id: ObjectId
    ) -> bool:
        """
        Auto-promote high quality keyword to product's searchAliases.
        
        Uses $addToSet to prevent duplicates.
        """
        try:
            result = await self.db.products.update_one(
                {"_id": product_id},
                {"$addToSet": {"searchAliases": keyword}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Auto-promote failed: {e}")
            return False
    
    # ==================== KEYWORD MANAGEMENT ====================
    
    async def get_pending_keywords(
        self,
        min_count: int = 5,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get keywords pending review (not promoted, not rejected).
        """
        cursor = self.db.searchAnalytics.find(
            {
                "promoted": {"$ne": True},
                "rejected": {"$ne": True},
                "count": {"$gte": min_count},
                "lastProductMatched": {"$exists": True}
            },
            {
                "_id": 1,
                "keyword": 1,
                "normalizedKeyword": 1,
                "count": 1,
                "qualityScore": 1,
                "lastProductMatched": 1,
                "lastSearchedAt": 1
            }
        ).sort("count", -1).limit(limit)
        
        results = await cursor.to_list(limit)
        
        # Enrich with product names
        for r in results:
            r["_id"] = str(r["_id"])
            if r.get("lastProductMatched"):
                product = await self.db.products.find_one(
                    {"_id": r["lastProductMatched"]},
                    {"name": 1, "slug": 1}
                )
                if product:
                    r["productName"] = product.get("name")
                    r["productSlug"] = product.get("slug")
                r["lastProductMatched"] = str(r["lastProductMatched"])
        
        return results
    
    async def approve_keyword(
        self,
        keyword_id: str,
        admin_id: str = None
    ) -> Dict:
        """Manually approve and promote a keyword."""
        try:
            keyword_oid = ObjectId(keyword_id)
        except:
            return {"success": False, "error": "Invalid keyword ID"}
        
        keyword_doc = await self.db.searchAnalytics.find_one({"_id": keyword_oid})
        
        if not keyword_doc:
            return {"success": False, "error": "Keyword not found"}
        
        if keyword_doc.get("promoted"):
            return {"success": False, "error": "Already promoted"}
        
        product_id = keyword_doc.get("lastProductMatched")
        normalized = keyword_doc.get("normalizedKeyword")
        
        if not product_id or not normalized:
            return {"success": False, "error": "No product match"}
        
        # Promote to searchAliases
        promoted = await self._auto_promote_keyword(normalized, product_id)
        
        if promoted:
            now = datetime.now(timezone.utc)
            await self.db.searchAnalytics.update_one(
                {"_id": keyword_oid},
                {"$set": {
                    "promoted": True,
                    "promotedAt": now,
                    "approvedBy": admin_id
                }}
            )
        
        return {"success": promoted, "keyword": normalized}
    
    async def reject_keyword(
        self,
        keyword_id: str,
        admin_id: str = None,
        reason: str = None
    ) -> Dict:
        """Reject a keyword (mark as spam/invalid)."""
        try:
            keyword_oid = ObjectId(keyword_id)
        except:
            return {"success": False, "error": "Invalid keyword ID"}
        
        now = datetime.now(timezone.utc)
        result = await self.db.searchAnalytics.update_one(
            {"_id": keyword_oid},
            {"$set": {
                "rejected": True,
                "rejectedAt": now,
                "rejectedBy": admin_id,
                "rejectionReason": reason
            }}
        )
        
        return {"success": result.modified_count > 0}
    
    # ==================== DAILY CRON JOB ====================
    
    async def run_daily_learning_job(self) -> Dict:
        """
        Daily cron job for self-learning system.
        
        Steps:
        1. Auto-promote high quality keywords
        2. Remove spam
        3. Update quality scores
        4. Clean old low-count keywords
        """
        stats = {
            "promoted": 0,
            "spam_removed": 0,
            "scores_updated": 0,
            "old_cleaned": 0
        }
        
        now = datetime.now(timezone.utc)
        
        # 1. Auto-promote high quality keywords
        pending = await self.db.searchAnalytics.find({
            "promoted": {"$ne": True},
            "rejected": {"$ne": True},
            "count": {"$gte": self.MIN_SEARCH_COUNT_FOR_PROMOTION},
            "qualityScore": {"$gte": self.MIN_QUALITY_SCORE_FOR_PROMOTION},
            "lastProductMatched": {"$exists": True}
        }).to_list(100)
        
        for kw in pending:
            promoted = await self._auto_promote_keyword(
                kw["normalizedKeyword"],
                kw["lastProductMatched"]
            )
            if promoted:
                await self.db.searchAnalytics.update_one(
                    {"_id": kw["_id"]},
                    {"$set": {"promoted": True, "promotedAt": now}}
                )
                stats["promoted"] += 1
        
        # 2. Mark spam keywords as rejected
        all_keywords = await self.db.searchAnalytics.find({
            "rejected": {"$ne": True}
        }).to_list(1000)
        
        for kw in all_keywords:
            if self.is_spam_keyword(kw.get("normalizedKeyword", "")):
                await self.db.searchAnalytics.update_one(
                    {"_id": kw["_id"]},
                    {"$set": {"rejected": True, "rejectionReason": "auto_spam"}}
                )
                stats["spam_removed"] += 1
        
        # 3. Clean old low-count keywords (older than 90 days, count < 3)
        cutoff = now - timedelta(days=90)
        result = await self.db.searchAnalytics.delete_many({
            "count": {"$lt": 3},
            "lastSearchedAt": {"$lt": cutoff},
            "promoted": {"$ne": True}
        })
        stats["old_cleaned"] = result.deleted_count
        
        return stats


# Factory function
def create_enterprise_search_engine(db):
    """Create enterprise search engine instance."""
    return EnterpriseSearchEngine(db)
