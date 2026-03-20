'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { useNetworkContext } from '@/context/NetworkContext';
import { toast } from 'sonner';
import Select, { StylesConfig, SingleValue } from 'react-select';
import {
  FileText, Plus, X, Trash2, Eye, Download, Send, Loader2,
  IndianRupee, Clock, CheckCircle2, AlertCircle, ArrowRight,
  WifiOff, Share2, ChevronDown, ChevronUp
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SelectOption { value: string; label: string; }
interface ProductOption extends SelectOption { stock: number; desc: string; }

const selectStyles: StylesConfig<SelectOption, false> = {
  control: (base, state) => ({ ...base, minHeight: '38px', borderRadius: '0.5rem', borderColor: state.isFocused ? '#6366f1' : '#d1d5db', boxShadow: state.isFocused ? '0 0 0 1px #6366f1' : 'none', fontSize: '0.875rem', '&:hover': { borderColor: '#6366f1' } }),
  menu: (base) => ({ ...base, zIndex: 50, fontSize: '0.875rem' }),
  option: (base, state) => ({ ...base, backgroundColor: state.isSelected ? '#6366f1' : state.isFocused ? '#eef2ff' : 'white', color: state.isSelected ? 'white' : '#1f2937', padding: '8px 12px', cursor: 'pointer' }),
  placeholder: (base) => ({ ...base, color: '#9ca3af' }),
  singleValue: (base) => ({ ...base, color: '#1f2937' }),
  input: (base) => ({ ...base, color: '#1f2937' }),
};

const productStyles: StylesConfig<ProductOption, false> = {
  control: (base, state) => ({ ...base, minHeight: '32px', borderRadius: '0.25rem', borderColor: state.isFocused ? '#6366f1' : '#d1d5db', boxShadow: state.isFocused ? '0 0 0 1px #6366f1' : 'none', fontSize: '0.8rem', '&:hover': { borderColor: '#6366f1' } }),
  menu: (base) => ({ ...base, zIndex: 50, fontSize: '0.8rem', minWidth: '300px' }),
  option: (base, state) => ({ ...base, backgroundColor: state.isSelected ? '#6366f1' : state.isFocused ? '#eef2ff' : 'white', color: state.isSelected ? 'white' : '#1f2937', padding: '6px 10px', cursor: 'pointer' }),
  placeholder: (base) => ({ ...base, color: '#9ca3af', fontSize: '0.8rem' }),
  singleValue: (base) => ({ ...base, color: '#1f2937', fontSize: '0.8rem' }),
  input: (base) => ({ ...base, color: '#1f2937', fontSize: '0.8rem' }),
  valueContainer: (base) => ({ ...base, padding: '0 8px' }),
  indicatorsContainer: (base) => ({ ...base, '> div': { padding: '4px' } }),
};

interface Buyer { id: string; buyerName: string; company: string; phone: string; state: string; }
interface Listing { id: string; productName: string; description: string; availableStock: number; hsnCode: string; specifications: any[]; }
interface QuotationItem { productId: string; productName: string; description: string; hsnCode: string; quantity: number; price: number; discount: number; gstPercent: number; total?: number; }
interface Quotation { id: string; quotationNumber: string; buyerName: string; buyerPhone: string; buyerId: string; date: string; status: string; items: QuotationItem[]; subtotal: number; gst: number; total: number; notes: string; validityDays: number; convertedToInvoice: boolean; convertedInvoiceNumber?: string; termsAndConditions: string; placeOfSupply: string; }

const emptyItem = (): QuotationItem => ({ productId: '', productName: '', description: '', hsnCode: '', quantity: 1, price: 0, discount: 0, gstPercent: 18 });

export default function QuotationsPage() {
  const router = useRouter();
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const { isOnline } = useNetworkContext();
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [viewQuotation, setViewQuotation] = useState<Quotation | null>(null);
  const [formData, setFormData] = useState({ buyerId: '', items: [emptyItem()], notes: '', validityDays: 15, termsAndConditions: '', placeOfSupply: '' });
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const authHeaders = useCallback(async () => {
    const token = await getIdToken();
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchAll = useCallback(async () => {
    try {
      const h = await authHeaders();
      const [qR, bR, lR] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/quotations`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/buyers`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/invoice-products`, { headers: h }),
      ]);
      if (qR.ok) setQuotations((await qR.json()).quotations || []);
      if (bR.ok) setBuyers((await bR.json()).buyers || []);
      if (lR.ok) setListings((await lR.json()).products || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const onProductSelect = (idx: number, productId: string) => {
    const listing = listings.find(l => l.id === productId);
    if (!listing) return;
    const items = [...formData.items];
    items[idx] = { ...items[idx], productId, productName: listing.productName, hsnCode: listing.hsnCode || '', description: listing.description || '', price: items[idx].price };
    setFormData(p => ({ ...p, items }));
  };

  const addItem = () => setFormData(p => ({ ...p, items: [...p.items, emptyItem()] }));
  const removeItem = (idx: number) => { if (formData.items.length > 1) setFormData(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) })); };

  const calcSubtotal = () => formData.items.reduce((sum, i) => sum + (i.price * i.quantity - i.discount), 0);
  const calcGst = () => formData.items.reduce((sum, i) => sum + ((i.price * i.quantity - i.discount) * i.gstPercent / 100), 0);

  const handleSubmit = async () => {
    if (!formData.buyerId) { toast.error('Select a buyer'); return; }
    if (formData.items.some(i => !i.productName && !i.productId)) { toast.error('All items need a product'); return; }

    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/quotations`, { method: 'POST', headers: h, body: JSON.stringify(formData) });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); return; }
      toast.success('Quotation created');
      setShowForm(false);
      setFormData({ buyerId: '', items: [emptyItem()], notes: '', validityDays: 15, termsAndConditions: '', placeOfSupply: '' });
      fetchAll();
    } catch { toast.error('Error creating quotation'); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this quotation?')) return;
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/quotations/${id}`, { method: 'DELETE', headers: h });
    if (res.ok) { toast.success('Deleted'); fetchAll(); } else toast.error('Failed to delete');
  };

  const handleConvertToInvoice = async (id: string) => {
    if (!isOnline) { toast.error('Cannot convert offline. Go online first.'); return; }
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/quotations/${id}/convert`, { method: 'POST', headers: h });
      if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Conversion failed'); return; }
      const { prefill } = await res.json();

      // Store prefill data and redirect to invoice page
      sessionStorage.setItem('quotation_prefill', JSON.stringify(prefill));
      router.push('/seller/business-tools/invoices?from_quotation=true');
    } catch { toast.error('Conversion error'); }
  };

  const handleMarkSent = async (id: string) => {
    if (!isOnline) { toast.error('Cannot update offline'); return; }
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/quotations/${id}`, { method: 'PUT', headers: h, body: JSON.stringify({ status: 'sent' }) });
    if (res.ok) { toast.success('Marked as sent'); fetchAll(); }
  };

  const shareWhatsApp = (quo: Quotation) => {
    if (!isOnline) { toast.error('Cannot send WhatsApp in offline mode'); return; }
    const msg = `Quotation: ${quo.quotationNumber}\nBuyer: ${quo.buyerName}\nTotal: ₹${quo.total?.toLocaleString('en-IN')}\nValid for ${quo.validityDays} days`;
    window.open(`https://wa.me/${quo.buyerPhone}?text=${encodeURIComponent(msg)}`, '_blank');
    handleMarkSent(quo.id);
  };

  const toggleRow = (id: string) => setExpandedRows(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const statusBadge = (q: Quotation) => {
    if (q.convertedToInvoice) return <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">Converted</span>;
    if (q.status === 'sent') return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">Sent</span>;
    return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">Draft</span>;
  };

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  return (
    <div className="space-y-4" data-testid="quotations-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900" data-testid="quotations-heading">Quotations</h2>
          <p className="text-sm text-gray-500">{quotations.length} quotation{quotations.length !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700" data-testid="create-quotation-btn">
          <Plus className="w-4 h-4" /> New Quotation
        </button>
      </div>

      {/* ─── Create Form ─── */}
      {showForm && (
        <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4" data-testid="quotation-form">
          <h3 className="font-semibold text-gray-900">Create Quotation</h3>

          {/* Buyer */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Buyer *</label>
            <Select<SelectOption>
              options={buyers.map(b => ({ value: b.id, label: `${b.buyerName}${b.company ? ` (${b.company})` : ''}${b.state ? ` - ${b.state}` : ''}` }))}
              value={formData.buyerId ? { value: formData.buyerId, label: (() => { const b = buyers.find(x => x.id === formData.buyerId); return b ? `${b.buyerName}${b.company ? ` (${b.company})` : ''}` : ''; })() } : null}
              onChange={(opt: SingleValue<SelectOption>) => setFormData(p => ({ ...p, buyerId: opt?.value || '' }))}
              placeholder="Search buyer..." isSearchable isClearable styles={selectStyles} inputId="quo-buyer-select" data-testid="quo-buyer-select"
            />
          </div>

          {/* Items */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Items</label>
            {formData.items.map((item, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 mb-2 items-end">
                <div className="col-span-4">
                  {idx === 0 && <span className="text-xs text-gray-500 block mb-1">Product</span>}
                  <Select<ProductOption>
                    options={[{ value: '', label: 'Manual entry', stock: 0, desc: '' }, ...listings.map(l => ({ value: l.id, label: l.productName, stock: l.availableStock, desc: l.description }))]}
                    value={item.productId ? { value: item.productId, label: listings.find(l => l.id === item.productId)?.productName || item.productName, stock: 0, desc: '' } : null}
                    onChange={(opt: SingleValue<ProductOption>) => {
                      if (!opt || opt.value === '') { const items = [...formData.items]; items[idx] = { ...items[idx], productId: '', productName: '' }; setFormData(p => ({ ...p, items })); }
                      else onProductSelect(idx, opt.value);
                    }}
                    placeholder="Search..." isSearchable isClearable styles={productStyles}
                    formatOptionLabel={(o) => o.value === '' ? <span className="text-gray-400 italic">Manual</span> : <span>{o.label} <span className="text-gray-400 text-xs">({o.stock})</span></span>}
                    inputId={`quo-item-product-${idx}`}
                  />
                  {!item.productId && <input type="text" value={item.productName} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], productName: e.target.value }; setFormData(p => ({ ...p, items })); }} placeholder="Product name" className="w-full mt-1 px-2 py-1 border rounded text-sm" />}
                </div>
                <div className="col-span-2">
                  {idx === 0 && <span className="text-xs text-gray-500 block mb-1">Price</span>}
                  <input type="number" value={item.price || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], price: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm" placeholder="0" />
                </div>
                <div className="col-span-1">
                  {idx === 0 && <span className="text-xs text-gray-500 block mb-1">Qty</span>}
                  <input type="number" value={item.quantity || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], quantity: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm" placeholder="1" min={1} />
                </div>
                <div className="col-span-2">
                  {idx === 0 && <span className="text-xs text-gray-500 block mb-1">GST %</span>}
                  <select value={item.gstPercent} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], gstPercent: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm">
                    <option value={0}>0%</option><option value={5}>5%</option><option value={12}>12%</option><option value={18}>18%</option><option value={28}>28%</option>
                  </select>
                </div>
                <div className="col-span-2">
                  {idx === 0 && <span className="text-xs text-gray-500 block mb-1">Total</span>}
                  <div className="px-2 py-1.5 bg-gray-50 border rounded text-sm text-gray-700 flex items-center">
                    <IndianRupee className="w-3 h-3 mr-0.5" />{((item.price * item.quantity - item.discount) * (1 + item.gstPercent / 100)).toFixed(2)}
                  </div>
                </div>
                <div className="col-span-1 flex items-end justify-center pb-1">
                  {formData.items.length > 1 && <button onClick={() => removeItem(idx)} className="text-gray-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>}
                </div>
              </div>
            ))}
            <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-1">+ Add Item</button>
          </div>

          {/* Totals */}
          <div className="flex justify-end gap-8 text-sm border-t pt-3">
            <div><span className="text-gray-500">Subtotal:</span> <span className="font-medium ml-1">₹{calcSubtotal().toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
            <div><span className="text-gray-500">GST:</span> <span className="font-medium ml-1">₹{calcGst().toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
            <div><span className="text-gray-500">Total:</span> <span className="font-bold text-lg ml-1">₹{Math.round(calcSubtotal() + calcGst()).toLocaleString('en-IN')}</span></div>
          </div>

          {/* Notes + Validity */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Notes</label>
              <textarea value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} rows={2} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Optional notes..." />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Validity (days)</label>
              <input type="number" value={formData.validityDays} onChange={e => setFormData(p => ({ ...p, validityDays: +e.target.value }))} className="w-full px-3 py-2 border rounded-lg text-sm" min={1} />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-quotation-btn">Cancel</button>
            <button onClick={handleSubmit} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium" data-testid="submit-quotation-btn">Create Quotation</button>
          </div>
        </div>
      )}

      {/* ─── Quotation List ─── */}
      {quotations.length === 0 && !showForm ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No quotations yet</p>
          <button onClick={() => setShowForm(true)} className="mt-3 text-sm text-indigo-600 font-medium hover:underline">Create your first quotation</button>
        </div>
      ) : (
        <div className="space-y-2" data-testid="quotation-list">
          {quotations.map(q => (
            <div key={q.id} className="bg-white rounded-xl border hover:shadow-sm transition-shadow" data-testid={`quotation-${q.id}`}>
              <div className="px-4 py-3 flex items-center justify-between cursor-pointer" onClick={() => toggleRow(q.id)}>
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium text-gray-900">{q.quotationNumber}</span>
                      {statusBadge(q)}
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{q.buyerName}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900 flex items-center justify-end"><IndianRupee className="w-3 h-3" />{q.total?.toLocaleString('en-IN')}</p>
                    <p className="text-xs text-gray-400">{new Date(q.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}</p>
                  </div>
                  {expandedRows.has(q.id) ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedRows.has(q.id) && (
                <div className="px-4 pb-4 border-t pt-3 space-y-3">
                  {/* Items */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="pb-1">Product</th><th className="pb-1">Qty</th><th className="pb-1">Price</th><th className="pb-1">GST</th><th className="pb-1 text-right">Total</th></tr></thead>
                      <tbody>
                        {q.items.map((item, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="py-1.5">{item.productName}{item.hsnCode ? <span className="text-xs text-gray-400 ml-1">[{item.hsnCode}]</span> : ''}</td>
                            <td>{item.quantity}</td>
                            <td>₹{item.price?.toLocaleString('en-IN')}</td>
                            <td>{item.gstPercent}%</td>
                            <td className="text-right font-medium">₹{item.total?.toLocaleString('en-IN')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {q.notes && <p className="text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2">{q.notes}</p>}

                  {q.convertedToInvoice && q.convertedInvoiceNumber && (
                    <p className="text-sm text-blue-600 font-medium">Converted to Invoice: {q.convertedInvoiceNumber}</p>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {!q.convertedToInvoice && (
                      <button onClick={() => handleConvertToInvoice(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700" data-testid={`convert-to-invoice-${q.id}`}>
                        <ArrowRight className="w-3.5 h-3.5" /> Convert to Invoice
                      </button>
                    )}
                    <button onClick={() => shareWhatsApp(q)} className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700" data-testid={`quotation-whatsapp-${q.id}`}>
                      <Share2 className="w-3.5 h-3.5" /> WhatsApp
                    </button>
                    {q.status === 'draft' && !q.convertedToInvoice && (
                      <button onClick={() => handleMarkSent(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200">
                        <Send className="w-3.5 h-3.5" /> Mark Sent
                      </button>
                    )}
                    <button onClick={() => handleDelete(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium" data-testid={`delete-quotation-${q.id}`}>
                      <Trash2 className="w-3.5 h-3.5" /> Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
