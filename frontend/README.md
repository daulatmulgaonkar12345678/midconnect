# MidConnect Website (Next.js)

B2B Marketplace website with SEO-optimized public pages and admin panel.

## Architecture

```
frontend-web/
├── src/
│   ├── app/                # Next.js App Router
│   │   ├── (main)/        # Public pages
│   │   ├── admin/         # Admin panel
│   │   └── layout.tsx     # Root layout
│   ├── components/        # React components
│   ├── context/           # Auth context
│   └── lib/
│       ├── firebase.ts    # Firebase (Web SDK)
│       └── api.ts         # API client
├── public/                # Static assets
├── .env.local            # Environment variables
└── package.json
```

## Key Differences from Mobile

| Feature | Web | Mobile |
|---------|-----|--------|
| Firebase SDK | `firebase/auth` | `firebase/auth/react-native` |
| Persistence | Browser (auto) | AsyncStorage |
| Routing | Next.js App Router | Expo Router |
| Styling | Tailwind CSS | StyleSheet.create() |
| SEO | Full SSR/SSG | N/A |

## Setup

```bash
# Install dependencies
yarn install

# Start development server
yarn dev

# Build for production
yarn build

# Start production server
yarn start
```

## Environment Variables

Create `.env.local`:

```env
# Backend API
NEXT_PUBLIC_API_URL=https://midconnect.onrender.com/api

# Firebase
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123
```

## Firebase Configuration

Firebase is configured in `src/lib/firebase.ts` using standard web SDK:

```typescript
import { getAuth } from 'firebase/auth';

// Browser persistence is automatic
export const auth = getAuth(app);
```

## API Calls

```typescript
import { getCategories, fetchWithAuth } from '@/lib/api';

// Public endpoints
const categories = await getCategories();

// Authenticated endpoints  
const profile = await fetchWithAuth('/users/me', token);
```

## Deployment (Vercel)

```bash
# Deploy to Vercel
vercel

# Set environment variables in Vercel dashboard
```

Required environment variables on Vercel:
- `NEXT_PUBLIC_API_URL`
- All `NEXT_PUBLIC_FIREBASE_*` variables

## No Mobile Code

This project is **web-only**. It does NOT:
- Use React Native components
- Use Expo packages
- Include any mobile-specific dependencies

For mobile, use the separate `frontend-mobile` project.

## Pages

### Public Pages
- `/` - Home page
- `/products` - Product listings
- `/search` - Product search

### Admin Panel
- `/admin` - Dashboard
- `/admin/categories` - Category management
- `/admin/products` - Product management
- `/admin/users` - User management
