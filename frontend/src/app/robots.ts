import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/admin/',
          '/seller/',
          '/dashboard/',
          '/login',
          '/register',
          '/verify-email',
          '/cart/',
        ],
      },
    ],
    sitemap: 'https://www.udyogconnect.in/sitemap.xml',
  };
}
