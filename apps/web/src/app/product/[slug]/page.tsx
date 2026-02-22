'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, notFound } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { 
  getProductWithSellers, 
  createInquiry,
  ProductWithAllSellers,
  ProductSeller,
  PricingTier
} from '@/lib/api';
import { 
  Package, 
  MapPin, 
  Users, 
  Clock, 
  ArrowLeft, 
  Send, 
  Loader2,
  Check,
  AlertCircle,
  MessageCircle,
  BadgeCheck,
  ShoppingCart,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function ProductPage() {
  const params = useParams();
  const router = useRouter();
  const { user, getIdToken, isAuthenticated } = useAuth();
  
  // The URL param is the slug (SEO-friendly) or ObjectId
  const productIdentifier = params?.slug ? decodeURIComponent(params.slug as string) : null;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<ProductWithAllSellers | null>(null);
  
  // Inquiry state
  const [inquiryModal, setInquiryModal] = useState<{ open: boolean; listing: ProductSeller | null }>({ open: false, listing: null });
  const [inquiryQuantity, setInquiryQuantity] = useState<number>(1);
  const [inquiryNote, setInquiryNote] = useState('');
  const [buyerType, setBuyerType] = useState<'trader' | 'contractor' | 'oem' | 'manufacturer' | 'other'>('other');
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  const [inquirySuccess, setInquirySuccess] = useState<string | null>(null);
  const [expandedSpecs, setExpandedSpecs] = useState(false);

  useEffect(() => {
    if (!productIdentifier || productIdentifier === 'null') {
      setError('Invalid product');
      setLoading(false);
      return;
    }

    async function loadProduct() {
      try {
        // API accepts both slug and ObjectId
        const data = await getProductWithSellers(productIdentifier as string);
        setProduct(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Product not found');
      } finally {
        setLoading(false);
      }
    }

    loadProduct();
  }, [productIdentifier]);

  const handleSendInquiry = async () => {
    if (!inquiryModal.listing) return;
    
    if (!isAuthenticated) {
      // Redirect to login with return URL (using slug for SEO-friendly URL)
      const returnPath = product?.slug ? `/product/${product.slug}` : `/product/${productIdentifier}`;
      router.push(`/login?redirect=${encodeURIComponent(returnPath)}`);
      return;
    }

    setSubmittingInquiry(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      // Use new standardized inquiry endpoint
      await createInquiry(token, {
        productId: product?.productId,
        sellerId: inquiryModal.listing.sellerId,
        listingId: inquiryModal.listing.listingId,
        quantity: inquiryQuantity,
        message: inquiryNote || undefined,
        buyerType: buyerType
      });

      setInquirySuccess(`Inquiry sent to ${inquiryModal.listing.companyName}! They will review and respond with a quote.`);
      setInquiryModal({ open: false, listing: null });
      setInquiryQuantity(1);
      setInquiryNote('');
      
      setTimeout(() => setInquirySuccess(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setSubmittingInquiry(false);
    }
  };

  const getLowestPrice = (tiers: ProductSeller['pricingTiers']) => {
    if (!tiers || tiers.length === 0) return null;
    return Math.min(...tiers.map((s: PricingTier) => s.pricePerUnit));
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Product Not Found</h2>
          <p className="text-gray-500 mb-4">{error || 'This product is not available'}</p>
          <Link href="/products" className="text-blue-600 hover:underline flex items-center justify-center gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Products
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Breadcrumb */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <nav className="text-sm text-gray-500">
            <Link href="/" className="hover:text-gray-700">Home</Link>
            <span className="mx-2">/</span>
            <Link href="/products" className="hover:text-gray-700">Products</Link>
            {product.categoryName && (
              <>
                <span className="mx-2">/</span>
                <Link href={`/category/${product.categoryId}`} className="hover:text-gray-700">
                  {product.categoryName}
                </Link>
              </>
            )}
            <span className="mx-2">/</span>
            <span className="text-gray-900">{product.productName}</span>
          </nav>
        </div>
      </div>

      {/* Success Message */}
      {inquirySuccess && (
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700">
            <Check className="h-5 w-5 flex-shrink-0" />
            {inquirySuccess}
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Product Info - Left Column */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              {/* Product Images */}
              <div className="aspect-video bg-gray-100 flex items-center justify-center">
                {product.images?.[0] ? (
                  <img 
                    src={product.images[0]} 
                    alt={product.productName}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <Package className="h-24 w-24 text-gray-300" />
                )}
              </div>

              {/* Product Details */}
              <div className="p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <span className="text-sm text-blue-600 font-medium">{product.categoryName}</span>
                    <h1 className="text-2xl font-bold text-gray-900 mt-1">{product.productName}</h1>
                  </div>
                  <div className="flex items-center gap-1.5 text-green-600 bg-green-50 px-3 py-1.5 rounded-full">
                    <Users className="h-4 w-4" />
                    <span className="font-medium">{product.sellerCount} Sellers</span>
                  </div>
                </div>

                {product.description && (
                  <p className="text-gray-600 mb-6">{product.description}</p>
                )}

                {/* Specifications */}
                {product.specifications && Object.keys(product.specifications).length > 0 && (
                  <div className="border-t pt-6">
                    <button
                      onClick={() => setExpandedSpecs(!expandedSpecs)}
                      className="flex items-center justify-between w-full text-left"
                    >
                      <h2 className="text-lg font-semibold text-gray-900">Technical Specifications</h2>
                      {expandedSpecs ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </button>
                    {expandedSpecs && (
                      <div className="mt-4 grid grid-cols-2 gap-3">
                        {Object.entries(product.specifications).map(([key, value]) => (
                          <div key={key} className="bg-gray-50 p-3 rounded-lg">
                            <p className="text-xs text-gray-500 uppercase">{key.replace(/_/g, ' ')}</p>
                            <p className="font-medium text-gray-900">{String(value)}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Quick Inquiry - Right Column */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 sticky top-24">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <ShoppingCart className="h-5 w-5 text-blue-600" />
                Get Best Quotes
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                {product.sellerCount} verified sellers available. Send inquiry to compare prices.
              </p>
              <Link
                href="#sellers"
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                <Send className="h-5 w-5" />
                View All Sellers
              </Link>
            </div>
          </div>
        </div>

        {/* Available Sellers Section */}
        <div id="sellers" className="mt-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              Available Suppliers ({product.sellerCount})
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {product.sellers.map((seller) => {
              const lowestPrice = getLowestPrice(seller.pricingTiers);
              
              return (
                <div 
                  key={seller.listingId}
                  className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100 hover:shadow-md transition"
                >
                  <div className="p-5">
                    {/* Seller Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900">{seller.companyName}</h3>
                          <BadgeCheck className="h-4 w-4 text-blue-500" />
                        </div>
                        <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                          <MapPin className="h-3.5 w-3.5" />
                          {seller.location}
                        </p>
                      </div>
                      {seller.stockStatus === 'in_stock' && (
                        <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                          In Stock
                        </span>
                      )}
                    </div>

                    {/* Pricing */}
                    <div className="bg-gray-50 rounded-lg p-4 mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Starting Price</span>
                        {lowestPrice && (
                          <span className="text-xl font-bold text-gray-900">
                            {formatPrice(lowestPrice)}/unit
                          </span>
                        )}
                      </div>
                      
                      {/* Price Slabs */}
                      {seller.pricingTiers && seller.pricingTiers.length > 0 && (
                        <div className="border-t border-gray-200 mt-3 pt-3">
                          <p className="text-xs text-gray-500 mb-2">Quantity-based pricing:</p>
                          <div className="space-y-1">
                            {seller.pricingTiers.slice(0, 3).map((slab, idx) => (
                              <div key={idx} className="flex justify-between text-sm">
                                <span className="text-gray-600">
                                  {slab.minQty}{slab.maxQty ? `-${slab.maxQty}` : '+'} units
                                </span>
                                <span className="font-medium">{formatPrice(slab.pricePerUnit)}/unit</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* MOQ & Lead Time */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
                      <span className="flex items-center gap-1">
                        <Package className="h-4 w-4" />
                        MOQ: {seller.moq} units
                      </span>
                      {seller.leadTimeDays && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {seller.leadTimeDays} days lead time
                        </span>
                      )}
                    </div>

                    {/* Inquiry Button */}
                    <button
                      onClick={() => setInquiryModal({ open: true, listing: seller })}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition"
                      data-testid={`inquiry-btn-${seller.listingId}`}
                    >
                      <Send className="h-4 w-4" />
                      Send Inquiry
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Buyer Inquiry Link */}
        {isAuthenticated && (
          <div className="mt-8 text-center">
            <Link
              href="/buyer/inquiries"
              className="text-blue-600 hover:underline text-sm"
            >
              View My Inquiries →
            </Link>
          </div>
        )}
      </main>

      {/* Inquiry Modal */}
      {inquiryModal.open && inquiryModal.listing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Send className="h-5 w-5 text-blue-600" />
                Send Inquiry to {inquiryModal.listing.companyName}
              </h3>

              {!isAuthenticated && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                  <AlertCircle className="h-4 w-4 inline mr-2" />
                  You need to login to send an inquiry
                </div>
              )}

              <div className="space-y-4">
                {/* Product Info */}
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-600">Product</p>
                  <p className="font-medium">{product.productName}</p>
                </div>

                {/* Quantity */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quantity Required *
                  </label>
                  <input
                    type="number"
                    value={inquiryQuantity}
                    onChange={(e) => setInquiryQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min={inquiryModal.listing.moq}
                    placeholder={`Minimum: ${inquiryModal.listing.moq}`}
                  />
                  <p className="text-xs text-gray-500 mt-1">MOQ: {inquiryModal.listing.moq} units</p>
                </div>

                {/* Buyer Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    I am a
                  </label>
                  <select
                    value={buyerType}
                    onChange={(e) => setBuyerType(e.target.value as typeof buyerType)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="trader">Trader</option>
                    <option value="contractor">Contractor</option>
                    <option value="oem">OEM</option>
                    <option value="manufacturer">Manufacturer</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                {/* Note */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Requirements / Message (Optional)
                  </label>
                  <textarea
                    value={inquiryNote}
                    onChange={(e) => setInquiryNote(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows={3}
                    placeholder="Describe your specific requirements, preferred delivery timeline, etc."
                    maxLength={1000}
                  />
                </div>
              </div>

              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {error}
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleSendInquiry}
                  disabled={submittingInquiry}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
                >
                  {submittingInquiry ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      <Send className="h-5 w-5" />
                      {isAuthenticated ? 'Send Inquiry' : 'Login & Send'}
                    </>
                  )}
                </button>
                <button
                  onClick={() => setInquiryModal({ open: false, listing: null })}
                  className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>

              <p className="text-xs text-gray-500 mt-4 text-center">
                Your contact details are masked until the seller accepts your inquiry.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center">
          <p className="text-gray-600">India's trusted B2B marketplace</p>
          <p className="text-gray-500 text-sm mt-1">Connecting verified buyers and sellers across industries.</p>
        </div>
      </footer>
    </div>
  );
}
