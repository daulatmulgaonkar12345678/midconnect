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
### Phase 2: Receipts, WhatsApp & Overdue System (DONE)
### Phase 3: Seller Onboarding & Branding (DONE)
### Phase 4: Dashboard & Notifications (PARTIALLY DONE)

### Inventory Module Improvements (DONE)
- minStock, reorderQuantity, lowStockAlertEnabled fields per product
- Min Stock column, alert toggle, sticky header, scroll fix

### Supplier-Product Mapping (DONE)
- Many-to-many via supplier_products collection with rates

### Low Stock Alert System (DONE)
- low_stock_alerts with dedup, pending/ordered/ignored/resolved status

### Purchase Order System (DONE)
- Auto PO number: PO-{YEAR}-{SEQ}
- Professional PDF generation (green theme, ReportLab)
- Status: draft → sent → confirmed → partially_received → received / cancelled
- WhatsApp sending to suppliers

### Goods Received (GRN) Flow (DONE - Feb 2026)
**Full Procurement Cycle:**
- Low Stock Alert → PO Created → PO Sent → Supplier Delivers → Receive Goods → Stock Updated

**GRN Features:**
- "Receive Goods" button on confirmed and partially_received POs
- Modal shows each PO item with ordered qty, already received, remaining
- Received quantity input capped at remaining
- Auto stock update: current_stock + received_quantity
- Inventory log: changeType = 'purchase_receipt', reference to PO number
- Low stock alert resolution: pending/ordered → resolved when stock > minStock
- Partial delivery support: partially_received status when not all items fully received
- GRN history stored in goods_receipts collection
- Stock update summary shown on success

**Invoice WhatsApp for Buyers:**
- "Send Invoice WhatsApp" button in invoice detail and list rows

## Key DB Collections
- users, sellerListings, seller_invoice_counters, invoices, invoice_payments
- seller_notifications, inventory_logs, seller_suppliers, supplier_products
- low_stock_alerts, purchase_orders, po_counters
- goods_receipts (sellerId, poId, poNumber, items, notes, receivedBy, receivedAt)

## Key API Endpoints
- CRUD /api/business-tools/inventory
- POST /api/business-tools/inventory/{id}/adjust
- CRUD /api/business-tools/suppliers (with products mapping)
- GET /api/business-tools/suppliers-for-listing/{id}
- GET/PUT /api/business-tools/low-stock-alerts
- POST /api/business-tools/purchase-orders
- GET /api/business-tools/purchase-orders/{id}/pdf
- GET /api/business-tools/purchase-orders/{id}/whatsapp-link
- PUT /api/business-tools/purchase-orders/{id}/status
- POST /api/business-tools/purchase-orders/{id}/receive (GRN)
- GET /api/business-tools/purchase-orders/{id}/receipts (GRN history)
- CRUD /api/business-tools/invoices
- GET /api/business-tools/invoices/{id}/whatsapp-link?reminder_type=send_invoice

## Prioritized Backlog

### P0 (High)
- Wire up dashboard metrics frontend to backend

### P1 (Medium)
- Admin View for Reports
- Seller Reminder Controls

### P2 (Low)
- Advanced token-based search
- Redis caching
- Refactor server.py
- Email reminders

## Mocked Integrations
- Resend email service (MOCKED)
