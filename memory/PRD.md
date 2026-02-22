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

## Role-Based Registration Flow

### Step 1: Sign Up
- User provides email/password
- Firebase user created
- Verification email sent
- **NO MongoDB user created yet**

### Step 2: Email Verification
- User clicks verification link
- User redirected to verify-email page
- Can resend verification email

### Step 3: Profile Completion
- User selects role: **Buyer** or **Seller**
- Fills profile fields:
  - Business Name, Phone, Address, City, State, Pincode
  - **Seller Only**: GST Number (mandatory)
- MongoDB user created with:
  - `roles`: ["buyer"] or ["buyer", "seller"]
  - `gst.status`: "pending" for sellers
  - `gst.verified`: false

### Seller States (Derived, NOT stored)
- **Not Seller**: Cannot access seller features
- **Seller (GST Pending)**: Can create drafts, cannot publish
- **Seller (GST Verified)**: Full permissions

## Key Features

### Buyer Features
- Browse products by category
- Search products
- Send inquiries to sellers
- Track inquiry status

### Seller Features
- Create product listings
- Set tier-based pricing
- Respond to buyer inquiries
- Quick price updates
- Subscription management

### Admin Features
- Manage categories and products
- Verify seller GST
- View analytics
- Manage user accounts

## Pincode Geolocation
- On profile completion, pincode is validated against `pincodes` collection
- Latitude/longitude fetched and stored in `profile.latitude`, `profile.longitude`

## Seller Permissions Matrix

| Role | GST Status | Create Draft | Publish |
|------|------------|--------------|---------|
| Buyer | N/A | No | No |
| Seller | Pending | Yes | No |
| Seller | Verified | Yes | Yes |

## API Endpoints

### Auth
- `POST /api/auth/complete-profile` - Complete registration after email verification

### Seller
- `GET /api/seller/status` - Get seller GST/permission status
- `POST /api/seller/listings` - Create listing (draft)
- `POST /api/seller/listings/{id}/publish` - Publish listing (requires verified GST)

---

## Implementation Status

### Completed (Feb 22, 2026)
- [x] TypeScript build error fixed - `UserProfile` type with `roles` array
- [x] 3-step registration flow (Sign Up → Verify Email → Complete Profile)
- [x] Role selection (Buyer/Seller) on complete-profile page
- [x] GST field shown only for sellers
- [x] GST pending banner on seller dashboard
- [x] Protected route redirects
- [x] Pincode-to-geolocation lookup implemented
- [x] Seller permission checks on product publishing

### Testing Results
- Backend: 100% (11/11 tests passed)
- Frontend: 100% (all pages load correctly)
- Firebase Auth: NOT CONFIGURED (manual testing required)

---

## Next Steps / Backlog

### P1 - High Priority
1. Configure Firebase Admin SDK for full authentication testing
2. End-to-end test with real Firebase users
3. Admin GST verification workflow

### P2 - Medium Priority
1. Enhanced seller analytics
2. Product image upload improvements
3. Inquiry notification system

### P3 - Low Priority
1. Multi-language support
2. Advanced search filters
3. Seller performance metrics
