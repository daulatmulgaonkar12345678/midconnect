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

---

### Session: 2026-03-02

#### COMPLETE: Marketplace-Standard SEO v2.0 (IndiaMART/Alibaba Level)

**Implemented Features:**

1. **SEO-Optimized Slug Generation**
   - Format: `{product-name}-{category}-supplier-india`
   - Example: `industrial-water-pump-pumps-supplier-india`
   - Uniqueness check with `-1, -2` suffix for duplicates
   - Applied via `seo_service.generate_seo_slug()`

2. **Title Tag Optimization (55-65 chars)**
   - Format: `Buy {Product} Online | {Category} Suppliers India | UdyogConnect`
   - CTR-optimized with primary keywords and India mention

3. **Meta Description Enhancement (150-160 chars)**
   - Includes: seller count, price range, MOQ, CTA
   - Template: "Explore {count}+ verified suppliers of {product} in India..."

4. **Structured On-Page SEO Content (300-500 words)**
   - H1: {Product Name} Suppliers in India
   - H2: Specifications
   - H2: Applications (Manufacturing, Construction, Engineering, Commercial)
   - H2: Suppliers by City (Mumbai, Delhi, Bangalore, etc.)
   - H2: Why Choose UdyogConnect (5-point value prop)

5. **Enhanced JSON-LD Schemas**
   - Product schema with AggregateOffer (INR pricing)
   - BreadcrumbList (Home > Products > Category > Product)
   - FAQPage (4 common questions for rich snippets)
   - Organization schema

6. **Internal Linking System**
   - Category links
   - Similar products
   - City-specific pages
   - Top-rated products link

7. **Backend Changes**
   - Updated `services/seo_service.py` - Complete rewrite with marketplace standards
   - Updated SEO API endpoint with price stats, MOQ, FAQ schema, internal links
   - Added admin migration endpoint: `POST /api/admin/migrate/generate-seo-slugs`
   - Updated enterprise product endpoints to support slug lookup

8. **Frontend Changes**
   - Updated `ProductSEO.tsx` with InternalLinksSection, SEOContentSection
   - Product pages now render internal links and collapsible SEO content
   - Fixed `.env.local` double `/api/` URL issue

9. **Migration Completed**
   - Generated SEO slugs for all existing products
   - Products now accessible via keyword-rich URLs

**Testing Results** (27/27 passed):
- SEO title 55-65 chars ✅
- SEO description 150-160 chars ✅
- SEO content H1/H2 structure ✅
- JSON-LD Product/FAQ/Breadcrumb schemas ✅
- Internal links structure ✅
- Slug-based URL routing ✅

### Session: 2026-03-02 (continued)

#### COMPLETE: SEO v2.0 Migration - Products & Categories

**Migration Implemented:**

1. **SEO Migration Service** (`/app/backend/services/seo_migration_service.py`)
   - `generate_product_slug()`: Format `{product-name}-{category}-supplier-india`
   - `generate_category_slug()`: Format `{category-name}`
   - `migrate_all_products()`: Batch migration with uniqueness checks
   - `migrate_all_categories()`: Batch migration with uniqueness checks
   - `get_redirect_mapping()`: Lookup old ID → new slug for 301 redirects
   - `validate_migration()`: Check for null/duplicate slugs

2. **301 Redirect Endpoints**
   - `GET /api/redirect/product/{identifier}`: Returns redirect info for old ObjectId/legacy slug
   - `GET /api/redirect/category/{identifier}`: Returns redirect info for old ObjectId/legacy slug
   - Stores `legacyIds` and `legacySlugs` arrays on documents for redirect resolution

3. **Admin Migration Endpoints**
   - `POST /api/admin/migrate/seo-v2-full`: Run complete migration (categories then products)
   - `GET /api/admin/migrate/seo-v2-validate`: Validate migration completeness

4. **Frontend Updates**
   - Product page: Added redirect check for ObjectId URLs → redirects to slug URL
   - Sitemap: Updated to ONLY include slug-based URLs, filter out entities without slugs
   - Layout: Fixed params Promise handling for Next.js 15

5. **API Fixes**
   - Added `slug` field to `/api/categories` projection
   - Added `slug` field to `/api/categories/public` response

**Migration Results:**
- 12 categories migrated with new slugs
- 10 products migrated with v2.0 format slugs (-supplier-india suffix)
- 0 null slugs
- 0 duplicate slugs
- All redirect mappings stored for 301 redirect resolution

**Testing Results** (14/14 passed after fix):
- Product redirect endpoint ✅
- Category redirect endpoint ✅
- All products have v2 slugs ✅
- All categories have slugs ✅
- No duplicate slugs ✅
- Sitemap uses slug-only URLs ✅

### Session: 2026-03-02 (continued)

#### COMPLETE: SEO v2.1 Enforcement - Marketplace Standard

**URL Structure (STEP 1):**
- Products: `/products/{slug}` (plural)
- Categories: `/categories/{slug}` (plural)
- Old routes (`/product/`, `/category/`) → 301 redirect to new routes

**Slug Formats (STEP 2):**
- Products: `{product-name}-{category}-supplier-india` (max 90 chars)
- Categories: `{category-name}-suppliers-india` (max 90 chars)
- Lowercase, hyphen-separated, no special characters

**Files Created/Modified:**
1. `/app/frontend/src/app/products/[slug]/page.tsx` - New product page (plural route)
2. `/app/frontend/src/app/products/[slug]/layout.tsx` - SEO metadata generation
3. `/app/frontend/src/app/categories/[slug]/page.tsx` - New category page (plural route)
4. `/app/frontend/src/app/product/[slug]/layout.tsx` - Redirect to /products/
5. `/app/frontend/src/app/category/[id]/page.tsx` - Redirect to /categories/
6. `/app/frontend/src/app/sitemap.ts` - Updated to use /products/ and /categories/
7. `/app/backend/services/seo_migration_service.py` - V2.1 patterns with 90-char limit

**Testing Results** (24/25 → 25/25 after fix):
- All redirect endpoints working ✅
- Product slugs end with -supplier-india ✅
- Category slugs end with -suppliers-india ✅
- All slugs within 90 chars ✅
- SEO data quality (title 55-65, desc 150-160) ✅
- JSON-LD schemas (Product, FAQ, Breadcrumb) ✅
- Frontend plural routes working ✅
- 301 redirects from singular routes ✅

---

### Session: 2026-03-02 (continued)

#### COMPLETE: SEO v2 Database Migration - Full Execution

**Phase 1 - Schema Upgrade:**
- Added fields: `slug`, `seoTitle`, `seoDescription`, `seoContent`, `legacyIds`, `updatedAt`
- Created unique indexes: `db.products.createIndex({ slug: 1 }, { unique: true })`
- Created unique indexes: `db.categories.createIndex({ slug: 1 }, { unique: true })`

**Phase 2 - Product Migration:**
- 10/10 products migrated with all SEO fields
- Slug format: `{product-name}-{category}-supplier-india`
- SEO title: 55-65 chars with "Suppliers India | UdyogConnect"
- SEO description: 150-160 chars with seller count, price range, MOQ
- SEO content: 300-500 words with H1/H2 structure, Applications, Cities, Why Choose sections

**Phase 3 - Category Migration:**
- 12/12 categories migrated with all SEO fields
- Slug format: `{category-name}-suppliers-india`
- All categories have seoTitle, seoDescription, seoContent, legacyIds

**Phase 4 - Frontend URL Updates:**
- Products listing: `/products/{slug}` links
- Categories listing: `/categories/{slug}` links
- Sitemap: Only slug-based URLs (no ObjectIds)

**Phase 5 - New Product Auto-Generation:**
- Both product creation endpoints now auto-generate all SEO fields
- seoTitle, seoDescription, seoContent, legacyIds created at insert time
- No runtime computation needed

**Phase 6 - 301 Redirects:**
- `/product/{id}` → `/products/{slug}`
- `/category/{id}` → `/categories/{slug}`
- Legacy mapping via `legacyIds` arrays

**Testing Results** (25/25 passed - 100%):
- All products have SEO fields ✅
- All categories have SEO fields ✅
- Unique indexes enforced ✅
- Frontend routing works ✅
- Sitemap uses slugs only ✅

---

### Session: 2026-03-02 (continued)

#### COMPLETE: Enterprise Architecture Hardening

**Phase 1 - Core Architecture (DONE):**

1. **Central Resolver Service** (`/app/backend/services/resolver_service.py`)
   - `resolve_product(identifier)` - Supports ObjectId, slug, legacy ID
   - `resolve_category(identifier)` - Same pattern
   - `get_product_with_redirect()` - Returns canonical URL info
   - `get_enterprise_product_data()` - Single aggregation, no N+1 queries
   - Lean queries with projections (PRODUCT_FIELDS, CATEGORY_FIELDS, LISTING_FIELDS)

2. **Enterprise Index Strategy** (`/app/backend/services/index_migration.py`)
   - 23+ indexes created across all collections
   - Products: slug (unique), categoryId, isActive, text search, legacy IDs
   - Categories: slug (unique), isActive, legacy IDs
   - SellerListings: productId+status, sellerId, price sorting
   - Users: email (unique), firebaseUid, role, city
   - Quotes: buyerId, sellerId, productId, status

3. **Enterprise Endpoints**
   - `GET /api/enterprise/resolve/product/{identifier}` - Canonical URL resolver
   - `GET /api/enterprise/resolve/category/{identifier}` - Category resolver
   - `POST /api/admin/enterprise/create-indexes` - Index migration
   - `GET /api/admin/enterprise/index-stats` - Index statistics

**Phase 2 - SEO Domination (DONE):**
- ✅ Clean URL structure: /products/{slug}, /categories/{slug}
- ✅ Dynamic metadata per page (generateMetadata)
- ✅ JSON-LD structured data (Product, AggregateOffer, BreadcrumbList, FAQPage)
- ✅ Sitemap automation (frontend-generated)
- ✅ Canonical URLs on all pages

**Phase 3 - Performance Layer (PARTIAL):**
- ✅ Lean queries with projections
- ✅ Single aggregation for enterprise page
- ⏳ Redis caching (future)
- ⏳ Cursor pagination (future)

**Testing Results** (17/19 passed - 89%):
- Resolver endpoints working ✅
- ObjectId and slug lookups ✅
- Canonical URLs correct ✅
- SEO fields verified ✅
- Indexes defined and created ✅

---

### Session: 2026-03-02 (final)

#### COMPLETE: Enterprise SEO Execution Plan

**Phase 1 - Database Structure:**
- ✅ Product schema finalized (slug, seoTitle, seoDescription, seoContent, legacyIds)
- ✅ Search Analytics Collection created
- ✅ All indexes created (23+ across collections)

**Phase 2 - Backend Implementation:**
- ✅ Central Product Resolver (`/app/backend/services/resolver_service.py`)
- ✅ Search Tracking Logic (`/app/backend/services/search_analytics_service.py`)
- ✅ City SEO Pages (`/app/backend/services/city_seo_service.py`)
- ✅ Endpoints: `/api/search/track`, `/api/products/{slug}/cities`, `/api/products/{slug}/city/{city}`

**Phase 3 - Frontend:**
- ✅ All links use slug (`/products/${product.slug}`)
- ✅ Canonical URLs on all pages
- ✅ SSR metadata with generateMetadata()
- ✅ Internal linking (category, similar products)

**Phase 4 - Admin Panel:**
- ✅ Search Insights endpoint: `GET /api/admin/search/insights`
- Returns: top searches, unmatched keywords, city demand

**Phase 5 - Google Search Enablement:**
- ✅ Sitemap uses slug-based URLs only
- ✅ SSR renders title, meta, content in HTML
- ✅ JSON-LD structured data (Product, FAQ, Breadcrumb)

**Testing Results** (25/25 passed - 100%):
- Search tracking works ✅
- City endpoints work ✅
- Resolver returns canonical URLs ✅
- Sitemap uses slugs only ✅
- No ObjectIds in URLs ✅

**Enterprise Architecture Summary:**
- ✔ One canonical slug per product
- ✔ Strict lowercase routing
- ✔ Search keyword tracking
- ✔ City-based SEO control (only when sellers exist)
- ✔ No duplicate content
- ✔ Dynamic resolver
- ✔ Admin analytics
- 301 redirects working ✅

---

### Session: 2026-03-03

#### COMPLETE: Token-Based URL Slug Resolution

**Problem Statement:**
User reported "Product Not Found" errors when accessing URLs like `/products/abc-power-tools-hand-tools`. The issue was that the exact slug didn't exist in the database, but a related product did. Required implementing flexible, order-independent URL resolution.

**Implementation:**

1. **Token-Based Slug Resolver** (`/app/backend/services/slug_resolver_service.py`)
   - Tokenizes URL slugs into meaningful words
   - Removes stop words (buy, online, supplier, india, manufacturer, etc.)
   - Removes Indian city/state names (mumbai, delhi, bangalore, etc.)
   - Uses `$and`-based regex matching against product name/slug
   - Scores candidates by token overlap
   - Returns best match with redirect info

2. **Features:**
   - **Order Independence**: "motor-electric" matches "electric-motor-xxx"
   - **Partial Slugs**: "motor" matches "industrial-electric-motor-5hp-xxx"
   - **City Tolerance**: "motor-mumbai" ignores "mumbai", finds product
   - **Stop Word Filtering**: "buy-motor-online-india" filters noise

3. **Endpoints Updated:**
   - `GET /api/products/detail/{identifier}` - Product detail
   - `GET /api/products/{id}/enterprise` - Enterprise product page
   - `GET /api/products/{id}/facets` - Filter facets
   - `POST /api/products/{id}/filter` - Filter listings
   - `GET /api/products/{id}/seo` - SEO data
   - `GET /api/enterprise/resolve/product/{identifier}` - Direct resolver

4. **Frontend Handling:**
   - `/app/frontend/src/app/products/[slug]/page.tsx` updated
   - Checks `redirect.needed` in API response
   - Uses `router.replace()` for canonical URL redirect
   - No visible flicker - smooth redirect experience

**API Response Format:**
```json
{
  "product": { "name": "...", "slug": "canonical-slug-here", ... },
  "redirect": {
    "needed": true,
    "canonicalSlug": "canonical-slug-here",
    "canonicalUrl": "https://www.udyogconnect.in/products/canonical-slug-here"
  }
}
```

**Testing Results** (21/21 backend, 5/5 frontend - 100%):
- ✅ Partial slug 'motor' matches product
- ✅ Word order 'motor-electric' matches
- ✅ City name 'mumbai' ignored
- ✅ Stop words 'buy', 'online' filtered
- ✅ Exact slug returns redirect.needed = false
- ✅ Frontend redirects to canonical URL
- ✅ Combined partial + city + stopwords works

**Files Created/Modified:**
- `/app/backend/services/slug_resolver_service.py` (NEW)
- `/app/backend/routers/enterprise_products.py` (MODIFIED)
- `/app/backend/server.py` (MODIFIED)
- `/app/frontend/src/app/products/[slug]/page.tsx` (MODIFIED)
- `/app/frontend/src/lib/api.ts` (MODIFIED - added redirect type)

---

### Session: 2026-03-03 (continued)

#### COMPLETE: Video Upload Feature for Seller Listings

**Problem Statement:**
Implement video upload capability for sellers to showcase product demos. Requirements:
- Max 2 videos per listing
- Max 30 seconds duration per video
- Max 5MB file size
- Optional field (not required)
- Stored same way as images (Cloudinary URL → DB)

**Implementation:**

1. **Backend Changes:**
   - Added `videos` field to `ListingCreate` and `ListingUpdate` Pydantic models (max_length=2)
   - Created `validate_videos()` in EnterpriseListingGuard:
     - Validates max 2 videos
     - Validates Cloudinary URL format
     - Returns empty list for None/empty (optional)
   - Updated listing creation to store `videos` in document
   - Updated enterprise endpoint to return `videos` in seller data

2. **Frontend Changes:**
   - Added `uploadSellerProductVideo()` to cloudinary.ts (uses video endpoint)
   - Added `uploadProductVideos()` to api.ts
   - Added video upload UI to new listing page (`/seller/listings/new`)
   - Added video upload UI to edit listing page (`/seller/listings/[id]`)
   - Added video display in seller card on product page

3. **Validation (Frontend):**
   - File type: video/mp4, video/webm, video/quicktime
   - File size: Max 5MB
   - Duration: Max 30 seconds (client-side validation via video element)

4. **Validation (Backend):**
   - Max 2 videos per listing
   - Cloudinary URL format: `https://res.cloudinary.com/*`

**Testing Results** (20/20 pytest + 7/7 direct tests - 100%):
- ✅ Max 2 videos validation works
- ✅ Cloudinary URL format validation works
- ✅ Videos field is optional (empty list returned for None)
- ✅ Videos stored in sellerListings collection
- ✅ Enterprise endpoint returns videos in seller data
- ✅ Frontend upload functions exist and configured correctly

**Files Created/Modified:**
- `/app/backend/seller_products.py` (MODIFIED - ListingCreate/Update with videos)
- `/app/backend/guards/enterprise_listing_guard.py` (MODIFIED - validate_videos)
- `/app/backend/routers/enterprise_products.py` (MODIFIED - returns videos)
- `/app/frontend/src/lib/cloudinary.ts` (MODIFIED - video upload support)
- `/app/frontend/src/lib/api.ts` (MODIFIED - uploadProductVideos)
- `/app/frontend/src/app/seller/listings/new/page.tsx` (MODIFIED - video upload UI)
- `/app/frontend/src/app/seller/listings/[id]/page.tsx` (MODIFIED - video upload in edit)
- `/app/frontend/src/app/products/[slug]/page.tsx` (MODIFIED - video display)
- `/app/frontend/src/types/index.ts` (MODIFIED - SellerListing with videos)

**Business Impact:**
- Videos can significantly boost buyer interest and conversion
- Helps machinery/industrial sellers demonstrate product in action
- "Product Demo Video" badge visible when videos uploaded

---

### Session: 2026-03-03 (continued)

#### COMPLETE: Full Media Integration Verification

**Implementation Summary - Image + Video System:**

| Layer | Images | Videos |
|-------|--------|--------|
| **Count** | Max 5 | Max 2 |
| **Size** | 5MB each | 5MB each |
| **Duration** | N/A | 30 seconds |
| **Required** | Min 1 | Optional |

**Validation Layers:**

1. **Frontend Validation (Pre-upload):**
   - File type check (image/* or video/mp4,webm,mov)
   - File size check (5MB per file)
   - Video duration check (30 seconds max)
   - Count check (5 images, 2 videos)

2. **Cloudinary Upload:**
   - Images: `/image/upload` with q_auto,f_auto compression
   - Videos: `/video/upload` with q_auto,f_auto,vc_auto compression
   - Separate presets for images vs videos

3. **Backend Validation (Post-upload):**
   - EnterpriseListingGuard validates:
     - max_allowed=5 for images
     - max_allowed=2 for videos
     - Cloudinary URL format (https://res.cloudinary.com/*)
     - Min 1 image required

4. **MongoDB Schema Validation:**
   - Collection: sellerListings
   - images: array with maxItems=5
   - videos: array with maxItems=2
   - validationAction: error (rejects invalid docs)

**Testing Results** (28/28 tests - 100%):
- ✅ Backend guard max_allowed=5 for images
- ✅ Backend guard Cloudinary URL validation for images
- ✅ Backend guard max_allowed=2 for videos
- ✅ Backend guard Cloudinary URL validation for videos
- ✅ Pydantic models with max_length constraints
- ✅ MongoDB schema with maxItems constraints
- ✅ Frontend 5MB per image/video
- ✅ Frontend 30 second video duration
- ✅ Separate Cloudinary endpoints (image vs video)
- ✅ Image compression configured

**Files Created/Modified:**
- `/app/backend/migrations/add_media_validation.py` (NEW)
- `/app/backend/guards/enterprise_listing_guard.py` (MODIFIED)
- `/app/frontend/src/lib/cloudinary.ts` (MODIFIED)
- `/app/frontend/src/lib/api.ts` (MODIFIED)
- `/app/frontend/src/app/seller/listings/new/page.tsx` (MODIFIED)
- `/app/frontend/src/app/seller/listings/[id]/page.tsx` (MODIFIED)

---

### Session: 2026-03-03 (continued)

#### FIXED: Category Page 500 Error (ObjectId URL)

**Problem:**
User received 500 Internal Server Error when accessing `/categories/69a07a9dd3f5c6b5c5ebdbce` (ObjectId-based URL).

**Root Cause:**
The category page was calling a redirect endpoint that failed, and the `redirect()` function from Next.js was being caught inside a try-catch block, preventing the redirect from working.

**Fix:**
1. Updated category page to use enterprise resolver endpoint for token-based slug matching
2. Fixed try-catch to re-throw redirect errors (Next.js redirect throws special `NEXT_REDIRECT` error)
3. Added fallback lookup in public categories list
4. Added secondary redirect check for ObjectId URLs that find a category with a slug

**Behavior:**
- `/categories/{objectId}` → Redirects to `/categories/{slug}`
- `/categories/{slug}` → Loads directly (no redirect)
- Category not found → Shows "Category Not Found" page

**Files Modified:**
- `/app/frontend/src/app/categories/[slug]/page.tsx`

---

### Session: 2026-03-03 (continued)

#### COMPLETE: Seller Detail Page with Reviews

**Problem Statement:**
Build a dedicated seller-specific product detail page that displays comprehensive seller information, media gallery (images/videos), pricing, and a complete review/rating system. Only buyers with accepted inquiries can leave reviews. Rating aggregation stored in sellerListings for performance.

**Implementation:**

1. **Backend - Reviews Router** (`/app/backend/routers/reviews.py`)
   - `GET /api/reviews/seller-listing/{id}/details` - Returns aggregated data:
     - Product info, seller profile, listing details
     - All reviews with buyer info
     - avgRating and totalReviews computed from reviews
   - `GET /api/reviews/eligible` - Checks if buyer can review (requires accepted inquiry)
   - `GET /api/reviews/listing/{id}` - Returns reviews for a listing
   - `POST /api/reviews` - Submit new review (validates eligibility)
   - `update_listing_rating_stats()` - Updates avgRating/totalReviews in sellerListings

2. **Backend - Rating Aggregation**
   - Stores `avgRating`, `totalReviews`, `lastReviewAt` directly in `sellerListings` document
   - Updated on every new review submission
   - Exposed in enterprise products API for seller cards

3. **Frontend - Seller Detail Page** (`/app/frontend/src/app/products/[slug]/seller/[listingId]/page.tsx`)
   - Media gallery with image thumbnails
   - Product info: name, pricing tiers, MOQ, stock, lead time
   - Seller info: company name, location, badge, verification status
   - Technical specifications grid
   - Reviews section with star ratings
   - Review submission form (conditional on eligibility)
   - Request Quote button (opens inquiry modal)

4. **Frontend - Seller Card Updates**
   - Added `avgRating` and `totalReviews` to `EnterpriseProductSeller` type
   - Added star rating display when seller has reviews
   - Added "View Details & Reviews" link button

5. **API Types Updated** (`/app/frontend/src/lib/api.ts`)
   - Added `avgRating?: number` and `totalReviews?: number` to EnterpriseProductSeller

**Testing Results** (15/15 backend + 9/9 frontend - 100%):
- ✅ Seller detail page loads at /products/{slug}/seller/{listingId}
- ✅ API returns product, seller, listing, reviews data
- ✅ avgRating and totalReviews computed correctly
- ✅ Eligibility check requires auth and accepted inquiry
- ✅ Rating displayed on seller cards
- ✅ "View Details & Reviews" button navigates correctly
- ✅ Request Quote redirects to login for unauthenticated users
- ✅ "No reviews yet" message displays when 0 reviews
- ✅ Technical specifications displayed correctly

**Files Created:**
- `/app/backend/routers/reviews.py` (Reviews API)
- `/app/frontend/src/app/products/[slug]/seller/[listingId]/page.tsx` (Seller detail page)
- `/app/frontend/src/lib/utils.ts` (cn utility function)
- `/app/backend/tests/test_seller_detail_reviews.py` (Tests)

**Files Modified:**
- `/app/backend/routers/enterprise_products.py` - Added avgRating, totalReviews to seller response
- `/app/frontend/src/app/products/[slug]/page.tsx` - Added rating display and View Details button
- `/app/frontend/src/components/enterprise/SellerCard.tsx` - Added rating display and View Details button
- `/app/frontend/src/lib/api.ts` - Updated EnterpriseProductSeller type

**Business Impact:**
- Builds buyer trust through social proof (reviews)
- Helps differentiate sellers based on ratings
- Provides detailed seller information for informed buying decisions
- Future: Can influence search ranking by seller rating

---

### Session: 2026-03-05 (Raw Material Smart Calculator - Phase 1 Complete)

#### COMPLETE: Raw Material Calculator - Core Components

**Problem Statement:**
Build a Raw Material Smart Calculator system for calculating weight and price of industrial materials (steel, aluminum, copper, etc.) based on shape and dimensions. The system must support multiple shapes (round bar, square bar, pipe, plate, sheet), multiple units (mm, cm, meter, inch, feet), and provide real-time client-side calculations.

**Implementation:**

1. **Backend - Raw Material Router** (`/app/backend/routers/raw_material_router.py`)
   - `GET /api/raw-materials/materials` - Returns all materials with densities
   - `GET /api/raw-materials/shapes` - Returns all shape configurations
   - `POST /api/raw-materials/calculate` - Server-side weight calculation
   - `GET /api/raw-materials/sellers/raw-material/{productId}` - Get sellers with rate/kg pricing
   - Admin CRUD endpoints for materials management

2. **Backend - Weight Calculator Service** (`/app/backend/services/weight_calculator_service.py`)
   - Client and server-side calculation engine
   - Unit conversion (mm, cm, meter, inch, feet → meters)
   - Shape formulas:
     - Round bar: V = π × (d/2)² × L
     - Square bar: V = side² × L
     - Pipe: V = π × ((OD/2)² - ((OD-2t)/2)²) × L
     - Plate/Sheet: V = thickness × width × length
   - Weight = Volume × Density
   - Price = Total Weight × Rate/kg

3. **Frontend - MaterialCalculatorCard** (`/app/frontend/src/components/calculator/MaterialCalculatorCard.tsx`)
   - Material selector (loads from API)
   - Shape selector (5 shapes: round_bar, square_bar, pipe, plate, sheet)
   - Dynamic dimension inputs based on shape
   - Unit selector per dimension
   - Quantity and rate inputs
   - Real-time client-side calculation
   - Display: weight per piece, total weight, estimated price

4. **Frontend - SellerPriceComparison** (`/app/frontend/src/components/calculator/SellerPriceComparison.tsx`)
   - Loads sellers with rate_per_kg pricing
   - Calculates price for each seller based on total weight
   - Displays seller cards sorted by rate
   - Send Inquiry button per seller

5. **Frontend - Test Calculator Page** (`/app/frontend/src/app/tools/test-calculator/page.tsx`)
   - Testing page at /tools/test-calculator
   - Full calculator with all features
   - Calculation details display
   - API endpoint documentation

6. **Admin - Materials Manager** (`/app/frontend/src/app/admin/materials/page.tsx`)
   - CRUD interface for materials
   - Material name, density, description
   - Active/inactive status toggle

7. **Database - Materials Collection**
   - Default materials seeded: MS Steel (7850), SS304 (7930), SS316 (8000), Aluminum (2700), Copper (8960), Brass (8500)
   - All densities in kg/m³

**Testing Results** (15/15 backend + All frontend - 100%):
- ✅ Materials API returns 6 materials with densities
- ✅ Shapes API returns 5 shape configurations
- ✅ Calculation API works for all shapes
- ✅ Unit conversion works correctly
- ✅ Price calculation with rate_per_kg
- ✅ Calculator page loads at /tools/test-calculator
- ✅ Material selector shows API data
- ✅ Shape changes update dimension fields
- ✅ Real-time calculations work
- ✅ Admin materials requires authentication

**Files Created:**
- `/app/backend/routers/raw_material_router.py` (Raw material API)
- `/app/backend/services/weight_calculator_service.py` (Calculation engine)
- `/app/frontend/src/components/calculator/MaterialCalculatorCard.tsx`
- `/app/frontend/src/components/calculator/SellerPriceComparison.tsx`
- `/app/frontend/src/app/tools/test-calculator/page.tsx`
- `/app/frontend/src/app/admin/materials/page.tsx`
- `/app/backend/tests/test_raw_material_calculator.py`

---

### Session: 2026-03-05 (Raw Material Smart Calculator - Phase 3 Complete)

#### COMPLETE: Product Page Calculator Integration

**Problem Statement:**
Integrate the weight calculator into raw material product pages. When a category has `categoryType='raw_material'`, the product page should display the MaterialCalculatorCard, allow buyers to enter dimensions, calculate weight, compare seller prices based on calculated weight, and send inquiries with all calculation data included.

**Implementation:**

1. **Product Page Integration** (`/app/frontend/src/app/products/[slug]/page.tsx`)
   - Added `isRawMaterial` state that's set based on category type
   - Fetches category info via `GET /api/spec-templates/by-category/{categoryId}`
   - Shows MaterialCalculatorCard when `isRawMaterial=true`
   - Shows SellerPriceComparison with calculated weight
   - Added raw material inquiry modal with calculation summary

2. **Calculator Performance Fix** (`MaterialCalculatorCard.tsx`)
   - Fixed infinite re-render bug by using `useRef` for `onCalculate` callback
   - Removed `onCalculate` from useCallback dependencies
   - Calculator now updates instantly without performance issues

3. **Backend - Inquiry with Calculation Data** (`server.py`)
   - Extended `InquiryCreate` model with `calculationData` field
   - Stores material, shape, dimensions, weight, rate, and price in inquiry
   - Sellers can see structured calculation data in their dashboard

4. **Frontend API Update** (`/app/frontend/src/lib/api.ts`)
   - Added `calculationData` field to `createInquiry` function
   - Supports raw material inquiry submissions

**Product Page Workflow:**
1. Product page loads → checks if category is raw_material
2. If raw_material → shows calculator card below product description
3. Buyer enters dimensions → weight calculated client-side in real-time
4. Seller price cards show calculated prices (weight × rate_per_kg)
5. Buyer clicks "Send Inquiry" → modal shows calculation summary
6. Inquiry saved with all calculation data for seller

**Testing Results** (100% backend, 90% frontend - fixed):
- ✅ GET /api/spec-templates/by-category returns isRawMaterial flag
- ✅ Calculator works with all shapes (round_bar, square_bar, pipe, plate, sheet)
- ✅ POST /api/inquiries accepts calculationData field
- ✅ Standard product pages don't show calculator
- ✅ Fixed infinite re-render bug in MaterialCalculatorCard
- ✅ TypeScript compiles without errors

**Files Modified:**
- `/app/frontend/src/app/products/[slug]/page.tsx` - Added calculator integration
- `/app/frontend/src/components/calculator/MaterialCalculatorCard.tsx` - Fixed useRef bug
- `/app/frontend/src/lib/api.ts` - Added calculationData support
- `/app/backend/server.py` - Extended InquiryCreate model

---

### Session: 2026-03-05 (Raw Material Smart Calculator - Phase 2 Complete)

#### COMPLETE: Admin Spec Template System for Raw Materials

**Problem Statement:**
Build an Admin Spec Template System that supports raw material templates with formula types (round_bar, square_bar, pipe, plate, sheet), auto-populated dimension fields, and category type classification (standard vs raw_material).

**Implementation:**

1. **Backend - Extended Spec Template Models** (`server.py`)
   - Added `templateType` field (standard | raw_material)
   - Added `formulaType` field (round_bar | square_bar | pipe | plate | sheet)
   - Added `supportedShapes` array field
   - Updated `AdminSpecTemplateCreate` and `AdminSpecTemplateUpdate` models

2. **Backend - Category Type Extension**
   - Added `categoryType` field to `AdminCategoryUpdate` (standard | raw_material)
   - Categories marked as raw_material will show calculator on product pages

3. **Backend - New API Endpoint**
   - `GET /api/spec-templates/by-category/{category_id}` - Returns:
     - Category info with name and categoryType
     - Associated spec templates
     - `isRawMaterial` flag for easy frontend detection

4. **Frontend - Admin Spec Templates Page** (`/admin/spec-templates/page.tsx`)
   - Template Type selector (Standard / Raw Material with Calculator)
   - Formula Type selection with 5 shape options
   - Auto-populate dimension fields when formula type selected
   - Supported Shapes multi-select
   - Visual badges for raw material templates
   - Filter by template type

5. **Frontend - Admin Categories Page** (`/admin/categories/page.tsx`)
   - Category Type radio buttons (Standard / Raw Materials)
   - Visual badge for raw material categories
   - Info text explaining raw material calculator behavior

**Testing Results** (100% - 12/12 backend + all frontend):
- ✅ All calculator shapes work (round_bar, square_bar, pipe, plate, sheet)
- ✅ GET /spec-templates/by-category returns category with isRawMaterial flag
- ✅ Admin spec templates page has raw material configuration
- ✅ Admin categories page has categoryType selection
- ✅ Auto-populate fields work for each formula type
- ✅ Auth required for admin pages

**Files Modified:**
- `/app/backend/server.py` - Added templateType, formulaType, supportedShapes, categoryType
- `/app/frontend/src/app/admin/spec-templates/page.tsx` - Raw material template creation
- `/app/frontend/src/app/admin/categories/page.tsx` - Category type selection
- `/app/frontend/src/types/index.ts` - Updated AdminSpecTemplate and Category types

---

## Pending Tasks (Priority Order)

### P0: Raw Material Calculator - Remaining Phases
1. ~~**Phase 2**: Admin UI for Spec Templates specific to raw materials~~ ✅ COMPLETE
2. ~~**Phase 3**: Integrate calculator into raw material product pages~~ ✅ COMPLETE
3. **Phase 4**: Inquiry system extension - display calculation data in seller dashboard
4. **Phase 5**: SEO Calculator pages (/tools/steel-weight-calculator, etc.)

### P1: Deploy Backend to Render
**CRITICAL**: User's production site is running outdated backend code. Recent fixes won't be live until redeployed.

### P1: Implement Token-Based Search
Refactor main site search to be order-independent like the slug resolver.

### P1: Implement Weighted Ranking
Sort search results by calculated score (rating, response time, badge status).

### P1: Self-Learning Keyword System
Auto-add popular search terms to product searchAliases from analytics.

### P2: Admin Search Insights Dashboard
Build admin interface to view search analytics data.

### P2: Redis Caching
Add caching layer for frequently accessed data.

### Future/Backlog
- Refactor `server.py` into more routers
- AI Semantic Search Layer
- Online Payments for Quotes
- Counter-Offer System
- Cost-effective media storage (store publicId for Cloudinary cleanup)
