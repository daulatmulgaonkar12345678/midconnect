import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPublicCategories, getProducts } from '@/lib/api';
import Link from 'next/link';
import { Package, Users, ArrowRight, ArrowLeft } from 'lucide-react';

interface Props {
  params: Promise<{ id: string }>;
}

interface PublicCategory {
  _id: string;
  name: string;
  productCount: number;
  listingCount: number;
}

interface ProductWithSellers {
  _id: string;
  name: string;
  slug: string;  // SEO-friendly URL identifier
  description?: string;
  categoryId?: string;
  categoryName?: string;
  images?: string[];
  sellerCount: number;
  minPrice?: number;
}

// Generate static params
export async function generateStaticParams() {
  try {
    const categories = await getPublicCategories();
    return categories.map((cat) => ({ id: cat._id }));
  } catch {
    return [];
  }
}

// Generate metadata
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const categories = await getPublicCategories();
    const category = categories.find((c) => c._id === id);
    if (category) {
      return {
        title: `${category.name} - Industrial Products | MidConnect`,
        description: `Browse ${category.name} products from verified sellers.`,
      };
    }
  } catch {}
  return { title: 'Category - MidConnect' };
}

export const revalidate = 60;

export default async function CategoryPage({ params }: Props) {
  const { id } = await params;
  let categories: PublicCategory[] = [];
  let category: PublicCategory | undefined;
  let products: ProductWithSellers[] = [];

  try {
    [categories, products] = await Promise.all([
      getPublicCategories(),
      getProducts(id)
    ]);
    category = categories.find((c) => c._id === id);
  } catch (error) {
    console.error('Failed to fetch category:', error);
  }

  // If no products for this category, redirect to all products
  if (!category && products.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-16 bg-white rounded-xl">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Products in This Category</h3>
          <p className="text-gray-500 mb-4">
            This category doesn't have any products with active sellers yet.
          </p>
          <Link
            href="/products"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <ArrowLeft className="h-4 w-4" />
            View All Products
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6">
        <Link href="/" className="hover:text-gray-700">Home</Link>
        <span className="mx-2">/</span>
        <Link href="/products" className="hover:text-gray-700">Products</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{category?.name || 'Category'}</span>
      </nav>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar */}
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
                {categories.map((cat) => (
                  <li key={cat._id}>
                    <Link
                      href={`/category/${cat._id}`}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                        cat._id === id
                          ? 'bg-blue-50 text-blue-600 font-medium'
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <span>{cat.name}</span>
                      <span className="text-xs text-gray-400">{cat.productCount}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No categories with active sellers</p>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900">{category?.name || 'Products'}</h1>
            <p className="text-gray-500">
              {products.length > 0 
                ? `${products.length} products from verified sellers`
                : 'No products currently available'}
            </p>
          </div>

          {products.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map((product) => {
                if (!product.name || !product.slug) return null;
                
                return (
                  <Link
                    key={product._id}
                    href={`/product/${product.slug}`}
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
                      {product.min_price && (
                        <p className="text-sm text-gray-600 mt-2">
                          Starting from <span className="font-semibold text-gray-900">₹{product.min_price.toLocaleString('en-IN')}</span>
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
            <div className="text-center py-16 bg-white rounded-xl">
              <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Products Currently Available</h3>
              <p className="text-gray-500">
                Products appear here when verified sellers list them for sale.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
