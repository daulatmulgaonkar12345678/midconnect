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

## HEADER SEARCH AUTOCOMPLETE COMPLETE (Feb 26, 2026)

### Product Autocomplete Added
- Debounced search (300ms) triggers after 2+ characters
- Shows product names with category context ("in Electric Motors")
- Shows "Popular" badge for trending searches
- Works on both desktop and mobile layouts

### API Integration
- **Product autocomplete**: `GET /api/search/autocomplete?q={query}&limit=8`
- **Location suggestions**: `GET /api/search/locations/active?limit=8`
- **Categories**: `GET /api/categories`

### Database Connection
- **Preview environment**: `midconnect` database (local)
- **Vercel deployment**: Your MongoDB Atlas `b2b_marketplace` database
- Data shown depends on which database the environment is connected to

---

## INDUSTRIAL HEADER STRUCTURE

### Layer 1 - Corporate Utility (60px)
- Logo + "B2B Marketplace" badge
- **Products** link (for all users) - NEW
- **Categories** link (for all users) - NEW
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
- `/app/frontend/src/components/IndustrialHeader.tsx` - Full header with autocomplete
- `/app/frontend/src/app/inquiries/page.tsx` - Buyer inquiries page
- `/app/frontend/src/app/search/page.tsx` - Geo search results

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
- ✅ Products and Categories navigation links visible for all users (Feb 26, 2026)

## NEXT TASKS
- **P0**: Verify header changes on Vercel deployment
- **P1**: Complete Admin & Seller Dashboard Integration
- **P2**: Add inquiry submission from product page
- **P2**: Fix number formatting in product attributes (Pydantic validation)
- **P2**: Cleanup linting warnings
