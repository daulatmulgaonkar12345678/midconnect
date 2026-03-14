"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import { Plus, Package, Trash2, ShoppingCart, ChevronDown, ChevronUp, Search, AlertCircle } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface CompositeItem {
  productId: string;
  productName?: string;
  quantity: number;
  currentStock?: number;
}

interface CompositeProduct {
  id: string;
  name: string;
  description?: string;
  items: CompositeItem[];
  createdAt: string;
}

interface SellerListing {
  id: string;
  productName: string;
  stock: number;
  sku?: string;
}

export default function CompositeProductsPage() {
  const { hasPermission, token } = usePermissions();
  const [products, setProducts] = useState<CompositeProduct[]>([]);
  const [listings, setListings] = useState<SellerListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sellQty, setSellQty] = useState<Record<string, number>>({});
  const [search, setSearch] = useState("");
  const [formData, setFormData] = useState({ name: "", description: "", items: [{ productId: "", quantity: 1 }] as { productId: string; quantity: number }[] });

  const headers = useCallback(() => ({
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }), [token]);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/composite-products?search=${search}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setProducts(data.compositeProducts || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [token, search]);

  const fetchListings = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/inventory`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setListings((data.listings || []).map((l: Record<string, unknown>) => ({ id: l.id, productName: l.productName, stock: l.stock, sku: l.sku })));
    } catch { /* empty */ }
  }, [token]);

  useEffect(() => { if (token) { fetchProducts(); fetchListings(); } }, [token, fetchProducts, fetchListings]);

  const handleSubmit = async () => {
    const validItems = formData.items.filter(i => i.productId && i.quantity > 0);
    if (!formData.name || validItems.length === 0) return;

    const url = editingId
      ? `${API_URL}/api/business-tools/composite-products/${editingId}`
      : `${API_URL}/api/business-tools/composite-products`;

    await fetch(url, {
      method: editingId ? "PUT" : "POST",
      headers: headers(),
      body: JSON.stringify({ ...formData, items: validItems })
    });
    setShowForm(false);
    setEditingId(null);
    setFormData({ name: "", description: "", items: [{ productId: "", quantity: 1 }] });
    fetchProducts();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this composite product?")) return;
    await fetch(`${API_URL}/api/business-tools/composite-products/${id}`, { method: "DELETE", headers: headers() });
    fetchProducts();
  };

  const handleSell = async (id: string) => {
    const qty = sellQty[id] || 1;
    const res = await fetch(`${API_URL}/api/business-tools/composite-products/${id}/sell`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ quantity: qty })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Failed to sell");
      return;
    }
    alert(`Sold! Stock deducted for ${data.deductions?.length || 0} components`);
    fetchProducts();
    fetchListings();
  };

  const startEdit = (cp: CompositeProduct) => {
    setFormData({
      name: cp.name,
      description: cp.description || "",
      items: cp.items.map(i => ({ productId: i.productId || "", quantity: i.quantity }))
    });
    setEditingId(cp.id);
    setShowForm(true);
  };

  const addItem = () => setFormData(prev => ({ ...prev, items: [...prev.items, { productId: "", quantity: 1 }] }));
  const removeItem = (idx: number) => setFormData(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== idx) }));

  if (!hasPermission("manage_inventory")) {
    return <div className="p-6 text-center text-gray-500" data-testid="no-permission">You do not have permission to manage composite products.</div>;
  }

  return (
    <div className="space-y-6" data-testid="composite-products-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Composite Products</h1>
          <p className="text-sm text-gray-500 mt-1">Create product bundles from existing inventory items</p>
        </div>
        <button onClick={() => { setShowForm(true); setEditingId(null); setFormData({ name: "", description: "", items: [{ productId: "", quantity: 1 }] }); }}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          data-testid="create-composite-btn">
          <Plus className="w-4 h-4" /> Create Bundle
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search bundles..."
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          data-testid="search-input" />
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="composite-form-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto p-6">
            <h2 className="text-lg font-semibold mb-4">{editingId ? "Edit" : "Create"} Composite Product</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input type="text" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Electrical Panel Kit"
                  data-testid="composite-name-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2}
                  data-testid="composite-desc-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Components *</label>
                {formData.items.map((item, idx) => (
                  <div key={idx} className="flex gap-2 mb-2 items-center">
                    <select value={item.productId} onChange={e => {
                      const newItems = [...formData.items];
                      newItems[idx].productId = e.target.value;
                      setFormData(p => ({ ...p, items: newItems }));
                    }} className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid={`item-product-${idx}`}>
                      <option value="">Select product</option>
                      {listings.map(l => <option key={l.id} value={l.id}>{l.productName} (Stock: {l.stock})</option>)}
                    </select>
                    <input type="number" min={1} value={item.quantity} onChange={e => {
                      const newItems = [...formData.items];
                      newItems[idx].quantity = parseInt(e.target.value) || 1;
                      setFormData(p => ({ ...p, items: newItems }));
                    }} className="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm text-center" data-testid={`item-qty-${idx}`} />
                    {formData.items.length > 1 && (
                      <button onClick={() => removeItem(idx)} className="text-red-500 hover:text-red-700 p-1" data-testid={`remove-item-${idx}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-1" data-testid="add-item-btn">
                  + Add Component
                </button>
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => { setShowForm(false); setEditingId(null); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-form-btn">Cancel</button>
              <button onClick={handleSubmit} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700" data-testid="submit-form-btn">
                {editingId ? "Update" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Products List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : products.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100" data-testid="empty-state">
          <Package className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No composite products yet</p>
          <p className="text-sm text-gray-400 mt-1">Create your first product bundle to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map(cp => (
            <div key={cp.id} className="bg-white border border-gray-100 rounded-xl overflow-hidden" data-testid={`composite-card-${cp.id}`}>
              <div className="p-4 flex items-center justify-between cursor-pointer" onClick={() => setExpandedId(expandedId === cp.id ? null : cp.id)}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center">
                    <Package className="w-5 h-5 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{cp.name}</h3>
                    <p className="text-xs text-gray-500">{cp.items?.length || 0} components</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1 mr-2">
                    <input type="number" min={1} value={sellQty[cp.id] || 1}
                      onChange={e => setSellQty(p => ({ ...p, [cp.id]: parseInt(e.target.value) || 1 }))}
                      onClick={e => e.stopPropagation()}
                      className="w-16 px-2 py-1 border border-gray-200 rounded-md text-sm text-center"
                      data-testid={`sell-qty-${cp.id}`} />
                    <button onClick={e => { e.stopPropagation(); handleSell(cp.id); }}
                      className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-700"
                      data-testid={`sell-btn-${cp.id}`}>
                      <ShoppingCart className="w-3.5 h-3.5" /> Sell
                    </button>
                  </div>
                  <button onClick={e => { e.stopPropagation(); startEdit(cp); }} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium" data-testid={`edit-btn-${cp.id}`}>Edit</button>
                  <button onClick={e => { e.stopPropagation(); handleDelete(cp.id); }} className="text-sm text-red-500 hover:text-red-700" data-testid={`delete-btn-${cp.id}`}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                  {expandedId === cp.id ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                </div>
              </div>
              {expandedId === cp.id && (
                <div className="border-t border-gray-100 p-4 bg-gray-50">
                  {cp.description && <p className="text-sm text-gray-600 mb-3">{cp.description}</p>}
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-500 text-xs uppercase">
                        <th className="text-left pb-2">Component</th>
                        <th className="text-right pb-2">Qty/Unit</th>
                        <th className="text-right pb-2">Current Stock</th>
                        <th className="text-right pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cp.items?.map((item, idx) => {
                        const isLow = (item.currentStock || 0) < item.quantity;
                        return (
                          <tr key={idx} className="border-t border-gray-100">
                            <td className="py-2 text-gray-700">{item.productName || "Unknown"}</td>
                            <td className="py-2 text-right text-gray-700">{item.quantity}</td>
                            <td className="py-2 text-right text-gray-700">{item.currentStock ?? 0}</td>
                            <td className="py-2 text-right">
                              {isLow ? (
                                <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                                  <AlertCircle className="w-3 h-3" /> Low
                                </span>
                              ) : (
                                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">OK</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
