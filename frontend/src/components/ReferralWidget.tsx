'use client';

import { useState, useEffect } from 'react';
import { Gift, Users, ChevronRight, Trophy, Copy, Check, Share2, IndianRupee } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function ReferralWidget({ token, onOpenModal }: { token: string | null; onOpenModal: () => void }) {
  const [stats, setStats] = useState<{ successfulReferrals: number; referralsToNextTier: number; nextTier: { label: string; min_referrals: number } | null; currentTier: { label: string } | null } | null>(null);
  const [earnings, setEarnings] = useState(0);
  const [link, setLink] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;
    const h = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
    Promise.all([
      fetch(`${API_URL}/api/referral/stats`, { headers: h }).then(r => r.ok ? r.json() : null),
      fetch(`${API_URL}/api/referral/my-link`, { headers: h }).then(r => r.ok ? r.json() : null),
      fetch(`${API_URL}/api/referral/sales-stats`, { headers: h }).then(r => r.ok ? r.json() : null),
    ]).then(([s, l, sales]) => {
      if (s) setStats(s);
      if (l) setLink(l.referralLink);
      if (sales) setEarnings(sales.totalEarnings || 0);
    }).catch(() => {});
  }, [token]);

  const copyLink = () => {
    if (!link) return;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const shareWhatsApp = () => {
    if (!link) return;
    const message = `Join UdyogConnect - India's Industrial B2B Marketplace & grow your business!\n\nSign up here: ${link}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank');
  };

  const successful = stats?.successfulReferrals || 0;
  const nextTier = stats?.nextTier;
  const progressMax = nextTier ? nextTier.min_referrals : 10;
  const progressPct = Math.min((successful / progressMax) * 100, 100);

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-xl p-5" data-testid="referral-widget">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-indigo-100 rounded-lg flex items-center justify-center">
            <Gift className="w-4.5 h-4.5 text-indigo-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900">Refer & Earn</h3>
            <p className="text-xs text-gray-500">Earn up to 6 months free</p>
          </div>
        </div>
        <button onClick={onOpenModal} className="text-indigo-600 hover:text-indigo-700 flex items-center gap-0.5 text-xs font-medium" data-testid="referral-widget-details-btn">
          Details <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 mb-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-indigo-500" />
          <span className="text-sm font-semibold text-gray-800">{successful}</span>
          <span className="text-xs text-gray-500">referral{successful !== 1 ? 's' : ''}</span>
        </div>
        {earnings > 0 && (
          <div className="flex items-center gap-1" data-testid="referral-widget-earnings">
            <IndianRupee className="w-3 h-3 text-emerald-600" />
            <span className="text-sm font-semibold text-emerald-700">{earnings.toLocaleString('en-IN')}</span>
            <span className="text-xs text-emerald-500">earned</span>
          </div>
        )}
        {stats?.currentTier && (
          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
            <Trophy className="w-3 h-3" /> {stats.currentTier.label}
          </span>
        )}
      </div>

      {/* Progress */}
      <div className="w-full bg-white/60 rounded-full h-2 mb-1.5">
        <div className="bg-indigo-600 h-2 rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
      </div>
      {nextTier ? (
        <p className="text-xs text-gray-500 mb-3">
          {stats?.referralsToNextTier} more to unlock <span className="font-semibold text-indigo-600">{nextTier.label}</span>
        </p>
      ) : (
        <p className="text-xs text-green-600 font-medium mb-3">Maximum tier achieved!</p>
      )}

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button onClick={copyLink} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors ${copied ? 'bg-green-100 text-green-700' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'}`} data-testid="referral-widget-copy-btn">
          {copied ? <><Check className="w-3.5 h-3.5" /> Copied</> : <><Copy className="w-3.5 h-3.5" /> Copy Link</>}
        </button>
        <button onClick={shareWhatsApp} className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium bg-green-600 text-white hover:bg-green-700 transition-colors" data-testid="referral-widget-whatsapp-btn">
          <Share2 className="w-3.5 h-3.5" /> WhatsApp
        </button>
      </div>
    </div>
  );
}
