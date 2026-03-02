import { Metadata } from 'next';
import { redirect } from 'next/navigation';

/**
 * SEO v2.1 - Server-side 301 redirect
 * Redirects /product/{slug} -> /products/{slug}
 */
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  
  // Return minimal metadata - redirect happens immediately
  return {
    title: 'Redirecting...',
    robots: {
      index: false,
      follow: true,
    }
  };
}

export default async function ProductLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  
  // Server-side permanent redirect to /products/[slug]
  redirect(`/products/${slug}`);
}
