import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: [
          '/',
          '/products',
          '/product/',
          '/categories',
          '/category/',
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
        ],
      },
    ],
    sitemap: 'https://www.udyogconnect.in/sitemap.xml',
  };
}
