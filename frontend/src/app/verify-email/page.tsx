'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Mail, RefreshCw, CheckCircle, ArrowRight, Loader2, XCircle } from 'lucide-react';
import { verifyEmailToken } from '@/lib/api';

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const verified = searchParams.get('verified');
  
  const { user, profile, resendVerificationEmail, refreshProfile, signOut } = useAuth();
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'waiting'>('waiting');
  const [message, setMessage] = useState('');
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  // Handle token verification on page load
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) return;
      
      setStatus('loading');
      setMessage('Verifying your email...');
      
      try {
        const data = await verifyEmailToken(token);
        
        if (data.success) {
          setStatus('success');
          setMessage(data.message || 'Email verified successfully!');
          
          // Redirect to login after a short delay
          setTimeout(() => {
            router.push('/login?verified=true');
          }, 2000);
        } else {
          setStatus('error');
          setMessage('Verification failed. Please try again.');
        }
      } catch (error: unknown) {
        setStatus('error');
        const errorMessage = error instanceof Error ? error.message : 'Verification failed';
        setMessage(errorMessage || 'An error occurred during verification. Please try again.');
      }
    };
    
    verifyToken();
  }, [token, router]);

  // If user is logged in and already verified, redirect
  useEffect(() => {
    if (verified === 'true') {
      setStatus('success');
      setMessage('Email verified successfully! Redirecting to login...');
      setTimeout(() => router.push('/login'), 1500);
      return;
    }
    
    if (user && profile?.isEmailVerified) {
      router.push('/complete-profile');
    }
  }, [user, profile, router, verified]);

  // Poll for verification status (for users waiting on the page)
  useEffect(() => {
    if (!user || token || status !== 'waiting') return;
    
    const interval = setInterval(async () => {
      await refreshProfile();
      // The refreshProfile will update the profile, and the useEffect above will handle redirect
    }, 5000);
    
    return () => clearInterval(interval);
  }, [user, token, status, refreshProfile]);

  const handleResendEmail = async () => {
    setIsResending(true);
    setResendSuccess(false);
    setMessage('');
    
    try {
      // ENTERPRISE FIX: No email parameter needed - backend gets it from auth token
      await resendVerificationEmail();
      setResendSuccess(true);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to send email');
    } finally {
      setIsResending(false);
    }
  };

  const handleCheckVerification = async () => {
    setStatus('loading');
    setMessage('Checking verification status...');
    
    try {
      await refreshProfile();
      
      // Check if now verified (profile state will be updated)
      setTimeout(() => {
        if (profile?.isEmailVerified) {
          router.push('/complete-profile');
        } else {
          setStatus('waiting');
          setMessage('Email not yet verified. Please check your inbox.');
        }
      }, 500);
    } catch {
      setStatus('waiting');
      setMessage('Failed to check. Please try again.');
    }
  };

  // Token verification view (when user clicks email link)
  if (token) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            {status === 'loading' && (
              <>
                <Loader2 className="h-16 w-16 text-blue-600 animate-spin mx-auto mb-6" />
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Verifying Email</h1>
                <p className="text-gray-600">{message}</p>
              </>
            )}
            
            {status === 'success' && (
              <>
                <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Email Verified!</h1>
                <p className="text-gray-600 mb-6">{message}</p>
                <p className="text-sm text-gray-500">Redirecting to login...</p>
              </>
            )}
            
            {status === 'error' && (
              <>
                <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
                  <XCircle className="h-8 w-8 text-red-600" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h1>
                <p className="text-red-600 mb-6">{message}</p>
                <div className="space-y-3">
                  <button
                    onClick={() => router.push('/register')}
                    className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition"
                  >
                    Back to Register
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Waiting for verification view (after signup)
  if (!user) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6">
            <Mail className="h-8 w-8 text-blue-600" />
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Verify Your Email</h1>
          <p className="text-gray-600 mb-6">We have sent a verification link to:</p>
          <p className="font-medium text-gray-900 mb-6 bg-gray-50 py-2 px-4 rounded-lg">
            {user.email}
          </p>
          <p className="text-sm text-gray-500 mb-8">
            Click the link in the email to verify your account. The email may take a few minutes to arrive.
          </p>

          {message && !resendSuccess && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">
              {message}
            </div>
          )}
          
          {resendSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded-lg text-sm mb-6 flex items-center gap-2 justify-center">
              <CheckCircle className="h-4 w-4" /> 
              Verification email sent! Please check your inbox.
            </div>
          )}

          <div className="space-y-3">
            <button
              onClick={handleCheckVerification}
              disabled={status === 'loading'}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {status === 'loading' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <ArrowRight className="h-5 w-5" />
                  I have Verified My Email
                </>
              )}
            </button>
            
            <button
              onClick={handleResendEmail}
              disabled={isResending}
              className="w-full border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isResending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <RefreshCw className="h-5 w-5" />
                  Resend Verification Email
                </>
              )}
            </button>
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 mb-3">
              Didn't receive the email? Check your spam folder.
            </p>
            <button
              onClick={async () => {
                await signOut();
                router.push('/register');
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Use a different email address
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-[80vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
