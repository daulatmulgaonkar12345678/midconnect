# MidConnect B2B Marketplace - PRD

## Project Overview
MidConnect is a B2B marketplace platform connecting verified buyers and sellers across industries in India.

## Original Problem Statement
Implement role-based registration flow with Firebase authentication and MongoDB user management:
- PHASE 1: Email + Password creates Firebase user only, sends verification email
- PHASE 2: After email verification, user selects role (Buyer/Seller) and completes profile
- PHASE 3: Seller status derived from roles array and gst.verified
- PHASE 4/5: Seller product permissions based on GST verification
- PHASE 6: Pincode geo-location lookup
- PHASE 7: Seller dashboard shows GST verification status banner
- PHASE 8: Product status structure (draft/published)
- PHASE 9: Atomic registration (no orphan Firebase users)
- PHASE 10: Enterprise validation checklist

## User Personas

### Buyer
- Can browse products
- Send inquiries
- Connect with verified sellers
- No GST required

### Seller
- Must have GST registration
- Can create draft listings immediately
- Can publish only after GST verification
- Access to seller dashboard with analytics

## Core Requirements (Static)

### Authentication Flow
1. User signs up with email/password → Firebase user created
2. Verification email sent → User verifies
3. After verification → Redirect to /complete-profile
4. User selects role (Buyer/Seller)
5. Fill profile details (GST required for sellers)
6. MongoDB user created with proper schema

### Database Schema (MongoDB)
```json
{
  "email": "string",
  "firebaseUid": "string",
  "roles": ["buyer"] or ["buyer", "seller"],
  "isAdmin": false,
  "profile": {
    "businessName": "string",
    "phone": "string",
    "city": "string",
    "state": "string",
    "pincode": "string",
    "address": "string",
    "latitude": "number",
    "longitude": "number"
  },
  "gst": {
    "number": "string or null",
    "status": "pending | verified | rejected | null",
    "verified": false
  },
  "emailVerified": true,
  "accountStatus": "active",
  "canLogin": true,
  "isActive": true,
  "subscription": {...},
  "favourites": [],
  "recentSearches": [],
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Seller Permissions
- Not seller → Cannot create listings
- Seller + GST pending → Can create drafts, cannot publish
- Seller + GST verified → Full access

## What's Been Implemented (Feb 22, 2026)

### Backend (server.py)
- [x] ProfileCompleteCreate model with role-based validation
- [x] POST /api/auth/complete-profile endpoint
- [x] GET /api/auth/check-registration endpoint
- [x] Updated require_verified_seller to use roles array
- [x] Added require_gst_verified_seller for publish permissions
- [x] GET /api/seller/status endpoint for dashboard status

### Backend (seller_products.py)
- [x] check_seller_role() helper
- [x] check_gst_verified() helper
- [x] get_seller_status() helper
- [x] GST verification check on publish endpoint
- [x] GST verification check on status update to "active"

### Frontend (AuthContext.tsx)
- [x] Updated signIn to return needsEmailVerification
- [x] Updated signUp to only create Firebase user
- [x] Added completeRegistration handler
- [x] Added resendVerificationEmail
- [x] Added checkEmailVerification
- [x] Derived isSeller from roles array
- [x] Added isGstVerified computed property

### Frontend (Pages)
- [x] /register - Step 1 only (email/password), redirects to /verify-email
- [x] /verify-email - Email verification waiting page
- [x] /complete-profile - Role selection + profile form
- [x] /login - Updated to handle email verification flow
- [x] /seller - GST verification status banner

### Frontend (API lib)
- [x] checkRegistrationStatus()
- [x] completeProfile()
- [x] getSellerStatus()

### Types (types/index.ts)
- [x] Updated User interface with roles array
- [x] Added UserGst interface
- [x] Added UserProfile interface
- [x] Added UserSubscription interface

## Prioritized Backlog

### P0 (Critical)
- [x] Role-based registration flow
- [x] Email verification enforcement
- [x] GST field only for sellers
- [x] Seller permission checks

### P1 (Important)
- [ ] Admin panel for GST verification
- [ ] Pincode validation from pincodes collection
- [ ] Lat/lng lookup from pincodes

### P2 (Nice to Have)
- [ ] SMS verification for phone
- [ ] Profile picture upload
- [ ] Seller badge system

## Next Action Items
1. Set up Firebase Admin SDK credentials for backend
2. Seed pincodes collection with Indian pincode data
3. Create admin panel for GST verification workflow
4. Add SMS verification for phone numbers
