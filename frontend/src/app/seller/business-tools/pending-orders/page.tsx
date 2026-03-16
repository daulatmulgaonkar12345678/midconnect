'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  Package2, Loader2, AlertTriangle, CheckCircle2, X,
  Clock, XCircle, Bell, RefreshCw, FileText
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface PendingOrder {
  id: string;
  productName: string;
  buyerName: string;
  buyerPhone: string;
  buyerId: string;
  listingId: string;
  orderedQty: number;
  fulfilledQty: number;
  pendingQty: number;
  price: number;
  gstPercent: number;
  invoiceNumber?: string;
  currentStock: number;
  availableStock: number;
  status: string;
  createdAt: string;
}

const statusConfig: Record<string, { color: string; icon: any; label: string }> = {
  pending: { color: 'bg-amber-100 text-amber-700', icon: Clock, label: 'Pending' },
  partially_fulfilled: { color: 'bg-blue-100 text-blue-700', icon: RefreshCw, label: 'Partial' },
  completed: { color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2, label: 'Completed' },
  cancelled: { color: 'bg-red-100 text-red-500', icon: XCircle, label: 'Cancelled' },
};

function fmtDate(d: string) {
  try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return d; }
}

export default function PendingOrdersPage() {
  const router = useRouter();
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [orders, setOrders] = useState<PendingOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [partialCount, setPartialCount] = useState(0);

  // Fulfil modal
  const [fulfilModal, setFulfilModal] = useState<PendingOrder | null>(null);
  const [fulfilQty, setFulfilQty] = useState('');

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchOrders = useCallback(async () => {
    try {
      const h = await authHeaders();
      const params = filter ? `?status=${filter}` : '';
      const res = await fetch(`${API_URL}/api/business-tools/pending-orders${params}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setOrders(data.pendingOrders || []);
        setPendingCount(data.pendingCount || 0);
        setPartialCount(data.partialCount || 0);
      }
    } catch { setError('Failed to load pending orders'); }
    setLoading(false);
  }, [authHeaders, filter]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const handleFulfil = async () => {
    if (!fulfilModal) return;
    const qty = parseInt(fulfilQty) || fulfilModal.pendingQty;
    setActionLoading(fulfilModal.id);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/pending-orders/${fulfilModal.id}/fulfil`, {
        method: 'POST', headers: h, body: JSON.stringify({ quantity: qty, deductStock: true })
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(data.message + (data.invoiceNumber ? ` (${data.invoiceNumber})` : ''));
        setTimeout(() => setSuccess(null), 4000);
        setFulfilModal(null);
        fetchOrders();
      } else {
        setError(data.detail || 'Fulfilment failed');
      }
    } catch { setError('Fulfilment failed'); }
    setActionLoading(null);
  };

  const handleCancel = async (orderId: string) => {
    if (!confirm('Cancel this pending order? Reserved stock will be released.')) return;
    setActionLoading(orderId);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/pending-orders/${orderId}/cancel`, {
        method: 'POST', headers: h, body: JSON.stringify({ reason: 'Cancelled by seller' })
      });
      if (res.ok) {
        setSuccess('Pending order cancelled');
        setTimeout(() => setSuccess(null), 3000);
        fetchOrders();
      }
    } catch { setError('Cancel failed'); }
    setActionLoading(null);
  };

  const handleCreateInvoice = (order: PendingOrder) => {
    const params = new URLSearchParams({
      buyerId: order.buyerId,
      productId: order.listingId,
      qty: String(order.pendingQty),
      price: String(order.price),
      gstPercent: String(order.gstPercent),
      pendingOrderRef: order.invoiceNumber || '',
    });
    router.push(`/seller/business-tools/invoices?${params.toString()}`);
  };

  const handleNotify = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/pending-orders/${orderId}/notify`, {
        method: 'POST', headers: h
      });
      const data = await res.json();
      if (res.ok && data.whatsappLink) {
        window.open(data.whatsappLink, '_blank');
        setSuccess('Opening WhatsApp to notify buyer...');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError((data as { detail?: string }).detail || 'Notification failed');
      }
    } catch { setError('Notification failed'); }
    setActionLoading(null);
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-indigo-600" /></div>;

  return (
    <div className="space-y-6" data-testid="pending-orders-page">
      {/* Success / Error */}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-sm" data-testid="success-msg">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" /> {success}
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm" data-testid="error-msg">
          <div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> {error}</div>
          <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="page-heading">Pending Orders</h1>
          <p className="text-gray-600 mt-1">
            {pendingCount + partialCount > 0
              ? `${pendingCount} pending, ${partialCount} partially fulfilled`
              : 'No pending backorders'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {[
          { value: 'pending', label: 'Pending', count: pendingCount },
          { value: 'partially_fulfilled', label: 'Partial', count: partialCount },
          { value: 'completed', label: 'Completed' },
          { value: 'cancelled', label: 'Cancelled' },
          { value: '', label: 'All' },
        ].map(f => (
          <button key={f.value} onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${filter === f.value ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            data-testid={`filter-${f.value || 'all'}`}>
            {f.label}{f.count !== undefined ? ` (${f.count})` : ''}
          </button>
        ))}
      </div>

      {/* Orders List */}
      {orders.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="empty-state">
          <Package2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No pending orders found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map(order => {
            const cfg = statusConfig[order.status] || statusConfig.pending;
            const StatusIcon = cfg.icon;
            const isActive = order.status === 'pending' || order.status === 'partially_fulfilled';
            const canFulfil = isActive && order.availableStock > 0;
            const expanded = expandedId === order.id;

            return (
              <div key={order.id} className="bg-white rounded-xl border shadow-sm overflow-hidden" data-testid={`order-${order.id}`}>
                <div className="p-4 cursor-pointer" onClick={() => isActive && setExpandedId(expanded ? null : order.id)}>
                  {/* Top row: product + status */}
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <h3 className="font-semibold text-gray-900 truncate" data-testid={`order-product-${order.id}`}>{order.productName}</h3>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${cfg.color}`}>
                        <StatusIcon className="h-3 w-3" /> {cfg.label}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400 flex-shrink-0">{fmtDate(order.createdAt)}</span>
                  </div>

                  {/* Info grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1.5 text-sm">
                    <div><span className="text-gray-500">Buyer:</span> <span className="font-medium" data-testid={`order-buyer-${order.id}`}>{order.buyerName}</span></div>
                    {order.invoiceNumber && (
                      <div><span className="text-gray-500">Ref Invoice:</span> <span className="font-mono text-xs" data-testid={`order-ref-${order.id}`}>{order.invoiceNumber}</span></div>
                    )}
                    <div><span className="text-gray-500">Ordered:</span> <strong data-testid={`order-ordered-${order.id}`}>{order.orderedQty}</strong></div>
                    <div><span className="text-emerald-600">Fulfilled:</span> <strong data-testid={`order-fulfilled-${order.id}`}>{order.fulfilledQty}</strong></div>
                    <div><span className="text-amber-600">Pending:</span> <strong data-testid={`order-pending-${order.id}`}>{order.pendingQty}</strong></div>
                    <div><span className="text-gray-500">Stock:</span> <span data-testid={`order-stock-${order.id}`}>{order.currentStock}</span></div>
                    <div><span className="text-gray-500">Available:</span> <span className={order.availableStock > 0 ? 'text-emerald-600 font-medium' : 'text-red-500 font-medium'} data-testid={`order-available-${order.id}`}>{order.availableStock}</span></div>
                  </div>
                </div>

                {/* Expanded actions */}
                {expanded && isActive && (
                  <div className="flex flex-wrap gap-2 px-4 pb-4 pt-2 border-t">
                    {canFulfil && (
                      <button onClick={(e) => { e.stopPropagation(); setFulfilModal(order); setFulfilQty(String(Math.min(order.pendingQty, order.availableStock))); }}
                        disabled={actionLoading === order.id}
                        className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition"
                        data-testid={`fulfil-btn-${order.id}`}>
                        <CheckCircle2 className="h-4 w-4" /> Fulfil Now
                      </button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); handleCreateInvoice(order); }}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                      data-testid={`create-invoice-btn-${order.id}`}>
                      <FileText className="h-4 w-4" /> Create Invoice
                    </button>
                    {order.buyerPhone && (
                      <button onClick={(e) => { e.stopPropagation(); handleNotify(order.id); }}
                        disabled={actionLoading === order.id}
                        className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
                        data-testid={`notify-btn-${order.id}`}>
                        <Bell className="h-4 w-4" /> Notify Buyer
                      </button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); handleCancel(order.id); }}
                      disabled={actionLoading === order.id}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition"
                      data-testid={`cancel-btn-${order.id}`}>
                      <XCircle className="h-4 w-4" /> Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Fulfil Modal */}
      {fulfilModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="fulfil-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Fulfil Pending Order</h3>
              <button onClick={() => setFulfilModal(null)} className="p-1 text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-600">Product</span><span className="font-medium">{fulfilModal.productName}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Buyer</span><span className="font-medium">{fulfilModal.buyerName}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Pending Qty</span><span className="font-semibold text-amber-600">{fulfilModal.pendingQty}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Available Stock</span><span className="font-semibold text-emerald-600">{fulfilModal.availableStock}</span></div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity to Fulfil</label>
                <input type="number" value={fulfilQty} onChange={e => setFulfilQty(e.target.value)}
                  min={1} max={Math.min(fulfilModal.pendingQty, fulfilModal.availableStock)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500"
                  data-testid="fulfil-qty-input" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setFulfilModal(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
              <button onClick={handleFulfil} disabled={actionLoading === fulfilModal.id}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                data-testid="fulfil-confirm-btn">
                {actionLoading === fulfilModal.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Fulfil
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
