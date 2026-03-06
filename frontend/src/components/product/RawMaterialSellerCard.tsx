'use client';

import { useState } from 'react';
import { 
  Building2, 
  BadgeCheck, 
  Package, 
  Clock, 
  Truck, 
  Scale,
  MessageSquare,
  ExternalLink,
  Award
} from 'lucide-react';

interface CalculationResult {
  calculator_name: string;
  material_name?: string;
  output_unit: string;
  output_label: string;
  value_per_piece: number;
  total_value: number;
  quantity: number;
  field_summary: Record<string, string>;
}

interface Seller {
  _id: string;
  sellerId: string;
  sellerName?: string;
  businessName?: string;
  rate: number;
  rate_unit?: string;
  moq?: number;
  leadTime?: number;
  stock?: number;
  isVerified?: boolean;
  rating?: number;
}

interface RawMaterialSellerCardProps {
  seller: Seller;
  calculationResult: CalculationResult;
  rank?: number;
  onRequestQuote: (seller: Seller, calculatedPrice: number) => void;
  onViewDetails?: (seller: Seller) => void;
}

export default function RawMaterialSellerCard({
  seller,
  calculationResult,
  rank,
  onRequestQuote,
  onViewDetails
}: RawMaterialSellerCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Calculate estimated price based on weight and rate
  const estimatedPrice = calculationResult.total_value * seller.rate;
  const pricePerPiece = calculationResult.value_per_piece * seller.rate;
  
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(price);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* Header with rank badge */}
      <div className="bg-gradient-to-r from-gray-50 to-white px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {rank === 1 && (
              <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full flex items-center gap-1">
                <Award className="h-3 w-3" />
                Best Price
              </span>
            )}
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-gray-400" />
              <span className="font-semibold text-gray-900">
                {seller.businessName || seller.sellerName || 'Seller'}
              </span>
              {seller.isVerified && (
                <BadgeCheck className="h-4 w-4 text-blue-500" />
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Rate</p>
            <p className="text-sm font-bold text-gray-900">
              {formatPrice(seller.rate)}/{seller.rate_unit || 'kg'}

            </p>
          </div>
        </div>
      </div>

      {/* Calculation Summary */}
      <div className="px-4 py-4 bg-gradient-to-br from-emerald-50 to-green-50 border-b border-emerald-100">
        <div className="flex items-center gap-2 mb-3">
          <Scale className="h-4 w-4 text-emerald-600" />
          <span className="text-sm font-medium text-emerald-800">Weight Calculation</span>
        </div>
        
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-white rounded-lg p-2 shadow-sm">
            <p className="text-xs text-gray-500">Per Piece</p>
            <p className="text-sm font-bold text-gray-900">
              {calculationResult.value_per_piece.toFixed(2)} {calculationResult.output_unit}
            </p>
          </div>
          <div className="bg-white rounded-lg p-2 shadow-sm">
            <p className="text-xs text-gray-500">Total ({calculationResult.quantity} pcs)</p>
            <p className="text-sm font-bold text-gray-900">
              {calculationResult.total_value.toFixed(2)} {calculationResult.output_unit}
            </p>
          </div>
          <div className="bg-emerald-600 rounded-lg p-2 text-white">
            <p className="text-xs text-emerald-100">Estimated Price</p>
            <p className="text-sm font-bold">{formatPrice(estimatedPrice)}</p>
          </div>
        </div>
        
        {/* Price breakdown */}
        <p className="text-xs text-emerald-700 mt-2 text-center">
          {calculationResult.total_value.toFixed(2)} {calculationResult.output_unit} × {formatPrice(seller.rate)}/{seller.rate_unit || 'kg'}

        </p>
      </div>

      {/* Seller Details */}
      <div className="px-4 py-3">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Package className="h-3.5 w-3.5" />
              <span className="text-xs">MOQ</span>
            </div>
            <p className="text-sm font-semibold text-gray-900">{seller.moq || 1}</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Truck className="h-3.5 w-3.5" />
              <span className="text-xs">Lead Time</span>
            </div>
            <p className="text-sm font-semibold text-gray-900">{seller.leadTime || '-'} days</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
              <Clock className="h-3.5 w-3.5" />
              <span className="text-xs">Stock</span>
            </div>
            <p className="text-sm font-semibold text-gray-900">{seller.stock || '-'}</p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex gap-2">
        <button
          onClick={() => onRequestQuote(seller, estimatedPrice)}
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
