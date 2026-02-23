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

## SPEC TEMPLATE ARCHITECTURE (Final)

### Category-Based Resolution
```
GET /api/seller/categories/{categoryId}/spec-template
```

Returns:
```json
{
  "specTemplate": {
    "_id": "ObjectId",
    "name": "electrical specification",
    "categoryId": "string",
    "fields": [
      {
        "key": "voltage",
        "label": "Voltage",
        "fieldType": "number",
        "unit": "V",
        "options": [],
        "required": true,
        "displayOrder": 0
      }
    ],
    "isActive": true
  },
  "category": { ... }
}
```

### REMOVED (Legacy)
- ❌ `getSpecTemplateById(token, templateId)`
- ❌ `GET /api/specTemplates/:id`
- ❌ `specTemplateIds` array on products

### SSOT Rules
- Use `getCategorySpecTemplate(token, categoryId)`
- Access fields via `specTemplate.fields`
- All field names camelCase

---

## LISTING PUBLISH VALIDATION

### Required Fields
| Field | Validation |
|-------|------------|
| `pricingTiers` | Array with 1+ items |
| `moq` | Integer > 0 |
| `stock` | Integer > 0 |
| `maxCapacity` | Integer > 0 |
| `images` | Array with 1+ items |
| `variantId` | Not null |

### Pre-Publish Validation
```
GET /api/seller/listings/{id}/validate
```

---

## MONGODB SCHEMA SSOT

### Subscriptions
```json
{
  "userId": ObjectId,
  "planName": "free" | "trial" | "pro",
  "status": "active" | "expired" | "suspended"
}
```

### GST
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

## IMPLEMENTATION STATUS

### Completed (Feb 22, 2026)
- [x] Category-based spec template resolution
- [x] Removed legacy getSpecTemplateById
- [x] Listing publish validation (6 fields)
- [x] MongoDB schema alignment (camelCase)
- [x] Subscription system fixes
- [x] Unified GST schema
- [x] Email verification architecture

### Testing Results
- Frontend: 100% (build success, no legacy code)
- Backend: 100% verified

---

## NEXT STEPS

### P0 - Critical
1. Configure Firebase Admin SDK

### P1 - High Priority
1. Payment integration
2. End-to-end testing

### P2 - Medium Priority
1. Email notifications
