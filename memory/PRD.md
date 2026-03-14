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

### Session: 2026-03-05 (Raw Material Pricing Flow - Complete Integration)

#### COMPLETE: End-to-End Raw Material Pricing System

**Problem Statement:**
Ensure complete raw material flow: Sellers set rate/kg → Buyers see calculator → Weight calculated → Price shown per seller → Inquiry sent with calculation data → Sellers see details.

**Implementation:**

1. **Seller Listing with Rate/kg** (`seller_products.py`)
   - Added `rate_per_kg` and `material_supported` to ListingCreate/ListingUpdate models
   - Created `RatePerKgUpdate` model for daily rate updates
   - Added `PATCH /api/seller/listings/{id}/rate-per-kg` endpoint
   - Tracks rate history for auditing

2. **Seller Listing Form** (`/seller/listings/new/page.tsx`)
   - Detects raw material category via `/api/spec-templates/by-category/{id}`
   - Shows "Raw Material Pricing" section with:
     - Rate per kg input (₹/kg)
     - Material selector (from admin materials list)
     - Preview of calculated price (e.g., "100kg = ₹8,500")

3. **Product Page Calculator** (`/products/[slug]/page.tsx`)
   - Shows calculator below product description when `isRawMaterial=true`
   - Buyer enters: Material, Shape, Dimensions, Quantity
   - Weight calculated in real-time (client-side)

4. **Seller Price Comparison** (`SellerPriceComparison.tsx`)
   - Fetches sellers via `GET /api/raw-materials/sellers/raw-material/{productId}`
   - Calculates price per seller: `totalWeight × rate_per_kg`
   - Shows: Seller name, Rate/kg, Calculated Total, Send Inquiry button

5. **Inquiry with Calculation Data**
   - Inquiry includes: material, shape, dimensions, quantity, weight, rate, price
   - Seller dashboard displays all calculation details
   - Complete transparency for both parties

**Complete Workflow:**
```
Admin → Creates materials list (MS Steel, SS304, etc.)
     → Marks category as raw_material type
     
Seller → Creates listing with rate_per_kg
      → Can update rate daily via quick update
      
Buyer → Opens product page
     → Sees calculator (if raw material)
     → Enters dimensions
     → Weight calculated instantly
     → Sees all seller prices (weight × rate)
     → Sends inquiry with full calculation data
     
Seller → Receives inquiry
      → Sees: Material, Shape, Dimensions, Weight, Price
      → Can accept/quote/respond
```

**Testing Results** (100% - 12/12 backend + frontend verified):
- ✅ POST /api/seller/listings accepts rate_per_kg
- ✅ PATCH /api/seller/listings/{id}/rate-per-kg works
- ✅ GET /api/raw-materials/sellers/raw-material/{productId} returns rates
- ✅ Calculator pages functional
- ✅ SellerPriceComparison calculates correctly
- ✅ Inquiry with calculationData saves properly

**Files Modified:**
- `/app/backend/seller_products.py` - ListingCreate, ListingUpdate, RatePerKgUpdate
- `/app/frontend/src/app/seller/listings/new/page.tsx` - Rate/kg input section
- `/app/frontend/src/lib/api.ts` - ListingCreatePayload, ListingUpdatePayload

---

### Session: 2026-03-05 (Raw Material Smart Calculator - Phase 5 Complete)

#### COMPLETE: SEO Calculator Pages

**Problem Statement:**
Create public SEO calculator pages that help users calculate raw material weight, rank on Google for industrial queries, and direct users to UdyogConnect suppliers.

**Implementation:**

1. **Reusable SEO Layout Component** (`/components/seo/SEOCalculatorLayout.tsx`)
   - Hero section with gradient background, H1 title, subtitle
   - Embedded MaterialCalculatorCard with configurable defaults
   - Calculation results panel with CTA to find suppliers
   - Educational content section with formulas and tables
   - Collapsible FAQ section with accordion behavior
   - Related tools links
   - Full footer with navigation

2. **Steel Weight Calculator** (`/tools/steel-weight-calculator`)
   - Default: MS Steel + Round Bar
   - SEO Title: "Steel Weight Calculator | Calculate MS Steel, SS304, SS316 Weight - UdyogConnect"
   - Content: Density table, all shape formulas, example calculations
   - 6 FAQs about steel weight calculation

3. **Pipe Weight Calculator** (`/tools/pipe-weight-calculator`)
   - Default: MS Steel + Pipe
   - SEO Title: "Pipe Weight Calculator | Calculate Steel Pipe, MS Pipe Weight - UdyogConnect"
   - Content: Pipe formula, seamless vs ERW, pipe schedules
   - 6 FAQs about pipe weight calculation

4. **Plate Weight Calculator** (`/tools/plate-weight-calculator`)
   - Default: MS Steel + Plate
   - SEO Title: "Plate Weight Calculator | Steel Plate, MS Plate Weight - UdyogConnect"
   - Content: Plate vs sheet, HR vs CR, standard sizes
   - 6 FAQs about plate weight calculation

5. **Round Bar Weight Calculator** (`/tools/round-bar-weight-calculator`)
   - Default: MS Steel + Round Bar
   - SEO Title: "Round Bar Weight Calculator | MS Round Bar, SS Round Bar Weight - UdyogConnect"
   - Content: Weight per meter table, quick formula, bar types
   - 6 FAQs about round bar weight

**SEO Features:**
- Next.js Metadata exports with title, description, keywords, openGraph
- Canonical URLs for each page
- JSON-LD WebApplication schema
- JSON-LD FAQPage schema for each FAQ section
- Semantic HTML structure (H1, H2, H3)
- Internal linking between calculator pages

**Testing Results** (100% - 9/9):
- ✅ All 4 calculator pages load with correct defaults
- ✅ Calculator functionality works on all pages
- ✅ FAQ sections expand/collapse correctly
- ✅ JSON-LD structured data present
- ✅ Internal navigation works
- ✅ Calculation results display correctly

**Files Created:**
- `/app/frontend/src/components/seo/SEOCalculatorLayout.tsx`
- `/app/frontend/src/app/tools/steel-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/steel-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/pipe-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/pipe-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/plate-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/plate-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/round-bar-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/round-bar-weight-calculator/client.tsx`

---

### Session: 2026-03-05 (Raw Material Smart Calculator - Phase 4 Complete)

#### COMPLETE: Seller Dashboard Integration for Raw Material Inquiries

**Problem Statement:**
Display raw material calculation data in the seller dashboard so sellers can immediately understand buyer requirements: material, shape, dimensions, quantity, calculated weight, and estimated price.

**Implementation:**

1. **Backend - Seller Inquiries Response** (`seller_products.py`)
   - Modified `get_seller_inquiries` to include `calculationData` in response
   - Serializes calculation data (material, shape, dimensions, weight, price)

2. **Frontend - Seller Inquiry Type** (`types/index.ts`)
   - Extended `SellerInquiry` interface with `calculationData` property
   - Fields: material, shape, dimensions, quantity, weight_per_piece, total_weight, rate_per_kg, calculated_price

3. **Frontend - Seller Inquiries Page** (`/seller/inquiries/page.tsx`)
   - Added "Raw Material Calculation" section (only shown when calculationData exists)
   - Displays material, shape, quantity, total weight
   - Shows dimensions as tags (e.g., "diameter: 20 mm", "length: 6 meter")
   - Visual price formula: Rate/kg × Weight = Buyer's Estimate
   - Uses Calculator and Scale icons from lucide-react
   - data-testid for testing: `calc-data-{inquiry._id}`

**UI Layout:**
```
Inquiry Card
├── Inquiry Header (product, buyer, status)
├── Raw Material Calculation (if calculationData exists)
│   ├── Material, Shape, Quantity, Total Weight
│   ├── Dimensions (as tags)
│   └── Price Formula: ₹Rate × Weight = ₹Estimate
├── Actions (Accept, Reject, Report)
└── Buyer Contact (if accepted)
```

**Testing Results** (100% - 12/12):
- ✅ POST /api/inquiries accepts calculationData field
- ✅ GET /api/seller/inquiries returns calculationData when present
- ✅ SellerInquiry type includes calculationData property
- ✅ Calculator and Scale icons imported
- ✅ Raw Material Calculation section renders correctly
- ✅ TypeScript compiles without errors

**Files Modified:**
- `/app/backend/seller_products.py` - Added calculationData to inquiry response
- `/app/frontend/src/types/index.ts` - Extended SellerInquiry type
- `/app/frontend/src/app/seller/inquiries/page.tsx` - Added calculation display section

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

### P0: Raw Material Calculator - ALL PHASES COMPLETE ✅
1. ~~**Phase 1**: Calculation Engine~~ ✅ COMPLETE
2. ~~**Phase 2**: Admin UI for Spec Templates~~ ✅ COMPLETE
3. ~~**Phase 3**: Product Page Calculator Integration~~ ✅ COMPLETE
4. ~~**Phase 4**: Seller Dashboard Display~~ ✅ COMPLETE
5. ~~**Phase 5**: SEO Calculator Pages~~ ✅ COMPLETE

---

### Session: 2026-03-05 (21 Shapes + 14 Materials + 4 New SEO Pages)

#### COMPLETE: Comprehensive Shape and Material Library

**Problem Statement:**
User requested to add all 21 industrial raw material shapes with their dependent dimension fields, 14 material types with accurate densities, and 4 new SEO calculator pages for Hex Bar, Angle, Channel, and Beam calculators.

**Implementation:**

1. **21 Shapes Added to Database** (`/app/backend/scripts/seed_shapes_and_materials.py`)
   - **Solid Bars**: Round Bar, Square Bar, Hex Bar, Flat Bar, Rectangular Bar
   - **Hollow Sections**: Pipe/Tube, Square Hollow Section (SHS), Rectangular Hollow Section (RHS)
   - **Structural Sections**: Angle (L Angle), Channel (C Channel), I Beam, H Beam, T Section, Z Section
   - **Flat Products**: Plate, Sheet, Chequered Plate, Perforated Sheet
   - **Wire & Coil Products**: Wire Rod, Strip, Coil

2. **14 Materials Added with Accurate Densities**
   - **MS & Carbon Steel**: MS Steel (7,850 kg/m³), EN8 Steel (7,850 kg/m³), EN19 Steel (7,850 kg/m³)
   - **Stainless Steel**: SS202 (7,900 kg/m³), SS304 (7,930 kg/m³), SS304L (7,930 kg/m³), SS316 (8,000 kg/m³), SS316L (8,000 kg/m³)
   - **Aluminum**: Aluminum 6061 (2,700 kg/m³), Aluminum 6063 (2,700 kg/m³)
   - **Other Metals**: Copper (8,960 kg/m³), Brass (8,500 kg/m³), Cast Iron (7,200 kg/m³), Titanium (4,500 kg/m³)

3. **Backend Weight Calculator Updated** (`/app/backend/services/weight_calculator_service.py`)
   - Added volume calculation functions for all shapes:
     - `calculate_hex_bar_volume()`: V = (√3/2) × AF² × L
     - `calculate_square_hollow_volume()`: V = (side² - (side-2t)²) × L
     - `calculate_rectangular_hollow_volume()`: V = (W×H - (W-2t)×(H-2t)) × L
     - `calculate_angle_volume()`: V = t × (A + B - t) × L
     - `calculate_channel_volume()`: V = (web×tw + 2×flange×tf) × L
     - `calculate_i_beam_volume()`: V = (2×W×tf + (H-2tf)×tw) × L
     - `calculate_t_section_volume()`, `calculate_z_section_volume()`
     - `calculate_chequered_plate_volume()` (1.05× for pattern)
     - `calculate_perforated_sheet_volume()` (1 - open_area)

4. **Frontend Calculator Updated** (`MaterialCalculatorCard.tsx`)
   - Dynamic shape loading from `/api/raw-materials/shapes` API
   - Client-side `calculateVolume()` function handles all 21 shapes
   - Dynamic field rendering based on shape configuration

5. **4 New SEO Calculator Pages Created**:
   - `/tools/hex-bar-weight-calculator` - Hex Bar with Across Flats field
   - `/tools/angle-weight-calculator` - L-Angle with Leg A, Leg B, Thickness
   - `/tools/channel-weight-calculator` - C-Channel with Web/Flange dimensions
   - `/tools/beam-weight-calculator` - I-Beam/H-Beam with structural dimensions

**Testing Results** (100% - 25/25 backend + 4/4 frontend):
- ✅ GET /api/raw-materials/shapes returns 21 shapes
- ✅ GET /api/raw-materials/materials returns 15 materials (14 required + 1 original)
- ✅ All shape calculations verified against expected weights:
  - Hex Bar 25mm × 3m = 12.75 kg ✅
  - Angle 65×65×6 × 6m = 35.04 kg ✅
  - I-Beam ISMB 200 × 6m = 149.63 kg ✅
  - Channel ISMC 150 × 6m = 97.16 kg ✅
- ✅ All 4 new SEO pages load with correct default shapes
- ✅ Dynamic fields render correctly for each shape

**Files Created:**
- `/app/backend/scripts/seed_shapes_and_materials.py` - Database seed script
- `/app/frontend/src/app/tools/hex-bar-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/hex-bar-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/angle-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/angle-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/channel-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/channel-weight-calculator/client.tsx`
- `/app/frontend/src/app/tools/beam-weight-calculator/page.tsx`
- `/app/frontend/src/app/tools/beam-weight-calculator/client.tsx`
- `/app/backend/tests/test_21_shapes_14_materials.py`

**Files Modified:**
- `/app/backend/services/weight_calculator_service.py` - Added all shape formulas
- `/app/frontend/src/components/calculator/MaterialCalculatorCard.tsx` - Dynamic shape loading
- `/app/frontend/src/components/seo/SEOCalculatorLayout.tsx` - Updated navigation links

---

### Session: 2026-03-05 - Configurable Calculator System Refactoring

#### COMPLETE: Flexible Admin-Configurable Calculator System

**Problem Statement:**
User requested to refactor the hardcoded raw material calculator into a fully configurable system where admins can create any type of calculator (steel, cement, chemicals, etc.) without code changes.

**System Architecture Implemented:**

1. **Unit Groups** (`/api/calculator/unit-groups`)
   - Admin-managed unit conversion system
   - 6 default groups: Length, Weight, Volume, Area, Quantity, Percentage
   - Each unit has conversion factor to base unit
   - Example: mm → 0.001 (to meters)

2. **Calculator Templates** (`/api/calculator/calculators`)
   - Admin-defined calculator configurations
   - Each template has:
     - Name, slug, description
     - Dynamic fields (key, label, unit_group, default_unit)
     - Formula expression (evaluated safely)
     - Output unit and label
     - Material type linking
   - Safe formula evaluator supports: pi, pow, sqrt, sin, cos, tan, log, min, max, round, floor, ceil

3. **Materials Table** (`/api/calculator/materials`)
   - Material name and type
   - Density (kg/m³) for volume calculations
   - Weight per unit (for common sizes, permanent values)
   - Example: "10mm_round_per_meter": 0.617 kg

4. **Dynamic Calculator Component** (`DynamicCalculator.tsx`)
   - Loads calculator from database
   - Renders fields dynamically based on template
   - Auto-calculates on value change
   - Shows formula used

**API Endpoints Created:**
- `GET /api/calculator/unit-groups` - List all unit groups
- `POST /api/calculator/unit-groups` - Create unit group
- `PUT /api/calculator/unit-groups/{id}` - Update unit group
- `GET /api/calculator/calculators` - List all calculators
- `GET /api/calculator/calculators/{id}` - Get single calculator
- `GET /api/calculator/calculators/by-category/{category_id}` - Get calculator for category
- `POST /api/calculator/calculators` - Create calculator
- `PUT /api/calculator/calculators/{id}` - Update calculator
- `DELETE /api/calculator/calculators/{id}` - Delete calculator
- `GET /api/calculator/materials` - List materials (with type filter)
- `GET /api/calculator/materials/types` - Get material types
- `POST /api/calculator/materials` - Create material
- `PUT /api/calculator/materials/{id}` - Update material
- `DELETE /api/calculator/materials/{id}` - Delete material
- `POST /api/calculator/calculate` - Perform calculation
- `POST /api/calculator/calculate-with-prices` - Calculate with seller prices

**Admin Pages Created:**
- `/admin/calculators` - Manage calculator templates with formula helper
- `/admin/unit-groups` - Manage unit groups and conversions
- `/admin/materials` - Updated to support material_type and weight_per_unit

**Test Page:**
- `/tools/dynamic-calculator` - Test page for the configurable calculator system

**Sample Calculators Created:**
1. Round Bar Calculator - `pi * pow(diameter / 2, 2) * length * density`
2. Hex Bar Calculator - `0.866 * pow(across_flats, 2) * length * density`
3. Pipe Calculator - `pi * (pow(OD/2, 2) - pow((OD-2t)/2, 2)) * length * density`
4. Plate Calculator - `thickness * width * length * density`

**Files Created:**
- `/app/backend/routers/configurable_calculator.py` - Full CRUD API + formula evaluator
- `/app/backend/scripts/seed_unit_groups.py` - Seed default unit groups
- `/app/frontend/src/components/calculator/DynamicCalculator.tsx` - Dynamic calculator component
- `/app/frontend/src/app/admin/calculators/page.tsx` - Calculator templates admin
- `/app/frontend/src/app/admin/unit-groups/page.tsx` - Unit groups admin
- `/app/frontend/src/app/tools/dynamic-calculator/page.tsx` - Test page

**Files Modified:**
- `/app/backend/server.py` - Added configurable calculator router
- `/app/frontend/src/app/admin/materials/page.tsx` - Updated for new material structure

**Key Benefits:**
1. No code changes needed to add new calculators
2. Admins define fields, formulas, and units through UI
3. Safe formula evaluation prevents code injection
4. Category-linked calculators for automatic loading
5. Seller pricing integration for B2B marketplace

---
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



---

### Session: 2026-03-05 (Dynamic Calculator System Verification - COMPLETE)

#### VERIFIED: ModernDynamicCalculator System

**Verification Results** (100% - All Tests Pass):

**P0 - Dynamic Calculator System:**
1. ✅ **ModernDynamicCalculator Rendering** - Beautiful modern UI with gradient header renders on product pages
2. ✅ **Calculator Fields Dynamic Loading** - OD, Thickness, Length, Quantity fields load from template
3. ✅ **Material Family Dropdown Filtering** - Shows only materials from "Steel" family (MS Steel, EN8 Steel, EN19 Steel)
4. ✅ **Real-Time Weight Calculation** - Formula executes correctly (33.29 kg for OD=50mm, Thickness=5mm, Length=6m)
5. ✅ **Material Density Usage** - Density (7,850 kg/m³) correctly pulled from materials table
6. ✅ **CalculatorSellerCards Display** - Seller info with rate, MOQ, lead time, stock shown
7. ✅ **Real-Time Price Updates** - Estimated Total Price updates when calculator values change
8. ✅ **Category-Based Calculator Loading** - Pipe Calculator loads for "Test Category" products

**Bug Fixed:**
- **Material Family Filter**: Fixed regex pattern to use exact match (`^{family}$`) instead of partial match. Previously, filtering for "Steel" also returned "Stainless Steel" materials.

**Testing Agent Results** (iteration_40.json):
- Backend: 17/17 tests passed (100%)
- Frontend: All calculator features verified (100%)
- Key calculation verified: Pipe OD=50mm, t=5mm, L=6m = 33.29 kg

**Files Modified:**
- `/app/backend/routers/configurable_calculator.py` - Fixed material family regex filter

**Key URLs Tested:**
- Product Page: `/products/industrial-electric-motor-5hp-test-category-supplier-india`
- Calculator ID: `69a9c3f643371dcb4a004e60` (Pipe Calculator)
- Category ID: `699be9023cbe1a8c31591667`

---

---

### Session: 2026-03-06 (Product Type Architecture - Complete)

#### COMPLETE: Product Type Differentiation System

**Problem Statement:**
User reported that both raw material and standard product seller cards were appearing on the same product page, causing UX confusion. Required implementing a `product_type` field to differentiate between `raw_material` and `standard_product` types, with each type having its own dedicated UI components.

**Implementation:**

1. **Backend - Product Type Field**
   - Added `product_type` to enterprise product API response
   - Modified `/api/products/{slug}/enterprise` to return `product_type: 'raw_material' | 'standard_product'`
   - Default value: `standard_product` for existing products
   - Calculator lookup updated to check both directions:
     - Calculator with `category_id` pointing to category
     - Category with `calculator_id` pointing to calculator

2. **Frontend - Conditional Rendering**
   - `raw_material` products:
     - Show Calculator section
     - Show RawMaterialSellerCard (₹/kg pricing)
     - Hide Filter Panel
     - Hide StandardSellerCard
   - `standard_product` products:
     - Show Filter Panel
     - Show StandardSellerCard (₹/piece pricing)
     - Hide Calculator section
     - Hide RawMaterialSellerCard

3. **StandardSellerCard Component** (`/components/product/StandardSellerCard.tsx`)
   - Displays ₹/piece pricing
   - Shows spec strip header
   - UdyogConnect badge support
   - Seller role badge
   - Rating display
   - Volume pricing tiers
   - Request Quote button
   - View Details link

4. **RawMaterialSellerCard Component** (`/components/product/RawMaterialSellerCard.tsx`)
   - Displays ₹/kg pricing
   - Shows calculated price based on weight
   - Displays price formula: `Weight × Rate = Total`

5. **Calculator Lookup Fix**
   - Updated `get_calculator_for_category()` in configurable_calculator.py
   - Now checks both:
     - `calculator_templates.category_id == category_id`
     - `categories.calculator_id` → fetch that calculator

**Testing Results (100% - 11/11 backend, all frontend verified):**
- ✅ Standard product API returns `product_type: 'standard_product'`
- ✅ Raw material API returns `product_type: 'raw_material'`
- ✅ Standard product page shows Filter Panel + StandardSellerCard
- ✅ Raw material page shows Calculator + RawMaterialSellerCard
- ✅ No overlap between product types
- ✅ Calculator loads correctly for raw materials

**Files Modified:**
- `/app/backend/routers/enterprise_products.py` - Added product_type to response
- `/app/backend/routers/configurable_calculator.py` - Fixed calculator lookup
- `/app/frontend/src/app/products/[slug]/page.tsx` - Conditional rendering
- `/app/frontend/src/components/product/StandardSellerCard.tsx` - Rewritten
- `/app/frontend/src/components/product/RawMaterialSellerCard.tsx` - ₹/kg unit

**Business Impact:**
- Clean separation of product types prevents user confusion
- Raw materials show weight-based pricing (industry standard)
- Standard products show per-piece pricing
- Maintainable architecture for future product types

---

### Session: 2026-03-07

#### P0: Quick Price Update Fix - COMPLETE
**Issue:**
The Quick Price Update feature on `/seller/pricing` was not working. When a seller updated the product price, the update didn't persist to the database.

**Root Cause Analysis:**
1. **Frontend Issue**: `pricingSlabs` was conditionally sent (`pricingSlabs: allSlabs.length > 1 ? allSlabs : undefined`) - when only updating base price without tiers, the pricing data was never sent.
2. **Backend Issue**: The `ListingUpdate` model in `seller_products.py` was missing `pricingSlabs` and `stockStatus` fields. These fields were silently ignored by Pydantic validation.

**Fix Applied:**
1. **Frontend (`/app/frontend/src/app/seller/pricing/page.tsx`):**
   - Changed to always send `pricingSlabs: allSlabs` (line 185)
   - Ensures pricing is always updated even for single-tier prices

2. **Backend (`/app/backend/seller_products.py`):**
   - Added `pricingSlabs: Optional[List[PricingTier]]` to ListingUpdate model (line 98)
   - Added `stockStatus: Optional[Literal[...]]` to ListingUpdate model (line 99)
   - Added handler to convert `pricingSlabs` → `pricingTiers` format (lines 814-830)
   - Added price history tracking for audit trail
   - Updates `minPrice` for search optimization

3. **Backend (`/app/backend/server.py`):**
   - Added `stockStatus` to ListingUpdate model (line 1683)
   - Added `stockStatus` to field_mapping (line 5910)

**Testing Results (100% - 8/8 backend tests passed):**
- ✅ Health check passes
- ✅ Seller listings endpoint exists
- ✅ Endpoint accepts `pricingSlabs` field
- ✅ Endpoint accepts `stockStatus` field
- ✅ Full quick price payload accepted

**Files Modified:**
- `/app/frontend/src/app/seller/pricing/page.tsx` - Always send pricingSlabs
- `/app/backend/seller_products.py` - Added fields and handler
- `/app/backend/server.py` - Added stockStatus field

**Business Impact:**
- Sellers can now update prices correctly from the Quick Price Update page
- Price history is tracked for audit/analytics
- Stock status can be updated alongside price

---

### Session: 2026-03-07 (Continued)

#### P0: Categories/Products Visibility Fix - COMPLETE
**Issue:**
The sidebar showed category counts (e.g., "Cleaning products: 5") that included ALL products in the category, but the main content area only showed products with active seller listings. This caused user confusion - clicking on a category with "5" products would show "No products available".

**Root Cause:**
The `/categories/public` endpoint was counting ALL products in a category (from the products table), instead of counting only products that have active seller listings.

**Fix Applied:**
1. **Refactored `/api/categories/public`** (`/app/backend/server.py`):
   - Changed aggregation to start from `sellerListings` (not `categories`)
   - Now aggregates: active listings → unique products → category
   - `productCount` now correctly represents products WITH active seller listings
   - Only shows categories that have at least 1 product with active listings

2. **Added Debug Endpoint** (`/api/admin/debug/category-listings/{category_id}`):
   - Helps diagnose why categories appear in dropdown but show no products
   - Shows breakdown of products and their listing status

**New Business Logic:**
- A category is visible ONLY if it has at least 1 product with at least 1 active seller listing
- `productCount` = number of unique products that have active seller listings (not total products)
- `listingCount` = total number of active seller listings in the category

**Files Modified:**
- `/app/backend/server.py` - Refactored `/categories/public` endpoint

---

### P0: SSOT sellerListings Fix - COMPLETE
**Issue:**
User has 1 listed product but category page showed 5 products. The categoryId in the listing didn't match the category page being viewed.

**Root Cause:**
1. `/products` endpoint was filtering by `product_info.categoryId` instead of `listing.categoryId`
2. `/categories` and `/categories/public` were using complex joins through products table instead of directly using listing's categoryId

**SSOT Principle Applied:**
**sellerListings is now the SINGLE SOURCE OF TRUTH for public visibility:**
- Category visibility is determined by listings having that categoryId
- Product visibility is determined by listing.categoryId directly
- Product counts come from counting listings, not products table

**Fixes Applied:**

1. **`/api/categories`** (`line 4248`):
   - Now aggregates from `sellerListings` directly
   - Groups by `listing.categoryId`
   - Only shows categories with active listings

2. **`/api/categories/public`** (`line 4310`):
   - Same SSOT approach as `/categories`
   - `productCount` = unique products in active listings
   - `listingCount` = total active listings

3. **`/api/products?categoryId=X`** (`line 4627`):
   - Changed filter from `product_info.categoryId` to `firstCategoryId` (listing's categoryId)
   - Products now filter by their listing's categoryId, not the products table

**Testing Results:**
- Category with 1 active listing shows `productCount: 1`, `listingCount: 1` ✅
- Products endpoint returns only 1 product for that category ✅
- Categories without listings don't appear ✅

**Key Change:**
```python
# BEFORE (wrong - used product's categoryId)
{"$match": {"product_info.categoryId": ObjectId(category_id)}}

# AFTER (correct - uses listing's categoryId)
{"$match": {"firstCategoryId": ObjectId(category_id)}}
```

---

### P0: /products Endpoint SSOT Fix - COMPLETE
**Issue:**
Products were not showing when clicking on a category, even though the category count was correct.

**Root Cause:**
The category filter was applied AFTER the `$group` stage in the `/products` endpoint. This meant we were trying to filter on `firstCategoryId` after grouping, but the filter needed to be applied BEFORE grouping to filter individual listings.

**Fix Applied:**
Completely rewrote `/api/products` endpoint:
```python
# Stage 1: Filter BEFORE grouping (SSOT)
base_match = {
    "status": "active",
    "categoryId": ObjectId(category_id)  # Filter by listing's categoryId
}
pipeline = [{"$match": base_match}, ...]
```

**Key Changes:**
1. Category filter now applied in Stage 1 (BEFORE `$group`)
2. Simplified pipeline from 8+ stages to 7 stages
3. All fields derived from listing data (not products table)
4. Removed complex fallback logic

**Testing Results:**
- Categories: 1 category with 1 product, 1 listing ✅
- Products API with categoryId filter: Returns 1 product ✅

---

### Session: 2026-03-09

#### Multi-WhatsApp Numbers Feature - COMPLETE

**Objective:**
Allow sellers to add multiple WhatsApp numbers and select one as primary contact. The primary number is used for automatic buyer connection after inquiry submission.

**Implementation:**

1. **Backend APIs** (`/app/backend/routers/seller_whatsapp_router.py`):
   - `GET /api/seller/whatsapp/contacts` - Get all seller's WhatsApp contacts
   - `POST /api/seller/whatsapp/contacts` - Add new contact (E.164 validation)
   - `PATCH /api/seller/whatsapp/contacts/{id}` - Update contact
   - `DELETE /api/seller/whatsapp/contacts/{id}` - Delete contact
   - `POST /api/seller/whatsapp/contacts/{id}/set-primary` - Set as primary
   - `GET /api/seller/whatsapp/settings` - Get autoWhatsappConnect setting
   - `PATCH /api/seller/whatsapp/settings` - Toggle auto connect
   - `GET /api/seller/whatsapp/seller/{id}/primary` - Public endpoint for buyer flow

2. **Database Schema** (`sellerWhatsappContacts` collection):
   ```json
   {
     "sellerId": ObjectId,
     "phoneNumber": "+919876543210",
     "label": "Sales",
     "isPrimary": true,
     "createdAt": datetime,
     "updatedAt": datetime
   }
   ```

3. **Seller Dashboard** (`/app/frontend/src/app/seller/whatsapp/page.tsx`):
   - Table to manage WhatsApp numbers
   - Add/Edit/Delete contacts
   - Set primary contact
   - Toggle auto-connect setting

4. **Buyer Inquiry Flow** (`/app/frontend/src/components/enterprise/InquiryModal.tsx`):
   - After inquiry submission, shows success page
   - "Connect with Seller on WhatsApp" button using primary number
   - WhatsApp link opens in new tab with pre-filled message

5. **Seller Inquiry Page** (`/app/frontend/src/app/seller/inquiries/page.tsx`):
   - WhatsApp contact dropdown on each inquiry
   - Seller can choose which number to use for contacting buyer

**Business Logic:**
- First contact added automatically becomes primary
- Only one contact can be primary at a time
- When primary is deleted, oldest remaining contact becomes primary
- International numbers supported (E.164 format)
- Auto-connect can be disabled by seller

**Testing Results:**
- 20/20 backend tests passed
- CRUD operations verified
- E.164 phone validation working
- Primary contact switching logic correct
- Public endpoint for buyer flow functional

**Files Created/Modified:**
- `/app/backend/routers/seller_whatsapp_router.py` (NEW)
- `/app/backend/server.py` (router registration + inquiry response)
- `/app/frontend/src/app/seller/whatsapp/page.tsx` (NEW)
- `/app/frontend/src/app/seller/page.tsx` (dashboard link)
- `/app/frontend/src/app/seller/inquiries/page.tsx` (WhatsApp dropdown)
- `/app/frontend/src/components/enterprise/InquiryModal.tsx` (WhatsApp connect)
- `/app/frontend/src/lib/api.ts` (API functions)

---

### Session: 2026-03-09 (Continued)

#### OTP-Based Registration - COMPLETE

**Objective:**
Replace email link verification with OTP-based registration. Users enter a 6-digit OTP sent to their email instead of clicking a verification link. This resolves the "link not clickable" issue reported during onboarding.

**Requirements:**
- 6-digit OTP format
- 10-minute expiry
- Max 5 verification attempts per OTP
- Max 5 OTP requests per email per hour
- 30-second resend cooldown
- OTP acts as verification layer BEFORE existing registration flow
- Existing login flow must remain unchanged

**Implementation:**

1. **Backend OTP Service** (`/app/backend/services/otp_service.py`):
   - `RegistrationOTPService` class with:
     - `request_otp()` - Generates 6-digit OTP, stores SHA256 hash, sends email
     - `verify_otp()` - Validates OTP, tracks attempts, marks as verified
     - `is_email_verified_via_otp()` - Checks if email was verified recently (30 min window)
   - Rate limiting: 5 requests/hour per email
   - Cooldown: 30 seconds between requests
   - Security: OTP stored as SHA256 hash

2. **Backend API Endpoints** (`/app/backend/server.py`):
   - `POST /api/auth/register/request-otp` - Request OTP for registration
   - `POST /api/auth/register/verify-otp` - Verify 6-digit OTP
   - `GET /api/auth/register/otp-status` - Check OTP verification status

3. **User Creation Integration** (`get_current_user` in server.py):
   - When creating new user, checks if email was verified via OTP
   - If verified, sets `isEmailVerified: true` immediately
   - Eliminates need for email verification link

4. **Frontend Registration Page** (`/app/frontend/src/app/register/page.tsx`):
   - **Step 1 (Details)**: Full Name, Email, Password, Confirm Password
   - **Step 2 (OTP)**: 6-digit input boxes with auto-focus
   - **Step 3 (Success)**: Confirmation + redirect to complete-profile
   - Step indicator: "1. Sign Up → 2. Verify OTP → 3. Complete Profile"

5. **Frontend OTP UI Features**:
   - 6 separate input boxes with auto-focus on next
   - Auto-submit when all 6 digits entered
   - Paste support (full 6-digit code)
   - Resend button with cooldown timer
   - Back button to return to details
   - Clear error messages with attempts remaining

6. **Frontend API Functions** (`/app/frontend/src/lib/api.ts`):
   - `requestRegistrationOTP(email, name)` - Request OTP
   - `verifyRegistrationOTP(email, otp)` - Verify OTP
   - `checkOTPStatus(email)` - Check verification status

7. **AuthContext Update** (`/app/frontend/src/context/AuthContext.tsx`):
   - `signUp()` now accepts `skipVerificationEmail` parameter
   - When OTP flow used, verification email is skipped
   - User created with correct verification status

**Database:**
- Collection: `registration_otps`
- Schema: `{ email, name, otpHash, attempts, isUsed, isVerified, expiresAt, createdAt }`

**Testing Results:**
- 88% backend tests passed (15/17) - 2 failures due to rate limiting correctly enforced
- 100% frontend tests passed
- Bug fixed: Double JSON.stringify in API client causing 422 errors

**Security Features Verified:**
- OTP length: 6 digits ✅
- OTP expiry: 10 minutes ✅
- Max attempts per OTP: 5 ✅
- Rate limit: 5 requests/minute ✅
- Resend cooldown: 30 seconds ✅
- Email normalization: lowercase, trimmed ✅
- OTP hashing: SHA256 ✅

**Files Created:**
- `/app/backend/services/otp_service.py` - OTP service implementation
- `/app/backend/tests/test_otp_registration.py` - Backend tests

**Files Modified:**
- `/app/backend/server.py` - Added OTP endpoints, updated user creation
- `/app/frontend/src/app/register/page.tsx` - Complete rewrite with OTP flow
- `/app/frontend/src/lib/api.ts` - Added OTP API functions, fixed double-stringify bug
- `/app/frontend/src/context/AuthContext.tsx` - Added skipVerificationEmail param

**Note:** Email sending is MOCKED when `RESEND_API_KEY` is not configured. In mock mode, OTP is returned in the API response for testing purposes.

---


### Session: 2026-03-10 (Seller Catalog System)

#### Seller Catalog System - P0 COMPLETE ✅

**Objective:**
Create a comprehensive seller catalog system allowing sellers to have their own digital catalog page that can be shared with buyers. Includes new seller fields, category-wise product display, clickable seller names, and SEO optimization.

**Implementation:**

1. **New Seller Fields (Backend)**:
   - `enterpriseEstablishmentYear`: User input during profile completion (required for sellers, 1800-current year, editable once)
   - `platformRegistrationYear`: Auto-generated from account creation year (never editable)
   - `sellerSlug`: Auto-generated from business name (lowercase, hyphenated, max 90 chars)
   - `sellerBannerImage`: Optional banner image for catalog page

2. **Seller Slug Generation** (`generate_seller_slug()`):
   - Convert to lowercase
   - Remove special characters
   - Replace spaces with hyphens
   - Max 90 characters (don't cut mid-word)
   - Auto-append suffix for duplicates (e.g., `abc-industries-2`)

3. **Backend API Endpoints** (`/app/backend/routers/seller_catalog_router.py`):
   - `GET /api/seller-catalog/{slug}` - Get seller catalog with products by category
   - `GET /api/seller-catalog/{slug}/category/{category_slug}` - Get products for specific category
   - `GET /api/seller-catalog/by-id/{seller_id}` - Redirect to slug-based URL

4. **Frontend Profile Completion** (`/app/frontend/src/app/complete-profile/page.tsx`):
   - Added "Enterprise Establishment Year" dropdown for sellers
   - Validation: Required for sellers, 1800-current year
   - Shows help text explaining the field purpose

5. **Seller Catalog Page** (`/app/frontend/src/app/seller-catalog/[slug]/`):
   - SEO-optimized metadata generation
   - Banner section (custom or gradient default)
   - Seller info card (logo, name, location, badges, rating)
   - Stats display (products count, categories count)
   - Action buttons (Send Inquiry, Call Seller)
   - Category-wise product display (4 products per category, random rotation)
   - Product cards with inquiry button

6. **Clickable Seller Names**:
   - Updated `StandardSellerCard` to link seller names to catalog page
   - Hover animation with underline transition
   - Added `sellerSlug` to `EnterpriseProductSeller` interface
   - Backend returns `sellerSlug` in seller data

7. **Reusable Component** (`/app/frontend/src/components/SellerNameLink.tsx`):
   - Consistent seller name linking across platform
   - Animated underline on hover

**Testing Results:**
- 100% backend tests passed (15/15)
- 100% frontend components render correctly
- API correctly handles 404 for non-existent sellers

**Files Created:**
- `/app/backend/routers/seller_catalog_router.py`
- `/app/frontend/src/app/seller-catalog/[slug]/page.tsx`
- `/app/frontend/src/app/seller-catalog/[slug]/SellerCatalogPage.tsx`
- `/app/frontend/src/components/SellerNameLink.tsx`
- `/app/backend/tests/test_seller_catalog_feature.py`

**Files Modified:**
- `/app/backend/server.py` - Added seller fields, generate_seller_slug(), updated ProfileCompleteCreate
- `/app/backend/routers/enterprise_products.py` - Added sellerSlug to seller data
- `/app/frontend/src/app/complete-profile/page.tsx` - Added establishment year field
- `/app/frontend/src/lib/api.ts` - Added seller catalog API types and functions
- `/app/frontend/src/components/product/StandardSellerCard.tsx` - Made seller name clickable

**Note:** Legacy sellers don't have `sellerSlug` field. Their names appear as plain text. New sellers registered after this update will have `sellerSlug` auto-generated, making their names clickable links to their catalog pages.

---

### Session: 2026-03-14 (Seller Catalog System - Data Migration & Fixes)

#### Data Migration for Seller Slugs - COMPLETE ✅

**Problem:**
- Legacy sellers in both `users` and `sellers` collections didn't have `sellerSlug` field
- Product pages and seller catalog pages couldn't link properly to legacy sellers
- The `/api/products/{slug}/filter` endpoint wasn't returning `sellerSlug` for legacy sellers

**Fixes Applied:**

1. **Data Migration Script** (`/app/backend/migrations/migrate_add_seller_slugs.py`):
   - Migrates all existing sellers to have `sellerSlug` field
   - Generates slug from `businessName` using same logic as new registrations
   - Handles duplicates by appending -2, -3, etc.
   - Skips sellers that already have valid slugs
   - Works for both `users` and `sellers` collections

2. **Dual Collection Lookup** (Backend APIs):
   - `GET /api/seller-catalog/{slug}` - Now checks both `users` and `sellers` collections
   - `POST /api/products/{slug}/filter` - Returns `sellerSlug` from either collection
   - `GET /api/products/{slug}/enterprise` - Includes `sellerSlug` in seller data

3. **Filter Endpoint Fix** (`/app/backend/routers/enterprise_products.py`):
   - Added `sellerSlug` to the result item dictionary (was missing before)
   - Fixed location display showing "None, None" when city/state are null
   - Now shows "India" as fallback location

4. **Seller Catalog Router Fix** (`/app/backend/routers/seller_catalog_router.py`):
   - `get_seller_by_slug()` now checks legacy `sellers` collection as fallback
   - Response building handles both nested `profile` structure (users) and flat structure (sellers)

**Testing Results:**
- Backend tests: 12/12 PASSED (100%)
- Seller catalog page loads correctly for legacy sellers
- Clickable seller names navigate to correct catalog page
- Products on catalog link to correct product detail pages

**API Verification:**
```
GET /api/seller-catalog/seller-de460c → 200 OK ✓
POST /api/products/.../filter → returns sellerSlug ✓
GET /api/products/.../enterprise → returns sellerSlug ✓
```

---

### Session: 2026-03-14 (Enhanced WhatsApp Inquiry Message)

#### Enhanced WhatsApp Message for Buyer-Seller Communication - COMPLETE ✅

**Problem:**
When buyers send inquiries via WhatsApp, the message was too basic:
```
Hello, I sent an inquiry on UdyogConnect.
Product: Safety Hand Gloves
Quantity: 1
Let's discuss further.
```
Sellers received minimal information and couldn't identify specific products.

**Solution:**
Enhanced the WhatsApp message to include comprehensive product details:
- Product specifications (from seller's searchableAttributes)
- Product description (truncated to 200 chars for readability)
- Product image URL (clickable link)
- Listed price and MOQ
- Quantity required

**New WhatsApp Message Format:**
```
Hello, I sent an inquiry on UdyogConnect.

🛒 *Product:* Industrial Electric Motor 5HP
📊 *Quantity Required:* 10 units
💰 *Listed Price:* ₹9,500 per unit
📦 *MOQ:* 5 units

📋 *Specifications:*
• Power: 5 HP
• Voltage: 415V
• Phase: 3 Phase
• RPM: 1440

📝 *Description:*
High-performance 5HP industrial electric motor suitable for various industrial applications...

🖼️ *Product Image:*
https://example.com/image.jpg

Let's discuss further.
```

**WhatsApp Limitation Note:**
WhatsApp's `wa.me` links only support text content - images cannot be directly attached. The product image is included as a clickable URL that sellers can view.

**Files Modified:**
- `/app/frontend/src/components/enterprise/InquiryModal.tsx` - Enhanced `handleWhatsAppConnect()` function, added `productDescription` prop
- `/app/frontend/src/app/products/[slug]/page.tsx` - Enhanced `handleWhatsAppConnect()` function
- `/app/frontend/src/app/seller-catalog/[slug]/SellerCatalogPage.tsx` - Updated `handleInquiry()` to pass product details, added description/images to modal
- `/app/frontend/src/app/ep/[slug]/page.tsx` - Added `productDescription` prop to InquiryModal

---

### Session: 2026-03-14 (Product Images in Seller Cards)

#### Added Product Images to Seller Cards - COMPLETE ✅

**Problem:**
Seller cards on product pages didn't display product images. Buyers couldn't see what they were inquiring about before clicking "Request Quote".

**Solution:**
Added a product image gallery section to the `StandardSellerCard` component:
- Displays the first product image prominently
- Navigation arrows for multiple images (prev/next)
- Thumbnail strip for quick image selection
- Image counter showing "1/3" etc.
- Responsive aspect ratio (16:9 on mobile, 21:9 on desktop)

**New Seller Card Layout:**
```
┌─────────────────────────────────────┐
│  5 HP | 415V | 3 Phase | 1440       │  ← Spec Strip
├─────────────────────────────────────┤
│                                     │
│      [PRODUCT IMAGE]                │  ← NEW: Product Image
│      < [1/2] >                      │     with navigation
├─────────────────────────────────────┤
│  ⭐ Best Price                      │
│  🏢 Seller Name • Manufacturer      │
│  📍 Location                        │
├─────────────────────────────────────┤
│  ₹9,500  │  MOQ: 5  │  Lead: 7d    │
├─────────────────────────────────────┤
│     [Request Quote]                 │
│     [View Details & Reviews]        │
└─────────────────────────────────────┘
```

**Files Modified:**
- `/app/frontend/src/components/product/StandardSellerCard.tsx`:
  - Added Image import from next/image
  - Added useState for image index tracking
  - Added ChevronLeft/ChevronRight icons
  - Added product image gallery section with navigation
  - Added thumbnail strip for multiple images

---

### Session: 2026-03-14 (Location Filter Added)

#### Added Location Filter to Product Page - COMPLETE ✅

**Problem:**
Buyers couldn't filter sellers by location. They had to scroll through all sellers manually to find ones in their preferred city/state.

**Solution:**
Added a "Filter by Location" dropdown below the "Sort By" section in the filter sidebar.

**Features:**
- Dropdown shows "All Locations" by default
- Lists unique cities/states from available sellers
- Filters sellers in real-time when location is selected
- Updates seller count to show "X sellers found in [Location]"
- "Clear location filter" link to reset
- Works in combination with spec filters and sort options

**UI Location:**
```
Filter by Specs
├── Power (HP)
├── Voltage (V)
├── Phase
├── RPM
├── Efficiency Class
├── Sort By         ← Price: Low to High
└── Filter by Location  ← NEW: All Locations dropdown
```

**Files Modified:**
- `/app/frontend/src/app/products/[slug]/page.tsx`:
  - Added `locationFilter` state
  - Added `filteredSellers` computed value using useMemo
  - Added "Filter by Location" dropdown UI
  - Updated seller count display to show filtered count
  - Updated empty state message for location filtering

---

### Session: 2026-03-14 (Seller Filter Added)

#### Added Seller Filter to Product Page - COMPLETE ✅

**Problem:**
Buyers couldn't filter to see products from a specific seller. If multiple sellers offer the same product, buyers had to scroll through all of them.

**Solution:**
Added a "Filter by Seller" dropdown below the "Filter by Location" section.

**Features:**
- Dropdown lists all sellers for the product
- Real-time filtering when seller is selected
- Works in combination with location filter
- Shows "X sellers found by [Seller Name]" count
- "Clear seller filter" link to reset

**UI Location:**
```
Filter by Specs
├── Power, Voltage, Phase, RPM, Efficiency Class
├── Sort By: Price: Low to High
├── Filter by Location: All Locations
└── Filter by Seller: All Sellers  ← NEW!
```

**Files Modified:**
- `/app/frontend/src/app/products/[slug]/page.tsx`:
  - Added `sellerFilter` state
  - Updated `filteredSellers` to filter by both location AND seller
  - Added "Filter by Seller" dropdown UI
  - Updated seller count display to show both filters
  - Updated empty state and clear filters logic

---




### Session: 2026-03-14 (Business Tools - Phase 1: RBAC Foundation)

#### Business Tools System - Phase 1 Implementation - COMPLETE ✅

**Overview:**
Implemented the foundation for a comprehensive Business Tools system for sellers, including Role-Based Access Control (RBAC), employee management, buyer/supplier CRM, and inventory tracking.

**New Collections Created:**
- `roles` - Seller-specific roles with permission flags
- `seller_buyers` - CRM for seller's customers
- `seller_suppliers` - Supplier management
- `inventory_logs` - Inventory adjustment tracking

**Extended Collections:**
- `users` - Added `accountType`, `sellerId`, `roleId`, `status` fields for employees
- `sellerListings` - Extended with `sku`, `lowStockAlert`, `warehouseLocation` fields

**Permission System:**
```
manage_listings    - Create, edit, delete product listings
manage_inventory   - Update stock levels and inventory
view_enquiries     - View buyer enquiries
manage_buyers      - Add, edit, delete buyer records
manage_suppliers   - Add, edit, delete supplier records
create_invoice     - Create and manage invoices
view_reports       - View sales and inventory reports
manage_employees   - Add, edit, deactivate employees
manage_roles       - Create and manage roles & permissions
```

**API Endpoints Created:**
- Roles: CRUD + permissions list + my-permissions
- Employees: CRUD with Firebase auth integration
- Buyers: CRUD with search
- Suppliers: CRUD with search
- Inventory: List, update, adjust stock, logs

**Frontend Pages Created:**
- `/seller/business-tools` - Main landing page
- `/seller/business-tools/roles` - Role management
- `/seller/business-tools/employees` - Employee management
- `/seller/business-tools/buyers` - Buyer CRM
- `/seller/business-tools/suppliers` - Supplier management
- `/seller/business-tools/inventory` - Stock tracking
- Placeholders for Invoices, Composite Products, Reports

**Testing Status (2026-03-14):**
- Backend: 23/23 tests passed (100% success rate) - Phase 1 RBAC
- Backend: 40/40 tests passed (100% success rate) - Phase 2-5 (ERP modules)
- Verified: All RBAC endpoints, role CRUD, employee CRUD, permission enforcement, role deletion constraints
- Verified: Composite Products CRUD + sell, Invoices CRUD + GST + PDF + auto-numbering, Reports (4 types), Activity Logs
- Firebase Auth: MOCKED in dev - uses dev fallback UID for employee creation
- Test files: `/app/backend/tests/test_business_tools_rbac.py`, `/app/backend/tests/test_business_tools_erp.py`

### Session: 2026-03-14 (Phase 2-6 Implementation)

**Composite Products (DONE - FINAL 2026-03-14):**
- **Product Identity** (name/category): From admin catalog via `GET /api/categories/all` → `GET /api/products/by-category/{id}` — seller CANNOT type product names
- **Components**: From seller's own inventory (`sellerListings`) via `GET /api/business-tools/composite-products/seller-inventory`
- Stock NOT stored independently - calculated dynamically: `min(component_stock / component_qty)`
- Price set manually by seller
- When created, sellerListing with `productType: "composite"` auto-created (uses compositeProductId as productId for index uniqueness)
- Form: Two sections — Product Identity (blue, from catalog) + Components (amber, from inventory)
- 27/27 tests passed

**Invoice System (DONE):**
- Auto-incrementing invoice numbers: INV-{sellerId_suffix}-{sequence}
- Per-item GST: each item has configurable gstPercent (0%, 5%, 12%, 18%, 28%)
- gstAmount = price * qty * gstPercent / 100, total = subtotal + gstAmount
- Stock deduction on invoice creation (with validation)
- PDF generation using ReportLab (seller/buyer details, items table, GST, totals)
- Status workflow: draft -> sent -> paid / cancelled
- Delete only draft/cancelled invoices
- Frontend: Full CRUD, PDF download, status management, buyer selection

**Reports Module (DONE):**
- Sales Summary: Monthly/Quarterly grouping with overall totals (revenue, GST, invoice count, avg)
- Product Sales: Top products by revenue from invoice items
- Inventory Status: Total items, low stock count, out of stock count
- Top Buyers: By invoice total with company info
- All with date range filters
- Frontend: Tab-based reports with bar charts, stat cards, tables

**Activity Log System (DONE):**
- Tracks: employee_created, role_created, stock_adjusted, buyer_created, supplier_created, invoice_created, composite_product_created, composite_product_sold
- Integrated into all existing routers (business_tools, inventory, composite products, invoices)
- Frontend: Timeline view with module filter, pagination, relative time display

**Permission Enforcement (DONE):**
- All new endpoints check RBAC permissions: manage_inventory (composite products), create_invoice (invoices), view_reports (reports), manage_roles (activity logs)
- HTTP 403 returned for unauthorized access
- Frontend: UI modules hidden based on permissions via layout navItems + hasPermission checks

**New Collections:**
- `composite_products` - Bundle definitions (sellerId, name, description)
- `composite_product_items` - Bundle components (compositeProductId, productId, quantity)
- `invoices` - Invoice records (invoiceNumber, sellerId, buyerId, items, subtotal, gst, total, status)
- `activity_logs` - Audit trail (sellerId, userId, action, module, entityId, timestamp)

**Extended Collections:**
- `users` - Added `invoiceCounter` field for auto-incrementing invoice numbers

**New API Endpoints:**
- Composite Products: GET/POST /composite-products, PUT/DELETE /composite-products/{id}, POST /composite-products/{id}/sell
- Invoices: GET/POST /invoices, GET /invoices/{id}, PUT /invoices/{id}/status, GET /invoices/{id}/pdf, DELETE /invoices/{id}
- Reports: GET /reports/sales-summary, /reports/product-sales, /reports/inventory-status, /reports/top-buyers
- Activity Logs: GET /activity-logs

**New Frontend Pages:**
- `/seller/business-tools/composite-products` - Full CRUD + sell
- `/seller/business-tools/invoices` - Full CRUD + PDF download + status management
- `/seller/business-tools/reports` - Tab-based reports with charts/tables
- `/seller/business-tools/activity-logs` - Audit timeline with filters

**Remaining/Future:**
- Refactor inline inquiry modal to use shared `InquiryModal.tsx`
- Advanced token-based search system
- Admin search insights dashboard
- Redis caching
- Refactor monolithic `server.py`

---


### Session: 2026-03-14

#### P0: Composite Products Marketplace Integration - COMPLETE

**What was done:**
Fully overhauled the Composite Products system so composite products behave exactly like regular marketplace products for buyers, while internally using component-based inventory management.

**Key Changes:**

1. **Backend - `composite_products_router.py` (full rewrite):**
   - Composite product creation now creates a `sellerListings` record with `productType: "composite"` and the admin `productId` (not the composite product's own ID)
   - This ensures composite products appear in: marketplace search, category pages, seller product pages, invoices, reports
   - Stock is dynamically calculated: `min(component_stock / component_qty)` for each component
   - `purchase_price` auto-calculated from component prices
   - `selling_price` manually set by seller
   - `sync_composite_stock()` helper recalculates stock whenever components change
   - `sync_all_composites_for_component()` triggers recalculation when any component's stock changes

2. **Backend - `inventory_router.py` updated:**
   - Returns `productType` field in inventory list for UI badge display
   - Manual stock adjustment blocked for composite products (400 error)
   - Stock quantity update via PUT blocked for composite products
   - After any regular stock adjustment, triggers composite stock recalculation for affected composites

3. **Backend - `invoice_router.py` updated:**
   - When invoicing a composite product, deducts stock from component items (not the composite listing)
   - Validates component stock before creating invoice
   - After deduction, recalculates composite stock via `sync_composite_stock()`
   - Creates proper inventory_logs for each component deduction

4. **MongoDB Index Update:**
   - Dropped old unique index `(productId, sellerId)` on `sellerListings`
   - Created new unique index `(productId, sellerId, productType)` to allow both regular AND composite listings for the same admin product

5. **Marketplace & Listing Integration:**
   - `productType` field added to marketplace search results (per-seller entry), listing detail response, and inventory API
   - Marketplace search returns both `single` and `composite` product types without filtering
   - Listing detail endpoint includes `productType` so buyers see it as a regular product

6. **Fallback Manual Linking (NEW):**
   - `POST /composite-products/{cp_id}/create-listing` endpoint for manually creating marketplace listing if auto-creation fails
   - Returns existing listing info if already linked
   - Frontend shows "Create Marketplace Listing" button on cards without a listing

7. **Composite Product Cards:**
   - Show "Listed" (green) or "Not Listed" (amber) badge indicating marketplace status
   - `hasListing`, `listingId`, `listingStatus` fields returned from API
   - Sell button only shown when listing exists and stock > 0

**Data Model - `sellerListings` for composite products:**
```
{
  sellerId: ObjectId,
  productId: ObjectId (admin product, for marketplace visibility),
  categoryId: ObjectId,
  productType: "composite",
  compositeProductId: ObjectId (links to composite_products collection),
  description: string,
  status: "active",
  isActive: true,
  stock: number (dynamically calculated),
  pricingTiers: [{minQty: 1, pricePerUnit: selling_price}],
  images: [],
  createdAt, updatedAt, lastStockUpdate, publishedAt
}
```

**Testing:**
- Iteration 51: 27/27 backend tests passed (100%)
- Iteration 52: 15/15 backend tests passed (100%) - listing integration features
- Test reports: `/app/test_reports/iteration_51.json`, `/app/test_reports/iteration_52.json`
- All features verified: CRUD, stock calculation, invoice deduction, RBAC, duplicate prevention, inventory integration, marketplace visibility, fallback manual linking

**Remaining/Future:**
- Refactor inline inquiry modal to use shared `InquiryModal.tsx`
- Advanced token-based search system
- Admin search insights dashboard
- Redis caching
- Refactor monolithic `server.py`
- Clean up unused Pydantic models in `business_tools.py`

---


#### Product Pricing System (Purchase Price + Selling Price) - COMPLETE

**What was done:**
Implemented a complete pricing system with `purchase_price` and `selling_price` fields on `sellerListings`, enabling profit tracking and financial reporting.

**Key Changes:**

1. **Backend Model (`business_tools.py`):**
   - Added `VIEW_PURCHASE_PRICE` permission to RBAC Permission enum
   - Added `purchase_price` and `selling_price` to `InventoryUpdate` model

2. **Inventory Router (`inventory_router.py`):**
   - Added `has_permission()` helper (non-throwing)
   - Returns `canViewPurchasePrice` flag in response
   - Completely removes `purchase_price` field (not null) when user lacks `view_purchase_price` permission
   - Accepts `purchase_price` and `selling_price` in inventory update
   - Blocks `purchase_price` change for composite products (400 error - auto-calculated)
   - Also updates `pricingTiers` when `selling_price` changes (for marketplace display)

3. **Reports Router (`reports_router.py`) - 3 new endpoints:**
   - `GET /reports/profit-summary` - Revenue, cost, profit, margin per month/quarter
   - `GET /reports/product-profit` - Per-product profit breakdown
   - `GET /reports/inventory-value` - Stock value and potential revenue per item

4. **Invoice Router (`invoice_router.py`):**
   - Stores `purchase_price` per item at invoice creation time
   - For composite products, dynamically calculates from component `purchase_price` fields
   - Enables profit tracking on historical invoice data

5. **Server.py:**
   - `ListingCreate` model accepts optional `purchase_price` and `selling_price`
   - Both stored on new and updated listings

6. **Composite Products:**
   - `purchase_price` dynamically calculated: `sum(component purchase_price * quantity)`
   - NOT permanently stored - recalculated on every read
   - Manual `purchase_price` change blocked for composite products

7. **Frontend - Inventory Page:**
   - Added Selling Price column (always visible)
   - Added Purchase Price column (conditional on `canViewPurchasePrice`)
   - Both editable in edit mode (composites excluded)

8. **Frontend - Reports Page:**
   - Added 3 new tabs: Profit Summary, Product Profit, Inventory Value
   - Profit summary shows revenue/cost/profit/margin with bar charts
   - Product profit shows per-product breakdown table
   - Inventory value shows stock value and potential revenue per item

**Access Control:**
- `purchase_price` field completely absent from API response for users without `view_purchase_price`
- Marketplace listing (`GET /api/listings/{id}`) does NOT expose `purchase_price`
- Invoices only show `selling_price` to buyers
- Reports require `view_reports` permission

**Testing:**
- Iteration 53: 10/10 passed, 2 skipped (manually verified)
- All report endpoints verified
- Composite purchase_price calculation verified (500*1 + 200*2 = 900)
- Purchase_price blocked for composite edits (400 error)
- Marketplace correctly hides purchase_price

---


#### Bug Fix: Inventory Pricing Input + Composite Price Control - COMPLETE

**Issue 1 - Inventory edit form auto-closes:**
- Root cause: `onBlur` handlers on each input field immediately called `handleUpdateInventory` which set `editingItem(null)` and triggered `loadInventory()` refresh
- Fix: Rewrote inventory page with proper controlled state management:
  - Edit values stored in `editState` (not individual onBlur handlers)
  - `isEditing` ref guards against auto-refresh while editing
  - Explicit Save/Cancel buttons - editor stays open until user clicks one
  - Inputs use `onChange` → state, not `onBlur` → API

**Issue 2 - Composite product selling_price locked:**
- Root cause: Frontend condition `item.productType !== 'composite'` blocked ALL editing for composites
- Fix: 
  - Edit button now shown for ALL products including composites
  - Selling price editable for both single and composite products
  - Purchase price input only shown for non-composite (shows "auto" for composites)
  - Stock adjustment button hidden for composites (shows "auto")
  - Backend: selling_price update syncs to `composite_products.price` for consistency

**Testing:** Iteration 54: 8/8 backend tests passed (100%)

---
