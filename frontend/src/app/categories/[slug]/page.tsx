import { Metadata } from 'next';
import { notFound, redirect } from 'next/navigation';
import { getPublicCategories, getProducts } from '@/lib/api';
import Link from 'next/link';
import { Package, Users, ArrowRight, ArrowLeft, Shield, Star } from 'lucide-react';

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
    const category = categories.find((c) => c.slug === slug || c._id === slug);
    
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
          url: `https://www.udyogconnect.in/categories/${category.slug || slug}`,
          siteName: 'UdyogConnect',
          type: 'website',
          locale: 'en_IN',
        },
        alternates: {
          canonical: `https://www.udyogconnect.in/categories/${category.slug || slug}`,
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
  
  // SEO v2.1: Check for ObjectId and redirect to slug-based URL
  if (isObjectId(slug)) {
    try {
      const response = await fetch(`${API_URL}/api/redirect/category/${slug}`, {
        cache: 'no-store'
      });
      const data = await response.json();
      
      if (data.redirect && data.slug) {
        redirect(`/categories/${data.slug}`);
      }
    } catch (error) {
      console.error('Redirect lookup failed:', error);
    }
  }
  
  let categories: PublicCategory[] = [];
  let category: PublicCategory | undefined;
  let products: ProductWithSellers[] = [];

  try {
    categories = await getPublicCategories();
    
    // Find category by slug first, then by ID
    category = categories.find((c) => c.slug === slug) || 
               categories.find((c) => c._id === slug);
    
    if (category) {
      // Get products for this category
      products = await getProducts(category._id);
    }
  } catch (error) {
    console.error('Failed to fetch category:', error);
  }

  // If category not found
  if (!category) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-100">
          <div className="bg-blue-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Package className="h-10 w-10 text-blue-500" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-3">Category Not Found</h3>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">
            This category doesn't exist or has no active products.
          </p>
          <Link
            href="/products"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Browse All Products
          </Link>
        </div>
      </div>
    );
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
