'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  MapPin, 
  Package, 
  Clock, 
  BadgeCheck, 
  Send,
  CheckSquare,
  Square,
  Building2,
  TrendingDown,
  Sparkles,
  Star,
  Eye
} from 'lucide-react';
import type { EnterpriseProductSeller, PricingTier } from '@/lib/api';

interface SellerCardProps {
  seller: EnterpriseProductSeller;
  productSlug?: string;  // Product slug for detail page link
  isCompareSelected: boolean;
  onCompareToggle: (sellerId: string) => void;
  onInquiry: (seller: EnterpriseProductSeller) => void;
  compareDisabled?: boolean;
  showRankingScore?: boolean;
}

// Seller role badges
const ROLE_CONFIG: Record<string, { label: string; color: string }> = {
  manufacturer: { label: 'Manufacturer', color: 'bg-indigo-100 text-indigo-700' },
  dealer: { label: 'Dealer', color: 'bg-blue-100 text-blue-700' },
  distributor: { label: 'Distributor', color: 'bg-orange-100 text-orange-700' },
  wholesaler: { label: 'Wholesaler', color: 'bg-purple-100 text-purple-700' },
  retailer: { label: 'Retailer', color: 'bg-pink-100 text-pink-700' },
};

// Get ranking badge config based on score
const getRankingBadge = (score: number) => {
  if (score >= 80) return { label: 'Top Pick', color: 'bg-green-100 text-green-700 border-green-200' };
  if (score >= 60) return { label: 'Great Match', color: 'bg-blue-100 text-blue-700 border-blue-200' };
  if (score >= 40) return { label: 'Good Match', color: 'bg-gray-100 text-gray-600 border-gray-200' };
  return null;
};

export default function SellerCard({ 
  seller, 
  productSlug,
  isCompareSelected, 
  onCompareToggle, 
  onInquiry,
  compareDisabled,
  showRankingScore = false
}: SellerCardProps) {
  const [showAllSpecs, setShowAllSpecs] = useState(false);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  const roleConfig = ROLE_CONFIG[seller.sellerRole?.toLowerCase()] || ROLE_CONFIG.dealer;
  
  // Get top specifications for the strip
  const specEntries = Object.entries(seller.searchableAttributes || {});
  const topSpecs = specEntries.slice(0, 3);
  const remainingSpecs = specEntries.slice(3);

  // Format spec value with label
  const formatSpecValue = (key: string, value: string | number) => {
    const label = seller.attributeLabels?.[key];
    const unit = typeof value === 'number' ? '' : '';
    return `${value}${unit}`;
  };

  return (
    <div 
      className={`bg-white rounded-lg border transition-all ${
        isCompareSelected 
          ? 'border-blue-500 ring-2 ring-blue-100' 
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
      data-testid={`seller-card-${seller.listingId}`}
    >
      {/* Top Spec Strip */}
      {topSpecs.length > 0 && (
        <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-sm font-medium text-gray-700">
              {topSpecs.map(([key, value], idx) => (
                <span key={key} className="flex items-center gap-1.5">
                  {idx > 0 && <span className="text-gray-300">|</span>}
                  <span className="text-gray-500 text-xs uppercase">{seller.attributeLabels?.[key] || key}:</span>
                  <span className="text-gray-900">{formatSpecValue(key, value)}</span>
                </span>
              ))}
            </div>
            {/* Ranking Badge */}
            {showRankingScore && seller.rankingScore !== undefined && getRankingBadge(seller.rankingScore) && (
              <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border ${getRankingBadge(seller.rankingScore)!.color}`}>
                <Sparkles className="h-3 w-3" />
                {getRankingBadge(seller.rankingScore)!.label}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="p-4">
        {/* Header Row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            {/* Seller Name with Verified Badge */}
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900 truncate" data-testid="seller-name">
                {seller.companyName}
              </h3>
              <BadgeCheck className="h-4 w-4 text-blue-500 flex-shrink-0" />
            </div>
            {/* Location: City, State */}
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-sm text-gray-500">
              <span className="flex items-center gap-1" data-testid="seller-location">
                <MapPin className="h-3.5 w-3.5" />
                {seller.city && seller.state 
                  ? `${seller.city}, ${seller.state}`
                  : seller.city || seller.state || seller.location || 'India'}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${roleConfig.color}`}>
                {roleConfig.label}
              </span>
            </div>
          </div>

          {/* Compare Checkbox */}
          <button
            onClick={() => onCompareToggle(seller.listingId)}
            disabled={compareDisabled && !isCompareSelected}
            className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-colors ${
              isCompareSelected 
                ? 'bg-blue-100 text-blue-700' 
                : compareDisabled 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            data-testid={`compare-toggle-${seller.listingId}`}
          >
            {isCompareSelected ? (
              <CheckSquare className="h-3.5 w-3.5" />
            ) : (
              <Square className="h-3.5 w-3.5" />
            )}
            Compare
          </button>
        </div>

        {/* Rating Display */}
        {(seller.totalReviews !== undefined && seller.totalReviews > 0) && (
          <div className="flex items-center gap-2 mb-3" data-testid={`seller-rating-${seller.listingId}`}>
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
              <span className="font-semibold text-gray-900">{seller.avgRating?.toFixed(1) || '0.0'}</span>
            </div>
            <span className="text-sm text-gray-500">({seller.totalReviews} reviews)</span>
          </div>
        )}

        {/* Price Section */}
        <div className="bg-gray-50 rounded-lg p-3 mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Starting Price</span>
            {seller.lowestPrice ? (
              <span className="text-xl font-bold text-gray-900">
                {formatPrice(seller.lowestPrice)}
                <span className="text-sm font-normal text-gray-500">/unit</span>
              </span>
            ) : (
              <span className="text-sm text-gray-500">Request Quote</span>
            )}
          </div>

          {/* Price Tiers */}
          {seller.pricingTiers && seller.pricingTiers.length > 1 && (
            <div className="border-t border-gray-200 mt-2 pt-2">
              <div className="flex items-center gap-1 text-xs text-gray-500 mb-1.5">
                <TrendingDown className="h-3 w-3" />
                Bulk Pricing Available
              </div>
              <div className="space-y-1">
                {seller.pricingTiers.slice(0, 3).map((tier: PricingTier, idx: number) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {tier.minQty}{tier.maxQty ? `-${tier.maxQty}` : '+'} units
                    </span>
                    <span className="font-medium text-gray-900">
                      {formatPrice(tier.pricePerUnit)}/unit
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Quick Info Row */}
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 mb-4">
          <span className="flex items-center gap-1.5">
            <Package className="h-4 w-4 text-gray-400" />
            MOQ: <span className="font-medium text-gray-900">{seller.moq}</span>
          </span>
          
          {seller.stock > 0 && (
            <span className="flex items-center gap-1.5">
              <Building2 className="h-4 w-4 text-gray-400" />
              Stock: <span className="font-medium text-gray-900">{seller.stock}</span>
            </span>
          )}
          
          {seller.leadTimeDays && (
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-gray-400" />
              Lead: <span className="font-medium text-gray-900">{seller.leadTimeDays} days</span>
            </span>
          )}
        </div>

        {/* Extended Specs (Collapsible) */}
        {remainingSpecs.length > 0 && (
          <div className="mb-4">
            <button
              onClick={() => setShowAllSpecs(!showAllSpecs)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {showAllSpecs ? 'Hide' : 'Show'} {remainingSpecs.length} more specs
            </button>
            
            {showAllSpecs && (
              <div className="mt-2 grid grid-cols-2 gap-2">
                {remainingSpecs.map(([key, value]) => (
                  <div key={key} className="text-sm">
                    <span className="text-gray-500">{seller.attributeLabels?.[key] || key}: </span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Stock Status Badge */}
        <div className="flex items-center justify-between">
          <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${
            seller.stockStatus === 'in_stock' 
              ? 'bg-green-100 text-green-700' 
              : seller.stockStatus === 'limited'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-gray-100 text-gray-600'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              seller.stockStatus === 'in_stock' 
                ? 'bg-green-500' 
                : seller.stockStatus === 'limited'
                  ? 'bg-yellow-500'
                  : 'bg-gray-400'
            }`} />
            {seller.stockStatus === 'in_stock' 
              ? 'In Stock' 
              : seller.stockStatus === 'limited' 
                ? 'Limited Stock' 
                : 'Out of Stock'}
          </span>
        </div>

        {/* RFQ Button */}
        <button
          onClick={() => onInquiry(seller)}
          className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors"
          data-testid={`rfq-btn-${seller.listingId}`}
        >
          <Send className="h-4 w-4" />
          Request Quote
        </button>

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
