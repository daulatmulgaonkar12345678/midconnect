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

## LISTING PUBLISH VALIDATION (Enterprise Grade)

### Validation Rules
- **Drafts**: Can be saved with incomplete data
- **Publishing**: MUST NOT be allowed if mandatory fields are missing
- **Backend enforces**: Frontend validation is NOT security

### Required Fields for Publishing
| Field | Validation | Error Message |
|-------|------------|---------------|
| `pricingTiers` | Array with at least 1 item | "At least one pricing tier required" |
| `moq` | Integer > 0 | "MOQ must be greater than 0" |
| `stock` | Integer > 0 | "Stock quantity must be greater than 0" |
| `maxCapacity` | Integer > 0 | "Maximum capacity must be greater than 0" |
| `images` | Array with at least 1 item | "At least one product image required" |
| `variantId` | Not null | "Product variant must be linked" |

### API Error Response (HTTP 400)
```json
{
  "error": "Listing is incomplete and cannot be published",
  "missingFields": ["pricingTiers", "moq"],
  "fieldErrors": {
    "pricingTiers": "At least one pricing tier required",
    "moq": "MOQ must be greater than 0"
  },
  "message": "Please complete the following fields before publishing: pricingTiers, moq"
}
```

### Pre-Publish Validation Endpoint
```
GET /api/seller/listings/{id}/validate
```
Returns:
```json
{
  "listingId": "abc123",
  "isComplete": false,
  "canPublish": false,
  "missingFields": ["pricingTiers"],
  "fieldErrors": {...},
  "gstVerified": true,
  "accountStatus": "active",
  "blockers": ["Missing fields: pricingTiers"]
}
```

---

## MONGODB SCHEMA SSOT

### Subscriptions Collection
```json
{
  "userId": ObjectId,
  "planName": "free" | "trial" | "pro" | "enterprise",
  "startDate": Date,
  "endDate": Date | null,
  "status": "active" | "expired" | "cancelled" | "suspended",
  "createdAt": Date
}
```

### GST Schema
```json
{
  "gst": {
    "number": string,
    "status": "pending" | "verified" | "rejected",
    "verified": boolean
  }
}
```

---

## API ENDPOINTS

### Seller Listings
- `POST /api/seller/listings` - Create draft listing (allows incomplete)
- `GET /api/seller/listings/{id}/validate` - Pre-publish validation
- `POST /api/seller/listings/{id}/publish` - Publish with validation
- `POST /api/seller/listings/{id}/pause` - Pause listing
- `DELETE /api/seller/listings/{id}` - Archive listing

---

## IMPLEMENTATION STATUS

### Completed (Feb 22, 2026)
- [x] Listing publish validation (6 required fields)
- [x] Pre-publish validation endpoint
- [x] Structured error response with missingFields and fieldErrors
- [x] Banned/suspended seller blocking
- [x] MongoDB schema alignment (camelCase)
- [x] Subscription system fixes
- [x] Unified GST schema
- [x] Email verification architecture

### Testing Results
- Backend: 100% (19/19 tests passed for listing validation)
- All endpoints verified

---

## NEXT STEPS / BACKLOG

### P0 - Critical
1. Configure Firebase Admin SDK for production

### P1 - High Priority
1. Full end-to-end test with real listings
2. Payment integration for Pro plan

### P2 - Medium Priority
1. Email notifications
2. Enhanced analytics

### P3 - Low Priority
1. Multi-language support
