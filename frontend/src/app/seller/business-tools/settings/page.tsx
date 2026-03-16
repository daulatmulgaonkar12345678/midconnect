'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  Building2, Save, Loader2, Image as ImageIcon, X, Eye,
  CreditCard, FileText, Upload, Palette, Trash2
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
  companyLogoUrl: string;
}

const DEFAULT_TERMS = `1. Goods once sold will not be taken back.
2. Interest @18% p.a. will be charged if payment is not made within due date.
3. Our risk and responsibility ceases as soon as the goods leave our premises.
4. Subject to local jurisdiction only. E.&O.E.`;

type TabKey = 'profile' | 'billing' | 'branding' | 'catalog';

interface CatalogSettings {
  showImage: boolean;
  showName: boolean;
  showCategory: boolean;
  showSpecification: boolean;
  showDescription: boolean;
  showPrice: boolean;
  showUnit: boolean;
  showMoq: boolean;
}

export default function SettingsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission, token, loading: permLoading } = usePermissions();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('profile');
  const [profile, setProfile] = useState<SellerProfile>({ businessName: '', phone: '', email: '', address: '', city: '', state: '', sellerLogoUrl: '', gstNumber: '' });
  const [billing, setBilling] = useState<BillingSettings>({ bankName: '', accountNumber: '', accountName: '', ifscCode: '', branch: '', upiId: '', invoiceTerms: '', invoiceBackgroundImage: '', companyLogoUrl: '' });
  const [catalogSettings, setCatalogSettings] = useState<CatalogSettings>({ showImage: true, showName: true, showCategory: true, showSpecification: true, showDescription: true, showPrice: true, showUnit: true, showMoq: true });
  const [showPreview, setShowPreview] = useState<'logo' | 'bg' | null>(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingBg, setUploadingBg] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);
  const bgInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (permLoading || !token) return;
    (async () => {
      try {
        const [profileRes, catalogRes] = await Promise.all([
          fetch(`${API_URL}/api/business-tools/seller-profile`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API_URL}/api/business-tools/catalog-settings`, { headers: { Authorization: `Bearer ${token}` } })
        ]);
        if (profileRes.ok) {
          const data = await profileRes.json();
          if (data.profile) setProfile(data.profile);
          if (data.billingSettings) setBilling(prev => ({ ...prev, ...data.billingSettings }));
        }
        if (catalogRes.ok) {
          const catData = await catalogRes.json();
          setCatalogSettings(prev => ({ ...prev, ...catData }));
        }
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [token, permLoading]);

  const save = async () => {
    setSaving(true);
    try {
      const [profileRes, catalogRes] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/seller-profile`, {
          method: 'PUT',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...profile, billingSettings: billing }),
        }),
        fetch(`${API_URL}/api/business-tools/catalog-settings`, {
          method: 'PUT',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ settings: catalogSettings }),
        })
      ]);
      if (profileRes.ok && catalogRes.ok) alert('Settings saved successfully');
      else alert('Some settings may not have saved');
    } catch { alert('Network error'); }
    setSaving(false);
  };

  const uploadLogo = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { alert('File too large. Max 2MB.'); return; }
    if (!['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'].includes(file.type)) { alert('Only PNG, JPG, or SVG allowed.'); return; }
    setUploadingLogo(true);
    try {
      const result = await uploadSellerProductImage(file);
      setBilling(prev => ({ ...prev, companyLogoUrl: result.url }));
    } catch { alert('Logo upload failed'); }
    setUploadingLogo(false);
  };

  const uploadBgImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { alert('File too large. Max 5MB.'); return; }
    if (!['image/png', 'image/jpeg', 'image/jpg'].includes(file.type)) { alert('Only PNG/JPG allowed.'); return; }
    setUploadingBg(true);
    try {
      const result = await uploadSellerProductImage(file);
      setBilling(prev => ({ ...prev, invoiceBackgroundImage: result.url }));
    } catch { alert('Upload failed'); }
    setUploadingBg(false);
  };

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Business Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your business profile, billing, and branding</p>
        </div>
        <button onClick={save} disabled={saving} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium" data-testid="save-settings-btn">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Settings
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1" data-testid="settings-tabs">
        {([
          { key: 'profile' as TabKey, label: 'Business Profile', icon: Building2 },
          { key: 'billing' as TabKey, label: 'Billing Settings', icon: CreditCard },
          { key: 'branding' as TabKey, label: 'Company Branding', icon: Palette },
          { key: 'catalog' as TabKey, label: 'Catalog Settings', icon: FileText },
        ]).map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${activeTab === tab.key ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-900'}`}
            data-testid={`tab-${tab.key}`}>
            <tab.icon className="h-4 w-4" /> {tab.label}
          </button>
        ))}
      </div>

      {/* ── Profile Tab ── */}
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

      {/* ── Billing Tab ── */}
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
        </div>
      )}

      {/* ── Branding Tab ── */}
      {activeTab === 'branding' && (
        <div className="space-y-6">
          {/* Company Logo */}
          <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="company-logo-section">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><Palette className="h-5 w-5 text-teal-600" /> Company Logo</h2>
            <p className="text-xs text-gray-500">Upload your company logo to appear on invoice headers. PNG, JPG, or SVG, max 2MB.</p>

            <div className="flex items-start gap-4">
              <div className="flex-1">
                <input ref={logoInputRef} type="file" accept="image/png,image/jpeg,image/jpg,image/svg+xml" onChange={uploadLogo} className="hidden" />
                <button onClick={() => logoInputRef.current?.click()} disabled={uploadingLogo}
                  className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-teal-400 hover:text-teal-600 transition disabled:opacity-50" data-testid="upload-logo-btn">
                  {uploadingLogo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {uploadingLogo ? 'Uploading...' : 'Upload Company Logo'}
                </button>
              </div>

              {billing.companyLogoUrl && (
                <div className="flex items-center gap-3">
                  <img src={billing.companyLogoUrl} alt="Company logo" className="w-16 h-16 object-contain border rounded bg-gray-50 p-1" />
                  <div className="flex flex-col gap-1">
                    <button onClick={() => setShowPreview('logo')} className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1" data-testid="preview-logo-btn">
                      <Eye className="h-3 w-3" /> Preview
                    </button>
                    <button onClick={() => setBilling(p => ({ ...p, companyLogoUrl: '' }))} className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1" data-testid="remove-logo-btn">
                      <Trash2 className="h-3 w-3" /> Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Invoice Background Template */}
          <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="background-section">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><ImageIcon className="h-5 w-5 text-purple-600" /> Invoice Background Template</h2>
            <p className="text-xs text-gray-500">Upload a background image (watermark) for your invoices. PNG or JPG, max 5MB. It will appear at low opacity behind invoice content.</p>

            <div className="flex items-start gap-4">
              <div className="flex-1">
                <input ref={bgInputRef} type="file" accept="image/png,image/jpeg,image/jpg" onChange={uploadBgImage} className="hidden" />
                <button onClick={() => bgInputRef.current?.click()} disabled={uploadingBg}
                  className="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-purple-400 hover:text-purple-600 transition disabled:opacity-50" data-testid="upload-bg-btn">
                  {uploadingBg ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {uploadingBg ? 'Uploading...' : 'Upload Background Image'}
                </button>
              </div>

              {billing.invoiceBackgroundImage && (
                <div className="flex items-center gap-3">
                  <img src={billing.invoiceBackgroundImage} alt="Background preview" className="w-16 h-20 object-cover border rounded" />
                  <div className="flex flex-col gap-1">
                    <button onClick={() => setShowPreview('bg')} className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1" data-testid="preview-bg-btn">
                      <Eye className="h-3 w-3" /> Preview
                    </button>
                    <button onClick={() => setBilling(p => ({ ...p, invoiceBackgroundImage: '' }))} className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1" data-testid="remove-bg-btn">
                      <Trash2 className="h-3 w-3" /> Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Branding Summary */}
          <div className="bg-gray-50 rounded-xl border border-dashed border-gray-200 p-5" data-testid="branding-summary">
            <p className="text-xs font-medium text-gray-500 mb-3">Invoice Branding Summary</p>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${billing.companyLogoUrl ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                <span className="text-gray-600">Company Logo: <span className="font-medium">{billing.companyLogoUrl ? 'Uploaded' : 'Not set'}</span></span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${billing.invoiceBackgroundImage ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                <span className="text-gray-600">Background: <span className="font-medium">{billing.invoiceBackgroundImage ? 'Uploaded' : 'Not set'}</span></span>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 mt-3">Your branding will be applied to all generated invoice PDFs. Click Save Settings to persist changes.</p>
          </div>
        </div>
      )}

      {/* ── Catalog Settings Tab ── */}
      {activeTab === 'catalog' && (
        <div className="bg-white rounded-xl border p-6 space-y-4" data-testid="catalog-settings-section">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><FileText className="h-5 w-5 text-teal-600" /> Catalog Sharing Settings</h2>
          <p className="text-xs text-gray-500">Choose which product fields are included when generating PDF and Excel catalogs for buyers/suppliers.</p>
          <div className="grid grid-cols-2 gap-3 mt-4">
            {([
              { key: 'showImage' as keyof CatalogSettings, label: 'Product Image' },
              { key: 'showName' as keyof CatalogSettings, label: 'Product Name' },
              { key: 'showCategory' as keyof CatalogSettings, label: 'Category' },
              { key: 'showSpecification' as keyof CatalogSettings, label: 'Specification' },
              { key: 'showDescription' as keyof CatalogSettings, label: 'Description' },
              { key: 'showPrice' as keyof CatalogSettings, label: 'Selling Price' },
              { key: 'showUnit' as keyof CatalogSettings, label: 'Unit' },
              { key: 'showMoq' as keyof CatalogSettings, label: 'Minimum Order Qty (MOQ)' },
            ]).map(field => (
              <label key={field.key} className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer" data-testid={`catalog-field-${field.key}`}>
                <input type="checkbox" checked={catalogSettings[field.key]} onChange={e => setCatalogSettings(prev => ({ ...prev, [field.key]: e.target.checked }))}
                  className="rounded border-gray-300 text-teal-600 focus:ring-teal-500" />
                <span className="text-sm text-gray-700">{field.label}</span>
              </label>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-3">These settings control both PDF and Excel catalog generation. Click Save Settings to persist.</p>
        </div>
      )}


      {/* ── Preview Modal: Invoice Layout ── */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowPreview(null)}>
          <div className="bg-white rounded-xl p-4 max-w-lg w-full" onClick={e => e.stopPropagation()} data-testid="branding-preview-modal">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">{showPreview === 'logo' ? 'Logo on Invoice Preview' : 'Invoice Background Preview'}</h3>
              <button onClick={() => setShowPreview(null)} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
            </div>
            <div className="relative border rounded-lg overflow-hidden bg-white" style={{ aspectRatio: '210/297' }}>
              {/* Background layer */}
              {billing.invoiceBackgroundImage && (
                <img src={billing.invoiceBackgroundImage} alt="Background" className="absolute inset-0 w-full h-full object-cover" style={{ opacity: 0.08 }} />
              )}
              {/* Content layer */}
              <div className="relative p-6">
                {/* Header with logo */}
                <div className="flex items-start justify-between mb-4">
                  {billing.companyLogoUrl ? (
                    <img src={billing.companyLogoUrl} alt="Logo" className="w-14 h-14 object-contain" />
                  ) : (
                    <div className="w-14 h-14 border-2 border-dashed border-gray-200 rounded flex items-center justify-center">
                      <span className="text-[9px] text-gray-300">Logo</span>
                    </div>
                  )}
                  <div className="text-center flex-1">
                    <p className="text-lg font-bold text-gray-900">TAX INVOICE</p>
                    <p className="text-xs text-gray-500">Original for Recipient</p>
                  </div>
                  <div className="w-14 h-14 border border-gray-200 rounded flex items-center justify-center">
                    <span className="text-[8px] text-gray-300">QR</span>
                  </div>
                </div>
                <div className="h-px bg-gray-800 mb-3" />
                {/* Sample content */}
                <div className="grid grid-cols-2 gap-4 text-[10px] text-gray-500 mb-4">
                  <div>
                    <p className="font-semibold text-gray-700 mb-1">Seller Details</p>
                    <p>{profile.businessName || 'Your Business'}</p>
                    <p>{profile.address || 'Address'}</p>
                    <p>GSTIN: {profile.gstNumber || 'XXXXXXXX'}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-700 mb-1">Buyer Details</p>
                    <p>Buyer Company Name</p>
                    <p>Buyer Address</p>
                    <p>GSTIN: XXXXXXXX</p>
                  </div>
                </div>
                <div className="border border-gray-200 rounded text-[9px]">
                  <div className="grid grid-cols-5 bg-gray-100 px-2 py-1 font-semibold text-gray-600">
                    <span>Item</span><span>HSN</span><span className="text-right">Qty</span><span className="text-right">Rate</span><span className="text-right">Amount</span>
                  </div>
                  <div className="grid grid-cols-5 px-2 py-1 text-gray-500">
                    <span>Sample Product</span><span>8501</span><span className="text-right">10</span><span className="text-right">500.00</span><span className="text-right">5,000.00</span>
                  </div>
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">
              {showPreview === 'bg' ? 'Background opacity is set to ~8% for readability' : 'Logo appears at top-left corner of the invoice'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
