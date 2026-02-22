# MidConnect B2B Marketplace - PRD

## Problem Statement
Implement role-based registration with Firebase + MongoDB. Roles system:
- Default → ["buyer"]
- Seller → ["buyer","seller"]
- Admin → ["buyer","admin"]

Seller state derived from:
- roles.includes("seller")
- gst.verified === true

## Fix Applied (Feb 22, 2026)
Fixed TypeScript build error: `Property 'roles' does not exist on type 'UserProfile'`

### Updated Files:
1. `/app/frontend/src/types/index.ts` - Added `roles: string[]` to UserProfile
2. `/app/frontend/src/context/AuthContext.tsx` - Updated roles-based logic:
   ```typescript
   const roles = state.profile?.roles ?? [];
   const isSeller = roles.includes('seller');
   const isAdmin = roles.includes('admin');
   const isGstVerified = state.profile?.gst?.verified === true;
   ```

### UserProfile Type Now Matches MongoDB:
```typescript
interface UserProfile {
  email: string;
  firebaseUid: string;
  roles: string[];  // Added this field
  isAdmin?: boolean;
  profile: { businessName, phone, city, state, pincode, address, latitude, longitude };
  gst?: { number, status, verified };
  emailVerified: boolean;
  accountStatus: string;
  canLogin: boolean;
  isActive: boolean;
  subscription?: any;
  favourites?: string[];
  recentSearches?: string[];
}
```

## Next Action Items
1. Configure Firebase Admin SDK credentials
2. Seed pincodes collection
3. Create admin panel for GST verification
