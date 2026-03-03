'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/context/AuthContext';
import StarRating, { StarRatingBadge } from '@/components/StarRating';
import {
  ArrowLeft,
  Send,
  MapPin,
  Building2,
  Calendar,
  BadgeCheck,
  Shield,
  Star,
  Play,
  Video,
  Package,
  Clock,
  Layers,
  Truck,
  MessageSquare,
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface SellerDetailData {
  product: {
    _id: string;
    name: string;
    slug?: string;
    description?: string;
    images: string[];
    categoryId?: string;
    normalizedSpecs?: Record<string, unknown>;
  };
  sellerListing: {
    _id: string;
    sellerId: string;
    productId: string;
    images: string[];
    videos?: string[];
    description?: string;
    moq: number;
    stock: number;
    maxCapacity?: number;
    leadTime?: number;
    currency: string;
    pricingTiers: Array<{
      minQty: number;
      maxQty?: number;
      pricePerUnit: number;
    }>;
    sellerRole: string;
    searchableAttributes?: Record<string, unknown>;
    attributeLabels?: Record<string, string>;
  };
  seller: {
    _id: string;
    businessName: string;
    city?: string;
    state?: string;
    badgeType: 'none' | 'choice' | 'trusted';
    gstNumber?: string;
    establishedYear?: number;
  };
  category: {
    _id: string;
    name: string;
    slug?: string;
  };
  reviews: Array<{
    _id: string;
    buyerName: string;
    rating: number;
    reviewText?: string;
    createdAt: string;
  }>;
  avgRating: number;
  totalReviews: number;
}

interface Props {
  params: Promise<{ slug: string; listingId: string }>;
}

export default function SellerDetailPage({ params }: Props) {
  const router = useRouter();
  const { user, getIdToken } = useAuth();
  
  const [data, setData] = useState<SellerDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedImage, setSelectedImage] = useState(0);
  const [showVideo, setShowVideo] = useState(false);
  
  // Review state
  const [canReview, setCanReview] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewText, setReviewText] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewSuccess, setReviewSuccess] = useState(false);
  
  // Inquiry state
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [inquiryMessage, setInquiryMessage] = useState('');
  const [inquiryQuantity, setInquiryQuantity] = useState('');
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  
  const [listingId, setListingId] = useState<string>('');
  const [productSlug, setProductSlug] = useState<string>('');
  
  // Load params
  useEffect(() => {
    params.then((p) => {
      setListingId(p.listingId);
      setProductSlug(p.slug);
    });
  }, [params]);
  
  // Fetch data
  useEffect(() => {
    if (!listingId) return;
    
    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/api/reviews/seller-listing/${listingId}/details`);
        
        if (!response.ok) {
          throw new Error('Seller listing not found');
        }
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load seller details');
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [listingId]);
  
  // Check review eligibility
  useEffect(() => {
    if (!listingId || !user) return;
    
    async function checkEligibility() {
      try {
        const token = await getIdToken();
        if (!token) return;
        
        const response = await fetch(`${API_URL}/api/reviews/eligible?sellerListingId=${listingId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (response.ok) {
          const result = await response.json();
          setCanReview(result.eligible);
        }
      } catch (err) {
        console.error('Failed to check review eligibility:', err);
      }
    }
    
    checkEligibility();
  }, [listingId, user, getIdToken]);
  
  // Submit review
  const handleSubmitReview = async () => {
    if (!user || !listingId) return;
    
    const token = await getIdToken();
    if (!token) return;
    
    setSubmittingReview(true);
    try {
      const response = await fetch(`${API_URL}/api/reviews`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          sellerListingId: listingId,
          rating: reviewRating,
          reviewText: reviewText.trim() || null
        })
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to submit review');
      }
      
      setReviewSuccess(true);
      setShowReviewForm(false);
      setCanReview(false);
      
      // Refresh data to show new review
      const refreshResponse = await fetch(`${API_URL}/api/reviews/seller-listing/${listingId}/details`);
      if (refreshResponse.ok) {
        const result = await refreshResponse.json();
        setData(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit review');
    } finally {
      setSubmittingReview(false);
    }
  };
  
  // Submit inquiry
  const handleSubmitInquiry = async () => {
    if (!user || !data) return;
    
    const token = await getIdToken();
    if (!token) return;
    
    setSubmittingInquiry(true);
    try {
      const response = await fetch(`${API_URL}/api/inquiries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          sellerId: data.seller?._id,
          productId: data.product._id,
          listingId: data.sellerListing._id,
          quantity: parseInt(inquiryQuantity) || data.sellerListing.moq,
          message: inquiryMessage
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to submit inquiry');
      }
      
      setShowInquiryModal(false);
      setInquiryMessage('');
      setInquiryQuantity('');
      alert('Inquiry sent successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setSubmittingInquiry(false);
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="text-lg">Loading seller details...</span>
        </div>
      </div>
    );
  }
  
  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Seller Not Found</h2>
          <p className="text-gray-600 mb-6">{error || 'Unable to load seller details'}</p>
          <button 
            onClick={() => router.back()} 
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Ensure seller data exists
  if (!data.seller || !data.sellerListing || !data.product) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Seller Information Unavailable</h2>
          <p className="text-gray-600 mb-6">Unable to load seller information for this listing.</p>
          <button 
            onClick={() => router.back()} 
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </button>
        </div>
      </div>
    );
  }
  
  const { product, sellerListing, seller, category, reviews, avgRating, totalReviews } = data;
  const allMedia = [...(sellerListing.images || [])];
  const hasVideos = sellerListing.videos && sellerListing.videos.length > 0;
  const lowestPrice = sellerListing.pricingTiers?.[0]?.pricePerUnit;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-14 gap-4">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
            >
              <ArrowLeft className="h-5 w-5" />
              <span className="hidden sm:inline">Back</span>
            </button>
            
            {/* Breadcrumb */}
            <nav className="flex items-center text-sm text-gray-500 overflow-hidden">
              <Link href="/products" className="hover:text-gray-700 shrink-0">Products</Link>
              <ChevronRight className="h-4 w-4 mx-1 shrink-0" />
              {category && (
                <>
                  <Link 
                    href={`/categories/${category.slug || category._id}`}
                    className="hover:text-gray-700 shrink-0"
                  >
                    {category.name}
                  </Link>
                  <ChevronRight className="h-4 w-4 mx-1 shrink-0" />
                </>
              )}
              <Link 
                href={`/products/${product.slug || product._id}`}
                className="hover:text-gray-700 truncate"
              >
                {product.name}
              </Link>
              <ChevronRight className="h-4 w-4 mx-1 shrink-0" />
              <span className="text-gray-900 font-medium truncate">{seller?.businessName || 'Verified Seller'}</span>
            </nav>
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Media Gallery */}
          <div className="space-y-4">
            {/* Main Image/Video */}
            <div className="relative aspect-square bg-white rounded-xl overflow-hidden shadow-sm">
              {showVideo && hasVideos ? (
                <video
                  src={sellerListing.videos![0]}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : allMedia.length > 0 ? (
                <Image
                  src={allMedia[selectedImage] || '/placeholder.png'}
                  alt={product.name}
                  fill
                  className="object-contain"
                  sizes="(max-width: 768px) 100vw, 50vw"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <Package className="h-24 w-24" />
                </div>
              )}
              
              {/* Video Badge */}
              {hasVideos && !showVideo && (
                <button
                  onClick={() => setShowVideo(true)}
                  className="absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition shadow-lg"
                >
                  <Play className="h-4 w-4" />
                  Watch Demo
                </button>
              )}
              
              {showVideo && (
                <button
                  onClick={() => setShowVideo(false)}
                  className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            
            {/* Thumbnails */}
            <div className="flex gap-2 overflow-x-auto pb-2">
              {allMedia.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => { setSelectedImage(idx); setShowVideo(false); }}
                  className={`relative w-16 h-16 rounded-lg overflow-hidden border-2 flex-shrink-0 transition ${
                    selectedImage === idx && !showVideo ? 'border-blue-500' : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <Image src={img} alt="" fill className="object-cover" sizes="64px" />
                </button>
              ))}
              
              {hasVideos && sellerListing.videos!.map((video, idx) => (
                <button
                  key={`video-${idx}`}
                  onClick={() => setShowVideo(true)}
                  className={`relative w-16 h-16 rounded-lg overflow-hidden border-2 flex-shrink-0 bg-gray-900 ${
                    showVideo ? 'border-purple-500' : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <Video className="h-6 w-6 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                  <span className="absolute bottom-0.5 right-0.5 text-[9px] bg-purple-600 text-white px-1 rounded">
                    Video
                  </span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Right: Seller Info + Pricing */}
          <div className="space-y-6">
            {/* Product Title */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{product.name}</h1>
              {sellerListing.description && (
                <p className="text-gray-600 text-sm">{sellerListing.description}</p>
              )}
            </div>
            
            {/* Seller Card */}
            <div className="bg-white rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-gray-900">{seller?.businessName || 'Verified Seller'}</h2>
                    {seller?.badgeType === 'trusted' && (
                      <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                        <Shield className="h-3 w-3" /> Trusted
                      </span>
                    )}
                    {seller?.badgeType === 'choice' && (
                      <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                        <BadgeCheck className="h-3 w-3" /> Choice
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    {(seller?.city || seller?.state) && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5" />
                        {[seller?.city, seller?.state].filter(Boolean).join(', ')}
                      </span>
                    )}
                    {seller?.establishedYear && (
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        Est. {seller?.establishedYear}
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Rating */}
                <div className="text-right">
                  <StarRatingBadge rating={avgRating} totalReviews={totalReviews} />
                </div>
              </div>
              
              <div className="border-t pt-4 grid grid-cols-2 gap-4">
                <span className="text-xs text-gray-500 uppercase">Role</span>
                <span className="text-sm font-medium text-gray-900 capitalize">{sellerListing.sellerRole}</span>
                
                {seller?.gstNumber && (
                  <>
                    <span className="text-xs text-gray-500 uppercase">GST</span>
                    <span className="text-sm text-gray-700 font-mono">{seller?.gstNumber}</span>
                  </>
                )}
              </div>
            </div>
            
            {/* Pricing */}
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="flex items-baseline gap-2 mb-4">
                <span className="text-3xl font-bold text-green-600">
                  ₹{lowestPrice?.toLocaleString() || 'RFQ'}
                </span>
                {sellerListing.pricingTiers.length > 1 && (
                  <span className="text-sm text-gray-500">onwards</span>
                )}
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <Layers className="h-4 w-4 text-gray-400 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-gray-900">{sellerListing.moq}</div>
                  <div className="text-xs text-gray-500">Min Order</div>
                </div>
                
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <Package className="h-4 w-4 text-gray-400 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-gray-900">
                    {sellerListing.stock > 0 ? sellerListing.stock.toLocaleString() : 'MTO'}
                  </div>
                  <div className="text-xs text-gray-500">In Stock</div>
                </div>
                
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <Truck className="h-4 w-4 text-gray-400 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-gray-900">
                    {sellerListing.leadTime ? `${sellerListing.leadTime}d` : '-'}
                  </div>
                  <div className="text-xs text-gray-500">Lead Time</div>
                </div>
                
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <Clock className="h-4 w-4 text-gray-400 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-gray-900">
                    {sellerListing.maxCapacity?.toLocaleString() || '-'}
                  </div>
                  <div className="text-xs text-gray-500">Max Capacity</div>
                </div>
              </div>
              
              {/* Pricing Tiers */}
              {sellerListing.pricingTiers.length > 1 && (
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Bulk Pricing</h4>
                  <div className="space-y-1">
                    {sellerListing.pricingTiers.map((tier, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-gray-600">
                          {tier.minQty}+ units
                        </span>
                        <span className="font-medium text-gray-900">
                          ₹{tier.pricePerUnit.toLocaleString()}/unit
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Request Quote Button */}
              <button 
                className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2"
                onClick={() => user ? setShowInquiryModal(true) : router.push('/login')}
              >
                <Send className="h-4 w-4" />
                Request Quote
              </button>
            </div>
          </div>
        </div>
        
        {/* Specifications */}
        {sellerListing.searchableAttributes && Object.keys(sellerListing.searchableAttributes).length > 0 && (
          <div className="mt-8 bg-white rounded-xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Technical Specifications</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.entries(sellerListing.searchableAttributes).map(([key, value]) => (
                <div key={key} className="border-l-2 border-gray-200 pl-3">
                  <div className="text-xs text-gray-500 uppercase">
                    {sellerListing.attributeLabels?.[key] || key.replace(/_/g, ' ')}
                  </div>
                  <div className="text-sm font-medium text-gray-900">{String(value)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Reviews Section */}
        <div className="mt-8 bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Customer Reviews</h3>
              <div className="flex items-center gap-3 mt-1">
                <StarRating rating={avgRating} size="lg" showValue />
                <span className="text-sm text-gray-500">({totalReviews} reviews)</span>
              </div>
            </div>
            
            {canReview && !showReviewForm && (
              <button 
                onClick={() => setShowReviewForm(true)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Write Review
              </button>
            )}
          </div>
          
          {/* Review Form */}
          {showReviewForm && (
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <h4 className="font-medium text-gray-900 mb-4">Write Your Review</h4>
              
              <div className="mb-4">
                <label className="text-sm text-gray-600 mb-2 block">Rating</label>
                <StarRating 
                  rating={reviewRating} 
                  interactive 
                  onChange={setReviewRating}
                  size="lg"
                />
              </div>
              
              <div className="mb-4">
                <label className="text-sm text-gray-600 mb-2 block">Review (optional)</label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Share your experience with this seller..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div className="flex gap-3">
                <button 
                  onClick={handleSubmitReview}
                  disabled={submittingReview}
                  className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submittingReview ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                  )}
                  Submit Review
                </button>
                <button 
                  onClick={() => setShowReviewForm(false)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          
          {/* Success Message */}
          {reviewSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span className="text-green-800">Thank you! Your review has been submitted.</span>
            </div>
          )}
          
          {/* Reviews List */}
          {reviews.length > 0 ? (
            <div className="space-y-4">
              {reviews.map((review) => (
                <div key={review._id} className="border-b border-gray-100 pb-4 last:border-0">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-600">
                        {review.buyerName.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{review.buyerName}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(review.createdAt).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric'
                          })}
                        </div>
                      </div>
                    </div>
                    <StarRating rating={review.rating} size="sm" />
                  </div>
                  {review.reviewText && (
                    <p className="text-gray-600 text-sm ml-11">{review.reviewText}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p>No reviews yet. Be the first to review!</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Inquiry Modal */}
      {showInquiryModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Request Quote</h3>
              <button onClick={() => setShowInquiryModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Quantity</label>
                <input
                  type="number"
                  value={inquiryQuantity}
                  onChange={(e) => setInquiryQuantity(e.target.value)}
                  placeholder={`Min ${sellerListing.moq} units`}
                  min={sellerListing.moq}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Message</label>
                <textarea
                  value={inquiryMessage}
                  onChange={(e) => setInquiryMessage(e.target.value)}
                  placeholder="Tell the seller about your requirements..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <button 
                className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 disabled:opacity-50"
                onClick={handleSubmitInquiry}
                disabled={submittingInquiry}
              >
                {submittingInquiry ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Send Inquiry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
