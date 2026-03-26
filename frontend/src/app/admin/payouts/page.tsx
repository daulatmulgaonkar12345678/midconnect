'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  Wallet, IndianRupee, Clock, CheckCircle2, Users, ChevronDown, ChevronRight,
  Download, Search, Loader2, AlertCircle, CreditCard, Building2, X, Filter
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Partner {
  code: string;
  name: string;
  revenue: number;
  commission: number;
  paidAmount: number;
  pendingAmount: number;
  sales: number;
  totalReferred: number;
  successfulReferred: number;
}

interface Order {
  orderId: string;
  userId: string;
  userName: string;
  plan: string;
  amount: number;
  commission: number;
  commissionPercent: number;
  payoutStatus: 'pending' | 'paid';
  payoutDate: string | null;
  payoutReference: string;
  payoutMethod: string;
  payoutBatchId: string;
  createdAt: string;
}

interface Overview {
  totalReferredUsers: number;
  paidUsers: number;
  totalRevenue: number;
  totalCommission: number;
  pendingPayout: number;
  paidOutAmount: number;
  partners: Partner[];
}

type DateFilter = 'all' | 'today' | 'week' | 'month';

export default function AdminPayoutsPage() {
  const { getIdToken } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedPartner, setExpandedPartner] = useState<string | null>(null);
  const [partnerOrders, setPartnerOrders] = useState<Record<string, { orders: Order[]; totalCommission: number; paidAmount: number; pendingAmount: number }>>({});
  const [loadingOrders, setLoadingOrders] = useState<string | null>(null);
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [payoutRef, setPayoutRef] = useState('');
  const [payoutMethod, setPayoutMethod] = useState<string>('bank');
  const [showPayoutModal, setShowPayoutModal] = useState(false);
  const [payoutMode, setPayoutMode] = useState<'single' | 'bulk'>('single');
  const [singlePayoutId, setSinglePayoutId] = useState('');
  const [processing, setProcessing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState<DateFilter>('all');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const headers = useCallback(async () => {
    const token = await getIdToken();
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }, [getIdToken]);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    try {
      const h = await headers();
      const res = await fetch(`${API_URL}/api/referral/admin/sales-overview`, { headers: h });
      if (res.ok) setOverview(await res.json());
    } catch { /* empty */ }
    setLoading(false);
  }, [headers]);

  useEffect(() => { fetchOverview(); }, [fetchOverview]);

  const fetchPartnerOrders = async (code: string) => {
    if (partnerOrders[code]) return;
    setLoadingOrders(code);
    try {
      const h = await headers();
      const res = await fetch(`${API_URL}/api/referral/admin/partner-orders/${code}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setPartnerOrders(prev => ({ ...prev, [code]: data }));
      }
    } catch { /* empty */ }
    setLoadingOrders(null);
  };

  const togglePartner = (code: string) => {
    if (expandedPartner === code) {
      setExpandedPartner(null);
      setSelectedOrders(new Set());
    } else {
      setExpandedPartner(code);
      setSelectedOrders(new Set());
      fetchPartnerOrders(code);
    }
  };

  const toggleOrderSelect = (orderId: string) => {
    setSelectedOrders(prev => {
      const next = new Set(prev);
      if (next.has(orderId)) next.delete(orderId);
      else next.add(orderId);
      return next;
    });
  };

  const selectAllPending = (code: string) => {
    const data = partnerOrders[code];
    if (!data) return;
    const pending = data.orders.filter(o => o.payoutStatus === 'pending').map(o => o.orderId);
    setSelectedOrders(new Set(pending));
  };

  const openSinglePayout = (orderId: string) => {
    setSinglePayoutId(orderId);
    setPayoutMode('single');
    setPayoutRef('');
    setPayoutMethod('bank');
    setShowPayoutModal(true);
  };

  const openBulkPayout = () => {
    if (selectedOrders.size === 0) return;
    setPayoutMode('bulk');
    setPayoutRef('');
    setPayoutMethod('bank');
    setShowPayoutModal(true);
  };

  const executePayout = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const h = await headers();
      if (payoutMode === 'single') {
        const res = await fetch(`${API_URL}/api/referral/admin/mark-payout`, {
          method: 'POST',
          headers: h,
          body: JSON.stringify({ orderId: singlePayoutId, payoutReference: payoutRef, payoutMethod }),
        });
        const data = await res.json();
        if (res.ok) {
          setMessage({ type: 'success', text: `Payout marked: ${data.payoutReference || 'N/A'}` });
        } else {
          setMessage({ type: 'error', text: data.detail || 'Failed' });
        }
      } else {
        const res = await fetch(`${API_URL}/api/referral/admin/bulk-payout`, {
          method: 'POST',
          headers: h,
          body: JSON.stringify({ orderIds: Array.from(selectedOrders), payoutReference: payoutRef, payoutMethod }),
        });
        const data = await res.json();
        if (res.ok) {
          setMessage({ type: 'success', text: `Batch ${data.batchId}: ${data.paidCount} paid, ${data.skippedCount} skipped` });
        } else {
          setMessage({ type: 'error', text: data.detail || 'Failed' });
        }
      }
      setShowPayoutModal(false);
      setSelectedOrders(new Set());
      // Refresh data
      const code = expandedPartner;
      if (code) {
        setPartnerOrders(prev => { const next = { ...prev }; delete next[code]; return next; });
        fetchPartnerOrders(code);
      }
      fetchOverview();
    } catch {
      setMessage({ type: 'error', text: 'Network error' });
    }
    setProcessing(false);
  };

  const downloadCSV = async () => {
    try {
      const h = await headers();
      const res = await fetch(`${API_URL}/api/referral/admin/export-payouts`, { headers: h });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payouts_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch { /* empty */ }
  };

  // Filter partners
  const filteredPartners = (overview?.partners || []).filter(p =>
    !searchQuery || p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter orders by date
  const filterOrdersByDate = (orders: Order[]) => {
    if (dateFilter === 'all') return orders;
    const now = new Date();
    const start = new Date();
    if (dateFilter === 'today') start.setHours(0, 0, 0, 0);
    else if (dateFilter === 'week') start.setDate(now.getDate() - 7);
    else if (dateFilter === 'month') start.setMonth(now.getMonth() - 1);
    return orders.filter(o => new Date(o.createdAt) >= start);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-payouts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payout Management</h1>
          <p className="text-sm text-gray-500 mt-1">Track and manage partner commission payouts</p>
        </div>
        <button
          onClick={downloadCSV}
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
          data-testid="export-csv-btn"
        >
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium ${message.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`} data-testid="payout-message">
          {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {message.text}
          <button onClick={() => setMessage(null)} className="ml-auto"><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          testId="total-commission-card"
          icon={<IndianRupee className="w-5 h-5" />}
          label="Total Commission"
          value={overview?.totalCommission || 0}
          color="blue"
        />
        <SummaryCard
          testId="paid-amount-card"
          icon={<CheckCircle2 className="w-5 h-5" />}
          label="Paid Out"
          value={overview?.paidOutAmount || 0}
          color="emerald"
        />
        <SummaryCard
          testId="pending-amount-card"
          icon={<Clock className="w-5 h-5" />}
          label="Pending Payout"
          value={overview?.pendingPayout || 0}
          color="amber"
        />
        <SummaryCard
          testId="total-revenue-card"
          icon={<Wallet className="w-5 h-5" />}
          label="Total Revenue"
          value={overview?.totalRevenue || 0}
          color="slate"
        />
      </div>

      {/* Search + Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search partners..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            data-testid="partner-search-input"
          />
        </div>
        <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1" data-testid="date-filter">
          {(['all', 'today', 'week', 'month'] as DateFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setDateFilter(f)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${dateFilter === f ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
              data-testid={`filter-${f}`}
            >
              {f === 'all' ? 'All' : f === 'today' ? 'Today' : f === 'week' ? 'This Week' : 'This Month'}
            </button>
          ))}
        </div>
      </div>

      {/* Partner Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden" data-testid="partner-table">
        {/* Table Header */}
        <div className="grid grid-cols-[1fr_100px_120px_120px_120px_80px] gap-2 px-5 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
          <span>Partner</span>
          <span className="text-right">Users</span>
          <span className="text-right">Earnings</span>
          <span className="text-right">Paid</span>
          <span className="text-right">Pending</span>
          <span></span>
        </div>

        {filteredPartners.length === 0 ? (
          <div className="px-5 py-12 text-center text-gray-400 text-sm" data-testid="no-partners">
            <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
            No partners found
          </div>
        ) : (
          filteredPartners.map(p => (
            <div key={p.code} data-testid={`partner-row-${p.code}`}>
              {/* Partner Row */}
              <button
                onClick={() => togglePartner(p.code)}
                className="w-full grid grid-cols-[1fr_100px_120px_120px_120px_80px] gap-2 px-5 py-4 hover:bg-gray-50 transition-colors items-center border-b border-gray-100 text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 font-bold text-sm">
                    {(p.name || p.code).charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{p.name || p.code}</div>
                    <div className="text-xs text-gray-400">{p.code}</div>
                  </div>
                </div>
                <div className="text-right text-sm font-medium text-gray-700">{p.sales}</div>
                <div className="text-right text-sm font-semibold text-gray-900">{formatINR(p.commission)}</div>
                <div className="text-right text-sm font-medium text-emerald-600">{formatINR(p.paidAmount)}</div>
                <div className="text-right text-sm font-medium text-amber-600">{formatINR(p.pendingAmount)}</div>
                <div className="flex justify-end">
                  {expandedPartner === p.code
                    ? <ChevronDown className="w-5 h-5 text-gray-400" />
                    : <ChevronRight className="w-5 h-5 text-gray-400" />
                  }
                </div>
              </button>

              {/* Expanded Orders */}
              {expandedPartner === p.code && (
                <div className="bg-gray-50/50 border-b border-gray-200">
                  {loadingOrders === p.code ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                    </div>
                  ) : (
                    <div className="px-5 py-4 space-y-3">
                      {/* Bulk actions bar */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => selectAllPending(p.code)}
                            className="text-xs font-medium text-blue-600 hover:text-blue-700"
                            data-testid="select-all-pending-btn"
                          >
                            Select All Pending
                          </button>
                          {selectedOrders.size > 0 && (
                            <span className="text-xs text-gray-500">{selectedOrders.size} selected</span>
                          )}
                        </div>
                        {selectedOrders.size > 0 && (
                          <button
                            onClick={openBulkPayout}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                            data-testid="bulk-payout-btn"
                          >
                            <CreditCard className="w-3.5 h-3.5" /> Mark {selectedOrders.size} as Paid
                          </button>
                        )}
                      </div>

                      {/* Orders table */}
                      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                        <div className="grid grid-cols-[32px_1fr_80px_90px_90px_90px_80px_100px] gap-2 px-4 py-2.5 bg-gray-50 border-b text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
                          <span></span>
                          <span>User</span>
                          <span>Plan</span>
                          <span className="text-right">Amount</span>
                          <span className="text-right">Commission</span>
                          <span>Status</span>
                          <span>Date</span>
                          <span>Action</span>
                        </div>
                        {filterOrdersByDate(partnerOrders[p.code]?.orders || []).length === 0 ? (
                          <div className="px-4 py-6 text-center text-sm text-gray-400">No orders in this period</div>
                        ) : (
                          filterOrdersByDate(partnerOrders[p.code]?.orders || []).map(o => (
                            <div
                              key={o.orderId}
                              className={`grid grid-cols-[32px_1fr_80px_90px_90px_90px_80px_100px] gap-2 px-4 py-3 border-b border-gray-50 items-center text-sm ${o.payoutStatus === 'paid' ? 'bg-emerald-50/30' : ''}`}
                              data-testid={`order-row-${o.orderId}`}
                            >
                              <div>
                                {o.payoutStatus === 'pending' && (
                                  <input
                                    type="checkbox"
                                    checked={selectedOrders.has(o.orderId)}
                                    onChange={() => toggleOrderSelect(o.orderId)}
                                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    data-testid={`order-checkbox-${o.orderId}`}
                                  />
                                )}
                              </div>
                              <div className="font-medium text-gray-800 truncate">{o.userName}</div>
                              <div>
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 uppercase">{o.plan}</span>
                              </div>
                              <div className="text-right text-gray-700">{formatINR(o.amount)}</div>
                              <div className="text-right font-semibold text-gray-900">{formatINR(o.commission)}</div>
                              <div>
                                {o.payoutStatus === 'paid' ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700" data-testid={`status-paid-${o.orderId}`}>
                                    <CheckCircle2 className="w-3 h-3" /> Paid
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700" data-testid={`status-pending-${o.orderId}`}>
                                    <Clock className="w-3 h-3" /> Pending
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500">{formatDate(o.createdAt)}</div>
                              <div>
                                {o.payoutStatus === 'pending' ? (
                                  <button
                                    onClick={() => openSinglePayout(o.orderId)}
                                    className="text-xs font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                                    data-testid={`mark-paid-${o.orderId}`}
                                  >
                                    <CreditCard className="w-3 h-3" /> Pay
                                  </button>
                                ) : (
                                  <span className="text-xs text-gray-400" title={o.payoutReference || 'No reference'}>
                                    {o.payoutReference ? o.payoutReference.slice(0, 12) : '-'}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Payout Modal */}
      {showPayoutModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={() => setShowPayoutModal(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()} data-testid="payout-modal">
            <div className="px-6 py-5 border-b border-gray-100">
              <h3 className="text-lg font-bold text-gray-900">
                {payoutMode === 'single' ? 'Mark Payout' : `Bulk Payout (${selectedOrders.size} orders)`}
              </h3>
              <p className="text-sm text-gray-500 mt-1">Enter payment details for tracking</p>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1.5">Payment Reference (UTR / Transaction ID)</label>
                <input
                  type="text"
                  value={payoutRef}
                  onChange={(e) => setPayoutRef(e.target.value)}
                  placeholder="e.g., UTR123456789"
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  data-testid="payout-reference-input"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1.5">Payment Method</label>
                <div className="flex gap-2">
                  {['bank', 'upi', 'manual'].map(m => (
                    <button
                      key={m}
                      onClick={() => setPayoutMethod(m)}
                      className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-sm font-medium border transition-colors ${payoutMethod === m ? 'bg-blue-50 border-blue-200 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}
                      data-testid={`method-${m}`}
                    >
                      {m === 'bank' && <Building2 className="w-3.5 h-3.5" />}
                      {m === 'upi' && <CreditCard className="w-3.5 h-3.5" />}
                      {m === 'manual' && <Wallet className="w-3.5 h-3.5" />}
                      {m.charAt(0).toUpperCase() + m.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
              <button
                onClick={() => setShowPayoutModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                data-testid="cancel-payout-btn"
              >
                Cancel
              </button>
              <button
                onClick={executePayout}
                disabled={processing}
                className="flex-1 px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="confirm-payout-btn"
              >
                {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Confirm Payout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ testId, icon, label, value, color }: { testId: string; icon: React.ReactNode; label: string; value: number; color: string }) {
  const colorMap: Record<string, { bg: string; iconBg: string; iconText: string; valueText: string }> = {
    blue: { bg: 'bg-blue-50 border-blue-100', iconBg: 'bg-blue-100', iconText: 'text-blue-600', valueText: 'text-blue-700' },
    emerald: { bg: 'bg-emerald-50 border-emerald-100', iconBg: 'bg-emerald-100', iconText: 'text-emerald-600', valueText: 'text-emerald-700' },
    amber: { bg: 'bg-amber-50 border-amber-100', iconBg: 'bg-amber-100', iconText: 'text-amber-600', valueText: 'text-amber-700' },
    slate: { bg: 'bg-slate-50 border-slate-200', iconBg: 'bg-slate-200', iconText: 'text-slate-600', valueText: 'text-slate-700' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className={`${c.bg} border rounded-xl p-5`} data-testid={testId}>
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 ${c.iconBg} rounded-lg flex items-center justify-center ${c.iconText}`}>{icon}</div>
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${c.valueText}`}>{formatINR(value)}</div>
    </div>
  );
}

function formatINR(n: number): string {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
}

function formatDate(iso: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}
