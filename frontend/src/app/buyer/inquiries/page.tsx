'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getBuyerInquiries } from '@/lib/api';
import type { BuyerInquiry } from '@/types';
import { 
  Loader2, 
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MessageSquare,
  Package,
  Building2,
  MapPin,
  Phone,
  Mail,
  ExternalLink,
  Filter
} from 'lucide-react';

const statusConfig = {
  pending: { 
    label: 'Pending', 
    color: 'bg-yellow-100 text-yellow-800',
    icon: Clock,
    description: 'Waiting for seller response'
  },
  accepted: { 
    label: 'Accepted', 
    color: 'bg-green-100 text-green-800',
    icon: CheckCircle2,
    description: 'Seller has accepted your inquiry'
  },
  rejected: { 
    label: 'Rejected', 
    color: 'bg-red-100 text-red-800',
    icon: XCircle,
    description: 'Seller has declined'
  },
  reported: { 
    label: 'Reported', 
    color: 'bg-gray-100 text-gray-800',
    icon: AlertTriangle,
    description: 'Under review'
  }
};

export default function BuyerInquiriesPage() {
  const router = useRouter();
  const { getIdToken, isAuthenticated, loading: authLoading } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inquiries, setInquiries] = useState<BuyerInquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login?redirect=/buyer/inquiries');
      return;
    }

    loadInquiries();
  }, [isAuthenticated, authLoading, page, statusFilter]);

  async function loadInquiries() {
    try {
      setLoading(true);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const data = await getBuyerInquiries(token, {
        status: statusFilter || undefined,
        page,
        limit: 20
      });
      
      setInquiries(data?.inquiries ?? []);
      setTotal(data?.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inquiries');
    } finally {
      setLoading(false);
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const openWhatsApp = (phone: string, productName?: string, quantity?: number) => {
    const message = encodeURIComponent(
      `Hi, I sent an inquiry for ${productName || 'your product'} (Qty: ${quantity || 'N/A'}) on MidConnect. I'd like to discuss further.`
    );
    window.open(`https://wa.me/${phone.replace(/[^0-9]/g, '')}?text=${message}`, '_blank');
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
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-gray-600 hover:text-gray-900">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900">My Inquiries</h1>
                <p className="text-sm text-gray-500">Track your product inquiries</p>
              </div>
            </div>
            
            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="status-filter"
              >
                <option value="">All Status</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {inquiries.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <MessageSquare className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No inquiries yet</h3>
            <p className="text-gray-500 mb-6">
              When you send inquiries to sellers, they will appear here.
            </p>
            <Link
              href="/products"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 transition"
            >
              <Package className="h-5 w-5" />
              Browse Products
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {inquiries.map((inquiry) => {
              const status = statusConfig[inquiry.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              
              // Get product/listing name - camelCase fields
              const productName = inquiry.productName || inquiry.listing?.name || 'Product Inquiry';
              
              return (
                <div 
                  key={inquiry._id} 
                  className="bg-white rounded-xl shadow-sm overflow-hidden"
                  data-testid={`inquiry-card-${inquiry._id}`}
                >
                  {/* Header */}
                  <div className="p-4 border-b flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {inquiry.listing?.image ? (
                        <img 
                          src={inquiry.listing.image} 
                          alt={productName}
                          className="w-12 h-12 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                          <Package className="h-6 w-6 text-gray-400" />
                        </div>
                      )}
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {productName}
                        </h3>
                        <p className="text-sm text-gray-500">
                          Qty: {inquiry.quantity} units
                        </p>
                      </div>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1.5 ${status.color}`}>
                      <StatusIcon className="h-4 w-4" />
                      {status.label}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      {/* Seller Info - camelCase fields */}
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Seller</p>
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-gray-400" />
                          <span className="font-medium text-gray-900">
                            {inquiry.seller.businessName}
                          </span>
                        </div>
                        {(inquiry.seller.city || inquiry.seller.state) && (
                          <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                            <MapPin className="h-3.5 w-3.5" />
                            {[inquiry.seller.city, inquiry.seller.state].filter(Boolean).join(', ')}
                          </div>
                        )}
                      </div>

                      {/* Date - camelCase createdAt */}
                      <div className="text-right">
                        <p className="text-xs text-gray-500 mb-1">Sent on</p>
                        <p className="text-sm text-gray-700">
                          {inquiry.createdAt ? formatDate(inquiry.createdAt) : 'N/A'}
                        </p>
                      </div>
                    </div>

                    {/* Message */}
                    {inquiry.message && (
                      <div className="bg-gray-50 rounded-lg p-3 mb-4">
                        <p className="text-xs text-gray-500 mb-1">Your message</p>
                        <p className="text-sm text-gray-700">{inquiry.message}</p>
                      </div>
                    )}

                    {/* Seller Response (if accepted) - camelCase sellerResponse */}
                    {inquiry.status === 'accepted' && inquiry.sellerResponse && (
                      <div className="bg-green-50 rounded-lg p-3 mb-4 border border-green-200">
                        <p className="text-xs text-green-700 font-medium mb-1">Seller Response</p>
                        {inquiry.sellerResponse.quotedPrice && (
                          <p className="text-sm text-gray-900">
                            Quoted Price: <span className="font-semibold">₹{inquiry.sellerResponse.quotedPrice.toLocaleString('en-IN')}</span>
                          </p>
                        )}
                        {inquiry.sellerResponse.message && (
                          <p className="text-sm text-gray-700 mt-1">{inquiry.sellerResponse.message}</p>
                        )}
                      </div>
                    )}

                    {/* Contact Info (only if accepted) */}
                    {inquiry.status === 'accepted' && (inquiry.seller.phone || inquiry.seller.email) && (
                      <div className="flex flex-wrap gap-3 pt-3 border-t">
                        {inquiry.seller.phone && (
                          <>
                            <a 
                              href={`tel:${inquiry.seller.phone}`}
                              className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                            >
                              <Phone className="h-4 w-4" />
                              {inquiry.seller.phone}
                            </a>
                            <button
                              onClick={() => openWhatsApp(
                                inquiry.seller.phone || '',
                                productName,
                                inquiry.quantity
                              )}
                              className="flex items-center gap-2 bg-green-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-green-700 transition"
                              data-testid="whatsapp-btn"
                            >
                              <ExternalLink className="h-4 w-4" />
                              WhatsApp
                            </button>
                          </>
                        )}
                        {inquiry.seller.email && (
                          <a 
                            href={`mailto:${inquiry.seller.email}`}
                            className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                          >
                            <Mail className="h-4 w-4" />
                            {inquiry.seller.email}
                          </a>
                        )}
                      </div>
                    )}

                    {/* Status Messages */}
                    {inquiry.status === 'pending' && (
                      <p className="text-sm text-yellow-700 bg-yellow-50 rounded-lg p-3 flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        Waiting for seller to respond to your inquiry
                      </p>
                    )}
                    {inquiry.status === 'rejected' && (
                      <p className="text-sm text-red-700 bg-red-50 rounded-lg p-3 flex items-center gap-2">
                        <XCircle className="h-4 w-4" />
                        The seller has declined this inquiry
                      </p>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Pagination */}
            {total > 20 && (
              <div className="flex justify-center gap-2 pt-4">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 border rounded-lg disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-gray-600">
                  Page {page}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={inquiries.length < 20}
                  className="px-4 py-2 border rounded-lg disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
