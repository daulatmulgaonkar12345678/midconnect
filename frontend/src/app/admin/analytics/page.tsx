'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import type { AdminAnalytics, AdminKPIMetrics } from '@/types';
import { 
  getAdminAnalytics, 
  getAdminKPIMetrics
} from '@/lib/api';
import { 
  ArrowLeft, 
  Loader2,
  Users,
  Crown,
  TrendingUp,
  TrendingDown,
  DollarSign,
  RefreshCw,
  XCircle,
  Percent,
  AlertTriangle,
  BarChart3,
  Activity,
  Zap,
  Target,
  Shield,
  Database,
  CheckCircle,
  AlertCircle,
  Info,
  ChevronDown,
  Calendar
} from 'lucide-react';

// Brand Colors
const colors = {
  primary: '#1E3A8A',
  accent: { from: '#2563EB', to: '#7C3AED' },
  success: '#16A34A',
  warning: '#F59E0B',
  danger: '#DC2626',
  background: '#F8FAFC',
};

// Metric Card Component
function MetricCard({ 
  icon: Icon, 
  label, 
  value, 
  subtext, 
  trend,
  color = 'primary' 
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtext?: string;
  trend?: { value: number; positive: boolean };
  color?: 'primary' | 'success' | 'warning' | 'danger';
}) {
  const colorMap = {
    primary: { bg: '#EFF6FF', icon: colors.primary, border: '#BFDBFE' },
    success: { bg: '#DCFCE7', icon: colors.success, border: '#BBF7D0' },
    warning: { bg: '#FEF3C7', icon: colors.warning, border: '#FDE68A' },
    danger: { bg: '#FEE2E2', icon: colors.danger, border: '#FECACA' },
  };
  const c = colorMap[color];

  return (
    <div 
      className="bg-white rounded-xl p-6 border transition-all duration-200 hover:shadow-md"
      style={{ borderColor: c.border }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 rounded-xl" style={{ backgroundColor: c.bg }}>
          <Icon className="h-6 w-6" style={{ color: c.icon }} />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-sm ${trend.positive ? 'text-green-600' : 'text-red-600'}`}>
            {trend.positive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            {trend.value}%
          </div>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {subtext && <p className="text-xs text-gray-400 mt-2">{subtext}</p>}
    </div>
  );
}

// Section Header Component
function SectionHeader({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-lg" style={{ backgroundColor: '#EFF6FF' }}>
          <Icon className="h-5 w-5" style={{ color: colors.primary }} />
        </div>
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
      </div>
      <p className="text-gray-500 text-sm ml-12">{description}</p>
    </div>
  );
}

// Simple Bar Chart Component
function SimpleBarChart({ data, dataKey, color, label }: { 
  data: Array<{ month: string; [key: string]: string | number }>;
  dataKey: string;
  color: string;
  label: string;
}) {
  const maxValue = Math.max(...data.map(d => Number(d[dataKey]) || 0));
  
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-gray-700 mb-4">{label}</p>
      {data.map((item, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-16">{item.month}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500 flex items-center justify-end pr-2"
              style={{ 
                width: `${maxValue > 0 ? (Number(item[dataKey]) / maxValue * 100) : 0}%`,
                backgroundColor: color,
                minWidth: Number(item[dataKey]) > 0 ? '30px' : '0'
              }}
            >
              <span className="text-xs text-white font-medium">{item[dataKey]}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Comparison Line Chart (Free vs Pro)
function ComparisonChart({ data }: { 
  data: Array<{ month: string; freeSellers: number; proSellers: number }>;
}) {
  const maxValue = Math.max(...data.flatMap(d => [d.freeSellers, d.proSellers]));
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-6 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#94A3B8' }}></div>
          <span className="text-xs text-gray-600">Free Sellers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors.primary }}></div>
          <span className="text-xs text-gray-600">Pro Sellers</span>
        </div>
      </div>
      {data.map((item, idx) => (
        <div key={idx} className="space-y-1">
          <span className="text-xs text-gray-500">{item.month}</span>
          <div className="flex gap-2">
            <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
              <div 
                className="h-full rounded transition-all duration-500"
                style={{ 
                  width: `${maxValue > 0 ? (item.freeSellers / maxValue * 100) : 0}%`,
                  backgroundColor: '#94A3B8'
                }}
              />
            </div>
            <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
              <div 
                className="h-full rounded transition-all duration-500"
                style={{ 
                  width: `${maxValue > 0 ? (item.proSellers / maxValue * 100) : 0}%`,
                  backgroundColor: colors.primary
                }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Insight Badge Component
function InsightBadge({ type, message }: { type: 'positive' | 'neutral' | 'warning'; message: string }) {
  const config = {
    positive: { bg: '#DCFCE7', border: '#BBF7D0', icon: CheckCircle, color: colors.success },
    neutral: { bg: '#F3F4F6', border: '#E5E7EB', icon: Info, color: '#6B7280' },
    warning: { bg: '#FEF3C7', border: '#FDE68A', icon: AlertCircle, color: colors.warning },
  };
  const c = config[type];
  const Icon = c.icon;

  return (
    <div 
      className="flex items-start gap-3 p-4 rounded-xl border"
      style={{ backgroundColor: c.bg, borderColor: c.border }}
    >
      <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" style={{ color: c.color }} />
      <p className="text-sm text-gray-700">{message}</p>
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const router = useRouter();
  const { getIdToken, isAuthenticated, loading: authLoading, user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [kpiMetrics, setKpiMetrics] = useState<AdminKPIMetrics | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login?redirect=/admin/analytics');
      return;
    }

    loadData();
  }, [isAuthenticated, authLoading, selectedDays]);

  async function loadData() {
    try {
      setLoading(true);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const [analyticsData, kpiData] = await Promise.all([
        getAdminAnalytics(token, selectedDays),
        getAdminKPIMetrics(token)
      ]);
      
      setAnalytics(analyticsData);
      setKpiMetrics(kpiData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }

  if (loading || authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin mx-auto" style={{ color: colors.primary }} />
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center max-w-md mx-auto p-8">
          <AlertTriangle className="h-12 w-12 mx-auto mb-4" style={{ color: colors.danger }} />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Analytics</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button 
            onClick={loadData}
            className="px-6 py-3 rounded-lg font-medium text-white transition-all duration-200 hover:scale-[1.02]"
            style={{ backgroundColor: colors.primary }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const kpi = kpiMetrics;
  const anal = analytics;

  return (
    <div className="min-h-screen" style={{ backgroundColor: colors.background }}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <Link 
                href="/admin" 
                className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm mb-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Dashboard
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">Platform Analytics & Revenue Insights</h1>
              <p className="text-gray-500 mt-1">
                Real-time visibility into seller growth, subscription performance, and monetization metrics.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select 
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white"
                data-testid="days-selector"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <button 
                onClick={loadData}
                className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                title="Refresh data"
              >
                <RefreshCw className="h-5 w-5 text-gray-500" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-10">

        {/* ============== Section 1: Key Performance Overview ============== */}
        <section data-testid="kpi-overview-section">
          <SectionHeader 
            icon={BarChart3} 
            title="Key Performance Overview" 
            description="These metrics update automatically based on live platform data."
          />
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              icon={Users}
              label="Total Sellers"
              value={kpi?.sellerOverview.totalSellers || 0}
              subtext="All registered sellers (Free + Pro)"
              color="primary"
            />
            <MetricCard 
              icon={Crown}
              label="Active Pro Sellers"
              value={kpi?.sellerOverview.proSellers || 0}
              subtext="Pro subscriptions generating revenue"
              color="success"
            />
            <MetricCard 
              icon={TrendingUp}
              label="Free → Pro Conversion"
              value={`${kpi?.sellerOverview.conversionRate || 0}%`}
              subtext="Indicates upgrade effectiveness"
              color="primary"
            />
            <MetricCard 
              icon={DollarSign}
              label="Revenue This Quarter"
              value={`₹${(kpi?.revenue.estimatedQuarterlyRevenue || 0).toLocaleString('en-IN')}`}
              subtext="Based on Pro subscription payments"
              color="success"
            />
          </div>
        </section>

        {/* ============== Section 2: Subscription Performance ============== */}
        <section data-testid="subscription-health-section">
          <SectionHeader 
            icon={Activity} 
            title="Subscription Health" 
            description="Track subscription lifecycle and renewal performance."
          />
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              icon={RefreshCw}
              label="Renewals This Quarter"
              value={kpi?.subscriptionHealth.renewalsThisQuarter || 0}
              subtext="Pro subscriptions renewed"
              color="success"
            />
            <MetricCard 
              icon={XCircle}
              label="Expired Subscriptions"
              value={kpi?.subscriptionHealth.expiredSubscriptions || 0}
              subtext="Helps monitor churn risk"
              color="danger"
            />
            <MetricCard 
              icon={Percent}
              label="Churn Rate"
              value={`${kpi?.subscriptionHealth.churnRate || 0}%`}
              subtext="Lower = stronger perceived value"
              color={kpi?.subscriptionHealth.churnRate && kpi.subscriptionHealth.churnRate > 10 ? 'warning' : 'success'}
            />
            <MetricCard 
              icon={AlertTriangle}
              label="Expiring Soon"
              value={kpi?.subscriptionHealth.expiringSoon || 0}
              subtext="Subscriptions ending in 7 days"
              color="warning"
            />
          </div>
        </section>

        {/* ============== Section 3: Usage & Monetization Signals ============== */}
        <section data-testid="monetization-signals-section">
          <SectionHeader 
            icon={Zap} 
            title="Free Plan Pressure Metrics" 
            description="These metrics show whether your free limits are driving upgrades."
          />
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#FEF3C7' }}>
                  <Target className="h-5 w-5" style={{ color: colors.warning }} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Inquiry Limit Exhaustion Rate</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {kpi?.monetizationSignals.limitExhaustionRate || 0}%
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-400">
                {kpi?.monetizationSignals.freeSellersAtLimit || 0} free sellers hit their {kpi?.monetizationSignals.freeMonthlyLimit || 5}/month limit
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Higher exhaustion rate increases upgrade probability.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#EFF6FF' }}>
                  <BarChart3 className="h-5 w-5" style={{ color: colors.primary }} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Trial Sellers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {kpi?.sellerOverview.trialSellers || 0}
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-400">
                Currently on 90-day trial period
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Trial users experiencing full Pro benefits.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#DCFCE7' }}>
                  <TrendingUp className="h-5 w-5" style={{ color: colors.success }} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Free Sellers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {kpi?.sellerOverview.freeSellers || 0}
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-400">
                Potential upgrade candidates
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Each limited to {kpi?.monetizationSignals.freeMonthlyLimit || 5} inquiries/month.
              </p>
            </div>
          </div>
        </section>

        {/* ============== Section 4: Growth Trends (Charts) ============== */}
        <section data-testid="growth-trends-section">
          <SectionHeader 
            icon={TrendingUp} 
            title="Growth Trends" 
            description="Visualize platform maturity and revenue scaling over time."
          />
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Seller Growth Chart */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-4">Seller Growth Trend</h3>
              <p className="text-xs text-gray-400 mb-6">Free vs Pro seller growth over time</p>
              {kpi?.growthTrends && kpi.growthTrends.length > 0 ? (
                <ComparisonChart data={kpi.growthTrends} />
              ) : (
                <p className="text-gray-400 text-sm">No growth data available</p>
              )}
            </div>

            {/* Revenue Trend */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-4">Monthly Revenue</h3>
              <p className="text-xs text-gray-400 mb-6">Track monetization momentum</p>
              {kpi?.growthTrends && kpi.growthTrends.length > 0 ? (
                <SimpleBarChart 
                  data={kpi.growthTrends} 
                  dataKey="revenue" 
                  color={colors.success}
                  label="Revenue (₹)"
                />
              ) : (
                <p className="text-gray-400 text-sm">No revenue data available</p>
              )}
            </div>

            {/* Inquiry Activity */}
            <div className="bg-white rounded-xl p-6 border border-gray-100 lg:col-span-2">
              <h3 className="font-semibold text-gray-900 mb-4">Inquiry Activity Overview</h3>
              <p className="text-xs text-gray-400 mb-6">Total inquiries per period ({selectedDays} days)</p>
              {anal?.leadsPerDay && anal.leadsPerDay.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-gray-50">
                    <p className="text-sm text-gray-500">Total Inquiries</p>
                    <p className="text-2xl font-bold text-gray-900">{anal.rates.totalInquiries}</p>
                  </div>
                  <div className="p-4 rounded-lg" style={{ backgroundColor: '#DCFCE7' }}>
                    <p className="text-sm text-gray-500">Accepted</p>
                    <p className="text-2xl font-bold" style={{ color: colors.success }}>{anal.rates.accepted}</p>
                    <p className="text-xs text-gray-400">{anal.rates.approvalRate}% rate</p>
                  </div>
                  <div className="p-4 rounded-lg" style={{ backgroundColor: '#FEE2E2' }}>
                    <p className="text-sm text-gray-500">Rejected</p>
                    <p className="text-2xl font-bold" style={{ color: colors.danger }}>{anal.rates.rejected}</p>
                    <p className="text-xs text-gray-400">{anal.rates.rejectionRate}% rate</p>
                  </div>
                  <div className="p-4 rounded-lg" style={{ backgroundColor: '#FEF3C7' }}>
                    <p className="text-sm text-gray-500">Pending</p>
                    <p className="text-2xl font-bold" style={{ color: colors.warning }}>
                      {anal.rates.totalInquiries - anal.rates.accepted - anal.rates.rejected}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">No inquiry data available</p>
              )}
            </div>
          </div>
        </section>

        {/* ============== Section 5: Risk & Fraud Monitoring ============== */}
        <section data-testid="fraud-monitoring-section">
          <SectionHeader 
            icon={Shield} 
            title="Risk & Fraud Monitoring" 
            description="Seller risk signals and suspicious activity alerts."
          />
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* High Rejection Sellers */}
            <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" style={{ color: colors.danger }} />
                <h3 className="font-semibold text-gray-900">High Rejection Sellers</h3>
              </div>
              <div className="p-4">
                {anal?.fraudMonitoring.highRejectionSellers && anal.fraudMonitoring.highRejectionSellers.length > 0 ? (
                  <div className="space-y-3">
                    {anal.fraudMonitoring.highRejectionSellers.slice(0, 5).map((seller, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{seller.seller?.name || 'Unknown'}</p>
                          <p className="text-xs text-gray-500">{seller.seller?.email}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold" style={{ color: colors.danger }}>{seller.rejectionRatio}%</p>
                          <p className="text-xs text-gray-400">{seller.rejectedCount}/{seller.totalInquiries} rejected</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <CheckCircle className="h-8 w-8 mx-auto mb-2" style={{ color: colors.success }} />
                    <p className="text-sm text-gray-500">No high-rejection sellers detected</p>
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-4">
                  Sellers with &gt;50% rejection rate and &gt;5 inquiries. May indicate low responsiveness.
                </p>
              </div>
            </div>

            {/* Suspicious Activity */}
            <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" style={{ color: colors.warning }} />
                <h3 className="font-semibold text-gray-900">Suspicious Activity Alerts</h3>
              </div>
              <div className="p-4">
                {anal?.fraudMonitoring.potentialSpamBuyers && anal.fraudMonitoring.potentialSpamBuyers.length > 0 ? (
                  <div className="space-y-3">
                    {anal.fraudMonitoring.potentialSpamBuyers.slice(0, 5).map((buyer, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{buyer.buyer?.name || 'Unknown Buyer'}</p>
                          <p className="text-xs text-gray-500">{buyer.date}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold" style={{ color: colors.warning }}>{buyer.inquiryCount}</p>
                          <p className="text-xs text-gray-400">inquiries/day</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <CheckCircle className="h-8 w-8 mx-auto mb-2" style={{ color: colors.success }} />
                    <p className="text-sm text-gray-500">No suspicious activity detected</p>
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-4">
                  Buyers sending &gt;10 inquiries in a single day. May indicate spam or misuse.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ============== Section 6: Auto-Generated Insights ============== */}
        {kpi?.insights && kpi.insights.length > 0 && (
          <section data-testid="insights-section">
            <SectionHeader 
              icon={Zap} 
              title="Monetization Insights Summary" 
              description="Auto-generated insights based on platform performance."
            />
            
            <div className="space-y-4">
              {kpi.insights.map((insight, idx) => (
                <InsightBadge key={idx} type={insight.type} message={insight.message} />
              ))}
            </div>
          </section>
        )}

        {/* ============== Section 7: Data Source Transparency ============== */}
        <section data-testid="data-integrity-section">
          <div className="bg-white rounded-xl p-6 border border-gray-100">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-gray-100">
                <Database className="h-5 w-5 text-gray-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Data Integrity Notice</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">All metrics are calculated from:</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {['Seller Collection', 'Subscription Records', 'Inquiry Logs', 'Payment Confirmations'].map((source, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm text-gray-500">
                  <CheckCircle className="h-4 w-4" style={{ color: colors.success }} />
                  {source}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-4">
              Data updates in real-time. Last generated: {kpi?.generatedAt ? new Date(kpi.generatedAt).toLocaleString() : 'N/A'}
            </p>
          </div>
        </section>

        {/* Footer */}
        <div className="text-center py-6 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            These insights help administrators make informed decisions about pricing, feature limits, and growth strategy.
          </p>
        </div>
      </main>
    </div>
  );
}
