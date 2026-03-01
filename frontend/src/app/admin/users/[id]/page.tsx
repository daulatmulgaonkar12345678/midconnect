'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import type { SubscriptionDetails } from '@/types';
import { 
  fetchWithAuth,
  getAdminSubscription,
  activateSubscription,
  extendSubscription,
  suspendSubscription,
  reactivateSubscription,
  SubscriptionWithUser
} from '@/lib/api';
import { 
  ArrowLeft, 
  Loader2,
  Crown,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Pause,
  Play,
  Plus,
  Save,
  User,
  Mail,
  Phone,
  MapPin,
  Building,
  AlertCircle,
  Star,
  Shield,
  Award
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

// Status Badge Component
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ElementType }> = {
    active: { bg: '#DCFCE7', text: colors.success, icon: CheckCircle },
    expired: { bg: '#FEE2E2', text: colors.danger, icon: XCircle },
    suspended: { bg: '#FEF3C7', text: colors.warning, icon: Pause },
  };
  const c = config[status] || config.expired;
  const Icon = c.icon;

  return (
    <span 
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium"
      style={{ backgroundColor: c.bg, color: c.text }}
      data-testid={`status-badge-${status}`}
    >
      <Icon className="h-4 w-4" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// Plan Badge
function PlanBadge({ plan }: { plan: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    free: { bg: '#F3F4F6', text: '#6B7280' },
    trial: { bg: '#DBEAFE', text: colors.primary },
    pro: { bg: `linear-gradient(135deg, ${colors.accent.from}, ${colors.accent.to})`, text: '#FFFFFF' },
  };
  const c = config[plan] || config.free;

  return (
    <span 
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold"
      style={{ background: c.bg, color: c.text }}
      data-testid={`plan-badge-${plan}`}
    >
      {plan === 'pro' && <Crown className="h-4 w-4" />}
      {plan.charAt(0).toUpperCase() + plan.slice(1)}
    </span>
  );
}

// User Info Interface
interface UserDetail {
  _id: string;
  email: string;
  business_name: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
  gst_number?: string;
  gst_status: string;
  // SSOT: Use camelCase to match database schema
  isSeller: boolean;
  isAdmin: boolean;
  accountStatus: string;
  createdAt?: string;
  listingCount?: number;
  badgeType?: 'none' | 'choice' | 'trusted';
}

export default function UserDetailPage() {
  const router = useRouter();
  const params = useParams();
  const userId = params.id as string;
  
  const { getIdToken, isAuthenticated, loading: authLoading } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // User data
  const [user, setUser] = useState<UserDetail | null>(null);
  
  // Subscription data
  const [subscription, setSubscription] = useState<SubscriptionWithUser | null>(null);
  
  // Form states
  const [activateForm, setActivateForm] = useState({
    planName: 'pro' as 'free' | 'trial' | 'pro',
    startDate: new Date().toISOString().split('T')[0],
    durationDays: 90,
    notes: ''
  });
  const [extendDays, setExtendDays] = useState(30);
  const [extendNotes, setExtendNotes] = useState('');
  const [suspendReason, setSuspendReason] = useState('');
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [badgeUpdating, setBadgeUpdating] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push(`/login?redirect=/admin/users/${userId}`);
      return;
    }

    loadData();
  }, [isAuthenticated, authLoading, userId]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      // Fetch user details
      const userData = await fetchWithAuth<UserDetail>(`/admin/users/${userId}/detail`, token);
      setUser(userData);
      
      // Fetch subscription details
      const subscriptionData = await getAdminSubscription(token, userId);
      setSubscription(subscriptionData);
      
    } catch (err) {
      console.error('Failed to load user data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  async function handleActivate() {
    try {
      setSaving(true);
      setError(null);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const result = await activateSubscription(token, userId, {
        planName: activateForm.planName,
        startDate: new Date(activateForm.startDate).toISOString(),
        durationDays: activateForm.planName === 'free' ? undefined : activateForm.durationDays,
        notes: activateForm.notes || undefined
      });
      
      setSuccessMessage(result.message);
      loadData(); // Re-fetch to get updated data from backend
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate subscription');
    } finally {
      setSaving(false);
    }
  }

  async function handleExtend() {
    try {
      setSaving(true);
      setError(null);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const result = await extendSubscription(token, userId, {
        extendDays: extendDays,
        notes: extendNotes || undefined
      });
      
      setSuccessMessage(result.message);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extend subscription');
    } finally {
      setSaving(false);
    }
  }

  async function handleSuspend() {
    if (!suspendReason.trim()) {
      setError('Please provide a reason for suspension');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const result = await suspendSubscription(token, userId, suspendReason);
      
      setSuccessMessage(result.message);
      setSuspendReason('');
      setShowSuspendModal(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to suspend subscription');
    } finally {
      setSaving(false);
    }
  }

  async function handleReactivate() {
    try {
      setSaving(true);
      setError(null);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const result = await reactivateSubscription(token, userId);
      
      setSuccessMessage(result.message);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reactivate subscription');
    } finally {
      setSaving(false);
    }
  }

  // Clear messages after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  if (loading || authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin mx-auto" style={{ color: colors.primary }} />
          <p className="mt-4 text-gray-600">Loading user details...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
        <div className="text-center">
          <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900">User Not Found</h2>
          <p className="text-gray-500 mt-2">The requested user could not be found.</p>
          <Link href="/admin/users" className="mt-4 inline-flex items-center gap-2 text-blue-600 hover:underline">
            <ArrowLeft className="h-4 w-4" />
            Back to Users
          </Link>
        </div>
      </div>
    );
  }

  const sub = subscription?.subscription;

  return (
    <div data-testid="user-detail-page">
      {/* Header */}
      <div className="mb-6">
        <Link 
          href="/admin/users" 
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm mb-2"
          data-testid="back-to-users-link"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Users
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{user.business_name || 'User Details'}</h1>
        <p className="text-gray-500">{user.email}</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700" data-testid="error-message">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}
      {successMessage && (
        <div className="mb-6 p-4 rounded-lg bg-green-50 border border-green-200 flex items-center gap-3 text-green-700" data-testid="success-message">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          {successMessage}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - User Info */}
        <div className="lg:col-span-1 space-y-6">
          {/* User Profile Card */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="user-info-card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="h-5 w-5 text-gray-400" />
              User Information
            </h2>
            
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <Building className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Business Name</p>
                  <p className="font-medium text-gray-900">{user.business_name || '-'}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <Mail className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="font-medium text-gray-900">{user.email}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <Phone className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Phone</p>
                  <p className="font-medium text-gray-900">{user.phone || '-'}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">Location</p>
                  <p className="font-medium text-gray-900">
                    {[user.city, user.state, user.pincode].filter(Boolean).join(', ') || '-'}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">GST Status</span>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    user.gst_status === 'verified' ? 'bg-green-100 text-green-700' :
                    user.gst_status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {user.gst_status || 'None'}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Account Status</span>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    user.accountStatus === 'deleted' ? 'bg-red-100 text-red-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {user.accountStatus || 'Active'}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Role</span>
                  <div className="flex gap-1">
                    {user.isSeller && (
                      <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full">Seller</span>
                    )}
                    {user.isAdmin && (
                      <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full">Admin</span>
                    )}
                    {!user.isSeller && !user.isAdmin && (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">Buyer</span>
                    )}
                  </div>
                </div>
                
                {user.listingCount !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Listings</span>
                    <span className="font-medium text-gray-900">{user.listingCount}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Subscription Management */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current Subscription Status Card */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="subscription-status-card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Crown className="h-5 w-5" style={{ color: colors.primary }} />
              Subscription Management
            </h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <p className="text-sm text-gray-500 mb-1">Plan</p>
                <PlanBadge plan={sub?.planName || 'free'} />
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Status</p>
                <StatusBadge status={sub?.status || 'active'} />
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Days Remaining</p>
                <p className="text-xl font-bold text-gray-900" data-testid="days-remaining">
                  {sub?.daysRemaining === -1 ? '∞' : sub?.daysRemaining ?? 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Expiring Soon?</p>
                <p className={`text-xl font-bold ${sub?.isExpiringSoon ? 'text-orange-500' : 'text-gray-400'}`} data-testid="expiring-soon">
                  {sub?.isExpiringSoon ? (
                    <span className="flex items-center gap-1">
                      <AlertTriangle className="h-5 w-5" />
                      Yes
                    </span>
                  ) : 'No'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg mb-6">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Start Date</p>
                  <p className="font-medium text-gray-900" data-testid="start-date">
                    {sub?.startDate ? new Date(sub.startDate).toLocaleDateString() : '-'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">End Date</p>
                  <p className="font-medium text-gray-900" data-testid="end-date">
                    {sub?.endDate ? new Date(sub.endDate).toLocaleDateString() : 'Never (Free)'}
                  </p>
                </div>
              </div>
            </div>

            {sub?.notes && (
              <div className="p-3 bg-blue-50 rounded-lg mb-6">
                <p className="text-sm text-blue-700"><strong>Notes:</strong> {sub.notes}</p>
              </div>
            )}

            {/* Action Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Activate/Change Plan */}
              <div className="p-4 border border-gray-200 rounded-lg" data-testid="activate-subscription-form">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Crown className="h-5 w-5" style={{ color: colors.primary }} />
                  Activate Subscription
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Plan</label>
                    <select 
                      value={activateForm.planName}
                      onChange={(e) => setActivateForm({ ...activateForm, planName: e.target.value as 'free' | 'trial' | 'pro' })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      data-testid="plan-select"
                    >
                      <option value="free">Free (5 inquiries/month)</option>
                      <option value="trial">Trial (90 days unlimited)</option>
                      <option value="pro">Pro (Quarterly)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={activateForm.startDate}
                      onChange={(e) => setActivateForm({ ...activateForm, startDate: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      data-testid="start-date-input"
                    />
                  </div>
                  
                  {activateForm.planName !== 'free' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Duration</label>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setActivateForm({ ...activateForm, durationDays: 30 })}
                          className={`flex-1 py-2 px-3 text-sm rounded-lg border ${activateForm.durationDays === 30 ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-200'}`}
                        >
                          30 days
                        </button>
                        <button
                          type="button"
                          onClick={() => setActivateForm({ ...activateForm, durationDays: 90 })}
                          className={`flex-1 py-2 px-3 text-sm rounded-lg border ${activateForm.durationDays === 90 ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-200'}`}
                        >
                          90 days
                        </button>
                        <input
                          type="number"
                          value={activateForm.durationDays}
                          onChange={(e) => setActivateForm({ ...activateForm, durationDays: parseInt(e.target.value) || 90 })}
                          className="w-20 px-2 py-2 border border-gray-200 rounded-lg text-sm text-center"
                          min={1}
                          max={365}
                          data-testid="duration-input"
                        />
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Admin Notes</label>
                    <textarea
                      value={activateForm.notes}
                      onChange={(e) => setActivateForm({ ...activateForm, notes: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      rows={2}
                      placeholder="Optional notes..."
                      data-testid="activate-notes-input"
                    />
                  </div>

                  <button
                    onClick={handleActivate}
                    disabled={saving}
                    className="w-full py-2.5 rounded-lg font-medium text-white flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
                    style={{ backgroundColor: colors.primary }}
                    data-testid="activate-subscription-btn"
                  >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Activate Subscription
                  </button>
                </div>
              </div>

              {/* Extend Subscription */}
              <div className="p-4 border border-gray-200 rounded-lg" data-testid="extend-subscription-form">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Plus className="h-5 w-5" style={{ color: colors.success }} />
                  Extend Subscription
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Add Days</label>
                    <input
                      type="number"
                      value={extendDays}
                      onChange={(e) => setExtendDays(parseInt(e.target.value) || 30)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      min={1}
                      max={365}
                      data-testid="extend-days-input"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                    <textarea
                      value={extendNotes}
                      onChange={(e) => setExtendNotes(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      rows={2}
                      placeholder="Reason for extension..."
                      data-testid="extend-notes-input"
                    />
                  </div>

                  <button
                    onClick={handleExtend}
                    disabled={saving || sub?.planName === 'free'}
                    className="w-full py-2.5 rounded-lg font-medium text-white flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
                    style={{ backgroundColor: colors.success }}
                    data-testid="extend-subscription-btn"
                  >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Extend by {extendDays} Days
                  </button>
                  
                  {sub?.planName === 'free' && (
                    <p className="text-xs text-gray-500 text-center">Cannot extend free plan</p>
                  )}
                </div>
              </div>
            </div>

            {/* Suspend / Reactivate Section */}
            <div className="mt-6 p-4 border border-gray-200 rounded-lg" data-testid="suspend-controls">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" style={{ color: colors.warning }} />
                Suspension Controls
              </h3>

              {sub?.status === 'suspended' ? (
                <div>
                  <p className="text-gray-600 mb-4">This subscription is currently suspended.</p>
                  <button
                    onClick={handleReactivate}
                    disabled={saving}
                    className="px-6 py-2.5 rounded-lg font-medium text-white flex items-center gap-2 disabled:opacity-50 transition-colors"
                    style={{ backgroundColor: colors.success }}
                    data-testid="reactivate-btn"
                  >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Reactivate Subscription
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-gray-600 mb-4">Suspending will immediately pause the user&apos;s subscription benefits.</p>
                  <button
                    onClick={() => setShowSuspendModal(true)}
                    disabled={saving}
                    className="px-6 py-2.5 rounded-lg font-medium text-white flex items-center gap-2 disabled:opacity-50 transition-colors"
                    style={{ backgroundColor: colors.danger }}
                    data-testid="suspend-btn"
                  >
                    <Pause className="h-4 w-4" />
                    Suspend Subscription
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Suspend Confirmation Modal */}
      {showSuspendModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="suspend-modal">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Confirm Suspension
            </h3>
            <p className="text-gray-600 mb-4">
              Are you sure you want to suspend this subscription? The user will lose access to subscription benefits immediately.
            </p>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Suspension Reason (required)</label>
              <textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                rows={3}
                placeholder="Reason for suspension..."
                data-testid="suspend-reason-input"
              />
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowSuspendModal(false);
                  setSuspendReason('');
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                data-testid="cancel-suspend-btn"
              >
                Cancel
              </button>
              <button
                onClick={handleSuspend}
                disabled={saving || !suspendReason.trim()}
                className="px-4 py-2 bg-red-600 text-white rounded-lg font-medium disabled:opacity-50 flex items-center gap-2 transition-colors hover:bg-red-700"
                data-testid="confirm-suspend-btn"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
                Suspend Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
