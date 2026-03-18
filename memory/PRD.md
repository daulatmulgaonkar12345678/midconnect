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
5. Inventory Management with HSN Codes
6. Purchase Orders + WhatsApp sharing
7. Buyer Management + Shipping Addresses
8. Pending Orders (Backorder) - fixed stock reservation
9. Permissions System (centralized)
10. Employee Management
11. Document Sharing (secure expiring links)
12. **GST Billing Engine** - Auto CGST/SGST vs IGST
13. **Shipping Address Management** - Multi-address per buyer, invoice integration
14. **Pending Orders Bug Fix** - Uses available_stock (stock - reserved) not raw stock
15. **WhatsApp Messaging Engine (SINGLE SOURCE OF TRUTH - COMPLETE):**
    - Centralized template engine at `/app/backend/utils/whatsapp_messages.py`
    - `BASE_URL = "https://www.udyogconnect.in"` - consistent domain for all shared links
    - `build_doc_url(token)` helper for consistent document URLs
    - 8 templates: PO, Invoice, Payment Soft, Payment Strict, Dispatch, Catalog, Catalog Marketing, Pending Order
    - Rotating ads in branded footer: "Powered by Udyog Connect / www.udyogconnect.in"
    - ALL WhatsApp messages (frontend + backend) use centralized templates
    - Names auto-trimmed to prevent extra spaces
    - 63 tests passed (48 template + 15 integration)
16. **Catalog Sharing Flow:**
    - "Share Catalog" button on Buyers page (renamed from Sales Push)
    - Catalog marketing template with branding
    - Inventory page catalog share uses backend message with footer
17. **HSN Code Fix:**
    - HSN code now correctly returned in inventory API response
    - Editable in inventory table, auto-populates on invoices

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
- `/app/backend/utils/whatsapp_messages.py` - Centralized WhatsApp template engine (BASE_URL, build_doc_url, 8 templates, name trimming)
- `/app/backend/utils/gst.py` - GST calculation engine
- `/app/backend/utils/permissions.py` - Centralized auth/permissions
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + GST + reminders + WhatsApp (with doc share tokens)
- `/app/backend/routers/inventory_router.py` - Inventory management (includes hsnCode in pipeline)
- `/app/backend/routers/business_tools_router.py` - Buyers + shipping addresses + share catalog
- `/app/backend/routers/product_share_router.py` - Catalog generation + WhatsApp sharing
- `/app/backend/routers/pending_orders_router.py` - Backorder management
- `/app/backend/tests/test_whatsapp_template_engine.py` - Template tests (48/48)
- `/app/backend/tests/test_hsn_whatsapp_fixes.py` - HSN + messaging integration tests (15/15)

## Single Source of Truth: WhatsApp Messages
ALL WhatsApp messages across the entire app flow through `/app/backend/utils/whatsapp_messages.py`:
- Invoice sending → `invoice_message()`
- Payment reminder (soft) → `payment_reminder_soft()`
- Payment reminder (overdue) → `payment_reminder_strict()`
- PO sharing → `po_message()`
- Catalog sharing (from inventory) → `catalog_marketing_message()`
- Share Catalog (from buyers) → `catalog_marketing_message()`
- Pending order notify → `pending_order_notify()`
- Dispatch → `dispatch_message()`
- All doc URLs → `build_doc_url(token)` using `BASE_URL`

## Refactoring Needed
- `/app/backend/routers/invoice_router.py` - Very large, extract business logic to services
- `firebase_app` unused lint warning in `business_tools_router.py` (P2)
