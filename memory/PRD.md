# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary | **PDF:** reportlab, PyPDF2 | **Email:** Resend (MOCKED)
- **PWA:** Service Worker + manifest.json | **Offline:** IndexedDB (via idb library)
- **Real-time:** python-socketio + socket.io-client (for employee access sync)

## Completed Features
1. Full B2B Marketplace + Seller/Admin Dashboards
2. **Invoice System (GST-Compliant)** — Auto CGST/SGST vs IGST, Bill To/Ship To, Freight/TCS/Round Off, Payment Terms, Per-item discount (% or Rs)
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
14. **Enhancement: Pricing + Sharing (Mar 2026)** — Auto product rate, Per-item discount (% / Rs), WhatsApp PDF sharing with public token-based links, "Powered by UdyogConnect" branding
15. **Employee System with Live Access Control (Mar 2026)**:
    - 3-Tab Management, Link via Email, Module-Based Permissions (10 modules), 6 Role Templates
    - Real-Time Access Sync via Socket.IO, Self-Protection, Soft Disable, Audit Logging
    - EmployeeAccessContext: canView(module), canAction(module), isFullAdmin, isDisabled helpers
16. **Company Banner in Business Tools (Mar 2026)**: Displays company name + logo in sidebar
17. **RBAC Fix (Mar 2026)**: Fixed critical architectural bug where useEmployeeAccess() hook was called outside EmployeeAccessProvider. Refactored layout.tsx into outer (BusinessToolsLayout) and inner (BusinessToolsInner) components. Admin = full access, Employee = filtered by canView/canAction. Added loading fallback for employee permission resolution.

## Recent Changes (Mar 2026)
- **Critical Fix:** Refactored `/app/frontend/src/app/seller/business-tools/layout.tsx` — split into `BusinessToolsLayout` (renders providers) and `BusinessToolsInner` (renders UI inside providers). This ensures `useEmployeeAccess()` hook receives correct React context.
- **Improved NoAccess component** — now shows "Access Restricted" with custom message support
- **Fixed unused `paid` variable** lint error in `invoice_router.py` (line 1531)
- Fixed Socket.IO duplicate CORS header: switched from `app.mount()` to `ASGIApp` wrapper pattern

## Prioritized Backlog
### P1
1. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
2. Seller Reminder Controls (configurable schedules)
3. Quotation/Employee Activity Dashboards

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- Enhanced Business Insights

### P3
- Offline sync queue panel | Conflict resolution UI

## Key Files
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - RBAC layout (BusinessToolsLayout + BusinessToolsInner)
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - Real-time access context with Socket.IO
- `/app/frontend/src/components/NoAccess.tsx` - Access restricted component
- `/app/backend/routers/employee_mgmt_router.py` - Employee management (link/unlink/permissions/audit)
- `/app/frontend/src/app/seller/business-tools/employees/page.tsx` - 3-tab employee management UI
- `/app/backend/routers/quotation_router.py` - Quotation CRUD + PDF + share-link + conversion
- `/app/backend/routers/invoice_router.py` - Invoice CRUD with discountType support
- `/app/frontend/src/lib/syncEngine.ts` - Priority-ordered offline sync
- `/app/backend/utils/permissions.py` - Backend permission resolution
