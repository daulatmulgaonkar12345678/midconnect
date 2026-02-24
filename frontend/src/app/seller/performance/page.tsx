'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertTriangle,
  Target,
  Zap,
  Award,
  ChevronRight,
  Info
} from 'lucide-react';

interface PerformanceData {
  sellerId: string;
  score: number;
  maxScore: number;
  tier: string;
  tierColor: string;
  metrics: {
    totalInquiries: number;
    acceptedInquiries: number;
    avgResponseTimeHours: number;
    totalQuotes: number;
    acceptedQuotes: number;
    expiredQuotes: number;
    acceptanceRate: number;
    expiryRate: number;
    quoteCompletionRate: number;
    subscriptionPlan: string;
    leadUtilization: number;
  };
  breakdown: {
    [key: string]: {
      score: number;
      maxScore: number;
      metric: string;
    };
  };
  marketplaceAverage: {
    avgResponseTimeHours: number;
    avgAcceptanceRate: number;
    avgExpiryRate: number;
  };
  suggestions: {
    category: string;
    priority: string;
    message: string;
    impact: string;
  }[];
}

interface LeadStats {
  leadStats: {
    plan: string;
    monthlyUsed: number;
    monthlyLimit: number;
    remaining: number;
    daysUntilReset: number;
  };
  canAcceptNewLead: boolean;
  limitMessage?: string;
}

export default function SellerPerformancePage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [leadStats, setLeadStats] = useState<LeadStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = await getIdToken();
        if (!token) {
          router.push('/login');
          return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
        
        const [perfRes, leadRes] = await Promise.all([
          fetch(`${API_URL}/api/seller/performance`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(`${API_URL}/api/seller/performance/lead-stats`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);

        if (!perfRes.ok) throw new Error('Failed to fetch performance data');

        const perfData = await perfRes.json();
        setPerformance(perfData);

        if (leadRes.ok) {
          const leadData = await leadRes.json();
          setLeadStats(leadData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        fetchData();
      }
    }
  }, [user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm p-8 max-w-md text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Performance</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link href="/seller" className="text-blue-600 hover:underline">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-600';
    if (score >= 70) return 'text-blue-600';
    if (score >= 50) return 'text-amber-600';
    if (score >= 30) return 'text-orange-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 90) return 'bg-emerald-500';
    if (score >= 70) return 'bg-blue-500';
    if (score >= 50) return 'bg-amber-500';
    if (score >= 30) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller" className="p-2 hover:bg-gray-100 rounded-lg">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-blue-600" />
                My Performance
              </h1>
              <p className="text-sm text-gray-500">Track your seller metrics & improve your ranking</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Score Card */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6" data-testid="score-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-gray-500">Performance Score</p>
              <p className={`text-5xl font-bold ${getScoreColor(performance?.score || 0)}`}>
                {performance?.score.toFixed(0)}
              </p>
            </div>
            <div 
              className="px-4 py-2 rounded-full text-white font-medium"
              style={{ backgroundColor: performance?.tierColor || '#6b7280' }}
            >
              <Award className="h-4 w-4 inline mr-1" />
              {performance?.tier}
            </div>
          </div>
          
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${getScoreBg(performance?.score || 0)} transition-all duration-500`}
              style={{ width: `${performance?.score || 0}%` }}
            />
          </div>
          
          <p className="mt-2 text-sm text-gray-500">
            {performance?.score! >= 90 ? 'Excellent! You\'re among the top performers.' :
             performance?.score! >= 70 ? 'Great work! Keep improving to reach Elite status.' :
             performance?.score! >= 50 ? 'Good progress. Focus on the suggestions below.' :
             'Room for improvement. Follow the suggestions to boost your score.'}
          </p>
        </div>

        {/* Lead Stats */}
        {leadStats && (
          <div className="bg-white rounded-xl shadow-sm p-5 mb-6" data-testid="lead-stats">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Leads Used This Month</p>
                <p className="text-2xl font-bold text-gray-900">
                  {leadStats.leadStats.monthlyUsed}
                  {leadStats.leadStats.monthlyLimit > 0 && (
                    <span className="text-gray-400 font-normal"> / {leadStats.leadStats.monthlyLimit}</span>
                  )}
                </p>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  leadStats.leadStats.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
                  leadStats.leadStats.plan === 'pro' ? 'bg-blue-100 text-blue-700' :
                  leadStats.leadStats.plan === 'trial' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {leadStats.leadStats.plan.charAt(0).toUpperCase() + leadStats.leadStats.plan.slice(1)} Plan
                </span>
                <p className="text-sm text-gray-500 mt-1">
                  Resets in {leadStats.leadStats.daysUntilReset} days
                </p>
              </div>
            </div>
            
            {leadStats.leadStats.monthlyLimit > 0 && (
              <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all"
                  style={{ width: `${(leadStats.leadStats.monthlyUsed / leadStats.leadStats.monthlyLimit) * 100}%` }}
                />
              </div>
            )}
            
            {!leadStats.canAcceptNewLead && (
              <div className="mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                <p className="text-sm text-orange-700">{leadStats.limitMessage}</p>
                <Link href="/seller/subscription" className="text-sm text-orange-600 font-medium hover:underline">
                  Upgrade Now →
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Score Breakdown */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="score-breakdown">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-600" />
            Score Breakdown
          </h3>
          
          <div className="space-y-4">
            {performance?.breakdown && Object.entries(performance.breakdown).map(([key, data]) => (
              <div key={key}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-700 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                  <span className="font-medium">
                    {data.score.toFixed(1)} / {data.maxScore}
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${(data.score / data.maxScore) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{data.metric}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Marketplace Comparison */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6" data-testid="marketplace-comparison">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Info className="h-5 w-5 text-blue-600" />
            vs Marketplace Average
          </h3>
          
          <div className="grid grid-cols-3 gap-4">
            <ComparisonMetric
              label="Response Time"
              yours={performance?.metrics.avgResponseTimeHours || 0}
              avg={performance?.marketplaceAverage.avgResponseTimeHours || 0}
              unit="h"
              lowerIsBetter
            />
            <ComparisonMetric
              label="Acceptance Rate"
              yours={performance?.metrics.acceptanceRate || 0}
              avg={performance?.marketplaceAverage.avgAcceptanceRate || 0}
              unit="%"
            />
            <ComparisonMetric
              label="Expiry Rate"
              yours={performance?.metrics.expiryRate || 0}
              avg={performance?.marketplaceAverage.avgExpiryRate || 0}
              unit="%"
              lowerIsBetter
            />
          </div>
        </div>

        {/* Improvement Suggestions */}
        {performance?.suggestions && performance.suggestions.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6" data-testid="suggestions">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-500" />
              Improvement Suggestions
            </h3>
            
            <div className="space-y-4">
              {performance.suggestions.map((suggestion, i) => (
                <div
                  key={i}
                  className={`p-4 rounded-lg border ${
                    suggestion.priority === 'HIGH' ? 'bg-red-50 border-red-200' :
                    suggestion.priority === 'MEDIUM' ? 'bg-yellow-50 border-yellow-200' :
                    'bg-blue-50 border-blue-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-1.5 rounded ${
                      suggestion.priority === 'HIGH' ? 'bg-red-100' :
                      suggestion.priority === 'MEDIUM' ? 'bg-yellow-100' :
                      'bg-blue-100'
                    }`}>
                      {suggestion.priority === 'HIGH' ? (
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                      ) : suggestion.priority === 'MEDIUM' ? (
                        <Clock className="h-4 w-4 text-yellow-600" />
                      ) : (
                        <Info className="h-4 w-4 text-blue-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">{suggestion.category}</p>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          suggestion.priority === 'HIGH' ? 'bg-red-100 text-red-700' :
                          suggestion.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {suggestion.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{suggestion.message}</p>
                      <p className="text-xs text-gray-500 mt-2">Impact: {suggestion.impact}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function ComparisonMetric({ label, yours, avg, unit, lowerIsBetter = false }: {
  label: string;
  yours: number;
  avg: number;
  unit: string;
  lowerIsBetter?: boolean;
}) {
  const isBetter = lowerIsBetter ? yours < avg : yours > avg;
  
  return (
    <div className="text-center p-3 bg-gray-50 rounded-lg">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${isBetter ? 'text-green-600' : 'text-gray-900'}`}>
        {yours.toFixed(1)}{unit}
      </p>
      <p className="text-xs text-gray-400">
        Avg: {avg.toFixed(1)}{unit}
      </p>
      {isBetter && (
        <span className="inline-flex items-center text-xs text-green-600 mt-1">
          <CheckCircle className="h-3 w-3 mr-1" />
          Better
        </span>
      )}
    </div>
  );
}
