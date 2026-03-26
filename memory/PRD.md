# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows with workflow automation.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client

## System Architecture: Decoupled Panels + Rules

### Core Principle
- **Panels = Data Layer** (schema + records only, no workflow logic)
- **Rules = Workflow Layer** (triggers, conditions, multi-target actions)
- **Single Source of Truth:** Data always flows from Source Panel -> Target Panels

### Automation Rule Contract (LOCKED)
```json
{
  "name": "string",
  "trigger_panel_id": "string (source panel ObjectId)",
  "trigger_type": "on_create | on_update | condition_based",
  "condition": { "field": "string", "operator": "string", "value": "string" },
  "targets": [
    {
      "target_panel_id": "string (custom panel ObjectId or system module ID)",
      "action_type": "create_record | create_records_per_item | update_record",
      "data_mode": "smart_sync | manual_only | full_copy",
      "relation_field": "string (optional)",
      "update_operation": "increment | decrement | set_value",
      "update_field": "string",
      "update_value_from": "string",
      "field_mappings": [
        { "target_field": "string", "source_field": "string", "default_value": "string", "mapping_type": "field | default | reference" }
      ],
      "field_visibility": [
        { "field": "string", "visible": true, "editable": true }
      ]
    }
  ],
  "is_active": true,
  "priority": 0
}
```

### Data Mode Behavior (LOCKED)
- **smart_sync** (default): Explicit mappings priority. Remaining target fields auto-fill from matching source field names.
- **manual_only**: Only explicitly mapped fields transfer. Most restrictive.
- **full_copy**: For each target field that exists in source, copy value. Explicit mappings override.

### System Modules Supported as Targets
inventory, invoices, buyers, suppliers, purchase_orders, quotations, composite_products, employees

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
- Validated: only known keys, correct types, user must exist

## Completed Features
1-25. B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions
26. Phase 3B: Smart Document Builder (Excel/PDF export)
27. Phase 4 Lite: Basic Automation (superseded)
28. **Phase 4 Full: Multi-Target Workflow Automation Engine (Mar 2026)**
29. **Phase 4.1: Data Mode + Preview (Mar 2026)**
30. **Bug Fix: Smart Sync relation field matching (Mar 2026)**
31. **Bug Fix: Update Record lookup field (Mar 2026)**
32. **ARCHITECTURE UPGRADE: Relational Update Engine (Mar 2026)**
33. **Field Visibility in Records UI (Mar 2026)**
34. **MATCH + UPDATE Engine Verification (Mar 2026)**
35. **System Modules in Rule Source/Trigger Panel (Mar 2026)**
36. **System Module Automation Hook — Invoices (Mar 2026)**
37. **Data Population Fix — Relation Auto-Linking (Mar 2026)**
38. **Per-Record PDF Download (Mar 2026)**
39. **Pricing & About Page Rewrite (Mar 2026)**
40. **Hybrid Referral + Sales Tracking System (Mar 2026)**
41. **Admin-Triggered Order Creation System (Mar 2026)**
42. **Admin Payout Management Module (Mar 2026)**
43. **Central Subscription Guard + SaaS Enforcement System (Mar 2026)**
44. **Flexible SaaS Plan System + Admin Override (Mar 2026)**
    - Unified 4-plan system: free/standard/pro/enterprise (removed trial/starter)
    - `get_effective_limits()` resolver in plan_features.py
    - Per-seller admin overrides: `subscriptions.overrides` field
    - Admin CRUD: POST/GET/DELETE /api/admin/subscription/override
    - Fixed /access-level 500 error (removed undefined MAX_PANELS_PER_BUSINESS)
    - Updated all enums, validators, frontend types to match 4-plan system
    - Tests: 29/29 passed (100%)

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
- `/app/backend/config/plan_features.py` — PLAN_CONFIG SSOT + get_effective_limits() resolver
- `/app/backend/middleware/subscription_guard.py` — enforce_subscription, check_resource_limit
- `/app/backend/services/subscription_service.py` — get_effective_subscription
- `/app/backend/services/subscription_engine.py` — Unified engine (activate/extend)
- `/app/backend/routers/panel_router.py` — Panel CRUD + /access-level endpoint
- `/app/backend/routers/automation_router.py` — Multi-target engine + subscription guard
- `/app/backend/routers/invoice_router.py` — Invoice CRUD + PDF export
- `/app/backend/routers/business_tools_router.py` — Buyer/Employee/Supplier CRUD
- `/app/backend/routers/inventory_router.py` — Inventory CRUD
- `/app/backend/routers/referral_router.py` — Referral + Sales + Orders + Payouts
- `/app/frontend/src/context/SubscriptionContext.tsx` — Frontend subscription state
- `/app/frontend/src/components/SubscriptionGates.tsx` — UI upgrade banners
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` — Panel config
- `/app/frontend/src/app/admin/payouts/page.tsx` — Admin Payout dashboard
