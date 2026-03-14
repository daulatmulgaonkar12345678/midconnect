'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  FileText, Plus, X, Download, Eye, Trash2, Send, CreditCard,
  IndianRupee, ChevronDown, ChevronUp, Clock, CheckCircle2,
  AlertCircle, Banknote, Calendar
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ── Types ──

interface Spec { key: string; value: string; }

interface InvoiceListing {
  id: string;
  productName: string;
  productType: string;
  stock: number;
  price: number;
  specifications: Spec[];
}

interface InvoiceFormItem {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
  gstPercent: number;
  allSpecs: Spec[];
  selectedSpecs: Spec[];
  customSpecs: Spec[];
  showSpecs: boolean;
}

interface Buyer { id: string; buyerName: string; company?: string; phone?: string; }
interface InvoiceItem { productName: string; quantity: number; price: number; gstPercent: number; gstAmount: number; total: number; selected_specifications?: Spec[]; }
interface PaymentEntry {
  id: string;
  amount: number;
  paymentDate: string;
  paymentMethod: string;
  accountName?: string;
  referenceNumber?: string;
  notes?: string;
  createdAt: string;
}
interface Invoice {
  id: string;
  invoiceNumber: string;
  buyerName: string;
  buyerPhone?: string;
  date: string;
  items: InvoiceItem[];
  subtotal: number;
  gst: number;
  total: number;
  totalPaid: number;
  pendingAmount: number;
  status: string;
  notes?: string;
  payments?: PaymentEntry[];
  buyerDetails?: Record<string, string>;
}

// ── Constants ──

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-cyan-100 text-cyan-700',
  partially_paid: 'bg-amber-100 text-amber-700',
  paid: 'bg-emerald-100 text-emerald-700',
  overdue: 'bg-red-100 text-red-700',
  cancelled: 'bg-red-50 text-red-500',
};

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  sent: 'Sent',
  viewed: 'Viewed',
  partially_paid: 'Partially Paid',
  paid: 'Paid',
  overdue: 'Overdue',
  cancelled: 'Cancelled',
};

const paymentMethods = [
  { value: 'upi', label: 'UPI' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'other', label: 'Other' },
];

function emptyItem(): InvoiceFormItem {
  return { productId: '', productName: '', quantity: 1, price: 0, gstPercent: 18, allSpecs: [], selectedSpecs: [], customSpecs: [], showSpecs: false };
}

function calcLine(qty: number, price: number, gst: number) {
  const sub = qty * price;
  const gstAmt = Math.round(sub * gst / 100 * 100) / 100;
  return { subtotal: sub, gstAmount: gstAmt, total: Math.round((sub + gstAmt) * 100) / 100 };
}

function formatCurrency(n: number) {
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr: string) {
  try { return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return dateStr; }
}

// ── Main Component ──

export default function InvoicesPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [listings, setListings] = useState<InvoiceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [viewInvoice, setViewInvoice] = useState<Invoice | null>(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentInvoiceId, setPaymentInvoiceId] = useState('');
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    paymentDate: new Date().toISOString().slice(0, 10),
    paymentMethod: 'upi',
    accountName: '',
    referenceNumber: '',
    notes: '',
  });

  const [formData, setFormData] = useState<{ buyerId: string; items: InvoiceFormItem[]; notes: string; deductStock: boolean }>({
    buyerId: '', items: [emptyItem()], notes: '', deductStock: true,
  });

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchAll = useCallback(async () => {
    try {
      const h = await authHeaders();
      const [invR, buyR, listR] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/invoices`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/buyers`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/invoice-products`, { headers: h }),
      ]);
      if (invR.ok) setInvoices((await invR.json()).invoices || []);
      if (buyR.ok) setBuyers((await buyR.json()).buyers || []);
      if (listR.ok) setListings((await listR.json()).products || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Fetch single invoice with payments ──
  const fetchInvoiceDetail = useCallback(async (invoiceId: string) => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${invoiceId}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setViewInvoice(data.invoice);
      }
    } catch { /* empty */ }
  }, [authHeaders]);

  const openInvoiceDetail = (inv: Invoice) => {
    setViewInvoice(inv);
    fetchInvoiceDetail(inv.id);
  };

  // ── Invoice form handlers ──
  const onProductSelect = (idx: number, listingId: string) => {
    const listing = listings.find(l => l.id === listingId);
    const items = [...formData.items];
    items[idx] = {
      ...items[idx],
      productId: listingId,
      productName: listing?.productName || '',
      price: listing?.price || items[idx].price,
      allSpecs: listing?.specifications || [],
      selectedSpecs: [...(listing?.specifications || [])],
      customSpecs: [],
      showSpecs: (listing?.specifications?.length || 0) > 0,
    };
    setFormData(p => ({ ...p, items }));
  };

  const toggleSpec = (itemIdx: number, specIdx: number) => {
    const items = [...formData.items];
    const item = { ...items[itemIdx] };
    const spec = item.allSpecs[specIdx];
    const isSelected = item.selectedSpecs.some(s => s.key === spec.key && s.value === spec.value);
    item.selectedSpecs = isSelected
      ? item.selectedSpecs.filter(s => !(s.key === spec.key && s.value === spec.value))
      : [...item.selectedSpecs, spec];
    items[itemIdx] = item;
    setFormData(p => ({ ...p, items }));
  };

  const addCustomSpec = (itemIdx: number) => {
    const items = [...formData.items];
    items[itemIdx] = { ...items[itemIdx], customSpecs: [...items[itemIdx].customSpecs, { key: '', value: '' }] };
    setFormData(p => ({ ...p, items }));
  };

  const updateCustomSpec = (itemIdx: number, specIdx: number, field: 'key' | 'value', val: string) => {
    const items = [...formData.items];
    const cs = [...items[itemIdx].customSpecs];
    cs[specIdx] = { ...cs[specIdx], [field]: val };
    items[itemIdx] = { ...items[itemIdx], customSpecs: cs };
    setFormData(p => ({ ...p, items }));
  };

  const removeCustomSpec = (itemIdx: number, specIdx: number) => {
    const items = [...formData.items];
    items[itemIdx] = { ...items[itemIdx], customSpecs: items[itemIdx].customSpecs.filter((_, i) => i !== specIdx) };
    setFormData(p => ({ ...p, items }));
  };

  const addItem = () => setFormData(p => ({ ...p, items: [...p.items, emptyItem()] }));
  const removeItem = (idx: number) => setFormData(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));

  const formTotals = formData.items.reduce((acc, it) => {
    const l = calcLine(it.quantity, it.price, it.gstPercent);
    return { subtotal: acc.subtotal + l.subtotal, gst: acc.gst + l.gstAmount, total: acc.total + l.total };
  }, { subtotal: 0, gst: 0, total: 0 });

  const handleSubmit = async () => {
    if (!formData.buyerId) { alert('Select a buyer'); return; }
    if (formData.items.some(i => !i.productName && !i.productId)) { alert('All items need a product'); return; }
    const h = await authHeaders();
    const payload = {
      buyerId: formData.buyerId,
      items: formData.items.map(i => ({
        productId: i.productId || null,
        productName: i.productName || null,
        quantity: i.quantity,
        price: i.price,
        gstPercent: i.gstPercent,
        selected_specifications: [...i.selectedSpecs, ...i.customSpecs.filter(s => s.key && s.value)],
      })),
      notes: formData.notes,
      deductStock: formData.deductStock,
    };
    const res = await fetch(`${API_URL}/api/business-tools/invoices`, { method: 'POST', headers: h, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'Failed to create invoice'); return; }
    setShowForm(false);
    setFormData({ buyerId: '', items: [emptyItem()], notes: '', deductStock: true });
    fetchAll();
  };

  const updateStatus = async (id: string, status: string) => {
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/invoices/${id}/status`, { method: 'PUT', headers: h, body: JSON.stringify({ status }) });
    fetchAll();
    if (viewInvoice?.id === id) fetchInvoiceDetail(id);
  };

  const deleteInvoice = async (id: string) => {
    if (!confirm('Delete this invoice?')) return;
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/invoices/${id}`, { method: 'DELETE', headers: h });
    if (viewInvoice?.id === id) setViewInvoice(null);
    fetchAll();
  };

  const downloadPdf = async (id: string, num: string) => {
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/invoices/${id}/pdf`, { headers: h });
    if (!res.ok) { alert('Failed to download'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${num}.pdf`; a.click(); URL.revokeObjectURL(url);
  };

  // ── Payment handlers ──
  const openPaymentModal = (invoiceId: string) => {
    setPaymentInvoiceId(invoiceId);
    setPaymentForm({
      amount: '',
      paymentDate: new Date().toISOString().slice(0, 10),
      paymentMethod: 'upi',
      accountName: '',
      referenceNumber: '',
      notes: '',
    });
    setShowPaymentModal(true);
  };

  const submitPayment = async () => {
    const amount = parseFloat(paymentForm.amount);
    if (!amount || amount <= 0) { alert('Enter a valid payment amount'); return; }
    setPaymentLoading(true);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${paymentInvoiceId}/payments`, {
        method: 'POST',
        headers: h,
        body: JSON.stringify({
          amount,
          paymentDate: paymentForm.paymentDate,
          paymentMethod: paymentForm.paymentMethod,
          accountName: paymentForm.accountName || null,
          referenceNumber: paymentForm.referenceNumber || null,
          notes: paymentForm.notes || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) { alert(data.detail || 'Failed to add payment'); return; }
      setShowPaymentModal(false);
      fetchAll();
      if (viewInvoice?.id === paymentInvoiceId) fetchInvoiceDetail(paymentInvoiceId);
    } catch { alert('Error adding payment'); }
    finally { setPaymentLoading(false); }
  };

  const deletePayment = async (invoiceId: string, paymentId: string) => {
    if (!confirm('Delete this payment entry?')) return;
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/invoices/${invoiceId}/payments/${paymentId}`, { method: 'DELETE', headers: h });
    if (!res.ok) { alert('Failed to delete payment'); return; }
    fetchAll();
    if (viewInvoice?.id === invoiceId) fetchInvoiceDetail(invoiceId);
  };

  const filteredInvoices = statusFilter === 'all' ? invoices : invoices.filter(i => i.status === statusFilter);

  if (!hasPermission('create_invoice')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border" data-testid="no-permission">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500">No permission to manage invoices.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="invoices-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Create invoices, track payments, and manage billing</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 text-sm font-medium" data-testid="create-invoice-btn">
          <Plus className="w-4 h-4" /> New Invoice
        </button>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'draft', 'sent', 'partially_paid', 'paid', 'overdue', 'cancelled'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${statusFilter === s ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'}`}
            data-testid={`filter-${s}`}>{statusLabels[s] || 'All'}</button>
        ))}
      </div>

      {/* ──── Create Invoice Modal ──── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-form-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Invoice</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              {/* Buyer */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Buyer *</label>
                <select value={formData.buyerId} onChange={e => setFormData(p => ({ ...p, buyerId: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="buyer-select">
                  <option value="">Select buyer</option>
                  {buyers.map(b => <option key={b.id} value={b.id}>{b.buyerName}{b.company ? ` (${b.company})` : ''}</option>)}
                </select>
              </div>

              {/* Items */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Items *</label>
                <div className="space-y-3">
                  {formData.items.map((item, idx) => {
                    const lineTotal = calcLine(item.quantity, item.price, item.gstPercent);
                    const allFinalSpecs = [...item.selectedSpecs, ...item.customSpecs.filter(s => s.key && s.value)];
                    return (
                      <div key={idx} className="bg-gray-50 rounded-lg p-3 space-y-2" data-testid={`invoice-item-${idx}`}>
                        <div className="grid grid-cols-12 gap-2 items-start">
                          <div className="col-span-4">
                            <label className="text-xs text-gray-500 mb-1 block">Product</label>
                            <select value={item.productId} onChange={e => onProductSelect(idx, e.target.value)}
                              className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-product-${idx}`}>
                              <option value="">Select / Manual</option>
                              {listings.map(l => <option key={l.id} value={l.id}>{l.productName} (Stock: {l.stock})</option>)}
                            </select>
                            {item.productId && item.allSpecs.length > 0 && (
                              <p className="text-[10px] text-gray-400 mt-0.5 truncate">{item.allSpecs.map(s => `${s.key}: ${s.value}`).join(' | ')}</p>
                            )}
                            {!item.productId && (
                              <input type="text" value={item.productName} onChange={e => {
                                const items = [...formData.items]; items[idx] = { ...items[idx], productName: e.target.value };
                                setFormData(p => ({ ...p, items }));
                              }} placeholder="Manual entry" className="w-full mt-1 px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-name-${idx}`} />
                            )}
                          </div>
                          <div className="col-span-1">
                            <label className="text-xs text-gray-500 mb-1 block">Qty</label>
                            <input type="number" min={1} value={item.quantity} onChange={e => {
                              const items = [...formData.items]; items[idx] = { ...items[idx], quantity: parseInt(e.target.value) || 1 };
                              setFormData(p => ({ ...p, items }));
                            }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm text-center" data-testid={`invoice-item-qty-${idx}`} />
                          </div>
                          <div className="col-span-2">
                            <label className="text-xs text-gray-500 mb-1 block">Price</label>
                            <input type="number" min={0} step={0.01} value={item.price} onChange={e => {
                              const items = [...formData.items]; items[idx] = { ...items[idx], price: parseFloat(e.target.value) || 0 };
                              setFormData(p => ({ ...p, items }));
                            }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-price-${idx}`} />
                          </div>
                          <div className="col-span-2">
                            <label className="text-xs text-gray-500 mb-1 block">GST %</label>
                            <select value={item.gstPercent} onChange={e => {
                              const items = [...formData.items]; items[idx] = { ...items[idx], gstPercent: parseFloat(e.target.value) };
                              setFormData(p => ({ ...p, items }));
                            }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-gst-${idx}`}>
                              {[0, 5, 12, 18, 28].map(g => <option key={g} value={g}>{g}%</option>)}
                            </select>
                          </div>
                          <div className="col-span-2">
                            <label className="text-xs text-gray-500 mb-1 block">Total</label>
                            <div className="px-2 py-1.5 bg-white border border-gray-200 rounded text-sm font-medium text-right">{formatCurrency(lineTotal.total)}</div>
                            <div className="text-[10px] text-gray-400 text-right mt-0.5">GST: {formatCurrency(lineTotal.gstAmount)}</div>
                          </div>
                          <div className="col-span-1 pt-5 flex gap-1">
                            {(item.allSpecs.length > 0 || item.customSpecs.length > 0) && (
                              <button onClick={() => {
                                const items = [...formData.items]; items[idx] = { ...items[idx], showSpecs: !items[idx].showSpecs };
                                setFormData(p => ({ ...p, items }));
                              }} className="text-indigo-400 hover:text-indigo-600" title="Toggle specs">
                                {item.showSpecs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                              </button>
                            )}
                            {formData.items.length > 1 && (
                              <button onClick={() => removeItem(idx)} className="text-red-400 hover:text-red-600" data-testid={`remove-invoice-item-${idx}`}>
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                        {allFinalSpecs.length > 0 && !item.showSpecs && (
                          <p className="text-xs text-gray-500 ml-1">{allFinalSpecs.map(s => `${s.key}: ${s.value}`).join(' | ')}</p>
                        )}
                        {item.showSpecs && (
                          <div className="border border-gray-200 rounded-lg p-3 bg-white space-y-2" data-testid={`spec-selector-${idx}`}>
                            <p className="text-xs font-medium text-gray-600">Specifications (select to include in invoice)</p>
                            {item.allSpecs.length > 0 && (
                              <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                                {item.allSpecs.map((spec, si) => {
                                  const isChecked = item.selectedSpecs.some(s => s.key === spec.key && s.value === spec.value);
                                  return (
                                    <label key={si} className={`flex items-center gap-1.5 px-2 py-1 rounded border text-xs cursor-pointer transition ${isChecked ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : 'bg-gray-50 border-gray-200 text-gray-500'}`}>
                                      <input type="checkbox" checked={isChecked} onChange={() => toggleSpec(idx, si)} className="rounded w-3 h-3" />
                                      <span className="font-medium">{spec.key}:</span> {spec.value}
                                    </label>
                                  );
                                })}
                              </div>
                            )}
                            {item.customSpecs.map((cs, ci) => (
                              <div key={ci} className="flex items-center gap-2">
                                <input type="text" value={cs.key} onChange={e => updateCustomSpec(idx, ci, 'key', e.target.value)}
                                  className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="Key (e.g. Warranty)" />
                                <input type="text" value={cs.value} onChange={e => updateCustomSpec(idx, ci, 'value', e.target.value)}
                                  className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="Value (e.g. 2 Years)" />
                                <button onClick={() => removeCustomSpec(idx, ci)} className="text-red-400 hover:text-red-600"><X className="w-3.5 h-3.5" /></button>
                              </div>
                            ))}
                            <button onClick={() => addCustomSpec(idx)} className="text-xs text-indigo-600 hover:text-indigo-700 font-medium" data-testid={`add-custom-spec-${idx}`}>
                              + Add custom specification
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2" data-testid="add-invoice-item-btn">+ Add Item</button>
              </div>

              {/* Totals */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{formatCurrency(formTotals.subtotal)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{formatCurrency(formTotals.gst)}</span></div>
                <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-2">
                  <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{formatCurrency(formTotals.total)}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="deductStock" checked={formData.deductStock}
                  onChange={e => setFormData(p => ({ ...p, deductStock: e.target.checked }))} className="rounded" data-testid="deduct-stock-checkbox" />
                <label htmlFor="deductStock" className="text-sm text-gray-700">Deduct stock from inventory</label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} data-testid="invoice-notes" />
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-invoice-btn">Cancel</button>
              <button onClick={handleSubmit} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium" data-testid="submit-invoice-btn">Create Invoice</button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Invoice Detail Modal ──── */}
      {viewInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-detail-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-lg font-semibold">{viewInvoice.invoiceNumber}</h2>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusColors[viewInvoice.status] || 'bg-gray-100 text-gray-700'}`}>
                  {statusLabels[viewInvoice.status] || viewInvoice.status}
                </span>
              </div>
              <button onClick={() => setViewInvoice(null)} className="text-gray-400 hover:text-gray-600" data-testid="close-invoice-detail"><X className="w-5 h-5" /></button>
            </div>

            {/* Invoice Info */}
            <div className="grid grid-cols-2 gap-4 mb-5 text-sm">
              <div><span className="text-gray-500">Buyer:</span> <span className="font-medium">{viewInvoice.buyerName}</span></div>
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{formatDate(viewInvoice.date)}</span></div>
            </div>

            {/* Items Table */}
            <table className="w-full text-sm mb-4">
              <thead><tr className="border-b border-gray-200 text-gray-500 text-xs uppercase">
                <th className="text-left py-2">Product</th><th className="text-right py-2">Qty</th><th className="text-right py-2">Price</th>
                <th className="text-right py-2">GST%</th><th className="text-right py-2">GST</th><th className="text-right py-2">Total</th>
              </tr></thead>
              <tbody>
                {viewInvoice.items.map((item, i) => (
                  <tr key={i} className="border-b border-gray-50">
                    <td className="py-2">
                      <div>{item.productName}</div>
                      {item.selected_specifications && item.selected_specifications.length > 0 && (
                        <div className="text-[10px] text-gray-400 mt-0.5">{item.selected_specifications.map(s => `${s.key}: ${s.value}`).join(' | ')}</div>
                      )}
                    </td>
                    <td className="py-2 text-right">{item.quantity}</td>
                    <td className="py-2 text-right">{formatCurrency(item.price)}</td>
                    <td className="py-2 text-right">{item.gstPercent}%</td>
                    <td className="py-2 text-right">{formatCurrency(item.gstAmount)}</td>
                    <td className="py-2 text-right font-medium">{formatCurrency(item.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Payment Summary */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm mb-5" data-testid="payment-summary">
              <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{formatCurrency(viewInvoice.subtotal)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{formatCurrency(viewInvoice.gst)}</span></div>
              <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-1">
                <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{formatCurrency(viewInvoice.total)}</span>
              </div>
              <div className="flex justify-between text-emerald-600 font-medium">
                <span className="flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Total Paid</span>
                <span>{formatCurrency(viewInvoice.totalPaid || 0)}</span>
              </div>
              <div className="flex justify-between text-amber-600 font-medium">
                <span className="flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" /> Pending Amount</span>
                <span>{formatCurrency(viewInvoice.pendingAmount ?? viewInvoice.total)}</span>
              </div>
            </div>

            {/* Payment History */}
            <div className="mb-5" data-testid="payment-history-section">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-indigo-500" /> Payment History
                </h3>
                {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                  <button
                    onClick={() => openPaymentModal(viewInvoice.id)}
                    className="flex items-center gap-1.5 bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-emerald-700 transition"
                    data-testid="add-payment-btn"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Payment
                  </button>
                )}
              </div>

              {(!viewInvoice.payments || viewInvoice.payments.length === 0) ? (
                <div className="text-center py-6 bg-gray-50 rounded-lg border border-dashed border-gray-200" data-testid="no-payments">
                  <Banknote className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No payments recorded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {viewInvoice.payments.map((payment) => (
                    <div key={payment.id} className="bg-white border border-gray-100 rounded-lg p-3 flex items-start justify-between" data-testid={`payment-entry-${payment.id}`}>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-gray-800 flex items-center gap-1">
                            <IndianRupee className="w-3.5 h-3.5" />{formatCurrency(payment.amount)}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 font-medium uppercase">
                            {payment.paymentMethod?.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500">
                          <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(payment.paymentDate)}</span>
                          {payment.accountName && <span>Account: {payment.accountName}</span>}
                          {payment.referenceNumber && <span>Ref: {payment.referenceNumber}</span>}
                        </div>
                        {payment.notes && <p className="text-xs text-gray-400 mt-1">{payment.notes}</p>}
                      </div>
                      <button
                        onClick={() => deletePayment(viewInvoice.id, payment.id)}
                        className="text-gray-300 hover:text-red-500 ml-2 flex-shrink-0 transition"
                        data-testid={`delete-payment-${payment.id}`}
                        title="Delete payment"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {viewInvoice.notes && <div className="text-sm text-gray-600 mb-4"><span className="font-medium">Notes:</span> {viewInvoice.notes}</div>}

            {/* Actions */}
            <div className="flex gap-2 flex-wrap border-t border-gray-100 pt-4">
              <button onClick={() => downloadPdf(viewInvoice.id, viewInvoice.invoiceNumber)}
                className="flex items-center gap-1 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-indigo-700" data-testid="download-pdf-btn">
                <Download className="w-4 h-4" /> Download PDF
              </button>
              {viewInvoice.status === 'draft' && (
                <button onClick={() => updateStatus(viewInvoice.id, 'sent')}
                  className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700" data-testid="mark-sent-btn">
                  <Send className="w-4 h-4" /> Mark Sent
                </button>
              )}
              {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                <button onClick={() => openPaymentModal(viewInvoice.id)}
                  className="flex items-center gap-1 bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-emerald-700" data-testid="add-payment-action-btn">
                  <CreditCard className="w-4 h-4" /> Add Payment
                </button>
              )}
              {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                <button onClick={() => updateStatus(viewInvoice.id, 'overdue')}
                  className="flex items-center gap-1 text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg text-sm font-medium" data-testid="mark-overdue-btn">
                  <AlertCircle className="w-4 h-4" /> Mark Overdue
                </button>
              )}
              {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                <button onClick={() => updateStatus(viewInvoice.id, 'cancelled')}
                  className="text-red-500 hover:text-red-700 px-3 py-1.5 text-sm font-medium" data-testid="cancel-invoice-status-btn">Cancel</button>
              )}
              {(viewInvoice.status === 'draft' || viewInvoice.status === 'cancelled') && (
                <button onClick={() => deleteInvoice(viewInvoice.id)}
                  className="text-red-500 hover:text-red-700 px-3 py-1.5 text-sm font-medium" data-testid="delete-invoice-btn">
                  <Trash2 className="w-4 h-4 inline mr-1" />Delete
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ──── Add Payment Modal ──── */}
      {showPaymentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4" data-testid="add-payment-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-emerald-600" /> Record Payment
              </h2>
              <button onClick={() => setShowPaymentModal(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount *</label>
                <div className="relative">
                  <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input type="number" min={0.01} step={0.01} value={paymentForm.amount}
                    onChange={e => setPaymentForm(p => ({ ...p, amount: e.target.value }))}
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="0.00"
                    data-testid="payment-amount-input" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Payment Date</label>
                <input type="date" value={paymentForm.paymentDate}
                  onChange={e => setPaymentForm(p => ({ ...p, paymentDate: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="payment-date-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Payment Method</label>
                <select value={paymentForm.paymentMethod}
                  onChange={e => setPaymentForm(p => ({ ...p, paymentMethod: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="payment-method-select">
                  {paymentMethods.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sender Account Name</label>
                <input type="text" value={paymentForm.accountName}
                  onChange={e => setPaymentForm(p => ({ ...p, accountName: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. John Doe"
                  data-testid="payment-account-name-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reference Number</label>
                <input type="text" value={paymentForm.referenceNumber}
                  onChange={e => setPaymentForm(p => ({ ...p, referenceNumber: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="UPI Ref / Transaction ID"
                  data-testid="payment-reference-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={paymentForm.notes}
                  onChange={e => setPaymentForm(p => ({ ...p, notes: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} placeholder="Optional notes"
                  data-testid="payment-notes-input" />
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowPaymentModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-payment-btn">Cancel</button>
              <button onClick={submitPayment} disabled={paymentLoading}
                className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50" data-testid="submit-payment-btn">
                {paymentLoading ? 'Recording...' : 'Record Payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Invoice List ──── */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : filteredInvoices.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100" data-testid="empty-state">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No invoices yet</p>
          <p className="text-sm text-gray-400 mt-1">Create your first invoice to get started</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <table className="w-full text-sm" data-testid="invoices-table">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                <th className="text-left px-4 py-3">Invoice #</th>
                <th className="text-left px-4 py-3">Buyer</th>
                <th className="text-left px-4 py-3">Date</th>
                <th className="text-right px-4 py-3">Total</th>
                <th className="text-right px-4 py-3">Paid</th>
                <th className="text-right px-4 py-3">Pending</th>
                <th className="text-center px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.map(inv => (
                <tr key={inv.id} className="border-b border-gray-50 hover:bg-gray-50/50" data-testid={`invoice-row-${inv.id}`}>
                  <td className="px-4 py-3 font-medium text-indigo-600 cursor-pointer" onClick={() => openInvoiceDetail(inv)}>{inv.invoiceNumber}</td>
                  <td className="px-4 py-3 text-gray-700">{inv.buyerName}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(inv.date)}</td>
                  <td className="px-4 py-3 text-right font-medium">
                    <span className="flex items-center justify-end gap-0.5"><IndianRupee className="w-3.5 h-3.5" />{formatCurrency(inv.total)}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-emerald-600 font-medium" data-testid={`invoice-paid-${inv.id}`}>
                    {formatCurrency(inv.totalPaid || 0)}
                  </td>
                  <td className="px-4 py-3 text-right text-amber-600 font-medium" data-testid={`invoice-pending-${inv.id}`}>
                    {formatCurrency(inv.pendingAmount ?? inv.total)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${statusColors[inv.status] || 'bg-gray-100 text-gray-700'}`} data-testid={`invoice-status-${inv.id}`}>
                      {statusLabels[inv.status] || inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => openInvoiceDetail(inv)} className="text-gray-400 hover:text-indigo-600" data-testid={`view-invoice-${inv.id}`} title="View"><Eye className="w-4 h-4" /></button>
                      <button onClick={() => downloadPdf(inv.id, inv.invoiceNumber)} className="text-gray-400 hover:text-indigo-600" data-testid={`download-invoice-${inv.id}`} title="PDF"><Download className="w-4 h-4" /></button>
                      {inv.status !== 'cancelled' && inv.status !== 'paid' && (
                        <button onClick={() => openPaymentModal(inv.id)} className="text-gray-400 hover:text-emerald-600" data-testid={`add-payment-row-${inv.id}`} title="Add Payment"><CreditCard className="w-4 h-4" /></button>
                      )}
                      {(inv.status === 'draft' || inv.status === 'cancelled') && (
                        <button onClick={() => deleteInvoice(inv.id)} className="text-gray-400 hover:text-red-600" data-testid={`delete-invoice-${inv.id}`} title="Delete"><Trash2 className="w-4 h-4" /></button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
