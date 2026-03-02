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
  
  // Try to get the new slug from redirect API
  try {
    const response = await fetch(`${API_URL}/api/redirect/category/${id}`, {
      cache: 'no-store'
    });
    const data = await response.json();
    
    if (data.redirect && data.slug) {
      redirect(`/categories/${data.slug}`);
    }
  } catch (error) {
    console.error('Redirect lookup failed:', error);
  }
  
  // Fallback: redirect to categories list
  redirect('/categories');
}
