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

26. **Phase 3B: Smart Document Builder (Mar 2026)** - LATEST:
    - Excel export: styled .xlsx with header formatting, relation field resolution, auto-width columns
    - PDF export: professional layout with reportlab, table styling, relation resolution, landscape for wide panels
    - Export buttons on panel records page with loading states, disabled when no records
    - Invalid ObjectId returns 400 (not 500) for both export endpoints
    - Exports are strictly READ-ONLY — no automation triggered during export

27. **Phase 4 Lite: Workflow Automation Engine (Mar 2026)** - LATEST:
    - Full CRUD: create, list, update, delete automation rules
    - Rule Builder UI: trigger panel selection, IF condition, THEN action via relation fields
    - Condition operators: equals, not_equals, greater_than, less_than, contains, not_empty, is_empty
    - Action operations: increment, decrement, set_value, create_record
    - Safety: ONLY custom panels can trigger automation (system modules blocked)
    - Relation-based actions: updates must go through a relation field (no blind/global updates)
    - Blocked system fields: _id, sellerId, createdAt, updatedAt, createdBy cannot be modified
    - Infinite loop prevention: _visited_rules set prevents re-execution in automation chains
    - Execution logging: success/error/skipped status with timestamps
    - System module support: inventory stock fields (stock, quantity, minStock, reorderPoint)
    - Sidebar link: Automation visible to admin users only (desktop + mobile)
    - Max 50 rules per business, max 5 actions per rule

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

Automation Rule:
{
  name, is_active, sellerId,
  trigger_panel_id (custom only),
  condition: { field, operator, value },
  actions: [{ type, target_panel_id, target_panel_type, relation_field, operation, field, value_from }],
  execution_count, last_executed
}
```

## Prioritized Backlog
### P0 (Next)
1. **Document Builder Templates**: Customizable PDF templates with {{variables}} for professional document generation

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
- `/app/backend/routers/panel_router.py` - Panel CRUD, export endpoints, automation hooks
- `/app/backend/server.py` - Router registration
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` - Rule Builder UI
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Records + export buttons
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/RelationField.tsx` - Reusable relation dropdown
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Sidebar with Automation link
