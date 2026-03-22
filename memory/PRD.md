# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client (employee access sync)
- **Offline:** IndexedDB (idb), Service Worker

## Completed Features
1-25. (Previous features - B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions, RelationField Component)

26. **Phase 3B: Smart Document Builder (Mar 2026)**:
    - Excel export: styled .xlsx with header formatting, relation field resolution, auto-width columns
    - PDF export: professional layout with reportlab, table styling, relation resolution, landscape for wide panels
    - Export buttons on panel records page with loading states, disabled when no records
    - Exports are strictly READ-ONLY — no automation triggered during export

27. **Phase 4 Lite: Workflow Automation Engine (Mar 2026)**:
    - Full CRUD: create, list, update, delete automation rules
    - Condition operators: equals, not_equals, greater_than, less_than, contains, not_empty, is_empty
    - Action operations: increment, decrement, set_value, create_record
    - Safety: ONLY custom panels can trigger automation (system modules blocked)
    - Relation-based actions: updates must go through a relation field (no blind/global updates)
    - Blocked system fields: _id, sellerId, createdAt, updatedAt, createdBy cannot be modified
    - Infinite loop prevention: _visited_rules set prevents re-execution in automation chains
    - Execution logging: success/error/skipped status with timestamps
    - Max 50 rules per business, max 5 actions per rule

28. **Phase 4 Lite UX Overhaul (Mar 2026)** - LATEST:
    - **Panel Creation**: "Connect Panel With (Entity)" replaces "Link This Panel To"
    - **systemManaged fields**: Auto-created relation fields marked `systemManaged: true`, shown with Lock icon, cannot be deleted
    - **Better labels**: "Product (Linked to Inventory)", "Invoice (Linked to Invoices)"
    - **Auto-derived target**: Rule Builder auto-derives target panel from selected relation field (read-only display, no dropdown)
    - **Dropdown-only conditions**: When condition field is dropdown/multiselect, value input becomes dropdown of options
    - **Filtered field lists**: Condition field and Value From exclude relation fields (only show data fields)
    - **No free text**: All field selection in rule builder uses dropdowns

## System Flow (Panel → Entity Binding → Rule)
```
1. PANEL CREATION:
   - User creates Custom Panel → "Connect Panel With (Entity)" → selects Inventory
   - System auto-creates: "Product (Linked to Inventory)" relation field (systemManaged, locked)
   
2. DATA ENTRY:
   - User selects "Product Name = Cable Drum" in RelationField dropdown
   - System stores: { product: "sellerListing_id_123" }
   - User sees name, system uses ID

3. RULE CREATION:
   - Trigger: Custom Panel (dropdown)
   - Condition: field (dropdown, excludes relations) + operator (dropdown) + value (dropdown if field has options)
   - Relation Field: auto-created field (e.g., "Product (Linked to Inventory)")
   - Target Panel: AUTO-SET from relation field (read-only, locked)
   - Target Field: dropdown (e.g., Stock, Quantity, Min Stock)
   - Operation: dropdown (Increment/Decrement/Set Value)
   - Value From: dropdown (trigger panel data fields, excludes relations)

4. RULE EXECUTION:
   - Get source record → Extract product_id from relation field
   - Find inventory record with same product_id
   - Apply operation to selected target field
```

## System Rules (Enforced)
1. No free text — only dropdowns everywhere in rule builder
2. Auto relation field only — user cannot manually create system relation fields
3. Same entity only — relation determines the target (Inventory via Product relation)
4. Lock binding — once set, systemManaged fields cannot be changed or deleted
5. One binding per module — each module link creates exactly one relation field

## Prioritized Backlog
### P0 (Next)
1. **Document Builder Templates**: Customizable PDF templates with {{variables}}

### P1
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
3. Seller Reminder Controls (configurable schedules)

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking | White-label toggle | WhatsApp Business API
- "Request Upgrade" button for sellers

### Future
- Many-to-many relations, deep chaining
- Advanced automation: webhooks, email notifications, scheduled triggers

## Key Files
- `/app/backend/routers/automation_router.py` - Automation CRUD + execution engine with loop prevention
- `/app/backend/routers/panel_router.py` - Panel CRUD, export endpoints, automation hooks, systemManaged fields
- `/app/backend/server.py` - Router registration
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` - Rule Builder UI with auto-derived targets
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel config with "Connect Panel With (Entity)"
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Records + export buttons
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/RelationField.tsx` - Reusable relation dropdown
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Sidebar with Automation link
