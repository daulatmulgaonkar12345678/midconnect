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
import { ProductJsonLd, CitySellerGroup, SEOContentSection, InternalLinksSection } from '@/components/ProductSEO';
import MaterialCalculatorCard, { CalculationResult } from '@/components/calculator/MaterialCalculatorCard';
import SellerPriceComparison, { RawMaterialSeller } from '@/components/calculator/SellerPriceComparison';
import ModernDynamicCalculator from '@/components/calculator/ModernDynamicCalculator';
import CalculatorSellerCards from '@/components/calculator/CalculatorSellerCards';
import RawMaterialSellerCard from '@/components/product/RawMaterialSellerCard';
import StandardSellerCard from '@/components/product/StandardSellerCard';
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
  GitCompare,
  Star,
  Shield,
  Play,
  Video,
  Eye,
  Calculator,
  Scale
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
            {labels[key] || (key ? key.replace(/_/g, ' ') : '')}
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
            {(labels?.[key] || key || '').split('(')[1]?.replace(')', '') || ''}
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

// UdyogConnect Seller Badge (Choice/Trusted)
function UdyogConnectBadge({ badgeType }: { badgeType?: string }) {
  if (!badgeType || badgeType === 'none') return null;
  
  if (badgeType === 'choice') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded border border-yellow-300">
        <Star className="h-3 w-3 fill-yellow-500 text-yellow-500" />
        UdyogConnect Choice
      </span>
    );
  }
  
  if (badgeType === 'trusted') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded border border-green-300">
        <Shield className="h-3 w-3 fill-green-500 text-green-500" />
        UdyogConnect Trusted
      </span>
    );
  }
  
  return null;
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

// Check if identifier is an ObjectId (24 hex chars)
function isObjectId(str: string): boolean {
  return /^[a-f0-9]{24}$/i.test(str);
}

export default function EnterpriseProductPage() {
  const params = useParams();
  const router = useRouter();
  const { user, getIdToken, isAuthenticated } = useAuth();

  const productId = params?.slug ? decodeURIComponent(params.slug as string) : null;
  
  // Redirect state for 301 redirects from old URLs
  const [redirectChecked, setRedirectChecked] = useState(false);

  // Data state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<EnterpriseProductResponse | null>(null);
  const [facets, setFacets] = useState<ProductFacetsResponse | null>(null);
  const [sellers, setSellers] = useState<EnterpriseProductSeller[]>([]);
  
  // SEO state - Enhanced for Marketplace v2.0
  const [seoData, setSeoData] = useState<{
    seoContent: string;
    sellersByCity: Record<string, Array<{ companyName: string; state: string; lowestPrice: number | null; badgeType: string }>>;
    internalLinks?: {
      category: { name: string; url: string } | null;
      similarProducts: Array<{ name: string; url: string }>;
      cityPages: Array<{ name: string; url: string }>;
      topRated: string;
    };
    minPrice?: number | null;
    maxPrice?: number | null;
    minMoq?: number | null;
    availableCities?: string[];
  } | null>(null);

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

  // Raw material calculator state
  const [productType, setProductType] = useState<'raw_material' | 'standard_product'>('standard_product');
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [rawMaterialInquiry, setRawMaterialInquiry] = useState<{
    open: boolean;
    seller: RawMaterialSeller | null;
    calculatedPrice: number;
  }>({ open: false, seller: null, calculatedPrice: 0 });
  
  // Configurable calculator state
  const [linkedCalculatorId, setLinkedCalculatorId] = useState<string | null>(null);
  const [dynamicCalcResult, setDynamicCalcResult] = useState<any>(null);
  const [sellersWithRates, setSellersWithRates] = useState<any[]>([]);
  const [inquiryModalOpen, setInquiryModalOpen] = useState(false);
  const [selectedSellerForInquiry, setSelectedSellerForInquiry] = useState<any>(null);
  const [calculatedPriceForInquiry, setCalculatedPriceForInquiry] = useState<number>(0);

  // Check for 301 redirect (old ObjectId or legacy slug URLs)
  useEffect(() => {
    if (!productId || redirectChecked) return;
    
    // If it looks like an ObjectId, check for redirect
    if (isObjectId(productId)) {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';
      
      fetch(`${API_URL}/api/redirect/product/${productId}`)
        .then(res => res.json())
        .then(data => {
          if (data.redirect && data.slug) {
            // Perform 301 redirect to new slug URL
            router.replace(`/product/${data.slug}`);
          } else {
            setRedirectChecked(true);
          }
        })
        .catch(() => setRedirectChecked(true));
    } else {
      setRedirectChecked(true);
    }
  }, [productId, redirectChecked, router]);

  // Load initial data
  useEffect(() => {
    if (!productId || !redirectChecked) {
      if (!productId) {
        setError('Invalid product');
        setLoading(false);
      }
      return;
    }

    async function loadData() {
      try {
        const [productData, facetsData] = await Promise.all([
          getEnterpriseProduct(productId as string),
          getProductFacets(productId as string)
        ]);

        // Handle 301 redirect if backend returns redirect info
        // This handles partial slugs, reordered words, city additions, etc.
        if (productData.redirect?.needed && productData.redirect?.canonicalSlug) {
          const canonicalSlug = productData.redirect.canonicalSlug;
          // Replace current URL with canonical URL for SEO
          router.replace(`/products/${canonicalSlug}`);
          return;
        }

        setProduct(productData);
        setFacets(facetsData);
        setSellers(productData.sellers);
        
        // Set product type from product data (defaults to 'standard_product')
        const pType = productData.product.product_type || 'standard_product';
        setProductType(pType as 'raw_material' | 'standard_product');
        console.log('Product type:', pType);
        
        // Only load calculator for raw_material products
        const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';
        const actualProductId = productData.product._id;
        const categoryId = productData.product.categoryId;
        
        if (pType === 'raw_material' && categoryId) {
          // Load configurable calculator for raw material products
          fetch(`${API_URL}/api/calculator/calculators/by-category/${categoryId}`)
            .then(res => {
              if (res.ok) return res.json();
              throw new Error('No calculator found');
            })
            .then(calcData => {
              if (calcData && calcData._id) {
                console.log('Found linked calculator:', calcData.name);
                setLinkedCalculatorId(calcData._id);
                
                // Fetch sellers with rate_per_unit for this product
                fetch(`${API_URL}/api/calculator/sellers-by-product/${actualProductId}`)
                  .then(res => res.ok ? res.json() : [])
                  .then(sellers => {
                    console.log('Sellers with rates:', sellers);
                    setSellersWithRates(sellers);
                  })
                  .catch(err => console.log('Failed to fetch seller rates:', err));
              }
            })
            .catch(() => {
              console.log('No configurable calculator found for raw material');
            });
        }
        
        // Load SEO data in background (non-blocking) - Enhanced for Marketplace v2.0
        fetch(`${API_URL}/api/products/${productId}/seo`)
          .then(res => res.json())
          .then(data => {
            // Handle redirect from SEO endpoint as well
            if (data.redirect?.needed && data.redirect?.canonicalSlug) {
              router.replace(`/products/${data.redirect.canonicalSlug}`);
              return;
            }
            setSeoData({
              seoContent: data.seoContent,
              sellersByCity: data.sellersByCity,
              internalLinks: data.internalLinks,
              minPrice: data.minPrice,
              maxPrice: data.maxPrice,
              minMoq: data.minMoq,
              availableCities: data.availableCities
            });
          })
          .catch(err => console.log('SEO data not available:', err));
          
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Product not found');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [productId, redirectChecked, router]);

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

  // Raw material inquiry handler with calculation data (LEGACY - uses calculationResult)
  const handleRawMaterialInquiry = async () => {
    if (!rawMaterialInquiry.seller || !calculationResult) return;

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

      // Create inquiry with calculation data embedded in message
      const calculationDetails = `
Material: ${calculationResult?.material || 'N/A'}
Shape: ${calculationResult?.shape?.replace?.('_', ' ') || 'N/A'}
Dimensions: ${calculationResult?.dimensions ? Object.entries(calculationResult.dimensions).map(([k, v]) => `${k}: ${v}`).join(', ') : 'N/A'}
Quantity: ${calculationResult?.quantity || 1} pieces
Calculated Weight: ${calculationResult?.total_weight_display || 'N/A'}
Rate/kg: ₹${rawMaterialInquiry.seller?.rate_per_kg || 0}
Estimated Total: ₹${rawMaterialInquiry.calculatedPrice?.toLocaleString?.('en-IN') || 0}
${inquiryNote ? `\nNote: ${inquiryNote}` : ''}`;

      await createInquiry(token, {
        sellerId: rawMaterialInquiry.seller.sellerId,
        listingId: rawMaterialInquiry.seller.listingId,
        quantity: calculationResult?.quantity || 1,
        message: calculationDetails.trim(),
        buyerType,
        // Include structured calculation data
        calculationData: {
          material: calculationResult?.material,
          shape: calculationResult?.shape,
          dimensions: calculationResult?.dimensions,
          quantity: calculationResult?.quantity,
          weight_per_piece: calculationResult?.weight_per_piece,
          total_weight: calculationResult?.total_weight,
          rate_per_kg: rawMaterialInquiry.seller?.rate_per_kg,
          calculated_price: rawMaterialInquiry.calculatedPrice
        }
      });

      setInquirySuccess('Inquiry sent successfully! The seller will contact you soon.');
      setRawMaterialInquiry({ open: false, seller: null, calculatedPrice: 0 });
      setInquiryNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setSubmittingInquiry(false);
    }
  };

  // NEW: Raw material inquiry handler using dynamicCalcResult
  const handleRawMaterialInquirySubmit = async () => {
    if (!rawMaterialInquiry.seller || !dynamicCalcResult) return;

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

      const sellerRate = rawMaterialInquiry.seller.rate_per_kg || rawMaterialInquiry.seller.rate || 0;

      await createInquiry(token, {
        sellerId: rawMaterialInquiry.seller.sellerId,
        listingId: rawMaterialInquiry.seller.listingId || rawMaterialInquiry.seller._id,
        quantity: dynamicCalcResult.quantity || 1,
        message: inquiryNote.trim() || 'Inquiry from weight calculator',
        buyerType,
        // Include structured calculation data from dynamic calculator
        calculationData: {
          calculator_name: dynamicCalcResult.calculator_name,
          material_name: dynamicCalcResult.material_name,
          formula_used: dynamicCalcResult.formula_used,
          formula_description: dynamicCalcResult.formula_description,
          field_summary: dynamicCalcResult.field_summary,
          quantity: dynamicCalcResult.quantity,
          weight_per_piece: dynamicCalcResult.value_per_piece,
          total_weight: dynamicCalcResult.total_value,
          output_unit: dynamicCalcResult.output_unit,
          rate_per_kg: sellerRate,
          calculated_price: rawMaterialInquiry.calculatedPrice
        }
      });

      setInquirySuccess('Inquiry sent successfully! The seller will contact you soon.');
      setRawMaterialInquiry({ open: false, seller: null, calculatedPrice: 0 });
      setInquiryNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setSubmittingInquiry(false);
    }
  };

  // Handle calculation result from calculator
  const handleCalculationResult = (result: CalculationResult) => {
    setCalculationResult(result);
  };

  // Generate calculation details for inquiry note
  const generateCalculationNote = () => {
    if (!dynamicCalcResult) return '';
    
    const lines = [
      '=== WEIGHT CALCULATION DETAILS ===',
      `Calculator: ${dynamicCalcResult.calculator_name || 'Weight Calculator'}`,
      `Material: ${dynamicCalcResult.material_name || 'N/A'}`,
      `Formula: ${dynamicCalcResult.formula_description || dynamicCalcResult.formula_used || 'Standard'}`,
      '',
      '--- Dimensions ---',
    ];
    
    // Add dimension details
    if (dynamicCalcResult.field_summary) {
      Object.entries(dynamicCalcResult.field_summary).forEach(([key, value]) => {
        const label = key.toUpperCase();
        lines.push(`${label}: ${value}`);
      });
    }
    
    lines.push('');
    lines.push('--- Calculation Results ---');
    lines.push(`Quantity: ${dynamicCalcResult.quantity} pcs`);
    lines.push(`Weight per piece: ${dynamicCalcResult.value_per_piece?.toFixed(3) || '0'} ${dynamicCalcResult.output_unit || 'kg'}`);
    lines.push(`Total Weight: ${dynamicCalcResult.total_value?.toFixed(3) || '0'} ${dynamicCalcResult.output_unit || 'kg'}`);
    
    return lines.join('\n');
  };

  // Handle raw material seller inquiry callback
  const handleRawMaterialSellerInquiry = (seller: RawMaterialSeller, calculatedPrice: number) => {
    // Pre-populate inquiry note with calculation details
    const calcNote = generateCalculationNote();
    setInquiryNote(calcNote);
    setRawMaterialInquiry({ open: true, seller, calculatedPrice });
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

      {/* ==================== RAW MATERIAL SECTION (Calculator + RawMaterialSellerCards) ==================== */}
      {productType === 'raw_material' && linkedCalculatorId && (
        <div className="bg-gradient-to-b from-gray-50 to-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold mb-3">
                <Calculator className="h-4 w-4" />
                Weight Calculator
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Calculate Your Requirements</h2>
              <p className="text-gray-600 mt-2">
                Enter dimensions to calculate weight and compare seller prices instantly
              </p>
            </div>

            {/* Full-width Calculator */}
            <div className="mb-8">
              <ModernDynamicCalculator
                calculatorId={linkedCalculatorId}
                productName={product?.product?.name}
                showPriceField={false}
                enableNavigation={true}
                onCalculate={(result) => {
                  setDynamicCalcResult(result);
                  console.log('Dynamic calculation result:', result);
                }}
                onMaterialChange={(material) => {
                  console.log('Material changed:', material);
                }}
              />
            </div>
            
            {/* Sort By for Raw Materials */}
            {dynamicCalcResult && dynamicCalcResult.total_value > 0 && sellersWithRates.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Compare Sellers ({sellersWithRates.length})
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">Sort by:</span>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'price' | 'leadTime' | 'stock')}
                      className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="price">Lowest Price</option>
                      <option value="leadTime">Fastest Delivery</option>
                      <option value="stock">Highest Stock</option>
                    </select>
                  </div>
                </div>
              </div>
            )}
            
            {/* Raw Material Seller Cards */}
            {dynamicCalcResult && dynamicCalcResult.total_value > 0 && (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {sellersWithRates
                  .sort((a, b) => {
                    if (sortBy === 'price') return a.rate - b.rate;
                    if (sortBy === 'leadTime') return (a.leadTime || 999) - (b.leadTime || 999);
                    if (sortBy === 'stock') return (b.stock || 0) - (a.stock || 0);
                    return 0;
                  })
                  .map((seller, index) => (
                    <RawMaterialSellerCard
                      key={seller._id}
                      seller={seller}
                      calculationResult={dynamicCalcResult}
                      rank={index + 1}
                      onRequestQuote={(s, price) => {
                        // Use the proper handler that sets rawMaterialInquiry state
                        handleRawMaterialSellerInquiry(s as RawMaterialSeller, price);
                      }}
                      onViewDetails={(s) => {
                        // Navigate to seller detail page
                        if (productId) {
                          window.location.href = `/products/${productId}/seller/${s._id}`;
                        }
                      }}
                    />
                  ))
                }
              </div>
            )}
            
            {/* No sellers message */}
            {dynamicCalcResult && dynamicCalcResult.total_value > 0 && sellersWithRates.length === 0 && (
              <div className="text-center py-8 bg-gray-50 rounded-xl">
                <Package className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p className="text-gray-500">No sellers available for this product yet.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== STANDARD PRODUCT SECTION (Filters + StandardSellerCards) ==================== */}
      {productType === 'standard_product' && (
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

            {/* ==================== SECTION 3: STANDARD SELLER CARDS ==================== */}
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
                {sellers.map((seller, index) => (
                  <div key={seller.listingId} className="relative">
                    {/* Compare Checkbox */}
                    {isComparing && (
                      <label className="absolute top-4 right-4 z-10 flex items-center gap-2 cursor-pointer bg-white px-2 py-1 rounded shadow-sm border">
                        <input
                          type="checkbox"
                          checked={compareItems.includes(seller.listingId)}
                          onChange={() => handleCompareToggle(seller.listingId)}
                          className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-600">Compare</span>
                      </label>
                    )}
                    <StandardSellerCard
                      seller={seller}
                      productSlug={productId || undefined}
                      rank={index === 0 ? 1 : undefined}
                      onRequestQuote={(s) => setInquiryModal({ open: true, seller: s as EnterpriseProductSeller })}
                      onViewDetails={(s) => {
                        window.location.href = `/products/${productId}/seller/${s.listingId}`;
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      )}

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

      {/* ==================== RAW MATERIAL INQUIRY MODAL ==================== */}
      {rawMaterialInquiry.open && rawMaterialInquiry.seller && dynamicCalcResult && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto" data-testid="raw-material-inquiry-modal">
            <div className="p-4 border-b border-slate-200 sticky top-0 bg-white">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Request Quote</h2>
                <button 
                  onClick={() => setRawMaterialInquiry({ open: false, seller: null, calculatedPrice: 0 })}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  <X className="h-5 w-5 text-slate-500" />
                </button>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {rawMaterialInquiry.seller.sellerName || rawMaterialInquiry.seller.companyName}
                {rawMaterialInquiry.seller.location && ` • ${rawMaterialInquiry.seller.location}`}
              </p>
            </div>

            <div className="p-4 space-y-4">
              {/* Calculation Summary */}
              <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                <h3 className="font-semibold text-orange-800 mb-3 flex items-center gap-2">
                  <Calculator className="h-4 w-4" />
                  Your Calculation
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-orange-600">Calculator:</span>
                    <p className="font-medium text-orange-800">{dynamicCalcResult.calculator_name || 'Weight Calculator'}</p>
                  </div>
                  <div>
                    <span className="text-orange-600">Material:</span>
                    <p className="font-medium text-orange-800">{dynamicCalcResult.material_name || 'N/A'}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-orange-600">Dimensions:</span>
                    <p className="font-medium text-orange-800">
                      {dynamicCalcResult.field_summary 
                        ? Object.entries(dynamicCalcResult.field_summary).map(([k, v]) => `${k}: ${v}`).join(' | ')
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-orange-600">Quantity:</span>
                    <p className="font-medium text-orange-800">{dynamicCalcResult.quantity} pieces</p>
                  </div>
                  <div>
                    <span className="text-orange-600">Total Weight:</span>
                    <p className="font-bold text-orange-800">{dynamicCalcResult.total_value?.toFixed(3)} {dynamicCalcResult.output_unit}</p>
                  </div>
                </div>
              </div>

              {/* Price Summary */}
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-600">Rate/kg</p>
                    <p className="font-semibold text-green-800">₹{(rawMaterialInquiry.seller.rate_per_kg || rawMaterialInquiry.seller.rate || 0).toLocaleString('en-IN')}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-green-600">Estimated Total</p>
                    <p className="text-2xl font-bold text-green-800">₹{rawMaterialInquiry.calculatedPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Quantity Required</label>
                <input
                  type="number"
                  value={dynamicCalcResult.quantity || 1}
                  readOnly
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-700"
                />
                <p className="text-xs text-slate-500 mt-1">MOQ: {rawMaterialInquiry.seller.moq || 1}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Type</label>
                <select
                  value={buyerType}
                  onChange={(e) => setBuyerType(e.target.value as typeof buyerType)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="manufacturer">Manufacturer</option>
                  <option value="contractor">Contractor</option>
                  <option value="oem">OEM</option>
                  <option value="trader">Trader</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Calculation Details (Sent to Seller)
                </label>
                <textarea
                  value={inquiryNote}
                  onChange={(e) => setInquiryNote(e.target.value)}
                  placeholder="Calculation details will be auto-filled..."
                  rows={8}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Seller will see these details to verify and prepare quote
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 sticky bottom-0 bg-white">
              <button
                onClick={handleRawMaterialInquirySubmit}
                disabled={submittingInquiry}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                data-testid="submit-raw-material-inquiry-btn"
              >
                {submittingInquiry ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending Inquiry...
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
      
      {/* ==================== SECTION 5: SEO CONTENT (MARKETPLACE v2.0) ==================== */}
      {/* JSON-LD Structured Data for Google Rich Snippets */}
      {productId && <ProductJsonLd slug={productId} />}
      
      {/* City-wise Seller Grouping */}
      {seoData?.sellersByCity && Object.keys(seoData.sellersByCity).length > 1 && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
          <CitySellerGroup sellersByCity={seoData.sellersByCity} />
        </div>
      )}
      
      {/* Internal Links for SEO (Category, Similar Products, City Pages) */}
      {seoData?.internalLinks && product && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <InternalLinksSection 
            internalLinks={seoData.internalLinks} 
            productName={product.product?.name || 'Product'} 
          />
        </div>
      )}
      
      {/* SEO Content (Collapsible) - 300-500 words structured content */}
      {seoData?.seoContent && product && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SEOContentSection 
            seoContent={seoData.seoContent} 
            productName={product.product?.name || 'Product'} 
          />
        </div>
      )}
    </div>
  );
}
