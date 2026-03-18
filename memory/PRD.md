# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management. Recent upgrades: GST-compliant billing, pending orders, shipping addresses, and branded WhatsApp messaging.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB (Motor), Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary
- **PDF:** reportlab, PyPDF2
- **Email:** Resend (MOCKED)
- **Charts:** recharts

## What's Been Implemented

### Completed Features
1. Full B2B Marketplace
2. Seller Dashboard
3. Admin Dashboard
4. Invoice System with GST
5. Inventory Management
6. Purchase Orders + WhatsApp sharing
7. Buyer Management + Shipping Addresses
8. Pending Orders (Backorder) - fixed stock reservation
9. Permissions System (centralized)
10. Employee Management
11. Document Sharing (secure expiring links)
12. **GST Billing Engine** - Auto CGST/SGST vs IGST
13. **Shipping Address Management** - Multi-address per buyer, invoice integration
14. **Pending Orders Bug Fix** - Uses available_stock (stock - reserved) not raw stock
15. **WhatsApp Messaging Engine (COMPLETE):**
    - Centralized template engine at `/app/backend/utils/whatsapp_messages.py`
    - 7 templates: PO, Invoice, Payment Soft, Payment Strict, Dispatch, Catalog, Catalog Marketing
    - Rotating ads in branded footer: "Powered by Udyog Connect / www.udyogconnect.in"
    - ALL existing WhatsApp endpoints updated to use templates
    - "Share Catalog" button in Buyers section (WhatsApp catalog push)
    - 48/48 tests passed
16. **Catalog Sharing Flow Fix (P0 - DONE 2026-03-18):**
    - Renamed `sales_push_message` → `catalog_marketing_message`
    - Added `BASE_URL = "https://udyogconnect.in"` for all shared document links
    - Added `build_doc_url(token)` helper for consistent URL generation
    - Catalog share endpoint returns `whatsappMessage` for frontend use
    - Frontend uses backend-provided message with branding + rotating ads
    - Renamed "Sales Push" → "Share Catalog" on Buyers page
    - Fixed link domain: all WhatsApp links use udyogconnect.in (not preview URL)
17. **HSN Code in Inventory** - Sellers can add/edit HSN codes on products

### Mocked
- Resend email service

## Prioritized Backlog

### P1 - Next Up (User-defined order)
1. **Seller Reminder Controls:** Configurable invoice reminder schedules (HIGH IMPACT)
2. **GST Batch 2:** GST-compliant PDF invoice layout, GST Summary Report (GSTR-1)
3. **Standardize Reports:** Professional Sales, Inventory, Profit, Low Stock, Stock Movement reports

### P2 - Future
- Short link tracking for WhatsApp shared links (VERY IMPORTANT per user)
- Premium toggle to hide branding (revenue feature)
- Inquiry modal refactor on product page
- Advanced token-based search + admin search dashboard
- Redis caching for performance
- Full WhatsApp Business API upgrade

## Key Files
- `/app/backend/utils/whatsapp_messages.py` - Centralized WhatsApp template engine (BASE_URL, build_doc_url, 7 templates)
- `/app/backend/utils/gst.py` - GST calculation engine
- `/app/backend/utils/permissions.py` - Centralized auth/permissions
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + GST + reminders
- `/app/backend/routers/business_tools_router.py` - Buyers + shipping addresses + share catalog
- `/app/backend/routers/product_share_router.py` - Catalog generation + WhatsApp sharing
- `/app/backend/routers/pending_orders_router.py` - Backorder management
- `/app/backend/tests/test_gst.py` - GST unit tests (9/9)
- `/app/backend/tests/test_whatsapp_template_engine.py` - Template tests (48/48)

## Refactoring Needed
- `/app/backend/routers/invoice_router.py` - Very large, extract business logic to services
- `firebase_app` unused lint warning in `business_tools_router.py` (P2)
