"""
SEARCH ANALYTICS SERVICE
=========================
Enterprise search tracking and analytics.

Features:
- Track all search keywords
- Normalize keywords for deduplication
- Track matched products
- City-based search insights
- Admin analytics dashboard data

This enables:
1. Understanding user search intent
2. Creating city pages when demand exists
3. SEO content optimization based on real searches
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

logger = logging.getLogger("search_analytics")


class SearchAnalyticsService:
    """
    Search keyword tracking and analytics service.
    
    Tracks:
    - Raw search terms
    - Normalized keywords (for deduplication)
    - Search counts
    - Matched products
    - City filters used
    """
    
    def __init__(self, db):
        self.db = db
    
    @staticmethod
    def normalize_keyword(keyword: str) -> str:
        """
        Normalize keyword for deduplication.
        
        Rules:
        - Lowercase
        - Remove extra whitespace
        - Remove special characters
        - Trim
        """
        if not keyword:
            return ""
        
        # Lowercase and trim
        normalized = keyword.lower().strip()
        
        # Remove special characters except spaces and hyphens
        normalized = re.sub(r'[^a-z0-9\s\-]', '', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    async def track_search(
        self,
        keyword: str,
        city: str = None,
        product_matched: ObjectId = None,
        results_count: int = 0,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Track a search event.
        
        Args:
            keyword: Raw search term from user
            city: City filter if used
            product_matched: First matched product ID
            results_count: Number of results returned
            user_id: Optional user ID for personalization
        
        Returns:
            Updated search analytics document
        """
        if not keyword or len(keyword.strip()) < 2:
            return None
        
        raw_keyword = keyword.strip()
        normalized = self.normalize_keyword(keyword)
        
        if not normalized or len(normalized) < 2:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Upsert search analytics
        update_doc = {
            "$inc": {"count": 1},
            "$set": {
                "lastSearchedAt": now,
                "updatedAt": now
            },
            "$setOnInsert": {
                "normalizedKeyword": normalized,
                "keyword": raw_keyword,  # Store original for display
                "createdAt": now
            }
        }
        
        # Add city to cities array if provided
        if city:
            update_doc["$addToSet"] = {"cities": city.lower()}
        
        # Update product matched if found
        if product_matched:
            update_doc["$set"]["lastProductMatched"] = product_matched
            update_doc["$inc"]["matchedCount"] = 1
        else:
            update_doc["$inc"]["noMatchCount"] = 1
        
        result = await self.db.searchAnalytics.find_one_and_update(
            {"normalizedKeyword": normalized},
            update_doc,
            upsert=True,
            return_document=True
        )
        
        # Convert ObjectId for response
        if result and "_id" in result:
            result["_id"] = str(result["_id"])
        if result and "lastProductMatched" in result:
            result["lastProductMatched"] = str(result["lastProductMatched"])
        
        return result
    
    async def get_top_searches(
        self,
        limit: int = 50,
        days: int = 30,
        city: str = None,
        has_match: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Get top searched keywords.
        
        Args:
            limit: Max results
            days: Look back period
            city: Filter by city
            has_match: Filter by whether product was matched
        
        Returns:
            List of top keywords with counts
        """
        from datetime import timedelta
        
        query = {}
        
        # Date filter
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query["lastSearchedAt"] = {"$gte": cutoff}
        
        # City filter
        if city:
            query["cities"] = city.lower()
        
        # Match filter
        if has_match is True:
            query["lastProductMatched"] = {"$exists": True}
        elif has_match is False:
            query["lastProductMatched"] = {"$exists": False}
        
        cursor = self.db.searchAnalytics.find(
            query,
            {
                "_id": 1,
                "keyword": 1,
                "normalizedKeyword": 1,
                "count": 1,
                "matchedCount": 1,
                "noMatchCount": 1,
                "lastSearchedAt": 1,
                "cities": 1,
                "lastProductMatched": 1
            }
        ).sort("count", -1).limit(limit)
        
        results = await cursor.to_list(limit)
        
        # Convert ObjectIds
        for r in results:
            r["_id"] = str(r["_id"])
            if "lastProductMatched" in r and r["lastProductMatched"]:
                r["lastProductMatched"] = str(r["lastProductMatched"])
        
        return results
    
    async def get_unmatched_searches(
        self,
        limit: int = 50,
        min_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get keywords that don't match any products.
        
        These represent:
        - Content gaps
        - New product opportunities
        - SEO content needs
        """
        cursor = self.db.searchAnalytics.find(
            {
                "lastProductMatched": {"$exists": False},
                "count": {"$gte": min_count}
            },
            {
                "_id": 1,
                "keyword": 1,
                "count": 1,
                "cities": 1,
                "lastSearchedAt": 1
            }
        ).sort("count", -1).limit(limit)
        
        results = await cursor.to_list(limit)
        
        for r in results:
            r["_id"] = str(r["_id"])
        
        return results
    
    async def get_city_search_demand(
        self,
        product_id: ObjectId = None,
        min_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get cities with high search demand.
        
        Used to determine when to create city-specific SEO pages.
        Only create city page if:
        1. Search demand exists (count >= min_count)
        2. Sellers exist in that city
        """
        pipeline = [
            {"$unwind": "$cities"},
            {"$group": {
                "_id": "$cities",
                "totalSearches": {"$sum": "$count"},
                "uniqueKeywords": {"$sum": 1},
                "keywords": {"$push": "$keyword"}
            }},
            {"$match": {"totalSearches": {"$gte": min_count}}},
            {"$sort": {"totalSearches": -1}},
            {"$limit": 20}
        ]
        
        results = await self.db.searchAnalytics.aggregate(pipeline).to_list(20)
        
        # Check seller availability per city
        for city_data in results:
            city = city_data["_id"]
            
            # Count sellers in this city
            seller_count = await self.db.sellerListings.count_documents({
                "city": {"$regex": f"^{city}$", "$options": "i"},
                "status": "active"
            })
            
            city_data["sellerCount"] = seller_count
            city_data["canCreateCityPage"] = seller_count > 0
        
        return results
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """Get overall search analytics statistics."""
        pipeline = [
            {"$group": {
                "_id": None,
                "totalSearches": {"$sum": "$count"},
                "uniqueKeywords": {"$sum": 1},
                "avgSearchesPerKeyword": {"$avg": "$count"},
                "keywordsWithMatch": {
                    "$sum": {"$cond": [{"$ifNull": ["$lastProductMatched", False]}, 1, 0]}
                }
            }}
        ]
        
        results = await self.db.searchAnalytics.aggregate(pipeline).to_list(1)
        
        if results:
            stats = results[0]
            del stats["_id"]
            stats["matchRate"] = (
                stats["keywordsWithMatch"] / stats["uniqueKeywords"] * 100
                if stats["uniqueKeywords"] > 0 else 0
            )
            return stats
        
        return {
            "totalSearches": 0,
            "uniqueKeywords": 0,
            "avgSearchesPerKeyword": 0,
            "keywordsWithMatch": 0,
            "matchRate": 0
        }


async def setup_search_analytics_indexes(db):
    """Create indexes for searchAnalytics collection."""
    indexes = [
        {
            "keys": [("normalizedKeyword", 1)],
            "options": {"unique": True, "name": "idx_search_normalized_unique"}
        },
        {
            "keys": [("count", -1)],
            "options": {"name": "idx_search_count"}
        },
        {
            "keys": [("lastSearchedAt", -1)],
            "options": {"name": "idx_search_date"}
        },
        {
            "keys": [("cities", 1)],
            "options": {"name": "idx_search_cities"}
        },
        {
            "keys": [("lastProductMatched", 1)],
            "options": {"sparse": True, "name": "idx_search_product_matched"}
        }
    ]
    
    created = []
    for idx in indexes:
        try:
            await db.searchAnalytics.create_index(idx["keys"], **idx["options"])
            created.append(idx["options"]["name"])
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.error(f"Failed to create index {idx['options']['name']}: {e}")
    
    return created


# Factory function
def create_search_analytics_service(db):
    """Create search analytics service instance."""
    return SearchAnalyticsService(db)
