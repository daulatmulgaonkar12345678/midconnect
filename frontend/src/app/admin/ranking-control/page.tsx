'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  Save,
  RotateCcw,
  Settings,
  CheckCircle,
  Info
} from 'lucide-react';

interface RankingConfig {
  stock: number;
  subscriptionTier: number;
  responseSpeed: number;
  acceptanceRate: number;
  specMatch: number;
  behaviorBoost: number;
  gstVerified: number;
}

const DEFAULT_CONFIG: RankingConfig = {
  stock: 20,
  subscriptionTier: 25,
  responseSpeed: 15,
  acceptanceRate: 15,
  specMatch: 15,
  behaviorBoost: 5,
  gstVerified: 5
};

const CONFIG_DESCRIPTIONS: Record<keyof RankingConfig, string> = {
  stock: 'Weight for in-stock availability. Higher value prioritizes sellers with available stock.',
  subscriptionTier: 'Weight for subscription level (Free, Trial, Pro, Enterprise). Paid tiers get higher scores.',
  responseSpeed: 'Weight for how quickly sellers respond to inquiries. Faster response = higher score.',
  acceptanceRate: 'Weight for quote acceptance rate. Higher acceptance = better quality quotes.',
  specMatch: 'Weight for how well seller listings match product specifications.',
  behaviorBoost: 'Capped boost based on buyer-seller interactions (views, inquiries, orders).',
  gstVerified: 'Bonus weight for GST-verified sellers. Builds trust in the marketplace.'
};

export default function RankingControlPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const [config, setConfig] = useState<RankingConfig>(DEFAULT_CONFIG);
  const [originalConfig, setOriginalConfig] = useState<RankingConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const token = await getIdToken();
        if (!token) {
          router.push('/login');
          return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
        const res = await fetch(`${API_URL}/api/products/ranking/config`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Failed to fetch ranking config');

        const data = await res.json();
        if (data.weights) {
          setConfig(data.weights);
          setOriginalConfig(data.weights);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load config');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        fetchConfig();
      }
    }
  }, [user, authLoading]);

  useEffect(() => {
    const changed = Object.keys(config).some(
      key => config[key as keyof RankingConfig] !== originalConfig[key as keyof RankingConfig]
    );
    setHasChanges(changed);
  }, [config, originalConfig]);

  const handleSliderChange = (key: keyof RankingConfig, value: number) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setError(null);
    setSuccess(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${API_URL}/api/products/ranking/config`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ weights: config })
      });

      if (!res.ok) throw new Error('Failed to save config');

      const data = await res.json();
      setOriginalConfig(config);
      setSuccess('Ranking configuration saved successfully. Changes are now active.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setConfig(DEFAULT_CONFIG);
    setError(null);
    setSuccess(null);
  };

  const handleRevert = () => {
    setConfig(originalConfig);
    setError(null);
    setSuccess(null);
  };

  const totalWeight = Object.values(config).reduce((sum, val) => sum + val, 0);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/admin/analytics" className="p-2 hover:bg-slate-700 rounded-lg">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-500" />
                Ranking Weight Control
              </h1>
              <p className="text-sm text-slate-400">Configure how sellers are ranked in search results</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Alerts */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-lg flex items-center gap-3 text-green-400">
            <CheckCircle className="h-5 w-5 flex-shrink-0" />
            {success}
          </div>
        )}

        {/* Info Box */}
        <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg" data-testid="info-box">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-slate-300">
              <p className="font-medium text-blue-400 mb-1">How Ranking Works</p>
              <p>Each weight determines how much that factor influences seller ranking. Higher weights mean more impact on the final score. The total weight should ideally be 100 for easier interpretation.</p>
            </div>
          </div>
        </div>

        {/* Total Weight Indicator */}
        <div className="mb-6 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Total Weight</span>
            <span className={`text-2xl font-bold ${totalWeight === 100 ? 'text-green-400' : totalWeight > 100 ? 'text-orange-400' : 'text-blue-400'}`}>
              {totalWeight}
            </span>
          </div>
          <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${totalWeight === 100 ? 'bg-green-500' : totalWeight > 100 ? 'bg-orange-500' : 'bg-blue-500'}`}
              style={{ width: `${Math.min(totalWeight, 100)}%` }}
            />
          </div>
        </div>

        {/* Weight Sliders */}
        <div className="space-y-6" data-testid="weight-sliders">
          {(Object.keys(config) as (keyof RankingConfig)[]).map((key) => (
            <div key={key} className="bg-slate-800 rounded-lg p-5 border border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <label className="font-medium capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</label>
                <span className="text-xl font-bold text-blue-400">{config[key]}</span>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                value={config[key]}
                onChange={(e) => handleSliderChange(key, parseInt(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
                data-testid={`slider-${key}`}
              />
              <p className="mt-2 text-sm text-slate-400">{CONFIG_DESCRIPTIONS[key]}</p>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex items-center gap-4">
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium"
            data-testid="save-btn"
          >
            {saving ? <Loader2 className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
            Save Changes
          </button>
          
          <button
            onClick={handleRevert}
            disabled={!hasChanges}
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium"
            data-testid="revert-btn"
          >
            Revert
          </button>
          
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-6 py-3 border border-slate-600 hover:bg-slate-800 rounded-lg font-medium"
            data-testid="reset-btn"
          >
            <RotateCcw className="h-4 w-4" />
            Reset to Default
          </button>
        </div>

        {/* Change Indicator */}
        {hasChanges && (
          <p className="mt-4 text-center text-sm text-yellow-400">
            You have unsaved changes
          </p>
        )}
      </main>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 20px;
          height: 20px;
          background: #3b82f6;
          border-radius: 50%;
          cursor: pointer;
        }
        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          background: #3b82f6;
          border-radius: 50%;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}
