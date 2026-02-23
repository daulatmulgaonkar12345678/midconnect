'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Loader2, 
  Package, 
  Filter, 
  ArrowLeft, 
  ArrowUpDown,
  LayoutGrid,
  List,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

import { 
  getEnterpriseProduct, 
  getProductFacets, 
  filterProductListings,
  type EnterpriseProductResponse,
  type ProductFacetsResponse,
  type FilterResponse,
  type EnterpriseProductSeller
} from '@/lib/api';

import {
  IdentityBlock,
  FilterPanel,
  SellerCard,
  ComparisonTable,
  MobileFilterDrawer,
  EmptyState,
  InquiryModal,
  FloatingCompareBar
} from '@/components/enterprise';

const DEBOUNCE_MS = 300;
const MAX_COMPARE = 3;
const PAGE_SIZE = 20;

type SortOption = 'price' | 'leadTime' | 'stock' | 'updatedAt' | 'ranking';
type SortOrder = 'asc' | 'desc';

export default function EnterpriseProductPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const productId = params?.slug as string;

  // Data states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [productData, setProductData] = useState<EnterpriseProductResponse | null>(null);
  const [facetsData, setFacetsData] = useState<ProductFacetsResponse | null>(null);
  const [filterResults, setFilterResults] = useState<FilterResponse | null>(null);

  // UI states
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);
  const [compareSelected, setCompareSelected] = useState<Set<string>>(new Set());
  const [showComparison, setShowComparison] = useState(false);
  const [inquirySeller, setInquirySeller] = useState<EnterpriseProductSeller | null>(null);
  const [isFiltering, setIsFiltering] = useState(false);

  // Filter and sort states
  const [activeFilters, setActiveFilters] = useState<Record<string, unknown>>({});
  const [sortBy, setSortBy] = useState<SortOption>('ranking');  // Default to ranking
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc'); // Ranking is desc by default
  const [currentPage, setCurrentPage] = useState(1);

  // Parse URL params into filters on mount
  useEffect(() => {
    const filters: Record<string, unknown> = {};
    searchParams.forEach((value, key) => {
      if (key !== 'page' && key !== 'sort' && key !== 'order') {
        // Try parsing as number or range
        if (value.includes('-')) {
          const [min, max] = value.split('-').map(Number);
          if (!isNaN(min) || !isNaN(max)) {
            filters[key] = {};
            if (!isNaN(min)) (filters[key] as Record<string, number>).$gte = min;
            if (!isNaN(max)) (filters[key] as Record<string, number>).$lte = max;
          }
        } else if (!isNaN(Number(value))) {
          filters[key] = Number(value);
        } else {
          filters[key] = value;
        }
      }
    });
    
    if (Object.keys(filters).length > 0) {
      setActiveFilters(filters);
    }

    const page = searchParams.get('page');
    if (page) setCurrentPage(Number(page) || 1);

    const sort = searchParams.get('sort') as SortOption;
    if (sort) setSortBy(sort);

    const order = searchParams.get('order') as SortOrder;
    if (order) setSortOrder(order);
  }, []);

  // Update URL when filters change
  const updateURL = useCallback((filters: Record<string, unknown>, page: number, sort: SortOption, order: SortOrder) => {
    const params = new URLSearchParams();
    
    Object.entries(filters).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        const rangeObj = value as Record<string, number>;
        const min = rangeObj.$gte;
        const max = rangeObj.$lte;
        if (min !== undefined || max !== undefined) {
          params.set(key, `${min ?? ''}-${max ?? ''}`);
        }
      } else if (value !== null && value !== undefined) {
        params.set(key, String(value));
      }
    });
    
    if (page > 1) params.set('page', String(page));
    if (sort !== 'price') params.set('sort', sort);
    if (order !== 'asc') params.set('order', order);

    const queryString = params.toString();
    const newPath = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
    router.replace(newPath, { scroll: false });
  }, [router]);

  // Initial data fetch
  useEffect(() => {
    if (!productId) return;

    async function loadData() {
      try {
        setLoading(true);
        const [product, facets] = await Promise.all([
          getEnterpriseProduct(productId, 1, PAGE_SIZE),
          getProductFacets(productId)
        ]);
        setProductData(product);
        setFacetsData(facets);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load product');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [productId]);

  // Debounced filter function
  useEffect(() => {
    if (!productId || loading) return;

    const hasActiveFilters = Object.keys(activeFilters).length > 0 || 
                              sortBy !== 'price' || 
                              sortOrder !== 'asc' || 
                              currentPage !== 1;

    if (!hasActiveFilters && !filterResults) return;

    const timer = setTimeout(async () => {
      setIsFiltering(true);
      try {
        const results = await filterProductListings(productId, {
          attributes: Object.keys(activeFilters).length > 0 ? activeFilters : undefined,
          sortBy,
          order: sortOrder,
          page: currentPage,
          limit: PAGE_SIZE
        });
        setFilterResults(results);
        updateURL(activeFilters, currentPage, sortBy, sortOrder);
      } catch (err) {
        console.error('Filter error:', err);
      } finally {
        setIsFiltering(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [productId, activeFilters, sortBy, sortOrder, currentPage, loading, updateURL]);

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Record<string, unknown>) => {
    setActiveFilters(newFilters);
    setCurrentPage(1); // Reset to first page on filter change
  }, []);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setActiveFilters({});
    setCurrentPage(1);
    setFilterResults(null);
  }, []);

  // Handle sort change
  const handleSortChange = useCallback((newSort: SortOption) => {
    if (newSort === sortBy) {
      // For ranking, don't toggle - it's always desc
      if (newSort !== 'ranking') {
        setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
      }
    } else {
      setSortBy(newSort);
      // Ranking defaults to desc, others to asc
      setSortOrder(newSort === 'ranking' ? 'desc' : 'asc');
    }
    setCurrentPage(1);
  }, [sortBy]);

  // Compare functionality
  const handleCompareToggle = useCallback((sellerId: string) => {
    setCompareSelected(prev => {
      const next = new Set(prev);
      if (next.has(sellerId)) {
        next.delete(sellerId);
      } else if (next.size < MAX_COMPARE) {
        next.add(sellerId);
      }
      return next;
    });
  }, []);

  const handleRemoveFromCompare = useCallback((sellerId: string) => {
    setCompareSelected(prev => {
      const next = new Set(prev);
      next.delete(sellerId);
      return next;
    });
  }, []);

  // Get current sellers to display
  const displaySellers = useMemo(() => {
    if (filterResults) {
      return filterResults.results;
    }
    return productData?.sellers || [];
  }, [filterResults, productData]);

  // Get sellers for comparison
  const compareSellers = useMemo(() => {
    return displaySellers.filter(s => compareSelected.has(s.listingId));
  }, [displaySellers, compareSelected]);

  // Pagination info
  const pagination = useMemo(() => {
    if (filterResults) {
      return {
        total: filterResults.total,
        pages: filterResults.pages,
        page: filterResults.page
      };
    }
    return productData?.pagination || { total: 0, pages: 1, page: 1 };
  }, [filterResults, productData]);

  // Facets for filter panel
  const facets = useMemo(() => {
    return facetsData?.facets || {};
  }, [facetsData]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading product...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !productData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Product Not Found</h2>
          <p className="text-gray-500 mb-6">{error || 'This product is not available'}</p>
          <Link 
            href="/products" 
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Products
          </Link>
        </div>
      </div>
    );
  }

  const { product, summary, availableFacets } = productData;

  return (
    <div className="min-h-screen bg-gray-50" data-testid="enterprise-product-page">
      {/* Identity Block */}
      <IdentityBlock 
        product={product} 
        summary={summary} 
        specSummary={availableFacets}
      />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Mobile Filter Button */}
        <div className="lg:hidden mb-4 flex items-center justify-between">
          <button
            onClick={() => setMobileFilterOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 font-medium hover:bg-gray-50"
            data-testid="mobile-filter-btn"
          >
            <Filter className="h-4 w-4" />
            Filters
            {Object.keys(activeFilters).length > 0 && (
              <span className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0.5 rounded-full">
                {Object.keys(activeFilters).length}
              </span>
            )}
          </button>

          {/* Sort Dropdown (Mobile) */}
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [sort, order] = e.target.value.split('-') as [SortOption, SortOrder];
              setSortBy(sort);
              setSortOrder(order);
            }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
          >
            <option value="ranking-desc">Best Match</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="leadTime-asc">Lead Time: Shortest</option>
            <option value="stock-desc">Stock: Highest</option>
          </select>
        </div>

        <div className="flex gap-6">
          {/* Desktop Filter Sidebar */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-24">
              <FilterPanel
                facets={facets}
                activeFilters={activeFilters}
                onFilterChange={handleFilterChange}
                onClearFilters={handleClearFilters}
                isLoading={isFiltering}
              />
            </div>
          </aside>

          {/* Results Area */}
          <main className="flex-1 min-w-0">
            {/* Results Header */}
            <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 mb-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600">
                  <span className="font-semibold text-gray-900">{pagination.total}</span> sellers
                  {isFiltering && <Loader2 className="inline h-4 w-4 ml-2 animate-spin" />}
                </span>
                
                {/* Compare Button */}
                {compareSelected.size > 0 && (
                  <button
                    onClick={() => setShowComparison(true)}
                    className="hidden sm:flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800"
                  >
                    <LayoutGrid className="h-4 w-4" />
                    Compare ({compareSelected.size})
                  </button>
                )}
              </div>

              {/* Sort Options (Desktop) */}
              <div className="hidden lg:flex items-center gap-2">
                <span className="text-sm text-gray-500">Sort by:</span>
                {(['ranking', 'price', 'leadTime', 'stock'] as SortOption[]).map((option) => (
                  <button
                    key={option}
                    onClick={() => handleSortChange(option)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      sortBy === option 
                        ? 'bg-blue-100 text-blue-700 font-medium' 
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {option === 'ranking' && 'Best Match'}
                    {option === 'price' && 'Price'}
                    {option === 'leadTime' && 'Lead Time'}
                    {option === 'stock' && 'Stock'}
                    {sortBy === option && option !== 'ranking' && (
                      <ArrowUpDown className="inline h-3 w-3 ml-1" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Fallback Banner */}
            {filterResults?.fallbackLevel && filterResults.fallbackLevel > 0 && (
              <EmptyState
                type="no-results"
                fallbackLevel={filterResults.fallbackLevel}
                fallbackMessage={filterResults.fallbackMessage}
                onClearFilters={handleClearFilters}
              />
            )}

            {/* Seller Cards */}
            {displaySellers.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {displaySellers.map((seller) => (
                  <SellerCard
                    key={seller.listingId}
                    seller={seller}
                    isCompareSelected={compareSelected.has(seller.listingId)}
                    onCompareToggle={handleCompareToggle}
                    onInquiry={setInquirySeller}
                    compareDisabled={compareSelected.size >= MAX_COMPARE}
                    showRankingScore={sortBy === 'ranking'}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                type={summary.sellerCount === 0 ? 'no-listings' : 'no-results'}
                onClearFilters={handleClearFilters}
                categoryId={product.categoryId}
              />
            )}

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                
                <span className="px-4 py-2 text-sm text-gray-600">
                  Page <span className="font-semibold text-gray-900">{currentPage}</span> of {pagination.pages}
                </span>
                
                <button
                  onClick={() => setCurrentPage(p => Math.min(pagination.pages, p + 1))}
                  disabled={currentPage === pagination.pages}
                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            )}
          </main>
        </div>

        {/* Mobile Compare Bar */}
        {compareSelected.size > 0 && !showComparison && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 lg:hidden z-40">
            <button
              onClick={() => setShowComparison(true)}
              className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold"
            >
              Compare {compareSelected.size} Sellers
            </button>
          </div>
        )}
      </div>

      {/* Mobile Filter Drawer */}
      <MobileFilterDrawer
        isOpen={mobileFilterOpen}
        onClose={() => setMobileFilterOpen(false)}
        facets={facets}
        activeFilters={activeFilters}
        onFilterChange={handleFilterChange}
        onClearFilters={handleClearFilters}
        isLoading={isFiltering}
        resultCount={pagination.total}
      />

      {/* Comparison Table */}
      {showComparison && compareSellers.length > 0 && (
        <ComparisonTable
          sellers={compareSellers}
          onRemove={handleRemoveFromCompare}
          onInquiry={setInquirySeller}
          onClose={() => setShowComparison(false)}
        />
      )}

      {/* Inquiry Modal */}
      <InquiryModal
        isOpen={inquirySeller !== null}
        onClose={() => setInquirySeller(null)}
        seller={inquirySeller}
        productId={product._id}
        productName={product.name}
      />

      {/* Floating Compare Bar */}
      <FloatingCompareBar
        selectedCount={compareSelected.size}
        maxCount={MAX_COMPARE}
        onViewCompare={() => setShowComparison(true)}
        onClearAll={() => setCompareSelected(new Set())}
      />
    </div>
  );
}
