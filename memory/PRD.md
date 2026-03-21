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

23. **Phase 3A: Granular Module Permissions + Panel Data Integration (Mar 2026)** - NEW:
    - **Module permissions upgraded** from simple boolean to `{view: bool, edit: bool}` per module
    - **PermissionGrid UI** shows [View] [Edit] checkboxes per system module, [View] [Create] [Edit] per custom panel
    - **Role templates** updated: Admin (full), Manager (no employees/settings edit), Viewer (view-only), etc.
    - **Panel Data Integration with Invoices**: Users can attach related panel records to invoices
    - **New API**: `GET /panels/related-records?module=inventory&entityId={id}` discovers panel records related to products
    - **Invoice storage**: `linkedPanels: [{panelId, recordId}]` stored in invoice documents
    - **Invoice display**: `linkedPanelData` resolved on read with panel name, color, and field values
    - **Frontend**: "Attach Panel Data" button in invoice form, panel picker modal, linked data display in invoice view
    - **Bug fix**: `resolve_seller_id` no longer returns None for admin-seller users

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

Backward Compatibility (normalize_permissions handles):
  1. Old: {inventory: {view: true, action: true}} → {modules: {inventory: {view: true, edit: true}}}
  2. Boolean: {modules: {inventory: true}} → {modules: {inventory: {view: true, edit: true}}}
  3. New format passes through unchanged

Backend Enforcement:
  - check_user_permission maps permission strings to (module, level):
    create_invoice → (invoices, edit), view_reports → (reports, view), etc.
  - check_panel_access(user, panel_id, action) in panel_router
  - Panel attachment: requires modules.invoices.edit + panels[panelId].canView
```

## Panel Data Integration (Phase 3A)
```
Flow: Invoice Creation → Attach Panel Data → Select Related Records → Store References

API: GET /panels/related-records?module=inventory&entityId={listingId}
  → Scans panels with relation fields pointing to 'inventory'
  → Returns records where relation field matches entityId
  → Grouped by panel: {panelId, panelName, panelColor, records: [{id, data}]}

Invoice Document:
  linkedPanels: [{panelId: "...", recordId: "..."}]  // stored on create
  linkedPanelData: [{panelId, panelName, panelColor, recordId, data: {field: value}}]  // resolved on read
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
- `/app/backend/utils/permissions.py` - normalize_permissions (3 formats), check_user_permission (view/edit)
- `/app/backend/routers/employee_mgmt_router.py` - ModulePermission(view,edit), EmployeePermissions, CRUD
- `/app/backend/routers/panel_router.py` - check_panel_access, related-records API
- `/app/backend/routers/invoice_router.py` - linkedPanels storage + linkedPanelData resolution
- `/app/backend/models/business_tools.py` - LinkedPanelRef model
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - canView(mp.view), canAction(mp.edit), panel methods
- `/app/frontend/src/app/seller/business-tools/employees/page.tsx` - PermissionGrid with View/Edit
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Attach Panel Data, picker modal, display
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Sidebar with sidebarPanels, showPanelsSection
