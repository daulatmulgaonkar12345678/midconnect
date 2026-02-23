'use client';

import Link from 'next/link';
import { SearchX, Filter, ArrowLeft, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  type: 'no-results' | 'no-listings' | 'error';
  fallbackLevel?: number;
  fallbackMessage?: string;
  onClearFilters?: () => void;
  categoryId?: string;
}

export default function EmptyState({ 
  type, 
  fallbackLevel, 
  fallbackMessage, 
  onClearFilters,
  categoryId 
}: EmptyStateProps) {
  // Show fallback message banner
  if (fallbackLevel && fallbackLevel > 0 && fallbackMessage) {
    return (
      <div 
        className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4"
        data-testid="fallback-banner"
      >
        <div className="flex items-start gap-3">
          <Filter className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              {fallbackMessage}
            </p>
            {onClearFilters && (
              <button
                onClick={onClearFilters}
                className="mt-2 text-sm text-amber-700 hover:text-amber-900 font-medium flex items-center gap-1"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Clear filters for exact results
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // No results after filtering
  if (type === 'no-results') {
    return (
      <div 
        className="text-center py-12 px-4 bg-white rounded-lg border border-gray-200"
        data-testid="empty-state-no-results"
      >
        <SearchX className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No Matching Sellers
        </h3>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">
          We couldn&apos;t find any sellers matching your current filters. 
          Try adjusting your criteria or clearing filters.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          {onClearFilters && (
            <button
              onClick={onClearFilters}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              <RefreshCw className="h-4 w-4" />
              Clear All Filters
            </button>
          )}
          <Link
            href="/products"
            className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Browse Products
          </Link>
        </div>
      </div>
    );
  }

  // No listings at all for this product
  if (type === 'no-listings') {
    return (
      <div 
        className="text-center py-12 px-4 bg-white rounded-lg border border-gray-200"
        data-testid="empty-state-no-listings"
      >
        <SearchX className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No Active Listings
        </h3>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">
          There are currently no sellers listing this product. 
          Check back later or browse similar products in the category.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          {categoryId && (
            <Link
              href={`/category/${categoryId}`}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Browse Category
            </Link>
          )}
          <Link
            href="/products"
            className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            All Products
          </Link>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div 
      className="text-center py-12 px-4 bg-red-50 rounded-lg border border-red-200"
      data-testid="empty-state-error"
    >
      <SearchX className="h-16 w-16 text-red-300 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-red-900 mb-2">
        Something Went Wrong
      </h3>
      <p className="text-red-700 mb-6 max-w-md mx-auto">
        We encountered an error loading this page. Please try refreshing.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium mx-auto"
      >
        <RefreshCw className="h-4 w-4" />
        Refresh Page
      </button>
    </div>
  );
}
