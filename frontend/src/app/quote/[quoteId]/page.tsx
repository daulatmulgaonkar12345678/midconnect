'use client';

import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { viewQuote, viewQuotePublic, acceptQuote, rejectQuote } from '@/lib/api';
import type { Quote } from '@/lib/api';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Package,
  Building2,
  Phone,
  Mail,
  MessageSquare,
  ArrowLeft,
  Calendar,
  Truck,
  CreditCard,
  AlertTriangle,
  ExternalLink
} from 'lucide-react';

export default function QuoteViewPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const quoteId = params.quoteId as string;
  const accessToken = searchParams.get('token');
  
  const [quote, setQuote] = useState<Quote | null>(null);
  const [canAccept, setCanAccept] = useState(false);
  const [isExpired, setIsExpired] = useState(false);
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [sellerContact, setSellerContact] = useState<{
    name?: string;
    phone?: string;
    email?: string;
    whatsapp?: string;
  } | null>(null);
  
  // Reject modal
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    const loadQuote = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Try authenticated view first if user is logged in
        if (user && !authLoading) {
          const token = await getIdToken();
          if (token) {
            const data = await viewQuote(token, quoteId, accessToken || undefined);
            setQuote(data.quote);
            setCanAccept(data.canAccept);
            setIsExpired(data.isExpired);
            setRequiresLogin(false);
            return;
          }
        }
        
        // Fall back to public view if access token provided
        if (accessToken) {
          const data = await viewQuotePublic(quoteId, accessToken);
          setQuote(data.quote as Quote);
          setIsExpired(data.isExpired);
          setRequiresLogin(data.requiresLogin);
          setCanAccept(!data.isExpired && !data.requiresLogin);
        } else if (!user && !authLoading) {
          // No token and not logged in - redirect to login
          router.push(`/login?redirect=/quote/${quoteId}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load quote');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      loadQuote();
    }
  }, [quoteId, accessToken, user, authLoading, getIdToken, router]);

  const handleAccept = async () => {
    if (!user) {
      router.push(`/login?redirect=/quote/${quoteId}${accessToken ? `?token=${accessToken}` : ''}`);
      return;
    }

    setActionLoading(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const result = await acceptQuote(token, quoteId);
      
      setQuote(prev => prev ? { ...prev, status: 'accepted' } : null);
      setCanAccept(false);
      setSellerContact(result.sellerContact);
      setSuccess('Quote accepted! Seller contact details are now visible.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept quote');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!user) {
      router.push(`/login?redirect=/quote/${quoteId}${accessToken ? `?token=${accessToken}` : ''}`);
      return;
    }

    setActionLoading(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      await rejectQuote(token, quoteId, rejectReason || undefined);
      
      setQuote(prev => prev ? { ...prev, status: 'rejected' } : null);
      setCanAccept(false);
      setShowRejectModal(false);
      setSuccess('Quote rejected.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject quote');
    } finally {
      setActionLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'sent':
        return <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">New Quote</span>;
      case 'viewed':
        return <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">Viewed</span>;
      case 'accepted':
        return <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium flex items-center gap-1"><CheckCircle className="h-4 w-4" /> Accepted</span>;
      case 'rejected':
        return <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium flex items-center gap-1"><XCircle className="h-4 w-4" /> Rejected</span>;
      case 'expired':
        return <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium flex items-center gap-1"><Clock className="h-4 w-4" /> Expired</span>;
      default:
        return null;
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !quote) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm p-8 max-w-md text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Quote Not Found</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Return to Home
          </Link>
        </div>
      </div>
    );
  }

  if (!quote) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/buyer/quotes" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-gray-900">Quotation</h1>
              <p className="text-sm text-gray-500">Quote ID: {quote.quoteId}</p>
            </div>
            {getStatusBadge(quote.status)}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        {/* Alerts */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700" data-testid="error-alert">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700" data-testid="success-alert">
            <CheckCircle className="h-5 w-5 flex-shrink-0" />
            {success}
          </div>
        )}

        {isExpired && quote.status !== 'expired' && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3 text-yellow-700" data-testid="expired-banner">
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
            This quote has expired and can no longer be accepted.
          </div>
        )}

        {requiresLogin && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg" data-testid="login-banner">
            <p className="text-blue-700 mb-3">Please log in to accept or reject this quote.</p>
            <Link 
              href={`/login?redirect=/quote/${quoteId}${accessToken ? `?token=${accessToken}` : ''}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Log In to Continue
            </Link>
          </div>
        )}

        {/* Product Info */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="product-section">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Package className="h-8 w-8 text-gray-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{quote.productName}</h2>
              <p className="text-gray-600 mt-1">
                <span className="font-medium">Requested Qty:</span> {quote.requestedQuantity}
              </p>
            </div>
          </div>
        </div>

        {/* Seller Info */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="seller-section">
          <div className="flex items-center gap-3 mb-4">
            <Building2 className="h-5 w-5 text-gray-400" />
            <h3 className="font-semibold text-gray-900">Seller</h3>
          </div>
          <p className="text-lg font-medium text-gray-900">{quote.sellerName}</p>
          
          {/* Show seller contact after acceptance */}
          {(quote.status === 'accepted' && sellerContact) && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200" data-testid="seller-contact">
              <p className="text-sm text-green-700 font-medium mb-3">Contact Details (Unlocked)</p>
              <div className="space-y-2">
                {sellerContact.phone && (
                  <a href={`tel:${sellerContact.phone}`} className="flex items-center gap-2 text-blue-600 hover:underline">
                    <Phone className="h-4 w-4" />
                    {sellerContact.phone}
                  </a>
                )}
                {sellerContact.email && (
                  <a href={`mailto:${sellerContact.email}`} className="flex items-center gap-2 text-blue-600 hover:underline">
                    <Mail className="h-4 w-4" />
                    {sellerContact.email}
                  </a>
                )}
                {sellerContact.phone && (
                  <a 
                    href={`https://wa.me/91${sellerContact.phone.replace(/\D/g, '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-green-600 hover:underline"
                  >
                    <MessageSquare className="h-4 w-4" />
                    WhatsApp Seller
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Pricing Details */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="pricing-section">
          <h3 className="font-semibold text-gray-900 mb-4">Pricing Details</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Unit Price</span>
              <span className="font-medium">{formatCurrency(quote.unitPrice)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Minimum Order Quantity (MOQ)</span>
              <span className="font-medium">{quote.moq}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Packaging Charges</span>
              <span className="font-medium">{formatCurrency(quote.packagingCharges)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 flex items-center gap-2">
                <Truck className="h-4 w-4" />
                Transportation Charges
              </span>
              <span className="font-medium text-orange-600">Not Included</span>
            </div>
            
            <hr className="my-4" />
            
            <div className="flex justify-between text-lg">
              <span className="font-semibold text-gray-900">Total (Excl. Transport)</span>
              <span className="font-bold text-blue-600">{formatCurrency(quote.totalPrice)}</span>
            </div>
          </div>
        </div>

        {/* Quote Details */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="details-section">
          <h3 className="font-semibold text-gray-900 mb-4">Quote Details</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Lead Time
              </span>
              <span className="font-medium">{quote.leadTimeDays} days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Valid Till
              </span>
              <span className="font-medium">{formatDate(quote.validityDate)}</span>
            </div>
            {quote.terms && (
              <div className="mt-4">
                <span className="text-gray-600 block mb-2">Terms & Conditions</span>
                <p className="text-gray-900 bg-gray-50 p-3 rounded-lg text-sm">{quote.terms}</p>
              </div>
            )}
            {quote.customMessage && (
              <div className="mt-4">
                <span className="text-gray-600 block mb-2">Message from Seller</span>
                <p className="text-gray-900 bg-blue-50 p-3 rounded-lg text-sm">{quote.customMessage}</p>
              </div>
            )}
          </div>
        </div>

        {/* Payment Banner */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 mb-6 border border-blue-100" data-testid="payment-banner">
          <div className="flex items-center gap-3">
            <CreditCard className="h-6 w-6 text-blue-600" />
            <div>
              <p className="font-medium text-gray-900">Online payments coming soon</p>
              <p className="text-sm text-gray-600">Pay securely on the platform - launching soon!</p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        {canAccept && !requiresLogin && quote.status !== 'accepted' && quote.status !== 'rejected' && (
          <div className="flex gap-4" data-testid="action-buttons">
            <button
              onClick={handleAccept}
              disabled={actionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:opacity-50 font-medium text-lg"
              data-testid="accept-btn"
            >
              {actionLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <CheckCircle className="h-5 w-5" />
              )}
              Accept Quote
            </button>
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={actionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 disabled:opacity-50 font-medium text-lg"
              data-testid="reject-btn"
            >
              <XCircle className="h-5 w-5" />
              Reject Quote
            </button>
          </div>
        )}

        {/* Quote Info */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Quote created on {formatDate(quote.createdAt)}</p>
        </div>
      </main>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl p-6" data-testid="reject-modal">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              Reject Quote
            </h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Reason (optional)
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                rows={3}
                placeholder="Let the seller know why..."
                maxLength={500}
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium"
                data-testid="confirm-reject-btn"
              >
                {actionLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <XCircle className="h-5 w-5" />}
                Reject
              </button>
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
