'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getSellerDashboard, getSellerSubscription, SellerSubscriptionStatus, getSellerStatus, SellerStatus } from '@/lib/api';
import { 
  Plus, 
  Package, 
  Loader2, 
  AlertCircle, 
  Eye,
  PauseCircle,
  FileText,
  Archive,
  MessageSquare,
  Zap,
  TrendingUp,
  ArrowRight,
  Crown,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Store
} from 'lucide-react';
import Link from 'next/link';
import { Suspense } from 'react';

function SellerDashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, profile, getIdToken, loading: authLoading, isSeller, isGstVerified } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    draft: 0,
    active: 0,
    paused: 0,
    archived: 0
  });
  const [subscription, setSubscription] = useState<SellerSubscriptionStatus | null>(null);
  const [sellerStatus, setSellerStatus] = useState<SellerStatus | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);

  // Check for welcome parameter
  useEffect(() => {
    if (searchParams.get('welcome') === 'true') {
      setShowWelcome(true);
    }
  }, [searchParams]);

  const loadDashboard = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }
      
      const [dashboardData, subscriptionData, statusData] = await Promise.all([
        getSellerDashboard(token),
        getSellerSubscription(token).catch(() => null),
        getSellerStatus(token).catch(() => null)
      ]);
      
      if (dashboardData?.stats) {
        setStats({
          total: dashboardData.stats.total ?? 0,
          draft: dashboardData.stats.draft ?? 0,
          active: dashboardData.stats.active ?? 0,
          paused: dashboardData.stats.paused ?? 0,
          archived: dashboardData.stats.archived ?? 0
        });
      }
      if (subscriptionData) {
        setSubscription(subscriptionData);
      }
      if (statusData) {
        setSellerStatus(statusData);
      }
    } catch (err) {
      // PHASE 7: Handle non-seller access
      if (err instanceof Error && err.message.includes('seller')) {
        setError('You must register as a seller to access this section.');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router]);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadDashboard();
      }
    }
  }, [user, authLoading, loadDashboard, router]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // PHASE 7: Non-seller access block
  if (!isSeller && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-6">
            <Store className="h-8 w-8 text-gray-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Seller Access Required</h1>
          <p className="text-gray-600 mb-6">
            Register as a seller to access the seller dashboard and list your products.
          </p>
          <Link
            href="/become-seller"
            className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium"
          >
            <Store className="h-5 w-5" />
            Become a Seller
          </Link>
        </div>
      </div>
    );
  }

  // Get GST status from profile or sellerStatus
  const gstStatus = sellerStatus?.gst?.status || profile?.gst?.status;
  const gstVerified = sellerStatus?.permissions?.canPublish || isGstVerified;
  const canCreateDraft = sellerStatus?.permissions?.canCreateDraft ?? isSeller;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Welcome Banner for new sellers */}
      {showWelcome && (
        <div className="bg-green-600 text-white px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5" />
              <span className="font-medium">Welcome! Your seller account has been created.</span>
            </div>
            <button
              onClick={() => setShowWelcome(false)}
              className="text-white/80 hover:text-white"
            >
              &times;
            </button>
          </div>
        </div>
      )}

      {/* PHASE 7: GST Verification Status Banner */}
      {isSeller && !gstVerified && (
        <div className={`px-4 py-3 ${gstStatus === 'rejected' ? 'bg-red-500' : 'bg-amber-500'} text-white`}>
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            {gstStatus === 'rejected' ? (
              <>
                <ShieldAlert className="h-5 w-5" />
                <span className="font-medium">GST verification rejected. Please re-submit valid documents.</span>
              </>
            ) : (
              <>
                <Clock className="h-5 w-5" />
                <span className="font-medium">GST verification in progress. You can create drafts but cannot publish until verified.</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Seller Dashboard</h1>
              <p className="text-gray-600 mt-1">Overview of your B2B marketplace activity</p>
            </div>
            
            {/* Primary Actions - Daily Use */}
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/seller/pricing"
                className="flex items-center gap-2 px-4 py-2.5 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition font-medium shadow-sm"
                data-testid="quick-price-header-btn"
              >
                <Zap className="h-5 w-5" />
                Quick Price Update
              </Link>
              <Link
                href="/seller/inquiries"
                className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition font-medium shadow-sm"
                data-testid="inquiries-header-btn"
              >
                <MessageSquare className="h-5 w-5" />
                Buyer Inquiries
              </Link>
              {canCreateDraft && (
                <Link
                  href="/seller/listings/new"
                  className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
                  data-testid="new-listing-header-btn"
                >
                  <Plus className="h-5 w-5" />
                  New Listing
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          {/* Subscription Status Card */}
          {subscription && (
            <Link
              href="/seller/subscription"
              className={`col-span-2 md:col-span-5 rounded-xl shadow-sm p-4 flex items-center justify-between ${
                subscription.subscription.status === 'active'
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white' 
                  : 'bg-white border border-gray-200'
              }`}
              data-testid="subscription-card"
            >
              <div className="flex items-center gap-3">
                <Crown className={`h-6 w-6 ${subscription.subscription.status === 'active' ? 'text-white' : 'text-gray-400'}`} />
                <div>
                  <p className={`font-semibold ${subscription.subscription.status === 'active' ? 'text-white' : 'text-gray-900'}`}>
                    {subscription.subscription.planName || 'Free'} Plan
                  </p>
                  <p className={`text-sm ${subscription.subscription.status === 'active' ? 'text-white/90' : 'text-gray-500'}`}>
                    {subscription.subscription.status === 'active'
                      ? `${subscription.subscription.daysRemaining} days remaining`
                      : `${subscription.usage.acceptedThisMonth}/${subscription.usage.monthlyLimit} inquiries this month`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {subscription.subscription.status !== 'active' && (
                  <span className="text-xs bg-blue-600 text-white px-3 py-1 rounded-full">
                    Upgrade
                  </span>
                )}
                <ArrowRight className={`h-5 w-5 ${subscription.subscription.status === 'active' ? 'text-white' : 'text-gray-400'}`} />
              </div>
            </Link>
          )}
          
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Package className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                <p className="text-sm text-gray-500">Total</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Eye className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.active}</p>
                <p className="text-sm text-gray-500">Active</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <FileText className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.draft}</p>
                <p className="text-sm text-gray-500">Drafts</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <PauseCircle className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.paused}</p>
                <p className="text-sm text-gray-500">Paused</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <Archive className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.archived}</p>
                <p className="text-sm text-gray-500">Archived</p>
              </div>
            </div>
          </div>
        </div>

        {/* Primary Actions - Card Grid */}
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Link
            href="/seller/pricing"
            className="flex items-center gap-4 bg-gradient-to-r from-yellow-50 to-yellow-100 rounded-xl shadow-sm p-6 hover:shadow-md transition group border border-yellow-200"
            data-testid="quick-price-action"
          >
            <div className="p-3 bg-yellow-500 rounded-lg group-hover:bg-yellow-600 transition">
              <Zap className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">⚡ Quick Price Update</h3>
              <p className="text-sm text-gray-600">Update prices and quantity slabs</p>
            </div>
            <ArrowRight className="h-5 w-5 text-yellow-600" />
          </Link>
          
          <Link
            href="/seller/inquiries"
            className="flex items-center gap-4 bg-gradient-to-r from-purple-50 to-purple-100 rounded-xl shadow-sm p-6 hover:shadow-md transition group border border-purple-200"
            data-testid="inquiries-action"
          >
            <div className="p-3 bg-purple-600 rounded-lg group-hover:bg-purple-700 transition">
              <MessageSquare className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">📩 Buyer Enquiries</h3>
              <p className="text-sm text-gray-600">View and respond to enquiries</p>
            </div>
            <ArrowRight className="h-5 w-5 text-purple-600" />
          </Link>
          
          <Link
            href="/seller/listings/new"
            className="flex items-center gap-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl shadow-sm p-6 hover:shadow-md transition group border border-blue-200"
            data-testid="new-listing-action"
          >
            <div className="p-3 bg-blue-600 rounded-lg group-hover:bg-blue-700 transition">
              <Plus className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">➕ New Listing</h3>
              <p className="text-sm text-gray-600">Add a new product to sell</p>
            </div>
            <ArrowRight className="h-5 w-5 text-blue-600" />
          </Link>
          
          <Link
            href="/seller/listings"
            className="flex items-center gap-4 bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition group border"
            data-testid="view-listings-action"
          >
            <div className="p-3 bg-gray-100 rounded-lg group-hover:bg-gray-200 transition">
              <Package className="h-6 w-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">🔹 My Listings</h3>
              <p className="text-sm text-gray-600">View all your products</p>
            </div>
            <ArrowRight className="h-5 w-5 text-gray-400" />
          </Link>
        </div>

        {/* Getting Started Guide */}
        {stats.total === 0 && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-8 border border-blue-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">🚀 Getting Started</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">1</div>
                <div>
                  <h3 className="font-medium text-gray-900">Create Your First Listing</h3>
                  <p className="text-sm text-gray-600 mt-1">Add product details, images, and specifications</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">2</div>
                <div>
                  <h3 className="font-medium text-gray-900">Set Your Pricing</h3>
                  <p className="text-sm text-gray-600 mt-1">Define quantity-based pricing slabs</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">3</div>
                <div>
                  <h3 className="font-medium text-gray-900">Receive Buyer Enquiries</h3>
                  <p className="text-sm text-gray-600 mt-1">Accept quotes and connect via WhatsApp</p>
                </div>
              </div>
            </div>
            <div className="mt-6">
              <Link
                href="/seller/listings/new"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                <Plus className="h-5 w-5" />
                Create Your First Listing
              </Link>
            </div>
          </div>
        )}

        {/* Quick Navigation Info */}
        <div className="mt-8 p-6 bg-gray-100 rounded-xl">
          <h3 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Daily Seller Workflow
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-yellow-600">⚡</span>
              <p><strong>Morning:</strong> Update today's prices using Quick Price Update</p>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-purple-600">📩</span>
              <p><strong>Throughout day:</strong> Check and respond to buyer enquiries</p>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-blue-600">📦</span>
              <p><strong>As needed:</strong> Add new listings or update product details</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center">
          <p className="text-gray-600">India's trusted B2B marketplace</p>
          <p className="text-gray-500 text-sm mt-1">Connecting verified buyers and sellers across industries.</p>
        </div>
      </footer>
    </div>
  );
}
