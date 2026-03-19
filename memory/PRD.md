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
2. **Invoice System (GST-Compliant):**
   - Auto CGST/SGST vs IGST based on state
   - Bill To / Ship To layout on PDF + UI, QR code removed
   - Freight, TCS, Auto Round Off, Payment Terms, Product Description
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (Single Source of Truth, 8 templates)
8. **Reporting System Phase 1 (DONE):**
   - Outstanding/Receivables Report (aging buckets, buyer filter, partial payments)
   - Purchase Report (confirmed/received POs, supplier filter)
   - Stock Movement Report (opening/closing stock, $facet aggregation)
   - CSV/Excel export for all 3 reports
9. **Reporting System Phase 2 (DONE - Feb 2026):**
   - **Buyer Ledger** — buyer-wise sales/paid/pending with drill-down transaction history per buyer
   - **Product Performance** — qty sold, revenue, profit, profit%, with Top Selling (top 5) & Slow Moving (bottom 5) sections
   - **Category Report** — sales, revenue, profit grouped by product category (with Uncategorized fallback)
   - **Low Stock Analytics** — min stock, current stock, times hit low, avg consumption/day, days of stock remaining, out-of-stock/low-stock/healthy status sorting
   - CSV/Excel export for all 4 reports
   - MongoDB indexes for performance

## Report Tabs (14 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API | Redis caching

## Test Coverage: 181+ tests
- WhatsApp: 48 | HSN: 15 | PDF Address: 18 | Freight/TCS: 24 | Description: 17 | Reports Phase 1: 27 | Reports Phase 2: 32

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (14 endpoints)
- `/app/backend/routers/export_import_router.py` - Export/import (12 export endpoints)
- `/app/backend/services/invoice_pdf_service.py` - GST invoice PDF
- `/app/backend/utils/whatsapp_messages.py` - WhatsApp templates
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + charges + description
- `/app/backend/routers/inventory_router.py` - Inventory with HSN + description
- `/app/backend/models/business_tools.py` - Models
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (14 tabs)
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI
