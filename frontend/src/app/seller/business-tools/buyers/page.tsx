'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { 
  Plus, 
  Pencil, 
  Trash2,
  Users,
  Loader2,
  X,
  AlertTriangle,
  Search,
  Building2,
  Phone,
  Mail,
  MapPin,
  Send
} from 'lucide-react';
import { INDIAN_STATES } from '@/lib/indian-states';

interface ShippingAddress {
  id: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  contactPerson?: string;
  phone?: string;
  isDefault: boolean;
}

interface Buyer {
  id: string;
  buyerName: string;
  company?: string;
  phone?: string;
  email?: string;
  gstNumber?: string;
  state?: string;
  address?: string;
  notes?: string;
  shippingAddresses?: ShippingAddress[];
  totalOrders: number;
  totalSpent: number;
  createdAt: string;
}

const emptyAddr = (): ShippingAddress => ({
  id: '', addressLine1: '', addressLine2: '', city: '', state: '', pincode: '', country: 'India', contactPerson: '', phone: '', isDefault: false,
});

export default function BuyersPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingBuyer, setEditingBuyer] = useState<Buyer | null>(null);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  // Shipping address management
  const [addrBuyer, setAddrBuyer] = useState<Buyer | null>(null);
  const [addrForm, setAddrForm] = useState<ShippingAddress>(emptyAddr());
  const [addrEditing, setAddrEditing] = useState(false);
  const [addrSaving, setAddrSaving] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    buyerName: '',
    company: '',
    phone: '',
    email: '',
    gstNumber: '',
    state: '',
    address: '',
    notes: ''
  });

  const loadBuyers = useCallback(async () => {
    try {
      const token = await getIdToken();
      const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers`);
      if (searchQuery) url.searchParams.set('search', searchQuery);

      const response = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) throw new Error('Failed to load buyers');

      const data = await response.json();
      setBuyers(data.buyers || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load buyers');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, searchQuery]);

  useEffect(() => {
    const timeoutId = setTimeout(loadBuyers, 300);
    return () => clearTimeout(timeoutId);
  }, [loadBuyers]);

  const openCreateModal = () => {
    setEditingBuyer(null);
    setFormData({ buyerName: '', company: '', phone: '', email: '', gstNumber: '', state: '', address: '', notes: '' });
    setShowModal(true);
  };

  const openEditModal = (buyer: Buyer) => {
    setEditingBuyer(buyer);
    setFormData({
      buyerName: buyer.buyerName,
      company: buyer.company || '',
      phone: buyer.phone || '',
      email: buyer.email || '',
      gstNumber: buyer.gstNumber || '',
      state: buyer.state || '',
      address: buyer.address || '',
      notes: buyer.notes || ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      const url = editingBuyer
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${editingBuyer.id}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers`;

      const response = await fetch(url, {
        method: editingBuyer ? 'PUT' : 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save buyer');
      }

      setShowModal(false);
      loadBuyers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save buyer');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (buyerId: string) => {
    try {
      const token = await getIdToken();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${buyerId}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete buyer');
      }

      setDeleteConfirm(null);
      loadBuyers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete buyer');
    }
  };

  // ── Shipping Address CRUD ──
  const openAddrManager = (buyer: Buyer) => {
    setAddrBuyer(buyer);
    setAddrForm(emptyAddr());
    setAddrEditing(false);
  };
  const startEditAddr = (addr: ShippingAddress) => { setAddrForm({ ...addr }); setAddrEditing(true); };
  const cancelAddrEdit = () => { setAddrForm(emptyAddr()); setAddrEditing(false); };

  const saveAddr = async () => {
    if (!addrBuyer || !addrForm.addressLine1 || !addrForm.city || !addrForm.state || !addrForm.pincode) {
      setError('Address Line 1, City, State and Pincode are required');
      return;
    }
    setAddrSaving(true);
    try {
      const token = await getIdToken();
      const isEdit = addrEditing && addrForm.id;
      const url = isEdit
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${addrBuyer.id}/shipping-addresses/${addrForm.id}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${addrBuyer.id}/shipping-addresses`;
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(addrForm),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Failed to save address'); }
      const data = await res.json();
      setAddrBuyer(prev => prev ? { ...prev, shippingAddresses: data.addresses } : prev);
      // Also update in the buyers list
      setBuyers(prev => prev.map(b => b.id === addrBuyer.id ? { ...b, shippingAddresses: data.addresses } : b));
      setAddrForm(emptyAddr());
      setAddrEditing(false);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to save address'); }
    setAddrSaving(false);
  };

  const deleteAddr = async (addrId: string) => {
    if (!addrBuyer) return;
    try {
      const token = await getIdToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${addrBuyer.id}/shipping-addresses/${addrId}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Failed to delete');
      const data = await res.json();
      setAddrBuyer(prev => prev ? { ...prev, shippingAddresses: data.addresses } : prev);
      setBuyers(prev => prev.map(b => b.id === addrBuyer.id ? { ...b, shippingAddresses: data.addresses } : b));
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to delete address'); }
  };

  const handleSalesPush = async (buyer: Buyer) => {
    if (!buyer.phone) {
      setError('Buyer has no phone number. Add phone to send sales push.');
      return;
    }
    try {
      const token = await getIdToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/buyers/${buyer.id}/sales-push`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ appUrl: window.location.origin }),
        }
      );
      const data = await res.json();
      if (res.ok && data.whatsappLink) {
        window.open(data.whatsappLink, '_blank');
      } else {
        setError(data.detail || 'Failed to generate sales push');
      }
    } catch { setError('Failed to generate sales push'); }
  };

  if (!hasPermission('manage_buyers')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to manage buyers.</p>
      </div>
    );
  }

  if (loading && buyers.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Buyers</h1>
          <p className="text-gray-600 mt-1">Manage your customer database</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
          data-testid="add-buyer-btn"
        >
          <Plus className="h-5 w-5" />
          Add Buyer
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search buyers by name, company, email..."
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="h-5 w-5 text-red-600" />
          </button>
        </div>
      )}

      {/* Buyers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {buyers.map((buyer) => (
          <div key={buyer.id} className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                  <span className="text-green-600 font-medium">
                    {buyer.buyerName.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{buyer.buyerName}</h3>
                  {buyer.company && (
                    <p className="text-sm text-gray-500 flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5" />
                      {buyer.company}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => openEditModal(buyer)}
                  className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                {deleteConfirm === buyer.id ? (
                  <>
                    <button
                      onClick={() => handleDelete(buyer.id)}
                      className="p-1.5 text-white bg-red-600 hover:bg-red-700 rounded-lg"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(buyer.id)}
                    className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-2 text-sm">
              {buyer.phone && (
                <p className="flex items-center gap-2 text-gray-600">
                  <Phone className="h-4 w-4 text-gray-400" />
                  {buyer.phone}
                </p>
              )}
              {buyer.email && (
                <p className="flex items-center gap-2 text-gray-600">
                  <Mail className="h-4 w-4 text-gray-400" />
                  {buyer.email}
                </p>
              )}
              {buyer.address && (
                <p className="flex items-center gap-2 text-gray-600">
                  <MapPin className="h-4 w-4 text-gray-400" />
                  <span className="truncate">{buyer.address}</span>
                </p>
              )}
            </div>

            {buyer.gstNumber && (
              <div className="mt-3 pt-3 border-t">
                <span className="text-xs font-medium text-gray-500">GST: {buyer.gstNumber}</span>
                {buyer.state && <span className="text-xs text-gray-400 ml-2">| {buyer.state}</span>}
              </div>
            )}
            {!buyer.gstNumber && buyer.state && (
              <div className="mt-3 pt-3 border-t">
                <span className="text-xs font-medium text-gray-500">{buyer.state}</span>
              </div>
            )}
            <div className="mt-3 pt-3 border-t flex items-center justify-between">
              <button onClick={() => openAddrManager(buyer)} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1" data-testid={`manage-addr-${buyer.id}`}>
                <MapPin className="h-3 w-3" />
                Addresses ({(buyer.shippingAddresses || []).length})
              </button>
              {buyer.phone && (
                <button onClick={() => handleSalesPush(buyer)} className="text-xs text-green-600 hover:text-green-800 font-medium flex items-center gap-1" data-testid={`sales-push-${buyer.id}`}>
                  <Send className="h-3 w-3" />
                  Sales Push
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {buyers.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
          <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No Buyers Yet</h3>
          <p className="text-gray-500 mt-1 mb-4">Start building your customer database.</p>
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Plus className="h-5 w-5" />
            Add Your First Buyer
          </button>
        </div>
      )}

      {/* Buyer Form Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                {editingBuyer ? 'Edit Buyer' : 'Add Buyer'}
              </h2>
              <button onClick={() => setShowModal(false)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={formData.buyerName}
                  onChange={(e) => setFormData(prev => ({ ...prev, buyerName: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                <input
                  type="text"
                  value={formData.company}
                  onChange={(e) => setFormData(prev => ({ ...prev, company: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">GST Number</label>
                <input
                  type="text"
                  value={formData.gstNumber}
                  onChange={(e) => setFormData(prev => ({ ...prev, gstNumber: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  placeholder="22AAAAA0000A1Z5"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                <select
                  value={formData.state}
                  onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  data-testid="buyer-state-select"
                >
                  <option value="">Select State</option>
                  {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea
                  value={formData.address}
                  onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  rows={2}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  rows={2}
                  placeholder="Internal notes about this buyer"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !formData.buyerName}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingBuyer ? 'Update' : 'Add Buyer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Shipping Address Modal */}
      {addrBuyer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="addr-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Shipping Addresses</h2>
                <p className="text-sm text-gray-500">{addrBuyer.buyerName}</p>
              </div>
              <button onClick={() => { setAddrBuyer(null); setAddrEditing(false); setAddrForm(emptyAddr()); }} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              {/* Existing addresses */}
              {(addrBuyer.shippingAddresses || []).length > 0 ? (
                <div className="space-y-2">
                  {(addrBuyer.shippingAddresses || []).map(a => (
                    <div key={a.id} className={`border rounded-lg p-3 text-sm ${a.isDefault ? 'border-indigo-300 bg-indigo-50' : 'border-gray-200'}`} data-testid={`addr-${a.id}`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900">{a.addressLine1}{a.addressLine2 ? `, ${a.addressLine2}` : ''}</p>
                          <p className="text-gray-600">{a.city}, {a.state} - {a.pincode}</p>
                          {a.contactPerson && <p className="text-xs text-gray-500 mt-1">Contact: {a.contactPerson}{a.phone ? ` (${a.phone})` : ''}</p>}
                          {a.isDefault && <span className="inline-block mt-1 px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full font-medium">Default</span>}
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                          <button onClick={() => startEditAddr(a)} className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded" data-testid={`edit-addr-${a.id}`}><Pencil className="h-3.5 w-3.5" /></button>
                          <button onClick={() => deleteAddr(a.id)} className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded" data-testid={`del-addr-${a.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-400 text-sm py-4">No shipping addresses yet</p>
              )}
              {/* Add / Edit form */}
              <div className="border-t pt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">{addrEditing ? 'Edit Address' : 'Add New Address'}</h3>
                <div className="space-y-3">
                  <div><label className="block text-xs font-medium text-gray-600 mb-1">Address Line 1 *</label><input type="text" value={addrForm.addressLine1} onChange={e => setAddrForm(p => ({ ...p, addressLine1: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500" placeholder="Building, Street" data-testid="addr-line1" /></div>
                  <div><label className="block text-xs font-medium text-gray-600 mb-1">Address Line 2</label><input type="text" value={addrForm.addressLine2 || ''} onChange={e => setAddrForm(p => ({ ...p, addressLine2: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Area, Landmark" data-testid="addr-line2" /></div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">City *</label><input type="text" value={addrForm.city} onChange={e => setAddrForm(p => ({ ...p, city: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="addr-city" /></div>
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">State *</label><select value={addrForm.state} onChange={e => setAddrForm(p => ({ ...p, state: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="addr-state"><option value="">Select</option>{INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">Pincode *</label><input type="text" value={addrForm.pincode} onChange={e => setAddrForm(p => ({ ...p, pincode: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" maxLength={6} data-testid="addr-pincode" /></div>
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">Country</label><input type="text" value={addrForm.country} onChange={e => setAddrForm(p => ({ ...p, country: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="addr-country" /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">Contact Person</label><input type="text" value={addrForm.contactPerson || ''} onChange={e => setAddrForm(p => ({ ...p, contactPerson: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="addr-contact" /></div>
                    <div><label className="block text-xs font-medium text-gray-600 mb-1">Phone</label><input type="tel" value={addrForm.phone || ''} onChange={e => setAddrForm(p => ({ ...p, phone: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="addr-phone" /></div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => setAddrForm(p => ({ ...p, isDefault: !p.isDefault }))} className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${addrForm.isDefault ? 'bg-indigo-500' : 'bg-gray-300'}`} data-testid="addr-default-toggle"><span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition ${addrForm.isDefault ? 'translate-x-4' : 'translate-x-0.5'}`} /></button>
                    <span className="text-xs text-gray-600">Mark as default</span>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button onClick={saveAddr} disabled={addrSaving} className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50" data-testid="save-addr-btn">
                      {addrSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      {addrEditing ? 'Update' : 'Add Address'}
                    </button>
                    {addrEditing && <button onClick={cancelAddrEdit} className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">Cancel</button>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
