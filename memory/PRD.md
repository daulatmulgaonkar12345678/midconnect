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

## ENTERPRISE PRODUCT ARCHITECTURE (Phase 1 Activated)

### 4-Layer Model (Now Enforced)
```
Category → SpecTemplate → Product → ProductVariant → SellerListing
                                         ↓
                              searchableAttributes (denormalized)
                              searchableText (full-text ready)
```

### New Collections Activated
```json
// productVariants collection
{
  "_id": ObjectId,
  "productId": ObjectId,
  "attributes": { "power": 45, "voltage": "415" },
  "attributeHash": "abc123...",  // For deduplication
  "templateVersions": [...],
  "isActive": true
}
```

### Denormalized Fields in sellerListings
```json
{
  "variantId": ObjectId,              // Required - links to productVariants
  "searchableAttributes": {...},       // Denormalized from variant
  "searchableText": "motor 45kw...",   // For text search
  "attributeLabels": {...}             // Human-readable labels
}
```

### Enterprise Indexes Created
- `enterprise_text_search` - Weighted text index on searchableText + description
- `product_variant_idx` - Compound index for product/variant queries
- `product_attrs_idx` - Attribute filtering index
- `variant_dedup_idx` - Unique index preventing duplicate variants

### New Enterprise Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /products/{id}/enterprise` | Single aggregation product page |
| `GET /products/{id}/facets` | Dynamic filter values |
| `POST /products/{id}/filter` | Structured attribute filtering with fallback |
| `GET /admin/enterprise/status` | Migration status |
| `POST /admin/enterprise/migrate` | Run enterprise migration |
| `POST /admin/enterprise/indexes` | Create enterprise indexes |

### Fallback Logic (4 Levels)
1. Remove lowest priority filter
2. Expand numeric range ±10%
3. Show other variants same product
4. Show related category products

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

### Completed (Feb 23, 2026 - Session 3)
- [x] **Enterprise Product Page Frontend (Phase 2 Complete)**
  - [x] Identity Block: Product name, breadcrumb, seller/variant counts, price, availability badge
  - [x] Sticky Filter Panel (desktop sidebar) with dynamic filters from `/facets` endpoint
  - [x] Mobile Filter Drawer with slide-in animation
  - [x] Enterprise Seller Cards with spec strips, pricing tiers, MOQ, stock, lead time, RFQ buttons
  - [x] Comparison Mode (max 3 sellers) with side-by-side table
  - [x] URL-synced filter state with 300ms debounce
  - [x] Sort options: Price, Lead Time, Stock (with asc/desc toggle)
  - [x] Fallback UI with elegant messaging for empty states
  - [x] Inquiry Modal with quantity, buyer type, message fields
  - [x] **All 9/9 frontend tests passed (100%)**

### New Frontend Components Created
```
/app/frontend/src/components/enterprise/
├── IdentityBlock.tsx      # Product header with stats
├── FilterPanel.tsx        # Desktop filter sidebar
├── SellerCard.tsx         # Individual seller listing
├── ComparisonTable.tsx    # Side-by-side comparison
├── MobileFilterDrawer.tsx # Mobile slide-in drawer
├── EmptyState.tsx         # No results/listings states
├── InquiryModal.tsx       # RFQ form modal
└── index.ts               # Component exports
```

### Enterprise Product Page Route
- **URL**: `/ep/[productId]` (e.g., `/ep/699be9023cbe1a8c31591668`)
- **Features**: Real-time filtering, URL deep linking, mobile responsive
- **API Used**: `/products/{id}/enterprise`, `/products/{id}/facets`, `/products/{id}/filter`

---

## NEXT STEPS

### P0 - Critical
1. Configure Firebase Admin SDK

### P1 - High Priority
1. Performance & Load Testing (10k, 50k, 100k listings) on enterprise endpoints
2. Deprecate old product page (`/product/[slug]`) after enterprise page is validated
3. Update seller dashboard to display subscription status from new SSOT
4. Show badge (e.g., "Pro Active", "Expired – Free Mode")

### P2 - Medium Priority
1. Usage analytics for filter interactions on enterprise page
2. Payment integration
3. Email notifications
4. Implement "Banned Seller" Status with `sellerStatus` field

### P3 - Future
1. AI Semantic Search Layer with vector embeddings
2. NLP-based query understanding for search
