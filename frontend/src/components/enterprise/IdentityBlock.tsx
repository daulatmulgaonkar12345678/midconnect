'use client';

import Link from 'next/link';
import { Package, Users, Layers, ChevronRight } from 'lucide-react';

interface IdentityBlockProps {
  product: {
    _id: string;
    name: string;
    slug?: string;
    description?: string;
    images: string[];
    categoryId?: string;
    categoryName?: string;
    categorySlug?: string;  // SEO-friendly category URL
  };
  summary: {
    sellerCount: number;
    minPrice?: number;
    variantCount: number;
  };
  specSummary?: Record<string, (string | number)[]>;
}

export default function IdentityBlock({ product, summary, specSummary }: IdentityBlockProps) {
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  return (
    <div className="bg-white border-b border-gray-200" data-testid="identity-block">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Breadcrumb */}
        <nav className="flex items-center text-sm text-gray-500 mb-4" aria-label="Breadcrumb">
          <Link href="/" className="hover:text-gray-700 transition-colors">Home</Link>
          <ChevronRight className="h-4 w-4 mx-2 flex-shrink-0" />
          <Link href="/products" className="hover:text-gray-700 transition-colors">Products</Link>
          {product.categoryName && (
            <>
              <ChevronRight className="h-4 w-4 mx-2 flex-shrink-0" />
              <Link 
                href={`/categories/${product.categorySlug || product.categoryId}`} 
                className="hover:text-gray-700 transition-colors"
              >
                {product.categoryName}
              </Link>
            </>
          )}
          <ChevronRight className="h-4 w-4 mx-2 flex-shrink-0" />
          <span className="text-gray-900 font-medium truncate">{product.name}</span>
        </nav>

        <div className="flex flex-col lg:flex-row lg:items-start gap-6">
          {/* Product Image */}
          <div className="w-full lg:w-48 h-48 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden">
            {product.images?.[0] ? (
              <img 
                src={product.images[0]} 
                alt={product.name}
                className="w-full h-full object-contain"
              />
            ) : (
              <Package className="h-16 w-16 text-gray-300" />
            )}
          </div>

          {/* Product Info */}
          <div className="flex-1 min-w-0">
            {/* Category Badge */}
            {product.categoryName && (
              <span className="inline-block text-xs font-medium text-blue-600 bg-blue-50 px-2.5 py-1 rounded mb-2">
                {product.categoryName}
              </span>
            )}

            {/* Product Name */}
            <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 mb-3">
              {product.name}
            </h1>

            {/* Stats Row */}
            <div className="flex flex-wrap items-center gap-4 mb-4">
              <div className="flex items-center gap-1.5 text-gray-700">
                <Users className="h-4 w-4 text-blue-600" />
                <span className="font-semibold">{summary.sellerCount}</span>
                <span className="text-gray-500">Sellers</span>
              </div>
              
              <div className="h-4 w-px bg-gray-300" />
              
              <div className="flex items-center gap-1.5 text-gray-700">
                <Layers className="h-4 w-4 text-purple-600" />
                <span className="font-semibold">{summary.variantCount}</span>
                <span className="text-gray-500">Variants</span>
              </div>

              {summary.minPrice && (
                <>
                  <div className="h-4 w-px bg-gray-300" />
                  <div className="text-gray-700">
                    <span className="text-gray-500">From</span>{' '}
                    <span className="font-bold text-green-600 text-lg">
                      {formatPrice(summary.minPrice)}
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Availability Badge */}
            <div className="flex items-center gap-2">
              {summary.sellerCount > 0 ? (
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 bg-green-50 px-3 py-1 rounded-full">
                  <span className="w-2 h-2 bg-green-500 rounded-full" />
                  Available Now
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
                  <span className="w-2 h-2 bg-gray-400 rounded-full" />
                  No Active Listings
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Spec Summary Grid */}
        {specSummary && Object.keys(specSummary).length > 0 && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Available Specifications
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {Object.entries(specSummary).slice(0, 10).map(([key, values]) => (
                <div 
                  key={key} 
                  className="bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-100"
                >
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="font-medium text-gray-900 text-sm truncate">
                    {values.length > 3 
                      ? `${values.slice(0, 3).join(', ')}...` 
                      : values.join(', ')
                    }
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
