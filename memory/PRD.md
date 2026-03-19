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
   - Bill To (left) / Ship To (right) layout on PDF + UI
   - QR code removed from PDF
   - Freight, TCS (toggle + %), Auto Round Off (nearest rupee)
   - Payment Terms (free text), flexible additionalCharges schema
   - **Product Description**: Short spec text (max 150 chars) auto-fills from inventory, shown below product name in brackets on UI + PDF
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (Single Source of Truth, 8 templates)
8. **Reporting System Phase 1 (NEW - Feb 2026):**
   - **Outstanding/Receivables Report** — Aging buckets (current, 0-30, 31-60, 61-90, 90+), buyer filter, partial payment handling, pagination, summary cards (Total Receivable, Overdue Amount, Total Buyers, Unpaid Invoices)
   - **Purchase Report** — Confirmed/received POs, supplier filter, pagination, summary cards (Total Purchase Value, Total Items, Avg Order Value, Total Suppliers)
   - **Stock Movement Report** — Opening/closing stock calculation via $facet aggregation on inventory_logs, inward/outward/adjustment tracking, product filter, summary cards (Total Inward, Total Outward, Net Movement)
   - **CSV/Excel Export** for all 3 new reports
   - MongoDB indexes for performance optimization

## Prioritized Backlog
### P0
1. Reporting Phase 2: Buyer Ledger, Product Performance, Category Report, Low Stock Analytics

### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment

### P2
- Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API | Redis caching

## Test Coverage: 149+ tests
- WhatsApp: 48 | HSN: 15 | PDF Address: 18 | Freight/TCS: 24 | Description: 17 | Reports Phase 1: 27

## Key Files
- `/app/backend/services/invoice_pdf_service.py` - GST invoice PDF
- `/app/backend/utils/whatsapp_messages.py` - WhatsApp templates
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + charges + description
- `/app/backend/routers/inventory_router.py` - Inventory with HSN + description
- `/app/backend/routers/reports_router.py` - All reports (10 endpoints incl. outstanding, purchase, stock-movement)
- `/app/backend/routers/export_import_router.py` - Export/import (8 export endpoints incl. 3 new)
- `/app/backend/models/business_tools.py` - Models (AdditionalCharge, InventoryUpdate)
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI
- `/app/frontend/src/app/seller/business-tools/inventory/page.tsx` - Inventory UI
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (10 tabs)
