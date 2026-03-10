'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { User, Store, AlertCircle, CheckCircle, Building2, Calendar } from 'lucide-react';
import LocationSelector from '@/components/LocationSelector';
import type { ProfileCompleteData } from '@/lib/api';

export default function CompleteProfilePage() {
  const router = useRouter();
  const { user, profile, needsRegistration, needsEmailVerification, completeRegistration, error, clearError, loading: authLoading, isAuthenticated } = useAuth();

  // Use backend's isEmailVerified from profile
  const emailVerified = profile?.isEmailVerified === true;

  const [step, setStep] = useState<'role' | 'profile'>('role');
  const [selectedRole, setSelectedRole] = useState<'buyer' | 'seller' | null>(null);
  const [formData, setFormData] = useState({ 
    businessName: '', 
    phone: '', 
    address: '', 
    city: '', 
    state: '', 
    pincode: '', 
    gstNumber: '',
    // NEW: Enterprise Establishment Year
    enterpriseEstablishmentYear: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  useEffect(() => {
    if (!user) { router.push('/register'); return; }
    if (needsEmailVerification) { router.push('/verify-email'); return; }
    if (isAuthenticated && !needsRegistration) { router.push('/dashboard'); }
  }, [user, needsEmailVerification, isAuthenticated, needsRegistration, router]);

  const handleChange = (field: string, value: string) => {
    let v = value;
    if (field === 'phone') v = value.replace(/[^0-9]/g, '').slice(0, 10);
    else if (field === 'pincode') v = value.replace(/[^0-9]/g, '').slice(0, 6);
    else if (field === 'gstNumber') v = value.toUpperCase().slice(0, 15);
    else if (field === 'enterpriseEstablishmentYear') v = value.replace(/[^0-9]/g, '').slice(0, 4);
    else v = value.slice(0, 200);
    setFormData(prev => ({ ...prev, [field]: v }));
  };

  const handleRoleSelect = (role: 'buyer' | 'seller') => { setSelectedRole(role); setStep('profile'); setLocalError(''); clearError(); };

  const validateProfile = () => {
    setLocalError('');
    if (!formData.businessName.trim()) { setLocalError('Full name / Business name is required'); return false; }
    if (!formData.phone || formData.phone.length !== 10) { setLocalError('Please enter a valid 10-digit phone number'); return false; }
    if (!formData.address.trim() || formData.address.length < 5) { setLocalError('Please enter a valid address'); return false; }
    if (!formData.state) { setLocalError('State is required'); return false; }
    if (!formData.city.trim()) { setLocalError('City is required'); return false; }
    if (!formData.pincode || formData.pincode.length !== 6) { setLocalError('Please enter a valid 6-digit PIN code'); return false; }
    
    if (selectedRole === 'seller') {
      if (!formData.gstNumber) { setLocalError('GST number is required for seller registration'); return false; }
      if (!/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(formData.gstNumber)) { 
        setLocalError('Please enter a valid GST number'); return false; 
      }
      
      // Validate Enterprise Establishment Year
      if (!formData.enterpriseEstablishmentYear) { 
        setLocalError('Enterprise establishment year is required for seller registration'); return false; 
      }
      const year = parseInt(formData.enterpriseEstablishmentYear, 10);
      const currentYear = new Date().getFullYear();
      if (year < 1800 || year > currentYear) { 
        setLocalError(`Establishment year must be between 1800 and ${currentYear}`); return false; 
      }
    }
    
    if (!acceptedTerms) { setLocalError('Please accept the terms and conditions'); return false; }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validateProfile() || !selectedRole) return;
    setIsSubmitting(true);
    try {
      const profileData: ProfileCompleteData = { 
        role: selectedRole, 
        businessName: formData.businessName.trim(), 
        phone: formData.phone, 
        address: formData.address.trim(), 
        city: formData.city.trim(), 
        state: formData.state, 
        pincode: formData.pincode, 
        ...(selectedRole === 'seller' && { 
          gstNumber: formData.gstNumber,
          enterpriseEstablishmentYear: parseInt(formData.enterpriseEstablishmentYear, 10)
        }) 
      };
      await completeRegistration(profileData);
      router.push(selectedRole === 'seller' ? '/seller?welcome=true' : '/dashboard?welcome=true');
    } catch {} finally { setIsSubmitting(false); }
  };

  const displayError = localError || error;
  if (!user || !emailVerified || (!needsRegistration && isAuthenticated)) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  // Generate year options (current year down to 1900)
  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: currentYear - 1899 }, (_, i) => currentYear - i);

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="mx-auto w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              {step === 'role' ? 'Choose Account Type' : 'Complete Your Profile'}
            </h1>
            <p className="text-gray-500 mt-2">
              {step === 'role' 
                ? 'Select how you want to use the platform' 
                : selectedRole === 'seller' 
                  ? 'Fill in your business details and GST information' 
                  : 'Fill in your business details'}
            </p>
          </div>

          {displayError && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm flex items-start gap-2 mb-6">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <span>{displayError}</span>
            </div>
          )}

          {step === 'role' && (
            <div className="space-y-4">
              <button 
                onClick={() => handleRoleSelect('buyer')} 
                className="w-full p-6 border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition group text-left" 
                data-testid="role-buyer-btn"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition">
                    <User className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Buyer</h3>
                    <p className="text-gray-500 text-sm mt-1">Browse products, send inquiries, and connect with sellers</p>
                  </div>
                </div>
              </button>
              
              <button 
                onClick={() => handleRoleSelect('seller')} 
                className="w-full p-6 border-2 border-gray-200 rounded-xl hover:border-green-500 hover:bg-green-50 transition group text-left" 
                data-testid="role-seller-btn"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition">
                    <Store className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Seller</h3>
                    <p className="text-gray-500 text-sm mt-1">List your products, receive inquiries, and grow your business</p>
                    <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                      <Building2 className="h-3 w-3" /> Requires GST registration
                    </p>
                  </div>
                </div>
              </button>
            </div>
          )}

          {step === 'profile' && selectedRole && (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                selectedRole === 'seller' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {selectedRole === 'seller' ? <Store className="h-4 w-4" /> : <User className="h-4 w-4" />}
                {selectedRole === 'seller' ? 'Seller Account' : 'Buyer Account'}
              </div>
              
              {/* Business Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name / Business Name *
                </label>
                <input 
                  type="text" 
                  value={formData.businessName} 
                  onChange={(e) => handleChange('businessName', e.target.value)} 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="Your name or company name" 
                  data-testid="input-business-name" 
                />
              </div>
              
              {/* Phone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mobile Number *</label>
                <div className="flex">
                  <span className="inline-flex items-center px-3 border border-r-0 border-gray-300 bg-gray-50 text-gray-500 rounded-l-lg">+91</span>
                  <input 
                    type="tel" 
                    value={formData.phone} 
                    onChange={(e) => handleChange('phone', e.target.value)} 
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-r-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                    placeholder="10-digit mobile number" 
                    data-testid="input-phone" 
                  />
                </div>
              </div>
              
              {/* Address */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Address *</label>
                <textarea 
                  value={formData.address} 
                  onChange={(e) => handleChange('address', e.target.value)} 
                  rows={2} 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none" 
                  placeholder="Street address, building, landmark" 
                  data-testid="input-address" 
                />
              </div>
              
              {/* Location Selector */}
              <LocationSelector
                state={formData.state}
                city={formData.city}
                pincode={formData.pincode}
                onStateChange={(v) => handleChange('state', v)}
                onCityChange={(v) => handleChange('city', v)}
                onPincodeChange={(v) => handleChange('pincode', v)}
                disabled={isSubmitting}
              />
              
              {/* Seller-only fields */}
              {selectedRole === 'seller' && (
                <>
                  {/* GST Number */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">GST Number *</label>
                    <input 
                      type="text" 
                      value={formData.gstNumber} 
                      onChange={(e) => handleChange('gstNumber', e.target.value)} 
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono" 
                      placeholder="27AABCU9603R1ZM" 
                      data-testid="input-gst" 
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Your GST will be verified. You can create drafts while verification is pending.
                    </p>
                  </div>
                  
                  {/* Enterprise Establishment Year - NEW */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <span className="flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        Enterprise Establishment Year *
                      </span>
                    </label>
                    <select
                      value={formData.enterpriseEstablishmentYear}
                      onChange={(e) => handleChange('enterpriseEstablishmentYear', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                      data-testid="input-establishment-year"
                    >
                      <option value="">Select year</option>
                      {yearOptions.map(year => (
                        <option key={year} value={year}>{year}</option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      When was your company originally founded? This will be displayed on your catalog page.
                    </p>
                  </div>
                </>
              )}
              
              {/* Terms */}
              <div className="flex items-start gap-2">
                <input 
                  type="checkbox" 
                  checked={acceptedTerms} 
                  onChange={(e) => setAcceptedTerms(e.target.checked)} 
                  className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded" 
                  data-testid="checkbox-terms" 
                />
                <label className="text-sm text-gray-600">
                  I agree to the <Link href="/terms" className="text-blue-600 hover:underline">Terms of Service</Link> and <Link href="/privacy" className="text-blue-600 hover:underline">Privacy Policy</Link>
                </label>
              </div>
              
              {/* Submit buttons */}
              <div className="flex gap-3 pt-2">
                <button 
                  type="button" 
                  onClick={() => { setStep('role'); setSelectedRole(null); setLocalError(''); }} 
                  className="flex-1 border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition"
                >
                  Back
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting || authLoading} 
                  className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50" 
                  data-testid="submit-profile-btn"
                >
                  {isSubmitting ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                  ) : (
                    'Complete Registration'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
