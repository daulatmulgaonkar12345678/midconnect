import Link from 'next/link';
import { getPublicCategories, searchProducts } from '@/lib/api';
import CategoryCard from '@/components/CategoryCard';
import { ArrowRight, Shield, Truck, BadgeCheck, MapPin, TrendingUp, Package } from 'lucide-react';
import { SearchListing } from '@/types';
import HeroSearchSection from '@/components/HeroSearchSection';

// Category type from public API
interface PublicCategory {
  _id: string;
  name: string;
  image?: string;
  icon?: string;
  productCount: number;
  listingCount: number;
}

export const revalidate = 3600; // Revalidate every hour

export default async function HomePage() {
  let categories: PublicCategory[] = [];
  let featuredProducts: SearchListing[] = [];

  try {
    // Use getPublicCategories to only show categories with active seller listings
    categories = await getPublicCategories();
    const searchResult = await searchProducts('');
    featuredProducts = searchResult.products?.slice(0, 8) || [];
  } catch (error) {
    console.error('Failed to fetch data:', error);
  }

  return (
    <div>
      {/* Hero Section with Search */}
      <HeroSearchSection />

      {/* Trust Badges */}
      <section className="bg-gray-50 py-8 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center gap-4">
              <div className="bg-green-100 p-3 rounded-full">
                <BadgeCheck className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold">GST Verified Sellers</h3>
                <p className="text-sm text-gray-500">All sellers are verified</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-blue-100 p-3 rounded-full">
                <Shield className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">Secure Transactions</h3>
                <p className="text-sm text-gray-500">Direct buyer-seller connect</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-orange-100 p-3 rounded-full">
                <Truck className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <h3 className="font-semibold">Pan India Delivery</h3>
                <p className="text-sm text-gray-500">Nationwide coverage</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Browse by Category</h2>
              <p className="text-gray-500 mt-1">Explore industrial products across categories</p>
            </div>
            {categories.length > 0 && (
              <Link href="/categories" className="text-blue-600 hover:text-blue-700 flex items-center gap-1">
                View All <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>
          
          {categories.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {categories.slice(0, 8).map((category) => (
                <CategoryCard key={category._id} category={category} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-xl border border-gray-100">
              <Package className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">Categories Coming Soon</h3>
              <p className="text-gray-500 max-w-md mx-auto">
                We&apos;re onboarding verified sellers. Product categories will appear here once sellers list their products.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Featured Products */}
      {featuredProducts.length > 0 && (
        <section className="py-16 bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Featured Products</h2>
                <p className="text-gray-500 mt-1">Latest listings from verified sellers</p>
              </div>
              <Link href="/products" className="text-blue-600 hover:text-blue-700 flex items-center gap-1">
                View All <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {featuredProducts.map((listing) => (
                <Link 
                  key={listing._id} 
                  href={`/product/${listing.productId}`}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
                >
                  <div className="aspect-[4/3] bg-gray-100 relative">
                    {listing.images?.[0] ? (
                      <img
                        src={listing.images[0]}
                        alt={listing.productName}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <span className="text-4xl">📦</span>
                      </div>
                    )}
                    {listing.inStock && (
                      <div className="absolute top-2 right-2 bg-green-600 text-white text-xs px-2 py-1 rounded-full">
                        In Stock
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
                      {listing.productName}
                    </h3>
                    {listing.price && (
                      <div className="flex items-center gap-1 text-lg font-bold text-green-600 mb-2">
                        <TrendingUp className="h-4 w-4" />
                        ₹{listing.price.toLocaleString()}
                        <span className="text-xs text-gray-500 font-normal">per unit</span>
                      </div>
                    )}
                    {(listing.city || listing.state) && (
                      <div className="flex items-center gap-1 text-sm text-gray-500">
                        <MapPin className="h-4 w-4" />
                        {listing.city}{listing.city && listing.state ? ', ' : ''}{listing.state}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* CTA Section */}
      <section className="py-16 bg-blue-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to Start Selling?</h2>
          <p className="text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of verified sellers on India&apos;s fastest growing B2B marketplace.
            List your products and reach buyers across India.
          </p>
          <Link
            href="/sell"
            className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition inline-flex items-center gap-2"
          >
            Register as Seller <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
