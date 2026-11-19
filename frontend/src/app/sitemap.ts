import { MetadataRoute } from 'next';

import { SITE_URL } from '@/lib/siteUrl';
const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'https://midconnect.onrender.com';

// Route-level ISR: re-evaluate the sitemap hourly (matches the per-fetch
// revalidate below). At revalidation time a failed fetch now throws — Next
// keeps serving the last-good sitemap and the error is logged; at build time
// a failed fetch fails the build loudly. Either way a degraded API can never
// silently produce a "successful" incomplete sitemap.
export const revalidate = 3600;

// Cap city pages to top N cities (programmatic scale). Full 20-city coverage
// per product. Backend endpoint generates all active products × TOP_CITIES.
const MAX_CITIES = 20;

// Programmatic intents emitted in the sitemap (subset of backend SUPPORTED_INTENTS).
// Only high-commercial-value intents are crawled to keep sitemap focused.
const SUPPORTED_INTENTS = ['price', 'suppliers'] as const;

// Google recommends ≤ 50 000 URLs per sitemap. We self-cap much lower for crawl efficiency.
const MAX_URLS = 45000;

// Simple slugify for categories/products that don't have a stored slug.
const slugify = (s: string): string =>
  (s || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');

interface Category {
  _id: string;
  name: string;
  slug?: string;
  updatedAt?: string;
}

interface SitemapCityPair {
  productSlug: string;
  citySlug: string;
  lastModified?: string | null;
  cityEligible?: boolean;
  priceEligible?: boolean;
  suppliersEligible?: boolean;
}

// Intent URL emitted only when the backend explicitly marks it eligible.
// A missing or non-true flag is never treated as eligible.
const INTENT_ELIGIBILITY_FIELD = {
  price: 'priceEligible',
  suppliers: 'suppliersEligible',
} as const;

// F3: fetch a sitemap data source and FAIL LOUDLY. A network error or a
// non-2xx response (the backend returns 503 when the DB is unavailable or
// eligibility overflows) must never silently degrade the sitemap to its
// static pages. The error is logged and rethrown so Next.js marks the
// sitemap route as errored instead of publishing an incomplete one.
async function fetchSitemapJson(url: string, label: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });
  } catch (error) {
    console.error(`[sitemap] ${label} fetch failed:`, error);
    throw new Error(
      `[sitemap] ${label} fetch failed — refusing to emit an incomplete sitemap`
    );
  }
  if (!response.ok) {
    console.error(`[sitemap] ${label} API responded ${response.status}`);
    throw new Error(
      `[sitemap] ${label} API responded ${response.status} — refusing to emit an incomplete sitemap`
    );
  }
  return response.json();
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Google Search Console flags full ISO timestamps; use YYYY-MM-DD only.
  const today = new Date().toISOString().split('T')[0];
  const toDateOnly = (iso?: string | null): string => {
    if (!iso) return today;
    return iso.split('T')[0] || today;
  };

  // Static pages - always included
  const staticPages: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: today, changeFrequency: 'daily', priority: 1.0 },
    { url: `${SITE_URL}/products`, lastModified: today, changeFrequency: 'daily', priority: 0.9 },
    { url: `${SITE_URL}/categories`, lastModified: today, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${SITE_URL}/about`, lastModified: today, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${SITE_URL}/contact`, lastModified: today, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${SITE_URL}/pricing`, lastModified: today, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${SITE_URL}/privacy`, lastModified: today, changeFrequency: 'yearly', priority: 0.3 },
    { url: `${SITE_URL}/terms`, lastModified: today, changeFrequency: 'yearly', priority: 0.3 },
  ];

  let productPages: MetadataRoute.Sitemap = [];
  let categoryPages: MetadataRoute.Sitemap = [];
  let cityPages: MetadataRoute.Sitemap = [];
  let cityPairs: SitemapCityPair[] = [];

  // --- Products (independent of seller listings: visible products only) ---
  const productsData = (await fetchSitemapJson(
    `${API_URL}/api/seo/sitemap-products`,
    'sitemap-products'
  )) as { products?: { productSlug: string; lastModified?: string | null }[] };
  const products: { productSlug: string; lastModified?: string | null }[] = productsData.products || [];

  productPages = products
    .filter((p) => p.productSlug && p.productSlug.length > 0)
    .map((p) => ({
      url: `${SITE_URL}/products/${p.productSlug}`,
      lastModified: toDateOnly(p.lastModified),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    }));

  // --- Categories ---
  const categoriesData = (await fetchSitemapJson(`${API_URL}/api/categories`, 'categories')) as
    | Category[]
    | { categories?: Category[] };
  const categories: Category[] = Array.isArray(categoriesData)
    ? categoriesData
    : categoriesData.categories || [];

  // Use stored slug when available, otherwise slugify the name
  // (prod DB currently stores slug=null for all categories — we still emit URLs).
  categoryPages = categories
    .filter((c) => c.name && c.name.length > 0)
    .map((category) => {
      const slug = (category.slug && category.slug.length > 0)
        ? category.slug
        : slugify(category.name);
      return {
        url: `${SITE_URL}/categories/${slug}`,
        lastModified: toDateOnly(category.updatedAt),
        changeFrequency: 'weekly' as const,
        priority: 0.7,
      };
    });

  console.log(`[sitemap] Categories added: ${categoryPages.length}/${categories.length}`);

  // --- City pages (only valid pairs with active sellers, capped to top N cities) ---
  const cityData = (await fetchSitemapJson(
    `${API_URL}/api/seo/sitemap-city-pages?max_cities=${MAX_CITIES}&mode=all`,
    'sitemap-city-pages'
  )) as { pairs?: SitemapCityPair[] };
  // City URL only when the backend confirms city eligibility.
  cityPairs = (cityData.pairs || []).filter((p: SitemapCityPair) => p.cityEligible === true);
  cityPages = cityPairs.map((p) => ({
    url: `${SITE_URL}/products/${p.productSlug}/in/${p.citySlug}`,
    lastModified: toDateOnly(p.lastModified),
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }));

  // --- Intent + City pages (programmatic SEO scale: 5 intents × N cityPairs) ---
  // Each (product, city) gets 5 intent variants at lower priority. We cap total.
  const intentPages: MetadataRoute.Sitemap = [];
  for (const p of cityPairs) {
    for (const intent of SUPPORTED_INTENTS) {
      if (p[INTENT_ELIGIBILITY_FIELD[intent]] !== true) continue;
      intentPages.push({
        url: `${SITE_URL}/products/${p.productSlug}/${intent}/in/${p.citySlug}`,
        lastModified: toDateOnly(p.lastModified),
        changeFrequency: 'weekly' as const,
        priority: 0.5,
      });
    }
  }

  const all = [
    ...staticPages,
    ...productPages,
    ...categoryPages,
    ...cityPages,
    ...intentPages,
  ];
  // Safety cap well below Google's 50 000-URL limit.
  return all.slice(0, MAX_URLS);
}
