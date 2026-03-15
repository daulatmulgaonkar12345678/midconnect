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

### Inventory Module Improvements (DONE - Feb 2026)
- `minStock`, `reorderQuantity`, `lowStockAlertEnabled` fields per product
- Min Stock column in table, alert toggle, sticky header, scroll fix

### Low Stock Alert → Order Material → WhatsApp Workflow (DONE - Feb 2026)
**Supplier-Product Mapping:**
- Many-to-many relationship via `supplier_products` collection
- Supplier create/edit modal includes "Supplied Products" section
- Product dropdown from seller inventory, rate per product
- Delete supplier also cleans up mappings

**Low Stock Alert System:**
- `low_stock_alerts` collection tracks alert status (pending/ordered/ignored)
- Deduplication: only 1 pending alert per listing
- Alerts created on stock adjust, inventory update, and invoice stock deduction
- Dashboard page with pending/ordered/ignored filter tabs
- "Order Material" and "Ignore" action buttons

**Order Material Modal:**
- Auto-populated: Product Name, SKU, Specification, Description, Current Stock
- Supplier dropdown filtered by product (from supplier_products)
- Supplier rates visible, Best Price label on lowest rate
- Editable order quantity with estimated cost
- "Send WhatsApp" generates wa.me URL with full product details + seller business name footer

**Alert Status Flow:**
- pending → ordered (after WhatsApp sent)
- pending → ignored (seller dismisses)

## Key DB Collections
- **users:** Extended with seller profile
- **sellerListings:** Inventory with minStock, reorderQuantity, lowStockAlertEnabled
- **seller_invoice_counters:** Atomic per-seller invoice sequences
- **invoices:** Unique invoiceNumber with seller_id
- **invoice_payments:** Payment records with Cloudinary receipt URLs
- **seller_notifications:** Notifications (low_stock, invoice_overdue, payment_received, etc.)
- **inventory_logs:** Stock adjustment history
- **seller_suppliers:** Supplier records per seller
- **supplier_products:** Many-to-many supplier-product mapping with rates
- **low_stock_alerts:** Alert tracking (sellerId, listingId, productName, currentStock, minStock, status)

## Key API Endpoints
- GET/PUT /api/business-tools/inventory
- POST /api/business-tools/inventory/{id}/adjust
- GET /api/business-tools/inventory/low-stock-alerts
- CRUD /api/business-tools/suppliers
- GET /api/business-tools/suppliers/{id} (includes products array)
- GET /api/business-tools/suppliers-for-listing/{listing_id}
- GET /api/business-tools/low-stock-alerts
- GET /api/business-tools/low-stock-alerts/{id}/order-details
- PUT /api/business-tools/low-stock-alerts/{id}/status
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
