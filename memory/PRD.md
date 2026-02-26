# MidConnect - B2B Marketplace PRD

## Product Overview
MidConnect is a B2B marketplace platform for industrial products connecting verified manufacturers, dealers, and distributors with buyers across India.

## Core Architecture

### Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB (via Motor async driver)
- **Auth**: Firebase Authentication

---

## GEO SEARCH IMPLEMENTATION COMPLETE (Feb 26, 2026)

### Phase 1: Schema Upgrade ✅
- Added `coordinates` (GeoJSON Point) to sellerListings
- Added `pincode` field from seller profile
- Fixed `minPrice` computation: now uses MIN of all pricing tiers (not first tier)
- All existing listings updated with coordinates

### Phase 2: 2dsphere Index ✅
- Created `coordinates_2dsphere` index on sellerListings
- Enables $geoNear queries and radius-based search

### Phase 3: Listing Creation Updated ✅
- Auto-populates coordinates from seller city using geocode service
- Uses pre-stored coordinates from seller profile if available
- Falls back to city lookup for geocoding

### Phase 4: Enterprise Geo Search with Fallback ✅
New endpoint: `GET /api/search/geo`

**Fallback Strategy (M0 Compatible):**
1. City exact match → 
2. Radius search (50km default, if coords provided) →
3. State → 
4. Pan India

**Returns:**
- `fallbackUsed`: "radius" | "state" | "pan_india" | null
- `message`: User-friendly fallback message
- `searchedLocation`: Original search parameters

### Phase 5: Frontend Integration ✅
- New `geoSearchProducts()` API function
- Search page uses geo search by default
- Displays fallback message when search expands area
- Shows "No sellers in [location]. Showing sellers from across India."

---

## KEY FILES MODIFIED

### Backend
- `/app/backend/seller_products.py` - Listing creation with coordinates
- `/app/backend/services/enterprise_search_service.py` - Added `geo_search()` method
- `/app/backend/routers/enterprise_search_router.py` - Added `/search/geo` endpoint

### Frontend
- `/app/frontend/src/lib/api.ts` - Added `geoSearchProducts()` function
- `/app/frontend/src/app/search/page.tsx` - Uses geo search, shows fallback message

### Database
- Created `coordinates_2dsphere` index on sellerListings
- All listings have `coordinates` field populated

---

## API ENDPOINTS

### Geo Search
```
GET /api/search/geo
Parameters:
  - q: Search query (optional)
  - city: City filter
  - state: State filter
  - lat: User latitude (for radius search)
  - lng: User longitude (for radius search)
  - radiusKm: Search radius (default: 50)
  - category: Category ID
  - minPrice, maxPrice: Price filters
  - inStock: Stock filter
  - limit, skip: Pagination

Response:
{
  "listings": [...],
  "total": 2,
  "fallbackUsed": "pan_india",
  "message": "No sellers in Pune. Showing sellers from across India.",
  "searchedLocation": {...}
}
```

---

## SELLER LISTINGS SCHEMA (Updated)

```json
{
  "_id": ObjectId,
  "productId": ObjectId,
  "sellerId": ObjectId,
  "city": "Delhi",
  "state": "Delhi",
  "pincode": "110001",
  "coordinates": {
    "type": "Point",
    "coordinates": [77.1025, 28.7041]  // [lng, lat]
  },
  "minPrice": 500,
  "inStock": true,
  "searchableText": "...",
  "searchableAttributes": {...}
}
```

---

## UPCOMING TASKS

### P1: Near Me Feature
- Add browser geolocation API to frontend
- "Use My Location" button in location dropdown
- Auto-detect user location for radius search

### P2: Atlas Search Index (When upgrading from M0)
- Create enterprise_search_v2 with geo mappings
- Enable Atlas Search geo operators (geoWithin, near)

### P3: Distance Display
- Show "X km away" on product cards when using radius search

---

## 3RD PARTY INTEGRATIONS
- Firebase (Authentication)
- MongoDB (Database with 2dsphere indexing)

---

## TEST STATUS
- Geo search API: ✅ Working
- Fallback strategy: ✅ Working (City → Radius → State → Pan India)
- 2dsphere index: ✅ Created
- Frontend integration: ✅ Complete
