"""
Enterprise Ranking Service
===========================

Deterministic ranking engine for B2B marketplace listings.
Computes weighted scores based on configurable business rules.

Score Components:
- Stock availability
- Subscription tier (monetization)
- Lead time
- Price competitiveness
- Location proximity
- Specification match quality
- Seller quality signals
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

from config.ranking_config import (
    ranking_config, 
    RankingWeights,
    get_region_for_state
)

logger = logging.getLogger(__name__)


class RankingBreakdown:
    """
    Detailed breakdown of ranking score calculation.
    Used for debugging and transparency.
    """
    
    def __init__(self, listing_id: str):
        self.listing_id = listing_id
        self.components: Dict[str, float] = {}
        self.raw_score: float = 0.0
        self.normalized_score: float = 0.0
        self.factors: Dict[str, Any] = {}
    
    def add_component(self, name: str, score: float, factor: Any = None):
        """Add a scoring component."""
        self.components[name] = score
        self.raw_score += score
        if factor is not None:
            self.factors[name] = factor
    
    def normalize(self, max_score: float):
        """Normalize score to 0-100 scale."""
        if max_score > 0:
            self.normalized_score = round((self.raw_score / max_score) * 100, 2)
        else:
            self.normalized_score = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "listing_id": self.listing_id,
            "raw_score": round(self.raw_score, 2),
            "normalized_score": self.normalized_score,
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "factors": self.factors
        }


class EnterpriseRankingService:
    """
    Enterprise ranking engine for seller listings.
    
    Usage:
        ranker = EnterpriseRankingService()
        ranked_listings = ranker.rank_listings(
            listings=seller_listings,
            buyer_context={"state": "Maharashtra", "city": "Mumbai"},
            price_stats={"min": 1000, "max": 50000, "median": 15000},
            match_quality="exact"
        )
    """
    
    def __init__(self):
        self.config = ranking_config
    
    @property
    def weights(self) -> RankingWeights:
        return self.config.weights
    
    def compute_listing_score(
        self,
        listing: Dict[str, Any],
        buyer_context: Optional[Dict[str, Any]] = None,
        price_stats: Optional[Dict[str, float]] = None,
        match_quality: str = "exact",
        subscription_cache: Optional[Dict[str, str]] = None,
        debug: bool = False
    ) -> Tuple[float, Optional[RankingBreakdown]]:
        """
        Compute ranking score for a single listing.
        
        Args:
            listing: The seller listing document
            buyer_context: Buyer's location info {"city", "state"}
            price_stats: Price distribution {"min", "max", "median", "p10", "p20"}
            match_quality: "exact", "partial", or "fallback"
            subscription_cache: Pre-loaded subscription data {seller_id: plan_name}
            debug: If True, return detailed breakdown
        
        Returns:
            Tuple of (normalized_score, breakdown or None)
        """
        w = self.weights
        breakdown = RankingBreakdown(str(listing.get("_id", ""))) if debug else None
        
        # === STOCK & AVAILABILITY (max 25) ===
        stock = listing.get("stock", 0)
        stock_score = 0.0
        
        if stock > 0:
            stock_score += w.stock_available
            if stock > 50:
                stock_score += w.stock_high
        
        if breakdown:
            breakdown.add_component("stock", stock_score, {"stock": stock})
        
        # === SUBSCRIPTION TIER (max 25) ===
        seller_id = str(listing.get("sellerId", ""))
        subscription_plan = "free"
        
        if subscription_cache and seller_id in subscription_cache:
            subscription_plan = subscription_cache[seller_id]
        
        subscription_score = {
            "free": w.subscription_free,
            "trial": w.subscription_trial,
            "pro": w.subscription_pro,
            "enterprise": w.subscription_enterprise,
        }.get(subscription_plan, w.subscription_free)
        
        if breakdown:
            breakdown.add_component("subscription", subscription_score, {"plan": subscription_plan})
        
        # === LEAD TIME (max 15) ===
        lead_time = listing.get("leadTime") or listing.get("leadTimeDays")
        lead_time_score = 0.0
        
        if lead_time is not None:
            if lead_time <= 3:
                lead_time_score = w.lead_time_under_3_days
            elif lead_time <= 7:
                lead_time_score = w.lead_time_under_7_days
            elif lead_time <= 14:
                lead_time_score = w.lead_time_under_14_days
            else:
                lead_time_score = w.lead_time_over_14_days
        
        if breakdown:
            breakdown.add_component("lead_time", lead_time_score, {"days": lead_time})
        
        # === PRICE COMPETITIVENESS (max 15) ===
        price_score = 0.0
        listing_price = self._get_listing_price(listing)
        
        if listing_price and price_stats:
            p10 = price_stats.get("p10")
            p20 = price_stats.get("p20")
            median = price_stats.get("median")
            
            if p10 and listing_price <= p10:
                price_score = w.price_lowest_10_percent
            elif p20 and listing_price <= p20:
                price_score = w.price_lowest_20_percent
            elif median and listing_price <= median:
                price_score = w.price_lowest_50_percent
            else:
                price_score = w.price_above_median
        
        if breakdown:
            breakdown.add_component("price", price_score, {"price": listing_price})
        
        # === LOCATION PROXIMITY (max 10) ===
        location_score = 0.0
        
        if buyer_context:
            buyer_city = (buyer_context.get("city") or "").lower().strip()
            buyer_state = (buyer_context.get("state") or "").lower().strip()
            buyer_region = get_region_for_state(buyer_state)
            
            seller_profile = listing.get("sellerProfile", {})
            seller_city = (seller_profile.get("city") or "").lower().strip()
            seller_state = (seller_profile.get("state") or "").lower().strip()
            seller_region = get_region_for_state(seller_state)
            
            if buyer_city and seller_city and buyer_city == seller_city:
                location_score = w.location_same_city
            elif buyer_state and seller_state and buyer_state == seller_state:
                location_score = w.location_same_state
            elif buyer_region != "unknown" and buyer_region == seller_region:
                location_score = w.location_same_region
            else:
                location_score = w.location_different_region
        
        if breakdown:
            breakdown.add_component("location", location_score)
        
        # === SPECIFICATION MATCH QUALITY (max 20) ===
        match_score = {
            "exact": w.spec_exact_match,
            "partial": w.spec_partial_match,
            "fallback": w.spec_fallback_match,
        }.get(match_quality, w.spec_fallback_match)
        
        if breakdown:
            breakdown.add_component("spec_match", match_score, {"quality": match_quality})
        
        # === SELLER QUALITY SIGNALS (bonus) ===
        quality_score = 0.0
        
        # Verified seller (check for badge or role)
        seller_role = listing.get("sellerRole", "").lower()
        if seller_role in ["manufacturer", "authorized_dealer"]:
            quality_score += w.verified_seller
        
        # Has images
        images = listing.get("images", [])
        if images and len(images) > 0:
            quality_score += w.has_images
        
        # Has description
        description = listing.get("description") or listing.get("searchableText", "")
        if description and len(description) > 50:
            quality_score += w.has_description
        
        # Recently updated
        updated_at = listing.get("updatedAt")
        if updated_at:
            try:
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                elif isinstance(updated_at, datetime) and updated_at.tzinfo is None:
                    # Make naive datetime UTC-aware
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                if updated_at and (datetime.now(timezone.utc) - updated_at) < timedelta(days=7):
                    quality_score += w.recently_updated
            except Exception:
                pass  # Skip if date parsing fails
        
        if breakdown:
            breakdown.add_component("quality", quality_score)
        
        # === BEHAVIOR BOOST (capped at 15) ===
        behavior_boost = listing.get("_behaviorBoost", 0)
        
        if breakdown and behavior_boost > 0:
            breakdown.add_component("behavior_boost", behavior_boost)
        
        # === CALCULATE FINAL SCORE ===
        base_score = (
            stock_score + 
            subscription_score + 
            lead_time_score + 
            price_score + 
            location_score + 
            match_score + 
            quality_score
        )
        
        # Add behavior boost (capped at 15)
        behavior_boost = min(behavior_boost, 15)
        raw_score = base_score + behavior_boost
        
        max_score = self.config.get_max_possible_score() + 15  # Include behavior boost cap
        normalized_score = round((raw_score / max_score) * 100, 2) if max_score > 0 else 0.0
        
        if breakdown:
            breakdown.raw_score = raw_score
            breakdown.factors["baseScore"] = round(base_score, 2)
            breakdown.factors["behaviorBoost"] = behavior_boost
            breakdown.normalize(max_score)
        
        return normalized_score, breakdown
    
    def rank_listings(
        self,
        listings: List[Dict[str, Any]],
        buyer_context: Optional[Dict[str, Any]] = None,
        match_quality: str = "exact",
        subscription_cache: Optional[Dict[str, str]] = None,
        behavior_boost_cache: Optional[Dict[str, int]] = None,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of listings and return them sorted by score.
        
        Args:
            listings: List of seller listing documents
            buyer_context: Buyer's location info
            match_quality: Match quality level
            subscription_cache: Pre-loaded subscription data
            behavior_boost_cache: Pre-loaded behavior boosts {seller_id: boost}
            debug: If True, add ranking_breakdown to each listing
        
        Returns:
            Sorted list of listings with rankingScore added
        """
        if not listings:
            return []
        
        # Calculate price statistics for competitiveness scoring
        price_stats = self._calculate_price_stats(listings)
        
        # Score each listing
        scored_listings = []
        breakdowns = []
        
        for listing in listings:
            # Inject behavior boost into listing for scoring
            seller_id = str(listing.get("sellerId", ""))
            if behavior_boost_cache and seller_id in behavior_boost_cache:
                listing["_behaviorBoost"] = behavior_boost_cache[seller_id]
            
            score, breakdown = self.compute_listing_score(
                listing=listing,
                buyer_context=buyer_context,
                price_stats=price_stats,
                match_quality=match_quality,
                subscription_cache=subscription_cache,
                debug=debug
            )
            
            listing_with_score = dict(listing)
            listing_with_score["rankingScore"] = score
            
            # Remove internal field
            listing_with_score.pop("_behaviorBoost", None)
            
            if debug and breakdown:
                listing_with_score["rankingBreakdown"] = breakdown.to_dict()
                breakdowns.append(breakdown.to_dict())
            
            scored_listings.append(listing_with_score)
        
        # Sort by ranking score (descending)
        scored_listings.sort(key=lambda x: x.get("rankingScore", 0), reverse=True)
        
        # Log breakdown summary if debug
        if debug and breakdowns:
            logger.info(f"Ranking breakdown for {len(breakdowns)} listings: "
                       f"Score range: {min(b['normalized_score'] for b in breakdowns):.1f} - "
                       f"{max(b['normalized_score'] for b in breakdowns):.1f}")
        
        return scored_listings
    
    def _get_listing_price(self, listing: Dict[str, Any]) -> Optional[float]:
        """Extract the lowest price from a listing."""
        # Check for pre-computed lowest price
        if "lowestPrice" in listing and listing["lowestPrice"]:
            return float(listing["lowestPrice"])
        
        # Extract from pricing tiers
        pricing_tiers = listing.get("pricingTiers", [])
        if pricing_tiers:
            prices = [t.get("pricePerUnit", 0) for t in pricing_tiers if t.get("pricePerUnit")]
            if prices:
                return float(min(prices))
        
        return None
    
    def _calculate_price_stats(self, listings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate price distribution statistics for the listing set."""
        prices = []
        for listing in listings:
            price = self._get_listing_price(listing)
            if price and price > 0:
                prices.append(price)
        
        if not prices:
            return {}
        
        prices.sort()
        n = len(prices)
        
        return {
            "min": prices[0],
            "max": prices[-1],
            "median": prices[n // 2],
            "p10": prices[int(n * 0.1)] if n >= 10 else prices[0],
            "p20": prices[int(n * 0.2)] if n >= 5 else prices[0],
            "count": n
        }


# Singleton instance
enterprise_ranker = EnterpriseRankingService()
