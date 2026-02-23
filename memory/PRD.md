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

## ENTERPRISE SUBSCRIPTION ARCHITECTURE (Final)

### Single Source of Truth (SSOT)
The `subscriptions` collection is the ONLY source of truth for subscription logic.
**DO NOT** use `users.subscription` for any subscription checks.

### MongoDB Schema
```json
// subscriptions collection
{
  "_id": ObjectId,
  "userId": ObjectId,          // References users._id
  "planName": "free" | "trial" | "pro" | "enterprise",
  "status": "free" | "active" | "trial" | "expired" | "cancelled" | "suspended",
  "startDate": ISODate,
  "endDate": ISODate | null,   // null for free plans
  "enquiryLimit": int,         // -1 for unlimited (pro/enterprise)
  "enquiriesUsed": int,        // Monthly counter, resets on enquiriesResetAt
  "enquiriesResetAt": ISODate  // First of next month
}
```

### Business Rules
1. **Pro/Enterprise (active)**: Unlimited leads, `enquiriesUsed` does NOT increment
2. **Trial (active)**: Defined limit per `enquiryLimit`, counter increments
3. **Free/Expired/Cancelled**: 5 leads/month limit, counter increments
4. **Monthly Reset**: When `enquiriesResetAt < now`, reset `enquiriesUsed` to 0

### Subscription Resolution Flow
```
accept_inquiry
   ↓
get_effective_subscription()    ← SSOT: reads subscriptions collection
   ↓
check_and_update_monthly_usage() ← handles monthly reset
   ↓
can_accept_inquiry()
   ↓
if used >= limit → 403 with detailed error
   ↓
if allowed → accept + increment (only for non-unlimited)
```

### Key Files
- `/app/backend/services/subscription_service.py` - SSOT for all subscription logic
- `/app/backend/seller_products.py` - `accept_inquiry`, `get_seller_stats`, `get_subscription_status`
- `/app/backend/server.py` - `seller_get_subscription_status`, `admin_activate_subscription`

### 403 Error Response (Limit Reached)
```json
{
  "detail": {
    "error": "LIMIT_REACHED",
    "currentCount": 5,
    "limit": 5,
    "resetsInDays": 5,
    "notification": "You've reached your monthly limit...",
    "upgradeUrl": "/seller/subscription"
  }
}
```

---

## PRODUCT ↔ SPEC TEMPLATE ARCHITECTURE (Final)

### MongoDB Schema
```json
// specTemplates collection
{
  "_id": ObjectId,
  "name": "electrical specification",
  "categoryId": ObjectId,
  "fields": [{ "key": "voltage", "label": "Voltage", "fieldType": "number", "unit": "V", "required": true }],
  "isActive": true
}

// products collection
{
  "_id": ObjectId,
  "name": "Industrial Motor",
  "categoryId": ObjectId,
  "specTemplateIds": [ObjectId]  // Array, not singular
}
```

### Architectural Rules (Mandatory)
1. Product can only reference templates that:
   - **Exist** in specTemplates collection
   - **Are active** (isActive != false)
   - **Have matching categoryId**

2. Template delete → Auto-cleanup:
   ```python
   db.products.update_many(
       {"specTemplateIds": template_id},
       {"$pull": {"specTemplateIds": template_id}}
   )
   ```

3. Field naming:
   - ✅ `specTemplateIds` (array, camelCase)
   - ❌ ~~`specTemplateId`~~ (singular)
   - ❌ ~~`spec_template_ids`~~ (snake_case)

---

## IMPLEMENTATION STATUS

### Completed (Feb 23, 2026)
- [x] **Enterprise Subscription Enforcement (P0)**
  - [x] `subscription_service.py` as SSOT
  - [x] `accept_inquiry` enforces limits via `can_accept_inquiry()`
  - [x] Pro/Enterprise: unlimited, counter NOT incremented
  - [x] Free/Expired: 5/month limit, counter incremented
  - [x] Monthly reset via `enquiriesResetAt`
  - [x] Admin activation initializes counters
  - [x] 403 error with detailed response
  - [x] **All 24/24 backend tests passed (100%)**

- [x] Product ↔ SpecTemplate architectural fix
  - [x] `validate_spec_template_ids()` helper function
  - [x] Strict validation on product create/update
  - [x] Template delete auto-cleans product references
  - [x] Cleanup endpoint for existing data
  - [x] Performance indexes
- [x] Category-based spec template resolution
- [x] Listing publish validation
- [x] MongoDB schema alignment
- [x] Subscription system fixes
- [x] Unified GST schema
- [x] Email verification architecture

### Completed (Feb 23, 2026 - Session 2)
- [x] **WhatsApp Button & Contact Masking Feature**
  - [x] Backend: `buyerMasked` for pending (companyInitial, city, state - NO phone/email)
  - [x] Backend: `buyerInfo` for accepted (full contact with phone/email)
  - [x] Backend: `unreadCount` for pending inquiries
  - [x] Backend: Fetch buyer from users collection via `buyerId`
  - [x] Backend: WhatsApp link with 91 prefix
  - [x] Frontend: Polling (30s) for new inquiries
  - [x] Frontend: Notification banner for new inquiries
  - [x] **Security: No phone/email leak before accept (backend enforced)**

### Testing Results
- Backend: 100% (All features verified)
- WhatsApp/Masking: 13/15 tests passed (2 skipped due to test order)

---

## NEXT STEPS

### P0 - Critical
1. Configure Firebase Admin SDK

### P1 - High Priority (Frontend Subscription UI)
1. Update seller dashboard to display subscription status from new SSOT
2. Show badge (e.g., "Pro Active", "Expired – Free Mode")
3. Display limit notification when nearing/at limit
4. Handle 403 error with user-friendly message

### P2 - Medium Priority
1. Payment integration
2. Email notifications
3. Implement "Banned Seller" Status with `sellerStatus` field
