'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronRight, MapPin, Star, Shield } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface InternalLink {
  name: string;
  url: string;
}

interface ProductSEOData {
  productName: string;
  seoTitle: string;
  seoDescription: string;
  seoContent: string;
  jsonLd: Record<string, unknown>;
  breadcrumbJsonLd: Record<string, unknown>;
  faqJsonLd: Record<string, unknown>;
  internalLinks: {
    category: InternalLink | null;
    similarProducts: InternalLink[];
    cityPages: InternalLink[];
    topRated: string;
  };
  sellerCount: number;
  sellersByCity: Record<string, Array<{
    companyName: string;
    state: string;
    lowestPrice: number | null;
    badgeType: string;
  }>>;
  minPrice: number | null;
  maxPrice: number | null;
  minMoq: number | null;
  availableCities: string[];
  canonicalUrl: string;
}

interface ProductJsonLdProps {
  slug: string;
}

export function ProductJsonLd({ slug }: ProductJsonLdProps) {
  const [seoData, setSeoData] = useState<ProductSEOData | null>(null);

  useEffect(() => {
    async function fetchSeoData() {
      try {
        const response = await fetch(`${API_URL}/api/products/${slug}/seo`);
        if (response.ok) {
          const data = await response.json();
          setSeoData(data);
        }
      } catch (error) {
        console.error('Error fetching SEO data:', error);
      }
    }
    
    if (slug) {
      fetchSeoData();
    }
  }, [slug]);

  if (!seoData) return null;

  // Organization schema (static)
  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "UdyogConnect",
    "url": "https://www.udyogconnect.in",
    "logo": "https://www.udyogconnect.in/logo.png",
    "description": "India's trusted B2B marketplace for industrial products",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "Pune",
      "addressRegion": "Maharashtra",
      "addressCountry": "IN"
    },
    "contactPoint": {
      "@type": "ContactPoint",
      "telephone": "+91-7387821042",
      "contactType": "customer service"
    }
  };

  return (
    <>
      {/* Product Schema with AggregateOffer */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.jsonLd) }}
      />
      
      {/* Breadcrumb Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.breadcrumbJsonLd) }}
      />
      
      {/* FAQ Schema for Rich Snippets */}
      {seoData.faqJsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(seoData.faqJsonLd) }}
        />
      )}
      
      {/* Organization Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
    </>
  );
}

interface CitySellerGroupProps {
  sellersByCity: Record<string, Array<{
    companyName: string;
    state: string;
    lowestPrice: number | null;
    badgeType: string;
  }>>;
}

// Badge component for sellers
function SellerBadge({ badgeType }: { badgeType: string }) {
  if (!badgeType || badgeType === 'none') return null;
  
  if (badgeType === 'choice') {
    return (
      <span className="inline-flex items-center gap-0.5 text-yellow-600">
        <Star className="h-3 w-3 fill-yellow-500" />
      </span>
    );
  }
  
  if (badgeType === 'trusted') {
    return (
      <span className="inline-flex items-center gap-0.5 text-green-600">
        <Shield className="h-3 w-3 fill-green-500" />
      </span>
    );
  }
  
  return null;
}

export function CitySellerGroup({ sellersByCity }: CitySellerGroupProps) {
  if (!sellersByCity || Object.keys(sellersByCity).length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Suppliers by City
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(sellersByCity).map(([city, sellers]) => (
          <div 
            key={city} 
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-gray-400" />
              <div>
                <span className="text-gray-900 font-medium">{city}</span>
                <span className="ml-2 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                  {sellers.length} {sellers.length === 1 ? 'Seller' : 'Sellers'}
                </span>
              </div>
            </div>
            {sellers.some(s => s.lowestPrice) && (
              <span className="text-sm text-green-600 font-medium">
                From ₹{Math.min(...sellers.filter(s => s.lowestPrice).map(s => s.lowestPrice!)).toLocaleString()}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface InternalLinksProps {
  internalLinks: {
    category: InternalLink | null;
    similarProducts: InternalLink[];
    cityPages: InternalLink[];
    intentCityPages?: Array<{ name: string; intent: string; url: string }>;
    topRated: string;
  };
  productName: string;
  productSlug?: string;
}

// Top cities for the "Related Searches" internal-links block. Kept inline to
// avoid new files; matches backend top-cities policy.
const RELATED_CITIES = ['Pune', 'Mumbai', 'Delhi', 'Ahmedabad', 'Bangalore'];
const RELATED_INTENTS: Array<{ key: string; label: string }> = [
  { key: 'price', label: 'Price' },
  { key: 'suppliers', label: 'Suppliers' },
  { key: 'buy', label: 'Buy' },
  { key: 'wholesale', label: 'Wholesale' },
  { key: 'cheap', label: 'Cheap' },
];

export function InternalLinksSection({ internalLinks, productName, productSlug }: InternalLinksProps) {
  if (!internalLinks) return null;

  const hasSimilarProducts = internalLinks.similarProducts && internalLinks.similarProducts.length > 0;
  const hasCityPages = internalLinks.cityPages && internalLinks.cityPages.length > 0;
  const hasIntentCityPages = (internalLinks.intentCityPages || []).length > 0;

  if (!hasSimilarProducts && !hasCityPages && !hasIntentCityPages && !internalLinks.category) {
    return null;
  }

  // Build "Related Searches" links. Prefer backend-provided intentCityPages (real
  // seller-backed combos) and fall back to a generated set so NEW products without
  // sellers still get crawlable internal links on day 1.
  type RelatedLink = { href: string; label: string; key: string };
  let relatedSearches: RelatedLink[] = [];

  if (hasIntentCityPages) {
    relatedSearches = internalLinks.intentCityPages!.slice(0, 15).map((l) => ({
      href: l.url.replace('https://www.udyogconnect.in', ''),
      label: l.name,
      key: `${l.intent}-${l.url}`,
    }));
  } else if (productSlug) {
    // Fallback: 5 cities × 3 key intents = 15 crawlable related links
    const cities = RELATED_CITIES.slice(0, 5);
    const intents = RELATED_INTENTS.slice(0, 3);
    for (const city of cities) {
      const citySlug = city.toLowerCase();
      // Plain city link
      relatedSearches.push({
        href: `/products/${productSlug}/in/${citySlug}`,
        label: `${productName} in ${city}`,
        key: `city-${citySlug}`,
      });
      // Intent+city links
      for (const intent of intents) {
        relatedSearches.push({
          href: `/products/${productSlug}/${intent.key}/in/${citySlug}`,
          label: `${productName} ${intent.label} in ${city}`,
          key: `intent-${intent.key}-${citySlug}`,
        });
      }
    }
  }

  // Dedupe by href to guarantee no duplicate anchors
  const seen = new Set<string>();
  relatedSearches = relatedSearches.filter((l) => {
    if (seen.has(l.href)) return false;
    seen.add(l.href);
    return true;
  });

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Related Products & Categories
      </h3>
      
      <div className="space-y-4">
        {/* Category Link */}
        {internalLinks.category && (
          <div>
            <h4 className="text-sm font-medium text-gray-600 mb-2">Browse Category</h4>
            <Link 
              href={internalLinks.category.url.replace('https://www.udyogconnect.in', '')}
              className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm"
            >
              <ChevronRight className="h-4 w-4" />
              {internalLinks.category.name}
            </Link>
          </div>
        )}
        
        {/* Similar Products */}
        {hasSimilarProducts && (
          <div>
            <h4 className="text-sm font-medium text-gray-600 mb-2">Similar Products</h4>
            <div className="flex flex-wrap gap-2">
              {internalLinks.similarProducts.map((product, idx) => (
                <Link
                  key={idx}
                  href={product.url.replace('https://www.udyogconnect.in', '')}
                  className="inline-flex items-center px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors"
                >
                  {product.name}
                </Link>
              ))}
            </div>
          </div>
        )}
        
        {/* City Pages */}
        {hasCityPages && (
          <div>
            <h4 className="text-sm font-medium text-gray-600 mb-2">{productName} by Location</h4>
            <div className="flex flex-wrap gap-2">
              {internalLinks.cityPages.map((city, idx) => (
                <Link
                  key={idx}
                  href={city.url.replace('https://www.udyogconnect.in', '')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <MapPin className="h-3 w-3" />
                  {city.name.replace(productName + ' in ', '')}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Related Searches — programmatic SEO internal linking (crawlable anchors) */}
        {relatedSearches.length > 0 && (
          <div data-testid="related-searches">
            <h3 className="text-sm font-medium text-gray-600 mb-2">Related Searches</h3>
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2 list-none">
              {relatedSearches.map((l) => (
                <li key={l.key}>
                  <a
                    href={l.href}
                    className="text-blue-600 hover:text-blue-800 hover:underline text-sm"
                    data-testid={`related-search-${l.key}`}
                  >
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

interface SEOContentSectionProps {
  seoContent: string;
  productName: string;
}

export function SEOContentSection({ seoContent, productName }: SEOContentSectionProps) {
  if (!seoContent) return null;

  // Convert markdown-like content to HTML with proper structure
  const formatContent = (content: string) => {
    return content
      // H1 heading
      .replace(/^# (.*)/gm, '<h1 class="text-2xl font-bold text-gray-900 mb-4">$1</h1>')
      // H2 headings
      .replace(/^## (.*)/gm, '<h2 class="text-xl font-semibold text-gray-900 mt-8 mb-3">$1</h2>')
      // H3 headings
      .replace(/^### (.*)/gm, '<h3 class="text-lg font-medium text-gray-800 mt-6 mb-2">$1</h3>')
      // Bold text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
      // Numbered lists
      .replace(/^(\d+)\. (.*)/gm, '<li class="ml-6 list-decimal text-gray-600 mb-1">$2</li>')
      // Bullet lists
      .replace(/^- (.*)/gm, '<li class="ml-6 list-disc text-gray-600 mb-1">$1</li>')
      // Paragraphs - wrap non-heading, non-list content
      .replace(/^(?!<h|<li)(.+)$/gm, '<p class="text-gray-600 mb-3 leading-relaxed">$1</p>')
      // Clean up empty paragraphs
      .replace(/<p class="text-gray-600 mb-3 leading-relaxed"><\/p>/g, '');
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-8">
      <details className="group" open>
        <summary className="flex items-center justify-between cursor-pointer list-none">
          <h2 className="text-lg font-semibold text-gray-900">
            About {productName}
          </h2>
          <span className="text-gray-500 group-open:rotate-180 transition-transform">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </span>
        </summary>
        <div 
          className="mt-6 prose prose-slate max-w-none"
          dangerouslySetInnerHTML={{ __html: formatContent(seoContent) }}
        />
      </details>
    </div>
  );
}

interface ProductMetaSummaryProps {
  sellerCount: number;
  minPrice: number | null;
  maxPrice: number | null;
  minMoq: number | null;
  availableCities: string[];
}

export function ProductMetaSummary({ 
  sellerCount, 
  minPrice, 
  maxPrice, 
  minMoq,
  availableCities 
}: ProductMetaSummaryProps) {
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      {sellerCount > 0 && (
        <span className="inline-flex items-center px-3 py-1 bg-blue-50 text-blue-700 rounded-full">
          {sellerCount} {sellerCount === 1 ? 'Supplier' : 'Suppliers'}
        </span>
      )}
      
      {minPrice && maxPrice && minPrice !== maxPrice && (
        <span className="inline-flex items-center px-3 py-1 bg-green-50 text-green-700 rounded-full">
          ₹{minPrice.toLocaleString()} - ₹{maxPrice.toLocaleString()}
        </span>
      )}
      
      {minPrice && (!maxPrice || minPrice === maxPrice) && (
        <span className="inline-flex items-center px-3 py-1 bg-green-50 text-green-700 rounded-full">
          From ₹{minPrice.toLocaleString()}
        </span>
      )}
      
      {minMoq && minMoq > 1 && (
        <span className="inline-flex items-center px-3 py-1 bg-amber-50 text-amber-700 rounded-full">
          MOQ: {minMoq} units
        </span>
      )}
      
      {availableCities && availableCities.length > 0 && (
        <span className="inline-flex items-center px-3 py-1 bg-purple-50 text-purple-700 rounded-full">
          {availableCities.length} Cities
        </span>
      )}
    </div>
  );
}
