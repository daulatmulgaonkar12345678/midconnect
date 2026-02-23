"""
Enterprise Ranking Configuration
================================

Configurable weights for deterministic seller ranking.
These weights control how listings are scored and sorted.

Score = Σ(weight * factor) normalized to 0-100
"""

from typing import Dict, Any
from pydantic import BaseModel


class RankingWeights(BaseModel):
    """Ranking weight configuration."""
    
    # Stock & Availability (max 25 points)
    stock_available: float = 20.0          # Has stock > 0
    stock_high: float = 5.0                # Stock > 50 units
    
    # Subscription Tier (max 25 points) - Monetization lever
    subscription_free: float = 0.0
    subscription_trial: float = 5.0
    subscription_pro: float = 15.0
    subscription_enterprise: float = 25.0
    
    # Lead Time (max 15 points)
    lead_time_under_3_days: float = 15.0
    lead_time_under_7_days: float = 10.0
    lead_time_under_14_days: float = 5.0
    lead_time_over_14_days: float = 0.0
    
    # Price Competitiveness (max 15 points)
    price_lowest_10_percent: float = 15.0
    price_lowest_20_percent: float = 10.0
    price_lowest_50_percent: float = 5.0
    price_above_median: float = 0.0
    
    # Location Proximity (max 10 points)
    location_same_city: float = 10.0
    location_same_state: float = 7.0
    location_same_region: float = 3.0
    location_different_region: float = 0.0
    
    # Specification Match Quality (max 20 points)
    spec_exact_match: float = 20.0
    spec_partial_match: float = 10.0
    spec_fallback_match: float = 5.0
    
    # Seller Quality Signals (bonus points)
    verified_seller: float = 5.0
    has_images: float = 3.0
    has_description: float = 2.0
    recently_updated: float = 3.0          # Updated within 7 days
    
    class Config:
        """Allow weight updates at runtime."""
        extra = "allow"


class RankingConfig:
    """
    Ranking configuration manager.
    Allows runtime weight updates for A/B testing and tuning.
    """
    
    _instance = None
    _weights: RankingWeights = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._weights = RankingWeights()
        return cls._instance
    
    @property
    def weights(self) -> RankingWeights:
        return self._weights
    
    def update_weights(self, updates: Dict[str, float]) -> None:
        """Update specific weights. Used by admin config endpoint."""
        current = self._weights.model_dump()
        current.update(updates)
        self._weights = RankingWeights(**current)
    
    def reset_weights(self) -> None:
        """Reset to default weights."""
        self._weights = RankingWeights()
    
    def get_weights_dict(self) -> Dict[str, float]:
        """Get all weights as dictionary."""
        return self._weights.model_dump()
    
    def get_max_possible_score(self) -> float:
        """
        Calculate maximum possible score.
        Used for normalization.
        """
        w = self._weights
        return (
            # Best case scenario
            w.stock_available + w.stock_high +
            w.subscription_enterprise +
            w.lead_time_under_3_days +
            w.price_lowest_10_percent +
            w.location_same_city +
            w.spec_exact_match +
            w.verified_seller + w.has_images + w.has_description + w.recently_updated
        )


# Regional mapping for India
INDIA_REGIONS = {
    "north": ["delhi", "haryana", "punjab", "uttar pradesh", "uttarakhand", "himachal pradesh", "jammu and kashmir", "ladakh", "chandigarh"],
    "south": ["karnataka", "tamil nadu", "kerala", "andhra pradesh", "telangana", "puducherry"],
    "west": ["maharashtra", "gujarat", "rajasthan", "goa", "daman and diu", "dadra and nagar haveli"],
    "east": ["west bengal", "odisha", "bihar", "jharkhand", "sikkim", "andaman and nicobar"],
    "northeast": ["assam", "meghalaya", "manipur", "mizoram", "tripura", "nagaland", "arunachal pradesh"],
    "central": ["madhya pradesh", "chhattisgarh"],
}


def get_region_for_state(state: str) -> str:
    """Get region for a given state."""
    if not state:
        return "unknown"
    state_lower = state.lower().strip()
    for region, states in INDIA_REGIONS.items():
        if state_lower in states:
            return region
    return "unknown"


# Singleton instance
ranking_config = RankingConfig()
