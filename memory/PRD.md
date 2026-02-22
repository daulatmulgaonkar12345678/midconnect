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

## MONGODB SCHEMA SSOT (Single Source of Truth)

### Subscriptions Collection Schema
```json
{
  "userId": ObjectId,           // Required, foreign key to users
  "planName": "free" | "trial" | "pro" | "enterprise",
  "durationDays": number,
  "startDate": Date,
  "endDate": Date | null,
  "status": "active" | "expired" | "cancelled" | "suspended",
  "lastUpdatedBy": ObjectId,    // Admin who last updated
  "updatedAt": Date,
  "notes": string,
  "createdAt": Date
}
```

### Subscription History Collection Schema
```json
{
  "userId": ObjectId,           // camelCase, stored as ObjectId
  "action": "activate" | "extend" | "suspend" | "reactivate",
  "oldSubscription": object,
  "newSubscription": object,
  "adminId": ObjectId,          // camelCase, stored as ObjectId
  "adminEmail": string,
  "note": string,
  "createdAt": Date
}
```

### Field Naming Convention
- **All fields use camelCase** (not snake_case)
- **All IDs stored as ObjectId** (not string)
- ✅ `userId`, `adminId`, `planName`, `startDate`, `endDate`, `daysRemaining`
- ❌ ~~`user_id`~~, ~~`admin_id`~~, ~~`plan_name`~~, ~~`start_date`~~, ~~`end_date`~~

---

## UNIFIED GST SCHEMA

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

---

## EMAIL VERIFICATION ARCHITECTURE

### User Schema
```json
{
  "firebaseUid": string,
  "email": string,
  "roles": ["buyer"] | ["buyer", "seller"],
  "isEmailVerified": boolean,
  "profileComplete": boolean,
  "status": "pending" | "active",
  "sellerStatus": "active" | "suspended" | "banned"
}
```

---

## API ENDPOINTS

### Subscription Admin
- `GET /api/admin/subscriptions/manage/{user_id}` - Get subscription details
- `POST /api/admin/subscriptions/activate/{user_id}` - Activate subscription
- `POST /api/admin/subscriptions/extend/{user_id}` - Extend subscription
- `POST /api/admin/subscriptions/suspend/{user_id}` - Suspend subscription
- `POST /api/admin/subscriptions/reactivate/{user_id}` - Reactivate subscription

### Seller Subscription
- `GET /api/seller/subscription/status` - Get subscription status with usage

---

## IMPLEMENTATION STATUS

### Completed (Feb 22, 2026)
- [x] MongoDB schema alignment (SSOT)
  - [x] All `user_id` → `userId` (camelCase)
  - [x] All IDs stored as ObjectId
  - [x] All `end_date` → `endDate`, `start_date` → `startDate`
  - [x] All `admin_id` → `adminId` in history
  - [x] Try/except validation guards on all admin endpoints
- [x] Subscription system camelCase API responses
- [x] Email verification architecture
- [x] Unified GST schema
- [x] GST status banners

### Testing Results
- Backend: 95% (19/20 tests passed)
- All admin subscription endpoints have validation guards
- Firebase Auth: NOT CONFIGURED

---

## NEXT STEPS / BACKLOG

### P0 - Critical
1. Configure Firebase Admin SDK for production

### P1 - High Priority
1. Full end-to-end test with real Firebase users
2. Payment integration for Pro plan

### P2 - Medium Priority
1. Email notifications
2. Enhanced analytics

### P3 - Low Priority
1. Multi-language support
