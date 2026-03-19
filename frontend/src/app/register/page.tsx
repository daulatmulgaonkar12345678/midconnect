'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { Eye, EyeOff, UserPlus, AlertCircle, Mail, ArrowLeft, RefreshCw, CheckCircle } from 'lucide-react';
import { Suspense } from 'react';
import { requestRegistrationOTP, verifyRegistrationOTP } from '@/lib/api';

type RegistrationStep = 'details' | 'otp' | 'success';

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signUp, error, clearError, loading: authLoading, user, needsEmailVerification, needsRegistration, isAuthenticated } = useAuth();
  
  // Form state
  const [step, setStep] = useState<RegistrationStep>('details');
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');
  
  // OTP state
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [isVerifyingOTP, setIsVerifyingOTP] = useState(false);
  
  // OTP input refs
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      if (needsEmailVerification) router.push('/verify-email');
      else if (needsRegistration) router.push('/complete-profile');
      else if (isAuthenticated) router.push('/dashboard');
    }
  }, [user, needsEmailVerification, needsRegistration, isAuthenticated, router]);

  // Capture referral code from URL
  useEffect(() => {
    const ref = searchParams.get('ref');
    if (ref) {
      localStorage.setItem('referralCode', ref);
    }
  }, [searchParams]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(c => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  // Focus first OTP input when step changes to OTP
  useEffect(() => {
    if (step === 'otp') {
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    }
  }, [step]);

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ 
      ...prev, 
      [field]: field === 'email' ? value.toLowerCase().slice(0, 100) : value.slice(0, 100) 
    }));
  };

  const validateDetailsForm = () => {
    setLocalError('');
    if (!formData.name.trim()) { setLocalError('Name is required'); return false; }
    if (formData.name.trim().length < 2) { setLocalError('Name must be at least 2 characters'); return false; }
    if (!formData.email) { setLocalError('Email is required'); return false; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { setLocalError('Please enter a valid email'); return false; }
    if (!formData.password) { setLocalError('Password is required'); return false; }
    if (formData.password.length < 6) { setLocalError('Password must be at least 6 characters'); return false; }
    if (formData.password !== formData.confirmPassword) { setLocalError('Passwords do not match'); return false; }
    return true;
  };

  // Step 1: Request OTP
  const handleRequestOTP = async (e?: React.FormEvent) => {
    e?.preventDefault();
    clearError();
    if (!validateDetailsForm()) return;
    
    setIsSubmitting(true);
    setLocalError('');
    
    try {
      const result = await requestRegistrationOTP(formData.email, formData.name);
      
      if (result.success) {
        // Set cooldown for resend
        if (result.cooldown_until) {
          const cooldownEnd = new Date(result.cooldown_until);
          const now = new Date();
          const remaining = Math.max(0, Math.ceil((cooldownEnd.getTime() - now.getTime()) / 1000));
          setResendCooldown(remaining);
        } else {
          setResendCooldown(30);
        }
        
        // Move to OTP step
        setStep('otp');
        setOtp(['', '', '', '', '', '']);
        setAttemptsRemaining(null);
      } else {
        setLocalError(result.message || 'Failed to send OTP');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send OTP. Please try again.';
      
      // Handle specific error codes
      if (message.includes('already registered')) {
        setLocalError('This email is already registered. Please login instead.');
      } else if (message.includes('cooldown') || message.includes('wait')) {
        // Extract cooldown time if available
        const match = message.match(/(\d+)\s*second/);
        if (match) {
          setResendCooldown(parseInt(match[1], 10));
        }
        setLocalError(message);
      } else {
        setLocalError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle OTP input
  const handleOTPChange = (index: number, value: string) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    
    // Auto-focus next input
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
    
    // Auto-submit when all digits entered
    if (value && index === 5 && newOtp.every(d => d)) {
      handleVerifyOTP(newOtp.join(''));
    }
  };

  const handleOTPKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      // Move to previous input on backspace if current is empty
      otpRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowLeft' && index > 0) {
      otpRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOTPPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    
    if (pastedData.length === 6) {
      const newOtp = pastedData.split('');
      setOtp(newOtp);
      otpRefs.current[5]?.focus();
      
      // Auto-submit
      handleVerifyOTP(pastedData);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOTP = async (otpValue?: string) => {
    const otpToVerify = otpValue || otp.join('');
    
    if (otpToVerify.length !== 6) {
      setLocalError('Please enter all 6 digits');
      return;
    }
    
    setIsVerifyingOTP(true);
    setLocalError('');
    
    try {
      const result = await verifyRegistrationOTP(formData.email, otpToVerify);
      
      if (result.success && result.verified) {
        // OTP verified - now create Firebase account
        await handleFirebaseSignup();
      } else {
        // Handle failure
        if (result.attempts_remaining !== undefined) {
          setAttemptsRemaining(result.attempts_remaining);
        }
        setLocalError(result.message || 'Invalid OTP');
        
        // Clear OTP inputs on failure
        setOtp(['', '', '', '', '', '']);
        otpRefs.current[0]?.focus();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to verify OTP';
      
      // Try to parse attempts remaining from error
      if (message.includes('attempt')) {
        const match = message.match(/(\d+)\s*attempt/);
        if (match) {
          setAttemptsRemaining(parseInt(match[1], 10));
        }
      }
      
      setLocalError(message);
      setOtp(['', '', '', '', '', '']);
      otpRefs.current[0]?.focus();
    } finally {
      setIsVerifyingOTP(false);
    }
  };

  // Step 3: Create Firebase account after OTP verification
  const handleFirebaseSignup = async () => {
    setIsSubmitting(true);
    
    try {
      // Pass skipVerificationEmail=true since OTP is already verified
      await signUp(formData.email.trim(), formData.password, true);
      
      // Show success and redirect
      setStep('success');
      
      // The user is now created with isEmailVerified=true (checked via OTP)
      // Redirect to complete profile
      setTimeout(() => {
        router.push('/complete-profile');
      }, 2000);
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      
      // Handle "email already in use" - this shouldn't happen as we check before OTP
      if (message.includes('already') || message.includes('in use')) {
        setLocalError('This email is already registered. Please login instead.');
        setStep('details');
      } else {
        setLocalError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Resend OTP
  const handleResendOTP = async () => {
    if (resendCooldown > 0 || isResending) return;
    
    setIsResending(true);
    setLocalError('');
    
    try {
      const result = await requestRegistrationOTP(formData.email, formData.name);
      
      if (result.success) {
        if (result.cooldown_until) {
          const cooldownEnd = new Date(result.cooldown_until);
          const now = new Date();
          const remaining = Math.max(0, Math.ceil((cooldownEnd.getTime() - now.getTime()) / 1000));
          setResendCooldown(remaining);
        } else {
          setResendCooldown(30);
        }
        
        // Reset OTP inputs
        setOtp(['', '', '', '', '', '']);
        setAttemptsRemaining(null);
        otpRefs.current[0]?.focus();
      } else {
        setLocalError(result.message || 'Failed to resend OTP');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to resend OTP';
      setLocalError(message);
    } finally {
      setIsResending(false);
    }
  };

  // Go back to details step
  const handleBackToDetails = () => {
    setStep('details');
    setOtp(['', '', '', '', '', '']);
    setLocalError('');
    setAttemptsRemaining(null);
  };

  const displayError = localError || error;

  // Success screen
  if (step === 'success') {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Account Created!</h1>
            <p className="text-gray-600 mb-4">Your email has been verified successfully.</p>
            <p className="font-medium text-gray-900 mb-6 bg-gray-50 py-2 px-4 rounded-lg">{formData.email}</p>
            <div className="flex items-center justify-center gap-2 text-blue-600">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
              <span>Redirecting to complete profile...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // OTP verification screen
  if (step === 'otp') {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl shadow-lg p-8">
            {/* Header */}
            <button
              onClick={handleBackToDetails}
              className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 transition"
              data-testid="back-to-details-btn"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="text-sm">Back</span>
            </button>
            
            <div className="text-center mb-8">
              <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Mail className="h-8 w-8 text-blue-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Verify Your Email</h1>
              <p className="text-gray-500">
                We&apos;ve sent a 6-digit code to
              </p>
              <p className="font-medium text-gray-900 mt-1">{formData.email}</p>
            </div>

            {/* Error display */}
            {displayError && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm mb-6 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <span>{displayError}</span>
              </div>
            )}

            {/* OTP Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3 text-center">
                Enter verification code
              </label>
              <div 
                className="flex justify-center gap-2 sm:gap-3"
                onPaste={handleOTPPaste}
              >
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => { otpRefs.current[index] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOTPChange(index, e.target.value)}
                    onKeyDown={(e) => handleOTPKeyDown(index, e)}
                    disabled={isVerifyingOTP || isSubmitting}
                    className="w-11 h-14 sm:w-12 sm:h-16 text-center text-xl sm:text-2xl font-bold border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition disabled:opacity-50 disabled:bg-gray-50"
                    data-testid={`otp-input-${index}`}
                  />
                ))}
              </div>
              
              {/* Attempts remaining */}
              {attemptsRemaining !== null && attemptsRemaining > 0 && (
                <p className="text-center text-sm text-orange-600 mt-3">
                  {attemptsRemaining} attempt{attemptsRemaining !== 1 ? 's' : ''} remaining
                </p>
              )}
            </div>

            {/* Verify Button */}
            <button
              onClick={() => handleVerifyOTP()}
              disabled={otp.some(d => !d) || isVerifyingOTP || isSubmitting}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mb-4"
              data-testid="verify-otp-btn"
            >
              {isVerifyingOTP || isSubmitting ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  Verify & Continue
                </>
              )}
            </button>

            {/* Resend OTP */}
            <div className="text-center">
              <p className="text-sm text-gray-500 mb-2">Didn&apos;t receive the code?</p>
              <button
                onClick={handleResendOTP}
                disabled={resendCooldown > 0 || isResending}
                className="text-sm text-blue-600 hover:underline disabled:text-gray-400 disabled:no-underline flex items-center justify-center gap-2 mx-auto"
                data-testid="resend-otp-btn"
              >
                {isResending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
                    Sending...
                  </>
                ) : resendCooldown > 0 ? (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    Resend in {resendCooldown}s
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    Resend OTP
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Details form (Step 1)
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Create Account</h1>
            <p className="text-gray-500 mt-2">Join India&apos;s largest B2B marketplace</p>
            <div className="flex items-center justify-center gap-2 mt-4 text-xs text-gray-400">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded">1. Sign Up</span>
              <span>→</span>
              <span>2. Verify OTP</span>
              <span>→</span>
              <span>3. Complete Profile</span>
            </div>
          </div>

          <form onSubmit={handleRequestOTP} className="space-y-5">
            {displayError && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <span>{displayError}</span>
              </div>
            )}

            {/* Name Field */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                Full Name
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                required
                autoComplete="name"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="John Doe"
                data-testid="register-name"
              />
            </div>

            {/* Email Field */}
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
                data-testid="register-email"
              />
            </div>

            {/* Password Field */}
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
                  data-testid="register-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {/* Confirm Password Field */}
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
                data-testid="register-confirm-password"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting || authLoading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="register-submit-btn"
            >
              {isSubmitting ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
              ) : (
                <>
                  <UserPlus className="h-5 w-5" />
                  Continue
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link href="/login" className="text-blue-600 hover:underline">
              Sign In
            </Link>
          </div>
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
