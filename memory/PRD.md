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

### Admin Low Stock Alerts Access (DONE - Mar 2026)
- **Bug Fix:** Admin users were getting 403 Permission Denied on Low Stock Alerts page
- **Backend:** `check_permission` now allows admin users (isAdmin:true or 'admin' in roles). Low stock alerts endpoint returns all sellers' alerts for admin with `isAdminView:true` and `sellerName` per alert
- **Frontend:** Admin view shows "Admin View" badge, seller name under each alert, hides "Order Material"/"Ignore" buttons, shows status badge instead

### Shared Permissions Utility Refactor (DONE - Mar 2026)
- **Bug Fix:** POST /api/business-tools/purchase-orders returned 403 for sellers because `accountType` was missing from user records
- **Root Cause:** 12 routers had duplicated, inconsistent permission logic. Some checked `user.get("accountType")` without a default value
- **Fix:** Created `/app/backend/utils/permissions.py` with centralized `authenticate_user`, `resolve_seller_id`, `check_user_permission`, `require_user_permission`, `is_platform_admin`. All 12 routers now import from this shared utility

### Invoice Share Link Fix (DONE - Mar 2026)
- **Bug Fix:** Shared invoice links via WhatsApp returned "Document reference missing"
- **Root Cause:** Backend `POST /share-document` endpoint defined params as query parameters, but frontend sent them in JSON body. `documentId` always defaulted to empty string
- **Fix:** Created `ShareDocumentRequest` Pydantic model to correctly parse JSON body. Also replaced hardcoded `app_url` with `os.environ.get("FRONTEND_URL")`

### PO WhatsApp Sharing with Secure Download Link (DONE - Mar 2026)
- **Feature:** Added secure document link (`/api/doc/{token}`) to PO WhatsApp messages, consistent with invoice and catalog sharing
- **Backend:** Updated `GET /purchase-orders/{poId}/whatsapp-link` to create `document_shares` record (7-day expiry), return `documentLink`, `whatsappLink`, `supplierPhone`. Fixed `/api/doc/{token}` PO handler to return actual PDF (was returning raw JSON). PO status auto-updates from draft to sent
- **Frontend:** WhatsApp button visible for all non-terminal PO statuses. Phone input modal shown when supplier phone is missing. "Opening WhatsApp..." confirmation on send

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
- Seller Reminder Controls (configure reminder schedule for invoices, low stock, POs; custom messages; enable/disable)
- Purchase Flow Integration: Low Stock Alert → auto-create PO draft → select supplier → send PO
- Admin View for Reports (aggregated data across all sellers, filter by seller/date/category)
- WhatsApp Business API integration (future upgrade from wa.me)

### P2
- Token-based search, Redis caching, server.py refactor
- Automatic email reminders
- Buyer-facing Product Offers panel
- Refactor inquiry modal, clean unused Pydantic models
- Admin search insights dashboard

## Mocked: Resend email service
