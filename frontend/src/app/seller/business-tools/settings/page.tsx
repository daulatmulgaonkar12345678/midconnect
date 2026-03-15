'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { Building2, Save, Upload, X, Camera, CheckCircle2 } from 'lucide-react';
import { uploadSellerProductImage } from '@/lib/cloudinary';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SellerProfile {
  businessName: string;
  phone: string;
  email: string;
  address: string;
  city: string;
  state: string;
  sellerLogoUrl: string;
  gstNumber: string;
}

interface InvoiceIdentity {
  sellerAbbreviation: string;
  sellerCode: string;
  lastSequence: number;
}

export default function SettingsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [profile, setProfile] = useState<SellerProfile>({
    businessName: '', phone: '', email: '', address: '', city: '', state: '', sellerLogoUrl: '', gstNumber: '',
  });
  const [identity, setIdentity] = useState<InvoiceIdentity>({ sellerAbbreviation: '', sellerCode: '', lastSequence: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [logoUploading, setLogoUploading] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  useEffect(() => {
    (async () => {
      try {
        const h = await authHeaders();
        const res = await fetch(`${API_URL}/api/business-tools/seller-profile`, { headers: h });
        if (res.ok) {
          const data = await res.json();
          setProfile(data.profile);
          setIdentity(data.invoiceIdentity);
        }
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [authHeaders]);

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/webp'];
    if (!allowed.includes(file.type)) { alert('Allowed: JPG, PNG, SVG, WEBP'); return; }
    if (file.size > 5 * 1024 * 1024) { alert('Max 5MB'); return; }
    setLogoUploading(true);
    try {
      const result = await uploadSellerProductImage(file);
      setProfile(p => ({ ...p, sellerLogoUrl: result.url }));
    } catch (err) { alert('Upload failed: ' + (err instanceof Error ? err.message : 'Unknown')); }
    setLogoUploading(false);
  };

  const handleSave = async () => {
    if (!profile.businessName.trim()) { alert('Business name is required'); return; }
    setSaving(true);
    setSaved(false);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/seller-profile`, {
        method: 'PUT', headers: h, body: JSON.stringify(profile),
      });
      const data = await res.json();
      if (!res.ok) { alert(data.detail || 'Failed to save'); return; }
      setProfile(data.profile);
      if (data.invoiceIdentity) setIdentity(data.invoiceIdentity);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { alert('Error saving profile'); }
    setSaving(false);
  };

  if (!hasPermission('create_invoice')) {
    return <div className="text-center py-12 bg-white rounded-xl border" data-testid="no-permission"><p className="text-gray-500">No permission to access settings.</p></div>;
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-2xl space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Business Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your business profile and invoice branding</p>
      </div>

      {/* Invoice Identity (Read-only) */}
      {identity.sellerAbbreviation && (
        <div className="bg-indigo-50 rounded-xl p-4 border border-indigo-100" data-testid="invoice-identity">
          <h3 className="text-sm font-semibold text-indigo-800 mb-2">Invoice Identity</h3>
          <div className="flex items-center gap-4 text-sm">
            <div><span className="text-indigo-500">Abbreviation:</span> <span className="font-bold text-indigo-900">{identity.sellerAbbreviation}</span></div>
            <div><span className="text-indigo-500">Code:</span> <span className="font-bold text-indigo-900">{identity.sellerCode}</span></div>
            <div><span className="text-indigo-500">Invoices:</span> <span className="font-bold text-indigo-900">{identity.lastSequence}</span></div>
          </div>
          <p className="text-xs text-indigo-400 mt-2">Format: INV{identity.sellerAbbreviation}-{identity.sellerCode}-XXXX</p>
        </div>
      )}

      {/* Logo */}
      <div className="bg-white rounded-xl border border-gray-100 p-5" data-testid="logo-section">
        <h3 className="text-sm font-semibold text-gray-800 mb-3">Firm Logo</h3>
        <div className="flex items-center gap-4">
          <div className="relative w-20 h-20 rounded-xl border-2 border-dashed border-gray-200 flex items-center justify-center bg-gray-50 overflow-hidden">
            {profile.sellerLogoUrl ? (
              <>
                <img src={profile.sellerLogoUrl} alt="Logo" className="w-full h-full object-contain" data-testid="logo-preview" />
                <button onClick={() => setProfile(p => ({ ...p, sellerLogoUrl: '' }))} className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5" data-testid="remove-logo-btn"><X className="w-3 h-3" /></button>
              </>
            ) : (
              <Camera className="w-6 h-6 text-gray-300" />
            )}
          </div>
          <div>
            <input type="file" ref={logoInputRef} onChange={handleLogoUpload} accept="image/jpeg,image/png,image/svg+xml,image/webp" className="hidden" />
            <button onClick={() => logoInputRef.current?.click()} disabled={logoUploading}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 disabled:opacity-50" data-testid="upload-logo-btn">
              <Upload className="w-4 h-4" /> {logoUploading ? 'Uploading...' : 'Upload Logo'}
            </button>
            <p className="text-xs text-gray-400 mt-1">PNG, JPG, SVG. Max 5MB.</p>
          </div>
        </div>
      </div>

      {/* Profile Form */}
      <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4" data-testid="profile-form">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5"><Building2 className="w-4 h-4 text-indigo-500" /> Business Information</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
          <input type="text" value={profile.businessName} onChange={e => setProfile(p => ({ ...p, businessName: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Akash Enterprises" data-testid="business-name-input" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input type="text" value={profile.phone} onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. 9876543210" data-testid="phone-input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={profile.email} onChange={e => setProfile(p => ({ ...p, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="email-input" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
          <input type="text" value={profile.address} onChange={e => setProfile(p => ({ ...p, address: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Street address" data-testid="address-input" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
            <input type="text" value={profile.city} onChange={e => setProfile(p => ({ ...p, city: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="city-input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
            <input type="text" value={profile.state} onChange={e => setProfile(p => ({ ...p, state: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="state-input" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">GST Number <span className="text-gray-400">(optional)</span></label>
          <input type="text" value={profile.gstNumber} onChange={e => setProfile(p => ({ ...p, gstNumber: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. 22AAAAA0000A1Z5" data-testid="gst-input" />
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-3">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50" data-testid="save-profile-btn">
          <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Changes'}
        </button>
        {saved && <span className="flex items-center gap-1 text-sm text-emerald-600 font-medium" data-testid="save-success"><CheckCircle2 className="w-4 h-4" /> Saved successfully</span>}
      </div>
    </div>
  );
}
