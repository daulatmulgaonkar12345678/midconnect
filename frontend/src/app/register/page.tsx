'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { Eye, EyeOff, UserPlus, AlertCircle, Mail } from 'lucide-react';
import { Suspense } from 'react';

function RegisterContent() {
  const router = useRouter();
  const { signUp, error, clearError, loading: authLoading, user, needsEmailVerification, needsRegistration, isAuthenticated } = useAuth();
  
  const [formData, setFormData] = useState({ email: '', password: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      if (needsEmailVerification) router.push('/verify-email');
      else if (needsRegistration) router.push('/complete-profile');
      else if (isAuthenticated) router.push('/dashboard');
    }
  }, [user, needsEmailVerification, needsRegistration, isAuthenticated, router]);

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: field === 'email' ? value.toLowerCase().slice(0, 100) : value.slice(0, 100) }));
  };

  const validateForm = () => {
    setLocalError('');
    if (!formData.email) { setLocalError('Email is required'); return false; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { setLocalError('Please enter a valid email'); return false; }
    if (!formData.password) { setLocalError('Password is required'); return false; }
    if (formData.password.length < 6) { setLocalError('Password must be at least 6 characters'); return false; }
    if (formData.password !== formData.confirmPassword) { setLocalError('Passwords do not match'); return false; }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validateForm()) return;
    setIsSubmitting(true);
    try {
      const result = await signUp(formData.email.trim(), formData.password);
      if (result.needsEmailVerification) {
        setRegistrationSuccess(true);
        setTimeout(() => router.push('/verify-email'), 2000);
      }
    } catch {} finally { setIsSubmitting(false); }
  };

  const displayError = localError || error;

  if (registrationSuccess) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6"><Mail className="h-8 w-8 text-green-600" /></div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Check Your Email</h1>
            <p className="text-gray-600 mb-4">We have sent a verification link to:</p>
            <p className="font-medium text-gray-900 mb-6 bg-gray-50 py-2 px-4 rounded-lg">{formData.email}</p>
            <div className="flex items-center justify-center gap-2 text-blue-600"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" /><span>Redirecting...</span></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Create Account</h1>
            <p className="text-gray-500 mt-2">Join India&apos;s largest B2B marketplace</p>
            <div className="flex items-center justify-center gap-2 mt-4 text-xs text-gray-400">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded">1. Sign Up</span><span>→</span><span>2. Verify Email</span><span>→</span><span>3. Complete Profile</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {displayError && <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm flex items-start gap-2"><AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" /><span>{displayError}</span></div>}
            <div><label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">Email Address</label><input id="email" type="email" value={formData.email} onChange={(e) => handleChange('email', e.target.value)} required autoComplete="email" className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="you@example.com" data-testid="register-email" /></div>
            <div><label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">Password</label><div className="relative"><input id="password" type={showPassword ? 'text' : 'password'} value={formData.password} onChange={(e) => handleChange('password', e.target.value)} required autoComplete="new-password" className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="At least 6 characters" data-testid="register-password" /><button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-3.5 text-gray-400">{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}</button></div></div>
            <div><label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label><input id="confirmPassword" type="password" value={formData.confirmPassword} onChange={(e) => handleChange('confirmPassword', e.target.value)} required autoComplete="new-password" className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="Confirm your password" data-testid="register-confirm-password" /></div>
            <button type="submit" disabled={isSubmitting || authLoading} className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50" data-testid="register-submit-btn">{isSubmitting ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" /> : <><UserPlus className="h-5 w-5" /> Create Account</>}</button>
          </form>
          <div className="mt-6 text-center text-sm text-gray-500">Already have an account? <Link href="/login" className="text-blue-600 hover:underline">Sign In</Link></div>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (<Suspense fallback={<div className="min-h-[80vh] flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>}><RegisterContent /></Suspense>);
}
