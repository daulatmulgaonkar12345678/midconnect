/**
 * Shared SSR renderer for city & intent+city product pages.
 * Used by:
 *   /products/[slug]/in/[city]/page.tsx
 *   /products/[slug]/[intent]/in/[city]/page.tsx
 */

import { SITE_URL, toRelativeUrl } from './siteUrl';

const API = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || '';

export async function fetchCityData(slug: string, city: string, intent?: string) {
  try {
    const q = intent ? `?intent=${encodeURIComponent(intent)}` : '';
    const res = await fetch(`${API}/api/products/${slug}/city/${city}${q}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

const INTENT_H1: Record<string, string> = {
  price: 'Price of',
  buy: 'Buy',
  suppliers: 'Top',
  wholesale: 'Wholesale',
  cheap: 'Cheap',
};

interface CityPageSeller {
  companyName?: string;
  businessName?: string;
  city?: string;
  price?: number | string;
  unit?: string;
  listingId?: string;
}

// Minimal typed shape of the backend city-page SEO payload.
interface CityPagePayload {
  product?: { name?: string };
  city?: { name?: string; slug?: string };
  sellers?: CityPageSeller[];
  stats?: { sellerCount?: number; minPrice?: number | string };
  seo?: {
    seoContent?: string;
    templateType?: string;
    jsonLd?: Record<string, unknown>;
    breadcrumbJsonLd?: Record<string, unknown>;
    faqJsonLd?: Record<string, unknown>;
  };
  internalLinks?: {
    mainProductPage?: string;
    categoryPage?: string | null;
    relatedIntents?: Array<{ intent: string; url: string }>;
    otherCities?: Array<{ city: string; slug: string; url: string }>;
  };
  localSignals?: { industrialZones?: string[]; nearbyCities?: string[] };
}

interface CityPageFaqEntry {
  name?: string;
  acceptedAnswer?: { text?: string };
}

/** Visible FAQ items extracted from the backend FAQPage JSON-LD, so the
 * rendered questions/answers always match the structured data exactly. */
function extractCityFaqItems(faqJsonLd: unknown): Array<{ q: string; a: string }> {
  const mainEntity = (faqJsonLd as { mainEntity?: CityPageFaqEntry[] } | null | undefined)?.mainEntity;
  if (!Array.isArray(mainEntity)) return [];
  return mainEntity
    .map((qa) => ({ q: (qa?.name || '').trim(), a: (qa?.acceptedAnswer?.text || '').trim() }))
    .filter((qa) => qa.q && qa.a);
}

export function renderCityPage(
  data: CityPagePayload,
  slug: string,
  city: string,
  intent?: string,
) {
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
  const relatedIntents: Array<{ intent: string; url: string }> = data.internalLinks?.relatedIntents || [];
  const otherCities: Array<{ city: string; slug: string; url: string }> = data.internalLinks?.otherCities || [];
  const industrialZones: string[] = data.localSignals?.industrialZones || [];
  const nearbyCities: string[] = data.localSignals?.nearbyCities || [];
  const templateType = data.seo?.templateType;
  const faqItems = extractCityFaqItems(data.seo?.faqJsonLd);
  const sellerCount = data.stats?.sellerCount ?? 0;

  const productJsonLd = data.seo?.jsonLd;
  const breadcrumbJsonLd = data.seo?.breadcrumbJsonLd;
  const faqJsonLd = data.seo?.faqJsonLd;
  const organizationJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'UdyogConnect',
    url: SITE_URL,
    logo: `${SITE_URL}/logo.png`,
    description: "India's trusted B2B marketplace for industrial products.",
  };

  return (
    <>
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

      <main className="max-w-5xl mx-auto px-4 py-8" data-testid="city-product-page" data-template={templateType}>
        <nav className="text-sm text-gray-500 mb-6" data-testid="city-breadcrumb">
          <a href="/" className="hover:text-blue-600">Home</a>
          <span className="mx-2">/</span>
          <a href="/products" className="hover:text-blue-600">Products</a>
          <span className="mx-2">/</span>
          <a href={mainProductUrl} className="hover:text-blue-600">{productName}</a>
          <span className="mx-2">/</span>
          {intent ? (
            <>
              <a href={`/products/${slug}/in/${data.city?.slug || city}`} className="hover:text-blue-600">{cityName}</a>
              <span className="mx-2">/</span>
              <span className="text-gray-900 font-medium capitalize">{intent}</span>
            </>
          ) : (
            <span className="text-gray-900 font-medium">{cityName}</span>
          )}
        </nav>

        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" data-testid="city-h1">
          {intent
            ? `${INTENT_H1[intent] || intent} ${productName} in ${cityName}`
            : `${productName} Suppliers in ${cityName}`}
        </h1>

        <div className="flex flex-wrap gap-4 mb-8 text-sm" data-testid="city-stats">
          {/* B4: never publish a "0 Verified Suppliers" claim — chip only when
              the backend reports real eligible sellers. */}
          {sellerCount > 0 && (
            <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full font-medium">
              {sellerCount} Verified Supplier{sellerCount === 1 ? '' : 's'}
            </span>
          )}
          {data.stats?.minPrice && (
            <span className="bg-green-50 text-green-700 px-3 py-1 rounded-full font-medium">
              Starting from ₹{Number(data.stats.minPrice).toLocaleString('en-IN')}
            </span>
          )}
        </div>

        {sellers.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Top {productName} Suppliers in {cityName}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sellers.map((seller: CityPageSeller, i: number) => (
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

        {/* Visible FAQ — kept in lockstep with faqJsonLd so the FAQPage
            structured data only marks up content shown on the page. */}
        {faqItems.length > 0 && (
          <section className="mb-10 border-t pt-6" data-testid="city-faq">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              {productName} in {cityName} — Frequently Asked Questions
            </h2>
            {faqItems.map((qa, i) => (
              <div key={i} className="mb-4">
                <h3 className="font-medium text-gray-900">{qa.q}</h3>
                <p className="text-sm text-gray-600 mt-1">{qa.a}</p>
              </div>
            ))}
          </section>
        )}

        {seoContent && (
          <article
            className="prose prose-gray max-w-none mb-10"
            data-testid="city-seo-content"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(seoContent) }}
          />
        )}

        {relatedIntents.length > 0 && (
          <nav className="border-t pt-6 mt-8" data-testid="city-related-intents">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Related Searches in {cityName}</h2>
            <div className="flex flex-wrap gap-2">
              {relatedIntents.map((ri) => (
                <a
                  key={ri.intent}
                  href={toRelativeUrl(ri.url)}
                  className="inline-flex items-center px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm hover:bg-blue-100 capitalize"
                  data-testid={`related-intent-${ri.intent}`}
                >
                  {ri.intent} {productName} in {cityName}
                </a>
              ))}
            </div>
          </nav>
        )}

        {/* Local Signals (industrial zones + nearby cities) — boosts local SEO */}
        {(industrialZones.length > 0 || nearbyCities.length > 0) && (
          <section className="border-t pt-6 mt-8" data-testid="city-local-signals">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">
              {productName} in {cityName} — Local Areas
            </h2>
            {industrialZones.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-600 mb-2">Top industrial zones in {cityName}</h3>
                <ul className="flex flex-wrap gap-2">
                  {industrialZones.map((z) => (
                    <li key={z} className="inline-block px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                      {z}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {nearbyCities.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-600 mb-2">Nearby cities also served</h3>
                <p className="text-sm text-gray-600">{nearbyCities.join(', ')}</p>
              </div>
            )}
          </section>
        )}

        {/* Other Cities — inter-city internal linking (high-value SEO) */}
        {otherCities.length > 0 && (
          <nav className="border-t pt-6 mt-8" data-testid="city-other-cities">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">{productName} in Other Cities</h2>
            <ul className="flex flex-wrap gap-2 list-none">
              {otherCities.map((c) => (
                <li key={c.slug}>
                  <a
                    href={toRelativeUrl(c.url)}
                    className="inline-flex items-center px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm hover:bg-blue-100"
                    data-testid={`other-city-${c.slug}`}
                  >
                    {productName} in {c.city}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

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
