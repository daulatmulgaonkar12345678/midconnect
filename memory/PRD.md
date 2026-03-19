# PRD - B2B E-commerce & ERP Platform (UdyogConnect / Udyog Connect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, and buyer management.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (phone OTP)
- **Storage:** Cloudinary | **PDF:** reportlab, PyPDF2 | **Email:** Resend (MOCKED)
- **PWA:** Service Worker + manifest.json | **Offline:** IndexedDB (via idb library)

## Completed Features
1. Full B2B Marketplace + Seller/Admin Dashboards
2. **Invoice System (GST-Compliant)** — Auto CGST/SGST vs IGST, Bill To/Ship To, Freight/TCS/Round Off, Payment Terms, Product Description
3. Inventory Management with HSN Codes + Product Description
4. Purchase Orders + WhatsApp sharing
5. Buyer Management + Shipping Addresses (CRUD)
6. Pending Orders (Backorder) with stock reservation
7. WhatsApp Messaging Engine (Single Source of Truth, 8 templates)
8. **Reporting Phase 1** — Outstanding/Receivables, Purchase, Stock Movement
9. **Reporting Phase 2** — Buyer Ledger, Product Performance, Category Report, Low Stock Analytics
10. **Business Insights Dashboard Widget** — 4 clickable insight cards
11. **HSN + GST in Sales Reports** — HSN Code, Taxable Value, GST% in Products & Product Performance tabs + exports
12. **GST Sales Report (GSTR-1 Compatible)** — B2B/B2C auto-classification, GSTIN validation, Place of Supply, CGST/SGST/IGST split, HSN Summary, 2-sheet Excel export
13. **Bug Fix: Invoice Number Format Consistency** — Fixed pending_orders_router.py generating `INV-XXXX` instead of standard `INV{Abbr}-{Code}-XXXX` format
14. **Invoice "Sent" Status Handling** — Auto-mark sent on WhatsApp share + manual Mark as Sent button
15. **Hybrid Offline Mode + Draft Invoice System (Feb 2026)**:
    - Network Detection (navigator.onLine + event listeners)
    - Global Network Status Indicator (Online/Offline badge in Business Tools header)
    - Smart Toast Notifications (sonner) for network changes and sync progress
    - IndexedDB Offline Storage (via `idb` library) — unified queue for drafts
    - Offline Draft Invoice Creation — saves locally with temp ID, syncs when online
    - Sync Engine — auto-sync on reconnect, sequential queue processing, retry with backoff
    - WhatsApp Offline Guard — blocks WhatsApp actions when offline across all pages
    - Data Caching — invoices, buyers, listings cached in IndexedDB for offline access
    - Dashboard Sync Status Widget — shows pending count, sync button, last sync time
    - PWA Setup — manifest.json, service worker (cache-first for assets, network-first for pages)
    - Service Worker Registration — auto-register on app load
    - Backend Sync Endpoint — POST /api/invoices/sync-offline-draft (server generates real ID/number)

## Report Tabs (15 total)
Outstanding | Purchase | Stock Movement | Buyer Ledger | Product Perf. | Category | Low Stock | GST Report | Sales | Profit | Product Profit | Inventory Value | Products | Stock Status | Top Buyers

## Prioritized Backlog
### P1
1. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
2. Seller Reminder Controls (configurable schedules)

### P2
- GSTR-1 JSON export | Amendment tracking | Custom Material Report | Short link tracking | White-label toggle | WhatsApp Business API
- Enhanced Business Insights (Profit summary, Cash flow alerts, Purchase alerts)

### P3 — Offline Enhancements
- Sync queue panel (pending / failed items details)
- Offline support for inventory updates and purchase orders (full CRUD)
- Conflict resolution UI for inventory mismatches

## Test Coverage: 260+ tests

## Key Files
- `/app/backend/routers/reports_router.py` - All reports (16 endpoints)
- `/app/backend/routers/export_import_router.py` - 13 export endpoints
- `/app/backend/routers/pending_orders_router.py` - Fixed: now uses get_next_invoice_number()
- `/app/backend/routers/invoice_router.py` - Invoice CRUD + sync-offline-draft + mark-sent
- `/app/frontend/src/app/seller/business-tools/reports/page.tsx` - Reports UI (15 tabs)
- `/app/frontend/src/app/seller/business-tools/layout.tsx` - NetworkProvider + Toaster + NetworkIndicator
- `/app/frontend/src/context/NetworkContext.tsx` - Global network state + sync triggers
- `/app/frontend/src/hooks/useNetwork.ts` - Network detection hook
- `/app/frontend/src/hooks/useOfflineInvoices.ts` - Offline invoice management hook
- `/app/frontend/src/lib/offlineStore.ts` - IndexedDB service
- `/app/frontend/src/lib/syncEngine.ts` - Sync queue processor
- `/app/frontend/src/components/NetworkStatusBanner.tsx` - Offline/syncing banner
- `/app/frontend/src/components/ServiceWorkerRegister.tsx` - PWA SW registration
- `/app/frontend/public/manifest.json` - PWA manifest
- `/app/frontend/public/sw.js` - Service worker
