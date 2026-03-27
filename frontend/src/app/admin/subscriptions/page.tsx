'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  Search, Loader2, ChevronDown, ChevronUp, Save, X, RotateCcw,
  Shield, Zap, Crown, Infinity, AlertCircle, CheckCircle2,
  SlidersHorizontal, Building2, Clock, Ban
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SellerLimits {
  maxPanels: number;
  maxRules: number;
  maxInvoicesPerMonth: number;
  maxEmployees: number;
  export: boolean;
  pdfExport: boolean;
  automation: boolean;
  maxSessions: number;
}

interface SellerRow {
  userId: string;
  email: string;
  name: string;
  companyName: string;
  plan: string;
  effectivePlan: string;
  status: string;
  isExpired: boolean;
  endDate: string | null;
  overrides: Partial<SellerLimits>;
  defaultLimits: SellerLimits;
  effectiveLimits: SellerLimits;
  usage: { panels: number; rules: number };
}

const PLAN_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  free:       { bg: 'bg-zinc-50',   text: 'text-zinc-700',   border: 'border-zinc-200', dot: 'bg-zinc-400' },
  standard:   { bg: 'bg-blue-50',   text: 'text-blue-700',   border: 'border-blue-200', dot: 'bg-blue-500' },
  pro:        { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', dot: 'bg-violet-500' },
  enterprise: { bg: 'bg-amber-50',  text: 'text-amber-700',  border: 'border-amber-200', dot: 'bg-amber-500' },
};

const PLAN_ICONS: Record<string, typeof Shield> = {
  free: Shield,
  standard: Zap,
  pro: Crown,
  enterprise: Infinity,
};

const STATUS_STYLES: Record<string, string> = {
  active: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  expired: 'text-red-700 bg-red-50 border-red-200',
  cancelled: 'text-gray-600 bg-gray-50 border-gray-200',
  suspended: 'text-orange-700 bg-orange-50 border-orange-200',
  free: 'text-zinc-600 bg-zinc-50 border-zinc-200',
};

function formatLimit(val: number): string {
  return val === -1 ? 'Unlimited' : String(val);
}

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit === -1 ? 0 : limit === 0 ? 100 : Math.min((used / limit) * 100, 100);
  const isAtLimit = limit !== -1 && used >= limit;
  return (
    <div className="space-y-1" data-testid={`usage-bar-${label.toLowerCase()}`}>
      <div className="flex justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className={isAtLimit ? 'text-red-600 font-semibold' : ''}>
          {used} / {limit === -1 ? <span className="inline-flex items-center"><Infinity className="h-3 w-3" /></span> : limit}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isAtLimit ? 'bg-red-500' : pct > 75 ? 'bg-amber-400' : 'bg-emerald-400'
          }`}
          style={{ width: limit === -1 ? '0%' : `${pct}%` }}
        />
      </div>
    </div>
  );
}

function OverrideEditor({
  seller,
  onSave,
  onClose,
}: {
  seller: SellerRow;
  onSave: (userId: string, overrides: Record<string, number | boolean>) => Promise<void>;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<Record<string, number | boolean>>({ ...seller.overrides });
  const [saving, setSaving] = useState(false);

  const numericFields = [
    { key: 'maxPanels', label: 'Max Panels' },
    { key: 'maxRules', label: 'Max Rules' },
    { key: 'maxInvoicesPerMonth', label: 'Max Invoices/Month' },
    { key: 'maxEmployees', label: 'Max Employees' },
    { key: 'maxSessions', label: 'Max Sessions' },
  ];
  const booleanFields = [
    { key: 'export', label: 'Excel Export' },
    { key: 'pdfExport', label: 'PDF Export' },
    { key: 'automation', label: 'Automation' },
  ];

  const handleSave = async () => {
    setSaving(true);
    // Only send keys that differ from plan default
    const cleanOverrides: Record<string, number | boolean> = {};
    for (const [k, v] of Object.entries(draft)) {
      const defaultVal = (seller.defaultLimits as unknown as Record<string, number | boolean>)[k];
      if (v !== defaultVal) cleanOverrides[k] = v;
    }
    await onSave(seller.userId, cleanOverrides);
    setSaving(false);
  };

  const hasChanges = JSON.stringify(draft) !== JSON.stringify(seller.overrides);

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-5 mt-3 animate-in slide-in-from-top-2 duration-200" data-testid="override-editor">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-violet-600" />
          <h4 className="font-semibold text-gray-900 text-sm">Override Limits for {seller.companyName || seller.name || seller.email}</h4>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-md transition" data-testid="close-override-editor">
          <X className="h-4 w-4 text-gray-400" />
        </button>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Overrides take priority over plan defaults. Leave blank to use the <strong>{seller.plan}</strong> plan default.
        Use <code className="bg-gray-100 px-1 rounded">-1</code> for unlimited.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        {numericFields.map(({ key, label }) => {
          const defaultVal = (seller.defaultLimits as unknown as Record<string, number>)[key];
          const isOverridden = key in draft;
          return (
            <div key={key} className={`rounded-lg border p-3 transition ${isOverridden ? 'border-violet-300 bg-violet-50/50' : 'border-gray-200'}`}>
              <label className="text-xs font-medium text-gray-600 block mb-1">{label}</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={draft[key] !== undefined ? String(draft[key]) : ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '') {
                      const next = { ...draft };
                      delete next[key];
                      setDraft(next);
                    } else {
                      setDraft({ ...draft, [key]: parseInt(val, 10) });
                    }
                  }}
                  placeholder={String(defaultVal === -1 ? 'Unlimited' : defaultVal)}
                  className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-violet-300 focus:border-violet-300 outline-none"
                  data-testid={`override-${key}`}
                />
                {isOverridden && (
                  <button
                    onClick={() => { const next = { ...draft }; delete next[key]; setDraft(next); }}
                    className="text-gray-400 hover:text-red-500 transition"
                    title="Reset to plan default"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <span className="text-[10px] text-gray-400 mt-1 block">
                Default: {defaultVal === -1 ? 'Unlimited' : defaultVal}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-3 mb-5">
        {booleanFields.map(({ key, label }) => {
          const defaultVal = (seller.defaultLimits as unknown as Record<string, boolean>)[key];
          const isOverridden = key in draft;
          const currentVal = draft[key] !== undefined ? draft[key] as boolean : defaultVal;
          return (
            <button
              key={key}
              onClick={() => {
                if (isOverridden && draft[key] === !defaultVal) {
                  const next = { ...draft };
                  delete next[key];
                  setDraft(next);
                } else {
                  setDraft({ ...draft, [key]: !currentVal });
                }
              }}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition ${
                currentVal
                  ? isOverridden ? 'bg-violet-100 border-violet-300 text-violet-800' : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : 'bg-gray-50 border-gray-200 text-gray-500'
              }`}
              data-testid={`override-${key}`}
            >
              {currentVal ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Ban className="h-3.5 w-3.5" />}
              {label}
              {isOverridden && <span className="text-[10px] font-medium text-violet-600 bg-violet-200 px-1 rounded">OVERRIDE</span>}
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-3 pt-3 border-t border-gray-100">
        <button
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          data-testid="save-overrides-btn"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? 'Saving...' : 'Save Overrides'}
        </button>
        {Object.keys(seller.overrides).length > 0 && (
          <button
            onClick={() => { setDraft({}); }}
            className="flex items-center gap-2 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition"
            data-testid="clear-all-overrides-btn"
          >
            <RotateCcw className="h-4 w-4" /> Clear All Overrides
          </button>
        )}
        <button onClick={onClose} className="px-4 py-2 text-gray-500 text-sm hover:text-gray-700 transition">
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function AdminSubscriptionsPage() {
  const { getIdToken } = useAuth();
  const [sellers, setSellers] = useState<SellerRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const fetchSellers = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getIdToken();
      const params = new URLSearchParams({ page: String(page), limit: '25' });
      if (search) params.set('search', search);
      if (planFilter) params.set('plan_filter', planFilter);

      const res = await fetch(`${API_URL}/api/admin/subscription/sellers?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSellers(data.sellers || []);
        setTotalPages(data.pages || 1);
      }
    } catch {
      /* network error */
    }
    setLoading(false);
  }, [getIdToken, page, search, planFilter]);

  useEffect(() => { fetchSellers(); }, [fetchSellers]);

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  const handleSaveOverrides = async (userId: string, overrides: Record<string, number | boolean>) => {
    try {
      const token = await getIdToken();

      if (Object.keys(overrides).length === 0) {
        // Clear overrides
        await fetch(`${API_URL}/api/admin/subscription/override/${userId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        showToast('success', 'Overrides cleared — back to plan defaults');
      } else {
        const res = await fetch(`${API_URL}/api/admin/subscription/override`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId, overrides }),
        });
        if (!res.ok) {
          const err = await res.json();
          showToast('error', err.detail || 'Failed to save overrides');
          return;
        }
        showToast('success', 'Custom limits applied');
      }

      setEditingUserId(null);
      fetchSellers();
    } catch {
      showToast('error', 'Network error');
    }
  };

  // Stats
  const planCounts = sellers.reduce<Record<string, number>>((acc, s) => {
    acc[s.plan] = (acc[s.plan] || 0) + 1;
    return acc;
  }, {});
  const overriddenCount = sellers.filter(s => Object.keys(s.overrides).length > 0).length;
  const expiredCount = sellers.filter(s => s.isExpired).length;

  return (
    <div className="max-w-7xl mx-auto" data-testid="admin-subscriptions-page">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all animate-in slide-in-from-right-5 ${
          toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`} data-testid="toast-notification">
          {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Subscription Management</h1>
        <p className="text-sm text-gray-500 mt-1">Manage seller plans, limits, and per-seller overrides</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {['free', 'standard', 'pro', 'enterprise'].map(plan => {
          const colors = PLAN_COLORS[plan] || PLAN_COLORS.free;
          const Icon = PLAN_ICONS[plan] || Shield;
          return (
            <button
              key={plan}
              onClick={() => setPlanFilter(planFilter === plan ? '' : plan)}
              className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                planFilter === plan ? `${colors.border} ${colors.bg} ring-2 ring-offset-1 ring-${plan === 'pro' ? 'violet' : plan === 'enterprise' ? 'amber' : plan === 'standard' ? 'blue' : 'zinc'}-300` : `border-gray-100 hover:${colors.border} hover:${colors.bg}`
              }`}
              data-testid={`filter-${plan}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`h-4 w-4 ${colors.text}`} />
                <span className={`text-xs font-semibold uppercase tracking-wide ${colors.text}`}>{plan}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{planCounts[plan] || 0}</div>
              <span className="text-xs text-gray-400">sellers</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="flex items-center gap-3 p-3 rounded-lg bg-violet-50 border border-violet-100">
          <SlidersHorizontal className="h-5 w-5 text-violet-600" />
          <div>
            <div className="text-lg font-bold text-gray-900">{overriddenCount}</div>
            <div className="text-xs text-gray-500">Custom Overrides</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50 border border-red-100">
          <Clock className="h-5 w-5 text-red-500" />
          <div>
            <div className="text-lg font-bold text-gray-900">{expiredCount}</div>
            <div className="text-xs text-gray-500">Expired</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 border border-emerald-100">
          <Building2 className="h-5 w-5 text-emerald-600" />
          <div>
            <div className="text-lg font-bold text-gray-900">{sellers.length}</div>
            <div className="text-xs text-gray-500">Total on Page</div>
          </div>
        </div>
      </div>

      {/* Search + Filter Bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by company, name, or email..."
            className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-300 focus:border-violet-300 outline-none"
            data-testid="search-input"
          />
        </div>
        {planFilter && (
          <button
            onClick={() => setPlanFilter('')}
            className="flex items-center gap-1 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition text-gray-600"
            data-testid="clear-filter-btn"
          >
            <X className="h-3 w-3" /> {planFilter}
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 text-violet-500 animate-spin" />
        </div>
      ) : sellers.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Building2 className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No sellers found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="sellers-table">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Seller</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Plan</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Panels</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Rules</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Features</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sellers.map((s) => {
                  const colors = PLAN_COLORS[s.effectivePlan] || PLAN_COLORS.free;
                  const PlanIcon = PLAN_ICONS[s.effectivePlan] || Shield;
                  const hasOverrides = Object.keys(s.overrides).length > 0;
                  const isEditing = editingUserId === s.userId;

                  return (
                    <tr key={s.userId} className="group" data-testid={`seller-row-${s.userId}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`h-8 w-8 rounded-lg ${colors.bg} flex items-center justify-center`}>
                            <PlanIcon className={`h-4 w-4 ${colors.text}`} />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900 truncate max-w-[180px]">
                              {s.companyName || s.name || 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-400 truncate max-w-[180px]">{s.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${colors.bg} ${colors.text} border ${colors.border}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />
                          {s.plan}
                          {hasOverrides && <span className="text-[9px] font-bold text-violet-600 bg-violet-100 px-1 rounded ml-1">+OVR</span>}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s.status] || STATUS_STYLES.free}`}>
                          {s.status}
                        </span>
                        {s.endDate && !s.isExpired && (
                          <div className="text-[10px] text-gray-400 mt-0.5">
                            Ends {new Date(s.endDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 min-w-[120px]">
                        <UsageBar used={s.usage.panels} limit={s.effectiveLimits.maxPanels} label="Panels" />
                      </td>
                      <td className="px-4 py-3 min-w-[120px]">
                        <UsageBar used={s.usage.rules} limit={s.effectiveLimits.maxRules} label="Rules" />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          {s.effectiveLimits.export && (
                            <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 text-[10px] rounded font-medium border border-emerald-100">XLS</span>
                          )}
                          {s.effectiveLimits.pdfExport && (
                            <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-[10px] rounded font-medium border border-blue-100">PDF</span>
                          )}
                          {s.effectiveLimits.automation && (
                            <span className="px-1.5 py-0.5 bg-violet-50 text-violet-600 text-[10px] rounded font-medium border border-violet-100">AUTO</span>
                          )}
                          {!s.effectiveLimits.export && !s.effectiveLimits.pdfExport && !s.effectiveLimits.automation && (
                            <span className="text-[10px] text-gray-400">None</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setEditingUserId(isEditing ? null : s.userId)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                            isEditing
                              ? 'bg-violet-600 text-white'
                              : hasOverrides
                              ? 'bg-violet-50 text-violet-700 border border-violet-200 hover:bg-violet-100'
                              : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'
                          }`}
                          data-testid={`edit-overrides-${s.userId}`}
                        >
                          <SlidersHorizontal className="h-3 w-3" />
                          {isEditing ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                          {hasOverrides ? 'Edit' : 'Override'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Inline Editor — renders below the table but controlled by editingUserId */}
          {editingUserId && sellers.find(s => s.userId === editingUserId) && (
            <div className="border-t border-gray-100 px-4 py-3">
              <OverrideEditor
                seller={sellers.find(s => s.userId === editingUserId)!}
                onSave={handleSaveOverrides}
                onClose={() => setEditingUserId(null)}
              />
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6" data-testid="pagination">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Prev
          </button>
          <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
