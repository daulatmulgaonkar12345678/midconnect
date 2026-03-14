"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import { Plus, FileText, Download, Trash2, Search, Eye, ChevronDown, Send, CreditCard, X, IndianRupee } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface InvoiceItem {
  productId?: string;
  productName: string;
  quantity: number;
  price: number;
  gstPercent: number;
  gstAmount: number;
  total: number;
}

interface Invoice {
  id: string;
  invoiceNumber: string;
  buyerId: string;
  buyerName: string;
  date: string;
  items: InvoiceItem[];
  subtotal: number;
  gst: number;
  total: number;
  status: string;
  notes?: string;
  createdAt: string;
}

interface Buyer {
  id: string;
  buyerName: string;
  company?: string;
}

interface Listing {
  id: string;
  productName: string;
  stock: number;
  price?: number;
}

export default function InvoicesPage() {
  const { hasPermission, token } = usePermissions();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [viewInvoice, setViewInvoice] = useState<Invoice | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [formData, setFormData] = useState({
    buyerId: "",
    notes: "",
    deductStock: true,
    items: [{ productId: "", productName: "", quantity: 1, price: 0, gstPercent: 18 }] as { productId: string; productName: string; quantity: number; price: number; gstPercent: number }[]
  });

  const authHeaders = useCallback(() => ({
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }), [token]);

  const fetchInvoices = useCallback(async () => {
    try {
      let url = `${API_URL}/api/business-tools/invoices?limit=100`;
      if (statusFilter) url += `&status=${statusFilter}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setInvoices(data.invoices || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [token, statusFilter]);

  const fetchBuyers = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/buyers`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setBuyers(data.buyers || []);
    } catch { /* empty */ }
  }, [token]);

  const fetchListings = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/inventory`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setListings((data.listings || []).map((l: Record<string, unknown>) => ({
        id: l.id as string, productName: l.productName as string, stock: l.stock as number, price: (l.price as number) || 0
      })));
    } catch { /* empty */ }
  }, [token]);

  useEffect(() => { if (token) { fetchInvoices(); fetchBuyers(); fetchListings(); } }, [token, fetchInvoices, fetchBuyers, fetchListings]);

  const calcLineTotal = (qty: number, price: number, gstPct: number) => {
    const sub = qty * price;
    const gst = sub * gstPct / 100;
    return { subtotal: sub, gstAmount: Math.round(gst * 100) / 100, total: Math.round((sub + gst) * 100) / 100 };
  };

  const formTotals = formData.items.reduce((acc, item) => {
    const { subtotal, gstAmount, total } = calcLineTotal(item.quantity, item.price, item.gstPercent);
    return { subtotal: acc.subtotal + subtotal, gst: acc.gst + gstAmount, total: acc.total + total };
  }, { subtotal: 0, gst: 0, total: 0 });

  const handleSubmit = async () => {
    if (!formData.buyerId || formData.items.every(i => !i.productName && !i.productId)) return;
    const items = formData.items.filter(i => i.productName || i.productId).map(i => ({
      productId: i.productId || undefined,
      productName: i.productName || undefined,
      quantity: i.quantity,
      price: i.price,
      gstPercent: i.gstPercent
    }));
    const res = await fetch(`${API_URL}/api/business-tools/invoices`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ buyerId: formData.buyerId, items, notes: formData.notes, deductStock: formData.deductStock })
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || "Failed to create invoice"); return; }
    setShowForm(false);
    setFormData({ buyerId: "", notes: "", deductStock: true, items: [{ productId: "", productName: "", quantity: 1, price: 0, gstPercent: 18 }] });
    fetchInvoices();
    fetchListings();
  };

  const updateStatus = async (id: string, status: string) => {
    await fetch(`${API_URL}/api/business-tools/invoices/${id}/status`, {
      method: "PUT", headers: authHeaders(), body: JSON.stringify({ status })
    });
    fetchInvoices();
    if (viewInvoice?.id === id) setViewInvoice(prev => prev ? { ...prev, status } : null);
  };

  const downloadPdf = async (id: string, invoiceNumber: string) => {
    const res = await fetch(`${API_URL}/api/business-tools/invoices/${id}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${invoiceNumber}.pdf`; a.click();
    URL.revokeObjectURL(url);
  };

  const deleteInvoice = async (id: string) => {
    if (!confirm("Delete this invoice?")) return;
    const res = await fetch(`${API_URL}/api/business-tools/invoices/${id}`, { method: "DELETE", headers: authHeaders() });
    if (!res.ok) { const d = await res.json(); alert(d.detail || "Cannot delete"); return; }
    fetchInvoices();
    if (viewInvoice?.id === id) setViewInvoice(null);
  };

  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    sent: "bg-blue-50 text-blue-700",
    paid: "bg-green-50 text-green-700",
    cancelled: "bg-red-50 text-red-700"
  };

  const addItem = () => setFormData(prev => ({ ...prev, items: [...prev.items, { productId: "", productName: "", quantity: 1, price: 0, gstPercent: 18 }] }));
  const removeItem = (idx: number) => setFormData(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== idx) }));

  const filteredInvoices = invoices.filter(inv =>
    !search || inv.invoiceNumber.toLowerCase().includes(search.toLowerCase()) || inv.buyerName?.toLowerCase().includes(search.toLowerCase())
  );

  if (!hasPermission("create_invoice")) {
    return <div className="p-6 text-center text-gray-500" data-testid="no-permission">You do not have permission to manage invoices.</div>;
  }

  return (
    <div className="space-y-6" data-testid="invoices-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Create and manage invoices with GST calculation</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          data-testid="create-invoice-btn">
          <Plus className="w-4 h-4" /> New Invoice
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search invoices..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm" data-testid="search-input" />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm" data-testid="status-filter">
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Create Invoice Form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-form-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Invoice</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Buyer *</label>
                <select value={formData.buyerId} onChange={e => setFormData(p => ({ ...p, buyerId: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="buyer-select">
                  <option value="">Select buyer</option>
                  {buyers.map(b => <option key={b.id} value={b.id}>{b.buyerName}{b.company ? ` (${b.company})` : ""}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Items *</label>
                <div className="space-y-2">
                  {formData.items.map((item, idx) => {
                    const lineTotals = calcLineTotal(item.quantity, item.price, item.gstPercent);
                    return (
                      <div key={idx} className="grid grid-cols-12 gap-2 items-start bg-gray-50 p-3 rounded-lg">
                        <div className="col-span-4">
                          <label className="text-xs text-gray-500 mb-1 block">Product</label>
                          <select value={item.productId} onChange={e => {
                            const listing = listings.find(l => l.id === e.target.value);
                            const items = [...formData.items];
                            items[idx] = { ...items[idx], productId: e.target.value, productName: listing?.productName || "", price: listing?.price || items[idx].price };
                            setFormData(p => ({ ...p, items }));
                          }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-product-${idx}`}>
                            <option value="">Select / Manual</option>
                            {listings.map(l => <option key={l.id} value={l.id}>{l.productName} (Stock: {l.stock})</option>)}
                          </select>
                          {!item.productId && (
                            <input type="text" value={item.productName} onChange={e => {
                              const items = [...formData.items];
                              items[idx].productName = e.target.value;
                              setFormData(p => ({ ...p, items }));
                            }} placeholder="Manual entry" className="w-full mt-1 px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-name-${idx}`} />
                          )}
                        </div>
                        <div className="col-span-1">
                          <label className="text-xs text-gray-500 mb-1 block">Qty</label>
                          <input type="number" min={1} value={item.quantity} onChange={e => {
                            const items = [...formData.items]; items[idx].quantity = parseInt(e.target.value) || 1;
                            setFormData(p => ({ ...p, items }));
                          }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm text-center" data-testid={`invoice-item-qty-${idx}`} />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs text-gray-500 mb-1 block">Price</label>
                          <input type="number" min={0} step={0.01} value={item.price} onChange={e => {
                            const items = [...formData.items]; items[idx].price = parseFloat(e.target.value) || 0;
                            setFormData(p => ({ ...p, items }));
                          }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-price-${idx}`} />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs text-gray-500 mb-1 block">GST %</label>
                          <select value={item.gstPercent} onChange={e => {
                            const items = [...formData.items]; items[idx].gstPercent = parseFloat(e.target.value);
                            setFormData(p => ({ ...p, items }));
                          }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-gst-${idx}`}>
                            <option value={0}>0%</option>
                            <option value={5}>5%</option>
                            <option value={12}>12%</option>
                            <option value={18}>18%</option>
                            <option value={28}>28%</option>
                          </select>
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs text-gray-500 mb-1 block">Total</label>
                          <div className="px-2 py-1.5 bg-white border border-gray-200 rounded text-sm font-medium text-right">
                            {lineTotals.total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                          <div className="text-[10px] text-gray-400 text-right mt-0.5">GST: {lineTotals.gstAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                        </div>
                        <div className="col-span-1 pt-5">
                          {formData.items.length > 1 && (
                            <button onClick={() => removeItem(idx)} className="text-red-400 hover:text-red-600" data-testid={`remove-invoice-item-${idx}`}>
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2" data-testid="add-invoice-item-btn">
                  + Add Item
                </button>
              </div>

              {/* Totals */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{formTotals.subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{formTotals.gst.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-2">
                  <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{formTotals.total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="deductStock" checked={formData.deductStock}
                  onChange={e => setFormData(p => ({ ...p, deductStock: e.target.checked }))}
                  className="rounded" data-testid="deduct-stock-checkbox" />
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
              <button onClick={handleSubmit} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium" data-testid="submit-invoice-btn">
                Create Invoice
              </button>
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
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[viewInvoice.status] || ""}`}>{viewInvoice.status}</span>
              </div>
              <button onClick={() => setViewInvoice(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
              <div><span className="text-gray-500">Buyer:</span> <span className="font-medium">{viewInvoice.buyerName}</span></div>
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{new Date(viewInvoice.date).toLocaleDateString("en-IN")}</span></div>
            </div>
            <table className="w-full text-sm mb-4">
              <thead><tr className="border-b border-gray-200 text-gray-500 text-xs uppercase">
                <th className="text-left py-2">Product</th><th className="text-right py-2">Qty</th><th className="text-right py-2">Price</th>
                <th className="text-right py-2">GST%</th><th className="text-right py-2">GST</th><th className="text-right py-2">Total</th>
              </tr></thead>
              <tbody>
                {viewInvoice.items.map((item, i) => (
                  <tr key={i} className="border-b border-gray-50">
                    <td className="py-2">{item.productName}</td>
                    <td className="py-2 text-right">{item.quantity}</td>
                    <td className="py-2 text-right">{item.price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                    <td className="py-2 text-right">{item.gstPercent}%</td>
                    <td className="py-2 text-right">{item.gstAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                    <td className="py-2 text-right font-medium">{item.total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm mb-4">
              <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{viewInvoice.subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{viewInvoice.gst.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
              <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-2">
                <span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{viewInvoice.total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
            {viewInvoice.notes && <div className="text-sm text-gray-600 mb-4"><span className="font-medium">Notes:</span> {viewInvoice.notes}</div>}
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => downloadPdf(viewInvoice.id, viewInvoice.invoiceNumber)}
                className="flex items-center gap-1 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-indigo-700"
                data-testid="download-pdf-btn"><Download className="w-4 h-4" /> Download PDF</button>
              {viewInvoice.status === "draft" && (
                <button onClick={() => updateStatus(viewInvoice.id, "sent")}
                  className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                  data-testid="mark-sent-btn"><Send className="w-4 h-4" /> Mark Sent</button>
              )}
              {(viewInvoice.status === "draft" || viewInvoice.status === "sent") && (
                <button onClick={() => updateStatus(viewInvoice.id, "paid")}
                  className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700"
                  data-testid="mark-paid-btn"><CreditCard className="w-4 h-4" /> Mark Paid</button>
              )}
              {viewInvoice.status !== "cancelled" && viewInvoice.status !== "paid" && (
                <button onClick={() => updateStatus(viewInvoice.id, "cancelled")}
                  className="text-red-500 hover:text-red-700 px-3 py-1.5 text-sm font-medium" data-testid="cancel-invoice-btn">Cancel</button>
              )}
              {(viewInvoice.status === "draft" || viewInvoice.status === "cancelled") && (
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
          <table className="w-full text-sm">
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
                  <td className="px-4 py-3 text-gray-500">{new Date(inv.date).toLocaleDateString("en-IN")}</td>
                  <td className="px-4 py-3 text-right font-medium flex items-center justify-end gap-0.5"><IndianRupee className="w-3.5 h-3.5" />{inv.total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[inv.status] || ""}`}>{inv.status}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => setViewInvoice(inv)} className="text-gray-400 hover:text-indigo-600" data-testid={`view-invoice-${inv.id}`}><Eye className="w-4 h-4" /></button>
                      <button onClick={() => downloadPdf(inv.id, inv.invoiceNumber)} className="text-gray-400 hover:text-indigo-600" data-testid={`download-invoice-${inv.id}`}><Download className="w-4 h-4" /></button>
                      {(inv.status === "draft" || inv.status === "cancelled") && (
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
