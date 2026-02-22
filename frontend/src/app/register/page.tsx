'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { Eye, EyeOff, UserPlus, AlertCircle } from 'lucide-react';
import { Suspense } from 'react';

// Indian states for dropdown
const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Jammu and Kashmir', 'Ladakh'
];

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signUp, completeRegistration, error, clearError, loading: authLoading, needsRegistration, user } = useAuth();
  
  // Check if this is completing registration for existing Firebase user
  const isCompletingRegistration = searchParams.get('complete') === 'true' && needsRegistration && user;
  
  // Form state
  const [step, setStep] = useState(isCompletingRegistration ? 2 : 1);
  const [formData, setFormData] = useState({
    email: user?.email || '',
    password: '',
    confirmPassword: '',
    businessName: '',
    phone: '',
    city: '',
    state: '',
    pincode: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  // If completing registration, skip to step 2
  useEffect(() => {
    if (isCompletingRegistration) {
      setStep(2);
      setFormData(prev => ({ ...prev, email: user?.email || '' }));
    }
  }, [isCompletingRegistration, user]);

  // Input handlers with sanitization
  const handleChange = (field: string, value: string) => {
    let sanitizedValue = value;
    
    // Field-specific validation
    switch (field) {
      case 'phone':
        sanitizedValue = value.replace(/[^0-9]/g, '').slice(0, 10);
        break;
      case 'pincode':
        sanitizedValue = value.replace(/[^0-9]/g, '').slice(0, 6);
        break;
      case 'email':
        sanitizedValue = value.toLowerCase().slice(0, 100);
        break;
      default:
        sanitizedValue = value.slice(0, 100);
    }
    
    setFormData(prev => ({ ...prev, [field]: sanitizedValue }));
  };

  // Step 1 validation
  const validateStep1 = (): boolean => {
    setLocalError('');
    
    if (!formData.email) {
      setLocalError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setLocalError('Please enter a valid email');
      return false;
    }
    if (!formData.password) {
      setLocalError('Password is required');
      return false;
    }
    if (formData.password.length < 6) {
      setLocalError('Password must be at least 6 characters');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setLocalError('Passwords do not match');
      return false;
    }
    return true;
  };

  // Step 2 validation
  const validateStep2 = (): boolean => {
    setLocalError('');
    
    if (!formData.businessName.trim()) {
      setLocalError('Business name is required');
      return false;
    }
    if (!formData.phone || formData.phone.length !== 10) {
      setLocalError('Please enter a valid 10-digit phone number');
      return false;
    }
    if (!formData.city.trim()) {
      setLocalError('City is required');
      return false;
    }
    if (!formData.state) {
      setLocalError('State is required');
      return false;
    }
    if (!formData.pincode || formData.pincode.length !== 6) {
      setLocalError('Please enter a valid 6-digit PIN code');
      return false;
    }
    if (!acceptedTerms) {
      setLocalError('Please accept the terms and conditions');
      return false;
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep1()) {
      setStep(2);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    if (!validateStep2()) return;

    setIsSubmitting(true);

    try {
      const profileData = {
        businessName: formData.businessName.trim(),
        phone: formData.phone,
        city: formData.city.trim(),
        state: formData.state,
        pincode: formData.pincode,
      };

      if (isCompletingRegistration) {
        // Complete registration for existing Firebase user
        await completeRegistration(profileData);
        router.push('/');
      } else {
        // Full new registration
        await signUp(formData.email.trim(), formData.password, profileData);
        router.push('/login?registered=true');
      }
    } catch (err) {
      // Error handled by AuthContext
      // Don't reset form on error - let user fix and retry
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              {isCompletingRegistration ? 'Complete Your Profile' : 'Create Account'}
            </h1>
            <p className="text-gray-500 mt-2">
              {isCompletingRegistration 
                ? 'Please provide your business details to continue'
                : "Join India's largest B2B marketplace"
              }
            </p>
            
            {/* Progress indicator - only for new registration */}
            {!isCompletingRegistration && (
              <>
                <div className="flex items-center justify-center gap-2 mt-4">
                  <div className={`w-3 h-3 rounded-full ${step >= 1 ? 'bg-blue-600' : 'bg-gray-300'}`} />
                  <div className="w-8 h-0.5 bg-gray-300">
                    <div className={`h-full transition-all ${step >= 2 ? 'bg-blue-600 w-full' : 'w-0'}`} />
                  </div>
                  <div className={`w-3 h-3 rounded-full ${step >= 2 ? 'bg-blue-600' : 'bg-gray-300'}`} />
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  Step {step} of 2: {step === 1 ? 'Account Details' : 'Business Info'}
                </p>
              </>
            )}
          </div>

          <form onSubmit={step === 1 ? (e) => { e.preventDefault(); handleNext(); } : handleSubmit} className="space-y-6">
            {displayError && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <span>{displayError}</span>
              </div>
            )}

            {step === 1 && !isCompletingRegistration ? (
              // Step 1: Email & Password (only for new registration)
              <>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                    Email Address
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleChange('email', e.target.value)}
                    required
                    autoComplete="email"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="you@example.com"
                  />
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => handleChange('password', e.target.value)}
                      required
                      autoComplete="new-password"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="At least 6 characters"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-3.5 text-gray-400"
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleChange('confirmPassword', e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Confirm your password"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition"
                >
                  Continue
                </button>
              </>
            ) : (
              // Step 2: Business Information
              <>
                {/* Show email for completing registration */}
                {isCompletingRegistration && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <p className="text-sm text-gray-600">Logged in as: <strong>{user?.email}</strong></p>
                  </div>
                )}

                <div>
                  <label htmlFor="businessName" className="block text-sm font-medium text-gray-700 mb-2">
                    Business Name
                  </label>
                  <input
                    id="businessName"
                    type="text"
                    value={formData.businessName}
                    onChange={(e) => handleChange('businessName', e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Your company name"
                  />
                </div>

                <div>
                  <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                    Phone Number
                  </label>
                  <div className="flex">
                    <span className="inline-flex items-center px-3 border border-r-0 border-gray-300 bg-gray-50 text-gray-500 rounded-l-lg">
                      +91
                    </span>
                    <input
                      id="phone"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => handleChange('phone', e.target.value)}
                      required
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-r-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="10-digit mobile number"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-2">
                      City
                    </label>
                    <input
                      id="city"
                      type="text"
                      value={formData.city}
                      onChange={(e) => handleChange('city', e.target.value)}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="City"
                    />
                  </div>
                  <div>
                    <label htmlFor="pincode" className="block text-sm font-medium text-gray-700 mb-2">
                      PIN Code
                    </label>
                    <input
                      id="pincode"
                      type="text"
                      value={formData.pincode}
                      onChange={(e) => handleChange('pincode', e.target.value)}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="6-digit PIN"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="state" className="block text-sm font-medium text-gray-700 mb-2">
                    State
                  </label>
                  <select
                    id="state"
                    value={formData.state}
                    onChange={(e) => handleChange('state', e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select State</option>
                    {INDIAN_STATES.map(state => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-start gap-2">
                  <input
                    id="terms"
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
                  />
                  <label htmlFor="terms" className="text-sm text-gray-600">
                    I agree to the{' '}
                    <Link href="/terms" className="text-blue-600 hover:underline">Terms of Service</Link>
                    {' '}and{' '}
                    <Link href="/privacy" className="text-blue-600 hover:underline">Privacy Policy</Link>
                  </label>
                </div>

                <div className="flex gap-3">
                  {!isCompletingRegistration && (
                    <button
                      type="button"
                      onClick={() => setStep(1)}
                      className="flex-1 border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition"
                    >
                      Back
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={isSubmitting || authLoading}
                    className={`${isCompletingRegistration ? 'w-full' : 'flex-1'} bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50`}
                  >
                    {isSubmitting ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    ) : (
                      <>
                        <UserPlus className="h-5 w-5" /> 
                        {isCompletingRegistration ? 'Complete Registration' : 'Create Account'}
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </form>

          {!isCompletingRegistration && (
            <div className="mt-6 text-center text-sm text-gray-500">
              Already have an account?{' '}
              <Link href="/login" className="text-blue-600 hover:underline">
                Sign In
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    }>
      <RegisterContent />
    </Suspense>
  );
}
