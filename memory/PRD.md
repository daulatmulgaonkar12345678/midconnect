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
- Receive goods -> auto stock update -> alert resolution -> partial delivery support

### Product Analytics Charts (DONE)
- 4 charts: Supplier Price Trend, Purchase Quantity, Stock Trend, Supplier Comparison
- Filters: Product, Supplier, Period (7D/30D/3M/6M/1Y/Custom)

### Invoice WhatsApp for Buyers (DONE)

### Business Tools Home Dashboard (DONE - Mar 2026)
- **Summary Widgets:** Total Products, Low Stock Items, Pending POs, Total Suppliers, Today's Sales, Total Revenue
- **Quick Charts:** Sales Trend (30d line), Purchase Trend (30d bar), Top Selling Products (horizontal bar), Stock Distribution by Category (pie)
- Backend endpoints: /api/business-tools/home/summary, /api/business-tools/home/charts
- Testing: 13/13 backend tests passed

### Charts & Graphs Page (DONE - Mar 2026)
- **6 Charts:** Supplier Price Trend (line), Purchase Quantity Trend (bar), Inventory Stock Trend (line), Supplier Price Comparison (bar), Category Sales Distribution (pie), Top Selling Products (horizontal bar)
- **Advanced Filters:** Category, Product, Supplier, Seller (admin only), Date Range (7D/30D/3M/Custom)
- Backend endpoints: analytics/categories, analytics/category-sales, analytics/top-products
- Navigation: Sidebar updated with Home (first) and Charts & Graphs (between POs and Product Analytics)

## Updated Sidebar Order
Home -> Inventory -> Low Stock Alerts -> Buyers -> Suppliers -> Invoices -> Purchase Orders -> Charts & Graphs -> Product Analytics -> Composite Products -> Reports -> Employees -> Roles & Permissions -> Activity Logs -> Business Settings

## Key DB Collections
- users, sellerListings, seller_invoice_counters, invoices, invoice_payments
- seller_notifications, inventory_logs, seller_suppliers, supplier_products
- low_stock_alerts, purchase_orders, po_counters, goods_receipts, categories

## Key API Endpoints
### Home
- GET /api/business-tools/home/summary
- GET /api/business-tools/home/charts

### Analytics
- GET /api/business-tools/analytics/products
- GET /api/business-tools/analytics/suppliers?listing_id=
- GET /api/business-tools/analytics/categories
- GET /api/business-tools/analytics/summary?listing_id=
- GET /api/business-tools/analytics/price-trend?listing_id=&period=&supplier_id=
- GET /api/business-tools/analytics/purchase-trend?listing_id=&period=&supplier_id=
- GET /api/business-tools/analytics/stock-trend?listing_id=&period=
- GET /api/business-tools/analytics/supplier-comparison?listing_id=
- GET /api/business-tools/analytics/category-sales?period=&category_id=&seller_id_filter=
- GET /api/business-tools/analytics/top-products?period=&category_id=&seller_id_filter=

## Database Indexes Added
- invoices: (sellerId, createdAt)
- purchase_orders: (sellerId, createdAt), (sellerId, status)
- inventory_logs: (sellerId, listingId, createdAt)
- supplier_products: (sellerId, listingId)

## Prioritized Backlog

### P1
- Admin View for Reports
- Seller Reminder Controls

### P2
- Token-based search, Redis caching, server.py refactor, email reminders
- Clean up unused Pydantic models in business_tools.py

## Mocked: Resend email service
