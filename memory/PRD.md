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
2. **Invoice System (GST-Compliant)** — Auto CGST/SGST vs IGST, Bill To/Ship To, Per-item discount
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (8 templates)
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
18. **Employee Pending Tab Fix (Mar 2026)**: Fixed active employees in Pending tab
19. **Custom Panel System — Phase 1 (Mar 2026)**:
    - Panel CRUD: create, edit, delete custom panels (max 10/business)
    - Field Builder: 8 types (text, number, date, dropdown, multiselect, boolean, longtext, relation)
    - Max 20 fields/panel, duplicate name validation, relation with linkable targets
    - Sidebar integration: Custom Panels section for advanced users
    - Role restriction: only seller admin can create (not employees)
20. **Business Tool Access Control (Mar 2026)** ← NEW:
    - 3-tier system: None / Standard / Advanced (super admin controlled)
    - Admin UI: Business Tool Access card in admin user profile page (/admin/users/{id})
    - Backend: `PUT /api/admin/users/{id}/business-tool-access` endpoint
    - `GET /api/admin/users/{id}/detail` includes businessToolAccess field
    - `GET /api/business-tools/my-permissions` includes businessToolAccess in response
    - Global gating in Business Tools layout: "none" → blocked page, "standard" → modules only, "advanced" → standard + panels
    - Sidebar: Custom Panels section only shows for "advanced" users
    - Panels page: Shows "Advanced Access Required" for non-advanced users
    - Platform admins always have advanced access (bypasses stored field)

## Panel System Architecture
```
Access Tiers:
  None     → Marketplace only (blocked from business tools)
  Standard → Inventory, Invoice, etc. (no panels)
  Advanced → Standard + Custom Panels + future Document Builder

Access Control Flow:
  /my-permissions → returns businessToolAccess
  Layout reads it → gates access globally
  Sidebar reads it → shows/hides Custom Panels section
  Panel page reads it → shows upgrade message or panel UI

Admin Control:
  /admin/users/{id} page → Business Tool Access card
  PUT /api/admin/users/{id}/business-tool-access → saves to DB
  Platform admins always = advanced (via is_platform_admin check)
```

## Prioritized Backlog
### P0 (Next)
1. **Panel System Phase 2**: Record entry (create/edit/view records), simple relations (many→one to Inventory/Invoice/Panels), safety rules (no circular links, delete protection)

### P1
2. **Panel System Phase 3**: Basic document builder (templates + {{variables}} + PDF/Excel), branding, shareable links
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls (configurable schedules)
5. Quotation/Employee Activity Dashboards

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- Enhanced Business Insights

## Key Files
- `/app/backend/server.py` - Admin endpoints incl. PUT business-tool-access (line ~9741)
- `/app/backend/routers/panel_router.py` - Panel CRUD + field management + access control
- `/app/backend/routers/business_tools_router.py` - /my-permissions includes businessToolAccess
- `/app/frontend/src/app/admin/users/[id]/page.tsx` - Admin user profile with Business Tool Access card
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - RBAC layout, global access gating, sidebar panels
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` - Panel management UI
- `/app/backend/utils/permissions.py` - Backend permission resolution + is_platform_admin
