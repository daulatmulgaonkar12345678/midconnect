import { MetadataRoute } from 'next';

const SITE_URL = 'https://www.udyogconnect.in';
const API_URL = process.env.REACT_APP_BACKEND_URL || 'https://midconnect.onrender.com';

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

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();
  
  // Static pages - always included
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/products`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/categories`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/about`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: `${SITE_URL}/contact`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: `${SITE_URL}/pricing`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${SITE_URL}/privacy`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${SITE_URL}/terms`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ];

  // Dynamic pages - fetch from API with timeout
  let productPages: MetadataRoute.Sitemap = [];
  let categoryPages: MetadataRoute.Sitemap = [];

  try {
    // Fetch products with a short timeout to avoid blocking
    const productsResponse = await fetch(`${API_URL}/api/products?limit=1000`, {
      next: { revalidate: 3600 }, // Cache for 1 hour
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (productsResponse.ok) {
      const productsData = await productsResponse.json();
      const products: Product[] = Array.isArray(productsData) 
        ? productsData 
        : productsData.products || [];

      productPages = products
        .filter((p) => p.slug || p._id) // Must have identifier
        .map((product) => ({
          url: `${SITE_URL}/product/${product.slug || product._id}`,
          lastModified: product.updatedAt || now,
          changeFrequency: 'weekly' as const,
          priority: 0.8,
        }));
    }
  } catch (error) {
    console.error('Sitemap: Failed to fetch products:', error);
    // Continue with static pages even if products fail
  }

  try {
    // Fetch categories with a short timeout
    const categoriesResponse = await fetch(`${API_URL}/api/categories`, {
      next: { revalidate: 3600 }, // Cache for 1 hour
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (categoriesResponse.ok) {
      const categoriesData = await categoriesResponse.json();
      const categories: Category[] = Array.isArray(categoriesData)
        ? categoriesData
        : categoriesData.categories || [];

      categoryPages = categories
        .filter((c) => c.slug || c._id) // Must have identifier
        .map((category) => ({
          url: `${SITE_URL}/category/${category.slug || category._id}`,
          lastModified: category.updatedAt || now,
          changeFrequency: 'weekly' as const,
          priority: 0.7,
        }));
    }
  } catch (error) {
    console.error('Sitemap: Failed to fetch categories:', error);
    // Continue with static pages even if categories fail
  }

  // Combine all pages
  return [...staticPages, ...productPages, ...categoryPages];
}
