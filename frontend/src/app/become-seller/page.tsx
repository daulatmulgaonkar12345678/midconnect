'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import RoleGuard from '@/components/RoleGuard';
import { Store, CheckCircle, Loader2, AlertCircle, Building, MapPin, BadgeCheck, Info } from 'lucide-react';
import Link from 'next/link';
import { ApiError, fetchWithAuth } from '@/lib/api';

export default function BecomeSellerPage() {
  return (
    <RoleGuard allowedRoles={['buyer', 'seller', 'admin']}>
      <BecomeSellerContent />
    </RoleGuard>
  );
}

function BecomeSellerContent() {
  const router = useRouter();
  const { isSeller, profile, getIdToken, refreshProfile } = useAuth();
  
  // Form state - NO business_type (badge comes from each product)
  const [businessName, setBusinessName] = useState(profile?.businessName || '');
  const [businessLocation, setBusinessLocation] = useState(
    profile?.city && profile?.state ? `${profile.city}, ${profile.state}` : ''
  );
  const [gstNumber, setGstNumber] = useState('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Already a seller - show success state
  if (isSeller) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">You're Already a Seller!</h1>
        <p className="text-gray-500 mb-6">
          Your seller account is active. Start listing your products now.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
        >
          Go to Dashboard
        </Link>
      </div>
    );
  }

  // Show success after upgrade
  if (success) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome, Seller!</h1>
        <p className="text-gray-500 mb-4">
          Your seller account has been activated. You can now start listing products.
        </p>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-left max-w-md mx-auto mb-6">
          <div className="flex items-start gap-2">
            <Info className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">GST Verification Pending</p>
              <p className="mt-1">Your products will be published only after GST verification. You can start creating product listings now - they will be saved as drafts.</p>
            </div>
          </div>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
        >
          Go to Dashboard
        </Link>
      </div>
    );
  }

  const validateGST = (gst: string): boolean => {
    // GST format: 2 digits (state code) + 10 chars (PAN) + 1 digit + Z + 1 checksum
    const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    return gstRegex.test(gst.toUpperCase());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate all fields
    if (!businessName.trim()) {
      setError('Business name is required');
      return;
    }
    if (!businessLocation.trim()) {
      setError('Business location is required');
      return;
    }
    if (!gstNumber.trim()) {
      setError('GST number is mandatory to become a seller');
      return;
    }
    if (!validateGST(gstNumber)) {
      setError('Please enter a valid 15-character GST number');
      return;
    }

    setIsSubmitting(true);

    try {
      const token = await getIdToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Call become-seller endpoint (NO business_type - badge comes from product)
      await fetchWithAuth('/users/become-seller', token, {
        method: 'POST',
        body: {
          businessName: businessName.trim(),
          businessLocation: businessLocation.trim(),
          gstNumber: gstNumber.toUpperCase().trim(),
        },
      });

      // Refresh profile to get updated seller status
      await refreshProfile();
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || err.getUserMessage());
      } else if (err instanceof Error) {
        setError(err.message || "We couldn't save your business details right now. Please try again.");
      } else {
        setError("We couldn't save your business details right now. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <Store className="h-16 w-16 text-blue-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Become a Seller</h1>
        <p className="text-gray-500">
          Start selling on India's fastest-growing B2B marketplace
        </p>
      </div>

      {/* Buyer clarification */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> Business details are required only if you want to sell products. 
          Buyers can continue without adding any business information.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Business Name */}
          <div>
            <label htmlFor="businessName" className="block text-sm font-medium text-gray-700 mb-2">
              <Building className="inline h-4 w-4 mr-1" />
              Business Name <span className="text-red-500">*</span>
            </label>
            <input
              id="businessName"
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              maxLength={100}
              placeholder="Enter your business name"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400"
              style={{ color: '#000000' }}
            />
          </div>

          {/* Business Location */}
          <div>
            <label htmlFor="businessLocation" className="block text-sm font-medium text-gray-700 mb-2">
              <MapPin className="inline h-4 w-4 mr-1" />
              Business Location <span className="text-red-500">*</span>
            </label>
            <input
              id="businessLocation"
              type="text"
              value={businessLocation}
              onChange={(e) => setBusinessLocation(e.target.value)}
              maxLength={100}
              placeholder="e.g., Pune, Maharashtra"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400"
              style={{ color: '#000000' }}
            />
          </div>

          {/* GST Number - MANDATORY */}
          <div>
            <label htmlFor="gst" className="block text-sm font-medium text-gray-700 mb-2">
              <BadgeCheck className="inline h-4 w-4 mr-1" />
              GST Number <span className="text-red-500">*</span> (Required for sellers)
            </label>
            <input
              id="gst"
              type="text"
              value={gstNumber}
              onChange={(e) => setGstNumber(e.target.value.toUpperCase())}
              maxLength={15}
              placeholder="e.g., 22AAAAA0000A1Z5"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent uppercase text-gray-900 placeholder-gray-400"
              style={{ color: '#000000' }}
            />
            <p className="text-xs text-gray-500 mt-2">
              GST is mandatory to become a seller. Your products will be published only after GST verification.
            </p>
          </div>

          {/* Role per Product Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">📦 Flexible Role Per Product</h4>
            <p className="text-sm text-gray-600 mb-3">
              As a seller, you can have different roles for different products:
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-2 text-gray-700">
                <span>🏭</span> Manufacturer
              </div>
              <div className="flex items-center gap-2 text-gray-700">
                <span>🏷️</span> Dealer
              </div>
              <div className="flex items-center gap-2 text-gray-700">
                <span>🚚</span> Distributor
              </div>
              <div className="flex items-center gap-2 text-gray-700">
                <span>📦</span> Wholesaler
              </div>
              <div className="flex items-center gap-2 text-gray-700">
                <span>🛍️</span> Retailer
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              You'll select your role when listing each product.
            </p>
          </div>

          {/* Benefits */}
          <div className="bg-green-50 rounded-lg p-4">
            <h4 className="font-semibold text-green-800 mb-3">As a Verified Seller, You Can:</h4>
            <ul className="space-y-2 text-green-700 text-sm">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> List unlimited products
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Receive enquiries from buyers
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Set quantity-based pricing
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Get seller badge on your products
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4" /> Track your performance
              </li>
            </ul>
          </div>

          {/* Terms */}
          <div className="flex items-start gap-2">
            <input
              id="terms"
              type="checkbox"
              required
              className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
            <label htmlFor="terms" className="text-sm text-gray-600">
              I agree to the{' '}
              <Link href="/terms" className="text-blue-600 hover:underline">Seller Terms</Link>
              {' '}and will provide accurate product information.
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Store className="h-5 w-5" /> Activate Seller Account
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
