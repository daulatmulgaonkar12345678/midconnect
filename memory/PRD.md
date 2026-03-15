# PRD - B2B E-commerce Seller Dashboard (UdyogConnect)

## Original Problem Statement
Build a comprehensive ERP/Business Tools system for sellers on a B2B e-commerce platform.

## Core Architecture
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS
- **Backend:** FastAPI + MongoDB (motor async driver)
- **Auth:** Firebase Authentication
- **PDF:** ReportLab
- **Storage:** Cloudinary
- **Email:** Resend (MOCKED)

## What's Been Implemented

### Phase 1: Advanced Payment Tracking (DONE)
- Partial payments, payment history, automatic status recalculation

### Phase 2: Receipts, WhatsApp & Overdue System (DONE)
- Cloudinary receipt uploads, WhatsApp follow-up, automatic overdue detection

### Phase 3: Seller Onboarding & Branding (DONE)
- Seller profile completion, dynamic invoice numbering (INV-{ABBR}-{CODE}-{SEQ}), branded PDFs

### Phase 4: Dashboard & Notifications (PARTIALLY DONE)
- Backend notification endpoints created and working
- Notification center page exists with support for: payment_received, partial_payment, invoice_overdue, invoice_created, low_stock, system_alert
- Dashboard metrics page exists but frontend not fully wired

### Inventory Module Improvements (DONE - Feb 2026)
- Added `minStock`, `reorderQuantity`, `lowStockAlertEnabled` fields per product
- Min Stock column in inventory table
- Edit mode: Minimum Stock input + Alert toggle (Bell on/off)
- Adjust Stock modal shows Minimum Stock info + low stock warning
- Low stock notification (`low_stock` type) auto-created when `current_stock <= minStock` (on adjust, update, and invoice deduction)
- Notifications page updated with orange theme for low_stock alerts
- **Table scroll fix:** max-height 70vh, vertical scroll, horizontal only on overflow
- **Sticky table header** for large inventories

### Critical Architectural Fixes (DONE)
- Multi-seller invoice numbering with atomic counters
- Data migration for historical data

## Key DB Collections
- **users:** Extended with seller profile
- **sellerListings:** Inventory with minStock, reorderQuantity, lowStockAlertEnabled
- **seller_invoice_counters:** Atomic per-seller invoice sequences
- **invoices:** Unique invoiceNumber with seller_id
- **invoice_payments:** Payment records with Cloudinary receipt URLs
- **seller_notifications:** Notifications (low_stock, invoice_overdue, payment_received, etc.)
- **inventory_logs:** Stock adjustment history

## Key API Endpoints
- GET/PUT /api/business-tools/inventory
- POST /api/business-tools/inventory/{id}/adjust
- GET /api/business-tools/inventory/low-stock-alerts
- GET /api/business-tools/notifications
- PUT /api/business-tools/notifications/{id}/read
- POST/GET /api/business-tools/invoices
- GET /api/business-tools/reports/sales-summary
- GET/PUT /api/business-tools/seller-profile

## Prioritized Backlog

### P0 (High)
- Wire up dashboard metrics frontend to backend

### P1 (Medium)
- Admin View for Reports (aggregated data across sellers)
- Seller Reminder Controls (configure reminder schedule)
- Refactor inline inquiry modal to shared InquiryModal.tsx

### P2 (Low)
- Advanced token-based search
- Admin search insights dashboard
- Redis caching for dashboard metrics
- Refactor monolithic server.py into smaller routers
- Clean up unused Pydantic models in business_tools.py
- Automatic email reminders as notification channel

## Mocked Integrations
- Resend email service (MOCKED)
