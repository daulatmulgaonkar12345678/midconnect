'use client';

import { useState, useEffect } from 'react';
import { Search, BadgeCheck, MapPin, Package } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://midconnect-fix.preview.emergentagent.com/api';

interface Seller {
  _id: string;
  email: string;
  name: string;
  businessName: string;
  city: string;
  state: string;
  gstStatus: string;
  isSeller: boolean;
  listingCount?: number;
}

export default function SellersPage() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchSellers();
  }, []);

  const fetchSellers = async () => {
    try {
      // This would need admin API
      // Placeholder for now
      setSellers([]);
    } catch (error) {
      console.error('Failed to fetch sellers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredSellers = sellers.filter(seller =>
    seller.businessName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    seller.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sellers</h1>
          <p className="text-gray-500">Manage registered sellers</p>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-3 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by business name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      ) : filteredSellers.length > 0 ? (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Business</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">GST Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Listings</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredSellers.map((seller) => (
                <tr key={seller._id}>
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{seller.businessName || 'N/A'}</p>
                      <p className="text-sm text-gray-500">{seller.email}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-sm text-gray-500">
                      <MapPin className="h-4 w-4" />
                      {seller.city}, {seller.state}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                      seller.gstStatus === 'verified'
                        ? 'bg-green-100 text-green-800'
                        : seller.gstStatus === 'pending'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {seller.gstStatus === 'verified' && <BadgeCheck className="h-3 w-3" />}
                      {seller.gstStatus || 'Not Submitted'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-sm">
                      <Package className="h-4 w-4 text-gray-400" />
                      {seller.listingCount || 0}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <button className="text-blue-600 hover:underline text-sm">
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm p-16 text-center">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Sellers Found</h3>
          <p className="text-gray-500">
            {searchQuery ? 'Try a different search term' : 'No registered sellers yet'}
          </p>
        </div>
      )}
    </div>
  );
}
