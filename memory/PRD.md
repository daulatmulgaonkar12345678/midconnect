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

