'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import Image from 'next/image';
import { 
  Package2, Loader2, X, AlertTriangle, Search, AlertCircle, Plus, Minus, RefreshCw, Save, Pencil
} from 'lucide-react';

interface InventoryItem {
  id?: string;
  listingId: string;
  productId: string;
  productType?: string;
  productName: string;
  categoryName?: string;
  sku: string;
  stock: number;
  lowStockAlert: number;
  warehouseLocation: string;
  purchase_price?: number | null;
  selling_price?: number | null;
  minPrice?: number;
  status: string;
  images: string[];
  isLowStock: boolean;
}

interface EditState {
  sku?: string;
  warehouseLocation?: string;
  selling_price?: number | null;
  purchase_price?: number | null;
}

export default function InventoryPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showLowStockOnly, setShowLowStockOnly] = useState(false);
  const [lowStockCount, setLowStockCount] = useState(0);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState>({});
  const [adjustModal, setAdjustModal] = useState<InventoryItem | null>(null);
  const [adjustData, setAdjustData] = useState({ changeType: 'adjustment', quantity: 0, note: '' });
  const [saving, setSaving] = useState(false);
  const [canViewPurchasePrice, setCanViewPurchasePrice] = useState(false);
  const isEditing = useRef(false);

  const loadInventory = useCallback(async () => {
    // Don't refresh while user is editing
    if (isEditing.current) return;
    try {
      const token = await getIdToken();
      const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/inventory`);
      if (searchQuery) url.searchParams.set('search', searchQuery);
      if (showLowStockOnly) url.searchParams.set('lowStockOnly', 'true');
      const response = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error('Failed to load inventory');
      const data = await response.json();
      setInventory(data.inventory || []);
      setLowStockCount(data.lowStockCount || 0);
      setCanViewPurchasePrice(data.canViewPurchasePrice || false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inventory');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, searchQuery, showLowStockOnly]);

  useEffect(() => {
    const timeoutId = setTimeout(loadInventory, 300);
    return () => clearTimeout(timeoutId);
  }, [loadInventory]);

  const startEditing = (item: InventoryItem) => {
    isEditing.current = true;
    setEditingItem(item.listingId);
    setEditState({
      sku: item.sku,
      warehouseLocation: item.warehouseLocation,
      selling_price: item.selling_price,
      purchase_price: item.purchase_price,
    });
  };

  const cancelEditing = () => {
    isEditing.current = false;
    setEditingItem(null);
    setEditState({});
  };

  const saveEditing = async (item: InventoryItem) => {
    setSaving(true);
    try {
      const token = await getIdToken();
      const payload: Record<string, unknown> = {};
      
      // Only include fields that changed
      if (editState.sku !== undefined && editState.sku !== item.sku) payload.sku = editState.sku;
      if (editState.warehouseLocation !== undefined && editState.warehouseLocation !== item.warehouseLocation) payload.warehouseLocation = editState.warehouseLocation;
      if (editState.selling_price !== undefined && editState.selling_price !== item.selling_price) payload.selling_price = editState.selling_price;
      // purchase_price only for non-composite
      if (item.productType !== 'composite' && editState.purchase_price !== undefined && editState.purchase_price !== item.purchase_price) {
        payload.purchase_price = editState.purchase_price;
      }

      if (Object.keys(payload).length > 0) {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/inventory/${item.listingId}`,
          { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
        );
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Failed to update');
        }
      }

      isEditing.current = false;
      setEditingItem(null);
      setEditState({});
      loadInventory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update');
    } finally {
      setSaving(false);
    }
  };

  const handleAdjustStock = async () => {
    if (!adjustModal) return;
    setSaving(true);
    try {
      const token = await getIdToken();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/inventory/${adjustModal.listingId}/adjust`,
        { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ listingId: adjustModal.listingId, changeType: adjustData.changeType, quantity: adjustData.quantity, note: adjustData.note || null }) }
      );
      if (!response.ok) { const data = await response.json(); throw new Error(data.detail || 'Failed to adjust stock'); }
      setAdjustModal(null);
      setAdjustData({ changeType: 'adjustment', quantity: 0, note: '' });
      loadInventory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to adjust stock');
    } finally {
      setSaving(false);
    }
  };

  if (!hasPermission('manage_inventory')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Package2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to manage inventory.</p>
      </div>
    );
  }

  if (loading && inventory.length === 0) {
    return (<div className="flex items-center justify-center min-h-[400px]"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>);
  }

  const isComposite = (item: InventoryItem) => item.productType === 'composite';
  const isEditingThis = (item: InventoryItem) => editingItem === item.listingId;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-gray-600 mt-1">Track stock levels and manage pricing</p>
        </div>
        {lowStockCount > 0 && (
          <button onClick={() => setShowLowStockOnly(!showLowStockOnly)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${showLowStockOnly ? 'bg-red-600 text-white' : 'bg-red-50 text-red-600 hover:bg-red-100'}`}>
            <AlertCircle className="h-5 w-5" />{lowStockCount} Low Stock Items
          </button>
        )}
      </div>

      {/* Search */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by product name or SKU..." className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>
        <button onClick={() => { if (!isEditing.current) loadInventory(); }} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
          <RefreshCw className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto"><X className="h-5 w-5 text-red-600" /></button>
        </div>
      )}

      {/* Inventory Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        {inventory.length === 0 ? (
          <div className="text-center py-12">
            <Package2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No Inventory Items</h3>
            <p className="text-gray-500 mt-1">{showLowStockOnly ? 'No low stock items found.' : 'Create product listings to track inventory.'}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200" data-testid="inventory-table">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Stock</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Selling Price</th>
                  {canViewPurchasePrice && (
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Purchase Price</th>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {inventory.map((item) => (
                  <tr key={item.listingId} className={`hover:bg-gray-50 ${item.isLowStock ? 'bg-red-50' : ''} ${isEditingThis(item) ? 'bg-blue-50/50 ring-1 ring-blue-200' : ''}`}>
                    {/* Product */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {item.images?.[0] ? (
                          <Image src={item.images[0]} alt={item.productName} width={40} height={40} className="rounded-lg object-cover" />
                        ) : (
                          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center"><Package2 className="h-5 w-5 text-gray-400" /></div>
                        )}
                        <div>
                          <p className="font-medium text-gray-900">
                            {item.productName}
                            {isComposite(item) && <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-full font-medium">Composite</span>}
                          </p>
                          {item.categoryName && <p className="text-xs text-gray-500">{item.categoryName}</p>}
                        </div>
                      </div>
                    </td>

                    {/* SKU */}
                    <td className="px-6 py-4">
                      {isEditingThis(item) && !isComposite(item) ? (
                        <input type="text" value={editState.sku ?? ''} onChange={(e) => setEditState(s => ({ ...s, sku: e.target.value }))}
                          className="w-24 px-2 py-1 border border-blue-300 rounded text-sm focus:ring-1 focus:ring-blue-500" data-testid={`sku-input-${item.listingId}`} />
                      ) : (
                        <span className="text-gray-600 font-mono text-sm">{item.sku || '-'}</span>
                      )}
                    </td>

                    {/* Stock */}
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium ${item.isLowStock ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                        {item.stock}
                      </span>
                      {isComposite(item) && <p className="text-[10px] text-gray-400 mt-0.5">auto</p>}
                    </td>

                    {/* Selling Price - editable for ALL items including composite */}
                    <td className="px-6 py-4 text-right">
                      {isEditingThis(item) ? (
                        <input type="number" value={editState.selling_price ?? ''} onChange={(e) => setEditState(s => ({ ...s, selling_price: e.target.value ? parseFloat(e.target.value) : null }))}
                          className="w-28 px-2 py-1 border border-blue-300 rounded text-sm text-right focus:ring-1 focus:ring-blue-500" placeholder="0"
                          data-testid={`selling-price-input-${item.listingId}`} />
                      ) : (
                        <span className="text-gray-700 font-medium">{item.selling_price != null ? `₹${item.selling_price.toLocaleString('en-IN')}` : '-'}</span>
                      )}
                    </td>

                    {/* Purchase Price - editable only for non-composite, auto-calc for composite */}
                    {canViewPurchasePrice && (
                      <td className="px-6 py-4 text-right">
                        {isEditingThis(item) && !isComposite(item) ? (
                          <input type="number" value={editState.purchase_price ?? ''} onChange={(e) => setEditState(s => ({ ...s, purchase_price: e.target.value ? parseFloat(e.target.value) : null }))}
                            className="w-28 px-2 py-1 border border-blue-300 rounded text-sm text-right focus:ring-1 focus:ring-blue-500" placeholder="0"
                            data-testid={`purchase-price-input-${item.listingId}`} />
                        ) : (
                          <span className="text-gray-500">
                            {item.purchase_price != null ? `₹${item.purchase_price.toLocaleString('en-IN')}` : '-'}
                            {isComposite(item) && <span className="block text-[10px] text-gray-400">auto</span>}
                          </span>
                        )}
                      </td>
                    )}

                    {/* Location */}
                    <td className="px-6 py-4">
                      {isEditingThis(item) && !isComposite(item) ? (
                        <input type="text" value={editState.warehouseLocation ?? ''} onChange={(e) => setEditState(s => ({ ...s, warehouseLocation: e.target.value }))}
                          className="w-32 px-2 py-1 border border-blue-300 rounded text-sm focus:ring-1 focus:ring-blue-500" />
                      ) : (
                        <span className="text-gray-600">{item.warehouseLocation || '-'}</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {isEditingThis(item) ? (
                          <>
                            <button onClick={cancelEditing} className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200" data-testid={`cancel-edit-${item.listingId}`}>
                              Cancel
                            </button>
                            <button onClick={() => saveEditing(item)} disabled={saving}
                              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50" data-testid={`save-edit-${item.listingId}`}>
                              {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />} Save
                            </button>
                          </>
                        ) : (
                          <>
                            {!isComposite(item) && (
                              <button onClick={() => setAdjustModal(item)} className="px-3 py-1.5 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100" data-testid={`adjust-btn-${item.listingId}`}>
                                Adjust
                              </button>
                            )}
                            <button onClick={() => startEditing(item)} className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg" data-testid={`edit-btn-${item.listingId}`}>
                              <Pencil className="h-3 w-3" /> Edit
                            </button>
                          </>
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

      {/* Adjust Stock Modal */}
      {adjustModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
            <div className="border-b px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Adjust Stock</h2>
              <button onClick={() => setAdjustModal(null)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                {adjustModal.images?.[0] && <Image src={adjustModal.images[0]} alt="" width={48} height={48} className="rounded-lg" />}
                <div>
                  <p className="font-medium text-gray-900">{adjustModal.productName}</p>
                  <p className="text-sm text-gray-500">Current Stock: {adjustModal.stock}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Adjustment Type</label>
                <select value={adjustData.changeType} onChange={(e) => setAdjustData(prev => ({ ...prev, changeType: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="purchase">Purchase (Add Stock)</option>
                  <option value="sale">Sale (Reduce Stock)</option>
                  <option value="adjustment">Manual Adjustment</option>
                  <option value="damage">Damage/Loss</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
                <div className="flex items-center gap-2">
                  <button onClick={() => setAdjustData(prev => ({ ...prev, quantity: Math.max(0, prev.quantity - 1) }))} className="p-2 border rounded-lg hover:bg-gray-50"><Minus className="h-4 w-4" /></button>
                  <input type="number" value={adjustData.quantity} onChange={(e) => setAdjustData(prev => ({ ...prev, quantity: parseInt(e.target.value) || 0 }))} className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-center" min="0" />
                  <button onClick={() => setAdjustData(prev => ({ ...prev, quantity: prev.quantity + 1 }))} className="p-2 border rounded-lg hover:bg-gray-50"><Plus className="h-4 w-4" /></button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Note (optional)</label>
                <textarea value={adjustData.note} onChange={(e) => setAdjustData(prev => ({ ...prev, note: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" rows={2} placeholder="Reason for adjustment" />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button onClick={() => setAdjustModal(null)} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
                <button onClick={handleAdjustStock} disabled={saving || adjustData.quantity === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />} Apply Adjustment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
