'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { 
  MapPin, Phone, Star, Shield, Calendar, Users, 
  ChevronRight, MessageSquare, Package,
  Building2, Award, RefreshCw
} from 'lucide-react';
import { getSellerCatalog, type SellerCatalogResponse, type EnterpriseProductSeller } from '@/lib/api';
import InquiryModal from '@/components/enterprise/InquiryModal';

interface SellerCatalogPageProps {
  slug: string;
}

export default function SellerCatalogPage({ slug }: SellerCatalogPageProps) {
  const [catalog, setCatalog] = useState<SellerCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inquiryModalOpen, setInquiryModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<{
    seller: EnterpriseProductSeller;
    productId: string;
    productName: string;
    productDescription?: string;
  } | null>(null);

  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        setLoading(true);
        // Fetch all products per category (seller catalog shows the seller's full portfolio)
        const data = await getSellerCatalog(slug, 500);
        setCatalog(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load seller catalog');
      } finally {
        setLoading(false);
      }
    };

    fetchCatalog();
  }, [slug]);

  const handleInquiry = (product?: { 
    listingId: string; 
    productName: string;
    productId?: string;
    description?: string;
    images?: string[];
    moq?: number;
    pricingSlabs?: Array<{minQty: number; maxQty: number; price: number}>;
  }) => {
    if (!catalog) return;
    
    // Calculate lowest price from pricing slabs
    const lowestPrice = product?.pricingSlabs && product.pricingSlabs.length > 0
      ? Math.min(...product.pricingSlabs.map(p => p.price))
      : undefined;
    
    // Create a minimal EnterpriseProductSeller object for the modal
    const sellerForModal: EnterpriseProductSeller = {
      listingId: product?.listingId || '',
      sellerId: catalog.seller.id,
      companyName: catalog.seller.companyName || 'Seller',
      location: catalog.seller.location?.city && catalog.seller.location?.state 
        ? `${catalog.seller.location.city}, ${catalog.seller.location.state}` 
        : 'India',
      city: catalog.seller.location?.city,
      state: catalog.seller.location?.state,
      sellerRole: 'dealer',
      sellerSlug: catalog.seller.slug,
      badgeType: catalog.seller.badgeType as 'none' | 'choice' | 'trusted' | undefined,
      searchableAttributes: {},
      attributeLabels: {},
      pricingTiers: [],
      moq: product?.moq || 1,
      stock: 100,
      images: product?.images || [],
      lowestPrice: lowestPrice,
      stockStatus: 'in_stock'
    };
    
    setSelectedProduct({
      seller: sellerForModal,
      productId: product?.productId || product?.listingId || '',
      productName: product?.productName || 'General Inquiry',
      productDescription: product?.description
    });
    setInquiryModalOpen(true);
  };

  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await getSellerCatalog(slug, 4);
      setCatalog(data);
    } catch {
      // Keep existing data on refresh error
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-8">
            {/* Banner skeleton */}
            <div className="h-48 bg-gray-200 rounded-xl" />
            {/* Info skeleton */}
            <div className="flex gap-6">
              <div className="w-24 h-24 bg-gray-200 rounded-xl" />
              <div className="flex-1 space-y-3">
                <div className="h-8 bg-gray-200 rounded w-1/3" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
              </div>
            </div>
            {/* Products skeleton */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-64 bg-gray-200 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !catalog) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Building2 className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Seller Not Found</h1>
          <p className="text-gray-500 mb-6">{error || 'The seller you are looking for could not be found.'}</p>
          <Link 
            href="/"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Browse All Sellers
          </Link>
        </div>
      </div>
    );
  }

  const { seller, categories, totalCategories, totalProducts } = catalog;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Banner Section */}
      <div className="relative">
        {seller.bannerImage ? (
          <div className="h-48 md:h-64 relative">
            <Image
              src={seller.bannerImage}
              alt={`${seller.companyName} banner`}
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30" />
          </div>
        ) : (
          <div className="h-48 md:h-64 bg-gradient-to-br from-blue-600 to-blue-800 relative">
            <div className="absolute inset-0 opacity-10">
              <div className="absolute inset-0" style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
              }} />
            </div>
          </div>
        )}
      </div>

      {/* Seller Info Card */}
      <div className="max-w-7xl mx-auto px-4 -mt-16 relative z-10">
        <div className="bg-white rounded-xl shadow-lg p-6 md:p-8">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Logo */}
            <div className="flex-shrink-0">
              {seller.logo ? (
                <Image
                  src={seller.logo}
                  alt={seller.companyName || 'Seller'}
                  width={100}
                  height={100}
                  className="w-24 h-24 md:w-28 md:h-28 rounded-xl object-cover border-4 border-white shadow-md"
                />
              ) : (
                <div className="w-24 h-24 md:w-28 md:h-28 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center border-4 border-white shadow-md">
                  <span className="text-3xl font-bold text-white">
                    {seller.companyName?.charAt(0) || 'S'}
                  </span>
                </div>
              )}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
                    {seller.companyName}
                  </h1>
                  
                  {/* Location */}
                  {(seller.location?.city || seller.location?.state) && (
                    <p className="flex items-center gap-2 text-gray-600 mb-3">
                      <MapPin className="h-4 w-4" />
                      {[seller.location.city, seller.location.state].filter(Boolean).join(', ')}
                    </p>
                  )}

                  {/* Badges */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {seller.enterpriseEstablishmentYear && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-full">
                        <Calendar className="h-3.5 w-3.5" />
                        Established {seller.enterpriseEstablishmentYear}
                      </span>
                    )}
                    {seller.platformRegistrationYear && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-50 text-green-700 text-sm rounded-full">
                        <Users className="h-3.5 w-3.5" />
                        Member since {seller.platformRegistrationYear}
                      </span>
                    )}
                    {seller.gstVerified && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 text-sm rounded-full">
                        <Shield className="h-3.5 w-3.5" />
                        GST Verified
                      </span>
                    )}
                    {seller.badgeType && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-700 text-sm rounded-full">
                        <Award className="h-3.5 w-3.5" />
                        {seller.badgeType}
                      </span>
                    )}
                  </div>
                </div>

                {/* Rating */}
                {seller.rating && seller.rating.totalReviews > 0 && (
                  <div className="text-center p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Star className="h-6 w-6 fill-yellow-400 text-yellow-400" />
                      <span className="text-2xl font-bold">{seller.rating.avgRating}</span>
                    </div>
                    <p className="text-sm text-gray-500">{seller.rating.totalReviews} reviews</p>
                  </div>
                )}
              </div>

              {/* Stats */}
              <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t">
                <div>
                  <p className="text-2xl font-bold text-gray-900">{totalProducts}</p>
                  <p className="text-sm text-gray-500">Products</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{totalCategories}</p>
                  <p className="text-sm text-gray-500">Categories</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-3 md:w-48">
              <button
                onClick={() => handleInquiry()}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2"
                data-testid="send-inquiry-btn"
              >
                <MessageSquare className="h-5 w-5" />
                Send Inquiry
              </button>
              
              {seller.phone && (
                <a
                  href={`tel:${seller.phone}`}
                  className="w-full border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 transition flex items-center justify-center gap-2"
                >
                  <Phone className="h-5 w-5" />
                  Call Seller
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Products by Category */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Products Catalog</h2>
          <button
            onClick={handleRefresh}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            title="Refresh to see different products"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {categories.length === 0 ? (
          <div className="bg-white rounded-xl p-12 text-center">
            <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Products Yet</h3>
            <p className="text-gray-500">This seller hasn&apos;t listed any products yet.</p>
          </div>
        ) : (
          <div className="space-y-8">
            {categories.map((category) => (
              <div key={category.categoryId} className="bg-white rounded-xl shadow-sm overflow-hidden">
                {/* Category Header */}
                <div className="p-4 md:p-6 border-b bg-gray-50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {category.categoryIcon && (
                      <span className="text-2xl">{category.categoryIcon}</span>
                    )}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {category.categoryName}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>{category.totalProducts} products</span>
                        {category.avgRating > 0 && (
                          <span className="flex items-center gap-1">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            {category.avgRating} ({category.totalReviews})
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {category.totalProducts > 4 && category.categorySlug && (
                    <Link
                      href={`/seller-catalog/${slug}/category/${category.categorySlug}`}
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
                    >
                      View All
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  )}
                </div>

                {/* Products Grid */}
                <div className="p-4 md:p-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {category.products.map((product) => (
                      <ProductCard
                        key={product.listingId}
                        product={product}
                        sellerSlug={slug}
                        sellerName={seller.companyName || ''}
                        onInquiry={() => handleInquiry({
                          listingId: product.listingId,
                          productId: product.productId,
                          productName: product.productName,
                          description: product.description,
                          images: product.images,
                          moq: product.moq,
                          pricingSlabs: product.pricingSlabs
                        })}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Inquiry Modal */}
      {selectedProduct && (
        <InquiryModal
          isOpen={inquiryModalOpen}
          onClose={() => {
            setInquiryModalOpen(false);
            setSelectedProduct(null);
          }}
          seller={selectedProduct.seller}
          productId={selectedProduct.productId}
          productName={selectedProduct.productName}
          productDescription={selectedProduct.productDescription}
        />
      )}

      {/* Schema.org Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Organization',
            name: seller.companyName,
            image: seller.logo,
            address: {
              '@type': 'PostalAddress',
              addressLocality: seller.location?.city,
              addressRegion: seller.location?.state,
              addressCountry: 'IN'
            },
            telephone: seller.phone,
            email: seller.email,
            foundingDate: seller.enterpriseEstablishmentYear?.toString(),
            aggregateRating: seller.rating?.totalReviews > 0 ? {
              '@type': 'AggregateRating',
              ratingValue: seller.rating.avgRating,
              reviewCount: seller.rating.totalReviews
            } : undefined
          })
        }}
      />
    </div>
  );
}

// Product Card Component
interface ProductCardProps {
  product: {
    listingId: string;
    productId: string;
    productName: string;
    productSlug: string;
    description: string;
    images: string[];
    pricingSlabs: Array<{minQty: number; maxQty: number; price: number}>;
    moq: number;
    avgRating: number;
    totalReviews: number;
    stockStatus: string;
  };
  sellerSlug: string;
  sellerName: string;
  onInquiry: () => void;
}

function ProductCard({ product, sellerSlug, sellerName, onInquiry }: ProductCardProps) {
  const firstImage = product.images?.[0];
  const basePrice = product.pricingSlabs?.[0]?.price;

  return (
    <div className="group relative bg-white border rounded-xl overflow-hidden hover:shadow-lg transition-shadow">
      {/* Image */}
      <Link href={`/products/${product.productSlug || product.productId}`}>
        <div className="aspect-square relative bg-gray-100">
          {firstImage ? (
            <Image
              src={firstImage}
              alt={product.productName}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <Package className="h-12 w-12 text-gray-300" />
            </div>
          )}
          
          {/* Stock status badge */}
          {product.stockStatus && product.stockStatus !== 'in_stock' && (
            <div className="absolute top-2 left-2">
              <span className={`px-2 py-1 text-xs font-medium rounded ${
                product.stockStatus === 'low_stock' 
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-red-100 text-red-700'
              }`}>
                {product.stockStatus === 'low_stock' ? 'Low Stock' : 'Out of Stock'}
              </span>
            </div>
          )}
        </div>
      </Link>

      {/* Info */}
      <div className="p-3">
        <Link href={`/products/${product.productSlug || product.productId}`}>
          <h4 className="font-medium text-gray-900 text-sm line-clamp-2 hover:text-blue-600 transition mb-1">
            {product.productName}
          </h4>
        </Link>

        {/* Seller link with hover animation */}
        <Link 
          href={`/seller-catalog/${sellerSlug}`}
          className="text-xs text-gray-500 hover:text-blue-600 transition-colors relative inline-block group/seller"
        >
          <span className="relative">
            By {sellerName}
            <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-blue-600 group-hover/seller:w-full transition-all duration-300" />
          </span>
        </Link>

        {/* Rating */}
        {product.avgRating > 0 && (
          <div className="flex items-center gap-1 mt-1">
            <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
            <span className="text-xs text-gray-600">{product.avgRating}</span>
            {product.totalReviews > 0 && (
              <span className="text-xs text-gray-400">({product.totalReviews})</span>
            )}
          </div>
        )}

        {/* Price */}
        {basePrice && (
          <p className="text-sm font-semibold text-gray-900 mt-2">
            ₹{basePrice.toLocaleString('en-IN')}
            <span className="text-xs font-normal text-gray-500">/unit</span>
          </p>
        )}

        {/* MOQ */}
        {product.moq > 1 && (
          <p className="text-xs text-gray-500 mt-0.5">
            MOQ: {product.moq} units
          </p>
        )}

        {/* Quick Inquiry Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            onInquiry();
          }}
          className="w-full mt-3 py-2 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
          data-testid={`inquiry-btn-${product.listingId}`}
        >
          Send Inquiry
        </button>
      </div>
    </div>
  );
}
