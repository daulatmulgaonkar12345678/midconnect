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
12. **GST Sales Report (GSTR-1 Compatible)** — B2B/B2C auto-classification, GSTIN validation, Place of Supply, CGST/SGST/IGST split, HSN Summary, 2-sheet Excel export
13. **Bug Fix: Invoice Number Format Consistency** — Fixed pending_orders_router.py generating `INV-XXXX` instead of standard `INV{Abbr}-{Code}-XXXX` format

## Report Tabs (15 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | GST Report | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- GSTR-1 JSON export | Amendment tracking | Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API

## Test Coverage: 249+ tests

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (16 endpoints)
- `/app/backend/routers/export_import_router.py` - 13 export endpoints
- `/app/backend/routers/pending_orders_router.py` - Fixed: now uses get_next_invoice_number()
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + get_next_invoice_number()
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (15 tabs)
