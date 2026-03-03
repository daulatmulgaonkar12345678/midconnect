import { redirect } from 'next/navigation';

const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '';

interface Props {
  params: Promise<{ id: string }>;
}

/**
 * SEO v2.1 - Permanent 301 redirect from old route to new route
 * 
 * Old: /category/{id}
 * New: /categories/{slug}
 * 
 * This preserves SEO authority by redirecting all old URLs.
 */
export default async function CategoryRedirectPage({ params }: Props) {
  const { id } = await params;
  
  // Try to get the category from enterprise resolver first
  try {
    const response = await fetch(`${API_URL}/api/enterprise/resolve/category/${id}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      const data = await response.json();
      
      if (data.category?.slug) {
        redirect(`/categories/${data.category.slug}`);
      }
    }
  } catch (error) {
    console.error('Resolver lookup failed:', error);
  }
  
  // Fallback: Try the redirect API
  try {
    const response = await fetch(`${API_URL}/api/redirect/category/${id}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000)
    });
    const data = await response.json();
    
    if (data.redirect && data.slug) {
      redirect(`/categories/${data.slug}`);
    }
  } catch (error) {
    console.error('Redirect lookup failed:', error);
  }
  
  // Final fallback: redirect to categories list with the ID (new page will handle it)
  redirect(`/categories/${id}`);
}
