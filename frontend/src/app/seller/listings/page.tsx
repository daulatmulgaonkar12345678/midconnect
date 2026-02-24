'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getSellerListings,
  SellerListing,
  PricingTier
} from '@/lib/api';
import { 
  Plus, 
  Package, 
  Loader2, 
  AlertCircle, 
  Eye,
  PauseCircle,
  FileText,
  Archive,
  Search,
  Filter,
  Clock,
  Zap,
  MessageSquare,
  Pencil,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react';
import Link from 'next/link';

export default function SellerListingsPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [listings, setListings] = useState<SellerListing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedPricing, setExpandedPricing] = useState<Set<string>>(new Set());

  const loadListings = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }
      
      const data = await getSellerListings(token, {
        status: statusFilter || undefined,
        page,
        limit: 12
      });
      setListings(data?.listings ?? []);
      setTotal(data?.total ?? 0);
      setTotalPages(data?.pages ?? 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load listings');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router, statusFilter, page]);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadListings();
      }
    }
  }, [user, authLoading, loadListings, router]);

  const togglePricing = (listingId: string) => {
    setExpandedPricing(prev => {
      const newSet = new Set(prev);
      if (newSet.has(listingId)) {
        newSet.delete(listingId);
      } else {
        newSet.add(listingId);
      }
      return newSet;
    });
  };

  const statusColors: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    draft: { bg: 'bg-gray-100', text: 'text-gray-700', icon: <FileText className="h-3 w-3" /> },
    active: { bg: 'bg-green-100', text: 'text-green-700', icon: <Eye className="h-3 w-3" /> },
    paused: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: <PauseCircle className="h-3 w-3" /> },
    archived: { bg: 'bg-red-100', text: 'text-red-700', icon: <Archive className="h-3 w-3" /> }
  };

  // FINAL ARCHITECTURE: Format pricing tier range (camelCase)
  const formatTierRange = (tier: PricingTier) => {
    const min = tier.minQty;
    const max = tier.maxQty;
    if (max === null || max === undefined) {
      return `${min}+ units`;
    }
    return `${min} – ${max} units`;
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Listings</h1>
              <p className="text-gray-600 mt-1">All your active products grouped by category</p>
            </div>
            
            {/* Primary Actions */}
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/seller/pricing"
                className="flex items-center gap-2 px-4 py-2.5 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition font-medium shadow-sm"
                data-testid="quick-price-header-btn"
                title="Update product prices and quantity slabs without editing full details"
              >
                <Zap className="h-5 w-5" />
                Quick Price Update
              </Link>
              <Link
                href="/seller/inquiries"
                className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition font-medium shadow-sm"
                data-testid="inquiries-header-btn"
                title="View, respond, and convert buyer enquiries in real time"
              >
                <MessageSquare className="h-5 w-5" />
                Buyer Enquiries
              </Link>
              <Link
                href="/seller/listings/new"
                className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
                data-testid="create-new-listing-btn"
                title="Add a new product and start receiving enquiries instantly"
              >
                <Plus className="h-5 w-5" />
                New Listing
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search listings..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="search-listings-input"
                />
              </div>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                data-testid="status-filter-select"
              >
                <option value="">All Status</option>
                <option value="draft">Drafts</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
        </div>

        {/* Empty State */}
        {listings.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Listings Yet</h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              {statusFilter 
                ? `No listings with "${statusFilter}" status found.`
                : "You haven't added any products yet. Start selling by creating your first listing."}
            </p>
            <Link
              href="/seller/listings/new"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              data-testid="empty-state-cta"
            >
              <Plus className="h-5 w-5" />
              Add New Listing
            </Link>
          </div>
        ) : (
          <>
            {/* Listings Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {listings
                .filter(listing => 
                  !searchQuery || 
                  listing.productName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  listing.categoryName?.toLowerCase().includes(searchQuery.toLowerCase())
                )
                .map((listing) => (
                <div 
                  key={listing._id}
                  className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100 hover:shadow-md transition"
                  data-testid={`listing-card-${listing._id}`}
                >
                  {/* Product Header */}
                  <div className="p-4 border-b bg-gray-50">
                    <div className="flex items-start gap-4">
                      {/* Image */}
                      <div className="w-20 h-20 bg-gray-200 rounded-lg overflow-hidden flex-shrink-0">
                        {listing.images?.[0] ? (
                          <img 
                            src={listing.images[0]} 
                            alt={listing.productName || 'Product'}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Package className="h-8 w-8 text-gray-400" />
                          </div>
                        )}
                      </div>
                      
                      {/* Product Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="group relative">
                            <h3 className="font-semibold text-gray-900 truncate cursor-help" title={listing.productName || ''}>
                              {listing.productName || 'Unnamed Product'}
                            </h3>
                            {/* Hover tooltip for full name + attributes */}
                            <div className="absolute left-0 top-full mt-1 z-20 hidden group-hover:block w-72 p-3 bg-gray-900 text-white text-sm rounded-lg shadow-xl">
                              <p className="font-medium mb-1">{listing.productName}</p>
                              {listing.searchableAttributes && Object.keys(listing.searchableAttributes).length > 0 && (
                                <div className="text-gray-300 text-xs space-y-0.5">
                                  {Object.entries(listing.searchableAttributes).slice(0, 5).map(([key, val]) => (
                                    <p key={key}>{key}: {String(val)}</p>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ${statusColors[listing.status]?.bg} ${statusColors[listing.status]?.text}`}>
                            {statusColors[listing.status]?.icon}
                            {listing.status}
                          </div>
                        </div>
                        
                        {/* Product Summary - FINAL ARCHITECTURE: flat moq field */}
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-600">
                          <span className="flex items-center gap-1">
                            <Package className="h-3.5 w-3.5" />
                            MOQ: {listing.moq || 1} unit
                          </span>
                          <span className="text-gray-300">|</span>
                          <span>{listing.categoryName || 'Uncategorized'}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Quantity-Based Pricing - ALWAYS VISIBLE */}
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-gray-700 flex items-center gap-1">
                        Quantity-Based Pricing
                        <Info className="h-3.5 w-3.5 text-gray-400" />
                      </h4>
                      {listing.pricingTiers && listing.pricingTiers.length > 2 && (
                        <button
                          onClick={() => togglePricing(listing._id)}
                          className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          {expandedPricing.has(listing._id) ? (
                            <>Hide <ChevronUp className="h-3 w-3" /></>
                          ) : (
                            <>Show all ({listing.pricingTiers.length}) <ChevronDown className="h-3 w-3" /></>
                          )}
                        </button>
                      )}
                    </div>

                    {listing.pricingTiers && listing.pricingTiers.length > 0 ? (
                      <div className="border rounded-lg overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="text-left px-3 py-2 text-gray-600 font-medium">Quantity Range</th>
                              <th className="text-right px-3 py-2 text-gray-600 font-medium">Price per Unit</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {(expandedPricing.has(listing._id) 
                              ? listing.pricingTiers 
                              : listing.pricingTiers.slice(0, 2)
                            ).map((tier, index) => (
                              <tr key={index} className="hover:bg-gray-50">
                                <td className="px-3 py-2 text-gray-700">
                                  {formatTierRange(tier)}
                                </td>
                                <td className="px-3 py-2 text-right font-semibold text-gray-900">
                                  {listing.currency === 'INR' ? '₹' : listing.currency}{tier.pricePerUnit.toLocaleString('en-IN')} / unit
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {!expandedPricing.has(listing._id) && listing.pricingTiers.length > 2 && (
                          <div className="px-3 py-1.5 bg-gray-50 text-xs text-gray-500 text-center">
                            +{listing.pricingTiers.length - 2} more price tiers
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-orange-600 py-2">
                        No pricing set - Add price to receive enquiries
                      </div>
                    )}

                    <p className="text-xs text-gray-500 mt-2">
                      Buyers automatically see the best applicable price based on quantity.
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="px-4 pb-4">
                    <div className="flex items-center gap-2 pt-3 border-t">
                      <Link
                        href={`/seller/pricing?listing=${listing._id}`}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-yellow-500 text-white text-sm font-medium rounded-lg hover:bg-yellow-600 transition"
                        title="Edit quantity-wise pricing tiers quickly. Best for frequent rate updates."
                        data-testid={`price-btn-${listing._id}`}
                      >
                        <Zap className="h-4 w-4" />
                        Price
                      </Link>
                      <Link
                        href={`/seller/inquiries?listing=${listing._id}`}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition"
                        title="View buyer enquiries specific to this product. Includes quantity, buyer details, and message."
                        data-testid={`enquiries-btn-${listing._id}`}
                      >
                        <MessageSquare className="h-4 w-4" />
                        Enquiries
                      </Link>
                      <Link
                        href={`/seller/listings/${listing._id}`}
                        className="flex items-center justify-center gap-1.5 px-3 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition"
                        title="Edit full product details including name, attributes, images, and MOQ."
                        data-testid={`edit-btn-${listing._id}`}
                      >
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center">
          <p className="text-gray-600">
            India's trusted B2B marketplace
          </p>
          <p className="text-gray-500 text-sm mt-1">
            Connecting verified buyers and sellers across industries.
          </p>
        </div>
      </footer>
    </div>
  );
}
