"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import { Plus, Package, Trash2, ShoppingCart, ChevronDown, ChevronUp, Search, AlertCircle, IndianRupee } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Category { id: string; name: string; }
interface AdminProduct { id: string; name: string; }
interface SellerInventoryItem { listingId: string; productName: string; stock: number; sku: string; }

interface CompositeComponent {
  listingId: string;
  productName?: string;
  quantity: number;
  currentStock?: number;
}

interface CompositeProduct {
  id: string;
  productId: string;
  categoryId: string;
  productName: string;
  categoryName: string;
  name: string;
  description?: string;
  price?: number;
  components: CompositeComponent[];
  availableStock: number;
  createdAt: string;
}

interface FormComponent { listingId: string; quantity: number; }

export default function CompositeProductsPage() {
  const { hasPermission, token } = usePermissions();
  const [products, setProducts] = useState<CompositeProduct[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [catProducts, setCatProducts] = useState<Record<string, AdminProduct[]>>({});
  const [sellerInventory, setSellerInventory] = useState<SellerInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sellQty, setSellQty] = useState<Record<string, number>>({});
  const [search, setSearch] = useState("");

  const [form, setForm] = useState({
    categoryId: "", productId: "", description: "", price: 0,
    components: [{ listingId: "", quantity: 1 }] as FormComponent[]
  });

  const authHeaders = useCallback(() => ({ "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }), [token]);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/composite-products?search=${search}`, { headers: { Authorization: `Bearer ${token}` } });
      setProducts((await res.json()).compositeProducts || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [token, search]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/categories/all`);
      setCategories((await res.json() || []).map((c: Record<string, string>) => ({ id: c.id || c._id, name: c.name })));
    } catch { /* empty */ }
  }, []);

  const fetchSellerInventory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/composite-products/seller-inventory`, { headers: { Authorization: `Bearer ${token}` } });
      setSellerInventory((await res.json()).inventory || []);
    } catch { /* empty */ }
  }, [token]);

  useEffect(() => { if (token) { fetchProducts(); fetchCategories(); fetchSellerInventory(); } }, [token, fetchProducts, fetchCategories, fetchSellerInventory]);

  const loadCatProducts = async (categoryId: string) => {
    if (catProducts[categoryId]) return;
    try {
      const res = await fetch(`${API_URL}/api/products/by-category/${categoryId}`);
      setCatProducts(prev => ({
        ...prev,
        [categoryId]: (await res.json() || []).map((p: Record<string, string>) => ({ id: p.id || p._id, name: p.name }))
      }));
    } catch { /* empty */ }
  };

  const handleSubmit = async () => {
    const validComps = form.components.filter(c => c.listingId && c.quantity > 0);
    if (!form.categoryId || !form.productId || !form.price || validComps.length === 0) return;

    const url = editingId
      ? `${API_URL}/api/business-tools/composite-products/${editingId}`
      : `${API_URL}/api/business-tools/composite-products`;

    const body = editingId
      ? { description: form.description, price: form.price, components: validComps }
      : { categoryId: form.categoryId, productId: form.productId, description: form.description, price: form.price, components: validComps };

    const res = await fetch(url, { method: editingId ? "PUT" : "POST", headers: authHeaders(), body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || "Failed"); return; }
    setShowForm(false); setEditingId(null); resetForm();
    fetchProducts(); fetchSellerInventory();
  };

  const resetForm = () => setForm({ categoryId: "", productId: "", description: "", price: 0, components: [{ listingId: "", quantity: 1 }] });

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this composite product?")) return;
    await fetch(`${API_URL}/api/business-tools/composite-products/${id}`, { method: "DELETE", headers: authHeaders() });
    fetchProducts();
  };

  const handleSell = async (id: string) => {
    const qty = sellQty[id] || 1;
    const res = await fetch(`${API_URL}/api/business-tools/composite-products/${id}/sell`, {
      method: "POST", headers: authHeaders(), body: JSON.stringify({ quantity: qty })
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || "Failed to sell"); return; }
    alert(`Sold! Stock deducted for ${data.deductions?.length || 0} components`);
    fetchProducts(); fetchSellerInventory();
  };

  const startEdit = (cp: CompositeProduct) => {
    setForm({
      categoryId: cp.categoryId || "",
      productId: cp.productId || "",
      description: cp.description || "",
      price: cp.price || 0,
      components: cp.components?.length > 0
        ? cp.components.map(c => ({ listingId: c.listingId || "", quantity: c.quantity }))
        : [{ listingId: "", quantity: 1 }]
    });
    if (cp.categoryId) loadCatProducts(cp.categoryId);
    setEditingId(cp.id);
    setShowForm(true);
  };

  const addComponent = () => setForm(prev => ({ ...prev, components: [...prev.components, { listingId: "", quantity: 1 }] }));
  const removeComponent = (idx: number) => setForm(prev => ({ ...prev, components: prev.components.filter((_, i) => i !== idx) }));

  if (!hasPermission("manage_inventory")) {
    return <div className="p-6 text-center text-gray-500" data-testid="no-permission">You do not have permission to manage composite products.</div>;
  }

  const currentCatProducts = catProducts[form.categoryId] || [];

  return (
    <div className="space-y-6" data-testid="composite-products-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Composite Products</h1>
          <p className="text-sm text-gray-500 mt-1">Create product bundles from your inventory</p>
        </div>
        <button onClick={() => { setShowForm(true); setEditingId(null); resetForm(); }}
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
          <div className="bg-white rounded-xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-lg font-semibold mb-4">{editingId ? "Edit" : "Create"} Composite Product</h2>
            <div className="space-y-5">

              {/* Section 1: Product Identity from Admin Catalog */}
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 space-y-3">
                <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Product Identity (from catalog)</p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
                    <select value={form.categoryId}
                      onChange={e => { setForm(p => ({ ...p, categoryId: e.target.value, productId: "" })); if (e.target.value) loadCatProducts(e.target.value); }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                      disabled={!!editingId}
                      data-testid="category-select">
                      <option value="">Select category</option>
                      {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Product Name *</label>
                    <select value={form.productId}
                      onChange={e => setForm(p => ({ ...p, productId: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                      disabled={!form.categoryId || !!editingId}
                      data-testid="product-select">
                      <option value="">{form.categoryId ? "Select product" : "Select category first"}</option>
                      {currentCatProducts.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} placeholder="Optional description"
                    data-testid="description-input" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bundle Price *</label>
                  <div className="relative">
                    <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input type="number" min={0} step={0.01} value={form.price} onChange={e => setForm(p => ({ ...p, price: parseFloat(e.target.value) || 0 }))}
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="0.00"
                      data-testid="price-input" />
                  </div>
                </div>
              </div>

              {/* Section 2: Components from Seller Inventory */}
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-4 space-y-3">
                <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Components (from your inventory)</p>

                {sellerInventory.length === 0 && (
                  <div className="bg-white border border-amber-200 rounded-lg p-3">
                    <p className="text-sm text-amber-700">No inventory items found. Add products to your seller listings first.</p>
                  </div>
                )}

                {form.components.map((comp, idx) => {
                  const selected = sellerInventory.find(i => i.listingId === comp.listingId);
                  return (
                    <div key={idx} className="flex gap-2 items-center bg-white rounded-lg p-2 border border-amber-100">
                      <div className="flex-1">
                        <select value={comp.listingId}
                          onChange={e => {
                            const comps = [...form.components];
                            comps[idx] = { ...comps[idx], listingId: e.target.value };
                            setForm(p => ({ ...p, components: comps }));
                          }}
                          className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                          data-testid={`component-select-${idx}`}>
                          <option value="">Select inventory item</option>
                          {sellerInventory.map(item => (
                            <option key={item.listingId} value={item.listingId}>
                              {item.productName} (Stock: {item.stock})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="w-20">
                        <input type="number" min={1} value={comp.quantity}
                          onChange={e => {
                            const comps = [...form.components];
                            comps[idx] = { ...comps[idx], quantity: parseInt(e.target.value) || 1 };
                            setForm(p => ({ ...p, components: comps }));
                          }}
                          className="w-full px-2 py-2 border border-gray-300 rounded-lg text-sm text-center"
                          placeholder="Qty"
                          data-testid={`component-qty-${idx}`} />
                      </div>
                      {form.components.length > 1 && (
                        <button onClick={() => removeComponent(idx)} className="text-red-400 hover:text-red-600 p-1" data-testid={`remove-component-${idx}`}>
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  );
                })}
                <button onClick={addComponent} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium" data-testid="add-component-btn">
                  + Add Component
                </button>
              </div>
            </div>

            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => { setShowForm(false); setEditingId(null); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-btn">Cancel</button>
              <button onClick={handleSubmit}
                disabled={editingId ? (!form.price || form.components.every(c => !c.listingId)) : (!form.categoryId || !form.productId || !form.price || form.components.every(c => !c.listingId))}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                data-testid="submit-btn">
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
                    <h3 className="font-medium text-gray-900">{cp.productName || cp.name}</h3>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                      {cp.categoryName && <span className="text-indigo-500">{cp.categoryName}</span>}
                      <span>{cp.components?.length || 0} components</span>
                      {cp.price != null && (
                        <span className="flex items-center gap-0.5 font-medium text-gray-700">
                          <IndianRupee className="w-3 h-3" />{cp.price.toLocaleString("en-IN")}
                        </span>
                      )}
                      <span className={`font-medium ${cp.availableStock > 0 ? "text-green-600" : "text-red-500"}`}>
                        {cp.availableStock > 0 ? `${cp.availableStock} available` : "Out of stock"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {cp.availableStock > 0 && (
                    <div className="flex items-center gap-1 mr-2">
                      <input type="number" min={1} max={cp.availableStock} value={sellQty[cp.id] || 1}
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
                  )}
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
                        <th className="text-right pb-2">In Stock</th>
                        <th className="text-right pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cp.components?.map((comp, idx) => {
                        const isLow = (comp.currentStock || 0) < comp.quantity;
                        return (
                          <tr key={idx} className="border-t border-gray-100">
                            <td className="py-2 text-gray-700 font-medium">{comp.productName || "Unknown"}</td>
                            <td className="py-2 text-right text-gray-700">{comp.quantity}</td>
                            <td className="py-2 text-right text-gray-700">{comp.currentStock ?? 0}</td>
                            <td className="py-2 text-right">
                              {(comp.currentStock || 0) === 0 ? (
                                <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full font-medium">Out</span>
                              ) : isLow ? (
                                <span className="inline-flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
                                  <AlertCircle className="w-3 h-3" /> Low
                                </span>
                              ) : (
                                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full font-medium">OK</span>
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
