'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ProductCard from '@/components/ProductCard';
import { ProductWithSellers } from '@/types';
import { Search, Info, AlertCircle, MapPin, X } from 'lucide-react';
import { searchProducts, sanitizeInput, ApiError } from '@/lib/api';

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const query = searchParams.get('q') || '';
  const city = searchParams.get('city') || '';
  const state = searchParams.get('state') || '';
  
  const [products, setProducts] = useState<ProductWithSellers[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guidanceDisclaimer, setGuidanceDisclaimer] = useState<string>('');

  const handleSearch = useCallback(async () => {
    if (!query) {
      setProducts([]);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const sanitizedQuery = sanitizeInput(query);
      const result = await searchProducts(sanitizedQuery, {
        city: city || undefined,
        state: state || undefined,
        limit: 50,
      });
      setProducts(result.products || []);
      setGuidanceDisclaimer(result.guidanceDisclaimer || '');
    } catch (err) {
      const message = err instanceof ApiError ? err.getUserMessage() : 'Search failed';
      setError(message);
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, city, state]);

  useEffect(() => {
    handleSearch();
  }, [handleSearch]);

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
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="search-results-title">
            {query ? `Results for "${query}"` : 'Search Products'}
          </h1>
          <p className="text-gray-500">
            {products.length} products found
            {(city || state) && <span className="ml-1">in {locationLabel}</span>}
          </p>
        </div>
        
        {/* Guidance Disclaimer */}
        {guidanceDisclaimer && (
          <div className="group relative">
            <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
              <Info className="h-4 w-4" />
              <span>About suggestions</span>
            </button>
            <div className="absolute right-0 top-full mt-2 w-72 p-3 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
              {guidanceDisclaimer}
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Searching...</p>
        </div>
      ) : products.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="search-results-grid">
          {products.map((product) => (
            <ProductCard key={product.productId} product={product} />
          ))}
        </div>
      ) : query ? (
        <div className="text-center py-16 bg-white rounded-xl">
          <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No products found for "{query}"</p>
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
