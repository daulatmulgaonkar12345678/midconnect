# MidConnect - B2B Marketplace PRD

## Product Overview
MidConnect is a B2B marketplace platform for industrial products connecting verified manufacturers, dealers, and distributors with buyers across India.

## Core Architecture

### Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB (via Motor async driver)
- **Auth**: Firebase Authentication

### Database Collections
- `users` - User accounts with roles, profile, GST info
- `categories` - Product categories
- `products` - Admin-created product templates
- `productVariants` - Attribute combinations
- `sellerListings` - Seller product offerings
- `specTemplates` - Specification field definitions
- `inquiries` - Buyer-to-seller inquiries

---

## NEW EMAIL VERIFICATION ARCHITECTURE (Feb 22, 2026)

### User Schema Updates
```json
{
  "firebaseUid": "string",
  "email": "string",
  "roles": ["buyer"],
  "isEmailVerified": false,
  "profileComplete": false,
  "status": "pending | active",
  "verificationDeadline": "datetime (createdAt + 24h)",
  "profile": null | {...},
  "gst": {...},
  "subscription": {...}
}
```

### Registration Flow

#### Step 1: Sign Up
```
User submits email/password
    ↓
Firebase user created
    ↓
Frontend gets ID token
    ↓
Backend get_current_user auto-creates MongoDB user
    - isEmailVerified: false
    - status: "pending"
    - profileComplete: false
    - verificationDeadline: now + 24h
    ↓
Verification email sent
    ↓
Redirect to /verify-email
```

#### Step 2: Email Verification
```
User clicks email link
    ↓
Firebase marks email as verified
    ↓
User logs in
    ↓
Backend syncs email_verified from Firebase token
    - Updates isEmailVerified: true
    - Updates status: "active"
    - Removes verificationDeadline
    ↓
Redirect to /complete-profile
```

#### Step 3: Profile Completion
```
User fills profile form (Buyer/Seller)
    ↓
Backend /api/auth/complete-profile
    - UPDATES existing user (not creates new)
    - Sets profileComplete: true
    - Sets roles, profile, gst fields
    - Sets subscription (trial)
    ↓
Redirect to /dashboard
```

### Cleanup & Re-registration

#### Auto Cleanup (Background Task)
```
Every 1 hour:
    ↓
Find users where:
    - isEmailVerified: false
    - verificationDeadline < now
    ↓
For each expired user:
    - Delete Firebase user
    - Delete MongoDB user
```

#### Re-registration Handler
```
POST /api/auth/cleanup-for-reregister
Body: { email: "..." }
    ↓
If user exists AND NOT verified:
    - Delete Firebase user
    - Delete MongoDB user
    - Return { cleaned: true }
    ↓
If user exists AND verified:
    - Return 400: "Already registered"
```

### Seller Permissions Matrix

| Role | Email Verified | Profile Complete | GST Verified | Create Draft | Publish |
|------|----------------|------------------|--------------|--------------|---------|
| Any | No | N/A | N/A | No | No |
| Buyer | Yes | Yes | N/A | No | No |
| Seller | Yes | Yes | No (Pending) | Yes | No |
| Seller | Yes | Yes | Yes | Yes | Yes |

---

## API Endpoints

### Authentication
- `GET /api/auth/check-registration` - Check profileComplete and isEmailVerified status
- `POST /api/auth/complete-profile` - Complete profile (UPDATES existing user)
- `POST /api/auth/cleanup-for-reregister` - Cleanup unverified user for re-registration

### Seller
- `GET /api/seller/status` - Get seller GST/permission status
- `POST /api/seller/listings` - Create listing (draft)
- `POST /api/seller/listings/{id}/publish` - Publish listing (requires verified GST)

---

## Implementation Status

### Completed (Feb 22, 2026)
- [x] TypeScript build error fixed
- [x] 3-step registration flow (Sign Up → Verify Email → Complete Profile)
- [x] MongoDB user auto-creation on Firebase signup
- [x] profileComplete flag tracking
- [x] isEmailVerified sync from Firebase on login
- [x] Background cleanup task for unverified users (24h expiry)
- [x] Re-registration cleanup endpoint
- [x] GST pending banner on seller dashboard
- [x] Seller permission checks on product publishing

### Testing Results (Feb 22, 2026)
- Backend: 100% (14/14 tests passed)
- Frontend: 100% (all pages load, types verified)
- Firebase Auth: NOT CONFIGURED (manual testing required)

---

## Next Steps / Backlog

### P0 - Critical
1. Configure Firebase Admin SDK for production

### P1 - High Priority
1. Full end-to-end test with real Firebase users
2. Admin GST verification workflow
3. Email notification system

### P2 - Medium Priority
1. Enhanced seller analytics
2. Product image upload improvements

### P3 - Low Priority
1. Multi-language support
2. Advanced search filters
