'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { useNetworkContext } from '@/context/NetworkContext';
import { addOfflineItem, generateTempId } from '@/lib/offlineStore';
import { toast } from 'sonner';
import Select, { StylesConfig, SingleValue } from 'react-select';
import {
  FileText, Plus, Trash2, Download, Send, Loader2,
  IndianRupee, ArrowRight, Share2, ChevronDown, ChevronUp, WifiOff, CloudOff, Percent, MessageCircle
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SelectOption { value: string; label: string; }
interface ProductOption extends SelectOption { stock: number; desc: string; price: number; gst: number; hsn: string; }

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
interface Listing { id: string; productName: string; description: string; availableStock: number; hsnCode: string; price: number; gstRate: number; specifications: Record<string, unknown>[]; }
interface QuotationItem {
  productId: string; productName: string; description: string; hsnCode: string;
  quantity: number; price: number; discount: number; discountType: '%' | 'Rs';
  gstPercent: number; total?: number;
}
interface Quotation {
  id: string; quotationNumber: string; buyerName: string; buyerPhone: string; buyerId: string;
  date: string; status: string; items: QuotationItem[]; subtotal: number; gst: number; total: number;
  notes: string; validityDays: number; convertedToInvoice: boolean;
  convertedInvoiceNumber?: string; termsAndConditions: string; placeOfSupply: string;
  cgst?: number; sgst?: number; igst?: number; roundOff?: number;
}

const emptyItem = (): QuotationItem => ({ productId: '', productName: '', description: '', hsnCode: '', quantity: 1, price: 0, discount: 0, discountType: '%', gstPercent: 18 });

function calcItemTotals(item: QuotationItem) {
  const base = item.price * item.quantity;
  const discAmt = item.discountType === '%' ? base * (item.discount / 100) : item.discount;
  const taxable = Math.max(base - discAmt, 0);
  const gstAmt = taxable * (item.gstPercent / 100);
  return { base, discAmt, taxable, gstAmt, total: taxable + gstAmt };
}

export default function QuotationsPage() {
  const router = useRouter();
  const { getIdToken, user } = useAuth();
  const { hasPermission } = usePermissions();
  const { isOnline } = useNetworkContext();
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ buyerId: '', items: [emptyItem()], notes: '', validityDays: 15, termsAndConditions: '', placeOfSupply: '' });
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);
  const [sharingWa, setSharingWa] = useState<string | null>(null);

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

  // Auto-fill price, GST%, HSN from inventory on product select
  const onProductSelect = (idx: number, productId: string) => {
    const listing = listings.find(l => l.id === productId);
    if (!listing) return;
    const items = [...formData.items];
    items[idx] = {
      ...items[idx],
      productId,
      productName: listing.productName,
      hsnCode: listing.hsnCode || '',
      description: listing.description || '',
      price: listing.price || items[idx].price,
      gstPercent: listing.gstRate ?? items[idx].gstPercent,
    };
    setFormData(p => ({ ...p, items }));
  };

  const addItem = () => setFormData(p => ({ ...p, items: [...p.items, emptyItem()] }));
  const removeItem = (idx: number) => { if (formData.items.length > 1) setFormData(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) })); };

  const calcTotals = () => formData.items.reduce((acc, item) => {
    const t = calcItemTotals(item);
    return { subtotal: acc.subtotal + t.taxable, gst: acc.gst + t.gstAmt, total: acc.total + t.total };
  }, { subtotal: 0, gst: 0, total: 0 });

  const resetForm = () => {
    setShowForm(false);
    setFormData({ buyerId: '', items: [emptyItem()], notes: '', validityDays: 15, termsAndConditions: '', placeOfSupply: '' });
  };

  const handleSubmit = async () => {
    if (!formData.buyerId) { toast.error('Select a buyer'); return; }
    if (formData.items.some(i => !i.productName && !i.productId)) { toast.error('All items need a product'); return; }
    setSubmitting(true);

    // Offline: save to IndexedDB
    if (!isOnline) {
      try {
        const userId = user?.uid || 'unknown';
        await addOfflineItem({
          id: generateTempId(userId),
          type: 'quotation',
          status: 'draft_offline',
          data: { ...formData, _offlineCreated: true },
          createdBy: userId,
        });
        toast.success('Quotation saved offline. Will sync when online.');
        resetForm();
      } catch { toast.error('Failed to save offline'); }
      setSubmitting(false);
      return;
    }

    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/quotations`, { method: 'POST', headers: h, body: JSON.stringify(formData) });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); setSubmitting(false); return; }
      toast.success('Quotation created');
      resetForm();
      fetchAll();
    } catch { toast.error('Error creating quotation'); }
    setSubmitting(false);
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
      const storeRes = await fetch(`${API_URL}/api/business-tools/quotations/${id}/store-prefill`, { method: 'POST', headers: h });
      if (!storeRes.ok) { const d = await storeRes.json(); toast.error(d.detail || 'Conversion failed'); return; }
      const { prefill } = await storeRes.json();
      sessionStorage.setItem('quotation_prefill', JSON.stringify(prefill));
      sessionStorage.setItem('source_quotation_id', id);
      router.push(`/seller/business-tools/invoices?from_quotation=true&quotation_id=${id}`);
    } catch { toast.error('Conversion error'); }
  };

  const handleMarkSent = async (id: string) => {
    if (!isOnline) { toast.error('Cannot update offline'); return; }
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/quotations/${id}`, { method: 'PUT', headers: h, body: JSON.stringify({ status: 'sent' }) });
    if (res.ok) { toast.success('Marked as sent'); fetchAll(); }
  };

  const handleDownloadPdf = async (id: string, quotationNumber: string) => {
    if (!isOnline) { toast.error('PDF download requires internet'); return; }
    setDownloadingPdf(id);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/quotations/${id}/pdf`, { headers: h });
      if (!res.ok) { toast.error('Failed to download PDF'); setDownloadingPdf(null); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${quotationNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('PDF downloaded');
    } catch { toast.error('Download failed'); }
    setDownloadingPdf(null);
  };

  // WhatsApp sharing with PDF link
  const handleShareWhatsApp = async (quo: Quotation) => {
    if (!isOnline) { toast.error('Cannot send WhatsApp in offline mode'); return; }
    if (!quo.buyerPhone) { toast.error('Buyer phone not available'); return; }
    setSharingWa(quo.id);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/quotations/${quo.id}/share-link`, { method: 'POST', headers: h });
      if (!res.ok) { toast.error('Failed to generate share link'); setSharingWa(null); return; }
      const data = await res.json();
      if (data.whatsappLink) {
        window.open(data.whatsappLink, '_blank');
        handleMarkSent(quo.id);
      } else {
        toast.error('Could not generate WhatsApp link');
      }
    } catch { toast.error('Share failed'); }
    setSharingWa(null);
  };

  const toggleRow = (id: string) => setExpandedRows(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const statusBadge = (q: Quotation) => {
    if (q.convertedToInvoice) return <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium" data-testid={`status-converted-${q.id}`}>Converted</span>;
    if (q.status === 'sent') return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium" data-testid={`status-sent-${q.id}`}>Sent</span>;
    return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium" data-testid={`status-draft-${q.id}`}>Draft</span>;
  };

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" data-testid="loading-spinner" /></div>;

  const totals = calcTotals();

  return (
    <div className="space-y-4" data-testid="quotations-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900" data-testid="quotations-heading">Quotations</h2>
          <p className="text-sm text-gray-500">{quotations.length} quotation{quotations.length !== 1 ? 's' : ''}{!isOnline && <span className="ml-2 text-amber-600 inline-flex items-center gap-1"><WifiOff className="w-3 h-3" /> Offline</span>}</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors" data-testid="create-quotation-btn">
          <Plus className="w-4 h-4" /> New Quotation
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4" data-testid="quotation-form">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Create Quotation</h3>
            {!isOnline && <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full"><CloudOff className="w-3 h-3" /> Offline mode</span>}
          </div>

          {/* Buyer */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Buyer *</label>
            <Select<SelectOption>
              options={buyers.map(b => ({ value: b.id, label: `${b.buyerName}${b.company ? ` (${b.company})` : ''}${b.state ? ` - ${b.state}` : ''}` }))}
              value={formData.buyerId ? { value: formData.buyerId, label: (() => { const b = buyers.find(x => x.id === formData.buyerId); return b ? `${b.buyerName}${b.company ? ` (${b.company})` : ''}` : ''; })() } : null}
              onChange={(opt: SingleValue<SelectOption>) => setFormData(p => ({ ...p, buyerId: opt?.value || '' }))}
              placeholder="Search buyer..." isSearchable isClearable styles={selectStyles} inputId="quo-buyer-select"
            />
          </div>

          {/* Items */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Items</label>
            <div className="space-y-3">
              {formData.items.map((item, idx) => {
                const t = calcItemTotals(item);
                return (
                  <div key={idx} className="bg-gray-50 rounded-lg p-3 space-y-2" data-testid={`quotation-item-${idx}`}>
                    <div className="grid grid-cols-12 gap-2 items-start">
                      {/* Product */}
                      <div className="col-span-4">
                        <label className="text-xs text-gray-500 mb-1 block">Product</label>
                        <Select<ProductOption>
                          options={[
                            { value: '', label: 'Manual entry', stock: 0, desc: '', price: 0, gst: 18, hsn: '' },
                            ...listings.map(l => ({ value: l.id, label: l.productName, stock: l.availableStock, desc: l.description, price: l.price, gst: l.gstRate, hsn: l.hsnCode }))
                          ]}
                          value={item.productId ? { value: item.productId, label: listings.find(l => l.id === item.productId)?.productName || item.productName, stock: 0, desc: '', price: 0, gst: 18, hsn: '' } : null}
                          onChange={(opt: SingleValue<ProductOption>) => {
                            if (!opt || opt.value === '') { const items = [...formData.items]; items[idx] = { ...items[idx], productId: '', productName: '' }; setFormData(p => ({ ...p, items })); }
                            else onProductSelect(idx, opt.value);
                          }}
                          placeholder="Search..." isSearchable isClearable styles={productStyles}
                          formatOptionLabel={(o) => o.value === '' ? <span className="text-gray-400 italic">Manual</span> : <span>{o.label} <span className="text-gray-400 text-xs">({o.stock} avail | Rs.{o.price})</span></span>}
                          inputId={`quo-item-product-${idx}`}
                        />
                        {!item.productId && <input type="text" value={item.productName} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], productName: e.target.value }; setFormData(p => ({ ...p, items })); }} placeholder="Product name" className="w-full mt-1 px-2 py-1.5 border rounded text-sm" data-testid={`manual-product-name-${idx}`} />}
                      </div>
                      {/* Rate */}
                      <div className="col-span-1">
                        <label className="text-xs text-gray-500 mb-1 block">Rate</label>
                        <input type="number" value={item.price || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], price: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm" placeholder="0" data-testid={`item-price-${idx}`} />
                      </div>
                      {/* Qty */}
                      <div className="col-span-1">
                        <label className="text-xs text-gray-500 mb-1 block">Qty</label>
                        <input type="number" value={item.quantity || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], quantity: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm" placeholder="1" min={1} data-testid={`item-qty-${idx}`} />
                      </div>
                      {/* Discount */}
                      <div className="col-span-2">
                        <label className="text-xs text-gray-500 mb-1 block">Discount</label>
                        <div className="flex gap-1">
                          <input type="number" value={item.discount || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], discount: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded-l text-sm" placeholder="0" min={0} data-testid={`item-discount-${idx}`} />
                          <button
                            type="button"
                            onClick={() => { const items = [...formData.items]; items[idx] = { ...items[idx], discountType: items[idx].discountType === '%' ? 'Rs' : '%' }; setFormData(p => ({ ...p, items })); }}
                            className="px-2 py-1.5 border rounded-r text-xs font-medium bg-gray-100 hover:bg-gray-200 whitespace-nowrap min-w-[32px]"
                            data-testid={`item-discount-toggle-${idx}`}
                          >
                            {item.discountType === '%' ? <Percent className="w-3 h-3" /> : <span>Rs</span>}
                          </button>
                        </div>
                        {t.discAmt > 0 && <span className="text-xs text-green-600 mt-0.5 block">-Rs.{t.discAmt.toFixed(2)}</span>}
                      </div>
                      {/* GST */}
                      <div className="col-span-1">
                        <label className="text-xs text-gray-500 mb-1 block">GST%</label>
                        <select value={item.gstPercent} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], gstPercent: +e.target.value }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border rounded text-sm" data-testid={`item-gst-${idx}`}>
                          <option value={0}>0%</option><option value={5}>5%</option><option value={12}>12%</option><option value={18}>18%</option><option value={28}>28%</option>
                        </select>
                      </div>
                      {/* Taxable */}
                      <div className="col-span-1">
                        <label className="text-xs text-gray-500 mb-1 block">Taxable</label>
                        <div className="px-2 py-1.5 bg-white border rounded text-sm text-right text-gray-600">{t.taxable.toFixed(2)}</div>
                      </div>
                      {/* Total */}
                      <div className="col-span-1">
                        <label className="text-xs text-gray-500 mb-1 block">Total</label>
                        <div className="px-2 py-1.5 bg-white border rounded text-sm font-semibold text-right flex items-center justify-end">
                          <IndianRupee className="w-3 h-3 mr-0.5" />{t.total.toFixed(2)}
                        </div>
                      </div>
                      {/* Remove */}
                      <div className="pt-6 flex items-start justify-center">
                        {formData.items.length > 1 && <button onClick={() => removeItem(idx)} className="text-gray-400 hover:text-red-500" data-testid={`remove-item-${idx}`}><Trash2 className="w-4 h-4" /></button>}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2" data-testid="add-item-btn">+ Add Item</button>
          </div>

          {/* Totals */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Taxable Amount</span><span data-testid="form-subtotal">Rs.{totals.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">GST</span><span data-testid="form-gst">Rs.{totals.gst.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-2">
              <span>Grand Total</span>
              <span className="flex items-center gap-1" data-testid="form-total"><IndianRupee className="w-4 h-4" />{Math.round(totals.total).toLocaleString('en-IN')}</span>
            </div>
          </div>

          {/* Notes + Validity */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Notes</label>
              <textarea value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} rows={2} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Optional notes..." data-testid="form-notes" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Validity (days)</label>
              <input type="number" value={formData.validityDays} onChange={e => setFormData(p => ({ ...p, validityDays: +e.target.value }))} className="w-full px-3 py-2 border rounded-lg text-sm" min={1} data-testid="form-validity" />
            </div>
          </div>

          {/* Terms */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Terms & Conditions</label>
            <textarea value={formData.termsAndConditions} onChange={e => setFormData(p => ({ ...p, termsAndConditions: e.target.value }))} rows={2} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Optional terms..." data-testid="form-terms" />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={resetForm} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-quotation-btn">Cancel</button>
            <button onClick={handleSubmit} disabled={submitting} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50 flex items-center gap-2" data-testid="submit-quotation-btn">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {!isOnline ? 'Save Offline' : 'Create Quotation'}
            </button>
          </div>
        </div>
      )}

      {/* Quotation List */}
      {quotations.length === 0 && !showForm ? (
        <div className="text-center py-12 bg-white rounded-xl border" data-testid="empty-state">
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
                      <span className="font-mono text-sm font-medium text-gray-900" data-testid={`quo-number-${q.id}`}>{q.quotationNumber}</span>
                      {statusBadge(q)}
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5" data-testid={`quo-buyer-${q.id}`}>{q.buyerName}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900 flex items-center justify-end" data-testid={`quo-total-${q.id}`}><IndianRupee className="w-3 h-3" />{q.total?.toLocaleString('en-IN')}</p>
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
                    <table className="w-full text-sm" data-testid={`quo-items-table-${q.id}`}>
                      <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="pb-1">#</th><th className="pb-1">Product</th><th className="pb-1">Qty</th><th className="pb-1">Rate</th><th className="pb-1">Disc</th><th className="pb-1">GST</th><th className="pb-1 text-right">Total</th></tr></thead>
                      <tbody>
                        {q.items.map((item, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="py-1.5 text-gray-400">{i + 1}</td>
                            <td className="py-1.5">{item.productName}{item.hsnCode ? <span className="text-xs text-gray-400 ml-1">[{item.hsnCode}]</span> : ''}</td>
                            <td>{item.quantity}</td>
                            <td>Rs.{item.price?.toLocaleString('en-IN')}</td>
                            <td>{item.discount ? `${item.discount}${item.discountType === '%' ? '%' : ' Rs'}` : '-'}</td>
                            <td>{item.gstPercent}%</td>
                            <td className="text-right font-medium">Rs.{item.total?.toLocaleString('en-IN')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Summary row */}
                  <div className="flex justify-end gap-6 text-sm border-t pt-2">
                    <span className="text-gray-500">Subtotal: <span className="font-medium text-gray-700">Rs.{q.subtotal?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></span>
                    <span className="text-gray-500">GST: <span className="font-medium text-gray-700">Rs.{q.gst?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></span>
                    <span className="text-gray-700 font-semibold">Total: Rs.{q.total?.toLocaleString('en-IN')}</span>
                  </div>

                  {q.notes && <p className="text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2"><span className="font-medium text-gray-600">Notes:</span> {q.notes}</p>}
                  {q.validityDays && <p className="text-xs text-gray-400">Valid for {q.validityDays} days from {new Date(q.date).toLocaleDateString('en-IN')}</p>}

                  {q.convertedToInvoice && q.convertedInvoiceNumber && (
                    <p className="text-sm text-blue-600 font-medium" data-testid={`converted-info-${q.id}`}>Converted to Invoice: {q.convertedInvoiceNumber}</p>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {/* Download PDF */}
                    <button onClick={() => handleDownloadPdf(q.id, q.quotationNumber)} disabled={downloadingPdf === q.id} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 text-white rounded-lg text-xs font-medium hover:bg-gray-900 disabled:opacity-50" data-testid={`download-pdf-${q.id}`}>
                      {downloadingPdf === q.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} PDF
                    </button>

                    {/* WhatsApp Share with PDF link */}
                    <button onClick={() => handleShareWhatsApp(q)} disabled={sharingWa === q.id} className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50" data-testid={`quotation-whatsapp-${q.id}`}>
                      {sharingWa === q.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <MessageCircle className="w-3.5 h-3.5" />} WhatsApp
                    </button>

                    {/* Convert to Invoice */}
                    {!q.convertedToInvoice && (
                      <button onClick={() => handleConvertToInvoice(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700" data-testid={`convert-to-invoice-${q.id}`}>
                        <ArrowRight className="w-3.5 h-3.5" /> Convert to Invoice
                      </button>
                    )}

                    {/* Mark Sent */}
                    {q.status === 'draft' && !q.convertedToInvoice && (
                      <button onClick={() => handleMarkSent(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200" data-testid={`mark-sent-${q.id}`}>
                        <Send className="w-3.5 h-3.5" /> Mark Sent
                      </button>
                    )}

                    {/* Delete */}
                    {!q.convertedToInvoice && (
                      <button onClick={() => handleDelete(q.id)} className="flex items-center gap-1.5 px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium" data-testid={`delete-quotation-${q.id}`}>
                        <Trash2 className="w-3.5 h-3.5" /> Delete
                      </button>
                    )}
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
