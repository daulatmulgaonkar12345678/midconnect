'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X, Send, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { createInquiry } from '@/lib/api';
import type { EnterpriseProductSeller } from '@/lib/api';

interface InquiryModalProps {
  isOpen: boolean;
  onClose: () => void;
  seller: EnterpriseProductSeller | null;
  productId: string;
  productName: string;
}

type BuyerType = 'trader' | 'contractor' | 'oem' | 'manufacturer' | 'other';

export default function InquiryModal({ 
  isOpen, 
  onClose, 
  seller, 
  productId,
  productName 
}: InquiryModalProps) {
  const router = useRouter();
  const { user, getIdToken, isAuthenticated, emailVerified, registrationState } = useAuth();
  
  const [quantity, setQuantity] = useState<number>(seller?.moq || 1);
  const [message, setMessage] = useState('');
  const [buyerType, setBuyerType] = useState<BuyerType>('other');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen || !seller) return null;

  // Check if buyer is fully verified
  const isFullyVerified = isAuthenticated && emailVerified && registrationState === 'complete';
  const needsEmailVerification = isAuthenticated && !emailVerified;
  const needsProfileCompletion = isAuthenticated && emailVerified && registrationState === 'incomplete';

  const handleSubmit = async () => {
    // Not logged in - redirect to login
    if (!isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
      return;
    }

    // Email not verified
    if (!emailVerified) {
      router.push('/verify-email');
      return;
    }

    // Profile not complete
    if (registrationState === 'incomplete') {
      router.push('/user/complete-profile');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      await createInquiry(token, {
        productId,
        sellerId: seller.sellerId,
        listingId: seller.listingId,
        quantity,
        message: message || undefined,
        buyerType
      });

      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setQuantity(seller?.moq || 1);
        setMessage('');
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send inquiry');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return 'Request Quote';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div 
        className="bg-white rounded-xl w-full max-w-md shadow-2xl overflow-hidden"
        data-testid="inquiry-modal"
      >
        {/* Header */}
        <div className="bg-gray-50 px-5 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">Request Quote</h3>
            <p className="text-sm text-gray-500">{seller.companyName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Success State */}
        {success ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Send className="h-8 w-8 text-green-600" />
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Inquiry Sent!</h4>
            <p className="text-gray-600">
              {seller.companyName} will review and respond with a quote.
            </p>
          </div>
        ) : (
          <div className="p-5 space-y-4">
            {/* Auth Warning - Not logged in */}
            {!isAuthenticated && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>You need to login to send an inquiry</span>
              </div>
            )}

            {/* Email Verification Warning */}
            {needsEmailVerification && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Email verification required</p>
                  <p className="text-xs mt-1">Please verify your email address before sending inquiries.</p>
                </div>
              </div>
            )}

            {/* Profile Completion Warning */}
            {needsProfileCompletion && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Profile completion required</p>
                  <p className="text-xs mt-1">Please complete your profile to send inquiries to sellers.</p>
                </div>
              </div>
            )}

            {/* Product Info */}
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Product</p>
              <p className="font-medium text-gray-900">{productName}</p>
              <p className="text-sm text-gray-600 mt-1">
                Starting at {formatPrice(seller.lowestPrice)}
              </p>
            </div>

            {/* Top Specs Summary */}
            {seller.searchableAttributes && Object.keys(seller.searchableAttributes).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {Object.entries(seller.searchableAttributes).slice(0, 4).map(([key, value]) => (
                  <span 
                    key={key} 
                    className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded"
                  >
                    {seller.attributeLabels?.[key] || key}: {String(value)}
                  </span>
                ))}
              </div>
            )}

            {/* Quantity Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Quantity Required *
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min={seller.moq}
                data-testid="inquiry-quantity"
              />
              <p className="text-xs text-gray-500 mt-1">
                MOQ: {seller.moq} units
              </p>
            </div>

            {/* Buyer Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                I am a
              </label>
              <select
                value={buyerType}
                onChange={(e) => setBuyerType(e.target.value as BuyerType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="inquiry-buyer-type"
              >
                <option value="trader">Trader</option>
                <option value="contractor">Contractor</option>
                <option value="oem">OEM</option>
                <option value="manufacturer">Manufacturer</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Requirements / Message (Optional)
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={3}
                placeholder="Describe your specific requirements, preferred delivery timeline..."
                maxLength={1000}
                data-testid="inquiry-message"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                data-testid="inquiry-submit"
              >
                {isSubmitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <Send className="h-5 w-5" />
                    {!isAuthenticated 
                      ? 'Login & Send' 
                      : needsEmailVerification 
                        ? 'Verify Email' 
                        : needsProfileCompletion 
                          ? 'Complete Profile'
                          : 'Send Inquiry'}
                  </>
                )}
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2.5 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium transition-colors"
              >
                Cancel
              </button>
            </div>

            {/* Privacy Note */}
            <p className="text-xs text-gray-500 text-center">
              Your contact details are masked until the seller accepts your inquiry.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
