'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  MapPin,
  Package,
  Clock,
  Send,
  BadgeCheck,
  Star,
  Loader2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

export interface RawMaterialSeller {
  listingId: string;
  sellerId: string;
  sellerName: string;
  sellerBadge?: string;
  rate_per_kg: number;
  material_supported?: string;
  moq?: number;
  stock?: number;
  leadTime?: number;
  location?: string;
  images?: string[];
}

export interface SellerPriceCardProps {
  seller: RawMaterialSeller;
  totalWeight: number;
  onInquiry?: (seller: RawMaterialSeller, calculatedPrice: number) => void;
}

/**
 * Individual seller card showing rate and calculated price
 */
export function SellerPriceCard({ seller, totalWeight, onInquiry }: SellerPriceCardProps) {
  const calculatedPrice = totalWeight * seller.rate_per_kg;
  const router = useRouter();

  const handleInquiry = () => {
    if (onInquiry) {
      onInquiry(seller, calculatedPrice);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-gray-900">{seller.sellerName}</h4>
            {seller.sellerBadge === 'trusted' && (
              <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                <BadgeCheck className="h-3 w-3" /> Trusted
              </span>
            )}
            {seller.sellerBadge === 'choice' && (
              <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                <Star className="h-3 w-3" /> Choice
              </span>
            )}
          </div>
          {seller.location && (
            <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
              <MapPin className="h-3.5 w-3.5" />
              {seller.location}
            </p>
          )}
        </div>
        
        {seller.images && seller.images[0] && (
          <img
            src={seller.images[0]}
            alt={seller.sellerName}
            className="w-12 h-12 rounded-lg object-cover"
          />
        )}
      </div>

      {/* Pricing */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-xs text-gray-500 uppercase">Rate</p>
          <p className="text-lg font-bold text-gray-900">₹{seller.rate_per_kg}/kg</p>
        </div>
        <div className="bg-blue-50 p-3 rounded-lg">
          <p className="text-xs text-blue-600 uppercase">Your Price</p>
          <p className="text-lg font-bold text-blue-600">
            ₹{calculatedPrice >= 1000 
              ? calculatedPrice.toLocaleString('en-IN', { maximumFractionDigits: 0 }) 
              : calculatedPrice.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Meta info */}
      <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
        {seller.moq && (
          <span className="flex items-center gap-1">
            <Package className="h-3.5 w-3.5" />
            MOQ: {seller.moq} kg
          </span>
        )}
        {seller.leadTime && (
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {seller.leadTime}d delivery
          </span>
        )}
        {seller.stock && (
          <span className="text-green-600">
            {seller.stock >= 1000 ? `${(seller.stock/1000).toFixed(0)}T` : `${seller.stock}kg`} in stock
          </span>
        )}
      </div>

      {/* Action */}
      <button
        onClick={handleInquiry}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
        data-testid={`inquiry-btn-${seller.listingId}`}
      >
        <Send className="h-4 w-4" />
        Send Inquiry
      </button>
    </div>
  );
}


export interface SellerPriceComparisonProps {
  productId: string;
  material?: string;
  totalWeight: number;
  onInquiry?: (seller: RawMaterialSeller, calculatedPrice: number) => void;
}

/**
 * Seller price comparison section - loads sellers and shows calculated prices
 */
export default function SellerPriceComparison({
  productId,
  material,
  totalWeight,
  onInquiry
}: SellerPriceComparisonProps) {
  const [sellers, setSellers] = useState<RawMaterialSeller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadSellers = async () => {
      if (!productId) return;
      
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (material) params.append('material', material);
        
        const res = await fetch(
          `${API_URL}/api/raw-materials/sellers/raw-material/${productId}?${params}`
        );
        
        if (!res.ok) throw new Error('Failed to load sellers');
        
        const data = await res.json();
        setSellers(data);
      } catch (err) {
        setError('Failed to load sellers');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadSellers();
  }, [productId, material]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-500">Loading sellers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        {error}
      </div>
    );
  }

  if (sellers.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Package className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <p>No sellers available for this product with rate/kg pricing.</p>
      </div>
    );
  }

  // Sort by rate (lowest first)
  const sortedSellers = [...sellers].sort((a, b) => a.rate_per_kg - b.rate_per_kg);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Compare Prices from {sellers.length} Sellers
        </h3>
        <span className="text-sm text-gray-500">
          For {totalWeight.toFixed(2)} kg
        </span>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedSellers.map((seller) => (
          <SellerPriceCard
            key={seller.listingId}
            seller={seller}
            totalWeight={totalWeight}
            onInquiry={onInquiry}
          />
        ))}
      </div>
    </div>
  );
}
