# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Storage:** Cloudinary | **PDF:** reportlab, PyPDF2 | **Email:** Resend (MOCKED)
- **PWA:** Service Worker + manifest.json | **Offline:** IndexedDB (via idb library)
- **Real-time:** python-socketio + socket.io-client (for employee access sync)

## Completed Features
1-16. (Previous features - B2B Marketplace, Invoices, Inventory, etc.)
17. **RBAC Fix (Mar 2026)**
18. **Employee Pending Tab Fix (Mar 2026)**
19. **Custom Panel System - Phase 1 (Mar 2026)**: Panel CRUD, Field Builder (8 types), sidebar integration, max 10 panels/20 fields
20. **Business Tool Access Control (Mar 2026)**: 3-tier (None/Standard/Advanced), admin-controlled, global gating
21. **Custom Panel System - Phase 2 (Mar 2026)**:
    - Record CRUD, data validation, relation system (many-to-one, one-to-one)
    - Relation lookup API, relation resolution, safety rules
    - Field editing, deletion protection, role-based access
    - Pagination + search, frontend CRUD UI
22. **Employee Permissions Architecture Upgrade (Mar 2026)** - NEW:
    - Migrated from flat `{module: {view, action}}` to separated `{modules: {module: bool}, panels: {panelId: {canView, canCreate, canEdit}}}`
    - Dynamic modules API (`/employee-mgmt/modules`) returns system modules + custom panels
    - Granular panel permissions: canView, canCreate, canEdit per panel per employee
    - Backend enforcement in panel_router via `check_panel_access()`
    - Frontend PermissionGrid with separate System Modules and Custom Panels sections
    - Sidebar shows panels based on employee's `permittedPanels` from my-access
    - Full backward compatibility via `normalize_permissions()` for old format data
    - Role templates updated to new format

## Permission Architecture
```
DB Schema (users.employeePermissions):
  {
    "modules": {
      "dashboard": true,
      "inventory": true,
      "invoices": false,
      ...
    },
    "panels": {
      "<panelId>": {
        "canView": true,
        "canCreate": true,
        "canEdit": false
      }
    }
  }

Backend Enforcement:
  - System modules: check_user_permission() maps old permission strings to modules
  - Panels: check_panel_access(user, panel_id, action) in panel_router
    - GET records/panel: requires canView
    - POST records: requires canCreate
    - PUT records: requires canEdit
    - DELETE records: requires canEdit
    - Panel structure management: admin only (unchanged)

API Endpoints:
  GET  /employee-mgmt/modules        -> {modules: [...], panels: [...]}
  GET  /employee-mgmt/role-templates  -> {templates: {name: {modules: {}, panels: {}}}}
  GET  /employee-mgmt/my-access       -> {permissions: {modules, panels}, permittedPanels: [...]}
  GET  /employee-mgmt/list            -> employees with normalized permissions
  POST /employee-mgmt/link            -> accepts {modules, panels} permissions
  PUT  /employee-mgmt/{id}            -> accepts {modules, panels} permissions
```

## Panel System Architecture
```
Database Collections:
  panels          -> { sellerId, name, slug, description, icon, color, fields[], createdAt, updatedAt }
  panel_records   -> { panelId, sellerId, data: {key: value}, createdBy, createdAt, updatedAt }

API Endpoints (all under /api/business-tools):
  Panel CRUD:
    GET    /panels                              -> List panels
    GET    /panels/{id}                         -> Get single panel (admin or employee with canView)
    POST   /panels                              -> Create panel (admin only)
    PUT    /panels/{id}                         -> Update panel metadata (admin only)
    DELETE /panels/{id}                         -> Delete panel (admin only, if no records)
  
  Field Management:
    POST   /panels/{id}/fields                  -> Add field (admin only)
    PUT    /panels/{id}/fields/{key}            -> Update field
    DELETE /panels/{id}/fields/{key}            -> Delete field
    PUT    /panels/{id}/fields-order            -> Reorder fields
  
  Record CRUD (permission-enforced):
    GET    /panels/{id}/records                 -> List records (canView)
    GET    /panels/{id}/records/{rid}           -> Get record (canView)
    POST   /panels/{id}/records                 -> Create record (canCreate)
    PUT    /panels/{id}/records/{rid}           -> Update record (canEdit)
    DELETE /panels/{id}/records/{rid}           -> Delete record (canEdit)
  
  Relations:
    GET    /panels/{id}/relation-lookup         -> Search linkable entities (canView)
    GET    /panels/linkable-targets             -> List linkable modules

Field Types: text, number, date, dropdown, multiselect, boolean, longtext, relation
Relation Types: many_to_one (default), one_to_one
Limits: 10 panels/business, 20 fields/panel, 50 records/page
```

## Prioritized Backlog
### P0 (Next)
1. **Panel System Phase 3**: Basic document builder (templates + {{variables}} + PDF/Excel), branding, shareable links

### P1
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
3. Seller Reminder Controls (configurable schedules)
4. Quotation/Employee Activity Dashboards

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- "Request Upgrade" button for sellers

### Future (Post Phase 3)
- Automation Engine (rules, triggers, IF/THEN logic)
- Many-to-many relations
- Deep chaining (>2 levels)

## Key Files
- `/app/backend/routers/employee_mgmt_router.py` - Employee CRUD, permissions (new architecture)
- `/app/backend/routers/panel_router.py` - Panel + Record CRUD, relation lookup, check_panel_access
- `/app/backend/utils/permissions.py` - normalize_permissions, check_user_permission, auth
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - canView/canAction/canViewPanel/canCreatePanel/canEditPanel
- `/app/frontend/src/app/seller/business-tools/employees/page.tsx` - Employee management UI with dynamic PermissionGrid
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - RBAC layout, sidebar with dynamic panels
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel management UI
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Record list + CRUD UI
- `/app/frontend/src/app/admin/users/[id]/page.tsx` - Admin user profile with access control
- `/app/backend/server.py` - Admin endpoints, auth
