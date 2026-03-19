'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { useNetworkContext } from '@/context/NetworkContext';
import { toast } from 'sonner';
import {
  FileText, Loader2, X, Download, Send,
  CheckCircle2, Package2, Truck, AlertTriangle, ClipboardList
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface POItem {
  listingId: string;
  productName: string;
  sku: string;
  description: string;
  specification: string;
  quantity: number;
  rate: number;
  total: number;
  receivedQuantity?: number;
}

interface PurchaseOrder {
  id: string;
  poNumber: string;
  supplierId: string;
  supplierName: string;
  supplierPhone: string;
  items: POItem[];
  itemCount: number;
  totalAmount: number;
  status: string;
  deliveryNotes?: string;
  createdAt: string;
  receivedAt?: string;
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  sent: 'bg-blue-100 text-blue-700',
  confirmed: 'bg-emerald-100 text-emerald-700',
  partially_received: 'bg-amber-100 text-amber-700',
  received: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-600',
};

const statusLabels: Record<string, string> = {
  draft: 'Draft', sent: 'Sent', confirmed: 'Confirmed',
  partially_received: 'Partially Received', received: 'Received', cancelled: 'Cancelled',
};

export default function PurchaseOrdersPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const { isOnline } = useNetworkContext();
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [statusUpdating, setStatusUpdating] = useState<string | null>(null);
  const [whatsappSending, setWhatsappSending] = useState<string | null>(null);
  const [whatsappConfirm, setWhatsappConfirm] = useState<string | null>(null);

  // WhatsApp phone modal state (for POs without supplier phone)
  const [waPhoneModal, setWaPhoneModal] = useState<PurchaseOrder | null>(null);
  const [waManualPhone, setWaManualPhone] = useState('');

  // GRN modal state
  const [grnModal, setGrnModal] = useState<PurchaseOrder | null>(null);
  const [grnLoading, setGrnLoading] = useState(false);
  const [grnQuantities, setGrnQuantities] = useState<Record<string, number>>({});
  const [grnNotes, setGrnNotes] = useState('');
  const [grnSubmitting, setGrnSubmitting] = useState(false);
  const [grnResult, setGrnResult] = useState<{ status: string; stockUpdates: Array<{ productName: string; previousStock: number; newStock: number; received: number }> } | null>(null);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchPOs = useCallback(async () => {
    try {
      const h = await authHeaders();
      const url = new URL(`${API_URL}/api/business-tools/purchase-orders`);
      if (filter) url.searchParams.set('status', filter);
      const res = await fetch(url.toString(), { headers: h });
      if (res.ok) {
        const data = await res.json();
        setPos(data.purchaseOrders || []);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders, filter]);

  useEffect(() => { fetchPOs(); }, [fetchPOs]);

  const downloadPDF = async (poId: string, poNumber: string) => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${poId}/pdf`, { headers: h });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `${poNumber}.pdf`; a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch { setError('Failed to download PDF'); }
  };

  const sendWhatsApp = async (poId: string) => {
    if (!isOnline) {
      toast.error('Cannot send WhatsApp in offline mode');
      return;
    }
    setWhatsappSending(poId);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${poId}/whatsapp-link`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        if (data.whatsappLink) {
          setWhatsappConfirm(poId);
          setTimeout(() => setWhatsappConfirm(null), 3000);
          window.open(data.whatsappLink, '_blank');
          fetchPOs();
        }
      } else {
        const data = await res.json();
        if (data.detail?.includes('phone')) {
          // Supplier phone missing — show phone input modal
          const po = pos.find(p => p.id === poId);
          if (po) {
            setWaPhoneModal(po);
            setWaManualPhone(po.supplierPhone || '');
          }
        } else {
          setError(data.detail || 'Failed to generate WhatsApp link');
        }
      }
    } catch { setError('Failed to send WhatsApp'); }
    setWhatsappSending(null);
  };

  const handleWhatsAppClick = (po: PurchaseOrder) => {
    if (po.supplierPhone) {
      sendWhatsApp(po.id);
    } else {
      setWaPhoneModal(po);
      setWaManualPhone('');
    }
  };

  const updateStatus = async (poId: string, status: string) => {
    setStatusUpdating(poId);
    try {
      const h = await authHeaders();
      await fetch(`${API_URL}/api/business-tools/purchase-orders/${poId}/status`, {
        method: 'PUT', headers: h, body: JSON.stringify({ status })
      });
      fetchPOs();
    } catch { /* empty */ }
    setStatusUpdating(null);
  };

  const openGrnModal = async (po: PurchaseOrder) => {
    setGrnLoading(true);
    setGrnResult(null);
    setGrnNotes('');
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${po.id}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        const fullPO = data.purchaseOrder as PurchaseOrder;
        setGrnModal(fullPO);
        const initQty: Record<string, number> = {};
        for (const item of fullPO.items) {
          const remaining = item.quantity - (item.receivedQuantity || 0);
          initQty[item.listingId] = Math.max(0, remaining);
        }
        setGrnQuantities(initQty);
      }
    } catch { setError('Failed to load PO details'); }
    setGrnLoading(false);
  };

  const submitGrn = async () => {
    if (!grnModal) return;
    setGrnSubmitting(true);
    try {
      const h = await authHeaders();
      const items = Object.entries(grnQuantities)
        .filter(([, qty]) => qty > 0)
        .map(([listingId, qty]) => ({ listingId, receivedQuantity: qty }));

      if (items.length === 0) { setError('Enter at least one received quantity'); setGrnSubmitting(false); return; }

      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${grnModal.id}/receive`, {
        method: 'POST', headers: h,
        body: JSON.stringify({ items, notes: grnNotes || null })
      });

      if (res.ok) {
        const data = await res.json();
        setGrnResult({ status: data.status, stockUpdates: data.stockUpdates || [] });
        fetchPOs();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to receive goods');
      }
    } catch { setError('Failed to submit GRN'); }
    setGrnSubmitting(false);
  };

  if (!hasPermission('manage_inventory')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Package2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="purchase-orders-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="po-heading">Purchase Orders</h1>
          <p className="text-gray-600 mt-1">Track and manage supplier purchase orders</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {[
          { val: '', label: 'All' },
          { val: 'draft', label: 'Draft' },
          { val: 'sent', label: 'Sent' },
          { val: 'confirmed', label: 'Confirmed' },
          { val: 'partially_received', label: 'Partial' },
          { val: 'received', label: 'Received' },
        ].map(f => (
          <button key={f.val} onClick={() => setFilter(f.val)} data-testid={`po-filter-${f.val || 'all'}`}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${filter === f.val ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto"><X className="h-5 w-5 text-red-600" /></button>
        </div>
      )}

      {/* PO List */}
      {loading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-green-600" /></div>
      ) : pos.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="no-pos">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900">No Purchase Orders</h3>
          <p className="text-sm text-gray-500 mt-1">Purchase orders will appear here when you order materials from the Low Stock Alerts page.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pos.map(po => (
            <div key={po.id} className="bg-white rounded-xl border p-5 hover:shadow-sm transition" data-testid={`po-card-${po.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                    <FileText className="h-5 w-5 text-green-700" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{po.poNumber}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[po.status] || 'bg-gray-100 text-gray-600'}`}>
                        {statusLabels[po.status] || po.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
                      <span className="flex items-center gap-1"><Truck className="h-3.5 w-3.5" />{po.supplierName}</span>
                      <span>{po.itemCount} item{po.itemCount !== 1 ? 's' : ''}</span>
                      <span className="font-medium text-gray-800">₹{po.totalAmount.toLocaleString('en-IN')}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(po.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                  <button onClick={() => downloadPDF(po.id, po.poNumber)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                    data-testid={`po-download-${po.id}`}>
                    <Download className="h-3.5 w-3.5" /> PDF
                  </button>

                  {!['received', 'cancelled'].includes(po.status) && (
                    <button onClick={() => handleWhatsAppClick(po)} disabled={whatsappSending === po.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                      data-testid={`po-whatsapp-${po.id}`}>
                      {whatsappSending === po.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                      {whatsappConfirm === po.id ? 'Opening WhatsApp...' : 'WhatsApp'}
                    </button>
                  )}

                  {po.status === 'sent' && (
                    <button onClick={() => updateStatus(po.id, 'confirmed')} disabled={statusUpdating === po.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition disabled:opacity-50"
                      data-testid={`po-confirm-${po.id}`}>
                      <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                    </button>
                  )}

                  {(po.status === 'confirmed' || po.status === 'partially_received') && (
                    <button onClick={() => openGrnModal(po)} disabled={grnLoading}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
                      data-testid={`po-receive-${po.id}`}>
                      <ClipboardList className="h-3.5 w-3.5" /> Receive Goods
                    </button>
                  )}

                  {(po.status === 'draft' || po.status === 'sent') && (
                    <button onClick={() => updateStatus(po.id, 'cancelled')} disabled={statusUpdating === po.id}
                      className="px-3 py-1.5 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition disabled:opacity-50"
                      data-testid={`po-cancel-${po.id}`}>
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* GRN Modal */}
      {grnModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="grn-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Receive Goods</h2>
                <p className="text-sm text-gray-500">{grnModal.poNumber}</p>
              </div>
              <button onClick={() => { setGrnModal(null); setGrnResult(null); }} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>

            {grnResult ? (
              /* GRN Success */
              <div className="p-6 space-y-4">
                <div className="text-center py-3">
                  <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-gray-900">Goods Received!</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    PO Status: <span className="font-medium capitalize">{grnResult.status.replace('_', ' ')}</span>
                  </p>
                </div>

                {grnResult.stockUpdates.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4" data-testid="grn-stock-updates">
                    <h4 className="text-sm font-medium text-green-800 mb-2">Stock Updated</h4>
                    {grnResult.stockUpdates.map((u, i) => (
                      <div key={i} className="flex items-center justify-between text-sm py-1">
                        <span className="text-gray-700">{u.productName}</span>
                        <span className="text-green-700 font-medium">
                          {u.previousStock} + {u.received} = {u.newStock}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <button onClick={() => { setGrnModal(null); setGrnResult(null); }}
                  className="w-full px-4 py-2 text-sm font-medium bg-gray-900 text-white rounded-lg hover:bg-gray-800">
                  Done
                </button>
              </div>
            ) : (
              /* GRN Form */
              <div className="p-6 space-y-4">
                <div className="space-y-3">
                  {grnModal.items.map((item) => {
                    const alreadyReceived = item.receivedQuantity || 0;
                    const remaining = item.quantity - alreadyReceived;
                    return (
                      <div key={item.listingId} className="bg-gray-50 rounded-lg p-4" data-testid={`grn-item-${item.listingId}`}>
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="font-medium text-gray-900">{item.productName}</p>
                            {item.sku && <p className="text-xs text-gray-500 font-mono">{item.sku}</p>}
                          </div>
                          <span className="text-sm text-gray-500">₹{item.rate.toLocaleString('en-IN')}/unit</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm mb-3">
                          <span>Ordered: <span className="font-semibold">{item.quantity}</span></span>
                          {alreadyReceived > 0 && (
                            <span className="text-green-600">Already Received: <span className="font-semibold">{alreadyReceived}</span></span>
                          )}
                          <span className="text-amber-600">Remaining: <span className="font-semibold">{remaining}</span></span>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">Received Quantity</label>
                          <input
                            type="number"
                            value={grnQuantities[item.listingId] ?? 0}
                            min={0}
                            max={remaining}
                            onChange={(e) => {
                              const val = Math.min(Math.max(0, parseInt(e.target.value) || 0), remaining);
                              setGrnQuantities(prev => ({ ...prev, [item.listingId]: val }));
                            }}
                            className="w-32 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                            data-testid={`grn-qty-${item.listingId}`}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                  <textarea value={grnNotes} onChange={(e) => setGrnNotes(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" rows={2}
                    placeholder="Any notes about the delivery..." data-testid="grn-notes" />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setGrnModal(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                    Cancel
                  </button>
                  <button onClick={submitGrn} disabled={grnSubmitting}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
                    data-testid="grn-submit-btn">
                    {grnSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardList className="h-4 w-4" />}
                    Confirm Receipt
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {/* WhatsApp Phone Input Modal */}
      {waPhoneModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="wa-phone-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Send via WhatsApp</h3>
              <button onClick={() => setWaPhoneModal(null)} className="p-1 text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-1">PO: <span className="font-medium">{waPhoneModal.poNumber}</span></p>
            <p className="text-sm text-gray-600 mb-4">Supplier: <span className="font-medium">{waPhoneModal.supplierName}</span></p>
            <label className="block text-sm font-medium text-gray-700 mb-1">Supplier Phone</label>
            <input
              type="tel"
              value={waManualPhone}
              onChange={(e) => setWaManualPhone(e.target.value)}
              placeholder="+91XXXXXXXXXX"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 mb-4"
              data-testid="wa-phone-input"
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => setWaPhoneModal(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!waManualPhone.trim()) { setError('Please enter a phone number'); return; }
                  // Update supplier phone first, then send
                  try {
                    const h = await authHeaders();
                    await fetch(`${API_URL}/api/business-tools/suppliers/${waPhoneModal.supplierId}`, {
                      method: 'PUT', headers: h,
                      body: JSON.stringify({ phone: waManualPhone.trim() })
                    });
                  } catch { /* continue even if update fails */ }
                  setWaPhoneModal(null);
                  sendWhatsApp(waPhoneModal.id);
                }}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition"
                data-testid="wa-send-btn"
              >
                <Send className="h-4 w-4" /> Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
