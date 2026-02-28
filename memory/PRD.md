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

## Session: 2026-02-28 (Email Verification - Final Fix)

### Issue Fixed: Send Email Not Working on Signup

**Root Cause**: After `createUserWithEmailAndPassword()`, Firebase auto-logs in the user which triggers `onAuthStateChanged`. This causes state changes and component re-renders, and the `sendVerificationEmail(email)` call sometimes gets swallowed before executing.

**Enterprise Fix Applied**:
Both `/send-verification` and `/resend-verification` endpoints now:
- Use auth token (not email in body)
- Backend gets user email from the Firebase auth token
- Eliminates race condition by getting token immediately after signup

**Changes Made (2026-02-28)**:

**Backend (`/app/backend/server.py`)**:
- `/api/send-verification`: Removed `SendVerificationRequest` body model, now uses auth token

**Frontend (`/app/frontend/src/lib/api.ts`)**:
- `sendVerificationEmail(token)`: Now takes auth token, not email

**Frontend (`/app/frontend/src/context/AuthContext.tsx`)**:
- `signUp()`: Gets token IMMEDIATELY after Firebase signup, then calls `sendVerificationEmail(token)`

**Test Results**:
- `/api/send-verification` with auth: ✅ 200 OK
- `/api/resend-verification` with auth: ✅ 200 OK
- Full verification flow working

## Session: 2026-02-27 (Email Verification - Enterprise Fix)

### Issue Fixed: Email Verification Loop + 400 Resend Error

**Root Causes Identified**:
1. **Mixed Verification Sources**: System was mixing Firebase `email_verified` with MongoDB `isEmailVerified`, causing confusion
2. **Resend Required Body**: `/api/resend-verification` required email in request body but should use auth token
3. **Firebase Blocking Access**: Backend was using Firebase `email_verified` to block access, should use MongoDB SSOT

**Enterprise Architecture Fix**:

```
Firebase → Identity Provider ONLY (authentication)
MongoDB → Single Source of Truth for ALL business logic (verification status, profile, etc.)
```

**Changes Made**:

**Backend (`/app/backend/server.py`)**:
1. `get_current_user()`: Removed Firebase `email_verified` sync logic. MongoDB `isEmailVerified` is now SSOT
2. `/api/resend-verification`: Now uses auth token to get user, no body required
3. `/api/auth/complete-profile`: Uses MongoDB `isEmailVerified` instead of Firebase
4. `/api/auth/check-registration`: Returns only MongoDB verification status

**Frontend (`/app/frontend/src/lib/api.ts`)**:
- `resendVerificationEmail()`: Now takes auth token, no email parameter

**Frontend (`/app/frontend/src/context/AuthContext.tsx`)**:
- Updated `resendVerificationEmail` signature - no email param
- Uses auth token from logged-in user

**Frontend (`/app/frontend/src/app/verify-email/page.tsx`)**:
- Updated to call resend without email parameter

**Test Results**:
- `/api/resend-verification` (with auth): 200 OK, sends verification email
- `/api/verify-email`: 200 OK, updates MongoDB `isEmailVerified` to `true`
- `/api/users/me`: Returns correct `isEmailVerified` from MongoDB
- `/api/auth/check-registration`: Returns correct verification status

**Expected Flow**:
1. User registers → stored with `isEmailVerified=false`
2. Verification email sent (Zoho SMTP or MOCK)
3. User clicks link → backend sets `isEmailVerified=true`
4. `/users/me` returns verified status
5. Access granted

No Firebase verification used in business logic.

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
