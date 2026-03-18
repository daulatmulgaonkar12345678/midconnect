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
2. Seller Dashboard + Admin Dashboard
3. Invoice System with GST (CGST/SGST vs IGST)
4. Inventory Management with HSN Codes
5. Purchase Orders + WhatsApp sharing
6. Buyer Management + Shipping Addresses (CRUD)
7. Pending Orders (Backorder) with stock reservation logic
8. Permissions System + Employee Management
9. Document Sharing (secure expiring links)
10. **WhatsApp Messaging Engine (Single Source of Truth):**
    - `BASE_URL = "https://www.udyogconnect.in"` for all shared links
    - 8 templates with branded footer + rotating ads
    - All messages generated server-side, no frontend hardcoding
    - Name trimming, 81 tests passing
11. **Invoice PDF Upgrade (2026-03-18):**
    - Removed QR code completely from PDF
    - New layout: Seller (full-width header) → Bill To (left) | Ship To (right)
    - If shipping address different from billing → shows separate Ship To details
    - If same/missing → shows "Same as Billing Address"
    - Shipping address selected during invoice creation from buyer's saved addresses
    - Works on both PDF download and UI detail view
    - 18 dedicated PDF tests passing

### Mocked
- Resend email service

## Prioritized Backlog

### P1 - Next Up
1. **Seller Reminder Controls:** Configurable invoice reminder schedules
2. **GST Batch 2:** GST-compliant PDF enhancements, GST Summary Report (GSTR-1)
3. **Standardize Reports:** Sales, Inventory, Profit, Low Stock, Stock Movement

### P2 - Future
- Short link tracking for WhatsApp shared links
- Premium toggle to hide branding
- Inquiry modal refactor
- Advanced search + admin dashboard
- Redis caching
- Full WhatsApp Business API upgrade

## Key Files
- `/app/backend/services/invoice_pdf_service.py` - GST invoice PDF (no QR, Bill To/Ship To layout)
- `/app/backend/utils/whatsapp_messages.py` - Centralized WhatsApp templates
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + PDF + WhatsApp
- `/app/backend/routers/inventory_router.py` - Inventory with HSN codes
- `/app/frontend/src/app/seller/business-tools/invoices/page.tsx` - Invoice UI

## Test Coverage
- 81 total tests: 48 WhatsApp + 15 HSN/messaging + 18 PDF address tests
- Test files: `test_whatsapp_template_engine.py`, `test_hsn_whatsapp_fixes.py`, `test_invoice_pdf_addresses.py`
