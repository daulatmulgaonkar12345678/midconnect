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
    - Sample URLs:
      - Main: `/products/ss304-round-bar-steel-raw-materials-supplier-india`
      - City: `/products/ss304-round-bar-steel-raw-materials-supplier-india/in/mumbai`

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
