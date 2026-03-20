# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary | **PDF:** reportlab, PyPDF2 | **Email:** Resend (MOCKED)
- **PWA:** Service Worker + manifest.json | **Offline:** IndexedDB (via idb library)

## Completed Features
1. Full B2B Marketplace + Seller/Admin Dashboards
2. **Invoice System (GST-Compliant)** — Auto CGST/SGST vs IGST, Bill To/Ship To, Freight/TCS/Round Off, Payment Terms, Product Description
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (Single Source of Truth, 8 templates)
8. **Reporting Phase 1** — Outstanding/Receivables, Purchase, Stock Movement
9. **Reporting Phase 2** — Buyer Ledger, Product Performance, Category Report, Low Stock Analytics
10. **Business Insights Dashboard Widget** — 4 clickable insight cards
11. **HSN + GST in Sales Reports**
12. **GST Sales Report (GSTR-1 Compatible)**
13. **Bug Fix: Invoice Number Format Consistency**
14. **Invoice "Sent" Status Handling**
15. **Hybrid Offline Mode + Draft Invoice System (Feb 2026)**
16. **Refer & Earn System (Feb 2026)**
17. **Advanced Offline Business System - Quotation Module (Mar 2026)**:
    - Full Quotation CRUD, PDF Generation, Convert to Invoice with dual storage
    - Offline Quotation + Buyer Sync with Deduplication, Priority-ordered Sync Engine
18. **Enhancement: Quotation & Invoice Pricing + Sharing (Mar 2026)**:
    - **Auto Product Rate:** On product select, auto-fills price, GST%, HSN from inventory
    - **Per-Item Discount System:** Toggle between % and Rs. Calculation: Base Rate → Discount → Tax → Total
    - **WhatsApp PDF Sharing:** Time-limited public PDF download links (3-day expiry, token-based, no auth needed for buyer)
    - **Clean WhatsApp Branding:** "Powered by UdyogConnect" in all shared messages
    - **Public PDF Endpoint:** Quotation doc type added to existing public document sharing infrastructure
    - **PDF Discount Display:** Shows "5% (amount)" for percentage or flat Rs amount
    - Applied to BOTH quotation and invoice systems

## Prioritized Backlog
### P1
1. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
2. Seller Reminder Controls (configurable schedules)

### P2
- GSTR-1 JSON export | Amendment tracking | Custom Material Report
- Short link tracking + click analytics
- White-label toggle | WhatsApp Business API
- Enhanced Business Insights (Profit summary, Cash flow alerts)

### P3 — Offline Enhancements
- Sync queue panel (pending / failed items details)
- Offline support for inventory updates and purchase orders (full CRUD)
- Conflict resolution UI for inventory mismatches

## Key Files
- `/app/backend/routers/quotation_router.py` - Quotation CRUD + PDF + conversion + share-link + offline sync
- `/app/backend/services/quotation_pdf_service.py` - Quotation PDF with discount + DRAFT watermark
- `/app/backend/services/invoice_pdf_service.py` - Invoice PDF with discount display
- `/app/backend/routers/invoice_router.py` - Invoice CRUD with discountType support
- `/app/backend/routers/product_share_router.py` - Public doc serving (catalog/invoice/po/quotation)
- `/app/backend/models/business_tools.py` - InvoiceItemCreate with discountType field
- `/app/frontend/src/app/seller/business-tools/quotations/page.tsx` - Quotation UI with discount + auto-pricing + WhatsApp PDF sharing
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI with discount toggle
- `/app/frontend/src/lib/offlineStore.ts` - IndexedDB with quotation + buyer types
- `/app/frontend/src/lib/syncEngine.ts` - Priority-ordered sync (Buyers → Quotations → Invoices)
