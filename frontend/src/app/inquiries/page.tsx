'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { 
  ClipboardList, 
  Package, 
  Building2, 
  ArrowRight, 
  Loader2,
  Phone,
  Mail,
  MessageCircle,
  CheckCircle2,
  Clock,
  XCircle,
  ExternalLink
} from 'lucide-react';
import { getBuyerInquiries } from '@/lib/api';

interface Inquiry {
  _id: string;
  productId: string | null;
  productName: string;
  listing?: {
    name?: string;
    image?: string;
    category?: string;
  };
  seller: {
    businessName: string;
    city?: string;
    state?: string;
    phone?: string;
    email?: string;
    whatsapp?: string;
  };
  quantity: number;
  message: string;
  status: 'pending' | 'accepted' | 'rejected' | 'reported';
  createdAt: string;
  sellerResponse?: {
    quotedPrice?: number;
    message?: string;
  };
}

export default function InquiriesPage() {
  const { user, loading: authLoading, getIdToken } = useAuth();
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
        const token = await getIdToken();
        if (!token) throw new Error('Not authenticated');
        
        const data = await getBuyerInquiries(token);
        
        // Map the API response to local interface
        const mappedInquiries: Inquiry[] = (data.inquiries || []).map((inq: any) => ({
          _id: inq._id || '',
          productId: inq.productId || null,
          productName: inq.productName || inq.listing?.name || 'Product',
          listing: inq.listing,
          seller: {
            businessName: inq.seller?.businessName || 'Seller',
            city: inq.seller?.city,
            state: inq.seller?.state,
            phone: inq.seller?.phone,
            email: inq.seller?.email,
            whatsapp: inq.seller?.whatsapp || inq.seller?.phone,
          },
          quantity: inq.quantity || 0,
          message: inq.message || '',
          status: inq.status || 'pending',
          createdAt: inq.createdAt || '',
          sellerResponse: inq.sellerResponse,
        }));
        
        setInquiries(mappedInquiries);
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
  }, [user, authLoading, getIdToken]);

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'pending':
        return { 
          color: 'bg-yellow-100 text-yellow-800', 
          icon: Clock,
          label: 'Pending'
        };
      case 'accepted':
        return { 
          color: 'bg-green-100 text-green-800', 
          icon: CheckCircle2,
          label: 'Accepted'
        };
      case 'rejected':
        return { 
          color: 'bg-red-100 text-red-800', 
          icon: XCircle,
          label: 'Rejected'
        };
      case 'reported':
        return { 
          color: 'bg-gray-100 text-gray-800', 
          icon: ClipboardList,
          label: 'Reported'
        };
      default:
        return { 
          color: 'bg-gray-100 text-gray-800', 
          icon: Clock,
          label: status
        };
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const openWhatsApp = (phone: string, productName: string, quantity: number) => {
    const cleanPhone = phone.replace(/\D/g, '');
    const finalPhone = cleanPhone.startsWith('91') ? cleanPhone : `91${cleanPhone}`;
    const message = `Hi, I sent an inquiry for ${productName} (Qty: ${quantity}) on MidConnect. I'd like to discuss further.`;
    window.open(`https://wa.me/${finalPhone}?text=${encodeURIComponent(message)}`, '_blank');
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
          {inquiries.map((inquiry) => {
            const statusConfig = getStatusConfig(inquiry.status);
            const StatusIcon = statusConfig.icon;
            
            return (
              <div 
                key={inquiry._id} 
                className="bg-white border rounded-xl p-6 hover:shadow-md transition-shadow"
                data-testid={`inquiry-card-${inquiry._id}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  {/* Left: Product & Seller Info */}
                  <div className="flex-1">
                    {/* Product Name with Link */}
                    <div className="flex items-start gap-3">
                      {inquiry.listing?.image ? (
                        <img 
                          src={inquiry.listing.image} 
                          alt={inquiry.productName}
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Package className="h-6 w-6 text-gray-400" />
                        </div>
                      )}
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {inquiry.productId ? (
                            <Link 
                              href={`/product/${inquiry.productId}`}
                              className="hover:text-blue-600 transition-colors"
                              data-testid={`product-link-${inquiry._id}`}
                            >
                              {inquiry.productName}
                            </Link>
                          ) : (
                            inquiry.productName
                          )}
                        </h3>
                        <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                          <Building2 className="h-4 w-4" />
                          <span>{inquiry.seller.businessName}</span>
                          {(inquiry.seller.city || inquiry.seller.state) && (
                            <span className="text-gray-400">
                              • {[inquiry.seller.city, inquiry.seller.state].filter(Boolean).join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Inquiry Details */}
                    <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Quantity</span>
                        <p className="font-medium text-gray-900">{inquiry.quantity} units</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Date</span>
                        <p className="font-medium text-gray-900">{formatDate(inquiry.createdAt)}</p>
                      </div>
                      {inquiry.sellerResponse?.quotedPrice && (
                        <div>
                          <span className="text-gray-500">Quoted Price</span>
                          <p className="font-medium text-green-600">
                            ₹{inquiry.sellerResponse.quotedPrice.toLocaleString('en-IN')} /unit
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Inquiry Message */}
                    {inquiry.message && (
                      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Your Message</p>
                        <p className="text-sm text-gray-700 line-clamp-2">{inquiry.message}</p>
                      </div>
                    )}

                    {/* Seller Response (if accepted) */}
                    {inquiry.status === 'accepted' && inquiry.sellerResponse?.message && (
                      <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200">
                        <p className="text-xs text-green-700 font-medium mb-1">Seller Response</p>
                        <p className="text-sm text-gray-700">{inquiry.sellerResponse.message}</p>
                      </div>
                    )}

                    {/* Seller Contact Details (only when accepted) */}
                    {inquiry.status === 'accepted' && (inquiry.seller.phone || inquiry.seller.email) && (
                      <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                        <p className="text-sm font-medium text-blue-800 mb-3">Seller Contact Details</p>
                        <div className="flex flex-wrap gap-3">
                          {inquiry.seller.phone && (
                            <>
                              <a 
                                href={`tel:${inquiry.seller.phone}`}
                                className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-blue-200 rounded-lg text-sm text-blue-700 hover:bg-blue-100 transition-colors"
                              >
                                <Phone className="h-4 w-4" />
                                {inquiry.seller.phone}
                              </a>
                              <button
                                onClick={() => openWhatsApp(
                                  inquiry.seller.phone || '',
                                  inquiry.productName,
                                  inquiry.quantity
                                )}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
                                data-testid={`whatsapp-btn-${inquiry._id}`}
                              >
                                <MessageCircle className="h-4 w-4" />
                                WhatsApp
                              </button>
                            </>
                          )}
                          {inquiry.seller.email && (
                            <a 
                              href={`mailto:${inquiry.seller.email}`}
                              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-blue-200 rounded-lg text-sm text-blue-700 hover:bg-blue-100 transition-colors"
                            >
                              <Mail className="h-4 w-4" />
                              {inquiry.seller.email}
                            </a>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Status Messages */}
                    {inquiry.status === 'pending' && (
                      <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                        <p className="text-sm text-yellow-800 flex items-center gap-2">
                          <Clock className="h-4 w-4" />
                          Waiting for seller to respond to your inquiry
                        </p>
                      </div>
                    )}
                    {inquiry.status === 'rejected' && (
                      <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
                        <p className="text-sm text-red-800 flex items-center gap-2">
                          <XCircle className="h-4 w-4" />
                          The seller has declined this inquiry
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Right: Status & View Product */}
                  <div className="flex sm:flex-col items-center sm:items-end gap-3">
                    <span className={`px-3 py-1.5 text-xs font-medium rounded-full flex items-center gap-1.5 ${statusConfig.color}`}>
                      <StatusIcon className="h-3.5 w-3.5" />
                      {statusConfig.label}
                    </span>
                    
                    {/* View Product Link */}
                    {inquiry.productId ? (
                      <Link 
                        href={`/product/${inquiry.productId}`}
                        className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        data-testid={`view-product-${inquiry._id}`}
                      >
                        View Product
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Link>
                    ) : (
                      <span className="text-sm text-gray-400">
                        Product unavailable
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
