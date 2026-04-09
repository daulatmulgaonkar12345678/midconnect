# Test Credentials

## Dev Mode (Preview Environment)
- **Auth Header**: `Authorization: Bearer dev-test-token`
- **Notes**: Firebase is not configured in preview. Backend uses dev mode which bypasses Firebase auth and simulates a Super Admin identity when `dev-test-token` is used.

## Firebase Auth (Production)
- Firebase Auth is used for production authentication (email/password)
- Admin users have `roles: ["admin"]` in the users collection
