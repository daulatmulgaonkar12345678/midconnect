import { MetadataRoute } from 'next';

const SITE_URL = 'https://www.udyogconnect.in';
const API_URL = process.env.REACT_APP_BACKEND_URL || 'https://midconnect.onrender.com';

// Cap city pages to top N cities globally (by seller volume) — prevents sitemap bloat.
// Only (product, city) pairs that have active sellers are included.
const MAX_CITIES = 10;

interface Product {
  _id: string;
  name: string;
  slug?: string;
  updatedAt?: string;
}

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

  // --- Products ---
  try {
    const productsResponse = await fetch(`${API_URL}/api/products?limit=1000`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });

    if (productsResponse.ok) {
      const productsData = await productsResponse.json();
      const products: Product[] = Array.isArray(productsData)
        ? productsData
        : productsData.products || [];

      productPages = products
        .filter((p) => p.slug && p.slug.length > 0)
        .map((product) => ({
          url: `${SITE_URL}/products/${product.slug}`,
          lastModified: toDateOnly(product.updatedAt),
          changeFrequency: 'weekly' as const,
          priority: 0.8,
        }));
    }
  } catch (error) {
    console.error('Sitemap: Failed to fetch products:', error);
  }

  // --- Categories ---
  try {
    const categoriesResponse = await fetch(`${API_URL}/api/categories`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });

    if (categoriesResponse.ok) {
      const categoriesData = await categoriesResponse.json();
      const categories: Category[] = Array.isArray(categoriesData)
        ? categoriesData
        : categoriesData.categories || [];

      categoryPages = categories
        .filter((c) => c.slug && c.slug.length > 0)
        .map((category) => ({
          url: `${SITE_URL}/categories/${category.slug}`,
          lastModified: toDateOnly(category.updatedAt),
          changeFrequency: 'weekly' as const,
          priority: 0.7,
        }));
    }
  } catch (error) {
    console.error('Sitemap: Failed to fetch categories:', error);
  }

  // --- City pages (only valid pairs with active sellers, capped to top N cities) ---
  try {
    const cityRes = await fetch(
      `${API_URL}/api/seo/sitemap-city-pages?max_cities=${MAX_CITIES}`,
      {
        next: { revalidate: 3600 },
        signal: AbortSignal.timeout(5000),
      }
    );
    if (cityRes.ok) {
      const cityData = await cityRes.json();
      const pairs: SitemapCityPair[] = cityData.pairs || [];
      cityPages = pairs.map((p) => ({
        url: `${SITE_URL}/products/${p.productSlug}/in/${p.citySlug}`,
        lastModified: toDateOnly(p.lastModified),
        changeFrequency: 'weekly' as const,
        priority: 0.6,
      }));
    }
  } catch (error) {
    console.error('Sitemap: Failed to fetch city pages:', error);
  }

  return [...staticPages, ...productPages, ...categoryPages, ...cityPages];
}
