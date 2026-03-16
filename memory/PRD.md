# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management. Recent upgrade: GST-compliant billing and professional reporting system.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB (Motor), Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary
- **PDF:** reportlab, PyPDF2
- **Email:** Resend (MOCKED)
- **Charts:** recharts

## Architecture
```
/app/backend/
  routers/          - All API routers
  models/           - Pydantic models
  utils/            - Shared utilities (permissions.py, gst.py)
  services/         - PDF generation, etc.
  constants.py      - Global constants
  server.py         - Main FastAPI app
/app/frontend/src/
  app/seller/business-tools/  - Seller dashboard pages
  components/ui/              - Shadcn components
  lib/                        - Utilities, auth, indian-states
```

## What's Been Implemented

### Completed Features
1. **Full B2B Marketplace** - Product listings, search, categories, inquiries
2. **Seller Dashboard** - Products, inventory, invoices, buyers, POs, settings
3. **Admin Dashboard** - User management, seller verification, subscription mgmt
4. **Invoice System** - Full CRUD, payments, reminders, PDF generation
5. **Inventory Management** - Stock tracking, low stock alerts, stock movement logs
6. **Purchase Orders** - Create, manage, WhatsApp sharing with secure PDF links
7. **Buyer Management** - CRUD with GSTIN and state fields
8. **Pending Orders (Backorder)** - Partial fulfillment, stock reservation, simplified workflow
9. **Permissions System** - Centralized role-based access control
10. **Employee Management** - Multi-role support per seller
11. **Document Sharing** - Secure expiring links for invoices/catalogs
12. **GST Billing Engine (P0 - COMPLETE):**
    - Automatic CGST/SGST vs IGST calculation based on seller/buyer states
    - Seller settings: State dropdown + GST enabled toggle
    - Buyer records: State field with standard Indian states dropdown
    - Invoice form: HSN, Taxable Amount, CGST, SGST, IGST, Total columns
    - Invoice totals: Taxable, CGST, SGST, IGST, Grand Total breakdown
    - Invoice detail view: Full GST breakdown display
    - Place of Supply: Auto-populated from buyer state, overridable dropdown
    - Backend: 9/9 unit tests passing
13. **Pending Orders Fix (COMPLETE):**
    - Fixed _id→id serialization bug causing undefined in API calls
    - Removed "Create PO" button (procurement not part of backorder workflow)
    - Added "Create Invoice" button → redirects to invoices page with prefilled buyer/product/qty
    - Improved card layout: Product, Buyer, Ref Invoice, Ordered, Fulfilled, Pending, Stock, Available
    - Stock = total physical inventory, Available = stock - reserved

### Mocked
- Resend email service (no API key configured)

## Prioritized Backlog

### P1 - Next Up
- **GST Batch 2:** GST-compliant PDF invoice layout, GST Summary Report (GSTR-1), Place of Supply on PDF
- **Standardize Reports:** Professional Sales, Inventory, Profit, Low Stock, Stock Movement reports
- **Seller Reminder Controls:** Configurable smart reminder schedules for invoices
- **Admin View for Reports:** Aggregated data views for admin users

### P2 - Future
- Refactor inquiry modal to shared component
- Advanced token-based search system
- Admin search insights dashboard
- Redis caching for performance
- WhatsApp Business API upgrade
- Extract GST/backorder logic into service files

## Key API Endpoints
- `POST /api/business-tools/invoices` - Create invoice (auto GST)
- `GET /api/business-tools/gst-config` - States list and GST rates
- `POST /api/business-tools/gst-calculate` - Preview GST calculation
- `GET /api/business-tools/seller-profile` - Seller profile with state and GST status
- `PUT /api/business-tools/seller-profile` - Update profile including gstStatus
- `POST /api/business-tools/buyers` - Create buyer with state
- `PUT /api/business-tools/buyers/{id}` - Update buyer with state
- `GET /api/business-tools/pending-orders` - List pending orders (returns `id` field)
- `POST /api/business-tools/pending-orders/{id}/fulfil` - Fulfil pending order
- `POST /api/business-tools/pending-orders/{id}/cancel` - Cancel pending order
- `POST /api/business-tools/pending-orders/{id}/notify` - Notify buyer via WhatsApp

## Key DB Fields
- `users.profile.state` - Seller's state for GST
- `users.gst.number` - Seller's GSTIN
- `users.gst.status` - "enabled" or "disabled"
- `seller_buyers.state` - Buyer's state for GST
- `seller_buyers.gstNumber` - Buyer's GSTIN
- `invoices.cgst/sgst/igst` - Tax breakdown
- `invoices.placeOfSupply/sellerState/buyerState/taxType` - GST context
- `pending_orders` - sellerId, buyerId, listingId, orderedQty, fulfilledQty, pendingQty, price, gstPercent, status

## Known Issues
- `firebase_app` lint warning (unused import) - P2, pre-existing
- Enterprise data integrity warnings on startup (empty searchableAttributes/images) - pre-existing
