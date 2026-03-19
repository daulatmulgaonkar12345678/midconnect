'use client';

import { useState, useEffect, useCallback } from 'react';
import { Gift, Copy, Check, X, Share2, Users, Trophy, ChevronRight, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface ReferralTier {
  min_referrals: number;
  reward_days: number;
  label: string;
}

interface ReferralStats {
  referralCode: string;
  totalReferred: number;
  successfulReferrals: number;
  pendingReferrals: number;
  currentTier: ReferralTier | null;
  nextTier: ReferralTier | null;
  referralsToNextTier: number;
  referredUsers: Array<{
    name: string;
    joinedAt: string;
    status: 'pending' | 'partial' | 'completed';
    activated: boolean;
    rewarded: boolean;
    progress: {
      products: number;
      productsRequired: number;
      invoices: number;
      invoicesRequired: number;
      buyerSupplier: boolean;
    };
  }>;
  rewardTier: string | null;
  tiers: ReferralTier[];
}

export default function ReferralModal({ isOpen, onClose, token }: { isOpen: boolean; onClose: () => void; token: string | null }) {
  const [link, setLink] = useState('');
  const [code, setCode] = useState('');
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const h = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
      const [linkRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/referral/my-link`, { headers: h }),
        fetch(`${API_URL}/api/referral/stats`, { headers: h }),
      ]);
      if (linkRes.ok) {
        const d = await linkRes.json();
        setLink(d.referralLink);
        setCode(d.referralCode);
      }
      if (statsRes.ok) setStats(await statsRes.json());
    } catch { /* empty */ }
    setLoading(false);
  }, [token]);

  useEffect(() => {
    if (isOpen) fetchData();
  }, [isOpen, fetchData]);

  const copyLink = () => {
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const shareWhatsApp = () => {
    const message = `Join UdyogConnect - India's Industrial B2B Marketplace & grow your business!\n\nSign up here: ${link}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank');
    setShared(true);
    setTimeout(() => setShared(false), 3000);
  };

  if (!isOpen) return null;

  const successful = stats?.successfulReferrals || 0;
  const nextTier = stats?.nextTier;
  const progressMax = nextTier ? nextTier.min_referrals : 10;
  const progressPct = Math.min((successful / progressMax) * 100, 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" data-testid="referral-modal-overlay" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="referral-modal">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-6 py-5 text-white relative">
          <button onClick={onClose} className="absolute top-4 right-4 text-white/70 hover:text-white" data-testid="referral-modal-close">
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Gift className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Refer & Earn</h2>
              <p className="text-sm text-white/80">Earn up to 6 months free with referrals</p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
          </div>
        ) : (
          <div className="p-6 space-y-5">
            {/* Referral Link */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">Your Referral Link</label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 font-mono truncate" data-testid="referral-link-display">
                  {link}
                </div>
                <button onClick={copyLink} className={`px-3 py-2.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${copied ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`} data-testid="copy-referral-link-btn">
                  {copied ? <><Check className="w-4 h-4" /> Copied</> : <><Copy className="w-4 h-4" /> Copy</>}
                </button>
              </div>
            </div>

            {/* Share Buttons */}
            <div className="flex gap-3">
              <button onClick={shareWhatsApp} className="flex-1 bg-green-600 text-white rounded-lg py-2.5 text-sm font-medium flex items-center justify-center gap-2 hover:bg-green-700 transition-colors" data-testid="share-whatsapp-btn">
                <Share2 className="w-4 h-4" />
                {shared ? 'Shared!' : 'Share via WhatsApp'}
              </button>
            </div>

            {shared && (
              <p className="text-center text-sm text-indigo-600 font-medium animate-pulse">Share with friends & unlock free months</p>
            )}

            {/* Progress */}
            <div className="bg-gray-50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-indigo-600" />
                  <span className="text-sm font-medium text-gray-800">Your Referrals: {successful}</span>
                </div>
                {stats?.currentTier && (
                  <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                    {stats.currentTier.label}
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} data-testid="referral-progress-bar" />
              </div>

              {nextTier ? (
                <p className="text-xs text-gray-500">
                  {stats?.referralsToNextTier} more referral{(stats?.referralsToNextTier || 0) > 1 ? 's' : ''} to unlock <span className="font-semibold text-indigo-600">{nextTier.label}</span>
                </p>
              ) : (
                <p className="text-xs text-green-600 font-medium flex items-center gap-1">
                  <Trophy className="w-3 h-3" /> Maximum reward tier achieved!
                </p>
              )}
            </div>

            {/* Tier Table */}
            <div>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Reward Tiers</h3>
              <div className="space-y-1.5">
                {(stats?.tiers || []).map((tier, i) => {
                  const achieved = successful >= tier.min_referrals;
                  return (
                    <div key={i} className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm ${achieved ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-100'}`}>
                      <span className={achieved ? 'text-green-700 font-medium' : 'text-gray-600'}>
                        {achieved && <Check className="w-3.5 h-3.5 inline mr-1" />}
                        {tier.min_referrals} referral{tier.min_referrals > 1 ? 's' : ''}
                      </span>
                      <span className={`font-medium ${achieved ? 'text-green-700' : 'text-gray-800'}`}>{tier.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Referred Users List */}
            {(stats?.referredUsers || []).length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Your Referrals</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {stats?.referredUsers.map((u, i) => (
                    <div key={i} className="px-3 py-2.5 bg-gray-50 rounded-lg" data-testid={`referral-user-${i}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-800">{u.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          u.status === 'completed' ? 'bg-green-100 text-green-700' :
                          u.status === 'partial' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-200 text-gray-600'
                        }`}>
                          {u.status === 'completed' ? 'Completed' : u.status === 'partial' ? 'In Progress' : 'Pending'}
                        </span>
                      </div>
                      {u.status !== 'completed' && u.progress && (
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
                          <span className={u.progress.products >= u.progress.productsRequired ? 'text-green-600' : ''}>
                            {u.progress.products}/{u.progress.productsRequired} products
                          </span>
                          <span className={u.progress.invoices >= u.progress.invoicesRequired ? 'text-green-600' : ''}>
                            {u.progress.invoices}/{u.progress.invoicesRequired} invoices
                          </span>
                          <span className={u.progress.buyerSupplier ? 'text-green-600' : ''}>
                            {u.progress.buyerSupplier ? 'Buyer+Supplier' : 'No buyer/supplier'}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
