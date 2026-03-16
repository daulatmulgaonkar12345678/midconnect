'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  Building2, Save, Loader2, Image as ImageIcon, X, Eye,
  CreditCard, FileText, Upload
} from 'lucide-react';
import { uploadSellerProductImage } from '@/lib/cloudinary';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface SellerProfile {
  businessName: string; phone: string; email: string;
  address: string; city: string; state: string;
  sellerLogoUrl: string; gstNumber: string;
}

interface BillingSettings {
  bankName: string; accountNumber: string; accountName: string;
  ifscCode: string; branch: string; upiId: string;
  invoiceTerms: string; invoiceBackgroundImage: string;
}

const DEFAULT_TERMS = `1. Goods once sold will not be taken back.
2. Interest @18% p.a. will be charged if payment is not made within due date.
3. Our risk and responsibility ceases as soon as the goods leave our premises.
4. Subject to local jurisdiction only. E.&O.E.`;

export default function SettingsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission, token, loading: permLoading } = usePermissions();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'billing'>('profile');
  const [profile, setProfile] = useState<SellerProfile>({ businessName: '', phone: '', email: '', address: '', city: '', state: '', sellerLogoUrl: '', gstNumber: '' });
  const [billing, setBilling] = useState<BillingSettings>({ bankName: '', accountNumber: '', accountName: '', ifscCode: '', branch: '', upiId: '', invoiceTerms: '', invoiceBackgroundImage: '' });
  const [showBgPreview, setShowBgPreview] = useState(false);
  const [uploading, setUploading] = useState(false);
  const bgInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (permLoading || !token) return;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/business-tools/seller-profile`, { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          if (data.profile) setProfile(data.profile);
          if (data.billingSettings) setBilling(prev => ({ ...prev, ...data.billingSettings }));
        }
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [token, permLoading]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/business-tools/seller-profile`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...profile, billingSettings: billing }),
      });
      if (res.ok) alert('Settings saved successfully');
      else { const d = await res.json(); alert(d.detail || 'Failed to save'); }
    } catch { alert('Network error'); }
    setSaving(false);
  };

  const uploadBgImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { alert('File too large. Max 5MB.'); return; }
    if (!['image/png', 'image/jpeg', 'image/jpg'].includes(file.type)) { alert('Only PNG/JPG allowed.'); return; }

    setUploading(true);
    try {
      const result = await uploadSellerProductImage(file);
      setBilling(prev => ({ ...prev, invoiceBackgroundImage: result.url }));
    } catch { alert('Upload failed'); }
    setUploading(false);
  };

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Business Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your business profile and billing settings</p>
        </div>
        <button onClick={save} disabled={saving} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium" data-testid="save-settings-btn">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Settings
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1" data-testid="settings-tabs">
        <button onClick={() => setActiveTab('profile')} className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${activeTab === 'profile' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-900'}`} data-testid="tab-profile">
          <Building2 className="h-4 w-4" /> Business Profile
        </button>
        <button onClick={() => setActiveTab('billing')} className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${activeTab === 'billing' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-900'}`} data-testid="tab-billing">
          <CreditCard className="h-4 w-4" /> Billing Settings
        </button>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="profile-section">
          <h2 className="text-lg font-semibold text-gray-900">Business Profile</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-xs font-medium text-gray-500 mb-1">Business Name</label><input type="text" value={profile.businessName} onChange={e => setProfile(p => ({ ...p, businessName: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="business-name-input" /></div>
            <div><label className="block text-xs font-medium text-gray-500 mb-1">GSTIN</label><input type="text" value={profile.gstNumber} onChange={e => setProfile(p => ({ ...p, gstNumber: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="22AAAAA0000A1Z5" data-testid="gstin-input" /></div>
            <div><label className="block text-xs font-medium text-gray-500 mb-1">Phone</label><input type="text" value={profile.phone} onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="phone-input" /></div>
            <div><label className="block text-xs font-medium text-gray-500 mb-1">Email</label><input type="email" value={profile.email} onChange={e => setProfile(p => ({ ...p, email: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="email-input" /></div>
            <div className="sm:col-span-2"><label className="block text-xs font-medium text-gray-500 mb-1">Address</label><textarea value={profile.address} onChange={e => setProfile(p => ({ ...p, address: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} data-testid="address-input" /></div>
            <div><label className="block text-xs font-medium text-gray-500 mb-1">City</label><input type="text" value={profile.city} onChange={e => setProfile(p => ({ ...p, city: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="city-input" /></div>
            <div><label className="block text-xs font-medium text-gray-500 mb-1">State</label><input type="text" value={profile.state} onChange={e => setProfile(p => ({ ...p, state: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="state-input" /></div>
          </div>
        </div>
      )}

      {/* Billing Tab */}
      {activeTab === 'billing' && (
        <div className="space-y-6">
          {/* Bank Details */}
          <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="bank-details-section">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><CreditCard className="h-5 w-5 text-blue-600" /> Bank Details</h2>
            <p className="text-xs text-gray-500">These details will automatically appear on every invoice footer.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Account Name</label><input type="text" value={billing.accountName} onChange={e => setBilling(p => ({ ...p, accountName: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="account-name-input" /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Bank Name</label><input type="text" value={billing.bankName} onChange={e => setBilling(p => ({ ...p, bankName: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Bank of India" data-testid="bank-name-input" /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Account Number</label><input type="text" value={billing.accountNumber} onChange={e => setBilling(p => ({ ...p, accountNumber: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="account-number-input" /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">IFSC Code</label><input type="text" value={billing.ifscCode} onChange={e => setBilling(p => ({ ...p, ifscCode: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="BKID0002017" data-testid="ifsc-code-input" /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Branch Name</label><input type="text" value={billing.branch} onChange={e => setBilling(p => ({ ...p, branch: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="branch-input" /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">UPI ID (optional)</label><input type="text" value={billing.upiId} onChange={e => setBilling(p => ({ ...p, upiId: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="business@upi" data-testid="upi-id-input" /></div>
            </div>
          </div>

          {/* Terms & Conditions */}
          <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="terms-section">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><FileText className="h-5 w-5 text-indigo-600" /> Invoice Terms & Conditions</h2>
            <p className="text-xs text-gray-500">This text will appear in the footer of every invoice automatically.</p>
            <textarea value={billing.invoiceTerms} onChange={e => setBilling(p => ({ ...p, invoiceTerms: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={5} placeholder={DEFAULT_TERMS} data-testid="invoice-terms-input" />
            {!billing.invoiceTerms && (
              <button onClick={() => setBilling(p => ({ ...p, invoiceTerms: DEFAULT_TERMS }))} className="text-xs text-blue-600 hover:text-blue-800 font-medium" data-testid="use-default-terms-btn">
                Use default terms
              </button>
            )}
          </div>

          {/* Invoice Background Template */}
          <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="background-section">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><ImageIcon className="h-5 w-5 text-purple-600" /> Invoice Background Template</h2>
            <p className="text-xs text-gray-500">Upload a background image (watermark) for your invoices. PNG or JPG, max 5MB. It will appear at low opacity behind invoice content.</p>

            <div className="flex items-start gap-4">
              <div className="flex-1">
                <input ref={bgInputRef} type="file" accept="image/png,image/jpeg,image/jpg" onChange={uploadBgImage} className="hidden" />
                <button onClick={() => bgInputRef.current?.click()} disabled={uploading}
                  className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition disabled:opacity-50" data-testid="upload-bg-btn">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {uploading ? 'Uploading...' : 'Upload Background Image'}
                </button>
              </div>

              {billing.invoiceBackgroundImage && (
                <div className="flex items-center gap-2">
                  <img src={billing.invoiceBackgroundImage} alt="Background preview" className="w-16 h-20 object-cover border rounded" />
                  <div className="flex flex-col gap-1">
                    <button onClick={() => setShowBgPreview(true)} className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1" data-testid="preview-bg-btn">
                      <Eye className="h-3 w-3" /> Preview
                    </button>
                    <button onClick={() => setBilling(p => ({ ...p, invoiceBackgroundImage: '' }))} className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1" data-testid="remove-bg-btn">
                      <X className="h-3 w-3" /> Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Background Preview Modal */}
      {showBgPreview && billing.invoiceBackgroundImage && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowBgPreview(false)}>
          <div className="bg-white rounded-xl p-4 max-w-lg w-full" onClick={e => e.stopPropagation()} data-testid="bg-preview-modal">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Invoice Background Preview</h3>
              <button onClick={() => setShowBgPreview(false)} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
            </div>
            <div className="relative border rounded-lg overflow-hidden" style={{ aspectRatio: '210/297' }}>
              <img src={billing.invoiceBackgroundImage} alt="Background" className="absolute inset-0 w-full h-full object-cover" style={{ opacity: 0.08 }} />
              <div className="relative p-6 text-center">
                <p className="text-lg font-bold text-gray-900">TAX INVOICE</p>
                <p className="text-xs text-gray-500">Original for Recipient</p>
                <div className="mt-4 text-xs text-gray-400">Your invoice content will appear here over the watermark background</div>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">Background opacity is set to ~8% for readability</p>
          </div>
        </div>
      )}
    </div>
  );
}
