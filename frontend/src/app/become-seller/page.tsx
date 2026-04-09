'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import RoleGuard from '@/components/RoleGuard';
import LocationSelector from '@/components/LocationSelector';
import { Store, CheckCircle, Loader2, AlertCircle, Building, BadgeCheck, Info } from 'lucide-react';
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

  const [businessName, setBusinessName] = useState(profile?.businessName || '');
  const [state, setState] = useState(profile?.state || '');
  const [city, setCity] = useState(profile?.city || '');
  const [pincode, setPincode] = useState(profile?.pincode || '');
  const [gstNumber, setGstNumber] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  if (isSeller) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">You&apos;re Already a Seller!</h1>
        <p className="text-gray-500 mb-6">Your seller account is active. Start listing your products now.</p>
        <Link href="/dashboard" className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition">
          Go to Dashboard
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-10 w-10 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Welcome to UdyogConnect!</h1>
        <p className="text-gray-500 mb-2">Your seller account has been created successfully.</p>
        <p className="text-sm text-gray-400 mb-8">Your GST verification is pending. You can start adding products while we verify your details.</p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/seller/business-tools" className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition font-medium" data-testid="go-to-dashboard-btn">
            Go to Business Tools
          </Link>
          <Link href="/sell" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 transition font-medium">
            List a Product
          </Link>
        </div>
      </div>
    );
  }

  const isGSTValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstNumber.toUpperCase());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!businessName.trim()) { setError('Business name is required'); return; }
    if (!state) { setError('Please select your state'); return; }
    if (!city) { setError('Please select your city'); return; }
    if (!pincode || pincode.length !== 6) { setError('Please enter a valid 6-digit PIN code'); return; }
    if (!gstNumber.trim()) { setError('GST number is required for sellers'); return; }
    if (!isGSTValid) { setError('Please enter a valid 15-character GST number'); return; }

    setIsSubmitting(true);
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Authentication failed. Please log in again.');
      await fetchWithAuth('/users/become-seller', token, {
        method: 'POST',
        body: {
          businessName: businessName.trim(),
          state,
          city,
          pincode,
          gstNumber: gstNumber.toUpperCase().trim(),
        },
      });
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
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white py-10 px-4">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Store className="h-8 w-8 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="become-seller-title">Become a Seller</h1>
          <p className="text-gray-500 text-sm mt-2">Set up your seller profile to start listing products on UdyogConnect</p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex gap-3">
          <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-700">
            <p className="font-medium mb-1">Your seller badge is product-specific</p>
            <p className="text-blue-600 text-xs">When you list each product, you&apos;ll choose your role (Manufacturer, Dealer, Distributor, etc.) for that product.</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3" data-testid="error-message">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-5">
          {/* Business Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Business Name *</label>
            <div className="relative">
              <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="e.g., Akash Enterprises"
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-500 outline-none"
                disabled={isSubmitting}
                data-testid="business-name-input"
              />
            </div>
          </div>

          {/* Location Selector — State → City → Pincode */}
          <LocationSelector
            state={state}
            city={city}
            pincode={pincode}
            onStateChange={setState}
            onCityChange={setCity}
            onPincodeChange={setPincode}
            disabled={isSubmitting}
          />

          {/* GST Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              GST Number * <span className="text-xs text-gray-400 font-normal">(15 characters)</span>
            </label>
            <div className="relative">
              <BadgeCheck className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={gstNumber}
                onChange={(e) => setGstNumber(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 15))}
                placeholder="e.g., 27AAPFU0939F1ZV"
                maxLength={15}
                className={`w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-500 outline-none uppercase tracking-wider ${
                  gstNumber.length === 15 ? (isGSTValid ? 'border-green-400 bg-green-50' : 'border-red-400 bg-red-50') : 'border-gray-300'
                }`}
                disabled={isSubmitting}
                data-testid="gst-number-input"
              />
              {gstNumber.length === 15 && (
                <span className={`absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium ${isGSTValid ? 'text-green-600' : 'text-red-600'}`}>
                  {isGSTValid ? 'Valid format' : 'Invalid format'}
                </span>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !businessName.trim() || !state || !city || !pincode || !isGSTValid}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            data-testid="submit-become-seller-btn"
          >
            {isSubmitting ? (
              <><Loader2 className="h-5 w-5 animate-spin" /> Setting up your account...</>
            ) : (
              <><Store className="h-5 w-5" /> Register as Seller</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
