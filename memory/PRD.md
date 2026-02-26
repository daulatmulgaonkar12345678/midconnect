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

## INDUSTRIAL HEADER REDESIGN COMPLETE (Feb 26, 2026)

### Design Specifications
- **Color Palette**: Deep Blue (#0B3C5D), Light Grey (#F5F6F7), Border Grey (#E5E7EB)
- **Typography**: Inter font (professional, corporate look)
- **Style**: Industrial B2B, enterprise-grade, no gradients/shadows/flashy elements

### 2-Layer Header Structure

#### Layer 1: Corporate Utility Header (60px height)
- **Left**: Logo + "B2B Marketplace" badge
- **Right**: 
  - My Inquiries (for buyers, with count badge)
  - Seller Dashboard (for sellers)
  - Admin Panel (for admins)
  - Login / Register buttons

#### Layer 2: Search Engine Header (56px height, Sticky)
- **Location Dropdown**: "All India" default, shows cities with seller counts
- **Category Dropdown**: All categories from database
- **Search Input**: Full-width, placeholder "Search industrial products, brands, specifications..."
- **Search Button**: Deep blue with white icon

### Mobile Behavior
- Full-screen mobile menu when hamburger clicked
- Location + Category + Search input stacked vertically
- Navigation links below search
- Search always accessible (never hidden)

### Backend Integration
- **Buyer Inquiries**: Fetches count from `/api/inquiries/buyer`
- **Categories**: Fetches from `/api/categories` (limit 10)
- **Locations**: Fetches from `/api/search/locations/active`

---

## GEO SEARCH IMPLEMENTATION (Feb 26, 2026)

### Schema
- `coordinates`: GeoJSON Point `[lng, lat]`
- `pincode`: String
- `minPrice`: Number (computed from MIN of all pricing tiers)
- `inStock`: Boolean

### 2dsphere Index
- Created on `coordinates` field for radius queries

### Fallback Strategy
1. City exact match → 
2. Radius 50km (if coords provided) →
3. State → 
4. Pan India

### API Endpoint
```
GET /api/search/geo
Returns: fallbackUsed, message, listings
```

---

## KEY FILES

### Frontend
- `/app/frontend/src/components/IndustrialHeader.tsx` - New enterprise header
- `/app/frontend/src/app/layout.tsx` - Uses IndustrialHeader
- `/app/frontend/src/app/search/page.tsx` - Geo search results

### Backend
- `/app/backend/services/enterprise_search_service.py` - Geo search with fallback
- `/app/backend/routers/enterprise_search_router.py` - `/search/geo` endpoint
- `/app/backend/seller_products.py` - Coordinates on listing creation

---

## 3RD PARTY INTEGRATIONS
- Firebase (Authentication)
- MongoDB (Database with 2dsphere indexing)

---

## NEXT TASKS
- **P1**: Add product autocomplete to header search input
- **P1**: Create buyer inquiries page (`/buyer/inquiries`)
- **P2**: Add "Near Me" geolocation button
