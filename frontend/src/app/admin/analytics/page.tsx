'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  Users,
  TrendingUp,
  FileText,
  Package,
  DollarSign,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  RefreshCw
} from 'lucide-react';

interface OverviewData {
  timestamp: string;
  period: string;
  users: {
    total: number;
    sellers: number;
    buyers: number;
    newThisMonth: number;
    suspended: number;
  };
  sellers: {
    total: number;
    free: number;
    trial: number;
    pro: number;
    enterprise: number;
    suspended: number;
  };
  inquiries: {
    total: number;
    pending: number;
    accepted: number;
    thisMonth: number;
  };
  quotes: {
    total: number;
    sent: number;
    viewed: number;
    accepted: number;
    rejected: number;
    expired: number;
    acceptanceRate: number;
  };
  performance: {
    avgResponseTimeHours: number;
    activeListings: number;
  };
}

interface RevenueData {
  subscriptions: {
    active: { total: number; trial: number; pro: number; enterprise: number };
    bySource: { manual: number; payment: number; unknown: number };
  };
  revenue: {
    projectedMRR: number;
    projectedMRRFormatted: string;
  };
  conversion: {
    upgradesThisMonth: number;
    conversionRate: number;
    totalFreeSellers: number;
  };
  leadLimits: {
    freeSellersAtLimit: number;
    leadLimitForFree: number;
  };
}

export default function AdminAnalyticsDashboard() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }

      // Ensure API_URL always ends with /api
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'https://midconnect.onrender.com';
      const cleanUrl = baseUrl.replace(/\/+$/, '');
      const API_URL = cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
      
      const [overviewRes, revenueRes] = await Promise.all([
        fetch(`${API_URL}/admin/analytics/overview`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${API_URL}/admin/analytics/revenue`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (!overviewRes.ok || !revenueRes.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const [overviewData, revenueData] = await Promise.all([
        overviewRes.json(),
        revenueRes.json()
      ]);

      setOverview(overviewData);
      setRevenue(revenueData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        fetchData();
      }
    }
  }, [user, authLoading]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 rounded-xl p-8 max-w-md text-center border border-slate-700">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error Loading Analytics</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button onClick={handleRefresh} className="text-blue-400 hover:underline">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <BarChart3 className="h-7 w-7 text-blue-500" />
                Admin Analytics
              </h1>
              <p className="text-slate-400 text-sm mt-1">Marketplace Control Center</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                data-testid="refresh-btn"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <Link
                href="/admin/market-monitor"
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm"
              >
                Market Monitor
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Total Users"
            value={overview?.users.total || 0}
            icon={<Users className="h-5 w-5" />}
            color="blue"
            subtext={`+${overview?.users.newThisMonth || 0} this month`}
          />
          <StatCard
            label="Active Sellers"
            value={overview?.sellers.total || 0}
            icon={<TrendingUp className="h-5 w-5" />}
            color="green"
            subtext={`${overview?.sellers.suspended || 0} suspended`}
          />
          <StatCard
            label="Total Quotes"
            value={overview?.quotes.total || 0}
            icon={<FileText className="h-5 w-5" />}
            color="purple"
            subtext={`${overview?.quotes.acceptanceRate || 0}% acceptance`}
          />
          <StatCard
            label="Projected MRR"
            value={revenue?.revenue.projectedMRRFormatted || '₹0'}
            icon={<DollarSign className="h-5 w-5" />}
            color="emerald"
            subtext="Based on active plans"
            isText
          />
        </div>

        {/* Seller Breakdown */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700" data-testid="seller-breakdown">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-500" />
              Seller Breakdown
            </h3>
            <div className="space-y-3">
              <ProgressBar label="Free" value={overview?.sellers.free || 0} total={overview?.sellers.total || 1} color="slate" />
              <ProgressBar label="Trial" value={overview?.sellers.trial || 0} total={overview?.sellers.total || 1} color="yellow" />
              <ProgressBar label="Pro" value={overview?.sellers.pro || 0} total={overview?.sellers.total || 1} color="blue" />
              <ProgressBar label="Enterprise" value={overview?.sellers.enterprise || 0} total={overview?.sellers.total || 1} color="purple" />
            </div>
            <div className="mt-4 pt-4 border-t border-slate-700 flex items-center justify-between text-sm">
              <span className="text-slate-400">At lead limit (free)</span>
              <span className="text-orange-400 font-medium">{revenue?.leadLimits.freeSellersAtLimit || 0}</span>
            </div>
          </div>

          {/* Quote Funnel */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700" data-testid="quote-funnel">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-500" />
              Quote Funnel
            </h3>
            <div className="space-y-3">
              <FunnelItem label="Sent" value={overview?.quotes.sent || 0} icon={<Clock className="h-4 w-4 text-blue-400" />} />
              <FunnelItem label="Viewed" value={overview?.quotes.viewed || 0} icon={<CheckCircle className="h-4 w-4 text-purple-400" />} />
              <FunnelItem label="Accepted" value={overview?.quotes.accepted || 0} icon={<CheckCircle className="h-4 w-4 text-green-400" />} />
              <FunnelItem label="Rejected" value={overview?.quotes.rejected || 0} icon={<XCircle className="h-4 w-4 text-red-400" />} />
              <FunnelItem label="Expired" value={overview?.quotes.expired || 0} icon={<AlertTriangle className="h-4 w-4 text-yellow-400" />} />
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h4 className="text-sm text-slate-400 mb-2">Avg Response Time</h4>
            <p className="text-3xl font-bold">{overview?.performance.avgResponseTimeHours.toFixed(1) || 0}h</p>
            <p className="text-sm text-slate-500 mt-1">Lead acceptance</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h4 className="text-sm text-slate-400 mb-2">Active Listings</h4>
            <p className="text-3xl font-bold">{overview?.performance.activeListings || 0}</p>
            <p className="text-sm text-slate-500 mt-1">Seller products</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h4 className="text-sm text-slate-400 mb-2">Upgrade Rate</h4>
            <p className="text-3xl font-bold">{revenue?.conversion.conversionRate || 0}%</p>
            <p className="text-sm text-slate-500 mt-1">{revenue?.conversion.upgradesThisMonth || 0} this month</p>
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid md:grid-cols-3 gap-4">
          <Link
            href="/admin/ranking-control"
            className="bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-blue-500 transition group"
            data-testid="ranking-control-link"
          >
            <h3 className="font-semibold flex items-center gap-2">
              Ranking Control
              <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition" />
            </h3>
            <p className="text-sm text-slate-400 mt-1">Manage ranking weights</p>
          </Link>
          <Link
            href="/admin/market-monitor"
            className="bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-orange-500 transition group"
            data-testid="market-monitor-link"
          >
            <h3 className="font-semibold flex items-center gap-2">
              Market Monitor
              <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition" />
            </h3>
            <p className="text-sm text-slate-400 mt-1">Abuse detection & governance</p>
          </Link>
          <Link
            href="/admin/gst-verification"
            className="bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-green-500 transition group"
          >
            <h3 className="font-semibold flex items-center gap-2">
              GST Verification
              <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition" />
            </h3>
            <p className="text-sm text-slate-400 mt-1">Pending verifications</p>
          </Link>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, icon, color, subtext, isText = false }: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  subtext: string;
  isText?: boolean;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    purple: 'bg-purple-500/20 text-purple-400',
    emerald: 'bg-emerald-500/20 text-emerald-400'
  };

  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
      <div className={`inline-flex p-2 rounded-lg mb-3 ${colorClasses[color]}`}>
        {icon}
      </div>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-2xl font-bold mt-1">{isText ? value : value.toLocaleString()}</p>
      <p className="text-xs text-slate-500 mt-1">{subtext}</p>
    </div>
  );
}

function ProgressBar({ label, value, total, color }: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  const colorClasses: Record<string, string> = {
    slate: 'bg-slate-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500',
    purple: 'bg-purple-500'
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="text-slate-400">{value}</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${colorClasses[color]} rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function FunnelItem({ label, value, icon }: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-700/50 rounded-lg">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
