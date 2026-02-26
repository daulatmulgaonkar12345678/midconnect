# MidConnect - B2B Marketplace PRD

## Product Overview
MidConnect is a B2B marketplace platform for industrial products connecting verified manufacturers, dealers, and distributors with buyers across India.

## Core Architecture

### Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS, Inter Font
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB (via Motor async driver) with 2dsphere geo indexing
- **Auth**: Firebase Authentication

---

## SMART SEARCH ENGINE (Feb 26, 2026)

### Features Implemented
- **Typo Tolerance**: Automatically corrects common typos (moter → motor)
- **Phonetic Matching**: India-friendly sound-based matching (motar → motor)
- **"Did you mean?" Suggestions**: Shows clickable suggestions when no results
- **Auto-correction**: Searches with corrected query when original returns no results
- **Smart Autocomplete**: Fuzzy matching in autocomplete dropdown

### Technical Implementation
- `SmartSearchService` in `/app/backend/services/smart_search_service.py`
- Uses `fuzzywuzzy` for fuzzy string matching
- Uses `metaphone` for phonetic matching (Double Metaphone algorithm)
- Product/category name caching for performance (5-min TTL)
- Known typo dictionary for common Indian English typos

### API Endpoints
- `GET /api/search/spelling?q={query}` - Check spelling and get suggestions
- `GET /api/search/autocomplete?q={query}` - Smart autocomplete with fuzzy matching
- `GET /api/search?q={query}` - Main search with "didYouMean" field
- `GET /api/search/geo?q={query}` - Geo search with typo tolerance

### Performance (M0 Optimized)
- Fuzzy logic runs only when results are empty
- Product names cached in memory (not queried every request)
- Suggestions limited to prevent timeout
- No Atlas Search index required (uses regex + in-memory matching)

---

## LOCATION DROPDOWN FIX & SMART SEARCH (Feb 26, 2026)

### Bug Fixes
- Fixed event listener cleanup (consistent `pointerdown` events for mobile reliability)
- Fixed premature dropdown closing with `onMouseDown` + `e.preventDefault()`
- Fixed location selection normalization (ensures city/state always exist)

### Smart Location Search Features
- **Search by**: City, State, or Pincode (6-digit)
- **Type indicators**: 📍 City, 🗺️ State, 📮 Pincode
- **Search priority**: pincode > city > state (sent to backend)
- **Seller counts**: Shows number of sellers in each location

### Backend Support (Already Exists)
- `/api/search/locations?q=` - Full location autocomplete
- `/api/search/locations/active` - Cities with active sellers
- `/api/search/locations/check` - Check seller availability
- Supports city, state, pincode parameters in search API

---

## CENTRALIZED API CLIENT REFACTOR (Feb 26, 2026)

### Changes Made
All frontend API calls now use the centralized API client (`/lib/api.ts`) instead of direct `fetch()` calls.

#### Removed
- `getApiBaseUrl()` function from all components
- Direct `NEXT_PUBLIC_BACKEND_URL` usage
- Manual `/api/` prefix handling

#### Added to lib/api.ts
- `getAutocompleteSuggestions(query)` - Product autocomplete
- `getLocationSuggestions(query?)` - Location dropdown data  
- `getPublicCategoriesList()` - Categories dropdown data

### Updated Components
- `IndustrialHeader.tsx` - Uses centralized API helpers
- `EnterpriseSearchBar.tsx` - Uses centralized API helpers
- `inquiries/page.tsx` - Uses `getBuyerInquiries()`

### Environment Variable
- Uses `NEXT_PUBLIC_API_URL` (primary)
- Fallback to `NEXT_PUBLIC_BACKEND_URL` for backwards compatibility

### Benefits
- ✅ Consistent API configuration
- ✅ Cold start retry logic
- ✅ Timeout handling
- ✅ Works in both local and production

---

## INDUSTRIAL HEADER STRUCTURE

### Layer 1 - Corporate Utility (60px)
- Logo + "B2B Marketplace" badge
- **Products** link (for all users)
- **Categories** link (for all users)
- Dashboard (sellers only)
- Admin (admins only)
- **Inquiries** link (for all users)
- Login + Register

### Layer 2 - Search Engine (56px, Sticky)
- **Location Dropdown**: All India → cities with seller counts
- **Category Dropdown**: All Categories from database
- **Search Input**: With product autocomplete (debounced)
- **Search Button**: Deep blue

### Responsive Behavior
- **Desktop (≥768px)**: Horizontal layout
- **Mobile (<768px)**: Stacked layout, both layers always visible

---

## KEY FILES

### Frontend
- `/app/frontend/src/lib/api.ts` - Centralized API client (SSOT)
- `/app/frontend/src/components/IndustrialHeader.tsx` - Main header
- `/app/frontend/src/components/EnterpriseSearchBar.tsx` - Reusable search bar
- `/app/frontend/src/app/inquiries/page.tsx` - Buyer inquiries page

### Backend
- `/app/backend/services/enterprise_search_service.py` - Geo search with fallback
- `/app/backend/routers/enterprise_search_router.py` - Search endpoints

---

## 3RD PARTY INTEGRATIONS
- Firebase (Authentication)
- MongoDB (Database with 2dsphere indexing)

---

## VERIFIED WORKING
- ✅ Product autocomplete in header (desktop + mobile)
- ✅ Location dropdown shows cities from database
- ✅ Category dropdown loads from database
- ✅ Both headers visible on all screen sizes
- ✅ Inquiries link visible for all users
- ✅ Products and Categories navigation links visible for all users
- ✅ Centralized API client for all search/dropdown calls
- ✅ Location dropdown click fixed (single-click selection)
- ✅ Smart location search with city/state/pincode support
- ✅ Location type indicators (📍📮🗺️) in dropdown
- ✅ **Smart Search Engine** - Typo tolerance (moter → motor)
- ✅ **"Did you mean?"** suggestions on search page
- ✅ **Phonetic matching** - India-friendly (motar → motor)
- ✅ **Auto-correction** - Searches with corrected query when no results

## NEXT TASKS
- **P0**: Verify changes on Vercel deployment
- **P1**: Complete Admin & Seller Dashboard Integration
- **P2**: Add inquiry submission from product page
- **P2**: Fix number formatting in product attributes (Pydantic validation)
- **P2**: Cleanup remaining ESLint warnings
