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
1. Full B2B Marketplace + Seller/Admin Dashboards
2. **Invoice System (GST-Compliant)** — Auto CGST/SGST vs IGST, Bill To/Ship To, Freight/TCS/Round Off, Per-item discount
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (Single Source of Truth, 8 templates)
8. **Reporting Phase 1 & 2** — All 15 report tabs
9. **Business Insights Dashboard Widget**
10. **GST Sales Report (GSTR-1 Compatible)**
11. **Hybrid Offline Mode + Draft Invoice System (Feb 2026)**
12. **Refer & Earn System (Feb 2026)**
13. **Advanced Offline Business System - Quotation Module (Mar 2026)**
14. **Enhancement: Pricing + Sharing (Mar 2026)**
15. **Employee System with Live Access Control (Mar 2026)**
16. **Company Banner in Business Tools (Mar 2026)**
17. **RBAC Fix (Mar 2026)**: Refactored layout.tsx into BusinessToolsLayout + BusinessToolsInner
18. **Employee Pending Tab Fix (Mar 2026)**: Fixed active employees appearing in Pending tab
19. **Custom Panel System — Phase 1 (Mar 2026)**:
    - 3-tier access control: None / Standard / Advanced (super admin controlled)
    - Panel CRUD: create, edit, delete custom data panels (max 10 per business)
    - Field Builder: 8 field types (text, number, date, dropdown, multiselect, boolean, longtext, relation)
    - Max 20 fields per panel, duplicate name validation, relation field with linkable targets
    - Sidebar integration: Custom Panels section for advanced users
    - Role restriction: only seller admin can create/modify panels (not employees)
    - Backend: `/api/business-tools/panels` (CRUD), `/api/business-tools/access-level`, `/api/business-tools/panels/linkable-targets`
    - Frontend: `/seller/business-tools/panels` management page with field builder UI

## Panel System Architecture
```
Access Tiers:
  None     → Marketplace only
  Standard → Inventory, Invoice, etc.
  Advanced → Standard + Panels + Document Builder (future)

Panel Schema (MongoDB: panels collection):
  sellerId, name, slug, description, icon, color,
  fields: [{ key, label, type, required, options, relatedPanel, relationType, order }],
  createdAt, updatedAt

Limits: 10 panels/business, 20 fields/panel
Field Types: text, number, date, dropdown, multiselect, boolean, longtext, relation
Relation Types (V1): many_to_one (default), one_to_one
```

## Prioritized Backlog
### P0 (Next)
1. **Panel System Phase 2**: Record entry (create/edit/view records in panels), simple relations (many→one linking to Inventory/Invoice/other panels), safety rules (no circular links, delete protection)

### P1
2. **Panel System Phase 3**: Basic document builder (templates + {{variables}} + PDF/Excel), branding (logo/company), shareable links
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls (configurable schedules)
5. Quotation/Employee Activity Dashboards

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- Enhanced Business Insights

### P3
- Offline sync queue panel | Conflict resolution UI

## Key Files
- `/app/backend/routers/panel_router.py` - Panel CRUD + field management + access control
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel management UI
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - RBAC layout + sidebar with custom panels
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - Real-time access context
- `/app/backend/routers/employee_mgmt_router.py` - Employee management
- `/app/backend/routers/business_tools_router.py` - Business tools + /my-permissions
- `/app/backend/utils/permissions.py` - Backend permission resolution
- `/app/backend/tests/test_custom_panel_system.py` - Panel system test suite (18 tests)
