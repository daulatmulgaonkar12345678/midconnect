'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getSellerInquiries,
  acceptInquiry,
  rejectInquiry,
  reportInquiry
} from '@/lib/api';
import type { SellerInquiry } from '@/types';
import { 
  Loader2, 
  AlertCircle, 
  ArrowLeft,
  MessageSquare,
  Package,
  Check,
  X,
  Flag,
  MapPin,
  Building2,
  Clock,
  Phone,
  Mail,
  Send,
  AlertTriangle,
  Bell,
  RefreshCw
} from 'lucide-react';
import Link from 'next/link';

type InquiryStatus = 'pending' | 'accepted' | 'rejected' | 'reported' | '';

const statusTabs: { value: InquiryStatus; label: string; color: string }[] = [
  { value: '', label: 'All', color: 'bg-gray-100 text-gray-700' },
  { value: 'pending', label: 'Pending', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'accepted', label: 'Accepted', color: 'bg-green-100 text-green-700' },
  { value: 'rejected', label: 'Rejected', color: 'bg-red-100 text-red-700' },
  { value: 'reported', label: 'Reported', color: 'bg-orange-100 text-orange-700' }
];

const rejectionReasons = [
  { value: 'price_too_low', label: 'Price expectation too low' },
  { value: 'not_available', label: 'Product not available' },
  { value: 'moq_issue', label: 'Quantity below MOQ' },
  { value: 'location_not_serviceable', label: 'Location not serviceable' },
  { value: 'capacity_full', label: 'Capacity full' },
  { value: 'other', label: 'Other reason' }
];

const reportTypes = [
  { value: 'spam', label: 'Spam inquiry' },
  { value: 'unrealistic_quantity', label: 'Unrealistic quantity' },
  { value: 'fake_inquiry', label: 'Fake/Test inquiry' },
  { value: 'abusive', label: 'Abusive content' },
  { value: 'other', label: 'Other' }
];

const buyerTypeLabels: Record<string, string> = {
  trader: 'Trader',
  contractor: 'Contractor',
  oem: 'OEM',
  manufacturer: 'Manufacturer',
  other: 'Other'
};

export default function SellerInquiriesPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [inquiries, setInquiries] = useState<SellerInquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<InquiryStatus>('');
  
  // New inquiry notification state
  const [hasNewInquiry, setHasNewInquiry] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const previousTotalRef = useRef(0);
  
  // Action states
  const [actionInquiryId, setActionInquiryId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<'accept' | 'reject' | 'report' | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Accept form
  const [quotedPrice, setQuotedPrice] = useState<number>(0);
  const [quoteMoq, setQuoteMoq] = useState<number | ''>('');
  const [quoteLeadTime, setQuoteLeadTime] = useState<number | ''>('');
  const [quoteValidity, setQuoteValidity] = useState<number>(7);
  const [quoteNote, setQuoteNote] = useState('');
  
  // Reject form
  const [rejectReason, setRejectReason] = useState('');
  const [rejectNote, setRejectNote] = useState('');
  
  // Report form
  const [reportType, setReportType] = useState('');
  const [reportDetails, setReportDetails] = useState('');

  const loadInquiries = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }
      
      const data = await getSellerInquiries(token, {
        status: statusFilter || undefined,
        page,
        limit: 20
      });
      
      const newTotal = data?.total ?? 0;
      const newUnreadCount = data?.unreadCount ?? 0;
      
      // Check for new inquiries (only if we've loaded before)
      if (previousTotalRef.current > 0 && newTotal > previousTotalRef.current) {
        setHasNewInquiry(true);
      }
      previousTotalRef.current = newTotal;
      
      setInquiries(data?.inquiries ?? []);
      setTotal(newTotal);
      setUnreadCount(newUnreadCount);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inquiries');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router, statusFilter, page]);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadInquiries();
      }
    }
  }, [user, authLoading, loadInquiries, router]);

  // Polling for new inquiries every 30 seconds
  useEffect(() => {
    if (!user || authLoading) return;
    
    const interval = setInterval(() => {
      loadInquiries();
    }, 30000);

    return () => clearInterval(interval);
  }, [user, authLoading, loadInquiries]);

  const handleRefresh = () => {
    setHasNewInquiry(false);
    setLoading(true);
    loadInquiries();
  };

  const openAction = (inquiryId: string, type: 'accept' | 'reject' | 'report') => {
    setActionInquiryId(inquiryId);
    setActionType(type);
    setError(null);
    
    // Reset forms
    if (type === 'accept') {
      setQuotedPrice(0);
      setQuoteMoq('');
      setQuoteLeadTime('');
      setQuoteValidity(7);
      setQuoteNote('');
    } else if (type === 'reject') {
      setRejectReason('');
      setRejectNote('');
    } else if (type === 'report') {
      setReportType('');
      setReportDetails('');
    }
  };

  const closeAction = () => {
    setActionInquiryId(null);
    setActionType(null);
  };

  const handleAccept = async () => {
    if (!actionInquiryId || quotedPrice <= 0) {
      setError('Please enter a valid quoted price');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const result = await acceptInquiry(token, actionInquiryId, {
        quotedPrice: quotedPrice,
        moq: quoteMoq ? Number(quoteMoq) : undefined,
        leadTimeDays: quoteLeadTime ? Number(quoteLeadTime) : undefined,
        validityDays: quoteValidity,
        sellerNote: quoteNote || undefined
      });

      // Update local state with buyer contact info and seller business name
      setInquiries(prev => prev.map(inq => 
        inq._id === actionInquiryId 
          ? { 
              ...inq, 
              status: 'accepted' as const, 
              buyerInfo: {
                name: result.buyerContact?.name,
                companyName: result.buyerContact?.company,
                phone: result.buyerContact?.phone,
                email: result.buyerContact?.email
              },
              sellerBusinessName: result.sellerContact?.businessName
            }
          : inq
      ));

      setSuccess('Inquiry accepted! You can now contact the buyer.');
      closeAction();
      setTimeout(() => setSuccess(null), 5000);

      // Auto-redirect to WhatsApp if link is available
      if (result.whatsappLink) {
         setSuccess('Inquiry accepted! Click WhatsApp to contact buyer.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept inquiry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!actionInquiryId || !rejectReason) {
      setError('Please select a rejection reason');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      await rejectInquiry(token, actionInquiryId, {
        reason: rejectReason as 'price_too_low' | 'not_available' | 'moq_issue' | 'location_not_serviceable' | 'capacity_full' | 'other',
        note: rejectNote || undefined
      });

      setInquiries(prev => prev.map(inq => 
        inq._id === actionInquiryId ? { ...inq, status: 'rejected' as const } : inq
      ));

      setSuccess('Inquiry rejected');
      closeAction();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject inquiry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReport = async () => {
    if (!actionInquiryId || !reportType) {
      setError('Please select a report type');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      await reportInquiry(token, actionInquiryId, {
        reportType: reportType as 'spam' | 'unrealistic_quantity' | 'fake_inquiry' | 'abusive' | 'other',
        details: reportDetails || undefined
      });

      setInquiries(prev => prev.map(inq => 
        inq._id === actionInquiryId ? { ...inq, status: 'reported' as const } : inq
      ));

      setSuccess('Inquiry reported for review');
      closeAction();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to report inquiry');
    } finally {
      setSubmitting(false);
    }
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
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-purple-600" />
                Buyer Enquiries
              </h1>
              <p className="text-sm text-gray-500">View, respond, and convert buyer enquiries in real time</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Status Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {statusTabs.map(tab => (
            <button
              key={tab.value}
              onClick={() => { setStatusFilter(tab.value); setPage(1); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition ${
                statusFilter === tab.value 
                  ? tab.color 
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
              data-testid={`tab-${tab.value || 'all'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700">
            <Check className="h-5 w-5 flex-shrink-0" />
            {success}
          </div>
        )}

        {/* New Inquiry Notification Banner */}
        {hasNewInquiry && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex justify-between items-center" data-testid="new-inquiry-banner">
            <span className="text-blue-700 font-medium flex items-center gap-2">
              <Bell className="h-5 w-5" />
              🔔 New inquiry received!
            </span>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium"
              data-testid="refresh-btn"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        )}

        {/* Unread Count Badge */}
        {unreadCount > 0 && !hasNewInquiry && (
          <div className="mb-4 text-sm text-gray-600">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full">
              {unreadCount} pending {unreadCount === 1 ? 'inquiry' : 'inquiries'}
            </span>
          </div>
        )}

        {inquiries.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <MessageSquare className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Buyer Enquiries Yet</h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Once buyers contact you, they will appear here. You can then respond, convert, and track enquiries in real time.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {inquiries.map((inquiry) => (
              <div 
                key={inquiry._id}
                className="bg-white rounded-xl shadow-sm overflow-hidden"
                data-testid={`inquiry-card-${inquiry._id}`}
              >
                {/* Inquiry Header */}
                <div className="p-4 border-b">
                  <div className="flex items-start gap-4">
                    {/* Product Image */}
                    <div className="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                      {inquiry.listingImage ? (
                        <img 
                          src={inquiry.listingImage} 
                          alt={inquiry.listingName || ''}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Package className="h-6 w-6 text-gray-400" />
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900 truncate">{inquiry.listingName}</h3>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          inquiry.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          inquiry.status === 'accepted' ? 'bg-green-100 text-green-700' :
                          inquiry.status === 'rejected' ? 'bg-red-100 text-red-700' :
                          'bg-orange-100 text-orange-700'
                        }`}>
                          {inquiry.status}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
                        <span className="font-medium">Qty: {inquiry.quantity}</span>
                        {inquiry.buyerType && (
                          <span className="flex items-center gap-1">
                            <Building2 className="h-3.5 w-3.5" />
                            {buyerTypeLabels[inquiry.buyerType] || inquiry.buyerType}
                          </span>
                        )}
                        {(inquiry.buyerMasked?.city || inquiry.buyerInfo?.city) && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" />
                            {inquiry.buyerInfo?.city || inquiry.buyerMasked?.city}
                            {(inquiry.buyerInfo?.state || inquiry.buyerMasked?.state) && 
                              `, ${inquiry.buyerInfo?.state || inquiry.buyerMasked?.state}`
                            }
                          </span>
                        )}
                        <span className="flex items-center gap-1 text-gray-400">
                          <Clock className="h-3.5 w-3.5" />
                          {new Date(inquiry.createdAt).toLocaleDateString('en-IN', {timeZone: 'Asia/Kolkata',
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit' 
                            })}
                        </span>
                      </div>

                      {inquiry.requirementNote && (
                        <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          {inquiry.requirementNote}
                        </p>
                      )}
                    </div>

                    {/* Masked Buyer Initial (if not accepted) */}
                    {inquiry.status !== 'accepted' && inquiry.buyerMasked?.companyInitial && (
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold">
                        {inquiry.buyerMasked.companyInitial}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions or Contact Info */}
                {inquiry.status === 'pending' && (
                  <div className="p-4 bg-gray-50 flex flex-wrap gap-3">
                    <button
                      onClick={() => openAction(inquiry._id, 'accept')}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                      data-testid={`accept-btn-${inquiry._id}`}
                    >
                      <Check className="h-4 w-4" />
                      Accept & Quote
                    </button>
                    <button
                      onClick={() => openAction(inquiry._id, 'reject')}
                      className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                      data-testid={`reject-btn-${inquiry._id}`}
                    >
                      <X className="h-4 w-4" />
                      Reject
                    </button>
                    <button
                      onClick={() => openAction(inquiry._id, 'report')}
                      className="flex items-center gap-2 px-4 py-2 text-orange-600 hover:bg-orange-50 rounded-lg"
                      data-testid={`report-btn-${inquiry._id}`}
                    >
                      <Flag className="h-4 w-4" />
                      Report
                    </button>
                  </div>
                )}

                {/* Accepted - Show Buyer Contact */}
                {inquiry.status === 'accepted' && inquiry.buyerInfo && (
                  <div className="p-4 bg-green-50 border-t border-green-100">
                    <div className="flex flex-wrap items-center gap-4 mb-3">
                      <div>
                        <p className="text-sm text-green-700 font-medium">Buyer Contact Unlocked</p>
                        <p className="font-semibold text-gray-900">{inquiry.buyerInfo.name}</p>
                        {inquiry.buyerInfo.companyName && (
                          <p className="text-sm text-gray-600">{inquiry.buyerInfo.companyName}</p>
                        )}
                      </div>
                      <div className="flex-1 flex flex-wrap gap-3 text-sm">
                        {inquiry.buyerInfo.phone && (
                          <a href={`tel:${inquiry.buyerInfo.phone}`} className="flex items-center gap-1 text-blue-600 hover:underline">
                            <Phone className="h-4 w-4" />
                            {inquiry.buyerInfo.phone}
                          </a>
                        )}
                        {inquiry.buyerInfo.email && (
                          <a href={`mailto:${inquiry.buyerInfo.email}`} className="flex items-center gap-1 text-blue-600 hover:underline">
                            <Mail className="h-4 w-4" />
                            {inquiry.buyerInfo.email}
                          </a>
                        )}
                      </div>
                      {inquiry.buyerInfo.phone && (
                        <button
                          onClick={() => {
                            const buyerName = inquiry.buyerInfo?.name || 'Customer';
const productName = inquiry.listingName || 'your product';
const quantity = inquiry.quantity || 0;

// Use sellerBusinessName from API response (set when inquiry was accepted)
const sellerBusiness = inquiry.sellerBusinessName || 'Your Business';
const sellerName = sellerBusiness;
const price = inquiry.quote?.price ?? 0;
const moq = inquiry.quote?.moq ?? null;
const leadTime = inquiry.quote?.leadTimeDays ?? null;

const validDate = inquiry.quote?.validTill
  ? new Date(inquiry.quote.validTill).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  : null;

let msg =
  `Hello ${buyerName},\n\n` +
  `Greetings from B2B Market Place.\n\n` +
  `This is ${sellerBusiness}.\n\n` +
  `We are pleased to share our quotation for your inquiry regarding "${productName}".\n\n` +
  `Requested Quantity: ${quantity}\n` +
  `Quoted Price: ₹${price} per unit\n`;

if (moq) msg += `Minimum Order Quantity (MOQ): ${moq}\n`;
if (leadTime) msg += `Lead Time: ${leadTime} days\n`;
if (validDate) msg += `Quotation Valid Till: ${validDate}\n`;

msg +=
  `\nPlease feel free to reach out for any further clarification.\n\n` +
  `Best Regards,\n` +
  `${sellerBusiness}\n` +
  `B2B Market Place`;
                            
                            // Clean phone number - remove non-digits
                            const rawPhone = inquiry.buyerInfo?.phone || '';
                            const cleaned = rawPhone.replace(/\D/g, '');
                            // Add India country code if not present
                            const finalPhone = cleaned.startsWith('91') ? cleaned : `91${cleaned}`;
                            
                            window.open(`https://wa.me/${finalPhone}?text=${encodeURIComponent(msg)}`, '_blank','noopener,noreferrer');
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                          data-testid={`whatsapp-btn-${inquiry._id}`}
                        >
                          <Send className="h-4 w-4" />
                          WhatsApp Buyer
                        </button>
                      )}
                    </div>
                    {inquiry.quote && (
                      <div className="text-sm text-green-800 bg-green-100 p-2 rounded">
                        Quoted: ₹{inquiry.quote.price} | Valid till: {new Date(inquiry.quote.validTill).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Action Modal */}
      {actionInquiryId && actionType && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl max-h-[90vh] overflow-y-auto">
            {/* Accept Form */}
            {actionType === 'accept' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Check className="h-5 w-5 text-green-600" />
                  Accept & Quote
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Quoted Price (per unit) *
                    </label>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">₹</span>
                      <input
                        type="number"
                        value={quotedPrice || ''}
                        onChange={(e) => setQuotedPrice(parseFloat(e.target.value) || 0)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                        placeholder="0.00"
                        min={0}
                        step={0.01}
                        data-testid="quote-price-input"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">MOQ</label>
                      <input
                        type="number"
                        value={quoteMoq}
                        onChange={(e) => setQuoteMoq(e.target.value ? parseInt(e.target.value) : '')}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="Optional"
                        min={1}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Lead Time (days)</label>
                      <input
                        type="number"
                        value={quoteLeadTime}
                        onChange={(e) => setQuoteLeadTime(e.target.value ? parseInt(e.target.value) : '')}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="Optional"
                        min={0}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Quote Valid For</label>
                    <select
                      value={quoteValidity}
                      onChange={(e) => setQuoteValidity(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value={3}>3 days</option>
                      <option value={7}>7 days</option>
                      <option value={15}>15 days</option>
                      <option value={30}>30 days</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Note to Buyer</label>
                    <textarea
                      value={quoteNote}
                      onChange={(e) => setQuoteNote(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      rows={2}
                      placeholder="Optional message..."
                      maxLength={500}
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={handleAccept}
                    disabled={submitting || quotedPrice <= 0}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
                    data-testid="confirm-accept-btn"
                  >
                    {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Check className="h-5 w-5" />}
                    Accept Inquiry
                  </button>
                  <button
                    onClick={closeAction}
                    className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Reject Form */}
            {actionType === 'reject' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <X className="h-5 w-5 text-red-600" />
                  Reject Inquiry
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Reason for rejection *
                    </label>
                    <div className="space-y-2">
                      {rejectionReasons.map(reason => (
                        <label key={reason.value} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name="rejectReason"
                            value={reason.value}
                            checked={rejectReason === reason.value}
                            onChange={(e) => setRejectReason(e.target.value)}
                            className="text-red-600"
                          />
                          <span className="text-sm text-gray-700">{reason.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Note (optional)</label>
                    <textarea
                      value={rejectNote}
                      onChange={(e) => setRejectNote(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      rows={2}
                      placeholder="Additional details..."
                      maxLength={300}
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={handleReject}
                    disabled={submitting || !rejectReason}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium"
                    data-testid="confirm-reject-btn"
                  >
                    {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <X className="h-5 w-5" />}
                    Reject
                  </button>
                  <button
                    onClick={closeAction}
                    className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Report Form */}
            {actionType === 'report' && (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-600" />
                  Report Inquiry
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Report type *
                    </label>
                    <div className="space-y-2">
                      {reportTypes.map(type => (
                        <label key={type.value} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name="reportType"
                            value={type.value}
                            checked={reportType === type.value}
                            onChange={(e) => setReportType(e.target.value)}
                            className="text-orange-600"
                          />
                          <span className="text-sm text-gray-700">{type.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Details (optional)</label>
                    <textarea
                      value={reportDetails}
                      onChange={(e) => setReportDetails(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      rows={2}
                      placeholder="Explain why you are reporting..."
                      maxLength={500}
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={handleReport}
                    disabled={submitting || !reportType}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 font-medium"
                    data-testid="confirm-report-btn"
                  >
                    {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Flag className="h-5 w-5" />}
                    Report
                  </button>
                  <button
                    onClick={closeAction}
                    className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
