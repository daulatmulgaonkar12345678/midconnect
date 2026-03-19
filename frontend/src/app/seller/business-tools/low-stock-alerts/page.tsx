'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { useNetworkContext } from '@/context/NetworkContext';
import { toast } from 'sonner';
import {
  AlertTriangle, Loader2, X, Package2, Phone, Download,
  CheckCircle2, XCircle, ShoppingCart, Send
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface LowStockAlert {
  id: string;
  listingId: string;
  productName: string;
  sku: string;
  description: string;
  specification: string;
  currentStock: number;
  minStock: number;
  status: string;
  createdAt: string;
  sellerName?: string;
}

interface SupplierOption {
  supplierId: string;
  supplierName: string;
  phone: string;
  rate: number;
}

interface OrderDetails {
  product: {
    productName: string;
    sku: string;
    description: string;
    specification: string;
    currentStock: number;
    minStock: number;
  };
  suppliers: SupplierOption[];
  sellerProfile: { businessName: string; phone: string; };
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function LowStockAlertsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission, isAdmin } = usePermissions();
  const { isOnline } = useNetworkContext();
  const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [filter, setFilter] = useState<string>('pending');
  const [error, setError] = useState<string | null>(null);
  const [isAdminView, setIsAdminView] = useState(false);

  // Order modal state
  const [orderModal, setOrderModal] = useState<LowStockAlert | null>(null);
  const [orderDetails, setOrderDetails] = useState<OrderDetails | null>(null);
  const [orderLoading, setOrderLoading] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<string>('');
  const [orderQuantity, setOrderQuantity] = useState<number>(0);
  const [deliveryNotes, setDeliveryNotes] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [createdPO, setCreatedPO] = useState<{ id: string; poNumber: string } | null>(null);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchAlerts = useCallback(async () => {
    try {
      const h = await authHeaders();
      const url = new URL(`${API_URL}/api/business-tools/low-stock-alerts`);
      if (filter) url.searchParams.set('status', filter);
      const res = await fetch(url.toString(), { headers: h });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
        setPendingCount(data.pendingCount || 0);
        setIsAdminView(data.isAdminView || false);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders, filter]);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const openOrderModal = async (alert: LowStockAlert) => {
    setOrderModal(alert);
    setOrderLoading(true);
    setOrderDetails(null);
    setSelectedSupplier('');
    setOrderQuantity(0);
    setDeliveryNotes('');
    setCreatedPO(null);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/low-stock-alerts/${alert.id}/order-details`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setOrderDetails(data);
        setOrderQuantity(Math.max(1, data.product.minStock - data.product.currentStock));
      }
    } catch { /* empty */ }
    setOrderLoading(false);
  };

  const updateAlertStatus = async (alertId: string, status: 'ordered' | 'ignored') => {
    setActionLoading(alertId);
    try {
      const h = await authHeaders();
      await fetch(`${API_URL}/api/business-tools/low-stock-alerts/${alertId}/status`, {
        method: 'PUT', headers: h, body: JSON.stringify({ status })
      });
      fetchAlerts();
      if (orderModal?.id === alertId) setOrderModal(null);
    } catch { /* empty */ }
    setActionLoading(null);
  };

  const createPurchaseOrder = async () => {
    if (!orderDetails || !selectedSupplier || !orderQuantity || !orderModal) return;
    setActionLoading('creating-po');
    try {
      const h = await authHeaders();
      const supplier = orderDetails.suppliers.find(s => s.supplierId === selectedSupplier);
      const { product } = orderDetails;

      const body = {
        supplierId: selectedSupplier,
        alertId: orderModal.id,
        deliveryNotes: deliveryNotes || null,
        items: [{
          listingId: orderModal.listingId,
          productName: product.productName,
          sku: product.sku,
          description: product.description,
          specification: product.specification,
          quantity: orderQuantity,
          rate: supplier?.rate || 0,
        }]
      };

      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders`, {
        method: 'POST', headers: h, body: JSON.stringify(body)
      });

      if (res.ok) {
        const data = await res.json();
        const po = data.purchaseOrder;
        setCreatedPO({ id: po.id, poNumber: po.poNumber });
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create PO');
      }
    } catch { setError('Failed to create purchase order'); }
    setActionLoading(null);
  };

  const downloadPOPdf = async () => {
    if (!createdPO) return;
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${createdPO.id}/pdf`, { headers: h });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `${createdPO.poNumber}.pdf`;
        a.click(); window.URL.revokeObjectURL(url);
      }
    } catch { setError('Failed to download PDF'); }
  };

  const sendPOWhatsApp = async () => {
    if (!createdPO) return;
    if (!isOnline) {
      toast.error('Cannot send WhatsApp in offline mode');
      return;
    }
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/purchase-orders/${createdPO.id}/whatsapp-link`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        if (data.whatsappLink) window.open(data.whatsappLink, '_blank');
        setOrderModal(null);
        fetchAlerts();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to generate WhatsApp link');
      }
    } catch { setError('Failed to send WhatsApp'); }
  };

  if (!hasPermission('manage_inventory')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Package2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
      </div>
    );
  }

  const selectedSupplierData = orderDetails?.suppliers.find(s => s.supplierId === selectedSupplier);
  const bestPrice = orderDetails?.suppliers[0]?.rate;

  return (
    <div className="space-y-6" data-testid="low-stock-alerts-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="alerts-heading">Low Stock Alerts</h1>
          <p className="text-gray-600 mt-1">
            {isAdminView && <span className="inline-block bg-indigo-100 text-indigo-700 text-xs font-medium px-2 py-0.5 rounded-full mr-2" data-testid="admin-badge">Admin View</span>}
            {pendingCount > 0 ? `${pendingCount} items need attention` : 'All stock levels healthy'}
          </p>
        </div>
        <div className="flex gap-2">
          {(['pending', 'ordered', 'ignored'] as const).map(s => (
            <button key={s} onClick={() => setFilter(s)} data-testid={`filter-${s}`}
              className={`px-3 py-1.5 text-sm rounded-lg capitalize transition ${filter === s ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto"><X className="h-5 w-5 text-red-600" /></button>
        </div>
      )}

      {/* Alerts List */}
      {loading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-orange-500" /></div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="no-alerts">
          <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900">
            {filter === 'pending' ? 'No pending alerts' : `No ${filter} alerts`}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {filter === 'pending' ? 'All products are above minimum stock levels.' : 'Nothing here yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map(alert => (
            <div key={alert.id} className={`bg-white rounded-xl border p-5 transition ${alert.status === 'pending' ? 'border-orange-200 shadow-sm' : 'border-gray-100'}`}
              data-testid={`alert-card-${alert.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${alert.status === 'pending' ? 'bg-orange-100' : alert.status === 'ordered' ? 'bg-green-100' : 'bg-gray-100'}`}>
                    {alert.status === 'ordered' ? <CheckCircle2 className="h-5 w-5 text-green-600" /> : alert.status === 'ignored' ? <XCircle className="h-5 w-5 text-gray-400" /> : <AlertTriangle className="h-5 w-5 text-orange-600" />}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{alert.productName}</h3>
                    {alert.sku && <p className="text-xs text-gray-500 font-mono mt-0.5">{alert.sku}</p>}
                    {isAdminView && alert.sellerName && (
                      <p className="text-xs text-indigo-600 font-medium mt-0.5" data-testid={`seller-name-${alert.id}`}>
                        Seller: {alert.sellerName}
                      </p>
                    )}
                    <div className="flex items-center gap-4 mt-2">
                      <span className="text-sm">Current Stock: <span className="font-semibold text-red-600">{alert.currentStock}</span></span>
                      <span className="text-sm">Min Stock: <span className="font-semibold text-gray-700">{alert.minStock}</span></span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{timeAgo(alert.createdAt)}</p>
                  </div>
                </div>

                {alert.status === 'pending' && !isAdminView && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={() => openOrderModal(alert)} disabled={actionLoading === alert.id}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition"
                      data-testid={`order-btn-${alert.id}`}>
                      <ShoppingCart className="h-4 w-4" /> Order Material
                    </button>
                    <button onClick={() => updateAlertStatus(alert.id, 'ignored')} disabled={actionLoading === alert.id}
                      className="px-3 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition"
                      data-testid={`ignore-btn-${alert.id}`}>
                      Ignore
                    </button>
                  </div>
                )}

                {alert.status === 'pending' && isAdminView && (
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full capitalize bg-orange-100 text-orange-700" data-testid={`pending-badge-${alert.id}`}>
                    pending
                  </span>
                )}

                {alert.status !== 'pending' && (
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full capitalize ${alert.status === 'ordered' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {alert.status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Order Material Modal */}
      {orderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="order-material-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-semibold text-gray-900">
                {createdPO ? `PO Created: ${createdPO.poNumber}` : 'Order Material'}
              </h2>
              <button onClick={() => { setOrderModal(null); if (createdPO) fetchAlerts(); }} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>

            {orderLoading ? (
              <div className="flex items-center justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-orange-500" /></div>
            ) : createdPO ? (
              /* PO Created Success State */
              <div className="p-6 space-y-5">
                <div className="text-center py-4">
                  <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-gray-900">Purchase Order Created!</h3>
                  <p className="text-sm text-gray-500 mt-1">{createdPO.poNumber}</p>
                </div>
                <div className="flex flex-col gap-3">
                  <button onClick={downloadPOPdf}
                    className="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                    data-testid="download-po-pdf-btn">
                    <Download className="h-4 w-4" /> Download PO PDF
                  </button>
                  <button onClick={sendPOWhatsApp}
                    className="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                    data-testid="send-po-whatsapp-btn">
                    <Send className="h-4 w-4" /> Send via WhatsApp
                  </button>
                </div>
              </div>
            ) : orderDetails ? (
              /* Order Form */
              <div className="p-6 space-y-5">
                {/* Product Info */}
                <div className="bg-gray-50 rounded-lg p-4 space-y-2" data-testid="order-product-info">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-gray-500">Product Name</span><p className="font-medium text-gray-900">{orderDetails.product.productName}</p></div>
                    <div><span className="text-gray-500">SKU</span><p className="font-medium text-gray-900 font-mono">{orderDetails.product.sku || '-'}</p></div>
                  </div>
                  {orderDetails.product.specification && (
                    <div className="text-sm"><span className="text-gray-500">Specification</span><p className="text-gray-800 whitespace-pre-line mt-0.5">{orderDetails.product.specification}</p></div>
                  )}
                  {orderDetails.product.description && (
                    <div className="text-sm"><span className="text-gray-500">Description</span><p className="text-gray-700 mt-0.5">{orderDetails.product.description}</p></div>
                  )}
                  <div className="flex gap-4 text-sm pt-1">
                    <span>Current Stock: <span className="font-semibold text-red-600">{orderDetails.product.currentStock}</span></span>
                  </div>
                </div>

                {/* Supplier Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Select Supplier</label>
                  {orderDetails.suppliers.length === 0 ? (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700" data-testid="no-suppliers-warning">
                      <AlertTriangle className="h-4 w-4 inline mr-1" />
                      No suppliers mapped to this product. Go to Suppliers page to add product mappings.
                    </div>
                  ) : (
                    <div className="space-y-2" data-testid="supplier-options">
                      {orderDetails.suppliers.map((s) => (
                        <label key={s.supplierId}
                          className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition ${selectedSupplier === s.supplierId ? 'border-orange-500 bg-orange-50' : 'border-gray-200 hover:border-gray-300'}`}
                          data-testid={`supplier-option-${s.supplierId}`}>
                          <div className="flex items-center gap-3">
                            <input type="radio" name="supplier" value={s.supplierId} checked={selectedSupplier === s.supplierId}
                              onChange={() => setSelectedSupplier(s.supplierId)} className="h-4 w-4 text-orange-600 focus:ring-orange-500" />
                            <div>
                              <p className="text-sm font-medium text-gray-900">{s.supplierName}</p>
                              {s.phone && <p className="text-xs text-gray-500 flex items-center gap-1"><Phone className="h-3 w-3" />{s.phone}</p>}
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-semibold text-gray-800">₹{s.rate.toLocaleString('en-IN')}</p>
                            {s.rate === bestPrice && orderDetails.suppliers.length > 1 && (
                              <span className="text-[10px] font-medium text-green-600 bg-green-100 px-1.5 py-0.5 rounded-full">Best Price</span>
                            )}
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Order Quantity */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Order Quantity</label>
                  <input type="number" value={orderQuantity} min={1}
                    onChange={(e) => setOrderQuantity(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                    data-testid="order-quantity-input" />
                  {selectedSupplierData && orderQuantity > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      Estimated cost: <span className="font-medium">₹{(selectedSupplierData.rate * orderQuantity).toLocaleString('en-IN')}</span>
                    </p>
                  )}
                </div>

                {/* Delivery Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Delivery Notes (optional)</label>
                  <textarea value={deliveryNotes} onChange={(e) => setDeliveryNotes(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500" rows={2}
                    placeholder="Delivery instructions..." data-testid="delivery-notes-input" />
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setOrderModal(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                    Cancel
                  </button>
                  <button onClick={createPurchaseOrder}
                    disabled={!selectedSupplier || !orderQuantity || actionLoading === 'creating-po'}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    data-testid="create-po-btn">
                    {actionLoading === 'creating-po' ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShoppingCart className="h-4 w-4" />}
                    Create Purchase Order
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">Failed to load order details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
