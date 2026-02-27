# MidConnect B2B Marketplace - Product Requirements Document

## Original Problem Statement
Build an enterprise-grade B2B marketplace platform ("midconnect") that connects industrial buyers with verified sellers. The platform enables:
- Product catalog management with technical specifications
- Buyer inquiry system with seller quotation workflow
- WhatsApp-based communication for quote delivery
- Subscription-based seller access control

## Core Requirements
1. **Multi-layer product architecture**: Category → SpecTemplate → Product → ProductVariant → SellerListing
2. **Buyer-seller inquiry flow**: Buyers submit RFQs, sellers accept/reject with quotes
3. **Contact masking**: Buyer details hidden until inquiry accepted
4. **Subscription limits**: Free tier has lead limits, paid plans for unlimited

## What's Been Implemented

### Session: 2026-02-27

#### P0: Quotation SSOT Fix - COMPLETE
- **Issue**: Duplicate WhatsApp message builders in frontend AND backend causing inconsistent messages
- **Fix**: 
  - Removed 45-line frontend message builder from `seller/inquiries/page.tsx`
  - Backend `accept_inquiry` now generates message and returns `whatsappLink`
  - Frontend only opens the returned link
  - Removed hardcoded "Your Business" / "B2B Market Seller" fallbacks
  - Added price validation to prevent ₹0 quotes
  - Seller name now comes from DB profile only

#### Previous Fixes (Local - Pending Deployment)
- Admin Panel "N/A" Product Name fix
- Public Data Visibility fix (flexible aggregation)
- CORS Policy fix for `udyogconnect.in`
- Cold Start Prevention (BackendWarmup + GitHub Actions ping)
- Timezone Display fix

### Architecture
```
/app/
├── backend/
│   ├── seller_products.py      # Seller listing & inquiry management (SSOT for quotes)
│   ├── services/
│   │   └── quotation_service.py # Full quote lifecycle (create_quote, generate_whatsapp_preview)
│   └── server.py               # Main FastAPI app, CORS, admin routes
├── frontend/
│   ├── src/app/
│   │   ├── admin/              # Admin dashboard pages
│   │   └── seller/
│   │       └── inquiries/page.tsx  # Seller inquiry management (uses backend whatsappLink)
│   └── src/types/index.ts      # TypeScript interfaces (SellerInquiry with whatsappLink)
```

## Prioritized Backlog

### P0 (Critical)
- [x] Quotation SSOT Fix - Completed 2026-02-27
- [ ] Backend Deployment to Render - Required for all fixes to go live

### P1 (High Priority)
- [ ] Enterprise Search - Atlas Indexing (Phase 2)
- [ ] Admin & Seller Dashboard audit

### P2 (Medium Priority)
- [ ] Number formatting in product attributes
- [ ] Code linting warnings cleanup
- [ ] Remove obsolete components (EnterpriseSearchBar.tsx, Header.tsx)
- [ ] AI Semantic Search Layer
- [ ] Online Payments for Quotes
- [ ] Counter-Offer System

## Technical Decisions

### SSOT for Quotation Messages
- **Decision**: Backend is the single source of truth for WhatsApp quotation messages
- **Rationale**: Prevents duplicate/inconsistent messages, ensures seller name always from DB
- **Implementation**: `accept_inquiry()` returns `whatsappLink`, frontend just opens it

### Data Flow
```
Frontend: Accept Inquiry (click)
    ↓
Backend: accept_inquiry()
    ↓
    ├── Price Validation (> ₹0)
    ├── DB Lookups (seller, buyer, product)
    ├── Generate WhatsApp Message
    └── Return { whatsappLink: "..." }
    ↓
Frontend: window.open(whatsappLink)
```

## Deployment Notes
- Frontend: Vercel (auto-deploy)
- Backend: Render (manual deploy required)
- Database: MongoDB Atlas
- **CRITICAL**: Backend changes require manual Render deployment
