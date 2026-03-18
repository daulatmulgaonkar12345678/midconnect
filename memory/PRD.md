# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management. Recent upgrades: GST-compliant billing, pending orders system, and shipping address management.

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
  models/           - Pydantic models (business_tools.py has ShippingAddressRef)
  utils/            - Shared utilities (permissions.py, gst.py)
  services/         - PDF generation
  constants.py      - Global constants
  server.py         - Main FastAPI app
/app/frontend/src/
  app/seller/business-tools/  - Seller dashboard pages
  components/ui/              - Shadcn components
  lib/                        - Utilities, auth, indian-states
```

## What's Been Implemented

### Completed Features
1. Full B2B Marketplace - Product listings, search, categories, inquiries
2. Seller Dashboard - Products, inventory, invoices, buyers, POs, settings
3. Admin Dashboard - User management, seller verification, subscription mgmt
4. Invoice System - Full CRUD, payments, reminders, PDF generation
5. Inventory Management - Stock tracking, low stock alerts, stock movement logs
6. Purchase Orders - Create, manage, WhatsApp sharing with secure PDF links
7. Buyer Management - CRUD with GSTIN, state, and shipping addresses
8. Pending Orders (Backorder) - Partial fulfillment, stock reservation, simplified workflow
9. Permissions System - Centralized role-based access control
10. Employee Management - Multi-role support per seller
11. Document Sharing - Secure expiring links for invoices/catalogs
12. **GST Billing Engine (COMPLETE):**
    - Automatic CGST/SGST vs IGST calculation based on seller/buyer states
    - Seller settings: State dropdown + GST enabled toggle
    - Buyer records: State field with standard Indian states dropdown
    - Invoice form: HSN, Taxable Amount, CGST, SGST, IGST, Total columns
    - Invoice totals: Taxable, CGST, SGST, IGST, Grand Total breakdown
    - Invoice detail view: Full GST breakdown display
    - Place of Supply: Auto-populated from buyer state, overridable dropdown
    - Backend: 9/9 unit tests passing
13. **Pending Orders Fix (COMPLETE):**
    - Fixed _id→id serialization bug
    - Removed "Create PO", added "Create Invoice" redirect with prefill
    - Improved card layout with all fields
14. **Shipping Address Management (COMPLETE):**
    - Multiple shipping addresses per buyer (CRUD)
    - Address fields: addressLine1, addressLine2, city, state, pincode, country, contactPerson, phone, isDefault
    - Address management modal in Buyers page
    - Shipping address dropdown in invoice creation (auto-populates from buyer)
    - Default address auto-selected on buyer selection
    - Fallback message when no addresses exist
    - Address preview under dropdown
    - Ship To section in invoice detail view
    - Full address snapshot stored with invoice for historical accuracy

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
- `POST /api/business-tools/invoices` - Create invoice (auto GST + shipping address)
- `GET /api/business-tools/gst-config` - States list and GST rates
- `GET /api/business-tools/seller-profile` - Seller profile with state and GST status
- `POST /api/business-tools/buyers` - Create buyer with state
- `GET /api/business-tools/buyers/{id}/shipping-addresses` - List shipping addresses
- `POST /api/business-tools/buyers/{id}/shipping-addresses` - Add shipping address
- `PUT /api/business-tools/buyers/{id}/shipping-addresses/{addrId}` - Update address
- `DELETE /api/business-tools/buyers/{id}/shipping-addresses/{addrId}` - Delete address
- `GET /api/business-tools/pending-orders` - List pending orders
- `POST /api/business-tools/pending-orders/{id}/fulfil` - Fulfil pending order

## Key DB Fields
- `seller_buyers.shippingAddresses[]` - Array of shipping address objects with id, addressLine1, city, state, pincode, country, contactPerson, phone, isDefault
- `invoices.shippingAddress` - Snapshot of selected shipping address at invoice creation time
- `users.profile.state` - Seller's state for GST
- `users.gst.status` - "enabled" or "disabled"
- `invoices.cgst/sgst/igst` - Tax breakdown

## Known Issues
- `firebase_app` lint warning (unused import) - P2, pre-existing
- Enterprise data integrity warnings on startup - pre-existing
