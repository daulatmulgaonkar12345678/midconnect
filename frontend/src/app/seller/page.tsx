'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getSellerDashboard, getSellerSubscription, SellerSubscriptionStatus } from '@/lib/api';
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
  Clock
} from 'lucide-react';
import Link from 'next/link';

export default function SellerDashboardPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading, isSeller, isGstVerified } = useAuth();
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

  const loadDashboard = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }
      
      const [dashboardData, subscriptionData] = await Promise.all([
        getSellerDashboard(token),
        getSellerSubscription(token).catch(() => null) // Non-blocking - subscription is optional
      ]);
      
      // Safely set stats with fallback to defaults
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
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

  return (
    <div className="min-h-screen bg-gray-50">
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
              <Link
                href="/seller/listings/new"
                className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
                data-testid="new-listing-header-btn"
              >
                <Plus className="h-5 w-5" />
                New Listing
              </Link>
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

        {/* GST Pending Banner - Show for sellers with unverified GST */}
        {isSeller && !isGstVerified && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3" data-testid="gst-pending-banner">
            <Clock className="h-6 w-6 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-800">GST Verification Pending</h3>
              <p className="text-sm text-amber-700 mt-1">
                Your GST number is being verified. You can create product drafts, but publishing will be enabled once verification is complete.
              </p>
            </div>
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
