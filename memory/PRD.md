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
    - 7 templates: PO, Invoice, Payment Soft, Payment Strict, Dispatch, Catalog, Sales Push
    - Rotating ads in branded footer: "Powered by Udyog Connect / www.udyogconnect.in"
    - ALL existing WhatsApp endpoints updated to use templates
    - New "Sales Push" button in Buyers section (WhatsApp catalog push)
    - 48/48 tests passed

### Mocked
- Resend email service

## Prioritized Backlog

### P1 - Next Up
- **GST Batch 2:** GST-compliant PDF invoice layout, GST Summary Report (GSTR-1)
- **Standardize Reports:** Professional Sales, Inventory, Profit, Low Stock, Stock Movement reports
- **Seller Reminder Controls:** Configurable invoice reminder schedules
- **Admin View for Reports:** Aggregated data for admin users

### P2 - Future
- Short link tracking for WhatsApp shared links
- Premium toggle to hide branding (paid users)
- Referral tracking from WhatsApp shares
- Bulk sales push to multiple buyers
- Advanced token-based search, Redis caching, WhatsApp Business API

## Key Files
- `/app/backend/utils/whatsapp_messages.py` - Centralized WhatsApp template engine
- `/app/backend/utils/gst.py` - GST calculation engine
- `/app/backend/utils/permissions.py` - Centralized auth/permissions
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + GST + reminders
- `/app/backend/routers/business_tools_router.py` - Buyers + shipping addresses + sales push
- `/app/backend/routers/pending_orders_router.py` - Backorder management
- `/app/backend/tests/test_gst.py` - GST unit tests (9/9)
- `/app/backend/tests/test_whatsapp_template_engine.py` - Template tests (48/48)
