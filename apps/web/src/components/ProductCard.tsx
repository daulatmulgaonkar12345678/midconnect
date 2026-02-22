import Link from 'next/link';
import { MapPin, Users, TrendingUp } from 'lucide-react';
import { ProductWithSellers } from '@/types';

interface ProductCardProps {
  product: ProductWithSellers & {
    badge?: string;
    badgeType?: string;
  };
}

// Badge styling based on type
const badgeStyles: { [key: string]: string } = {
  local: 'bg-green-100 text-green-700 border-green-200',
  best_value: 'bg-blue-100 text-blue-700 border-blue-200',
  fast: 'bg-purple-100 text-purple-700 border-purple-200',
  warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
};

// Seller type badges with emojis
const SELLER_TYPE_BADGES: { [key: string]: { emoji: string; label: string; color: string } } = {
  manufacturer: { emoji: '🏭', label: 'Manufacturer', color: 'bg-indigo-100 text-indigo-700' },
  dealer: { emoji: '🏷️', label: 'Dealer', color: 'bg-blue-100 text-blue-700' },
  distributor: { emoji: '🚚', label: 'Distributor', color: 'bg-orange-100 text-orange-700' },
  wholesaler: { emoji: '📦', label: 'Wholesaler', color: 'bg-purple-100 text-purple-700' },
  retailer: { emoji: '🛍️', label: 'Retailer', color: 'bg-pink-100 text-pink-700' },
};

export default function ProductCard({ product }: ProductCardProps) {
  const firstSeller = product.sellers?.[0];
  const thumbnail = firstSeller?.images?.[0] || '/placeholder-product.png';
  
  // Get seller type from first seller's role - camelCase
  const sellerType = firstSeller?.sellerRole?.toLowerCase();
  const sellerBadge = sellerType ? SELLER_TYPE_BADGES[sellerType] : null;

  return (
    <Link href={`/product/${product.productId}`}>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow relative">
        {/* Product Badge - ONE badge only */}
        {product.badge && (
          <div className={`absolute top-2 left-2 z-10 px-2 py-1 rounded-full text-xs font-medium border ${badgeStyles[product.badgeType || 'best_value']}`}>
            {product.badge}
          </div>
        )}

        {/* Image */}
        <div className="aspect-[4/3] bg-gray-100 relative">
          {thumbnail && thumbnail !== '/placeholder-product.png' ? (
            <img
              src={thumbnail}
              alt={product.productName}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              <span className="text-4xl">📦</span>
            </div>
          )}
          {product.sellerCount > 1 && (
            <div className="absolute top-2 right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
              <Users className="h-3 w-3" />
              {product.sellerCount} sellers
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Seller Type Badge */}
          {sellerBadge && (
            <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium mb-2 ${sellerBadge.color}`}>
              <span>{sellerBadge.emoji}</span>
              <span>{sellerBadge.label}</span>
            </div>
          )}
          
          <p className="text-xs text-blue-600 font-medium mb-1">
            {product.categoryName}
          </p>
          <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
            {product.productName}
          </h3>
          <p className="text-sm text-gray-500 mb-3">
            {product.productFamily} • {product.productVariant}
          </p>

          {/* Price - camelCase minPrice */}
          {product.minPrice && (
            <div className="flex items-center gap-1 text-lg font-bold text-green-600">
              <TrendingUp className="h-4 w-4" />
              ₹{product.minPrice.toLocaleString()}
              <span className="text-xs text-gray-500 font-normal">/{product.productUnit}</span>
            </div>
          )}

          {/* Location with classification hint - camelCase fields */}
          {firstSeller?.sellerArea && (
            <div className="flex items-center gap-1 text-sm text-gray-500 mt-2">
              <MapPin className="h-4 w-4" />
              {firstSeller.sellerArea}, {firstSeller.sellerState}
              {firstSeller.locationClass === 'LOCAL' && (
                <span className="ml-1 text-xs text-green-600">(Local)</span>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
