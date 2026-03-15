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

### Notifications System (DONE - Mar 2026)
- **Sidebar:** Purchase Orders removed, Notifications added below Home with Bell icon + red badge
- **Badge:** Shows unread count, polls every 30s, hidden when 0
- **Page:** Full notification center at /seller/business-tools/notifications
- **Features:** Type filters (All/Low Stock/Invoices/Payments/Purchases/Inventory/System), Unread Only toggle, Mark as Read (single + all), Pagination
- **Backend:** GET /notifications/unread-count, GET /notifications (with type/unread filters), PUT /notifications/{id}/read, PUT /notifications/mark-all-read
- **Testing:** 11/11 backend tests passed

### Auth Fix: Analytics 403 (DONE - Mar 2026)
- Fixed get_seller_id() in analytics_router.py and home_router.py to default accountType to "seller" (matching business_tools_router.py pattern)

## Updated Sidebar Order
Home > Notifications > Inventory > Low Stock Alerts > Buyers > Suppliers > Invoices > Charts & Graphs > Product Analytics > Composite Products > Reports > Employees > Roles & Permissions > Activity Logs > Business Settings

## Key API Endpoints
### Notifications
- GET /api/business-tools/notifications/unread-count
- GET /api/business-tools/notifications?notification_type=&unread_only=&limit=&skip=
- PUT /api/business-tools/notifications/{id}/read
- PUT /api/business-tools/notifications/mark-all-read

## Prioritized Backlog
### P1
- Admin View for Reports
- Seller Reminder Controls

### P2
- Token-based search, Redis caching, server.py refactor, email reminders

## Mocked: Resend email service
