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

### Validation Flow
```
Product Create/Update
    ↓
validate_spec_template_ids()
    ↓
For each template ID:
    ├── Convert to ObjectId (or 400)
    ├── Fetch from DB (or 400: "not found")
    ├── Check isActive (or 400: "inactive")
    └── Check categoryId match (or 400: "category mismatch")
    ↓
Return validated ObjectId list
```

### Cleanup Endpoint
```
POST /api/admin/products/cleanup-template-refs
```
Returns:
```json
{
  "productsScanned": 100,
  "productsCleaned": 5,
  "invalidRefsRemoved": 3,
  "categoryMismatchRemoved": 2
}
```

### Database Indexes
```javascript
db.products.createIndex({ specTemplateIds: 1 });
db.specTemplates.createIndex({ categoryId: 1 });
db.specTemplates.createIndex({ categoryId: 1, isActive: 1 });
```

---

## IMPLEMENTATION STATUS

### Completed (Feb 23, 2026)
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

### Testing Results
- Backend: 100% (19/19 tests passed)

---

## NEXT STEPS

### P0 - Critical
1. Configure Firebase Admin SDK

### P1 - High Priority
1. Payment integration
2. End-to-end testing

### P2 - Medium Priority
1. Email notifications
