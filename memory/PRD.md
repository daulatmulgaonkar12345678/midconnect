# PRD - B2B E-commerce Seller Dashboard (UdyogConnect)

## Original Problem Statement
Build a comprehensive ERP/Business Tools system for sellers on a B2B e-commerce platform.

## Core Architecture
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS + Recharts
- **Backend:** FastAPI + MongoDB (motor async driver)
- **Auth:** Firebase Authentication
- **PDF:** ReportLab
- **Storage:** Cloudinary
- **Email:** Resend (MOCKED)

## What's Been Implemented

### Phase 1-3: Payment Tracking, Receipts, Onboarding (ALL DONE)
### Phase 4: Dashboard & Notifications (PARTIALLY DONE)

### Inventory Module (DONE)
- minStock, reorderQuantity, lowStockAlertEnabled, sticky header, scroll fix

### Supplier-Product Mapping (DONE)
- Many-to-many with rates

### Low Stock Alerts (DONE)
- Deduped alerts, pending/ordered/ignored/resolved

### Purchase Order System (DONE)
- Auto PO number, PDF generation, WhatsApp, status tracking

### Goods Received (GRN) Flow (DONE)
- Receive goods → auto stock update → alert resolution → partial delivery support

### Product Analytics Charts (DONE - Feb 2026)
- **Supplier Price Trend** (multi-supplier line chart)
- **Purchase Quantity Over Time** (bar chart)
- **Inventory Stock Trend** (line chart from logs)
- **Supplier Rate Comparison** (horizontal bar, best price highlight)
- Product dropdown filter, Period selector (7d/30d/3m/6m/1y)
- Summary KPI cards (Total POs, Qty, Spend, Suppliers)
- Smart grouping: daily for <=31 days, monthly otherwise

### Invoice WhatsApp for Buyers (DONE)

## Key DB Collections
- users, sellerListings, seller_invoice_counters, invoices, invoice_payments
- seller_notifications, inventory_logs, seller_suppliers, supplier_products
- low_stock_alerts, purchase_orders, po_counters, goods_receipts

## Key API Endpoints (Analytics)
- GET /api/business-tools/analytics/products
- GET /api/business-tools/analytics/summary?listing_id=
- GET /api/business-tools/analytics/price-trend?listing_id=&period=
- GET /api/business-tools/analytics/purchase-trend?listing_id=&period=
- GET /api/business-tools/analytics/stock-trend?listing_id=&period=
- GET /api/business-tools/analytics/supplier-comparison?listing_id=

## Prioritized Backlog

### P0
- Wire up dashboard metrics frontend

### P1
- Admin View for Reports
- Seller Reminder Controls

### P2
- Token-based search, Redis caching, server.py refactor, email reminders

## Mocked: Resend email service
