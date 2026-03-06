'use client';
import { 
  Building2, 
  BadgeCheck, 
  Package, 
  Clock, 
  Truck, 
  MessageSquare,
  ExternalLink,
  Award,
  Star
} from 'lucide-react';

interface Seller {
  _id: string;
  sellerId: string;
  sellerName?: string;
  businessName?: string;
  price?: number;
  startingPrice?: number;
  rate?: number;
  rate_unit?: string;
  moq?: number;
  leadTime?: number;
  stock?: number;
  isVerified?: boolean;
  rating?: number;
}

interface StandardSellerCardProps {
  seller: Seller;
  rank?: number;
  onRequestQuote: (seller: Seller) => void;
  onViewDetails?: (seller: Seller) => void;


export default function StandardSellerCard({
  seller,

  rank,
  onRequestQuote,
  onViewDetails
}: StandardSellerCardProps) {
  const displayPrice = seller.price || seller.startingPrice || seller.rate || 0;
  
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {rank === 1 && (
              <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full flex items-center gap-1">
                <Award className="h-3 w-3" />
                Best Price
              </span>
            )}
            <div>
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-gray-400" />
                <span className="font-semibold text-gray-900">
                  {seller.businessName || seller.sellerName || 'Seller'}
                </span>
                {seller.isVerified && (
                  <BadgeCheck className="h-4 w-4 text-blue-500" />
                )}
              </div>
              {seller.rating && (
                <div className="flex items-center gap-1 mt-1">
                  <Star className="h-3.5 w-3.5 text-amber-400 fill-amber-400" />
                  <span className="text-xs text-gray-600">{seller.rating.toFixed(1)}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Price */}
          <div className="text-right">
            <p className="text-xs text-gray-500">Starting from</p>
            <p className="text-xl font-bold text-gray-900">{formatPrice(displayPrice)}</p>
            <p className="text-xs text-gray-500">per {seller.rate_unit || 'piece'}</p>
          </div>
        </div>
      </div>

      {/* Seller Details */}
      <div className="px-4 py-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Package className="h-4 w-4" />
            </div>
            <p className="text-xs text-gray-500">MOQ</p>
            <p className="text-sm font-semibold text-gray-900">{seller.moq || 1} pcs</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Truck className="h-4 w-4" />
            </div>
            <p className="text-xs text-gray-500">Lead Time</p>
            <p className="text-sm font-semibold text-gray-900">{seller.leadTime || '-'} days</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Clock className="h-4 w-4" />
            </div>
            <p className="text-xs text-gray-500">Stock</p>
            <p className="text-sm font-semibold text-gray-900">{seller.stock || 'In Stock'}</p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex gap-2">
        <button
          onClick={() => onRequestQuote(seller)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium text-sm"
          data-testid="request-quote-btn"
        >
          <MessageSquare className="h-4 w-4" />
          Request Quote
        </button>
        {onViewDetails && (
          <button
            onClick={() => onViewDetails(seller)}
            className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors text-sm"
            data-testid="view-details-btn"
          >
            <ExternalLink className="h-4 w-4" />
          </button>

        )}
      </div>
    </div>
  );
}


// Export the Seller type for use in parent components
export type { StandardSellerCardSeller };
