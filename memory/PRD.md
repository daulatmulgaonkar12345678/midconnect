# MidConnect B2B Marketplace - Product Requirements Document

## Original Problem Statement
Build an enterprise-grade B2B marketplace platform ("midconnect") that connects industrial buyers with verified sellers. The platform enables:
- Product catalog management with technical specifications
- Buyer inquiry system with seller quotation workflow
- WhatsApp-based communication for quote delivery
- Subscription-based seller access control

## Core Requirements
1. **Multi-layer product architecture**: Category → SpecTemplate → Product → ProductVariant → SellerListing
2. **Buyer-seller inquiry flow**: Buyers submit RFQs, sellers accept/reject with quotes
3. **Contact masking**: Buyer details hidden until inquiry accepted
4. **Subscription limits**: Free tier has lead limits, paid plans for unlimited

## What's Been Implemented

### Session: 2026-02-27

#### P0: True SSOT Quotation Architecture - COMPLETE
**Issues Fixed:**
1. Fixed indentation error (QuotationService code was outside function)
2. Removed duplicate quote storage in `inquiries` collection
3. `whatsapp_link` NameError - variable was undefined
4. Manual quote reconstruction in return block

**Implementation:**
- Quote now ONLY stored in `quotes` collection via `QuotationService.create_quote()`
- WhatsApp message ONLY generated via `QuotationService.generate_whatsapp_preview()`
- Inquiry only stores status + reference to quote (no embedded quote data)
- Frontend maps `unitPrice` → `price`, `validityDate` → `validTill`
- No hardcoded fallbacks ("B2B Market Place", "Your Business")

**New 9-Step Flow:**
```
1. Validate price (> ₹0)
2. Governance check (banned/suspended)
3. Subscription check (lead limit)
4. Fetch inquiry
5. Update inquiry status ONLY
6. Create quote via QuotationService
7. Generate WhatsApp preview via QuotationService
8. Build whatsapp_link
9. Return { whatsappLink, quote: quote_result }
```

#### Previous Fixes (Local - Pending Deployment)
- Admin Panel "N/A" Product Name fix
- Public Data Visibility fix (flexible aggregation)
- CORS Policy fix for `udyogconnect.in`
- Cold Start Prevention (BackendWarmup + GitHub Actions ping)
- Timezone Display fix

### Architecture
```
/app/
├── backend/
│   ├── seller_products.py           # Seller listing & inquiry management
│   │   └── accept_inquiry()         # SSOT: Uses QuotationService only
│   ├── services/
│   │   └── quotation_service.py     # SSOT for all quotes
│   │       ├── create_quote()       # Creates quote in 'quotes' collection
│   │       └── generate_whatsapp_preview()  # Generates WhatsApp message
│   └── server.py                    # Main FastAPI app
├── frontend/
│   ├── src/app/
│   │   └── seller/inquiries/page.tsx  # Uses whatsappLink from backend
│   └── src/lib/api.ts               # Updated acceptInquiry response type
```

## Database Schema

### quotes Collection (SSOT for all quotes)
```json
{
  "quoteId": "QT-XXXXX",
  "inquiryId": ObjectId,
  "sellerId": ObjectId,
  "buyerId": ObjectId,
  "productId": ObjectId,
  "productName": String,
  "sellerName": String,
  "buyerName": String,
  "unitPrice": Number,
  "moq": Number,
  "totalPrice": Number,
  "leadTimeDays": Number,
  "validityDate": ISODate,
  "status": "sent" | "viewed" | "accepted" | "rejected" | "expired"
}
```

### inquiries Collection (Status + Reference Only)
```json
{
  "status": "pending" | "accepted" | "rejected",
  "quoteId": String,  // Reference to quotes.quoteId
  "acceptedAt": ISODate,
  "updatedAt": ISODate
  // NO embedded quote data (SSOT compliance)
}
```

## Prioritized Backlog

### P0 (Critical)
- [x] Quotation SSOT Fix - Completed 2026-02-27
- [x] Email Verification Blocking I/O Fix - Completed 2026-02-27
- [ ] Backend Deployment to Render - Required for all fixes to go live

### P1 (High Priority)
- [x] Custom Email Verification (Zoho SMTP) - Architecture complete
- [ ] Enterprise Search - Atlas Indexing (Phase 2)
- [ ] Admin & Seller Dashboard audit

### P2 (Medium Priority)
- [ ] Number formatting in product attributes
- [ ] Code linting warnings cleanup
- [ ] Remove obsolete components (EnterpriseSearchBar.tsx, Header.tsx)
- [ ] AI Semantic Search Layer
- [ ] Online Payments for Quotes
- [ ] Counter-Offer System

## Session: 2026-02-27 (Email Verification Fix)

### Issue Fixed: CORS Errors During Email Verification
**Root Cause**: Multiple issues were identified:

1. **Frontend API Prefix Missing**: The `fetchAPI` function was not prepending `/api` to endpoints. All backend routes require this prefix for proper Kubernetes ingress routing.

2. **Blocking I/O in Async**: The original `send_verification_email()` used synchronous `smtplib.SMTP_SSL()` inside an async endpoint, blocking the event loop.

3. **No Mock Mode**: When Zoho SMTP credentials were not configured, the service returned an error instead of gracefully degrading.

4. **Timezone Comparison**: The `verify_token()` function compared naive and aware datetimes, causing a TypeError.

**Fixes Applied**:

**Frontend (`/app/frontend/src/lib/api.ts`)**:
- `fetchAPI()`: Added automatic `/api` prefix for all endpoints
- Health check URL: Changed `/health` to `/api/health`
- Admin export URL: Changed `/admin/...` to `/api/admin/...`

**Backend (`/app/backend/services/email_verification_service.py`)**:
- Refactored to use `asyncio.to_thread()` for non-blocking SMTP
- Added MOCK mode that generates tokens and logs verification links when credentials aren't configured
- Fixed timezone comparison in `verify_token()` to handle naive datetimes from MongoDB

**Backend (`/app/backend/.env`)**:
- Added `FRONTEND_URL` for proper verification link generation

**Test Results**:
- `/api/send-verification`: 200 OK, generates verification link (MOCK mode in preview)
- `/api/verify-email`: 200 OK, successfully marks user as verified
- Full flow tested: send → verify → user status updated

## Technical Decisions

### SSOT for Quotation Messages
- **Decision**: QuotationService is the ONLY source for quotes and WhatsApp messages
- **Rationale**: 
  - Prevents duplicate/inconsistent messages
  - Single place to update quote format
  - Seller name always from DB lookup
  - No hardcoded business names
- **Implementation**: 
  - `accept_inquiry()` calls `QuotationService.create_quote()`
  - `accept_inquiry()` calls `QuotationService.generate_whatsapp_preview()`
  - Returns `whatsappLink` to frontend
  - Frontend only calls `window.open(whatsappLink)`

### Data Flow (Accept Inquiry)
```
Frontend: Accept Inquiry (click)
    ↓
Backend: accept_inquiry()
    ↓
    ├── Price Validation (> ₹0)
    ├── Governance Check
    ├── Subscription Check
    ├── Update Inquiry Status ONLY
    ├── QuotationService.create_quote() → quotes collection
    ├── QuotationService.generate_whatsapp_preview()
    └── Return { whatsappLink, quote }
    ↓
Frontend: window.open(whatsappLink)
```

## Deployment Notes
- Frontend: Vercel (auto-deploy)
- Backend: Render (manual deploy required)
- Database: MongoDB Atlas
- **CRITICAL**: Backend changes require manual Render deployment

## Post-Deployment Verification Checklist
- [ ] Accept inquiry twice - confirm identical WhatsApp message
- [ ] Verify seller name from DB (never hardcoded)
- [ ] Verify no ₹0 quotes possible
- [ ] Verify quote only in `quotes` collection (not in `inquiries.quote`)
