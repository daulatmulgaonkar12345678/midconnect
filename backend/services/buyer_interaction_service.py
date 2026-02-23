"""
BUYER INTERACTION TRACKING SERVICE
===================================

Tracks buyer interactions with sellers/products for behavior-based ranking boost.

Collection: buyerInteractions
Schema:
{
    "_id": ObjectId,
    "buyerId": ObjectId,
    "sellerId": ObjectId,
    "productId": ObjectId,
    "views": int,
    "inquiries": int,
    "orders": int,
    "lastInteractionAt": ISODate
}

Boost Logic (capped at 15 points):
- orders > 0: +15
- inquiries > 0: +10
- views > 2: +5
"""

from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Boost configuration (capped, deterministic)
BEHAVIOR_BOOST_CONFIG = {
    "has_orders": 15,
    "has_inquiries": 10,
    "has_views": 5,
    "max_boost": 15  # CAP
}


class BuyerInteractionService:
    """
    Service for tracking and calculating buyer interaction boosts.
    
    Usage:
        service = BuyerInteractionService(db)
        
        # Track interactions
        await service.track_view(buyer_id, seller_id, product_id)
        await service.track_inquiry(buyer_id, seller_id, product_id)
        await service.track_order(buyer_id, seller_id, product_id)
        
        # Get boost for ranking
        boost = await service.calculate_behavior_boost(buyer_id, seller_id, product_id)
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create required indexes."""
        # Compound unique index for buyer + seller + product
        await self.db.buyerInteractions.create_index(
            [("buyerId", 1), ("sellerId", 1), ("productId", 1)],
            name="buyer_seller_product_unique",
            unique=True
        )
        
        # Index for batch lookups
        await self.db.buyerInteractions.create_index(
            [("buyerId", 1), ("productId", 1)],
            name="buyer_product_lookup"
        )
        
        logger.info("BuyerInteraction indexes ensured")
    
    async def track_view(
        self, 
        buyer_id: ObjectId, 
        seller_id: ObjectId, 
        product_id: ObjectId
    ) -> bool:
        """
        Track a product view.
        Increments views counter using upsert (no race conditions).
        """
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        if isinstance(seller_id, str):
            seller_id = ObjectId(seller_id)
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        now = datetime.now(timezone.utc)
        
        await self.db.buyerInteractions.update_one(
            {
                "buyerId": buyer_id,
                "sellerId": seller_id,
                "productId": product_id
            },
            {
                "$inc": {"views": 1},
                "$set": {"lastInteractionAt": now},
                "$setOnInsert": {
                    "inquiries": 0,
                    "orders": 0,
                    "createdAt": now
                }
            },
            upsert=True
        )
        
        return True
    
    async def track_inquiry(
        self, 
        buyer_id: ObjectId, 
        seller_id: ObjectId, 
        product_id: ObjectId
    ) -> bool:
        """
        Track an inquiry.
        Increments inquiries counter and sets one view if first interaction.
        """
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        if isinstance(seller_id, str):
            seller_id = ObjectId(seller_id)
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        now = datetime.now(timezone.utc)
        
        await self.db.buyerInteractions.update_one(
            {
                "buyerId": buyer_id,
                "sellerId": seller_id,
                "productId": product_id
            },
            {
                "$inc": {"inquiries": 1, "views": 1},  # Inquiry implies a view
                "$set": {"lastInteractionAt": now},
                "$setOnInsert": {
                    "orders": 0,
                    "createdAt": now
                }
            },
            upsert=True
        )
        
        return True
    
    async def track_order(
        self, 
        buyer_id: ObjectId, 
        seller_id: ObjectId, 
        product_id: ObjectId
    ) -> bool:
        """
        Track an order.
        Increments orders counter.
        """
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        if isinstance(seller_id, str):
            seller_id = ObjectId(seller_id)
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        now = datetime.now(timezone.utc)
        
        await self.db.buyerInteractions.update_one(
            {
                "buyerId": buyer_id,
                "sellerId": seller_id,
                "productId": product_id
            },
            {
                "$inc": {"orders": 1},
                "$set": {"lastInteractionAt": now},
                "$setOnInsert": {
                    "views": 1,
                    "inquiries": 0,
                    "createdAt": now
                }
            },
            upsert=True
        )
        
        return True
    
    def calculate_boost_from_interaction(self, interaction: Dict[str, Any]) -> int:
        """
        Calculate behavior boost from a single interaction document.
        
        Logic (priority order, capped at 15):
        - orders > 0: +15 (max)
        - inquiries > 0: +10
        - views > 2: +5
        
        Returns:
            Boost value (0-15)
        """
        if not interaction:
            return 0
        
        orders = interaction.get("orders", 0)
        inquiries = interaction.get("inquiries", 0)
        views = interaction.get("views", 0)
        
        boost = 0
        
        if orders > 0:
            boost = BEHAVIOR_BOOST_CONFIG["has_orders"]
        elif inquiries > 0:
            boost = BEHAVIOR_BOOST_CONFIG["has_inquiries"]
        elif views > 2:
            boost = BEHAVIOR_BOOST_CONFIG["has_views"]
        
        # Cap at max
        return min(boost, BEHAVIOR_BOOST_CONFIG["max_boost"])
    
    async def calculate_behavior_boost(
        self, 
        buyer_id: ObjectId, 
        seller_id: ObjectId, 
        product_id: ObjectId
    ) -> int:
        """
        Calculate behavior boost for a specific buyer-seller-product combination.
        
        Returns:
            Boost value (0-15)
        """
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        if isinstance(seller_id, str):
            seller_id = ObjectId(seller_id)
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        interaction = await self.db.buyerInteractions.find_one({
            "buyerId": buyer_id,
            "sellerId": seller_id,
            "productId": product_id
        })
        
        return self.calculate_boost_from_interaction(interaction)
    
    async def get_batch_boosts(
        self,
        buyer_id: ObjectId,
        product_id: ObjectId,
        seller_ids: List[str]
    ) -> Dict[str, int]:
        """
        Batch load behavior boosts for multiple sellers.
        Used by ranking engine to avoid N+1 queries.
        
        Args:
            buyer_id: Buyer ObjectId
            product_id: Product ObjectId
            seller_ids: List of seller IDs (as strings)
        
        Returns:
            Dict mapping seller_id -> boost value
        """
        if not buyer_id or not product_id or not seller_ids:
            return {}
        
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        # Convert seller_ids to ObjectIds
        seller_oids = [ObjectId(sid) for sid in seller_ids if ObjectId.is_valid(sid)]
        
        if not seller_oids:
            return {}
        
        # Single batch query
        cursor = self.db.buyerInteractions.find({
            "buyerId": buyer_id,
            "productId": product_id,
            "sellerId": {"$in": seller_oids}
        })
        
        result = {}
        async for interaction in cursor:
            seller_id = str(interaction["sellerId"])
            boost = self.calculate_boost_from_interaction(interaction)
            result[seller_id] = boost
        
        return result
    
    async def get_interaction_stats(
        self,
        buyer_id: ObjectId
    ) -> Dict[str, Any]:
        """
        Get aggregate interaction stats for a buyer.
        Useful for analytics/debugging.
        """
        if isinstance(buyer_id, str):
            buyer_id = ObjectId(buyer_id)
        
        pipeline = [
            {"$match": {"buyerId": buyer_id}},
            {"$group": {
                "_id": None,
                "totalViews": {"$sum": "$views"},
                "totalInquiries": {"$sum": "$inquiries"},
                "totalOrders": {"$sum": "$orders"},
                "uniqueSellers": {"$addToSet": "$sellerId"},
                "uniqueProducts": {"$addToSet": "$productId"}
            }}
        ]
        
        result = await self.db.buyerInteractions.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "totalViews": 0,
                "totalInquiries": 0,
                "totalOrders": 0,
                "uniqueSellers": 0,
                "uniqueProducts": 0
            }
        
        stats = result[0]
        return {
            "totalViews": stats.get("totalViews", 0),
            "totalInquiries": stats.get("totalInquiries", 0),
            "totalOrders": stats.get("totalOrders", 0),
            "uniqueSellers": len(stats.get("uniqueSellers", [])),
            "uniqueProducts": len(stats.get("uniqueProducts", []))
        }


# Helper for backward compatibility
async def get_interaction_service(db) -> BuyerInteractionService:
    """Factory function to get interaction service instance."""
    service = BuyerInteractionService(db)
    return service
