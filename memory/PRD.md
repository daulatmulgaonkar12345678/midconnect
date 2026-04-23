# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows with workflow automation.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client

## Subscription & Plan System (CURRENT — Mar 2026)

### Plans (4 tiers — NO trial, NO starter)
| Plan | maxPanels | maxRules | Export | Automation | maxEmployees |
|------|-----------|----------|--------|------------|--------------|
| free | 3 | 10 | No | No | 0 |
| standard | 10 | 50 | Yes | Yes | 15 |
| pro | 50 | 200 | Yes | Yes | Unlimited |
| enterprise | Unlimited | Unlimited | Yes | Yes | Unlimited |

### Limit Resolution (SSOT)
- **PLAN_CONFIG** (`config/plan_features.py`) — Default limits per plan
- **Per-Seller Overrides** — Admin-set custom limits in `subscriptions.overrides`
- **`get_effective_limits(db, user)`** — Core resolver: merges defaults + overrides
- **Backend is single source of truth** — No frontend-based limits

### Free Plan Behavior
- **Can view**: Panels, records, data, dashboard — all GET requests work
- **Cannot**: Create records/panels/invoices, export (Excel/PDF), run automation
- **Shows**: Formal "Upgrade" popup (UpgradeModal) when attempting gated actions
- **Backend**: Returns 403 with `FEATURE_NOT_AVAILABLE` or `SUBSCRIPTION_EXPIRED`

### Admin Override System
- `POST /api/admin/subscription/override` — Set per-seller overrides
- `GET /api/admin/subscription/override/{userId}` — Get current overrides
- `DELETE /api/admin/subscription/override/{userId}` — Clear overrides
- Admin UI at `/admin/subscriptions`

## Completed Features
1-43. B2B Marketplace, Invoicing, Inventory, Panels Phase 1-3B, RBAC, Automation, Referral, Payouts, Central Subscription Guard
44. Flexible SaaS Plan System + Admin Override (Mar 2026)
45. Admin Subscription Management UI (Mar 2026)
46. **Export Bug Fix + Free Plan Enforcement (Mar 2026)**
    - Fixed timezone-naive datetime crash on /export/outstanding (ensure_utc())
    - Added enforce_export_access() to all 14 export endpoints
    - Built UpgradeModal component with useUpgradeModal hook
    - Wired guards into Panels, Records, Reports, Invoices pages
    - Free users blocked from create/download with formal upgrade popup
    - Tests: 26/26 passed
47. **Admin Employees Page + Become-Seller Location Selector (Apr 2026)**
    - Admin Employee Management page at /admin/employees (list/delete employees)
    - Become-seller flow updated with State/City/Pincode location selector
    - Fixed deployment: backend SyntaxError in server.py, frontend TS null check
    - Added sidebar link for Employees in admin layout
48. **Seller Listing Publish/Draft Toggle (Apr 2026)**
    - POST /api/listings/{listing_id}/unpublish — active/paused → draft
    - Draft listings hidden from public search, visible to seller only
    - Toggle button on seller listings page + "Move to Draft" on edit page
    - Tests: 9/9 passed (iteration_123)
49. **GST Verification Bug Fix (Apr 2026)**
    - Fixed GST pending query to check multiple data locations (gst.status, gstStatus, isSeller, roles)
    - Fixed field name mismatch: backend now returns snake_case matching frontend interface
    - Verify endpoint now normalizes user data (adds "seller" to roles, sets isSeller)
    - Root cause: some production users have GST data in legacy field locations
50. **Employee Access Enforcement (Apr 2026)**
    - Admin-controlled employee blocking when `maxEmployees=0` in subscription overrides
    - Guard added in both `require_auth` (server.py) and `authenticate_user` (utils/permissions.py)
    - Covers ALL endpoints: server.py routes + business-tool routers (panels, invoices, POs, etc.)
    - Link employee endpoint also enforces maxEmployees limit before linking
    - Seller/admin users NOT blocked; only employees of that seller
    - Tests: 11/11 passed (iteration_124)
51. **Draft Products in Seller Business Tools (Apr 2026)**
    - Draft products now visible in ALL seller-side tools: dashboard, inventory, invoices, panels, reports, exports, composite products, analytics, product shares
    - Updated 9 routers: inventory_router, home_router, invoice_router, composite_products_router, export_import_router, reports_router, panel_router, product_share_router, analytics_router + server.py admin counts
    - Draft products remain hidden from public search and product pages (enterprise_products, search endpoints)
    - Tests: 22/22 passed (iteration_125), inventory endpoint manually verified with draft listings
52. **SEO System Overhaul (Apr 2026)**
    - Enhanced `seo_service.py`: titles (55-65 chars, city-aware), descriptions (140-160 chars), content (400-800 words with 5 H2 sections: Types, Applications, Buying Guide, Cities, Why UdyogConnect)
    - City location pages: `/products/{slug}/city/{city}` with unique 400+ word content, city-specific titles, internal cross-linking
    - Auto-SEO on product update: regenerates if fields weak/missing (skip manual edits)
    - Bulk update script: `scripts/update_seo_for_all_products.py` (--dry-run, --force)
    - City pages added to frontend sitemap
    - Fixed city_seo_service.py: now uses $lookup to match seller.profile.city
    - Tests: 18/18 passed (iteration_126)
53. **SEO Phase 2 — Enterprise Rich Snippets (Apr 2026)**
    - SEO_VERSION bumped to 3; content now 500-900 words with FAQ + Market Insights sections, titles include intent words (Best/Top/Compare) + pricing + year when available
    - City pages now emit full JSON-LD (Product with `areaServed`, AggregateOffer/Offer, city-scoped Breadcrumb, city-scoped FAQ, Organization)
    - Frontend SSR: moved JSON-LD from client `ProductJsonLd` → Next.js App Router layouts. Used route group `(main)` so city pages don't inherit main-product JSON-LD (zero duplicates)
    - Bulk script v3: queries `seoVersion < SEO_VERSION` OR weak content, writes `seoVersion` + `seoGeneratedAt`, preserves manually edited SEO
    - All JSON-LD validated against schema.org; graceful fallback when product data missing (defaults to "Request Quote" offer)
    - Tests: 23/23 passed (iteration_127)
54. **SEO v5 — Global Ranking Overhaul (Apr 2026)**
    - SEO_VERSION=5; thresholds tightened (title<50, desc<120, content<600 triggers regen)
    - Title fallback chain now carries intent+year even when no price (e.g. "Best GRN Test Product Prices in India (2026) | UdyogConnect")
    - Description v5 template: "{Product} suppliers in {region}. Prices start from ₹X. Compare verified manufacturers, dealers & distributors on UdyogConnect. Get best deals today."
    - SEO content 700-1124 words with mandatory 5-city H3 sections (Pune/Mumbai/Delhi/Ahmedabad/Bangalore) even when no seller data — boosts `{product} in {city}` rankings
    - Auto-SEO on CREATE + UPDATE now writes `seoVersion` + `seoGeneratedAt` fields; all 3 product creation paths in `server.py` updated
    - Sitemap `<lastmod>` format YYYY-MM-DD only (Google-compliant)
    - Removed legacy `/api/sitemap.xml` + `/api/robots.txt` (404s); only Next.js `/sitemap.xml` and `/robots.txt` remain
    - robots.txt cleaned: removed `/product/`, `/category/`, `/inquiries` disallows (unblocked indexing)
    - Admin endpoint `POST /api/admin/seo/bulk-regenerate` (supports `?dry_run=true` and `?force=true`) for one-shot production regen
    - Backend endpoint `GET /api/seo/sitemap-city-pages` returns only (productSlug, citySlug) pairs with active sellers — no thin pages
    - 14 dev products regenerated to v5

55. **Programmatic SEO Scaling — Intent + Template System (Apr 2026)**
    - Added `SUPPORTED_INTENTS = [price, buy, suppliers, wholesale, cheap]` + `TEMPLATE_TYPES = [MARKET, BUYER, LOCAL, EDUCATION]` to `seo_service.py`
    - `get_template_type(slug, city, intent)` — deterministic md5-based template picker
    - `generate_programmatic_content()` — template + intent-aware 1000-1250 word content generator; unique intent subsections (Price Trends, Buying Steps, Supplier Tiers, Wholesale Playbook, Affordability Strategies) force uniqueness
    - `generate_seo_title` + `generate_seo_description` extended with `intent` param → "Price of X in City (2026)", "Buy X in City" etc
    - `city_seo_service.get_city_page_data()` accepts `intent` param; returns `pageUrl` + `templateType` + `relatedIntents`
    - Backend routes: `GET /api/products/{slug}/city/{city}?intent=X` and `GET /api/products/{slug}/intent/{intent}/in/{city}` (path-based)
    - Frontend routes: `/products/[slug]/in/[city]` + NEW `/products/[slug]/[intent]/in/[city]` (invalid intent → 404)
    - Shared SSR renderer at `/app/frontend/src/lib/cityPageRenderer.tsx` used by both routes (no UI duplication)
    - Self-canonical URLs on city + intent pages → each can be independently indexed
    - `generate_internal_links` now emits real `/in/city` URLs + `intentCityPages` for 3 cities × 5 intents per product (up to 15 programmatic links per product page)
    - Sitemap scales from 17 URLs → 41 URLs now (8 static + 7 products + 2 cats + 4 city + 20 intent) with hard safety cap at 45,000
    - **Content uniqueness validated**: Jaccard 5-gram similarity dropped from 99% (same-template) to 58-77% across intent variants
    - Fully backward compatible — existing URLs, UI, and APIs unchanged
    - Sample URLs:
      - Main: `/products/ss304-round-bar-steel-raw-materials-supplier-india`
      - City: `/products/ss304-round-bar-steel-raw-materials-supplier-india/in/mumbai`

48. **Homepage Console Cleanup + null:1 404 + Seller Catalog Fixes (Apr 2026)**
    - Removed preload warnings + `null:1 404` + fixed seller catalog 404 for null-slug sellers
    - **Root cause #1 (preload warnings)**: React 19's `ReactDOM.preload()` auto-preloaded image URLs from RSC Flight payload
    - **Root cause #2 (`null:1 404`)**: Broken `<Link>` rendered `href=/seller-catalog/.../category/null` when `categorySlug` was null
    - **Root cause #3 (seller 404)**: Sellers like `Matrix Green Enterprise Private Limited` had `sellerSlug: null` in DB but URLs used slugified company name. Backend's `get_seller_by_slug` only checked DB `sellerSlug` field, didn't try matching by slugified companyName.
    - **Seller Catalog** now shows ALL products per category (previously capped at 4).
    - **Fixes:**
      - `HeroSearchSection.tsx` → Server Component + `fetchPriority="high"`
      - `layout.tsx` → Removed duplicate `icons` metadata
      - `page.tsx` → Stripped RSC payload; converted Featured Products `<img>` → `<Image>`
      - `CategoryCard.tsx` → Explicit `loading="lazy"`
      - `SellerCatalogPage.tsx:343` → Guarded `<Link>` for null `categorySlug`; `|| product.productId` fallback for product slug links
      - `SellerCatalogPage.tsx:34` → Fetches `products_per_category=500`
      - `seller_catalog_router.py` → Raised limit `le=20` → `le=500`; added `_slugify()` + name-based fallback in `get_seller_by_slug` with auto-backfill of `sellerSlug` on first match
    - Preview verified: 0 console warnings, 0 errors; slugify matches all test cases
    - **Production requires Vercel redeploy AND backend redeploy on Render**
    - Files: `HeroSearchSection.tsx`, `layout.tsx`, `page.tsx`, `CategoryCard.tsx`, `SellerCatalogPage.tsx`, `seller_catalog_router.py`

## Prioritized Backlog
### P0 (Next)
1. Session Control (Device tracking + max devices per plan)
2. Document Builder Templates: customizable PDF with {{variables}}

### P1
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls

### P2
- GSTR-1 JSON export | Custom Material Report
- White-label toggle | WhatsApp Business API

## Key Files
- `/app/backend/config/plan_features.py` — PLAN_CONFIG SSOT + get_effective_limits()
- `/app/backend/middleware/subscription_guard.py` — enforce_subscription, check_resource_limit
- `/app/backend/routers/export_import_router.py` — ensure_utc(), enforce_export_access()
- `/app/frontend/src/components/SubscriptionGates.tsx` — UpgradeModal, useUpgradeModal, FeatureGate
- `/app/frontend/src/app/admin/subscriptions/page.tsx` — Admin subscription management UI
- `/app/frontend/src/context/SubscriptionContext.tsx` — Frontend subscription state
