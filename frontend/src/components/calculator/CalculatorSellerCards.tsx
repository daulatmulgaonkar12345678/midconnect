'use client';

import { useState } from 'react';
import {
  MapPin,
  Send,
  Eye,
  Award,
  CheckCircle,
  Package,
  Clock,
  Building2,
  Star
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface CalculationResult {
  calculator_name: string;
  material_name?: string;
  calculated_value: number;
  output_unit: string;
  output_label: string;
  value_per_piece: number;
  total_value: number;
  quantity: number;
  field_summary: Record<string, string>;
}

interface SellerListing {
  _id: string;
  sellerId: string;
  sellerName: string;
  companyName?: string;
  city?: string;
  state?: string;
  badgeType?: string;
  rating?: number;
  reviewCount?: number;
  rate_per_unit: number;
  rate_unit: string;
  minOrderQty?: number;
  leadTime?: string;
  stock?: number;
  materialType?: string;
}

interface CalculatorSellerCardsProps {
  calculationResult: CalculationResult | null;
  sellers: SellerListing[];
  onRequestQuote: (seller: SellerListing, calculatedPrice: number) => void;
  onViewDetails: (seller: SellerListing) => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const formatPrice = (price: number): string => {
  return `₹${price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const getBadgeColor = (badgeType?: string) => {
  switch (badgeType?.toLowerCase()) {
    case 'manufacturer':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'distributor':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'wholesaler':
      return 'bg-orange-100 text-orange-700 border-orange-200';
    case 'verified':
      return 'bg-green-100 text-green-700 border-green-200';
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200';
  }
};

// ============================================================================
// CALCULATION SUMMARY COMPONENT
// ============================================================================

function CalculationSummary({ result }: { result: CalculationResult }) {
  return (
    <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-2xl border border-emerald-200 p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-emerald-100 rounded-lg">
          <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-emerald-800">Calculation Summary</h3>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white/60 backdrop-blur rounded-xl p-4 text-center">
          <p className="text-sm text-emerald-600 mb-1">Calculator</p>
          <p className="font-bold text-emerald-800">{result.calculator_name.replace(' Calculator', '')}</p>
        </div>
        
        {result.material_name && (
          <div className="bg-white/60 backdrop-blur rounded-xl p-4 text-center">
            <p className="text-sm text-emerald-600 mb-1">Material</p>
            <p className="font-bold text-emerald-800">{result.material_name}</p>
          </div>
        )}
        
        <div className="bg-emerald-100 rounded-xl p-4 text-center border-2 border-emerald-300">
          <p className="text-sm text-emerald-600 mb-1">Total {result.output_label}</p>
          <p className="font-bold text-emerald-700 text-2xl">
            {result.total_value.toFixed(2)} {result.output_unit}
          </p>
        </div>
      </div>

      {/* Dimensions used */}
      <div className="mt-4 pt-4 border-t border-emerald-200">
        <p className="text-sm text-emerald-600 mb-2">Dimensions:</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(result.field_summary).map(([key, value]) => (
            <span key={key} className="px-3 py-1 bg-white/80 text-emerald-700 text-sm rounded-full border border-emerald-200">
              {key}: {value}
            </span>
          ))}
          {result.quantity > 1 && (
            <span className="px-3 py-1 bg-emerald-200 text-emerald-800 text-sm rounded-full font-medium">
              × {result.quantity} pcs
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SELLER CARD COMPONENT
// ============================================================================

function SellerCard({
  seller,
  calculatedWeight,
  outputUnit,
  onRequestQuote,
  onViewDetails
}: {
  seller: SellerListing;
  calculatedWeight: number;
  outputUnit: string;
  onRequestQuote: (calculatedPrice: number) => void;
  onViewDetails: () => void;
}) {
  const finalPrice = calculatedWeight * seller.rate_per_unit;
  const displayName = seller.companyName || seller.sellerName || 'Seller';
  const location = [seller.city, seller.state].filter(Boolean).join(', ');

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow">
      {/* Dark Header with Specs */}
      <div className="bg-slate-800 px-4 py-3">
        <div className="flex items-center gap-3 text-slate-300 text-sm">
          {seller.materialType && (
            <>
              <span>{seller.materialType}</span>
              <span className="text-slate-500">|</span>
            </>
          )}
          <span>{outputUnit}</span>
          <span className="text-slate-500">|</span>
          <span>{calculatedWeight.toFixed(2)} {outputUnit}</span>
        </div>
      </div>

      {/* Seller Info */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-bold text-lg text-gray-900">{displayName}</h4>
              {seller.badgeType && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getBadgeColor(seller.badgeType)}`}>
                  <CheckCircle className="w-3 h-3 inline mr-1" />
                  {seller.badgeType}
                </span>
              )}
            </div>
            {location && (
              <p className="text-gray-500 text-sm flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {location}
              </p>
            )}
          </div>
          {seller.rating && (
            <div className="flex items-center gap-1 text-amber-500">
              <Star className="w-4 h-4 fill-current" />
              <span className="font-medium text-sm">{seller.rating}</span>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-2 mb-5">
          <div className="bg-emerald-50 rounded-xl p-3 text-center border border-emerald-100">
            <p className="text-xs text-emerald-600 uppercase font-medium mb-1">Rate</p>
            <p className="font-bold text-emerald-700 text-lg">₹{seller.rate_per_unit}</p>
            <p className="text-xs text-emerald-500">/{seller.rate_unit}</p>
          </div>
          
          <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
            <p className="text-xs text-gray-500 uppercase font-medium mb-1">MOQ</p>
            <p className="font-bold text-gray-800 text-lg">{seller.minOrderQty || 1}</p>
          </div>
          
          <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
            <p className="text-xs text-gray-500 uppercase font-medium mb-1">Lead Time</p>
            <p className="font-bold text-gray-800 text-lg">{seller.leadTime || '1d'}</p>
          </div>
          
          <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
            <p className="text-xs text-gray-500 uppercase font-medium mb-1">Stock</p>
            <p className="font-bold text-gray-800 text-lg">{seller.stock || '∞'}</p>
          </div>
        </div>

        {/* Calculated Price Highlight */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 mb-5 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Estimated Total Price</p>
              <p className="text-xs text-blue-500">
                {calculatedWeight.toFixed(2)} {outputUnit} × ₹{seller.rate_per_unit}/{seller.rate_unit}
              </p>
            </div>
            <p className="text-2xl font-bold text-blue-700">{formatPrice(finalPrice)}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2">
          <button
            onClick={() => onRequestQuote(finalPrice)}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors"
          >
            <Send className="w-4 h-4" />
            Request Quote
          </button>
          
          <button
            onClick={onViewDetails}
            className="w-full py-3 px-4 bg-white hover:bg-gray-50 text-gray-700 font-medium rounded-xl border border-gray-200 flex items-center justify-center gap-2 transition-colors"
          >
            <Eye className="w-4 h-4" />
            View Details & Reviews
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function CalculatorSellerCards({
  calculationResult,
  sellers,
  onRequestQuote,
  onViewDetails
}: CalculatorSellerCardsProps) {
  if (!calculationResult || calculationResult.total_value <= 0) {
    return null;
  }

  // Sort sellers by final price (lowest first)
  const sortedSellers = [...sellers]
    .filter(s => s.rate_per_unit > 0)
    .sort((a, b) => {
      const priceA = calculationResult.total_value * a.rate_per_unit;
      const priceB = calculationResult.total_value * b.rate_per_unit;
      return priceA - priceB;
    });

  return (
    <div className="space-y-6">
      {/* Calculation Summary */}
      <CalculationSummary result={calculationResult} />

      {/* Sellers Section */}
      {sortedSellers.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Compare Sellers ({sortedSellers.length})
            </h3>
            <span className="text-sm text-gray-500">
              Sorted by lowest price
            </span>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedSellers.map((seller, index) => (
              <div key={seller._id} className="relative">
                {index === 0 && (
                  <div className="absolute -top-2 -right-2 z-10">
                    <span className="px-2 py-1 bg-green-500 text-white text-xs font-bold rounded-full shadow-lg">
                      Best Price
                    </span>
                  </div>
                )}
                <SellerCard
                  seller={seller}
                  calculatedWeight={calculationResult.total_value}
                  outputUnit={calculationResult.output_unit}
                  onRequestQuote={(price) => onRequestQuote(seller, price)}
                  onViewDetails={() => onViewDetails(seller)}
                />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-xl p-8 text-center">
          <Building2 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-600 font-medium">No sellers with pricing available</p>
          <p className="text-gray-500 text-sm mt-1">
            Contact sellers to get quotes for this material
          </p>
        </div>
      )}
    </div>
  );
}
