'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getSellerListings,
  quickPriceUpdate,
  SellerListing,
  PricingSlab
} from '@/lib/api';
import { 
  Loader2, 
  AlertCircle, 
  ArrowLeft,
  TrendingUp,
  Package,
  Check,
  X,
  Zap,
  Calendar,
  ChevronDown,
  Plus,
  Trash2
} from 'lucide-react';
import Link from 'next/link';

type ValidityOption = 'today' | '7_days' | '15_days' | '30_days' | 'custom';
type StockStatus = 'in_stock' | 'limited' | 'made_to_order' | 'out_of_stock';

interface EditState {
  basePrice: number;
  validTill: ValidityOption;
  customDate: string;
  stockStatus: StockStatus;
  slabs: PricingSlab[];
  note: string;
}

const validityOptions: { value: ValidityOption; label: string }[] = [
  { value: 'today', label: 'Today only' },
  { value: '7_days', label: '7 days' },
  { value: '15_days', label: '15 days' },
  { value: '30_days', label: '30 days' },
  { value: 'custom', label: 'Custom date' }
];

const stockOptions: { value: StockStatus; label: string; color: string }[] = [
  { value: 'in_stock', label: 'In Stock', color: 'bg-green-100 text-green-700' },
  { value: 'limited', label: 'Limited', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'made_to_order', label: 'Made to Order', color: 'bg-blue-100 text-blue-700' },
  { value: 'out_of_stock', label: 'Out of Stock', color: 'bg-red-100 text-red-700' }
];

export default function QuickPricingPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [listings, setListings] = useState<SellerListing[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [saving, setSaving] = useState(false);
  const [showTiers, setShowTiers] = useState(false);

  const loadListings = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }
      
      const data = await getSellerListings(token, {
        status: 'active',
        limit: 100
      });
      setListings(data.listings);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load listings');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router]);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadListings();
      }
    }
  }, [user, authLoading, loadListings, router]);

  const startEditing = (listing: SellerListing) => {
    const currentTiers = listing.pricingTiers || [];
    const basePrice = currentTiers[0]?.pricePerUnit || 0;
    
    setEditingId(listing._id);
    setEditState({
      basePrice,
      validTill: '7_days',
      customDate: '',
      stockStatus: 'in_stock',
      slabs: currentTiers.length > 1 ? currentTiers.slice(1) : [],
      note: ''
    });
    setShowTiers(currentTiers.length > 1);
    setError(null);
    setSuccess(null);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditState(null);
    setShowTiers(false);
  };

  const addTier = () => {
    if (!editState) return;
    const lastSlab = editState.slabs[editState.slabs.length - 1];
    const newMin = lastSlab ? (lastSlab.maxQty || lastSlab.minQty) + 1 : 100;
    
    setEditState({
      ...editState,
      slabs: [...editState.slabs, {
        minQty: newMin,
        maxQty: null,
        pricePerUnit: editState.basePrice * 0.95
      }]
    });
  };

  const removeTier = (index: number) => {
    if (!editState) return;
    setEditState({
      ...editState,
      slabs: editState.slabs.filter((_, i) => i !== index)
    });
  };

  const updateTier = (index: number, field: keyof PricingSlab, value: number | null) => {
    if (!editState) return;
    setEditState({
      ...editState,
      slabs: editState.slabs.map((slab, i) => 
        i === index ? { ...slab, [field]: value } : slab
      )
    });
  };

  const savePrice = async (listingId: string) => {
    if (!editState || editState.basePrice <= 0) {
      setError('Price must be greater than 0');
      return;
    }

    if (editState.validTill === 'custom' && !editState.customDate) {
      setError('Please select a custom validity date');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      // Build slabs - base price as first slab
      const allSlabs: PricingSlab[] = [
        {
          minQty: 1,
          maxQty: editState.slabs.length > 0 ? (editState.slabs[0].minQty - 1) : null,
          pricePerUnit: editState.basePrice
        },
        ...editState.slabs
      ];

      await quickPriceUpdate(token, listingId, {
        basePrice: editState.basePrice,
        pricingSlabs: allSlabs.length > 1 ? allSlabs : undefined,
        validTill: editState.validTill,
        stockStatus: editState.stockStatus
      });

      // Update local state
      setListings(prev => prev.map(l => 
        l._id === listingId 
          ? { 
              ...l, 
              pricingTiers: allSlabs
            } 
          : l
      ));

      setSuccess(`Price updated to ₹${editState.basePrice}`);
      setEditingId(null);
      setEditState(null);
      setShowTiers(false);
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update price');
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                Quick Price Update
              </h1>
              <p className="text-sm text-gray-500">Update prices instantly for your active listings</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700">
            <Check className="h-5 w-5 flex-shrink-0" />
            {success}
          </div>
        )}

        {listings.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Active Listings</h3>
            <p className="text-gray-600 mb-4">
              You need active listings to update prices. Create and publish a listing first.
            </p>
            <Link
              href="/seller/listings/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              data-testid="create-listing-cta"
            >
              Create Listing
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {listings.map((listing) => (
              <div 
                key={listing._id}
                className={`bg-white rounded-xl shadow-sm overflow-hidden transition-all ${
                  editingId === listing._id ? 'ring-2 ring-blue-500' : ''
                }`}
                data-testid={`pricing-card-${listing._id}`}
              >
                {/* Listing Header */}
                <div className="p-4 flex items-center gap-4 border-b">
                  <div className="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                    {listing.images?.[0] ? (
                      <img 
                        src={listing.images[0]} 
                        alt={listing.productName}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package className="h-6 w-6 text-gray-400" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">{listing.productName}</h3>
                    <p className="text-sm text-gray-500">{listing.categoryName}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-400">MOQ: {listing.moq || 1}</span>
                    </div>
                  </div>

                  {editingId !== listing._id && (
                    <div className="text-right">
                      <div className="text-xl font-bold text-gray-900">
                        ₹{listing.pricingTiers?.[0]?.pricePerUnit || 0}
                      </div>
                      <button
                        onClick={() => startEditing(listing)}
                        className="mt-2 flex items-center gap-1.5 px-3 py-1.5 bg-yellow-500 text-white text-sm font-medium rounded-lg hover:bg-yellow-600 transition"
                        data-testid={`quick-update-btn-${listing._id}`}
                      >
                        <Zap className="h-4 w-4" />
                        Update Price
                      </button>
                    </div>
                  )}
                </div>

                {/* Edit Form */}
                {editingId === listing._id && editState && (
                  <div className="p-4 bg-gray-50 space-y-4">
                    {/* Base Price */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Base Price (per unit)
                      </label>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 text-lg">₹</span>
                        <input
                          type="number"
                          value={editState.basePrice}
                          onChange={(e) => setEditState({...editState, basePrice: parseFloat(e.target.value) || 0})}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg font-semibold"
                          min={0}
                          step={0.01}
                          autoFocus
                          data-testid="base-price-input"
                        />
                      </div>
                    </div>

                    {/* Price Tiers Toggle */}
                    <div>
                      <button
                        onClick={() => setShowTiers(!showTiers)}
                        className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                        data-testid="toggle-tiers-btn"
                      >
                        <ChevronDown className={`h-4 w-4 transition ${showTiers ? 'rotate-180' : ''}`} />
                        {showTiers ? 'Hide price tiers' : 'Add price tiers (bulk discounts)'}
                      </button>

                      {showTiers && (
                        <div className="mt-3 space-y-2">
                          {editState.slabs.map((slab, index) => (
                            <div key={index} className="flex items-center gap-2 bg-white p-2 rounded-lg border">
                              <input
                                type="number"
                                value={slab.minQty}
                                onChange={(e) => updateTier(index, 'minQty', parseInt(e.target.value) || 0)}
                                className="w-20 px-2 py-1 border rounded text-sm"
                                placeholder="Min"
                              />
                              <span className="text-gray-400">-</span>
                              <input
                                type="number"
                                value={slab.maxQty || ''}
                                onChange={(e) => updateTier(index, 'maxQty', e.target.value ? parseInt(e.target.value) : null)}
                                className="w-20 px-2 py-1 border rounded text-sm"
                                placeholder="Max"
                              />
                              <span className="text-gray-500">qty → ₹</span>
                              <input
                                type="number"
                                value={slab.pricePerUnit}
                                onChange={(e) => updateTier(index, 'pricePerUnit', Math.round(parseFloat(e.target.value) * 100) / 100 || 0)}
                                className="w-24 px-2 py-1 border rounded text-sm font-medium"
                                step={0.01}
                              />
                              <button
                                onClick={() => removeTier(index)}
                                className="p-1 text-red-500 hover:bg-red-50 rounded"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          ))}
                          <button
                            onClick={addTier}
                            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                          >
                            <Plus className="h-4 w-4" />
                            Add tier
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Valid Till */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <Calendar className="h-4 w-4 inline mr-1" />
                        Price valid till
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {validityOptions.map(opt => (
                          <button
                            key={opt.value}
                            onClick={() => setEditState({...editState, validTill: opt.value})}
                            className={`px-3 py-1.5 text-sm rounded-lg border transition ${
                              editState.validTill === opt.value
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-500'
                            }`}
                            data-testid={`validity-${opt.value}`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                      {editState.validTill === 'custom' && (
                        <input
                          type="date"
                          value={editState.customDate}
                          onChange={(e) => setEditState({...editState, customDate: e.target.value})}
                          className="mt-2 px-3 py-2 border border-gray-300 rounded-lg"
                          min={new Date().toISOString().split('T')[0]}
                          data-testid="custom-date-input"
                        />
                      )}
                    </div>

                    {/* Stock Status */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Stock Availability
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {stockOptions.map(opt => (
                          <button
                            key={opt.value}
                            onClick={() => setEditState({...editState, stockStatus: opt.value})}
                            className={`px-3 py-1.5 text-sm rounded-lg border transition ${
                              editState.stockStatus === opt.value
                                ? opt.color + ' border-transparent'
                                : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                            }`}
                            data-testid={`stock-${opt.value}`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Note */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Internal Note (optional)
                      </label>
                      <input
                        type="text"
                        value={editState.note}
                        onChange={(e) => setEditState({...editState, note: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        placeholder="e.g., Price hike due to raw material cost"
                        maxLength={200}
                      />
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 pt-2">
                      <button
                        onClick={() => savePrice(listing._id)}
                        disabled={saving}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
                        data-testid="save-price-btn"
                      >
                        {saving ? (
                          <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                          <>
                            <Check className="h-5 w-5" />
                            Save Price
                          </>
                        )}
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="px-4 py-2.5 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                        data-testid="cancel-btn"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tips */}
        <div className="mt-8 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border border-yellow-200">
          <h3 className="font-medium text-yellow-900 mb-2 flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Quick Price Tips
          </h3>
          <ul className="text-sm text-yellow-800 space-y-1">
            <li>• Update prices daily to stay competitive</li>
            <li>• Use price tiers for bulk order discounts</li>
            <li>• Set "Valid till" to create urgency for buyers</li>
            <li>• Keep stock status accurate to avoid inquiry rejections</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
