'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAdminStats, AdminStats } from '@/lib/api';
import { Users, Package, TrendingUp, AlertCircle, FolderTree, ClipboardList, Loader2, CreditCard, Clock, UserCheck, BarChart3 } from 'lucide-react';
import Link from 'next/link';

export default function AdminDashboard() {
  const { getIdToken } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const data = await getAdminStats(token);
      
      // Defensive guard: Validate API response structure
      if (!data || typeof data !== 'object') {
        console.error('[DATA INTEGRITY] Invalid API response:', data);
        throw new Error('Invalid API response structure');
      }
      
      if (!data.stats || typeof data.stats !== 'object') {
        console.error('[DATA INTEGRITY] Missing stats object in response:', data);
        throw new Error('Missing stats object in API response');
      }
      
      setStats(data.stats);
    } catch (err: any) {
      console.error('Failed to fetch stats:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        <p>Failed to load stats: {error}</p>
        <button onClick={fetchStats} className="mt-2 text-sm underline">Retry</button>
      </div>
    );
  }

  const statCards = [
    { label: 'Total Users', value: stats?.users?.total ?? 0, icon: Users, color: 'blue', subtext: `${stats?.users?.active ?? 0} active` },
    { label: 'Verified Sellers', value: stats?.users?.sellers ?? 0, icon: Users, color: 'green', subtext: `${stats?.users?.pendingGst ?? 0} pending GST` },
    { label: 'Total Inquiries', value: stats?.inquiries?.total ?? 0, icon: AlertCircle, color: 'pink', subtext: `${stats?.inquiries?.pending ?? 0} pending` },
    { label: 'Active Listings', value: stats?.listings?.active ?? 0, icon: Package, color: 'orange', subtext: `${stats?.listings?.drafts ?? 0} drafts` },
  ];

  const subscriptionCards = [
    { label: 'Pro Subscriptions', value: stats?.subscriptions?.pro ?? 0, icon: CreditCard, color: 'blue', subtext: 'Active paid plans' },
    { label: 'Trial Users', value: stats?.subscriptions?.trial ?? 0, icon: Clock, color: 'purple', subtext: '90-day trial' },
    { label: 'Free Sellers', value: (stats?.subscriptions?.free ?? 0) + (stats?.subscriptions?.noSubscription ?? 0), icon: UserCheck, color: 'gray', subtext: '5 leads/month limit' },
    { label: 'Expiring Soon', value: stats?.subscriptions?.expiringSoon ?? 0, icon: AlertCircle, color: 'red', subtext: 'Next 7 days' },
  ];

  const catalogCards = [
    { label: 'Categories', value: stats?.catalog?.categories ?? 0, icon: FolderTree, color: 'purple', subtext: 'Active categories' },
    { label: 'Products', value: stats?.catalog?.products ?? 0, icon: Package, color: 'indigo', subtext: 'In master catalog' },
    { label: 'Spec Templates', value: stats?.catalog?.specTemplates ?? 0, icon: ClipboardList, color: 'teal', subtext: 'Active templates' },
    { label: 'Deleted Users', value: stats?.users?.deleted ?? 0, icon: Users, color: 'red', subtext: 'Pending restoration' },
  ];

  return (
    <div data-testid="admin-dashboard">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-500">Overview of your B2B marketplace</p>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl shadow-sm p-6" data-testid={`stat-card-${stat.label.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-lg bg-${stat.color}-100`}>
                <stat.icon className={`h-6 w-6 text-${stat.color}-600`} />
              </div>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="text-xs text-gray-400 mt-1">{stat.subtext}</p>
          </div>
        ))}
      </div>

      {/* Subscription Stats */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {subscriptionCards.map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl shadow-sm p-6" data-testid={`subscription-card-${stat.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg bg-${stat.color}-100`}>
                  <stat.icon className={`h-6 w-6 text-${stat.color}-600`} />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-xs text-gray-400 mt-1">{stat.subtext}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Catalog Stats */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Catalog & Users</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {catalogCards.map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg bg-${stat.color}-100`}>
                  <stat.icon className={`h-6 w-6 text-${stat.color}-600`} />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-xs text-gray-400 mt-1">{stat.subtext}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <Link
            href="/admin/analytics"
            className="block p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg hover:from-blue-100 hover:to-indigo-100 transition border border-blue-200"
            data-testid="quick-action-analytics"
          >
            <TrendingUp className="h-8 w-8 text-blue-600 mb-2" />
            <h3 className="font-medium">Analytics</h3>
            <p className="text-sm text-gray-500">Revenue & Growth</p>
          </Link>
          <Link
            href="/admin/users"
            className="block p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg hover:from-purple-100 hover:to-pink-100 transition border border-purple-200"
            data-testid="quick-action-users"
          >
            <Users className="h-8 w-8 text-purple-600 mb-2" />
            <h3 className="font-medium">Users</h3>
            <p className="text-sm text-gray-500">Users & Subscriptions</p>
          </Link>
          <Link
            href="/admin/leads"
            className="block p-4 bg-pink-50 rounded-lg hover:bg-pink-100 transition"
            data-testid="quick-action-leads"
          >
            <BarChart3 className="h-8 w-8 text-pink-600 mb-2" />
            <h3 className="font-medium">View Leads</h3>
            <p className="text-sm text-gray-500">All inquiries</p>
          </Link>
          <Link
            href="/admin/categories"
            className="block p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition"
          >
            <FolderTree className="h-8 w-8 text-purple-600 mb-2" />
            <h3 className="font-medium">Categories</h3>
            <p className="text-sm text-gray-500">Manage catalog</p>
          </Link>
          <Link
            href="/admin/products"
            className="block p-4 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition"
          >
            <Package className="h-8 w-8 text-indigo-600 mb-2" />
            <h3 className="font-medium">Products</h3>
            <p className="text-sm text-gray-500">Master catalog</p>
          </Link>
          <Link
            href="/admin/spec-templates"
            className="block p-4 bg-teal-50 rounded-lg hover:bg-teal-100 transition"
          >
            <ClipboardList className="h-8 w-8 text-teal-600 mb-2" />
            <h3 className="font-medium">Spec Templates</h3>
            <p className="text-sm text-gray-500">Define specs</p>
          </Link>
        </div>
      </div>

      {/* Pending Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Pending GST Verifications</h2>
          {stats?.users?.pendingGst === 0 ? (
            <p className="text-gray-500 text-sm">No pending verifications</p>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold text-yellow-600">{stats?.users?.pendingGst}</p>
                <p className="text-sm text-gray-500">Awaiting review</p>
              </div>
              <Link
                href="/admin/gst-verification"
                className="px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition"
              >
                Review Now
              </Link>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Deleted Accounts</h2>
          {stats?.users.deleted === 0 ? (
            <p className="text-gray-500 text-sm">No deleted accounts</p>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold text-red-600">{stats?.users.deleted}</p>
                <p className="text-sm text-gray-500">Can be restored</p>
              </div>
              <Link
                href="/admin/users?status=deleted"
                className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition"
              >
                View All
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
