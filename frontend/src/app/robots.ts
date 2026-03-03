import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: [
          '/',
          '/products',
          '/products/',
          '/categories',
          '/categories/',
          '/about',
          '/contact',
          '/pricing',
        ],
        disallow: [
          '/api/',
          '/admin/',
          '/seller/',
          '/dashboard/',
          '/login',
          '/register',
          '/verify-email',
          '/inquiries',
          '/cart/',
          '/product/',   // Old format - redirect to /products/
          '/category/',  // Old format - redirect to /categories/
        ],
      },
    ],
    sitemap: 'https://www.udyogconnect.in/sitemap.xml',
  };
}
