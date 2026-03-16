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

### GST Invoice System (DONE - Mar 2026)
- GST-Compliant PDF with seller/buyer GSTIN, HSN codes, CGST/SGST vs IGST
- 4 Invoice Copies: Original, Transporter, Supplier/CA, Office
- QR Code, Amount in Words, Transport Details, E-Way Bill placeholder

### Invoice Checkbox Modal for Merged PDF (DONE - Mar 2026)
- Single "Download PDF" button opens modal with copy selection checkboxes
- Select All, Download Selected with dynamic count
- Merged PDF via GET /api/business-tools/invoices/{id}/pdf-merged?copies=...

### Centralized Billing Settings (DONE - Mar 2026)
- Billing tab: Bank Details (6 fields), Terms & Conditions
- Auto-rendered on invoice PDF footer

### Company Branding (DONE - Mar 2026)
- New "Company Branding" tab in Business Settings (3 tabs: Profile, Billing, Branding)
- Company Logo upload (PNG/JPG/SVG, max 2MB) stored as billingSettings.companyLogoUrl
- Invoice Background Template upload (PNG/JPG, max 5MB) stored as billingSettings.invoiceBackgroundImage
- Preview modal shows sample invoice layout with logo at top-left + background at 8% opacity
- Remove buttons for both with fallback to default layout
- Multi-company support: each seller stores separate branding
- PDF rendering: Layer 1=Background, Layer 2=Content, Layer 3=Logo (top-left)
- Backend prioritizes companyLogoUrl from billingSettings, falls back to profile.sellerLogoUrl

## Key API Endpoints
### Invoice
- POST /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/pdf?copy_type=original|transporter|supplier|office
- GET /api/business-tools/invoices/{id}/pdf-merged?copies=original,transporter,...
- POST /api/business-tools/invoices/{id}/eway-bill

### Settings
- GET /api/business-tools/seller-profile (returns billingSettings with companyLogoUrl)
- PUT /api/business-tools/seller-profile (accepts billingSettings with companyLogoUrl)

## Sidebar Order
Home > Notifications > Inventory > Low Stock Alerts > Buyers > Suppliers > Invoices > Charts & Graphs > Product Analytics > Composite Products > Reports > Employees > Roles & Permissions > Activity Logs > Business Settings

## Prioritized Backlog
### P1
- Seller Reminder Controls (configure reminder schedule, custom messages, enable/disable)
- Admin View for Reports

### P2
- Token-based search, Redis caching, server.py refactor, email reminders
- Refactor inquiry modal to shared component
- Clean unused Pydantic models

## Mocked: Resend email service
