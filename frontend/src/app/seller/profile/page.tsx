'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  Loader2, 
  ArrowLeft,
  User,
  Building2,
  Mail,
  Phone,
  MapPin,
  Shield,
  CheckCircle,
  AlertCircle,
  Package,
  Key
} from 'lucide-react';
import Link from 'next/link';

export default function SellerProfilePage() {
  const router = useRouter();
  const { user, profile, loading: authLoading, signOut, isSeller } = useAuth();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        setLoading(false);
      }
    }
  }, [user, authLoading, router]);

  const handleSignOut = async () => {
    try {
      await signOut();
      router.push('/login');
    } catch (error) {
      console.error('Sign out error:', error);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const isVerified = profile?.gst?.status === 'verified' || profile?.gst?.verified || profile?.isEmailVerified;

  // Get profile data - it's nested in profile.profile
  const profileData = profile?.profile;
  const businessName = profileData?.businessName || profile?.businessName;
  const phone = profileData?.phone || profile?.phone;
  const city = profileData?.city;
  const state = profileData?.state;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <User className="h-5 w-5 text-blue-600" />
                Seller Profile
              </h1>
              <p className="text-sm text-gray-500">Manage your business information</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Profile Card */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden mb-6">
          {/* Profile Header */}
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center">
                <User className="h-10 w-10 text-blue-600" />
              </div>
              <div className="text-white">
                <h2 className="text-2xl font-bold">{businessName || user?.email?.split('@')[0] || 'Seller'}</h2>
                <p className="text-blue-100">{user?.email}</p>
                <div className="flex items-center gap-2 mt-2">
                  {isSeller && (
                    <span className="px-2 py-1 bg-green-500 text-white text-xs font-medium rounded-full flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Seller
                    </span>
                  )}
                  {isVerified ? (
                    <span className="px-2 py-1 bg-blue-400 text-white text-xs font-medium rounded-full flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      Verified
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-yellow-500 text-white text-xs font-medium rounded-full flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Pending Verification
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Profile Details */}
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Business Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                <Building2 className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Business Name</p>
                  <p className="font-medium text-gray-900">{businessName || 'Not set'}</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                <Mail className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="font-medium text-gray-900">{user?.email || 'Not set'}</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                <Phone className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Phone</p>
                  <p className="font-medium text-gray-900">{phone || 'Not set'}</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                <MapPin className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Location</p>
                  <p className="font-medium text-gray-900">
                    {city && state 
                      ? `${city}, ${state}` 
                      : city || state || 'Not set'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Links</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link
              href="/seller/listings"
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition"
              data-testid="my-listings-link"
            >
              <Package className="h-5 w-5 text-blue-600" />
              <div>
                <p className="font-medium text-gray-900">My Listings</p>
                <p className="text-sm text-gray-500">View and manage your products</p>
              </div>
            </Link>

            <Link
              href="/seller"
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition"
              data-testid="dashboard-link"
            >
              <Building2 className="h-5 w-5 text-green-600" />
              <div>
                <p className="font-medium text-gray-900">Seller Dashboard</p>
                <p className="text-sm text-gray-500">Overview of your activity</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Account Actions */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Account</h3>
          <div className="space-y-3">
            <Link
              href="/forgot-password"
              className="flex items-center gap-3 p-4 w-full border rounded-lg hover:bg-gray-50 transition text-left"
              data-testid="change-password-btn"
            >
              <Key className="h-5 w-5 text-gray-600" />
              <div>
                <p className="font-medium text-gray-900">Change Password</p>
                <p className="text-sm text-gray-500">Update your security credentials via OTP</p>
              </div>
            </Link>

            <button
              onClick={handleSignOut}
              className="flex items-center gap-3 p-4 w-full border border-red-200 rounded-lg hover:bg-red-50 transition text-left"
              data-testid="sign-out-btn"
            >
              <ArrowLeft className="h-5 w-5 text-red-600" />
              <div>
                <p className="font-medium text-red-600">Sign Out</p>
                <p className="text-sm text-red-400">Log out of your account</p>
              </div>
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <p className="text-gray-600">India's trusted B2B marketplace</p>
          <p className="text-gray-500 text-sm mt-1">Connecting verified buyers and sellers across industries.</p>
        </div>
      </footer>
    </div>
  );
}
