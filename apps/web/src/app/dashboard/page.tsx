'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import RoleGuard from '@/components/RoleGuard';
import Link from 'next/link';
import { getSellerListings, getSellerStats, ApiError, SellerListing, SellerStats } from '@/lib/api';
import { Package, Plus, Eye, Edit, BarChart3, AlertCircle, Loader2, ChevronDown, ChevronRight, FolderOpen } from 'lucide-react';

export default function DashboardPage() {
  return (
    <RoleGuard allowedRoles={['seller', 'admin']}>
      <DashboardContent />
    </RoleGuard>
  );
}

interface CategoryGroup {
  categoryName: string;
  categoryId: string;
  listings: SellerListing[];
  expanded: boolean;
}

function DashboardContent() {
  const { getIdToken, profile } = useAuth();
  const [categoryGroups, setCategoryGroups] = useState<CategoryGroup[]>([]);
  const [stats, setStats] = useState<SellerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const [listingsData, statsData] = await Promise.all([
        getSellerListings(token, { limit: 100 }),
        getSellerStats(token),
      ]);

      // Group listings by category
      const groups: Record<string, CategoryGroup> = {};
      
      for (const listing of listingsData.listings || []) {
        const catId = listing.categoryId || 'uncategorized';
        const catName = listing.categoryName || 'Uncategorized';
        
        if (!groups[catId]) {
          groups[catId] = {
            categoryId: catId,
            categoryName: catName,
            listings: [],
            expanded: true // Default expanded
          };
        }
        groups[catId].listings.push(listing);
      }

      // Sort groups by category name
      const sortedGroups = Object.values(groups).sort((a, b) => 
        a.categoryName.localeCompare(b.categoryName)
      );

      setCategoryGroups(sortedGroups);
      setStats(statsData || null);
    } catch (err) {
      const message = err instanceof ApiError ? err.getUserMessage() : 'Failed to load dashboard';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (categoryId: string) => {
    setCategoryGroups(prev => prev.map(group => 
      group.categoryId === categoryId 
        ? { ...group, expanded: !group.expanded }
        : group
    ));
  };

  const getStatusBadge = (status: string) => {
    const statusLower = status?.toLowerCase() || 'draft';
    switch (statusLower) {
      case 'published':
      case 'active':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700">Active</span>;
      case 'draft':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">Draft</span>;
      case 'paused':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">Paused</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600" />
        <p className="mt-4 text-gray-500">Loading dashboard...</p>
      </div>
    );
  }

  const totalListings = categoryGroups.reduce((sum, g) => sum + g.listings.length, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Seller Dashboard</h1>
          <p className="text-gray-500">Welcome back, {profile?.businessName || profile?.email}</p>
        </div>
        <Link
          href="/seller/listings/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
          data-testid="new-listing-btn"
        >
          <Plus className="h-5 w-5" /> New Listing
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center gap-3">
              <div className="bg-blue-100 p-3 rounded-lg">
                <Package className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.totalListings}</p>
                <p className="text-sm text-gray-500">Total Listings</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center gap-3">
              <div className="bg-green-100 p-3 rounded-lg">
                <Eye className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.publishedListings}</p>
                <p className="text-sm text-gray-500">Published</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center gap-3">
              <div className="bg-yellow-100 p-3 rounded-lg">
                <BarChart3 className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.totalEnquiries}</p>
                <p className="text-sm text-gray-500">Total Enquiries</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center gap-3">
              <div className="bg-purple-100 p-3 rounded-lg">
                <BarChart3 className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.thisMonthEnquiries}</p>
                <p className="text-sm text-gray-500">This Month</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Listings Grouped by Category */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">My Listings</h2>
          <span className="text-sm text-gray-500">{totalListings} product(s) in {categoryGroups.length} categories</span>
        </div>

        {categoryGroups.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {categoryGroups.map((group) => (
              <div key={group.categoryId} data-testid={`category-group-${group.categoryId}`}>
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(group.categoryId)}
                  className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition"
                >
                  <div className="flex items-center gap-3">
                    {group.expanded ? (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    )}
                    <FolderOpen className="h-5 w-5 text-blue-600" />
                    <span className="font-medium text-gray-900">{group.categoryName}</span>
                    <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                      {group.listings.length} product{group.listings.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                </button>

                {/* Listings in Category */}
                {group.expanded && (
                  <div className="divide-y divide-gray-100">
                    {group.listings.map((listing) => (
                      <div 
                        key={listing._id} 
                        className="px-6 py-4 pl-14 flex items-center justify-between hover:bg-gray-50"
                        data-testid={`listing-row-${listing._id}`}
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden">
                            {listing.images?.[0] ? (
                              <img
                                src={listing.images[0]}
                                alt={listing.productName}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Package className="h-6 w-6 text-gray-400" />
                            )}
                          </div>
                          <div>
                            <h3 className="font-medium text-gray-900">{listing.productName}</h3>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span>MOQ: {listing.moq || 1}</span>
                              {listing.pricingTiers?.[0] && (
                                <span>₹{listing.pricingTiers[0].pricePerUnit?.toLocaleString()}/unit</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {getStatusBadge(listing.status)}
                          <Link
                            href={`/seller/listings/${listing._id}`}
                            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                          >
                            <Edit className="h-5 w-5" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-12 text-center">
            <Package className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No listings yet</h3>
            <p className="text-gray-500 mb-4">Start selling by creating your first product listing</p>
            <Link
              href="/seller/listings/new"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-5 w-5" /> Create Listing
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
