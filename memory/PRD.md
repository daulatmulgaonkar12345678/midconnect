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
10. **Business Insights Dashboard Widget** — 4 clickable insight cards (Outstanding, Low Stock, Top Product, Monthly Sales + Growth %)
11. **HSN + GST in Sales Reports (NEW - Feb 2026):**
    - Product Sales (Products tab): HSN Code, Taxable Value, GST %, GST Amount columns
    - Product Performance tab: HSN Code column
    - CSV/Excel exports: Sales export has 15 columns (incl. HSN, GSTIN, GST %, CGST/SGST/IGST), Product Performance export has HSN Code
    - HSN lookup via sellerListings → products join pipeline

## Report Tabs (14 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API | Redis caching

## Test Coverage: 228+ tests
- WhatsApp: 48 | HSN: 15 | PDF Address: 18 | Freight/TCS: 24 | Description: 17 | Reports P1: 27 | Reports P2: 32 | Insights: 22 | HSN Reports: 25

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (15 endpoints)
- `/app/backend/routers/export_import_router.py` - 12 export endpoints
- `/app/frontend/src/app/seller/business-tools/page.tsx` - Dashboard with Business Insights
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (14 tabs)
