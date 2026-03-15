'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  FileText, Loader2, X, Download, ExternalLink, Send,
  CheckCircle2, Clock, Package2, Truck, AlertTriangle
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface PurchaseOrder {
  id: string;
  poNumber: string;
  supplierName: string;
  supplierPhone: string;
  itemCount: number;
  totalAmount: number;
  status: string;
  createdAt: string;
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  sent: 'bg-blue-100 text-blue-700',
  confirmed: 'bg-emerald-100 text-emerald-700',
  received: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-600',
};

const statusLabels: Record<string, string> = {
  draft: 'Draft', sent: 'Sent', confirmed: 'Confirmed',
  received: 'Received', cancelled: 'Cancelled',
};

export default function PurchaseOrdersPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [statusUpdating, setStatusUpdating] = useState<string | null>(null);

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
        const a = document.createElement('a');
        a.href = url;
        a.download = `${poNumber}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch { setError('Failed to download PDF'); }
  };

  const sendWhatsApp = async (poId: string) => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${poId}/whatsapp-link`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        if (data.whatsappLink) {
          window.open(data.whatsappLink, '_blank');
          fetchPOs(); // Refresh to show updated status
        }
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to generate WhatsApp link');
      }
    } catch { setError('Failed to send WhatsApp'); }
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

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Download PDF */}
                  <button onClick={() => downloadPDF(po.id, po.poNumber)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                    data-testid={`po-download-${po.id}`}>
                    <Download className="h-3.5 w-3.5" /> PDF
                  </button>

                  {/* Send WhatsApp */}
                  {po.supplierPhone && (
                    <button onClick={() => sendWhatsApp(po.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 transition"
                      data-testid={`po-whatsapp-${po.id}`}>
                      <Send className="h-3.5 w-3.5" /> WhatsApp
                    </button>
                  )}

                  {/* Status Actions */}
                  {po.status === 'sent' && (
                    <button onClick={() => updateStatus(po.id, 'confirmed')} disabled={statusUpdating === po.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition disabled:opacity-50"
                      data-testid={`po-confirm-${po.id}`}>
                      <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                    </button>
                  )}
                  {po.status === 'confirmed' && (
                    <button onClick={() => updateStatus(po.id, 'received')} disabled={statusUpdating === po.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 rounded-lg hover:bg-green-100 transition disabled:opacity-50"
                      data-testid={`po-received-${po.id}`}>
                      <Package2 className="h-3.5 w-3.5" /> Received
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
    </div>
  );
}
