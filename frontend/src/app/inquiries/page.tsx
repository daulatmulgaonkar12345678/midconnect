'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { ClipboardList, Package, Calendar, MapPin, Building2, ArrowRight, Loader2 } from 'lucide-react';

// API base URL
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const publicUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (publicUrl && publicUrl.startsWith('http')) return publicUrl;
    if (window.location.hostname.includes('vercel.app')) {
      return 'https://b2b-marketplace-v2.preview.emergentagent.com';
    }
    return '';
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || '';
};

interface Inquiry {
  _id: string;
  productId: string;
  productName: string;
  sellerId: string;
  sellerName: string;
  quantity: number;
  message: string;
  status: 'pending' | 'responded' | 'quoted' | 'closed';
  createdAt: string;
  quotation?: {
    pricePerUnit: number;
    totalAmount: number;
    validUntil: string;
  };
}

export default function InquiriesPage() {
  const { user, loading: authLoading } = useAuth();
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInquiries = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        const apiBase = getApiBaseUrl();
        const token = await user.getIdToken();
        const res = await fetch(`${apiBase}/api/inquiries/buyer`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
          const data = await res.json();
          setInquiries(Array.isArray(data) ? data : []);
        } else {
          setError('Failed to fetch inquiries');
        }
      } catch (err) {
        console.error('Error fetching inquiries:', err);
        setError('Failed to load inquiries');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      fetchInquiries();
    }
  }, [user, authLoading]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'responded': return 'bg-blue-100 text-blue-800';
      case 'quoted': return 'bg-green-100 text-green-800';
      case 'closed': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <ClipboardList className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Track Your Inquiries</h1>
        <p className="text-gray-600 mb-6">Login to view and manage your product inquiries</p>
        <div className="flex gap-4 justify-center">
          <Link href="/login" className="px-6 py-3 bg-[#0B3C5D] text-white rounded-md hover:bg-[#083047] transition-colors">
            Login
          </Link>
          <Link href="/register" className="px-6 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors">
            Register
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">My Inquiries</h1>
        <p className="text-gray-600 mt-1">Track and manage your product inquiries</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {inquiries.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <ClipboardList className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Inquiries Yet</h2>
          <p className="text-gray-600 mb-6">Start browsing products and send inquiries to sellers</p>
          <Link href="/products" className="inline-flex items-center gap-2 px-6 py-3 bg-[#0B3C5D] text-white rounded-md hover:bg-[#083047] transition-colors">
            Browse Products <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {inquiries.map((inquiry) => (
            <div key={inquiry._id} className="bg-white border rounded-xl p-6 hover:shadow-md transition-shadow">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                {/* Left: Product Info */}
                <div className="flex-1">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Package className="h-5 w-5 text-gray-500" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{inquiry.productName}</h3>
                      <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                        <Building2 className="h-4 w-4" />
                        <span>{inquiry.sellerName || 'Seller'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Quantity</span>
                      <p className="font-medium text-gray-900">{inquiry.quantity} units</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Date</span>
                      <p className="font-medium text-gray-900">{formatDate(inquiry.createdAt)}</p>
                    </div>
                    {inquiry.quotation && (
                      <div>
                        <span className="text-gray-500">Quote</span>
                        <p className="font-medium text-green-600">₹{inquiry.quotation.totalAmount.toLocaleString()}</p>
                      </div>
                    )}
                  </div>

                  {inquiry.message && (
                    <p className="mt-3 text-sm text-gray-600 line-clamp-2">{inquiry.message}</p>
                  )}
                </div>

                {/* Right: Status */}
                <div className="flex sm:flex-col items-center sm:items-end gap-3">
                  <span className={`px-3 py-1 text-xs font-medium rounded-full capitalize ${getStatusColor(inquiry.status)}`}>
                    {inquiry.status}
                  </span>
                  <Link 
                    href={`/product/${inquiry.productId}`}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    View Product →
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
