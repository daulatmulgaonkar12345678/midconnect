import { Metadata } from 'next';
import { notFound, permanentRedirect } from 'next/navigation';
import { getPublicCategories, getProducts } from '@/lib/api';
import Link from 'next/link';
import { Package, Users, ArrowRight, ArrowLeft, Shield, Star } from 'lucide-react';
import { SITE_URL } from '@/lib/siteUrl';

const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '';

interface Props {
  params: Promise<{ slug: string }>;
}

interface PublicCategory {
  _id: string;
  name: string;
  slug?: string;
  productCount: number;
  listingCount: number;
}

interface ProductWithSellers {
  _id: string;
  name: string;
  slug: string;
  description?: string;
  categoryId?: string;
  categoryName?: string;
  images?: string[];
  sellerCount: number;
  minPrice?: number;
}

// Check if identifier is an ObjectId
function isObjectId(str: string): boolean {
  return /^[a-f0-9]{24}$/i.test(str);
}

// Generate static params using slugs
// NOTE (owner revision 5): dynamicParams defaults to true and is NOT set to
// false, so categories added after deployment (e.g. after the V20 slug
// backfill) still resolve correctly at request time even though they were not
// prerendered by this function.
export async function generateStaticParams() {
  try {
    const categories = await getPublicCategories();
    return categories
      .filter((cat) => cat.slug)
      .map((cat) => ({ slug: cat.slug }));
  } catch {
    return [];
  }
}

// Generate SEO-optimized metadata
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  
  // If it's an ObjectId, redirect will happen - return minimal metadata
  if (isObjectId(slug)) {
    return { title: 'Redirecting...' };
  }
  
  try {
    const categories = await getPublicCategories();
    // Batch 6 final remediation (correction 6): match slugs case-insensitively.
    const category = categories.find(
      (c) => (c.slug || '').toLowerCase() === slug.toLowerCase() || c._id === slug
    );
    
    if (category) {
      const title = `Buy ${category.name} Online | Verified Suppliers India | UdyogConnect`;
      const description = `Explore ${category.productCount}+ ${category.name} products from verified suppliers in India. Compare prices, specifications & MOQ. Get best deals on UdyogConnect.`;
      
      return {
        title: title.length > 65 ? `${category.name} Suppliers India | UdyogConnect` : title,
        description: description.slice(0, 160),
        keywords: `${category.name}, buy ${category.name}, ${category.name} suppliers, ${category.name} manufacturers, India, B2B marketplace`,
        openGraph: {
          title,
          description,
          url: `${SITE_URL}/categories/${category.slug || slug}`,
          siteName: 'UdyogConnect',
          type: 'website',
          locale: 'en_IN',
        },
        alternates: {
          canonical: `${SITE_URL}/categories/${category.slug || slug}`,
        },
        robots: {
          index: true,
          follow: true,
        },
      };
    }
  } catch {}
  
  return { 
    title: 'Category - UdyogConnect',
    description: 'Browse industrial products from verified suppliers on UdyogConnect.'
  };
}

export const revalidate = 60;

export default async function CategoryPage({ params }: Props) {
  const { slug } = await params;
  
  let categories: PublicCategory[] = [];
  let category: PublicCategory | undefined;
  let products: ProductWithSellers[] = [];
  // Batch 6 final remediation (correction 4): Next.js redirect helpers abort
  // rendering by THROWING a control-flow error. Redirect targets are only
  // resolved inside try/catch below; the redirect itself is always invoked
  // OUTSIDE any try/catch, so a catch block can never swallow it.
  let redirectTarget: string | null = null;

  // Fetch public categories first (this works on all environments)
  try {
    categories = await getPublicCategories();
  } catch (error) {
    console.error('Failed to fetch categories:', error);
    categories = [];
  }

  // SEO v2.1: Handle ObjectId-based URLs
  if (isObjectId(slug)) {
    // Try to find category by _id in the fetched categories list
    category = categories.find((c) => c._id === slug);
    
    // If found and has a slug, redirect to the canonical URL
    if (category?.slug && category.slug !== slug) {
      redirectTarget = category.slug;
    }
    
    // If not found in categories list, try the enterprise resolver (if available)
    if (!category) {
      try {
        const resolverResponse = await fetch(`${API_URL}/api/enterprise/resolve/category/${slug}`, {
          cache: 'no-store',
          signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        // Batch 6 final remediation: validate the HTTP response BEFORE
        // parsing JSON — a non-2xx body is not resolver data.
        if (resolverResponse.ok) {
          const resolverData = await resolverResponse.json();
          
          // Batch 6 final review (correction 1): redirect ONLY when the
          // canonical slug differs from the requested slug. When the resolver
          // returns the category for the very slug in the URL, the page must
          // RENDER it — setting redirectTarget as well would 308 the page to
          // its own address forever (canonical self-redirect loop).
          if (resolverData.category?.slug && resolverData.category.slug !== slug) {
            redirectTarget = resolverData.category.slug;
          }
          
          if (resolverData.category) {
            category = {
              _id: resolverData.category._id,
              name: resolverData.category.name,
              slug: resolverData.category.slug,
              productCount: 0,
              listingCount: 0
            };
          }
        }
      } catch (resolverError) {
        console.error('Resolver lookup failed (fallback to direct lookup):', resolverError);
      }
    }
  } else {
    // Batch 6 final remediation (correction 6): slugs are stored lowercase.
    // Matching is normalized so any casing of the canonical slug resolves,
    // and noncanonical casing is redirected to the canonical slug.
    const normalizedSlug = slug.toLowerCase();
    category = categories.find((c) => (c.slug || '').toLowerCase() === normalizedSlug);
    if (category?.slug && category.slug !== slug) {
      redirectTarget = category.slug;
    }
  }

  // Corrections 4 & 6: canonicalizing redirects (308) to the persisted
  // canonical slug — invoked strictly outside try/catch.
  if (redirectTarget) {
    permanentRedirect(`/categories/${redirectTarget}`);
  }

  // If category found, update with full data and get products
  if (category) {
    // Update category with full data from public categories
    const fullCategory = categories.find(c => c._id === category?._id);
    if (fullCategory) {
      category = fullCategory;
    }
    
    // Get products for this category
    try {
      products = await getProducts(category._id);
    } catch (error) {
      console.error('Failed to fetch products:', error);
      products = [];
    }
  }

  // Batch 6: an unknown category address is a genuine 404 (never a soft-404
  // HTML page rendered with HTTP 200).
  if (!category) {
    notFound();
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* SEO v2.1 - Structured Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6" aria-label="Breadcrumb">
        <ol className="flex items-center" itemScope itemType="https://schema.org/BreadcrumbList">
          <li itemProp="itemListElement" itemScope itemType="https://schema.org/ListItem">
            <Link href="/" itemProp="item" className="hover:text-gray-700">
              <span itemProp="name">Home</span>
            </Link>
            <meta itemProp="position" content="1" />
          </li>
          <span className="mx-2">/</span>
          <li itemProp="itemListElement" itemScope itemType="https://schema.org/ListItem">
            <Link href="/categories" itemProp="item" className="hover:text-gray-700">
              <span itemProp="name">Categories</span>
            </Link>
            <meta itemProp="position" content="2" />
          </li>
          <span className="mx-2">/</span>
          <li itemProp="itemListElement" itemScope itemType="https://schema.org/ListItem">
            <span itemProp="name" className="text-gray-900">{category.name}</span>
            <meta itemProp="position" content="3" />
          </li>
        </ol>
      </nav>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar - Categories */}
        <aside className="w-full md:w-64 flex-shrink-0">
          <div className="bg-white rounded-xl shadow-sm p-6 sticky top-24">
            <h2 className="font-semibold text-gray-900 mb-4">Categories</h2>
            {categories.length > 0 ? (
              <ul className="space-y-2">
                <li>
                  <Link
                    href="/products"
                    className="flex items-center justify-between px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
                  >
                    <span>All Products</span>
                  </Link>
                </li>
                {categories.map((cat) => {
                  const catUrl = cat.slug ? `/categories/${cat.slug}` : `/categories/${cat._id}`;
                  return (
                    <li key={cat._id}>
                      <Link
                        href={catUrl}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                          cat._id === category._id
                            ? 'bg-blue-50 text-blue-600 font-medium'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        <span>{cat.name}</span>
                        <span className="text-xs text-gray-400">{cat.productCount}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No categories with active sellers</p>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1">
          {/* SEO v2.1 - H1 with category name */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900">
              {category.name} Suppliers in India
            </h1>
            <p className="text-gray-500 mt-2">
              {products.length > 0 
                ? `${products.length} products from ${category.listingCount || products.length} verified sellers`
                : 'No products currently available'}
            </p>
          </div>

          {products.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map((product) => {
                if (!product.name) return null;
                // SEO v2.1: Always use slug-based URLs
                const productUrl = product.slug 
                  ? `/products/${product.slug}` 
                  : `/products/${product._id}`;
                
                return (
                  <Link
                    key={product._id}
                    href={productUrl}
                    className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition group"
                  >
                    <div className="aspect-video bg-gray-100 flex items-center justify-center">
                      {product.images?.[0] ? (
                        <img 
                          src={product.images[0]} 
                          alt={product.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Package className="h-12 w-12 text-gray-400" />
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition line-clamp-1">
                        {product.name}
                      </h3>
                      
                      {/* Seller Count */}
                      <div className="mt-3 flex items-center gap-1.5 text-green-600">
                        <Users className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          {product.sellerCount === 1 
                            ? '1 Seller Available'
                            : `${product.sellerCount} Sellers Available`}
                        </span>
                      </div>
                      
                      {/* Min Price */}
                      {product.minPrice && (
                        <p className="text-sm text-gray-600 mt-2">
                          Starting from <span className="font-semibold text-gray-900">₹{product.minPrice.toLocaleString('en-IN')}</span>
                        </p>
                      )}
                      
                      <div className="mt-3 flex items-center text-blue-600 text-sm font-medium">
                        View Details <ArrowRight className="h-4 w-4 ml-1" />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-100">
              <div className="bg-amber-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5">
                <Package className="h-8 w-8 text-amber-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Sellers Coming Soon</h3>
              <p className="text-gray-500 max-w-sm mx-auto">
                We're connecting with verified suppliers in this category.
              </p>
            </div>
          )}
          
          {/* SEO v2.1 - Structured Content Section */}
          {products.length > 0 && (
            <div className="mt-12 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                About {category.name}
              </h2>
              <p className="text-gray-600 mb-4">
                UdyogConnect connects you with verified suppliers, manufacturers, and dealers 
                of {category.name} across India. Whether you need bulk quantities for industrial 
                projects or are looking for competitive pricing, our platform offers direct 
                access to trusted sellers.
              </p>
              
              <h3 className="text-lg font-medium text-gray-900 mt-6 mb-3">
                Why Buy {category.name} from UdyogConnect?
              </h3>
              <ul className="space-y-2 text-gray-600">
                <li className="flex items-start gap-2">
                  <Shield className="h-5 w-5 text-green-500 mt-0.5" />
                  <span><strong>Verified Suppliers:</strong> All sellers undergo strict verification</span>
                </li>
                <li className="flex items-start gap-2">
                  <Star className="h-5 w-5 text-yellow-500 mt-0.5" />
                  <span><strong>Compare Prices:</strong> Get quotes from multiple suppliers instantly</span>
                </li>
                <li className="flex items-start gap-2">
                  <Users className="h-5 w-5 text-blue-500 mt-0.5" />
                  <span><strong>Direct Communication:</strong> Connect directly with manufacturers</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
