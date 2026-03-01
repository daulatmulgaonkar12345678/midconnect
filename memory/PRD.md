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

#### P0: True SSOT Quotation Architecture - COMPLETE
**Issues Fixed:**
1. Fixed indentation error (QuotationService code was outside function)
2. Removed duplicate quote storage in `inquiries` collection
3. `whatsapp_link` NameError - variable was undefined
4. Manual quote reconstruction in return block

**Implementation:**
- Quote now ONLY stored in `quotes` collection via `QuotationService.create_quote()`
- WhatsApp message ONLY generated via `QuotationService.generate_whatsapp_preview()`
- Inquiry only stores status + reference to quote (no embedded quote data)
- Frontend maps `unitPrice` → `price`, `validityDate` → `validTill`
- No hardcoded fallbacks ("B2B Market Place", "Your Business")

**New 9-Step Flow:**
```
1. Validate price (> ₹0)
2. Governance check (banned/suspended)
3. Subscription check (lead limit)
4. Fetch inquiry
5. Update inquiry status ONLY
6. Create quote via QuotationService
7. Generate WhatsApp preview via QuotationService
8. Build whatsapp_link
9. Return { whatsappLink, quote: quote_result }
```

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
│   ├── seller_products.py           # Seller listing & inquiry management
│   │   └── accept_inquiry()         # SSOT: Uses QuotationService only
│   ├── services/
│   │   └── quotation_service.py     # SSOT for all quotes
│   │       ├── create_quote()       # Creates quote in 'quotes' collection
│   │       └── generate_whatsapp_preview()  # Generates WhatsApp message
│   └── server.py                    # Main FastAPI app
├── frontend/
│   ├── src/app/
│   │   └── seller/inquiries/page.tsx  # Uses whatsappLink from backend
│   └── src/lib/api.ts               # Updated acceptInquiry response type
```

## Database Schema

### quotes Collection (SSOT for all quotes)
```json
{
  "quoteId": "QT-XXXXX",
  "inquiryId": ObjectId,
  "sellerId": ObjectId,
  "buyerId": ObjectId,
  "productId": ObjectId,
  "productName": String,
  "sellerName": String,
  "buyerName": String,
  "unitPrice": Number,
  "moq": Number,
  "totalPrice": Number,
  "leadTimeDays": Number,
  "validityDate": ISODate,
  "status": "sent" | "viewed" | "accepted" | "rejected" | "expired"
}
```

### inquiries Collection (Status + Reference Only)
```json
{
  "status": "pending" | "accepted" | "rejected",
  "quoteId": String,  // Reference to quotes.quoteId
  "acceptedAt": ISODate,
  "updatedAt": ISODate
  // NO embedded quote data (SSOT compliance)
}
```

## Prioritized Backlog

### P0 (Critical)
- [x] Quotation SSOT Fix - Completed 2026-02-27
- [x] Email Verification Blocking I/O Fix - Completed 2026-02-27
- [x] Email Verification Enterprise Fix (Auth Token) - Completed 2026-02-28
- [x] Production API URL Fallback Fix - Completed 2026-02-28
- [x] **RESEND MIGRATION** - Completed 2026-02-28 (Replaced Zoho SMTP)
- [ ] Backend Deployment to Render - Required for all fixes to go live

### P1 (High Priority)
- [x] Custom Email Verification (Resend) - Architecture complete
- [ ] Enterprise Search - Atlas Indexing (Phase 2)
- [ ] Admin & Seller Dashboard audit

### P2 (Medium Priority)
- [ ] Number formatting in product attributes
- [ ] Code linting warnings cleanup
- [ ] Remove obsolete components (EnterpriseSearchBar.tsx, Header.tsx)
- [ ] AI Semantic Search Layer
- [ ] Online Payments for Quotes
- [ ] Counter-Offer System

## Session: 2026-02-28 (Category Visibility Fix)

### Issue Fixed: Category Visibility Inconsistency

**Problem**: Home page showed ALL categories (including empty ones) while categories page only showed categories with active listings. This caused confusion and broken links.

**Root Cause**: 
- Home page (`page.tsx`) was using `getCategories()` → `/api/categories/all` (returns ALL categories)
- Categories page (`categories/page.tsx`) was using `getPublicCategories()` → `/api/categories/public` (filtered by listings)

**Fix Applied**:
1. Updated home page to use `getPublicCategories()` instead of `getCategories()`
2. Added proper empty state messages for when no categories have active listings

**AI Empty State Text Added**:
- **Home page**: "Categories Coming Soon - We're onboarding verified sellers. Product categories will appear here once sellers list their products."
- **Categories page**: "Categories Coming Soon - We're onboarding verified industrial suppliers across India. Categories will appear here once sellers start listing their products. Check back soon!"
- **Category detail page**: "No Products Available Yet - We're actively onboarding sellers in this category. Check back soon or explore other categories with verified supplier listings."

**Files Changed**:
- `/app/frontend/src/app/page.tsx` - Now uses `getPublicCategories()`
- `/app/frontend/src/app/categories/page.tsx` - Updated empty state
- `/app/frontend/src/app/category/[id]/page.tsx` - Updated empty state
- `/app/frontend/src/components/CategoryCard.tsx` - Extended type support

### Major Migration: Zoho SMTP → Resend

**What Changed**:
- Completely replaced Zoho SMTP with Resend email service
- Created centralized email service at `/app/backend/services/email_service.py`
- Removed old `/app/backend/services/email_verification_service.py`

**New Email Service Architecture**:
```
/app/backend/services/email_service.py
├── EmailVerificationService (signup, resend, token verification)
├── SubscriptionEmailService (activated, expiring, expired, upgraded, renewed)
├── InquiryEmailService (buyer confirmation, seller notification, quote received)
└── OrderEmailService (placed, payment, tracking, completed)
```

**Environment Variables Required**:
```
RESEND_API_KEY=re_xxx        # From https://resend.com/api-keys
SENDER_EMAIL=noreply@udyogconnect.in
FRONTEND_URL=https://udyogconnect.in
```

**Security Improvements**:
- Verification tokens are now SHA256 hashed before storage
- Token expiry reduced to 1 hour (from 24 hours)
- Tokens invalidated after successful verification

**Email Notifications Now Implemented**:
1. **On Signup**: Buyer receives verification email
2. **On Inquiry Create**: 
   - Buyer receives confirmation email
   - Seller receives new inquiry notification
3. **On Quote Created**: Buyer receives quote notification with pricing details

**MOCK Mode**:
- If `RESEND_API_KEY` is not set, emails are logged but not sent
- Verification links are logged for testing purposes

**Files Changed**:
- `/app/backend/services/email_service.py` (NEW - centralized email service)
- `/app/backend/server.py` (updated email endpoints, removed OTP SMTP code)
- `/app/backend/routers/quotation_router.py` (added email on quote creation)
- `/app/frontend/src/lib/api.ts` (updated comments)
- `/app/frontend/src/context/AuthContext.tsx` (updated comments)

## Session: 2026-02-27 (Email Verification - Enterprise Fix)

### Issue Fixed: Email Verification Loop + 400 Resend Error

**Root Causes Identified**:
1. **Mixed Verification Sources**: System was mixing Firebase `email_verified` with MongoDB `isEmailVerified`, causing confusion
2. **Resend Required Body**: `/api/resend-verification` required email in request body but should use auth token
3. **Firebase Blocking Access**: Backend was using Firebase `email_verified` to block access, should use MongoDB SSOT

**Enterprise Architecture Fix**:

```
Firebase → Identity Provider ONLY (authentication)
MongoDB → Single Source of Truth for ALL business logic (verification status, profile, etc.)
```

**Changes Made**:

**Backend (`/app/backend/server.py`)**:
1. `get_current_user()`: Removed Firebase `email_verified` sync logic. MongoDB `isEmailVerified` is now SSOT
2. `/api/resend-verification`: Now uses auth token to get user, no body required
3. `/api/auth/complete-profile`: Uses MongoDB `isEmailVerified` instead of Firebase
4. `/api/auth/check-registration`: Returns only MongoDB verification status

**Frontend (`/app/frontend/src/lib/api.ts`)**:
- `resendVerificationEmail()`: Now takes auth token, no email parameter

**Frontend (`/app/frontend/src/context/AuthContext.tsx`)**:
- Updated `resendVerificationEmail` signature - no email param
- Uses auth token from logged-in user

**Frontend (`/app/frontend/src/app/verify-email/page.tsx`)**:
- Updated to call resend without email parameter

**Test Results**:
- `/api/resend-verification` (with auth): 200 OK, sends verification email
- `/api/verify-email`: 200 OK, updates MongoDB `isEmailVerified` to `true`
- `/api/users/me`: Returns correct `isEmailVerified` from MongoDB
- `/api/auth/check-registration`: Returns correct verification status

**Expected Flow**:
1. User registers → stored with `isEmailVerified=false`
2. Verification email sent via Resend (or MOCK if no API key)
3. User clicks link → backend verifies hashed token, sets `isEmailVerified=true`
4. `/users/me` returns verified status
5. Access granted

No Firebase verification used in business logic.

## Email Templates (Branded)
All emails use Udyog Connect branded templates with:
- Blue gradient header (#0B3C5D)
- Clean, professional design
- Support email footer
- Mobile-responsive tables

## Technical Decisions

### SSOT for Quotation Messages
- **Decision**: QuotationService is the ONLY source for quotes and WhatsApp messages
- **Rationale**: 
  - Prevents duplicate/inconsistent messages
  - Single place to update quote format
  - Seller name always from DB lookup
  - No hardcoded business names
- **Implementation**: 
  - `accept_inquiry()` calls `QuotationService.create_quote()`
  - `accept_inquiry()` calls `QuotationService.generate_whatsapp_preview()`
  - Returns `whatsappLink` to frontend
  - Frontend only calls `window.open(whatsappLink)`

### Data Flow (Accept Inquiry)
```
Frontend: Accept Inquiry (click)
    ↓
Backend: accept_inquiry()
    ↓
    ├── Price Validation (> ₹0)
    ├── Governance Check
    ├── Subscription Check
    ├── Update Inquiry Status ONLY
    ├── QuotationService.create_quote() → quotes collection
    ├── QuotationService.generate_whatsapp_preview()
    └── Return { whatsappLink, quote }
    ↓
Frontend: window.open(whatsappLink)
```

## Deployment Notes
- Frontend: Vercel (auto-deploy)
- Backend: Render (manual deploy required)
- Database: MongoDB Atlas
- **CRITICAL**: Backend changes require manual Render deployment

## Post-Deployment Verification Checklist
- [ ] Accept inquiry twice - confirm identical WhatsApp message
- [ ] Verify seller name from DB (never hardcoded)
- [ ] Verify no ₹0 quotes possible
- [ ] Verify quote only in `quotes` collection (not in `inquiries.quote`)

---

## Session: 2026-03-01

### TASK 1: Fix Smart Search Fuzzy Error - COMPLETE

**Issue**: `Fuzzy match error: not enough values to unpack (expected 3, got 2)`

**Root Cause**: The `fuzzywuzzy` library's `process.extractOne()` returns 2-value tuples `(match, score)` in some versions, but code expected 3-value tuples `(match, score, index)`.

**Fixes Implemented**:
1. **Safe tuple unpacking** in `find_fuzzy_match()` (lines 147-162):
   - Changed from `match, score, _ = result` to safe index access `match = result[0]; score = result[1]`
   - Added defensive try/except with proper logging

2. **Cache optimization** via singleton pattern:
   - Added `_cache_initialized` and `_cache_loading` flags to prevent redundant loads
   - Created `initialize_smart_search_cache()` for startup pre-warming
   - Cache now logs only once at startup: "SmartSearch cache initialized: X products, Y categories"

3. **Server startup integration**:
   - Added background task in `startup_db_client()` to pre-warm cache at server start
   - 2-second delay to ensure DB connection is ready

**Files Modified**:
- `/app/backend/services/smart_search_service.py` - Singleton pattern + safe unpacking
- `/app/backend/server.py` - Startup cache initialization

**Verification**:
- `curl /api/search/autocomplete?q=glows` → returns `"didYouMean": "gloves"` ✅
- `curl /api/search/autocomplete?q=moter` → returns `"didYouMean": "motor"` ✅
- Backend logs show cache loaded only once per restart ✅

---

### TASK 2: Implement Seller Badge System - COMPLETE

**Feature**: Admin can assign badges (UdyogConnect Choice, UdyogConnect Trusted) to sellers. Badges appear on product cards across the site.

**Badge Types**:
- `none` - No badge (default)
- `choice` - UdyogConnect Choice (yellow star badge)
- `trusted` - UdyogConnect Trusted (green shield badge)

**Backend Implementation**:
1. **User Model Extension**: Added `badgeType` field with enum validation
2. **Admin Badge Update API**: `PUT /api/admin/sellers/{seller_id}/badge`
   - Validates badge type
   - Requires admin role
   - Logs badge updates for audit
3. **Admin Sellers List API**: `GET /api/admin/sellers`
   - Returns sellers with `badgeType` field
   - Supports filtering by badge type
4. **Product APIs Updated**: 
   - `get_product_with_sellers()` now includes `badgeType` in seller data
   - Search aggregation pipelines include `badgeType` via `$ifNull`

**Frontend Implementation**:
1. **Admin Sellers Page** (`/app/frontend/src/app/admin/sellers/page.tsx`):
   - Lists all sellers with current badge status
   - Dropdown to change badge type
   - Real-time UI updates on change
2. **ProductCard Component** (`/app/frontend/src/components/ProductCard.tsx`):
   - `SellerBadgeDisplay` component for Choice/Trusted badges
   - Badges display above seller type badges
3. **Product Detail Page** (`/app/frontend/src/app/product/[slug]/page.tsx`):
   - `UdyogConnectBadge` component on seller cards
   - Displays above seller name/role

**TypeScript Types Updated**:
- `/app/frontend/src/types/index.ts` - Added `badgeType` to `Seller` interface
- `/app/frontend/src/lib/api.ts` - Added `badgeType` to `EnterpriseProductSeller`

**Testing Results** (13/13 passed):
- Fuzzy search typo correction working ✅
- Badge CRUD APIs functional ✅
- Cache singleton verified ✅

---

## Pending Tasks (Priority Order)

### P0: Deploy Backend to Render
**CRITICAL**: User's production site is running outdated backend code. Recent fixes won't be live until redeployed.

### P1: Enterprise Search Atlas Indexing (Phase 2)
Create and deploy the `enterprise_search_v2` MongoDB Atlas Search index.

### P1: Complete Admin & Seller Dashboard Audit
Full audit of all remaining UI scaffolds in `/app/frontend/src/app/admin/` and `/app/frontend/src/app/seller/`.

### P2: Subscription-based Automated Emails
Implement emails for subscription lifecycle (activated, expiring, expired).

### Future/Backlog
- AI Semantic Search Layer (vector embeddings)
- Online Payments for Quotes
- Counter-Offer System
- Refactor `api.ts` and `server.py` into smaller modules
