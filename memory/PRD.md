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
8. **Reporting Phase 1** — Outstanding/Receivables, Purchase, Stock Movement reports
9. **Reporting Phase 2** — Buyer Ledger (with drill-down transactions), Product Performance (top/slow movers), Category Report, Low Stock Analytics
10. **Business Insights Dashboard Widget (NEW - Feb 2026):**
    - GET /reports/overview — lightweight aggregation returning 8 key metrics
    - 4 clickable insight cards on Business Tools homepage: Outstanding Alerts, Low Stock Alerts, Top Product, Monthly Sales + Growth %
    - Color-coded (red=urgent, amber=warning, green=good), links to respective report tabs via ?tab= query param
    - Reports page reads ?tab= URL param for deep linking

## Report Tabs (14 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API | Redis caching
- Extend insights widget: Profit summary, Cash flow alerts, Purchase alerts

## Test Coverage: 203+ tests
- WhatsApp: 48 | HSN: 15 | PDF Address: 18 | Freight/TCS: 24 | Description: 17 | Reports P1: 27 | Reports P2: 32 | Insights Overview: 22

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (15 endpoints incl. overview)
- `/app/backend/routers/export_import_router.py` - 12 export endpoints
- `/app/backend/routers/home_router.py` - Dashboard home summary/charts
- `/app/frontend/src/app/seller/business-tools/page.tsx` - Dashboard with Business Insights
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (14 tabs, ?tab= deep link)
