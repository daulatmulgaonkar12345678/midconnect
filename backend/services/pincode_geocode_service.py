"""
PINCODE GEOCODING SERVICE
=========================

Converts Indian pincodes to latitude/longitude coordinates.

Uses a static database of pincode centroids for India.
Falls back to approximate city coordinates if pincode not found.
"""

import os
import json
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Geographic location with coordinates"""
    latitude: float
    longitude: float
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


# Major Indian cities with approximate coordinates
MAJOR_CITY_COORDINATES = {
    # Maharashtra
    'mumbai': (19.0760, 72.8777),
    'pune': (18.5204, 73.8567),
    'nagpur': (21.1458, 79.0882),
    'nashik': (20.0063, 73.7900),
    'aurangabad': (19.8762, 75.3433),
    'solapur': (17.6599, 75.9064),
    'kolhapur': (16.7050, 74.2433),
    'sangli': (16.8524, 74.5815),
    'thane': (19.2183, 72.9781),
    'navi mumbai': (19.0330, 73.0297),
    
    # Gujarat
    'ahmedabad': (23.0225, 72.5714),
    'surat': (21.1702, 72.8311),
    'vadodara': (22.3072, 73.1812),
    'rajkot': (22.3039, 70.8022),
    
    # Karnataka
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'mysore': (12.2958, 76.6394),
    'hubli': (15.3647, 75.1240),
    
    # Tamil Nadu
    'chennai': (13.0827, 80.2707),
    'coimbatore': (11.0168, 76.9558),
    'madurai': (9.9252, 78.1198),
    
    # Telangana
    'hyderabad': (17.3850, 78.4867),
    
    # Delhi NCR
    'delhi': (28.7041, 77.1025),
    'new delhi': (28.6139, 77.2090),
    'noida': (28.5355, 77.3910),
    'gurgaon': (28.4595, 77.0266),
    'gurugram': (28.4595, 77.0266),
    'faridabad': (28.4089, 77.3178),
    'ghaziabad': (28.6692, 77.4538),
    
    # Uttar Pradesh
    'lucknow': (26.8467, 80.9462),
    'kanpur': (26.4499, 80.3319),
    'agra': (27.1767, 78.0081),
    'varanasi': (25.3176, 82.9739),
    
    # West Bengal
    'kolkata': (22.5726, 88.3639),
    
    # Rajasthan
    'jaipur': (26.9124, 75.7873),
    'jodhpur': (26.2389, 73.0243),
    'udaipur': (24.5854, 73.7125),
    
    # Madhya Pradesh
    'indore': (22.7196, 75.8577),
    'bhopal': (23.2599, 77.4126),
    
    # Bihar
    'patna': (25.5941, 85.1376),
    
    # Odisha
    'bhubaneswar': (20.2961, 85.8245),
    
    # Kerala
    'kochi': (9.9312, 76.2673),
    'cochin': (9.9312, 76.2673),
    'thiruvananthapuram': (8.5241, 76.9366),
    
    # Punjab
    'chandigarh': (30.7333, 76.7794),
    'ludhiana': (30.9010, 75.8573),
    'amritsar': (31.6340, 74.8723),
    
    # Assam
    'guwahati': (26.1445, 91.7362),
}

# State coordinates (approximate center)
STATE_COORDINATES = {
    'maharashtra': (19.7515, 75.7139),
    'gujarat': (22.2587, 71.1924),
    'karnataka': (15.3173, 75.7139),
    'tamil nadu': (11.1271, 78.6569),
    'telangana': (18.1124, 79.0193),
    'andhra pradesh': (15.9129, 79.7400),
    'delhi': (28.7041, 77.1025),
    'uttar pradesh': (26.8467, 80.9462),
    'west bengal': (22.9868, 87.8550),
    'rajasthan': (27.0238, 74.2179),
    'madhya pradesh': (22.9734, 78.6569),
    'bihar': (25.0961, 85.3131),
    'odisha': (20.9517, 85.0985),
    'kerala': (10.8505, 76.2711),
    'punjab': (31.1471, 75.3412),
    'haryana': (29.0588, 76.0856),
    'assam': (26.2006, 92.9376),
    'jharkhand': (23.6102, 85.2799),
    'chhattisgarh': (21.2787, 81.8661),
    'uttarakhand': (30.0668, 79.0193),
    'himachal pradesh': (31.1048, 77.1734),
    'goa': (15.2993, 74.1240),
}

# Pincode prefix to state mapping (first 2 digits)
PINCODE_PREFIX_TO_STATE = {
    '11': 'delhi',
    '12': 'haryana',
    '13': 'punjab',
    '14': 'punjab',
    '15': 'punjab',
    '16': 'punjab',
    '17': 'himachal pradesh',
    '18': 'jammu and kashmir',
    '19': 'jammu and kashmir',
    '20': 'uttar pradesh',
    '21': 'uttar pradesh',
    '22': 'uttar pradesh',
    '23': 'uttar pradesh',
    '24': 'uttar pradesh',
    '25': 'uttar pradesh',
    '26': 'uttar pradesh',
    '27': 'uttar pradesh',
    '28': 'uttar pradesh',
    '30': 'rajasthan',
    '31': 'rajasthan',
    '32': 'rajasthan',
    '33': 'rajasthan',
    '34': 'rajasthan',
    '36': 'gujarat',
    '37': 'gujarat',
    '38': 'gujarat',
    '39': 'gujarat',
    '40': 'maharashtra',
    '41': 'maharashtra',
    '42': 'maharashtra',
    '43': 'maharashtra',
    '44': 'maharashtra',
    '45': 'madhya pradesh',
    '46': 'madhya pradesh',
    '47': 'madhya pradesh',
    '48': 'madhya pradesh',
    '49': 'chhattisgarh',
    '50': 'telangana',
    '51': 'andhra pradesh',
    '52': 'andhra pradesh',
    '53': 'andhra pradesh',
    '56': 'karnataka',
    '57': 'karnataka',
    '58': 'karnataka',
    '59': 'karnataka',
    '60': 'tamil nadu',
    '61': 'tamil nadu',
    '62': 'tamil nadu',
    '63': 'tamil nadu',
    '64': 'tamil nadu',
    '67': 'kerala',
    '68': 'kerala',
    '69': 'kerala',
    '70': 'west bengal',
    '71': 'west bengal',
    '72': 'west bengal',
    '73': 'west bengal',
    '74': 'west bengal',
    '75': 'odisha',
    '76': 'odisha',
    '77': 'odisha',
    '78': 'assam',
    '79': 'northeast',
    '80': 'bihar',
    '81': 'bihar',
    '82': 'bihar',
    '83': 'jharkhand',
    '84': 'jharkhand',
    '85': 'bihar',
}

# Common pincode to city mapping (expandable)
PINCODE_TO_CITY = {
    # Mumbai
    '400001': ('mumbai', 'maharashtra', 18.9387, 72.8353),
    '400002': ('mumbai', 'maharashtra', 18.9543, 72.8327),
    # Pune
    '411001': ('pune', 'maharashtra', 18.5167, 73.8563),
    '411002': ('pune', 'maharashtra', 18.5362, 73.8475),
    '411046': ('pune', 'maharashtra', 18.4621, 73.8352),
    '411057': ('pune', 'maharashtra', 18.4897, 73.9256),
    # Delhi
    '110001': ('new delhi', 'delhi', 28.6358, 77.2245),
    '110002': ('delhi', 'delhi', 28.6692, 77.2219),
    # Bangalore
    '560001': ('bangalore', 'karnataka', 12.9791, 77.5913),
    # Chennai
    '600001': ('chennai', 'tamil nadu', 13.0878, 80.2785),
    # Hyderabad
    '500001': ('hyderabad', 'telangana', 17.3841, 78.4564),
    # Kolkata
    '700001': ('kolkata', 'west bengal', 22.5697, 88.3697),
    # Ahmedabad
    '380001': ('ahmedabad', 'gujarat', 23.0258, 72.5873),
}


class PincodeGeocodeService:
    """
    Service to convert pincodes to geographic coordinates.
    """
    
    def __init__(self):
        self.pincode_cache: Dict[str, GeoLocation] = {}
    
    def get_coordinates_by_pincode(self, pincode: str) -> Optional[GeoLocation]:
        """
        Get coordinates for an Indian pincode.
        
        Falls back to:
        1. Known pincode database
        2. State center based on pincode prefix
        """
        if not pincode or len(pincode) != 6:
            return None
        
        # Check cache
        if pincode in self.pincode_cache:
            return self.pincode_cache[pincode]
        
        # Check known pincodes
        if pincode in PINCODE_TO_CITY:
            city, state, lat, lng = PINCODE_TO_CITY[pincode]
            location = GeoLocation(
                latitude=lat,
                longitude=lng,
                city=city.title(),
                state=state.title(),
                pincode=pincode
            )
            self.pincode_cache[pincode] = location
            return location
        
        # Fallback to state center based on prefix
        prefix = pincode[:2]
        state = PINCODE_PREFIX_TO_STATE.get(prefix)
        
        if state and state in STATE_COORDINATES:
            lat, lng = STATE_COORDINATES[state]
            location = GeoLocation(
                latitude=lat,
                longitude=lng,
                state=state.title(),
                pincode=pincode
            )
            self.pincode_cache[pincode] = location
            return location
        
        return None
    
    def get_coordinates_by_city(self, city: str) -> Optional[GeoLocation]:
        """
        Get coordinates for a city name.
        """
        city_lower = city.lower().strip()
        
        if city_lower in MAJOR_CITY_COORDINATES:
            lat, lng = MAJOR_CITY_COORDINATES[city_lower]
            return GeoLocation(
                latitude=lat,
                longitude=lng,
                city=city.title()
            )
        
        return None
    
    def get_coordinates(self, pincode: str = None, city: str = None, state: str = None) -> Optional[GeoLocation]:
        """
        Get coordinates using available information.
        
        Priority: pincode > city > state
        """
        # Try pincode first
        if pincode:
            location = self.get_coordinates_by_pincode(pincode)
            if location:
                return location
        
        # Try city
        if city:
            location = self.get_coordinates_by_city(city)
            if location:
                return location
        
        # Try state
        if state:
            state_lower = state.lower().strip()
            if state_lower in STATE_COORDINATES:
                lat, lng = STATE_COORDINATES[state_lower]
                return GeoLocation(
                    latitude=lat,
                    longitude=lng,
                    state=state.title()
                )
        
        return None
    
    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        """
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


# Singleton instance
geocode_service = PincodeGeocodeService()
