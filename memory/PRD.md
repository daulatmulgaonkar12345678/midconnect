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
   - **Freight** (manual Rs. amount), **TCS** (toggle + percentage 0-5%), **Auto Round Off** (nearest rupee)
   - **Payment Terms** (free text, e.g., "100% advance")
   - Flexible `additionalCharges` schema for future: Packing, Loading, Insurance
   - Consistent across: Form → Detail View → PDF
3. Inventory Management with HSN Codes
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. **WhatsApp Messaging Engine (Single Source of Truth):**
   - 8 templates, branded footer, rotating ads, `BASE_URL = "https://www.udyogconnect.in"`

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Standardize Reports (Sales, Inventory, Profit, Low Stock)

### P2
- Short link tracking | White-label toggle | WhatsApp Business API | Redis caching

## Test Coverage: 105 tests
- 48 WhatsApp + 15 HSN + 18 PDF address + 24 Freight/TCS/RoundOff

## Key Files
- `/app/backend/services/invoice_pdf_service.py` - GST invoice PDF
- `/app/backend/utils/whatsapp_messages.py` - Centralized WhatsApp templates
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + charges
- `/app/backend/models/business_tools.py` - AdditionalCharge, InvoiceCreate models
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI
