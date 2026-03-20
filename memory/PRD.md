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
    - **3-Tab Management:** Active, Pending, Unlinked employees
    - **Link via Email:** Admin searches by email, validates buyer status, assigns role + permissions
    - **Module-Based Permissions:** 10 modules (Dashboard, Inventory, Invoices, Quotations, Purchase Orders, Reports, Buyers, Suppliers, Employees, Settings) with View + Action per module
    - **6 Role Templates:** Admin (full), Manager (no employee/settings action), Sales Executive, Inventory Manager, Accountant, Viewer (read-only)
    - **Flexible Roles:** Templates pre-fill permissions but admin can customize any combination
    - **Real-Time Access Sync:** Socket.IO (python-socketio + socket.io-client) pushes access_updated events. No logout required — UI updates instantly
    - **Self-Protection:** Admin cannot modify their own access or unlink themselves
    - **Soft Disable:** active/disabled status. Disabled = login allowed, no system access
    - **Audit Logging:** employee_logs collection tracks all link/unlink/permission changes
    - **Unlink Employee:** Instant access revocation, moves to "Unlinked" tab
    - **Re-link:** Previously unlinked employees can be re-linked with new role/permissions
    - **Company Delete Impact:** POST /unlink-all endpoint revokes all employee access when company deleted
    - **Permission Grid UI:** Visual checkbox grid for View/Action per module
    - **EmployeeAccessContext:** canView(module), canAction(module), isFullAdmin, isDisabled helpers
    - **Nav Items:** Each nav item has module field for permission-based visibility

## Recent Changes (Mar 2026)
- Fixed Socket.IO duplicate CORS header: switched from `app.mount()` to `ASGIApp` wrapper pattern — Socket.IO handles own CORS for `/api/socket.io/*`, FastAPI CORSMiddleware handles the rest
- Set explicit `cors_allowed_origins` on Socket.IO matching production domains
- Reassigned `app` at end of server.py so `server:app` works on Render without start command changes
- Frontend Socket.IO client: polling-first transport, reconnection cap (10 attempts), backoff (3s→30s)
- Removed private `emergentintegrations==0.1.0` from `requirements.txt` to unblock Render/Vercel deployments
- Fixed unused `firebase_app` variable lint warning in `business_tools_router.py`

## Prioritized Backlog
### P1
1. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
2. Seller Reminder Controls (configurable schedules)

### P2
- GSTR-1 JSON export | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- Enhanced Business Insights

### P3
- Offline sync queue panel | Conflict resolution UI

## Key Files
- `/app/backend/routers/employee_mgmt_router.py` - Enhanced employee management (link/unlink/permissions/audit)
- `/app/frontend/src/context/EmployeeAccessContext.tsx` - Real-time access context with Socket.IO
- `/app/frontend/src/app/seller/business-tools/employees/page.tsx` - 3-tab employee management UI
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - Updated with EmployeeAccessProvider + module nav
- `/app/backend/routers/quotation_router.py` - Quotation CRUD + PDF + share-link + conversion
- `/app/backend/services/quotation_pdf_service.py` - Quotation PDF with discount + DRAFT watermark
- `/app/backend/routers/invoice_router.py` - Invoice CRUD with discountType support
- `/app/frontend/src/lib/syncEngine.ts` - Priority-ordered offline sync
