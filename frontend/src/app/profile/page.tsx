'use client';

import { useAuth } from '@/context/AuthContext';
import RoleGuard from '@/components/RoleGuard';
import { User, Mail, Phone, MapPin, Building, BadgeCheck, ShieldAlert, Loader2 } from 'lucide-react';
import Link from 'next/link';

export default function ProfilePage() {
  return (
    <RoleGuard allowedRoles={['buyer', 'seller', 'admin']}>
      <ProfileContent />
    </RoleGuard>
  );
}

function ProfileContent() {
  const { profile, user, isAdmin, isSeller, loading, refreshProfile } = useAuth();

  if (loading || !profile) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600" />
        <p className="mt-4 text-gray-500">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Profile</h1>

      <div className="grid gap-6">
        {/* Account Status Card */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Account Status</h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              profile.accountStatus === 'ACTIVE' 
                ? 'bg-green-100 text-green-700' 
                : 'bg-yellow-100 text-yellow-700'
            }`}>
              {profile.accountStatus}
            </span>
          </div>

          <div className="flex flex-wrap gap-4">
            {/* Role Badge */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              isAdmin ? 'bg-purple-100 text-purple-700' :
              isSeller ? 'bg-blue-100 text-blue-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {isAdmin ? (
                <ShieldAlert className="h-4 w-4" />
              ) : isSeller ? (
                <Building className="h-4 w-4" />
              ) : (
                <User className="h-4 w-4" />
              )}
              <span className="font-medium">
                {isAdmin ? 'Administrator' : isSeller ? 'Verified Seller' : 'Buyer'}
              </span>
            </div>

            {/* Email Verified - Use backend's isEmailVerified */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              profile?.isEmailVerified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
            }`}>
              <Mail className="h-4 w-4" />
              <span>Email {profile?.isEmailVerified ? 'Verified' : 'Not Verified'}</span>
            </div>

            {/* GST Status */}
            {isSeller && (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                profile.gstStatus === 'VERIFIED' ? 'bg-green-100 text-green-700' :
                profile.gstStatus === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                <BadgeCheck className="h-4 w-4" />
                <span>GST {profile.gstStatus}</span>
              </div>
            )}
          </div>
        </div>

        {/* Business Information */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Business Information</h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm text-gray-500 mb-1">Business Name</label>
              <p className="text-gray-900 font-medium">{profile.businessName}</p>
            </div>
            
            <div>
              <label className="block text-sm text-gray-500 mb-1">Email</label>
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-gray-400" />
                <p className="text-gray-900">{profile.email}</p>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-500 mb-1">Phone</label>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-gray-400" />
                <p className="text-gray-900">+91 {profile.phone}</p>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-500 mb-1">Location</label>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" />
                <p className="text-gray-900">{profile.city}, {profile.state} - {profile.pincode}</p>
              </div>
            </div>

            {profile.gstNumber && (
              <div className="md:col-span-2">
                <label className="block text-sm text-gray-500 mb-1">GST Number</label>
                <p className="text-gray-900 font-mono">{profile.gstNumber}</p>
              </div>
            )}
          </div>
        </div>

        {/* Subscription Info (for sellers) */}
        {isSeller && profile.subscription && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription</h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm text-gray-500 mb-1">Status</label>
                <p className={`font-medium ${
                  profile.subscription.status === 'ACTIVE' ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {profile.subscription.status}
                </p>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Enquiries This Month</label>
                <p className="text-2xl font-bold text-gray-900">
                  {profile.subscription.enquiriesThisMonth}
                </p>
              </div>
              {profile.subscription.trialEndsAt && (
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Trial Ends</label>
                  <p className="text-gray-900">
                    {new Date(profile.subscription.trialEndsAt).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            {!isSeller && (
              <Link
                href="/sell"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Become a Seller
              </Link>
            )}
            {isSeller && (
              <Link
                href="/dashboard"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                My Listings
              </Link>
            )}
            {isAdmin && (
              <Link
                href="/admin"
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition"
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={() => refreshProfile()}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition"
            >
              Refresh Profile
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
