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
- **`get_effective_limits(db, user)`** — Core resolver: merges defaults + overrides, override wins
- **Backend is single source of truth** — No frontend-based limits

### Admin Override System
- `POST /api/admin/subscription/override` — Set per-seller overrides
- `GET /api/admin/subscription/override/{userId}` — Get current overrides
- `DELETE /api/admin/subscription/override/{userId}` — Clear overrides

### Admin Subscription Management UI
- Page: `/admin/subscriptions`
- Backend: `GET /api/admin/subscription/sellers` — Lists sellers with plan, status, usage, overrides, effective limits
- Features: Plan filter cards, search, usage bars, inline override editor, feature badges

## Completed Features
1-43. B2B Marketplace, Invoicing, Inventory, Panels Phase 1-3B, RBAC, Automation, Referral, Payouts, Central Subscription Guard
44. **Flexible SaaS Plan System + Admin Override (Mar 2026)**
    - Unified 4-plan system (removed trial/starter)
    - `get_effective_limits()` resolver with admin override merging
    - Admin CRUD endpoints for per-seller overrides
    - Fixed /access-level 500 error
    - Tests: 29/29 passed
45. **Admin Subscription Management UI (Mar 2026)**
    - Full admin page at /admin/subscriptions
    - Seller list with plan, status, usage bars, feature badges
    - Inline override editor (numeric + boolean toggles)
    - Search, plan filter, pagination
    - Tests: 12/12 passed

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
- `/app/backend/server.py` — Admin override & sellers list endpoints
- `/app/frontend/src/app/admin/subscriptions/page.tsx` — Admin subscription management UI
- `/app/frontend/src/context/SubscriptionContext.tsx` — Frontend subscription state
- `/app/frontend/src/app/admin/layout.tsx` — Admin sidebar nav
