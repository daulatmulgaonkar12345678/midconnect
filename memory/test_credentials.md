# Test Credentials

## Dev Mode (Preview Environment)
- **Admin Token**: `Authorization: Bearer dev-test-token` — Simulates Super Admin (seller ID: 69a0ac1089b696c2337c5a6e)
- **Employee Token**: `Authorization: Bearer test-employee-uid` — Simulates employee linked to above seller
- **Notes**: Dev mode accepts any token as firebaseUid. `dev-test-token` maps to admin, any other token looks up user by firebaseUid.

## Firebase Auth (Production)
- Firebase Auth is used for production authentication (email/password)
- Admin users have `roles: ["admin"]` in the users collection
