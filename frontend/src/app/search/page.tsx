'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { SearchListing } from '@/types';
import { Search, Info, AlertCircle, MapPin, X, TrendingUp, Navigation } from 'lucide-react';
import { geoSearchProducts, sanitizeInput, ApiError } from '@/lib/api';

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const query = searchParams.get('q') || '';
  const city = searchParams.get('city') || '';
  const state = searchParams.get('state') || '';
  const lat = searchParams.get('lat');
  const lng = searchParams.get('lng');
  const radiusKm = searchParams.get('radiusKm');
  
  const [products, setProducts] = useState<SearchListing[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);
  const [fallbackUsed, setFallbackUsed] = useState<string | null>(null);
  const [didYouMean, setDidYouMean] = useState<string | null>(null);
  const [autoCorreced, setAutoCorreced] = useState<boolean>(false);
  const [originalQuery, setOriginalQuery] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setFallbackMessage(null);
    setFallbackUsed(null);
    setDidYouMean(null);
    setAutoCorreced(false);
    setOriginalQuery(null);
    
    try {
      const result = await geoSearchProducts({
        query: query ? sanitizeInput(query) : undefined,
        city: city || undefined,
        state: state || undefined,
        lat: lat ? parseFloat(lat) : undefined,
        lng: lng ? parseFloat(lng) : undefined,
        radiusKm: radiusKm ? parseInt(radiusKm) : 50,
        limit: 50,
      });
      setProducts(result.products || []);
      setFallbackMessage(result.fallbackMessage);
      setFallbackUsed(result.fallbackUsed);
      
      // Handle "Did you mean?" suggestion
      if (result.didYouMean) {
        setDidYouMean(result.didYouMean);
      }
      if (result.autoCorreced) {
        setAutoCorreced(true);
        setOriginalQuery(result.originalQuery || query);
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.getUserMessage() : 'Search failed';
      setError(message);
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, city, state, lat, lng, radiusKm]);

  useEffect(() => {
    handleSearch();
  }, [handleSearch]);

  // Handle clicking on "Did you mean?" suggestion
  const handleDidYouMeanClick = () => {
    if (didYouMean) {
      const params = new URLSearchParams(searchParams.toString());
      params.set('q', didYouMean);
      router.push(`/search?${params.toString()}`);
    }
  };

  // Revert to original query
  const handleRevertToOriginal = () => {
    if (originalQuery) {
      const params = new URLSearchParams(searchParams.toString());
      params.set('q', originalQuery);
      router.push(`/search?${params.toString()}`);
    }
  };

  // Build location label for display
  const locationLabel = city ? `${city}${state ? `, ${state}` : ''}` : (state || 'All India');
  const hasLocationFilter = !!(city || state);

  // Clear location filter
  const clearLocationFilter = () => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    router.push(`/search?${params.toString()}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="search-results-page">
      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* Results Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="search-results-title">
            {query ? `Results for "${query}"` : 'Browse Products'}
          </h1>
          <p className="text-gray-500">
            {products.length} products found
            {hasLocationFilter && <span className="ml-1">in {locationLabel}</span>}
          </p>
        </div>
      </div>

      {/* Fallback Message - Shows when search fell back to wider area */}
      {fallbackMessage && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3" data-testid="fallback-message">
          <Navigation className="h-5 w-5 text-amber-600 flex-shrink-0" />
          <div>
            <p className="text-amber-800 font-medium">{fallbackMessage}</p>
            {fallbackUsed === 'radius' && (
              <p className="text-amber-600 text-sm mt-1">Results are sorted by distance from your location</p>
            )}
          </div>
        </div>
      )}

      {/* Active Location Filter Chip - Prominent Display */}
      {hasLocationFilter && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between" data-testid="active-filter-section">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-blue-800">Filtering by location:</span>
            <span 
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-full shadow-md"
              data-testid="location-filter-chip"
            >
              <MapPin className="h-4 w-4" />
              {locationLabel}
              <button
                onClick={clearLocationFilter}
                className="ml-1 hover:bg-blue-700 rounded-full p-1 transition-colors"
                data-testid="clear-location-filter-btn"
                aria-label="Remove location filter"
              >
                <X className="h-4 w-4" />
              </button>
            </span>
          </div>
          <p className="text-xs text-blue-600">Click X to search all of India</p>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Searching...</p>
        </div>
      ) : products.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="search-results-grid">
          {products.map((listing) => (
            <Link 
              key={listing._id} 
              href={`/product/${listing.productId}`}
              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
              data-testid="search-result-card"
            >
              {/* Image */}
              <div className="aspect-[4/3] bg-gray-100 relative">
                {listing.images?.[0] ? (
                  <img
                    src={listing.images[0]}
                    alt={listing.productName}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <span className="text-4xl">📦</span>
                  </div>
                )}
                {listing.inStock && (
                  <div className="absolute top-2 right-2 bg-green-600 text-white text-xs px-2 py-1 rounded-full">
                    In Stock
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
                  {listing.productName}
                </h3>
                
                {/* Price */}
                {listing.price && (
                  <div className="flex items-center gap-1 text-lg font-bold text-green-600 mb-2">
                    <TrendingUp className="h-4 w-4" />
                    ₹{listing.price.toLocaleString()}
                    <span className="text-xs text-gray-500 font-normal">per unit</span>
                  </div>
                )}

                {/* Location */}
                {(listing.city || listing.state) && (
                  <div className="flex items-center gap-1 text-sm text-gray-500">
                    <MapPin className="h-4 w-4" />
                    {listing.city}{listing.city && listing.state ? ', ' : ''}{listing.state}
                  </div>
                )}

                {/* MOQ */}
                <div className="text-xs text-gray-400 mt-2">
                  MOQ: {listing.moq} units
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : query ? (
        <div className="text-center py-16 bg-white rounded-xl">
          <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No products found for &quot;{query}&quot;</p>
          <p className="text-gray-400 mt-2">Try a different search term or use the search bar above</p>
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-xl">
          <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Use the search bar above to find products</p>
          <p className="text-gray-400 mt-2">Search by product name, category, or specifications</p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    }>
      <SearchContent />
    </Suspense>
  );
}
