'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { 
  Plus, Pencil, Trash2, Truck, Loader2, X, AlertTriangle,
  Search, Phone, Mail, MapPin, User, Package2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SupplierProduct {
  id?: string;
  listingId: string;
  productName?: string;
  description?: string;
  sku?: string;
  rate: number;
}

interface Supplier {
  id: string;
  supplierName: string;
  contact?: string;
  phone?: string;
  email?: string;
  gstNumber?: string;
  address?: string;
  notes?: string;
  products?: SupplierProduct[];
  createdAt: string;
}

interface InventoryItem {
  listingId: string;
  productName: string;
  sku: string;
  description?: string;
}

export default function SuppliersPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);

  // Form state
  const [formData, setFormData] = useState({
    supplierName: '', contact: '', phone: '', email: '',
    gstNumber: '', address: '', notes: ''
  });
  const [productMappings, setProductMappings] = useState<SupplierProduct[]>([]);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const loadSuppliers = useCallback(async () => {
    try {
      const h = await authHeaders();
      const url = new URL(`${API_URL}/api/business-tools/suppliers`);
      if (searchQuery) url.searchParams.set('search', searchQuery);
      const response = await fetch(url.toString(), { headers: h });
      if (!response.ok) throw new Error('Failed to load suppliers');
      const data = await response.json();
      setSuppliers(data.suppliers || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  }, [authHeaders, searchQuery]);

  const loadInventoryItems = useCallback(async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/inventory?limit=200`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setInventoryItems((data.inventory || []).map((item: Record<string, string>) => ({
          listingId: item.listingId,
          productName: item.productName,
          sku: item.sku || '',
        })));
      }
    } catch { /* empty */ }
  }, [authHeaders]);

  useEffect(() => {
    const t = setTimeout(loadSuppliers, 300);
    return () => clearTimeout(t);
  }, [loadSuppliers]);

  const openCreateModal = () => {
    setEditingSupplier(null);
    setFormData({ supplierName: '', contact: '', phone: '', email: '', gstNumber: '', address: '', notes: '' });
    setProductMappings([]);
    loadInventoryItems();
    setShowModal(true);
  };

  const openEditModal = async (supplier: Supplier) => {
    setEditingSupplier(supplier);
    setFormData({
      supplierName: supplier.supplierName,
      contact: supplier.contact || '', phone: supplier.phone || '',
      email: supplier.email || '', gstNumber: supplier.gstNumber || '',
      address: supplier.address || '', notes: supplier.notes || ''
    });
    loadInventoryItems();
    // Fetch supplier details with product mappings
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/suppliers/${supplier.id}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setProductMappings(data.supplier.products || []);
      } else {
        setProductMappings([]);
      }
    } catch {
      setProductMappings([]);
    }
    setShowModal(true);
  };

  const addProductMapping = () => {
    setProductMappings(prev => [...prev, { listingId: '', rate: 0 }]);
  };

  const removeProductMapping = (index: number) => {
    setProductMappings(prev => prev.filter((_, i) => i !== index));
  };

  const updateProductMapping = (index: number, field: string, value: string | number) => {
    setProductMappings(prev => prev.map((p, i) => i === index ? { ...p, [field]: value } : p));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const h = await authHeaders();
      const url = editingSupplier
        ? `${API_URL}/api/business-tools/suppliers/${editingSupplier.id}`
        : `${API_URL}/api/business-tools/suppliers`;

      const validProducts = productMappings.filter(p => p.listingId && p.rate > 0);
      const body = {
        ...formData,
        products: validProducts.map(p => ({ listingId: p.listingId, rate: p.rate }))
      };

      const response = await fetch(url, {
        method: editingSupplier ? 'PUT' : 'POST',
        headers: h, body: JSON.stringify(body)
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save supplier');
      }

      setShowModal(false);
      loadSuppliers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save supplier');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (supplierId: string) => {
    try {
      const h = await authHeaders();
      const response = await fetch(`${API_URL}/api/business-tools/suppliers/${supplierId}`, {
        method: 'DELETE', headers: h
      });
      if (!response.ok) { const data = await response.json(); throw new Error(data.detail || 'Failed to delete'); }
      setDeleteConfirm(null);
      loadSuppliers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete supplier');
    }
  };

  if (!hasPermission('manage_suppliers')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Truck className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to manage suppliers.</p>
      </div>
    );
  }

  if (loading && suppliers.length === 0) {
    return (<div className="flex items-center justify-center min-h-[400px]"><Loader2 className="h-8 w-8 animate-spin text-purple-600" /></div>);
  }

  const selectedListingName = (listingId: string) => {
    const item = inventoryItems.find(i => i.listingId === listingId);
    return item ? `${item.productName}${item.sku ? ` (${item.sku})` : ''}` : '';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
          <p className="text-gray-600 mt-1">Manage your supplier network and product mappings</p>
        </div>
        <button onClick={openCreateModal} data-testid="add-supplier-btn"
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition">
          <Plus className="h-5 w-5" /> Add Supplier
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search suppliers by name, contact, email..."
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500" />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto"><X className="h-5 w-5 text-red-600" /></button>
        </div>
      )}

      {/* Suppliers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.map((supplier) => (
          <div key={supplier.id} className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition" data-testid={`supplier-card-${supplier.id}`}>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                  <Truck className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{supplier.supplierName}</h3>
                  {supplier.contact && (
                    <p className="text-sm text-gray-500 flex items-center gap-1"><User className="h-3.5 w-3.5" />{supplier.contact}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => openEditModal(supplier)} className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg" data-testid={`edit-supplier-${supplier.id}`}>
                  <Pencil className="h-4 w-4" />
                </button>
                {deleteConfirm === supplier.id ? (
                  <>
                    <button onClick={() => handleDelete(supplier.id)} className="p-1.5 text-white bg-red-600 hover:bg-red-700 rounded-lg">
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <button onClick={() => setDeleteConfirm(null)} className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg">
                      <X className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <button onClick={() => setDeleteConfirm(supplier.id)} className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg">
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-2 text-sm">
              {supplier.phone && (<p className="flex items-center gap-2 text-gray-600"><Phone className="h-4 w-4 text-gray-400" />{supplier.phone}</p>)}
              {supplier.email && (<p className="flex items-center gap-2 text-gray-600"><Mail className="h-4 w-4 text-gray-400" />{supplier.email}</p>)}
              {supplier.address && (<p className="flex items-center gap-2 text-gray-600"><MapPin className="h-4 w-4 text-gray-400" /><span className="truncate">{supplier.address}</span></p>)}
            </div>

            {supplier.gstNumber && (
              <div className="mt-3 pt-3 border-t">
                <span className="text-xs font-medium text-gray-500">GST: {supplier.gstNumber}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {suppliers.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
          <Truck className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No Suppliers Yet</h3>
          <p className="text-gray-500 mt-1 mb-4">Start building your supplier network.</p>
          <button onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
            <Plus className="h-5 w-5" /> Add Your First Supplier
          </button>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-xl font-semibold text-gray-900" data-testid="supplier-modal-title">
                {editingSupplier ? 'Edit Supplier' : 'Add Supplier'}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5" /></button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {/* Basic Info */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Supplier Name *</label>
                <input type="text" value={formData.supplierName}
                  onChange={(e) => setFormData(prev => ({ ...prev, supplierName: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" required data-testid="supplier-name-input" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contact Person</label>
                <input type="text" value={formData.contact}
                  onChange={(e) => setFormData(prev => ({ ...prev, contact: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input type="tel" value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" data-testid="supplier-phone-input" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input type="email" value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">GST Number</label>
                <input type="text" value={formData.gstNumber}
                  onChange={(e) => setFormData(prev => ({ ...prev, gstNumber: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea value={formData.address}
                  onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" rows={2} />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" rows={2} />
              </div>

              {/* Product Mappings Section */}
              <div className="border-t pt-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                      <Package2 className="h-4 w-4 text-purple-600" /> Supplied Products
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">Define which products this supplier provides and their rates</p>
                  </div>
                  <button type="button" onClick={addProductMapping}
                    className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition"
                    data-testid="add-product-mapping-btn">
                    <Plus className="h-3.5 w-3.5" /> Add Product
                  </button>
                </div>

                {productMappings.length === 0 ? (
                  <p className="text-sm text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded-lg">
                    No products mapped. Click &quot;Add Product&quot; to link products.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {productMappings.map((pm, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg" data-testid={`product-mapping-${idx}`}>
                        <div className="flex-1 space-y-2">
                          <select value={pm.listingId}
                            onChange={(e) => updateProductMapping(idx, 'listingId', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
                            data-testid={`product-select-${idx}`}>
                            <option value="">Select Product</option>
                            {inventoryItems.map(item => (
                              <option key={item.listingId} value={item.listingId}>
                                {item.productName}{item.sku ? ` (${item.sku})` : ''}
                              </option>
                            ))}
                          </select>
                          {pm.listingId && (
                            <p className="text-xs text-gray-500 px-1">{selectedListingName(pm.listingId)}</p>
                          )}
                          <div>
                            <label className="text-xs text-gray-500">Rate (₹)</label>
                            <input type="number" value={pm.rate || ''} min={0} step="0.01"
                              onChange={(e) => updateProductMapping(idx, 'rate', parseFloat(e.target.value) || 0)}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
                              placeholder="0.00" data-testid={`rate-input-${idx}`} />
                          </div>
                        </div>
                        <button type="button" onClick={() => removeProductMapping(idx)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg mt-1">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                  Cancel
                </button>
                <button type="submit" disabled={saving || !formData.supplierName}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50" data-testid="save-supplier-btn">
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingSupplier ? 'Update' : 'Add Supplier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
