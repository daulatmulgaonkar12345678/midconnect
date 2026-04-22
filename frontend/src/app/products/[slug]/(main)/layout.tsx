import { Metadata } from 'next';

const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '';

function isObjectId(str: string): boolean {
  return /^[a-f0-9]{24}$/i.test(str);
}

type SeoPayload = {
  productName?: string;
  seoTitle?: string;
  seoDescription?: string;
  canonicalUrl?: string;
  categoryName?: string;
  jsonLd?: Record<string, unknown>;
  breadcrumbJsonLd?: Record<string, unknown>;
  faqJsonLd?: Record<string, unknown>;
};

async function fetchSeo(slug: string): Promise<SeoPayload | null> {
  try {
    const response = await fetch(`${API_URL}/api/products/${slug}/seo`, {
      next: { revalidate: 3600 },
    });
    if (!response.ok) return null;
    return (await response.json()) as SeoPayload;
  } catch {
    return null;
  }
}

// Static Organization schema — SSR, single instance
const ORGANIZATION_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'UdyogConnect',
  url: 'https://www.udyogconnect.in',
  logo: 'https://www.udyogconnect.in/logo.png',
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
  if (isObjectId(slug)) return getDefaultMetadata();
  const seoData = await fetchSeo(slug);
  if (!seoData || !seoData.seoTitle) return getDefaultMetadata();
  return {
    title: seoData.seoTitle,
    description: seoData.seoDescription,
    keywords: `${seoData.productName}, buy ${seoData.productName}, ${seoData.categoryName || 'industrial products'}, suppliers, manufacturers, India, UdyogConnect`,
    openGraph: {
      title: seoData.seoTitle,
      description: seoData.seoDescription,
      url: seoData.canonicalUrl,
      siteName: 'UdyogConnect',
      type: 'website',
      locale: 'en_IN',
    },
    twitter: {
      card: 'summary_large_image',
      title: seoData.seoTitle,
      description: seoData.seoDescription,
    },
    alternates: { canonical: seoData.canonicalUrl },
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
  const seoData = isObjectId(slug) ? null : await fetchSeo(slug);

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
