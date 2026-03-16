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
- GST-Compliant PDF Template with seller/buyer GSTIN, HSN codes, CGST/SGST vs IGST
- 4 Invoice Copies: Original, Transporter, Supplier/CA, Office
- QR Code, Amount in Words (Indian numbering), Transport Details
- E-Way Bill placeholder endpoint

### Invoice Checkbox Modal for Merged PDF (DONE - Mar 2026)
- Replaced 4 separate download buttons with single "Download PDF" button
- Modal with checkboxes for selecting invoice copies (all selected by default)
- Select All option, Download Selected with dynamic count
- Calls GET /api/business-tools/invoices/{id}/pdf-merged?copies=...
- Single merged PDF with one copy per page

### Centralized Billing Settings (DONE - Mar 2026)
- Business Settings page has "Billing Settings" tab
- Bank Details (6 fields), Terms & Conditions textarea, Invoice Background Image upload
- Background renders as 8% opacity watermark on invoice PDFs
- Bank details and T&C auto-rendered in invoice footer

## Key API Endpoints
### Invoice
- POST /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/pdf?copy_type=original|transporter|supplier|office
- GET /api/business-tools/invoices/{id}/pdf-merged?copies=original,transporter,...
- POST /api/business-tools/invoices/{id}/eway-bill

### Settings
- GET /api/business-tools/seller-profile
- PUT /api/business-tools/seller-profile (accepts billingSettings object)

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
