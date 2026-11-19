import { Metadata } from 'next';

import { canonicalSelfUrl, SITE_URL } from '@/lib/siteUrl';
import { fetchProductSeoPayload, type ProductSeoPayload } from '@/lib/productSeoServer';

// Batch 3 (2026-11-19): the /seo payload fetch moved to the shared
// server-only helper `fetchProductSeoPayload` (same URL, same
// `next: { revalidate: 3600 }` cache policy, null on failure) so the page
// shell can fetch the identical payload for the server-rendered hero without
// a second upstream call (request memoization dedupes within a render).

// Static Organization schema — SSR, single instance
const ORGANIZATION_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'UdyogConnect',
  url: SITE_URL,
  logo: `${SITE_URL}/logo.png`,
  description:
    "India's trusted B2B marketplace for industrial products. Connect with verified manufacturers, dealers, and distributors.",
  address: {
    '@type': 'PostalAddress',
    streetAddress: 'D2, Kedareshwar Park, Gujarwadi, Katraj',
    addressLocality: 'Pune',
    addressRegion: 'Maharashtra',
    postalCode: '411046',
    addressCountry: 'IN',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    telephone: '+91-7387821042',
    contactType: 'customer service',
    availableLanguage: ['English', 'Hindi'],
  },
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const seoData: ProductSeoPayload | null = await fetchProductSeoPayload(slug);
  if (!seoData || !seoData.seoTitle) return getDefaultMetadata();
  // Batch 2: re-anchor the payload's absolute canonical URL on the approved
  // apex origin. A cached payload fetched before the backend switched from
  // www to apex can still carry the www host (no origin-aware invalidation on
  // the fetch cache), so the emission point normalizes: canonical and og:url
  // are derived from the SAME normalized value and always agree.
  const canonicalUrl = canonicalSelfUrl(seoData.canonicalUrl, `/products/${slug}`);
  return {
    title: seoData.seoTitle,
    description: seoData.seoDescription,
    keywords: `${seoData.productName}, buy ${seoData.productName}, ${seoData.categoryName || 'industrial products'}, suppliers, manufacturers, India, UdyogConnect`,
    openGraph: {
      title: seoData.seoTitle,
      description: seoData.seoDescription,
      url: canonicalUrl,
      siteName: 'UdyogConnect',
      type: 'website',
      locale: 'en_IN',
    },
    twitter: {
      card: 'summary_large_image',
      title: seoData.seoTitle,
      description: seoData.seoDescription,
    },
    alternates: { canonical: canonicalUrl },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-snippet': -1,
        'max-image-preview': 'large',
        'max-video-preview': -1,
      },
    },
  };
}

function getDefaultMetadata(): Metadata {
  return {
    title: "Product | UdyogConnect - India's Industrial Marketplace",
    description:
      'Find verified suppliers of industrial products. Compare prices, MOQ and contact manufacturers directly on UdyogConnect.',
    robots: { index: true, follow: true },
  };
}

export default async function MainProductLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const seoData = await fetchProductSeoPayload(slug);

  return (
    <>
      {seoData?.jsonLd && (
        <script
          type="application/ld+json"
          data-testid="product-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.jsonLd) }}
        />
      )}
      {seoData?.breadcrumbJsonLd && (
        <script
          type="application/ld+json"
          data-testid="breadcrumb-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.breadcrumbJsonLd) }}
        />
      )}
      {seoData?.faqJsonLd && (
        <script
          type="application/ld+json"
          data-testid="faq-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.faqJsonLd) }}
        />
      )}
      <script
        type="application/ld+json"
        data-testid="org-jsonld"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ORGANIZATION_SCHEMA) }}
      />
      {children}
    </>
  );
}
