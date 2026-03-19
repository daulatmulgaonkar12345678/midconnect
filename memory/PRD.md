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

## Prioritized Backlog
### P1
1. Seller Reminder Controls (configurable schedules)
2. GST Summary Report (GSTR-1)
3. Standardize Reports (Sales, Inventory, Profit, Low Stock)

### P2
- Short link tracking | White-label toggle | WhatsApp Business API | Redis caching

## Test Coverage: 122+ tests
- WhatsApp: 48 | HSN: 15 | PDF Address: 18 | Freight/TCS: 24 | Description: 17

## Key Files
- `/app/backend/services/invoice_pdf_service.py` - GST invoice PDF
- `/app/backend/utils/whatsapp_messages.py` - WhatsApp templates
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + charges + description
- `/app/backend/routers/inventory_router.py` - Inventory with HSN + description
- `/app/backend/models/business_tools.py` - Models (AdditionalCharge, InventoryUpdate)
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI
- `/app/frontend/src/app/seller/business-tools/inventory/page.tsx` - Inventory UI
