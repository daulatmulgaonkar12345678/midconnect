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
### Inventory Module (DONE)
### Supplier-Product Mapping (DONE)
### Low Stock Alerts (DONE)
### Purchase Order System (DONE)
### Goods Received (GRN) Flow (DONE)
### Product Analytics Charts (DONE)
### Invoice WhatsApp for Buyers (DONE)
### Business Tools Home Dashboard (DONE)
### Charts & Graphs Page (DONE)
### Notifications System (DONE)

### GST Invoice System (DONE)
- GST-Compliant PDF with seller/buyer GSTIN, HSN codes, CGST/SGST vs IGST
- 4 Invoice Copies: Original, Transporter, Supplier/CA, Office
- QR Code, Amount in Words, Transport Details, E-Way Bill placeholder

### Invoice Checkbox Modal for Merged PDF (DONE)
- Single "Download PDF" button opens modal with copy selection checkboxes
- Select All, Download Selected with dynamic count
- Merged PDF via GET /api/business-tools/invoices/{id}/pdf-merged?copies=...

### Centralized Billing Settings (DONE)
- Billing tab: Bank Details (6 fields), Terms & Conditions
- Auto-rendered on invoice PDF footer

### Company Branding (DONE)
- "Company Branding" tab in Business Settings (3 tabs: Profile, Billing, Branding)
- Company Logo upload (PNG/JPG/SVG, max 2MB) stored as billingSettings.companyLogoUrl
- Invoice Background Template upload (PNG/JPG, max 5MB) stored as billingSettings.invoiceBackgroundImage
- Preview modal showing sample invoice layout with logo at top-left + background at 8% opacity
- Multi-company support: each seller stores separate branding

### Export & Import System (DONE - Mar 2026)
- **Export:** CSV and Excel (.xlsx) buttons on every report tab
  - Sales, Profit, Inventory, Buyers, Invoices export endpoints
  - Exports respect date range filters
  - Styled Excel files with colored headers and auto-width columns
- **Import:** 3-step modal workflow
  - Step 1: Select data type (Products/Inventory/Suppliers/Buyers), download templates
  - Step 2: Upload CSV/XLSX, validate, preview parsed data table
  - Step 3: Confirm import, shows imported/skipped/total counts with error notes
  - Validation: required fields, duplicate checks, GSTIN length, numeric fields
  - Templates available in both CSV and Excel formats

## Key API Endpoints
### Invoice
- POST /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/pdf?copy_type=...
- GET /api/business-tools/invoices/{id}/pdf-merged?copies=...

### Settings
- GET /api/business-tools/seller-profile (returns billingSettings with companyLogoUrl)
- PUT /api/business-tools/seller-profile

### Export
- GET /api/business-tools/export/sales?format=csv|xlsx&startDate=&endDate=
- GET /api/business-tools/export/profit?format=csv|xlsx&startDate=&endDate=
- GET /api/business-tools/export/inventory?format=csv|xlsx
- GET /api/business-tools/export/buyers?format=csv|xlsx&startDate=&endDate=
- GET /api/business-tools/export/invoices?format=csv|xlsx&startDate=&endDate=

### Import
- GET /api/business-tools/import/template/{type}?format=csv|xlsx
- POST /api/business-tools/import/validate (file + data_type)
- POST /api/business-tools/import/process (file + data_type)

## Prioritized Backlog
### P1
- Seller Reminder Controls (configure reminder schedule, custom messages, enable/disable)
- Admin View for Reports

### P2
- Token-based search, Redis caching, server.py refactor, email reminders
- Refactor inquiry modal to shared component
- Clean unused Pydantic models

## Mocked: Resend email service
