'use client';

import { useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface ProductSEOData {
  productName: string;
  seoTitle: string;
  seoDescription: string;
  seoContent: string;
  jsonLd: Record<string, unknown>;
  breadcrumbJsonLd: Record<string, unknown>;
  sellerCount: number;
  sellersByCity: Record<string, Array<{
    companyName: string;
    state: string;
    lowestPrice: number | null;
    badgeType: string;
  }>>;
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

export function CitySellerGroup({ sellersByCity }: CitySellerGroupProps) {
  if (!sellersByCity || Object.keys(sellersByCity).length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Suppliers by City
      </h3>
      <div className="space-y-3">
        {Object.entries(sellersByCity).map(([city, sellers]) => (
          <div key={city} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <div className="flex items-center gap-2">
              <span className="text-gray-900 font-medium">{city}</span>
              <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                {sellers.length} {sellers.length === 1 ? 'Seller' : 'Sellers'}
              </span>
            </div>
            {sellers.some(s => s.lowestPrice) && (
              <span className="text-sm text-green-600">
                From ₹{Math.min(...sellers.filter(s => s.lowestPrice).map(s => s.lowestPrice!)).toLocaleString()}
              </span>
            )}
          </div>
        ))}
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

  // Convert markdown-like content to HTML
  const formatContent = (content: string) => {
    return content
      .replace(/## (.*)/g, '<h2 class="text-xl font-semibold text-gray-900 mt-6 mb-3">$1</h2>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/- (.*)/g, '<li class="ml-4">$1</li>')
      .replace(/\n\n/g, '</p><p class="text-gray-600 mb-3">')
      .replace(/^\d+\. (.*)/gm, '<li class="ml-4 list-decimal">$1</li>');
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-8">
      <details className="group">
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
          className="mt-4 prose prose-sm max-w-none text-gray-600"
          dangerouslySetInnerHTML={{ __html: formatContent(seoContent) }}
        />
      </details>
    </div>
  );
}
