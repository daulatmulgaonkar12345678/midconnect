# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client (employee access sync)
- **Offline:** IndexedDB (idb), Service Worker

## System Flow (Panel → Entity Binding → Rule)
```
1. PANEL CREATION:
   User creates Custom Panel → selects Relation type → picks "Inventory"
   → SECOND DROPDOWN appears: "Binding Variable (Common Field)"
   → Shows: Product Name, SKU, Stock, Quantity, etc.
   → User picks "Product Name"
   → System auto-labels: "Product Name (Linked to Inventory)"
   → Stores: { key: "product_name", relatedPanel: "inventory", bindingField: "productName" }

2. DATA ENTRY:
   User selects "Product Name = Cable Drum" in RelationField dropdown
   System stores: { product_name: "sellerListing_id_123" }
   User sees name → system uses ID

3. RULE CREATION:
   Trigger: Custom Panel (dropdown)
   Condition: field (dropdown) + operator (dropdown) + value (dropdown if options exist)
   Relation Field: "Product Name (Linked to Inventory)" (shows binding info)
   Target Panel: AUTO-SET from relation (read-only, locked)
   Target Field: dropdown (Stock, Quantity, etc.)
   Operation: Increment/Decrement/Set Value (dropdown)
   Value From: trigger panel data fields (dropdown)

4. EXECUTION:
   Get source record → Extract product_id from relation field
   → Find inventory record with same product_id → Apply operation
```

## Completed Features

### Phase 1-2: Core Platform (Previous)
1-25. B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions, RelationField Component

### Phase 3B: Smart Document Builder (Mar 2026)
- Excel/PDF export with styled formatting, relation resolution
- Export buttons with loading states, disabled when empty
- Exports strictly READ-ONLY (no automation triggered)

### Phase 4 Lite: Workflow Automation (Mar 2026)
- Full CRUD, condition operators (7), action operations (increment/decrement/set_value/create_record)
- Safety: ONLY custom panels trigger, relation-based actions, system fields blocked
- Infinite loop prevention via _visited_rules set
- Execution logging (success/error/skipped)

### Phase 4 UX Overhaul (Mar 2026) - LATEST
- **Panel Creation**: "Connect Panel With (Entity)" section
- **Binding Variable**: When adding relation field, after selecting target, second dropdown shows target's fields so user picks the common reference field
- **Auto-label**: "Product Name (Linked to Inventory)" generated from binding selection
- **systemManaged fields**: Auto-created relation fields locked (Lock icon, can't delete)
- **Rule Builder**: Target panel auto-derived from relation field (read-only display)
- **Dropdown-only**: Condition values dropdown for fields with options, all selections are dropdowns
- **Module Fields API**: `GET /api/business-tools/panels/module-fields/{module_id}` returns available fields for any system module or custom panel
- **bindingField stored**: Added to PanelFieldInput and AddFieldRequest Pydantic models

## System Rules (Enforced)
1. No free text — only dropdowns everywhere in rule builder
2. Auto relation field only — systemManaged fields can't be deleted
3. Binding variable required — user must select common field when creating relation
4. Target auto-derived — relation field determines the target panel (no manual selection)
5. System modules only update via automation rules, never directly

## Prioritized Backlog
### P0 (Next)
1. Document Builder Templates: customizable PDF with {{variables}}

### P1
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
3. Seller Reminder Controls

### P2
- GSTR-1 JSON export | Custom Material Report
- White-label toggle | WhatsApp Business API
- "Request Upgrade" button

### Future
- Many-to-many relations, deep chaining
- Advanced automation: webhooks, email notifications, scheduled triggers

## Key Files
- `/app/backend/routers/automation_router.py` - Automation CRUD + execution engine with loop prevention
- `/app/backend/routers/panel_router.py` - Panel CRUD, module-fields API, export endpoints, automation hooks, bindingField support
- `/app/backend/server.py` - Router registration
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` - Rule Builder with auto-derived targets
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel config with binding variable dropdown
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Records + export buttons
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/RelationField.tsx` - Reusable relation dropdown
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Sidebar with Automation link
