'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { fetchWithAuth } from '@/lib/api';
import { 
  Loader2, 
  Filter, 
  ChevronLeft, 
  ChevronRight, 
  Package,
  Store,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Trash2,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  IndianRupee,
  Clock,
  Layers,
  Search,
  X,
  ChevronDown
} from 'lucide-react';

interface PricingTier {
  minQty: number;
  maxQty: number | null;
  pricePerUnit: number;
}

interface AdminListing {
  _id: string;
  productId: string;
  sellerId: string;
  status: 'active' | 'inactive';
  stock: number;
  leadTime: number;
  currency: string;
  pricingTiers: PricingTier[];
  createdAt: string;
  updatedAt: string;
  productName?: string;
  productStatus?: string;
  productExists?: boolean;
  sellerName?: string;
  sellerEmail?: string;
  sellerPhone?: string;
  sellerExists?: boolean;
}

interface ListingsResponse {
  listings: AdminListing[];
  total: number;
  page: number;
  pages: number;
}

interface DropdownItem {
  _id: string;
  name?: string;
  business_name?: string;
  email?: string;
}

interface ProductDropdownResponse {
  products: DropdownItem[];
}

interface SellerDropdownResponse {
  sellers: DropdownItem[];
}

// Searchable Dropdown Component
function SearchableDropdown({
  label,
  placeholder,
  items,
  selectedId,
  onSelect,
  onSearch,
  isLoading,
  icon: Icon,
  displayField
}: {
  label: string;
  placeholder: string;
  items: DropdownItem[];
  selectedId: string | null;
  onSelect: (id: string | null, item?: DropdownItem) => void;
  onSearch: (term: string) => void;
  isLoading: boolean;
  icon: React.ElementType;
  displayField: 'name' | 'business_name';
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedItem = items.find(item => item._id === selectedId);
  const displayValue = selectedItem 
    ? (displayField === 'name' ? selectedItem.name : selectedItem.business_name) || selectedItem.email
    : null;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    onSearch(value);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm hover:border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
        data-testid={`dropdown-${label.toLowerCase().replace(/\s/g, '-')}`}
      >
        <div className="flex items-center gap-2 truncate">
          <Icon className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <span className={displayValue ? 'text-gray-900' : 'text-gray-400'}>
            {displayValue || placeholder}
          </span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {selectedId && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelect(null);
                setSearchTerm('');
              }}
              className="p-0.5 hover:bg-gray-100 rounded"
            >
              <X className="h-3.5 w-3.5 text-gray-400" />
            </button>
          )}
          <ChevronDown className={`h-4 w-4 text-gray-400 transition ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg">
          {/* Search Input */}
          <div className="p-2 border-b border-gray-100">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder={`Search ${label.toLowerCase()}...`}
                className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>
          </div>

          {/* Options List */}
          <div className="max-h-60 overflow-y-auto">
            {isLoading ? (
              <div className="p-4 text-center">
                <Loader2 className="h-5 w-5 animate-spin text-blue-600 mx-auto" />
              </div>
            ) : items.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No results found
              </div>
            ) : (
              items.map((item) => (
                <button
                  key={item._id}
                  type="button"
                  onClick={() => {
                    onSelect(item._id, item);
                    setIsOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 ${
                    item._id === selectedId ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  <Icon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <div className="truncate">
                    <span className="font-medium">
                      {displayField === 'name' ? item.name : item.business_name || item.email}
                    </span>
                    {displayField === 'business_name' && item.email && (
                      <span className="text-gray-400 text-xs ml-2">{item.email}</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AdminListingsPage() {
  const { getIdToken } = useAuth();
  const [listings, setListings] = useState<AdminListing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dropdown data
  const [products, setProducts] = useState<DropdownItem[]>([]);
  const [sellers, setSellers] = useState<DropdownItem[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [sellersLoading, setSellersLoading] = useState(false);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [lowStockFilter, setLowStockFilter] = useState<string>('');
  const [productFilter, setProductFilter] = useState<string | null>(null);
  const [sellerFilter, setSellerFilter] = useState<string | null>(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState('createdAt');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Fetch products for dropdown
  const fetchProducts = useCallback(async (search?: string) => {
    setProductsLoading(true);
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const params = new URLSearchParams();
      params.append('limit', '50');
      if (search) params.append('search', search);
      
      const data = await fetchWithAuth<ProductDropdownResponse>(
        `/admin/listings/dropdown/products?${params.toString()}`,
        token
      );
      setProducts(data?.products ?? []);
    } catch (err) {
      console.error('Failed to fetch products:', err);
    } finally {
      setProductsLoading(false);
    }
  }, [getIdToken]);

  // Fetch sellers for dropdown
  const fetchSellers = useCallback(async (search?: string) => {
    setSellersLoading(true);
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const params = new URLSearchParams();
      params.append('limit', '50');
      if (search) params.append('search', search);
      
      const data = await fetchWithAuth<SellerDropdownResponse>(
        `/admin/listings/dropdown/sellers?${params.toString()}`,
        token
      );
      setSellers(data?.sellers ?? []);
    } catch (err) {
      console.error('Failed to fetch sellers:', err);
    } finally {
      setSellersLoading(false);
    }
  }, [getIdToken]);

  // Initial load of dropdown data
  useEffect(() => {
    fetchProducts();
    fetchSellers();
  }, [fetchProducts, fetchSellers]);

  const fetchListings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', '20');
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      
      if (lowStockFilter && parseInt(lowStockFilter) >= 0) {
        params.append('low_stock', lowStockFilter);
      }

      if (productFilter) {
        params.append('product_id', productFilter);
      }

      if (sellerFilter) {
        params.append('seller_id', sellerFilter);
      }
      
      const data = await fetchWithAuth<ListingsResponse>(
        `/admin/listings?${params.toString()}`,
        token
      );
      
      setListings(data?.listings ?? []);
      setTotalPages(data?.pages ?? 1);
      setTotal(data?.total ?? 0);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch listings';
      setError(errorMessage);
      console.error('Failed to fetch listings:', err);
    } finally {
      setIsLoading(false);
    }
  }, [getIdToken, page, statusFilter, lowStockFilter, productFilter, sellerFilter, sortBy, sortOrder]);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  const handleToggleStatus = async (listing: AdminListing) => {
    const action = listing.status === 'active' ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} this listing?`)) return;
    
    try {
      const token = await getIdToken();
      if (!token) return;
      
      await fetchWithAuth(
        `/admin/listings/${listing._id}/toggle-status`,
        token,
        { method: 'POST' }
      );
      
      fetchListings();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to toggle status';
      alert(errorMessage);
    }
  };

  const handleDelete = async (listing: AdminListing) => {
    if (!confirm(`Are you sure you want to DELETE this listing? This action cannot be undone.`)) return;
    
    try {
      const token = await getIdToken();
      if (!token) return;
      
      await fetchWithAuth(
        `/admin/listings/${listing._id}`,
        token,
        { method: 'DELETE' }
      );
      
      fetchListings();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete listing';
      alert(errorMessage);
    }
  };

  const formatPrice = (tiers: PricingTier[]) => {
    if (!tiers || tiers.length === 0) return 'N/A';
    const lowest = Math.min(...tiers.map(t => t.pricePerUnit));
    return `₹${lowest.toLocaleString('en-IN')}`;
  };

  const getStatusBadge = (status: string) => {
    if (status === 'active') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="h-3 w-3" />
          Active
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <XCircle className="h-3 w-3" />
        Inactive
      </span>
    );
  };

  const getStockBadge = (stock: number) => {
    if (stock === 0) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
          Out of Stock
        </span>
      );
    }
    if (stock <= 10) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">
          Low: {stock}
        </span>
      );
    }
    return (
      <span className="text-sm text-gray-700">{stock}</span>
    );
  };

  const clearAllFilters = () => {
    setStatusFilter('all');
    setLowStockFilter('');
    setProductFilter(null);
    setSellerFilter(null);
    setPage(1);
  };

  const hasActiveFilters = statusFilter !== 'all' || lowStockFilter || productFilter || sellerFilter;

  return (
    <div data-testid="admin-listings-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Seller Listings</h1>
        <p className="text-gray-500">
          Commercial SSOT - Manage all seller listings and pricing
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        {/* Searchable Dropdowns Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Product Filter */}
          <SearchableDropdown
            label="Filter by Product"
            placeholder="All Products"
            items={products}
            selectedId={productFilter}
            onSelect={(id) => { setProductFilter(id); setPage(1); }}
            onSearch={fetchProducts}
            isLoading={productsLoading}
            icon={Package}
            displayField="name"
          />

          {/* Seller Filter */}
          <SearchableDropdown
            label="Filter by Seller"
            placeholder="All Sellers"
            items={sellers}
            selectedId={sellerFilter}
            onSelect={(id) => { setSellerFilter(id); setPage(1); }}
            onSearch={fetchSellers}
            isLoading={sellersLoading}
            icon={Store}
            displayField="business_name"
          />

          {/* Status Filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
            <select
              data-testid="status-filter"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          {/* Low Stock Filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Low Stock Threshold</label>
            <div className="relative">
              <AlertTriangle className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <input
                type="number"
                data-testid="low-stock-filter"
                placeholder="e.g., 10"
                value={lowStockFilter}
                onChange={(e) => {
                  setLowStockFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="0"
              />
            </div>
          </div>
        </div>

        {/* Sort & Actions Row */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-4">
            {/* Sort */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                data-testid="sort-by"
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="createdAt">Created Date</option>
                <option value="updatedAt">Updated Date</option>
                <option value="stock">Stock</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
              >
                {sortOrder === 'desc' ? '↓ Desc' : '↑ Asc'}
              </button>
            </div>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg flex items-center gap-1"
              >
                <X className="h-4 w-4" />
                Clear Filters
              </button>
            )}
          </div>

          {/* Refresh */}
          <button
            data-testid="refresh-btn"
            onClick={fetchListings}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium flex items-center gap-2 transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Summary Stats */}
        <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-6 text-sm">
          <span className="text-gray-600">
            Total: <strong className="text-gray-900">{total}</strong> listings
          </span>
          {productFilter && (
            <span className="text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
              Product filter active
            </span>
          )}
          {sellerFilter && (
            <span className="text-purple-600 bg-purple-50 px-2 py-0.5 rounded">
              Seller filter active
            </span>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading listings...</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Package className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Listings Found</h3>
          <p className="text-gray-500">
            {hasActiveFilters
              ? 'Try adjusting your filters'
              : 'No seller listings have been created yet'}
          </p>
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
            >
              Clear All Filters
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Listings Table */}
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="listings-table">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Product
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Seller
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Stock
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Lead Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Price Tiers
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Lowest Price
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {listings.map((listing) => (
                    <tr 
                      key={listing._id} 
                      className="hover:bg-gray-50 transition"
                      data-testid={`listing-row-${listing._id}`}
                    >
                      {/* Product */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            listing.productExists === false ? 'bg-red-100' : 'bg-blue-100'
                          }`}>
                            <Package className={`h-5 w-5 ${
                              listing.productExists === false ? 'text-red-600' : 'text-blue-600'
                            }`} />
                          </div>
                          <div>
                            <p className={`font-medium truncate max-w-[200px] ${
                              listing.productName?.includes('[Deleted') ? 'text-red-600' : 'text-gray-900'
                            }`}>
                              {listing.productName || 'Unknown Product'}
                            </p>
                            <p className="text-xs text-gray-500 truncate max-w-[200px]">
                              ID: {listing.productId || 'N/A'}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Seller */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            listing.sellerExists === false ? 'bg-red-100' : 'bg-purple-100'
                          }`}>
                            <Store className={`h-5 w-5 ${
                              listing.sellerExists === false ? 'text-red-600' : 'text-purple-600'
                            }`} />
                          </div>
                          <div>
                            <p className={`font-medium truncate max-w-[150px] ${
                              listing.sellerName?.includes('[Deleted') ? 'text-red-600' : 'text-gray-900'
                            }`}>
                              {listing.sellerName || 'Unknown Seller'}
                            </p>
                            <p className="text-xs text-gray-500 truncate max-w-[150px]">
                              {listing.sellerEmail || listing.sellerId || 'N/A'}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-4">
                        {getStatusBadge(listing.status)}
                      </td>

                      {/* Stock */}
                      <td className="px-4 py-4">
                        {getStockBadge(listing.stock)}
                      </td>

                      {/* Lead Time */}
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center gap-1 text-sm text-gray-700">
                          <Clock className="h-3.5 w-3.5 text-gray-400" />
                          {listing.leadTime} days
                        </span>
                      </td>

                      {/* Price Tiers */}
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center gap-1 text-sm text-gray-700">
                          <Layers className="h-3.5 w-3.5 text-gray-400" />
                          {listing.pricingTiers?.length || 0} tiers
                        </span>
                      </td>

                      {/* Lowest Price */}
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center gap-1 text-sm font-semibold text-gray-900">
                          <IndianRupee className="h-3.5 w-3.5 text-green-600" />
                          {formatPrice(listing.pricingTiers).replace('₹', '')}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleStatus(listing)}
                            className={`p-2 rounded-lg transition ${
                              listing.status === 'active'
                                ? 'text-orange-600 hover:bg-orange-50'
                                : 'text-green-600 hover:bg-green-50'
                            }`}
                            title={listing.status === 'active' ? 'Deactivate' : 'Activate'}
                            data-testid={`toggle-status-${listing._id}`}
                          >
                            {listing.status === 'active' ? (
                              <ToggleRight className="h-5 w-5" />
                            ) : (
                              <ToggleLeft className="h-5 w-5" />
                            )}
                          </button>
                          <button
                            onClick={() => handleDelete(listing)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                            title="Delete Listing"
                            data-testid={`delete-listing-${listing._id}`}
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages} ({total} total)
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 flex items-center gap-1"
                  data-testid="prev-page"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 flex items-center gap-1"
                  data-testid="next-page"
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Data Architecture Note */}
      <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-100">
        <h4 className="text-sm font-semibold text-blue-800 mb-2">
          Data Architecture Note
        </h4>
        <p className="text-sm text-blue-700">
          This panel displays data from the <code className="bg-blue-100 px-1 rounded">seller_listings</code> collection - 
          the Single Source of Truth (SSOT) for all commercial data. 
          Price aggregates, seller counts, and stock are always computed dynamically from this collection.
          Use the Product and Seller filters to audit specific relationships.
        </p>
      </div>
    </div>
  );
}
