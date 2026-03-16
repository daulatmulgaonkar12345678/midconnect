# PRD - B2B E-commerce Seller Dashboard (UdyogConnect)

## Original Problem Statement
Build a comprehensive ERP/Business Tools system for sellers on a B2B e-commerce platform.

## Core Architecture
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS + Recharts
- **Backend:** FastAPI + MongoDB (motor async driver)
- **Auth:** Firebase Authentication
- **PDF:** ReportLab + qrcode
- **Storage:** Cloudinary (receipts/logos)
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
- **GST-Compliant PDF Template:** Seller/Buyer GSTIN, HSN codes, CGST/SGST vs IGST (auto-detected), bank details, terms & conditions, authorized signatory
- **4 Invoice Copies:** Original for Recipient, Duplicate for Transporter, Triplicate for Supplier/CA, Office Copy — generated on-the-fly via `copy_type` parameter
- **QR Code:** Contains Invoice No, Seller GSTIN, Buyer GSTIN, Amount, Date
- **Amount in Words:** Indian numbering (Lakh, Crore)
- **Transport Details:** Transporter Name, LR Number, Vehicle Number, Booking Location, No. of Packages
- **E-Way Bill:** Placeholder endpoint returns JSON + redirects to ewaybillgst.gov.in
- **Frontend:** 4 download buttons per invoice, transport/GST fields in form, E-Way Bill button
- **Testing:** 22/22 backend tests passed

## Key API Endpoints
### Invoice (Updated)
- POST /api/business-tools/invoices (new fields: poNumber, challanNumber, placeOfSupply, transport, termsAndConditions, items.hsnCode, items.discount)
- GET /api/business-tools/invoices/{id}/pdf?copy_type=original|transporter|supplier|office
- POST /api/business-tools/invoices/{id}/eway-bill

## Sidebar Order
Home > Notifications > Inventory > Low Stock Alerts > Buyers > Suppliers > Invoices > Charts & Graphs > Product Analytics > Composite Products > Reports > Employees > Roles & Permissions > Activity Logs > Business Settings

## Prioritized Backlog
### P1
- Admin View for Reports
- Seller Reminder Controls

### P2
- Token-based search, Redis caching, server.py refactor, email reminders

## Mocked: Resend email service
