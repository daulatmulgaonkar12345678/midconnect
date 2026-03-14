'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { FileText, Plus, X, Download, Eye, Trash2, Send, CreditCard, IndianRupee, ChevronDown, ChevronUp } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

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

interface Buyer { id: string; buyerName: string; company?: string; }
interface InvoiceItem { productName: string; quantity: number; price: number; gstPercent: number; gstAmount: number; total: number; selected_specifications?: Spec[]; }
interface Invoice { id: string; invoiceNumber: string; buyerName: string; date: string; items: InvoiceItem[]; subtotal: number; gst: number; total: number; status: string; notes?: string; }

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700', sent: 'bg-blue-100 text-blue-700', paid: 'bg-green-100 text-green-700', cancelled: 'bg-red-100 text-red-700',
};

function emptyItem(): InvoiceFormItem {
  return { productId: '', productName: '', quantity: 1, price: 0, gstPercent: 18, allSpecs: [], selectedSpecs: [], customSpecs: [], showSpecs: false };
}

function calcLine(qty: number, price: number, gst: number) {
  const sub = qty * price;
  const gstAmt = Math.round(sub * gst / 100 * 100) / 100;
  return { subtotal: sub, gstAmount: gstAmt, total: Math.round((sub + gstAmt) * 100) / 100 };
}

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

  const onProductSelect = (idx: number, listingId: string) => {
    const listing = listings.find(l => l.id === listingId);
    const items = [...formData.items];
    items[idx] = {
      ...items[idx],
      productId: listingId,
      productName: listing?.productName || '',
      price: listing?.price || items[idx].price,
      allSpecs: listing?.specifications || [],
      selectedSpecs: [...(listing?.specifications || [])], // all checked by default
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
        selected_specifications: [
          ...i.selectedSpecs,
          ...i.customSpecs.filter(s => s.key && s.value),
        ],
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
    if (viewInvoice?.id === id) setViewInvoice(prev => prev ? { ...prev, status } : null);
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

  const filteredInvoices = statusFilter === 'all' ? invoices : invoices.filter(i => i.status === statusFilter);

  if (!hasPermission('create_invoice')) {
    return <div className="text-center py-12 bg-white rounded-xl border" data-testid="no-permission"><FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" /><p className="text-gray-500">No permission to manage invoices.</p></div>;
  }

  return (
    <div className="space-y-6" data-testid="invoices-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Create and manage invoices with product specifications</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 text-sm font-medium" data-testid="create-invoice-btn">
          <Plus className="w-4 h-4" /> New Invoice
        </button>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2">
        {['all', 'draft', 'sent', 'paid', 'cancelled'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition ${statusFilter === s ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'}`}
            data-testid={`filter-${s}`}>{s}</button>
        ))}
      </div>

      {/* Create Invoice Modal */}
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
                        {/* Product Row */}
                        <div className="grid grid-cols-12 gap-2 items-start">
                          <div className="col-span-4">
                            <label className="text-xs text-gray-500 mb-1 block">Product</label>
                            <select value={item.productId} onChange={e => onProductSelect(idx, e.target.value)}
                              className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-product-${idx}`}>
                              <option value="">Select / Manual</option>
                              {listings.map(l => (
                                <option key={l.id} value={l.id}>
                                  {l.productName} (Stock: {l.stock})
                                </option>
                              ))}
                            </select>
                            {/* Spec preview under dropdown */}
                            {item.productId && item.allSpecs.length > 0 && (
                              <p className="text-[10px] text-gray-400 mt-0.5 truncate">
                                {item.allSpecs.map(s => `${s.key}: ${s.value}`).join(' | ')}
                              </p>
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
                            <div className="px-2 py-1.5 bg-white border border-gray-200 rounded text-sm font-medium text-right">
                              {lineTotal.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </div>
                            <div className="text-[10px] text-gray-400 text-right mt-0.5">GST: {lineTotal.gstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
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

                        {/* Spec preview line */}
                        {allFinalSpecs.length > 0 && !item.showSpecs && (
                          <p className="text-xs text-gray-500 ml-1">
                            {allFinalSpecs.map(s => `${s.key}: ${s.value}`).join(' | ')}
                          </p>
                        )}

                        {/* Specification Selector */}
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
                            {/* Custom Specs */}
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
                <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{formTotals.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{formTotals.gst.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-2">
                  <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{formTotals.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
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

      {/* Invoice Detail Modal */}
      {viewInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-detail-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold">{viewInvoice.invoiceNumber}</h2>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[viewInvoice.status] || ''}`}>{viewInvoice.status}</span>
              </div>
              <button onClick={() => setViewInvoice(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
              <div><span className="text-gray-500">Buyer:</span> <span className="font-medium">{viewInvoice.buyerName}</span></div>
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{new Date(viewInvoice.date).toLocaleDateString('en-IN')}</span></div>
            </div>
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
                        <div className="text-[10px] text-gray-400 mt-0.5">
                          {item.selected_specifications.map(s => `${s.key}: ${s.value}`).join(' | ')}
                        </div>
                      )}
                    </td>
                    <td className="py-2 text-right">{item.quantity}</td>
                    <td className="py-2 text-right">{item.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td className="py-2 text-right">{item.gstPercent}%</td>
                    <td className="py-2 text-right">{item.gstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td className="py-2 text-right font-medium">{item.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm mb-4">
              <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{viewInvoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{viewInvoice.gst.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
              <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-2">
                <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{viewInvoice.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
            {viewInvoice.notes && <div className="text-sm text-gray-600 mb-4"><span className="font-medium">Notes:</span> {viewInvoice.notes}</div>}
            <div className="flex gap-2 flex-wrap">
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
              {(viewInvoice.status === 'draft' || viewInvoice.status === 'sent') && (
                <button onClick={() => updateStatus(viewInvoice.id, 'paid')}
                  className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700" data-testid="mark-paid-btn">
                  <CreditCard className="w-4 h-4" /> Mark Paid
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

      {/* Invoice List */}
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
                <th className="text-center px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.map(inv => (
                <tr key={inv.id} className="border-b border-gray-50 hover:bg-gray-50/50" data-testid={`invoice-row-${inv.id}`}>
                  <td className="px-4 py-3 font-medium text-indigo-600 cursor-pointer" onClick={() => setViewInvoice(inv)}>{inv.invoiceNumber}</td>
                  <td className="px-4 py-3 text-gray-700">{inv.buyerName}</td>
                  <td className="px-4 py-3 text-gray-500">{new Date(inv.date).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-right font-medium flex items-center justify-end gap-0.5"><IndianRupee className="w-3.5 h-3.5" />{inv.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-3 text-center"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[inv.status] || ''}`}>{inv.status}</span></td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => setViewInvoice(inv)} className="text-gray-400 hover:text-indigo-600" data-testid={`view-invoice-${inv.id}`}><Eye className="w-4 h-4" /></button>
                      <button onClick={() => downloadPdf(inv.id, inv.invoiceNumber)} className="text-gray-400 hover:text-indigo-600" data-testid={`download-invoice-${inv.id}`}><Download className="w-4 h-4" /></button>
                      {(inv.status === 'draft' || inv.status === 'cancelled') && (
                        <button onClick={() => deleteInvoice(inv.id)} className="text-gray-400 hover:text-red-600" data-testid={`delete-invoice-${inv.id}`}><Trash2 className="w-4 h-4" /></button>
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
