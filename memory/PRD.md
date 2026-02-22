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

## UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH (Feb 22, 2026)

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

### Removed Legacy Fields
- ❌ `gstNumber` (flat field)
- ❌ `gstStatus` (flat field)
- ❌ `business.gst`
- ❌ `business.gst_verified`
- ❌ `isSeller` (use `roles.includes("seller")`)

### GST Status Flow
```
New Seller Registration
    ↓
gst.status = "pending"
gst.verified = false
    ↓
Admin Reviews
    ↓
┌─────────────────┬─────────────────┐
│   APPROVED      │   REJECTED      │
├─────────────────┼─────────────────┤
│ gst.status =    │ gst.status =    │
│  "verified"     │  "rejected"     │
│ gst.verified =  │ gst.verified =  │
│  true           │  false          │
└─────────────────┴─────────────────┘
```

### Seller Permission Matrix
| GST Status | Can Create Draft | Can Publish | Banner Color |
|------------|------------------|-------------|--------------|
| `none`     | ❌ No            | ❌ No       | N/A          |
| `pending`  | ✅ Yes           | ❌ No       | Amber        |
| `verified` | ✅ Yes           | ✅ Yes      | None         |
| `rejected` | ✅ Yes           | ❌ No       | Red          |

### Seller Account Status
| Status | Can Access Dashboard | Can Create Listings | Banner |
|--------|---------------------|---------------------|--------|
| `active` | ✅ Yes | ✅ Yes | None |
| `suspended` | ✅ Yes | ❌ No | Orange |
| `banned` | ✅ Yes | ❌ No | Red |

---

## Email Verification Architecture

### User Schema
```json
{
  "firebaseUid": "string",
  "email": "string",
  "roles": ["buyer"] | ["buyer", "seller"],
  "isEmailVerified": boolean,
  "profileComplete": boolean,
  "status": "pending" | "active",
  "verificationDeadline": "datetime",
  "sellerStatus": "active" | "suspended" | "banned",
  "profile": { ... },
  "gst": { number, status, verified },
  "subscription": { ... }
}
```

### Registration Flow
1. Sign Up → Firebase user created, MongoDB user created with `isEmailVerified: false`
2. Email Verification → Firebase verifies email
3. Login → Backend syncs `isEmailVerified: true`
4. Profile Completion → User fills profile, `profileComplete: true`

### Background Cleanup
- Hourly task deletes users where `isEmailVerified: false` AND `verificationDeadline < now`
- Deletes from both MongoDB and Firebase

---

## API Endpoints

### Authentication
- `GET /api/auth/check-registration` - Check profile and email verification status
- `POST /api/auth/complete-profile` - Complete profile (updates existing user)
- `POST /api/auth/cleanup-for-reregister` - Cleanup unverified user for re-registration

### Admin GST Management
- `GET /api/admin/gst/pending` - Get pending GST reviews (returns `pending_reviews` array)
- `PATCH /api/admin/users/{id}/verify-gst` - Verify or reject seller GST

### Seller
- `GET /api/seller/status` - Get seller GST and permission status
- `POST /api/seller/listings` - Create listing (draft)
- `POST /api/seller/listings/{id}/publish` - Publish listing (requires `gst.status: "verified"`)

---

## Implementation Status

### Completed (Feb 22, 2026)
- [x] Email verification architecture (7 steps)
- [x] Unified GST schema (SSOT)
- [x] Legacy field removal from queries
- [x] GST pending/rejected banners on seller dashboard
- [x] Seller banned/suspended handling
- [x] Admin GST pending endpoint with correct response format
- [x] AuthContext exposes `gstStatus` and `sellerStatus`

### Testing Results
- Backend: 100% (all tests passed)
- Frontend: 100% (code review verified)
- Firebase Auth: NOT CONFIGURED

---

## Next Steps / Backlog

### P0 - Critical
1. Configure Firebase Admin SDK for production

### P1 - High Priority
1. Full end-to-end test with real Firebase users
2. Admin UI for GST verification workflow
3. GST re-upload flow for rejected sellers

### P2 - Medium Priority
1. Email notifications (welcome, verification reminder)
2. Enhanced seller analytics

### P3 - Low Priority
1. Multi-language support
2. Advanced search filters
