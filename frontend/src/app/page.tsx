import Link from 'next/link';
import { getPublicCategories, searchProducts, getProducts } from '@/lib/api';
import CategoryCard from '@/components/CategoryCard';
import { ArrowRight, Shield, Truck, BadgeCheck, MapPin, TrendingUp, Package } from 'lucide-react';
import { SearchListing, Category } from '@/types';
import HeroSearchSection from '@/components/HeroSearchSection';

export const revalidate = 3600; // Revalidate every hour

// Top Indian industrial cities used for the homepage "Popular by City" internal links.
// Keep in sync with backend SUPPORTED_INTENTS & top cities for consistency.
const TOP_CITIES = ['Pune', 'Mumbai', 'Delhi', 'Ahmedabad', 'Bangalore'];

export default async function HomePage() {
  // Use Category type - compatible with PublicCategory response
  let categories: Category[] = [];
  let featuredProducts: SearchListing[] = [];
  // Slug-bearing products for SEO-friendly internal links ("Popular Industrial Products" section).
  let popularProducts: Array<{ _id: string; name: string; slug: string }> = [];

  try {
    // Use getPublicCategories to only show categories with active seller listings
    const publicCategories = await getPublicCategories();
    // Map to Category type (all required fields are present in response)
    categories = publicCategories.map(cat => ({
      ...cat,
      description: '',
      isActive: true
    }));
    const searchResult = await searchProducts('');
    featuredProducts = searchResult.products?.slice(0, 8) || [];

    // Fetch top 20 products with slugs for SEO internal links. Reuses existing API.
    const allProducts = await getProducts();
    popularProducts = allProducts
      .filter(p => p.slug && p.slug.length > 0)
      .slice(0, 20);
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

      {/* Popular Industrial Products — SEO internal linking (crawlable anchor links) */}
      {popularProducts.length > 0 && (
        <section className="py-12 bg-white border-t border-gray-100" data-testid="popular-products-seo">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Popular Industrial Products</h2>
            <p className="text-gray-500 mb-6 text-sm">
              Discover verified suppliers of top industrial products across India.
            </p>
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3 list-none">
              {popularProducts.map((p) => (
                <li key={p._id}>
                  <a
                    href={`/products/${p.slug}`}
                    className="text-blue-600 hover:text-blue-800 hover:underline text-sm"
                    data-testid={`popular-product-link-${p.slug}`}
                  >
                    {p.name} Suppliers in India
                  </a>
                </li>
              ))}
            </ul>

            {/* Popular by City — top 4 products × 5 cities = 20 crawlable city URLs */}
            <h3 className="text-lg font-semibold text-gray-900 mt-10 mb-4">Popular Products by City</h3>
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-2 list-none">
              {popularProducts.slice(0, 4).flatMap((p) =>
                TOP_CITIES.map((city) => {
                  const citySlug = city.toLowerCase();
                  return (
                    <li key={`${p._id}-${citySlug}`}>
                      <a
                        href={`/products/${p.slug}/in/${citySlug}`}
                        className="text-gray-700 hover:text-blue-700 hover:underline text-sm"
                        data-testid={`popular-city-link-${p.slug}-${citySlug}`}
                      >
                        {p.name} in {city}
                      </a>
                    </li>
                  );
                })
              )}
            </ul>
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
