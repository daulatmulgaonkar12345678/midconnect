'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  getEnterpriseProduct,
  getProductFacets,
  filterProductListings,
  createInquiry,
  EnterpriseProductResponse,
  EnterpriseProductSeller,
  ProductFacetsResponse,
  FilterRequest
} from '@/lib/api';
import {
  Package,
  MapPin,
  Users,
  Clock,
  ArrowLeft,
  Send,
  Loader2,
  Check,
  AlertCircle,
  BadgeCheck,
  Filter,
  X,
  ChevronRight,
  Layers,
  Box,
  Truck,
  Building2,
  BarChart3,
  RefreshCw,
  SlidersHorizontal,
  GitCompare
} from 'lucide-react';

// ==================== TYPES ====================

interface FilterState {
  [key: string]: string | number | { $gte?: number; $lte?: number } | undefined;
}

interface CompareItem {
  seller: EnterpriseProductSeller;
  selected: boolean;
}

// ==================== HELPER COMPONENTS ====================

function SpecGrid({ attributes, labels }: { 
  attributes: Record<string, string | number>; 
  labels: Record<string, string>;
}) {
  const entries = Object.entries(attributes);
  if (entries.length === 0) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="spec-grid">
      {entries.map(([key, value]) => (
        <div key={key} className="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500 uppercase tracking-wide font-medium">
            {labels[key] || key.replace(/_/g, ' ')}
          </div>
          <div className="text-lg font-semibold text-slate-900 mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </div>
        </div>
      ))}
    </div>
  );
}

function SpecStrip({ attributes, labels }: { 
  attributes: Record<string, string | number>; 
  labels: Record<string, string>;
}) {
  const entries = Object.entries(attributes).slice(0, 4);
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 text-sm" data-testid="spec-strip">
      {entries.map(([key, value], idx) => (
        <span key={key} className="inline-flex items-center">
          <span className="font-semibold text-slate-800">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          <span className="text-slate-500 ml-1">
            {(labels[key] || key).split('(')[1]?.replace(')', '') || ''}
          </span>
          {idx < entries.length - 1 && (
            <span className="mx-2 text-slate-300">|</span>
          )}
        </span>
      ))}
    </div>
  );
}

function StockBadge({ status, stock }: { status: string; stock: number }) {
  if (status === 'in_stock' || stock > 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
        <Check className="h-3 w-3" />
        In Stock ({stock.toLocaleString()})
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded">
      <Clock className="h-3 w-3" />
      Made to Order
    </span>
  );
}

function SellerRoleBadge({ role }: { role: string }) {
  const roleConfig: Record<string, { bg: string; text: string; label: string }> = {
    manufacturer: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Manufacturer' },
    distributor: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Distributor' },
    dealer: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Dealer' },
    trader: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Trader' }
  };
  
  const config = roleConfig[role] || roleConfig.dealer;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 ${config.bg} ${config.text} text-xs font-medium rounded`}>
      <BadgeCheck className="h-3 w-3" />
      {config.label}
    </span>
  );
}

// ==================== FILTER PANEL ====================

function FilterPanel({
  facets,
  filters,
  onFilterChange,
  onClearFilters,
  loading
}: {
  facets: ProductFacetsResponse | null;
  filters: FilterState;
  onFilterChange: (key: string, value: unknown) => void;
  onClearFilters: () => void;
  loading: boolean;
}) {
  if (!facets || Object.keys(facets.facets).length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-slate-500">
          <Filter className="h-4 w-4" />
          <span className="text-sm">No filters available</span>
        </div>
      </div>
    );
  }

  const hasActiveFilters = Object.keys(filters).length > 0;

  return (
    <div className="bg-white border border-slate-200 rounded-lg" data-testid="filter-panel">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-slate-700" />
            <h3 className="font-semibold text-slate-900">Filter by Specs</h3>
          </div>
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              data-testid="clear-filters-btn"
            >
              <X className="h-4 w-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="p-4 space-y-5">
        {Object.entries(facets.facets).map(([key, facet]) => {
          const { values, metadata } = facet;
          const currentValue = filters[key];
          const isNumeric = metadata.fieldType === 'number' || values.every(v => typeof v === 'number');

          return (
            <div key={key} className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                {metadata.label}
                {metadata.unit && <span className="text-slate-500 ml-1">({metadata.unit})</span>}
              </label>

              {isNumeric && values.length > 1 ? (
                // Numeric range or select
                <select
                  value={currentValue as string || ''}
                  onChange={(e) => onFilterChange(key, e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid={`filter-${key}`}
                >
                  <option value="">Any {metadata.label}</option>
                  {(values as number[]).sort((a, b) => a - b).map((v) => (
                    <option key={v} value={v}>{v} {metadata.unit || ''}</option>
                  ))}
                </select>
              ) : (
                // Enum/text select
                <select
                  value={currentValue as string || ''}
                  onChange={(e) => onFilterChange(key, e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid={`filter-${key}`}
                >
                  <option value="">Any {metadata.label}</option>
                  {values.map((v) => (
                    <option key={String(v)} value={String(v)}>{String(v)}</option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>

      {loading && (
        <div className="p-4 border-t border-slate-200 flex items-center justify-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Filtering...</span>
        </div>
      )}
    </div>
  );
}

// ==================== SELLER CARD ====================

function SellerCard({
  seller,
  onInquiry,
  onCompare,
  isComparing,
  compareSelected
}: {
  seller: EnterpriseProductSeller;
  onInquiry: () => void;
  onCompare: () => void;
  isComparing: boolean;
  compareSelected: boolean;
}) {
  console.log('SellerCard rendering with:', JSON.stringify({
    companyName: seller.companyName,
    city: seller.city,
    state: seller.state
  }));
  const lowestPrice = seller.lowestPrice || (seller.pricingTiers[0]?.pricePerUnit);

  return (
    <div 
      className={`bg-white border rounded-lg overflow-hidden transition-all ${
        compareSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200 hover:border-slate-300'
      }`}
      data-testid={`seller-card-${seller.listingId}`}
    >
      {/* Spec Strip Header */}
      <div className="bg-slate-800 text-white px-4 py-3">
        <SpecStrip 
          attributes={seller.searchableAttributes} 
          labels={seller.attributeLabels} 
        />
      </div>

      <div className="p-4">
        {/* Seller Info Row */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-slate-900" data-testid="seller-name">{seller.companyName || 'Unknown Seller'}</span>
              <SellerRoleBadge role={seller.sellerRole} />
            </div>
            <div className="flex items-center gap-1 text-sm text-slate-500" data-testid="seller-location">
              <MapPin className="h-4 w-4" />
              {seller.city && seller.state 
                ? `${seller.city}, ${seller.state}`
                : seller.city || seller.state || seller.location || 'India'}
            </div>
          </div>
          
          {/* Compare Checkbox */}
          {isComparing && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={compareSelected}
                onChange={onCompare}
                className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-600">Compare</span>
            </label>
          )}
        </div>

        {/* Price & Stock Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <div className="text-xs text-green-600 uppercase font-medium">Starting</div>
            <div className="text-xl font-bold text-green-700">
              ₹{lowestPrice?.toLocaleString() || 'RFQ'}
            </div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">MOQ</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.moq.toLocaleString()}
            </div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">Lead Time</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.leadTimeDays ? `${seller.leadTimeDays}d` : '-'}
            </div>
          </div>
          
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
            <div className="text-xs text-slate-500 uppercase font-medium">Stock</div>
            <div className="text-xl font-bold text-slate-800">
              {seller.stock > 0 ? seller.stock.toLocaleString() : 'MTO'}
            </div>
          </div>
        </div>

        {/* Pricing Tiers */}
        {seller.pricingTiers.length > 1 && (
          <div className="mb-4">
            <div className="text-xs text-slate-500 uppercase font-medium mb-2">Volume Pricing</div>
            <div className="flex flex-wrap gap-2">
              {seller.pricingTiers.slice(0, 3).map((tier, idx) => (
                <span key={idx} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                  {tier.minQty}+ @ ₹{tier.pricePerUnit.toLocaleString()}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onInquiry}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            data-testid={`rfq-btn-${seller.listingId}`}
          >
            <Send className="h-4 w-4" />
            Request Quote
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== COMPARE MODAL ====================

function CompareModal({
  sellers,
  onClose
}: {
  sellers: EnterpriseProductSeller[];
  onClose: () => void;
}) {
  // Get all unique attribute keys
  const allKeys = useMemo(() => {
    const keys = new Set<string>();
    sellers.forEach(s => Object.keys(s.searchableAttributes).forEach(k => keys.add(k)));
    return Array.from(keys);
  }, [sellers]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-5xl w-full max-h-[90vh] overflow-hidden" data-testid="compare-modal">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <GitCompare className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-slate-900">Compare Sellers</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        <div className="overflow-auto p-4">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50">
                <th className="text-left p-3 text-sm font-medium text-slate-600 border-b">Attribute</th>
                {sellers.map(s => (
                  <th key={s.listingId} className="text-left p-3 text-sm font-medium text-slate-900 border-b">
                    {s.companyName}
                    <div className="text-xs font-normal text-slate-500">{s.location}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Specifications */}
              {allKeys.map(key => (
                <tr key={key} className="border-b border-slate-100">
                  <td className="p-3 text-sm text-slate-600">
                    {sellers[0]?.attributeLabels[key] || key}
                  </td>
                  {sellers.map(s => (
                    <td key={s.listingId} className="p-3 text-sm font-medium text-slate-900">
                      {s.searchableAttributes[key] ?? '-'}
                    </td>
                  ))}
                </tr>
              ))}
              
              {/* Price */}
              <tr className="border-b border-slate-100 bg-green-50">
                <td className="p-3 text-sm font-medium text-green-700">Price</td>
                {sellers.map(s => (
                  <td key={s.listingId} className="p-3 text-lg font-bold text-green-700">
                    ₹{s.lowestPrice?.toLocaleString() || 'RFQ'}
                  </td>
                ))}
              </tr>
              
              {/* MOQ */}
              <tr className="border-b border-slate-100">
                <td className="p-3 text-sm text-slate-600">MOQ</td>
                {sellers.map(s => (
                  <td key={s.listingId} className="p-3 text-sm font-medium text-slate-900">
                    {s.moq.toLocaleString()}
                  </td>
                ))}
              </tr>
              
              {/* Lead Time */}
              <tr className="border-b border-slate-100">
                <td className="p-3 text-sm text-slate-600">Lead Time</td>
                {sellers.map(s => (
                  <td key={s.listingId} className="p-3 text-sm font-medium text-slate-900">
                    {s.leadTimeDays ? `${s.leadTimeDays} days` : '-'}
                  </td>
                ))}
              </tr>
              
              {/* Stock */}
              <tr className="border-b border-slate-100">
                <td className="p-3 text-sm text-slate-600">Stock</td>
                {sellers.map(s => (
                  <td key={s.listingId} className="p-3 text-sm font-medium text-slate-900">
                    {s.stock > 0 ? s.stock.toLocaleString() : 'Made to Order'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ==================== MAIN PAGE ====================

export default function EnterpriseProductPage() {
  const params = useParams();
  const router = useRouter();
  const { user, getIdToken, isAuthenticated } = useAuth();

  const productId = params?.slug ? decodeURIComponent(params.slug as string) : null;

  // Data state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<EnterpriseProductResponse | null>(null);
  const [facets, setFacets] = useState<ProductFacetsResponse | null>(null);
  const [sellers, setSellers] = useState<EnterpriseProductSeller[]>([]);

  // Filter state
  const [filters, setFilters] = useState<FilterState>({});
  const [sortBy, setSortBy] = useState<'price' | 'leadTime' | 'stock'>('price');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [filterLoading, setFilterLoading] = useState(false);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);

  // Compare state
  const [isComparing, setIsComparing] = useState(false);
  const [compareItems, setCompareItems] = useState<string[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Inquiry state
  const [inquiryModal, setInquiryModal] = useState<{ open: boolean; seller: EnterpriseProductSeller | null }>({
    open: false,
    seller: null
  });
  const [inquiryQuantity, setInquiryQuantity] = useState(1);
  const [inquiryNote, setInquiryNote] = useState('');
  const [buyerType, setBuyerType] = useState<'trader' | 'contractor' | 'oem' | 'manufacturer' | 'other'>('other');
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  const [inquirySuccess, setInquirySuccess] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    if (!productId) {
      setError('Invalid product');
      setLoading(false);
      return;
    }

    async function loadData() {
      try {
        const [productData, facetsData] = await Promise.all([
          getEnterpriseProduct(productId as string),
          getProductFacets(productId as string)
        ]);

        setProduct(productData);
        setFacets(facetsData);
        setSellers(productData.sellers);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Product not found');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [productId]);

  // Apply filters
  const applyFilters = useCallback(async () => {
    if (!productId) return;

    setFilterLoading(true);
    setFallbackMessage(null);

    try {
      const filterRequest: FilterRequest = {
        attributes: Object.keys(filters).length > 0 ? filters : undefined,
        sortBy,
        order: sortOrder,
        page: 1,
        limit: 50
      };

      const result = await filterProductListings(productId as string, filterRequest);
      setSellers(result.results);
      setFallbackMessage(result.fallbackMessage || null);
    } catch (err) {
      console.error('Filter error:', err);
    } finally {
      setFilterLoading(false);
    }
  }, [productId, filters, sortBy, sortOrder]);

  // Apply filters when they change
  useEffect(() => {
    if (product) {
      applyFilters();
    }
  }, [filters, sortBy, sortOrder, applyFilters, product]);

  const handleFilterChange = (key: string, value: unknown) => {
    setFilters(prev => {
      const next = { ...prev };
      if (value === undefined || value === '') {
        delete next[key];
      } else {
        next[key] = value as string | number;
      }
      return next;
    });
  };

  const handleClearFilters = () => {
    setFilters({});
  };

  const handleCompareToggle = (listingId: string) => {
    setCompareItems(prev => {
      if (prev.includes(listingId)) {
        return prev.filter(id => id !== listingId);
      }
      if (prev.length >= 3) {
        return prev;
      }
      return [...prev, listingId];
    });
  };

  const handleInquiry = async () => {
    if (!inquiryModal.seller) return;

    if (!isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
      return;
    }

    setSubmittingInquiry(true);

    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }

      await createInquiry(token, {
        sellerId: inquiryModal.seller.sellerId,
        listingId: inquiryModal.seller.listingId,
        quantity: inquiryQuantity,
        message: inquiryNote || undefined,
        buyerType
      });

      setInquirySuccess('Inquiry sent successfully! The seller will contact you soon.');
      setInquiryModal({ open: false, seller: null });
      setInquiryQuantity(1);
      setInquiryNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setSubmittingInquiry(false);
    }
  };

  const compareSellers = useMemo(() => {
    return sellers.filter(s => compareItems.includes(s.listingId));
  }, [sellers, compareItems]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-600">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="text-lg">Loading product...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !product) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Product Not Found</h2>
          <p className="text-slate-600 mb-4">{error || 'This product does not exist.'}</p>
          <Link href="/products" className="text-blue-600 hover:text-blue-800">
            ← Browse Products
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* ==================== SECTION 1: IDENTITY BLOCK ==================== */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-sm text-slate-500 mb-4">
            <Link href="/" className="hover:text-slate-700">Home</Link>
            <ChevronRight className="h-4 w-4" />
            <Link href="/products" className="hover:text-slate-700">Products</Link>
            {product.product.categoryName && (
              <>
                <ChevronRight className="h-4 w-4" />
                <span className="hover:text-slate-700">{product.product.categoryName}</span>
              </>
            )}
            <ChevronRight className="h-4 w-4" />
            <span className="text-slate-900 font-medium">{product.product.name}</span>
          </nav>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Product Image */}
            <div className="lg:col-span-1">
              <div className="bg-slate-100 rounded-lg aspect-square flex items-center justify-center">
                {product.product.images?.[0] ? (
                  <img
                    src={product.product.images[0]}
                    alt={product.product.name}
                    className="max-h-full max-w-full object-contain rounded-lg"
                  />
                ) : (
                  <Package className="h-24 w-24 text-slate-400" />
                )}
              </div>
            </div>

            {/* Product Info */}
            <div className="lg:col-span-2">
              <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 mb-4" data-testid="product-name">
                {product.product.name}
              </h1>

              {/* Summary Badges */}
              <div className="flex flex-wrap gap-3 mb-6">
                <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg">
                  <Users className="h-4 w-4" />
                  <span className="font-medium">{product.summary.sellerCount} {product.summary.sellerCount === 1 ? 'Seller' : 'Sellers'}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-purple-50 text-purple-700 rounded-lg">
                  <Layers className="h-4 w-4" />
                  <span className="font-medium">{product.summary.variantCount} {product.summary.variantCount === 1 ? 'Variant' : 'Variants'}</span>
                </div>
                {product.summary.minPrice && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg">
                    <span className="font-bold">₹</span>
                    <span className="font-medium">From ₹{product.summary.minPrice.toLocaleString('en-IN')}</span>
                  </div>
                )}
              </div>

              {/* Spec Grid from first seller's attributes (or template) */}
              {sellers[0]?.searchableAttributes && Object.keys(sellers[0].searchableAttributes).length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
                    Specifications
                  </h3>
                  <SpecGrid
                    attributes={sellers[0].searchableAttributes}
                    labels={sellers[0].attributeLabels}
                  />
                </div>
              )}

              {/* Description */}
              {product.product.description && (
                <p className="text-slate-600">{product.product.description}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ==================== MAIN CONTENT ==================== */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Success Message */}
        {inquirySuccess && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700">
            <Check className="h-5 w-5" />
            {inquirySuccess}
            <button onClick={() => setInquirySuccess(null)} className="ml-auto">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Fallback Message */}
        {fallbackMessage && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3 text-amber-700">
            <AlertCircle className="h-5 w-5" />
            {fallbackMessage}
          </div>
        )}

        <div className="flex gap-8">
          {/* ==================== SECTION 2: FILTER PANEL ==================== */}
          <div className="hidden lg:block w-72 flex-shrink-0">
            <div className="sticky top-24">
              <FilterPanel
                facets={facets}
                filters={filters}
                onFilterChange={handleFilterChange}
                onClearFilters={handleClearFilters}
                loading={filterLoading}
              />

              {/* Sort Options */}
              <div className="mt-4 bg-white border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Sort By</h3>
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [field, order] = e.target.value.split('-');
                    setSortBy(field as 'price' | 'leadTime' | 'stock');
                    setSortOrder(order as 'asc' | 'desc');
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  data-testid="sort-select"
                >
                  <option value="price-asc">Price: Low to High</option>
                  <option value="price-desc">Price: High to Low</option>
                  <option value="leadTime-asc">Lead Time: Fastest</option>
                  <option value="stock-desc">Stock: Highest</option>
                </select>
              </div>
            </div>
          </div>

          {/* ==================== SECTION 3: SELLER CARDS ==================== */}
          <div className="flex-1">
            {/* Compare Toggle Bar */}
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">
              <div className="text-slate-600">
                <span className="font-semibold text-slate-900">{sellers.length}</span> sellers found
              </div>
              
              <div className="flex items-center gap-4">
                {isComparing && compareItems.length >= 2 && (
                  <button
                    onClick={() => setShowCompareModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    data-testid="compare-now-btn"
                  >
                    <GitCompare className="h-4 w-4" />
                    Compare ({compareItems.length})
                  </button>
                )}
                
                <button
                  onClick={() => {
                    setIsComparing(!isComparing);
                    if (isComparing) setCompareItems([]);
                  }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                    isComparing 
                      ? 'bg-blue-50 border-blue-200 text-blue-700' 
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                  data-testid="toggle-compare-btn"
                >
                  <GitCompare className="h-4 w-4" />
                  {isComparing ? 'Cancel Compare' : 'Compare Sellers'}
                </button>
              </div>
            </div>

            {/* Seller Cards Grid */}
            {sellers.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
                <Package className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">No sellers found</h3>
                <p className="text-slate-500 mb-4">Try adjusting your filters</p>
                <button
                  onClick={handleClearFilters}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Clear all filters
                </button>
              </div>
            ) : (
              <div className="grid gap-4">
                {sellers.map(seller => (
                  <SellerCard
                    key={seller.listingId}
                    seller={seller}
                    onInquiry={() => setInquiryModal({ open: true, seller })}
                    onCompare={() => handleCompareToggle(seller.listingId)}
                    isComparing={isComparing}
                    compareSelected={compareItems.includes(seller.listingId)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ==================== INQUIRY MODAL ==================== */}
      {inquiryModal.open && inquiryModal.seller && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full" data-testid="inquiry-modal">
            <div className="p-4 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Request Quote</h2>
                <button 
                  onClick={() => setInquiryModal({ open: false, seller: null })}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  <X className="h-5 w-5 text-slate-500" />
                </button>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {inquiryModal.seller.companyName} • {inquiryModal.seller.location}
              </p>
            </div>

            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Quantity Required</label>
                <input
                  type="number"
                  value={inquiryQuantity}
                  onChange={(e) => setInquiryQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  min={inquiryModal.seller.moq}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  data-testid="inquiry-quantity"
                />
                <p className="text-xs text-slate-500 mt-1">MOQ: {inquiryModal.seller.moq}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Type</label>
                <select
                  value={buyerType}
                  onChange={(e) => setBuyerType(e.target.value as typeof buyerType)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  data-testid="buyer-type"
                >
                  <option value="manufacturer">Manufacturer</option>
                  <option value="contractor">Contractor</option>
                  <option value="oem">OEM</option>
                  <option value="trader">Trader</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Additional Notes</label>
                <textarea
                  value={inquiryNote}
                  onChange={(e) => setInquiryNote(e.target.value)}
                  placeholder="Any specific requirements..."
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  data-testid="inquiry-note"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-200">
              <button
                onClick={handleInquiry}
                disabled={submittingInquiry}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                data-testid="submit-inquiry-btn"
              >
                {submittingInquiry ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Send Inquiry
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== SECTION 4: COMPARE MODAL ==================== */}
      {showCompareModal && compareSellers.length >= 2 && (
        <CompareModal
          sellers={compareSellers}
          onClose={() => setShowCompareModal(false)}
        />
      )}
    </div>
  );
}
