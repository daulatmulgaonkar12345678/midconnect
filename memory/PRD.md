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
1-22. (Previous features - B2B Marketplace, Invoices, Inventory, Panel System Phase 1-2, RBAC, Employee Permissions Architecture)

23. **Phase 3A: Granular Module Permissions + Panel Data Integration (Mar 2026)**:
    - Module permissions upgraded from simple boolean to `{view, edit}` per module
    - PermissionGrid UI with [View] [Edit] checkboxes per system module, [View] [Create] [Edit] per custom panel
    - Role templates updated: Admin (full), Manager (no employees/settings edit), Viewer (view-only)
    - Panel Data Integration with Invoices: attach related panel records to invoices
    - New API: `GET /panels/related-records?module=inventory&entityId={id}`
    - Invoice storage: `linkedPanels: [{panelId, recordId}]` stored in invoice documents
    - Invoice display: `linkedPanelData` resolved on read with panel name, color, and field values
    - Bug fix: `resolve_seller_id` no longer returns None for admin-seller users

24. **Phase 3A (Part 2): Panel Binding UI & Controlled Linking (Mar 2026)** - LATEST:
    - **Panel Configuration UI**: "Link This Panel To" section in create/edit modal
    - **Module Linking**: Checkboxes for Inventory and Invoices modules
    - **Panel Linking**: Dropdown to link up to 2 other panels with validation
    - **Linking Rules**: No self-linking, no circular linking, max 2 linked panels
    - **Auto-add Relation Fields**: System auto-adds required Product/Invoice relation fields when modules are linked
    - **Unique Field Support**: "Unique" checkbox on field definitions, enforced at DB level
    - **Activity Logging**: `PANEL_RECORD_CREATED` events logged with productId, qcNumber references
    - **UI Badges**: Panel cards display linked modules/panels as colored badges
    - **Backend**: `allowedPanels` added to panel schema, `validate_allowed_panels` helper for rules enforcement

25. **RelationField Component Fix (Mar 2026)** - LATEST:
    - Created reusable `RelationField.tsx` component for searchable relation dropdowns
    - Debounced API calls (300ms) to `/relation-lookup` endpoint
    - Loading spinner, empty state ("No results found"), outside-click-to-close
    - Displays product name + SKU for inventory, invoice number + buyer name for invoices
    - Selected value shown as chip with clear button
    - Pre-populates resolved labels when editing existing records
    - Works for inventory, invoices, and custom panel relations
    - **Critical Backend Fix**: relation-lookup for inventory now queries `sellerListings` (with `$lookup` to `products`) instead of `products` directly — matching the inventory system's architecture
    - **Validation Fix**: inventory relation validation now checks `sellerListings` collection
    - **Display Fix**: resolved relation display joins `sellerListings` with `products` for name

## Permission Architecture
```
DB Schema (users.employeePermissions):
{
  "modules": {
    "dashboard": { "view": true, "edit": true },
    "inventory": { "view": true, "edit": false },
    "invoices": { "view": true, "edit": true }
  },
  "panels": {
    "<panelId>": {
      "canView": true,
      "canCreate": true,
      "canEdit": false
    }
  }
}
```

## Panel System Architecture
```
Panel Config:
{
  panelId, name, slug, description, icon, color,
  fields: [{ key, label, type, required, unique, options, relatedPanel, relationType }],
  allowedModules: ["inventory", "invoices"],
  allowedPanels: ["<panelId1>", "<panelId2>"]
}

Auto-generated Fields:
- If allowedModules includes "inventory" → auto-add Product relation field (required)
- If allowedModules includes "invoices" → auto-add Invoice relation field (required)

Linking Rules:
- Max 2 allowedPanels per panel
- No self-linking (panel cannot link to itself)
- No circular linking (if A→B, then B→A is blocked)
- Only existing panels can be linked

Activity Log:
- Collection: panel_activity_logs
- Event: PANEL_RECORD_CREATED
- Fields: type, panelId, panelName, recordId, sellerId, createdBy, timestamp, productId, qcNumber
```

## Prioritized Backlog
### P0 (Next)
1. **Panel System Phase 3B**: Document Builder (templates + {{variables}} + PDF/Excel export)

### P1
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
3. Seller Reminder Controls (configurable schedules)

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking | White-label toggle | WhatsApp Business API
- "Request Upgrade" button for sellers

### Future
- Automation Engine (rules, triggers, IF/THEN logic) - Phase 4
- Many-to-many relations, deep chaining

## Key Files
- `/app/backend/utils/permissions.py` - normalize_permissions, check_user_permission
- `/app/backend/routers/employee_mgmt_router.py` - ModulePermission, EmployeePermissions, CRUD
- `/app/backend/routers/panel_router.py` - Panel CRUD, validate_allowed_panels, auto-add relation fields, activity logging
- `/app/backend/routers/invoice_router.py` - linkedPanels storage + resolution
- `/app/backend/models/business_tools.py` - LinkedPanelRef model
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - canView, canAction, panel methods
- `/app/frontend/src/app/seller/business-tools/employees/page.tsx` - PermissionGrid
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Attach Panel Data
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel config with linking UI
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Record CRUD with RelationField integration
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/RelationField.tsx` - Reusable searchable relation dropdown
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Sidebar with sidebarPanels
