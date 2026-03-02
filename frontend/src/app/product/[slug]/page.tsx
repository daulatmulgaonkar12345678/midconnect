'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

/**
 * SEO v2.1 - Permanent 301 redirect from old route to new route
 * 
 * Old: /product/{slug or id}
 * New: /products/{slug}
 * 
 * This preserves SEO authority by redirecting all old URLs.
 */
export default function ProductRedirectPage() {
  const params = useParams();
  const router = useRouter();
  
  useEffect(() => {
    const slug = params?.slug;
    if (slug) {
      // Permanent redirect to /products/[slug]
      router.replace(`/products/${slug}`);
    }
  }, [params, router]);
  
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting...</p>
      </div>
    </div>
  );
}
