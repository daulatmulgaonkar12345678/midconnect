# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary | **PDF:** reportlab, PyPDF2 | **Email:** Resend (MOCKED)

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
11. **HSN + GST in Sales Reports** — HSN Code, Taxable Value, GST% in Products & Product Performance tabs + exports
12. **GST Sales Report (GSTR-1 Compatible) (NEW - Feb 2026):**
    - Invoice-level data: Invoice #, Date, Buyer, GSTIN, Invoice Type, Place of Supply, B2B/B2C, Taxable Value, CGST/SGST/IGST, Total
    - Auto B2B/B2C classification from GSTIN validation (15-char regex)
    - B2C Large (>2.5L + interstate) vs B2C Small
    - CGST+SGST for intra-state, IGST for inter-state (state code from GSTIN first 2 digits)
    - HSN Summary section: grouped by HSN code with UQC, Qty, Taxable, CGST/SGST/IGST
    - Excel export: 2-sheet workbook (Invoice Data + HSN Summary) with formatted headers
    - Filters: Date range, Buyer, GST Type (B2B/B2C)
    - Excludes cancelled/draft invoices

## Report Tabs (15 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | **GST Report** | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- GSTR-1 JSON export for direct GST portal upload
- Amendment tracking for GST
- Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API

## Test Coverage: 249+ tests
- WhatsApp: 48 | HSN: 15 | PDF: 18 | Freight/TCS: 24 | Description: 17 | Reports P1: 27 | Reports P2: 32 | Insights: 22 | HSN Reports: 25 | GST Report: 21

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (16 endpoints incl. GST report)
- `/app/backend/routers/export_import_router.py` - 13 export endpoints (incl. GST 2-sheet Excel)
- `/app/frontend/src/app/seller/business-tools/page.tsx` - Dashboard with Business Insights
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (15 tabs)
