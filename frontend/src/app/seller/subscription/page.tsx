'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getSellerSubscriptionStatus, SellerSubscriptionStatus } from '@/lib/api';
import { 
  Crown, 
  Check, 
  X,
  ArrowLeft, 
  Loader2,
  Calendar,
  MessageCircle,
  Shield,
  BadgeCheck,
  Zap,
  AlertCircle,
  TrendingUp,
  Clock,
  Star,
  Lock,
  Unlock,
  HelpCircle,
  ChevronRight,
  Sparkles,
  Bell
} from 'lucide-react';

// Brand Colors (B2B SaaS Professional Palette)
const colors = {
  primary: '#1E3A8A',      // Deep Royal Blue - trust, authority
  accent: {
    from: '#2563EB',       // Gradient start
    to: '#7C3AED',         // Gradient end (violet)
  },
  success: '#16A34A',      // Green
  warning: '#F59E0B',      // Orange/Amber
  danger: '#DC2626',       // Red
  background: '#F8FAFC',   // Very light grey
};

// Expiry Warning Popup Component
function ExpiryWarningPopup({ 
  daysRemaining, 
  onClose 
}: { 
  daysRemaining: number; 
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in duration-200">
        <div 
          className="p-6 text-center"
          style={{ background: `linear-gradient(135deg, ${colors.warning} 0%, ${colors.danger} 100%)` }}
        >
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Bell className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white">Subscription Expiring Soon</h2>
        </div>
        
        <div className="p-6">
          <div className="text-center mb-6">
            <p className="text-5xl font-bold" style={{ color: colors.danger }}>{daysRemaining}</p>
            <p className="text-gray-500">days remaining</p>
          </div>
          
          <p className="text-gray-600 text-center mb-6">
            Your subscription will expire in <strong>{daysRemaining} days</strong>. 
            Please renew to continue receiving buyer inquiries and accessing premium features.
          </p>
          
          <div className="space-y-3">
            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl font-semibold text-white transition-all duration-200 hover:scale-[1.02]"
              style={{ background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)` }}
            >
              Renew Now
            </button>
            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl font-medium text-gray-500 hover:bg-gray-100 transition"
            >
              Remind Me Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SellerSubscriptionPage() {
  const router = useRouter();
  const { getIdToken, isAuthenticated, loading: authLoading } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscription, setSubscription] = useState<SellerSubscriptionStatus | null>(null);
  const [showExpiryPopup, setShowExpiryPopup] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login?redirect=/seller/subscription');
      return;
    }

    async function loadSubscription() {
      try {
        const token = await getIdToken();
        if (!token) throw new Error('Not authenticated');
        
        const data = await getSellerSubscriptionStatus(token);
        setSubscription(data);
        
        // Check if we should show expiry popup (once per session)
        const popupShown = sessionStorage.getItem('expiry_popup_shown');
        if (data.showExpiryWarning && !popupShown) {
          setShowExpiryPopup(true);
          sessionStorage.setItem('expiry_popup_shown', 'true');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load subscription');
      } finally {
        setLoading(false);
      }
    }

    loadSubscription();
  }, [isAuthenticated, authLoading, getIdToken, router]);

  if (loading || authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin mx-auto" style={{ color: colors.primary }} />
          <p className="mt-4 text-gray-600">Loading your subscription...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: '#FEE2E2' }}>
            <AlertCircle className="h-8 w-8" style={{ color: colors.danger }} />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Subscription</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link 
            href="/seller" 
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all duration-200 hover:scale-[1.02]"
            style={{ backgroundColor: colors.primary, color: 'white' }}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Plan status calculations (using new API structure)
  const plan = subscription?.subscription.planName ?? 'free';
  const subscriptionStatus = subscription?.subscription.status ?? 'active';
  const isActive = subscription?.subscription.isActive ?? false;
  const isPro = plan === 'pro' && isActive;
  const isTrial = plan === 'trial' && isActive;
  const isFree = plan === 'free' || !isActive;
  const isExpired = (subscriptionStatus as string) === 'expired';
  const isSuspended = (subscriptionStatus as string) === 'suspended';
  
  const usedCount = subscription?.usage.acceptedThisMonth || 0;
  const limitCount = subscription?.usage.monthlyLimit || 5;
  const remainingCount = subscription?.usage.remaining || 0;
  const usagePercent = limitCount > 0 ? Math.min(100, (usedCount / limitCount) * 100) : 0;
  
  // Color logic for progress bar
  const getUsageColor = () => {
    if (usagePercent >= 100) return colors.danger;
    if (usagePercent >= 60) return colors.warning;
    return colors.success;
  };

  const getUsageStatus = () => {
    if (usagePercent >= 100) return { label: 'Limit Reached', color: colors.danger, bg: '#FEE2E2' };
    if (usagePercent >= 80) return { label: 'Almost Full', color: colors.warning, bg: '#FEF3C7' };
    if (usagePercent >= 60) return { label: 'Getting Low', color: colors.warning, bg: '#FEF3C7' };
    return { label: 'Available', color: colors.success, bg: '#DCFCE7' };
  };

  const usageStatus = getUsageStatus();

  // Comparison table data
  const comparisonFeatures = [
    { feature: 'Monthly Buyer Inquiry Acceptances', free: '5', pro: 'Unlimited', highlight: true },
    { feature: 'Verified Seller Badge', free: false, pro: true },
    { feature: 'Priority in Search Results', free: false, pro: true },
    { feature: 'Analytics & Insights Dashboard', free: false, pro: true },
    { feature: 'Priority Customer Support', free: 'Standard', pro: '24/7 Priority' },
    { feature: 'Instant Inquiry Approval', free: false, pro: true },
  ];

  return (
    <div className="min-h-screen" style={{ backgroundColor: colors.background }}>
      {/* Expiry Warning Popup */}
      {showExpiryPopup && subscription?.subscription.daysRemaining !== undefined && (
        <ExpiryWarningPopup 
          daysRemaining={subscription.subscription.daysRemaining}
          onClose={() => setShowExpiryPopup(false)}
        />
      )}
      
      {/* Suspended/Expired Banner */}
      {isSuspended && (
        <div className="bg-red-600 text-white py-3 px-4">
          <div className="max-w-5xl mx-auto flex items-center gap-3">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Your subscription has been suspended. Please contact support.</span>
          </div>
        </div>
      )}
      {isExpired && (
        <div className="bg-orange-500 text-white py-3 px-4">
          <div className="max-w-5xl mx-auto flex items-center gap-3">
            <Clock className="h-5 w-5" />
            <span className="font-medium">Your subscription has expired. Renew now to continue receiving buyer inquiries.</span>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <Link 
            href="/seller" 
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors duration-200"
            data-testid="back-to-dashboard"
          >
            <ArrowLeft className="h-5 w-5" />
            Back to Dashboard
          </Link>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-8">
        
        {/* ============== ABOVE THE FOLD: Current Plan Status ============== */}
        <div 
          className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-8"
          data-testid="current-plan-section"
        >
          {/* Plan Header */}
          <div 
            className="p-6 md:p-8"
            style={{ 
              background: isPro 
                ? `linear-gradient(135deg, ${colors.primary} 0%, #3B82F6 100%)` 
                : isTrial 
                  ? `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)`
                  : 'linear-gradient(135deg, #475569 0%, #64748B 100%)'
            }}
          >
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="text-white">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-white/20">
                    <Crown className="h-6 w-6" />
                  </div>
                  <div>
                    <span className="text-2xl font-bold">
                      {plan.charAt(0).toUpperCase() + plan.slice(1)} Plan
                    </span>
                    {isTrial && (
                      <span className="ml-3 px-3 py-1 bg-white/20 text-white text-sm rounded-full">
                        90-Day Trial
                      </span>
                    )}
                    {isPro && (
                      <span className="ml-3 px-3 py-1 bg-white/20 text-white text-sm rounded-full flex items-center gap-1">
                        <BadgeCheck className="h-4 w-4" /> Active
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-white/90 text-sm md:text-base">
                  {isPro 
                    ? `Your premium benefits are active until ${new Date(subscription?.subscription.endDate || '').toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}`
                    : isTrial
                    ? `Enjoy unlimited access. Trial ends ${new Date(subscription?.subscription.endDate || '').toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}`
                    : 'Limited to 5 buyer inquiry acceptances per month'}
                </p>
              </div>
              
              {/* Days Remaining Badge */}
              {(isPro || isTrial) && subscription?.subscription.daysRemaining !== undefined && (
                <div className="bg-white/20 backdrop-blur-sm rounded-xl px-6 py-4 text-white text-center min-w-[120px]">
                  <p className="text-3xl font-bold">{subscription.subscription.daysRemaining}</p>
                  <p className="text-sm opacity-90">days remaining</p>
                </div>
              )}
            </div>
          </div>

          {/* ============== USAGE BLOCK (Critical for Free Users) ============== */}
          {isFree && (
            <div className="p-6 md:p-8 border-b border-gray-100" data-testid="usage-block">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <MessageCircle className="h-5 w-5" style={{ color: colors.primary }} />
                  <h3 className="text-lg font-semibold text-gray-900">Buyer Inquiry Acceptances</h3>
                  <div className="relative group">
                    <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                      Each time you accept a buyer inquiry and unlock their contact details, it counts against your monthly limit.
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                </div>
                <span 
                  className="px-3 py-1 rounded-full text-sm font-medium"
                  style={{ backgroundColor: usageStatus.bg, color: usageStatus.color }}
                >
                  {usageStatus.label}
                </span>
              </div>

              {/* Big Usage Display */}
              <div className="flex items-end gap-2 mb-4">
                <span className="text-5xl font-bold" style={{ color: colors.primary }}>{usedCount}</span>
                <span className="text-2xl text-gray-400 mb-1">/ {limitCount}</span>
                <span className="text-lg text-gray-500 mb-1 ml-1">used this month</span>
              </div>

              {/* Progress Bar with Animation */}
              <div className="w-full bg-gray-100 rounded-full h-4 mb-4 overflow-hidden">
                <div 
                  className="h-4 rounded-full transition-all duration-1000 ease-out"
                  style={{ 
                    width: `${usagePercent}%`,
                    backgroundColor: getUsageColor(),
                  }}
                />
              </div>

              {/* Status Row */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-sm">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1.5 text-gray-600">
                    <Unlock className="h-4 w-4" />
                    <strong style={{ color: remainingCount > 0 ? colors.success : colors.danger }}>
                      {remainingCount} remaining
                    </strong>
                  </span>
                  <span className="flex items-center gap-1.5 text-gray-600">
                    <Calendar className="h-4 w-4" />
                    Resets on {subscription?.usage.resetsOn}
                  </span>
                </div>
              </div>

              {/* Warning Message when limit reached */}
              {usagePercent >= 100 && (
                <div 
                  className="mt-4 p-4 rounded-lg border flex items-start gap-3"
                  style={{ backgroundColor: '#FEF2F2', borderColor: '#FECACA' }}
                >
                  <Lock className="h-5 w-5 flex-shrink-0 mt-0.5" style={{ color: colors.danger }} />
                  <div>
                    <p className="font-medium" style={{ color: colors.danger }}>Monthly limit reached</p>
                    <p className="text-sm text-gray-600 mt-1">
                      New buyer inquiries cannot be accepted until your limit resets. Upgrade to Pro for unlimited buyer inquiry acceptances.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Pro/Trial Users: Unlimited Badge */}
          {(isPro || isTrial) && (
            <div className="p-6 md:p-8 border-b border-gray-100" data-testid="unlimited-usage">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl" style={{ backgroundColor: '#DCFCE7' }}>
                  <Check className="h-6 w-6" style={{ color: colors.success }} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Unlimited Buyer Inquiry Acceptances</h3>
                  <p className="text-gray-600">
                    You have accepted <strong>{usedCount}</strong> inquiries this month with no limits.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Quick Benefits Summary */}
          <div className="p-6 md:p-8" data-testid="benefits-summary">
            <h3 className="font-semibold text-gray-900 mb-4">Your Active Benefits</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { 
                  icon: MessageCircle, 
                  label: 'Inquiries', 
                  value: subscription?.features.unlimitedInquiries ? 'Unlimited' : `${remainingCount} left`,
                  active: subscription?.features.unlimitedInquiries || remainingCount > 0
                },
                { 
                  icon: Zap, 
                  label: 'Fast Approval', 
                  value: subscription?.features.canAcceptInquiries ? 'Enabled' : 'Pro Only',
                  active: subscription?.features.canAcceptInquiries 
                },
                { 
                  icon: BadgeCheck, 
                  label: 'Verified Badge', 
                  value: subscription?.features.verifiedBadge ? 'Active' : 'Pro Only',
                  active: subscription?.features.verifiedBadge 
                },
                { 
                  icon: TrendingUp, 
                  label: 'Analytics', 
                  value: subscription?.features.analyticsAccess ? 'Available' : 'Pro Only',
                  active: subscription?.features.analyticsAccess 
                },
              ].map((benefit, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-xl transition-all duration-200 ${
                    benefit.active 
                      ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100' 
                      : 'bg-gray-50 border border-gray-100'
                  }`}
                >
                  <benefit.icon 
                    className="h-5 w-5 mb-2" 
                    style={{ color: benefit.active ? colors.primary : '#9CA3AF' }} 
                  />
                  <p className="text-xs text-gray-500 uppercase tracking-wide">{benefit.label}</p>
                  <p className={`text-sm font-semibold mt-1 ${benefit.active ? 'text-gray-900' : 'text-gray-400'}`}>
                    {benefit.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ============== PRO PLAN UPGRADE CARD (Visually Dominant) ============== */}
        {subscription?.showUpgradeCta && (
          <div 
            className="relative bg-white rounded-2xl shadow-xl border-2 overflow-hidden mb-8 transform transition-all duration-300 hover:shadow-2xl hover:scale-[1.01]"
            style={{ borderColor: colors.primary }}
            data-testid="upgrade-card"
          >
            {/* Most Popular Badge */}
            <div 
              className="absolute top-0 right-0 px-4 py-2 rounded-bl-xl text-white text-sm font-semibold flex items-center gap-1.5"
              style={{ background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)` }}
            >
              <Star className="h-4 w-4 fill-current" />
              Most Popular
            </div>

            <div className="p-8">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
                {/* Left: Value Proposition */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div 
                      className="p-3 rounded-xl"
                      style={{ background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)` }}
                    >
                      <Crown className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900">Upgrade to Pro</h2>
                      <p className="text-gray-500">Scale your business without limits</p>
                    </div>
                  </div>

                  {/* ROI Statement */}
                  <div 
                    className="p-4 rounded-xl mb-6"
                    style={{ backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE' }}
                  >
                    <p className="text-sm" style={{ color: colors.primary }}>
                      <strong>Average Pro seller</strong> converts 3x more inquiries into orders. 
                      Don&apos;t let limits hold back your growth.
                    </p>
                  </div>

                  {/* Key Benefits */}
                  <ul className="space-y-3">
                    {[
                      'Unlimited buyer inquiry acceptances',
                      'Verified seller badge (builds trust)',
                      'Priority placement in search results',
                      'Advanced analytics & insights',
                      '24/7 priority customer support',
                    ].map((benefit, idx) => (
                      <li key={idx} className="flex items-center gap-3 text-gray-700">
                        <div 
                          className="p-1 rounded-full flex-shrink-0"
                          style={{ backgroundColor: '#DCFCE7' }}
                        >
                          <Check className="h-4 w-4" style={{ color: colors.success }} />
                        </div>
                        {benefit}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Right: Pricing & CTA */}
                <div className="lg:w-72 text-center">
                  <div 
                    className="p-6 rounded-2xl"
                    style={{ backgroundColor: colors.background }}
                  >
                    <p className="text-gray-500 text-sm mb-1">Quarterly plan</p>
                    <div className="flex items-baseline justify-center gap-1 mb-1">
                      <span className="text-4xl font-bold" style={{ color: colors.primary }}>
                        ₹{999}
                      </span>
                      <span className="text-gray-500">/quarter</span>
                    </div>
                    <p className="text-xs text-gray-400 mb-6">
                      Just ₹{Math.round((999) / 90)}/day
                    </p>

                    <button 
                      className="w-full py-4 px-6 rounded-xl font-semibold text-white text-lg transition-all duration-200 transform hover:scale-[1.02] hover:shadow-lg active:scale-[0.98] flex items-center justify-center gap-2"
                      style={{ 
                        background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)`,
                      }}
                      onClick={() => alert('Payment integration coming soon!')}
                      data-testid="upgrade-btn"
                    >
                      <Unlock className="h-5 w-5" />
                      Unlock Unlimited Inquiries
                    </button>

                    {/* Trust Microcopy */}
                    <p className="text-xs text-gray-400 mt-4 flex items-center justify-center gap-2">
                      <Shield className="h-3 w-3" />
                      Secure payment  ·  GST invoice  ·  Cancel anytime
                    </p>
                  </div>

                  {/* Instant Activation */}
                  <p className="text-xs text-gray-500 mt-3 flex items-center justify-center gap-1">
                    <Zap className="h-3 w-3" style={{ color: colors.warning }} />
                    Instant activation after payment
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============== COMPARISON TABLE ============== */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-8" data-testid="comparison-table">
          <div className="p-6 md:p-8 border-b border-gray-100">
            <h3 className="text-xl font-bold text-gray-900">Compare Plans</h3>
            <p className="text-gray-500 mt-1">See what you get with each plan</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left p-6 font-semibold text-gray-900">Features</th>
                  <th className="text-center p-6 font-semibold text-gray-500 w-36">Free</th>
                  <th className="text-center p-6 w-36">
                    <div 
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-white font-semibold"
                      style={{ background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)` }}
                    >
                      <Crown className="h-4 w-4" />
                      Pro
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((row, idx) => (
                  <tr 
                    key={idx} 
                    className={`border-b border-gray-50 transition-colors duration-200 hover:bg-gray-50 ${
                      row.highlight ? 'bg-blue-50/50' : ''
                    }`}
                  >
                    <td className="p-6 text-gray-700">
                      {row.feature}
                      {row.highlight && (
                        <span 
                          className="ml-2 px-2 py-0.5 text-xs rounded-full font-medium"
                          style={{ backgroundColor: '#DBEAFE', color: colors.primary }}
                        >
                          Key Difference
                        </span>
                      )}
                    </td>
                    <td className="p-6 text-center">
                      {typeof row.free === 'boolean' ? (
                        row.free ? (
                          <Check className="h-5 w-5 mx-auto" style={{ color: colors.success }} />
                        ) : (
                          <X className="h-5 w-5 mx-auto text-gray-300" />
                        )
                      ) : (
                        <span className="text-gray-600">{row.free}</span>
                      )}
                    </td>
                    <td className="p-6 text-center">
                      {typeof row.pro === 'boolean' ? (
                        row.pro ? (
                          <Check className="h-5 w-5 mx-auto" style={{ color: colors.success }} />
                        ) : (
                          <X className="h-5 w-5 mx-auto text-gray-300" />
                        )
                      ) : (
                        <span className="font-semibold" style={{ color: colors.primary }}>{row.pro}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ============== TRUST SECTION ============== */}
        <div 
          className="rounded-2xl p-6 md:p-8 mb-8"
          style={{ backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE' }}
          data-testid="trust-section"
        >
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div 
              className="p-4 rounded-2xl flex-shrink-0"
              style={{ backgroundColor: 'white' }}
            >
              <Sparkles className="h-8 w-8" style={{ color: colors.primary }} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                Thousands of sellers upgrade to Pro to grow faster
              </h3>
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
                <span className="flex items-center gap-1.5">
                  <Check className="h-4 w-4" style={{ color: colors.success }} />
                  Higher search visibility
                </span>
                <span className="flex items-center gap-1.5">
                  <Check className="h-4 w-4" style={{ color: colors.success }} />
                  Faster buyer responses
                </span>
                <span className="flex items-center gap-1.5">
                  <Check className="h-4 w-4" style={{ color: colors.success }} />
                  Verified credibility badge
                </span>
                <span className="flex items-center gap-1.5">
                  <Check className="h-4 w-4" style={{ color: colors.success }} />
                  3x more inquiry conversions
                </span>
              </div>
            </div>
            {isFree && (
              <button 
                className="md:ml-auto px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200 hover:scale-[1.02] whitespace-nowrap flex items-center gap-2"
                style={{ background: `linear-gradient(135deg, ${colors.accent.from} 0%, ${colors.accent.to} 100%)` }}
                onClick={() => alert('Payment integration coming soon!')}
              >
                Join Them
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* ============== TRIAL USER NOTICE ============== */}
        {isTrial && (
          <div 
            className="rounded-2xl p-6 md:p-8 mb-8 border-2"
            style={{ backgroundColor: '#FEF3C7', borderColor: '#FCD34D' }}
            data-testid="trial-notice"
          >
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              <div className="p-4 rounded-2xl bg-white flex-shrink-0">
                <Clock className="h-8 w-8" style={{ color: colors.warning }} />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900 mb-2">Your Trial Period is Active</h3>
                <p className="text-gray-700">
                  Enjoy unlimited access during your trial. <strong>Trial cannot be renewed</strong> — 
                  upgrade to Pro before it expires to keep all your benefits.
                </p>
              </div>
              <button 
                className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200 hover:scale-[1.02] whitespace-nowrap"
                style={{ backgroundColor: colors.primary }}
                onClick={() => alert('Payment integration coming soon!')}
                data-testid="trial-upgrade-btn"
              >
                Upgrade to Pro - ₹{999}/quarter
              </button>
            </div>
          </div>
        )}

        {/* ============== PRO USER: Subscription Details ============== */}
        {isPro && (
          <div 
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8 mb-8"
            data-testid="pro-details"
          >
            <h3 className="text-lg font-bold text-gray-900 mb-4">Subscription Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-4 rounded-xl bg-gray-50">
                <p className="text-sm text-gray-500 mb-1">Plan</p>
                <p className="font-semibold text-gray-900">Pro (Quarterly)</p>
              </div>
              <div className="p-4 rounded-xl bg-gray-50">
                <p className="text-sm text-gray-500 mb-1">Started On</p>
                <p className="font-semibold text-gray-900">
                  {subscription?.subscription.startDate 
                    ? new Date(subscription.subscription.startDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                    : '-'}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-gray-50">
                <p className="text-sm text-gray-500 mb-1">Renews On</p>
                <p className="font-semibold text-gray-900">
                  {subscription?.subscription.endDate 
                    ? new Date(subscription.subscription.endDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                    : '-'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ============== FOOTER ============== */}
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">
            Questions about your subscription? Contact us at{' '}
            <a href="mailto:support@b2bmarket.com" className="text-blue-600 hover:underline">
              admin@.udyogconnect.in
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
