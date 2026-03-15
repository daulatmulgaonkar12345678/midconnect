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
- Backend notification endpoints created
- Notification center page supports: payment_received, partial_payment, invoice_overdue, invoice_created, low_stock, system_alert
- Dashboard metrics page exists but frontend not fully wired

### Inventory Module Improvements (DONE)
- minStock, reorderQuantity, lowStockAlertEnabled fields per product
- Min Stock column, alert toggle, sticky header, scroll fix

### Supplier-Product Mapping (DONE)
- Many-to-many via supplier_products collection
- Supplier create/edit modal includes "Supplied Products" section
- Product dropdown from seller inventory, rate per product

### Low Stock Alert System (DONE)
- low_stock_alerts collection with dedup (1 pending alert per listing)
- Dashboard page with pending/ordered/ignored filter tabs
- Order Material and Ignore actions

### Purchase Order (PO) System (DONE - Feb 2026)
**PO Creation & Management:**
- Auto PO number: PO-{YEAR}-{SEQ} via po_counters collection
- PO items with product details, quantities, rates
- Status tracking: draft → sent → confirmed → received → cancelled
- Professional PDF generation (green theme, ReportLab)
- Purchase Orders listing page with status filter tabs

**PO WhatsApp Workflow:**
- "Order Material" on Low Stock Alerts creates a PO
- After PO creation: Download PDF + Send via WhatsApp options
- WhatsApp message includes PO number, product details, quantity
- PO status auto-updates from draft → sent on WhatsApp send

**Invoice WhatsApp for Buyers:**
- "Send Invoice WhatsApp" button in invoice detail and list
- Message format: greeting, invoice number, total amount, seller name
- Uses wa.me URL with buyer phone number

## Key DB Collections
- users, sellerListings, seller_invoice_counters, invoices, invoice_payments
- seller_notifications, inventory_logs, seller_suppliers
- supplier_products (supplierId, listingId, rate)
- low_stock_alerts (sellerId, listingId, status: pending/ordered/ignored)
- purchase_orders (poNumber, supplierId, items, totalAmount, status)
- po_counters (sellerId, year, sequence)

## Key API Endpoints
- CRUD /api/business-tools/inventory
- POST /api/business-tools/inventory/{id}/adjust
- CRUD /api/business-tools/suppliers (with products mapping)
- GET /api/business-tools/suppliers-for-listing/{id}
- GET/PUT /api/business-tools/low-stock-alerts
- GET /api/business-tools/low-stock-alerts/{id}/order-details
- POST /api/business-tools/purchase-orders
- GET /api/business-tools/purchase-orders
- GET /api/business-tools/purchase-orders/{id}/pdf
- GET /api/business-tools/purchase-orders/{id}/whatsapp-link
- PUT /api/business-tools/purchase-orders/{id}/status
- CRUD /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/pdf
- GET /api/business-tools/invoices/{id}/whatsapp-link?reminder_type=send_invoice

## Prioritized Backlog

### P0 (High)
- Wire up dashboard metrics frontend to backend

### P1 (Medium)
- Admin View for Reports (aggregated data across sellers)
- Seller Reminder Controls (configure reminder schedule)

### P2 (Low)
- Advanced token-based search
- Redis caching for dashboard metrics
- Refactor monolithic server.py into smaller routers
- Clean up unused Pydantic models
- Automatic email reminders

## Mocked Integrations
- Resend email service (MOCKED)
