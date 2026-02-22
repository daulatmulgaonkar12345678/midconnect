'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Mail, RefreshCw, CheckCircle, ArrowRight } from 'lucide-react';

export default function VerifyEmailPage() {
  const router = useRouter();
  const { user, emailVerified, resendVerificationEmail, checkEmailVerification, signOut } = useAuth();
  
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { router.push('/register'); return; }
    if (emailVerified) { router.push('/complete-profile'); }
  }, [user, emailVerified, router]);

  useEffect(() => {
    if (!user || emailVerified) return;
    const interval = setInterval(async () => {
      const verified = await checkEmailVerification();
      if (verified) router.push('/complete-profile');
    }, 3000);
    return () => clearInterval(interval);
  }, [user, emailVerified, checkEmailVerification, router]);

  const handleResendEmail = async () => {
    setIsResending(true); setError(''); setResendSuccess(false);
    try { await resendVerificationEmail(); setResendSuccess(true); }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to send'); }
    finally { setIsResending(false); }
  };

  const handleCheckVerification = async () => {
    setIsChecking(true); setError('');
    try {
      const verified = await checkEmailVerification();
      if (verified) router.push('/complete-profile');
      else setError('Email not yet verified. Please check your inbox.');
    } catch { setError('Failed to check'); }
    finally { setIsChecking(false); }
  };

  if (!user) return null;

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6">
            <Mail className="h-8 w-8 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Verify Your Email</h1>
          <p className="text-gray-600 mb-6">We have sent a verification link to:</p>
          <p className="font-medium text-gray-900 mb-6 bg-gray-50 py-2 px-4 rounded-lg">{user.email}</p>
          <p className="text-sm text-gray-500 mb-8">Click the link in the email to verify your account.</p>

          {error && <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">{error}</div>}
          {resendSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded-lg text-sm mb-6 flex items-center gap-2 justify-center">
              <CheckCircle className="h-4 w-4" /> Verification email sent!
            </div>
          )}

          <div className="space-y-3">
            <button onClick={handleCheckVerification} disabled={isChecking}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50">
              {isChecking ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" /> : <><ArrowRight className="h-5 w-5" /> I have Verified My Email</>}
            </button>
            <button onClick={handleResendEmail} disabled={isResending}
              className="w-full border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition flex items-center justify-center gap-2 disabled:opacity-50">
              {isResending ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-700" /> : <><RefreshCw className="h-5 w-5" /> Resend Verification Email</>}
            </button>
          </div>
          <div className="mt-6 pt-6 border-t border-gray-200">
            <button onClick={async () => { await signOut(); router.push('/register'); }} className="text-sm text-gray-500 hover:text-gray-700">
              Use a different email address
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
