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

## PHASE A STABILIZATION COMPLETE (Feb 25, 2026)

### Security Fixes
- [x] **Migration Endpoint Removed** - Temporary admin endpoint deleted for security

### Search UX Fixes (Latest)
- [x] **Header Dropdown Fixed** - Removed `overflow-hidden` from search bar container to allow dropdowns to render
- [x] **Auto-Search Disabled** - Clicking suggestions now only populates the query, does NOT auto-search. User must click Search button
- [x] **Location Search Improved** - Backend now queries both `activeSellerCities` AND `sellerListings` directly to show all seller locations immediately

### UI/UX Fixes
- [x] **Location Filter Chip Visibility** - Prominent blue chip with X button
- [x] **Search Navigation** - EnterpriseSearchBar redirects to `/search` page

### API Fixes
- [x] **Vercel Fallback** - Added hardcoded fallback for `*.vercel.app` domains to use production backend URL

---

## KEY FIXES SUMMARY

### 1. Header Search Dropdown Not Showing
**Problem**: Dropdowns were cut off by parent container
**Fix**: Removed `overflow-hidden` from search bar container styles

### 2. Auto-Search Without Clicking Button
**Problem**: Clicking a suggestion auto-navigated to search results
**Fix**: Removed auto-search from `handleSuggestionClick` - now only sets query text

### 3. Pune Not Showing in Location Search
**Problem**: Location API only searched `activeSellerCities` collection
**Fix**: Updated `_get_city_suggestions` to ALSO query `sellerListings` directly

---

## IMPLEMENTATION STATUS

### Completed (Feb 25, 2026)
- [x] Header dropdown visibility fix
- [x] Auto-search disabled
- [x] Location search queries seller listings
- [x] Vercel API fallback

### In Progress
- None

### Upcoming Tasks (P0-P1)
1. **Create MongoDB Atlas Search index** (`enterprise_search_v2`)
2. **Geo-search & Fallback** - Nearby location suggestions
3. **Admin & Seller Dashboards**

### Future Tasks (P2+)
1. AI Semantic Search Layer
2. Online Payments (Stripe/Razorpay)
3. Counter-Offer System

---

## KEY FILES REFERENCE

### Recently Modified
- `/app/frontend/src/components/Header.tsx` - Added overflow-visible
- `/app/frontend/src/components/EnterpriseSearchBar.tsx` - Removed auto-search, removed overflow-hidden
- `/app/backend/services/seller_location_service.py` - Query seller listings for locations
- `/app/frontend/src/lib/api.ts` - Vercel API fallback

### Key API Endpoints
- `GET /api/search?q={query}` - Enterprise search
- `GET /api/search/autocomplete?q={query}` - Product suggestions
- `GET /api/search/locations/active` - Cities with sellers
- `GET /api/search/locations?q={query}` - Location autocomplete

---

## 3RD PARTY INTEGRATIONS
- Firebase (Authentication)
- MongoDB (Database)

---

## TEST STATUS
- Header dropdown: ✅ Working
- Location dropdown: ✅ Working
- Auto-search disabled: ✅ Confirmed
- TypeScript: ✅ Compiles
