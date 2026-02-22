# MidConnect - B2B Marketplace PRD

## Product Overview
MidConnect is a B2B marketplace platform for industrial products connecting verified manufacturers, dealers, and distributors with buyers across India.

## Core Architecture

### Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB (via Motor async driver)
- **Auth**: Firebase Authentication

---

## UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH

### Schema Structure
```json
{
  "gst": {
    "number": "22AAAAA0000A1Z5",
    "status": "pending" | "verified" | "rejected",
    "verified": boolean
  }
}
```

### GST Status Flow
```
New Seller → gst.status = "pending" → Admin Reviews
    ↓                                      ↓
    └──────────────────────────────────────┤
                                           ↓
                           ┌───────────────┴───────────────┐
                           │ APPROVED         REJECTED     │
                           │ gst.status =     gst.status = │
                           │  "verified"       "rejected"  │
                           └───────────────────────────────┘
```

---

## SUBSCRIPTION SYSTEM - SINGLE SOURCE OF TRUTH

### Data Architecture
```
subscriptions collection ← SSOT for subscription data
    ↓
Used by:
  - /api/seller/subscription/status
  - /api/admin/subscriptions
  - /api/admin/users (joined)
```

### API Response Structure (camelCase)
```json
{
  "subscription": {
    "planName": "free" | "trial" | "pro",
    "status": "active" | "expired" | "suspended",
    "startDate": "ISO date",
    "endDate": "ISO date | null",
    "daysRemaining": number,
    "isExpiringSoon": boolean,
    "isActive": boolean
  },
  "usage": {
    "acceptedThisMonth": number,
    "monthlyLimit": number,
    "remaining": number,
    "limitReached": boolean,
    "resetsOn": "formatted date"
  },
  "features": {
    "canAcceptInquiries": boolean,
    "unlimitedInquiries": boolean,
    "verifiedBadge": boolean,
    "prioritySupport": boolean,
    "analyticsAccess": boolean
  },
  "showExpiryWarning": boolean,
  "showUpgradeCta": boolean
}
```

### Plan Features
| Plan | Inquiry Limit | Verified Badge | Priority Support | Analytics |
|------|---------------|----------------|------------------|-----------|
| Free | 5/month | ❌ | ❌ | ❌ |
| Trial | Unlimited | ❌ | ❌ | ❌ |
| Pro | Unlimited | ✅ | ✅ | ✅ |

---

## EMAIL VERIFICATION ARCHITECTURE

### User Schema
```json
{
  "firebaseUid": "string",
  "email": "string",
  "roles": ["buyer"] | ["buyer", "seller"],
  "isEmailVerified": boolean,
  "profileComplete": boolean,
  "status": "pending" | "active",
  "sellerStatus": "active" | "suspended" | "banned"
}
```

### Registration Flow
1. Sign Up → Firebase user + MongoDB user (isEmailVerified: false)
2. Email Verification → Firebase verifies email
3. Login → Backend syncs isEmailVerified: true
4. Profile Completion → profileComplete: true

---

## API ENDPOINTS

### Seller Subscription
- `GET /api/seller/subscription/status` - Get subscription status with usage and features

### Admin GST Management
- `GET /api/admin/gst/pending` - Get pending GST reviews (returns `pending_reviews` array)
- `PATCH /api/admin/users/{id}/verify-gst` - Verify or reject seller GST

### Admin Users
- `GET /api/admin/users` - List users with subscription fields included

---

## IMPLEMENTATION STATUS

### Completed (Feb 22, 2026)
- [x] Email verification architecture
- [x] Unified GST schema (SSOT)
- [x] Subscription system fixes
  - [x] Variable mismatch fix (snake_case → camelCase)
  - [x] API endpoint alignment (/seller/subscription/status)
  - [x] Admin users subscription columns
- [x] GST pending/rejected banners
- [x] Seller banned/suspended handling

### Testing Results
- Backend: 100% (all tests passed)
- Frontend: 100% verified
- Firebase Auth: NOT CONFIGURED

---

## NEXT STEPS / BACKLOG

### P0 - Critical
1. Configure Firebase Admin SDK for production

### P1 - High Priority
1. Full end-to-end test with real Firebase users
2. Admin UI for GST verification workflow
3. Payment integration for Pro plan

### P2 - Medium Priority
1. Email notifications
2. Enhanced seller analytics

### P3 - Low Priority
1. Multi-language support
2. Advanced search filters
