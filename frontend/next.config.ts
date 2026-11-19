import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,
  
  // Optimize images from external sources.
  //
  // Batch 1 (2026-11-19): Vercel's image optimizer answers every uncached
  // /_next/image request with HTTP 402 (response header
  // X-Vercel-Error: OPTIMIZED_IMAGE_REQUEST_PAYMENT_REQUIRED — image
  // optimization quota/payment state on the Vercel account, external to this
  // repo). Cached variants still serve 200, so breakage is intermittent and
  // grows as new images/widths are requested. While the account is in this
  // state we bypass the optimizer entirely: next/image emits the original
  // source URLs as-is (Cloudinary URLs already carry f_auto,q_auto
  // transformations, so format/quality optimization is preserved at the
  // origin, and width/height attributes keep layout stable).
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'res.cloudinary.com',
      },
      {
        protocol: 'https',
        hostname: '**.firebasestorage.app',
      },
      {
        protocol: 'https',
        hostname: 'firebasestorage.googleapis.com',
      },
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: 'storage.googleapis.com',
      },
      {
        protocol: 'https',
        hostname: 'customer-assets.emergentagent.com',
      },
      {
        protocol: 'https',
        hostname: 'example.com',
      },
    ],
  },

  // API rewrites to proxy requests to the backend
  // This allows frontend to call /api/* without CORS issues
  async rewrites() {
    // For Vercel deployment, use the production backend URL
    // For local dev, use localhost
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.VITE_API_BASE_URL || 'http://localhost:8001';
    
    console.log('[Next.js Config] Using backend URL for rewrites:', backendUrl);
    
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },

  // Security headers for production
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Environment variable validation at build time
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
