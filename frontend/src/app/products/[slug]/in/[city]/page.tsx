import type { Metadata } from 'next';

const API = process.env.REACT_APP_BACKEND_URL || '';

interface CityPageProps {
  params: Promise<{ slug: string; city: string }>;
}

async function fetchCityData(slug: string, city: string) {
  try {
    const res = await fetch(`${API}/api/products/${slug}/city/${city}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: CityPageProps): Promise<Metadata> {
  const { slug, city } = await params;
  const data = await fetchCityData(slug, city);
  if (!data) return { title: 'Product Not Found | UdyogConnect', robots: { index: false, follow: false } };
  return {
    title: data.seo?.title || `${data.product?.name} in ${city} | UdyogConnect`,
    description: data.seo?.description,
    alternates: { canonical: data.seo?.cityPageUrl },
    openGraph: {
      title: data.seo?.title,
      description: data.seo?.description,
      url: data.seo?.cityPageUrl,
      siteName: 'UdyogConnect',
      type: 'website',
      locale: 'en_IN',
    },
    robots: { index: true, follow: true },
  };
}

export default async function CityProductPage({ params }: CityPageProps) {
  const { slug, city } = await params;
  const data = await fetchCityData(slug, city);

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="city-not-found">
        <p className="text-gray-500 text-lg">Product not found in this city.</p>
      </div>
    );
  }

  const productName = data.product?.name || slug;
  const cityName = data.city?.name || city;
  const sellers = data.sellers || [];
  const seoContent = data.seo?.seoContent || '';
  const mainProductUrl = data.internalLinks?.mainProductPage || `/products/${slug}`;
  const categoryUrl = data.internalLinks?.categoryPage;

  // SSR JSON-LD schemas (from backend) — fallback gracefully if missing
  const productJsonLd = data.seo?.jsonLd;
  const breadcrumbJsonLd = data.seo?.breadcrumbJsonLd;
  const faqJsonLd = data.seo?.faqJsonLd;
  const organizationJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'UdyogConnect',
    url: 'https://www.udyogconnect.in',
    logo: 'https://www.udyogconnect.in/logo.png',
    description: "India's trusted B2B marketplace for industrial products.",
  };

  return (
    <>
      {/* ==================== SSR JSON-LD ==================== */}
      {productJsonLd && (
        <script
          type="application/ld+json"
          data-testid="city-product-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd) }}
        />
      )}
      {breadcrumbJsonLd && (
        <script
          type="application/ld+json"
          data-testid="city-breadcrumb-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />
      )}
      {faqJsonLd && (
        <script
          type="application/ld+json"
          data-testid="city-faq-jsonld"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
        />
      )}
      <script
        type="application/ld+json"
        data-testid="city-org-jsonld"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
      />

      <main className="max-w-5xl mx-auto px-4 py-8" data-testid="city-product-page">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500 mb-6" data-testid="city-breadcrumb">
          <a href="/" className="hover:text-blue-600">Home</a>
          <span className="mx-2">/</span>
          <a href="/products" className="hover:text-blue-600">Products</a>
          <span className="mx-2">/</span>
          <a href={mainProductUrl} className="hover:text-blue-600">{productName}</a>
          <span className="mx-2">/</span>
          <span className="text-gray-900 font-medium">{cityName}</span>
        </nav>

        {/* H1 */}
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" data-testid="city-h1">
          {productName} Suppliers in {cityName}
        </h1>

        {/* Stats */}
        <div className="flex flex-wrap gap-4 mb-8 text-sm" data-testid="city-stats">
          <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium">
            {data.stats?.sellerCount || 0} Verified Suppliers
          </span>
          {data.stats?.minPrice && (
            <span className="bg-green-50 text-green-700 px-3 py-1 rounded-full font-medium">
              Starting from ₹{Number(data.stats.minPrice).toLocaleString('en-IN')}
            </span>
          )}
        </div>

        {/* Sellers Grid */}
        {sellers.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Top {productName} Suppliers in {cityName}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sellers.map((seller: any, i: number) => (
                <div key={i} className="border rounded-lg p-4 hover:shadow-md transition bg-white" data-testid={`city-seller-${i}`}>
                  <h3 className="font-semibold text-gray-900">{seller.companyName || seller.businessName || 'Verified Supplier'}</h3>
                  <p className="text-sm text-gray-500 mt-1">{seller.city || cityName}</p>
                  {seller.price && (
                    <p className="text-sm font-medium text-green-700 mt-2">
                      ₹{Number(seller.price).toLocaleString('en-IN')} {seller.unit ? `/ ${seller.unit}` : ''}
                    </p>
                  )}
                  {seller.listingId && (
                    <a
                      href={`/products/${slug}/seller/${seller.listingId}`}
                      className="inline-block mt-3 text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View Details &rarr;
                    </a>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SEO Content (rendered as HTML from markdown) */}
        {seoContent && (
          <article
            className="prose prose-gray max-w-none mb-10"
            data-testid="city-seo-content"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(seoContent) }}
          />
        )}

        {/* Internal Links */}
        <nav className="border-t pt-6 mt-8" data-testid="city-internal-links">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Related Pages</h2>
          <div className="flex flex-wrap gap-3">
            <a href={mainProductUrl} className="text-blue-600 hover:text-blue-800 underline text-sm">
              View all {productName} suppliers in India
            </a>
            {categoryUrl && (
              <a href={categoryUrl} className="text-blue-600 hover:text-blue-800 underline text-sm">
                Browse more products in this category
              </a>
            )}
          </div>
        </nav>
      </main>
    </>
  );
}

/** Simple markdown to HTML (headings, bold, lists, paragraphs) */
function markdownToHtml(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hulo])/gm, '<p>')
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<[hulo])/g, '$1')
    .replace(/(<\/[hulo][^>]*>)<\/p>/g, '$1');
}
