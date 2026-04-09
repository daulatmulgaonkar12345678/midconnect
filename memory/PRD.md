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
