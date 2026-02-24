'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  AlertTriangle,
  Clock,
  XCircle,
  Shield,
  RefreshCw,
  Eye,
  UserX,
  Activity
} from 'lucide-react';

interface MarketHealth {
  quotes: {
    total: number;
    acceptanceRate: number;
    expiryRate: number;
    rejectionRate: number;
  };
  sellers: {
    active: number;
    warned: number;
    suspended: number;
    banned: number;
  };
  response: {
    avgResponseHours: number;
    maxResponseHours: number;
  };
  healthScore: number;
}

interface SellerAlert {
  sellerId: string;
  email?: string;
  businessName?: string;
  status?: string;
  warningCount?: number;
  expiryRate?: number;
  avgResponseHours?: number;
  totalQuotes?: number;
}

interface AbuseSummary {
  thresholds: {
    high_expiry_rate: number;
    slow_response_hours: number;
    min_quotes_for_analysis: number;
  };
  alerts: {
    highExpiry: { count: number; sellers: SellerAlert[] };
    slowResponders: { count: number; sellers: SellerAlert[] };
    zeroConversion: { count: number; sellers: SellerAlert[] };
    suspicious: { count: number; patterns: any[] };
  };
  totalAlerts: number;
}

export default function MarketMonitorPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const [health, setHealth] = useState<MarketHealth | null>(null);
  const [abuse, setAbuse] = useState<AbuseSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'expiry' | 'slow' | 'zero'>('overview');

  const fetchData = async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      
      const [healthRes, abuseRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/governance/market-health`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/admin/governance/abuse-summary`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (!healthRes.ok || !abuseRes.ok) {
        throw new Error('Failed to fetch market data');
      }

      const [healthData, abuseData] = await Promise.all([
        healthRes.json(),
        abuseRes.json()
      ]);

      setHealth(healthData);
      setAbuse(abuseData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
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

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    if (score >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getHealthBg = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/admin/analytics" className="p-2 hover:bg-slate-700 rounded-lg">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold flex items-center gap-2">
                  <Shield className="h-5 w-5 text-orange-500" />
                  Market Monitor
                </h1>
                <p className="text-sm text-slate-400">Abuse detection & governance</p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Health Score */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="md:col-span-1 bg-slate-800 rounded-xl p-6 border border-slate-700" data-testid="health-score">
            <h3 className="text-sm text-slate-400 mb-3">Marketplace Health</h3>
            <div className={`text-5xl font-bold ${getHealthColor(health?.healthScore || 0)}`}>
              {health?.healthScore || 0}
            </div>
            <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${getHealthBg(health?.healthScore || 0)} transition-all`}
                style={{ width: `${health?.healthScore || 0}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {(health?.healthScore || 0) >= 80 ? 'Healthy' : 
               (health?.healthScore || 0) >= 60 ? 'Moderate' : 
               (health?.healthScore || 0) >= 40 ? 'Needs Attention' : 'Critical'}
            </p>
          </div>

          <div className="md:col-span-3 grid grid-cols-3 gap-4">
            <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <h4 className="text-sm text-slate-400 mb-1">Acceptance Rate</h4>
              <p className="text-2xl font-bold text-green-400">{health?.quotes.acceptanceRate || 0}%</p>
            </div>
            <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <h4 className="text-sm text-slate-400 mb-1">Expiry Rate</h4>
              <p className="text-2xl font-bold text-yellow-400">{health?.quotes.expiryRate || 0}%</p>
            </div>
            <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
              <h4 className="text-sm text-slate-400 mb-1">Avg Response</h4>
              <p className="text-2xl font-bold text-blue-400">{health?.response.avgResponseHours.toFixed(1) || 0}h</p>
            </div>
          </div>
        </div>

        {/* Alert Summary */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <AlertCard
            label="High Expiry"
            count={abuse?.alerts.highExpiry.count || 0}
            icon={<AlertTriangle className="h-5 w-5" />}
            color="yellow"
            onClick={() => setActiveTab('expiry')}
            active={activeTab === 'expiry'}
          />
          <AlertCard
            label="Slow Responders"
            count={abuse?.alerts.slowResponders.count || 0}
            icon={<Clock className="h-5 w-5" />}
            color="orange"
            onClick={() => setActiveTab('slow')}
            active={activeTab === 'slow'}
          />
          <AlertCard
            label="Zero Conversion"
            count={abuse?.alerts.zeroConversion.count || 0}
            icon={<XCircle className="h-5 w-5" />}
            color="red"
            onClick={() => setActiveTab('zero')}
            active={activeTab === 'zero'}
          />
          <AlertCard
            label="Suspicious"
            count={abuse?.alerts.suspicious.count || 0}
            icon={<Eye className="h-5 w-5" />}
            color="purple"
            onClick={() => setActiveTab('overview')}
            active={activeTab === 'overview'}
          />
        </div>

        {/* Seller Status */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Activity className="h-5 w-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{health?.sellers.active || 0}</p>
              <p className="text-sm text-slate-400">Active</p>
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{health?.sellers.warned || 0}</p>
              <p className="text-sm text-slate-400">Warned</p>
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center gap-3">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <UserX className="h-5 w-5 text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{health?.sellers.suspended || 0}</p>
              <p className="text-sm text-slate-400">Suspended</p>
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <XCircle className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{health?.sellers.banned || 0}</p>
              <p className="text-sm text-slate-400">Banned</p>
            </div>
          </div>
        </div>

        {/* Alert Details */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden" data-testid="alert-details">
          <div className="px-6 py-4 border-b border-slate-700">
            <h3 className="font-semibold">
              {activeTab === 'overview' && 'Suspicious Activity'}
              {activeTab === 'expiry' && `High Expiry Sellers (>${abuse?.thresholds.high_expiry_rate}%)`}
              {activeTab === 'slow' && `Slow Responders (>${abuse?.thresholds.slow_response_hours}h)`}
              {activeTab === 'zero' && 'Zero Conversion Sellers'}
            </h3>
          </div>
          
          <div className="p-6">
            {activeTab === 'overview' && (
              <SuspiciousPatterns patterns={abuse?.alerts.suspicious.patterns || []} />
            )}
            {activeTab === 'expiry' && (
              <SellerTable sellers={abuse?.alerts.highExpiry.sellers || []} type="expiry" />
            )}
            {activeTab === 'slow' && (
              <SellerTable sellers={abuse?.alerts.slowResponders.sellers || []} type="slow" />
            )}
            {activeTab === 'zero' && (
              <SellerTable sellers={abuse?.alerts.zeroConversion.sellers || []} type="zero" />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function AlertCard({ label, count, icon, color, onClick, active }: {
  label: string;
  count: number;
  icon: React.ReactNode;
  color: string;
  onClick: () => void;
  active: boolean;
}) {
  const colorClasses: Record<string, string> = {
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
    red: 'bg-red-500/20 text-red-400 border-red-500/50',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/50'
  };

  return (
    <button
      onClick={onClick}
      className={`bg-slate-800 rounded-xl p-5 border text-left transition ${
        active ? colorClasses[color] : 'border-slate-700 hover:border-slate-600'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color].split(' ').slice(0, 2).join(' ')}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold">{count}</p>
          <p className="text-sm text-slate-400">{label}</p>
        </div>
      </div>
    </button>
  );
}

function SellerTable({ sellers, type }: { sellers: SellerAlert[]; type: string }) {
  if (sellers.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <p>No sellers flagged in this category</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-700">
            <th className="pb-3 font-medium">Seller</th>
            <th className="pb-3 font-medium">Status</th>
            <th className="pb-3 font-medium">
              {type === 'expiry' && 'Expiry Rate'}
              {type === 'slow' && 'Avg Response'}
              {type === 'zero' && 'Total Quotes'}
            </th>
            <th className="pb-3 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {sellers.map((seller) => (
            <tr key={seller.sellerId} className="border-b border-slate-700/50">
              <td className="py-3">
                <p className="font-medium">{seller.businessName || 'Unknown'}</p>
                <p className="text-xs text-slate-500">{seller.email}</p>
              </td>
              <td className="py-3">
                <span className={`px-2 py-1 rounded text-xs ${
                  seller.status === 'active' ? 'bg-green-500/20 text-green-400' :
                  seller.status === 'warned' ? 'bg-yellow-500/20 text-yellow-400' :
                  seller.status === 'suspended' ? 'bg-red-500/20 text-red-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                  {seller.status || 'active'}
                </span>
              </td>
              <td className="py-3 font-mono">
                {type === 'expiry' && `${seller.expiryRate?.toFixed(1)}%`}
                {type === 'slow' && `${seller.avgResponseHours?.toFixed(1)}h`}
                {type === 'zero' && seller.totalQuotes}
              </td>
              <td className="py-3">
                <Link
                  href={`/admin/seller/${seller.sellerId}`}
                  className="text-blue-400 hover:underline text-sm"
                >
                  Review
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SuspiciousPatterns({ patterns }: { patterns: any[] }) {
  if (patterns.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <p>No suspicious patterns detected</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {patterns.map((p, i) => (
        <div key={i} className={`p-4 rounded-lg border ${
          p.severity === 'HIGH' ? 'bg-red-500/10 border-red-500/30' :
          p.severity === 'MEDIUM' ? 'bg-yellow-500/10 border-yellow-500/30' :
          'bg-slate-700 border-slate-600'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">{p.pattern.replace(/_/g, ' ')}</span>
            <span className={`px-2 py-0.5 rounded text-xs ${
              p.severity === 'HIGH' ? 'bg-red-500/20 text-red-400' :
              p.severity === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-slate-500/20 text-slate-400'
            }`}>
              {p.severity}
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Seller: {p.sellerId?.slice(-8)}
            {p.details && ` • ${JSON.stringify(p.details)}`}
          </p>
        </div>
      ))}
    </div>
  );
}
