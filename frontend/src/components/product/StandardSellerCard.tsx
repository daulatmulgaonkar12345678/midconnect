'use client';

import { 
  Building2, 
  BadgeCheck, 
  Send,
  Eye,
  Award,
  Star,
  Shield,
  MapPin,
  Video,
  Play,
  Package,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';
import { EnterpriseProductSeller } from '@/lib/api';

// UdyogConnect Seller Badge (Choice/Trusted)
function UdyogConnectBadge({ badgeType }: { badgeType?: string }) {
  if (!badgeType || badgeType === 'none') return null;
  
  if (badgeType === 'choice') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded border border-yellow-300">
        <Star className="h-3 w-3 fill-yellow-500 text-yellow-500" />
        UdyogConnect Choice
      </span>
    );
  }
  
  if (badgeType === 'trusted') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded border border-green-300">
        <Shield className="h-3 w-3 fill-green-500 text-green-500" />
        UdyogConnect Trusted
      </span>
    );
  }
  
  return null;
}

function SellerRoleBadge({ role }: { role: string }) {
  const roleConfig: Record<string, { bg: string; text: string; label: string }> = {
    manufacturer: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Manufacturer' },
    distributor: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Distributor' },
    dealer: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Dealer' },
    trader: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Trader' }
  };
  
  const config = roleConfig[role] || roleConfig.dealer;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 ${config.bg} ${config.text} text-xs font-medium rounded`}>
      <BadgeCheck className="h-3 w-3" />
      {config.label}
    </span>
  );
}

function SpecStrip({ attributes, labels }: { 
  attributes: Record<string, string | number>; 
  labels: Record<string, string>;
}) {
  const entries = Object.entries(attributes).slice(0, 4);
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 text-sm" data-testid="spec-strip">
      {entries.map(([key, value], idx) => (
        <span key={key} className="inline-flex items-center">
          <span className="font-semibold text-white">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          <span className="text-slate-300 ml-1">
            {(labels?.[key] || key || '').split('(')[1]?.replace(')', '') || ''}
          </span>
          {idx < entries.length - 1 && (
            <span className="mx-2 text-slate-500">|</span>
          )}
        </span>
      ))}
    </div>
  );
}

interface StandardSellerCardProps {
  seller: EnterpriseProductSeller;
  productSlug?: string;
  rank?: number;
  onRequestQuote: (seller: EnterpriseProductSeller) => void;
  onViewDetails?: (seller: EnterpriseProductSeller) => void;
}

export default function StandardSellerCard({
  seller,
  productSlug,
  rank,
  onRequestQuote,
  onViewDetails
}: StandardSellerCardProps) {
  const displayPrice = seller.lowestPrice || (seller.pricingTiers?.[0]?.pricePerUnit) || 0;
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  // Handle image navigation
  const hasImages = seller.images && seller.images.length > 0;
  const totalImages = seller.images?.length || 0;

  const nextImage = () => {
    if (hasImages) {
      setCurrentImageIndex((prev) => (prev + 1) % totalImages);
    }
  };

  const prevImage = () => {
    if (hasImages) {
      setCurrentImageIndex((prev) => (prev - 1 + totalImages) % totalImages);
    }
  };

  return (
    <div 
      className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden"
      data-testid={`standard-seller-card-${seller.listingId}`}
    >
      {/* Spec Strip Header */}
      {Object.keys(seller.searchableAttributes || {}).length > 0 && (
        <div className="bg-slate-800 text-white px-4 py-3">
          <SpecStrip 
            attributes={seller.searchableAttributes} 
            labels={seller.attributeLabels || {}} 
          />
        </div>
      )}

      {/* Product Images Section */}
      {hasImages && (
        <div className="relative bg-gray-100" data-testid="seller-product-images">
          {/* Main Image */}
          <div className="relative aspect-[16/9] md:aspect-[21/9] overflow-hidden">
            <Image
              src={seller.images[currentImageIndex]}
              alt={`Product image ${currentImageIndex + 1}`}
              fill
              className="object-contain"
              sizes="(max-width: 768px) 100vw, 50vw"
            />
            
            {/* Image Navigation */}
            {totalImages > 1 && (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); prevImage(); }}
                  className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-white/90 rounded-full flex items-center justify-center shadow-md hover:bg-white transition"
                  aria-label="Previous image"
                >
                  <ChevronLeft className="h-5 w-5 text-gray-700" />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); nextImage(); }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-white/90 rounded-full flex items-center justify-center shadow-md hover:bg-white transition"
                  aria-label="Next image"
                >
                  <ChevronRight className="h-5 w-5 text-gray-700" />
                </button>
                
                {/* Image Counter */}
                <div className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
                  {currentImageIndex + 1} / {totalImages}
                </div>
              </>
            )}
          </div>
          
          {/* Thumbnail Strip (for multiple images) */}
          {totalImages > 1 && (
            <div className="flex gap-1 p-2 bg-gray-50 overflow-x-auto">
              {seller.images.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentImageIndex(idx)}
                  className={`flex-shrink-0 w-12 h-12 rounded border-2 overflow-hidden transition ${
                    idx === currentImageIndex ? 'border-blue-500' : 'border-transparent hover:border-gray-300'
                  }`}
                >
                  <Image
                    src={img}
                    alt={`Thumbnail ${idx + 1}`}
                    width={48}
                    height={48}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="p-4">
        {/* UdyogConnect Badge - Priority display above seller info */}
        {seller.badgeType && seller.badgeType !== 'none' && (
          <div className="mb-3">
            <UdyogConnectBadge badgeType={seller.badgeType} />
          </div>
        )}
        
        {/* Best Price Badge */}
        {rank === 1 && (
          <div className="mb-3">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full">
              <Award className="h-3 w-3" />
              Best Price
            </span>
          </div>
        )}
        
        {/* Seller Info Row */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="h-4 w-4 text-gray-400" />
              {seller.sellerSlug ? (
                <Link 
                  href={`/seller-catalog/${seller.sellerSlug}`}
                  className="font-semibold text-gray-900 hover:text-blue-600 transition-colors relative group"
                  data-testid="seller-name"
                >
                  {seller.companyName || 'Verified Seller'}
                  <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-blue-600 group-hover:w-full transition-all duration-300" />
                </Link>
              ) : (
                <span className="font-semibold text-gray-900" data-testid="seller-name">
                  {seller.companyName || 'Verified Seller'}
                </span>
              )}
              <SellerRoleBadge role={seller.sellerRole} />
            </div>
            <div className="flex items-center gap-1 text-sm text-gray-500" data-testid="seller-location">
              <MapPin className="h-4 w-4" />
              {seller.city && seller.state 
                ? `${seller.city}, ${seller.state}`
                : seller.location || 'India'}
            </div>
          </div>
        </div>

        {/* Rating Display */}
        {seller.totalReviews !== undefined && seller.totalReviews > 0 && (
          <div className="flex items-center gap-2 mb-3" data-testid={`seller-rating-${seller.listingId}`}>
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
              <span className="font-semibold text-gray-900">{seller.avgRating?.toFixed(1) || '0.0'}</span>
            </div>
            <span className="text-sm text-gray-500">({seller.totalReviews} reviews)</span>
          </div>
        )}

        {/* Price & Stock Grid - per piece unit */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <div className="text-xs text-green-600 uppercase font-medium">Starting</div>
            <div className="text-xl font-bold text-green-700">
              {displayPrice > 0 ? formatPrice(displayPrice) : 'RFQ'}
            </div>
            <div className="text-xs text-green-600">per piece</div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">MOQ</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.moq?.toLocaleString() || 1}
            </div>
            <div className="text-xs text-slate-500">pcs</div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">Lead Time</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.leadTimeDays ? `${seller.leadTimeDays}d` : '-'}
            </div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">Stock</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.stock > 0 ? seller.stock.toLocaleString() : 'MTO'}
            </div>
          </div>
        </div>

        {/* Product Demo Videos */}
        {seller.videos && seller.videos.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Video className="h-4 w-4 text-purple-600" />
              <span className="text-xs text-gray-500 uppercase font-medium">Product Demo</span>
              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                {seller.videos.length} video{seller.videos.length > 1 ? 's' : ''}
              </span>
            </div>
            <div className={`grid ${seller.videos.length > 1 ? 'grid-cols-2' : 'grid-cols-1'} gap-2`}>
              {seller.videos.map((videoUrl, idx) => (
                <div key={idx} className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden">
                  <video
                    src={videoUrl}
                    className="w-full h-full object-contain"
                    controls
                    preload="metadata"
                    poster=""
                    data-testid={`seller-video-${seller.listingId}-${idx}`}
                  />
                  {idx === 0 && seller.videos && seller.videos.length > 1 && (
                    <span className="absolute top-2 left-2 px-2 py-0.5 bg-purple-600 text-white text-xs rounded flex items-center gap-1">
                      <Play className="h-3 w-3" /> Main
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pricing Tiers */}
        {seller.pricingTiers && seller.pricingTiers.length > 1 && (
          <div className="mb-4">
            <div className="text-xs text-gray-500 uppercase font-medium mb-2">Volume Pricing</div>
            <div className="flex flex-wrap gap-2">
              {seller.pricingTiers.slice(0, 3).map((tier, idx) => (
                <span key={idx} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                  {tier.minQty}+ @ {formatPrice(tier.pricePerUnit)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => onRequestQuote(seller)}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            data-testid={`rfq-btn-${seller.listingId}`}
          >
            <Send className="h-4 w-4" />
            Request Quote
          </button>
        </div>
        
        {/* View Details Link */}
        {productSlug && (
          <Link
            href={`/products/${productSlug}/seller/${seller.listingId}`}
            className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
            data-testid={`view-details-btn-${seller.listingId}`}
          >
            <Eye className="h-4 w-4" />
            View Details & Reviews
          </Link>
        )}
      </div>
    </div>
  );
}

// Export the type for use in parent components
export type { StandardSellerCardProps };
