"""
SELLER LOCATION SERVICE
========================

Manages:
1. activeSellerCities collection - Cities where sellers are onboarded
2. Location autocomplete - Returns only seller-validated cities
3. Nearby city suggestions - When no sellers in searched location
4. Geo proximity calculations

ARCHITECTURE:
- Buyers can ONLY search cities where sellers exist
- No dead zone searches
- Trust-building location system
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from bson import ObjectId
from datetime import datetime, timezone

from services.pincode_geocode_service import geocode_service, GeoLocation, MAJOR_CITY_COORDINATES, STATE_COORDINATES

logger = logging.getLogger(__name__)


@dataclass
class LocationSuggestion:
    """Structured location suggestion for autocomplete"""
    label: str
    type: str  # 'city', 'state', 'pincode', 'pan_india'
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    coordinates: Optional[List[float]] = None  # [lng, lat]
    seller_count: int = 0


class SellerLocationService:
    """
    Manages seller locations and provides location autocomplete.
    
    Key Features:
    - Only returns cities where sellers exist
    - Provides nearby suggestions for empty cities
    - Maintains activeSellerCities collection
    """
    
    def __init__(self, db):
        self.db = db
    
    # ==================== ACTIVE SELLER CITIES ====================
    
    async def update_seller_city(self, city: str, state: str, increment: int = 1):
        """
        Update seller count for a city.
        Called when seller creates/deletes listing.
        
        Args:
            city: City name
            state: State name
            increment: +1 for new listing, -1 for deleted
        """
        if not city or not state:
            return
        
        city_normalized = city.strip().title()
        state_normalized = state.strip().title()
        
        # Get coordinates
        coords = None
        location = geocode_service.get_coordinates_by_city(city_normalized)
        if location:
            coords = [location.longitude, location.latitude]  # GeoJSON format
        
        await self.db.activeSellerCities.update_one(
            {"city": city_normalized, "state": state_normalized},
            {
                "$inc": {"sellerCount": increment},
                "$set": {
                    "coordinates": coords,
                    "updatedAt": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "city": city_normalized,
                    "state": state_normalized,
                    "createdAt": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # Remove if count drops to 0 or below
        await self.db.activeSellerCities.delete_many({"sellerCount": {"$lte": 0}})
    
    async def rebuild_active_seller_cities(self):
        """
        Rebuild the activeSellerCities collection from scratch.
        Run this as a maintenance task.
        """
        logger.info("Rebuilding activeSellerCities collection...")
        
        # Clear existing
        await self.db.activeSellerCities.delete_many({})
        
        # Aggregate from sellerListings
        pipeline = [
            {"$match": {"isActive": True, "status": "active"}},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": "$seller"},
            {"$group": {
                "_id": {
                    "city": "$seller.profile.city",
                    "state": "$seller.profile.state"
                },
                "sellerCount": {"$sum": 1},
                "sellerIds": {"$addToSet": "$sellerId"}
            }},
            {"$match": {
                "_id.city": {"$ne": None},
                "_id.state": {"$ne": None}
            }}
        ]
        
        results = await self.db.sellerListings.aggregate(pipeline).to_list(None)
        
        for r in results:
            city = r["_id"]["city"]
            state = r["_id"]["state"]
            
            if city and state:
                city_normalized = city.strip().title()
                state_normalized = state.strip().title()
                
                # Get coordinates
                coords = None
                location = geocode_service.get_coordinates_by_city(city_normalized)
                if location:
                    coords = [location.longitude, location.latitude]
                
                await self.db.activeSellerCities.insert_one({
                    "city": city_normalized,
                    "state": state_normalized,
                    "sellerCount": len(r["sellerIds"]),
                    "coordinates": coords,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                })
        
        count = await self.db.activeSellerCities.count_documents({})
        logger.info(f"Rebuilt activeSellerCities: {count} cities with active sellers")
        return count
    
    # ==================== LOCATION AUTOCOMPLETE ====================
    
    async def get_location_suggestions(
        self,
        query: str,
        limit: int = 10,
        include_states: bool = True,
        include_pan_india: bool = True
    ) -> List[LocationSuggestion]:
        """
        Get location suggestions for autocomplete.
        
        ONLY returns cities where sellers exist (from activeSellerCities).
        
        Args:
            query: User input (e.g., "pu", "411", "maha")
            limit: Max suggestions
            include_states: Include state-level options
            include_pan_india: Include "Pan India" option
        
        Returns:
            List of structured location suggestions
        """
        suggestions = []
        query_lower = query.lower().strip()
        
        if not query_lower:
            return suggestions
        
        # 1. Check if it's a pincode (all digits, 6 chars)
        if query_lower.isdigit():
            pincode_suggestions = await self._get_pincode_suggestions(query_lower, limit)
            suggestions.extend(pincode_suggestions)
        
        # 2. Search active seller cities
        city_suggestions = await self._get_city_suggestions(query_lower, limit)
        suggestions.extend(city_suggestions)
        
        # 3. Search states (if enabled)
        if include_states:
            state_suggestions = self._get_state_suggestions(query_lower, limit)
            suggestions.extend(state_suggestions)
        
        # 4. Add Pan India option if query matches
        if include_pan_india and 'pan' in query_lower or 'india' in query_lower or 'all' in query_lower:
            suggestions.append(LocationSuggestion(
                label="Pan India (All Locations)",
                type="pan_india",
                seller_count=await self.db.sellerListings.count_documents({"isActive": True})
            ))
        
        # Deduplicate and sort by seller count
        seen = set()
        unique = []
        for s in suggestions:
            key = (s.type, s.city, s.state, s.pincode)
            if key not in seen:
                seen.add(key)
                unique.append(s)
        
        unique.sort(key=lambda x: x.seller_count, reverse=True)
        
        return unique[:limit]
    
    async def _get_pincode_suggestions(self, query: str, limit: int) -> List[LocationSuggestion]:
        """Get suggestions for pincode input."""
        suggestions = []
        
        # Find cities with matching pincodes in seller data
        pipeline = [
            {"$match": {
                "isActive": True,
                "status": "active"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": "$seller"},
            {"$match": {
                "seller.profile.pincode": {"$regex": f"^{query}"}
            }},
            {"$group": {
                "_id": {
                    "pincode": "$seller.profile.pincode",
                    "city": "$seller.profile.city",
                    "state": "$seller.profile.state"
                },
                "count": {"$sum": 1}
            }},
            {"$limit": limit}
        ]
        
        results = await self.db.sellerListings.aggregate(pipeline).to_list(limit)
        
        for r in results:
            pincode = r["_id"]["pincode"]
            city = r["_id"]["city"]
            state = r["_id"]["state"]
            
            if pincode:
                # Get coordinates from pincode
                location = geocode_service.get_coordinates_by_pincode(pincode)
                coords = [location.longitude, location.latitude] if location else None
                
                suggestions.append(LocationSuggestion(
                    label=f"{pincode} - {city or 'Unknown'}, {state or 'Unknown'}",
                    type="pincode",
                    city=city,
                    state=state,
                    pincode=pincode,
                    coordinates=coords,
                    seller_count=r["count"]
                ))
        
        return suggestions
    
    async def _get_city_suggestions(self, query: str, limit: int) -> List[LocationSuggestion]:
        """Get city suggestions from activeSellerCities."""
        suggestions = []
        
        # Search cities matching query
        cities = await self.db.activeSellerCities.find({
            "$or": [
                {"city": {"$regex": query, "$options": "i"}},
                {"state": {"$regex": query, "$options": "i"}}
            ],
            "sellerCount": {"$gt": 0}
        }).sort("sellerCount", -1).limit(limit).to_list(limit)
        
        for c in cities:
            suggestions.append(LocationSuggestion(
                label=f"{c['city']}, {c['state']}",
                type="city",
                city=c["city"],
                state=c["state"],
                coordinates=c.get("coordinates"),
                seller_count=c["sellerCount"]
            ))
        
        return suggestions
    
    def _get_state_suggestions(self, query: str, limit: int) -> List[LocationSuggestion]:
        """Get state suggestions from static list."""
        suggestions = []
        
        for state, coords in STATE_COORDINATES.items():
            if query in state.lower():
                suggestions.append(LocationSuggestion(
                    label=state.title(),
                    type="state",
                    state=state.title(),
                    coordinates=[coords[1], coords[0]],  # [lng, lat]
                    seller_count=0  # Will be populated from DB if needed
                ))
        
        return suggestions[:limit]
    
    # ==================== NEARBY SUGGESTIONS ====================
    
    async def get_nearby_cities(
        self,
        city: str = None,
        state: str = None,
        pincode: str = None,
        limit: int = 5
    ) -> List[LocationSuggestion]:
        """
        Get nearby cities with active sellers.
        
        Used when buyer searches a city without sellers.
        
        "No sellers onboarded yet in Nashik.
         Showing nearby cities: Pune, Mumbai, Aurangabad"
        """
        # Get coordinates for the searched location
        target_coords = None
        
        if pincode:
            location = geocode_service.get_coordinates_by_pincode(pincode)
            if location:
                target_coords = (location.latitude, location.longitude)
        
        if not target_coords and city:
            location = geocode_service.get_coordinates_by_city(city)
            if location:
                target_coords = (location.latitude, location.longitude)
        
        if not target_coords:
            # Can't calculate distance, return top cities by seller count
            cities = await self.db.activeSellerCities.find(
                {"sellerCount": {"$gt": 0}}
            ).sort("sellerCount", -1).limit(limit).to_list(limit)
            
            return [
                LocationSuggestion(
                    label=f"{c['city']}, {c['state']}",
                    type="city",
                    city=c["city"],
                    state=c["state"],
                    coordinates=c.get("coordinates"),
                    seller_count=c["sellerCount"]
                )
                for c in cities
            ]
        
        # Get all active seller cities and calculate distance
        cities = await self.db.activeSellerCities.find(
            {"sellerCount": {"$gt": 0}, "coordinates": {"$ne": None}}
        ).to_list(None)
        
        # Calculate distance for each
        cities_with_distance = []
        for c in cities:
            if c.get("coordinates"):
                # coordinates are [lng, lat]
                city_coords = (c["coordinates"][1], c["coordinates"][0])
                distance = geocode_service.calculate_distance_km(
                    target_coords[0], target_coords[1],
                    city_coords[0], city_coords[1]
                )
                cities_with_distance.append((c, distance))
        
        # Sort by distance
        cities_with_distance.sort(key=lambda x: x[1])
        
        # Return closest cities
        return [
            LocationSuggestion(
                label=f"{c['city']}, {c['state']} ({int(dist)} km away)",
                type="city",
                city=c["city"],
                state=c["state"],
                coordinates=c.get("coordinates"),
                seller_count=c["sellerCount"]
            )
            for c, dist in cities_with_distance[:limit]
        ]
    
    async def check_sellers_in_location(
        self,
        city: str = None,
        state: str = None,
        pincode: str = None
    ) -> Dict[str, Any]:
        """
        Check if sellers exist in a location.
        
        Returns:
            {
                "hasSellers": bool,
                "sellerCount": int,
                "nearbyAlternatives": [...] if no sellers
            }
        """
        seller_count = 0
        
        if city:
            result = await self.db.activeSellerCities.find_one({
                "city": {"$regex": f"^{city}$", "$options": "i"},
                "sellerCount": {"$gt": 0}
            })
            if result:
                seller_count = result["sellerCount"]
        elif state:
            # Count all cities in state
            pipeline = [
                {"$match": {"state": {"$regex": f"^{state}$", "$options": "i"}}},
                {"$group": {"_id": None, "total": {"$sum": "$sellerCount"}}}
            ]
            result = await self.db.activeSellerCities.aggregate(pipeline).to_list(1)
            if result:
                seller_count = result[0]["total"]
        
        if seller_count > 0:
            return {
                "hasSellers": True,
                "sellerCount": seller_count,
                "nearbyAlternatives": []
            }
        
        # No sellers - get nearby alternatives
        nearby = await self.get_nearby_cities(city=city, state=state, pincode=pincode)
        
        return {
            "hasSellers": False,
            "sellerCount": 0,
            "message": f"No sellers onboarded yet in {city or state or pincode}",
            "nearbyAlternatives": [
                {
                    "label": n.label,
                    "city": n.city,
                    "state": n.state,
                    "sellerCount": n.seller_count
                }
                for n in nearby
            ]
        }


# Factory function to create service
def create_seller_location_service(db):
    return SellerLocationService(db)
