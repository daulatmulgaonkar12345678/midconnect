# PRD - B2B E-commerce Seller Dashboard (UdyogConnect)

## Original Problem Statement
Build a comprehensive ERP/Business Tools system for sellers on a B2B e-commerce platform.

## Core Architecture
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS + Recharts
- **Backend:** FastAPI + MongoDB (motor async driver)
- **Auth:** Firebase Authentication
- **PDF:** ReportLab + qrcode + PyPDF2 (merging)
- **Storage:** Cloudinary (receipts/logos/invoice backgrounds)
- **Email:** Resend (MOCKED)

## What's Been Implemented

### Phase 1-3: Payment Tracking, Receipts, Onboarding (DONE)
### Phase 4: Dashboard & Notifications (DONE)
### Inventory, Suppliers, Low Stock Alerts, PO/GRN (DONE)
### Product Analytics, Charts & Graphs (DONE)
### GST Invoice System with Merged PDF Modal (DONE)
### Centralized Billing & Company Branding Settings (DONE)
### Export & Import System (DONE)

### Share Product Catalog & WhatsApp Document Sharing (DONE - Mar 2026)
- **Inventory "Share Product Catalog" flow:**
  - Product selection: individual checkboxes, category-based (Select All in Category), global Select All
  - 4-step modal: Product review (category grouping) → Recipient selection (buyers + suppliers with type badge) → Format & Options (PDF/Excel + Show/Hide Price) → Result (download + WhatsApp per recipient)
  - Generates professional PDF catalog (reportlab) or styled Excel catalog (openpyxl)
  - Secure document links (7-day expiry, no auth required) via GET /api/doc/{token}
- **WhatsApp Document Sharing (wa.me mode):**
  - Catalog sharing via WhatsApp with secure download link
  - Invoice sharing enhanced: generates secure link in WhatsApp message
  - Message templates for catalogs, invoices, POs
- **Catalog Sharing Settings (Business Settings → Catalog tab):**
  - 8 field toggles: Image, Name, Category, Specification, Description, Price, Unit, MOQ
  - Controls both PDF and Excel catalog generation
- **Security:** Seller can only share own products; no stock/cost data exposed; links are token-based and time-limited

## Key API Endpoints
### Product Sharing & Documents
- GET /api/business-tools/recipients (buyers + suppliers)
- POST /api/business-tools/product-shares (generate catalog)
- GET /api/business-tools/product-shares/{id}/download
- POST /api/business-tools/share-document (secure link for any doc)
- GET /api/doc/{token} (public, no auth, 7-day expiry)
- GET /api/business-tools/catalog-settings
- PUT /api/business-tools/catalog-settings

### Invoice
- POST /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/pdf?copy_type=...
- GET /api/business-tools/invoices/{id}/pdf-merged?copies=...

### Export/Import
- GET /api/business-tools/export/{type}?format=csv|xlsx
- GET /api/business-tools/import/template/{type}
- POST /api/business-tools/import/validate
- POST /api/business-tools/import/process

### Settings
- GET/PUT /api/business-tools/seller-profile
- GET/PUT /api/business-tools/catalog-settings

## Business Settings Tabs
1. Business Profile (name, GSTIN, contact, address)
2. Billing Settings (bank details, T&C)
3. Company Branding (logo, background template)
4. Catalog Settings (field visibility toggles)

## Prioritized Backlog
### P1
- Seller Reminder Controls (configure reminder schedule, custom messages, enable/disable)
- Admin View for Reports
- WhatsApp Business API integration (future upgrade from wa.me)

### P2
- Token-based search, Redis caching, server.py refactor
- Automatic email reminders
- Buyer-facing Product Offers panel
- Refactor inquiry modal, clean unused Pydantic models

## Mocked: Resend email service
