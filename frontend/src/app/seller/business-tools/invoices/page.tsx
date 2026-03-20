'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import { useNetworkContext } from '@/context/NetworkContext';
import { useOfflineInvoices } from '@/hooks/useOfflineInvoices';
import { toast } from 'sonner';
import {
  FileText, Plus, X, Download, Eye, Trash2, Send, CreditCard,
  IndianRupee, ChevronDown, ChevronUp, Clock, CheckCircle2,
  AlertCircle, AlertTriangle, Banknote, Calendar, MessageCircle, Upload, Image as ImageIcon,
  FileDown, Bell, Settings, ExternalLink, Paperclip, Loader2, WifiOff, CloudOff
} from 'lucide-react';
import { uploadPaymentReceipt } from '@/lib/cloudinary';
import { INDIAN_STATES, calcGstBreakdown } from '@/lib/indian-states';
import Select, { StylesConfig, SingleValue } from 'react-select';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ── React-Select shared styles ──
interface SelectOption { value: string; label: string; }
interface ProductOption extends SelectOption { stock: number; reserved: number; desc: string; }

const selectStyles: StylesConfig<SelectOption, false> = {
  control: (base, state) => ({ ...base, minHeight: '38px', borderRadius: '0.5rem', borderColor: state.isFocused ? '#6366f1' : '#d1d5db', boxShadow: state.isFocused ? '0 0 0 1px #6366f1' : 'none', fontSize: '0.875rem', '&:hover': { borderColor: '#6366f1' } }),
  menu: (base) => ({ ...base, zIndex: 50, fontSize: '0.875rem' }),
  option: (base, state) => ({ ...base, backgroundColor: state.isSelected ? '#6366f1' : state.isFocused ? '#eef2ff' : 'white', color: state.isSelected ? 'white' : '#1f2937', padding: '8px 12px', cursor: 'pointer' }),
  placeholder: (base) => ({ ...base, color: '#9ca3af' }),
  singleValue: (base) => ({ ...base, color: '#1f2937' }),
  input: (base) => ({ ...base, color: '#1f2937' }),
};

const productSelectStyles: StylesConfig<ProductOption, false> = {
  control: (base, state) => ({ ...base, minHeight: '32px', borderRadius: '0.25rem', borderColor: state.isFocused ? '#6366f1' : '#d1d5db', boxShadow: state.isFocused ? '0 0 0 1px #6366f1' : 'none', fontSize: '0.875rem', '&:hover': { borderColor: '#6366f1' } }),
  menu: (base) => ({ ...base, zIndex: 50, fontSize: '0.8rem', minWidth: '320px' }),
  option: (base, state) => ({ ...base, backgroundColor: state.isSelected ? '#6366f1' : state.isFocused ? '#eef2ff' : 'white', color: state.isSelected ? 'white' : '#1f2937', padding: '6px 10px', cursor: 'pointer' }),
  placeholder: (base) => ({ ...base, color: '#9ca3af', fontSize: '0.8rem' }),
  singleValue: (base) => ({ ...base, color: '#1f2937', fontSize: '0.8rem' }),
  input: (base) => ({ ...base, color: '#1f2937', fontSize: '0.8rem' }),
  valueContainer: (base) => ({ ...base, padding: '0 8px' }),
  indicatorsContainer: (base) => ({ ...base, '> div': { padding: '4px' } }),
};

// ── Types ──

interface Spec { key: string; value: string; }
interface InvoiceListing { id: string; productName: string; productType: string; stock: number; reservedStock: number; availableStock: number; price: number; gstRate: number; hsnCode: string; description: string; specifications: Spec[]; }
interface InvoiceFormItem { productId: string; productName: string; hsnCode: string; description: string; quantity: number; price: number; discount: number; discountType: '%' | 'Rs'; gstPercent: number; allSpecs: Spec[]; selectedSpecs: Spec[]; customSpecs: Spec[]; showSpecs: boolean; }
interface Buyer { id: string; buyerName: string; company?: string; phone?: string; state?: string; gstNumber?: string; address?: string; shippingAddresses?: { id: string; addressLine1: string; addressLine2?: string; city: string; state: string; pincode: string; country: string; contactPerson?: string; phone?: string; isDefault: boolean; }[]; }
interface InvoiceItem { productName: string; description?: string; hsnCode?: string; quantity: number; price: number; gstPercent: number; taxableAmount?: number; cgst?: number; cgstRate?: number; sgst?: number; sgstRate?: number; igst?: number; igstRate?: number; gstAmount: number; total: number; selected_specifications?: Spec[]; }
interface PaymentEntry { id: string; amount: number; paymentDate: string; paymentMethod: string; accountName?: string; referenceNumber?: string; notes?: string; receiptUrls?: string[]; createdAt: string; }
interface Invoice {
  id: string; invoiceNumber: string; buyerName: string; buyerPhone?: string; buyerId?: string; date: string;
  items: InvoiceItem[]; subtotal: number; cgst?: number; sgst?: number; igst?: number; gst: number; total: number;
  totalPaid: number; pendingAmount: number; status: string; notes?: string;
  payments?: PaymentEntry[]; buyerDetails?: Record<string, string>; dueDays?: number;
  taxType?: string; placeOfSupply?: string;
  paymentTerms?: string;
  additionalCharges?: { name: string; type: string; value: number; amount: number }[];
  freight?: number; tcsEnabled?: boolean; tcsPercent?: number; tcsAmount?: number; roundOff?: number;
  sentAt?: string; sentVia?: string;
}
interface Reminder {
  invoiceId: string; invoiceNumber: string; buyerName: string; buyerPhone: string;
  daysSince: number; reminderLevel: number; reminderType: string;
  pendingAmount: number; total: number; totalPaid: number;
  message: string; whatsappLink: string | null; status: string;
}
interface ReminderSettings { enabled: boolean; reminderDays: number[]; customMessages: Record<string, string>; }

// ── Constants ──

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700', sent: 'bg-blue-100 text-blue-700', viewed: 'bg-cyan-100 text-cyan-700',
  partially_paid: 'bg-amber-100 text-amber-700', paid: 'bg-emerald-100 text-emerald-700',
  overdue: 'bg-red-100 text-red-700', cancelled: 'bg-red-50 text-red-500',
};
const statusLabels: Record<string, string> = {
  draft: 'Draft', sent: 'Sent', viewed: 'Viewed', partially_paid: 'Partially Paid',
  paid: 'Paid', overdue: 'Overdue', cancelled: 'Cancelled',
};
const paymentMethods = [
  { value: 'upi', label: 'UPI' }, { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'cash', label: 'Cash' }, { value: 'cheque', label: 'Cheque' }, { value: 'other', label: 'Other' },
];
const RECEIPT_REQUIRED_METHODS = ['upi', 'bank_transfer', 'cheque'];

function emptyItem(): InvoiceFormItem {
  return { productId: '', productName: '', hsnCode: '', description: '', quantity: 1, price: 0, discount: 0, discountType: '%', gstPercent: 18, allSpecs: [], selectedSpecs: [], customSpecs: [], showSpecs: false };
}
function fmt(n: number) { return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmtDate(d: string) { try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); } catch { return d; } }
function isReceiptRequired(method: string) { return RECEIPT_REQUIRED_METHODS.includes(method); }

// ── Main Component ──

export default function InvoicesPage() {
  const { getIdToken, user } = useAuth();
  const { hasPermission } = usePermissions();
  const { isOnline } = useNetworkContext();
  const searchParams = useSearchParams();
  const prefillApplied = useRef(false);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [listings, setListings] = useState<InvoiceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [viewInvoice, setViewInvoice] = useState<Invoice | null>(null);
  const [statusFilter, setStatusFilter] = useState('all');
  // Payment modal
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentInvoiceId, setPaymentInvoiceId] = useState('');
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [receiptFiles, setReceiptFiles] = useState<File[]>([]);
  const [receiptUploading, setReceiptUploading] = useState(false);
  const [uploadedReceiptUrls, setUploadedReceiptUrls] = useState<string[]>([]);
  const receiptInputRef = useRef<HTMLInputElement>(null);
  const [paymentForm, setPaymentForm] = useState({ amount: '', paymentDate: new Date().toISOString().slice(0, 10), paymentMethod: 'upi', accountName: '', referenceNumber: '', notes: '' });
  // Reminders
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [showReminders, setShowReminders] = useState(false);
  const [showReminderSettings, setShowReminderSettings] = useState(false);
  const [reminderSettings, setReminderSettings] = useState<ReminderSettings>({ enabled: true, reminderDays: [3, 7, 15], customMessages: {} });
  const [reminderDaysInput, setReminderDaysInput] = useState('3, 7, 15');
  // Image preview
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  // Stock shortage modal
  const [shortageModal, setShortageModal] = useState<{
    shortages: Array<{
      productId: string; productName: string;
      requestedQty: number; totalStock: number; reservedStock: number;
      availableStock: number; shortage: number;
    }>;
    payload: any;
  } | null>(null);
  const [shortageSubmitting, setShortageSubmitting] = useState(false);
  // Seller state for GST calculation
  const [sellerState, setSellerState] = useState('');
  // PDF Download modal
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfModalInvoice, setPdfModalInvoice] = useState<{ id: string; invoiceNumber: string } | null>(null);
  const [pdfCopies, setPdfCopies] = useState<Record<string, boolean>>({ original: true, transporter: true, supplier: true, office: true });
  const [pdfDownloading, setPdfDownloading] = useState(false);
  // Invoice form
  const [formData, setFormData] = useState<{
    buyerId: string; items: InvoiceFormItem[]; notes: string; deductStock: boolean; dueDays: number;
    poNumber: string; challanNumber: string; placeOfSupply: string; termsAndConditions: string;
    shippingAddressId: string;
    transport: { transporterName: string; lrNumber: string; vehicleNumber: string; bookingLocation: string; numberOfPackages: string; };
    paymentTerms: string;
    freight: number;
    tcsEnabled: boolean;
    tcsPercent: number;
  }>({
    buyerId: '', items: [emptyItem()], notes: '', deductStock: true, dueDays: 7,
    poNumber: '', challanNumber: '', placeOfSupply: '', termsAndConditions: '',
    shippingAddressId: '',
    transport: { transporterName: '', lrNumber: '', vehicleNumber: '', bookingLocation: '', numberOfPackages: '' },
    paymentTerms: '',
    freight: 0,
    tcsEnabled: false,
    tcsPercent: 0.1,
  });

  // Offline invoices hook
  const userId = user?.uid || null;
  const { offlineDrafts, saveDraftOffline, deleteDraftOffline } = useOfflineInvoices(userId);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchAll = useCallback(async () => {
    // If offline, try loading from IndexedDB cache
    if (!isOnline) {
      try {
        const { getCachedData } = await import('@/lib/offlineStore');
        const cachedInvoices = await getCachedData<Invoice[]>('invoices');
        const cachedBuyers = await getCachedData<Buyer[]>('buyers');
        const cachedListings = await getCachedData<InvoiceListing[]>('listings');
        const cachedState = await getCachedData<string>('sellerState');
        if (cachedInvoices) setInvoices(cachedInvoices);
        if (cachedBuyers) setBuyers(cachedBuyers);
        if (cachedListings) setListings(cachedListings);
        if (cachedState) setSellerState(cachedState);
      } catch { /* empty */ }
      setLoading(false);
      return;
    }
    try {
      const h = await authHeaders();
      const [invR, buyR, listR, profileR] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/invoices`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/buyers`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/invoice-products`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/seller-profile`, { headers: h }),
      ]);
      const invoicesData = invR.ok ? (await invR.json()).invoices || [] : [];
      const buyersData = buyR.ok ? (await buyR.json()).buyers || [] : [];
      const listingsData = listR.ok ? (await listR.json()).products || [] : [];
      let state = '';
      if (profileR.ok) {
        const pData = await profileR.json();
        state = pData?.profile?.state || '';
      }
      setInvoices(invoicesData);
      setBuyers(buyersData);
      setListings(listingsData);
      setSellerState(state);

      // Cache data in IndexedDB for offline access
      try {
        const { cacheData } = await import('@/lib/offlineStore');
        await Promise.all([
          cacheData('invoices', invoicesData),
          cacheData('buyers', buyersData),
          cacheData('listings', listingsData),
          cacheData('sellerState', state),
        ]);
      } catch { /* cache failed silently */ }
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders, isOnline]);

  const fetchReminders = useCallback(async () => {
    try {
      const h = await authHeaders();
      const [remR, setR] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/invoice-reminders`, { headers: h }),
        fetch(`${API_URL}/api/business-tools/reminder-settings`, { headers: h }),
      ]);
      if (remR.ok) { const d = await remR.json(); setReminders(d.reminders || []); }
      if (setR.ok) {
        const d = await setR.json();
        const s = d.settings || { enabled: true, reminderDays: [3, 7, 15], customMessages: {} };
        setReminderSettings(s);
        setReminderDaysInput(s.reminderDays.join(', '));
      }
    } catch { /* empty */ }
  }, [authHeaders]);

  useEffect(() => { fetchAll(); fetchReminders(); }, [fetchAll, fetchReminders]);

  // Handle quotation → invoice conversion prefill
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('from_quotation') !== 'true') return;

    const applyPrefill = (prefill: Record<string, unknown>) => {
      const items = ((prefill.items || []) as Record<string, unknown>[]).map((i) => ({
        productId: (i.productId as string) || '', productName: (i.productName as string) || '',
        description: (i.description as string) || '', hsnCode: (i.hsnCode as string) || '',
        quantity: (i.quantity as number) || 1, price: (i.price as number) || 0, discount: (i.discount as number) || 0,
        discountType: ((i.discountType as string) || '%') as '%' | 'Rs',
        gstPercent: (i.gstPercent as number) || 18, allSpecs: [], selectedSpecs: [], customSpecs: [], showSpecs: false,
      }));
      setFormData(p => ({
        ...p,
        buyerId: (prefill.buyerId as string) || '',
        items: items.length > 0 ? items : [emptyItem()],
        notes: (prefill.notes as string) || '',
        termsAndConditions: (prefill.termsAndConditions as string) || '',
        placeOfSupply: (prefill.placeOfSupply as string) || '',
      }));
      setShowForm(true);
      toast.info(`Pre-filled from Quotation ${(prefill.sourceQuotationNumber as string) || ''}`);
      // Store sourceQuotationId for marking as converted after invoice creation
      if (prefill.sourceQuotationId) {
        sessionStorage.setItem('source_quotation_id', prefill.sourceQuotationId as string);
      }
    };

    // Try sessionStorage first
    try {
      const raw = sessionStorage.getItem('quotation_prefill');
      if (raw) {
        const prefill = JSON.parse(raw);
        sessionStorage.removeItem('quotation_prefill');
        applyPrefill(prefill);
        return;
      }
    } catch { /* empty */ }

    // Fallback: fetch from server using quotation_id from URL
    const quotationId = params.get('quotation_id');
    if (quotationId) {
      (async () => {
        try {
          const h = await authHeaders();
          const res = await fetch(`${API_URL}/api/business-tools/quotations/get-prefill/${quotationId}`, { headers: h });
          if (res.ok) {
            const data = await res.json();
            applyPrefill(data.prefill);
          }
        } catch { /* empty */ }
      })();
    }
  }, []);

  // Prefill from query params (e.g. from Pending Orders → Create Invoice)
  useEffect(() => {
    if (prefillApplied.current || loading || buyers.length === 0) return;
    const buyerId = searchParams.get('buyerId');
    const productId = searchParams.get('productId');
    const qty = searchParams.get('qty');
    const price = searchParams.get('price');
    const gstPercent = searchParams.get('gstPercent');
    if (buyerId) {
      prefillApplied.current = true;
      const buyer = buyers.find(b => b.id === buyerId);
      const item = { ...emptyItem() };
      if (productId) item.productId = productId;
      if (qty) item.quantity = parseInt(qty) || 1;
      if (price) item.price = parseFloat(price) || 0;
      if (gstPercent) item.gstPercent = parseFloat(gstPercent) || 18;
      // Fill product name from listings if available
      if (productId) {
        const listing = listings.find(l => l.id === productId);
        if (listing) {
          item.productName = listing.productName;
          item.hsnCode = listing.hsnCode || '';
          if (listing.gstRate !== undefined && !gstPercent) item.gstPercent = listing.gstRate;
        }
      }
      setFormData(p => ({
        ...p,
        buyerId,
        items: [item],
        placeOfSupply: buyer?.state || '',
      }));
      setShowForm(true);
    }
  }, [searchParams, loading, buyers, listings]);

  const fetchInvoiceDetail = useCallback(async (invoiceId: string) => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${invoiceId}`, { headers: h });
      if (res.ok) setViewInvoice((await res.json()).invoice);
    } catch { /* empty */ }
  }, [authHeaders]);

  const openInvoiceDetail = (inv: Invoice) => { setViewInvoice(inv); fetchInvoiceDetail(inv.id); };

  // ── Invoice form handlers ──
  const onProductSelect = (idx: number, listingId: string) => {
    const listing = listings.find(l => l.id === listingId);
    const items = [...formData.items];
    items[idx] = { ...items[idx], productId: listingId, productName: listing?.productName || '', hsnCode: listing?.hsnCode || '', description: listing?.description || '', price: listing?.price || items[idx].price, gstPercent: listing?.gstRate || items[idx].gstPercent, allSpecs: listing?.specifications || [], selectedSpecs: [...(listing?.specifications || [])], customSpecs: [], showSpecs: (listing?.specifications?.length || 0) > 0 };
    setFormData(p => ({ ...p, items }));
  };
  const toggleSpec = (itemIdx: number, specIdx: number) => {
    const items = [...formData.items]; const item = { ...items[itemIdx] }; const spec = item.allSpecs[specIdx];
    const isSel = item.selectedSpecs.some(s => s.key === spec.key && s.value === spec.value);
    item.selectedSpecs = isSel ? item.selectedSpecs.filter(s => !(s.key === spec.key && s.value === spec.value)) : [...item.selectedSpecs, spec];
    items[itemIdx] = item; setFormData(p => ({ ...p, items }));
  };
  const addCustomSpec = (i: number) => { const items = [...formData.items]; items[i] = { ...items[i], customSpecs: [...items[i].customSpecs, { key: '', value: '' }] }; setFormData(p => ({ ...p, items })); };
  const updateCustomSpec = (i: number, si: number, f: 'key' | 'value', v: string) => { const items = [...formData.items]; const cs = [...items[i].customSpecs]; cs[si] = { ...cs[si], [f]: v }; items[i] = { ...items[i], customSpecs: cs }; setFormData(p => ({ ...p, items })); };
  const removeCustomSpec = (i: number, si: number) => { const items = [...formData.items]; items[i] = { ...items[i], customSpecs: items[i].customSpecs.filter((_, j) => j !== si) }; setFormData(p => ({ ...p, items })); };
  const addItem = () => setFormData(p => ({ ...p, items: [...p.items, emptyItem()] }));
  const removeItem = (i: number) => setFormData(p => ({ ...p, items: p.items.filter((_, j) => j !== i) }));

  const effectivePlaceOfSupply = formData.placeOfSupply || buyers.find(b => b.id === formData.buyerId)?.state || '';
  const formTotals = formData.items.reduce((a, it) => {
    const base = it.quantity * it.price;
    const discAmt = it.discountType === '%' ? base * (it.discount / 100) : (it.discount || 0);
    const taxable = Math.max(base - discAmt, 0);
    const b = calcGstBreakdown(taxable, it.gstPercent, sellerState, effectivePlaceOfSupply);
    return { subtotal: a.subtotal + b.taxable, cgst: a.cgst + b.cgst, sgst: a.sgst + b.sgst, igst: a.igst + b.igst, gst: a.gst + b.totalTax, total: a.total + b.total };
  }, { subtotal: 0, cgst: 0, sgst: 0, igst: 0, gst: 0, total: 0 });

  const buildPayload = () => {
    const transportData = formData.transport.transporterName || formData.transport.lrNumber || formData.transport.vehicleNumber
      ? { ...formData.transport, numberOfPackages: formData.transport.numberOfPackages ? parseInt(formData.transport.numberOfPackages) : undefined }
      : undefined;
    // Build shipping address from selected ID
    const selectedBuyer = buyers.find(b => b.id === formData.buyerId);
    const selectedAddr = formData.shippingAddressId ? (selectedBuyer?.shippingAddresses || []).find(a => a.id === formData.shippingAddressId) : undefined;
    return {
      buyerId: formData.buyerId,
      items: formData.items.map(i => ({
        productId: i.productId || null, productName: i.productName || null,
        hsnCode: i.hsnCode || null,
        description: i.description || null,
        quantity: i.quantity, price: i.price,
        discount: i.discount || 0,
        discountType: i.discountType || '%',
        gstPercent: i.gstPercent,
        selected_specifications: [...i.selectedSpecs, ...i.customSpecs.filter(s => s.key && s.value)]
      })),
      notes: formData.notes, deductStock: formData.deductStock, dueDays: formData.dueDays,
      poNumber: formData.poNumber || undefined,
      challanNumber: formData.challanNumber || undefined,
      placeOfSupply: formData.placeOfSupply || undefined,
      transport: transportData,
      termsAndConditions: formData.termsAndConditions || undefined,
      shippingAddress: selectedAddr ? { id: selectedAddr.id, addressLine1: selectedAddr.addressLine1, addressLine2: selectedAddr.addressLine2, city: selectedAddr.city, state: selectedAddr.state, pincode: selectedAddr.pincode, country: selectedAddr.country, contactPerson: selectedAddr.contactPerson, phone: selectedAddr.phone } : undefined,
      paymentTerms: formData.paymentTerms || undefined,
      additionalCharges: formData.freight > 0 ? [{ name: "Freight", type: "fixed", value: formData.freight }] : [],
      tcsEnabled: formData.tcsEnabled,
      tcsPercent: formData.tcsEnabled ? formData.tcsPercent : 0,
    };
  };

  const submitInvoice = async (payload: any) => {
    // If offline, save as draft locally
    if (!isOnline) {
      await saveDraftOffline(payload);
      setShowForm(false);
      setFormData({
        buyerId: '', items: [emptyItem()], notes: '', deductStock: true, dueDays: 7,
        poNumber: '', challanNumber: '', placeOfSupply: '', termsAndConditions: '',
        shippingAddressId: '',
        transport: { transporterName: '', lrNumber: '', vehicleNumber: '', bookingLocation: '', numberOfPackages: '' },
        paymentTerms: '', freight: 0, tcsEnabled: false, tcsPercent: 0.1,
      });
      return;
    }
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/invoices`, { method: 'POST', headers: h, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'Failed to create invoice'); return; }
    setShowForm(false);
    setFormData({
      buyerId: '', items: [emptyItem()], notes: '', deductStock: true, dueDays: 7,
      poNumber: '', challanNumber: '', placeOfSupply: '', termsAndConditions: '',
      shippingAddressId: '',
      transport: { transporterName: '', lrNumber: '', vehicleNumber: '', bookingLocation: '', numberOfPackages: '' },
      paymentTerms: '', freight: 0, tcsEnabled: false, tcsPercent: 0.1,
    });
    fetchAll();
    
    // Mark source quotation as converted (if creating from quotation)
    const params = new URLSearchParams(window.location.search);
    if (params.get('from_quotation') === 'true') {
      try {
        const sourceId = sessionStorage.getItem('source_quotation_id');
        if (sourceId) {
          sessionStorage.removeItem('source_quotation_id');
          const h2 = await authHeaders();
          await fetch(`${API_URL}/api/business-tools/quotations/${sourceId}/mark-converted`, { method: 'POST', headers: h2 });
        }
      } catch { /* empty */ }
      toast.success('Invoice created from quotation!');
    }

    if (data.pendingOrders?.length > 0) {
      const names = data.pendingOrders.map((p: any) => `${p.productName}: ${p.pendingQty} units`).join('\n');
      alert(`Invoice created with pending orders:\n${names}\n\nView them in Pending Orders section.`);
    }
  };

  const handleSubmit = async () => {
    if (!formData.buyerId) { alert('Select a buyer'); return; }
    if (formData.items.some(i => !i.productName && !i.productId)) { alert('All items need a product'); return; }
    const payload = buildPayload();

    // Skip stock check when offline
    if (isOnline && payload.deductStock) {
      const h = await authHeaders();
      const checkRes = await fetch(`${API_URL}/api/business-tools/invoices/check-stock`, { method: 'POST', headers: h, body: JSON.stringify(payload) });
      if (checkRes.ok) {
        const checkData = await checkRes.json();
        if (checkData.hasShortage) {
          setShortageModal({ shortages: checkData.shortages, payload });
          return;
        }
      }
    }

    await submitInvoice(payload);
  };

  const handleShortageAction = async (action: 'partial' | 'full_pending' | 'cancel') => {
    if (action === 'cancel' || !shortageModal) { setShortageModal(null); return; }
    setShortageSubmitting(true);
    const payload = { ...shortageModal.payload, allowPartialFulfillment: true };
    await submitInvoice(payload);
    setShortageSubmitting(false);
    setShortageModal(null);
  };

  const updateStatus = async (id: string, status: string) => {
    const h = await authHeaders();
    if (status === 'sent') {
      await fetch(`${API_URL}/api/business-tools/invoices/${id}/mark-sent`, { method: 'PUT', headers: h });
    } else {
      await fetch(`${API_URL}/api/business-tools/invoices/${id}/status`, { method: 'PUT', headers: h, body: JSON.stringify({ status }) });
    }
    fetchAll(); if (viewInvoice?.id === id) fetchInvoiceDetail(id);
  };
  const deleteInvoice = async (id: string) => {
    if (!confirm('Delete this invoice?')) return;
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/invoices/${id}`, { method: 'DELETE', headers: h });
    if (viewInvoice?.id === id) setViewInvoice(null); fetchAll();
  };
  const openPdfModal = (id: string, invoiceNumber: string) => {
    setPdfModalInvoice({ id, invoiceNumber });
    setPdfCopies({ original: true, transporter: true, supplier: true, office: true });
    setShowPdfModal(true);
  };

  const togglePdfCopy = (key: string) => setPdfCopies(p => ({ ...p, [key]: !p[key] }));
  const toggleAllCopies = (checked: boolean) => setPdfCopies({ original: checked, transporter: checked, supplier: checked, office: checked });
  const selectedCopyCount = Object.values(pdfCopies).filter(Boolean).length;
  const allCopiesSelected = selectedCopyCount === 4;

  const downloadMergedPdf = async () => {
    if (!pdfModalInvoice || selectedCopyCount === 0) return;
    setPdfDownloading(true);
    try {
      const h = await authHeaders();
      const selected = Object.entries(pdfCopies).filter(([, v]) => v).map(([k]) => k);
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${pdfModalInvoice.id}/pdf-merged?copies=${selected.join(',')}`, { headers: h });
      if (!res.ok) { alert('Failed to download PDF'); setPdfDownloading(false); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${pdfModalInvoice.invoiceNumber}-${selected.length > 1 ? 'merged' : selected[0]}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setShowPdfModal(false);
    } catch { alert('Download failed'); }
    setPdfDownloading(false);
  };

  const openEwayBill = async (id: string) => {
    const h = await authHeaders();
    const res = await fetch(`${API_URL}/api/business-tools/invoices/${id}/eway-bill`, { method: 'POST', headers: h });
    if (!res.ok) { alert('Failed to prepare E-Way Bill data'); return; }
    const data = await res.json();
    alert(`E-Way Bill data prepared for Invoice ${data.invoiceNumber}.\n\nYou will be redirected to the GST E-Way Bill portal.`);
    window.open(data.portalUrl, '_blank');
  };

  // ── WhatsApp ──
  const openWhatsApp = async (inv: Invoice, type: 'followup' | 'overdue' | 'send_invoice' = 'followup') => {
    if (!isOnline) {
      toast.error('Cannot send WhatsApp in offline mode');
      return;
    }
    const phone = inv.buyerPhone || '';
    if (!phone) { alert('Buyer phone number not available'); return; }

    // Use backend API as single source of truth for all WhatsApp messages
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${inv.id}/whatsapp-link?reminder_type=${type}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        if (data.whatsappLink) {
          window.open(data.whatsappLink, '_blank');
          return;
        }
      }
      // Fallback: if API fails, alert user
      alert('Failed to generate WhatsApp message. Please try again.');
    } catch {
      alert('Failed to generate WhatsApp message. Please try again.');
    }
  };

  // ── Payment handlers ──
  const openPaymentModal = (invoiceId: string) => {
    setPaymentInvoiceId(invoiceId);
    setPaymentForm({ amount: '', paymentDate: new Date().toISOString().slice(0, 10), paymentMethod: 'upi', accountName: '', referenceNumber: '', notes: '' });
    setReceiptFiles([]); setUploadedReceiptUrls([]);
    setShowPaymentModal(true);
  };

  const handleReceiptSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const valid = files.filter(f => ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'].includes(f.type));
    if (valid.length !== files.length) alert('Some files were skipped. Allowed: JPG, PNG, WEBP, PDF');
    setReceiptFiles(prev => [...prev, ...valid]);
  };

  const removeReceiptFile = (idx: number) => setReceiptFiles(prev => prev.filter((_, i) => i !== idx));

  const uploadReceipts = async (): Promise<string[]> => {
    if (receiptFiles.length === 0) return uploadedReceiptUrls;
    setReceiptUploading(true);
    const urls = [...uploadedReceiptUrls];
    for (const file of receiptFiles) {
      try {
        const result = await uploadPaymentReceipt(file);
        urls.push(result.url);
      } catch (err) {
        alert(`Failed to upload ${file.name}: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
    setUploadedReceiptUrls(urls);
    setReceiptFiles([]);
    setReceiptUploading(false);
    return urls;
  };

  const submitPayment = async () => {
    const amount = parseFloat(paymentForm.amount);
    if (!amount || amount <= 0) { alert('Enter a valid payment amount'); return; }
    const method = paymentForm.paymentMethod;
    // Check receipt requirement
    if (isReceiptRequired(method) && receiptFiles.length === 0 && uploadedReceiptUrls.length === 0) {
      alert(`Receipt upload is mandatory for ${method.replace('_', ' ')} payments. Please attach at least one receipt.`);
      return;
    }
    setPaymentLoading(true);
    try {
      const urls = await uploadReceipts();
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/invoices/${paymentInvoiceId}/payments`, {
        method: 'POST', headers: h,
        body: JSON.stringify({ amount, paymentDate: paymentForm.paymentDate, paymentMethod: method, accountName: paymentForm.accountName || null, referenceNumber: paymentForm.referenceNumber || null, notes: paymentForm.notes || null, receiptUrls: urls.length > 0 ? urls : null }),
      });
      const data = await res.json();
      if (!res.ok) { alert(data.detail || 'Failed to add payment'); return; }
      setShowPaymentModal(false); fetchAll(); fetchReminders();
      if (viewInvoice?.id === paymentInvoiceId) fetchInvoiceDetail(paymentInvoiceId);
    } catch { alert('Error adding payment'); }
    finally { setPaymentLoading(false); }
  };

  const deletePayment = async (invoiceId: string, paymentId: string) => {
    if (!confirm('Delete this payment entry?')) return;
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/invoices/${invoiceId}/payments/${paymentId}`, { method: 'DELETE', headers: h });
    fetchAll(); fetchReminders();
    if (viewInvoice?.id === invoiceId) fetchInvoiceDetail(invoiceId);
  };

  // ── Reminder settings ──
  const saveReminderSettings = async () => {
    const days = reminderDaysInput.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n) && n > 0);
    if (days.length === 0) { alert('Enter at least one reminder day'); return; }
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/reminder-settings`, {
      method: 'PUT', headers: h,
      body: JSON.stringify({ enabled: reminderSettings.enabled, reminderDays: days, customMessages: reminderSettings.customMessages }),
    });
    setShowReminderSettings(false); fetchReminders();
  };

  const filteredInvoices = statusFilter === 'all' ? invoices : invoices.filter(i => i.status === statusFilter);

  if (!hasPermission('create_invoice')) {
    return <div className="text-center py-12 bg-white rounded-xl border" data-testid="no-permission"><FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" /><p className="text-gray-500">No permission to manage invoices.</p></div>;
  }

  return (
    <div className="space-y-6" data-testid="invoices-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Create invoices, track payments, and manage billing</p>
        </div>
        <div className="flex items-center gap-2">
          {reminders.length > 0 && (
            <button onClick={() => setShowReminders(!showReminders)}
              className="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-amber-700 bg-amber-50 rounded-lg hover:bg-amber-100 transition" data-testid="reminders-toggle-btn">
              <Bell className="w-4 h-4" />Reminders
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] w-5 h-5 rounded-full flex items-center justify-center font-bold">{reminders.length}</span>
            </button>
          )}
          <button onClick={() => setShowReminderSettings(true)} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100" title="Reminder Settings" data-testid="reminder-settings-btn">
            <Settings className="w-4 h-4" />
          </button>
          <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 text-sm font-medium" data-testid="create-invoice-btn">
            <Plus className="w-4 h-4" /> New Invoice
          </button>
        </div>
      </div>

      {/* ── Reminders Panel ── */}
      {showReminders && reminders.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4" data-testid="reminders-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-amber-800 flex items-center gap-1.5"><Bell className="w-4 h-4" /> Payment Reminders ({reminders.length})</h3>
            <button onClick={() => setShowReminders(false)} className="text-amber-400 hover:text-amber-600"><X className="w-4 h-4" /></button>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {reminders.map((r) => (
              <div key={r.invoiceId} className={`bg-white rounded-lg p-3 border flex items-center justify-between ${r.reminderType === 'overdue' ? 'border-red-200' : r.reminderType === 'due' ? 'border-amber-200' : 'border-gray-200'}`} data-testid={`reminder-${r.invoiceId}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold text-gray-800">{r.invoiceNumber}</span>
                    <span className="text-gray-500">{r.buyerName}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${r.reminderType === 'overdue' ? 'bg-red-100 text-red-700' : r.reminderType === 'due' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                      {r.reminderType === 'overdue' ? 'Overdue' : r.reminderType === 'due' ? 'Due' : 'Friendly'}
                    </span>
                    <span className="text-xs text-gray-400">{r.daysSince}d ago</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">Pending: <span className="font-medium text-amber-600">Rs.{fmt(r.pendingAmount)}</span></p>
                </div>
                {r.whatsappLink && (
                  <a href={r.whatsappLink} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-700 ml-3 flex-shrink-0" data-testid={`reminder-wa-${r.invoiceId}`}>
                    <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'draft', 'sent', 'partially_paid', 'paid', 'overdue', 'cancelled'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${statusFilter === s ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'}`}
            data-testid={`filter-${s}`}>{statusLabels[s] || 'All'}</button>
        ))}
      </div>

      {/* ──── Create Invoice Modal ──── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-form-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Invoice</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Buyer *</label>
                  <Select<SelectOption>
                    options={buyers.map(b => ({ value: b.id, label: `${b.buyerName}${b.company ? ` (${b.company})` : ''}${b.state ? ` - ${b.state}` : ''}` }))}
                    value={formData.buyerId ? { value: formData.buyerId, label: (() => { const b = buyers.find(x => x.id === formData.buyerId); return b ? `${b.buyerName}${b.company ? ` (${b.company})` : ''}${b.state ? ` - ${b.state}` : ''}` : ''; })() } : null}
                    onChange={(opt: SingleValue<SelectOption>) => {
                      const buyerId = opt?.value || '';
                      const selectedBuyer = buyers.find(b => b.id === buyerId);
                      const defaultAddr = (selectedBuyer?.shippingAddresses || []).find(a => a.isDefault);
                      setFormData(p => ({ ...p, buyerId, placeOfSupply: selectedBuyer?.state || p.placeOfSupply, shippingAddressId: defaultAddr?.id || '' }));
                    }}
                    placeholder="Search buyer by name..."
                    isSearchable
                    isClearable
                    styles={selectStyles}
                    noOptionsMessage={() => 'No buyers found'}
                    data-testid="buyer-select"
                    inputId="buyer-select"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Payment Due (days)</label>
                  <input type="number" min={1} max={365} value={formData.dueDays}
                    onChange={e => setFormData(p => ({ ...p, dueDays: parseInt(e.target.value) || 7 }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="due-days-input" />
                </div>
              </div>

              {/* Shipping Address */}
              {formData.buyerId && (() => {
                const selectedBuyer = buyers.find(b => b.id === formData.buyerId);
                const addrs = selectedBuyer?.shippingAddresses || [];
                return (
                  <div data-testid="shipping-address-section">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Shipping Address</label>
                    {addrs.length > 0 ? (
                      <select value={formData.shippingAddressId} onChange={e => setFormData(p => ({ ...p, shippingAddressId: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="shipping-address-select">
                        <option value="">Select shipping address</option>
                        {addrs.map(a => (
                          <option key={a.id} value={a.id}>
                            {a.addressLine1}, {a.city} - {a.pincode}{a.isDefault ? ' (Default)' : ''}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                        No shipping address found. <a href="/seller/business-tools/buyers" className="text-indigo-600 hover:underline font-medium">+ Add Address in Buyer section</a>
                      </div>
                    )}
                    {formData.shippingAddressId && (() => {
                      const addr = addrs.find(a => a.id === formData.shippingAddressId);
                      return addr ? (
                        <div className="mt-1.5 text-xs text-gray-500 bg-gray-50 rounded px-3 py-2" data-testid="shipping-address-preview">
                          <p>{addr.addressLine1}{addr.addressLine2 ? `, ${addr.addressLine2}` : ''}</p>
                          <p>{addr.city}, {addr.state} - {addr.pincode}, {addr.country}</p>
                          {addr.contactPerson && <p className="mt-0.5">Contact: {addr.contactPerson}{addr.phone ? ` (${addr.phone})` : ''}</p>}
                        </div>
                      ) : null;
                    })()}
                  </div>
                );
              })()}

              {/* Items */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Items *</label>
                <div className="space-y-3">
                  {formData.items.map((item, idx) => {
                    const base = item.quantity * item.price;
                    const discAmt = item.discountType === '%' ? base * (item.discount / 100) : (item.discount || 0);
                    const taxable = Math.max(base - discAmt, 0);
                    const gstLine = calcGstBreakdown(taxable, item.gstPercent, sellerState, effectivePlaceOfSupply);
                    const allFinalSpecs = [...item.selectedSpecs, ...item.customSpecs.filter(s => s.key && s.value)];
                    const isSameState = sellerState && effectivePlaceOfSupply && sellerState.trim().toLowerCase() === effectivePlaceOfSupply.trim().toLowerCase();
                    return (
                      <div key={idx} className="bg-gray-50 rounded-lg p-3 space-y-2" data-testid={`invoice-item-${idx}`}>
                        <div className="grid grid-cols-12 gap-2 items-start">
                          <div className="col-span-3">
                            <label className="text-xs text-gray-500 mb-1 block">Product</label>
                            <Select<ProductOption>
                              options={[
                                { value: '', label: 'Manual entry', stock: 0, reserved: 0, desc: '' },
                                ...listings.map(l => ({ value: l.id, label: l.productName, stock: l.availableStock, reserved: l.reservedStock, desc: l.description }))
                              ]}
                              value={item.productId ? { value: item.productId, label: listings.find(l => l.id === item.productId)?.productName || item.productName, stock: 0, reserved: 0, desc: '' } : null}
                              onChange={(opt: SingleValue<ProductOption>) => {
                                if (!opt || opt.value === '') {
                                  const items = [...formData.items];
                                  items[idx] = { ...items[idx], productId: '', productName: '', hsnCode: '', description: '', allSpecs: [], selectedSpecs: [], customSpecs: [], showSpecs: false };
                                  setFormData(p => ({ ...p, items }));
                                } else {
                                  onProductSelect(idx, opt.value);
                                }
                              }}
                              placeholder="Search product..."
                              isSearchable
                              isClearable
                              styles={productSelectStyles}
                              formatOptionLabel={(opt) => opt.value === '' ? (
                                <span className="text-gray-400 italic">Manual entry</span>
                              ) : (
                                <div className="flex items-center justify-between gap-2">
                                  <span className="truncate">{opt.label}{opt.desc ? <span className="text-gray-400 ml-1">— {opt.desc}</span> : ''}</span>
                                  <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">Avail: {opt.stock}{opt.reserved > 0 ? `, Res: ${opt.reserved}` : ''}</span>
                                </div>
                              )}
                              noOptionsMessage={() => 'No products found'}
                              inputId={`invoice-item-product-${idx}`}
                            />
                            {!item.productId && <input type="text" value={item.productName} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], productName: e.target.value }; setFormData(p => ({ ...p, items })); }} placeholder="Manual entry" className="w-full mt-1 px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-name-${idx}`} />}
                          </div>
                          <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">HSN</label><input type="text" value={item.hsnCode} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], hsnCode: e.target.value }; setFormData(p => ({ ...p, items })); }} placeholder="HSN" className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-hsn-${idx}`} /></div>
                          <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">Qty</label><input type="number" min={1} value={item.quantity} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], quantity: parseInt(e.target.value) || 1 }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm text-center" data-testid={`invoice-item-qty-${idx}`} /></div>
                          <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">Rate</label><input type="number" min={0} step={0.01} value={item.price} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], price: parseFloat(e.target.value) || 0 }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-price-${idx}`} /></div>
                          <div className="col-span-1">
                            <label className="text-xs text-gray-500 mb-1 block">Discount</label>
                            <div className="flex">
                              <input type="number" min={0} step={0.01} value={item.discount || ''} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], discount: parseFloat(e.target.value) || 0 }; setFormData(p => ({ ...p, items })); }} className="w-full px-1.5 py-1.5 border border-gray-300 rounded-l text-sm" placeholder="0" data-testid={`invoice-item-discount-${idx}`} />
                              <button type="button" onClick={() => { const items = [...formData.items]; items[idx] = { ...items[idx], discountType: items[idx].discountType === '%' ? 'Rs' : '%' }; setFormData(p => ({ ...p, items })); }} className="px-1.5 py-1.5 border border-l-0 border-gray-300 rounded-r text-xs font-medium bg-gray-100 hover:bg-gray-200 min-w-[28px]" data-testid={`invoice-item-discount-toggle-${idx}`}>{item.discountType === '%' ? '%' : 'Rs'}</button>
                            </div>
                            {discAmt > 0 && <span className="text-xs text-green-600 block mt-0.5">-{fmt(discAmt)}</span>}
                          </div>
                          <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">GST%</label><select value={item.gstPercent} onChange={e => { const items = [...formData.items]; items[idx] = { ...items[idx], gstPercent: parseFloat(e.target.value) }; setFormData(p => ({ ...p, items })); }} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid={`invoice-item-gst-${idx}`}>{[0, 5, 12, 18, 28].map(g => <option key={g} value={g}>{g}%</option>)}</select></div>
                          {isSameState ? (
                            <>
                              <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">CGST</label><div className="px-1 py-1.5 bg-blue-50 border border-blue-100 rounded text-xs text-right text-blue-700">{fmt(gstLine.cgst)}</div></div>
                              <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">SGST</label><div className="px-1 py-1.5 bg-blue-50 border border-blue-100 rounded text-xs text-right text-blue-700">{fmt(gstLine.sgst)}</div></div>
                            </>
                          ) : (
                            <div className="col-span-2"><label className="text-xs text-gray-500 mb-1 block">IGST</label><div className="px-1 py-1.5 bg-amber-50 border border-amber-100 rounded text-xs text-right text-amber-700">{fmt(gstLine.igst)}</div></div>
                          )}
                          <div className="col-span-1"><label className="text-xs text-gray-500 mb-1 block">Total</label><div className="px-1 py-1.5 bg-white border border-gray-200 rounded text-xs font-semibold text-right">{fmt(gstLine.total)}</div></div>
                          <div className="pt-5 flex gap-1">
                            {(item.allSpecs.length > 0 || item.customSpecs.length > 0) && <button onClick={() => { const items = [...formData.items]; items[idx] = { ...items[idx], showSpecs: !items[idx].showSpecs }; setFormData(p => ({ ...p, items })); }} className="text-indigo-400 hover:text-indigo-600">{item.showSpecs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</button>}
                            {formData.items.length > 1 && <button onClick={() => removeItem(idx)} className="text-red-400 hover:text-red-600" data-testid={`remove-invoice-item-${idx}`}><Trash2 className="w-4 h-4" /></button>}
                          </div>
                        </div>
                        {allFinalSpecs.length > 0 && !item.showSpecs && <p className="text-xs text-gray-500 ml-1">{allFinalSpecs.map(s => `${s.key}: ${s.value}`).join(' | ')}</p>}
                        {item.showSpecs && (
                          <div className="border border-gray-200 rounded-lg p-3 bg-white space-y-2" data-testid={`spec-selector-${idx}`}>
                            <p className="text-xs font-medium text-gray-600">Specifications</p>
                            {item.allSpecs.length > 0 && <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">{item.allSpecs.map((spec, si) => { const isC = item.selectedSpecs.some(s => s.key === spec.key && s.value === spec.value); return <label key={si} className={`flex items-center gap-1.5 px-2 py-1 rounded border text-xs cursor-pointer ${isC ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : 'bg-gray-50 border-gray-200 text-gray-500'}`}><input type="checkbox" checked={isC} onChange={() => toggleSpec(idx, si)} className="rounded w-3 h-3" /><span className="font-medium">{spec.key}:</span> {spec.value}</label>; })}</div>}
                            {item.customSpecs.map((cs, ci) => <div key={ci} className="flex items-center gap-2"><input type="text" value={cs.key} onChange={e => updateCustomSpec(idx, ci, 'key', e.target.value)} className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="Key" /><input type="text" value={cs.value} onChange={e => updateCustomSpec(idx, ci, 'value', e.target.value)} className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="Value" /><button onClick={() => removeCustomSpec(idx, ci)} className="text-red-400 hover:text-red-600"><X className="w-3.5 h-3.5" /></button></div>)}
                            <button onClick={() => addCustomSpec(idx)} className="text-xs text-indigo-600 hover:text-indigo-700 font-medium" data-testid={`add-custom-spec-${idx}`}>+ Add custom specification</button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <button onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2" data-testid="add-invoice-item-btn">+ Add Item</button>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Taxable Amount</span><span>{fmt(formTotals.subtotal)}</span></div>
                {formTotals.cgst > 0 && <div className="flex justify-between text-blue-600"><span>CGST</span><span>{fmt(formTotals.cgst)}</span></div>}
                {formTotals.sgst > 0 && <div className="flex justify-between text-blue-600"><span>SGST</span><span>{fmt(formTotals.sgst)}</span></div>}
                {formTotals.igst > 0 && <div className="flex justify-between text-amber-600"><span>IGST</span><span>{fmt(formTotals.igst)}</span></div>}
                {formTotals.gst === 0 && <div className="flex justify-between text-gray-400"><span>GST</span><span>0.00</span></div>}
                <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-2"><span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{fmt(formTotals.total)}</span></div>
                {sellerState && effectivePlaceOfSupply && (
                  <div className="text-xs text-gray-400 pt-1">
                    {sellerState.trim().toLowerCase() === effectivePlaceOfSupply.trim().toLowerCase()
                      ? `Intra-state (${sellerState}) - CGST + SGST`
                      : `Inter-state (${sellerState} to ${effectivePlaceOfSupply}) - IGST`}
                  </div>
                )}
                {!sellerState && <div className="text-xs text-amber-500 pt-1">Set your state in Business Settings for accurate GST calculation</div>}
              </div>
              <div className="flex items-center gap-2"><input type="checkbox" id="deductStock" checked={formData.deductStock} onChange={e => setFormData(p => ({ ...p, deductStock: e.target.checked }))} className="rounded" data-testid="deduct-stock-checkbox" /><label htmlFor="deductStock" className="text-sm text-gray-700">Deduct stock from inventory</label></div>
              {/* GST & Reference Fields */}
              <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                <h4 className="text-sm font-semibold text-gray-700">Invoice Reference & GST</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div><label className="block text-xs text-gray-500 mb-1">PO Number</label><input type="text" value={formData.poNumber} onChange={e => setFormData(p => ({ ...p, poNumber: e.target.value }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" placeholder="PO-001" data-testid="po-number-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Challan No.</label><input type="text" value={formData.challanNumber} onChange={e => setFormData(p => ({ ...p, challanNumber: e.target.value }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" placeholder="CH-001" data-testid="challan-number-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Place of Supply</label><select value={formData.placeOfSupply} onChange={e => setFormData(p => ({ ...p, placeOfSupply: e.target.value }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="place-of-supply-input"><option value="">Auto (Buyer State)</option>{INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                </div>
              </div>
              {/* Transport Details */}
              <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                <h4 className="text-sm font-semibold text-gray-700">Transport Details</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div><label className="block text-xs text-gray-500 mb-1">Transporter Name</label><input type="text" value={formData.transport.transporterName} onChange={e => setFormData(p => ({ ...p, transport: { ...p.transport, transporterName: e.target.value } }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="transporter-name-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">LR Number</label><input type="text" value={formData.transport.lrNumber} onChange={e => setFormData(p => ({ ...p, transport: { ...p.transport, lrNumber: e.target.value } }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="lr-number-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Vehicle Number</label><input type="text" value={formData.transport.vehicleNumber} onChange={e => setFormData(p => ({ ...p, transport: { ...p.transport, vehicleNumber: e.target.value } }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="vehicle-number-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Booking Location</label><input type="text" value={formData.transport.bookingLocation} onChange={e => setFormData(p => ({ ...p, transport: { ...p.transport, bookingLocation: e.target.value } }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="booking-location-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">No. of Packages</label><input type="text" value={formData.transport.numberOfPackages} onChange={e => setFormData(p => ({ ...p, transport: { ...p.transport, numberOfPackages: e.target.value } }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" data-testid="num-packages-input" /></div>
                </div>
              </div>
              {/* Payment Terms & Additional Charges */}
              <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                <h4 className="text-sm font-semibold text-gray-700">Payment & Additional Charges</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2"><label className="block text-xs text-gray-500 mb-1">Mode / Terms of Payment</label><input type="text" value={formData.paymentTerms} onChange={e => setFormData(p => ({ ...p, paymentTerms: e.target.value }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" placeholder="e.g. 100% advance, 30 days credit" data-testid="payment-terms-input" /></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Freight (Rs.)</label><input type="number" min="0" step="0.01" value={formData.freight || ''} onChange={e => setFormData(p => ({ ...p, freight: parseFloat(e.target.value) || 0 }))} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" placeholder="0.00" data-testid="freight-input" /></div>
                </div>
                <div className="flex items-center gap-4 pt-1">
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input type="checkbox" checked={formData.tcsEnabled} onChange={e => setFormData(p => ({ ...p, tcsEnabled: e.target.checked }))} className="rounded" data-testid="tcs-toggle" />
                    Apply TCS
                  </label>
                  {formData.tcsEnabled && (
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-gray-500">TCS %</label>
                      <input type="number" min="0" max="5" step="0.01" value={formData.tcsPercent} onChange={e => setFormData(p => ({ ...p, tcsPercent: Math.min(5, Math.max(0, parseFloat(e.target.value) || 0)) }))} className="w-20 px-2 py-1 border border-gray-300 rounded text-sm" data-testid="tcs-percent-input" />
                      <span className="text-xs text-gray-400">of taxable + GST</span>
                    </div>
                  )}
                </div>
                {/* Live charges preview */}
                {(formData.freight > 0 || formData.tcsEnabled) && (
                  <div className="bg-gray-50 rounded p-2 text-xs text-gray-600 space-y-0.5 mt-1" data-testid="charges-preview">
                    {formData.freight > 0 && <div className="flex justify-between"><span>Freight</span><span>Rs.{formData.freight.toFixed(2)}</span></div>}
                    {formData.tcsEnabled && <div className="flex justify-between"><span>TCS ({formData.tcsPercent}%)</span><span>Rs.{((formTotals.subtotal + formTotals.gst) * formData.tcsPercent / 100).toFixed(2)}</span></div>}
                    {(() => { const preRound = formTotals.total + formData.freight + (formData.tcsEnabled ? (formTotals.subtotal + formTotals.gst) * formData.tcsPercent / 100 : 0); const rounded = Math.round(preRound); const diff = +(rounded - preRound).toFixed(2); return (<><div className="flex justify-between"><span>Round Off</span><span>{diff >= 0 ? '+' : ''}{diff.toFixed(2)}</span></div><div className="flex justify-between font-semibold text-gray-800 border-t border-gray-200 pt-1 mt-1"><span>Grand Total</span><span>Rs.{rounded.toLocaleString('en-IN')}</span></div></>); })()}
                  </div>
                )}
              </div>
              {/* Terms */}
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Terms & Conditions</label><textarea value={formData.termsAndConditions} onChange={e => setFormData(p => ({ ...p, termsAndConditions: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} placeholder="Payment terms, conditions..." data-testid="terms-input" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Notes</label><textarea value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} data-testid="invoice-notes" /></div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-invoice-btn">Cancel</button>
              <button onClick={handleSubmit} className={`px-4 py-2 text-sm rounded-lg font-medium flex items-center gap-2 ${isOnline ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-amber-600 text-white hover:bg-amber-700'}`} data-testid="submit-invoice-btn">
                {!isOnline && <WifiOff className="w-3.5 h-3.5" />}
                {isOnline ? 'Create Invoice' : 'Save Draft (Offline)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Invoice Detail Modal ──── */}
      {viewInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="invoice-detail-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-lg font-semibold">{viewInvoice.invoiceNumber}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusColors[viewInvoice.status] || 'bg-gray-100 text-gray-700'}`}>{statusLabels[viewInvoice.status] || viewInvoice.status}</span>
                  {viewInvoice.sentAt && <span className="text-[11px] text-gray-400">Sent on {fmtDate(viewInvoice.sentAt)}{viewInvoice.sentVia ? ` via ${viewInvoice.sentVia}` : ''}</span>}
                </div>
              </div>
              <button onClick={() => setViewInvoice(null)} className="text-gray-400 hover:text-gray-600" data-testid="close-invoice-detail"><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-5 text-sm">
              <div><span className="text-gray-500">Buyer:</span> <span className="font-medium">{viewInvoice.buyerName}</span></div>
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{fmtDate(viewInvoice.date)}</span></div>
            </div>
            {/* Billing & Shipping Address */}
            {(() => {
              const sa = (viewInvoice as any)?.shippingAddress;
              const buyer = buyers.find(b => b.id === viewInvoice.buyerId);
              const billingAddr = buyer?.address || '';
              const hasShipping = sa && sa.addressLine1;
              const shippingStr = hasShipping ? `${sa.addressLine1} ${sa.city} ${sa.state} ${sa.pincode}`.toLowerCase().trim() : '';
              const isSame = billingAddr && shippingStr && billingAddr.toLowerCase().trim() === shippingStr;

              return (
                <div className="grid grid-cols-2 gap-4 mb-4" data-testid="invoice-addresses">
                  <div className="bg-gray-50 rounded-lg p-3 text-sm" data-testid="invoice-billing-addr">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Bill To</span>
                    <p className="text-gray-800 font-medium mt-1">{viewInvoice.buyerName}</p>
                    {buyer?.company && <p className="text-gray-600 text-xs">{buyer.company}</p>}
                    {billingAddr && <p className="text-gray-600 mt-0.5">{billingAddr}</p>}
                    {buyer?.gstNumber && <p className="text-xs text-gray-500 mt-0.5"><span className="font-medium">GSTIN:</span> {buyer.gstNumber}</p>}
                    {buyer?.phone && <p className="text-xs text-gray-500">Ph: {buyer.phone}</p>}
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-sm" data-testid="invoice-shipping-addr">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Ship To</span>
                    {hasShipping && !isSame ? (
                      <>
                        {sa.contactPerson && <p className="text-gray-800 font-medium mt-1">{sa.contactPerson}</p>}
                        <p className="text-gray-600 mt-0.5">{sa.addressLine1}{sa.addressLine2 ? `, ${sa.addressLine2}` : ''}</p>
                        <p className="text-gray-600">{sa.city}, {sa.state} - {sa.pincode}</p>
                        {sa.phone && <p className="text-xs text-gray-500 mt-0.5">Ph: {sa.phone}</p>}
                      </>
                    ) : (
                      <p className="text-gray-500 italic mt-1">Same as Billing Address</p>
                    )}
                  </div>
                </div>
              );
            })()}
            {/* Items Table */}
            <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200 text-gray-500 text-xs uppercase">
                <th className="text-left py-2">Product</th><th className="text-left py-2">HSN</th><th className="text-right py-2">Qty</th><th className="text-right py-2">Rate</th><th className="text-right py-2">Taxable</th>
                {(viewInvoice.taxType === 'intra' || (viewInvoice.cgst && viewInvoice.cgst > 0)) ? (
                  <><th className="text-right py-2">CGST</th><th className="text-right py-2">SGST</th></>
                ) : (
                  <th className="text-right py-2">IGST</th>
                )}
                <th className="text-right py-2">Total</th>
              </tr></thead>
              <tbody>{viewInvoice.items.map((item, i) => (
                <tr key={i} className="border-b border-gray-50">
                  <td className="py-2"><div className="font-medium">{item.productName}</div>{item.description && <div className="text-[10px] text-gray-500 mt-0.5">({item.description})</div>}{item.selected_specifications && item.selected_specifications.length > 0 && <div className="text-[10px] text-gray-400 mt-0.5">{item.selected_specifications.map(s => `${s.key}: ${s.value}`).join(' | ')}</div>}</td>
                  <td className="py-2 text-xs text-gray-500">{item.hsnCode || '-'}</td>
                  <td className="py-2 text-right">{item.quantity}</td>
                  <td className="py-2 text-right">{fmt(item.price)}</td>
                  <td className="py-2 text-right">{fmt(item.taxableAmount || item.quantity * item.price)}</td>
                  {(viewInvoice.taxType === 'intra' || (viewInvoice.cgst && viewInvoice.cgst > 0)) ? (
                    <><td className="py-2 text-right text-blue-600">{fmt(item.cgst || 0)}</td><td className="py-2 text-right text-blue-600">{fmt(item.sgst || 0)}</td></>
                  ) : (
                    <td className="py-2 text-right text-amber-600">{fmt(item.igst || 0)}</td>
                  )}
                  <td className="py-2 text-right font-medium">{fmt(item.total)}</td>
                </tr>
              ))}</tbody>
            </table>
            </div>
            {/* Payment Summary */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm mb-5" data-testid="payment-summary">
              <div className="flex justify-between"><span className="text-gray-500">Taxable Amount</span><span>{fmt(viewInvoice.subtotal)}</span></div>
              {(viewInvoice.cgst ?? 0) > 0 && <div className="flex justify-between text-blue-600"><span>CGST</span><span>{fmt(viewInvoice.cgst || 0)}</span></div>}
              {(viewInvoice.sgst ?? 0) > 0 && <div className="flex justify-between text-blue-600"><span>SGST</span><span>{fmt(viewInvoice.sgst || 0)}</span></div>}
              {(viewInvoice.igst ?? 0) > 0 && <div className="flex justify-between text-amber-600"><span>IGST</span><span>{fmt(viewInvoice.igst || 0)}</span></div>}
              {viewInvoice.gst === 0 && <div className="flex justify-between text-gray-400"><span>GST</span><span>0.00</span></div>}
              {viewInvoice.placeOfSupply && <div className="text-xs text-gray-400">Place of Supply: {viewInvoice.placeOfSupply}{viewInvoice.taxType === 'intra' ? ' (Intra-state)' : viewInvoice.taxType === 'inter' ? ' (Inter-state)' : ''}</div>}
              {/* Additional Charges */}
              {(viewInvoice.additionalCharges || []).filter(c => c.amount > 0).map((ch, i) => (
                <div key={i} className="flex justify-between text-gray-600"><span>{ch.name}</span><span>{fmt(ch.amount)}</span></div>
              ))}
              {viewInvoice.tcsEnabled && (viewInvoice.tcsAmount ?? 0) > 0 && (
                <div className="flex justify-between text-purple-600"><span>TCS ({viewInvoice.tcsPercent}%)</span><span>{fmt(viewInvoice.tcsAmount || 0)}</span></div>
              )}
              {(viewInvoice.roundOff ?? 0) !== 0 && (
                <div className="flex justify-between text-gray-400"><span>Round Off</span><span>{(viewInvoice.roundOff ?? 0) >= 0 ? '+' : ''}{(viewInvoice.roundOff ?? 0).toFixed(2)}</span></div>
              )}
              <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-1"><span>Grand Total</span><span className="flex items-center gap-1"><IndianRupee className="w-4 h-4" />{fmt(viewInvoice.total)}</span></div>
              {viewInvoice.paymentTerms && <div className="text-xs text-gray-500 pt-1">Payment Terms: {viewInvoice.paymentTerms}</div>}
              <div className="flex justify-between text-emerald-600 font-medium"><span className="flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Total Paid</span><span>{fmt(viewInvoice.totalPaid || 0)}</span></div>
              <div className="flex justify-between text-amber-600 font-medium"><span className="flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" /> Pending Amount</span><span>{fmt(viewInvoice.pendingAmount ?? viewInvoice.total)}</span></div>
            </div>
            {/* Payment History */}
            <div className="mb-5" data-testid="payment-history-section">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5"><Clock className="w-4 h-4 text-indigo-500" /> Payment History</h3>
                {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                  <button onClick={() => openPaymentModal(viewInvoice.id)} className="flex items-center gap-1.5 bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-emerald-700" data-testid="add-payment-btn"><Plus className="w-3.5 h-3.5" /> Add Payment</button>
                )}
              </div>
              {(!viewInvoice.payments || viewInvoice.payments.length === 0) ? (
                <div className="text-center py-6 bg-gray-50 rounded-lg border border-dashed border-gray-200" data-testid="no-payments"><Banknote className="w-8 h-8 text-gray-300 mx-auto mb-2" /><p className="text-xs text-gray-400">No payments recorded yet</p></div>
              ) : (
                <div className="space-y-2">
                  {viewInvoice.payments.map((payment) => (
                    <div key={payment.id} className="bg-white border border-gray-100 rounded-lg p-3" data-testid={`payment-entry-${payment.id}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-gray-800 flex items-center gap-1"><IndianRupee className="w-3.5 h-3.5" />{fmt(payment.amount)}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 font-medium uppercase">{payment.paymentMethod?.replace('_', ' ')}</span>
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500">
                            <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{fmtDate(payment.paymentDate)}</span>
                            {payment.accountName && <span>Account: {payment.accountName}</span>}
                            {payment.referenceNumber && <span>Ref: {payment.referenceNumber}</span>}
                          </div>
                          {payment.notes && <p className="text-xs text-gray-400 mt-1">{payment.notes}</p>}
                        </div>
                        <button onClick={() => deletePayment(viewInvoice.id, payment.id)} className="text-gray-300 hover:text-red-500 ml-2 flex-shrink-0" data-testid={`delete-payment-${payment.id}`} title="Delete payment"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                      {/* Receipt thumbnails */}
                      {payment.receiptUrls && payment.receiptUrls.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-gray-50" data-testid={`receipts-${payment.id}`}>
                          {payment.receiptUrls.map((url, ri) => {
                            const isPdf = url.includes('/raw/upload/') || url.endsWith('.pdf');
                            return isPdf ? (
                              <a key={ri} href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 px-2 py-1 bg-red-50 rounded border border-red-100 text-xs text-red-600 hover:bg-red-100" data-testid={`receipt-pdf-${ri}`}>
                                <FileDown className="w-3.5 h-3.5" /> PDF Receipt
                              </a>
                            ) : (
                              <button key={ri} onClick={() => setPreviewImage(url)} className="w-12 h-12 rounded border border-gray-200 overflow-hidden hover:border-indigo-300 transition" data-testid={`receipt-thumb-${ri}`}>
                                <img src={url} alt="Receipt" className="w-full h-full object-cover" />
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            {viewInvoice.notes && <div className="text-sm text-gray-600 mb-4"><span className="font-medium">Notes:</span> {viewInvoice.notes}</div>}
            {/* Actions */}
            <div className="space-y-3 border-t border-gray-100 pt-4">
              {/* Invoice PDF Download */}
              <div>
                <button onClick={() => openPdfModal(viewInvoice.id, viewInvoice.invoiceNumber)} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700" data-testid="download-pdf-btn"><Download className="w-4 h-4" /> Download PDF</button>
              </div>
              {/* Actions Row */}
              <div className="flex gap-2 flex-wrap">
                {viewInvoice.buyerPhone && (
                  <button onClick={() => openWhatsApp(viewInvoice, 'send_invoice')}
                    className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700" data-testid="send-invoice-whatsapp-btn">
                    <Send className="w-4 h-4" /> Send Invoice WhatsApp
                  </button>
                )}
                <button onClick={() => openEwayBill(viewInvoice.id)}
                  className="flex items-center gap-1 bg-amber-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-amber-700" data-testid="eway-bill-btn">
                  <ExternalLink className="w-4 h-4" /> Generate E-Way Bill
                </button>
                {viewInvoice.status === 'draft' && <button onClick={() => updateStatus(viewInvoice.id, 'sent')} className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700" data-testid="mark-sent-btn"><Send className="w-4 h-4" /> Mark Sent</button>}
                {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                  <button onClick={() => openPaymentModal(viewInvoice.id)} className="flex items-center gap-1 bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-emerald-700" data-testid="add-payment-action-btn"><CreditCard className="w-4 h-4" /> Add Payment</button>
                )}
                {(viewInvoice.pendingAmount ?? viewInvoice.total) > 0 && viewInvoice.status !== 'cancelled' && (
                  <button onClick={() => openWhatsApp(viewInvoice, viewInvoice.status === 'overdue' ? 'overdue' : 'followup')}
                    className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700" data-testid="whatsapp-followup-btn">
                    <MessageCircle className="w-4 h-4" /> {viewInvoice.status === 'overdue' ? 'Overdue Reminder' : 'WhatsApp Follow-Up'}
                  </button>
                )}
                {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && (
                  <button onClick={() => updateStatus(viewInvoice.id, 'overdue')} className="flex items-center gap-1 text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg text-sm font-medium" data-testid="mark-overdue-btn"><AlertCircle className="w-4 h-4" /> Mark Overdue</button>
                )}
                {viewInvoice.status !== 'cancelled' && viewInvoice.status !== 'paid' && <button onClick={() => updateStatus(viewInvoice.id, 'cancelled')} className="text-red-500 hover:text-red-700 px-3 py-1.5 text-sm font-medium" data-testid="cancel-invoice-status-btn">Cancel</button>}
                {(viewInvoice.status === 'draft' || viewInvoice.status === 'cancelled') && <button onClick={() => deleteInvoice(viewInvoice.id)} className="text-red-500 hover:text-red-700 px-3 py-1.5 text-sm font-medium" data-testid="delete-invoice-btn"><Trash2 className="w-4 h-4 inline mr-1" />Delete</button>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ──── Add Payment Modal ──── */}
      {showPaymentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4" data-testid="add-payment-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold flex items-center gap-2"><CreditCard className="w-5 h-5 text-emerald-600" /> Record Payment</h2>
              <button onClick={() => setShowPaymentModal(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount *</label>
                <div className="relative"><IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input type="number" min={0.01} step={0.01} value={paymentForm.amount} onChange={e => setPaymentForm(p => ({ ...p, amount: e.target.value }))} className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="0.00" data-testid="payment-amount-input" />
                </div>
              </div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Payment Date</label><input type="date" value={paymentForm.paymentDate} onChange={e => setPaymentForm(p => ({ ...p, paymentDate: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="payment-date-input" /></div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Payment Method</label>
                <select value={paymentForm.paymentMethod} onChange={e => setPaymentForm(p => ({ ...p, paymentMethod: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" data-testid="payment-method-select">
                  {paymentMethods.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Sender Account Name</label><input type="text" value={paymentForm.accountName} onChange={e => setPaymentForm(p => ({ ...p, accountName: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. John Doe" data-testid="payment-account-name-input" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Reference Number</label><input type="text" value={paymentForm.referenceNumber} onChange={e => setPaymentForm(p => ({ ...p, referenceNumber: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="UPI Ref / Transaction ID" data-testid="payment-reference-input" /></div>
              {/* Receipt Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Payment Receipt {isReceiptRequired(paymentForm.paymentMethod) ? <span className="text-red-500">*</span> : <span className="text-gray-400">(optional)</span>}
                </label>
                {isReceiptRequired(paymentForm.paymentMethod) && (
                  <p className="text-xs text-amber-600 mb-2 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Receipt is mandatory for {paymentForm.paymentMethod.replace('_', ' ')} payments</p>
                )}
                <input type="file" ref={receiptInputRef} onChange={handleReceiptSelect} accept="image/jpeg,image/png,image/webp,application/pdf" multiple className="hidden" />
                <button onClick={() => receiptInputRef.current?.click()} className="flex items-center gap-2 w-full px-3 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-indigo-300 hover:text-indigo-600 transition" data-testid="receipt-upload-btn">
                  <Upload className="w-4 h-4" /> Upload Receipt (JPG, PNG, PDF)
                </button>
                {/* Staged files */}
                {receiptFiles.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {receiptFiles.map((f, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-50 px-2 py-1.5 rounded text-xs">
                        <span className="flex items-center gap-1 truncate"><Paperclip className="w-3 h-3" />{f.name} ({(f.size / 1024).toFixed(0)}KB)</span>
                        <button onClick={() => removeReceiptFile(i)} className="text-red-400 hover:text-red-600 ml-2"><X className="w-3.5 h-3.5" /></button>
                      </div>
                    ))}
                  </div>
                )}
                {uploadedReceiptUrls.length > 0 && (
                  <div className="mt-2 flex gap-2 flex-wrap">
                    {uploadedReceiptUrls.map((url, i) => (
                      <div key={i} className="w-10 h-10 rounded border border-green-200 overflow-hidden"><img src={url} alt="" className="w-full h-full object-cover" /></div>
                    ))}
                  </div>
                )}
              </div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Notes</label><textarea value={paymentForm.notes} onChange={e => setPaymentForm(p => ({ ...p, notes: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} placeholder="Optional notes" data-testid="payment-notes-input" /></div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowPaymentModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-payment-btn">Cancel</button>
              <button onClick={submitPayment} disabled={paymentLoading || receiptUploading}
                className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50" data-testid="submit-payment-btn">
                {receiptUploading ? 'Uploading...' : paymentLoading ? 'Recording...' : 'Record Payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Reminder Settings Modal ──── */}
      {showReminderSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4" data-testid="reminder-settings-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Settings className="w-5 h-5 text-gray-600" /> Reminder Settings</h2>
              <button onClick={() => setShowReminderSettings(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <input type="checkbox" id="remindersEnabled" checked={reminderSettings.enabled} onChange={e => setReminderSettings(p => ({ ...p, enabled: e.target.checked }))} className="rounded" data-testid="reminders-enabled-toggle" />
                <label htmlFor="remindersEnabled" className="text-sm font-medium text-gray-700">Enable Payment Reminders</label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reminder Days (comma-separated)</label>
                <input type="text" value={reminderDaysInput} onChange={e => setReminderDaysInput(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="3, 7, 15" data-testid="reminder-days-input" />
                <p className="text-xs text-gray-400 mt-1">Days after invoice date when reminders appear. Default: 3, 7, 15</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs font-medium text-gray-600 mb-2">Reminder Schedule Preview</p>
                {reminderDaysInput.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n) && n > 0).sort((a, b) => a - b).map((day, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs py-1">
                    <span className={`w-2 h-2 rounded-full ${day <= 3 ? 'bg-blue-400' : day <= 7 ? 'bg-amber-400' : 'bg-red-400'}`} />
                    <span className="text-gray-600">Day {day}:</span>
                    <span className="text-gray-500">{day <= 3 ? 'Friendly reminder' : day <= 7 ? 'Payment due reminder' : 'Overdue reminder'}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowReminderSettings(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={saveReminderSettings} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium" data-testid="save-reminder-settings-btn">Save Settings</button>
            </div>
          </div>
        </div>
      )}

      {/* ──── PDF Copy Selection Modal ──── */}
      {showPdfModal && pdfModalInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4" data-testid="pdf-copy-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold flex items-center gap-2"><FileDown className="w-5 h-5 text-indigo-600" /> Download Invoice PDF</h2>
              <button onClick={() => setShowPdfModal(false)} className="text-gray-400 hover:text-gray-600" data-testid="close-pdf-modal"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-gray-500 mb-4">Invoice: <span className="font-medium text-gray-700">{pdfModalInvoice.invoiceNumber}</span></p>
            <div className="space-y-1 mb-4">
              <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer border border-gray-100" data-testid="select-all-copies">
                <input type="checkbox" checked={allCopiesSelected} onChange={e => toggleAllCopies(e.target.checked)} className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                <span className="text-sm font-medium text-gray-800">Select All</span>
              </label>
              <div className="h-px bg-gray-100 my-1" />
              {([
                { key: 'original', label: 'Original for Recipient' },
                { key: 'transporter', label: 'Duplicate for Transporter' },
                { key: 'supplier', label: 'Triplicate for Supplier / CA' },
                { key: 'office', label: 'Office Copy' },
              ] as const).map(item => (
                <label key={item.key} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer" data-testid={`copy-check-${item.key}`}>
                  <input type="checkbox" checked={pdfCopies[item.key]} onChange={() => togglePdfCopy(item.key)} className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                  <span className="text-sm text-gray-700">{item.label}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowPdfModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="cancel-pdf-modal">Cancel</button>
              <button onClick={downloadMergedPdf} disabled={pdfDownloading || selectedCopyCount === 0}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50" data-testid="download-selected-btn">
                {pdfDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                {pdfDownloading ? 'Generating...' : `Download Selected (${selectedCopyCount})`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Image Preview Modal ──── */}
      {previewImage && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[70] p-4" onClick={() => setPreviewImage(null)} data-testid="image-preview-modal">
          <div className="relative max-w-3xl max-h-[90vh]">
            <button onClick={() => setPreviewImage(null)} className="absolute -top-3 -right-3 bg-white rounded-full p-1 shadow-lg text-gray-600 hover:text-gray-800"><X className="w-5 h-5" /></button>
            <img src={previewImage} alt="Receipt" className="max-w-full max-h-[85vh] rounded-lg shadow-xl" />
            <a href={previewImage} target="_blank" rel="noopener noreferrer" className="absolute bottom-3 right-3 flex items-center gap-1 bg-white/90 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-700 hover:bg-white">
              <ExternalLink className="w-3.5 h-3.5" /> Open Full Size
            </a>
          </div>
        </div>
      )}

      {/* ──── Offline Drafts Section ──── */}
      {offlineDrafts.length > 0 && (
        <div className="mb-4 bg-amber-50 border border-amber-200 rounded-xl p-4" data-testid="offline-drafts-section">
          <div className="flex items-center gap-2 mb-3">
            <CloudOff className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-semibold text-amber-800">Offline Drafts ({offlineDrafts.length})</h3>
            <span className="text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">Will sync when online</span>
          </div>
          <div className="space-y-2">
            {offlineDrafts.map(draft => {
              const d = draft.data as Record<string, unknown>;
              const buyerName = buyers.find(b => b.id === d.buyerId)?.buyerName || 'Unknown Buyer';
              const items = (d.items as Array<Record<string, unknown>>) || [];
              const itemCount = items.length;
              return (
                <div key={draft.id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-amber-100" data-testid={`offline-draft-${draft.id}`}>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-amber-600">
                      <WifiOff className="w-3.5 h-3.5" />
                      <span className="text-xs font-medium bg-amber-100 px-2 py-0.5 rounded">Draft (Offline)</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{buyerName}</p>
                      <p className="text-xs text-gray-500">{itemCount} item{itemCount !== 1 ? 's' : ''} &middot; {new Date(draft.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {draft.status === 'failed' && (
                      <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded" title={draft.lastError}>Sync failed</span>
                    )}
                    {draft.status === 'syncing' && (
                      <span className="text-xs text-blue-600 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Syncing...</span>
                    )}
                    <button onClick={() => deleteDraftOffline(draft.id)} className="text-gray-400 hover:text-red-500 p-1" data-testid={`delete-offline-draft-${draft.id}`} title="Delete draft">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ──── Invoice List ──── */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : filteredInvoices.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100" data-testid="empty-state"><FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" /><p className="text-gray-500 font-medium">No invoices yet</p><p className="text-sm text-gray-400 mt-1">Create your first invoice to get started</p></div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <table className="w-full text-sm" data-testid="invoices-table">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                <th className="text-left px-4 py-3">Invoice #</th><th className="text-left px-4 py-3">Buyer</th><th className="text-left px-4 py-3">Date</th>
                <th className="text-right px-4 py-3">Total</th><th className="text-right px-4 py-3">Paid</th><th className="text-right px-4 py-3">Pending</th>
                <th className="text-center px-4 py-3">Status</th><th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.map(inv => (
                <tr key={inv.id} className={`border-b border-gray-50 hover:bg-gray-50/50 ${inv.status === 'overdue' ? 'bg-red-50/30' : ''}`} data-testid={`invoice-row-${inv.id}`}>
                  <td className="px-4 py-3 font-medium text-indigo-600 cursor-pointer" onClick={() => openInvoiceDetail(inv)}>{inv.invoiceNumber}</td>
                  <td className="px-4 py-3 text-gray-700">{inv.buyerName}</td>
                  <td className="px-4 py-3 text-gray-500">{fmtDate(inv.date)}</td>
                  <td className="px-4 py-3 text-right font-medium"><span className="flex items-center justify-end gap-0.5"><IndianRupee className="w-3.5 h-3.5" />{fmt(inv.total)}</span></td>
                  <td className="px-4 py-3 text-right text-emerald-600 font-medium" data-testid={`invoice-paid-${inv.id}`}>{fmt(inv.totalPaid || 0)}</td>
                  <td className={`px-4 py-3 text-right font-medium ${inv.status === 'overdue' ? 'text-red-600' : 'text-amber-600'}`} data-testid={`invoice-pending-${inv.id}`}>{fmt(inv.pendingAmount ?? inv.total)}</td>
                  <td className="px-4 py-3 text-center"><span className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${statusColors[inv.status] || 'bg-gray-100 text-gray-700'}`} data-testid={`invoice-status-${inv.id}`}>{statusLabels[inv.status] || inv.status}</span></td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button onClick={() => openInvoiceDetail(inv)} className="text-gray-400 hover:text-indigo-600" data-testid={`view-invoice-${inv.id}`} title="View"><Eye className="w-4 h-4" /></button>
                      <button onClick={() => openPdfModal(inv.id, inv.invoiceNumber)} className="text-gray-400 hover:text-indigo-600" data-testid={`download-invoice-${inv.id}`} title="Download PDF"><Download className="w-4 h-4" /></button>
                      {inv.buyerPhone && <button onClick={() => openWhatsApp(inv, 'send_invoice')} className="text-gray-400 hover:text-green-600" data-testid={`send-invoice-wa-${inv.id}`} title="Send Invoice WhatsApp"><Send className="w-4 h-4" /></button>}
                      {inv.status !== 'cancelled' && inv.status !== 'paid' && <button onClick={() => openPaymentModal(inv.id)} className="text-gray-400 hover:text-emerald-600" data-testid={`add-payment-row-${inv.id}`} title="Add Payment"><CreditCard className="w-4 h-4" /></button>}
                      {(inv.pendingAmount ?? inv.total) > 0 && inv.buyerPhone && inv.status !== 'cancelled' && <button onClick={() => openWhatsApp(inv, inv.status === 'overdue' ? 'overdue' : 'followup')} className="text-gray-400 hover:text-green-600" data-testid={`wa-invoice-${inv.id}`} title="WhatsApp"><MessageCircle className="w-4 h-4" /></button>}
                      {(inv.status === 'draft' || inv.status === 'cancelled') && <button onClick={() => deleteInvoice(inv.id)} className="text-gray-400 hover:text-red-600" data-testid={`delete-invoice-${inv.id}`} title="Delete"><Trash2 className="w-4 h-4" /></button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* ── Stock Shortage Modal ── */}
      {shortageModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="shortage-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 rounded-lg"><AlertTriangle className="h-5 w-5 text-amber-600" /></div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Stock Insufficient</h3>
                <p className="text-sm text-gray-500">Some items exceed available stock</p>
              </div>
            </div>
            <div className="space-y-3 mb-6">
              {shortageModal.shortages.map((s, i) => (
                <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-3" data-testid={`shortage-item-${i}`}>
                  <p className="font-medium text-gray-900">{s.productName}</p>
                  <div className="flex flex-wrap gap-4 mt-1 text-sm">
                    <span>Available: <strong className="text-emerald-600">{s.availableStock}</strong></span>
                    <span>Requested: <strong>{s.requestedQty}</strong></span>
                    <span>Shortage: <strong className="text-red-600">{s.shortage}</strong></span>
                    {s.reservedStock > 0 && <span className="text-xs text-gray-500">(Reserved: {s.reservedStock})</span>}
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <button onClick={() => handleShortageAction('partial')} disabled={shortageSubmitting}
                className="w-full flex items-center justify-between px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
                data-testid="shortage-partial-btn">
                <div className="text-left">
                  <p className="font-medium text-sm">Deliver Available Stock & Create Pending Order</p>
                  <p className="text-xs text-indigo-200">Invoice for available qty, backorder for the rest</p>
                </div>
                {shortageSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />}
              </button>
              <button onClick={() => handleShortageAction('cancel')}
                className="w-full px-4 py-3 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition text-left"
                data-testid="shortage-cancel-btn">
                Cancel — Go back to edit invoice
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
