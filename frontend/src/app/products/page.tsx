import { Metadata } from 'next';
import { getPublicCategories, getProducts } from '@/lib/api';
import Link from 'next/link';
import { Package, Users, ArrowRight } from 'lucide-react';

export const metadata: Metadata = {
  title: 'All Products - UdyogConnect',
  description: 'Browse industrial products from verified sellers. Steel, electrical equipment, chemicals, building materials and more.',
};

export const revalidate = 60; // 1 minute

interface PublicCategory {
  _id: string;
  name: string;
  slug?: string;  // SEO-friendly URL identifier
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

export default async function ProductsPage() {
  let categories: PublicCategory[] = [];
  let products: ProductWithSellers[] = [];

  try {
    [categories, products] = await Promise.all([
      getPublicCategories(),
      getProducts()
    ]);
  } catch (error) {
    console.error('Failed to fetch products:', error);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar - Categories with active sellers only */}
        <aside className="w-full md:w-64 flex-shrink-0">
          <div className="bg-white rounded-xl shadow-sm p-6 sticky top-24">
            <h2 className="font-semibold text-gray-900 mb-4">Categories</h2>
            {categories.length > 0 ? (
              <ul className="space-y-2">
                <li>
                  <Link
                    href="/products"
                    className="flex items-center justify-between px-3 py-2 rounded-lg bg-blue-50 text-blue-600 font-medium"
                  >
                    <span>All Products</span>
                    <span className="text-xs bg-blue-100 px-2 py-0.5 rounded-full">{products.length}</span>
                  </Link>
                </li>
                {categories.map((cat) => (
                  <li key={cat._id}>
                    <Link
                      href={`/categories/${cat.slug || cat._id}`}
                      className="flex items-center justify-between px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
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
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">All Products</h1>
              <p className="text-gray-500">
                {products.length > 0 
                  ? `${products.length} products from verified sellers`
                  : 'No products currently available'}
              </p>
            </div>
          </div>

          {products.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map((product) => (
                <Link
                  key={product._id}
                  href={`/products/${product.slug || product._id}`}
                  className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition group"
                >
                  <div className="aspect-video bg-gray-100 flex items-center justify-center">
                    {product.images && product.images[0] ? (
                      <img 
                        src={product.images[0]} 
                        alt={product.name || 'Product'}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Package className="h-12 w-12 text-gray-400" />
                    )}
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition line-clamp-1">
                      {product.name || 'Unnamed Product'}
                    </h3>
                    {product.categoryName && (
                      <p className="text-sm text-gray-500 mt-1">{product.categoryName}</p>
                    )}
                    
                    {/* Seller Count */}
                    <div className="mt-3 flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-green-600">
                        <Users className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          {product.sellerCount === 1 
                            ? '1 Seller Available'
                            : `${product.sellerCount || 0} Sellers Available`}
                        </span>
                      </div>
                    </div>
                    
                    {/* Min Price */}
                    {product.minPrice && product.minPrice > 0 && (
                      <p className="text-sm text-gray-600 mt-2">
                        Starting from <span className="font-semibold text-gray-900">₹{product.minPrice.toLocaleString('en-IN')}</span>
                      </p>
                    )}
                    
                    <div className="mt-3 flex items-center text-blue-600 text-sm font-medium">
                      View Details <ArrowRight className="h-4 w-4 ml-1" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 bg-white rounded-xl">
              <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Products Currently Available</h3>
              <p className="text-gray-500 max-w-md mx-auto">
                Products appear here when verified sellers list them for sale.
                Check back later for new listings.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
