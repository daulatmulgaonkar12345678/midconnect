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
1-16. (Previous features — B2B Marketplace, Invoices, Inventory, etc.)
17. **RBAC Fix (Mar 2026)**
18. **Employee Pending Tab Fix (Mar 2026)**
19. **Custom Panel System — Phase 1 (Mar 2026)**: Panel CRUD, Field Builder (8 types), sidebar integration, max 10 panels/20 fields
20. **Business Tool Access Control (Mar 2026)**: 3-tier (None/Standard/Advanced), admin-controlled, global gating
21. **Custom Panel System — Phase 2 (Mar 2026)** ← NEW:
    - **Record CRUD**: Create/edit/view/delete records with dynamic forms based on panel field definitions
    - **Data Validation**: Required fields enforced, dropdown/multiselect options validated, boolean/number type checking
    - **Relation System V1**: many→one (default) and one→one linking to Inventory, Invoices, or other custom panels
    - **Relation Lookup API**: Searchable dropdown that fetches products, invoices, or panel records
    - **Relation Resolution**: When viewing records, relation values auto-resolve to display labels
    - **Safety Rules**: Block deletion of linked records, one-to-one uniqueness enforced, disabled fields skipped
    - **Field Editing**: Update label, toggle required, update options, soft disable (disabled flag)
    - **Field Deletion Protection**: Cannot delete field if records contain data for it
    - **Role-Based Access**: Seller admin = full control, Employees = create/edit records only, Buyers = blocked
    - **Pagination + Search**: Records list paginated (50/page), search across text/longtext/dropdown fields
    - **Frontend**: Full panel detail page with records table, create/edit modal, view modal, relation lookup UI

## Panel System Architecture
```
Database Collections:
  panels          → { sellerId, name, slug, description, icon, color, fields[], createdAt, updatedAt }
  panel_records   → { panelId, sellerId, data: {key: value}, createdBy, createdAt, updatedAt }

API Endpoints (all under /api/business-tools):
  Panel CRUD:
    GET    /panels                              → List panels
    GET    /panels/{id}                         → Get single panel
    POST   /panels                              → Create panel
    PUT    /panels/{id}                         → Update panel metadata
    DELETE /panels/{id}                         → Delete panel (if no records)
  
  Field Management:
    POST   /panels/{id}/fields                  → Add field
    PUT    /panels/{id}/fields/{key}            → Update field (label, required, options, disabled)
    DELETE /panels/{id}/fields/{key}            → Delete field (blocked if data exists)
    PUT    /panels/{id}/fields-order            → Reorder fields
  
  Record CRUD:
    GET    /panels/{id}/records                 → List records (paginated, searchable)
    GET    /panels/{id}/records/{rid}           → Get single record (with resolved relations)
    POST   /panels/{id}/records                 → Create record (validated)
    PUT    /panels/{id}/records/{rid}           → Update record
    DELETE /panels/{id}/records/{rid}           → Delete record (blocked if linked)
  
  Relations:
    GET    /panels/{id}/relation-lookup         → Search linkable entities
    GET    /panels/linkable-targets             → List linkable modules
  
  Access Control:
    GET    /access-level                        → Get user's access tier
    PUT    /admin/set-access-level              → Set access (admin only)

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

### Future (Post Phase 3)
- Automation Engine (rules, triggers, IF/THEN logic)
- Many-to-many relations
- Deep chaining (>2 levels)

## Key Files
- `/app/backend/routers/panel_router.py` - Panel + Record CRUD, relation lookup, validation
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel management UI
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` - Record list + CRUD UI
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - RBAC layout, sidebar panels
- `/app/frontend/src/app/admin/users/[id]/page.tsx` - Admin user profile with access control
- `/app/backend/server.py` - Admin endpoints, auth
- `/app/backend/tests/test_panel_records_phase2.py` - Phase 2 test suite (25 tests)
