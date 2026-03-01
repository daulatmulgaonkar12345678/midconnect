'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { 
  Search, BadgeCheck, MapPin, Package, Star, Shield, 
  ChevronLeft, ChevronRight, Loader2, AlertCircle 
} from 'lucide-react';

// Ensure API_URL always ends with /api
const getApiUrl = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'https://midconnect.onrender.com';
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
};
const API_URL = getApiUrl();

interface Seller {
  _id: string;
  email: string;
  businessName: string;
  phone: string;
  gstNumber: string;
  gstVerified: boolean;
  badgeType: 'none' | 'choice' | 'trusted';
  city: string;
  state: string;
  status: string;
  createdAt: string;
}

const BADGE_OPTIONS = [
  { value: 'none', label: 'No Badge', icon: null, color: 'gray' },
  { value: 'choice', label: 'UdyogConnect Choice', icon: Star, color: 'yellow' },
  { value: 'trusted', label: 'UdyogConnect Trusted', icon: Shield, color: 'green' },
];

export default function AdminSellersPage() {
  const { getIdToken } = useAuth();
  const router = useRouter();
  
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [badgeFilter, setBadgeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [updatingBadge, setUpdatingBadge] = useState<string | null>(null);

  const fetchSellers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }

      const params = new URLSearchParams({
        page: page.toString(),
        limit: '20',
      });
      if (searchQuery) params.append('search', searchQuery);
      if (badgeFilter) params.append('badgeFilter', badgeFilter);

      const res = await fetch(`${API_URL}/admin/sellers?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw new Error('Failed to fetch sellers');

      const data = await res.json();
      setSellers(data.sellers || []);
      setTotalPages(data.totalPages || 1);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to fetch sellers:', err);
      setError('Failed to load sellers. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [getIdToken, router, page, searchQuery, badgeFilter]);

  useEffect(() => {
    fetchSellers();
  }, [fetchSellers]);

  const handleBadgeChange = async (sellerId: string, newBadge: string) => {
    setUpdatingBadge(sellerId);
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const res = await fetch(`${API_URL}/admin/sellers/${sellerId}/badge`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ badgeType: newBadge })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to update badge');
      }

      // Update local state
      setSellers(prev => prev.map(s => 
        s._id === sellerId ? { ...s, badgeType: newBadge as Seller['badgeType'] } : s
      ));
    } catch (err) {
      console.error('Failed to update badge:', err);
      alert('Failed to update badge. Please try again.');
    } finally {
      setUpdatingBadge(null);
    }
  };

  const getBadgeDisplay = (badgeType: string) => {
    switch (badgeType) {
      case 'choice':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800">
            <Star className="h-3 w-3" />
            Choice
          </span>
        );
      case 'trusted':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
            <Shield className="h-3 w-3" />
            Trusted
          </span>
        );
      default:
        return (
          <span className="text-xs text-gray-400">No Badge</span>
        );
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Seller Management</h1>
          <p className="text-gray-500">Manage sellers and assign badges</p>
        </div>
        <div className="text-sm text-gray-500">
          Total: {total} sellers
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by business name, email, or GST..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full pl-12 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          {/* Badge Filter */}
          <select
            value={badgeFilter}
            onChange={(e) => {
              setBadgeFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Badges</option>
            <option value="none">No Badge</option>
            <option value="choice">UdyogConnect Choice</option>
            <option value="trusted">UdyogConnect Trusted</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-16">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
          <p className="text-gray-500 mt-4">Loading sellers...</p>
        </div>
      ) : sellers.length > 0 ? (
        <>
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Business</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">GST</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current Badge</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assign Badge</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sellers.map((seller) => (
                    <tr key={seller._id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900">{seller.businessName || 'N/A'}</p>
                          <p className="text-sm text-gray-500">{seller.email}</p>
                          {seller.phone && (
                            <p className="text-xs text-gray-400">{seller.phone}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {seller.city || seller.state ? (
                          <div className="flex items-center gap-1 text-sm text-gray-500">
                            <MapPin className="h-4 w-4" />
                            {[seller.city, seller.state].filter(Boolean).join(', ')}
                          </div>
                        ) : (
                          <span className="text-gray-400 text-sm">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {seller.gstNumber ? (
                          <div>
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                              seller.gstVerified
                                ? 'bg-green-100 text-green-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {seller.gstVerified && <BadgeCheck className="h-3 w-3" />}
                              {seller.gstVerified ? 'Verified' : 'Pending'}
                            </span>
                            <p className="text-xs text-gray-400 mt-1 font-mono">{seller.gstNumber}</p>
                          </div>
                        ) : (
                          <span className="text-gray-400 text-sm">Not Submitted</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {getBadgeDisplay(seller.badgeType)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="relative">
                          <select
                            value={seller.badgeType || 'none'}
                            onChange={(e) => handleBadgeChange(seller._id, e.target.value)}
                            disabled={updatingBadge === seller._id}
                            className={`px-3 py-1.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 ${
                              updatingBadge === seller._id ? 'opacity-50 cursor-wait' : ''
                            }`}
                          >
                            {BADGE_OPTIONS.map(opt => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                          {updatingBadge === seller._id && (
                            <Loader2 className="absolute right-8 top-2 h-4 w-4 animate-spin text-blue-500" />
                          )}
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
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-xl shadow-sm p-16 text-center">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Sellers Found</h3>
          <p className="text-gray-500">
            {searchQuery || badgeFilter ? 'Try different search criteria' : 'No registered sellers yet'}
          </p>
        </div>
      )}
    </div>
  );
}
